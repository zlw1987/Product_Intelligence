"""Shared vendor-commercial binding/encoding policy (VREF-R1-1, decision D10).

This module carries the 4D-B candidate binding / issue mapping / supplement
encoding policy, extracted VERBATIM from
``product_intelligence.execution.orchestration._try_vendor_commercial_lookup``
at the frozen R0 base SHA ``3983db4b57e9b960d5bf6841042c93a14687fdd0``.

R1-1 is a pure refactor: the frozen 4D-B behavior (pinned by the golden
dicts in ``tests/execution/test_vendor_commercial_binding.py``, captured
from the pre-extraction orchestration path) must remain byte-identical.

Purity contract (AST-pinned by the R1-1 tests):

* no database access
* no network access
* no environment/config access
* no provider adapter construction (no ``providers.internal_vendor`` import)
* no FX, semantic, search, or comparable execution
* no modification of its input response
* no new codec or authority interpretation

Import allowlist (pinned): ``product_intelligence.research.identity``
(frozen 2A ``compare_part_numbers``),
``product_intelligence.research.commercial_supplement_codec`` (frozen V1
dataclasses + encoder), ``product_intelligence.providers.commercial``
(``LookupStatus``; the response type is annotation-only), and stdlib.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from product_intelligence.providers.commercial import LookupStatus
from product_intelligence.research.identity import compare_part_numbers

if TYPE_CHECKING:  # pragma: no cover - annotation only
    from product_intelligence.providers.commercial import (
        CommercialSourceResponse,
    )


def bind_and_encode_vendor_lookup(
    requested_mpn: str,
    response: "CommercialSourceResponse",
) -> dict:
    """Bind the returned commercial candidates and encode the supplement.

    This is the moved 4D-B binding/encoding policy (frozen R0 inline block
    of ``_try_vendor_commercial_lookup`` steps 6-7). It receives the
    already-executed ``CommercialSourceResponse`` and produces the encoded
    supplemental payload dict; it performs no lookup, no adapter
    construction, and no I/O of any kind.

    Policy (unchanged from the frozen 4D-B implementation):

    * Iterate the returned commercial candidates.
    * Bind each candidate against the exact requested MPN using the frozen
      2A ``compare_part_numbers``.
    * Admit only EXACT and NORMALIZED_EXACT identity matches as
      observations; every other candidate maps to the bounded
      ``MPN_MISMATCH`` / ``vendor_mpn_mismatch`` issue.
    * ``brand_new=True`` / ``brand_new_basis="VENDOR_API_POLICY"`` apply
      ONLY to successfully identity-bound observations.
    * Provider-layer issues are copied with bounded fields and
      ``detail=None`` (never raw provider text).
    * Price, currency, availability, price-basis, quantity, and note-kind
      values are preserved without reinterpretation.
    * Transport-level FAILED maps to ``lookup_status="FAILED"`` and
      ``retrieved_at=None``; SUCCESS and PARTIAL preserve
      ``response.status.value`` and ``response.retrieved_at``.
    * The result is encoded with the frozen V1
      ``encode_research_supplement_result``; ``SupplementCodecError``
      propagates (programming/contract defect) without leaking raw private
      provider data.
    """
    # Frozen V1 codec symbols are resolved at call time, exactly as the
    # pre-extraction function-level import in
    # ``_try_vendor_commercial_lookup`` did (frozen 4D-B contract).
    from product_intelligence.research.commercial_supplement_codec import (
        ResearchSupplementResult,
        SupplementCodecError,
        SupplementSourceIssue,
        SupplementSourceObservation,
        VendorCommercialResult,
        encode_research_supplement_result,
    )

    # Filter candidates through frozen 2A identity binding
    bound_observations: list[SupplementSourceObservation] = []
    bound_issues: list[SupplementSourceIssue] = []

    for candidate in response.candidates:
        assessment = compare_part_numbers(
            requested_mpn,
            candidate.explicit_candidate_mpn,
        )
        if assessment.match_type.value in ("EXACT", "NORMALIZED_EXACT"):
            # Identity-bound — apply business policy.
            # Brand New is a business-policy conclusion that applies ONLY
            # after frozen 2A has successfully identity-bound the vendor
            # observation to the requested product.
            bound_observations.append(SupplementSourceObservation(
                source_name=candidate.source_name,
                explicit_candidate_mpn=candidate.explicit_candidate_mpn,
                vendor_mpn_match_type=assessment.match_type.value,
                price_amount=candidate.price_amount,
                currency_code=candidate.currency_code,
                availability=candidate.availability.value,
                price_basis=candidate.price_basis.value,
                quantity=candidate.quantity,
                note_kind=candidate.note_kind.value if candidate.note_kind else None,
                brand_new=True,
                brand_new_basis="VENDOR_API_POLICY",
            ))
        else:
            # MPN mismatch — bounded detail only, never raw provider text
            bound_issues.append(SupplementSourceIssue(
                source_name=candidate.source_name,
                outcome="MPN_MISMATCH",
                detail="vendor_mpn_mismatch",
            ))

    # Copy issues from the original response.
    # Provider-layer issues carry bounded outcome only (no arbitrary detail).
    for issue in response.issues:
        bound_issues.append(SupplementSourceIssue(
            source_name=issue.source_name,
            outcome=issue.outcome.value,
            detail=None,
        ))

    # Determine final lookup status
    if response.status == LookupStatus.FAILED:
        # Whole transport failure — encode as FAILED
        final_status = "FAILED"
        retrieved_at = None
    else:
        final_status = response.status.value
        retrieved_at = response.retrieved_at

    # Encode the supplemental result
    try:
        supplement_result = ResearchSupplementResult(
            vendor_commercial_result=VendorCommercialResult(
                lookup_status=final_status,
                retrieved_at=retrieved_at,
                observations=tuple(bound_observations),
                source_issues=tuple(bound_issues),
            ),
        )
        encoded = encode_research_supplement_result(supplement_result)
    except SupplementCodecError:
        # Codec error — propagate (programming/contract defect).
        # No raw exception text in logs.
        raise

    return encoded
