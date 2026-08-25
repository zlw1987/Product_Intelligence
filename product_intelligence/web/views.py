"""Standalone intake and report views (PRODUCT-INTEL.1B, extended 4B, 4C-C).

Two views, and between them the whole browser workflow:

```text
GET  /research/new      the form (with optional MPN/description prefill from query)
POST /research/new      -> ResearchRequest -> ResearchRun (CREATED) -> execute -> redirect
GET  /research/<uuid>   the durable report (with optional price snapshot, 4B)
POST /research/<uuid>/retry  create a new run from a FAILED run and execute it
```

Query flags used for transient error notices:
- ?start_error=1  — execution could not be started (run remains CREATED)
- ?retry_error=1  — retry could not be started (old run is shown)
"""

from logging import getLogger

import uuid

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from product_intelligence.execution import ExecutionError, execute_research_run
from product_intelligence.runs import ClaimExecutionFailed, retry_run
from product_intelligence.runs.models import PriceIntelligenceSnapshot, ResearchRun

from .forms import ResearchRequestForm
from .presentation import build_report_presentation
from product_intelligence.research.aggregation import PriceAggregationResult
from product_intelligence.research.price_result_codec import (
    PriceResultCodecError,
    decode_price_aggregation_result,
)


def _redirect_to_report(run: ResearchRun, start_error: bool = False, retry_error: bool = False) -> HttpResponse:
    """Redirect to the report for *run*, optionally adding a transient flag."""
    if start_error:
        return redirect(f"/research/{run.id}?start_error=1")
    if retry_error:
        return redirect(f"/research/{run.id}?retry_error=1")
    return redirect("research-detail", run_id=run.id)


def research_new(request: HttpRequest) -> HttpResponse:
    """Show the standalone intake form, and accept its submission.

    GET: Display the form. If query parameters ``mpn`` or ``description`` are
    present, prepopulate the form fields. GET is always a form display, never
    a run creation.

    POST: Create a ResearchRequest from the form, then create a ResearchRun
    in CREATED state, call the backend executor synchronously, and redirect
    to the run's detail page.

    If execution fails (ExecutionError), the run transitions to FAILED and
    the user is directed to the report with failure state.

    If execution cannot be started at all (e.g., server misconfiguration),
    the run is left in CREATED and the user is redirected with ?start_error=1.
    """
    logger = getLogger(__name__)
    if request.method == "POST":
        form = ResearchRequestForm(request.POST)
        if form.is_valid():
            run = ResearchRun.objects.create_from_request(form.research_request)
            try:
                execute_research_run(str(run.id))
            except ClaimExecutionFailed as exc:
                logger.warning(
                    "Execution claim failed for run %s: %s", run.id, exc
                )
                return _redirect_to_report(run)
            except ExecutionError:
                return _redirect_to_report(run)
            except Exception:
                logger.exception("Unexpected error during research execution for run %s", run.id)
                return _redirect_to_report(run, start_error=True)
            return _redirect_to_report(run)
        # Invalid form - re-render with errors
        return render(request, "web/research_new.html", {"form": form})
    else:
        # GET: Prepopulate form from query parameters if present
        form = ResearchRequestForm(
            initial={
                "manufacturer_part_number": request.GET.get("mpn", ""),
                "description": request.GET.get("description", ""),
            }
        )

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

    Query flags:
    - ?start_error=1  — transient: execution could not be started
    - ?retry_error=1  — transient: retry creation/start failed
    """
    run = get_object_or_404(ResearchRun, pk=run_id)

    # Read transient flags (do not persist them)
    start_error = request.GET.get("start_error") == "1"
    retry_error = request.GET.get("retry_error") == "1"

    # --- Attempt to load and decode the snapshot ---
    decoded_result: "PriceAggregationResult | None" = None
    snapshot_error: "str | None" = None
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
        "start_error": start_error,
        "retry_error": retry_error,
    }

    return render(request, "web/research_detail.html", context)


@require_POST
def research_retry(request: HttpRequest, run_id: uuid.UUID) -> HttpResponse:
    """Retry a failed research run.

    POST-only. Creates a new ResearchRun from the failed run's request,
    executes it, and redirects to the new run's report.

    The old run remains unchanged in FAILED state.

    If retry_run itself fails (unexpected), the old run is shown with
    ?retry_error=1 so the user knows the retry was not started.

    If the new run's execution fails to start (but new_run exists), the new
    run is shown with ?start_error=1.
    """
    logger = getLogger(__name__)
    run = get_object_or_404(ResearchRun, pk=run_id)

    # Only allow retry for FAILED runs
    if run.current_state.name != "FAILED":
        return redirect("research-detail", run_id=run_id)

    try:
        new_run = retry_run(run)
    except Exception:
        logger.exception("retry_run failed for run %s", run_id)
        return _redirect_to_report(run, retry_error=True)

    try:
        execute_research_run(str(new_run.id))
    except ClaimExecutionFailed as exc:
        logger.warning("Execution claim failed for new run %s: %s", new_run.id, exc)
        return _redirect_to_report(new_run)
    except ExecutionError:
        return _redirect_to_report(new_run)
    except Exception:
        logger.exception("Unexpected error during retry execution for run %s", new_run.id)
        return _redirect_to_report(new_run, start_error=True)

    return _redirect_to_report(new_run)