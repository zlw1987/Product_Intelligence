"""Standalone intake and report views (PRODUCT-INTEL.1B, extended 4B).

Two views, and between them the whole browser workflow:

```text
GET  /research/new      the form
POST /research/new      -> ResearchRequest -> ResearchRun (CREATED) -> redirect
GET  /research/<uuid>   the durable report (with optional price snapshot, 4B)
```

**No research happens here.** A submitted run is stored in `CREATED` and stays
there. The report reads an optional ``PriceIntelligenceSnapshot`` and renders
it if present. It starts nothing, transitions nothing, and writes no timestamp.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import uuid

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from product_intelligence.research.price_result_codec import (
    PriceResultCodecError,
    decode_price_aggregation_result,
)
from product_intelligence.runs.models import PriceIntelligenceSnapshot, ResearchRun
from product_intelligence.web.forms import ResearchRequestForm

if TYPE_CHECKING:
    from product_intelligence.research.aggregation import PriceAggregationResult
from product_intelligence.web.presentation import build_report_presentation


def research_new(request: HttpRequest) -> HttpResponse:
    """Show the standalone intake form, and accept its submission.

    Post/Redirect/Get: a successful POST creates exactly one run and answers
    with a redirect, so reloading the report cannot submit anything a second
    time. An invalid POST re-renders the form with its errors and creates
    nothing.

    A GET is *always* a form display, even when query parameters are present.
    The launcher entry point that turns ``?mpn=…&description=…`` into a run is
    phase 5B and is deliberately not implemented here.
    """
    if request.method == "POST":
        form = ResearchRequestForm(request.POST)
        if form.is_valid():
            run = ResearchRun.objects.create_from_request(form.research_request)
            return redirect("research-detail", run_id=run.id)
    else:
        form = ResearchRequestForm()

    return render(request, "web/research_new.html", {"form": form})


def research_detail(request: HttpRequest, run_id: uuid.UUID) -> HttpResponse:
    """The durable report for one run.

    Read-only in the strictest sense: loads rows and renders them. Starts
    nothing, transitions nothing, writes no timestamp.

    When a ``PriceIntelligenceSnapshot`` exists, the report decodes it and
    presents the price intelligence evidence. On decode failure, corrupt
    payload, unsupported schema version, or request-provenance mismatch, the
    report renders *zero* price numbers and shows a neutral unavailable
    notice.
    """
    run = get_object_or_404(ResearchRun, pk=run_id)

    # --- Attempt to load and decode the snapshot ---
    decoded_result: PriceAggregationResult | None = None
    snapshot_error: str | None = None
    snapshot_created_at = None

    try:
        snapshot = run.price_intelligence_snapshot
    except PriceIntelligenceSnapshot.DoesNotExist:
        snapshot = None

    if snapshot is not None:
        snapshot_created_at = snapshot.created_at
        try:
            decoded = decode_price_aggregation_result(
                snapshot.payload,
                schema_version=snapshot.schema_version,
            )
        except PriceResultCodecError:
            snapshot_error = (
                "The stored price result is invalid or in an unsupported "
                "format."
            )
        else:
            # --- Request provenance check ---
            if decoded.request != run.to_research_request():
                snapshot_error = (
                    "The stored price result does not match this research "
                    "request."
                )
            else:
                decoded_result = decoded

    # --- Build presentation from decoded result ---
    report_presentation = None
    if decoded_result is not None:
        report_presentation = build_report_presentation(decoded_result)

    context = {
        "run": run,
        "report_presentation": report_presentation,
        "snapshot_error": snapshot_error,
        "snapshot_created_at": snapshot_created_at,
        "has_snapshot": snapshot is not None,
    }

    return render(request, "web/research_detail.html", context)
