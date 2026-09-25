"""Public-only historical compact quote replay (PRODUCT-INTEL.4D-C, FU2).

Bounded execution/read-side service for the DENIED branch of the 4D-C
compact quote summary browser rendering.

The 4D-C security decision occurs in the web view BEFORE any vendor
supplemental artifact is read, decoded, or projected. This module is the
denied branch: it produces a ``CompactQuoteProjection`` containing NO
vendor rows — only rows derived from the public listing evidence and the
persisted FX evidence, plus (PROD-FIX1) run-scoped human-CONFIRMED
semantic rows whose identity authority is a persisted review-state fact
about the run (never vendor data).

FU2 authority ownership (PROD-FIX1 final review blocker): the public
replay now OWNS its price/currency/condition evidence authority exactly
like the authorized replay. It loads the run's own persisted
``PriceIntelligenceSnapshot`` and decodes it through the canonical
price-result codec. A caller-supplied price aggregation result is NO
LONGER part of this API: a same-request cross-run result (identical
source URL / title / MPN field / SKU / evidence source, different
persisted price) can never substitute for the persisted snapshot, and a
bare caller integer can never mint HUMAN_CONFIRMED authority.
Confirmation establishes identity authority only over the persisted
evidence belonging to THAT SAME run.

What this module does:
* verify ``run`` is a real ``ResearchRun`` (programming contract)
* load ``PriceIntelligenceSnapshot.objects.get(run=run)`` — the
  authority source for this replay (missing artifact fails closed)
* decode it through the canonical price-result codec (malformed
  artifact / unsupported schema version fails closed)
* verify the decoded request is bound to this run
  (``decoded.request == run.to_research_request()``; a
  request-provenance-corrupt snapshot fails closed)
* read the persisted ``ResearchFxSnapshot`` (optional) and decode it
  through the frozen V1 FX codec
* project public rows through the frozen ``project_public_rows``
* derive the human-confirmed selection from persisted state via the
  shared ``derive_human_confirmed_assessment_indices``
* derive HIGH auto-included Working Quote candidates from persisted state via
  the shared ``derive_ai_auto_included_assessment_indices``
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
is unchanged. This is a bounded correction of the denied-path
authority source, not a refactor of the authorized path.
"""

from __future__ import annotations

from dataclasses import dataclass

from product_intelligence.research.compact_quote import (
    CompactQuoteProjection,
    CompactQuoteProjectionError,
    project_ai_assisted_rows,
    project_human_confirmed_rows,
    project_public_rows,
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
    ResearchRun,
)

