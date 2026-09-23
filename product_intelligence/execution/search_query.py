"""Search query builder for deterministic research execution.

This module builds one deterministic search query from a ResearchRequest.
"""

from __future__ import annotations

from product_intelligence.domain import ResearchRequest
from product_intelligence.providers.search import SearchQuery
from product_intelligence.research.micron_packaging_alias import (
    MicronPackagingAliasRelation,
)


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


def build_alias_expanded_search_query(
    request: ResearchRequest,
    relation: MicronPackagingAliasRelation,
) -> SearchQuery:
    """Build ONE alias-expanded search query for an established 4D-D relation.

    Additive to ``build_search_query`` (which is unchanged). Frozen 4D-D
    query shape: the requested MPN, the established relation's alias
    identifiers (the family members other than the requested form, in
    deterministic relation order), and nothing else, are grouped as ONE
    parenthesized OR clause with the requested MPN first:

        ("REQUESTED" OR "ALIAS1" OR "ALIAS2") description

    with the description omitted when the request has none:

        ("REQUESTED" OR "ALIAS1" OR "ALIAS2")

    The OR grouping is what makes the expansion recall-oriented: a document
    matching ANY of the family forms is returned. An AND grouping would have
    required one result to carry every quoted identifier simultaneously and
    would have defeated the purpose of alias expansion.

    The aliases are a CUSTOMER-DEFINED retrieval relation (retrieval recall
    only). This builder generates a query string; it grants no identity,
    category, manufacturer, or pricing authority, and it must only ever be
    called with an ESTABLISHED relation (one per run, at most one search
    call total).

    Raises ``TypeError``/``ValueError`` on a non-relation argument or a
    relation whose requested form does not bind this request — a
    programming defect, not a bounded authority outcome.
    """
    if not isinstance(relation, MicronPackagingAliasRelation):
        raise TypeError(
            "relation must be a MicronPackagingAliasRelation, got "
            f"{type(relation).__name__}"
        )
    mpn = request.manufacturer_part_number
    if not mpn:
        raise ValueError(
            "an alias-expanded query requires the request's MPN; an "
            "established relation always binds one"
        )
    if relation.requested_mpn != mpn:
        raise ValueError(
            "the relation does not bind this request's MPN; an "
            "alias-expanded query must use the request's own established "
            "relation"
        )

    quoted = [f'"{mpn}"']
    for alias in relation.aliases:
        quoted.append(f'"{alias}"')
    grouped = "(" + " OR ".join(quoted) + ")"
    query_text = grouped

    description = request.description
    if description:
        query_text = f"{grouped} {description}"

    return SearchQuery(text=query_text)
