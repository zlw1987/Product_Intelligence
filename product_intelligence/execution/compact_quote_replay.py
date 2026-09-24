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
    project_human_confirmed_rows,
    project_public_rows,
    project_vendor_api_row,
)
from product_intelligence.research.fx_codec import (
    FxObservationSnapshot,
    decode_fx_observation,
)
from product_intelligence.research.price_result_codec import (
    decode_price_aggregation_result,
)
from product_intelligence.runs.models import (
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


def replay_compact_quote_projection(
    run_id: str,
    *,
    confirmed_assessment_indices: frozenset[int] | None = None,
) -> CompactQuoteReplayResult:
    """Build the compact quote projection from persisted artifacts.

    BLOCKER 5 (FU2): Historical replay entry point.

    This function reads persisted artifacts from a completed ResearchRun
    and builds the authority-safe CompactQuoteProjection WITHOUT any
    live provider calls.

    This is the approved server-side replay entry point for 4D-C web usage.
    It does NOT render HTML.

    Authority rules:
    * Public rows: only from frozen 4A bucket membership
      (via project_public_rows which reads PriceAggregationResult.buckets)
    * Vendor rows: only from actual SupplementSourceObservation instances
      with EXACT/NORMALIZED_EXACT match type and brand_new=True/VENDOR_API_POLICY
    * Human-confirmed rows (PROD-FIX1): only from run-scoped
      assessment indices supplied by the caller AFTER the caller's own
      fail-closed candidate-to-assessment binding validation passed
      (same validated indices that feed the Reviewed Price). The
      projection re-validates each index against the persisted snapshot
      (range, semantic eligibility, persisted price/currency). Human
      confirmation establishes identity authority only — it never alters
      the frozen Machine Price snapshot.
    * FX: from persisted ResearchFxSnapshot only (never live ECB call)

    Parameters
    ----------
    run_id : str
        The UUID of the completed ResearchRun.
    confirmed_assessment_indices : frozenset[int] | None
        Optional run-scoped, binding-validated indices of human-CONFIRMED
        semantic candidates. ``None`` (or empty) projects no
        human-confirmed rows (frozen 4D-C behavior).

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

    # Project human-confirmed rows (PROD-FIX1): run-scoped identity
    # authority overlay only. Never touches the frozen Machine Price
    # artifact; price/currency/condition are read from it as-is.
    human_confirmed_rows: tuple[CompactQuoteRow, ...] = ()
    if confirmed_assessment_indices:
        human_confirmed_rows = project_human_confirmed_rows(
            decoded_price,
            confirmed_assessment_indices,
            fx_snapshot=fx_snapshot,
        )

    # Combine: vendor rows first, then human-confirmed rows, then public
    # rows (deterministic order; frozen 4D-C vendor-first rule preserved)
    projection = CompactQuoteProjection(
        rows=tuple(vendor_rows) + human_confirmed_rows + public_rows
    )

    return CompactQuoteReplayResult(
        projection=projection,
        fx_snapshot=fx_snapshot,
        run=run,
        warnings=tuple(warnings),
    )