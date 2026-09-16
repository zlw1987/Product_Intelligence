"""Default-provider adapter for comparable research execution (PRODUCT-INTEL.7C-C).

Thin adapter that constructs the two concrete production providers and
delegates to the frozen ``execute_comparable_research`` operation.

This is the ONLY place in the web stack that touches concrete provider
classes. The web layer imports only this adapter, never providers directly.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from product_intelligence.runs.models import ComparableResearchExecution


__all__ = [
    "execute_comparable_research_with_default_providers",
]


def execute_comparable_research_with_default_providers(
    child_id: uuid.UUID | str,
) -> "ComparableResearchExecution":
    """Execute a PENDING ComparableResearchExecution with default providers.

    Constructs exactly:
        HttpPageFetcher()
        HttpPdfFetcher()

    and delegates once to the frozen ``execute_comparable_research``.

    Parameters
    ----------
    child_id
        The ComparableResearchExecution to execute.

    Returns
    -------
    ComparableResearchExecution
        The refreshed terminal row from the frozen operation.

    Raises
    ------
    ComparableResearchExecutionError
        Expected bounded failure (child terminalised FAILED).
    ComparableResearchClaimError
        If the child cannot be claimed.
    Exception
        Unexpected programming/invariant exceptions propagate unchanged.
    """
    from product_intelligence.execution.comparable_research import (
        execute_comparable_research,
    )
    from product_intelligence.providers.http_pdf import HttpPdfFetcher
    from product_intelligence.providers.http_page import HttpPageFetcher

    page_fetcher = HttpPageFetcher()
    document_fetcher = HttpPdfFetcher()

    return execute_comparable_research(
        child_id,
        page_fetcher=page_fetcher,
        document_fetcher=document_fetcher,
    )
