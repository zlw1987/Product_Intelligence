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

    Rules:
    * If MPN exists (with or without a description): the paid query is the
      EXACT requested MPN — the exact-MPN phrase, and nothing else.
    * If only description exists: search by the canonical description.

    Exact-MPN retrieval is a first-class retrieval path
    (PRODUCT-INTEL.PUBLIC-RESEARCH-RECALL-FU1):

    For an explicit-MPN request the query must not be a blend of the MPN and
    the description. Search engines treat quoted phrases as a strong but SOFT
    ranking signal, and every extra term in the query is a channel through
    which the engine can displace the rare exact-MPN results with broad
    description matches (production request MTC20F2085S1RC64BH1T /
    "Micron 32GB DDR5-6400 ECC 2Rx8 RDIMM CL52 Tray": the blended query
    returned only generic "Micron 32GB DDR5" pages while the exact-MPN pages
    were absent from the response). A degradation can only drift toward terms
    that are present in the query; with the description removed from the paid
    query, every result the engine returns — even its phrase-degraded
    fallbacks — stays inside the requested MPN's token space.

    Removing the description from the PAID QUERY loses nothing the identity
    pipeline can use: a listing is ACCEPTED only when the page itself
    publishes an explicit MPN field that is EXACT / NORMALIZED_EXACT to the
    requested MPN (frozen 3C). Any page the frozen gate can accept therefore
    contains the exact MPN string, is indexed under it, and is reachable by
    the exact-MPN phrase query. Pages that do not contain the MPN can only
    ever be REJECTED (NO_EXPLICIT_MPN_EVIDENCE / MPN_MISMATCH) — retrieving
    them is cost and noise, not recall. The description remains fully in
    effect as pipeline context (identity assessment, semantic evaluation,
    presentation); it simply no longer competes with the MPN for the paid
    query's ranking.

    The MPN-only and description-only forms are unchanged from the original
    PRICE MVP contract.

    The query builder is pure and directly tested.

    Returns
    -------
    SearchQuery
        One query string for the search provider.
    """
    mpn = request.manufacturer_part_number
    description = request.description

    if mpn:
        # Explicit-MPN request (with or without a description): the exact
        # requested MPN is the entire paid query. With a description the
        # phrase is quoted so the exact identifier is the search term, not a
        # bag of its tokens.
        query_text = f'"{mpn}"' if description else mpn
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
