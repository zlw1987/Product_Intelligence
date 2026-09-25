"""Historical compact quote projection from persisted artifacts.

PRODUCT-INTEL.4D-C-A / BLOCKER 5 (FU2).

This module provides the server-side replay entry point for 4D-C web usage.
It reads persisted ResearchRun artifacts from the database and builds the
authority-safe CompactQuoteProjection WITHOUT any live provider calls.

**No browser HTML is rendered here.** The projection produces Python objects
containing display values. HTML rendering belongs to a later task after
the security gate is independently verified.

What this module does:
* Accept/load completed ResearchRun persisted artifacts
* Read PriceIntelligenceSnapshot
* Read ResearchSupplementSnapshot if present
* Read ResearchFxSnapshot if present
* Decode each through the canonical versioned codec
* Build the authority-safe CompactQuoteProjection
* Derive bounded UNREVIEWED AI Working Quote rows from persisted candidate
  state only (HIGH + exact target SKU + no conflicts + full binding)
* Perform NO live provider or semantic work

What this module does NOT do:
* Render HTML or any browser-visible format
* Call SearchProvider, PageFetcher, InternalVendorAdapter, EcbFxProvider
* Perform semantic evaluation
* Change Machine Price or Reviewed Price
* Affect any existing pipeline statistics
"""

from __future__ import annotations

from dataclasses import dataclass

from product_intelligence.research.compact_quote import (
    CompactQuoteProjection,
    CompactQuoteRow,
    project_ai_assisted_unreviewed_rows,
    project_condition_unknown_quote_rows,
    project_human_confirmed_rows,
    project_public_rows,
    project_vendor_api_row,
)
from product_intelligence.research.fx_codec import (
    FxObservationSnapshot,
    decode_fx_observation,
)
from product_intelligence.research.matching import is_review_candidate_binding_valid
from product_intelligence.research.working_quote_policy import (
    AiWorkingQuoteDisposition,
    classify_ai_match_for_working_quote,
)
from product_intelligence.research.price_result_codec import (
    decode_price_aggregation_result,
)
from product_intelligence.runs.models import (
    AiAssistedReviewCandidate,
    PriceIntelligenceSnapshot,
    ResearchFxSnapshot,
    ResearchSupplementSnapshot,
    ResearchRun,
)


@dataclass(frozen=True)
class CompactQuoteReplayResult:
    """The result of a historical compact quote replay.

    Attributes:
        projection: The complete compact quote projection with all rows.
        fx_snapshot: Decoded FX observation snapshot, or None if no FX evidence.
        run: The ResearchRun this replay is for.
        warnings: List of warnings encountered during replay.
    """

    projection: CompactQuoteProjection
    fx_snapshot: FxObservationSnapshot | None
    run: ResearchRun
    warnings: tuple[str, ...]


def derive_human_confirmed_assessment_indices(
    run: ResearchRun,
    assessments: tuple,
) -> frozenset[int]:
    """Prove, from PERSISTED STATE, the human-confirmed Compact Quote indices.

    FU1 authority ownership: the replay boundary — not the caller — decides
    which assessment indices carry human-confirmation authority. A bare
    integer index supplied by any caller is NEVER treated as proof of
    confirmation. For each index returned here, this function proves from
    persisted state that:

    1. an ``AiAssistedReviewCandidate`` exists for THIS run (the query is
       run-scoped — a candidate from another run cannot enter);
    2. its ``review_state`` is CONFIRMED (UNREVIEWED / REJECTED / undone
       candidates never qualify);
    3. it is mapped to the assessment index (in range of the persisted
       snapshot assessments — a stale out-of-range index never qualifies);
    4. its full candidate-to-assessment provenance binding is still valid
       (the single pure binding primitive shared with the web path — a
       tampered candidate never qualifies);
    5. the mapped assessment is still human-review eligible (part of the
       shared binding check);
    6. persisted price/currency existence is enforced downstream by
       ``project_human_confirmed_rows`` (a confirmed listing without
       persisted price evidence produces no row).

    Zero live I/O: this reads persisted review state only (database).
    Candidates that fail any check are dropped (fail closed — the row
    simply does not exist); they never raise and never enter the quote.
    """
    confirmed_candidates = AiAssistedReviewCandidate.objects.filter(
        run=run,
        review_state=AiAssistedReviewCandidate.REVIEW_STATE_CONFIRMED,
    )
    valid_indices: set[int] = set()
    for candidate in confirmed_candidates:
        idx = candidate.assessment_index
        if not isinstance(idx, int) or isinstance(idx, bool):
            continue  # contract-invalid persisted row: fail closed
        if idx < 0 or idx >= len(assessments):
            continue  # stale mapping: fail closed
        if not is_review_candidate_binding_valid(candidate, assessments[idx]):
            continue  # tampered / foreign / non-eligible binding: fail closed
        valid_indices.add(idx)
    return frozenset(valid_indices)


