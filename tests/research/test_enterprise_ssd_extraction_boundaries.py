"""Architecture boundary tests for 6C modules.

Enforces:
- Research extraction module imports ONLY stdlib + approved research modules
- Execution specification-evidence module imports approved modules only
- Neither imports providers (execution imports protocol via providers.page only)
- Neither imports evaluation, web, django, semantic, runs
"""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Research extraction module boundaries
# ---------------------------------------------------------------------------


def test_enterprise_ssd_extraction_imports_no_forbidden_modules() -> None:
    """The research extraction module must not import forbidden modules."""
    module_path = BASE_DIR / "product_intelligence" / "research" / "enterprise_ssd_extraction.py"
    source = module_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(module_path))

    forbidden_modules = {
        "product_intelligence.providers",
        "product_intelligence.execution",
        "product_intelligence.runs",
        "product_intelligence.web",
        "product_intelligence.semantic",
        "product_intelligence.evaluation",
        "django",
        "requests",
        "httpx",
        "urllib",
        "socket",
        "os",
        "sys",
        "subprocess",
        "pathlib",
    }

    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)

    # Extract top-level package
    top_level_imports = {imp.split(".")[0] for imp in imports}
    # Check against allowed research packages
    allowed_research_imports = {
        "product_intelligence",  # parent package
        "json",
        "re",
        "datetime",
        "typing",
    }

    forbidden_found = set()
    for imp in imports:
        for forbidden in forbidden_modules:
            if imp == forbidden or imp.startswith(forbidden + "."):
                # Check if it's an allowed research submodule
                if imp.startswith("product_intelligence.research") or imp.startswith("product_intelligence.domain"):
                    continue
                forbidden_found.add(imp)

    assert not forbidden_found, (
        f"enterprise_ssd_extraction.py imports forbidden modules: {forbidden_found}"
    )


def test_enterprise_ssd_extraction_may_only_import_research_and_domain() -> None:
    """The extraction module may only import from research.* and domain.* within the product."""
    module_path = BASE_DIR / "product_intelligence" / "research" / "enterprise_ssd_extraction.py"
    source = module_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(module_path))

    product_intelligence_imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("product_intelligence"):
                product_intelligence_imports.append(node.module)

    for imp in product_intelligence_imports:
        assert imp.startswith("product_intelligence.research") or \
               imp.startswith("product_intelligence.domain"), (
            f"enterprise_ssd_extraction.py imports {imp} which is not "
            f"research.* or domain.*"
        )


# ---------------------------------------------------------------------------
# Execution specification-evidence module boundaries
# ---------------------------------------------------------------------------


def test_specification_evidence_execution_imports_no_forbidden_modules() -> None:
    """The execution module must not import forbidden modules."""
    module_path = BASE_DIR / "product_intelligence" / "execution" / "specification_evidence.py"
    source = module_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(module_path))

    forbidden_modules = {
        "product_intelligence.web",
        "product_intelligence.semantic",
        "product_intelligence.evaluation",
        "django",
    }

    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)

    forbidden_found = set()
    for imp in imports:
        for forbidden in forbidden_modules:
            if imp == forbidden or imp.startswith(forbidden + "."):
                forbidden_found.add(imp)

    assert not forbidden_found, (
        f"specification_evidence.py imports forbidden modules: {forbidden_found}"
    )


def test_specification_evidence_does_not_import_concrete_vendor_adapters() -> None:
    """The execution module must not import HttpPageFetcher or other concrete adapters."""
    module_path = BASE_DIR / "product_intelligence" / "execution" / "specification_evidence.py"
    source = module_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(module_path))

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and "http_page" in (node.module or ""):
                pytest.fail(
                    "specification_evidence.py must not import http_page (concrete adapter). "
                    "It must depend on the PageFetcher protocol only."
                )


# ---------------------------------------------------------------------------
# Import runtime checks
# ---------------------------------------------------------------------------


def test_enterprise_ssd_extraction_does_not_load_providers() -> None:
    """Importing the extraction module must not load any provider module."""
    # Evict modules that might be cached
    modules_to_check = [
        "product_intelligence.providers.http_page",
        "product_intelligence.providers.serper",
    ]
    for mod_name in modules_to_check:
        if mod_name in sys.modules:
            del sys.modules[mod_name]

    # Import the extraction module
    import product_intelligence.research.enterprise_ssd_extraction  # noqa: F401

    for mod_name in modules_to_check:
        assert mod_name not in sys.modules, (
            f"Importing enterprise_ssd_extraction loaded {mod_name}"
        )


def test_enterprise_ssd_extraction_does_not_load_evaluation() -> None:
    """Importing the extraction module must not load evaluation."""
    if "product_intelligence.evaluation" in sys.modules:
        del sys.modules["product_intelligence.evaluation"]

    import product_intelligence.research.enterprise_ssd_extraction  # noqa: F401

    assert "product_intelligence.evaluation" not in sys.modules, (
        "Importing enterprise_ssd_extraction loaded evaluation module"
    )
