"""Core execution orchestration (PRODUCT-INTEL.4C-B).

This module implements the research pipeline:

    ResearchRequest  ->  claim_execution  ->  search  ->  fetch  ->  extract
                                         ->  normalize  ->  match  ->  aggregate
                                         ->  snapshot  ->  terminal state

Key invariants:
* ONE paid search call maximum per ResearchRun (claimed execution)
* Candidate-level fetch/extract failures are recoverable
* Deterministic primitives, with optional semantic assist for eligible non-accepted candidates
* Evidence-first: every conclusion traces to preserved evidence

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
from product_intelligence.domain.enums import ResearchRunState
from product_intelligence.domain.evidence import (
    ExecutionDetailCode,
    ExecutionOutcome,
    ExecutionStage,
)
from product_intelligence.execution.aggregation import aggregate_prices
from product_intelligence.execution.semantic_integration import (
    AiAssistedMatchResult,
    evaluate_semantic_matches,
)
from product_intelligence.execution.deduplication import CandidateDeduplicator
from product_intelligence.execution.evidence_writer import ExecutionEvidenceWriter
from product_intelligence.execution import matching as _matching
from product_intelligence.research.listings import ListingObservation
from product_intelligence.execution.normalization import normalize_listings
from product_intelligence.execution.search_query import build_search_query
from product_intelligence.providers.http_page import HttpPageFetcher
from product_intelligence.providers.page import PageFetcher, PageFetchRequest, UnsafeFetchTargetError
from product_intelligence.providers.search import SearchProvider
from product_intelligence.providers.serper import SerperSearchProvider
from product_intelligence.research.aggregation import PriceAggregationResult
from product_intelligence.runs import complete_execution, execution_claims
from product_intelligence.runs.execution_claims import ClaimExecutionFailed
from product_intelligence.runs.models import PriceIntelligenceSnapshot, ResearchRun

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExecutionResult:
    """The result of a research execution.

    This is what the orchestrator returns to the caller. It includes:

    * The ResearchRun (now in terminal state)
    * The final PriceIntelligenceSnapshot if successful
    * Statistics about what was processed
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


