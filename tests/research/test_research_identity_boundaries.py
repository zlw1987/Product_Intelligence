"""Architecture guards for the research core (PRODUCT-INTEL.2A).

The research core is the layer most likely to acquire dependencies by
convenience: a database handle "just to look something up", a provider "just to
fetch a candidate", the evaluation corpus "just to check an answer". Each of
those would be a different failure — an engine that cannot be reasoned about
without a database, business logic bound to a vendor, or benchmark answers
leaking into runtime resolution, which is test leakage in its purest form.

Two directions are checked: what the research core may depend on, and who may
depend on it. 2A is a primitive with no candidate source, so nothing wires it
into a run or a page yet, and these guards assert that too.

Deliberately structural. Import inspection answers these questions, so there is
no need for a lexical scan beyond the vendor-name check the other guards already
share.
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
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
RESEARCH_ROOT = PACKAGE_ROOT / "research"
IDENTITY_MODULE = RESEARCH_ROOT / "identity.py"


def _imported_modules(path: Path) -> set[str]:
    """Every dotted module name imported by a file, absolute imports only."""
    modules: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            modules.add(node.module)
    return modules


def test_the_research_core_has_source_files_to_check() -> None:
    """Guard against the scans below silently passing on an empty set."""
    assert _python_files(RESEARCH_ROOT)
    assert IDENTITY_MODULE.exists()


@pytest.mark.parametrize("path", _python_files(RESEARCH_ROOT), ids=lambda p: p.name)
def test_the_research_core_imports_only_stdlib_and_the_domain(path: Path) -> None:
    """No framework, no vendor library, no HTTP client, no model client."""
    modules = _top_level_imports(path.read_text(encoding="utf-8"))
    disallowed = {
        module
        for module in modules
        if module != "product_intelligence" and module not in sys.stdlib_module_names
    }

    assert not disallowed, (
        f"{path.name} imports non-stdlib modules {sorted(disallowed)}; the "
        "research core stays free of frameworks and vendors."
    )


@pytest.mark.parametrize("path", _python_files(RESEARCH_ROOT), ids=lambda p: p.name)
def test_the_research_core_imports_no_persistence_provider_or_benchmark(
    path: Path,
) -> None:
    imported = _imported_modules(path)

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
        assert not offending, f"{path.name} imports {sorted(offending)}"


# Modules that reach outside the process: a network stack, a filesystem, a
# database, a subprocess, or the environment. None of them may appear anywhere
# in the research core, which is the durable rule — the core reads nothing,
# fetches nothing, and stores nothing.
#
# `json` and `html.parser` are deliberately **not** here, and that is a
# narrowing made in 3A rather than a relaxation. Both are pure computation over
# a string already held in memory: `json.loads` opens no file and `HTMLParser`
# opens no socket. 2A's version of this list named `json` because nothing in the
# core had a reason to parse anything, so the coarser list cost nothing; 3A's
# deterministic extractor reads JSON-LD blocks out of a document string, which
# is the whole of what it does. The rule the plan and CLAUDE.md actually state
# — "a network or filesystem module" — is what is enforced here. `urllib.parse`
# is absent for the same reason the provider boundary excludes it: splitting a
# URL string is not fetching one.
IO_MODULES = {
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


@pytest.mark.parametrize("path", _python_files(RESEARCH_ROOT), ids=lambda p: p.name)
def test_the_research_core_performs_no_network_or_file_access(path: Path) -> None:
    """The core computes over values it is handed, and reaches nothing."""
    imported = _imported_modules(path) | _top_level_imports(path.read_text(encoding="utf-8"))
    offending = {
        module
        for module in imported
        for forbidden in IO_MODULES
        if module == forbidden or module.startswith(f"{forbidden}.")
    }

    assert not offending, (
        f"{path.name} imports {sorted(offending)}; the research core "
        "reads nothing, fetches nothing, and stores nothing."
    )


def test_the_identity_primitive_still_parses_nothing() -> None:
    """2A's stricter promise, kept for 2A's module specifically.

    The part-number comparison is a pure function of two strings. It has no
    reason to parse a document, a payload, or a URL, and the narrowing above —
    made so 3A's extractor can read JSON-LD — must not quietly widen what
    `identity.py` is allowed to do.
    """
    modules = _top_level_imports(IDENTITY_MODULE.read_text(encoding="utf-8"))

    assert not modules & {"json", "html", "urllib", "xml", "csv", "pickle"}


def test_extraction_computes_no_numbers() -> None:
    """3A observes text. It converts nothing, and it may not acquire the means to.

    `Decimal` in the extractor would be a price becoming a number one layer
    early — before 3B has decided what an unparseable price means and before 3C
    has decided the listing is even about the right product. 3B will import it;
    this module may not.
    """
    extraction = RESEARCH_ROOT / "extraction.py"
    assert extraction.exists()

    modules = _top_level_imports(extraction.read_text(encoding="utf-8"))

    assert not modules & {"decimal", "fractions", "statistics", "numbers", "math"}


@pytest.mark.parametrize("path", _python_files(RESEARCH_ROOT), ids=lambda p: p.name)
def test_the_research_core_names_no_external_vendor(path: Path) -> None:
    found = _find_tokens(path.read_text(encoding="utf-8"), VENDOR_TOKENS)

    assert not found, f"{path.name} references external vendors {found}"


def test_the_research_core_depends_on_the_domain_contracts() -> None:
    """The permitted direction, so the guards above cannot pass vacuously."""
    imported = {
        module for path in _python_files(RESEARCH_ROOT) for module in _imported_modules(path)
    }

    assert any(module.startswith("product_intelligence.domain") for module in imported)


def test_the_domain_does_not_import_the_research_core() -> None:
    """The dependency runs one way: research imports domain, never the reverse."""
    for path in _python_files(PACKAGE_ROOT / "domain"):
        offending = {
            module
            for module in _imported_modules(path)
            if module.startswith("product_intelligence.research")
        }
        assert not offending, f"{path} imports {sorted(offending)}"


@pytest.mark.parametrize(
    "root",
    [PACKAGE_ROOT / "runs", PACKAGE_ROOT / "evaluation"],
    ids=lambda p: p.name,
)
def test_no_outer_layer_is_wired_to_the_identity_primitive_yet(root: Path) -> None:
    """2A supplies a comparison; nothing yet supplies a candidate to compare.

    Persistence and the benchmark are both unchanged by this phase.
    Runtime integration waits for the phase that has real candidate evidence.
    The web layer is excluded from this check because 1B and 4B import
    research contracts (and the codec) for the report view.
    """
    for path in _python_files(root):
        offending = {
            module
            for module in _imported_modules(path)
            if module.startswith("product_intelligence.research")
        }
        assert not offending, f"{path} imports {sorted(offending)}"


def test_the_identity_primitive_adds_no_model_and_no_migration() -> None:
    from django.apps import apps

    assert not list(RESEARCH_ROOT.rglob("models.py"))
    assert not list(RESEARCH_ROOT.rglob("migrations"))
    expected = {"runs.ResearchRun", "runs.PriceIntelligenceSnapshot", "runs.ExecutionEvidenceRecord", "runs.AiAssistedReviewCandidate"}
    assert {model._meta.label for model in apps.get_models()} == expected


def test_importing_the_research_core_pulls_in_no_third_party_dependency() -> None:
    """The structural half: import it in a clean interpreter and look.

    A transitive Django import would mean the engine could not be exercised
    without a database, which is the specific thing `research/` exists to avoid.
    """
    script = (
        "import sys, json\n"
        "before = set(sys.modules)\n"
        "import product_intelligence.research\n"
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


def test_the_research_core_exports_the_phase_2a_primitive() -> None:
    import product_intelligence.research as research

    assert {
        "PartNumberMatchAssessment",
        "compare_part_numbers",
        "compare_request_to_candidate",
        "normalize_part_number",
    } <= set(research.__all__)
