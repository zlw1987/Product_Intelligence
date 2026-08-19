"""Architecture guards specific to matching (PRODUCT-INTEL.3C).

The matching module is the first research-core primitive that imports
``product_intelligence.domain`` (for ``ResearchRequest``) in addition to other
research-core modules. These guards ensure that expansion is exactly that — one
domain contract plus intra-core imports — and nothing leaks back to persistence,
providers, web, or the evaluation benchmark.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "product_intelligence"
RESEARCH_ROOT = PACKAGE_ROOT / "research"
MATCHING_MODULE = RESEARCH_ROOT / "matching.py"


def test_the_matching_module_exists() -> None:
    assert MATCHING_MODULE.exists()
    assert MATCHING_MODULE.read_text(encoding="utf-8").strip()


def test_matching_imports_only_authorized_modules() -> None:
    """matching.py may import stdlib, product_intelligence.domain, and
    product_intelligence.research submodules only. Nothing else."""
    tree = ast.parse(MATCHING_MODULE.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            imported.add(node.module)

    disallowed = set()
    for mod in imported:
        top = mod.split(".")[0]
        if top == "product_intelligence":
            continue
        if top in sys.stdlib_module_names:
            continue
        if top.startswith("_"):
            continue
        disallowed.add(mod)

    assert not disallowed, (
        f"matching.py imports unauthorized modules {sorted(disallowed)}"
    )


def test_matching_imports_no_persistence_provider_web_or_benchmark() -> None:
    tree = ast.parse(MATCHING_MODULE.read_text(encoding="utf-8"))
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
    ):
        offending = {
            m for m in imported
            if m == forbidden or m.startswith(f"{forbidden}.")
        }
        assert not offending, f"matching.py imports {sorted(offending)}"


def test_matching_imports_no_network_or_subprocess() -> None:
    """3C performs no network access and spawns no subprocesses."""
    tree = ast.parse(MATCHING_MODULE.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            imported.add(node.module)

    forbidden = {
        "subprocess",
        "socket",
        "urllib",
        "httpx",
        "requests",
        "urllib3",
    }
    offending = {
        m for m in imported for f in forbidden
        if m == f or m.startswith(f"{f}.")
    }
    assert not offending, f"matching.py imports {sorted(offending)}"


def test_matching_computes_no_arithmetic() -> None:
    """Price aggregation is 4A; matching.py must not import arithmetic modules."""
    tree = ast.parse(MATCHING_MODULE.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            imported.add(node.module)

    forbidden = {"decimal", "statistics", "math", "fractions", "numbers"}
    offending = {m for m in imported if m in forbidden}
    assert not offending, f"matching.py imports arithmetic modules {sorted(offending)}"


def test_matching_uses_only_authorized_research_submodules() -> None:
    """matching.py imports identity (2A comparator), listings (3A contract),
    and normalization (3B contract). It must not import extraction (it consumes
    already-extracted observations) or the evaluation loader."""
    tree = ast.parse(MATCHING_MODULE.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and not node.level:
            imported.add(node.module)

    research_imports = {
        m for m in imported
        if m.startswith("product_intelligence.research.")
    }
    allowed = {
        "product_intelligence.research.identity",
        "product_intelligence.research.listings",
        "product_intelligence.research.normalization",
    }
    unexpected = research_imports - allowed
    assert not unexpected, (
        f"matching.py imports unexpected research submodules "
        f"{sorted(unexpected)}; allowed: {sorted(allowed)}"
    )


def test_the_research_core_exports_the_phase_3c_api() -> None:
    import product_intelligence.research as research

    assert {
        "EvidenceSource",
        "IdentityRejectionReason",
        "ListingIdentityAssessment",
        "assess_listing_identity",
        "assess_listing_identities",
    } <= set(research.__all__)