def derive_ai_working_quote_unreviewed_indices(
    run: ResearchRun,
    assessments: tuple,
) -> frozenset[int]:
    """Derive auto-included UNREVIEWED AI Working Quote assessment indices.

    Every candidate is run-scoped and must pass the same full binding used by
    human review. The pure policy then requires HIGH confidence, exact target
    SKU evidence, and no conflicts. Anything else fails closed out of the
    Working Quote.
    """
    candidates = AiAssistedReviewCandidate.objects.filter(
        run=run,
        review_state=AiAssistedReviewCandidate.REVIEW_STATE_UNREVIEWED,
    )
    valid_indices: set[int] = set()
    for candidate in candidates:
        idx = candidate.assessment_index
        if type(idx) is not int or idx < 0 or idx >= len(assessments):
            continue
        assessment = assessments[idx]
        if not is_review_candidate_binding_valid(candidate, assessment):
            continue
        norm = assessment.normalized_listing
        if norm.price_amount is None or norm.currency_code is None:
            continue
        disposition = classify_ai_match_for_working_quote(
            assessment,
            review_state=candidate.review_state,
            semantic_confidence=candidate.semantic_confidence,
            candidate_sku=candidate.candidate_sku,
            target_mpn=candidate.target_mpn,
            conflicting_attributes=candidate.semantic_conflicting_attributes,
        )
        if disposition is AiWorkingQuoteDisposition.AUTO_INCLUDE_UNVERIFIED:
            valid_indices.add(idx)
    return frozenset(valid_indices)


