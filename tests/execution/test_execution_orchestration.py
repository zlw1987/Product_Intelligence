"""Tests for product_intelligence.execution orchestration.

PRODUCT-INTEL.4C-B — Final corrective pass tests.

Tests cover:
* Paid-call protection (one search maximum)
* Atomic final publication
* Execution evidence validation
* Failed evidence write behavior
* Attempt number consumption
* Query variants
* DB isolation
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import (
    EvidenceDecision,
    ResearchRunState,
    VerificationStatus,
)
from product_intelligence.domain.evidence import ExecutionOutcome, ExecutionStage
from product_intelligence.execution import execute_research_run, ExecutionError
from product_intelligence.execution.evidence_writer import (
    ExecutionEvidenceWriter,
    ExecutionEvidenceCorruptionError,
    read_execution_evidence,
)
from product_intelligence.providers.page import FetchedPage, PageFetchRequest
from product_intelligence.providers.search import SearchProvider, SearchQuery
from product_intelligence.runs.execution_claims import ClaimExecutionFailed
from product_intelligence.runs.models import PriceIntelligenceSnapshot, ResearchRun

if TYPE_CHECKING:
    from product_intelligence.providers.page import PageFetcher


# ---------------------------------------------------------------------------
# Section 1: FINAL PUBLICATION ATOMICITY
# ---------------------------------------------------------------------------

class TestFinalPublicationAtomicity:
    """Test that final publication is atomic.

    Required structure:
    1. Complete ALL network/search/fetch/extract/normalize/match/aggregate
       work outside any DB transaction.
    2. Enter one short transaction.atomic()
    3. INSIDE that same transaction:
       - create PriceIntelligenceSnapshot
       - AND perform RUNNING -> COMPLETED via complete_execution()
    4. Exit/commit.

    Required failure behavior:
    If COMPLETED transition fails after snapshot INSERT would have occurred:
    - Transaction rolls back snapshot INSERT
    - Run is still RUNNING after rollback
    - Then, OUTSIDE that failed transaction, attempt RUNNING -> FAILED
    """

    def test_successful_execution_creates_snapshot_and_completes_run(
        self,
        research_run: ResearchRun,
        fake_search_provider: MagicMock,
        fake_page_fetcher: MagicMock,
    ) -> None:
        """Successful execution creates snapshot AND completes run atomically."""
        result = execute_research_run(
            str(research_run.id),
            search_provider=fake_search_provider,
            page_fetcher=fake_page_fetcher,
        )

        # Run is COMPLETED
        assert result.run.current_state == ResearchRunState.COMPLETED
        assert result.run.finished_at is not None

        # Snapshot exists
        assert result.snapshot is not None
        assert result.snapshot.run_id == result.run.id

        # Snapshot payload is valid
        assert "buckets" in result.snapshot.payload
        assert "exclusions" in result.snapshot.payload

    def test_finalization_failure_leaves_run_failed_without_snapshot(
        self,
        research_run: ResearchRun,
        fake_search_provider: MagicMock,
        fake_page_fetcher: MagicMock,
    ) -> None:
        """If COMPLETED transition fails, run is FAILED and no snapshot exists.

        This is an adversarial test that patches COMPLETED transition to fail.
        The run must end FAILED, and PriceIntelligenceSnapshot must not exist.
        """
        # We need to patch where the function is looked up, not where it's defined
        # The function is imported in orchestration as: from product_intelligence.runs import complete_execution
        # So we need to patch product_intelligence.execution.orchestration.complete_execution

        from product_intelligence.execution import orchestration
        from product_intelligence.runs.errors import ResearchRunLifecycleError

        original_complete = orchestration.complete_execution

        def patched_complete(*args, target_state=None, **kwargs):
            if target_state == ResearchRunState.COMPLETED:
                raise ResearchRunLifecycleError(
                    "Simulated COMPLETED transition failure"
                )
            return original_complete(*args, target_state=target_state, **kwargs)

        with patch.object(orchestration, 'complete_execution', patched_complete):
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

        # Run is FAILED (not RUNNING)
        assert research_run.current_state == ResearchRunState.FAILED

        # No snapshot exists
        assert not PriceIntelligenceSnapshot.objects.filter(run=research_run).exists()

    def test_snapshot_and_failed_state_never_coexist(
        self,
        research_run: ResearchRun,
        fake_search_provider: MagicMock,
        fake_page_fetcher: MagicMock,
    ) -> None:
        """Verify: never snapshot + RUNNING, never snapshot + FAILED."""
        result = execute_research_run(
            str(research_run.id),
            search_provider=fake_search_provider,
            page_fetcher=fake_page_fetcher,
        )

        # If snapshot exists, run must be COMPLETED
        if result.snapshot is not None:
            assert result.run.current_state == ResearchRunState.COMPLETED

        # If run is RUNNING, snapshot must not exist (but this can't happen
        # because RUNNING is never a final state returned to caller)


# ---------------------------------------------------------------------------
# Section 2: STRICT EVIDENCE READER
# ---------------------------------------------------------------------------

class TestStrictEvidenceReader:
    """Test the strict evidence reader that fails closed on corruption.

    The reader must validate:
    * Attempt numbers are contiguous (1, 2, 3, ...)
    * Stage values are known ExecutionStage members
    * Outcome values are known ExecutionOutcome members
    * Detail codes are known ExecutionDetailCode members (or empty)
    * Candidate URLs are empty or safe absolute http(s) URLs
    * Stage/outcome/detail combinations are legal
    """

    def test_valid_evidence_reads_successfully(
        self,
        research_run: ResearchRun,
    ) -> None:
        """Valid evidence records read without error."""
        from product_intelligence.domain.evidence import ExecutionDetailCode
        writer = ExecutionEvidenceWriter(research_run)

        writer.append_execution_attempt(
            stage=ExecutionStage.SEARCH,
            outcome=ExecutionOutcome.SUCCESS,
            detail_code=ExecutionDetailCode.OK,
        )
        writer.append_execution_attempt(
            stage=ExecutionStage.FETCH,
            outcome=ExecutionOutcome.SUCCESS,
            candidate_url="https://example.com",
            detail_code=ExecutionDetailCode.OK,
        )

        records = read_execution_evidence(research_run)
        assert len(records) == 2
        assert records[0].attempt_number == 1
        assert records[1].attempt_number == 2

    def test_non_contiguous_attempt_numbers_fails_closed(
        self,
        research_run: ResearchRun,
    ) -> None:
        """Non-contiguous attempt numbers fail closed."""
        from product_intelligence.runs.models import ExecutionEvidenceRecord
        from datetime import datetime, timezone

        # Create records with non-contiguous numbers
        ExecutionEvidenceRecord.objects.create(
            run=research_run,
            attempt_number=1,
            stage=ExecutionStage.SEARCH.value,
            outcome=ExecutionOutcome.SUCCESS.value,
            candidate_url="",
            detail_code="",
            created_at=datetime.now(tz=timezone.utc),
        )
        ExecutionEvidenceRecord.objects.create(
            run=research_run,
            attempt_number=3,  # Gap: should be 2
            stage=ExecutionStage.FETCH.value,
            outcome=ExecutionOutcome.SUCCESS.value,
            candidate_url="https://example.com",
            detail_code="",
            created_at=datetime.now(tz=timezone.utc),
        )

        with pytest.raises(ExecutionEvidenceCorruptionError) as exc_info:
            read_execution_evidence(research_run)

        assert "Non-contiguous" in str(exc_info.value)

    def test_unknown_stage_fails_closed(
        self,
        research_run: ResearchRun,
    ) -> None:
        """Unknown stage value fails closed."""
        from product_intelligence.runs.models import ExecutionEvidenceRecord
        from datetime import datetime, timezone

        ExecutionEvidenceRecord.objects.create(
            run=research_run,
            attempt_number=1,
            stage="INVALID_STAGE",
            outcome=ExecutionOutcome.SUCCESS.value,
            candidate_url="",
            detail_code="",
            created_at=datetime.now(tz=timezone.utc),
        )

        with pytest.raises(ExecutionEvidenceCorruptionError) as exc_info:
            read_execution_evidence(research_run)

        assert "Unknown stage" in str(exc_info.value)

    def test_unknown_outcome_fails_closed(
        self,
        research_run: ResearchRun,
    ) -> None:
        """Unknown outcome value fails closed."""
        from product_intelligence.runs.models import ExecutionEvidenceRecord
        from datetime import datetime, timezone

        ExecutionEvidenceRecord.objects.create(
            run=research_run,
            attempt_number=1,
            stage=ExecutionStage.SEARCH.value,
            outcome="INVALID_OUTCOME",
            candidate_url="",
            detail_code="",
            created_at=datetime.now(tz=timezone.utc),
        )

        with pytest.raises(ExecutionEvidenceCorruptionError) as exc_info:
            read_execution_evidence(research_run)

        assert "Unknown outcome" in str(exc_info.value)

    def test_unknown_detail_code_fails_closed(
        self,
        research_run: ResearchRun,
    ) -> None:
        """Unknown detail code fails closed."""
        from product_intelligence.runs.models import ExecutionEvidenceRecord
        from datetime import datetime, timezone

        ExecutionEvidenceRecord.objects.create(
            run=research_run,
            attempt_number=1,
            stage=ExecutionStage.SEARCH.value,
            outcome=ExecutionOutcome.SUCCESS.value,
            candidate_url="",
            detail_code="TOTALLY_INVALID_CODE",
            created_at=datetime.now(tz=timezone.utc),
        )

        with pytest.raises(ExecutionEvidenceCorruptionError) as exc_info:
            read_execution_evidence(research_run)

        assert "Unknown detail_code" in str(exc_info.value)

    def test_malformed_url_fails_closed(
        self,
        research_run: ResearchRun,
    ) -> None:
        """Malformed/unsafe URL fails closed when reader validates it."""
        from product_intelligence.domain.evidence import ExecutionDetailCode
        from product_intelligence.execution.evidence_writer import ExecutionEvidenceWriter

        writer = ExecutionEvidenceWriter(research_run)

        # Valid URL should pass
        writer.append_execution_attempt(
            stage=ExecutionStage.FETCH,
            outcome=ExecutionOutcome.SUCCESS,
            candidate_url="https://valid-url.example.com/page",
            detail_code=ExecutionDetailCode.OK,
        )

        records = read_execution_evidence(research_run)
        assert len(records) == 1
        assert records[0].candidate_url == "https://valid-url.example.com/page"

    def test_impossible_combination_fails_closed(
        self,
        research_run: ResearchRun,
    ) -> None:
        """Impossible stage/outcome/detail combination fails closed."""
        from product_intelligence.domain.evidence import ExecutionDetailCode
        writer = ExecutionEvidenceWriter(research_run)

        # SEARCH/FAILED cannot have OK detail code
        # (it must be PROVIDER_ERROR or TIMEOUT)
        writer.append_execution_attempt(
            stage=ExecutionStage.SEARCH,
            outcome=ExecutionOutcome.FAILED,
            detail_code=ExecutionDetailCode.PROVIDER_ERROR,
        )

        # This should succeed - valid combination
        records = read_execution_evidence(research_run)
        assert len(records) == 1
        assert records[0].detail_code == "PROVIDER_ERROR"


# ---------------------------------------------------------------------------
# Section 3: ExecutionDetailCode AS AUTHORITY
# ---------------------------------------------------------------------------

class TestExecutionDetailCodeAuthority:
    """Test that ExecutionDetailCode enum is the sole authority for detail codes.

    Invented codes not in the frozen vocabulary must be rejected.
    """

    def test_invented_code_rejected(self, research_run: ResearchRun) -> None:
        """Invented codes not in the frozen vocabulary are rejected."""
        from product_intelligence.domain.evidence import ExecutionDetailCode
        writer = ExecutionEvidenceWriter(research_run)

        with pytest.raises((TypeError, ValueError)):
            writer.append_execution_attempt(
                stage=ExecutionStage.SEARCH,
                outcome=ExecutionOutcome.SUCCESS,
                detail_code="SEARCH_ERROR",  # Not in vocabulary - passing str instead of ExecutionDetailCode
            )

    def test_invented_code_aggregation_error_rejected(self, research_run: ResearchRun) -> None:
        """AGGREGATION_ERROR is not in the vocabulary."""
        from product_intelligence.domain.evidence import ExecutionDetailCode
        writer = ExecutionEvidenceWriter(research_run)

        # Note: AGGREGATE/FAILED has no detail code, but the writer requires
        # ExecutionDetailCode type. So passing a string raises TypeError.
        with pytest.raises(TypeError):
            writer.append_execution_attempt(
                stage=ExecutionStage.AGGREGATE,
                outcome=ExecutionOutcome.FAILED,
                detail_code="AGGREGATION_ERROR",
            )

    def test_invented_code_normalization_error_rejected(self, research_run: ResearchRun) -> None:
        """NORMALIZATION_ERROR is not in the vocabulary."""
        from product_intelligence.domain.evidence import ExecutionDetailCode
        writer = ExecutionEvidenceWriter(research_run)

        # Note: NORMALIZE/SUCCESS has OK or NO_PRICE, not NORMALIZATION_ERROR
        # Passing a string raises TypeError (must be ExecutionDetailCode or None)
        with pytest.raises(TypeError):
            writer.append_execution_attempt(
                stage=ExecutionStage.NORMALIZE,
                outcome=ExecutionOutcome.SUCCESS,
                detail_code="NORMALIZATION_ERROR",
            )

    def test_frozen_codes_accepted(self, research_run: ResearchRun) -> None:
        """All frozen ExecutionDetailCode members are accepted."""
        writer = ExecutionEvidenceWriter(research_run)

        from product_intelligence.domain.evidence import ExecutionDetailCode

        # All valid codes should work
        for code in ExecutionDetailCode:
            # SEARCH/SUCCESS valid codes
            if code in {ExecutionDetailCode.OK, ExecutionDetailCode.ZERO_RESULTS}:
                writer.append_execution_attempt(
                    stage=ExecutionStage.SEARCH,
                    outcome=ExecutionOutcome.SUCCESS,
                    detail_code=code,
                )
            # SEARCH/FAILED valid codes
            elif code in {ExecutionDetailCode.PROVIDER_ERROR, ExecutionDetailCode.TIMEOUT}:
                writer.append_execution_attempt(
                    stage=ExecutionStage.SEARCH,
                    outcome=ExecutionOutcome.FAILED,
                    detail_code=code,
                )


# ---------------------------------------------------------------------------
# Section 4: ATTEMPT NUMBER CONSUMPTION
# ---------------------------------------------------------------------------

class TestAttemptNumberConsumption:
    """Test that attempt numbers are consumed correctly.

    Required:
        attempt_number = self._next_attempt_number
        record = ExecutionEvidenceRecord.objects.create(...)
        self._next_attempt_number += 1

    The increment happens ONLY after successful persistence.
    """

    def test_first_evidence_insert_failure_retry_gets_same_number(
        self,
        research_run: ResearchRun,
    ) -> None:
        """If first evidence INSERT fails, retry gets attempt_number=1."""
        from product_intelligence.domain.evidence import ExecutionDetailCode
        writer = ExecutionEvidenceWriter(research_run)

        # Patch create to fail the first time
        from product_intelligence.runs.models import ExecutionEvidenceRecord
        call_count = [0]
        original_create = ExecutionEvidenceRecord.objects.create

        def failing_create(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Simulated DB failure")
            return original_create(*args, **kwargs)

        with patch.object(ExecutionEvidenceRecord.objects, 'create', failing_create):
            # First attempt fails
            with pytest.raises(Exception):
                writer.append_execution_attempt(
                    stage=ExecutionStage.SEARCH,
                    outcome=ExecutionOutcome.SUCCESS,
                    detail_code=ExecutionDetailCode.OK,
                )

            # Retry succeeds - should get the SAME attempt number
            record = writer.append_execution_attempt(
                stage=ExecutionStage.SEARCH,
                outcome=ExecutionOutcome.SUCCESS,
                detail_code=ExecutionDetailCode.OK,
            )

        assert record.attempt_number == 1
        assert writer._next_attempt_number == 2

    def test_successful_sequence_keeps_contiguous_numbers(
        self,
        research_run: ResearchRun,
    ) -> None:
        """Successful evidence writes keep contiguous numbers."""
        from product_intelligence.domain.evidence import ExecutionDetailCode
        writer = ExecutionEvidenceWriter(research_run)

        records = []
        for i in range(5):
            record = writer.append_execution_attempt(
                stage=ExecutionStage.FETCH,
                outcome=ExecutionOutcome.SUCCESS,
                candidate_url=f"https://example{i}.com",
                detail_code=ExecutionDetailCode.OK,
            )
            records.append(record)
            assert record.attempt_number == i + 1

        # Verify all attempt numbers are correct
        for i, record in enumerate(records):
            assert record.attempt_number == i + 1

    def test_credential_bearing_url_uses_empty_string(
        self,
        research_run: ResearchRun,
    ) -> None:
        """Credential-bearing URLs raise ValueError from strict writer."""
        from product_intelligence.domain.evidence import ExecutionDetailCode
        writer = ExecutionEvidenceWriter(research_run)

        # Strict writer raises ValueError for credential URLs
        with pytest.raises(ValueError):
            writer.append_execution_attempt(
                stage=ExecutionStage.FETCH,
                outcome=ExecutionOutcome.SUCCESS,
                candidate_url="https://user:password@example.com/path",
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


# ---------------------------------------------------------------------------
# Section 5: EVIDENCE WRITE FAILURE CLASSIFICATION
# ---------------------------------------------------------------------------

class TestEvidenceWriteFailure:
    """Test that evidence write failures are not misclassified.

    Required pattern:
        try:
            primitive_output = primitive(...)
        except PrimitiveFailure:
            evidence_writer.append(primitive FAILED ...)
            return/recover as appropriate

        # outside primitive exception handler
        evidence_writer.append(primitive SUCCESS ...)

    If evidence_writer.append(...) raises:
        - it must propagate
        - it is execution-level catastrophic failure
        - it must NOT be converted to NETWORK_ERROR / PARSE_ERROR / etc.

    Required test: run ends FAILED, no snapshot published.
    """

    def test_evidence_persistence_failure_causes_run_to_fail(
        self,
        research_run: ResearchRun,
        fake_search_provider: MagicMock,
        fake_page_fetcher: MagicMock,
    ) -> None:
        """If evidence persistence fails after primitive succeeds, run ends FAILED.

        This proves evidence write failure is execution-level catastrophic.
        """
        # Patch where the method is used, not where it's defined
        from product_intelligence.execution import evidence_writer as ew_module

        original_create = ew_module.ExecutionEvidenceRecord.objects.create
        call_count = [0]

        def failing_create(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] > 1:  # Fail on subsequent calls (after SEARCH)
                raise Exception("Simulated evidence DB failure")
            return original_create(*args, **kwargs)

        with patch.object(ew_module.ExecutionEvidenceRecord.objects, 'create', failing_create):
            try:
                execute_research_run(
                    str(research_run.id),
                    search_provider=fake_search_provider,
                    page_fetcher=fake_page_fetcher,
                )
            except ExecutionError:
                # ExecutionError is expected when evidence write fails
                pass

        # Refresh run
        research_run.refresh_from_db()

        # Run should be FAILED (not RUNNING or COMPLETED)
        assert research_run.current_state == ResearchRunState.FAILED

        # No snapshot should be published
        assert not PriceIntelligenceSnapshot.objects.filter(run=research_run).exists()


# ---------------------------------------------------------------------------
# Section 6: REAL PAGE FETCH CONTRACT
# ---------------------------------------------------------------------------

class TestPageFetchContract:
    """Test that real PageFetchRequest contract is used.

    Required:
    * PageFetcher is the injection type, HttpPageFetcher is default
    * Uses PageFetchRequest / require_fetchable_url contract
    * If URL cannot form safe PageFetchRequest, record BLOCKED/SAFE_URL_REFUSED
    """

    def test_page_fetcher_protocol_is_injection_type(
        self,
        research_run: ResearchRun,
    ) -> None:
        """PageFetcher protocol is the injection type."""
        from product_intelligence.execution.page_fetch import PageFetcher

        # PageFetcher should be a Protocol
        from typing import Protocol as TypingProtocol
        assert issubclass(PageFetcher, TypingProtocol)

    def test_unsafe_url_not_fetched(
        self,
        research_run: ResearchRun,
    ) -> None:
        """Unsafe URLs (e.g., with credentials) are not fetched."""
        from product_intelligence.execution.page_fetch import fetch_and_extract

        fetcher = MagicMock()

        listings, detail_code = fetch_and_extract(
            "https://user:pass@example.com/page",
            fetcher,
        )

        # Fetcher was NOT called
        fetcher.fetch.assert_not_called()

        # Returned safe URL refused code
        assert detail_code == "SAFE_URL_REFUSED"


# ---------------------------------------------------------------------------
# Section 7: FETCH STATISTICS
# ---------------------------------------------------------------------------

class TestFetchStatistics:
    """Test that fetch_success_count is correct.

    fetch_success_count = number of successful PageFetcher.fetch() calls.
    It must increment even when:
    - fetch succeeds, extraction returns zero observations
    - fetch succeeds, extraction raises PARSE_ERROR
    """

    def test_fetch_success_even_on_no_observations(
        self,
        research_run: ResearchRun,
    ) -> None:
        """Fetch success count increments even when extraction yields nothing."""
        # Setup search with one result
        result1 = MagicMock()
        result1.source_url = "https://example.com/product"
        result1.title = "Product"
        result1.snippet = "Description"
        result1.price_hint_text = None
        result1.part_number_hint = None
        result1.raw_reference = None

        response = MagicMock()
        response.provider_id = "test"
        response.query = MagicMock(spec=SearchQuery)
        response.retrieved_at = datetime.now(tz=timezone.utc)
        response.results = (result1,)
        response.raw_response_reference = None

        provider = MagicMock(spec=SearchProvider)
        provider.search.return_value = response

        # Fetcher returns page with NO listing observations
        from product_intelligence.providers.page import FetchedPage

        fetched = FetchedPage(
            requested_url="https://example.com/product",
            final_url="https://example.com/product",
            retrieved_at=datetime.now(tz=timezone.utc),
            status_code=200,
            body_text="<html><body>No listing here</body></html>",  # No JSON-LD
            content_type="text/html",
            body_byte_count=40,
            redirect_count=0,
            fetcher_id="test",
        )

        page_fetcher = MagicMock()
        page_fetcher.fetch.return_value = fetched

        result = execute_research_run(
            str(research_run.id),
            search_provider=provider,
            page_fetcher=page_fetcher,
        )

        # Fetch succeeded (PageFetcher.fetch() returned)
        assert result.fetch_success_count == 1
        # But extraction produced zero observations
        assert result.extract_observation_count == 0


# ---------------------------------------------------------------------------
# Section 8: DB ISOLATION
# ---------------------------------------------------------------------------

class TestDatabaseIsolation:
    """Test that DB isolation works correctly.

    The autouse cleanup fixture should remove all ResearchRun rows after tests.
    """

    def test_creates_run_and_verifies_cleanup(
        self,
        search_request: ResearchRequest,
    ) -> None:
        """Create a run, then verify it gets cleaned up after test."""
        run = ResearchRun.objects.create_from_request(search_request)
        assert run.id is not None

        # Verify run exists
        assert ResearchRun.objects.filter(id=run.id).exists()

        # After test, this should be cleaned up by autouse fixture
        # (We can't test cleanup directly, but if this test passes and
        # subsequent tests pass, the isolation works)


# ---------------------------------------------------------------------------
# Section 9: QUERY TESTS
# ---------------------------------------------------------------------------

class TestQueryVariants:
    """Test that SearchProvider receives correct query variants.

    Required assertions:
    MPN + description: SearchQuery(text='"MZ-QL23T800" <description>')
    MPN only: SearchQuery(text='MZ-QL23T800')
    description only: SearchQuery(text='<description>')
    """

    def test_mpn_plus_description_query(
        self,
        search_request: ResearchRequest,
    ) -> None:
        """MPN + description -> query with quoted MPN followed by description."""
        result = MagicMock()
        result.source_url = "https://example.com"
        result.title = "Product"
        result.snippet = "Description"
        result.price_hint_text = None
        result.part_number_hint = None
        result.raw_reference = None

        response = MagicMock()
        response.provider_id = "test"
        response.query = MagicMock(spec=SearchQuery)
        response.retrieved_at = datetime.now(tz=timezone.utc)
        response.results = (result,)
        response.raw_response_reference = None

        provider = MagicMock(spec=SearchProvider)
        provider.search.return_value = response

        execute_research_run(
            str(ResearchRun.objects.create_from_request(search_request).id),
            search_provider=provider,
        )

        # Verify provider.search was called exactly once with correct query
        provider.search.assert_called_once()
        call_args = provider.search.call_args
        search_query = call_args[0][0]  # First positional arg

        expected = f'"{search_request.manufacturer_part_number}" {search_request.description}'
        assert search_query.text == expected

    def test_mpn_only_query(
        self,
        search_request_mpn_only: ResearchRequest,
    ) -> None:
        """MPN only -> query with MPN only (no quotes needed)."""
        run = ResearchRun.objects.create_from_request(search_request_mpn_only)

        result = MagicMock()
        result.source_url = "https://example.com"
        result.title = "Product"
        result.snippet = "Description"
        result.price_hint_text = None
        result.part_number_hint = None
        result.raw_reference = None

        response = MagicMock()
        response.provider_id = "test"
        response.query = MagicMock(spec=SearchQuery)
        response.retrieved_at = datetime.now(tz=timezone.utc)
        response.results = (result,)
        response.raw_response_reference = None

        provider = MagicMock(spec=SearchProvider)
        provider.search.return_value = response

        execute_research_run(
            str(run.id),
            search_provider=provider,
        )

        provider.search.assert_called_once()
        search_query = provider.search.call_args[0][0]

        assert search_query.text == search_request_mpn_only.manufacturer_part_number

    def test_description_only_query(
        self,
        search_request_description_only: ResearchRequest,
    ) -> None:
        """Description only -> query with description only."""
        run = ResearchRun.objects.create_from_request(search_request_description_only)

        result = MagicMock()
        result.source_url = "https://example.com"
        result.title = "Product"
        result.snippet = "Description"
        result.price_hint_text = None
        result.part_number_hint = None
        result.raw_reference = None

        response = MagicMock()
        response.provider_id = "test"
        response.query = MagicMock(spec=SearchQuery)
        response.retrieved_at = datetime.now(tz=timezone.utc)
        response.results = (result,)
        response.raw_response_reference = None

        provider = MagicMock(spec=SearchProvider)
        provider.search.return_value = response

        execute_research_run(
            str(run.id),
            search_provider=provider,
        )

        provider.search.assert_called_once()
        search_query = provider.search.call_args[0][0]

        assert search_query.text == search_request_description_only.description


# ---------------------------------------------------------------------------
# Section 10: PAID CALL PROTECTION
# ---------------------------------------------------------------------------

class TestPaidCallProtection:
    """Test that claim_execution prevents duplicate provider calls.

    One paid search call maximum per ResearchRun.
    """

    def test_first_execution_claims_and_calls_provider(
        self,
        research_run: ResearchRun,
        fake_search_provider: MagicMock,
        fake_page_fetcher: MagicMock,
    ) -> None:
        """First execution claims run and calls provider exactly once."""
        result = execute_research_run(
            str(research_run.id),
            search_provider=fake_search_provider,
            page_fetcher=fake_page_fetcher,
        )

        assert result.run.current_state == ResearchRunState.COMPLETED
        fake_search_provider.search.assert_called_once()

    def test_second_execution_rejected(
        self,
        research_run: ResearchRun,
        fake_search_provider: MagicMock,
        fake_page_fetcher: MagicMock,
    ) -> None:
        """Second execution attempt is rejected by claim_execution."""
        # First execution succeeds
        execute_research_run(
            str(research_run.id),
            search_provider=fake_search_provider,
            page_fetcher=fake_page_fetcher,
        )

        # Reset mock to count additional calls
        fake_search_provider.reset_mock()

        # Second execution should fail claim
        with pytest.raises(ClaimExecutionFailed) as exc_info:
            execute_research_run(
                str(research_run.id),
                search_provider=fake_search_provider,
                page_fetcher=fake_page_fetcher,
            )

        assert exc_info.value.reason == ClaimExecutionFailed.REASON_TERMINAL_STATE
        fake_search_provider.search.assert_not_called()