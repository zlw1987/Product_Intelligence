"""Boundary tests for 6D modules (PRODUCT-INTEL.6D).

Proves:
- research datasheet module imports no providers/execution/network
- provider/document infrastructure imports no Enterprise SSD business rules
- execution enrichment imports only allowed modules
"""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "product_intelligence"


def _top_level_imports(source: str) -> set[str]:
    """Extract top-level import module names from source code."""
    import ast
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            imported.add(node.module)
    return imported


class TestResearchDatasheetBoundaries:
    """research/enterprise_ssd_datasheet.py must import no provider/execution modules."""

    def test_source_contains_no_provider_imports(self) -> None:
        source = (PACKAGE_ROOT / "research" / "enterprise_ssd_datasheet.py").read_text()
        imports = _top_level_imports(source)
        for imp in imports:
            if imp.startswith("product_intelligence.providers"):
                raise AssertionError(
                    f"research/enterprise_ssd_datasheet source imports provider: {imp}"
                )

    def test_source_contains_no_execution_imports(self) -> None:
        source = (PACKAGE_ROOT / "research" / "enterprise_ssd_datasheet.py").read_text()
        imports = _top_level_imports(source)
        for imp in imports:
            if imp.startswith("product_intelligence.execution"):
                raise AssertionError(
                    f"research/enterprise_ssd_datasheet source imports execution: {imp}"
                )

    def test_source_contains_no_pdf_library_imports(self) -> None:
        source = (PACKAGE_ROOT / "research" / "enterprise_ssd_datasheet.py").read_text()
        imports = _top_level_imports(source)
        for imp in imports:
            for forbidden in ("pdfplumber", "pdfminer", "pypdf", "fitz", "pymupdf"):
                if forbidden in imp.lower():
                    raise AssertionError(
                        f"research/enterprise_ssd_datasheet source imports PDF library: {imp}"
                    )

    def test_source_contains_no_network_imports(self) -> None:
        source = (PACKAGE_ROOT / "research" / "enterprise_ssd_datasheet.py").read_text()
        imports = _top_level_imports(source)
        for imp in imports:
            for forbidden in ("urllib", "requests", "httpx", "aiohttp", "socket", "ssl"):
                if imp == forbidden or imp.startswith(f"{forbidden}."):
                    raise AssertionError(
                        f"research/enterprise_ssd_datasheet source imports network: {imp}"
                    )

    def test_source_contains_no_filesystem_imports(self) -> None:
        source = (PACKAGE_ROOT / "research" / "enterprise_ssd_datasheet.py").read_text()
        imports = _top_level_imports(source)
        for imp in imports:
            if imp in ("os", "pathlib", "io"):
                raise AssertionError(
                    f"research/enterprise_ssd_datasheet source imports filesystem: {imp}"
                )

    def test_source_contains_only_allowed_imports(self) -> None:
        source = (PACKAGE_ROOT / "research" / "enterprise_ssd_datasheet.py").read_text()
        imports = _top_level_imports(source)
        # Allowed: stdlib + domain + research contracts
        allowed_prefixes = (
            "__future__", "datetime", "typing",
            "product_intelligence.domain",
            "product_intelligence.research",
        )
        for imp in imports:
            if not any(imp.startswith(p) for p in allowed_prefixes):
                # Check if it's a stdlib module
                import sys
                if imp not in sys.stdlib_module_names:
                    raise AssertionError(
                        f"research/enterprise_ssd_datasheet imports unexpected module: {imp}"
                    )


class TestProviderDocumentBoundaries:
    """Provider/document infrastructure must import no Enterprise SSD business rules."""

    def test_document_source_no_enterprise_ssd(self) -> None:
        source = (PACKAGE_ROOT / "providers" / "document.py").read_text()
        imports = _top_level_imports(source)
        for imp in imports:
            if "enterprise_ssd" in imp.lower():
                raise AssertionError(
                    f"providers/document source imports enterprise_ssd: {imp}"
                )

    def test_document_source_no_similarity(self) -> None:
        source = (PACKAGE_ROOT / "providers" / "document.py").read_text()
        imports = _top_level_imports(source)
        for imp in imports:
            if "similarity" in imp.lower():
                raise AssertionError(
                    f"providers/document source imports similarity: {imp}"
                )

    def test_document_source_no_business_labels(self) -> None:
        source = (PACKAGE_ROOT / "providers" / "document.py").read_text()
        for label in ("capacity", "sequential_read", "random_write", "DWPD",
                       "form_factor", "IOPS", "endurance"):
            assert label not in source.lower(), (
                f"providers/document contains business label: {label}"
            )

    def test_http_pdf_source_no_enterprise_ssd(self) -> None:
        source = (PACKAGE_ROOT / "providers" / "http_pdf.py").read_text()
        imports = _top_level_imports(source)
        for imp in imports:
            if "enterprise_ssd" in imp.lower():
                raise AssertionError(
                    f"providers/http_pdf source imports enterprise_ssd: {imp}"
                )

    def test_http_pdf_source_no_business_labels(self) -> None:
        source = (PACKAGE_ROOT / "providers" / "http_pdf.py").read_text()
        for label in ("capacity", "sequential_read", "random_write", "DWPD",
                       "form_factor", "IOPS"):
            assert label not in source.lower(), (
                f"providers/http_pdf contains business label: {label}"
            )


class TestExecutionEnrichmentBoundaries:
    """Execution enrichment may import provider/document boundary but not web/search."""

    def test_source_imports_document_boundary(self) -> None:
        source = (PACKAGE_ROOT / "execution" / "specification_enrichment.py").read_text()
        assert "from product_intelligence.providers.document import" in source

    def test_source_imports_frozen_contracts(self) -> None:
        source = (PACKAGE_ROOT / "execution" / "specification_enrichment.py").read_text()
        assert "normalize_enterprise_ssd_observation" in source
        assert "resolve_specification" in source
        assert "ENTERPRISE_SSD_SCHEMA" in source

    def test_source_no_web_imports(self) -> None:
        source = (PACKAGE_ROOT / "execution" / "specification_enrichment.py").read_text()
        imports = _top_level_imports(source)
        for imp in imports:
            if imp.startswith("product_intelligence.web"):
                raise AssertionError(
                    f"execution/specification_enrichment source imports web: {imp}"
                )

    def test_source_no_search_provider_imports(self) -> None:
        source = (PACKAGE_ROOT / "execution" / "specification_enrichment.py").read_text()
        imports = _top_level_imports(source)
        for imp in imports:
            if "serper" in imp.lower() or imp.endswith(".search"):
                raise AssertionError(
                    f"execution/specification_enrichment source imports search: {imp}"
                )

    def test_source_no_semantic_imports(self) -> None:
        source = (PACKAGE_ROOT / "execution" / "specification_enrichment.py").read_text()
        imports = _top_level_imports(source)
        for imp in imports:
            if "semantic" in imp.lower():
                raise AssertionError(
                    f"execution/specification_enrichment source imports semantic: {imp}"
                )

    def test_source_no_runs_models_imports(self) -> None:
        source = (PACKAGE_ROOT / "execution" / "specification_enrichment.py").read_text()
        imports = _top_level_imports(source)
        for imp in imports:
            if "runs.models" in imp or imp == "product_intelligence.runs":
                raise AssertionError(
                    f"execution/specification_enrichment source imports runs.models: {imp}"
                )
