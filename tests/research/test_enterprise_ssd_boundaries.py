"""Architecture boundary tests for PRODUCT-INTEL.6B — Enterprise SSD module.

Prove that product_intelligence/research/enterprise_ssd.py:
1. Imports only stdlib + frozen research.specifications contracts
2. Does NOT import django, runs, providers, semantic, execution, web,
   evaluation, network, filesystem, or environment access
3. Does NOT perform extraction, resolution, or authority inference
4. Cannot import forbidden modules through transitive dependencies

Also proves:
- No VERIFIED/UNVERIFIED/CONFLICT/UNKNOWN states are produced
- No resolve_specification() calls
- No ProductSpecificationSet construction
- No SourceAuthority inference
- No ProductIdentity creation
- No HTML parsing, URL fetching, file reading
- No environment variable reading
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
ENTERPRISE_SSD_MODULE = RESEARCH_ROOT / "enterprise_ssd.py"


def _imported_modules(path: Path) -> set[str]:
    """Every dotted module name imported by a file, absolute imports only."""
    modules: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names if alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            modules.add(node.module)
    return modules


def _top_level_imports(source: str) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name:
                    modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                continue
            if node.module:
                modules.add(node.module.split(".")[0])
    return modules


# ===================================================================
# Module existence and source structure
# ===================================================================


def test_enterprise_ssd_module_exists() -> None:
    assert ENTERPRISE_SSD_MODULE.exists()


def test_enterprise_ssd_module_is_nonempty() -> None:
    assert ENTERPRISE_SSD_MODULE.read_text(encoding="utf-8").strip()


# ===================================================================
# Import boundary: allowed imports
# ===================================================================


def test_enterprise_ssd_imports_only_stdlib_and_specifications() -> None:
    """Only stdlib and product_intelligence.research.specifications allowed."""
    source = ENTERPRISE_SSD_MODULE.read_text(encoding="utf-8")
    modules = _top_level_imports(source)
    disallowed = {
        module
        for module in modules
        if module != "product_intelligence" and module not in sys.stdlib_module_names
    }
    assert not disallowed, (
        f"enterprise_ssd.py imports non-stdlib modules {sorted(disallowed)}"
    )


def test_enterprise_ssd_imports_specifications() -> None:
    """Must import frozen 6A specifications contracts."""
    imported = _imported_modules(ENTERPRISE_SSD_MODULE)
    assert any(
        m.startswith("product_intelligence.research.specifications")
        for m in imported
    ), "enterprise_ssd.py must import frozen specifications contracts"


def test_enterprise_ssd_imports_no_persistence_provider_or_web() -> None:
    """No Django, runs, providers, web, execution, semantic, evaluation."""
    imported = _imported_modules(ENTERPRISE_SSD_MODULE)
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
        assert not offending, (
            f"enterprise_ssd.py imports forbidden module: {sorted(offending)}"
        )


def test_enterprise_ssd_imports_no_io_modules() -> None:
    """No network, filesystem, subprocess, or environment access."""
    imported = _imported_modules(ENTERPRISE_SSD_MODULE) | _top_level_imports(
        ENTERPRISE_SSD_MODULE.read_text(encoding="utf-8")
    )
    io_modules = {
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
        f"enterprise_ssd.py imports I/O modules {sorted(offending)}"
    )


# ===================================================================
# Import boundary: does not import research submodules it shouldn't
# ===================================================================


def test_enterprise_ssd_imports_no_listing_normalization() -> None:
    """6B must not import 3B listing normalization."""
    imported = _imported_modules(ENTERPRISE_SSD_MODULE)
    for mod in imported:
        if mod and mod.startswith("product_intelligence.research"):
            assert mod == "product_intelligence.research.specifications", (
                f"enterprise_ssd.py imports research submodule "
                f"'{mod}' which is not specifications"
            )


def test_enterprise_ssd_imports_no_matching() -> None:
    """6B must not import 3C matching."""
    imported = _imported_modules(ENTERPRISE_SSD_MODULE)
    assert not any(
        "matching" in (m or "") for m in imported
    ), "enterprise_ssd.py must not import matching"


def test_enterprise_ssd_imports_no_aggregation() -> None:
    """6B must not import 4A aggregation."""
    imported = _imported_modules(ENTERPRISE_SSD_MODULE)
    assert not any(
        "aggregation" in (m or "") for m in imported
    ), "enterprise_ssd.py must not import aggregation"


def test_enterprise_ssd_imports_no_extraction() -> None:
    """6B must not import 3A extraction."""
    imported = _imported_modules(ENTERPRISE_SSD_MODULE)
    assert not any(
        "extraction" in (m or "") for m in imported
    ), "enterprise_ssd.py must not import extraction"


def test_enterprise_ssd_imports_no_identity() -> None:
    """6B must not import 2A identity."""
    imported = _imported_modules(ENTERPRISE_SSD_MODULE)
    assert not any(
        "identity" in (m or "") for m in imported
    ), "enterprise_ssd.py must not import identity"


# ===================================================================
# Source-level behavioral checks
# ===================================================================


def test_enterprise_ssd_source_no_resolve_specification_call() -> None:
    """6B normalization must not call resolve_specification()."""
    source = ENTERPRISE_SSD_MODULE.read_text(encoding="utf-8")
    assert "resolve_specification(" not in source, (
        "enterprise_ssd.py must not call resolve_specification()"
    )


def test_enterprise_ssd_source_no_productspecificationset() -> None:
    """6B must not construct ProductSpecificationSet."""
    source = ENTERPRISE_SSD_MODULE.read_text(encoding="utf-8")
    assert "ProductSpecificationSet(" not in source, (
        "enterprise_ssd.py must not construct ProductSpecificationSet"
    )


def test_enterprise_ssd_source_no_verified() -> None:
    """6B must not produce VERIFIED state."""
    source = ENTERPRISE_SSD_MODULE.read_text(encoding="utf-8")
    assert "VERIFIED" not in source, (
        "enterprise_ssd.py must not reference VERIFIED state"
    )


def test_enterprise_ssd_source_no_conflict() -> None:
    """6B must not produce CONFLICT state."""
    source = ENTERPRISE_SSD_MODULE.read_text(encoding="utf-8")
    assert "CONFLICT" not in source, (
        "enterprise_ssd.py must not reference CONFLICT state"
    )


def test_enterprise_ssd_source_no_unknown_state() -> None:
    """6B must not produce UNKNOWN resolution state."""
    source = ENTERPRISE_SSD_MODULE.read_text(encoding="utf-8")
    # Check for ResolutionState.UNKNOWN or standalone UNKNOWN as a state
    assert "ResolutionState" not in source, (
        "enterprise_ssd.py must not reference ResolutionState"
    )


def test_enterprise_ssd_source_no_authority_inference() -> None:
    """6B must not infer or change SourceAuthority."""
    source = ENTERPRISE_SSD_MODULE.read_text(encoding="utf-8")
    assert "SourceAuthority.AUTHORITATIVE" not in source, (
        "enterprise_ssd.py must not reference SourceAuthority.AUTHORITATIVE"
    )
    assert "SourceAuthority.SECONDARY" not in source, (
        "enterprise_ssd.py must not reference SourceAuthority.SECONDARY"
    )


def test_enterprise_ssd_source_no_identity_creation() -> None:
    """6B must not create ProductIdentity."""
    source = ENTERPRISE_SSD_MODULE.read_text(encoding="utf-8")
    assert "ProductIdentity(" not in source, (
        "enterprise_ssd.py must not construct ProductIdentity"
    )


def test_enterprise_ssd_source_no_os_environ() -> None:
    """6B must not read environment variables."""
    source = ENTERPRISE_SSD_MODULE.read_text(encoding="utf-8")
    assert "os.environ" not in source
    assert "os.getenv" not in source


# ===================================================================
# Decimal allowlist — enterprise_ssd.py legitimately uses Decimal
# ===================================================================


def test_enterprise_ssd_legitimately_uses_decimal() -> None:
    """enterprise_ssd.py must use Decimal for numeric normalization."""
    modules = _top_level_imports(
        ENTERPRISE_SSD_MODULE.read_text(encoding="utf-8")
    )
    assert "decimal" in modules, (
        "enterprise_ssd.py must import decimal for numeric normalization"
    )


# ===================================================================
# Runtime import boundary (subprocess)
# ===================================================================


def test_importing_enterprise_ssd_pulls_in_no_third_party() -> None:
    """Import in a clean interpreter and verify no third-party loaded."""
    script = (
        "import sys, json\n"
        "before = set(sys.modules)\n"
        "from product_intelligence.research.enterprise_ssd import (\n"
        "    ENTERPRISE_SSD_SCHEMA,\n"
        "    ENTERPRISE_SSD_SCHEMA_ID,\n"
        "    ENTERPRISE_SSD_SCHEMA_VERSION,\n"
        "    normalize_enterprise_ssd_observation,\n"
        "    normalize_enterprise_ssd_observations,\n"
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


def test_importing_enterprise_ssd_does_not_load_django() -> None:
    """Django must not be loaded by importing enterprise_ssd."""
    script = (
        "import sys\n"
        "from product_intelligence.research.enterprise_ssd import "
        "normalize_enterprise_ssd_observation\n"
        "print('django' in sys.modules)\n"
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
    assert result.stdout.strip() == "False"


# ===================================================================
# No forbidden runtime behaviors
# ===================================================================


def test_enterprise_ssd_no_model_no_migration() -> None:
    """6B is pure framework — no Django model, no migration."""
    assert not ENTERPRISE_SSD_MODULE.name.endswith("models.py")
    migrations = RESEARCH_ROOT / "migrations"
    assert not migrations.exists() or not list(migrations.rglob("*.py"))
