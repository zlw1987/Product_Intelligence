"""Core execution orchestration (PRODUCT-INTEL.4C-B).

This module implements the research pipeline:

    ResearchRequest  ->  claim_execution  ->  [direct]  ->  [search]  ->  fetch  ->  extract
                                                     ->  normalize  ->  match  ->  aggregate
                                                     ->  snapshot  ->  terminal state

Key invariants:
* ONE paid search call maximum per ResearchRun (claimed execution)
* Candidate-level fetch/extract failures are recoverable
* Deterministic primitives, with optional semantic assist for eligible non-accepted candidates
* Evidence-first: every conclusion traces to preserved evidence
* 4D-A: preferred-source direct acquisition may satisfy the run without any
  paid search call; fallback Serper is invoked only when direct evidence is
  insufficient (zero valid 4A price buckets)

Dependency direction:
    execution  <-  domain, research, providers, runs
    web        <-  execution (web calls execution, execution knows nothing about web)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from collections.abc import Sequence
from typing import TYPE_CHECKING

from django.db import transaction

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import EvidenceDecision, ResearchRunState
from product_intelligence.domain.evidence import (
    ExecutionDetailCode,
    ExecutionOutcome,
    ExecutionStage,
)
from product_intelligence.execution.aggregation import aggregate_prices
from product_intelligence.execution.micron_alias_authority import (
    acquire_micron_alias_eligibility,
)
from product_intelligence.execution.semantic_integration import (
    AiAssistedMatchResult,
    evaluate_semantic_matches,
)
from product_intelligence.execution.deduplication import CandidateDeduplicator
from product_intelligence.execution.evidence_writer import ExecutionEvidenceWriter
from product_intelligence.execution import matching as _matching
from product_intelligence.research.listings import ListingObservation
from product_intelligence.execution.normalization import normalize_listings
from product_intelligence.execution.search_query import (
    build_alias_expanded_search_query,
    build_search_query,
)
from product_intelligence.providers.http_page import (
    JSON_ACCEPTED_MEDIA_TYPES,
    JSON_ACCEPT_HEADER,
    HttpPageFetcher,
)
from product_intelligence.providers.page import PageFetcher, PageFetchRequest, UnsafeFetchTargetError
from product_intelligence.providers.search import SearchProvider
from product_intelligence.research.aggregation import PriceAggregationResult, aggregate_listing_prices
from product_intelligence.research.identity import compare_part_numbers
from product_intelligence.research.micron_alias_codec import encode_micron_alias_snapshot
from product_intelligence.research.micron_packaging_alias import (
    MicronAliasEligibilityResult,
)
from product_intelligence.runs import complete_execution, execution_claims
from product_intelligence.runs.execution_claims import ClaimExecutionFailed
from product_intelligence.runs.models import (
    AiAssistedReviewCandidate,
    PriceIntelligenceSnapshot,
    ResearchFxSnapshot,
    ResearchMicronAliasSnapshot,
    ResearchRun,
    ResearchSupplementSnapshot,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _UrlProcessingResult:
    """Result of processing one candidate URL through the pipeline.

    Returned by _process_candidate_url so the caller can increment
    execution statistics without querying the evidence table.

    Attributes:
        assessments: ListingIdentityAssessment objects produced.
        fetch_succeeded: True if a FETCH SUCCESS evidence record was written.
        extract_observation_count: Number of unique extracted observations
            (after exact-structural dedup, before normalization/matching drops
            any listing). A later normalization or matching failure must NOT
            retroactively erase this count.
    """

    assessments: list
    fetch_succeeded: bool
    extract_observation_count: int


@dataclass(frozen=True)
class ExecutionResult:
    """The result of a research execution.

    This is what the orchestrator returns to the caller. It includes:

    * The ResearchRun (now in terminal state)
    * The PriceIntelligenceSnapshot if successful
    * Statistics about what was processed

    ``search_result_count`` means actual SearchProvider result count.
    If Serper/SearchProvider was skipped (direct-sufficient run):
        search_result_count = 0
    """

    run: ResearchRun
    snapshot: PriceIntelligenceSnapshot | None
    search_result_count: int
    fetch_success_count: int
    extract_observation_count: int
    accepted_assessment_count: int
    verification_status: object | None
    price_buckets: int
    ai_assisted_matches: tuple["AiAssistedMatchResult", ...] = ()

    @property
    def ai_assisted_match_count(self) -> int:
        """Number of AI-assisted matches (derived, never stored independently)."""
        return len(self.ai_assisted_matches)


class ExecutionError(Exception):
    """Catastrophic execution failure.

    This is raised when orchestration cannot complete due to a top-level
    failure (not recoverable at candidate level). Examples include:

    * SearchProvider call fails as a whole
    * Aggregation contract fails
    * Price-result encoding fails
    * Final snapshot persistence fails
    * Evidence writer failure (execution-level catastrophic)

    Candidate-level failures (fetch/extract/normalize for one URL) do NOT
    raise ExecutionError - they are handled internally and the run continues.
    """

    pass


def _default_micron_authority_fetcher() -> HttpPageFetcher:
    """Lazily create the DEFAULT production Micron authority fetcher (4D-D FU1).

    The reviewed Micron 7500 family-catalog endpoint publishes
    ``application/json`` (PRE2 recorded evidence: ``Content-Type:
    application/json;charset=utf-8``), while the ordinary default
    candidate-page fetcher is HTML-only by frozen 3A design. The real
    default runtime therefore uses a JSON-configured ``HttpPageFetcher``
    for the authority fetch ONLY — an explicit, narrow media-type
    capability on the existing fetcher, not a second HTTP/provider
    abstraction. All other bounds (SSRF/redirect/credential/timeout/size)
    are identical to the default fetcher, and the default candidate
    fetcher is never reconfigured.

    Created lazily, only when authority acquisition is actually reached
    (fallback search required AND non-empty request MPN); direct-
    sufficient runs never instantiate it and never fetch the catalog.
    """
    return HttpPageFetcher(
        accepted_media_types=JSON_ACCEPTED_MEDIA_TYPES,
        accept_header=JSON_ACCEPT_HEADER,
    )


def _execute_claimed_run(
    claimed_run: ResearchRun,
    request: ResearchRequest,
    search_provider: SearchProvider | None,
    page_fetcher: PageFetcher,
    micron_authority_fetcher: PageFetcher | None = None,
) -> tuple[PriceAggregationResult, ExecutionResult]:
    """Execute research for a claimed ResearchRun.

    4D-A execution order:

    1. If request has non-empty MPN AND direct acquisition is enabled:
       obtain DirectSourceTarget(s) from evidence-backed locators.
    2. Process direct targets through the same existing pipeline:
       fetch -> extract -> normalize -> match.
    3. Check if direct assessments produce >= 1 valid frozen-4A bucket.
    4. If direct evidence is sufficient:
       skip search provider entirely (zero Serper calls).
    5. If direct evidence is insufficient:
       invoke SearchProvider once (lazy construction if not injected).
    6. Combine direct + fallback assessments for semantic integration,
       final aggregation, snapshot persistence.

    NOTE: This function does NOT create the snapshot or transition to COMPLETED.
    The caller handles atomic final publication inside a transaction.

    This function is called ONLY after claim_execution succeeds.
    Any exception raised from this function leaves the run RUNNING.
    The caller (execute_research_run) catches and terminalizes RUNNING -> FAILED.

    Parameters
    ----------
    claimed_run : ResearchRun
        The run that was successfully claimed for execution.
    request : ResearchRequest
        The canonical request from the run.
    search_provider : SearchProvider | None
        The search provider to use if fallback is needed. If None, a default
        SerperSearchProvider is constructed lazily (only when fallback fires).
    page_fetcher : PageFetcher
        The page fetcher to use for ordinary candidate pages.
    micron_authority_fetcher : PageFetcher, optional
        4D-D FU1: the fetcher used for the ONE reviewed Micron catalog
        authority fetch. ``None`` (the real default runtime) means a
        JSON-configured ``HttpPageFetcher`` is lazily created only when
        authority acquisition is actually reached. A non-None value means
        the caller explicitly injected a page fetcher, and that same
        injection governs the authority fetch (deterministic
        fake-provider execution tests).

    Returns
    -------
    tuple[PriceAggregationResult, ExecutionResult]
        - The aggregation result for encoding and snapshot creation
        - The execution result with statistics (snapshot is None at this point)

    Raises
    ------
    ExecutionError
        If orchestration fails catastrophically (not recoverable at candidate level)
    """
    evidence_writer = ExecutionEvidenceWriter(claimed_run)
    deduplicator = CandidateDeduplicator()

    # Track statistics
    fetch_success_count = 0
    extract_observation_count = 0
    total_assessments: list = []
    search_result_count = 0

    # ---------------------------------------------------------------
    # Step 1: Preferred-source direct acquisition (4D-A)
    # ---------------------------------------------------------------
    # Only when request has a non-empty MPN AND direct acquisition
    # is enabled by preferred-source configuration.
    direct_assessments: list = []
    if request.manufacturer_part_number:
        direct_assessments, fetch_success_count, extract_observation_count = (
            _try_direct_acquisition(
                claimed_run,
                request,
                page_fetcher,
                evidence_writer,
                deduplicator,
                fetch_success_count,
                extract_observation_count,
            )
        )
        total_assessments.extend(direct_assessments)

    # ---------------------------------------------------------------
    # Step 2: Determine whether fallback Serper is required.
    # ---------------------------------------------------------------
    # Use the pure frozen aggregation primitive on DIRECT assessments only.
    # If direct assessments already produce >= 1 valid 4A price bucket:
    #     Serper is NOT needed.
    # Otherwise: invoke SearchProvider.
    fallback_required = not _has_valid_4a_buckets(request, direct_assessments)

    # 4D-D: the paid-search batch (assessments originating from the ONE
    # fallback search call) and whether that call used the ESTABLISHED
    # alias-expanded query. The semantic firewall below partitions on
    # exactly these.
    search_batch_assessments: list = []
    alias_expanded = False

    # ---------------------------------------------------------------
    # Step 3: Fallback search (lazy construction)
    # ---------------------------------------------------------------
    if fallback_required:
        # -----------------------------------------------------------------
        # 4D-D: Micron packaging-alias eligibility (direct-insufficient
        # runs with a non-empty MPN only). Direct-sufficient runs perform
        # zero paid search and zero Micron authority fetch.
        #
        # * At most ONE reviewed family-catalog fetch per run.
        # * The bounded audit (ESTABLISHED or bounded non-established)
        #   is persisted BEFORE the paid search, so the retrieval
        #   decision is evidenced on held authority, not after the fact.
        # * Only an ESTABLISHED result changes the query (to the
        #   alias-expanded form); every other result keeps the ordinary
        #   query. There is never a second search.
        # * A DB/persistence failure here is NOT a bounded authority
        #   failure: it propagates to the outer catastrophic boundary.
        # -----------------------------------------------------------------
        search_query = build_search_query(request)
        if request.manufacturer_part_number:
            # 4D-D FU1: the real default runtime must not feed the
            # reviewed JSON catalog endpoint through the HTML-only default
            # candidate fetcher. When no page fetcher was explicitly
            # injected, the authority fetch uses a lazily created
            # JSON-configured HttpPageFetcher; an explicitly injected
            # fetcher remains the authority fetcher (test doubles).
            authority_fetcher = (
                micron_authority_fetcher
                if micron_authority_fetcher is not None
                else _default_micron_authority_fetcher()
            )
            alias_result = acquire_micron_alias_eligibility(
                request=request, page_fetcher=authority_fetcher
            )
            _persist_alias_snapshot(claimed_run, alias_result)
            if alias_result.is_established:
                search_query = build_alias_expanded_search_query(
                    request, alias_result.alias_relation
                )
                alias_expanded = True

        # Lazy construction: build default Serper only when actually needed.
        # A direct-sufficient run does not require SERPER_API_KEY.
        if search_provider is None:
            from product_intelligence.providers.serper import SerperSearchProvider
            search_provider = SerperSearchProvider.from_environment()

        # Call search provider (outside transaction)
        search_response = None
        try:
            search_response = search_provider.search(search_query)
        except Exception as exc:
            logger.error(
                "Search provider call failed for run %s: %s",
                claimed_run.id, exc, exc_info=True,
            )
            evidence_writer.append_execution_attempt(
                stage=ExecutionStage.SEARCH,
                outcome=ExecutionOutcome.FAILED,
                detail_code=ExecutionDetailCode.PROVIDER_ERROR,
            )
            raise ExecutionError(
                f"Search provider call failed: {exc}"
            ) from exc

        search_result_count = len(search_response.results)
        logger.info(
            "Search returned %d results for run %s",
            search_result_count, claimed_run.id,
        )

        try:
            if search_result_count == 0:
                evidence_writer.append_execution_attempt(
                    stage=ExecutionStage.SEARCH,
                    outcome=ExecutionOutcome.SUCCESS,
                    detail_code=ExecutionDetailCode.ZERO_RESULTS,
                )
            else:
                evidence_writer.append_execution_attempt(
                    stage=ExecutionStage.SEARCH,
                    outcome=ExecutionOutcome.SUCCESS,
                    detail_code=ExecutionDetailCode.OK,
                )
        except Exception as exc:
            logger.error(
                "Search evidence write failed for run %s: %s",
                claimed_run.id, exc, exc_info=True,
            )
            raise ExecutionError(
                f"Search evidence write failed: {exc}"
            ) from exc

        # Process each search result through the same pipeline
        for result in search_response.results:
            url_result = _process_candidate_url(
                url=result.source_url,
                page_fetcher=page_fetcher,
                evidence_writer=evidence_writer,
                deduplicator=deduplicator,
                request=request,
            )
            if url_result.fetch_succeeded:
                fetch_success_count += 1
            extract_observation_count += url_result.extract_observation_count
            search_batch_assessments.extend(url_result.assessments)
        total_assessments.extend(search_batch_assessments)
    else:
        # Direct evidence sufficient — no SEARCH evidence record written.
        logger.info(
            "Direct-source evidence sufficient for run %s; "
            "no search provider call required.",
            claimed_run.id,
        )

    # ---------------------------------------------------------------
    # Step 4: Semantic integration + final aggregation
    # ---------------------------------------------------------------
    # 4D-D semantic / human-review firewall:
    #
    # When the paid search used the ESTABLISHED alias-expanded query, ALL
    # non-deterministically-ACCEPTED assessments originating from THAT
    # search batch are excluded from semantic evaluation — they cannot
    # produce AI_ASSISTED_MATCH, AiAssistedReviewCandidate, or Reviewed
    # Price path membership. They REMAIN in total_assessments: frozen 4A
    # aggregation input and frozen exclusions are unchanged, and the
    # persisted PriceAggregationResult keeps them. Direct assessments
    # retain their current frozen semantic behavior; ordinary (non-alias)
    # paid-search assessments do too. Deterministically ACCEPTED
    # search-batch assessments (exact requested MPN) keep normal frozen
    # behavior (they are never semantic-eligible in the first place).
    if alias_expanded:
        semantic_input = [
            *direct_assessments,
            *(a for a in search_batch_assessments
              if a.decision is EvidenceDecision.ACCEPTED),
        ]
    else:
        semantic_input = total_assessments

    ai_assisted_results = evaluate_semantic_matches(
        request, semantic_input, evidence_writer,
    )

    aggregation_result: PriceAggregationResult
    try:
        aggregation_result = aggregate_prices(
            request, total_assessments, evidence_writer
        )
    except Exception as exc:
        logger.error(
            "Aggregation failed for run %s: %s",
            claimed_run.id, exc, exc_info=True,
        )
        raise ExecutionError(f"Aggregation failed: {exc}") from exc

    # Compute statistics
    accepted_count = sum(
        1 for a in total_assessments if a.decision.name == "ACCEPTED"
    )
    verification_status = aggregation_result.verification_status
    price_buckets = len(aggregation_result.buckets)

    return aggregation_result, ExecutionResult(
        run=claimed_run,
        snapshot=None,
        search_result_count=search_result_count,
        fetch_success_count=fetch_success_count,
        extract_observation_count=extract_observation_count,
        accepted_assessment_count=accepted_count,
        verification_status=verification_status,
        price_buckets=price_buckets,
        ai_assisted_matches=ai_assisted_results,
    )


def execute_research_run(
    run_id: str,
    *,
    search_provider: SearchProvider | None = None,
    page_fetcher: PageFetcher | None = None,
    fx_provider: object | None = None,
) -> ExecutionResult:
    """Execute research for one ResearchRun.

    This is the top-level orchestration function that:

    1. Claims the run for execution (ensures ONE paid search call max)
    2. Tries preferred-source direct acquisition (4D-A) if enabled
    3. Falls back to search provider if direct evidence is insufficient
    4. Fetches each candidate safely
    5. Extracts listing observations from pages
    6. Normalizes observations
    7. Assesses identity against the request
    8. Aggregates accepted listings by currency/condition
    9. Encodes and persists the price result
    10. Fetches FX rates if non-USD reportable currencies exist (4D-C-A)
    11. Persists FX evidence alongside price result
    12. Transitions the run to COMPLETED or FAILED

    Parameters
    ----------
    run_id : str
        The UUID of the ResearchRun to execute.
    search_provider : SearchProvider, optional
        The search provider to use. If not injected, a default
        SerperSearchProvider is constructed lazily (only when fallback fires).
        A direct-sufficient run requires no SERPER_API_KEY.
    page_fetcher : PageFetcher, optional
        The page fetcher to use for ordinary candidate pages. Defaults to
        the HTML-only ``HttpPageFetcher``. 4D-D FU1: when None, the ONE
        reviewed Micron JSON catalog authority fetch uses a separately
        JSON-configured ``HttpPageFetcher`` (lazily created); when a fetcher
        is explicitly injected, it governs the authority fetch as well.
    fx_provider : FxProvider, optional
        FX rate provider for currency conversion evidence (4D-C-A).
        If None and non-USD currencies require conversion, an EcbFxProvider
        is constructed. If all reportable prices are USD, no FX call is made
        regardless of whether an fx_provider is injected.

    Returns
    -------
    ExecutionResult
        The execution result with final state and statistics.

    Raises
    ------
    ClaimExecutionFailed
        If the run cannot be claimed (already claimed, terminal state, etc.)
    ExecutionError
        If orchestration fails catastrophically (not recoverable at candidate level)
    """
    # Lazy page fetcher default (always needed)
    if page_fetcher is None:
        # Ordinary candidate-page fetcher: the frozen HTML-only default.
        page_fetcher = HttpPageFetcher()
        # 4D-D FU1: no explicitly injected fetcher — the reviewed Micron
        # JSON authority endpoint gets its own JSON-configured fetcher,
        # created lazily inside _execute_claimed_run only when authority
        # acquisition is actually reached.
        micron_authority_fetcher: PageFetcher | None = None
    else:
        # Explicitly injected page fetcher: it governs BOTH ordinary
        # candidate pages and the Micron authority fetch, so existing
        # deterministic fake-provider execution tests remain possible.
        micron_authority_fetcher = page_fetcher
    # search_provider is intentionally NOT eagerly constructed.
    # If None, it is constructed lazily inside _execute_claimed_run
    # only when fallback search is actually required.

    # Get the run
    try:
        run = ResearchRun.objects.get(id=run_id)
    except ResearchRun.DoesNotExist:
        raise ClaimExecutionFailed(
            run_id=run_id,
            reason=ClaimExecutionFailed.REASON_RUN_NOT_FOUND,
            detail=f"no run with ID {run_id}",
        ) from None

    # Build the canonical request from the run
    request = run.to_research_request()

    # Claim execution - this is the FIRST durable operation before any provider call
    # It ensures at most ONE paid search call per run
    try:
        claimed_run = execution_claims.claim_execution(run=run)
    except ClaimExecutionFailed as exc:
        logger.warning("Execution claim failed for run %s: %s", run_id, exc)
        raise

    # ================================================================
    # ONE singular post-claim catastrophic-failure boundary
    # After successful claim, exactly ONE outer boundary owns terminalization:
    #   - Any exception from _execute_claimed_run -> terminalize -> raise ExecutionError
    #   - Any exception from atomic final publication -> terminalize -> raise ExecutionError
    #   - Inner stages and final publication ONLY propagate errors
    #   - Already-COMPLETED runs are never changed by _terminalize_run
    # ================================================================
    try:
        # Execute search/fetch/extract/normalize/match/aggregate (outside transaction)
        aggregation_result, exec_result = _execute_claimed_run(
            claimed_run,
            request,
            search_provider,
            page_fetcher,
            micron_authority_fetcher=micron_authority_fetcher,
        )

        # ================================================================
        # ATOMIC FINAL PUBLICATION
        # Complete search/fetch/extract/normalize/match/aggregate outside.
        # Now encode and atomically:
        #   1. Create PriceIntelligenceSnapshot
        #   2. Transition RUNNING -> COMPLETED
        # ================================================================
        # Encoding is done BEFORE the transaction so encoding failure is
        # caught by this outer boundary, not rolled back inside a transaction
        encoded_payload = _encode_aggregation_result(aggregation_result)

        # ================================================================
        # 4D-B: Vendor API commercial lookup (supplemental)
        # After public aggregation succeeds, but BEFORE atomic final
        # publication. At most ONE Vendor API call per run.
        # Vendor commercial evidence does NOT affect 4D-A, Price
        # Intelligence, or any existing pipeline statistics.
        # ================================================================
        supplement_payload: dict | None = None
        if request.manufacturer_part_number:
            supplement_payload = _try_vendor_commercial_lookup(
                claimed_run, request,
            )

        # ================================================================
        # 4D-C-A: FX rate evidence fetch (supplemental, display-only)
        # After public aggregation and vendor lookup, but BEFORE atomic
        # final publication. At most ONE FX provider call per run.
        # FX evidence does NOT affect Machine Price, Reviewed Price,
        # deterministic identity, or any existing pipeline statistics.
        # USD-only runs require ZERO ECB calls.
        # FX failure is NONFATAL — run still completes.
        # ================================================================
        fx_payload: dict | None = None
        fx_payload = _try_fetch_fx_rates(
            claimed_run,
            aggregation_result,
            fx_provider,
            supplemental_payload=supplement_payload,
        )

        with transaction.atomic():
            # Create the snapshot
            snapshot = PriceIntelligenceSnapshot.objects.create(
                run=claimed_run,
                schema_version=1,
                payload=encoded_payload,
            )

            # Create review candidates for AI-assisted matches (HUMAN-REVIEW)
            _create_review_candidates(
                run=claimed_run,
                assessments=aggregation_result.assessments,
                ai_assisted_matches=exec_result.ai_assisted_matches,
            )

            # 4D-B: Persist supplemental snapshot if vendor lookup was attempted
            if supplement_payload is not None:
                ResearchSupplementSnapshot.objects.create(
                    run=claimed_run,
                    schema_version=1,
                    payload=supplement_payload,
                )

                # 4D-C-A: Persist FX snapshot if FX evidence was obtained
            if fx_payload is not None:
                ResearchFxSnapshot.objects.create(
                    run=claimed_run,
                    schema_version=1,
                    payload=fx_payload,
                )

            # Commit the entire publication atomically
            # All three rows (snapshot + optional supplement + optional FX)
            # are persisted together or not at all

            # Transition to COMPLETED
            completed_run = complete_execution(
                run=claimed_run,
                target_state=ResearchRunState.COMPLETED,
            )

        # Build final result with snapshot (only reached on success)
        return ExecutionResult(
            run=completed_run,
            snapshot=snapshot,
            search_result_count=exec_result.search_result_count,
            fetch_success_count=exec_result.fetch_success_count,
            extract_observation_count=exec_result.extract_observation_count,
            accepted_assessment_count=exec_result.accepted_assessment_count,
            verification_status=exec_result.verification_status,
            price_buckets=exec_result.price_buckets,
            ai_assisted_matches=exec_result.ai_assisted_matches,
        )

    except ExecutionError:
        # ExecutionError already raised - this means an inner handler already
        # determined this is a catastrophic failure. Re-terminalize (idempotent)
        # and re-raise without wrapping again.
        _terminalize_run(claimed_run)
        raise

    except Exception as exc:
        # Any other unexpected exception from _execute_claimed_run or atomic publication
        # is catastrophic. Terminalize the still-RUNNING run to FAILED, then wrap and raise.
        # Log only bounded info (class name, run ID); never raw exception text.
        logger.error(
            "Unexpected execution failure for run %s (class=%s)",
            run_id, type(exc).__name__,
        )
        _terminalize_run(claimed_run)
        raise ExecutionError(f"Execution failed unexpectedly") from exc


def _create_review_candidates(
    run: ResearchRun,
    assessments: tuple,
    ai_assisted_matches: tuple,
) -> None:
    """Create AiAssistedReviewCandidate records for each AI-assisted MATCH.

    Each AiAssistedMatchResult.original_assessment is located by value in the
    assessments tuple. The resulting candidate record preserves the semantic
    provenance from the AiAssistedMatchResult for later human review.

    This function is called inside the atomic final publication block,
    so it participates in the same transaction as snapshot creation and
    run terminalization.

    Args:
        run: The ResearchRun being finalized.
        assessments: The ordered tuple of ListingIdentityAssessment objects
            from the aggregation result.
        ai_assisted_matches: Tuple of AiAssistedMatchResult objects produced
            by semantic evaluation during this run.
    """
    if not ai_assisted_matches:
        return

    # Build a lookup: assessment object -> index in the ordered tuple
    assessment_index: dict = {}
    for idx, assessment in enumerate(assessments):
        assessment_index[assessment] = idx

    for match_result in ai_assisted_matches:
        original = match_result.original_assessment
        semantic = match_result.semantic_result

        # Find the assessment index (fail-closed)
        idx = assessment_index.get(original)
        if idx is None:
            raise ValueError(
                f"AiAssistedMatchResult original_assessment not found in "
                f"assessments tuple for run {run.id}. "
                f"This indicates a data integrity failure."
            )

        AiAssistedReviewCandidate.objects.create(
            run=run,
            assessment_index=idx,
            source_url=original.normalized_listing.observation.source_url,
            target_mpn=semantic.target_mpn,
            target_description=semantic.target_description or "",
            candidate_title=semantic.candidate_title,
            candidate_mpn_field=semantic.candidate_mpn_field or "",
            candidate_sku=semantic.candidate_sku or "",
            candidate_specs=semantic.candidate_specs or "",
            evidence_source=semantic.evidence_source,
            semantic_confidence=(
                semantic.confidence.value
                if semantic.confidence is not None
                else ""
            ),
            semantic_reason_code=semantic.reason_code or "",
            semantic_matched_attributes=list(semantic.matched_attributes),
            semantic_conflicting_attributes=list(semantic.conflicting_attributes),
            actual_provider=semantic.actual_provider or "",
            actual_model=semantic.actual_model or "",
            prompt_version=semantic.prompt_version,
        )



def _encode_aggregation_result(result: PriceAggregationResult) -> dict:
    """Encode aggregation result to JSON-serializable dict."""
    from product_intelligence.research.price_result_codec import (
        encode_price_aggregation_result,
    )

    return encode_price_aggregation_result(result)


def _terminalize_run(run: ResearchRun) -> None:
    """Terminalize a RUNNING run to FAILED.
    
    Called by the singular post-claim catastrophic boundary when an exception
    occurs. This function is idempotent - if the run is already COMPLETED or
    FAILED, it does nothing.
    """
    try:
        # Check current state before attempting transition
        run.refresh_from_db()
        if run.current_state not in (ResearchRunState.RUNNING,):
            # Already terminal - nothing to do
            logger.info(
                "Run %s is already in state %s, skipping terminalization",
                run.id, run.current_state
            )
            return
    except Exception as exc:
        logger.critical(
            "CRITICAL: Failed to refresh run %s state: %s",
            run.id, exc, exc_info=True
        )
        raise

    try:
        complete_execution(
            run=run,
            target_state=ResearchRunState.FAILED,
        )
        logger.info("Run %s terminalized to FAILED", run.id)
    except Exception as exc:
        logger.critical(
            "CRITICAL: Failed to transition run %s to FAILED: %s",
            run.id, exc, exc_info=True,
        )
        raise


# ---------------------------------------------------------------
# 4D-A helper functions: direct acquisition, fallback, URL processing
# ---------------------------------------------------------------


def _persist_alias_snapshot(
    claimed_run: ResearchRun,
    alias_result: MicronAliasEligibilityResult,
) -> None:
    """Persist the bounded 4D-D alias-authority audit BEFORE the paid search.

    The eligibility audit (ESTABLISHED or bounded non-established) is
    written as its own pre-search durability step so the retrieval
    decision — including the ESTABLISHED authority that changes the paid
    search query — is evidenced on held authority, not reconstructed
    after the fact. The snapshot carries bounded provenance (URLs,
    retrieved_at, body SHA-256, status, policy), never the catalog body.

    A DB/persistence failure is NOT a bounded authority failure: it
    propagates to the outer catastrophic boundary (the run terminalizes
    to FAILED; the audit is wholly persisted or wholly absent).
    """
    payload = encode_micron_alias_snapshot(alias_result)
    ResearchMicronAliasSnapshot.objects.create(
        run=claimed_run,
        schema_version=1,
        payload=payload,
    )


def _try_direct_acquisition(
    claimed_run: ResearchRun,
    request: ResearchRequest,
    page_fetcher: PageFetcher,
    evidence_writer: ExecutionEvidenceWriter,
    deduplicator: CandidateDeduplicator,
    fetch_success_count: int,
    extract_observation_count: int,
) -> tuple[list, int, int]:
    """Try preferred-source direct acquisition.

    If direct acquisition is enabled by configuration AND the request
    has a non-empty MPN, obtain DirectSourceTarget(s) and process them
    through the same existing fetch/extract/normalize/match pipeline.

    Returns (assessments, fetch_success_count, extract_observation_count).
    """
    from product_intelligence.providers.preferred_source_config import (
        is_directmacro_enabled,
    )
    from product_intelligence.providers.direct_source import DirectSourceQuery
    from product_intelligence.providers.directmacro import DirectMacroLocator

    if not is_directmacro_enabled():
        return [], fetch_success_count, extract_observation_count

    query = DirectSourceQuery(
        manufacturer_part_number=request.manufacturer_part_number
    )
    locator = DirectMacroLocator()
    targets = locator.locate(query)

    if not targets:
        return [], fetch_success_count, extract_observation_count

    logger.info(
        "Direct acquisition for run %s: %d target(s) from DirectMacro",
        claimed_run.id, len(targets),
    )

    assessments: list = []
    for target in targets:
        url_result = _process_candidate_url(
            url=target.url,
            page_fetcher=page_fetcher,
            evidence_writer=evidence_writer,
            deduplicator=deduplicator,
            request=request,
        )
        if url_result.fetch_succeeded:
            fetch_success_count += 1
        extract_observation_count += url_result.extract_observation_count
        assessments.extend(url_result.assessments)

    return assessments, fetch_success_count, extract_observation_count


def _has_valid_4a_buckets(
    request: ResearchRequest,
    assessments: list,
) -> bool:
    """Check if assessments produce >= 1 valid frozen-4A price bucket.

    Uses the pure research primitive (aggregate_listing_prices) and
    does NOT write an AGGREGATE execution-evidence record.

    Contract failures (TypeError, ValueError) from the 4A primitive
    propagate to the outer catastrophic boundary. They are NOT caught
    here - they must not trigger fallback, consume a search credit,
    or be reclassified as "direct evidence insufficient".
    """
    if not assessments:
        return False
    result = aggregate_listing_prices(request, tuple(assessments))
    return len(result.buckets) >= 1


def _process_candidate_url(
    *,
    url: str,
    page_fetcher: PageFetcher,
    evidence_writer: ExecutionEvidenceWriter,
    deduplicator: CandidateDeduplicator,
    request: ResearchRequest,
) -> _UrlProcessingResult:
    """Process one candidate URL through fetch/extract/normalize/match.

    Returns a _UrlProcessingResult with assessments, fetch success flag,
    and extract observation count.
    """
    from product_intelligence.research.extraction import (
        extract_listing_observations,
    )

    fetch_succeeded = False
    extract_observation_count = 0

    # Deduplicate candidate URLs across direct + fallback
    if deduplicator.is_duplicate(url):
        evidence_writer.append_execution_attempt(
            stage=ExecutionStage.FETCH,
            outcome=ExecutionOutcome.SKIPPED,
            candidate_url=url,
            detail_code=None,
        )
        return _UrlProcessingResult(
            assessments=[],
            fetch_succeeded=False,
            extract_observation_count=0,
        )

    # Step 1: Validate URL can form a PageFetchRequest
    fetch_request = None
    try:
        fetch_request = PageFetchRequest(url=url)
    except (ValueError, TypeError) as exc:
        logger.info("PageFetchRequest refused for URL %s: %s", url, exc)
        evidence_writer.append_execution_attempt(
            stage=ExecutionStage.FETCH,
            outcome=ExecutionOutcome.BLOCKED,
            candidate_url="",
            detail_code=ExecutionDetailCode.SAFE_URL_REFUSED,
        )
        return _UrlProcessingResult(
            assessments=[],
            fetch_succeeded=False,
            extract_observation_count=0,
        )

    # Step 2: Call PageFetcher with validated request
    fetched = None
    try:
        fetched = page_fetcher.fetch(fetch_request)
    except UnsafeFetchTargetError as exc:
        logger.info("Fetch refused for URL %s: %s", url, exc)
        evidence_writer.append_execution_attempt(
            stage=ExecutionStage.FETCH,
            outcome=ExecutionOutcome.BLOCKED,
            candidate_url=url,
            detail_code=ExecutionDetailCode.SAFE_URL_REFUSED,
        )
        return _UrlProcessingResult(
            assessments=[],
            fetch_succeeded=False,
            extract_observation_count=0,
        )
    except Exception as exc:
        logger.warning("Fetch failed for URL %s: %s", url, exc, exc_info=True)
        evidence_writer.append_execution_attempt(
            stage=ExecutionStage.FETCH,
            outcome=ExecutionOutcome.FAILED,
            candidate_url=url,
            detail_code=ExecutionDetailCode.NETWORK_ERROR,
        )
        return _UrlProcessingResult(
            assessments=[],
            fetch_succeeded=False,
            extract_observation_count=0,
        )

    # Record successful fetch BEFORE extraction
    evidence_writer.append_execution_attempt(
        stage=ExecutionStage.FETCH,
        outcome=ExecutionOutcome.SUCCESS,
        candidate_url=url,
        detail_code=ExecutionDetailCode.OK,
    )
    fetch_succeeded = True

    # Extract listing observations
    try:
        listings = extract_listing_observations(
            fetched.body_text, source_url=fetched.final_url
        )
    except Exception as exc:
        logger.warning(
            "Extraction failed for URL %s: %s", url, exc, exc_info=True
        )
        evidence_writer.append_execution_attempt(
            stage=ExecutionStage.EXTRACT,
            outcome=ExecutionOutcome.FAILED,
            candidate_url=url,
            detail_code=ExecutionDetailCode.PARSE_ERROR,
        )
        return _UrlProcessingResult(
            assessments=[],
            fetch_succeeded=fetch_succeeded,
            extract_observation_count=0,
        )

    # Deduplicate exact structural duplicates
    unique_listings = _deduplicate_exact_observations(listings)
    extract_observation_count = len(unique_listings)

    # Record extract outcome
    if not unique_listings:
        evidence_writer.append_execution_attempt(
            stage=ExecutionStage.EXTRACT,
            outcome=ExecutionOutcome.EMPTY,
            candidate_url=url,
            detail_code=ExecutionDetailCode.NO_LISTING_OBSERVATIONS,
        )
    else:
        evidence_writer.append_execution_attempt(
            stage=ExecutionStage.EXTRACT,
            outcome=ExecutionOutcome.SUCCESS,
            candidate_url=url,
            detail_code=ExecutionDetailCode.OK,
        )

    # Normalize listings (handles empty unique_listings gracefully)
    try:
        normalized_listings, norm_codes = normalize_listings(
            unique_listings, evidence_writer, url
        )
    except Exception as exc:
        logger.error(
            "Normalize failed for run: %s", exc, exc_info=True
        )
        raise ExecutionError(f"Normalize failed: {exc}") from exc

    # Assess identity (handles empty normalized_listings gracefully)
    assessments, match_detail = _matching.assess_identity(
        request, normalized_listings, evidence_writer, url
    )

    return _UrlProcessingResult(
        assessments=list(assessments),
        fetch_succeeded=fetch_succeeded,
        extract_observation_count=extract_observation_count,
    )


def _deduplicate_exact_observations(
    observations: Sequence[ListingObservation],
) -> tuple[ListingObservation, ...]:
    """Deduplicate ListingObservation objects by exact value equality.

    A real page may publish the exact same Product/Offer node multiple times
    in its structured data (HTML/structured-data duplication). This is distinct
    from multiple independent market observations - it is one observation
    published multiple times.

    Passing exact structural duplicates through normalize->match->aggregate
    produces duplicate ListingIdentityAssessment values which 4A correctly
    rejects with ValueError.

    This function eliminates exact structural duplicates BEFORE they become
    independent normalization/matching evidence. The fix is at the earliest
    layer where exact structural duplication becomes known.

    Rules:
    * Stable first-occurrence wins
    * Exact dataclass value equality only (frozen dataclass __eq__)
    * No fuzzy deduplication, no semantic deduplication
    * No seller deduplication, no price deduplication
    * No cross-product inference, no cross-URL merging
    * Every genuinely distinct observation is preserved
    * Published order of retained observations is preserved

    Parameters
    ----------
    observations : Sequence[ListingObservation]
        Raw observations from one extracted page (may contain duplicates).

    Returns
    -------
    tuple[ListingObservation, ...]
        Deduplicated observations in original order.
    """
    seen: list[ListingObservation] = []
    for obs in observations:
        if obs not in seen:
            seen.append(obs)
    return tuple(seen)


# ---------------------------------------------------------------
# 4D-B: Vendor API commercial lookup (supplemental)
# ---------------------------------------------------------------


def _try_vendor_commercial_lookup(
    claimed_run: ResearchRun,
    request: ResearchRequest,
) -> dict | None:
    """Try the internal Vendor API commercial lookup (4D-B).

    Returns an encoded supplemental payload dict if the lookup was
    attempted, or None if the lookup was not attempted (no config).

    This function:
    * Makes at most ONE Vendor API network call
    * Binds returned candidates with frozen 2A (compare_part_numbers)
    * Encodes the supplemental result
    * Returns None (not attempted) if PI_VENDOR_LOOKUP_BASE_URL absent
    * Propagates programming errors (does NOT catch broad Exception)
    * Catches expected vendor failures (timeout, connection, invalid JSON)
      and encodes them as FAILED supplemental result

    Vendor commercial evidence MUST NOT affect:
    * PriceIntelligenceSnapshot
    * Machine Price
    * Reviewed Price
    * public ExecutionResult statistics
    * whether 4D-A invokes Serper
    """
    import os

    # Check if configured
    base_url = os.environ.get("PI_VENDOR_LOOKUP_BASE_URL", "").strip()
    if not base_url:
        # Not configured — no vendor call, no supplemental snapshot
        return None

    from product_intelligence.providers.commercial import (
        CommercialLookupQuery,
        LookupStatus,
    )
    from product_intelligence.providers.internal_vendor import (
        InternalVendorAdapter,
    )
    from product_intelligence.research.commercial_supplement_codec import (
        ResearchSupplementResult,
        SupplementSourceIssue,
        VendorCommercialResult,
        SupplementSourceObservation,
        encode_research_supplement_result,
    )

    # Build lookup query from the request's canonical MPN
    query = CommercialLookupQuery(mpn=request.manufacturer_part_number)

    # Execute the single Vendor API call.
    # Programming / configuration errors propagate to the outer
    # catastrophic boundary in execute_research_run. No broad catch here.
    adapter = InternalVendorAdapter()
    response = adapter.lookup(query)

    # Filter candidates through frozen 2A identity binding
    bound_observations: list[SupplementSourceObservation] = []
    bound_issues: list[SupplementSourceIssue] = []

    for candidate in response.candidates:
        assessment = compare_part_numbers(
            request.manufacturer_part_number,
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


# ---------------------------------------------------------------
# 4D-C-A: FX rate evidence fetch (supplemental, display-only)
# ---------------------------------------------------------------


def _get_required_fx_currencies(
    aggregation_result: PriceAggregationResult,
    supplemental_payload: dict | None = None,
) -> frozenset[str]:
    """Determine which non-USD currencies need FX evidence.

    Inspects BOTH:
    A. The public PriceAggregationResult buckets (frozen 4A)
    B. The 4D-B supplemental result's usable Vendor API observations

    Only USABLE vendor observations count (not source_issues, mismatches,
    malformed sections, or other non-usable vendor observations).

    Rules:
    * USD-only runs return empty set (ZERO ECB calls)
    * Each non-USD bucket currency is included (from public buckets)
    * Each non-USD currency from usable vendor observations is included
    * USD is always included so ECB formula can compute equivalents
    * Excluded listings (NO_COMPARABLE_CURRENCY etc.) do NOT count
    * Only ACCEPTED bucket currencies are reportable (public)
    * Only USABLE vendor observations are reportable (vendor)

    Returns a frozenset of currency codes that must be fetched.
    Empty frozenset means no FX call is needed.
    """
    non_usd_currencies: set[str] = set()

    # A. Include currencies from public 4A price buckets
    for bucket in aggregation_result.buckets:
        if bucket.currency_code.upper() != "USD":
            non_usd_currencies.add(bucket.currency_code.upper())

    # B. Include currencies from usable 4D-B Vendor API observations
    # Only USABLE observations count: outcome == "USABLE" with valid currency.
    #
    # BLOCKER 3 (FU2): supplemental_payload is not None only when it was
    # successfully produced by the canonical 4D-B encoder in the same execution.
    # A non-None payload that fails to decode is a programming/data-integrity
    # defect and MUST propagate — it cannot be silently converted to "no
    # vendor currencies."
    #
    # Valid empty states (no vendor currencies):
    #   supplemental_payload is None -> no vendor data
    #   supplemental_payload is valid but has zero usable observations -> no currencies
    #   supplemental_payload has only USD observations -> no non-USD currencies
    #
    # Defect states (MUST propagate):
    #   malformed dict (not valid encoded payload)
    #   codec version violation (unknown schema_version)
    #   contract violation (missing required fields)
    #   unexpected structure (malformed supplement result)
    if supplemental_payload is not None:
        from product_intelligence.research.commercial_supplement_codec import (
            decode_research_supplement_result,
        )
        # No bare except: any decode failure propagates.
        # This is an internal programming/data-integrity defect, not
        # a graceful empty-state.
        supplement_result = decode_research_supplement_result(supplemental_payload)

        for obs in supplement_result.vendor_commercial_result.observations:
            # Usable observation: has a valid currency code
            currency = obs.currency_code.strip().upper()
            if currency and currency != "USD":
                non_usd_currencies.add(currency)

    if not non_usd_currencies:
        return frozenset()

    # USD is required for the conversion formula
    # (amount_C / rate_C * rate_USD)
    required = non_usd_currencies | {"USD"}
    return frozenset(required)


def _try_fetch_fx_rates(
    claimed_run: ResearchRun,
    aggregation_result: PriceAggregationResult,
    fx_provider: object | None,
    supplemental_payload: dict | None = None,
) -> dict | None:
    """Try to fetch FX rate evidence for the completed aggregation.

    Returns an encoded FX payload dict if FX evidence was obtained,
    or None if FX evidence was not needed or not obtained.

    Rules:
    * USD-only runs: returns None immediately (zero ECB calls)
    * Non-USD currencies from public buckets: included in FX call
    * Non-USD currencies from usable vendor observations: included in FX call
    * At most ONE FX provider fetch
    * FX failure (network, parse, timeout): NONFATAL, returns None
    * Programming/contract defects: propagate (NOT silently caught)
    * FX evidence remains DISPLAY-SUPPLEMENTAL

    Parameters
    ----------
    claimed_run : ResearchRun
        The run being finalized.
    aggregation_result : PriceAggregationResult
        The completed aggregation with price buckets.
    fx_provider : FxProvider | None
        Injected FX provider, or None for default EcbFxProvider.
    supplemental_payload : dict | None
        Encoded 4D-B supplemental payload for vendor currency discovery.

    Returns
    -------
    dict | None
        Encoded FX payload for persistence, or None.
    """
    # Determine which currencies need FX rates
    # Considers both public buckets AND usable vendor observations
    required_currencies = _get_required_fx_currencies(
        aggregation_result,
        supplemental_payload=supplemental_payload,
    )

    # USD-only run — no FX call needed
    if not required_currencies:
        logger.info(
            "Run %s: all reportable prices are USD; "
            "no FX rate fetch required.",
            claimed_run.id,
        )
        return None

    # Resolve the provider
    if fx_provider is None:
        from product_intelligence.providers.fx import EcbFxProvider
        fx_provider = EcbFxProvider()

    # At most ONE FX provider fetch per run
    from product_intelligence.providers.fx import FxProviderError
    try:
        observation_set = fx_provider.fetch_rates(
            requested_currencies=required_currencies,
        )
    except FxProviderError as exc:
        # Bounded FX provider failure (FxNetworkError / FxParseError).
        # NONFATAL — FX is display-supplemental only.
        # The original source amount/currency remain authoritative.
        # USD Equivalent will be "Unavailable" for affected currencies.
        logger.info(
            "FX rate fetch failed for run %s (class=%s); "
            "USD Equivalent will be unavailable for non-USD currencies.",
            claimed_run.id, type(exc).__name__,
        )
        return None
    # NOTE: Any exception other than FxProviderError is a programming /
    # contract defect (TypeError, ValueError, AssertionError, etc.) and
    # MUST NOT be silently downgraded to a supplemental FX failure.
    # It propagates to the outer catastrophic boundary.

    # Encode the observation through the V1 FX codec
    try:
        from product_intelligence.research.fx_codec import (
            encode_fx_observation,
        )
        fx_payload = encode_fx_observation(
            provider_id=observation_set.provider_id,
            observation_date=observation_set.observation_date,
            base_currency=observation_set.base_currency,
            rates=observation_set.rates,
            retrieved_at=observation_set.retrieved_at,
        )
    except Exception as exc:
        # Codec error — programming/contract defect, NOT a provider failure.
        # Do NOT silently downgrade.
        raise

    logger.info(
        "FX rates fetched for run %s: %d currencies (%s)",
        claimed_run.id,
        len(required_currencies),
        ", ".join(sorted(required_currencies)),
    )

    return fx_payload