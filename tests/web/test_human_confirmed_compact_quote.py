"""Integration tests: Human Confirm Match -> Compact Quote (PROD-FIX1,
defect 4).

A valid run-scoped, human-CONFIRMED semantic candidate MAY contribute to the
Compact Quote for that SAME ResearchRun. It must NEVER alter the frozen
Machine Price snapshot. Human confirmation establishes IDENTITY authority
only — it must not invent or upgrade other facts.

Proofs required by the production correction:

1. Weak/title-only UNREVIEWED semantic candidate absent from Working Quote.
2. CONFIRM candidate -> redirected GET -> candidate appears.
3. Machine Price unchanged byte-for-byte / semantically unchanged.
4. HUMAN_CONFIRMED provenance is explicit.
5. UNKNOWN condition remains Brand New Unknown.
6. NEW condition can truthfully render Brand New Yes.
7. REJECT candidate -> absent.
8. Confirm then Undo -> row disappears.
9. Cross-run candidate cannot enter another run.
10. Invalid/stale binding cannot enter Compact Quote.
11. Historical GET performs zero live provider/network/semantic work.

Plus: the DENIED (public-only) branch shows the confirmed public row while
vendor data remains absent; the frozen Reviewed Price behavior is unchanged.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import (
    ConfidenceLevel,
    EvidenceDecision,
    IdentityMatchType,
    ResearchRunState,
    VerificationStatus,
)
from product_intelligence.execution import semantic_integration
from product_intelligence.providers.fx import EcbFxProvider, FxRateObservation
from product_intelligence.providers.http_page import HttpPageFetcher
from product_intelligence.providers.internal_vendor import InternalVendorAdapter
from product_intelligence.providers.serper import SerperSearchProvider
from product_intelligence.research import (
    PriceAggregateBucket,
    encode_price_aggregation_result,
)
from product_intelligence.research.aggregation import aggregate_listing_prices
from product_intelligence.research.fx_codec import encode_fx_observation
from product_intelligence.research.listings import ExtractionMethod, ListingObservation
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
from product_intelligence.runs.models import (
    AiAssistedReviewCandidate,
    PriceIntelligenceSnapshot,
    ResearchFxSnapshot,
    ResearchRun,
)
from product_intelligence.semantic.runtime import SemanticRuntime


ALLOWED_CIDRS = "10.0.0.0/8"
ALLOWED_ADDR = "10.0.0.1"
DENIED_ADDR = "192.0.2.1"  # TEST-NET-1 — never assigned

MPN = "HCC-MPN-001"
DESCRIPTION = "Human confirmed compact quote test product"

USD_RATE = Decimal("1.0934")


# ---------------------------------------------------------------------------
# Settings / boundary helpers
# ---------------------------------------------------------------------------


def _mock_settings(cidrs: "str | None" = ALLOWED_CIDRS):
    return type("Settings", (), {"PI_VENDOR_PRICE_ALLOWED_CIDRS": cidrs})()


@contextmanager
def _settings_patch(cidrs: "str | None" = ALLOWED_CIDRS):
    from unittest.mock import patch

    with patch(
        "product_intelligence.web.commercial_access._django_settings",
        _mock_settings(cidrs),
    ):
        yield


@contextmanager
def _armed_live_boundaries():
    """Arm every live provider/network/semantic boundary (fail-fast)."""
    import urllib.request
    from unittest.mock import patch

    def _boom(*args, **kwargs):
        raise RuntimeError("live provider/network boundary touched")

    with (
        patch.object(SerperSearchProvider, "search", side_effect=_boom),
        patch.object(HttpPageFetcher, "fetch", side_effect=_boom),
        patch.object(InternalVendorAdapter, "lookup", side_effect=_boom),
        patch.object(EcbFxProvider, "__init__", side_effect=_boom),
        patch.object(EcbFxProvider, "fetch_rates", side_effect=_boom),
        patch.object(SemanticRuntime, "evaluate", side_effect=_boom),
        patch.object(
            semantic_integration,
            "evaluate_semantic_matches",
            side_effect=_boom,
        ),
        patch("urllib.request.urlopen", side_effect=_boom),
        patch("urllib.request.OpenerDirector.open", side_effect=_boom),
    ):
        yield


# ---------------------------------------------------------------------------
# Assessment / candidate builders
# ---------------------------------------------------------------------------


def _semantic_observation(
    source_url: str,
    title: str,
    price: Decimal,
    currency: str,
    condition_text: str,
) -> ListingObservation:
    return ListingObservation(
        source_url=source_url,
        extraction_method=ExtractionMethod.JSON_LD,
        product_title=title,
        manufacturer_part_number_text="",  # -> None: no explicit MPN field
        sku_text=None,
        brand_text=None,
        price_text=str(price),
        currency_text=currency,
        availability_text="In Stock",
        condition_text=condition_text,
        seller_text="Semantic Seller",
        offer_url_text=None,
        raw_reference=None,
    )


def _semantic_assessment(
    obs: ListingObservation,
    condition: NormalizedCondition,
    price: Decimal,
    currency: str,
) -> ListingIdentityAssessment:
    norm = NormalizedListingObservation(
        observation=obs,
        price_amount=price,
        currency_code=currency,
        availability=NormalizedAvailability.IN_STOCK,
        condition=condition,
        seller_name="Semantic Seller",
        normalization_issues=(),
    )
    return ListingIdentityAssessment(
        normalized_listing=norm,
        requested_part_number=MPN,
        candidate_part_number_raw=MPN,  # TITLE_TEXT: requested MPN token in title
        candidate_part_number_compared=MPN,
        candidate_evidence_source=EvidenceSource.TITLE_TEXT,
        match_type=IdentityMatchType.UNKNOWN,
        decision=EvidenceDecision.REJECTED,
        rejection_reason=IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE,
    )


def _accepted_assessment(
    source_url: str, price: Decimal, currency: str
) -> ListingIdentityAssessment:
    obs = ListingObservation(
        source_url=source_url,
        extraction_method=ExtractionMethod.JSON_LD,
        product_title=f"Deterministic listing for {MPN}",
        manufacturer_part_number_text=MPN,
        sku_text=None,
        brand_text=None,
        price_text=str(price),
        currency_text=currency,
        availability_text="In Stock",
        condition_text="New",
        seller_text="Det Seller",
        offer_url_text=None,
        raw_reference=None,
    )
    norm = NormalizedListingObservation(
        observation=obs,
        price_amount=price,
        currency_code=currency,
        availability=NormalizedAvailability.IN_STOCK,
        condition=NormalizedCondition.NEW,
        seller_name="Det Seller",
        normalization_issues=(),
    )
    return ListingIdentityAssessment(
        normalized_listing=norm,
        requested_part_number=MPN,
        candidate_part_number_raw=MPN,
        candidate_part_number_compared=MPN,
        candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
        match_type=IdentityMatchType.EXACT,
        decision=EvidenceDecision.ACCEPTED,
        rejection_reason=None,
    )


def _persist_fx(run: ResearchRun) -> None:
    payload = encode_fx_observation(
        provider_id="ECB",
        observation_date=date(2026, 9, 23),
        base_currency="EUR",
        rates=(
            FxRateObservation(currency_code="USD", rate=USD_RATE),
            FxRateObservation(currency_code="EUR", rate=Decimal("1")),
        ),
        retrieved_at=datetime(2026, 9, 23, 12, 0, 0, tzinfo=timezone.utc),
    )
    ResearchFxSnapshot.objects.create(run=run, schema_version=1, payload=payload)


def _make_completed_run(
    *,
    unknown_semantic_url: str = "https://semantic-unknown.example.com/u",
    new_semantic_url: str = "https://semantic-new.example.com/n",
    accepted_url: str = "https://deterministic.example.com/a",
) -> tuple[ResearchRun, ListingObservation, ListingObservation]:
    """A COMPLETED run with one deterministic bucket (1500 EUR NEW) and two
    semantic-eligible REJECTED assessments:

    * index 1: 1890 USD, condition UNKNOWN
    * index 2: 1635 USD, condition NEW
    """
    request = ResearchRequest(manufacturer_part_number=MPN, description=DESCRIPTION)
    run = ResearchRun.objects.create_from_request(request)
    run.transition_to(ResearchRunState.RUNNING)
    run.transition_to(ResearchRunState.COMPLETED)

    accepted = _accepted_assessment(accepted_url, Decimal("1500.00"), "EUR")

    obs_unknown = _semantic_observation(
        unknown_semantic_url,
        f"Great deal {MPN} drive 1890",
        Decimal("1890.00"),
        "USD",
        "unknown",
    )
    sem_unknown = _semantic_assessment(
        obs_unknown, NormalizedCondition.UNKNOWN, Decimal("1890.00"), "USD"
    )

    obs_new = _semantic_observation(
        new_semantic_url,
        f"Brand new {MPN} enterprise 1635",
        Decimal("1635.00"),
        "USD",
        "New",
    )
    sem_new = _semantic_assessment(
        obs_new, NormalizedCondition.NEW, Decimal("1635.00"), "USD"
    )

    price_result = aggregate_listing_prices(request, (accepted, sem_unknown, sem_new))
    PriceIntelligenceSnapshot.objects.create(
        run=run,
        schema_version=1,
        payload=encode_price_aggregation_result(price_result),
    )
    _persist_fx(run)
    return run, obs_unknown, obs_new


def _make_candidate(run: ResearchRun, obs: ListingObservation, index: int) -> AiAssistedReviewCandidate:
    """A binding-exact review candidate for one semantic observation."""
    return AiAssistedReviewCandidate.objects.create(
        run=run,
        assessment_index=index,
        source_url=obs.source_url,
        target_mpn=MPN,
        target_description=DESCRIPTION,
        candidate_title=obs.product_title or "",
        candidate_mpn_field=obs.manufacturer_part_number_text or "",
        candidate_sku=obs.sku_text or "",
        evidence_source="TITLE_TEXT",
        actual_provider="amax",
        actual_model="nemotron-3-super",
        prompt_version="v1.1",
    )


def _review_url(run: ResearchRun, candidate: AiAssistedReviewCandidate) -> str:
    return reverse(
        "research-review",
        kwargs={"run_id": run.id, "candidate_id": candidate.id},
    )


def _detail_url(run: ResearchRun) -> str:
    return reverse("research-detail", kwargs={"run_id": run.id})


def _detail_rows(client: Client, run: ResearchRun, addr: str = ALLOWED_ADDR):
    with _settings_patch():
        response = client.get(_detail_url(run), REMOTE_ADDR=addr)
    assert response.status_code == 200
    compact = response.context["compact_quote"]
    assert compact is not None
    return response, list(compact.rows)


# ---------------------------------------------------------------------------
# Fixture for DB isolation (plain pytest functions)
# ---------------------------------------------------------------------------


@pytest.fixture
def human_confirmed_db_isolation():
    yield
    from django.db import transaction

    from product_intelligence.runs.models import (
        ResearchMicronAliasSnapshot,
    )

    with transaction.atomic():
        AiAssistedReviewCandidate.objects.all().delete()
        ResearchFxSnapshot.objects.all().delete()
        ResearchMicronAliasSnapshot.objects.all().delete()
        PriceIntelligenceSnapshot.objects.all().delete()
        ResearchRun.objects.all().delete()


@pytest.fixture
def client() -> Client:
    return Client()


# ---------------------------------------------------------------------------
# Proof 1: UNREVIEWED candidate absent
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("human_confirmed_db_isolation")
def test_1_unreviewed_candidate_absent_from_compact_quote(client: Client) -> None:
    run, obs_unknown, obs_new = _make_completed_run()
    cand_unknown = _make_candidate(run, obs_unknown, 1)
    cand_new = _make_candidate(run, obs_new, 2)
    assert cand_unknown.review_state == "UNREVIEWED"
    assert cand_new.review_state == "UNREVIEWED"

    _, rows = _detail_rows(client, run)

    human_rows = [r for r in rows if r.note and "Human Confirmed" in r.note]
    assert human_rows == []
    # Neither semantic price is in the compact quote
    prices = [r.price for r in rows]
    assert "$1,890.00 USD" not in prices
    assert "$1,635.00 USD" not in prices
    # The deterministic bucket row is present
    assert any(r.price == "€1,500.00 EUR" for r in rows)


# ---------------------------------------------------------------------------
# Proof 2: CONFIRM -> redirected GET -> appears
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("human_confirmed_db_isolation")
def test_2_confirm_then_get_shows_candidate(client: Client) -> None:
    run, obs_unknown, _ = _make_completed_run()
    cand = _make_candidate(run, obs_unknown, 1)

    # POST confirm redirects to the detail page
    response = client.post(
        _review_url(run, cand), {"action": "confirm"}, follow=False
    )
    assert response.status_code == 302
    assert _detail_url(run) in response["Location"]

    # Redirected GET: the candidate now appears in the Compact Quote
    _, rows = _detail_rows(client, run)
    human_rows = [r for r in rows if r.note == "Human Confirmed"]
    assert len(human_rows) == 1
    row = human_rows[0]
    assert row.price == "$1,890.00 USD"
    # USD pass-through equivalent (no FX needed for USD)
    assert row.usd_equivalent == "$1,890.00 USD"
    # Source: the public listing hostname (www.-stripped display)
    assert row.source_display == "semantic-unknown.example.com"
    assert row.source_url == "https://semantic-unknown.example.com/u"
    assert row.source_url_safe is True


# ---------------------------------------------------------------------------
# Proof 3: Machine Price unchanged byte-for-byte
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("human_confirmed_db_isolation")
def test_3_machine_price_unchanged_by_confirmation(client: Client) -> None:
    run, obs_unknown, _ = _make_completed_run()
    cand = _make_candidate(run, obs_unknown, 1)

    snapshot_before = PriceIntelligenceSnapshot.objects.get(run=run)
    bytes_before = (
        snapshot_before.schema_version,
        snapshot_before.payload,
    )

    response = client.post(
        _review_url(run, cand), {"action": "confirm"}, follow=True
    )
    assert response.status_code == 200

    snapshot_after = PriceIntelligenceSnapshot.objects.get(run=run)
    # Byte-for-byte identical frozen 4A artifact
    assert snapshot_after.schema_version == bytes_before[0]
    assert snapshot_after.payload == bytes_before[1]

    # Semantically: the Machine Price bucket is unchanged
    report = response.context["report_presentation"]
    assert report is not None
    assert len(report.buckets) == 1
    assert report.buckets[0].count == 1
    assert report.buckets[0].median == "1500.00"


# ---------------------------------------------------------------------------
# Proof 4: HUMAN_CONFIRMED provenance is explicit
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("human_confirmed_db_isolation")
def test_4_human_confirmed_provenance_explicit(client: Client) -> None:
    run, obs_unknown, _ = _make_completed_run()
    cand = _make_candidate(run, obs_unknown, 1)
    client.post(_review_url(run, cand), {"action": "confirm"})

    with _settings_patch():
        response = client.get(_detail_url(run), REMOTE_ADDR=ALLOWED_ADDR)
    assert response.status_code == 200

    rows = list(response.context["compact_quote"].rows)
    human_rows = [r for r in rows if r.note == "Human Confirmed"]
    assert len(human_rows) == 1
    html = response.content.decode()
    # The rendered compact quote section carries the provenance
    compact_start = html.index("<h2>Quote & Market Summary</h2>")
    compact_end = html.index("<h2>AI-assisted evidence & review</h2>")
    compact_section = html[compact_start:compact_end]
    assert "Human Confirmed" in compact_section


# ---------------------------------------------------------------------------
# Proof 5: UNKNOWN condition remains Brand New Unknown
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("human_confirmed_db_isolation")
def test_5_unknown_condition_not_upgraded(client: Client) -> None:
    run, obs_unknown, _ = _make_completed_run()
    cand = _make_candidate(run, obs_unknown, 1)
    client.post(_review_url(run, cand), {"action": "confirm"})

    _, rows = _detail_rows(client, run)
    human_rows = [r for r in rows if r.note == "Human Confirmed"]
    assert len(human_rows) == 1
    # CRITICAL: UNKNOWN condition must NOT become Yes
    assert human_rows[0].brand_new == "Unknown"
    # Price is exactly the persisted value
    assert human_rows[0].price == "$1,890.00 USD"


# ---------------------------------------------------------------------------
# Proof 6: NEW condition can truthfully render Brand New Yes
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("human_confirmed_db_isolation")
def test_6_new_condition_renders_yes(client: Client) -> None:
    run, _, obs_new = _make_completed_run()
    cand = _make_candidate(run, obs_new, 2)
    client.post(_review_url(run, cand), {"action": "confirm"})

    _, rows = _detail_rows(client, run)
    human_rows = [r for r in rows if r.note == "Human Confirmed"]
    assert len(human_rows) == 1
    assert human_rows[0].brand_new == "Yes"
    assert human_rows[0].price == "$1,635.00 USD"


# ---------------------------------------------------------------------------
# Proof 7: REJECT -> absent
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("human_confirmed_db_isolation")
def test_7_rejected_candidate_absent(client: Client) -> None:
    run, _, obs_new = _make_completed_run()
    cand = _make_candidate(run, obs_new, 2)
    client.post(_review_url(run, cand), {"action": "reject"})

    _, rows = _detail_rows(client, run)
    assert [r for r in rows if r.note == "Human Confirmed"] == []
    prices = [r.price for r in rows]
    assert "$1,635.00 USD" not in prices


# ---------------------------------------------------------------------------
# Proof 8: Confirm then Undo -> row disappears
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("human_confirmed_db_isolation")
def test_8_confirm_then_undo_removes_row(client: Client) -> None:
    run, obs_unknown, _ = _make_completed_run()
    cand = _make_candidate(run, obs_unknown, 1)

    client.post(_review_url(run, cand), {"action": "confirm"})
    _, rows = _detail_rows(client, run)
    assert len([r for r in rows if r.note == "Human Confirmed"]) == 1

    # Undo on the next request
    client.post(_review_url(run, cand), {"action": "undo"})
    cand.refresh_from_db()
    assert cand.review_state == "UNREVIEWED"

    # The effective Compact Quote projection no longer contains the row
    _, rows = _detail_rows(client, run)
    assert [r for r in rows if r.note == "Human Confirmed"] == []
    prices = [r.price for r in rows]
    assert "$1,890.00 USD" not in prices


# ---------------------------------------------------------------------------
# Proof 9: Cross-run candidate cannot enter another run
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("human_confirmed_db_isolation")
def test_9_cross_run_candidate_cannot_enter_another_run(client: Client) -> None:
    # Run A: confirm its candidate
    run_a, obs_a, _ = _make_completed_run(
        unknown_semantic_url="https://cross-a.example.com/u",
        new_semantic_url="https://cross-a.example.com/n",
        accepted_url="https://cross-a.example.com/a",
    )
    cand_a = _make_candidate(run_a, obs_a, 1)
    client.post(_review_url(run_a, cand_a), {"action": "confirm"})

    # Run B: different content, its own UNREVIEWED candidate
    run_b, obs_b, _ = _make_completed_run(
        unknown_semantic_url="https://cross-b.example.com/u",
        new_semantic_url="https://cross-b.example.com/n",
        accepted_url="https://cross-b.example.com/a",
    )
    cand_b = _make_candidate(run_b, obs_b, 1)
    assert cand_b.review_state == "UNREVIEWED"

    _, rows_a = _detail_rows(client, run_a)
    assert len([r for r in rows_a if r.note == "Human Confirmed"]) == 1

    # B's compact quote must NOT contain A's confirmed candidate row
    _, rows_b = _detail_rows(client, run_b)
    human_rows_b = [r for r in rows_b if r.note == "Human Confirmed"]
    assert human_rows_b == []
    # A's confirmed price/URL must not leak into B
    for row in rows_b:
        assert row.price != "$1,890.00 USD"
    with _settings_patch():
        response_b = client.get(_detail_url(run_b), REMOTE_ADDR=ALLOWED_ADDR)
    assert "cross-a.example.com" not in response_b.content.decode()


# ---------------------------------------------------------------------------
# Proof 10: Invalid/stale binding cannot enter Compact Quote
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("human_confirmed_db_isolation")
def test_10_invalid_stale_binding_cannot_enter(client: Client) -> None:
    run, obs_unknown, _ = _make_completed_run()
    cand = _make_candidate(run, obs_unknown, 1)
    client.post(_review_url(run, cand), {"action": "confirm"})
    cand.refresh_from_db()
    assert cand.review_state == "CONFIRMED"

    # Corrupt the persisted binding AFTER confirmation (simulate stale /
    # tampered candidate provenance). The GET must fail closed: the row
    # does not enter the Compact Quote.
    AiAssistedReviewCandidate.objects.filter(id=cand.id).update(
        candidate_title="TAMPERED TITLE THAT MATCHES NOTHING"
    )

    with _settings_patch():
        response = client.get(_detail_url(run), REMOTE_ADDR=ALLOWED_ADDR)
    assert response.status_code == 200
    rows = list(response.context["compact_quote"].rows)
    assert [r for r in rows if r.note == "Human Confirmed"] == []
    # The review section shows the candidate as unavailable (binding failed)
    presentations = response.context["review_candidates"]
    assert presentations[0].binding_valid is False
    # Reviewed Price is also excluded (same fail-closed binding)
    assert response.context["reviewed_result"] is None


@pytest.mark.usefixtures("human_confirmed_db_isolation")
def test_10b_stale_out_of_range_index_cannot_enter(client: Client) -> None:
    """A CONFIRMED candidate whose index no longer maps into the persisted
    snapshot (stale binding) cannot produce a Compact Quote row."""
    run, obs_unknown, _ = _make_completed_run()
    cand = _make_candidate(run, obs_unknown, 1)
    client.post(_review_url(run, cand), {"action": "confirm"})

    # Forge an out-of-range index directly at persistence level (the
    # service layer would refuse it; this proves the read side is
    # independently fail-closed).
    AiAssistedReviewCandidate.objects.filter(id=cand.id).update(
        assessment_index=99
    )

    with _settings_patch():
        response = client.get(_detail_url(run), REMOTE_ADDR=ALLOWED_ADDR)
    assert response.status_code == 200
    rows = list(response.context["compact_quote"].rows)
    assert [r for r in rows if r.note == "Human Confirmed"] == []


# ---------------------------------------------------------------------------
# Proof 11: Historical GET performs zero live work
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("human_confirmed_db_isolation")
def test_11_historical_get_zero_live_work_with_confirmation(client: Client) -> None:
    run, obs_unknown, obs_new = _make_completed_run()
    cand_unknown = _make_candidate(run, obs_unknown, 1)
    cand_new = _make_candidate(run, obs_new, 2)
    client.post(_review_url(run, cand_unknown), {"action": "confirm"})
    client.post(_review_url(run, cand_new), {"action": "confirm"})

    with _settings_patch(), _armed_live_boundaries():
        response = client.get(_detail_url(run), REMOTE_ADDR=ALLOWED_ADDR)
    assert response.status_code == 200
    rows = list(response.context["compact_quote"].rows)
    human_rows = [r for r in rows if r.note == "Human Confirmed"]
    # Both confirmed candidates present — recomputed purely from persisted
    # artifacts, with every live boundary armed.
    assert len(human_rows) == 2
    prices = sorted(r.price for r in human_rows)
    assert prices == ["$1,635.00 USD", "$1,890.00 USD"]


# ---------------------------------------------------------------------------
# Authority separation: vendor supplemental remains separate
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("human_confirmed_db_isolation")
def test_denied_branch_shows_confirmed_row_but_no_vendor(client: Client) -> None:
    """The human-confirmed row is public-listing evidence: it renders on
    the DENIED (public-only) branch as well, while vendor data stays
    absent."""
    run, obs_unknown, _ = _make_completed_run()
    cand = _make_candidate(run, obs_unknown, 1)
    client.post(_review_url(run, cand), {"action": "confirm"})

    _, rows = _detail_rows(client, run, addr=DENIED_ADDR)
    human_rows = [r for r in rows if r.note == "Human Confirmed"]
    assert len(human_rows) == 1
    assert human_rows[0].price == "$1,890.00 USD"
    # No vendor rows on the denied branch
    assert all("Vendor API" not in (r.source_display or "") for r in rows)


@pytest.mark.usefixtures("human_confirmed_db_isolation")
def test_reviewed_price_behavior_unchanged(client: Client) -> None:
    """Frozen Reviewed Price semantics: the confirmed UNKNOWN-condition
    candidate does NOT enter the Reviewed Price bucket (price eligibility
    unchanged) while the NEW-condition one does."""
    run, obs_unknown, obs_new = _make_completed_run()
    cand_unknown = _make_candidate(run, obs_unknown, 1)
    cand_new = _make_candidate(run, obs_new, 2)
    client.post(_review_url(run, cand_unknown), {"action": "confirm"})
    client.post(_review_url(run, cand_new), {"action": "confirm"})

    with _settings_patch():
        response = client.get(_detail_url(run), REMOTE_ADDR=ALLOWED_ADDR)
    assert response.status_code == 200
    reviewed = response.context["reviewed_result"]
    assert reviewed is not None
    assert response.context["confirmed_count"] == 2
    # Only the NEW-condition confirmed listing is price-eligible (USD),
    # separate from the deterministic EUR bucket
    usd_buckets = [b for b in reviewed.buckets if b.currency_code == "USD"]
    assert len(usd_buckets) == 1
    assert usd_buckets[0].count == 1
    assert usd_buckets[0].human_confirmed_count == 1
    # The UNKNOWN-condition confirmation still renders in the Compact
    # Quote (display), but never in the reviewed price arithmetic
    human_rows = [
        r for r in response.context["compact_quote"].rows
        if r.note == "Human Confirmed"
    ]
    assert len(human_rows) == 2


@pytest.mark.usefixtures("human_confirmed_db_isolation")
def test_no_confirmation_no_human_rows_semantics_unchanged(client: Client) -> None:
    """Without any human confirmation, the projection is exactly the frozen
    4D-C behavior (public bucket rows only)."""
    run, _, _ = _make_completed_run()
    with _settings_patch():
        response = client.get(_detail_url(run), REMOTE_ADDR=ALLOWED_ADDR)
    rows = list(response.context["compact_quote"].rows)
    assert len(rows) == 1
    assert rows[0].price == "€1,500.00 EUR"
    assert response.context["reviewed_result"] is None


# ---------------------------------------------------------------------------
# FU1: Reviewed Price wording accuracy — the summary sentence must state
# the PRICE-CONTRIBUTING confirmed count (from the reviewed buckets
# themselves), never the validated-CONFIRMED-candidate count.
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("human_confirmed_db_isolation")
def test_reviewed_price_wording_uses_price_contributing_count(client: Client) -> None:
    """confirmed_count = 2, but only 1 confirmed candidate is
    price-eligible for Reviewed Price (the other has UNKNOWN condition).
    The sentence must not falsely say the Reviewed Price "includes 2".
    """
    run, obs_unknown, obs_new = _make_completed_run()
    cand_unknown = _make_candidate(run, obs_unknown, 1)
    cand_new = _make_candidate(run, obs_new, 2)
    client.post(_review_url(run, cand_unknown), {"action": "confirm"})
    client.post(_review_url(run, cand_new), {"action": "confirm"})

    with _settings_patch():
        response = client.get(_detail_url(run), REMOTE_ADDR=ALLOWED_ADDR)
    assert response.status_code == 200

    # The candidate-level count is still 2 (unchanged context contract)...
    assert response.context["confirmed_count"] == 2
    # ...but the truthful PRICE-CONTRIBUTING counts come from the buckets:
    # 1 human-confirmed (the NEW-condition 1635 USD listing) and 1
    # deterministic (the 1500 EUR listing). The UNKNOWN-condition confirmed
    # listing is NOT in any reviewed bucket.
    assert response.context["reviewed_confirmed_price_count"] == 1
    assert response.context["reviewed_deterministic_price_count"] == 1

    html = response.content.decode()
    reviewed_start = html.index("<h2>Reviewed price</h2>")
    reviewed_end = html.index("<h3>Reviewed comparable price group</h3>")
    summary = " ".join(html[reviewed_start:reviewed_end].split())
    # Truthful wording: exactly ONE human-confirmed listing is in the price.
    assert (
        "This price includes 1 human-confirmed AI-assisted listing "
        "in addition to 1 deterministic match."
    ) in summary
    # The overclaim must be gone.
    assert "includes 2 human-confirmed" not in summary
    assert "2 human-confirmed AI-assisted" not in summary


@pytest.mark.usefixtures("human_confirmed_db_isolation")
def test_reviewed_price_wording_when_no_confirmed_listing_is_price_eligible(
    client: Client,
) -> None:
    """A run whose ONLY assessment is a semantic-eligible UNKNOWN-condition
    listing, confirmed by the human: zero reviewed price buckets. The
    wording must state that no price groups are available — never that the
    price "includes" the confirmed listing."""
    request = ResearchRequest(manufacturer_part_number=MPN, description=DESCRIPTION)
    run = ResearchRun.objects.create_from_request(request)
    run.transition_to(ResearchRunState.RUNNING)
    run.transition_to(ResearchRunState.COMPLETED)

    obs = _semantic_observation(
        "https://wording-none.example.com/u",
        f"Only listing {MPN} no price group",
        Decimal("1890.00"),
        "USD",
        "unknown",
    )
    sem = _semantic_assessment(obs, NormalizedCondition.UNKNOWN, Decimal("1890.00"), "USD")
    price_result = aggregate_listing_prices(request, (sem,))
    PriceIntelligenceSnapshot.objects.create(
        run=run,
        schema_version=1,
        payload=encode_price_aggregation_result(price_result),
    )
    cand = _make_candidate(run, obs, 0)
    client.post(_review_url(run, cand), {"action": "confirm"})

    with _settings_patch():
        response = client.get(_detail_url(run), REMOTE_ADDR=ALLOWED_ADDR)
    assert response.status_code == 200

    assert response.context["confirmed_count"] == 1
    assert response.context["reviewed_confirmed_price_count"] == 0
    assert response.context["reviewed_deterministic_price_count"] == 0
    reviewed = response.context["reviewed_result"]
    assert reviewed is not None
    assert reviewed.buckets == []

    html = response.content.decode()
    reviewed_start = html.index("<h2>Reviewed price</h2>")
    nxt = html.find("<h2>", reviewed_start + 10)
    summary = " ".join(html[reviewed_start : nxt if nxt != -1 else len(html)].split())
    assert "No price groups are available" in summary
    assert "includes 1 human-confirmed" not in summary

# ---------------------------------------------------------------------------
# B3 end-to-end: auto-included HIGH SKU row + inline remove/restore
# ---------------------------------------------------------------------------


def _make_auto_ai_completed_run(
    *,
    confidence: str = "HIGH",
    conflicts: tuple[str, ...] = (),
    evidence_source: EvidenceSource = EvidenceSource.SKU_FIELD,
) -> tuple[ResearchRun, AiAssistedReviewCandidate]:
    """Completed USD run with one deterministic $120 row and one AI $100 row."""
    request = ResearchRequest(manufacturer_part_number=MPN, description=DESCRIPTION)
    run = ResearchRun.objects.create_from_request(request)
    run.transition_to(ResearchRunState.RUNNING)
    run.transition_to(ResearchRunState.COMPLETED)

    deterministic = _accepted_assessment(
        "https://det-working.example.com/item",
        Decimal("120.00"),
        "USD",
    )

    if evidence_source is EvidenceSource.SKU_FIELD:
        title = "AI assisted candidate"
        sku = MPN
    else:
        title = f"AI assisted candidate {MPN}"
        sku = None

    obs = ListingObservation(
        source_url="https://ai-working.example.com/item",
        extraction_method=ExtractionMethod.JSON_LD,
        product_title=title,
        manufacturer_part_number_text="",
        sku_text=sku,
        brand_text="Example",
        price_text="100.00",
        currency_text="USD",
        availability_text="In Stock",
        condition_text="unknown",
        seller_text="AI Working Seller",
        offer_url_text=None,
        raw_reference=None,
    )
    norm = NormalizedListingObservation(
        observation=obs,
        price_amount=Decimal("100.00"),
        currency_code="USD",
        availability=NormalizedAvailability.IN_STOCK,
        condition=NormalizedCondition.UNKNOWN,
        seller_name="AI Working Seller",
        normalization_issues=(),
    )
    semantic = ListingIdentityAssessment(
        normalized_listing=norm,
        requested_part_number=MPN,
        candidate_part_number_raw=MPN,
        candidate_part_number_compared=MPN,
        candidate_evidence_source=evidence_source,
        match_type=IdentityMatchType.UNKNOWN,
        decision=EvidenceDecision.REJECTED,
        rejection_reason=IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE,
    )

    result = aggregate_listing_prices(request, (deterministic, semantic))
    PriceIntelligenceSnapshot.objects.create(
        run=run,
        schema_version=1,
        payload=encode_price_aggregation_result(result),
    )
    candidate = AiAssistedReviewCandidate.objects.create(
        run=run,
        assessment_index=1,
        source_url=obs.source_url,
        target_mpn=MPN,
        target_description=DESCRIPTION,
        candidate_title=obs.product_title or "",
        candidate_mpn_field="",
        candidate_sku=obs.sku_text or "",
        candidate_specs=(f"SKU: {MPN}" if sku else ""),
        evidence_source=evidence_source.value,
        semantic_confidence=confidence,
        semantic_reason_code="exact_mpn_match",
        semantic_matched_attributes=["mpn"],
        semantic_conflicting_attributes=list(conflicts),
        actual_provider="amax",
        actual_model="nemotron-3-super",
        prompt_version="v1.1",
    )
    return run, candidate


@pytest.mark.usefixtures("human_confirmed_db_isolation")
def test_b3_high_exact_sku_auto_included_with_inline_actions(client: Client) -> None:
    run, candidate = _make_auto_ai_completed_run()

    with _settings_patch(), _armed_live_boundaries():
        response = client.get(_detail_url(run), REMOTE_ADDR=ALLOWED_ADDR)
    assert response.status_code == 200

    compact = response.context["compact_quote"]
    assert compact.quotes_found == 2
    assert compact.in_stock_count == 2
    assert compact.lowest_in_stock_price == "$100.00 USD"
    assert compact.lowest_in_stock_source == "ai-working.example.com"
    assert compact.public_market_count == 1

    ai_rows = [r for r in compact.rows if r.source_type == "AI_ASSISTED_UNVERIFIED"]
    assert len(ai_rows) == 1
    ai_row = ai_rows[0]
    assert ai_row.review_candidate_id == str(candidate.id)
    assert ai_row.condition == "Not stated"
    assert ai_row.match_evidence == "AI High — Not human verified"
    assert ai_row.market_use == "Quote only — AI-assisted"

    deterministic_rows = [r for r in compact.rows if r.source_type == "PUBLIC_LISTING"]
    assert len(deterministic_rows) == 1
    assert deterministic_rows[0].review_candidate_id is None

    html = response.content.decode()
    assert f'id="quote-row-{candidate.id}"' in html
    assert f'id="ai-candidate-{candidate.id}"' in html
    assert "Review / Verify" in html
    assert 'name="action" value="remove"' in html
    assert "Verify / Confirm" in html


@pytest.mark.usefixtures("human_confirmed_db_isolation")
def test_b3_remove_recomputes_summary_and_restore_returns_auto_row(client: Client) -> None:
    run, candidate = _make_auto_ai_completed_run()

    response = client.post(_review_url(run, candidate), {"action": "remove"})
    assert response.status_code == 302
    candidate.refresh_from_db()
    assert candidate.review_state == "REJECTED"

    response, rows = _detail_rows(client, run)
    compact = response.context["compact_quote"]
    assert compact.quotes_found == 1
    assert compact.in_stock_count == 1
    assert compact.lowest_in_stock_price == "$120.00 USD"
    assert compact.lowest_in_stock_source == "det-working.example.com"
    assert [r.source_type for r in rows] == ["PUBLIC_LISTING"]
    assert len(response.context["ai_rejected_candidates"]) == 1
    assert "Restore" in response.content.decode()

    response = client.post(_review_url(run, candidate), {"action": "undo"})
    assert response.status_code == 302
    candidate.refresh_from_db()
    assert candidate.review_state == "UNREVIEWED"

    response, rows = _detail_rows(client, run)
    compact = response.context["compact_quote"]
    assert compact.quotes_found == 2
    assert compact.in_stock_count == 2
    assert compact.lowest_in_stock_price == "$100.00 USD"
    assert any(r.source_type == "AI_ASSISTED_UNVERIFIED" for r in rows)


@pytest.mark.usefixtures("human_confirmed_db_isolation")
def test_b3_confirm_replaces_unreviewed_row_without_duplicate(client: Client) -> None:
    run, candidate = _make_auto_ai_completed_run()

    response = client.post(_review_url(run, candidate), {"action": "confirm"})
    assert response.status_code == 302
    candidate.refresh_from_db()
    assert candidate.review_state == "CONFIRMED"

    response, rows = _detail_rows(client, run)
    assert len([r for r in rows if r.source_type == "HUMAN_CONFIRMED"]) == 1
    assert len([r for r in rows if r.source_type == "AI_ASSISTED_UNVERIFIED"]) == 0
    human = [r for r in rows if r.source_type == "HUMAN_CONFIRMED"][0]
    assert human.review_candidate_id == str(candidate.id)
    assert human.match_evidence == "AI High — Human confirmed"
    assert response.context["compact_quote"].quotes_found == 2
    assert "Remove from quote" in response.content.decode()


@pytest.mark.usefixtures("human_confirmed_db_isolation")
@pytest.mark.parametrize(
    ("confidence", "evidence_source", "conflicts", "expected_group"),
    (
        ("MEDIUM", EvidenceSource.SKU_FIELD, (), "ai_needs_review_candidates"),
        ("LOW", EvidenceSource.SKU_FIELD, (), "ai_low_confidence_candidates"),
        ("HIGH", EvidenceSource.TITLE_TEXT, (), "ai_needs_review_candidates"),
        ("HIGH", EvidenceSource.SKU_FIELD, ("capacity",), "ai_needs_review_candidates"),
    ),
)
def test_b3_non_auto_tiers_stay_out_of_quote_and_remain_reviewable(
    client: Client,
    confidence: str,
    evidence_source: EvidenceSource,
    conflicts: tuple[str, ...],
    expected_group: str,
) -> None:
    run, candidate = _make_auto_ai_completed_run(
        confidence=confidence,
        conflicts=conflicts,
        evidence_source=evidence_source,
    )

    response, rows = _detail_rows(client, run)
    candidate.refresh_from_db()
    assert candidate.review_state == "UNREVIEWED"
    assert not any(
        r.source_type in ("AI_ASSISTED_UNVERIFIED", "HUMAN_CONFIRMED")
        for r in rows
    )
    assert response.context["compact_quote"].quotes_found == 1
    group = response.context[expected_group]
    assert [c.candidate_id for c in group] == [str(candidate.id)]

    html = response.content.decode()
    if confidence == "LOW":
        assert "Other possible sources — low confidence (1)" in html
    else:
        assert "Possible matches — needs review" in html
    assert 'name="action" value="confirm"' in html
    if confidence == "LOW":
        # Low confidence stays UNREVIEWED and excluded by default.
        # Include remains available without an eager Reject action.
        assert 'name="action" value="reject"' not in html
    else:
        assert 'name="action" value="reject"' in html

