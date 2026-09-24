"""Standalone intake and report views (PRODUCT-INTEL.1B, extended 4B, 4C-C, 4D-C-SEC, PILOT-RELEASE-1).

PRODUCT-INTEL.4D-C-SEC adds vendor_commercial_access_allowed boolean to the
research detail context, evaluated server-side from REMOTE_ADDR-only policy.

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

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
import logging

logger = logging.getLogger(__name__)


from product_intelligence.execution import (
    ComparableResearchExecutionError,
    ExecutionError,
    execute_comparable_research_with_default_providers,
    execute_research_run,
    replay_compact_quote_projection,
    replay_public_compact_quote_projection,
)
from product_intelligence.runs import (
    ClaimExecutionFailed,
    ComparableResearchClaimError,
    ComparableResearchTriggerError,
    retry_run,
    trigger_comparable_research,
)
from product_intelligence.runs.models import (
    AiAssistedReviewCandidate,
    ComparableResearchExecution,
    ComparableResearchState,
    PriceIntelligenceSnapshot,
    ResearchMicronAliasSnapshot,
    ResearchRun,
)

from product_intelligence.web.commercial_access import vendor_price_access_allowed

from .forms import ResearchRequestForm
from .presentation import build_report_presentation
from product_intelligence.research.aggregation import PriceAggregationResult
from product_intelligence.research.price_result_codec import (
    PriceResultCodecError,
    decode_price_aggregation_result,
)
from product_intelligence.research.comparable_result_codec import (
    ComparableResultCodecError,
    decode_comparable_result,
)
from product_intelligence.research.compact_quote import (
    CompactQuoteProjectionError,
)
from product_intelligence.research.commercial_supplement_codec import (
    SupplementCodecError,
)
from product_intelligence.research.fx_codec import FxCodecError
from product_intelligence.research.micron_alias_codec import (
    MicronAliasCodecError,
    decode_micron_alias_snapshot,
)
from .comparable_presentation import (
    build_comparable_result_presentation,
)
from .compact_quote_presentation import (
    build_compact_quote_presentation,
)
from .micron_alias_presentation import (
    build_micron_alias_presentation,
)


def healthz(request: HttpRequest) -> HttpResponse:
    """Operational health check endpoint (PILOT-RELEASE-1).

    GET /healthz returns a minimal health response:
    - HTTP 200 when the process is healthy
    - HTTP 503 when the database is unavailable

    Requirements:
    - GET only (POST returns 405)
    - No authentication (internal network-restricted pilot)
    - No research execution
    - No provider calls
    - No LLM calls
    - No sensitive configuration
    - No model/provider identifiers
    - No database record counts
    - No customer data
    - No UUIDs

    The endpoint performs a minimal database connectivity check.
    It does NOT mutate database state.
    """
    if request.method != "GET":
        return JsonResponse(
            {"status": "error", "message": "Method not allowed"},
            status=405,
        )

    # Minimal database connectivity check
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({"status": "healthy"}, status=200)
    except Exception:
        return JsonResponse(
            {"status": "unhealthy", "message": "Database unavailable"},
            status=503,
        )



def _validate_comparable_result_parent_binding(
    result: object,
    parent_mpn: str,
) -> bool:
    """Validate that a decoded comparable result is bound to the correct parent.

    Uses the frozen 2A part-number comparison primitive. Accepts only
    EXACT or NORMALIZED_EXACT matches (or empty MPN for NO_REQUESTED_MPN).

    This lives in views (read-side web integrity path), not in the
    display-only comparable_presentation module.
    """
    from product_intelligence.domain.enums import ESTABLISHED_MATCH_TYPES
    from product_intelligence.research.comparable_research_results import (
        ComparableResultKind,
    )
    from product_intelligence.research.identity import compare_part_numbers

    # NO_REQUESTED_MPN: both must be empty
    if result.kind is ComparableResultKind.NO_REQUESTED_MPN:
        return (
            not parent_mpn.strip() and not result.target_mpn.strip()
        )

    # For all other kinds, compare via frozen 2A primitive
    if not parent_mpn.strip() or not result.target_mpn.strip():
        return False

    comparison = compare_part_numbers(parent_mpn, result.target_mpn)

    # Accept only EXACT or NORMALIZED_EXACT
    if comparison.match_type not in ESTABLISHED_MATCH_TYPES:
        return False

    return True


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


def _select_comparable_child(
    run: ResearchRun,
) -> ComparableResearchExecution | None:
    """Select the one comparable child whose state should be presented.

    Deterministic precedence:
    1. Active child (PENDING / RUNNING) — newest created active child
    2. Otherwise COMPLETED child — newest completed child
    3. Otherwise FAILED child — newest failed child
    4. Otherwise None
    """
    children = ComparableResearchExecution.objects.filter(
        parent_run=run,
    )

    # 1. Active child (PENDING / RUNNING) — newest first
    active = children.filter(
        state__in=[ComparableResearchState.PENDING, ComparableResearchState.RUNNING],
    ).order_by("-created_at")
    for child in active:
        return child

    # 2. COMPLETED — newest first
    completed = children.filter(
        state=ComparableResearchState.COMPLETED,
    ).order_by("-created_at")
    for child in completed:
        return child

    # 3. FAILED — newest first
    failed = children.filter(
        state=ComparableResearchState.FAILED,
    ).order_by("-created_at")
    for child in failed:
        return child

    # 4. None
    return None


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

    # --- Attempt to load and decode the price snapshot ---
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

    # --- Transient comparable error flag ---
    comparable_start_error = request.GET.get("comparable_start_error") == "1"

    # --- PRODUCT-INTEL.4D-C: Compact quote summary (browser rendering) ---
    #
    # The security decision is made server-side BEFORE any vendor
    # supplemental artifact is read, decoded, or projected:
    #
    # * ALLOWED (vendor_commercial_access_allowed is True):
    #     the frozen 4D-C-A historical replay
    #     (replay_compact_quote_projection) builds the complete
    #     projection. It may read PriceIntelligenceSnapshot,
    #     ResearchFxSnapshot, and ResearchSupplementSnapshot, and it
    #     performs ZERO live provider/network/semantic work. Its
    #     fail-closed behavior remains binding: a malformed vendor
    #     supplemental artifact, a malformed FX artifact, or a
    #     projection authority defect produces no partial compact
    #     summary. There is NO silent fallback to public-only rows.
    # * DENIED (False):
    #     the new public-only replay
    #     (replay_public_compact_quote_projection) builds a
    #     PUBLIC_LISTING-only projection from the already
    #     provenance-validated PriceAggregationResult plus persisted
    #     FX evidence. It NEVER reads ResearchSupplementSnapshot and
    #     NEVER decodes the commercial supplement codec.
    #
    # The compact summary is constructed only when the existing price
    # snapshot decoded and passed the request-provenance check
    # (decoded_result is not None). Otherwise the existing report error
    # behavior is preserved and no compact table is rendered.
    vendor_commercial_access_allowed = vendor_price_access_allowed(request)

    compact_quote = None
    compact_quote_unavailable = False

    if decoded_result is not None:
        try:
            # PROD-FIX1: run-scoped, binding-validated human-CONFIRMED
            # indices (the same fail-closed validation that feeds the
            # Reviewed Price) may contribute Compact Quote rows for this
            # SAME run. Identity authority only — the frozen Machine Price
            # snapshot is never mutated. Zero live work: everything here is
            # persisted state already read on this GET.
            effective_confirmed_indices = confirmed_indices or None
            if vendor_commercial_access_allowed:
                replay = replay_compact_quote_projection(
                    str(run.id),
                    confirmed_assessment_indices=effective_confirmed_indices,
                )
            else:
                replay = replay_public_compact_quote_projection(
                    run=run,
                    price_result=decoded_result,
                    confirmed_assessment_indices=effective_confirmed_indices,
                )
            projection = replay.projection
            compact_quote = build_compact_quote_presentation(
                projection=projection,
                price_result=decoded_result,
                confirmed_assessment_indices=effective_confirmed_indices,
            )
        except (
            CompactQuoteProjectionError,
            PriceResultCodecError,
            SupplementCodecError,
            FxCodecError,
            ObjectDoesNotExist,
        ) as exc:
            # Expected persisted-artifact / projection failures only.
            # Programming errors (e.g. RuntimeError) propagate and are
            # never converted into "unavailable".
            logger.warning(
                "Compact quote summary unavailable for run %s: %s",
                run.id,
                exc,
            )
            compact_quote = None
            compact_quote_unavailable = True

    # --- PRODUCT-INTEL.4D-D: Micron packaging alias audit (historical) ---
    #
    # The historical report uses ONLY the persisted alias snapshot:
    # zero live Micron / search / vendor / FX / semantic / generic
    # network work. The alias section is display-only retrieval
    # provenance; its data never enters Machine Price, Reviewed Price,
    # Compact Quote, or Comparable presentation.
    #
    # Fail-closed: a malformed persisted alias artifact (codec error,
    # unsupported version, or request-provenance mismatch) renders NO
    # alias data at all — no partial rows, no live reacquisition — and
    # the existing main report remains usable. Programming defects
    # propagate (they are never converted into "unavailable").
    micron_alias = None
    micron_alias_unavailable = False

    try:
        alias_snapshot = run.research_micron_alias_snapshot
    except ResearchMicronAliasSnapshot.DoesNotExist:
        alias_snapshot = None

    if alias_snapshot is not None:
        try:
            alias_decoded = decode_micron_alias_snapshot(
                alias_snapshot.payload,
                schema_version=alias_snapshot.schema_version,
            )
        except MicronAliasCodecError as exc:
            logger.warning(
                "Micron alias snapshot unavailable for run %s: %s",
                run.id,
                exc,
            )
            micron_alias_unavailable = True
        else:
            # --- Request provenance check (mirrors the price snapshot) ---
            if alias_decoded.request != run.to_research_request():
                logger.warning(
                    "Micron alias snapshot does not match this research "
                    "request for run %s; rendering no alias data.",
                    run.id,
                )
                micron_alias_unavailable = True
            else:
                micron_alias = build_micron_alias_presentation(
                    alias_decoded,
                    decoded_result,
                )

    # --- Comparable research child + decoded result ---
    comparable_child = _select_comparable_child(run)
    comparable_presentation = None
    comparable_decode_error = None
    comparable_binding_error = False
    comparable_result = None

    if comparable_child is not None and comparable_child.state == ComparableResearchState.COMPLETED:
        try:
            comparable_result = decode_comparable_result(
                comparable_child.result_payload,
                schema_version=comparable_child.result_schema_version,
            )
        except ComparableResultCodecError:
            comparable_decode_error = (
                "The stored comparable result is invalid or in an unsupported format."
            )
        else:
            # Parent / result binding check
            if not _validate_comparable_result_parent_binding(
                comparable_result,
                run.manufacturer_part_number,
            ):
                comparable_binding_error = True
            else:
                comparable_presentation = build_comparable_result_presentation(
                    comparable_result,
                )

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
        "comparable_child": comparable_child,
        "comparable_presentation": comparable_presentation,
        "comparable_decode_error": comparable_decode_error,
        "comparable_binding_error": comparable_binding_error,
        "comparable_start_error": comparable_start_error,
        # PRODUCT-INTEL.4D-C: display-only compact quote rows assembled
        # server-side. On the DENIED branch the projection contains no
        # vendor rows at all — this context value never carries vendor
        # commercial data for an unauthorized connection.
        "compact_quote": compact_quote,
        "compact_quote_unavailable": compact_quote_unavailable,
        # PRODUCT-INTEL.4D-C-SEC: server-side network access authorization
        # for vendor commercial price visibility.  Boolean only — no raw payload,
        # no vendor rows, no sensitive metadata projected into template context.
        # Used for neutral messaging only, never as the row-hiding mechanism.
        "vendor_commercial_access_allowed": vendor_commercial_access_allowed,
        # PRODUCT-INTEL.4D-D: display-only Micron packaging alias audit,
        # built exclusively from the persisted alias snapshot (zero live
        # work). None means "no alias snapshot for this run"; the
        # unavailable flag means "persisted artifact failed closed".
        "micron_alias": micron_alias,
        "micron_alias_unavailable": micron_alias_unavailable,
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


@require_POST
def research_comparables(
    request: HttpRequest,
    run_id: uuid.UUID,
) -> HttpResponse:
    """Trigger (or re-trigger) comparable research for a completed run.

    POST-only. Redirects back to research-detail after every bounded outcome.

    Flow:
    1. Load the parent ResearchRun (404 if missing).
    2. Call frozen trigger_comparable_research(run.id).
    3. If trigger returns COMPLETED child -> redirect (idempotent).
    4. If trigger returns RUNNING child -> redirect (already executing).
    5. If trigger returns PENDING child -> execute synchronously with default
       providers -> redirect.
    6. On ComparableResearchTriggerError -> redirect with
       ?comparable_start_error=1.
    7. On ComparableResearchExecutionError or ComparableResearchClaimError
       -> redirect normally (child state is authoritative).
    8. On unexpected exception -> log + redirect with
       ?comparable_start_error=1.
    """
    logger = getLogger(__name__)
    run = get_object_or_404(ResearchRun, pk=run_id)

    # Trigger (idempotent)
    try:
        child = trigger_comparable_research(run.id)
    except ComparableResearchTriggerError:
        logger.warning(
            "Comparable research trigger failed for run %s", run.id
        )
        return redirect(
            f"/research/{run.id}?comparable_start_error=1"
        )

    # Already terminal (COMPLETED) or RUNNING
    if child.state in (
        ComparableResearchState.COMPLETED,
        ComparableResearchState.RUNNING,
    ):
        return redirect("research-detail", run_id=run.id)

    # PENDING — execute synchronously
    try:
        execute_comparable_research_with_default_providers(child.id)
    except ComparableResearchExecutionError:
        # Bounded failure: child already terminalised FAILED by 7C-B
        pass
    except ComparableResearchClaimError:
        # Race: another request claimed the child after trigger returned it.
        # Child state is authoritative; redirect normally.
        pass
    except Exception:
        logger.exception(
            "Unexpected error during comparable research execution "
            "for child %s (run %s)", child.id, run.id
        )
        return redirect(
            f"/research/{run.id}?comparable_start_error=1"
        )

    return redirect("research-detail", run_id=run_id)
