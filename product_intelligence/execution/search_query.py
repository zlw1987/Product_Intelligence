"""Search query builder for deterministic research execution.

This module builds one deterministic search query from a ResearchRequest.
"""

from __future__ import annotations

from product_intelligence.domain import ResearchRequest
from product_intelligence.providers.search import SearchQuery


def build_search_query(request: ResearchRequest) -> SearchQuery:
    """Build one deterministic search query from the ResearchRequest.

    Rules (PRICE MVP):
    * If MPN exists: make exact MPN the primary search term
    * If description also exists: use it only as additional context
    * If only description exists: search by the canonical description

    A reasonable target form when both exist is conceptually:
        "<exact MPN>" <description>

    The query builder is pure and directly tested.

    Returns
    -------
    SearchQuery
        One query string for the search provider.
    """
    mpn = request.manufacturer_part_number
    description = request.description

    if mpn and description:
        # Both exist: MPN primary, description as context
        # Use exact match quotes for MPN, append description
        query_text = f'"{mpn}" {description}'
    elif mpn:
        # Only MPN exists
        query_text = mpn
    else:
        # Only description exists
        query_text = description

    return SearchQuery(text=query_text)
