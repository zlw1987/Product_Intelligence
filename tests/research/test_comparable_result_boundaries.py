"""Architecture guard: new 7C-A research modules are pure.

The comparable_research_results.py and comparable_result_codec.py modules
must remain pure: no Django, no runs, no providers, no web, no execution.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "product_intelligence"
RESEARCH_ROOT = PACKAGE_ROOT / "research"

FORBIDDEN_IMPORTS = [
    "django",
    "product_intelligence.runs",
    "product_intelligence.providers",
    "product_intelligence.evaluation",
    "product_intelligence.web",
    "product_intelligence.execution",
]


def _top_level_imports(source: str) -> set[str]:
    import ast
    modules: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            modules.add(node.module.split(".")[0])
    return modules


def _imported_modules(source: str) -> set[str]:
    import ast
    modules: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            modules.add(node.module)
    return modules


@pytest.mark.parametrize(
    "module_name",
    ["comparable_research_results", "comparable_result_codec"],
)
def test_comparable_result_modules_import_only_stdlib_and_domain(
    module_name: str,
) -> None:
    path = RESEARCH_ROOT / f"{module_name}.py"
    assert path.exists(), f"{path} should exist"
    source = path.read_text(encoding="utf-8")
    imported = _imported_modules(source)
    for forbidden in FORBIDDEN_IMPORTS:
        offending = {
            m for m in imported
            if m == forbidden or m.startswith(f"{forbidden}.")
        }
        assert not offending, (
            f"{module_name}.py imports {sorted(offending)}; "
            "research-layer comparable result contracts must stay pure."
        )