# FU1: the human-confirmation authority derivation is shared with the
# authorized-path replay (ONE code path proves the persisted CONFIRMED
# candidates; the two DENIED/ALLOWED branches must not diverge).
from product_intelligence.execution.compact_quote_replay import (
    derive_ai_auto_included_assessment_indices,
    derive_human_confirmed_assessment_indices,
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
) -> PublicCompactQuoteReplayResult:
    """Build a vendor-free compact quote projection from persisted artifacts.

    This is the approved server-side replay entry point for the DENIED
    branch of the 4D-C compact quote summary. It does NOT render HTML.

    Authority rules:
    * Price authority source (FU2): ONLY this run's own persisted
      ``PriceIntelligenceSnapshot``, loaded here and decoded through the
      canonical price-result codec. No parameter of this function accepts
      a price aggregation result — a caller-supplied same-request result
      (even one whose identity/provenance fields match exactly) can never
      substitute for the persisted snapshot, so historical reports stay
      immutable and run-scoped.
    * Request provenance: the decoded persisted result must satisfy
      ``decoded.request == run.to_research_request()`` or the replay
      fails closed (``CompactQuoteProjectionError``).
    * Public rows: only from frozen 4A bucket membership of the decoded
      persisted result, via the frozen ``project_public_rows``.
    * Human-confirmed rows (PROD-FIX1, FU1 authority ownership): derived
      EXCLUSIVELY from persisted state by the shared
      ``derive_human_confirmed_assessment_indices`` — a CONFIRMED run-scoped
      candidate whose full candidate-to-assessment binding is still valid
      against the persisted assessments of THIS run. Human confirmation is
      identity authority only; the frozen Machine Price snapshot is never
      altered. These rows are public-listing evidence — never vendor data.
    * FX: from persisted ``ResearchFxSnapshot`` only (never live).
    * Vendor supplemental data: NEVER read in this path. Authorization
      happens before sensitive commercial artifact access; this service is
      unreachable from any code path that reads vendor artifacts.

    Parameters
    ----------
    run : ResearchRun
        The persisted research run (already loaded by the caller). The
        run's own persisted price snapshot is the authority source.

    Returns
    -------
    PublicCompactQuoteReplayResult
        Public-only projection plus the decoded persisted FX evidence.

    Raises
    ------
    TypeError
        If ``run`` is not a ResearchRun (programming error; propagates).
    PriceIntelligenceSnapshot.DoesNotExist
        If the run has no persisted price snapshot (fail closed — the
        existing persisted-artifact behavior of the authorized replay;
        the web view maps this to "summary unavailable", never to a
        partial or borrowed summary).
    PriceResultCodecError
        If the persisted price artifact is malformed or its schema
        version is unsupported (fail closed — no partial summary).
    CompactQuoteProjectionError
        If the decoded persisted price result is not bound to this run
        (request-provenance mismatch), or the frozen public projection
        fails (fail closed — no partial summary).
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

    # FU2 authority ownership: the price/currency/condition evidence must
    # be the persisted PriceIntelligenceSnapshot belonging to THIS run.
    # The snapshot is loaded and decoded HERE — no caller can supply a
    # same-request result from another run in its place. A missing
    # artifact fails closed (DoesNotExist propagates, mirroring the
    # authorized replay's persisted-artifact behavior).
    price_snapshot = PriceIntelligenceSnapshot.objects.get(run=run)
    price_result = decode_price_aggregation_result(
        price_snapshot.payload,
        schema_version=price_snapshot.schema_version,
    )

    # Verify the decoded persisted result is bound to this run's request.
    # The authorized web path performs the same check before rendering;
    # this check makes the denied replay boundary safe against
    # independent misuse and fails closed on any mismatch.
    if price_result.request != run.to_research_request():
        raise CompactQuoteProjectionError(
            "Public compact quote replay requires the persisted "
            "PriceIntelligenceSnapshot to be bound to this run's request; "
            "request provenance mismatch."
        )

    # Persisted FX evidence only — zero live FX calls.
    fx_snapshot: FxObservationSnapshot | None = None
    try:
        fx_row = ResearchFxSnapshot.objects.get(run=run)
        fx_snapshot = decode_fx_observation(fx_row.payload)
    except ResearchFxSnapshot.DoesNotExist:
        pass  # No FX evidence — USD-equivalent display unavailable

    # Frozen authority-safe public projection over THIS run's persisted
    # result. FAIL-CLOSED: any projection failure propagates (no partial
    # summary).
    public_rows = project_public_rows(price_result, fx_snapshot=fx_snapshot)

    # Human-confirmed rows (FU1 authority ownership): the effective
    # human-confirmed selection is derived from PERSISTED state via the
    # shared derivation helper (CONFIRMED run-scoped candidates with
    # still-valid full bindings against THIS run's persisted
    # assessments). A caller cannot inject indices: this entry point
    # does not accept them. Zero vendor data.
    human_confirmed_rows: tuple = ()
    human_confirmed_indices = derive_human_confirmed_assessment_indices(
        run, price_result.assessments
    )
    if human_confirmed_indices:
        human_confirmed_rows = project_human_confirmed_rows(
            price_result,
            human_confirmed_indices,
            fx_snapshot=fx_snapshot,
        )

    ai_assisted_rows: tuple = ()
    ai_assisted_indices = derive_ai_auto_included_assessment_indices(
        run, price_result.assessments
    )
    if ai_assisted_indices:
        ai_assisted_rows = project_ai_assisted_rows(
            price_result,
            ai_assisted_indices,
            fx_snapshot=fx_snapshot,
        )

    projection = CompactQuoteProjection(
        rows=(
            tuple(human_confirmed_rows)
            + tuple(ai_assisted_rows)
            + tuple(public_rows)
        )
    )

    return PublicCompactQuoteReplayResult(
        projection=projection,
        fx_snapshot=fx_snapshot,
        run=run,
    )
