"""Tests for the human review web interface.

PRODUCT-INTEL.HUMAN-REVIEW.

Validates:
- GET detail renders AI-assisted candidate evidence
- POST confirm/reject/undo work through public review service
- POST redirects back to detail
- GET to review endpoint is rejected
- Cross-run candidate fails closed
- CSRF remains enabled
- Machine Price and Reviewed Price shown separately
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from django.test import Client
from django.urls import reverse

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import ResearchRunState
from product_intelligence.research.aggregation import PriceAggregationExclusionReason

from product_intelligence.runs.models import (
    AiAssistedReviewCandidate,
    PriceIntelligenceSnapshot,
    ResearchRun,
)

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client() -> Client:
    return Client()


@pytest.fixture
def completed_run_with_candidate(human_review_db_isolation) -> tuple[ResearchRun, AiAssistedReviewCandidate]:
    """A completed run with one review candidate and a V1-encoded real snapshot.

    The snapshot is built through actual research contracts so POST boundary
    decoding succeeds.  The candidate's binding fields exactly match the
    single semantic-eligible REJECTED assessment in the snapshot.

    Frozen FU3B semantics: the persisted assessment is the ORIGINAL deterministic
    REJECTED (not AI_ASSISTED_MATCH). The candidate exists as separate semantic
    authority mapped to that assessment.
    """
    from product_intelligence.research.aggregation import aggregate_listing_prices
    from product_intelligence.research.price_result_codec import (
        PRICE_RESULT_SCHEMA_VERSION,
        encode_price_aggregation_result,
    )
    from product_intelligence.research.matching import (
        EvidenceSource,
        IdentityRejectionReason,
        ListingIdentityAssessment,
    )
    from product_intelligence.research.normalization import (
        NormalizedAvailability,
        NormalizedCondition,
        NormalizedListingObservation,
    )
    from product_intelligence.research.listings import (
        ExtractionMethod,
        ListingObservation,
    )
    from product_intelligence.domain.enums import (
        EvidenceDecision,
        IdentityMatchType,
    )
    from decimal import Decimal

    request = ResearchRequest(
        manufacturer_part_number="TEST-001",
        description="Test product",
    )
    run = ResearchRun.objects.create_from_request(request)
    run.transition_to(ResearchRunState.RUNNING)
    run.transition_to(ResearchRunState.COMPLETED)

    # Build a REAL FU3B snapshot assessment:
    #   REJECTED + NO_EXPLICIT_MPN_EVIDENCE + TITLE_TEXT
    #
    # Evidence-source derivation (matching.py _find_evidence):
    #   Priority: EXPLICIT_MPN_FIELD > SKU_FIELD > TITLE_TEXT > NONE
    #   With manufacturer_part_number_text="", sku_text=None, and
    #   product_title="Test product for TEST-001", the strongest evidence
    #   is TITLE_TEXT (MPN token found in title).
    #
    # The assessment declares REJECTED (frozen deterministic result) with
    # NO_EXPLICIT_MPN_EVIDENCE reason and TITLE_TEXT source.
    # The candidate record is the separate semantic MATCH authority.
    obs = ListingObservation(
        source_url="https://example.com/product/1",
        extraction_method=ExtractionMethod.JSON_LD,
        manufacturer_part_number_text="",
        sku_text=None,
        product_title="Test product for TEST-001",
        price_text="99.99",
        currency_text="USD",
        condition_text="new",
    )
    norm = NormalizedListingObservation(
        observation=obs,
        price_amount=Decimal("99.99"),
        currency_code="USD",
        condition=NormalizedCondition.NEW,
        availability=NormalizedAvailability.UNKNOWN,
        seller_name="Test Seller",
        normalization_issues=(),
    )
    assessment = ListingIdentityAssessment(
        normalized_listing=norm,
        requested_part_number="TEST-001",
        candidate_part_number_raw="TEST-001",
        candidate_part_number_compared="TEST-001",
        candidate_evidence_source=EvidenceSource.TITLE_TEXT,
        match_type=IdentityMatchType.UNKNOWN,
        decision=EvidenceDecision.REJECTED,
        rejection_reason=IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE,
    )

    price_result = aggregate_listing_prices(request, (assessment,))
    payload = encode_price_aggregation_result(price_result)
    PriceIntelligenceSnapshot.objects.create(
        run=run,
        schema_version=PRICE_RESULT_SCHEMA_VERSION,
        payload=payload,
    )

    # Candidate binding exactly matches the snapshot assessment.
    # candidate_mpn_field is observation.manufacturer_part_number_text (""),
    # not the candidate_part_number_raw ("TEST-001") — those are different
    # fields with different provenance.
    candidate = AiAssistedReviewCandidate.objects.create(
        run=run,
        assessment_index=0,
        source_url=obs.source_url,
        target_mpn=request.manufacturer_part_number,
        target_description=request.description,
        candidate_title=obs.product_title or "",
        candidate_mpn_field=obs.manufacturer_part_number_text or "",
        candidate_sku=obs.sku_text or "",
        evidence_source="TITLE_TEXT",
        actual_provider="amax",
        actual_model="nemotron-3-super",
        prompt_version="v1.1",
    )
    return run, candidate


# ---------------------------------------------------------------------------
# GET detail tests
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("human_review_db_isolation")
class TestDetailPage:
    def test_get_detail_shows_review_candidates(
        self, client: Client, completed_run_with_candidate
    ) -> None:
        """GET detail renders AI-assisted candidate evidence."""
        run, candidate = completed_run_with_candidate
        url = reverse("research-detail", kwargs={"run_id": run.id})
        response = client.get(url)
        assert response.status_code == 200
        # The candidate should be in the context (even if decoded_result is None)
        candidates = response.context.get("review_candidates")
        assert candidates is not None
        assert len(candidates) == 1
        assert candidates[0].candidate_id == str(candidate.id)

    def test_get_detail_shows_unreviewed_state(
        self, client: Client, completed_run_with_candidate
    ) -> None:
        """Unreviewed candidate shows in UNREVIEWED state."""
        run, candidate = completed_run_with_candidate
        url = reverse("research-detail", kwargs={"run_id": run.id})
        response = client.get(url)
        assert response.status_code == 200
        # Check through context
        candidates = response.context.get("review_candidates")
        assert candidates is not None
        assert candidates[0].review_state == AiAssistedReviewCandidate.REVIEW_STATE_UNREVIEWED

    def test_get_detail_no_candidates_when_none_exist(
        self, client: Client
    ) -> None:
        """Detail page works without review candidates."""
        request = ResearchRequest(
            manufacturer_part_number="TEST-001",
            description="Test product",
        )
        run = ResearchRun.objects.create_from_request(request)
        run.transition_to(ResearchRunState.RUNNING)
        run.transition_to(ResearchRunState.COMPLETED)
        PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=1,
            payload={
                "request": {
                    "manufacturer_part_number": "TEST-001",
                    "description": "Test product",
                },
                "assessments": [],
                "exclusions": [],
                "buckets": [],
                "verification_status": "UNKNOWN",
            },
        )
        url = reverse("research-detail", kwargs={"run_id": run.id})
        response = client.get(url)
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# POST review tests
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("human_review_db_isolation")
class TestReviewActions:
    def test_post_confirm_redirects_to_detail(
        self, client: Client, completed_run_with_candidate
    ) -> None:
        """POST confirm redirects back to detail page."""
        run, candidate = completed_run_with_candidate
        url = reverse(
            "research-review",
            kwargs={"run_id": run.id, "candidate_id": candidate.id},
        )
        response = client.post(url, {"action": "confirm"})
        assert response.status_code in (301, 302)
        # Redirect to detail page
        expected_url = reverse("research-detail", kwargs={"run_id": run.id})
        assert response.url == expected_url

    def test_post_confirm_changes_state(
        self, client: Client, completed_run_with_candidate
    ) -> None:
        """POST confirm actually confirms the candidate."""
        run, candidate = completed_run_with_candidate
        url = reverse(
            "research-review",
            kwargs={"run_id": run.id, "candidate_id": candidate.id},
        )
        client.post(url, {"action": "confirm"})
        candidate.refresh_from_db()
        assert candidate.review_state == AiAssistedReviewCandidate.REVIEW_STATE_CONFIRMED

    def test_post_reject_changes_state(
        self, client: Client, completed_run_with_candidate
    ) -> None:
        """POST reject actually rejects the candidate."""
        run, candidate = completed_run_with_candidate
        url = reverse(
            "research-review",
            kwargs={"run_id": run.id, "candidate_id": candidate.id},
        )
        client.post(url, {"action": "reject"})
        candidate.refresh_from_db()
        assert candidate.review_state == AiAssistedReviewCandidate.REVIEW_STATE_REJECTED

    def test_post_undo_restores_unreviewed(
        self, client: Client, completed_run_with_candidate
    ) -> None:
        """POST undo restores UNREVIEWED state."""
        run, candidate = completed_run_with_candidate
        url = reverse(
            "research-review",
            kwargs={"run_id": run.id, "candidate_id": candidate.id},
        )
        # First confirm
        client.post(url, {"action": "confirm"})
        candidate.refresh_from_db()
        assert candidate.review_state == AiAssistedReviewCandidate.REVIEW_STATE_CONFIRMED
        # Then undo
        client.post(url, {"action": "undo"})
        candidate.refresh_from_db()
        assert candidate.review_state == AiAssistedReviewCandidate.REVIEW_STATE_UNREVIEWED

    def test_get_review_endpoint_rejected(
        self, client: Client, completed_run_with_candidate
    ) -> None:
        """GET to review endpoint is rejected (require_POST)."""
        run, candidate = completed_run_with_candidate
        url = reverse(
            "research-review",
            kwargs={"run_id": run.id, "candidate_id": candidate.id},
        )
        response = client.get(url)
        assert response.status_code == 405

    def test_invalid_action_redirects(
        self, client: Client, completed_run_with_candidate
    ) -> None:
        """Invalid action redirects without error."""
        run, candidate = completed_run_with_candidate
        url = reverse(
            "research-review",
            kwargs={"run_id": run.id, "candidate_id": candidate.id},
        )
        response = client.post(url, {"action": "invalid"})
        assert response.status_code in (301, 302)
        # Candidate state should not change
        candidate.refresh_from_db()
        assert candidate.review_state == AiAssistedReviewCandidate.REVIEW_STATE_UNREVIEWED

    def test_cross_run_candidate_fails_closed(
        self, client: Client, completed_run_with_candidate
    ) -> None:
        """Candidate from another run cannot be reviewed through this run."""
        run, candidate = completed_run_with_candidate
        # Create another run to use as the "wrong" run_id
        from product_intelligence.domain import ResearchRequest as RR
        other_run = ResearchRun.objects.create_from_request(
            RR(manufacturer_part_number="OTHER", description="Other")
        )
        other_run.transition_to(ResearchRunState.RUNNING)
        other_run.transition_to(ResearchRunState.COMPLETED)
        PriceIntelligenceSnapshot.objects.create(
            run=other_run,
            schema_version=1,
            payload={"request": {}, "assessments": [], "exclusions": [], "buckets": [], "verification_status": "UNKNOWN"},
        )
        url = reverse(
            "research-review",
            kwargs={"run_id": other_run.id, "candidate_id": candidate.id},
        )
        response = client.post(url, {"action": "confirm"})
        # Should redirect (fail closed)
        assert response.status_code in (301, 302)
        # State should not change
        candidate.refresh_from_db()
        assert candidate.review_state == AiAssistedReviewCandidate.REVIEW_STATE_UNREVIEWED

    def test_nonexistent_candidate_redirects(
        self, client: Client, completed_run_with_candidate
    ) -> None:
        """Nonexistent candidate redirects without error."""
        run, _ = completed_run_with_candidate
        fake_id = uuid.uuid4()
        url = reverse(
            "research-review",
            kwargs={"run_id": run.id, "candidate_id": fake_id},
        )
        response = client.post(url, {"action": "confirm"})
        # The view redirects to the run detail page
        assert response.status_code in (301, 302)
        assert f"research/{run.id}" in response.url


# ---------------------------------------------------------------------------
# CSRF tests
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("human_review_db_isolation")
class TestCSRF:
    """Real CSRF enforcement tests."""
    def test_post_without_csrf_token_returns_403(self, completed_run_with_candidate) -> None:
        """POST review without a CSRF token must return 403."""
        from django.test import Client
        from django.test import override_settings
        run, candidate = completed_run_with_candidate
        with override_settings(ALLOWED_HOSTS=["testserver"]):
            csrf_client = Client(enforce_csrf_checks=True)
            url = reverse(
                "research-review",
                kwargs={"run_id": run.id, "candidate_id": candidate.id},
            )
            response = csrf_client.post(url, {"action": "confirm"})
            assert response.status_code == 403, (
                f"Expected 403 for POST without CSRF token, got {response.status_code}"
            )
            # Candidate state should not change
            candidate.refresh_from_db()
            assert candidate.review_state == AiAssistedReviewCandidate.REVIEW_STATE_UNREVIEWED

    def test_post_with_valid_csrf_token_succeeds(self, completed_run_with_candidate) -> None:
        """POST review with a valid CSRF token succeeds and redirects.

        The review endpoint is protected by @require_POST and Django's CSRF
        middleware. A valid POST requires both a valid CSRF cookie and a
        matching csrfmiddlewaretoken form field.

        This test exercises the full middleware stack: Client -> URL resolver
        -> CsrfViewMiddleware -> view.
        """
        from django.test import Client
        from django.test import override_settings
        run, candidate = completed_run_with_candidate
        with override_settings(ALLOWED_HOSTS=["testserver"]):
            csrf_client = Client(enforce_csrf_checks=True)
            # GET the intake form to obtain a CSRF cookie
            response = csrf_client.get("/research/new")
            assert response.status_code == 200
            # The intake form sets a CSRF cookie
            token = csrf_client.cookies["csrftoken"].value
            # POST to the review endpoint with the valid CSRF token
            review_url = reverse(
                "research-review",
                kwargs={"run_id": run.id, "candidate_id": candidate.id},
            )
            response = csrf_client.post(
                review_url,
                {"action": "confirm", "csrfmiddlewaretoken": token},
            )
            assert response.status_code in (301, 302), (
                f"Expected redirect, got {response.status_code}"
            )
            candidate.refresh_from_db()
            assert candidate.review_state == AiAssistedReviewCandidate.REVIEW_STATE_CONFIRMED

class TestStateDisplay:
    def test_confirmed_state_shows_correctly(
        self, client: Client, completed_run_with_candidate
    ) -> None:
        """Confirmed candidate shows CONFIRMED state on detail page."""
        run, candidate = completed_run_with_candidate
        from product_intelligence.runs import confirm_candidate
        confirm_candidate(candidate.id)

        url = reverse("research-detail", kwargs={"run_id": run.id})
        response = client.get(url)
        assert response.status_code == 200
        # Verify through context
        candidates = response.context["review_candidates"]
        assert len(candidates) == 1
        assert candidates[0].review_state == AiAssistedReviewCandidate.REVIEW_STATE_CONFIRMED

    def test_rejected_state_shows_correctly(
        self, client: Client, completed_run_with_candidate
    ) -> None:
        """Rejected candidate shows REJECTED state on detail page."""
        run, candidate = completed_run_with_candidate
        from product_intelligence.runs import reject_candidate
        reject_candidate(candidate.id)

        url = reverse("research-detail", kwargs={"run_id": run.id})
        response = client.get(url)
        assert response.status_code == 200
        # Verify through context
        candidates = response.context["review_candidates"]
        assert len(candidates) == 1
        assert candidates[0].review_state == AiAssistedReviewCandidate.REVIEW_STATE_REJECTED



@pytest.mark.usefixtures("human_review_db_isolation")
class TestRealSnapshotWebTests:
    """End-to-end web tests with real snapshot encoding."""

    @pytest.fixture
    def run_with_real_snapshot(self) -> tuple[ResearchRun, ...]:
        """Build a run with a properly encoded snapshot."""
        from product_intelligence.research.aggregation import (
            PriceAggregationResult,
            PriceAggregationExclusion,
        )
        from product_intelligence.research.price_result_codec import (
            encode_price_aggregation_result,
            PRICE_RESULT_SCHEMA_VERSION,
        )
        from product_intelligence.research.matching import (
            EvidenceSource,
            ListingIdentityAssessment,
            IdentityRejectionReason,
        )
        from product_intelligence.research.normalization import (
            NormalizedAvailability,
            NormalizedCondition,
            NormalizedListingObservation,
        )
        from product_intelligence.research.listings import (
            ExtractionMethod,
            ListingObservation,
        )
        from product_intelligence.domain.enums import (
            ConfidenceLevel,
            EvidenceDecision,
            IdentityMatchType,
            VerificationStatus,
        )
        from decimal import Decimal

        request = ResearchRequest(
            manufacturer_part_number="REAL-001",
            description="Real test product",
        )
        run = ResearchRun.objects.create_from_request(request)
        run.transition_to(ResearchRunState.RUNNING)
        run.transition_to(ResearchRunState.COMPLETED)

        # Build real assessments
        def _make_obs(url, price):
            return ListingObservation(
                source_url=url,
                extraction_method=ExtractionMethod.JSON_LD,
                manufacturer_part_number_text="REAL-001",
                price_text=str(price),
                currency_text="USD",
                condition_text="new",
            )

        # Deterministic ACCEPTED
        accepted_obs = _make_obs("https://example.com/accepted", Decimal("100.00"))
        accepted_norm = NormalizedListingObservation(
            observation=accepted_obs,
            price_amount=Decimal("100.00"),
            currency_code="USD",
            condition=NormalizedCondition.NEW,
            availability=NormalizedAvailability.UNKNOWN,
            seller_name="Test Seller",
            normalization_issues=(),
        )
        accepted_assessment = ListingIdentityAssessment(
            normalized_listing=accepted_norm,
            requested_part_number="REAL-001",
            candidate_part_number_raw="REAL-001",
            candidate_part_number_compared="REAL-001",
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.EXACT,
            decision=EvidenceDecision.ACCEPTED,
            rejection_reason=None,
        )

        # AI-assisted match (TITLE_TEXT evidence: MPN token found in product title).
        # Frozen FU3B semantics: this is the ORIGINAL deterministic REJECTED assessment.
        # The candidate record is the separate semantic MATCH authority.
        from product_intelligence.research.listings import ExtractionMethod as EM
        from product_intelligence.research.matching import IdentityRejectionReason
        ai_obs = ListingObservation(
            source_url="https://example.com/ai-match",
            extraction_method=EM.JSON_LD,
            manufacturer_part_number_text="",
            sku_text=None,
            price_text="110.00",
            currency_text="USD",
            condition_text="new",
            product_title="Compatible component for REAL-001",
        )
        ai_norm = NormalizedListingObservation(
            observation=ai_obs,
            price_amount=Decimal("110.00"),
            currency_code="USD",
            condition=NormalizedCondition.NEW,
            availability=NormalizedAvailability.UNKNOWN,
            seller_name="AI Seller",
            normalization_issues=(),
        )
        ai_assessment = ListingIdentityAssessment(
            normalized_listing=ai_norm,
            requested_part_number="REAL-001",
            candidate_part_number_raw="REAL-001",
            candidate_part_number_compared="REAL-001",
            candidate_evidence_source=EvidenceSource.TITLE_TEXT,
            match_type=IdentityMatchType.UNKNOWN,
            decision=EvidenceDecision.REJECTED,
            rejection_reason=IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE,
        )

        assessments = (accepted_assessment, ai_assessment)

        # Build real aggregation result
        from product_intelligence.research.aggregation import aggregate_listing_prices
        price_result = aggregate_listing_prices(request, assessments)

        # Encode and persist
        payload = encode_price_aggregation_result(price_result)
        PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=PRICE_RESULT_SCHEMA_VERSION,
            payload=payload,
        )

        # Create candidate for the AI-assisted match (index 1).
        # Candidate binding fields mirror the observation exactly.
        candidate = AiAssistedReviewCandidate.objects.create(
            run=run,
            assessment_index=1,  # Points to AI-assisted match
            source_url=ai_obs.source_url,
            target_mpn=request.manufacturer_part_number,
            target_description=request.description,
            candidate_title=ai_obs.product_title or "",
            candidate_mpn_field=ai_obs.manufacturer_part_number_text or "",
            candidate_sku=ai_obs.sku_text or "",
            evidence_source="TITLE_TEXT",
            actual_provider="amax",
            actual_model="nemotron-3-super",
            prompt_version="v1.1",
        )

        return run, candidate, price_result

    def test_machine_price_remains_deterministic(
        self, client: Client, run_with_real_snapshot
    ) -> None:
        """Machine Price shows only deterministic ACCEPTED listings."""
        run, candidate, price_result = run_with_real_snapshot
        url = reverse("research-detail", kwargs={"run_id": run.id})
        response = client.get(url)
        assert response.status_code == 200
        assert response.context.get("has_snapshot") is True
        # Machine price should be from deterministic aggregation
        report = response.context.get("report_presentation")
        assert report is not None
        # The deterministic result has 1 bucket with 1 assessment (the ACCEPTED one)
        assert len(report.buckets) == 1
        assert report.buckets[0].count == 1

    def test_confirmed_candidate_produces_reviewed_price(
        self, client: Client, run_with_real_snapshot
    ) -> None:
        """Confirming AI-assisted candidate produces a distinct Reviewed Price."""
        from product_intelligence.runs import confirm_candidate
        run, candidate, price_result = run_with_real_snapshot
        confirm_candidate(candidate.id)

        url = reverse("research-detail", kwargs={"run_id": run.id})
        response = client.get(url)
        assert response.status_code == 200
        # Reviewed price should now be available
        reviewed = response.context.get("reviewed_result")
        assert reviewed is not None, "Reviewed price should be available after confirmation"
        # It should have deterministic + human-confirmed
        assert len(reviewed.buckets) == 1
        bucket = reviewed.buckets[0]
        assert bucket.count == 2  # ACCEPTED + HUMAN_CONFIRMED
        assert bucket.deterministic_count == 1
        assert bucket.human_confirmed_count == 1

    def test_confirmed_count_shown_on_detail(
        self, client: Client, run_with_real_snapshot
    ) -> None:
        """Confirmed count is shown on detail page."""
        from product_intelligence.runs import confirm_candidate
        run, candidate, _ = run_with_real_snapshot
        confirm_candidate(candidate.id)

        url = reverse("research-detail", kwargs={"run_id": run.id})
        response = client.get(url)
        assert response.context.get("confirmed_count") == 1


# ---------------------------------------------------------------------------
# Multi-candidate confirmation test
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("human_review_db_isolation")
class TestMultiCandidateConfirmation:
    """Tests for confirming multiple AI-assisted candidates."""

    @pytest.fixture
    def run_with_two_candidates(
        self, human_review_db_isolation
    ) -> tuple[ResearchRun, AiAssistedReviewCandidate, AiAssistedReviewCandidate]:
        """A completed run with two semantic-eligible REJECTED candidates and a real snapshot.

        Candidate 0 maps to assessment 0 (source URL A).
        Candidate 1 maps to assessment 1 (source URL B).
        Both use TITLE_TEXT evidence style consistent with completed_run_with_candidate.
        Both are REJECTED + NO_EXPLICIT_MPN_EVIDENCE (frozen FU3B originals).
        """
        from product_intelligence.research.aggregation import (
            aggregate_listing_prices,
        )
        from product_intelligence.research.price_result_codec import (
            PRICE_RESULT_SCHEMA_VERSION,
            encode_price_aggregation_result,
        )
        from product_intelligence.research.matching import (
            EvidenceSource,
            IdentityRejectionReason,
            ListingIdentityAssessment,
        )
        from product_intelligence.research.normalization import (
            NormalizedAvailability,
            NormalizedCondition,
            NormalizedListingObservation,
        )
        from product_intelligence.research.listings import (
            ExtractionMethod,
            ListingObservation,
        )
        from product_intelligence.domain.enums import (
            EvidenceDecision,
            IdentityMatchType,
        )
        from decimal import Decimal

        request = ResearchRequest(
            manufacturer_part_number="TEST-MC-001",
            description="Multi-candidate test product",
        )
        run = ResearchRun.objects.create_from_request(request)
        run.transition_to(ResearchRunState.RUNNING)
        run.transition_to(ResearchRunState.COMPLETED)

        def _make_obs(source_url, price):
            return ListingObservation(
                source_url=source_url,
                extraction_method=ExtractionMethod.JSON_LD,
                manufacturer_part_number_text="",
                sku_text=None,
                product_title=f"Product listing for {request.manufacturer_part_number}",
                price_text=price,
                currency_text="USD",
                condition_text="new",
            )

        def _make_norm(obs, price):
            return NormalizedListingObservation(
                observation=obs,
                price_amount=Decimal(price),
                currency_code="USD",
                condition=NormalizedCondition.NEW,
                availability=NormalizedAvailability.UNKNOWN,
                seller_name="Test Seller",
                normalization_issues=(),
            )

        def _make_assessment(obs, normalized):
            return ListingIdentityAssessment(
                normalized_listing=normalized,
                requested_part_number=request.manufacturer_part_number,
                candidate_part_number_raw=request.manufacturer_part_number,
                candidate_part_number_compared=request.manufacturer_part_number,
                candidate_evidence_source=EvidenceSource.TITLE_TEXT,
                match_type=IdentityMatchType.UNKNOWN,
                decision=EvidenceDecision.REJECTED,
                rejection_reason=IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE,
            )

        obs0 = _make_obs("https://example.com/mc-candidate-a", "100.00")
        norm0 = _make_norm(obs0, "100.00")
        assess0 = _make_assessment(obs0, norm0)

        obs1 = _make_obs("https://example.com/mc-candidate-b", "120.00")
        norm1 = _make_norm(obs1, "120.00")
        assess1 = _make_assessment(obs1, norm1)

        price_result = aggregate_listing_prices(request, (assess0, assess1))
        payload = encode_price_aggregation_result(price_result)
        PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=PRICE_RESULT_SCHEMA_VERSION,
            payload=payload,
        )

        cand0 = AiAssistedReviewCandidate.objects.create(
            run=run,
            assessment_index=0,
            source_url=obs0.source_url,
            target_mpn=request.manufacturer_part_number,
            target_description=request.description,
            candidate_title=obs0.product_title or "",
            candidate_mpn_field=obs0.manufacturer_part_number_text or "",
            candidate_sku=obs0.sku_text or "",
            evidence_source="TITLE_TEXT",
            actual_provider="amax",
            actual_model="nemotron-3-super",
            prompt_version="v1.1",
        )
        cand1 = AiAssistedReviewCandidate.objects.create(
            run=run,
            assessment_index=1,
            source_url=obs1.source_url,
            target_mpn=request.manufacturer_part_number,
            target_description=request.description,
            candidate_title=obs1.product_title or "",
            candidate_mpn_field=obs1.manufacturer_part_number_text or "",
            candidate_sku=obs1.sku_text or "",
            evidence_source="TITLE_TEXT",
            actual_provider="amax",
            actual_model="nemotron-3-super",
            prompt_version="v1.1",
        )

        return run, cand0, cand1

    def test_confirm_two_candidates_shows_correct_counts(
        self, client: Client, run_with_two_candidates
    ) -> None:
        """Confirming both candidates shows confirmed_count==2 and human_confirmed_count==2."""
        run, cand0, cand1 = run_with_two_candidates

        # Confirm both candidates through the real web review POST endpoint
        url0 = reverse(
            "research-review",
            kwargs={"run_id": run.id, "candidate_id": cand0.id},
        )
        url1 = reverse(
            "research-review",
            kwargs={"run_id": run.id, "candidate_id": cand1.id},
        )
        response0 = client.post(url0, {"action": "confirm"})
        assert response0.status_code in (301, 302)
        response1 = client.post(url1, {"action": "confirm"})
        assert response1.status_code in (301, 302)

        # Both candidates should now be CONFIRMED
        cand0.refresh_from_db()
        cand1.refresh_from_db()
        assert cand0.review_state == AiAssistedReviewCandidate.REVIEW_STATE_CONFIRMED
        assert cand1.review_state == AiAssistedReviewCandidate.REVIEW_STATE_CONFIRMED

        # GET detail and check counts
        detail_url = reverse("research-detail", kwargs={"run_id": run.id})
        response = client.get(detail_url)
        assert response.status_code == 200

        # confirmed_count must be 2
        assert response.context.get("confirmed_count") == 2

        # reviewed_result must be present
        reviewed_result = response.context.get("reviewed_result")
        assert reviewed_result is not None

        # Bucket must show human_confirmed_count == 2
        bucket = reviewed_result.buckets[0]
        assert bucket.human_confirmed_count == 2


# ---------------------------------------------------------------------------
# Candidate binding regression tests — BLOCKER 2
# Two assessments at the SAME source_url but different title/MPN/SKU evidence.
# A candidate persisted for one assessment but pointing at the wrong assessment
# (via assessment_index) MUST fail binding and not contribute to Reviewed Price.
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("human_review_db_isolation")
class TestCandidateBindingRegression:
    """Regression tests for exact candidate -> snapshot assessment binding.

    These tests prove that a corrupt or wrong candidate binding cannot
    contribute to Reviewed Price. A candidate must match ALL deterministic
    evidence fields before it is accepted as valid.
    """

    @pytest.fixture
    def run_with_same_url_different_assessments(
        self, human_review_db_isolation
    ) -> tuple[
        ResearchRun,
        AiAssistedReviewCandidate,
    ]:
        """Two semantic-eligible REJECTED assessments at same URL, only cand0 is persisted.

        Both assessments use legal TITLE_TEXT evidence shapes (MPN token
        found in product title, no explicit MPN field, no SKU).
        Both are REJECTED + NO_EXPLICIT_MPN_EVIDENCE (frozen FU3B originals).

        Assessment 0: REJECTED at https://example.com/page
            title="Samsung REAL-001 Product", mpn_field="", sku=""
        Assessment 1: REJECTED at https://example.com/page
            title="Other REAL-001 Product", mpn_field="", sku=""

        Only cand0 (bound to index 0) is created.  cand1 is NOT created,
        so changing cand0.assessment_index to 1 does NOT hit the UNIQUE
        (run, assessment_index) constraint — it tests binding validation.
        """
        from product_intelligence.research.aggregation import (
            aggregate_listing_prices,
        )
        from product_intelligence.research.price_result_codec import (
            PRICE_RESULT_SCHEMA_VERSION,
            encode_price_aggregation_result,
        )
        from product_intelligence.research.matching import (
            EvidenceSource,
            IdentityRejectionReason,
            ListingIdentityAssessment,
        )
        from product_intelligence.research.normalization import (
            NormalizedAvailability,
            NormalizedCondition,
            NormalizedListingObservation,
        )
        from product_intelligence.research.listings import (
            ExtractionMethod,
            ListingObservation,
        )
        from product_intelligence.domain.enums import (
            EvidenceDecision,
            IdentityMatchType,
        )
        from decimal import Decimal

        request = ResearchRequest(
            manufacturer_part_number="REAL-001",
            description="Test product",
        )
        run = ResearchRun.objects.create_from_request(request)
        run.transition_to(ResearchRunState.RUNNING)
        run.transition_to(ResearchRunState.COMPLETED)

        shared_url = "https://example.com/page"

        # Both assessments are legal TITLE_TEXT shapes:
        #   manufacturer_part_number_text = ""
        #   sku_text = None
        #   product_title contains the requested MPN token
        def _make_obs(title):
            return ListingObservation(
                source_url=shared_url,
                extraction_method=ExtractionMethod.JSON_LD,
                manufacturer_part_number_text="",
                sku_text=None,
                product_title=title,
                price_text="99.99",
                currency_text="USD",
                condition_text="new",
            )

        def _make_norm(obs):
            return NormalizedListingObservation(
                observation=obs,
                price_amount=Decimal("99.99"),
                currency_code="USD",
                condition=NormalizedCondition.NEW,
                availability=NormalizedAvailability.UNKNOWN,
                seller_name="Test Seller",
                normalization_issues=(),
            )

        def _make_assessment(obs, normalized):
            return ListingIdentityAssessment(
                normalized_listing=normalized,
                requested_part_number=request.manufacturer_part_number,
                candidate_part_number_raw=request.manufacturer_part_number,
                candidate_part_number_compared=request.manufacturer_part_number,
                candidate_evidence_source=EvidenceSource.TITLE_TEXT,
                match_type=IdentityMatchType.UNKNOWN,
                decision=EvidenceDecision.REJECTED,
                rejection_reason=IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE,
            )

        obs0 = _make_obs("Samsung REAL-001 Product")
        norm0 = _make_norm(obs0)
        assess0 = _make_assessment(obs0, norm0)

        obs1 = _make_obs("Other REAL-001 Product")
        norm1 = _make_norm(obs1)
        assess1 = _make_assessment(obs1, norm1)

        assessments = (assess0, assess1)

        price_result = aggregate_listing_prices(request, assessments)

        payload = encode_price_aggregation_result(price_result)
        PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=PRICE_RESULT_SCHEMA_VERSION,
            payload=payload,
        )

        # Candidate correctly bound to assessment 0.
        # candidate_title matches obs0.product_title,
        # candidate_mpn_field = obs.manufacturer_part_number_text = "",
        # candidate_sku = obs.sku_text = None -> ""
        cand0 = AiAssistedReviewCandidate.objects.create(
            run=run,
            assessment_index=0,
            source_url=shared_url,
            target_mpn=request.manufacturer_part_number,
            target_description=request.description,
            candidate_title=obs0.product_title or "",
            candidate_mpn_field=obs0.manufacturer_part_number_text or "",
            candidate_sku=obs0.sku_text or "",
            evidence_source="TITLE_TEXT",
            actual_provider="amax",
            actual_model="nemotron-3-super",
            prompt_version="v1.1",
        )

        return run, cand0

    def test_same_url_wrong_title_candidate_is_unavailable(
        self,
        client: Client,
        run_with_same_url_different_assessments,
    ) -> None:
        """A confirmed candidate with wrong title fails binding.

        cand0 is correctly bound to index 0 (title="Samsung Product").
        Confirm cand0, then corrupt its title to a wrong value in the DB.
        The title mismatch causes binding to fail and the candidate does
        NOT contribute to Reviewed Price.
        """
        from product_intelligence.runs import confirm_candidate
        run, cand0 = run_with_same_url_different_assessments

        confirm_candidate(cand0.id)

        # Corrupt cand0's title to fail binding
        AiAssistedReviewCandidate.objects.filter(id=cand0.id).update(
            candidate_title="Completely Wrong Title"
        )
        cand0.refresh_from_db()
        assert cand0.candidate_title == "Completely Wrong Title"

        url = reverse("research-detail", kwargs={"run_id": run.id})
        response = client.get(url)
        assert response.status_code == 200

        reviewed = response.context.get("reviewed_result")
        assert reviewed is None, (
            "Candidate with mismatched title should not contribute to "
            "Reviewed Price. Binding validation should have rejected it."
        )
        assert response.context.get("confirmed_count") == 0

    def test_same_url_wrong_mpn_candidate_is_unavailable(
        self,
        client: Client,
        run_with_same_url_different_assessments,
    ) -> None:
        """A candidate at same URL but wrong MPN fails binding."""
        from product_intelligence.runs import confirm_candidate
        run, cand0 = run_with_same_url_different_assessments

        confirm_candidate(cand0.id)

        # Corrupt cand0's MPN field so it no longer matches the snapshot
        AiAssistedReviewCandidate.objects.filter(id=cand0.id).update(
            candidate_mpn_field="WRONG-MPN"
        )
        cand0.refresh_from_db()
        assert cand0.candidate_mpn_field == "WRONG-MPN"

        url = reverse("research-detail", kwargs={"run_id": run.id})
        response = client.get(url)
        assert response.status_code == 200

        reviewed = response.context.get("reviewed_result")
        assert reviewed is None, (
            "Candidate with mismatched MPN field should not contribute to "
            "Reviewed Price."
        )
        assert response.context.get("confirmed_count") == 0

    def test_same_url_wrong_sku_candidate_is_unavailable(
        self,
        client: Client,
        run_with_same_url_different_assessments,
    ) -> None:
        """A candidate at same URL but wrong SKU fails binding."""
        from product_intelligence.runs import confirm_candidate
        run, cand0 = run_with_same_url_different_assessments

        # Confirm cand0 (index 0, sku="SKU-001")
        confirm_candidate(cand0.id)

        # Corrupt cand0's SKU
        AiAssistedReviewCandidate.objects.filter(id=cand0.id).update(
            candidate_sku="WRONG-SKU"
        )
        cand0.refresh_from_db()
        assert cand0.candidate_sku == "WRONG-SKU"

        url = reverse("research-detail", kwargs={"run_id": run.id})
        response = client.get(url)
        assert response.status_code == 200

        reviewed = response.context.get("reviewed_result")
        assert reviewed is None, (
            "Candidate with mismatched SKU should not contribute to "
            "Reviewed Price."
        )
        assert response.context.get("confirmed_count") == 0

    @pytest.fixture
    def run_with_unavailable_candidate(
        self, human_review_db_isolation
    ) -> tuple[ResearchRun, AiAssistedReviewCandidate]:
        """A run with two snapshot assessments and one candidate bound to the semantic-eligible index.

        Index 0: ACCEPTED (deterministic) — has a different title/MPN than the candidate.
        Index 1: REJECTED + NO_EXPLICIT_MPN_EVIDENCE + TITLE_TEXT — matches the candidate's binding fields.

        The candidate is correctly bound to index 1 (semantic-eligible REJECTED).
        Tests can corrupt the candidate to test binding failures.
        This allows testing that a candidate CANNOT use the ACCEPTED index 0.
        """
        from product_intelligence.research.aggregation import (
            aggregate_listing_prices,
        )
        from product_intelligence.research.price_result_codec import (
            PRICE_RESULT_SCHEMA_VERSION,
            encode_price_aggregation_result,
        )
        from product_intelligence.research.matching import (
            EvidenceSource,
            IdentityRejectionReason,
            ListingIdentityAssessment,
        )
        from product_intelligence.research.normalization import (
            NormalizedAvailability,
            NormalizedCondition,
            NormalizedListingObservation,
        )
        from product_intelligence.research.listings import (
            ExtractionMethod,
            ListingObservation,
        )
        from product_intelligence.domain.enums import (
            EvidenceDecision,
            IdentityMatchType,
        )
        from decimal import Decimal

        request = ResearchRequest(
            manufacturer_part_number="TEST-001",
            description="Test product",
        )
        run = ResearchRun.objects.create_from_request(request)
        run.transition_to(ResearchRunState.RUNNING)
        run.transition_to(ResearchRunState.COMPLETED)

        # Index 0: ACCEPTED (deterministic) — different title, no MPN
        obs0 = ListingObservation(
            source_url="https://example.com/deterministic-page",
            extraction_method=ExtractionMethod.JSON_LD,
            manufacturer_part_number_text="TEST-001",
            sku_text="",
            product_title="Deterministic Matched Product",
            price_text="88.88",
            currency_text="USD",
            condition_text="new",
        )
        norm0 = NormalizedListingObservation(
            observation=obs0,
            price_amount=Decimal("88.88"),
            currency_code="USD",
            condition=NormalizedCondition.NEW,
            availability=NormalizedAvailability.UNKNOWN,
            seller_name="Seller A",
            normalization_issues=(),
        )
        assess0 = ListingIdentityAssessment(
            normalized_listing=norm0,
            requested_part_number="TEST-001",
            candidate_part_number_raw="TEST-001",
            candidate_part_number_compared="TEST-001",
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.EXACT,
            decision=EvidenceDecision.ACCEPTED,
            rejection_reason=None,
        )

        # Index 1: REJECTED + NO_EXPLICIT_MPN_EVIDENCE + TITLE_TEXT — semantic-eligible
        obs1 = ListingObservation(
            source_url="https://example.com/product/1",
            extraction_method=ExtractionMethod.JSON_LD,
            manufacturer_part_number_text="",
            sku_text=None,
            price_text="99.99",
            currency_text="USD",
            condition_text="new",
            product_title="Listing for TEST-001 component",
        )
        norm1 = NormalizedListingObservation(
            observation=obs1,
            price_amount=Decimal("99.99"),
            currency_code="USD",
            condition=NormalizedCondition.NEW,
            availability=NormalizedAvailability.UNKNOWN,
            seller_name="Test Seller",
            normalization_issues=(),
        )
        assess1 = ListingIdentityAssessment(
            normalized_listing=norm1,
            requested_part_number="TEST-001",
            candidate_part_number_raw="TEST-001",
            candidate_part_number_compared="TEST-001",
            candidate_evidence_source=EvidenceSource.TITLE_TEXT,
            match_type=IdentityMatchType.UNKNOWN,
            decision=EvidenceDecision.REJECTED,
            rejection_reason=IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE,
        )

        assessments = (assess0, assess1)
        price_result = aggregate_listing_prices(request, assessments)
        payload = encode_price_aggregation_result(price_result)
        PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=PRICE_RESULT_SCHEMA_VERSION,
            payload=payload,
        )

        # Candidate bound to semantic-eligible index (index 1), NOT ACCEPTED (index 0)
        candidate = AiAssistedReviewCandidate.objects.create(
            run=run,
            assessment_index=1,
            source_url=obs1.source_url,
            target_mpn=request.manufacturer_part_number,
            target_description=request.description,
            candidate_title=obs1.product_title or "",
            candidate_mpn_field=obs1.manufacturer_part_number_text or "",
            candidate_sku=obs1.sku_text or "",
            evidence_source="TITLE_TEXT",
            actual_provider="amax",
            actual_model="nemotron-3-super",
            prompt_version="v1.1",
        )
        return run, candidate

    def test_deterministic_assessment_index_rejected(
        self, client: Client, run_with_unavailable_candidate
    ) -> None:
        """A confirmed candidate pointing to a deterministic ACCEPTED index
        (not human-review-eligible) must NOT contribute to Reviewed Price."""
        from product_intelligence.runs import confirm_candidate
        run, candidate = run_with_unavailable_candidate

        # Confirm the candidate
        confirm_candidate(candidate.id)

        # Corrupt its assessment_index to point to the ACCEPTED assessment (index 0)
        # instead of the semantic-eligible REJECTED (index 1)
        AiAssistedReviewCandidate.objects.filter(id=candidate.id).update(
            assessment_index=0
        )
        candidate.refresh_from_db()
        assert candidate.assessment_index == 0

        url = reverse("research-detail", kwargs={"run_id": run.id})
        response = client.get(url)
        assert response.status_code == 200

        # Index 0 is ACCEPTED, not human-review-eligible — binding must reject it
        reviewed = response.context.get("reviewed_result")
        assert reviewed is None, (
            "Candidate bound to deterministic ACCEPTED assessment must not "
            "contribute to Reviewed Price."
        )
        assert response.context.get("confirmed_count") == 0

    def test_out_of_range_index_rejected(
        self, client: Client, run_with_unavailable_candidate
    ) -> None:
        """A confirmed candidate with out-of-range assessment_index is rejected."""
        from product_intelligence.runs import confirm_candidate
        run, candidate = run_with_unavailable_candidate

        confirm_candidate(candidate.id)

        # Set out-of-range index
        AiAssistedReviewCandidate.objects.filter(id=candidate.id).update(
            assessment_index=999
        )
        candidate.refresh_from_db()
        assert candidate.assessment_index == 999

        url = reverse("research-detail", kwargs={"run_id": run.id})
        response = client.get(url)
        assert response.status_code == 200

        reviewed = response.context.get("reviewed_result")
        assert reviewed is None
        assert response.context.get("confirmed_count") == 0

    def test_wrong_target_mpn_rejected(
        self, client: Client, run_with_unavailable_candidate
    ) -> None:
        """A confirmed candidate with wrong target_mpn fails binding."""
        from product_intelligence.runs import confirm_candidate
        run, candidate = run_with_unavailable_candidate

        confirm_candidate(candidate.id)

        # Change target_mpn to something that doesn't match the assessment
        AiAssistedReviewCandidate.objects.filter(id=candidate.id).update(
            target_mpn="WRONG-MPN"
        )
        candidate.refresh_from_db()
        assert candidate.target_mpn == "WRONG-MPN"

        url = reverse("research-detail", kwargs={"run_id": run.id})
        response = client.get(url)
        assert response.status_code == 200

        reviewed = response.context.get("reviewed_result")
        assert reviewed is None, (
            "Candidate with wrong target_mpn must not contribute to "
            "Reviewed Price."
        )
        assert response.context.get("confirmed_count") == 0
    def test_valid_candidate_contributes_to_reviewed_price(
        self,
        client: Client,
        run_with_same_url_different_assessments,
    ) -> None:
        """A correctly-bound confirmed candidate DOES contribute."""
        from product_intelligence.runs import confirm_candidate
        run, cand0 = run_with_same_url_different_assessments

        # Confirm the correctly-bound candidate
        confirm_candidate(cand0.id)

        url = reverse("research-detail", kwargs={"run_id": run.id})
        response = client.get(url)
        assert response.status_code == 200

        # The confirmed candidate is valid, so Reviewed Price should include it
        reviewed = response.context.get("reviewed_result")
        assert reviewed is not None
        assert response.context.get("confirmed_count") == 1
        bucket = reviewed.buckets[0]
        assert bucket.human_confirmed_count == 1

    def test_same_url_wrong_index_get_rejects_binding(
        self,
        client: Client,
        run_with_same_url_different_assessments,
    ) -> None:
        """A confirmed candidate at same URL but wrong assessment_index fails GET binding.

        cand0 is correctly bound to index 0 (title='Samsung REAL-001 Product').
        The snapshot also has assessment 1 (title='Other REAL-001 Product').
        Both assessments are TITLE_TEXT AI_ASSISTED_MATCH at the same URL.

        This test: confirm cand0, then point cand0 at index 1 (wrong index, same URL).
        GET must reject the binding — cand0 cannot contribute to Reviewed Price.
        The UNIQUE (run, assessment_index) constraint does NOT cause this failure;
        binding validation does.
        """
        from product_intelligence.runs import confirm_candidate
        run, cand0 = run_with_same_url_different_assessments

        # Confirm cand0 while correctly bound
        confirm_candidate(cand0.id)

        # Now corrupt cand0's assessment_index to point to index 1
        # cand0 was bound to assessment 0 (Samsung REAL-001 Product)
        # assessment 1 is (Other REAL-001 Product)
        # cand0's title mismatches assessment 1 — binding validation rejects it
        AiAssistedReviewCandidate.objects.filter(id=cand0.id).update(
            assessment_index=1
        )
        cand0.refresh_from_db()
        assert cand0.assessment_index == 1

        url = reverse("research-detail", kwargs={"run_id": run.id})
        response = client.get(url)
        assert response.status_code == 200

        reviewed = response.context.get("reviewed_result")
        assert reviewed is None, (
            "Candidate with wrong assessment_index must not contribute to "
            "Reviewed Price even at same URL."
        )
        assert response.context.get("confirmed_count") == 0

    def test_same_url_wrong_index_post_rejects_write(
        self,
        client: Client,
        run_with_same_url_different_assessments,
    ) -> None:
        """Corrupt assessment_index BEFORE POST confirm; candidate stays UNREVIEWED.

        This tests the WRITE boundary: a candidate that was correctly bound at
        index 0 is altered to point to index 1 BEFORE the POST confirm call.
        The POST must fail closed — candidate remains UNREVIEWED.
        The UNIQUE (run, assessment_index) constraint does NOT fire; only
        binding validation does.
        """
        from product_intelligence.runs import confirm_candidate
        run, cand0 = run_with_same_url_different_assessments

        # cand0 is correctly bound to index 0; corrupt its index to 1
        # (assessment 1 has different title — binding validation fails)
        AiAssistedReviewCandidate.objects.filter(id=cand0.id).update(
            assessment_index=1
        )
        cand0.refresh_from_db()
        assert cand0.assessment_index == 1
        assert cand0.review_state == AiAssistedReviewCandidate.REVIEW_STATE_UNREVIEWED

        # POST confirm through real research-review URL
        url = reverse(
            "research-review",
            kwargs={"run_id": run.id, "candidate_id": cand0.id},
        )
        response = client.post(url, {"action": "confirm"})

        # Must redirect (fail closed)
        assert response.status_code in (301, 302)

        # Candidate must remain UNREVIEWED
        cand0.refresh_from_db()
        assert cand0.review_state == AiAssistedReviewCandidate.REVIEW_STATE_UNREVIEWED, (
            "Corrupt assessment_index must prevent confirmation — candidate "
            "remains UNREVIEWED."
        )
        assert cand0.reviewed_at is None, "reviewed_at must remain NULL for UNREVIEWED."

        # reviewed_at must remain NULL
        assert cand0.reviewed_at is None

        # GET also shows no reviewed price contribution
        detail_url = reverse("research-detail", kwargs={"run_id": run.id})
        detail_response = client.get(detail_url)
        assert detail_response.status_code == 200
        assert detail_response.context.get("reviewed_result") is None
        assert detail_response.context.get("confirmed_count") == 0

class TestUnavailableCandidatePresentation:
    """Tests for "Review evidence unavailable" presentation.

    When a candidate's binding is corrupt/stale/unavailable, the report must:
    - Show a neutral "Review evidence unavailable" message for that candidate
    - NOT show Confirm/Reject buttons for that candidate
    - NOT omit the candidate from the list (silently hiding is wrong)
    """

    @pytest.fixture
    def run_with_unavailable_candidate(
        self, human_review_db_isolation
    ) -> tuple[ResearchRun, AiAssistedReviewCandidate]:
        """A run with a snapshot and one semantic-eligible REJECTED candidate.

        The observation has no explicit MPN field and no SKU. The MPN token
        is found in the product title, giving TITLE_TEXT evidence.
        The candidate's binding fields match the observation exactly.
        The assessment is REJECTED + NO_EXPLICIT_MPN_EVIDENCE (frozen FU3B original).
        """
        from product_intelligence.research.aggregation import (
            aggregate_listing_prices,
        )
        from product_intelligence.research.price_result_codec import (
            PRICE_RESULT_SCHEMA_VERSION,
            encode_price_aggregation_result,
        )
        from product_intelligence.research.matching import (
            EvidenceSource,
            IdentityRejectionReason,
            ListingIdentityAssessment,
        )
        from product_intelligence.research.normalization import (
            NormalizedAvailability,
            NormalizedCondition,
            NormalizedListingObservation,
        )
        from product_intelligence.research.listings import (
            ExtractionMethod,
            ListingObservation,
        )
        from product_intelligence.domain.enums import (
            EvidenceDecision,
            IdentityMatchType,
        )
        from decimal import Decimal

        request = ResearchRequest(
            manufacturer_part_number="TEST-001",
            description="Test product",
        )
        run = ResearchRun.objects.create_from_request(request)
        run.transition_to(ResearchRunState.RUNNING)
        run.transition_to(ResearchRunState.COMPLETED)

        # Snapshot with one semantic-eligible REJECTED (TITLE_TEXT)
        obs = ListingObservation(
            source_url="https://example.com/product/1",
            extraction_method=ExtractionMethod.JSON_LD,
            manufacturer_part_number_text="",
            sku_text=None,
            price_text="99.99",
            currency_text="USD",
            condition_text="new",
            product_title="Listing for TEST-001 part",
        )
        norm = NormalizedListingObservation(
            observation=obs,
            price_amount=Decimal("99.99"),
            currency_code="USD",
            condition=NormalizedCondition.NEW,
            availability=NormalizedAvailability.UNKNOWN,
            seller_name="Test Seller",
            normalization_issues=(),
        )
        assess = ListingIdentityAssessment(
            normalized_listing=norm,
            requested_part_number="TEST-001",
            candidate_part_number_raw="TEST-001",
            candidate_part_number_compared="TEST-001",
            candidate_evidence_source=EvidenceSource.TITLE_TEXT,
            match_type=IdentityMatchType.UNKNOWN,
            decision=EvidenceDecision.REJECTED,
            rejection_reason=IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE,
        )

        assessments = (assess,)
        price_result = aggregate_listing_prices(request, assessments)
        payload = encode_price_aggregation_result(price_result)
        PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=PRICE_RESULT_SCHEMA_VERSION,
            payload=payload,
        )

        # Candidate bound to index 0 with matching evidence.
        # candidate_title == obs.product_title, candidate_mpn_field == "",
        # candidate_sku == ""
        candidate = AiAssistedReviewCandidate.objects.create(
            run=run,
            assessment_index=0,
            source_url=obs.source_url,
            target_mpn=request.manufacturer_part_number,
            target_description=request.description,
            candidate_title=obs.product_title or "",
            candidate_mpn_field=obs.manufacturer_part_number_text or "",
            candidate_sku=obs.sku_text or "",
            evidence_source="TITLE_TEXT",
            actual_provider="amax",
            actual_model="nemotron-3-super",
            prompt_version="v1.1",
        )
        return run, candidate

    def test_unavailable_candidate_has_no_review_actions(
        self, client: Client, run_with_unavailable_candidate
    ) -> None:
        """An unavailable candidate must not have Confirm/Reject buttons."""
        from product_intelligence.runs import confirm_candidate
        run, candidate = run_with_unavailable_candidate

        # Confirm the candidate
        confirm_candidate(candidate.id)

        # Now corrupt the snapshot so the candidate binding fails
        # Set assessment_index to 999 (out of range)
        AiAssistedReviewCandidate.objects.filter(id=candidate.id).update(
            assessment_index=999
        )
        candidate.refresh_from_db()

        url = reverse("research-detail", kwargs={"run_id": run.id})
        response = client.get(url)
        assert response.status_code == 200

        content = response.content.decode("utf-8")
        # The candidate row should still appear in the HTML
        # (we show it, we don't silently omit it)
        assert "review-candidate" in content, (
            "Unavailable candidate should still appear in the page"
        )
        # The candidate should show "Review evidence unavailable" message
        assert "Review evidence unavailable" in content, (
            "Unavailable candidate must display 'Review evidence unavailable' message"
        )
        # Since binding fails, confirmed_count is 0
        assert response.context.get("confirmed_count") == 0

        # Candidate-specific proof: the unavailable candidate's review URL
        # must NOT have an action form targeting it
        review_url = reverse(
            "research-review",
            kwargs={"run_id": run.id, "candidate_id": candidate.id},
        )
        # The form action for this candidate's review URL must NOT appear
        # in the rendered page (it is suppressed for unavailable candidates)
        review_action_str = f'action="{review_url}"'
        assert review_action_str not in content, (
            "Unavailable candidate must not render a review action form"
        )
        # No confirm/reject/undo buttons for this candidate at all
        assert f'value="confirm"' not in content, (
            "Unavailable candidate must not render a confirm button"
        )
        assert f'value="reject"' not in content, (
            "Unavailable candidate must not render a reject button"
        )
        assert f'value="undo"' not in content, (
            "Unavailable candidate must not render an undo button"
        )

    def test_corrupt_confirmed_candidate_does_not_affect_reviewed_price(
        self, client: Client, run_with_unavailable_candidate
    ) -> None:
        """A corrupt CONFIRMED candidate must not contribute to Reviewed Price.

        Proves: valid-confirmed -> corrupt -> excluded.
        """
        from product_intelligence.runs import confirm_candidate
        run, candidate = run_with_unavailable_candidate

        # Confirm the candidate while it still has valid binding
        confirm_candidate(candidate.id)

        # VALID-BEFORE-CORRUPTION precondition: confirmed candidate contributes
        detail_url = reverse("research-detail", kwargs={"run_id": run.id})
        response = client.get(detail_url)
        assert response.status_code == 200
        assert response.context.get("confirmed_count") == 1
        reviewed_before = response.context.get("reviewed_result")
        assert reviewed_before is not None, (
            "Valid confirmed candidate must contribute to Reviewed Price "
            "before corruption."
        )

        # Now corrupt its binding to fail the validation
        AiAssistedReviewCandidate.objects.filter(id=candidate.id).update(
            assessment_index=999
        )
        candidate.refresh_from_db()

        # After corruption: candidate is excluded
        response = client.get(detail_url)
        assert response.status_code == 200

        # reviewed_result should be None (no valid confirmed candidates)
        reviewed = response.context.get("reviewed_result")
        assert reviewed is None, (
            "Corrupt CONFIRMED candidate must not affect Reviewed Price. "
            "Binding validation should have dropped it."
        )
        assert response.context.get("confirmed_count") == 0
        # Machine price should still show correctly (snapshot is valid)
        report = response.context.get("report_presentation")
        assert report is not None
        assert report.verification_status == "UNKNOWN"
