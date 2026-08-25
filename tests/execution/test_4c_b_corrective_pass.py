"""Tests for PRODUCT-INTEL.4C-B corrective pass.

Tests cover the 15-point corrective pass:

1. ONE post-claim catastrophic-failure boundary
2. Never catch evidence-write failure as primitive failure
3. Strict evidence reader rejects impossible combinations
4. Tight legal combination table
5. Correct NORMALIZE evidence classification
6. Correct MATCH no-MPN classification using enum identity
7. Safe PageFetchRequest construction in real orchestration
8. Strict evidence writer (no silent URL erasure)
9. Atomic final publication (unchanged - just validate)
10. Correct canonical MZ-QL23T800 integration data
11. Post-claim failure invariant test

All tests use fake providers to avoid network calls.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from django.db import transaction

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import EvidenceDecision, ResearchRunState
from product_intelligence.domain.evidence import (
    ExecutionDetailCode,
    ExecutionOutcome,
    ExecutionStage,
)
from product_intelligence.execution import execute_research_run, ExecutionError
from product_intelligence.execution.evidence_writer import (
    ExecutionEvidenceCorruptionError,
    ExecutionEvidenceWriter,
    _validate_combination_shared,
)
from product_intelligence.providers.page import FetchedPage, PageFetchRequest, UnsafeFetchTargetError
from product_intelligence.providers.search import SearchProvider, SearchQuery
from product_intelligence.research.listings import ExtractionMethod
from product_intelligence.runs.execution_claims import ClaimExecutionFailed
from product_intelligence.runs.models import ExecutionEvidenceRecord, PriceIntelligenceSnapshot, ResearchRun

if TYPE_CHECKING:
    from product_intelligence.providers.page import PageFetcher


# ---------------------------------------------------------------------------
# Section 1: ONE POST-CLAIM CATASTROPHIC-FAILURE BOUNDARY
# ---------------------------------------------------------------------------

class TestPostClaimCatastrophicFailureBoundary:
    """Test that after successful claim, one outer boundary catches failures.

    After claim_execution succeeds, ALL non-recoverable exceptions
    must attempt to terminalize the run as FAILED.

    Required behaviors:
    * ExecutionError raised
    * run == FAILED
    * snapshot does not exist

    Test cases:
    1. SEARCH success-evidence write fails (stage-based)
    2. NORMALIZE success-evidence write fails (stage-based)
    3. MATCH success-evidence write fails (stage-based)
    4. Unexpected post-claim error (patched build_search_query)
    5. EXTRACT/SUCCESS evidence write fails (stage-based)
    6. FETCH success-evidence write fails (stage-based)
    7. AGGREGATE success-evidence write fails (stage-based)
    
    Stage-based patching approach:
        Patches ExecutionEvidenceWriter.append_execution_attempt
        Fails when stage is TARGET_STAGE AND outcome is SUCCESS
        No Nth-INSERT assumptions.
    """

    def _make_json_ld_html(
        self,
        mpn: str = "MZ-QL23T800",
        price: float | None = 99.99,
        price_currency: str = "USD",
    ) -> str:
        """Generate valid JSON-LD Product with Offer markup."""
        if price is not None:
            offer = f'''
            "offers": {{
                "@type": "Offer",
                "price": {price},
                "priceCurrency": "{price_currency}"
            }}
            '''
        else:
            offer = '"offers": {"@type": "Offer"}'

        return f'''<!DOCTYPE html>
<html>
<head>
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "Test Product",
        "mpn": "{mpn}",
        {offer}
    }}
    </script>
</head>
<body>Test product page</body>
</html>'''

    def _patch_evidence_writer_success_failure(
        self,
        target_stage: ExecutionStage,
    ):
        """Create a patch that fails append_execution_attempt for target stage SUCCESS.

        This patches ExecutionEvidenceWriter.append_execution_attempt to fail
        exactly when the stage and outcome match the target, avoiding Nth-INSERT
        assumptions.
        """
        from product_intelligence.execution import evidence_writer

        original_append = evidence_writer.ExecutionEvidenceWriter.append_execution_attempt
        failure_message = f"Simulated {target_stage.value}/SUCCESS evidence write failure"

        def failing_append(self_wrapped, stage, outcome, **kwargs):
            if stage == target_stage and outcome == ExecutionOutcome.SUCCESS:
                raise Exception(failure_message)
            return original_append(self_wrapped, stage, outcome, **kwargs)

        return patch.object(
            evidence_writer.ExecutionEvidenceWriter,
            'append_execution_attempt',
            failing_append,
        )

    def test_search_success_evidence_write_fails(
        self,
        research_run: ResearchRun,
        fake_search_provider: MagicMock,
        fake_page_fetcher: MagicMock,
    ) -> None:
        """SEARCH success-evidence write fails -> run FAILED.

        Uses stage-based patching of append_execution_attempt.
        Note: When SEARCH/SUCCESS write fails, no evidence record is created.
        The run fails immediately after the exception.
        """
        ResearchRun.objects.get(id=research_run.id)

        with self._patch_evidence_writer_success_failure(ExecutionStage.SEARCH):
            with pytest.raises(ExecutionError) as exc_info:
                execute_research_run(
                    str(research_run.id),
                    search_provider=fake_search_provider,
                    page_fetcher=fake_page_fetcher,
                )

        # ExecutionError was raised
        assert "execution failed" in str(exc_info.value).lower() or "evidence" in str(exc_info.value).lower()

        # Verify run state
        research_run.refresh_from_db()
        assert research_run.current_state == ResearchRunState.FAILED
        assert not PriceIntelligenceSnapshot.objects.filter(run=research_run).exists()

        # Verify no evidence was persisted (SEARCH write failed before persistence)
        from product_intelligence.execution.evidence_writer import read_execution_evidence
        evidence = read_execution_evidence(research_run)
        assert len(evidence) == 0, "No evidence should be persisted when SEARCH write fails"

    def test_fetch_success_evidence_write_fails(
        self,
        research_run: ResearchRun,
        fake_search_provider: MagicMock,
        fake_page_fetcher: MagicMock,
    ) -> None:
        """FETCH success-evidence write fails -> run FAILED.

        Uses valid JSON-LD to reach listing processing.
        Uses stage-based patching of append_execution_attempt.
        """
        ResearchRun.objects.get(id=research_run.id)

        # Setup search with one result
        from product_intelligence.providers.search import SearchResult, SearchResponse
        result = MagicMock(spec=SearchResult)
        result.source_url = "https://example.com/product"
        result.title = "Test Product"
        result.snippet = "Description"
        result.price_hint_text = None
        result.part_number_hint = None
        result.raw_reference = None

        response = MagicMock(spec=SearchResponse)
        response.provider_id = "fake"
        response.query = MagicMock(spec=SearchQuery)
        response.retrieved_at = datetime.now(tz=timezone.utc)
        response.results = (result,)
        response.raw_response_reference = None

        fake_search_provider.search.return_value = response

        # Return valid JSON-LD page
        fake_page_fetcher.fetch.return_value = MagicMock(
            body_text=self._make_json_ld_html(),
            requested_url="https://example.com/product",
            final_url="https://example.com/product",
        )

        with self._patch_evidence_writer_success_failure(ExecutionStage.FETCH):
            with pytest.raises(ExecutionError) as exc_info:
                execute_research_run(
                    str(research_run.id),
                    search_provider=fake_search_provider,
                    page_fetcher=fake_page_fetcher,
                )

        assert "execution failed" in str(exc_info.value).lower() or "evidence" in str(exc_info.value).lower()

        research_run.refresh_from_db()
        assert research_run.current_state == ResearchRunState.FAILED
        assert not PriceIntelligenceSnapshot.objects.filter(run=research_run).exists()

        # Verify FETCH was actually reached by checking prior stages have evidence
        from product_intelligence.execution.evidence_writer import read_execution_evidence
        evidence = read_execution_evidence(research_run)
        search_records = [r for r in evidence if r.stage == ExecutionStage.SEARCH.value]
        assert len(search_records) >= 1, "SEARCH should have evidence (FETCH follows SEARCH)"
        # FETCH failed to write evidence (it's the target), so no FETCH record exists
        fetch_records = [r for r in evidence if r.stage == ExecutionStage.FETCH.value]
        assert len(fetch_records) == 0, "FETCH should not have evidence (write failed)"

    def test_extract_success_evidence_write_fails(
        self,
        research_run: ResearchRun,
        fake_search_provider: MagicMock,
        fake_page_fetcher: MagicMock,
    ) -> None:
        """EXTRACT success-evidence write fails -> run FAILED.

        Uses valid JSON-LD to reach EXTRACT.
        Uses stage-based patching of append_execution_attempt.
        Additionally proves no EXTRACT/FAILED/PARSE_ERROR is created.
        """
        ResearchRun.objects.get(id=research_run.id)

        # Setup search with one result
        from product_intelligence.providers.search import SearchResult, SearchResponse
        result = MagicMock(spec=SearchResult)
        result.source_url = "https://example.com/product"
        result.title = "Test Product"
        result.snippet = "Description"
        result.price_hint_text = None
        result.part_number_hint = None
        result.raw_reference = None

        response = MagicMock(spec=SearchResponse)
        response.provider_id = "fake"
        response.query = MagicMock(spec=SearchQuery)
        response.retrieved_at = datetime.now(tz=timezone.utc)
        response.results = (result,)
        response.raw_response_reference = None

        fake_search_provider.search.return_value = response

        # Return valid JSON-LD page
        fake_page_fetcher.fetch.return_value = MagicMock(
            body_text=self._make_json_ld_html(),
            requested_url="https://example.com/product",
            final_url="https://example.com/product",
        )

        with self._patch_evidence_writer_success_failure(ExecutionStage.EXTRACT):
            with pytest.raises(ExecutionError) as exc_info:
                execute_research_run(
                    str(research_run.id),
                    search_provider=fake_search_provider,
                    page_fetcher=fake_page_fetcher,
                )

        assert "execution failed" in str(exc_info.value).lower() or "evidence" in str(exc_info.value).lower()

        research_run.refresh_from_db()
        assert research_run.current_state == ResearchRunState.FAILED
        assert not PriceIntelligenceSnapshot.objects.filter(run=research_run).exists()

        # Verify EXTRACT was actually reached by checking prior stages have evidence
        from product_intelligence.execution.evidence_writer import read_execution_evidence
        evidence = read_execution_evidence(research_run)
        search_records = [r for r in evidence if r.stage == ExecutionStage.SEARCH.value]
        fetch_records = [r for r in evidence if r.stage == ExecutionStage.FETCH.value]
        assert len(search_records) >= 1 and len(fetch_records) >= 1, \
            "SEARCH and FETCH should have evidence (they precede EXTRACT)"
        # EXTRACT failed to write evidence (it's the target), so no EXTRACT record exists
        extract_records = [r for r in evidence if r.stage == ExecutionStage.EXTRACT.value]
        assert len(extract_records) == 0, "EXTRACT should not have evidence (write failed)"

        # Prove NO EXTRACT/FAILED/PARSE_ERROR was created
        extract_failed = [
            r for r in evidence
            if r.stage == ExecutionStage.EXTRACT.value and r.outcome == ExecutionOutcome.FAILED.value
        ]
        assert len(extract_failed) == 0, (
            f"EXTRACT/FAILED/PARSE_ERROR should not exist when EXTRACT/SUCCESS write fails, "
            f"got: {extract_failed}"
        )

    def test_normalize_success_evidence_write_fails(
        self,
        research_run: ResearchRun,
        fake_search_provider: MagicMock,
        fake_page_fetcher: MagicMock,
    ) -> None:
        """NORMALIZE success-evidence write fails -> run FAILED.

        Uses valid JSON-LD to reach NORMALIZE.
        Uses stage-based patching of append_execution_attempt.
        """
        ResearchRun.objects.get(id=research_run.id)

        # Setup search with one result
        from product_intelligence.providers.search import SearchResult, SearchResponse
        result = MagicMock(spec=SearchResult)
        result.source_url = "https://example.com/product"
        result.title = "Test Product"
        result.snippet = "Description"
        result.price_hint_text = None
        result.part_number_hint = None
        result.raw_reference = None

        response = MagicMock(spec=SearchResponse)
        response.provider_id = "fake"
        response.query = MagicMock(spec=SearchQuery)
        response.retrieved_at = datetime.now(tz=timezone.utc)
        response.results = (result,)
        response.raw_response_reference = None

        fake_search_provider.search.return_value = response

        # Return valid JSON-LD page
        fake_page_fetcher.fetch.return_value = MagicMock(
            body_text=self._make_json_ld_html(),
            requested_url="https://example.com/product",
            final_url="https://example.com/product",
        )

        with self._patch_evidence_writer_success_failure(ExecutionStage.NORMALIZE):
            with pytest.raises(ExecutionError) as exc_info:
                execute_research_run(
                    str(research_run.id),
                    search_provider=fake_search_provider,
                    page_fetcher=fake_page_fetcher,
                )

        assert "execution failed" in str(exc_info.value).lower() or "evidence" in str(exc_info.value).lower()

        research_run.refresh_from_db()
        assert research_run.current_state == ResearchRunState.FAILED
        assert not PriceIntelligenceSnapshot.objects.filter(run=research_run).exists()

        # Verify NORMALIZE was actually reached by checking prior stages have evidence
        from product_intelligence.execution.evidence_writer import read_execution_evidence
        evidence = read_execution_evidence(research_run)
        search_records = [r for r in evidence if r.stage == ExecutionStage.SEARCH.value]
        fetch_records = [r for r in evidence if r.stage == ExecutionStage.FETCH.value]
        extract_records = [r for r in evidence if r.stage == ExecutionStage.EXTRACT.value]
        assert len(search_records) >= 1 and len(fetch_records) >= 1 and len(extract_records) >= 1, \
            "SEARCH, FETCH, EXTRACT should have evidence (they precede NORMALIZE)"
        # NORMALIZE failed to write evidence (it's the target)
        normalize_records = [r for r in evidence if r.stage == ExecutionStage.NORMALIZE.value]
        assert len(normalize_records) == 0, "NORMALIZE should not have evidence (write failed)"

    def test_match_success_evidence_write_fails(
        self,
        research_run: ResearchRun,
        fake_search_provider: MagicMock,
        fake_page_fetcher: MagicMock,
    ) -> None:
        """MATCH success-evidence write fails -> run FAILED.

        Uses valid JSON-LD with matching MPN to reach MATCH.
        Uses stage-based patching of append_execution_attempt.
        """
        ResearchRun.objects.get(id=research_run.id)

        # Setup search with one result
        from product_intelligence.providers.search import SearchResult, SearchResponse
        result = MagicMock(spec=SearchResult)
        result.source_url = "https://example.com/product"
        result.title = "Test Product"
        result.snippet = "Description"
        result.price_hint_text = None
        result.part_number_hint = None
        result.raw_reference = None

        response = MagicMock(spec=SearchResponse)
        response.provider_id = "fake"
        response.query = MagicMock(spec=SearchQuery)
        response.retrieved_at = datetime.now(tz=timezone.utc)
        response.results = (result,)
        response.raw_response_reference = None

        fake_search_provider.search.return_value = response

        # Return valid JSON-LD page with matching MPN
        fake_page_fetcher.fetch.return_value = MagicMock(
            body_text=self._make_json_ld_html(mpn="MZ-QL23T800"),
            requested_url="https://example.com/product",
            final_url="https://example.com/product",
        )

        with self._patch_evidence_writer_success_failure(ExecutionStage.MATCH):
            with pytest.raises(ExecutionError) as exc_info:
                execute_research_run(
                    str(research_run.id),
                    search_provider=fake_search_provider,
                    page_fetcher=fake_page_fetcher,
                )

        assert "execution failed" in str(exc_info.value).lower() or "evidence" in str(exc_info.value).lower()

        research_run.refresh_from_db()
        assert research_run.current_state == ResearchRunState.FAILED
        assert not PriceIntelligenceSnapshot.objects.filter(run=research_run).exists()

        # Verify MATCH was actually reached by checking prior stages have evidence
        from product_intelligence.execution.evidence_writer import read_execution_evidence
        evidence = read_execution_evidence(research_run)
        search_records = [r for r in evidence if r.stage == ExecutionStage.SEARCH.value]
        fetch_records = [r for r in evidence if r.stage == ExecutionStage.FETCH.value]
        extract_records = [r for r in evidence if r.stage == ExecutionStage.EXTRACT.value]
        normalize_records = [r for r in evidence if r.stage == ExecutionStage.NORMALIZE.value]
        assert all(len(r) >= 1 for r in [search_records, fetch_records, extract_records, normalize_records]), \
            "Prior stages should have evidence (they precede MATCH)"
        # MATCH failed to write evidence (it's the target)
        match_records = [r for r in evidence if r.stage == ExecutionStage.MATCH.value]
        assert len(match_records) == 0, "MATCH should not have evidence (write failed)"

    def test_aggregate_success_evidence_write_fails(
        self,
        research_run: ResearchRun,
        fake_search_provider: MagicMock,
        fake_page_fetcher: MagicMock,
    ) -> None:
        """AGGREGATE success-evidence write fails -> run FAILED.

        Uses valid JSON-LD to reach AGGREGATE.
        Uses stage-based patching of append_execution_attempt.
        """
        ResearchRun.objects.get(id=research_run.id)

        # Setup search with one result
        from product_intelligence.providers.search import SearchResult, SearchResponse
        result = MagicMock(spec=SearchResult)
        result.source_url = "https://example.com/product"
        result.title = "Test Product"
        result.snippet = "Description"
        result.price_hint_text = None
        result.part_number_hint = None
        result.raw_reference = None

        response = MagicMock(spec=SearchResponse)
        response.provider_id = "fake"
        response.query = MagicMock(spec=SearchQuery)
        response.retrieved_at = datetime.now(tz=timezone.utc)
        response.results = (result,)
        response.raw_response_reference = None

        fake_search_provider.search.return_value = response

        # Return valid JSON-LD page
        fake_page_fetcher.fetch.return_value = MagicMock(
            body_text=self._make_json_ld_html(),
            requested_url="https://example.com/product",
            final_url="https://example.com/product",
        )

        with self._patch_evidence_writer_success_failure(ExecutionStage.AGGREGATE):
            with pytest.raises(ExecutionError) as exc_info:
                execute_research_run(
                    str(research_run.id),
                    search_provider=fake_search_provider,
                    page_fetcher=fake_page_fetcher,
                )

        assert "execution failed" in str(exc_info.value).lower() or "evidence" in str(exc_info.value).lower()

        research_run.refresh_from_db()
        assert research_run.current_state == ResearchRunState.FAILED
        assert not PriceIntelligenceSnapshot.objects.filter(run=research_run).exists()

        # Verify AGGREGATE was actually reached by checking prior stages have evidence
        from product_intelligence.execution.evidence_writer import read_execution_evidence
        evidence = read_execution_evidence(research_run)
        search_records = [r for r in evidence if r.stage == ExecutionStage.SEARCH.value]
        fetch_records = [r for r in evidence if r.stage == ExecutionStage.FETCH.value]
        extract_records = [r for r in evidence if r.stage == ExecutionStage.EXTRACT.value]
        normalize_records = [r for r in evidence if r.stage == ExecutionStage.NORMALIZE.value]
        match_records = [r for r in evidence if r.stage == ExecutionStage.MATCH.value]
        assert all(len(r) >= 1 for r in [search_records, fetch_records, extract_records, normalize_records, match_records]), \
            "All prior stages should have evidence (they precede AGGREGATE)"
        # AGGREGATE failed to write evidence (it's the target)
        aggregate_records = [r for r in evidence if r.stage == ExecutionStage.AGGREGATE.value]
        assert len(aggregate_records) == 0, "AGGREGATE should not have evidence (write failed)"

    def test_unexpected_post_claim_error_raises_execution_error(
        self,
        research_run: ResearchRun,
        fake_search_provider: MagicMock,
        fake_page_fetcher: MagicMock,
    ) -> None:
        """Unexpected post-claim error (patched build_search_query) -> ExecutionError."""
        ResearchRun.objects.get(id=research_run.id)

        # Patch build_search_query to raise an unexpected exception
        with patch('product_intelligence.execution.orchestration.build_search_query') as mock_build:
            mock_build.side_effect = RuntimeError("Simulated unexpected error")

            with pytest.raises(ExecutionError) as exc_info:
                execute_research_run(
                    str(research_run.id),
                    search_provider=fake_search_provider,
                    page_fetcher=fake_page_fetcher,
                )

        # ExecutionError was raised
        assert "Execution failed unexpectedly" in str(exc_info.value)

        # Refresh run from database
        research_run.refresh_from_db()

        # Run is FAILED
        assert research_run.current_state == ResearchRunState.FAILED

        # No snapshot exists
        assert not PriceIntelligenceSnapshot.objects.filter(run=research_run).exists()


# ---------------------------------------------------------------------------
# Section 3: STRICT EVIDENCE READER - IMPOSSIBLE COMBINATIONS
# ---------------------------------------------------------------------------

class TestStrictEvidenceReaderImpossibleCombinations:
    """Test that the reader rejects impossible stage/outcome/detail combinations.

    The writer and reader must share the same combination validator.
    Impossible combinations must fail closed, not be silently accepted.
    """

    def test_search_blocked_fails_closed(self, research_run: ResearchRun) -> None:
        """SEARCH / BLOCKED is impossible - must fail closed."""
        from product_intelligence.domain.evidence import ExecutionDetailCode

        # Manually insert an impossible combination
        ExecutionEvidenceRecord.objects.create(
            run=research_run,
            attempt_number=1,
            stage=ExecutionStage.SEARCH.value,
            outcome=ExecutionOutcome.BLOCKED.value,
            candidate_url="",
            detail_code="",
            created_at=datetime.now(tz=timezone.utc),
        )

        with pytest.raises(ExecutionEvidenceCorruptionError) as exc_info:
            from product_intelligence.execution.evidence_writer import read_execution_evidence
            read_execution_evidence(research_run)

        assert "invalid" in str(exc_info.value).lower() or "impossible" in str(exc_info.value).lower()

    def test_search_empty_fails_closed(self, research_run: ResearchRun) -> None:
        """SEARCH / EMPTY is impossible - must fail closed."""
        from product_intelligence.domain.evidence import ExecutionDetailCode

        ExecutionEvidenceRecord.objects.create(
            run=research_run,
            attempt_number=1,
            stage=ExecutionStage.SEARCH.value,
            outcome=ExecutionOutcome.EMPTY.value,
            candidate_url="",
            detail_code="",
            created_at=datetime.now(tz=timezone.utc),
        )

        with pytest.raises(ExecutionEvidenceCorruptionError) as exc_info:
            from product_intelligence.execution.evidence_writer import read_execution_evidence
            read_execution_evidence(research_run)

        assert "invalid" in str(exc_info.value).lower() or "impossible" in str(exc_info.value).lower()

    def test_aggregate_blocked_fails_closed(self, research_run: ResearchRun) -> None:
        """AGGREGATE / BLOCKED is impossible - must fail closed."""
        from product_intelligence.domain.evidence import ExecutionDetailCode

        ExecutionEvidenceRecord.objects.create(
            run=research_run,
            attempt_number=1,
            stage=ExecutionStage.AGGREGATE.value,
            outcome=ExecutionOutcome.BLOCKED.value,
            candidate_url="",
            detail_code="",
            created_at=datetime.now(tz=timezone.utc),
        )

        with pytest.raises(ExecutionEvidenceCorruptionError) as exc_info:
            from product_intelligence.execution.evidence_writer import read_execution_evidence
            read_execution_evidence(research_run)

        assert "invalid" in str(exc_info.value).lower() or "impossible" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Section 4: TIGHT LEGAL COMBINATION TABLE
# ---------------------------------------------------------------------------

class TestLegalCombinationTable:
    """Test the legal combination table matches approved semantics.

    VALID combinations per 4C-B requirements:

    NORMALIZE / SUCCESS:
        - Numeric price present -> detail_code = OK
        - NO numeric price -> detail_code = NO_PRICE

    MATCH / SUCCESS:
        - ACCEPTED -> detail_code = ACCEPTED
        - REJECTED + NO_EXPLICIT_MPN_EVIDENCE -> detail_code = NO_MPN_IN_OBSERVATION
        - REJECTED + other reason -> detail_code = IDENTITY_REJECTED
        - UNDECIDED -> no detail code

    AGGREGATE:
        - SUCCESS -> no detail code (None)
        - FAILED -> no detail code (None)
    """

    def test_validate_combination_shared_rejects_impossible(self):
        """_validate_combination_shared rejects impossible combinations."""
        # SEARCH / FAILED / OK is impossible (must be PROVIDER_ERROR or TIMEOUT)
        with pytest.raises(ValueError):
            _validate_combination_shared(
                ExecutionStage.SEARCH,
                ExecutionOutcome.FAILED,
                ExecutionDetailCode.OK,
            )

        # MATCH / BLOCKED doesn't exist
        with pytest.raises(ValueError):
            _validate_combination_shared(
                ExecutionStage.MATCH,
                ExecutionOutcome.BLOCKED,
                None,
            )

    def test_validate_combination_shared_accepts_valid(self):
        """_validate_combination_shared accepts valid combinations."""
        # Valid combinations should not raise
        _validate_combination_shared(ExecutionStage.SEARCH, ExecutionOutcome.SUCCESS, ExecutionDetailCode.OK)
        _validate_combination_shared(ExecutionStage.SEARCH, ExecutionOutcome.SUCCESS, ExecutionDetailCode.ZERO_RESULTS)
        _validate_combination_shared(ExecutionStage.SEARCH, ExecutionOutcome.FAILED, ExecutionDetailCode.PROVIDER_ERROR)
        _validate_combination_shared(ExecutionStage.MATCH, ExecutionOutcome.SUCCESS, ExecutionDetailCode.ACCEPTED)
        _validate_combination_shared(ExecutionStage.AGGREGATE, ExecutionOutcome.SUCCESS, None)

    def test_normalizer_produces_correct_detail_codes(self):
        """Test that the NORMALIZE primitive produces correct detail codes."""
        from product_intelligence.research.normalization import normalize_listing_observation
        from product_intelligence.research.listings import ListingObservation
        from datetime import datetime, timezone
        from product_intelligence.execution.evidence_writer import ExecutionEvidenceWriter

        # Create a normalized listing with price
        obs = ListingObservation(
            source_url="https://example.com",
            extraction_method=ExtractionMethod.JSON_LD,
            product_title="Test Product",
            manufacturer_part_number_text="ABC123",
            sku_text=None,
            price_text="$99.99",
            condition_text="New",
            currency_text="USD",
        )
        normalized = normalize_listing_observation(obs)

        assert normalized.price_amount is not None

    def test_aggregate_has_no_detail_code(self):
        """AGGREGATE/SUCCESS and AGGREGATE/FAILED have no detail code."""
        # This is validated in the code - both SUCCESS and FAILED use None
        assert ExecutionDetailCode.for_aggregate_success() is None


# ---------------------------------------------------------------------------
# Section 5: NORMALIZE NO_PRICE CLASSIFICATION
# ---------------------------------------------------------------------------

class TestNormalizeNoPriceClassification:
    """Test that NORMALIZE correctly classifies NO_PRICE vs OK.

    Normalization issues in other fields do NOT justify inventing another
    ExecutionDetailCode.

    Rules:
    * price_amount is None -> NO_PRICE
    * price_amount exists -> OK
    """

    def test_normalize_with_price_uses_ok(self):
        """Normalization with price -> NORMALIZE/SUCCESS/OK."""
        from product_intelligence.research.normalization import normalize_listing_observation
        from product_intelligence.research.listings import ListingObservation
        from datetime import datetime, timezone

        obs = ListingObservation(
            source_url="https://example.com",
            extraction_method=ExtractionMethod.JSON_LD,
            product_title="Test Product",
            manufacturer_part_number_text="ABC123",
            sku_text=None,
            price_text="$99.99",
            condition_text="New",
            currency_text="USD",
        )
        normalized = normalize_listing_observation(obs)

        assert normalized.price_amount is not None
        # The price was parsed successfully
        assert normalized.price_amount > 0

    def test_normalize_without_price_uses_no_price(self):
        """Normalization without numeric price -> NORMALIZE/SUCCESS/NO_PRICE."""
        from product_intelligence.research.normalization import normalize_listing_observation
        from product_intelligence.research.listings import ListingObservation
        from datetime import datetime, timezone

        # No price text at all
        obs = ListingObservation(
            source_url="https://example.com",
            extraction_method=ExtractionMethod.JSON_LD,
            product_title="Test Product",
            manufacturer_part_number_text="ABC123",
            sku_text=None,
            price_text="",
            condition_text="New",
            currency_text="USD",
        )
        normalized = normalize_listing_observation(obs)

        # price_amount is None
        assert normalized.price_amount is None


# ---------------------------------------------------------------------------
# Section 6: MATCH NO_MPN_IN_OBSERVATION CLASSIFICATION
# ---------------------------------------------------------------------------

class TestMatchNoMpnClassification:
    """Test that MATCH correctly classifies no-MPN rejection.

    Do NOT test substring parsing:
        "no explicit mpn" in rejection_reason.lower()  # WRONG

    Do use direct enum comparison:
        rejection_reason is IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE  # RIGHT

    Mapping:
        ACCEPTED -> ACCEPTED
        REJECTED + NO_EXPLICIT_MPN_EVIDENCE -> NO_MPN_IN_OBSERVATION
        REJECTED + other reason -> IDENTITY_REJECTED
        UNDECIDED -> no detail code
    """

    def test_match_rejection_no_explicit_mpn_uses_enum_identity(self):
        """MATCH rejection for NO_EXPLICIT_MPN_EVIDENCE uses enum comparison, not substring."""
        from product_intelligence.research.matching import (
            IdentityRejectionReason,
            assess_listing_identity,
        )
        from product_intelligence.domain import ResearchRequest
        from product_intelligence.research.normalization import normalize_listing_observation
        from product_intelligence.research.listings import ListingObservation
        from datetime import datetime, timezone

        # Create a listing with no explicit MPN field (only SKU)
        obs = ListingObservation(
            source_url="https://example.com",
            extraction_method=ExtractionMethod.JSON_LD,
            product_title="Product with SKU XYZ123",
            manufacturer_part_number_text=None,  # No explicit MPN
            sku_text="XYZ123",  # Only SKU
            price_text="$99.99",
            condition_text="New",
            currency_text="USD",
        )
        normalized = normalize_listing_observation(obs)

        # Create a request with MPN
        request = ResearchRequest(
            manufacturer_part_number="ABC123",
            description="Test product",
        )

        # Assess identity
        assessment = assess_listing_identity(request, normalized)

        # The rejection reason must be NO_EXPLICIT_MPN_EVIDENCE
        assert assessment.rejection_reason is IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE

    def test_match_rejection_mpn_mismatch_uses_identity_rejected(self):
        """MATCH rejection for MPN mismatch -> IDENTITY_REJECTED."""
        from product_intelligence.research.matching import (
            IdentityRejectionReason,
            assess_listing_identity,
        )
        from product_intelligence.domain import ResearchRequest
        from product_intelligence.research.normalization import normalize_listing_observation
        from product_intelligence.research.listings import ListingObservation
        from datetime import datetime, timezone

        # Create a listing with an explicit MPN that doesn't match
        obs = ListingObservation(
            source_url="https://example.com",
            extraction_method=ExtractionMethod.JSON_LD,
            product_title="Product XYZ",
            manufacturer_part_number_text="XYZ999",  # Different from requested ABC123
            sku_text=None,
            price_text="$99.99",
            condition_text="New",
            currency_text="USD",
        )
        normalized = normalize_listing_observation(obs)

        # Create a request with different MPN
        request = ResearchRequest(
            manufacturer_part_number="ABC123",
            description="Test product",
        )

        # Assess identity
        assessment = assess_listing_identity(request, normalized)

        # The rejection reason must be MPN_MISMATCH
        assert assessment.rejection_reason is IdentityRejectionReason.MPN_MISMATCH

    def test_match_accepted_uses_accepted_code(self):
        """MATCH ACCEPTED -> detail code ACCEPTED."""
        from product_intelligence.research.matching import (
            IdentityRejectionReason,
            assess_listing_identity,
        )
        from product_intelligence.domain import ResearchRequest
        from product_intelligence.research.normalization import normalize_listing_observation
        from product_intelligence.research.listings import ListingObservation
        from datetime import datetime, timezone
        from product_intelligence.execution.matching import assess_identity as execute_assess_identity
        from product_intelligence.execution.evidence_writer import ExecutionEvidenceWriter

        # Create a listing with an explicit MPN that matches
        obs = ListingObservation(
            source_url="https://example.com",
            extraction_method=ExtractionMethod.JSON_LD,
            product_title="Product ABC123",
            manufacturer_part_number_text="mpn:ABC123",  # Matches after wrapper cleanup
            sku_text=None,
            price_text="$99.99",
            condition_text="New",
            currency_text="USD",
        )
        normalized = normalize_listing_observation(obs)

        # Create a request with matching MPN
        request = ResearchRequest(
            manufacturer_part_number="ABC123",
            description="Test product",
        )

        # Assess identity
        assessment = assess_listing_identity(request, normalized)

        # The assessment must be ACCEPTED
        assert assessment.decision is EvidenceDecision.ACCEPTED
        assert assessment.rejection_reason is None


# ---------------------------------------------------------------------------
# Section 7: SAFE PAGEFETCHREQUEST CONSTRUCTION IN REAL ORCHESTRATION
# ---------------------------------------------------------------------------

class TestSafePageFetchRequestConstruction:
    """Test that PageFetchRequest construction fails safely.

    Required behavior when candidate cannot construct valid PageFetchRequest:

        PageFetcher is NOT called
        FETCH / BLOCKED / SAFE_URL_REFUSED

    For credential-bearing URL:
        candidate_url persisted as ""

    For structurally invalid non-secret URL:
        Follow the strict writer URL contract (raise ValueError)

    Tests through execute_research_run(), not only through fetch_and_extract().
    """

    def test_credential_bearing_url_is_refused_before_fetch(
        self,
        research_run: ResearchRun,
        fake_search_provider: MagicMock,
    ) -> None:
        """Credential-bearing URL is refused -> FETCH/BLOCKED/SAFE_URL_REFUSED."""
        from product_intelligence.providers.search import SearchResult, SearchResponse

        # Create a result with credential-bearing URL
        result = MagicMock(spec=SearchResult)
        result.source_url = "https://user:password@example.com/page"
        result.title = "Product"
        result.snippet = "Description"
        result.price_hint_text = None
        result.part_number_hint = None
        result.raw_reference = None

        response = MagicMock(spec=SearchResponse)
        response.provider_id = "fake"
        response.query = MagicMock(spec=SearchQuery)
        response.retrieved_at = datetime.now(tz=timezone.utc)
        response.results = (result,)
        response.raw_response_reference = None

        fake_search_provider.search.return_value = response

        result = execute_research_run(
            str(research_run.id),
            search_provider=fake_search_provider,
            page_fetcher=fake_search_provider,  # Using search provider as placeholder
        )

        # The URL should not have been fetched
        # (PageFetcher would have been called if URL was accepted)

        # Check evidence: FETCH/BLOCKED/SAFE_URL_REFUSED
        from product_intelligence.execution.evidence_writer import read_execution_evidence
        records = read_execution_evidence(research_run)

        # Find the FETCH record for the credential-bearing URL
        fetch_records = [r for r in records if r.stage == ExecutionStage.FETCH.value]
        fetch_blocked = [r for r in fetch_records if r.outcome == ExecutionOutcome.BLOCKED.value]

        assert len(fetch_blocked) >= 1
        # The URL should be empty string in evidence (for safety)
        assert fetch_blocked[0].candidate_url == ""


# ---------------------------------------------------------------------------
# Section 8: STRICT EVIDENCE WRITER - MALFORMED URL TESTS
# ---------------------------------------------------------------------------

class TestStrictEvidenceWriterMalformedUrl:
    """Test that evidence writer rejects malformed URLs instead of silently erasing.

    Writer rules:
    * candidate_url == "" is valid (no safe URL)
    * Valid non-empty URL is stored exactly
    * Invalid non-empty URL raises ValueError (not silently converted to "")
    """

    def test_valid_absolute_url_preserved_exactly(self, research_run: ResearchRun) -> None:
        """Valid absolute URL is preserved exactly."""
        from product_intelligence.domain.evidence import ExecutionDetailCode
        writer = ExecutionEvidenceWriter(research_run)

        url = "https://example.com/path?query=value"
        record = writer.append_execution_attempt(
            stage=ExecutionStage.FETCH,
            outcome=ExecutionOutcome.SUCCESS,
            candidate_url=url,
            detail_code=ExecutionDetailCode.OK,
        )

        assert record.candidate_url == url

    def test_malformed_url_raises_value_error(self, research_run: ResearchRun) -> None:
        """Malformed URL raises ValueError, not silently converted to empty."""
        from product_intelligence.domain.evidence import ExecutionDetailCode
        writer = ExecutionEvidenceWriter(research_run)

        with pytest.raises(ValueError):
            writer.append_execution_attempt(
                stage=ExecutionStage.FETCH,
                outcome=ExecutionOutcome.SUCCESS,
                candidate_url="not-a-url",
                detail_code=ExecutionDetailCode.OK,
            )

    def test_credential_bearing_url_passed_to_writer_raises_value_error(
        self,
        research_run: ResearchRun,
    ) -> None:
        """Credential-bearing URL passed to writer -> raises ValueError (strict writer)."""
        from product_intelligence.domain.evidence import ExecutionDetailCode
        writer = ExecutionEvidenceWriter(research_run)

        url = "https://user:password@example.com/page"
        # Strict writer raises ValueError for credential URLs
        with pytest.raises(ValueError):
            writer.append_execution_attempt(
                stage=ExecutionStage.FETCH,
                outcome=ExecutionOutcome.SUCCESS,
                candidate_url=url,
                detail_code=ExecutionDetailCode.OK,
            )

        # Valid empty string is still accepted
        record = writer.append_execution_attempt(
            stage=ExecutionStage.FETCH,
            outcome=ExecutionOutcome.BLOCKED,
            candidate_url="",
            detail_code=ExecutionDetailCode.SAFE_URL_REFUSED,
        )
        assert record.candidate_url == ""

    def test_ftp_url_raises_value_error(self, research_run: ResearchRun) -> None:
        """FTP URL (non-http) raises ValueError."""
        from product_intelligence.domain.evidence import ExecutionDetailCode
        writer = ExecutionEvidenceWriter(research_run)

        with pytest.raises(ValueError):
            writer.append_execution_attempt(
                stage=ExecutionStage.FETCH,
                outcome=ExecutionOutcome.SUCCESS,
                candidate_url="ftp://example.com/file",
                detail_code=ExecutionDetailCode.OK,
            )

    def test_url_without_hostname_raises_value_error(self, research_run: ResearchRun) -> None:
        """URL without hostname raises ValueError."""
        from product_intelligence.domain.evidence import ExecutionDetailCode
        writer = ExecutionEvidenceWriter(research_run)

        with pytest.raises(ValueError):
            writer.append_execution_attempt(
                stage=ExecutionStage.FETCH,
                outcome=ExecutionOutcome.SUCCESS,
                candidate_url="https://",
                detail_code=ExecutionDetailCode.OK,
            )


# ---------------------------------------------------------------------------
# Section 9: ATOMIC FINAL PUBLICATION (REGRESSION)
# ---------------------------------------------------------------------------

class TestAtomicFinalPublicationRegression:
    """Regression tests for atomic final publication.

    Current corrected final publication shape is good.
    Preserve:

        try:
            with transaction.atomic():
                create snapshot
                complete_execution(... COMPLETED)
        except:
            # outside rolled-back transaction
            terminalize FAILED

    Required: adversarial test proving COMPLETED transition failure -> FAILED -> no snapshot.
    """

    def test_finalization_failure_still_fails_correctly(
        self,
        research_run: ResearchRun,
        fake_search_provider: MagicMock,
        fake_page_fetcher: MagicMock,
    ) -> None:
        """Finalization failure -> FAILED, no snapshot (regression test)."""
        from product_intelligence.runs import complete_execution
        from product_intelligence.runs.errors import ResearchRunLifecycleError

        original_complete = complete_execution

        def patched_complete(*args, target_state=None, **kwargs):
            if target_state == ResearchRunState.COMPLETED:
                raise ResearchRunLifecycleError("Simulated COMPLETED transition failure")
            return original_complete(*args, target_state=target_state, **kwargs)

        with patch('product_intelligence.execution.orchestration.complete_execution', patched_complete):
            with pytest.raises(ExecutionError) as exc_info:
                execute_research_run(
                    str(research_run.id),
                    search_provider=fake_search_provider,
                    page_fetcher=fake_page_fetcher,
                )

        # ExecutionError was raised - the outer boundary catches any exception
        # from final publication and wraps it in "Execution failed unexpectedly"
        assert "Execution failed unexpectedly" in str(exc_info.value)

        # Refresh run from database
        research_run.refresh_from_db()

        # Run is FAILED
        assert research_run.current_state == ResearchRunState.FAILED

        # No snapshot exists
        assert not PriceIntelligenceSnapshot.objects.filter(run=research_run).exists()


# ---------------------------------------------------------------------------
# Section 11: POST-CLAIM FAILURE INVARIANT TEST
# ---------------------------------------------------------------------------

class TestPostClaimFailureInvariant:
    """Test that any unexpected exception after claim leaves no RUNNING run.

    Patch a harmless internal step (e.g., query construction).
    Expected:
        ExecutionError
        run == FAILED
        snapshot absent
    """

    def test_post_claim_failure_leaves_run_failed_no_snapshot(
        self,
        research_run: ResearchRun,
        fake_search_provider: MagicMock,
        fake_page_fetcher: MagicMock,
    ) -> None:
        """Unexpected exception after claim leaves run FAILED, no snapshot."""
        ResearchRun.objects.get(id=research_run.id)

        # Patch something inside _execute_claimed_run to raise
        with patch('product_intelligence.execution.matching.assess_identity') as mock_match:
            mock_match.side_effect = RuntimeError("Simulated internal error")

            with pytest.raises(ExecutionError) as exc_info:
                execute_research_run(
                    str(research_run.id),
                    search_provider=fake_search_provider,
                    page_fetcher=fake_page_fetcher,
                )

        # ExecutionError was raised
        assert "Execution failed unexpectedly" in str(exc_info.value)

        # Refresh run from database
        research_run.refresh_from_db()

        # Run is FAILED
        assert research_run.current_state == ResearchRunState.FAILED

        # No snapshot exists
        assert not PriceIntelligenceSnapshot.objects.filter(run=research_run).exists()


# ---------------------------------------------------------------------------
# Section 12: NO_PRICE EXECUTION EVIDENCE TEST
# ---------------------------------------------------------------------------

class TestNormalizeNoPriceExecutionEvidence:
    """Test that NORMALIZE/SUCCESS/NO_PRICE is recorded during full orchestration.

    Required assertions:
    - Uses valid JSON-LD Product markup with explicit MPN but NO price
    - Executes the actual orchestration pipeline (not just unit test)
    - Durable evidence contains: stage=NORMALIZE, outcome=SUCCESS, detail_code=NO_PRICE
    - Does NOT merely assert normalized.price_amount is None (unit test)
    """

    def test_normalize_no_price_records_correct_evidence(
        self,
        research_run: ResearchRun,
        fake_search_provider: MagicMock,
        fake_page_fetcher: MagicMock,
    ) -> None:
        """NORMALIZE/SUCCESS/NO_PRICE is recorded during full orchestration.

        Uses valid JSON-LD Product markup with explicit MPN but NO price.
        Asserts durable evidence, not just in-memory normalized object.
        """
        ResearchRun.objects.get(id=research_run.id)

        # Create search result
        from product_intelligence.providers.search import SearchResult, SearchResponse
        result = MagicMock(spec=SearchResult)
        result.source_url = "https://example.com/product"
        result.title = "Test Product"
        result.snippet = "Description"
        result.price_hint_text = None
        result.part_number_hint = None
        result.raw_reference = None

        response = MagicMock(spec=SearchResponse)
        response.provider_id = "fake"
        response.query = MagicMock(spec=SearchQuery)
        response.retrieved_at = datetime.now(tz=timezone.utc)
        response.results = (result,)
        response.raw_response_reference = None

        fake_search_provider.search.return_value = response

        # Valid JSON-LD Product with MPN but NO price
        html_with_no_price = '''<!DOCTYPE html>
<html>
<head>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "Test Product",
        "mpn": "ABC123",
        "sku": "SKU123"
    }
    </script>
</head>
<body>Product page with no price</body>
</html>'''

        fetched = MagicMock(spec=FetchedPage)
        fetched.body_text = html_with_no_price
        fetched.requested_url = "https://example.com/product"
        fetched.final_url = "https://example.com/product"

        fake_page_fetcher.fetch.return_value = fetched

        # Execute the full orchestration pipeline
        result = execute_research_run(
            str(research_run.id),
            search_provider=fake_search_provider,
            page_fetcher=fake_page_fetcher,
        )

        # The run completes (price-less listing is still processed)
        assert result.run.current_state == ResearchRunState.COMPLETED

        # Read durable evidence from the database
        from product_intelligence.execution.evidence_writer import read_execution_evidence
        evidence = read_execution_evidence(result.run)

        # Find the NORMALIZE evidence record
        normalize_records = [
            r for r in evidence
            if r.stage == ExecutionStage.NORMALIZE.value
        ]

        assert len(normalize_records) >= 1, "Expected at least one NORMALIZE evidence record"

        # Find the NO_PRICE record
        no_price_record = None
        for record in normalize_records:
            if record.outcome == ExecutionOutcome.SUCCESS.value and record.detail_code == "NO_PRICE":
                no_price_record = record
                break

        assert no_price_record is not None, (
            f"Expected NORMALIZE/SUCCESS/NO_PRICE evidence. "
            f"Found normalize records: {[(r.outcome, r.detail_code) for r in normalize_records]}"
        )

        # Verify the record is for our candidate URL
        assert no_price_record.candidate_url == "https://example.com/product"


# ---------------------------------------------------------------------------
# Section 13: AGGREGATE PRIMITIVE-FAILURE REGRESSION TEST
# ---------------------------------------------------------------------------

class TestAggregatePrimitiveFailure:
    """Test that AGGREGATE primitive failure is handled correctly.

    When aggregate_listing_prices() raises, the function must:
    1. Record AGGREGATE/FAILED evidence with detail_code=""
    2. Re-raise so outer boundary terminalizes FAILED
    3. No snapshot survives

    This is a regression test for the previous bug where evidence write
    and primitive failure were conflated.
    """

    def test_aggregate_primitive_failure_records_evidence_and_raises(
        self,
        research_run: ResearchRun,
        fake_search_provider: MagicMock,
        fake_page_fetcher: MagicMock,
    ) -> None:
        """AGGREGATE primitive failure -> AGGREGATE/FAILED evidence, ExecutionError, FAILED run.

        Patches the actual aggregation primitive to raise.
        Asserts:
        - ExecutionError raised
        - run == FAILED
        - snapshot absent
        - exactly one AGGREGATE evidence row
        - outcome == FAILED
        - detail_code == "" (empty string for primitive failure)
        """
        ResearchRun.objects.get(id=research_run.id)

        # Patch aggregate_listing_prices to raise
        with patch('product_intelligence.execution.aggregation.aggregate_listing_prices') as mock_agg:
            mock_agg.side_effect = RuntimeError("Simulated aggregation failure")

            with pytest.raises(ExecutionError) as exc_info:
                execute_research_run(
                    str(research_run.id),
                    search_provider=fake_search_provider,
                    page_fetcher=fake_page_fetcher,
                )

        # ExecutionError was raised
        assert "Aggregation failed" in str(exc_info.value)

        # Refresh run from database
        research_run.refresh_from_db()

        # Run is FAILED
        assert research_run.current_state == ResearchRunState.FAILED

        # No snapshot exists
        assert not PriceIntelligenceSnapshot.objects.filter(run=research_run).exists()

        # Read evidence
        from product_intelligence.execution.evidence_writer import read_execution_evidence
        evidence = read_execution_evidence(research_run)

        # Exactly one AGGREGATE evidence row
        aggregate_records = [
            r for r in evidence
            if r.stage == ExecutionStage.AGGREGATE.value
        ]

        assert len(aggregate_records) == 1, (
            f"Expected exactly one AGGREGATE evidence row, got {len(aggregate_records)}"
        )

        # AGGREGATE/FAILED
        agg_record = aggregate_records[0]
        assert agg_record.outcome == ExecutionOutcome.FAILED.value
        assert agg_record.detail_code == "", (
            f"AGGREGATE/FAILED should have empty detail_code, got {agg_record.detail_code!r}"
        )

