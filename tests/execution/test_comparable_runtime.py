"""Tests for the default-provider comparable runtime adapter (PRODUCT-INTEL.7C-C).

Proves the adapter creates/passes the two concrete providers and delegates once.
No live network test.

BLOCKER 7: Strengthened to prove exact construction counts and exact delegation.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch, call

import pytest


class TestExecuteComparableResearchWithDefaultProviders:
    """Tests for execute_comparable_research_with_default_providers."""

    def test_imports_are_available(self) -> None:
        """The adapter is exported from the public execution API."""
        from product_intelligence.execution import (
            execute_comparable_research_with_default_providers,
        )
        assert callable(execute_comparable_research_with_default_providers)

    def test_constructs_and_passes_providers_exactly_once(self) -> None:
        """HttpPageFetcher constructed exactly once, HttpPdfFetcher constructed
        exactly once, execute_comparable_research called exactly once with those
        exact two objects.

        BLOCKER 7: Strengthened combined construction proof.
        """
        from product_intelligence.execution import (
            execute_comparable_research_with_default_providers,
        )

        mock_page_fetcher = MagicMock()
        mock_pdf_fetcher = MagicMock()

        call_records: list[dict] = []

        def _capture(child_id, *, page_fetcher, document_fetcher):
            call_records.append({
                "child_id": child_id,
                "page_fetcher": page_fetcher,
                "document_fetcher": document_fetcher,
            })

        with patch(
            "product_intelligence.providers.http_page.HttpPageFetcher",
            return_value=mock_page_fetcher,
        ) as mock_page_cls, patch(
            "product_intelligence.providers.http_pdf.HttpPdfFetcher",
            return_value=mock_pdf_fetcher,
        ) as mock_pdf_cls, patch(
            "product_intelligence.execution.comparable_research."
            "execute_comparable_research",
            side_effect=_capture,
        ) as mock_exec:
            execute_comparable_research_with_default_providers("test-child-id")

        # HttpPageFetcher constructed exactly once
        mock_page_cls.assert_called_once()
        # HttpPdfFetcher constructed exactly once
        mock_pdf_cls.assert_called_once()
        # execute_comparable_research called exactly once
        mock_exec.assert_called_once()

        # The exact same objects were passed
        assert len(call_records) == 1
        assert call_records[0]["child_id"] == "test-child-id"
        assert call_records[0]["page_fetcher"] is mock_page_fetcher
        assert call_records[0]["document_fetcher"] is mock_pdf_fetcher

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
