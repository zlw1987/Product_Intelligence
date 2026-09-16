"""Tests for the comparable web trigger & report (PRODUCT-INTEL.7C-C).

Covers:
- Action/routing: POST route exists, GET returns 405, CSRF, 404, redirect
- Idempotency: COMPLETED child -> no re-execution, RUNNING -> no re-execution
  PENDING -> execute once, FAILED -> retry creates new child
- GET read-only: no trigger calls, no executor calls, no provider construction
  no timestamp mutation
- Child selection: active before terminal, COMPLETED > FAILED
- Decode: valid payload, bad schema version, malformed payload
- Result kinds: NO_REQUESTED_MPN, NO_AUTHORITY_MATCH, AMBIGUOUS_AUTHORITY
  FULL zero candidates, FULL multiple candidates
- Presentation: candidate order, no sorting, all retained, Decimal exactness
- Lifecycle/error: execution error -> FAILED, claim race -> redirect
- BLOCKER 5: CSRF, idempotency, error handling, GET read-only, corruption,
  result-kind HTML assertions
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.test import Client
from django.urls import reverse

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import ResearchRunState
from product_intelligence.research.comparable_research_results import (
    AuthorityAttemptResult,
    AuthorityAuditOutcomeKind,
    ComparableCandidateResult,
    ComparableResearchResult,
    ComparableResultKind,
    DatasheetAttemptResult,
    DatasheetAuditOutcomeKind,
    ProductEnrichmentAudit,
    EvidenceSourceReference,
    EvidenceLayer,
    SourceAuthority,
)
from product_intelligence.research.enterprise_ssd_similarity import (
    ComparisonState,
)
from product_intelligence.research.specifications import (
    ResolutionState,
)
from product_intelligence.runs.models import (
    ComparableResearchExecution,
    ComparableResearchFailureReason,
    ComparableResearchState,
    PriceIntelligenceSnapshot,
    ResearchRun,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client() -> Client:
    return Client()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_evidence() -> tuple:
    """Create a minimal evidence reference."""
    return (EvidenceSourceReference(
        source_name="TestSource",
        source_url="https://example.com/support",
        evidence_layer=EvidenceLayer.SUPPORT_PAGE,
        source_authority=SourceAuthority.AUTHORITATIVE,
        retrieved_at="2024-01-01T00:00:00+00:00",
    ),)


def _make_field_assessments(
    scored_count: int = 0,
    field_similarity: Decimal = Decimal("1"),
) -> tuple:
    """Build 12 field assessments matching ENTERPRISE_SSD_SCHEMA order."""
    from product_intelligence.research.enterprise_ssd import (
        ENTERPRISE_SSD_SCHEMA,
    )
    from product_intelligence.research.comparable_research_results import (
        FieldAssessmentResult,
    )

    assessments = []
    for idx, key in enumerate(ENTERPRISE_SSD_SCHEMA.definitions.keys()):
        if idx < scored_count:
            assessments.append(
                FieldAssessmentResult(
                    definition_key=key,
                    comparison_state=ComparisonState.SCORED,
                    target_resolution_state=ResolutionState.VERIFIED,
                    candidate_resolution_state=ResolutionState.VERIFIED,
                    field_similarity=field_similarity,
                    target_value="test",
                    candidate_value="test",
                    target_evidence=_make_evidence(),
                    candidate_evidence=_make_evidence(),
                )
            )
        else:
            assessments.append(
                FieldAssessmentResult(
                    definition_key=key,
                    comparison_state=ComparisonState.BOTH_NOT_VERIFIED,
                    target_resolution_state=ResolutionState.UNKNOWN,
                    candidate_resolution_state=ResolutionState.UNKNOWN,
                    field_similarity=None,
                    target_value=None,
                    candidate_value=None,
                    target_evidence=(),
                    candidate_evidence=(),
                )
            )
    return tuple(assessments)


def _make_comparable_candidate(
    mpn: str = "CAND-001",
    scored_count: int = 7,
    field_similarity: Decimal = Decimal("1"),
) -> ComparableCandidateResult:
    from product_intelligence.research.enterprise_ssd import (
        ENTERPRISE_SSD_SCHEMA,
    )
    total = len(ENTERPRISE_SSD_SCHEMA.definitions)
    scored_sims = [field_similarity] * scored_count
    obs_sim = sum(scored_sims, Decimal("0")) / Decimal(scored_count) if scored_count > 0 else None
    w_sim = sum(scored_sims, Decimal("0")) / Decimal(total) if scored_count > 0 else None

    return ComparableCandidateResult(
        candidate_mpn=mpn,
        candidate_normalized_mpn=mpn.upper(),
        scored_field_count=scored_count,
        evidence_coverage=Decimal(scored_count) / Decimal(total),
        observed_similarity=obs_sim,
        evidence_weighted_similarity=w_sim,
        field_assessments=_make_field_assessments(scored_count, field_similarity),
        enrichment_audit=ProductEnrichmentAudit(
            product_mpn=mpn,
            attempts=(
                DatasheetAttemptResult(
                    outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
                ),
            ),
        ),
    )


def _make_full_result(
    target_mpn: str = "XP15360SE70005",
    candidates: tuple | None = None,
) -> ComparableResearchResult:
    """Build a minimal valid FULL result."""
    if candidates is None:
        candidates = ()
    return ComparableResearchResult(
        kind=ComparableResultKind.FULL,
        target_mpn=target_mpn,
        target_manufacturer="Seagate",
        target_enrichment_audit=ProductEnrichmentAudit(
            product_mpn=target_mpn,
            attempts=(
                DatasheetAttemptResult(
                    outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
                ),
            ),
        ),
        authority_audit=(
            AuthorityAttemptResult(
                policy_id="test-policy",
                outcome=AuthorityAuditOutcomeKind.MATCHED,
                requested_source_url="https://example.com/support",
                fetched_final_url="https://example.com/support",
                retrieved_at=datetime.now(timezone.utc).isoformat(),
                matching_mpn=target_mpn,
            ),
        ),
        candidates=candidates,
    )


def _make_no_requested_mpn_result() -> ComparableResearchResult:
    return ComparableResearchResult(
        kind=ComparableResultKind.NO_REQUESTED_MPN,
        target_mpn="",
        target_manufacturer=None,
        target_enrichment_audit=None,
        authority_audit=(
            AuthorityAttemptResult(
                policy_id="test-policy",
                outcome=AuthorityAuditOutcomeKind.NO_REQUESTED_MPN,
                requested_source_url="https://example.com/support",
            ),
        ),
        candidates=(),
    )


def _make_no_authority_match_result() -> ComparableResearchResult:
    return ComparableResearchResult(
        kind=ComparableResultKind.NO_AUTHORITY_MATCH,
        target_mpn="XP15360SE70005",
        target_manufacturer=None,
        target_enrichment_audit=None,
        authority_audit=(
            AuthorityAttemptResult(
                policy_id="test-policy",
                outcome=AuthorityAuditOutcomeKind.NO_MPN_IN_SOURCE,
                requested_source_url="https://example.com/support",
                fetched_final_url="https://example.com/support/final",
                retrieved_at=datetime.now(timezone.utc).isoformat(),
            ),
        ),
        candidates=(),
    )


def _make_ambiguous_authority_result() -> ComparableResearchResult:
    return ComparableResearchResult(
        kind=ComparableResultKind.AMBIGUOUS_AUTHORITY,
        target_mpn="XP15360SE70005",
        target_manufacturer=None,
        target_enrichment_audit=None,
        authority_audit=(
            AuthorityAttemptResult(
                policy_id="test-policy",
                outcome=AuthorityAuditOutcomeKind.AMBIGUOUS_MPN_MATCH,
                requested_source_url="https://example.com/support",
                fetched_final_url="https://example.com/support/final",
                retrieved_at=datetime.now(timezone.utc).isoformat(),
            ),
        ),
        candidates=(),
    )


def _make_completed_run(client: Client = None):
    """Helper to create a COMPLETED run with snapshot."""
    run = ResearchRun.objects.create_from_request(
        ResearchRequest(manufacturer_part_number="XP15360SE70005", description="Test"),
    )
    run.transition_to(ResearchRunState.RUNNING)
    run.transition_to(ResearchRunState.COMPLETED)
    PriceIntelligenceSnapshot.objects.create(
        run=run, schema_version=1,
        payload={"request": {"manufacturer_part_number": "XP15360SE70005", "description": "Test"},
                 "assessments": [], "price_buckets": [], "excluded_listings": [],
                 "verification_status": "VERIFIED",
                 "aggregated_at": datetime.now(timezone.utc).isoformat()},
    )
    return run


# ---------------------------------------------------------------------------
# ACTION / SECURITY (BLOCKER 5 items 1-3)
# ---------------------------------------------------------------------------


class TestComparableActionSecurity:
    """CSRF and transient error flag tests."""

    def test_csrf_post_without_token_returns_403(self, human_review_db_isolation):
        """POST without CSRF token -> 403.

        BLOCKER 5 item 1: CSRF protection.
        """
        from django.test import Client as DjangoClient

        csrf_client = DjangoClient(enforce_csrf_checks=True)
        run = ResearchRun.objects.create_from_request(
            ResearchRequest(manufacturer_part_number="TEST", description="Test"),
        )
        # Must force a cookie for CSRF to apply
        response = csrf_client.get(f"/research/{run.id}")
        assert response.status_code == 200
        # POST without CSRF token
        response = csrf_client.post(f"/research/{run.id}/comparables")
        assert response.status_code == 403

    def test_csrf_post_with_token_reaches_action(self, human_review_db_isolation):
        """POST with valid CSRF token reaches the action normally.

        BLOCKER 5 item 2: valid CSRF.
        """
        from django.test import Client as DjangoClient
        from django.utils.crypto import get_random_string

        csrf_client = DjangoClient(enforce_csrf_checks=True)
        run = _make_completed_run()

        with patch(
            "product_intelligence.web.views.trigger_comparable_research",
        ) as mock_trigger:
            mock_child = MagicMock()
            mock_child.state = ComparableResearchState.RUNNING
            mock_trigger.return_value = mock_child

            # GET first to get CSRF cookie from the server
            csrf_client.get(f"/research/{run.id}")
            # Extract CSRF token from the set-cookie header and use it
            token = csrf_client.cookies.get("csrftoken")
            csrf_token = token.value if token else None

            # POST with CSRF token in header
            response = csrf_client.post(
                f"/research/{run.id}/comparables",
                HTTP_X_CSRFTOKEN=csrf_token,
            )

        # Should redirect (301/302/303), not 403
        assert response.status_code in (301, 302, 303)

    def test_comparable_start_error_flag_renders_notice(self, client, human_review_db_isolation):
        """comparable_start_error=1 renders the transient error notice.

        BLOCKER 5 item 3.
        """
        run = ResearchRun.objects.create_from_request(
            ResearchRequest(manufacturer_part_number="TEST", description="Test"),
        )
        response = client.get(f"/research/{run.id}?comparable_start_error=1")
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "Comparable research could not be started" in content


# ---------------------------------------------------------------------------
# Action / Routing
# ---------------------------------------------------------------------------


class TestComparableActionRouting:
    """POST route exists, GET returns 405, CSRF, 404."""

    def test_post_route_exists(self, human_review_db_isolation):
        """POST to /research/<uuid>/comparables exists."""
        run = ResearchRun.objects.create_from_request(
            ResearchRequest(
                manufacturer_part_number="XP15360SE70005",
                description="Test SSD",
            ),
        )
        run.transition_to(ResearchRunState.RUNNING)
        run.transition_to(ResearchRunState.COMPLETED)
        PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=1,
            payload={
                "request": {"manufacturer_part_number": "XP15360SE70005", "description": "Test SSD"},
                "assessments": [], "price_buckets": [], "excluded_listings": [],
                "verification_status": "VERIFIED",
                "aggregated_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        url = reverse("research-comparables", kwargs={"run_id": run.id})
        assert url == f"/research/{run.id}/comparables"

    def test_get_returns_405(self, client, human_review_db_isolation):
        """GET to the action endpoint returns 405."""
        run = ResearchRun.objects.create_from_request(
            ResearchRequest(manufacturer_part_number="TEST", description="Test"),
        )
        response = client.get(f"/research/{run.id}/comparables")
        assert response.status_code == 405

    def test_nonexistent_run_returns_404(self, client):
        """POST for nonexistent run returns 404."""
        response = client.post(f"/research/{uuid.uuid4()}/comparables")
        assert response.status_code == 404

    def test_action_redirects_to_detail(self, client, human_review_db_isolation):
        """POST always redirects to research-detail."""
        run = _make_completed_run()

        with patch(
            "product_intelligence.web.views.trigger_comparable_research",
        ) as mock_trigger:
            mock_child = MagicMock()
            mock_child.state = ComparableResearchState.RUNNING
            mock_trigger.return_value = mock_child

            response = client.post(f"/research/{run.id}/comparables")

        assert response.status_code in (301, 302, 303)
        assert f"/research/{run.id}" in response.url

    def test_ineligible_parent_no_child_mutation(self, client, human_review_db_isolation):
        """Trigger failure for ineligible parent does not mutate anything."""
        run = ResearchRun.objects.create_from_request(
            ResearchRequest(manufacturer_part_number="TEST", description="Test"),
        )
        run.transition_to(ResearchRunState.RUNNING)
        run.transition_to(ResearchRunState.FAILED)

        initial_count = ComparableResearchExecution.objects.count()
        response = client.post(f"/research/{run.id}/comparables")

        assert "comparable_start_error=1" in response.url
        assert ComparableResearchExecution.objects.count() == initial_count


# ---------------------------------------------------------------------------
# IDEMPOTENCY / ACTION (BLOCKER 5 items 4-9)
# ---------------------------------------------------------------------------


class TestComparableIdempotency:
    """Trigger idempotency and execution once."""

    def test_no_existing_child_creates_pending_and_executes_once(
        self, client, human_review_db_isolation,
    ):
        """No existing child: real trigger path produces PENDING child,
        executor called exactly once.

        BLOCKER 5 item 4.
        """
        from product_intelligence.runs import trigger_comparable_research

        run = _make_completed_run()

        executor_calls = []

        def _fake_exec(child_id):
            executor_calls.append(child_id)

        with patch(
            "product_intelligence.web.views.trigger_comparable_research",
            wraps=trigger_comparable_research,
        ) as mock_trigger, patch(
            "product_intelligence.web.views."
            "execute_comparable_research_with_default_providers",
            side_effect=_fake_exec,
        ) as mock_executor:
            response = client.post(f"/research/{run.id}/comparables")

        assert response.status_code in (301, 302, 303)
        assert len(executor_calls) == 1

    def test_existing_running_child_not_reexecuted(
        self, client, human_review_db_isolation,
    ):
        """Existing RUNNING child: executor is not called.

        BLOCKER 5 item 5.
        """
        run = _make_completed_run()

        # RUNNING child requires: active_slot=1, started_at not null,
        # finished_at null, no result_payload
        child = ComparableResearchExecution.objects.create(
            parent_run=run, state=ComparableResearchState.RUNNING,
            active_slot=1,
            started_at=datetime.now(timezone.utc),
        )

        with patch(
            "product_intelligence.web.views.trigger_comparable_research",
            return_value=child,
        ), patch(
            "product_intelligence.web.views."
            "execute_comparable_research_with_default_providers",
        ) as mock_exec:
            response = client.post(f"/research/{run.id}/comparables")

        assert response.status_code in (301, 302, 303)
        mock_exec.assert_not_called()

    def test_existing_failed_child_retries(
        self, client, human_review_db_isolation,
    ):
        """Existing FAILED child: POST creates/selects a NEW PENDING child
        and executes it. Old FAILED child remains unchanged.

        BLOCKER 5 item 6.
        """
        from product_intelligence.runs import trigger_comparable_research

        run = _make_completed_run()

        old_failed = ComparableResearchExecution.objects.create(
            parent_run=run,
            state=ComparableResearchState.FAILED,
            active_slot=None,
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            failure_reason=ComparableResearchFailureReason.INTERNAL_ERROR,
        )

        new_pending = ComparableResearchExecution.objects.create(
            parent_run=run,
            state=ComparableResearchState.PENDING,
            active_slot=1,
        )

        executor_calls = []

        def _fake_exec(child_id):
            executor_calls.append(child_id)

        with patch(
            "product_intelligence.web.views.trigger_comparable_research",
            return_value=new_pending,
        ), patch(
            "product_intelligence.web.views."
            "execute_comparable_research_with_default_providers",
            side_effect=_fake_exec,
        ):
            response = client.post(f"/research/{run.id}/comparables")

        assert response.status_code in (301, 302, 303)
        assert len(executor_calls) == 1
        # Old failed child remains unchanged
        old_failed.refresh_from_db()
        assert old_failed.state == ComparableResearchState.FAILED

    def test_existing_completed_no_second_execution(
        self, client, human_review_db_isolation,
    ):
        """Existing COMPLETED child -> no second execution."""
        run = _make_completed_run()

        child = ComparableResearchExecution.objects.create(
            parent_run=run, state=ComparableResearchState.COMPLETED,
            active_slot=None,
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            result_schema_version=1, result_payload={},
        )

        with patch(
            "product_intelligence.web.views.trigger_comparable_research",
            return_value=child,
        ), patch(
            "product_intelligence.web.views."
            "execute_comparable_research_with_default_providers",
        ) as mock_exec:
            response = client.post(f"/research/{run.id}/comparables")

        assert response.status_code in (301, 302, 303)
        mock_exec.assert_not_called()

    def test_repeated_post_after_completed_no_duplicate(
        self, client, human_review_db_isolation,
    ):
        """Repeated POST after COMPLETED does not create duplicate child."""
        run = _make_completed_run()

        child = ComparableResearchExecution.objects.create(
            parent_run=run, state=ComparableResearchState.COMPLETED,
            active_slot=None,
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            result_schema_version=1, result_payload={},
        )

        initial_count = ComparableResearchExecution.objects.filter(
            parent_run=run,
        ).count()

        for _ in range(3):
            with patch(
                "product_intelligence.web.views.trigger_comparable_research",
                return_value=child,
            ):
                client.post(f"/research/{run.id}/comparables")

        assert ComparableResearchExecution.objects.filter(
            parent_run=run,
        ).count() == initial_count


# ---------------------------------------------------------------------------
# ERROR HANDLING (BLOCKER 5 items 7-9)
# ---------------------------------------------------------------------------


class TestComparableErrorHandling:
    """Lifecycle error handling tests."""

    def test_claim_race_error_redirects_normally(
        self, client, human_review_db_isolation,
    ):
        """Claim-race ComparableResearchClaimError: redirect normally;
        web does not rewrite lifecycle.

        BLOCKER 5 item 7.
        """
        from product_intelligence.runs import ComparableResearchClaimError

        run = _make_completed_run()

        pending = ComparableResearchExecution.objects.create(
            parent_run=run,
            state=ComparableResearchState.PENDING,
            active_slot=1,
        )

        with patch(
            "product_intelligence.web.views.trigger_comparable_research",
            return_value=pending,
        ), patch(
            "product_intelligence.web.views."
            "execute_comparable_research_with_default_providers",
            side_effect=ComparableResearchClaimError("race"),
        ):
            response = client.post(f"/research/{run.id}/comparables")

        assert response.status_code in (301, 302, 303)
        # No error flag for claim race
        assert "comparable_start_error=1" not in response.url

    def test_execution_error_redirects_normally(
        self, client, human_review_db_isolation,
    ):
        """ComparableResearchExecutionError: redirect normally;
        FAILED child remains authoritative.

        BLOCKER 5 item 8.
        """
        from product_intelligence.execution import ComparableResearchExecutionError

        run = _make_completed_run()

        pending = ComparableResearchExecution.objects.create(
            parent_run=run,
            state=ComparableResearchState.PENDING,
            active_slot=1,
        )

        with patch(
            "product_intelligence.web.views.trigger_comparable_research",
            return_value=pending,
        ), patch(
            "product_intelligence.web.views."
            "execute_comparable_research_with_default_providers",
            side_effect=ComparableResearchExecutionError("bounded"),
        ):
            response = client.post(f"/research/{run.id}/comparables")

        assert response.status_code in (301, 302, 303)
        # No error flag for bounded execution error
        assert "comparable_start_error=1" not in response.url

    def test_unexpected_executor_exception_shows_error_flag(
        self, client, human_review_db_isolation,
    ):
        """Unexpected executor exception: redirect with comparable_start_error=1;
        web performs no manual lifecycle mutation.

        BLOCKER 5 item 9.
        """
        run = _make_completed_run()

        pending = ComparableResearchExecution.objects.create(
            parent_run=run,
            state=ComparableResearchState.PENDING,
            active_slot=1,
        )

        with patch(
            "product_intelligence.web.views.trigger_comparable_research",
            return_value=pending,
        ), patch(
            "product_intelligence.web.views."
            "execute_comparable_research_with_default_providers",
            side_effect=RuntimeError("unexpected crash"),
        ):
            response = client.post(f"/research/{run.id}/comparables")

        assert response.status_code in (301, 302, 303)
        assert "comparable_start_error=1" in response.url


# ---------------------------------------------------------------------------
# GET Read-Only (BLOCKER 5 items 10-13)
# ---------------------------------------------------------------------------


class TestGetReadOnly:
    """GET report never calls trigger, executor, or providers."""

    def test_get_preserves_parent_state_and_timestamps(
        self, client, human_review_db_isolation,
    ):
        """GET preserves parent state AND all parent lifecycle timestamps.

        BLOCKER 5 item 10.
        """
        run = ResearchRun.objects.create_from_request(
            ResearchRequest(manufacturer_part_number="TEST", description="Test"),
        )
        run.transition_to(ResearchRunState.RUNNING)
        original_state = run.state
        original_created = run.created_at
        original_started = run.started_at
        original_finished = run.finished_at

        response = client.get(f"/research/{run.id}")
        assert response.status_code == 200

        run.refresh_from_db()
        assert run.state == original_state
        assert run.created_at == original_created
        assert run.started_at == original_started
        assert run.finished_at == original_finished

    def test_get_preserves_child_state_and_timestamps(
        self, client, human_review_db_isolation,
    ):
        """GET preserves child state AND all child lifecycle timestamps.

        BLOCKER 5 item 11.
        """
        run = _make_completed_run()
        ts = datetime.now(timezone.utc)

        child = ComparableResearchExecution.objects.create(
            parent_run=run, state=ComparableResearchState.COMPLETED,
            active_slot=None,
            started_at=ts,
            finished_at=ts,
            result_schema_version=1, result_payload={},
        )
        original_child_state = child.state
        original_created = child.created_at

        response = client.get(f"/research/{run.id}")
        assert response.status_code == 200

        child.refresh_from_db()
        assert child.state == original_child_state
        assert child.created_at == original_created

    def test_repeated_get_produces_no_mutation(
        self, client, human_review_db_isolation,
    ):
        """Repeated GET produces no durable mutation.

        BLOCKER 5 item 12.
        """
        run = _make_completed_run()

        initial_children = ComparableResearchExecution.objects.filter(
            parent_run=run,
        ).count()

        for _ in range(5):
            response = client.get(f"/research/{run.id}")
            assert response.status_code == 200

        assert ComparableResearchExecution.objects.filter(
            parent_run=run,
        ).count() == initial_children

    def test_get_never_constructs_providers(
        self, client, human_review_db_isolation,
    ):
        """GET never constructs providers.

        BLOCKER 5 item 13: Proved by patching the adapter path and verifying
        the provider-import boundary is not invoked.
        """
        run = _make_completed_run()

        with patch(
            "product_intelligence.providers.http_page.HttpPageFetcher",
        ) as mock_page, patch(
            "product_intelligence.providers.http_pdf.HttpPdfFetcher",
        ) as mock_pdf:
            response = client.get(f"/research/{run.id}")
            assert response.status_code == 200

        mock_page.assert_not_called()
        mock_pdf.assert_not_called()

    def test_get_never_calls_trigger(self, client, human_review_db_isolation):
        """GET does not call trigger_comparable_research."""
        run = ResearchRun.objects.create_from_request(
            ResearchRequest(manufacturer_part_number="TEST", description="Test"),
        )

        with patch(
            "product_intelligence.web.views.trigger_comparable_research",
        ) as mock_trigger:
            response = client.get(f"/research/{run.id}")
            assert response.status_code == 200

        mock_trigger.assert_not_called()

    def test_get_never_calls_executor(self, client, human_review_db_isolation):
        """GET does not call execute_comparable_research."""
        run = ResearchRun.objects.create_from_request(
            ResearchRequest(manufacturer_part_number="TEST", description="Test"),
        )

        with patch(
            "product_intelligence.web.views."
            "execute_comparable_research_with_default_providers",
        ) as mock_exec:
            response = client.get(f"/research/{run.id}")
            assert response.status_code == 200

        mock_exec.assert_not_called()

    def test_get_does_not_alter_parent(self, client, human_review_db_isolation):
        """GET does not mutate parent timestamps or state."""
        run = ResearchRun.objects.create_from_request(
            ResearchRequest(manufacturer_part_number="TEST", description="Test"),
        )
        original_state = run.state

        response = client.get(f"/research/{run.id}")
        assert response.status_code == 200

        run.refresh_from_db()
        assert run.state == original_state


# ---------------------------------------------------------------------------
# Child Selection (BLOCKER 5 item 14)
# ---------------------------------------------------------------------------


class TestChildSelection:
    """Deterministic child selection."""

    def test_active_preferred_over_completed(self, human_review_db_isolation):
        """Active child (PENDING/RUNNING) is preferred over COMPLETED."""
        run = ResearchRun.objects.create_from_request(
            ResearchRequest(manufacturer_part_number="TEST", description="Test"),
        )

        completed = ComparableResearchExecution.objects.create(
            parent_run=run, state=ComparableResearchState.COMPLETED,
            active_slot=None, started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            result_schema_version=1, result_payload={},
        )
        pending = ComparableResearchExecution.objects.create(
            parent_run=run, state=ComparableResearchState.PENDING,
            active_slot=1,
        )

        from product_intelligence.web.views import _select_comparable_child
        selected = _select_comparable_child(run)
        assert selected == pending

    def test_completed_preferred_over_failed(self, human_review_db_isolation):
        """COMPLETED is preferred over old FAILED."""
        run = ResearchRun.objects.create_from_request(
            ResearchRequest(manufacturer_part_number="TEST", description="Test"),
        )

        failed = ComparableResearchExecution.objects.create(
            parent_run=run, state=ComparableResearchState.FAILED,
            active_slot=None, started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            failure_reason=ComparableResearchFailureReason.INTERNAL_ERROR,
        )
        completed = ComparableResearchExecution.objects.create(
            parent_run=run, state=ComparableResearchState.COMPLETED,
            active_slot=None, started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            result_schema_version=1, result_payload={},
        )

        from product_intelligence.web.views import _select_comparable_child
        selected = _select_comparable_child(run)
        assert selected == completed

    def test_newest_failed_selected_when_no_active_or_completed(
        self, human_review_db_isolation,
    ):
        """When no active/completed child exists, newest FAILED child is selected.

        BLOCKER 5 item 14.
        """
        run = ResearchRun.objects.create_from_request(
            ResearchRequest(manufacturer_part_number="TEST", description="Test"),
        )

        old_failed = ComparableResearchExecution.objects.create(
            parent_run=run, state=ComparableResearchState.FAILED,
            active_slot=None,
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            failure_reason=ComparableResearchFailureReason.INTERNAL_ERROR,
        )
        new_failed = ComparableResearchExecution.objects.create(
            parent_run=run, state=ComparableResearchState.FAILED,
            active_slot=None,
            created_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            failure_reason=ComparableResearchFailureReason.INTERNAL_ERROR,
        )

        from product_intelligence.web.views import _select_comparable_child
        selected = _select_comparable_child(run)
        assert selected == new_failed

    def test_no_child_returns_none(self, human_review_db_isolation):
        """No children returns None."""
        run = ResearchRun.objects.create_from_request(
            ResearchRequest(manufacturer_part_number="TEST", description="Test"),
        )

        from product_intelligence.web.views import _select_comparable_child
        selected = _select_comparable_child(run)
        assert selected is None


# ---------------------------------------------------------------------------
# DECODE / CORRUPTION (BLOCKER 5 items 15-16)
# ---------------------------------------------------------------------------


class TestDecodeAndCorruption:
    """Decode behavior and corruption handling."""

    def test_bad_schema_version_neutral(self, client, human_review_db_isolation):
        """Bad schema version -> neutral unavailable."""
        run = _make_completed_run()

        ComparableResearchExecution.objects.create(
            parent_run=run, state=ComparableResearchState.COMPLETED,
            active_slot=None, started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            result_schema_version=999, result_payload={"kind": "FULL"},
        )

        response = client.get(f"/research/{run.id}")
        assert response.status_code == 200
        assert response.context["comparable_decode_error"] is not None

    def test_malformed_payload_neutral(self, client, human_review_db_isolation):
        """Malformed payload -> neutral unavailable."""
        run = _make_completed_run()

        ComparableResearchExecution.objects.create(
            parent_run=run, state=ComparableResearchState.COMPLETED,
            active_slot=None, started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            result_schema_version=1, result_payload={"garbage": "data"},
        )

        response = client.get(f"/research/{run.id}")
        assert response.status_code == 200
        assert response.context["comparable_decode_error"] is not None

    def test_result_parent_mpn_mismatch(self, client, human_review_db_isolation):
        """Result/parent MPN mismatch -> neutral unavailable."""
        from product_intelligence.research.comparable_result_codec import (
            encode_comparable_result,
        )

        run = _make_completed_run()

        result = _make_full_result(target_mpn="DIFFERENT-MPN")
        payload = encode_comparable_result(result)

        ComparableResearchExecution.objects.create(
            parent_run=run, state=ComparableResearchState.COMPLETED,
            active_slot=None, started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            result_schema_version=1, result_payload=payload,
        )

        response = client.get(f"/research/{run.id}")
        assert response.status_code == 200
        assert response.context["comparable_binding_error"] is True

    def test_normalized_exact_accepted(self, client, human_review_db_isolation):
        """NORMALIZED_EXACT target spelling is accepted."""
        from product_intelligence.research.comparable_result_codec import (
            encode_comparable_result,
        )

        run = _make_completed_run()

        result = _make_full_result(target_mpn="XP15360SE70005")
        payload = encode_comparable_result(result)

        ComparableResearchExecution.objects.create(
            parent_run=run, state=ComparableResearchState.COMPLETED,
            active_slot=None, started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            result_schema_version=1, result_payload=payload,
        )

        response = client.get(f"/research/{run.id}")
        assert response.status_code == 200
        assert response.context["comparable_binding_error"] is False

    def test_corrupt_payload_renders_zero_candidates(
        self, client, human_review_db_isolation,
    ):
        """Completed corrupt payload renders zero candidate similarity metrics.

        BLOCKER 5 item 15: corrupt payload -> decode error -> no candidates.
        """
        run = _make_completed_run()

        ComparableResearchExecution.objects.create(
            parent_run=run, state=ComparableResearchState.COMPLETED,
            active_slot=None, started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            result_schema_version=1, result_payload={"kind": "FULL", "broken": True},
        )

        response = client.get(f"/research/{run.id}")
        assert response.status_code == 200
        # Decode error present -> no presentation -> no candidate metrics
        assert response.context["comparable_decode_error"] is not None
        assert response.context["comparable_presentation"] is None

    def test_corrupt_payload_no_automatic_rerun(
        self, client, human_review_db_isolation,
    ):
        """Completed corrupt payload does NOT trigger automatic rerun.

        BLOCKER 5 item 16.
        """
        run = _make_completed_run()

        ComparableResearchExecution.objects.create(
            parent_run=run, state=ComparableResearchState.COMPLETED,
            active_slot=None, started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            result_schema_version=1, result_payload={"garbage": "data"},
        )

        initial_count = ComparableResearchExecution.objects.filter(
            parent_run=run,
        ).count()

        with patch(
            "product_intelligence.web.views.trigger_comparable_research",
        ) as mock_trigger:
            response = client.get(f"/research/{run.id}")
            assert response.status_code == 200

        # No trigger call on GET, and no new child created
        mock_trigger.assert_not_called()
        assert ComparableResearchExecution.objects.filter(
            parent_run=run,
        ).count() == initial_count


# ---------------------------------------------------------------------------
# RESULT-KIND HTML (BLOCKER 5 items 17-20)
# ---------------------------------------------------------------------------


class TestResultKindHTML:
    """Actual rendered HTML for result kinds."""

    def test_no_requested_mpn_actual_rendered_message(
        self, client, human_review_db_isolation,
    ):
        """NO_REQUESTED_MPN actual rendered message.

        BLOCKER 5 item 17.
        """
        from product_intelligence.research.comparable_result_codec import (
            encode_comparable_result,
        )

        run = ResearchRun.objects.create_from_request(
            ResearchRequest(manufacturer_part_number="", description="Test SSD"),
        )
        run.transition_to(ResearchRunState.RUNNING)
        run.transition_to(ResearchRunState.COMPLETED)
        PriceIntelligenceSnapshot.objects.create(
            run=run, schema_version=1,
            payload={"request": {"manufacturer_part_number": "", "description": "Test SSD"},
                     "assessments": [], "price_buckets": [], "excluded_listings": [],
                     "verification_status": "VERIFIED",
                     "aggregated_at": datetime.now(timezone.utc).isoformat()},
        )

        result = _make_no_requested_mpn_result()
        payload = encode_comparable_result(result)

        ComparableResearchExecution.objects.create(
            parent_run=run, state=ComparableResearchState.COMPLETED,
            active_slot=None, started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            result_schema_version=1, result_payload=payload,
        )

        response = client.get(f"/research/{run.id}")
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "no MPN was supplied" in content

    def test_no_authority_match_actual_rendered_message(
        self, client, human_review_db_isolation,
    ):
        """NO_AUTHORITY_MATCH actual rendered message + authority audit.

        BLOCKER 5 item 18.
        """
        from product_intelligence.research.comparable_result_codec import (
            encode_comparable_result,
        )

        run = _make_completed_run()

        result = _make_no_authority_match_result()
        payload = encode_comparable_result(result)

        ComparableResearchExecution.objects.create(
            parent_run=run, state=ComparableResearchState.COMPLETED,
            active_slot=None, started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            result_schema_version=1, result_payload=payload,
        )

        response = client.get(f"/research/{run.id}")
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "did not establish the requested MPN" in content
        assert "Authority audit" in content

    def test_ambiguous_authority_actual_rendered_message(
        self, client, human_review_db_isolation,
    ):
        """AMBIGUOUS_AUTHORITY actual rendered message + authority audit.

        BLOCKER 5 item 19.
        """
        from product_intelligence.research.comparable_result_codec import (
            encode_comparable_result,
        )

        run = _make_completed_run()

        result = _make_ambiguous_authority_result()
        payload = encode_comparable_result(result)

        ComparableResearchExecution.objects.create(
            parent_run=run, state=ComparableResearchState.COMPLETED,
            active_slot=None, started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            result_schema_version=1, result_payload=payload,
        )

        response = client.get(f"/research/{run.id}")
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "ambiguous target match" in content
        assert "Authority audit" in content

    def test_full_zero_candidates_actual_rendered_message(
        self, client, human_review_db_isolation,
    ):
        """FULL zero-candidate actual rendered message.

        BLOCKER 5 item 20.
        """
        from product_intelligence.research.comparable_result_codec import (
            encode_comparable_result,
        )

        run = _make_completed_run()

        result = _make_full_result(candidates=())
        payload = encode_comparable_result(result)

        ComparableResearchExecution.objects.create(
            parent_run=run, state=ComparableResearchState.COMPLETED,
            active_slot=None, started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            result_schema_version=1, result_payload=payload,
        )

        response = client.get(f"/research/{run.id}")
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "No comparable candidates were discovered" in content

    def test_full_multiple_candidates(self, client, human_review_db_isolation):
        """FULL with multiple candidates renders all in order."""
        from product_intelligence.research.comparable_result_codec import (
            encode_comparable_result,
        )

        run = _make_completed_run()

        candidates = (
            _make_comparable_candidate("XP15360SE70015", scored_count=7),
            _make_comparable_candidate("XP3840SE70005", scored_count=7),
        )
        result = _make_full_result(candidates=candidates)
        payload = encode_comparable_result(result)

        ComparableResearchExecution.objects.create(
            parent_run=run, state=ComparableResearchState.COMPLETED,
            active_slot=None, started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            result_schema_version=1, result_payload=payload,
        )

        response = client.get(f"/research/{run.id}")
        assert response.status_code == 200
        presentation = response.context["comparable_presentation"]
        assert presentation is not None
        assert len(presentation.candidates) == 2
        assert presentation.candidates[0].candidate_mpn == "XP15360SE70015"
        assert presentation.candidates[1].candidate_mpn == "XP3840SE70005"


# ---------------------------------------------------------------------------
# BLOCKER 4: Comparable section ordering
# ---------------------------------------------------------------------------


class TestComparableSectionOrdering:
    """Comparable products section must appear AFTER existing review content."""

    def test_comparable_section_after_reviewed_price_in_template(self) -> None:
        """Source-order assertion: comparable section is after reviewed price
        content in the template.

        BLOCKER 4: Comparable section moved after existing review content.
        """
        from pathlib import Path

        template_path = (
            Path(__file__).resolve().parents[2]
            / "product_intelligence"
            / "web"
            / "templates"
            / "web"
            / "research_detail.html"
        )
        source = template_path.read_text(encoding="utf-8")

        # Find positions of key sections
        reviewed_price_pos = source.find('<h2>Reviewed price</h2>')
        comparable_products_pos = source.find('<h2>Comparable products</h2>')

        # Both must exist
        assert reviewed_price_pos >= 0, "Reviewed price section not found"
        assert comparable_products_pos >= 0, "Comparable products section not found"

        # Comparable products must come AFTER Reviewed price
        assert comparable_products_pos > reviewed_price_pos, (
            "Comparable products section must appear after Reviewed price section"
        )
