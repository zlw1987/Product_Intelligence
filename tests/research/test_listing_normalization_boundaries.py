"""Architecture guards specific to normalization (PRODUCT-INTEL.3B).

Most of what 3B must prove is already covered, by construction, by the
parametrized scans in `test_research_identity_boundaries.py`: they enumerate
every file under `product_intelligence/research/` at collection time, so
`normalization.py` is automatically checked for stdlib-only imports, no
persistence/provider/benchmark/web import, and no network or filesystem
access — the same guards 2A and 3A already had to pass. This file adds only
what is specific to 3B: that `decimal` is legitimately used *here* (a
narrowing the identity and extraction guards do not relax), that extraction
still forbids it, and that the new API is actually exported and wired to
nothing new.
"""

from __future__ import annotations

import ast
from pathlib import Path

from tests.domain.test_domain_boundaries import _python_files, _top_level_imports

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "product_intelligence"
RESEARCH_ROOT = PACKAGE_ROOT / "research"
NORMALIZATION_MODULE = RESEARCH_ROOT / "normalization.py"
EXTRACTION_MODULE = RESEARCH_ROOT / "extraction.py"


def test_the_normalization_module_exists() -> None:
    assert NORMALIZATION_MODULE.exists()
    assert NORMALIZATION_MODULE.read_text(encoding="utf-8").strip()


def test_normalization_is_the_only_module_permitted_to_use_decimal() -> None:
    """`decimal` becomes legitimate at 3B, and only at this one module.

    `extraction.py` (3A) and `identity.py` (2A) already forbid it explicitly;
    this asserts the positive claim so the guard cannot pass vacuously — if
    nothing in the research core imported `decimal`, the exclusions on the
    other two modules would be proving nothing.
    """
    modules = _top_level_imports(NORMALIZATION_MODULE.read_text(encoding="utf-8"))
    assert "decimal" in modules

    for path in _python_files(RESEARCH_ROOT):
        if path in (NORMALIZATION_MODULE,):
            continue
        other_modules = _top_level_imports(path.read_text(encoding="utf-8"))
        assert "decimal" not in other_modules, (
            f"{path.name} imports decimal; only normalization.py may convert "
            "a price to a number"
        )


def test_extraction_still_computes_no_numbers() -> None:
    """3B must not have relaxed 3A's boundary to make its own job easier."""
    modules = _top_level_imports(EXTRACTION_MODULE.read_text(encoding="utf-8"))

    assert not modules & {"decimal", "fractions", "statistics", "numbers", "math"}


def test_normalization_performs_no_network_or_filesystem_access() -> None:
    """Restated narrowly here even though the parametrized 3A/2A guard already
    covers every file under `research/`, because this is the one module a
    reviewer would most expect to reach for `requests` "just this once"."""
    modules = _top_level_imports(
        NORMALIZATION_MODULE.read_text(encoding="utf-8")
    ) | {
        module
        for node in ast.walk(ast.parse(NORMALIZATION_MODULE.read_text(encoding="utf-8")))
        if isinstance(node, ast.ImportFrom) and node.module and not node.level
        for module in [node.module]
    }
    forbidden = {
        "requests",
        "httpx",
        "urllib.request",
        "urllib3",
        "socket",
        "ssl",
        "http",
        "pathlib",
        "sqlite3",
        "os",
        "subprocess",
        "webbrowser",
    }
    offending = {m for m in modules for f in forbidden if m == f or m.startswith(f"{f}.")}

    assert not offending, f"normalization.py imports {sorted(offending)}"


def test_normalization_imports_no_django_provider_or_benchmark() -> None:
    tree = ast.parse(NORMALIZATION_MODULE.read_text(encoding="utf-8"))
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
            module
            for module in imported
            if module == forbidden or module.startswith(f"{forbidden}.")
        }
        assert not offending, f"normalization.py imports {sorted(offending)}"


def test_normalization_imports_the_3a_contract_and_nothing_more_of_research() -> None:
    """Normalization depends on `listings.ListingObservation`; it does not
    depend on `extraction` (it consumes an already-extracted observation) or
    on `identity` (§24 — commercial normalization never touches identity)."""
    tree = ast.parse(NORMALIZATION_MODULE.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and not node.level:
            imported.add(node.module)

    research_imports = {m for m in imported if m.startswith("product_intelligence.research")}
    assert research_imports == {"product_intelligence.research.listings"}


def test_the_research_core_exports_the_phase_3b_api() -> None:
    import product_intelligence.research as research

    assert {
        "NormalizationIssue",
        "NormalizationIssueCode",
        "NormalizedAvailability",
        "NormalizedCondition",
        "NormalizedListingObservation",
        "normalize_listing_observation",
        "normalize_listing_observations",
    } <= set(research.__all__)


def test_importing_the_research_core_still_pulls_in_no_third_party_dependency() -> None:
    """The 2A/3A structural guard already proves this for the whole package;
    restated as a direct check that `normalization` alone is clean, in a clean
    subprocess so it cannot disturb classes (like the two vocabularies above)
    that other already-running test modules hold references to. Reloading the
    module in-process was tried and rejected for exactly that reason: it
    mints new `Enum` classes, and `is`-identity checks elsewhere in the suite
    against the original classes then fail for a reason that has nothing to
    do with normalization itself.
    """
    import json
    import os
    import subprocess
    import sys

    script = (
        "import sys, json\n"
        "before = set(sys.modules)\n"
        "import product_intelligence.research.normalization\n"
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
