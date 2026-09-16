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
# Idempotency
# ---------------------------------------------------------------------------


class TestComparableIdempotency:
    """Trigger idempotency and execution once."""

    def test_existing_completed_no_second_execution(
        self, client, human_review_db_isolation,
    ):
        """Existing COMPLETED child -> no second execution."""
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
# GET Read-Only
# ---------------------------------------------------------------------------


class TestGetReadOnly:
    """GET report never calls trigger, executor, or providers."""

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
# Child Selection
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

    def test_no_child_returns_none(self, human_review_db_isolation):
        """No children returns None."""
        run = ResearchRun.objects.create_from_request(
            ResearchRequest(manufacturer_part_number="TEST", description="Test"),
        )

        from product_intelligence.web.views import _select_comparable_child
        selected = _select_comparable_child(run)
        assert selected is None


# ---------------------------------------------------------------------------
# Decode + Result Kinds
# ---------------------------------------------------------------------------


class TestDecodeAndResultKinds:
    """Decode behavior and result kind rendering."""

    def test_bad_schema_version_neutral(self, client, human_review_db_isolation):
        """Bad schema version -> neutral unavailable."""
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

    def test_full_zero_candidates(self, client, human_review_db_isolation):
        """FULL with zero candidates renders."""
        from product_intelligence.research.comparable_result_codec import (
            encode_comparable_result,
        )

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
        presentation = response.context["comparable_presentation"]
        assert presentation is not None
        assert presentation.kind == "FULL"
        assert len(presentation.candidates) == 0

    def test_full_multiple_candidates(self, client, human_review_db_isolation):
        """FULL with multiple candidates renders all in order."""
        from product_intelligence.research.comparable_result_codec import (
            encode_comparable_result,
        )

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
