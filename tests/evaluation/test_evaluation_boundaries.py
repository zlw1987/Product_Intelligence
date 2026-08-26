"""Architecture guard tests for the evaluation layer.

Two properties have to hold for a benchmark to stay trustworthy:

* **it never reaches the network.** Provenance URLs are recorded so a person
  can re-check a claim, not so code can re-fetch one. A corpus that loaded over
  the network would be non-deterministic, would fail offline, and would let a
  changed page silently rewrite the expected answers;
* **it drags in nothing from the research stack.** Loading the corpus must not
  import a search provider, an LLM provider, Django, or the research core —
  otherwise "the benchmark loads" would stop being independent of the thing
  being measured.

Like the domain guards, these are mechanical. A later phase that breaks a
boundary should fail a test, not merely contradict a document.
"""

from __future__ import annotations

import ast
import json
import os
import re
import socket
import subprocess
import sys
from pathlib import Path

import pytest

# Reused rather than restated so the two guards cannot drift apart: if a vendor
# is added to the domain's list, the evaluation layer is scanned for it too.
from tests.domain.test_domain_boundaries import VENDOR_TOKENS

REPO_ROOT = Path(__file__).resolve().parents[2]
EVALUATION_PACKAGE_ROOT = REPO_ROOT / "product_intelligence" / "evaluation"
CORPUS_DIRECTORY = REPO_ROOT / "evaluation" / "corpus"

# Modules the evaluation layer must not need in order to load the corpus.
FORBIDDEN_MODULES = ("django", "product_intelligence.providers", "product_intelligence.research")


def _python_files(root: Path) -> list[Path]:
    return sorted(root.rglob("*.py"))


def _find_tokens(text: str, tokens: list[str]) -> list[str]:
    lowered = text.lower()
    return [token for token in tokens if re.search(rf"\b{re.escape(token)}\b", lowered)]


def test_evaluation_package_has_source_files_to_check() -> None:
    """Guard against the scans below silently passing on an empty set."""
    assert _python_files(EVALUATION_PACKAGE_ROOT)


@pytest.mark.parametrize(
    "path", _python_files(EVALUATION_PACKAGE_ROOT), ids=lambda p: p.name
)
def test_evaluation_code_names_no_search_or_llm_vendor(path: Path) -> None:
    # Only model_catalog and transport are allowed to contain explicit vendor/model
    # names as they are the catalog definition and transport layer respectively.
    # runner, cli, comparison, and __init__ must NOT hardcode model identities.
    if path.parent.name == "semantic" and path.stem in (
        "model_catalog",
        "transport",
    ):
        return

    found = _find_tokens(path.read_text(encoding="utf-8"), VENDOR_TOKENS)

    assert not found, (
        f"{path.name} references external vendors {found}; the corpus must not "
        "encode which provider a later phase will use."
    )


@pytest.mark.parametrize(
    "path", sorted(CORPUS_DIRECTORY.glob("*.json")), ids=lambda p: p.name
)
def test_corpus_data_names_no_search_or_llm_vendor(path: Path) -> None:
    """Product manufacturers are the corpus's subject; search/LLM vendors are not.

    An expectation mentioning a provider would be an implementation choice
    smuggled into evaluation truth.
    """
    found = _find_tokens(path.read_text(encoding="utf-8"), VENDOR_TOKENS)

    assert not found, f"{path.name} references external vendors {found}"


def test_loading_the_corpus_makes_no_network_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """Break the socket layer, then load. Any lookup or fetch fails loudly."""

    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("the evaluation corpus must not use the network")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)

    from product_intelligence.evaluation import load_corpus

    corpus = load_corpus()

    assert corpus.real_verified
    # The URLs are still present as data — recorded, never requested.
    assert all(case.provenance.source_url for case in corpus.real_verified)


def test_loading_the_corpus_imports_no_framework_or_provider() -> None:
    """Load the corpus in a clean interpreter and inspect what it pulled in."""
    script = (
        "import sys, json\n"
        "before = set(sys.modules)\n"
        "from product_intelligence.evaluation import load_corpus\n"
        "corpus = load_corpus()\n"
        "assert len(corpus) > 0\n"
        "loaded = set(sys.modules) - before\n"
        "third_party = sorted(\n"
        "    name for name in {n.split('.')[0] for n in loaded}\n"
        "    if not name.startswith('_')\n"
        "    and name != 'product_intelligence'\n"
        "    and name not in sys.stdlib_module_names\n"
        ")\n"
        "forbidden = sorted(n for n in loaded if n in "
        f"{FORBIDDEN_MODULES!r})\n"
        "print(json.dumps({'third_party': third_party, 'forbidden': forbidden}))\n"
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

    report = json.loads(result.stdout.strip().splitlines()[-1])

    assert report["third_party"] == []
    assert report["forbidden"] == []


def test_evaluation_data_lives_outside_the_python_package() -> None:
    """The corpus is reviewable reference data, not application state.

    Keeping the JSON out of the package is what makes it read as a document a
    person maintains, and keeps it from drifting toward runtime state.
    """
    assert CORPUS_DIRECTORY.is_dir()
    assert not list(EVALUATION_PACKAGE_ROOT.rglob("*.json"))


@pytest.mark.parametrize(
    "path", _python_files(EVALUATION_PACKAGE_ROOT), ids=lambda p: p.name
)
def test_evaluation_imports_only_stdlib_and_this_project(path: Path) -> None:
    """No Django, no ORM, no HTTP client, no vendor SDK.

    The structural half of the guard above: evaluation data is reference
    material a person maintains, never persisted runtime state, so nothing here
    should need a framework to load.
    """
    modules: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
            modules.add(node.module.split(".")[0])

    disallowed = {
        module
        for module in modules
        if module != "product_intelligence" and module not in sys.stdlib_module_names
    }

    assert not disallowed, f"{path.name} imports non-stdlib modules {sorted(disallowed)}"
