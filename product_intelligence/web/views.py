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
import logging

logger = logging.getLogger(__name__)


from product_intelligence.execution import ExecutionError, execute_research_run
from product_intelligence.runs import ClaimExecutionFailed, retry_run
from product_intelligence.runs.models import (
    AiAssistedReviewCandidate,
    PriceIntelligenceSnapshot,
    ResearchRun,
)

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





def _validate_confirmed_candidates(
    confirmed_candidates,
    assessments,
    logger,
) -> frozenset:
    """Validate confirmed candidates against the decoded snapshot assessments.

    Returns a frozenset of assessment indices for confirmed candidates whose
    binding_valid is True (meaning the candidate-to-assessment binding passed
    all identity checks). Silently drops invalid ones rather than failing the
    page.
    """
    valid_indices = set()
    for candidate in confirmed_candidates:
        if candidate.binding_valid:
            valid_indices.add(candidate.assessment_index)
    return frozenset(valid_indices)

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

    # --- AI-assisted review candidates ---
    candidates_qs = AiAssistedReviewCandidate.objects.filter(
        run=run
    ).order_by("assessment_index")
    raw_candidates = list(candidates_qs)

    # Build presentation objects from snapshot assessments + candidate metadata.
    # The snapshot is the authoritative source of listing evidence.
    review_candidates = []
    if decoded_result is not None:
        from .presentation import _build_review_candidate_presentations
        review_candidates = _build_review_candidate_presentations(
            raw_candidates,
            decoded_result.assessments,
            logger,
        )
    else:
        # No snapshot: build minimal presentations with binding_valid=False
        from .presentation import ReviewCandidatePresentation
        for candidate in raw_candidates:
            review_candidates.append(ReviewCandidatePresentation(
                candidate_id=str(candidate.id),
                assessment_index=candidate.assessment_index,
                binding_valid=False,
                review_state=candidate.review_state,
                reviewed_at=candidate.reviewed_at,
                source_url=None,
                source_url_safe=False,
                seller_name=None,
                normalized_price=None,
                currency_code=None,
                condition=None,
                product_title=None,
                candidate_mpn_field=candidate.candidate_mpn_field,
                candidate_sku=candidate.candidate_sku,
                semantic_confidence=candidate.semantic_confidence,
                semantic_reason_code=candidate.semantic_reason_code,
                semantic_matched_attributes=list(candidate.semantic_matched_attributes),
                semantic_conflicting_attributes=list(candidate.semantic_conflicting_attributes),
                actual_provider=candidate.actual_provider,
                actual_model=candidate.actual_model,
                prompt_version=candidate.prompt_version,
                source_url_candidate=candidate.source_url,
                target_mpn=candidate.target_mpn,
                candidate_title=candidate.candidate_title,
            ))

    confirmed_candidates = [
        c for c in review_candidates
        if c.review_state == AiAssistedReviewCandidate.REVIEW_STATE_CONFIRMED
    ]


    # Validate candidate -> snapshot binding before aggregation
    confirmed_indices = frozenset()
    if confirmed_candidates and decoded_result is not None:
        confirmed_indices = _validate_confirmed_candidates(
            confirmed_candidates,
            decoded_result.assessments,
            logger,
        )

    confirmed_count = len(confirmed_indices)

    reviewed_result = None
    if confirmed_indices and decoded_result is not None:
        from product_intelligence.research.aggregation import aggregate_reviewed_listing_prices
        try:
            reviewed_result_raw = aggregate_reviewed_listing_prices(
                request=decoded_result.request,
                assessments=decoded_result.assessments,
                confirmed_assessment_indices=confirmed_indices,
            )
            from .presentation import build_reviewed_report_presentation
            reviewed_result = build_reviewed_report_presentation(reviewed_result_raw)
        except (ValueError, TypeError) as exc:
            # Expected: corrupt/stale persisted data or invalid mapping.
            # Surface as neutral "unavailable" rather than a 500.
            logger.warning(
                "Reviewed price aggregation failed for run %s: %s",
                run.id, exc,
            )
            reviewed_result = None

    context = {
        "run": run,
        "report_presentation": report_presentation,
        "snapshot_error": snapshot_error,
        "snapshot_created_at": snapshot_created_at,
        "has_snapshot": snapshot is not None,
        "start_error": start_error,
        "retry_error": retry_error,
        "review_candidates": review_candidates,
        "reviewed_result": reviewed_result,
        "confirmed_count": confirmed_count,
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


@require_POST
def research_review(
    request: HttpRequest,
    run_id: uuid.UUID,
    candidate_id: uuid.UUID,
) -> HttpResponse:
    """Handle a human review action for an AI-assisted candidate.

    POST-only with CSRF. Accepts action as confirm, reject, or undo.

    Web-side fail-closed binding validation (Step C):
    1. run must exist and match run_id
    2. candidate must exist and belong to run
    3. snapshot must exist
    4. snapshot must decode successfully
    5. decoded.request must equal run.to_research_request()
    6. assessment_index must be in range
    7. mapped assessment must pass the same binding helper used by GET

    Only on ALL checks passing is the runs service called.
    On any failure: no mutation, redirect back to detail.
    """
    from product_intelligence.runs import (
        CandidateNotFoundError,
        CrossRunReviewError,
        InvalidCandidateError,
        ReviewConflictError,
        RunNotReviewableError,
        confirm_candidate,
        reject_candidate,
        undo_review,
    )
    from product_intelligence.web.presentation import _check_candidate_binding
    from product_intelligence.research.price_result_codec import (
        PriceResultCodecError,
        decode_price_aggregation_result,
    )

    action = request.POST.get("action", "").strip().lower()

    if action not in ("confirm", "reject", "undo"):
        return redirect("research-detail", run_id=run_id)

    # Step C-1: load run
    run = get_object_or_404(ResearchRun, pk=run_id)

    # Step C-2: load candidate
    try:
        candidate = AiAssistedReviewCandidate.objects.get(id=candidate_id)
    except AiAssistedReviewCandidate.DoesNotExist:
        logger.warning(
            "Review action %s failed: candidate %s does not exist.",
            action, candidate_id,
        )
        return redirect("research-detail", run_id=run_id)

    # Step C-3: candidate must belong to this run
    if candidate.run_id != run.id:
        logger.warning(
            "Review action %s failed: candidate %s belongs to run %s, not %s.",
            action, candidate_id, candidate.run_id, run_id,
        )
        return redirect("research-detail", run_id=run_id)

    # Step C-4: snapshot must exist
    try:
        snapshot = run.price_intelligence_snapshot
    except PriceIntelligenceSnapshot.DoesNotExist:
        logger.warning(
            "Review action %s failed for candidate %s: run %s has no snapshot.",
            action, candidate_id, run_id,
        )
        return redirect("research-detail", run_id=run_id)

    # Step C-5: snapshot must decode successfully
    try:
        decoded = decode_price_aggregation_result(
            snapshot.payload,
            schema_version=snapshot.schema_version,
        )
    except PriceResultCodecError:
        logger.warning(
            "Review action %s failed for candidate %s: snapshot decode error.",
            action, candidate_id,
        )
        return redirect("research-detail", run_id=run_id)

    # Step C-6: decoded request must match run's request
    if decoded.request != run.to_research_request():
        logger.warning(
            "Review action %s failed for candidate %s: request mismatch.",
            action, candidate_id,
        )
        return redirect("research-detail", run_id=run_id)

    # Step C-7: assessment_index must be in range
    if not (0 <= candidate.assessment_index < len(decoded.assessments)):
        logger.warning(
            "Review action %s failed for candidate %s: index %d out of range [0, %d).",
            action, candidate_id, candidate.assessment_index, len(decoded.assessments),
        )
        return redirect("research-detail", run_id=run_id)

    # Step C-8: binding helper must pass (same logic as GET presentation)
    assessment = decoded.assessments[candidate.assessment_index]
    if not _check_candidate_binding(candidate, assessment, logger):
        logger.warning(
            "Review action %s failed for candidate %s: binding validation failed.",
            action, candidate_id,
        )
        return redirect("research-detail", run_id=run_id)

    # All binding checks passed — call the runs service
    fn = {"confirm": confirm_candidate, "reject": reject_candidate, "undo": undo_review}[action]

    try:
        fn(candidate_id, run_id=run_id)
    except (
        CandidateNotFoundError,
        CrossRunReviewError,
        InvalidCandidateError,
        ReviewConflictError,
        RunNotReviewableError,
    ):
        logger.warning(
            "Review action %s failed for candidate %s on run %s",
            action, candidate_id, run_id,
        )
        return redirect("research-detail", run_id=run_id)
    except Exception:
        logger.exception(
            "Unexpected error during review action %s for candidate %s",
            action, candidate_id,
        )
        return redirect("research-detail", run_id=run_id)

    return redirect("research-detail", run_id=run_id)
