"""Tests for the default-provider comparable runtime adapter (PRODUCT-INTEL.7C-C).

Proves the adapter creates/passes the two concrete providers and delegates once.
No live network test.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest


class TestExecuteComparableResearchWithDefaultProviders:
    """Tests for execute_comparable_research_with_default_providers."""

    def test_imports_are_available(self) -> None:
        """The adapter is exported from the public execution API."""
        from product_intelligence.execution import (
            execute_comparable_research_with_default_providers,
        )
        assert callable(execute_comparable_research_with_default_providers)

    def test_constructs_http_page_fetcher(self) -> None:
        """HttpPageFetcher is constructed once."""
        from product_intelligence.execution import (
            execute_comparable_research_with_default_providers,
        )

        mock_result = MagicMock()
        mock_page_fetcher = MagicMock()
        mock_pdf_fetcher = MagicMock()

        call_args: list[list] = []

        def _capture(child_id, *, page_fetcher, document_fetcher):
            call_args.append([child_id, page_fetcher, document_fetcher])

        with patch(
            "product_intelligence.providers.http_page.HttpPageFetcher",
            return_value=mock_page_fetcher,
        ), patch(
            "product_intelligence.providers.http_pdf.HttpPdfFetcher",
            return_value=mock_pdf_fetcher,
        ), patch(
            "product_intelligence.execution.comparable_research."
            "execute_comparable_research",
            side_effect=_capture,
        ):
            execute_comparable_research_with_default_providers("test-child-id")

        assert len(call_args) == 1
        assert call_args[0][0] == "test-child-id"
        assert mock_page_fetcher is call_args[0][1]

    def test_constructs_http_pdf_fetcher(self) -> None:
        """HttpPdfFetcher is constructed once."""
        from product_intelligence.execution import (
            execute_comparable_research_with_default_providers,
        )

        mock_page_fetcher = MagicMock()
        mock_pdf_fetcher = MagicMock()

        call_args: list[list] = []

        def _capture(child_id, *, page_fetcher, document_fetcher):
            call_args.append([child_id, page_fetcher, document_fetcher])

        with patch(
            "product_intelligence.providers.http_page.HttpPageFetcher",
            return_value=mock_page_fetcher,
        ), patch(
            "product_intelligence.providers.http_pdf.HttpPdfFetcher",
            return_value=mock_pdf_fetcher,
        ), patch(
            "product_intelligence.execution.comparable_research."
            "execute_comparable_research",
            side_effect=_capture,
        ):
            execute_comparable_research_with_default_providers("test-child-id")

        assert len(call_args) == 1
        assert mock_pdf_fetcher is call_args[0][2]

    def test_delegates_once_to_frozen_operation(self) -> None:
        """Frozen execute_comparable_research is called exactly once."""
        from product_intelligence.execution import (
            execute_comparable_research_with_default_providers,
        )

        mock_result = MagicMock()

        with patch(
            "product_intelligence.execution.comparable_research."
            "execute_comparable_research",
            return_value=mock_result,
        ) as mock_exec:
            result = execute_comparable_research_with_default_providers(
                "test-child-id",
            )

        mock_exec.assert_called_once()
        assert result is mock_result

    def test_passes_both_providers_as_kwargs(self) -> None:
        """Both providers are passed as keyword arguments."""
        from product_intelligence.execution import (
            execute_comparable_research_with_default_providers,
        )

        captured_kwargs: dict | None = None

        def _capture(child_id, **kwargs):
            nonlocal captured_kwargs
            captured_kwargs = dict(kwargs)

        with patch(
            "product_intelligence.execution.comparable_research."
            "execute_comparable_research",
            side_effect=_capture,
        ):
            execute_comparable_research_with_default_providers("child-id")

        assert captured_kwargs is not None
        assert "page_fetcher" in captured_kwargs
        assert "document_fetcher" in captured_kwargs

    def test_exceptions_propagate_unchanged(self) -> None:
        """Provider/execution exceptions propagate unchanged."""
        from product_intelligence.execution import (
            execute_comparable_research_with_default_providers,
        )

        expected = RuntimeError("bounded execution failure")

        with patch(
            "product_intelligence.execution.comparable_research."
            "execute_comparable_research",
            side_effect=expected,
        ):
            with pytest.raises(RuntimeError, match="bounded execution failure"):
                execute_comparable_research_with_default_providers("child-id")

    def test_accepts_uuid_child_id(self) -> None:
        """UUID child_id is passed through."""
        from uuid import UUID

        from product_intelligence.execution import (
            execute_comparable_research_with_default_providers,
        )

        captured_id: object | None = None

        def _capture(child_id, **kwargs):
            nonlocal captured_id
            captured_id = child_id

        with patch(
            "product_intelligence.execution.comparable_research."
            "execute_comparable_research",
            side_effect=_capture,
        ):
            test_uuid = UUID("12345678-1234-5678-1234-567812345678")
            execute_comparable_research_with_default_providers(test_uuid)

        assert captured_id is test_uuid

    def test_web_does_not_import_providers_directly(self) -> None:
        """The web layer does not import HttpPageFetcher or HttpPdfFetcher.

        Only the adapter in execution/comparable_runtime.py owns concrete
        provider construction.
        """
        import ast
        from pathlib import Path

        web_root = Path(__file__).resolve().parents[2] / "product_intelligence" / "web"

        forbidden_modules = {
            "product_intelligence.providers.http_page",
            "product_intelligence.providers.http_pdf",
            "product_intelligence.providers",
        }

        for py_file in web_root.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if node.module in forbidden_modules:
                        pytest.fail(
                            f"{py_file.name} imports {node.module}; "
                            "web must not import providers directly."
                        )
                    if node.module.startswith("product_intelligence.providers"):
                        pytest.fail(
                            f"{py_file.name} imports {node.module}; "
                            "web must not import providers directly."
                        )
