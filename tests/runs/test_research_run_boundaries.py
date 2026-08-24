"""Architecture guards for the persistence layer.

Two boundaries have to hold once a database exists:

* **a run records the canonical request and nothing about who asked.** The
  research core is caller-independent by design, and a persisted record is
  exactly where that would quietly stop being true — one "just for audit"
  column at a time;
* **persistence stays out of the domain and out of the research core.** The
  domain must remain importable without a framework, and the engine must remain
  reasonable about without a database.

Like the other guards in this suite, these are mechanical: a later phase that
breaks a boundary should fail a test rather than merely contradict a document.
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
RUNS_ROOT = PACKAGE_ROOT / "runs"
RESEARCH_ROOT = PACKAGE_ROOT / "research"

# The complete set of concrete fields on a research run. Written out here so
# that adding a column is a decision someone has to make twice: once in the
# model, once against this list, with the review that implies.
EXPECTED_FIELDS = {
    "id",
    "manufacturer_part_number",
    "description",
    "state",
    "created_at",
    "started_at",
    "finished_at",
    "price_intelligence_snapshot",  # 4B: reverse OneToOne from snapshot
    "execution_evidence",  # 4C-A: reverse FK to execution evidence records
}

# The exact fields on PriceIntelligenceSnapshot (4B).
EXPECTED_SNAPSHOT_FIELDS = {
    "run",
    "schema_version",
    "payload",
    "created_at",
}


def test_runs_package_has_source_files_to_check() -> None:
    assert _python_files(RUNS_ROOT)


def test_a_research_run_has_exactly_the_approved_fields() -> None:
    from product_intelligence.runs.models import ResearchRun

    assert {field.name for field in ResearchRun._meta.get_fields()} == EXPECTED_FIELDS


def test_a_price_snapshot_has_exactly_the_approved_fields() -> None:
    from product_intelligence.runs.models import PriceIntelligenceSnapshot

    assert (
        {field.name for field in PriceIntelligenceSnapshot._meta.get_fields()}
        == EXPECTED_SNAPSHOT_FIELDS
    )


def test_a_price_snapshot_carries_no_caller_or_provider_data() -> None:
    from product_intelligence.runs.models import PriceIntelligenceSnapshot

    field_names = {field.name for field in PriceIntelligenceSnapshot._meta.get_fields()}
    forbidden = {
        "caller",
        "client",
        "source_system",
        "search_provider",
        "llm_provider",
        "provider",
        "model_name",
        "order_number",
        "customer",
        "user",
    }

    assert not field_names & forbidden


def test_a_price_snapshot_carries_no_raw_business_columns() -> None:
    """The snapshot is a versioned JSON box, not a denormalised fact table."""
    from product_intelligence.runs.models import PriceIntelligenceSnapshot

    field_names = {field.name for field in PriceIntelligenceSnapshot._meta.get_fields()}
    forbidden = {
        "seller",
        "seller_name",
        "price",
        "price_amount",
        "currency",
        "currency_code",
        "status",
        "decision",
        "manufacturer_part_number",
        "description",
        "report_html",
        "error",
        "error_message",
    }

    assert not field_names & forbidden


def test_a_research_run_carries_no_caller_or_provider_data() -> None:
    """The names a caller-shaped column would plausibly arrive under."""
    from product_intelligence.runs.models import ResearchRun

    field_names = {field.name for field in ResearchRun._meta.get_fields()}
    forbidden = {
        "caller",
        "client",
        "source_system",
        "calling_system",
        "order_number",
        "order_line",
        "customer",
        "customer_number",
        "user",
        "username",
        "requested_by",
        "session",
        "referer",
        "user_agent",
        "ip_address",
        "search_provider",
        "llm_provider",
        "provider",
        "model_name",
    }

    assert not field_names & forbidden


@pytest.mark.parametrize("path", _python_files(RUNS_ROOT), ids=lambda p: p.name)
def test_the_persistence_layer_names_no_calling_system(path: Path) -> None:
    found = _find_tokens(path.read_text(encoding="utf-8"), CALLER_TOKENS)

    assert not found, (
        f"{path.name} references calling-system concepts {found}; a persisted "
        "run records the canonical request, not who sent it."
    )


@pytest.mark.parametrize("path", _python_files(RUNS_ROOT), ids=lambda p: p.name)
def test_the_persistence_layer_names_no_external_vendor(path: Path) -> None:
    found = _find_tokens(path.read_text(encoding="utf-8"), VENDOR_TOKENS)

    assert not found, f"{path.name} references external vendors {found}"


@pytest.mark.parametrize(
    "path",
    _python_files(PACKAGE_ROOT / "domain") + _python_files(RESEARCH_ROOT),
    ids=lambda p: f"{p.parent.name}/{p.name}",
)
def test_the_domain_and_research_core_stay_free_of_persistence(path: Path) -> None:
    modules = _top_level_imports(path.read_text(encoding="utf-8"))

    assert "django" not in modules, (
        f"{path} imports Django; persistence belongs to product_intelligence.runs, "
        "not to the domain or the research core."
    )


def test_the_research_core_defines_no_models() -> None:
    assert not list(RESEARCH_ROOT.rglob("models.py"))
    assert not list(RESEARCH_ROOT.rglob("migrations"))


def test_the_domain_does_not_import_the_persistence_layer() -> None:
    """The dependency runs one way: runs imports domain, never the reverse."""
    for path in _python_files(PACKAGE_ROOT / "domain"):
        source = path.read_text(encoding="utf-8")
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("product_intelligence.runs"), path
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("product_intelligence.runs"), path


def test_the_evaluation_corpus_is_not_persisted() -> None:
    """0B stays reference infrastructure; it is not runtime state.

    A run must not depend on the benchmark, and no benchmark case may become a
    database row — otherwise a migration or a research run could edit evaluation
    truth.
    """
    from django.apps import apps

    model_labels = {model._meta.label for model in apps.get_models()}
    expected = {
        "runs.ResearchRun",
        "runs.PriceIntelligenceSnapshot",
        "runs.ExecutionEvidenceRecord",  # 4C-A
    }
    assert model_labels == expected

    for path in _python_files(RUNS_ROOT):
        modules = _top_level_imports(path.read_text(encoding="utf-8"))
        assert "product_intelligence.evaluation" not in modules

    for path in _python_files(PACKAGE_ROOT / "evaluation"):
        source = path.read_text(encoding="utf-8")
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("product_intelligence.runs"), path


def test_the_domain_still_imports_without_django_present() -> None:
    """The 1A regression: adding a database must not make the domain need one.

    The domain guard covers imports declared in its own files. This covers the
    other direction — that nothing added in this phase caused the domain to pull
    a framework in transitively when imported on its own.
    """
    script = (
        "import sys, json\n"
        "before = set(sys.modules)\n"
        "import product_intelligence.domain\n"
        "print(json.dumps(sorted(\n"
        "    name for name in set(sys.modules) - before\n"
        "    if name.split('.')[0] in {'django', 'sqlite3'}\n"
        ")))\n"
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
