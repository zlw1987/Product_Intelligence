"""Architecture guards for the provider boundary (PRODUCT-INTEL.2B, extended 2C).

The provider layer is where vendors are allowed to exist — and that is exactly
why the *generic* boundary has to stay clean. Two directions are checked.

**What the generic boundary may contain.** `providers/__init__.py` and
`providers/search.py` are contracts and a `Protocol`: standard library only, no
vendor name, no credential, no environment reading, no HTTP client, no Django,
and no model. A vendor package imported here would not be an adapter detail; it
would be the vendor becoming part of the interface every other layer depends on.
This remains true after 2C: `providers/serper.py` is a *third* file in the
package, and the scans below stay scoped to the original two, deliberately —
a vendor name inside an adapter is correct, that is what an adapter is for. A
guard that forbade vendor names package-wide would fail 2C for doing the right
thing, and would then be relaxed under pressure, which is worse than scoping it
from the start.

**Who may depend on the boundary.** 2B defined a shape and integrated no
provider; 2C added the first real adapter (Serper, ordinary Google Search) but
still wires it to nothing — the domain, the research core, the run lifecycle,
the web shell, and the evaluation layer remain unchanged and import no part of
`providers`. The provider layer likewise imports none of them — a provider that
reached into the run lifecycle or the identity comparator would be deciding
research outcomes from inside a transport adapter.
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
    CALLER_TOKENS,
    VENDOR_TOKENS,
    _find_tokens,
    _python_files,
    _top_level_imports,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "product_intelligence"
PROVIDERS_ROOT = PACKAGE_ROOT / "providers"

# The vendor-neutral half of the provider package: the contracts every other
# layer is allowed to depend on. An adapter added in 2C is deliberately not in
# this list.
GENERIC_BOUNDARY_MODULES = [
    PROVIDERS_ROOT / "__init__.py",
    PROVIDERS_ROOT / "search.py",
]

# Modules that perform or configure I/O. `urllib.parse` is deliberately absent:
# splitting a URL string is not fetching one, and the boundary validates result
# URLs without ever opening one.
NETWORK_MODULES = [
    "urllib.request",
    "urllib.error",
    "http.client",
    "socket",
    "ssl",
    "asyncio",
    "requests",
    "httpx",
    "urllib3",
    "aiohttp",
]

# Reading configuration or secrets is an adapter concern, and a server-side one.
# The generic contracts must not acquire it: a boundary that reads an API key is
# no longer a boundary.
CONFIGURATION_MODULES = ["os", "dotenv", "configparser", "django.conf"]

# The layers that must stay unaware of the provider boundary in this phase.
INNER_ROOTS = [
    PACKAGE_ROOT / "domain",
    PACKAGE_ROOT / "research",
    PACKAGE_ROOT / "runs",
    PACKAGE_ROOT / "web",
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


def _imports_any(imported: set[str], forbidden: list[str]) -> set[str]:
    return {
        module
        for module in imported
        for name in forbidden
        if module == name or module.startswith(f"{name}.")
    }


def test_the_generic_boundary_modules_exist() -> None:
    """Guard against every scan below silently passing on an empty set."""
    for path in GENERIC_BOUNDARY_MODULES:
        assert path.exists(), path
        assert path.read_text(encoding="utf-8").strip()


@pytest.mark.parametrize("path", GENERIC_BOUNDARY_MODULES, ids=lambda p: p.name)
def test_the_generic_boundary_imports_only_stdlib_and_itself(path: Path) -> None:
    """No vendor SDK, no HTTP library, no framework — including transitively."""
    modules = _top_level_imports(path.read_text(encoding="utf-8"))
    disallowed = {
        module
        for module in modules
        if module != "product_intelligence" and module not in sys.stdlib_module_names
    }

    assert not disallowed, (
        f"{path.name} imports non-stdlib modules {sorted(disallowed)}; the "
        "generic provider boundary depends on no vendor and no framework."
    )


@pytest.mark.parametrize("path", GENERIC_BOUNDARY_MODULES, ids=lambda p: p.name)
def test_the_generic_boundary_names_no_external_vendor(path: Path) -> None:
    found = _find_tokens(path.read_text(encoding="utf-8"), VENDOR_TOKENS)

    assert not found, (
        f"{path.name} references external vendors {found}; the contracts stay "
        "provider-neutral even though the first vendor was selected in 2C — "
        "that vendor's name belongs only in its adapter module."
    )


@pytest.mark.parametrize("path", GENERIC_BOUNDARY_MODULES, ids=lambda p: p.name)
def test_the_generic_boundary_names_no_calling_system(path: Path) -> None:
    """A search boundary is caller-independent for the same reason the core is."""
    found = _find_tokens(path.read_text(encoding="utf-8"), CALLER_TOKENS)

    assert not found, f"{path.name} references calling-system concepts {found}"


@pytest.mark.parametrize("path", GENERIC_BOUNDARY_MODULES, ids=lambda p: p.name)
def test_the_generic_boundary_opens_no_connection(path: Path) -> None:
    """The generic boundary defines a shape; it never performs a request.

    2C's adapter makes the first real call — from `providers/serper.py`, a
    module outside this scan. These two modules stay exactly as network-free
    as 2B left them.
    """
    offending = _imports_any(_imported_modules(path), NETWORK_MODULES)

    assert not offending, (
        f"{path.name} imports {sorted(offending)}; the generic boundary opens "
        "no connection itself, even after 2C added a real adapter elsewhere."
    )


@pytest.mark.parametrize("path", GENERIC_BOUNDARY_MODULES, ids=lambda p: p.name)
def test_the_generic_boundary_reads_no_configuration_or_credentials(
    path: Path,
) -> None:
    """No API key, no environment variable, no settings module.

    Checked structurally rather than by scanning for words like "secret": the
    docstrings in this package *state* the credential rules, so a lexical scan
    would flag the documentation that forbids the thing it is looking for.
    """
    offending = _imports_any(_imported_modules(path), CONFIGURATION_MODULES)

    assert not offending, f"{path.name} imports {sorted(offending)}"


@pytest.mark.parametrize("path", _python_files(PROVIDERS_ROOT), ids=lambda p: p.name)
def test_the_provider_layer_imports_no_persistence_core_or_web(path: Path) -> None:
    """A provider observes. It does not run, store, judge, or display anything.

    `research` is on this list for a specific reason: a provider that called the
    part-number comparison could return "verified" results, which would make a
    vendor the authority on product identity (§9, AD-036). The core compares;
    the provider reports what it saw.
    """
    imported = _imported_modules(path)
    offending = _imports_any(
        imported,
        [
            "django",
            "product_intelligence.runs",
            "product_intelligence.research",
            "product_intelligence.web",
            "product_intelligence.evaluation",
        ],
    )

    assert not offending, f"{path.name} imports {sorted(offending)}"


@pytest.mark.parametrize(
    "path",
    [path for root in INNER_ROOTS for path in _python_files(root)],
    ids=lambda p: f"{p.parent.name}/{p.name}",
)
def test_nothing_is_wired_to_the_search_boundary_yet(path: Path) -> None:
    """2C added a real adapter, but nothing outside `providers/` depends on it.

    The web shell in particular must remain unchanged: a run submitted through
    the browser is still `CREATED`. An adapter existing is not the same as an
    adapter being called from research execution, and this guard is what keeps
    that true — deliberately, not by oversight.
    """
    offending = {
        module
        for module in _imported_modules(path)
        if module.startswith("product_intelligence.providers")
    }

    assert not offending, (
        f"{path} imports the provider boundary {sorted(offending)}; the "
        "adapter added in 2C is intentionally not wired into the research "
        "core, the run lifecycle, or the web shell."
    )


def test_the_provider_layer_adds_no_model_and_no_migration() -> None:
    """Search results are not persisted in this phase — or by this layer, ever."""
    from django.apps import apps

    assert not list(PROVIDERS_ROOT.rglob("models.py"))
    assert not list(PROVIDERS_ROOT.rglob("migrations"))
    assert {model._meta.label for model in apps.get_models()} == {"runs.ResearchRun"}


def test_importing_the_provider_boundary_pulls_in_no_third_party_dependency() -> None:
    """The structural half: import it in a clean interpreter and look.

    A vendor SDK or a Django import appearing here would mean the boundary
    cannot be used, or tested, without that dependency installed — and would be
    the clearest possible sign that a vendor had entered the interface.
    """
    script = (
        "import sys, json\n"
        "before = set(sys.modules)\n"
        "import product_intelligence.providers\n"
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


def test_only_the_expected_adapter_modules_exist() -> None:
    """2B was the boundary with no adapter. 2C adds exactly one: Serper.

    The generic boundary (`__init__.py`, `search.py`) stays as 2B left it;
    `serper.py` is the one vendor-specific module 2C is permitted to add.
    Recorded fixtures live under `tests/fixtures/providers/serper/`, not here
    — the provider package itself stores no test data.
    """
    assert sorted(path.name for path in _python_files(PROVIDERS_ROOT)) == [
        "__init__.py",
        "search.py",
        "serper.py",
    ]
    assert not list(PROVIDERS_ROOT.rglob("fixtures"))


def test_the_provider_package_exports_the_phase_2b_boundary() -> None:
    import product_intelligence.providers as providers

    assert {
        "SearchProvider",
        "SearchProviderError",
        "SearchQuery",
        "SearchResponse",
        "SearchResult",
    } <= set(providers.__all__)
