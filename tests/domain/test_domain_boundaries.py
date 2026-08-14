"""Architecture guard tests.

These enforce the invariants that the rest of the design rests on:

* the domain layer is caller-independent (no calling-system concepts leak in)
* the domain layer is vendor-independent (no search/LLM vendor leaks in)
* the domain layer needs no web framework, no network, and no LLM to import

They are deliberately mechanical. A future phase that violates a boundary
should fail a test, not merely contradict a document.
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "product_intelligence"
DOMAIN_ROOT = PACKAGE_ROOT / "domain"
RESEARCH_ROOT = PACKAGE_ROOT / "research"

# Concepts belonging to a specific calling system. The research core must work
# identically no matter which client produced the request, so these must never
# appear in the domain or the research core. The intake layer is where callers
# are allowed to exist.
CALLER_TOKENS = ["foxpro", "fox pro", "vfp", "sap", "erp"]

# Specific external vendors. Business logic depends on a provider boundary,
# never on a named vendor.
VENDOR_TOKENS = [
    "tavily",
    "serpapi",
    "google",
    "bing",
    "openai",
    "anthropic",
    "claude",
    "gemini",
    "langchain",
]


def _python_files(root: Path) -> list[Path]:
    return sorted(root.rglob("*.py"))


def _top_level_imports(source: str) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # relative import, stays inside the package
                continue
            if node.module:
                modules.add(node.module.split(".")[0])
    return modules


def _find_tokens(text: str, tokens: list[str]) -> list[str]:
    lowered = text.lower()
    return [
        token
        for token in tokens
        if re.search(rf"\b{re.escape(token)}\b", lowered)
    ]


def test_domain_package_has_source_files_to_check() -> None:
    """Guard against the scans below silently passing on an empty set."""
    assert _python_files(DOMAIN_ROOT)


@pytest.mark.parametrize("path", _python_files(DOMAIN_ROOT), ids=lambda p: p.name)
def test_domain_imports_only_stdlib_and_itself(path: Path) -> None:
    modules = _top_level_imports(path.read_text(encoding="utf-8"))
    disallowed = {
        module
        for module in modules
        if module != "product_intelligence" and module not in sys.stdlib_module_names
    }

    assert not disallowed, (
        f"{path.name} imports non-stdlib modules {sorted(disallowed)}; the "
        "domain layer must stay framework-light."
    )


@pytest.mark.parametrize(
    "path",
    _python_files(DOMAIN_ROOT) + _python_files(RESEARCH_ROOT),
    ids=lambda p: f"{p.parent.name}/{p.name}",
)
def test_core_contains_no_calling_system_concepts(path: Path) -> None:
    found = _find_tokens(path.read_text(encoding="utf-8"), CALLER_TOKENS)

    assert not found, (
        f"{path} references calling-system concepts {found}; callers belong "
        "to the intake boundary, not the core."
    )


@pytest.mark.parametrize("path", _python_files(DOMAIN_ROOT), ids=lambda p: p.name)
def test_domain_contains_no_external_vendor_names(path: Path) -> None:
    found = _find_tokens(path.read_text(encoding="utf-8"), VENDOR_TOKENS)

    assert not found, (
        f"{path.name} references external vendors {found}; vendors live "
        "behind a provider boundary."
    )


def test_domain_imports_without_django_network_or_llm_dependencies() -> None:
    """Import the domain in a clean interpreter and inspect what it loaded.

    Anything third-party pulled in here would mean the domain cannot be used
    (or tested) without that dependency present.
    """
    script = (
        "import sys, json\n"
        "before = set(sys.modules)\n"
        "import product_intelligence.domain\n"
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


def test_domain_exports_the_phase_0a_contracts() -> None:
    import product_intelligence.domain as domain

    assert {
        "ResearchRequest",
        "ProductIdentity",
        "EvidenceReference",
    } <= set(domain.__all__)
