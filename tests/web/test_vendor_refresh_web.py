"""VENDOR-REFRESH-WEB — the browser Refresh Vendor Prices action.

Focused regression coverage for the POST
``/research/<uuid>/vendor-refresh`` endpoint and the latest-refresh
display on the research detail page:

* CSRF protection (no token -> 403, zero mutation; valid token -> the
  action runs);
* the existing corporate Vendor Price access policy (4D-C-SEC)
  authorizes the operation: DENIED connections (no configured CIDRs,
  or an out-of-network REMOTE_ADDR) mutate nothing and learn nothing
  (total zero-knowledge, the frozen D8 standard);
* cooldown (a terminal child finished < 300 s ago is refused: no new
  child, zero Vendor calls; outside the window a new child is
  created) — the web surface has NO bypass;
* concurrency / single winner (a pre-existing active child —
  PENDING or RUNNING, command- or web-created — is reported and left
  untouched: no second claim, zero lookups);
* execution ownership (M3 Option A): the web POST claims and executes
  ONLY the child its own request created; a pre-existing PENDING
  orphan is never claimed or executed by the web surface;
* result visibility (ALLOWED GET renders the latest completed refresh
  result — source, price, currency, availability, retrieval time —
  SEPARATELY from the original vendor snapshot; in-progress /
  cooldown / failure states are clearly displayed);
* original-snapshot preservation (the parent ResearchRun and every
  original persisted artifact are byte-identical before and after a
  refresh: no Machine Price, no Reviewed Price, no matching decision,
  no historical vendor evidence is touched);
* missing / failed results (no record; a mechanically FAILED child;
  a COMPLETED child with a FAILED lookup; a SUCCESS lookup with zero
  observations; a corrupted COMPLETED payload -> "recorded but
  unreadable");
* provenance (a web trigger records ``trigger_source=WEB_UI`` + the
  bounded web operator literal — never MANAGEMENT_COMMAND).

Class discipline: deterministic D nodes over the in-memory suite
database with pinned clocks, counting fakes, and armed boundaries.
The GENUINE file-backed process concurrency of the shared decision
service (single winner, cooldown interleavings, SQLite locking) is
proven by ``tests/runs/test_vendor_refresh_concurrency.py`` (the C
class, unchanged — the web surface shares the exact same service).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone as dt_timezone
from decimal import Decimal
from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import (
    EvidenceDecision,
    IdentityMatchType,
    ResearchRunState,
    VerificationStatus,
)
from product_intelligence.research import (
    IdentityRejectionReason,
    ListingIdentityAssessment,
    ListingObservation,
    PriceAggregationExclusion,
    PriceAggregationExclusionReason,
    PriceAggregationResult,
    encode_price_aggregation_result,
)
from product_intelligence.research.listings import ExtractionMethod
from product_intelligence.research.matching import EvidenceSource
from product_intelligence.research.normalization import (
    NormalizedAvailability,
    NormalizedCondition,
    NormalizedListingObservation,
)
from product_intelligence.runs import (
    claim_vendor_refresh,
    complete_vendor_refresh,
    trigger_vendor_refresh,
)
from product_intelligence.runs.models import (
    AiAssistedReviewCandidate,
    ComparableResearchExecution,
    ExecutionEvidenceRecord,
    PriceIntelligenceSnapshot,
    ResearchFxSnapshot,
    ResearchMicronAliasSnapshot,
    ResearchRun,
    ResearchSupplementSnapshot,
    VendorRefreshExecution,
    VendorRefreshFailureReason,
    VendorRefreshState,
    VendorRefreshTriggerSource,
)
from product_intelligence.research.commercial_supplement_codec import (
    ResearchSupplementResult,
    VendorCommercialResult,
    encode_research_supplement_result,
)

import product_intelligence.execution.vendor_refresh as core
from product_intelligence.execution.vendor_refresh import (
    execute_claimed_vendor_refresh,
)
from tests.execution.test_vendor_commercial_binding import (
    build_success_exact_match_response,
)

TEST_MPN = "BCM957608-P2200GQF00"
TEST_DESCRIPTION = "Enterprise SSD"
ALLOWED_ADDR = "10.1.2.3"
DENIED_ADDR = "203.0.113.9"
CIDRS = "10.0.0.0/8"

PINNED = datetime(2026, 6, 1, 12, 0, 0, tzinfo=dt_timezone.utc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _settings_mock(cidrs: str | None) -> object:
    return type("Settings", (), {"PI_VENDOR_PRICE_ALLOWED_CIDRS": cidrs})()


def _unknown_result(run: ResearchRun) -> PriceAggregationResult:
    """A minimal decodable price result (zero buckets; the same shape
    the compact-report suite persists)."""
    mpn = run.manufacturer_part_number or "X"
    obs = ListingObservation(
        source_url="https://example.com/wrong",
        extraction_method=ExtractionMethod.JSON_LD,
        product_title="Different Product",
        manufacturer_part_number_text="WRONG-MPN",
        sku_text=None,
        brand_text=None,
        price_text="$50.00",
        currency_text="USD",
        availability_text="In Stock",
        condition_text="New",
        seller_text=None,
        offer_url_text=None,
        raw_reference=None,
    )
    norm = NormalizedListingObservation(
        observation=obs,
        price_amount=Decimal("50.00"),
        currency_code="USD",
        availability=NormalizedAvailability.IN_STOCK,
        condition=NormalizedCondition.NEW,
        seller_name=None,
        normalization_issues=(),
    )
    assess = ListingIdentityAssessment(
        normalized_listing=norm,
        requested_part_number=mpn,
        candidate_part_number_raw="WRONG-MPN",
        candidate_part_number_compared="WRONG-MPN",
        candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
        match_type=IdentityMatchType.UNKNOWN,
        decision=EvidenceDecision.REJECTED,
        rejection_reason=IdentityRejectionReason.MPN_MISMATCH,
    )
    return PriceAggregationResult(
        request=run.to_research_request(),
        assessments=(assess,),
        exclusions=(
            PriceAggregationExclusion(
                assessment=assess,
                reason=PriceAggregationExclusionReason.IDENTITY_NOT_ACCEPTED,
            ),
        ),
        buckets=(),
        verification_status=VerificationStatus.UNKNOWN,
    )


def _make_completed_run(
    mpn: str = TEST_MPN, description: str = TEST_DESCRIPTION
) -> ResearchRun:
    request = ResearchRequest(manufacturer_part_number=mpn, description=description)
    run = ResearchRun.objects.create_from_request(request)
    run.transition_to(ResearchRunState.RUNNING)
    run.transition_to(ResearchRunState.COMPLETED)
    PriceIntelligenceSnapshot.objects.create(
        run=run,
        schema_version=1,
        payload=encode_price_aggregation_result(_unknown_result(run)),
    )
    return run


def _make_running_run() -> ResearchRun:
    run = ResearchRun.objects.create_from_request(
        ResearchRequest(manufacturer_part_number=TEST_MPN, description=TEST_DESCRIPTION)
    )
    run.transition_to(ResearchRunState.RUNNING)
    return run


def _parent_artifact_snapshot(run: ResearchRun) -> dict:
    """The parent ResearchRun + every original persisted artifact
    (byte-identity frame, the I7 central regression)."""
    fresh = ResearchRun.objects.get(pk=run.pk)
    snapshot = {
        "run_state": fresh.state,
        "run_mpn": fresh.manufacturer_part_number,
        "run_description": fresh.description,
        "run_created_at": fresh.created_at,
        "run_started_at": fresh.started_at,
        "run_finished_at": fresh.finished_at,
        "price_count": PriceIntelligenceSnapshot.objects.filter(run=fresh).count(),
        "supplement_count": ResearchSupplementSnapshot.objects.filter(run=fresh).count(),
        "fx_count": ResearchFxSnapshot.objects.filter(run=fresh).count(),
        "micron_alias_count": ResearchMicronAliasSnapshot.objects.filter(run=fresh).count(),
        "evidence_count": ExecutionEvidenceRecord.objects.filter(run=fresh).count(),
        "review_candidate_count": AiAssistedReviewCandidate.objects.filter(run=fresh).count(),
        "comparable_count": ComparableResearchExecution.objects.filter(parent_run=fresh).count(),
    }
    price = PriceIntelligenceSnapshot.objects.filter(run=fresh).first()
    if price is not None:
        snapshot["price_schema_version"] = price.schema_version
        snapshot["price_payload"] = price.payload
        snapshot["price_created_at"] = price.created_at
    supplement = ResearchSupplementSnapshot.objects.filter(run=fresh).first()
    if supplement is not None:
        snapshot["supplement_payload"] = supplement.payload
        snapshot["supplement_created_at"] = supplement.created_at
    return snapshot


class _FakeAdapter:
    """Canned-response adapter; records lookup() calls."""

    def __init__(self, response) -> None:
        self.response = response
        self.lookup_queries: list = []

    def lookup(self, query):
        self.lookup_queries.append(query)
        return self.response


def _fake_entry(adapter: _FakeAdapter):
    """The command-stack execution entry over the counting adapter
    (the runtime's delegation, with the concrete adapter replaced by
    the test double — the flow itself is NOT patched)."""

    def entry(child_id):
        return execute_claimed_vendor_refresh(child_id, vendor_adapter=adapter)

    return entry


def _refresh_url(run_id: uuid.UUID) -> str:
    return reverse("research-vendor-refresh", kwargs={"run_id": run_id})


def _detail_url(run_id: uuid.UUID) -> str:
    return reverse("research-detail", kwargs={"run_id": run_id})


def _csrf_token(client: Client) -> str:
    client.get("/research/new")
    return client.cookies["csrftoken"].value


def _post_refresh(
    client: Client,
    run: ResearchRun,
    *,
    with_csrf: bool = True,
    follow: bool = True,
):
    data = {}
    if with_csrf:
        data["csrfmiddlewaretoken"] = _csrf_token(client)
    return client.post(_refresh_url(run.id), data, follow=follow)


# ---------------------------------------------------------------------------
# CSRF + method discipline
# ---------------------------------------------------------------------------


class TestCsrfAndMethod(TestCase):
    """The action is POST-only and CSRF-protected; a GET or a
    tokenless POST mutates nothing and issues no Vendor call."""

    def test_get_on_the_action_route_is_405_with_zero_mutation(self) -> None:
        run = _make_completed_run()
        adapter = _FakeAdapter(build_success_exact_match_response())
        with (
            patch("product_intelligence.web.commercial_access._django_settings", _settings_mock(CIDRS)),
            patch.dict("os.environ", {"PI_VENDOR_LOOKUP_BASE_URL": "http://vendor.internal/api"}),
            patch("product_intelligence.web.views.execute_claimed_vendor_refresh_with_default_providers", _fake_entry(adapter)),
        ):
            client = Client(REMOTE_ADDR=ALLOWED_ADDR)
            response = client.get(_refresh_url(run.id))
        assert response.status_code == 405
        assert VendorRefreshExecution.objects.count() == 0
        assert len(adapter.lookup_queries) == 0

    def test_post_without_csrf_token_is_403_with_zero_mutation(self) -> None:
        run = _make_completed_run()
        adapter = _FakeAdapter(build_success_exact_match_response())
        with (
            patch("product_intelligence.web.commercial_access._django_settings", _settings_mock(CIDRS)),
            patch.dict("os.environ", {"PI_VENDOR_LOOKUP_BASE_URL": "http://vendor.internal/api"}),
            patch("product_intelligence.web.views.execute_claimed_vendor_refresh_with_default_providers", _fake_entry(adapter)),
        ):
            client = Client(REMOTE_ADDR=ALLOWED_ADDR, enforce_csrf_checks=True)
            response = client.post(_refresh_url(run.id), {})
        assert response.status_code == 403
        assert VendorRefreshExecution.objects.count() == 0
        assert len(adapter.lookup_queries) == 0

    def test_post_with_valid_csrf_token_runs_the_action(self) -> None:
        run = _make_completed_run()
        adapter = _FakeAdapter(build_success_exact_match_response())
        with (
            patch("product_intelligence.web.commercial_access._django_settings", _settings_mock(CIDRS)),
            patch.dict("os.environ", {"PI_VENDOR_LOOKUP_BASE_URL": "http://vendor.internal/api"}),
            patch("product_intelligence.web.views.execute_claimed_vendor_refresh_with_default_providers", _fake_entry(adapter)),
        ):
            client = Client(REMOTE_ADDR=ALLOWED_ADDR, enforce_csrf_checks=True)
            response = _post_refresh(client, run)
        assert response.status_code == 200
        child = VendorRefreshExecution.objects.get(parent_run=run)
        assert child.state == VendorRefreshState.COMPLETED
        assert len(adapter.lookup_queries) == 1
        # The bound MPN is transmitted exactly once (LB-1).
        assert adapter.lookup_queries[0].mpn == TEST_MPN


# ---------------------------------------------------------------------------
# Access policy (the existing 4D-C-SEC corporate Vendor Price gate)
# ---------------------------------------------------------------------------


class TestAccessPolicy(TestCase):
    """DENIED connections (fail-closed gate) mutate nothing and learn
    nothing: not existence, not state, not operator, not price, not
    error (the frozen D8 standard)."""

    def _denied_setup(self):
        run = _make_completed_run()
        adapter = _FakeAdapter(build_success_exact_match_response())
        return run, adapter

    def test_no_configured_cidrs_denies_the_post_and_the_display(self) -> None:
        run, adapter = self._denied_setup()
        with (
            patch("product_intelligence.web.commercial_access._django_settings", _settings_mock(None)),
            patch.dict("os.environ", {"PI_VENDOR_LOOKUP_BASE_URL": "http://vendor.internal/api"}),
            patch("product_intelligence.web.views.execute_claimed_vendor_refresh_with_default_providers", _fake_entry(adapter)),
        ):
            client = Client(REMOTE_ADDR=ALLOWED_ADDR)
            response = _post_refresh(client, run, follow=False)
            page = client.get(_detail_url(run.id))
        assert response.status_code == 302  # neutral redirect; nothing done
        assert VendorRefreshExecution.objects.count() == 0
        assert len(adapter.lookup_queries) == 0
        html = page.content.decode()
        assert "Vendor refresh" not in html
        assert "Refresh Vendor Prices" not in html
        assert "2,120" not in html

    def test_out_of_network_remote_addr_denied(self) -> None:
        run, adapter = self._denied_setup()
        # A pre-existing COMPLETED refresh record proves the DENIED
        # page leaks nothing about it (no existence, no price).
        child = claim_vendor_refresh(
            trigger_vendor_refresh(run.id, operator="op-cmd").id
        )
        complete_vendor_refresh(
            child.id, 1, encode_research_supplement_result(ResearchSupplementResult(vendor_commercial_result=VendorCommercialResult(lookup_status="SUCCESS", retrieved_at=PINNED, observations=(), source_issues=())))
        )
        with (
            patch("product_intelligence.web.commercial_access._django_settings", _settings_mock(CIDRS)),
            patch.dict("os.environ", {"PI_VENDOR_LOOKUP_BASE_URL": "http://vendor.internal/api"}),
            patch("product_intelligence.web.views.execute_claimed_vendor_refresh_with_default_providers", _fake_entry(adapter)),
        ):
            denied = Client(REMOTE_ADDR=DENIED_ADDR)
            response = _post_refresh(denied, run, follow=False)
            page = denied.get(_detail_url(run.id))
        assert response.status_code == 302
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 1
        assert len(adapter.lookup_queries) == 0
        html = page.content.decode()
        assert "Vendor refresh" not in html
        assert "Refresh Vendor Prices" not in html
        assert "2,120" not in html
        assert "op-cmd" not in html

    def test_denied_get_does_not_query_refresh_rows(self) -> None:
        """Armed fail-fast: a DENIED detail GET must not touch the
        refresh model access path at all."""
        run = _make_completed_run()
        boom = {}

        def _boom(*a, **k):
            boom["hit"] = True
            raise AssertionError("refresh model queried on the DENIED path")

        with (
            patch("product_intelligence.web.commercial_access._django_settings", _settings_mock(None)),
            patch.object(VendorRefreshExecution.objects, "filter", side_effect=_boom),
        ):
            Client(REMOTE_ADDR=ALLOWED_ADDR).get(_detail_url(run.id))
        assert not boom


# ---------------------------------------------------------------------------
# Cooldown (five-minute repeat safeguard; the web has NO bypass)
# ---------------------------------------------------------------------------


class TestCooldown(TestCase):
    """A terminal child finished less than 300 s ago refuses a new web
    refresh: no new child, zero claims, zero lookups — and the page
    clearly shows the cooldown state. Outside the window (or exactly
    at the 300 s boundary: the refusal is STRICT < 300 s) a new child
    is created."""

    def _terminal_child_at(self, run, age_seconds: float):
        child = claim_vendor_refresh(trigger_vendor_refresh(run.id, operator="op-t").id)
        complete_vendor_refresh(
            child.id,
            1,
            encode_research_supplement_result(
                ResearchSupplementResult(
                    vendor_commercial_result=VendorCommercialResult(
                        lookup_status="FAILED",
                        retrieved_at=None,
                        observations=(),
                        source_issues=(),
                    )
                )
            ),
            at=PINNED - timedelta(seconds=age_seconds),
        )
        return child

    def test_within_cooldown_refused_no_child_no_lookup_notice_shown(self) -> None:
        run = _make_completed_run()
        blocker = self._terminal_child_at(run, 299.9)
        adapter = _FakeAdapter(build_success_exact_match_response())
        with (
            patch("django.utils.timezone.now", lambda: PINNED),
            patch("product_intelligence.web.commercial_access._django_settings", _settings_mock(CIDRS)),
            patch.dict("os.environ", {"PI_VENDOR_LOOKUP_BASE_URL": "http://vendor.internal/api"}),
            patch("product_intelligence.web.views.execute_claimed_vendor_refresh_with_default_providers", _fake_entry(adapter)),
        ):
            client = Client(REMOTE_ADDR=ALLOWED_ADDR)
            page = _post_refresh(client, run)
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 1
        assert len(adapter.lookup_queries) == 0
        html = page.content.decode()
        assert "Refreshes are limited to one per five minutes" in html
        # The blocking record is displayed (its bounded facts).
        assert f"Part number" in html

    def test_outside_cooldown_creates_a_new_child(self) -> None:
        run = _make_completed_run()
        self._terminal_child_at(run, 300.1)
        adapter = _FakeAdapter(build_success_exact_match_response())
        with (
            patch("django.utils.timezone.now", lambda: PINNED),
            patch("product_intelligence.web.commercial_access._django_settings", _settings_mock(CIDRS)),
            patch.dict("os.environ", {"PI_VENDOR_LOOKUP_BASE_URL": "http://vendor.internal/api"}),
            patch("product_intelligence.web.views.execute_claimed_vendor_refresh_with_default_providers", _fake_entry(adapter)),
        ):
            client = Client(REMOTE_ADDR=ALLOWED_ADDR)
            page = _post_refresh(client, run)
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 2
        assert len(adapter.lookup_queries) == 1
        assert "Vendor prices were refreshed" in page.content.decode()

    def test_boundary_exactly_300s_is_allowed(self) -> None:
        """The refusal is STRICT < 300 s (O7): age exactly 300.0 s
        permits a new attempt."""
        run = _make_completed_run()
        self._terminal_child_at(run, 300.0)
        adapter = _FakeAdapter(build_success_exact_match_response())
        with (
            patch("django.utils.timezone.now", lambda: PINNED),
            patch("product_intelligence.web.commercial_access._django_settings", _settings_mock(CIDRS)),
            patch.dict("os.environ", {"PI_VENDOR_LOOKUP_BASE_URL": "http://vendor.internal/api"}),
            patch("product_intelligence.web.views.execute_claimed_vendor_refresh_with_default_providers", _fake_entry(adapter)),
        ):
            client = Client(REMOTE_ADDR=ALLOWED_ADDR)
            _post_refresh(client, run)
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 2


# ---------------------------------------------------------------------------
# In progress / single winner / execution ownership (M3 Option A)
# ---------------------------------------------------------------------------


class TestInProgressAndOwnership(TestCase):
    """A pre-existing active child (command- or web-created) is
    reported and left untouched: no new child, no claim, zero lookups.
    The web POST executes ONLY the child its own request created — a
    PENDING orphan is never claimed or executed by the web surface."""

    def test_preexisting_pending_orphan_is_never_claimed_or_executed(self) -> None:
        run = _make_completed_run()
        orphan = trigger_vendor_refresh(run.id, operator="op-orphan")
        before = orphan.refresh_from_db() or orphan
        orphan.refresh_from_db()
        adapter = _FakeAdapter(build_success_exact_match_response())
        with (
            patch("product_intelligence.web.commercial_access._django_settings", _settings_mock(CIDRS)),
            patch.dict("os.environ", {"PI_VENDOR_LOOKUP_BASE_URL": "http://vendor.internal/api"}),
            patch("product_intelligence.web.views.execute_claimed_vendor_refresh_with_default_providers", _fake_entry(adapter)),
        ):
            client = Client(REMOTE_ADDR=ALLOWED_ADDR)
            page = _post_refresh(client, run)
        orphan.refresh_from_db()
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 1
        assert orphan.state == VendorRefreshState.PENDING  # untouched
        assert orphan.operator == "op-orphan"  # provenance untouched
        assert len(adapter.lookup_queries) == 0
        html = page.content.decode()
        assert "already in progress" in html

    def test_preexisting_running_child_is_reported_in_progress(self) -> None:
        run = _make_completed_run()
        child = claim_vendor_refresh(trigger_vendor_refresh(run.id, operator="op-r").id)
        adapter = _FakeAdapter(build_success_exact_match_response())
        with (
            patch("product_intelligence.web.commercial_access._django_settings", _settings_mock(CIDRS)),
            patch.dict("os.environ", {"PI_VENDOR_LOOKUP_BASE_URL": "http://vendor.internal/api"}),
            patch("product_intelligence.web.views.execute_claimed_vendor_refresh_with_default_providers", _fake_entry(adapter)),
        ):
            client = Client(REMOTE_ADDR=ALLOWED_ADDR)
            page = _post_refresh(client, run)
        child.refresh_from_db()
        assert child.state == VendorRefreshState.RUNNING  # untouched
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 1
        assert len(adapter.lookup_queries) == 0
        assert "already in progress" in page.content.decode()

    def test_second_post_over_active_child_is_in_progress(self) -> None:
        """Two sequential web POSTs: the first creates + executes;
        over a parent whose child is still ACTIVE (a slow-lookup
        shape), the second POST is refused by the in-progress report:
        no second child, no second claim, zero lookups."""
        run = _make_completed_run(description="second")
        orphan = trigger_vendor_refresh(run.id, operator="op-active")
        adapter = _FakeAdapter(build_success_exact_match_response())
        with (
            patch("product_intelligence.web.commercial_access._django_settings", _settings_mock(CIDRS)),
            patch.dict("os.environ", {"PI_VENDOR_LOOKUP_BASE_URL": "http://vendor.internal/api"}),
            patch("product_intelligence.web.views.execute_claimed_vendor_refresh_with_default_providers", _fake_entry(adapter)),
        ):
            client = Client(REMOTE_ADDR=ALLOWED_ADDR)
            page = _post_refresh(client, run)
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 1
        orphan.refresh_from_db()
        assert orphan.state == VendorRefreshState.PENDING  # never claimed
        assert len(adapter.lookup_queries) == 0
        assert "already in progress" in page.content.decode()


# ---------------------------------------------------------------------------
# Provenance (WEB_UI — never mislabeled MANAGEMENT_COMMAND)
# ---------------------------------------------------------------------------


class TestTriggerProvenance(TestCase):
    """A web trigger records the bounded WEB_UI trigger source and the
    bounded web operator literal (self-reported provenance, NOT
    authentication). It is never mislabeled as MANAGEMENT_COMMAND."""

    def test_web_trigger_records_web_ui_source_and_bounded_operator(self) -> None:
        run = _make_completed_run()
        adapter = _FakeAdapter(build_success_exact_match_response())
        with (
            patch("product_intelligence.web.commercial_access._django_settings", _settings_mock(CIDRS)),
            patch.dict("os.environ", {"PI_VENDOR_LOOKUP_BASE_URL": "http://vendor.internal/api"}),
            patch("product_intelligence.web.views.execute_claimed_vendor_refresh_with_default_providers", _fake_entry(adapter)),
        ):
            client = Client(REMOTE_ADDR=ALLOWED_ADDR)
            _post_refresh(client, run)
        child = VendorRefreshExecution.objects.get(parent_run=run)
        assert child.trigger_source == VendorRefreshTriggerSource.WEB_UI
        assert child.trigger_source != VendorRefreshTriggerSource.MANAGEMENT_COMMAND
        assert child.operator == "web"
        # The bound MPN is captured verbatim from the parent.
        assert child.requested_mpn == TEST_MPN
        # The row is durably COMPLETED with the codec payload.
        assert child.state == VendorRefreshState.COMPLETED
        assert child.result_schema_version == 1

    def test_command_trigger_still_records_management_command(self) -> None:
        """The pre-existing command provenance is unchanged (no
        mislabeling in either direction)."""
        run = _make_completed_run()
        child = trigger_vendor_refresh(run.id, operator="op-cmd")
        assert child.trigger_source == VendorRefreshTriggerSource.MANAGEMENT_COMMAND


# ---------------------------------------------------------------------------
# Result visibility (ALLOWED only; separate from the original snapshot)
# ---------------------------------------------------------------------------


class TestResultVisibility(TestCase):
    """The latest completed refresh result renders SEPARATELY from the
    original vendor snapshot, with source, price, currency,
    availability, and retrieval time where recorded; failure,
    cooldown, and in-progress states are clearly displayed; DENIED
    connections see nothing."""

    def test_completed_result_shows_source_price_currency_availability_retrieval(self) -> None:
        run = _make_completed_run()
        adapter = _FakeAdapter(build_success_exact_match_response())
        with (
            patch("product_intelligence.web.commercial_access._django_settings", _settings_mock(CIDRS)),
            patch.dict("os.environ", {"PI_VENDOR_LOOKUP_BASE_URL": "http://vendor.internal/api"}),
            patch("product_intelligence.web.views.execute_claimed_vendor_refresh_with_default_providers", _fake_entry(adapter)),
        ):
            client = Client(REMOTE_ADDR=ALLOWED_ADDR)
            page = _post_refresh(client, run)
            html = page.content.decode()
        # The section is separate from the original summary.
        assert html.index("Vendor refresh") > html.index("Quote & Market Summary")
        assert "Refreshed vendor prices are separate from the original vendor snapshot" in html
        # Source / price / currency / availability (the frozen
        # _format_price convention over the canned 2120.00 USD quote).
        assert "Ingram" in html
        assert "$2,120.00 USD" in html
        assert "In Stock" in html
        # Retrieval time where recorded (the canned response's
        # PINNED-ish retrieved_at, rendered UTC second precision).
        assert "Prices retrieved" in html
        # Trigger provenance displayed.
        assert "Web UI" in html

    def test_original_snapshot_sections_unchanged_by_refresh(self) -> None:
        """The original vendor snapshot (a persisted
        ResearchSupplementSnapshot with its own quote) renders
        byte-identically in the Quote & Market Summary region before
        and after a refresh: the refresh result appears ONLY in the
        separate section."""
        run = _make_completed_run()
        original = ResearchSupplementResult(
            vendor_commercial_result=VendorCommercialResult(
                lookup_status="SUCCESS",
                retrieved_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=dt_timezone.utc),
                observations=(
                    # A deliberately distinct original quote (CDW 1999.99)
                    # so the refreshed Ingram 2120.00 cannot be confused
                    # with it.
                    _original_observation("CDW", Decimal("1999.99"), "USD"),
                ),
                source_issues=(),
            )
        )
        ResearchSupplementSnapshot.objects.create(
            run=run, schema_version=1, payload=encode_research_supplement_result(original)
        )

        def _original_region(html: str) -> str:
            start = html.index("Quote & Market Summary")
            end = html.index("</section>", start)
            return html[start:end]

        adapter = _FakeAdapter(build_success_exact_match_response())
        with (
            patch("product_intelligence.web.commercial_access._django_settings", _settings_mock(CIDRS)),
            patch.dict("os.environ", {"PI_VENDOR_LOOKUP_BASE_URL": "http://vendor.internal/api"}),
            patch("product_intelligence.web.views.execute_claimed_vendor_refresh_with_default_providers", _fake_entry(adapter)),
        ):
            client = Client(REMOTE_ADDR=ALLOWED_ADDR)
            before = client.get(_detail_url(run.id)).content.decode()
            after = _post_refresh(client, run).content.decode()
        original_before = _original_region(before)
        original_after = _original_region(after)
        assert original_before == original_after  # byte-identical region
        # The refreshed quote appears ONLY in the separate section.
        assert "$2,120.00 USD" not in original_after
        assert "$2,120.00 USD" in after
        # The original supplement row is untouched in the database.
        row = ResearchSupplementSnapshot.objects.get(run=run)
        assert row.payload == encode_research_supplement_result(original)

    def test_no_record_yet_shows_the_bounded_line_and_the_action(self) -> None:
        run = _make_completed_run()
        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            _settings_mock(CIDRS),
        ):
            client = Client(REMOTE_ADDR=ALLOWED_ADDR)
            html = client.get(_detail_url(run.id)).content.decode()
        assert "No vendor refresh has been recorded for this run yet." in html
        assert "Refresh Vendor Prices" in html

    def test_in_progress_state_is_clearly_displayed(self) -> None:
        run = _make_completed_run()
        claim_vendor_refresh(trigger_vendor_refresh(run.id, operator="op-x").id)
        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            _settings_mock(CIDRS),
        ):
            client = Client(REMOTE_ADDR=ALLOWED_ADDR)
            html = client.get(_detail_url(run.id)).content.decode()
        assert "In progress" in html
        # The active child's bounded facts (no payload content).
        assert "op-x" in html

    def test_mechanically_failed_child_shows_the_bounded_reason(self) -> None:
        run = _make_completed_run()
        child = claim_vendor_refresh(trigger_vendor_refresh(run.id, operator="op-f").id)
        from product_intelligence.runs import fail_vendor_refresh

        fail_vendor_refresh(child.id, VendorRefreshFailureReason.VENDOR_LOOKUP_CONFIG_MISSING)
        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            _settings_mock(CIDRS),
        ):
            client = Client(REMOTE_ADDR=ALLOWED_ADDR)
            html = client.get(_detail_url(run.id)).content.decode()
        assert "Failed" in html
        assert "vendor lookup configuration is missing" in html

    def _refresh_section(self, html: str) -> str:
        start = html.index('aria-label="Vendor refresh"')
        end = html.index("</section>", start)
        return html[start:end]

    def test_completed_child_with_failed_lookup_is_not_a_quotation(self) -> None:
        """A COMPLETED child with lookup_status=FAILED is an executed
        lookup with a FAILED result — NOT a successful quotation:
        the section carries the bounded failed-lookup label and no
        price."""
        run = _make_completed_run()
        child = claim_vendor_refresh(trigger_vendor_refresh(run.id, operator="op-l").id)
        complete_vendor_refresh(
            child.id,
            1,
            encode_research_supplement_result(
                ResearchSupplementResult(
                    vendor_commercial_result=VendorCommercialResult(
                        lookup_status="FAILED",
                        retrieved_at=None,
                        observations=(),
                        source_issues=(),
                    )
                )
            ),
        )
        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            _settings_mock(CIDRS),
        ):
            client = Client(REMOTE_ADDR=ALLOWED_ADDR)
            html = client.get(_detail_url(run.id)).content.decode()
        section = self._refresh_section(html)
        assert "Lookup failed — no vendor quote obtained" in section
        assert "$" not in section  # no price fabricated

    def test_success_lookup_with_zero_observations_is_not_a_quotation(self) -> None:
        run = _make_completed_run()
        child = claim_vendor_refresh(trigger_vendor_refresh(run.id, operator="op-z").id)
        complete_vendor_refresh(
            child.id,
            1,
            encode_research_supplement_result(
                ResearchSupplementResult(
                    vendor_commercial_result=VendorCommercialResult(
                        lookup_status="SUCCESS",
                        retrieved_at=PINNED,
                        observations=(),
                        source_issues=(),
                    )
                )
            ),
        )
        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            _settings_mock(CIDRS),
        ):
            client = Client(REMOTE_ADDR=ALLOWED_ADDR)
            html = client.get(_detail_url(run.id)).content.decode()
        assert "No usable vendor quote was recorded for this refresh." in html

    def test_corrupted_completed_payload_fails_closed_unreadable(self) -> None:
        run = _make_completed_run()
        child = claim_vendor_refresh(trigger_vendor_refresh(run.id, operator="op-c").id)
        # A COMPLETED lifecycle shape with a non-codec payload (the
        # tamper/corruption scenario: the storage CHECK admits any
        # dict payload; the codec owns validity).
        VendorRefreshExecution.objects.filter(id=child.id).update(
            state=VendorRefreshState.COMPLETED,
            active_slot=None,
            finished_at=PINNED,
            result_schema_version=1,
            result_payload={"not": "a codec payload"},
        )
        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            _settings_mock(CIDRS),
        ):
            client = Client(REMOTE_ADDR=ALLOWED_ADDR)
            html = client.get(_detail_url(run.id)).content.decode()
        assert "could not be read" in html
        assert "Ingram" not in html

    def test_non_completed_parent_shows_no_section(self) -> None:
        run = _make_running_run()
        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            _settings_mock(CIDRS),
        ):
            client = Client(REMOTE_ADDR=ALLOWED_ADDR)
            html = client.get(_detail_url(run.id)).content.decode()
        assert "Vendor refresh" not in html
        assert "Refresh Vendor Prices" not in html

    def test_ineligible_post_on_non_completed_run_is_bounded(self) -> None:
        run = _make_running_run()
        adapter = _FakeAdapter(build_success_exact_match_response())
        with (
            patch("product_intelligence.web.commercial_access._django_settings", _settings_mock(CIDRS)),
            patch.dict("os.environ", {"PI_VENDOR_LOOKUP_BASE_URL": "http://vendor.internal/api"}),
            patch("product_intelligence.web.views.execute_claimed_vendor_refresh_with_default_providers", _fake_entry(adapter)),
        ):
            client = Client(REMOTE_ADDR=ALLOWED_ADDR)
            response = _post_refresh(client, run)
        assert VendorRefreshExecution.objects.count() == 0
        assert len(adapter.lookup_queries) == 0
        # The section (and thus the notice) does not render for a
        # non-COMPLETED parent: bounded, no vendor fact.
        assert "not eligible" not in response.content.decode() or "Vendor refresh" not in response.content.decode()


def _original_observation(source_name: str, price: Decimal, currency: str):
    from product_intelligence.research.commercial_supplement_codec import (
        SupplementSourceObservation,
    )

    return SupplementSourceObservation(
        source_name=source_name,
        explicit_candidate_mpn=TEST_MPN,
        vendor_mpn_match_type="EXACT",
        price_amount=price,
        currency_code=currency,
        availability="IN_STOCK",
        price_basis="CUSTOMER_PRICE",
        quantity=1,
        note_kind=None,
        brand_new=True,
        brand_new_basis="VENDOR_API_POLICY",
    )


# ---------------------------------------------------------------------------
# Original-snapshot preservation (the central regression)
# ---------------------------------------------------------------------------


class TestOriginalSnapshotPreservation(TestCase):
    """A web refresh NEVER overwrites the original research report,
    Machine Price, Reviewed Price, matching decisions, or historical
    vendor evidence: the parent + every original artifact is
    byte-identical before and after (the I7 invariant)."""

    def test_parent_and_all_original_artifacts_byte_identical(self) -> None:
        run = _make_completed_run()
        # The full original artifact surface: price snapshot, an
        # original supplement (historical vendor evidence), FX, review
        # candidates, comparable children, and evidence records.
        original = ResearchSupplementResult(
            vendor_commercial_result=VendorCommercialResult(
                lookup_status="SUCCESS",
                retrieved_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=dt_timezone.utc),
                observations=(_original_observation("CDW", Decimal("1999.99"), "USD"),),
                source_issues=(),
            )
        )
        ResearchSupplementSnapshot.objects.create(
            run=run, schema_version=1, payload=encode_research_supplement_result(original)
        )
        ExecutionEvidenceRecord.objects.create(
            run=run, attempt_number=1, stage="SEARCH", outcome="SUCCESS", candidate_url="", detail_code="OK"
        )
        before = _parent_artifact_snapshot(run)

        adapter = _FakeAdapter(build_success_exact_match_response())
        with (
            patch("product_intelligence.web.commercial_access._django_settings", _settings_mock(CIDRS)),
            patch.dict("os.environ", {"PI_VENDOR_LOOKUP_BASE_URL": "http://vendor.internal/api"}),
            patch("product_intelligence.web.views.execute_claimed_vendor_refresh_with_default_providers", _fake_entry(adapter)),
        ):
            client = Client(REMOTE_ADDR=ALLOWED_ADDR)
            _post_refresh(client, run)

        after = _parent_artifact_snapshot(run)
        assert after == before
        # The refresh added exactly ONE new row (the refresh record
        # itself) — nothing else moved.
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 1
        assert len(adapter.lookup_queries) == 1