def _execute_claimed_run(
    claimed_run: ResearchRun,
    request: ResearchRequest,
    search_provider: SearchProvider,
    page_fetcher: PageFetcher,
) -> tuple[PriceAggregationResult, ExecutionResult]:
    """Execute research for a claimed ResearchRun.

    This is the post-claim orchestration function that:

    1. Builds a deterministic search query from the request
    2. Calls the search provider
    3. Deduplicates candidate URLs
    4. Fetches each candidate safely
    5. Extracts listing observations from pages
    6. Normalizes observations
    7. Assesses identity against the request
    8. Aggregates accepted listings by currency/condition

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
    search_provider : SearchProvider
        The search provider to use.
    page_fetcher : PageFetcher
        The page fetcher to use.

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

    # Build search query from request
    search_query = build_search_query(request)

    # Call search provider (outside transaction)
    search_response = None
    try:
        search_response = search_provider.search(search_query)
    except Exception as exc:
        logger.error(
            "Search provider call failed for run %s: %s", claimed_run.id, exc, exc_info=True
        )
        # Record failure evidence
        evidence_writer.append_execution_attempt(
            stage=ExecutionStage.SEARCH,
            outcome=ExecutionOutcome.FAILED,
            detail_code=ExecutionDetailCode.PROVIDER_ERROR,
        )
        raise ExecutionError(f"Search provider call failed: {exc}") from exc

    # Record search success
    search_result_count = len(search_response.results)
    logger.info("Search returned %d results for run %s", search_result_count, claimed_run.id)

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
        logger.error("Search evidence write failed for run %s: %s", claimed_run.id, exc, exc_info=True)
        raise ExecutionError(f"Search evidence write failed: {exc}") from exc

    # Process each search result
    for result in search_response.results:
        url = result.source_url

        # Deduplicate candidate URLs
        if deduplicator.is_duplicate(url):
            evidence_writer.append_execution_attempt(
                stage=ExecutionStage.FETCH,
                outcome=ExecutionOutcome.SKIPPED,
                candidate_url=url,
                detail_code=None,
            )
            continue

        # Fetch and extract (outside transaction)
        fetched = None

        # Step 1: Validate URL can form a PageFetchRequest
        # This raises ValueError for credential-bearing or structurally invalid URLs
        fetch_request = None
        try:
            fetch_request = PageFetchRequest(url=url)
        except (ValueError, TypeError) as exc:
            # URL is structurally invalid (including credential-bearing)
            # PageFetcher is NOT called
            logger.info("PageFetchRequest refused for URL %s: %s", url, exc)
            evidence_writer.append_execution_attempt(
                stage=ExecutionStage.FETCH,
                outcome=ExecutionOutcome.BLOCKED,
                candidate_url="",
                detail_code=ExecutionDetailCode.SAFE_URL_REFUSED,
            )
            continue

        # Step 2: Call PageFetcher with validated request
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
            continue
        except Exception as exc:
            logger.warning("Fetch failed for URL %s: %s", url, exc, exc_info=True)
            evidence_writer.append_execution_attempt(
                stage=ExecutionStage.FETCH,
                outcome=ExecutionOutcome.FAILED,
                candidate_url=url,
                detail_code=ExecutionDetailCode.NETWORK_ERROR,
            )
            continue

        # Record successful fetch BEFORE extraction
        evidence_writer.append_execution_attempt(
            stage=ExecutionStage.FETCH,
            outcome=ExecutionOutcome.SUCCESS,
            candidate_url=url,
            detail_code=ExecutionDetailCode.OK,
        )
        fetch_success_count += 1

        # Extract listing observations
        listings: list = []
        from product_intelligence.research.extraction import (
            extract_listing_observations,
        )

        try:
            # Use the real FetchedPage contract: body_text and final_url
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
            continue

        # Deduplicate exact structural duplicates BEFORE normalization/matching.
        # A real page may publish the exact same Product/Offer node multiple
        # times in its structured data (HTML/structured-data duplication).
        # Passing exact duplicates through normalize->match->aggregate produces
        # duplicate ListingIdentityAssessment values which 4A correctly rejects.
        # Stable first-occurrence wins; distinct observations from same page are
        # preserved.
        unique_listings = _deduplicate_exact_observations(listings)

        # Record extract outcome OUTSIDE the primitive try
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
            extract_observation_count += len(unique_listings)

        # Normalize listings (use deduplicated list)
        try:
            normalized_listings, norm_codes = normalize_listings(
                unique_listings, evidence_writer, url
            )
        except Exception as exc:
            logger.error("Normalize failed for run %s: %s", claimed_run.id, exc, exc_info=True)
            raise ExecutionError(f"Normalize failed: {exc}") from exc

        # Assess identity - exceptions propagate as catastrophic failures
        assessments, match_detail = _matching.assess_identity(
            request, normalized_listings, evidence_writer, url
        )

        total_assessments.extend(assessments)

    # Semantic integration: evaluate unresolved candidates with usable evidence
    # This runs AFTER deterministic matching and does NOT change deterministic semantics
    ai_assisted_results = evaluate_semantic_matches(
        request, total_assessments, evidence_writer,
    )

    # Aggregate accepted listings (outside transaction)
    # Evidence write for AGGREGATE is INSIDE aggregate_prices, separate from primitive
    aggregation_result: PriceAggregationResult
    try:
        aggregation_result = aggregate_prices(
            request, total_assessments, evidence_writer
        )
    except Exception as exc:
        logger.error(
            "Aggregation failed for run %s: %s", claimed_run.id, exc, exc_info=True
        )
        raise ExecutionError(f"Aggregation failed: {exc}") from exc

    # Compute statistics
    accepted_count = sum(
        1 for a in total_assessments if a.decision.name == "ACCEPTED"
    )
    verification_status = aggregation_result.verification_status
    price_buckets = len(aggregation_result.buckets)

    # Return aggregation result for atomic publication in caller
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
) -> ExecutionResult:
    """Execute research for one ResearchRun.

    This is the top-level orchestration function that:

    1. Claims the run for execution (ensures ONE paid search call max)
    2. Builds a deterministic search query from the request
    3. Calls the search provider
    4. Deduplicates candidate URLs
    5. Fetches each candidate safely
    6. Extracts listing observations from pages
    7. Normalizes observations
    8. Assesses identity against the request
    9. Aggregates accepted listings by currency/condition
    10. Encodes and persists the price result
    11. Transitions the run to COMPLETED or FAILED

    Parameters
    ----------
    run_id : str
        The UUID of the ResearchRun to execute.
    search_provider : SearchProvider, optional
        The search provider to use. Defaults to SerperSearchProvider.
    page_fetcher : PageFetcher, optional
        The page fetcher to use. Defaults to HttpPageFetcher.

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
    # Default providers for production use
    if search_provider is None:
        search_provider = SerperSearchProvider.from_environment()
    if page_fetcher is None:
        page_fetcher = HttpPageFetcher()

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

        with transaction.atomic():
            # Create the snapshot
            snapshot = PriceIntelligenceSnapshot.objects.create(
                run=claimed_run,
                schema_version=1,
                payload=encoded_payload,
            )

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
        logger.error(
            "Unexpected execution failure for run %s: %s", run_id, exc, exc_info=True
        )
        _terminalize_run(claimed_run)
        raise ExecutionError(f"Execution failed unexpectedly: {exc}") from exc


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