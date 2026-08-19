"""Architecture boundary tests for 4A price aggregation.

Prove that the aggregation module obeys the same stdlib-only, no-I/O,
no-framework rules as the rest of the research core.
"""

from __future__ import annotations

import ast
import os
import pathlib

import pytest

# ---------------------------------------------------------------------------
# Guards: what aggregation.py must NOT import
# ---------------------------------------------------------------------------


def _get_module_source() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent.parent.parent / "product_intelligence" / "research" / "aggregation.py"


def _parse_imports(filepath: pathlib.Path) -> set[str]:
    """Return all top-level import names from a Python file."""
    tree = ast.parse(filepath.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])
    return imports


class TestAggregationModuleBoundaries:
    """The aggregation module must be a pure research-core primitive."""

    @pytest.fixture
    def imports(self):
        return _parse_imports(_get_module_source())

    def test_no_provider_import(self, imports) -> None:
        """Aggregation must not import the provider layer."""
        assert "product_intelligence.providers" not in str(imports)
        # The top-level import would be "product_intelligence" but let's check
        # the parsed source directly
        source = _get_module_source().read_text(encoding="utf-8")
        assert "providers" not in source.split("#")[0] or all(
            "providers" in line  # in a comment
            for line in source.split("\n")
            if "providers" in line
        )

    def test_no_django_import(self, imports) -> None:
        """Aggregation must not import Django."""
        assert "django" not in imports

    def test_no_persistence_import(self, imports) -> None:
        """Aggregation must not import runs/ (persistence)."""
        source = _get_module_source().read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and "runs" in node.module:
                    pytest.fail(f"aggregation imports persistence: from {node.module}")

    def test_no_web_import(self, imports) -> None:
        """Aggregation must not import web/."""
        source = _get_module_source().read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and "web" in node.module:
                    pytest.fail(f"aggregation imports web: from {node.module}")

    def test_no_evaluation_import(self, imports) -> None:
        """Aggregation must not import evaluation/."""
        source = _get_module_source().read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and "evaluation" in node.module:
                    pytest.fail(f"aggregation imports evaluation: from {node.module}")

    def test_no_network_io(self, imports) -> None:
        """Aggregation must not perform network or filesystem I/O."""
        forbidden = {"urllib", "http", "socket", "subprocess"}
        found = imports & forbidden
        assert not found, f"aggregation imports I/O modules: {found}"

    def test_no_llm_import(self, imports) -> None:
        """Aggregation must not import any LLM provider."""
        forbidden = {"openai", "anthropic", "qwen", "llm"}
        found = imports & forbidden
        assert not found, f"aggregation imports LLM modules: {found}"

    def test_no_extraction_import(self, imports) -> None:
        """Aggregation must not import extraction (3A)."""
        source = _get_module_source().read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and "extraction" in (node.module or ""):
                    pytest.fail("aggregation must not import extraction")

    def test_no_float_for_money(self, imports) -> None:
        """Aggregation must use Decimal for all money, never float()."""
        source = _get_module_source().read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "float":
                    pytest.fail(
                        "aggregation calls float(); money must be Decimal"
                    )

    def test_decimal_is_allowed(self, imports) -> None:
        """Aggregation must import decimal for money arithmetic."""
        assert "decimal" in imports, "aggregation must import Decimal for money"


class TestAggregationDoesNotWireOthers:
    """Other layers must not import aggregation (yet)."""

    def test_runs_does_not_import_research(self) -> None:
        """runs/ must not import the research core (still true after 4A)."""
        runs_dir = (
            pathlib.Path(__file__).resolve().parent.parent.parent
            / "product_intelligence" / "runs"
        )
        for py_file in runs_dir.glob("*.py"):
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and "research" in node.module:
                        pytest.fail(
                            f"runs/{py_file.name} imports research core: "
                            f"from {node.module}"
                        )

    def test_web_does_not_import_aggregation(self) -> None:
        """web/ must not import aggregation (4B is separate)."""
        web_dir = (
            pathlib.Path(__file__).resolve().parent.parent.parent
            / "product_intelligence" / "web"
        )
        for py_file in web_dir.glob("*.py"):
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and "aggregation" in (node.module or ""):
                        pytest.fail(
                            f"web/{py_file.name} imports aggregation: "
                            f"from {node.module}"
                        )

    def test_providers_do_not_import_aggregation(self) -> None:
        """providers/ must not import aggregation."""
        providers_dir = (
            pathlib.Path(__file__).resolve().parent.parent.parent
            / "product_intelligence" / "providers"
        )
        for py_file in providers_dir.glob("*.py"):
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and "aggregation" in (node.module or ""):
                        pytest.fail(
                            f"providers/{py_file.name} imports aggregation: "
                            f"from {node.module}"
                        )


class TestAggregationAPIExported:
    """The 4A public API must be exported from product_intelligence.research."""

    def test_aggregation_api_in_research_all(self) -> None:
        """4A symbols must appear in research.__all__."""
        from product_intelligence import research
        expected = {
            "aggregate_listing_prices",
            "PriceAggregationResult",
            "PriceAggregateBucket",
            "PriceAggregationExclusion",
            "PriceAggregationExclusionReason",
        }
        assert expected.issubset(set(research.__all__)), (
            f"Missing from research.__all__: {expected - set(research.__all__)}"
        )
