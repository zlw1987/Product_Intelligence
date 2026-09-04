"""Architecture boundary tests for PRODUCT-INTEL.6A specifications module.

Prove that product_intelligence/research/specifications.py does NOT import:
    Django, runs, providers, web, execution, semantic,
    evaluation corpus, network modules, filesystem modules.

Allowed: standard library + existing domain contracts (product_intelligence.domain).
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "product_intelligence"
RESEARCH_ROOT = PACKAGE_ROOT / "research"
SPECIFICATIONS_MODULE = RESEARCH_ROOT / "specifications.py"


def _imported_modules(path: Path) -> set[str]:
    """Every dotted module name imported by a file, absolute imports only."""
    modules: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            modules.add(node.module)
    return modules


def _top_level_imports(source: str) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                continue
            if node.module:
                modules.add(node.module.split(".")[0])
    return modules


def test_specifications_module_exists() -> None:
    assert SPECIFICATIONS_MODULE.exists()


def test_specifications_module_imports_only_domain_and_stdlib() -> None:
    """No framework, no vendor library, no HTTP client, no model client."""
    source = SPECIFICATIONS_MODULE.read_text(encoding="utf-8")
    modules = _top_level_imports(source)
    disallowed = {
        module
        for module in modules
        if module != "product_intelligence" and module not in sys.stdlib_module_names
    }
    assert not disallowed, (
        f"specifications.py imports non-stdlib modules {sorted(disallowed)}"
    )


def test_specifications_module_imports_no_persistence_provider_or_web() -> None:
    """No Django, runs, providers, web, execution, semantic, evaluation, etc."""
    imported = _imported_modules(SPECIFICATIONS_MODULE)
    forbidden_prefixes = (
        "django",
        "product_intelligence.runs",
        "product_intelligence.providers",
        "product_intelligence.evaluation",
        "product_intelligence.web",
        "product_intelligence.execution",
        "product_intelligence.semantic",
    )
    for forbidden in forbidden_prefixes:
        offending = {
            module
            for module in imported
            if module == forbidden or module.startswith(f"{forbidden}.")
        }
        assert not offending, f"specifications.py imports {sorted(offending)}"


def test_specifications_module_performs_no_network_or_file_access() -> None:
    """No network, filesystem, subprocess, or environment access."""
    source = SPECIFICATIONS_MODULE.read_text(encoding="utf-8")
    imported = _imported_modules(SPECIFICATIONS_MODULE) | _top_level_imports(source)
    io_modules = {
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
    }
    offending = {
        module
        for module in imported
        for forbidden in io_modules
        if module == forbidden or module.startswith(f"{forbidden}.")
    }
    assert not offending, (
        f"specifications.py imports I/O modules {sorted(offending)}"
    )


def test_specifications_module_depends_on_domain_contracts() -> None:
    """The permitted direction: research imports domain."""
    imported = _imported_modules(SPECIFICATIONS_MODULE)
    assert any(
        m.startswith("product_intelligence.domain") for m in imported
    ), "specifications.py must import domain contracts"


def test_specifications_module_adds_no_model_and_no_migration() -> None:
    """6A is pure framework — no Django model, no migration."""
    assert not list(RESEARCH_ROOT.rglob("specifications/models.py"))
    # The research directory should not have migrations
    migrations = RESEARCH_ROOT / "migrations"
    assert not migrations.exists() or not list(migrations.rglob("*.py"))


def test_importing_specifications_pulls_in_no_third_party_dependency() -> None:
    """Import it in a clean interpreter and look."""
    script = (
        "import sys, json\n"
        "before = set(sys.modules)\n"
        "from product_intelligence.research.specifications import (\n"
        "    SpecificationDefinition,\n"
        "    SpecificationValue,\n"
        "    SpecificationObservation,\n"
        "    NormalizedSpecificationObservation,\n"
        "    SpecificationResolution,\n"
        "    CategorySchema,\n"
        "    ProductSpecificationSet,\n"
        "    resolve_specification,\n"
        "    SpecificationValueKind,\n"
        "    SourceAuthority,\n"
        "    ResolutionState,\n"
        ")\n"
        "loaded = {name.split('.')[0] for name in set(sys.modules) - before}\n"
        "third_party = sorted(\n"
        "    name for name in loaded\n"
        "    if not name.startswith('_')\n"
        "    and name != 'product_intelligence'\n"
        "    and name not in sys.stdlib_module_names\n"
        ")\n"
        "print(json.dumps(third_party))\n"
    )
    env = dict(os.environ, PYTHONPATH=str(REPO_ROOT))
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(result.stdout.strip().splitlines()[-1]) == []