def replay_compact_quote_projection(
    run_id: str,
) -> CompactQuoteReplayResult:
    """Build the compact quote projection from persisted artifacts.

    BLOCKER 5 (FU2): Historical replay entry point.

    This function reads persisted artifacts from a completed ResearchRun
    and builds the authority-safe CompactQuoteProjection WITHOUT any
    live provider calls.

    This is the approved server-side replay entry point for 4D-C web usage.
    It does NOT render HTML.

    Authority rules:
    * Public market rows: only from frozen 4A bucket membership
      (via project_public_rows which reads PriceAggregationResult.buckets)
    * Public quote-only rows: only from frozen 4A UNKNOWN_CONDITION
      exclusions; they never become market buckets or statistics
    * Vendor rows: only from actual SupplementSourceObservation instances
      with EXACT/NORMALIZED_EXACT match type and brand_new=True/VENDOR_API_POLICY
    * Unreviewed AI Working Quote rows: derived only from run-scoped
      UNREVIEWED candidates with full provenance binding and the pure
      bounded policy (HIGH + exact target SKU + no conflicts). They remain
      AI-assisted display evidence and never enter frozen 4A market buckets.
    * Human-confirmed rows (PROD-FIX1, FU1 authority ownership): derived
      EXCLUSIVELY from persisted state by
      ``derive_human_confirmed_assessment_indices`` — a CONFIRMED
      run-scoped candidate whose full candidate-to-assessment binding is
      still valid. This entry point accepts NO caller-supplied indices: a
      bare integer can never mint HUMAN_CONFIRMED authority. The
      projection re-validates each derived index against the persisted
      snapshot (range, semantic eligibility, persisted price/currency).
      Human confirmation establishes identity authority only — it never
      alters the frozen Machine Price snapshot.
    * FX: from persisted ResearchFxSnapshot only (never live ECB call)

    Parameters
    ----------
    run_id : str
        The UUID of the completed ResearchRun.

    Returns
    -------
    CompactQuoteReplayResult
        The complete replay result with projection, FX evidence, and warnings.

    Raises
    ------
    ResearchRun.DoesNotExist
        If no run exists with the given ID.
    PriceIntelligenceSnapshot.DoesNotExist
        If the run has no price intelligence snapshot.
    """
    warnings: list[str] = []

    # Get the run
    run = ResearchRun.objects.get(id=run_id)

    # Read and decode price intelligence snapshot
    price_snapshot = PriceIntelligenceSnapshot.objects.get(run=run)
    decoded_price = decode_price_aggregation_result(
        price_snapshot.payload,
        schema_version=price_snapshot.schema_version,
    )

    # Read and decode FX snapshot (optional)
    fx_snapshot: FxObservationSnapshot | None = None
    try:
        fx_row = ResearchFxSnapshot.objects.get(run=run)
        fx_snapshot = decode_fx_observation(fx_row.payload)
    except ResearchFxSnapshot.DoesNotExist:
        pass  # No FX evidence — USD-only run

    # Read and decode supplemental snapshot (optional, for vendor rows)
    supplemental_result = None
    try:
        supplement_row = ResearchSupplementSnapshot.objects.get(run=run)
        from product_intelligence.research.commercial_supplement_codec import (
            decode_research_supplement_result,
        )
        supplemental_result = decode_research_supplement_result(supplement_row.payload)
    except ResearchSupplementSnapshot.DoesNotExist:
        pass  # No supplemental evidence

    # Build public listing rows from frozen 4A buckets
    # BLOCKER 1 (FU2): Authority flows through actual bucket membership.
    # project_public_rows reads price_result.buckets[*].assessments as the
    # frozen 4A authority source. An assessment not in any bucket cannot
    # be projected.
    # BLOCKER 1 (FU3): Fail-closed — any projection failure propagates.
    # Optional artifact absence (no FX, no supplemental) is valid.
    # But codec failure, authority-contract failure, projection failure,
    # programming error, or unexpected exception from project_public_rows
    # MUST propagate — the replay does NOT silently return a partial
    # projection.
    public_rows = project_public_rows(
        decoded_price,
        fx_snapshot=fx_snapshot,
    )

    # Exact-identity listings with persisted price/currency but UNKNOWN
    # condition remain outside frozen 4A market arithmetic. Surface them
    # only as explicit quote-only evidence.
    quote_only_rows = project_condition_unknown_quote_rows(
        decoded_price,
        fx_snapshot=fx_snapshot,
    )

    # Project vendor API rows from supplemental result
    # Only usable observations (EXACT/NORMALIZED_EXACT, brand_new=True)
    # can become rows
    # BLOCKER 1 (FU3): Fail-closed — any vendor row projection failure
    # propagates. A decoded SupplementSourceObservation that violates the
    # reportability policy fails the replay rather than disappearing into
    # warnings.
    vendor_rows: list[CompactQuoteRow] = []
    if supplemental_result is not None:
        for obs in supplemental_result.vendor_commercial_result.observations:
            row = project_vendor_api_row(
                obs,
                fx_snapshot=fx_snapshot,
            )
            vendor_rows.append(row)

    # Project human-confirmed rows (FU1 authority ownership): the
    # effective human-confirmed selection is derived from PERSISTED state
    # — CONFIRMED run-scoped candidates with still-valid full bindings.
    # A caller cannot inject indices: this entry point no longer accepts
    # them. Never touches the frozen Machine Price artifact;
    # price/currency/condition are read from it as-is.
    human_confirmed_rows: tuple[CompactQuoteRow, ...] = ()
    human_confirmed_indices = derive_human_confirmed_assessment_indices(
        run, decoded_price.assessments
    )
    if human_confirmed_indices:
        human_confirmed_rows = project_human_confirmed_rows(
            decoded_price,
            human_confirmed_indices,
            fx_snapshot=fx_snapshot,
        )

    ai_unreviewed_rows: tuple[CompactQuoteRow, ...] = ()
    ai_unreviewed_indices = derive_ai_working_quote_unreviewed_indices(
        run, decoded_price.assessments
    )
    if ai_unreviewed_indices:
        ai_unreviewed_rows = project_ai_assisted_unreviewed_rows(
            decoded_price,
            ai_unreviewed_indices,
            fx_snapshot=fx_snapshot,
        )

    # Combine: vendor rows first, then human-confirmed rows, then public
    # rows (deterministic order; frozen 4D-C vendor-first rule preserved)
    projection = CompactQuoteProjection(
        rows=(
            tuple(vendor_rows)
            + human_confirmed_rows
            + ai_unreviewed_rows
            + public_rows
            + quote_only_rows
        )
    )

    return CompactQuoteReplayResult(
        projection=projection,
        fx_snapshot=fx_snapshot,
        run=run,
        warnings=tuple(warnings),
    )