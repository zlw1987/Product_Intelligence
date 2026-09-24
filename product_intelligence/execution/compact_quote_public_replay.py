"""Public-only historical compact quote replay (PRODUCT-INTEL.4D-C).

Bounded execution/read-side service for the DENIED branch of the 4D-C
compact quote summary browser rendering.

The 4D-C security decision occurs in the web view BEFORE any vendor
supplemental artifact is read, decoded, or projected. This module is the
denied branch: it produces a ``CompactQuoteProjection`` containing NO
vendor rows — only rows derived from the public listing evidence and the
persisted FX evidence, plus (PROD-FIX1) run-scoped human-CONFIRMED
semantic rows whose identity authority is a persisted review-state fact
about the run (never vendor data):

* the already provenance-validated ``PriceAggregationResult`` supplied by
  the view (decoded from ``PriceIntelligenceSnapshot`` and verified against
  ``run.to_research_request()`` in ``research_detail``), and
* the persisted ``ResearchFxSnapshot``, if present.

What this module does:
* re-verify the request-provenance binding of the supplied
  ``PriceAggregationResult`` to the run (fail closed)
* read the persisted ``ResearchFxSnapshot`` (optional) and decode it
  through the frozen V1 FX codec
* project public rows through the frozen ``project_public_rows``
* perform ZERO live provider/network/semantic work

What this module does NOT do (binding):
* read ``ResearchSupplementSnapshot``
* import or call the commercial supplement codec
  (``decode_research_supplement_result``)
* call Vendor API providers, SearchProvider, PageFetcher, the semantic
  runtime, or the ECB live provider
* render HTML or any browser-visible format
* change Machine Price, Reviewed Price, or any authority

The frozen authorized-path replay (``execution/compact_quote_replay.py``)
is unchanged. This is a small additive service, not a refactor of it.
"""

from __future__ import annotations

from dataclasses import dataclass

from product_intelligence.research.aggregation import PriceAggregationResult
from product_intelligence.research.compact_quote import (
    CompactQuoteProjection,
    CompactQuoteProjectionError,
    project_human_confirmed_rows,
    project_public_rows,
)
from product_intelligence.research.fx_codec import (
    FxObservationSnapshot,
    decode_fx_observation,
)
from product_intelligence.runs.models import (
    ResearchFxSnapshot,
    ResearchRun,
)


@dataclass(frozen=True)
class PublicCompactQuoteReplayResult:
    """The result of a public-only compact quote replay.

    Attributes:
        projection: CompactQuoteProjection containing public listing rows
            plus (PROD-FIX1) human-confirmed rows — zero vendor rows.
        fx_snapshot: Decoded persisted FX observation snapshot, or None
            when no FX evidence is persisted for this run.
        run: The ResearchRun this replay is for.
    """

    projection: CompactQuoteProjection
    fx_snapshot: FxObservationSnapshot | None
    run: ResearchRun


def replay_public_compact_quote_projection(
    *,
    run: ResearchRun,
    price_result: PriceAggregationResult,
    confirmed_assessment_indices: frozenset[int] | None = None,
) -> PublicCompactQuoteReplayResult:
    """Build a vendor-free compact quote projection from persisted artifacts.

    This is the approved server-side replay entry point for the DENIED
    branch of the 4D-C compact quote summary. It does NOT render HTML.

    Authority rules:
    * Public rows: only from frozen 4A bucket membership, via the frozen
      ``project_public_rows`` reading ``price_result.buckets``.
    * Human-confirmed rows (PROD-FIX1): only from run-scoped assessment
      indices supplied by the caller AFTER the caller's fail-closed
      candidate-to-assessment binding validation (the same validated
      indices feeding the Reviewed Price). Human confirmation is identity
      authority only; the frozen Machine Price snapshot is never altered.
      These rows are public-listing evidence — never vendor data.
    * FX: from persisted ``ResearchFxSnapshot`` only (never live).
    * Vendor supplemental data: NEVER read in this path. Authorization
      happens before sensitive commercial artifact access; this service is
      unreachable from any code path that reads vendor artifacts.

    Parameters
    ----------
    run : ResearchRun
        The persisted research run (already loaded by the caller).
    price_result : PriceAggregationResult
        The already provenance-validated price aggregation result decoded
        from the run's ``PriceIntelligenceSnapshot``.
    confirmed_assessment_indices : frozenset[int] | None
        Optional run-scoped, binding-validated indices of human-CONFIRMED
        semantic candidates. ``None`` (or empty) projects no
        human-confirmed rows (frozen 4D-C behavior).

    Returns
    -------
    PublicCompactQuoteReplayResult
        Public-only projection plus the decoded persisted FX evidence.

    Raises
    ------
    TypeError
        If ``run`` is not a ResearchRun (programming error; propagates).
    CompactQuoteProjectionError
        If ``price_result`` is not an actual PriceAggregationResult, or is
        not bound to this run (request-provenance mismatch), or the frozen
        public projection fails (fail closed — no partial summary).
    FxCodecError
        If the persisted FX artifact is malformed (fail closed — mirrors
        the frozen authorized replay; no partial summary).
    """
    # Programming-contract check: the run must be the real ORM object.
    # A wrong type is a programming defect and must propagate, not be
    # converted into an "unavailable" summary.
    if not isinstance(run, ResearchRun):
        raise TypeError(
            f"run must be a ResearchRun, got {type(run).__name__!r}"
        )

    # The authority source must be the real frozen 4A result.
    if not isinstance(price_result, PriceAggregationResult):
        raise CompactQuoteProjectionError(
            f"Public compact quote replay requires a PriceAggregationResult "
            f"instance; got {type(price_result).__name__!r}. A duck-typed "
            f"object cannot be the frozen 4A authority source."
        )

    # Re-verify the request-provenance binding on the read side. The view
    # has already validated ``decoded.request == run.to_research_request()``
    # before reaching this service; this check makes the service safe
    # against independent misuse and fails closed on any mismatch.
    if price_result.request != run.to_research_request():
        raise CompactQuoteProjectionError(
            "Public compact quote replay requires a PriceAggregationResult "
            "bound to this run; request provenance mismatch."
        )

    # Persisted FX evidence only — zero live FX calls.
    fx_snapshot: FxObservationSnapshot | None = None
    try:
        fx_row = ResearchFxSnapshot.objects.get(run=run)
        fx_snapshot = decode_fx_observation(fx_row.payload)
    except ResearchFxSnapshot.DoesNotExist:
        pass  # No FX evidence — USD-equivalent display unavailable

    # Frozen authority-safe public projection.
    # FAIL-CLOSED: any projection failure propagates (no partial summary).
    public_rows = project_public_rows(price_result, fx_snapshot=fx_snapshot)

    # Human-confirmed rows (PROD-FIX1): public-listing evidence with a
    # persisted run-scoped identity authority overlay. Zero vendor data.
    human_confirmed_rows: tuple = ()
    if confirmed_assessment_indices:
        human_confirmed_rows = project_human_confirmed_rows(
            price_result,
            confirmed_assessment_indices,
            fx_snapshot=fx_snapshot,
        )

    projection = CompactQuoteProjection(
        rows=tuple(human_confirmed_rows) + tuple(public_rows)
    )

    return PublicCompactQuoteReplayResult(
        projection=projection,
        fx_snapshot=fx_snapshot,
        run=run,
    )
