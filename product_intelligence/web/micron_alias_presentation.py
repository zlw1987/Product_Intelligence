"""Display-only presentation for the persisted Micron alias audit
(PRODUCT-INTEL.4D-D).

Reads ONE decoded, persisted ``MicronAliasEligibilityResult`` (from the
historical report's ResearchMicronAliasSnapshot — never a live
acquisition) plus the already-decoded persisted
``PriceAggregationResult`` and prepares display data for the report:

* the bounded authority audit (status, policy, provenance, SSD evidence,
  alias relation) — always display-only, never an authority source;
* the alias reference rows: persisted EXCLUDED assessments whose published
  candidate MPN is a customer-defined alias identifier of an ESTABLISHED
  relation.

This module:

* performs ZERO network work (no Micron, search, vendor, FX, semantic, or
  generic fetch paths);
* carries no research semantics beyond the approved read-side reference
  labeling primitive ``find_alias_reference`` (frozen 2A comparison
  against the alias identifiers — reference labeling only, not identity);
* reuses the authoritative URL-safety helper from ``presentation``
  (no duplication);
* never feeds any value into Machine Price, Reviewed Price, Compact
  Quote, or Comparable presentation; the alias section is a separate,
  clearly labeled part of the report.

The alias relation is a CUSTOMER-DEFINED retrieval relation. Nothing in
this module claims the manufacturer documents R/T packaging semantics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from product_intelligence.research.matching import ListingIdentityAssessment
from product_intelligence.research.micron_packaging_alias import (
    MicronAliasEligibilityStatus,
    find_alias_reference,
)

from .presentation import _is_safe_href_url

if TYPE_CHECKING:
    from product_intelligence.research.micron_packaging_alias import (
        MicronAliasEligibilityResult,
    )

# NOTE: this module deliberately does NOT import
# ``product_intelligence.research.aggregation`` — the frozen web-aggregation
# import boundary (tests/research/test_price_aggregation_boundaries.py)
# allows aggregation imports in web/ only in views, presentation, and
# __init__. The persisted ``PriceAggregationResult`` is therefore consumed
# structurally (Any), matching the frozen 4D-C compact_quote_presentation
# precedent.


# The exact display wording for alias reference rows (binding 4D-D
# contract). These rows are customer-defined retrieval references,
# excluded from all pricing authority.
ALIAS_REFERENCE_NOTE = (
    "Customer-defined packaging alias reference — excluded from pricing authority"
)

# Neutral wording for the authority audit; never claims manufacturer
# documentation of R/T packaging semantics.
ALIAS_RELATION_NOTE = (
    "Customer-defined retrieval relation (retrieval recall only). "
    "Not manufacturer-published packaging identity."
)


@dataclass(frozen=True)
class AliasReferenceRow:
    """One persisted excluded listing that published a customer-defined
    alias identifier of an ESTABLISHED relation.

    Reference labeling only: this row exists so a reviewer can see which
    excluded listings published the alias identifiers. It grants no
    identity, no pricing, and no review-candidate membership.
    """

    source_url: str
    source_url_safe: bool
    product_title: str | None
    seller_name: str | None
    normalized_price: str | None
    currency_code: str | None
    condition: str | None
    published_candidate_mpn: str
    referenced_alias: str
    decision: str
    rejection_reason: str | None
    exclusion_reason: str


@dataclass
class MicronAliasPresentation:
    """Display-ready data for one persisted 4D-D alias audit."""

    status: str
    established: bool
    # Authority audit (bounded provenance; None values render as absent)
    policy_id: str
    requested_mpn: str
    lookup_base_candidate: str | None
    manufacturer: str | None
    category: str | None
    source_name: str | None
    requested_source_url: str | None
    requested_source_url_safe: bool
    fetched_final_url: str | None
    fetched_final_url_safe: bool
    retrieved_at: str | None
    matched_base_mpn: str | None
    part_number_match_type: str | None
    ssd_attr_name: str | None
    ssd_attr_id: str | None
    ssd_attr_value: str | None
    body_sha256: str | None
    alias_base_mpn: str | None
    alias_identifiers: tuple[str, ...] = ()
    # Reference rows (established only; persisted excluded listings that
    # publish an alias identifier)
    reference_rows: list[AliasReferenceRow] = field(default_factory=list)


def _format_retrieved_at(value: object) -> str | None:
    """Deterministic display form for a persisted retrieval timestamp."""
    if value is None:
        return None
    return str(value)


def build_micron_alias_presentation(
    alias_result: "MicronAliasEligibilityResult",
    price_result: Any,
) -> MicronAliasPresentation:
    """Build display-only data from one persisted alias audit.

    ``price_result`` is the persisted ``PriceAggregationResult`` (typed
    as Any to respect the frozen web-aggregation import boundary) or
    None (the run has no decodable price snapshot, e.g. a FAILED run):
    the authority audit still renders and the reference-row list is
    empty. No live work of any kind occurs.
    """
    status: MicronAliasEligibilityStatus = alias_result.status

    presentation = MicronAliasPresentation(
        status=status.value,
        established=status is MicronAliasEligibilityStatus.ESTABLISHED,
        policy_id=alias_result.policy_id,
        requested_mpn=alias_result.request.manufacturer_part_number,
        lookup_base_candidate=alias_result.lookup_base_candidate,
        manufacturer=alias_result.manufacturer,
        category=alias_result.category,
        source_name=alias_result.source_name,
        requested_source_url=alias_result.requested_source_url,
        requested_source_url_safe=_is_safe_href_url(
            alias_result.requested_source_url or ""
        ),
        fetched_final_url=alias_result.fetched_final_url,
        fetched_final_url_safe=_is_safe_href_url(
            alias_result.fetched_final_url or ""
        ),
        retrieved_at=_format_retrieved_at(alias_result.retrieved_at),
        matched_base_mpn=alias_result.matched_base_mpn,
        part_number_match_type=(
            alias_result.part_number_match.match_type.value
            if alias_result.part_number_match is not None
            else None
        ),
        ssd_attr_name=(
            alias_result.ssd_category_evidence.attr_name
            if alias_result.ssd_category_evidence is not None
            else None
        ),
        ssd_attr_id=(
            alias_result.ssd_category_evidence.attr_id
            if alias_result.ssd_category_evidence is not None
            else None
        ),
        ssd_attr_value=(
            str(alias_result.ssd_category_evidence.attr_value)
            if alias_result.ssd_category_evidence is not None
            else None
        ),
        body_sha256=alias_result.body_sha256,
        alias_base_mpn=(
            alias_result.alias_relation.base_mpn
            if alias_result.alias_relation is not None
            else None
        ),
        alias_identifiers=(
            tuple(alias_result.alias_relation.aliases)
            if alias_result.alias_relation is not None
            else ()
        ),
    )

    if not presentation.established or price_result is None:
        return presentation

    # Reference rows: persisted EXCLUDED assessments (frozen 4A exclusions
    # only — bucket members never appear here) whose published candidate
    # MPN is one of the customer-defined alias identifiers.
    relation = alias_result.alias_relation
    for exclusion in price_result.exclusions:
        assessment: ListingIdentityAssessment = exclusion.assessment
        referenced = find_alias_reference(
            relation.aliases, assessment.candidate_part_number_compared
        )
        if referenced is None:
            continue
        norm = assessment.normalized_listing
        obs = norm.observation
        presentation.reference_rows.append(
            AliasReferenceRow(
                source_url=obs.source_url,
                source_url_safe=_is_safe_href_url(obs.source_url),
                product_title=obs.product_title,
                seller_name=norm.seller_name,
                normalized_price=(
                    str(norm.price_amount)
                    if norm.price_amount is not None
                    else None
                ),
                currency_code=norm.currency_code,
                condition=(
                    norm.condition.value
                    if norm.condition is not None
                    else None
                ),
                published_candidate_mpn=assessment.candidate_part_number_compared,
                referenced_alias=referenced,
                decision=assessment.decision.value,
                rejection_reason=(
                    assessment.rejection_reason.value
                    if assessment.rejection_reason is not None
                    else None
                ),
                exclusion_reason=exclusion.reason.value,
            )
        )

    return presentation
