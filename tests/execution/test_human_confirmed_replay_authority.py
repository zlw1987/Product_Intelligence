"""Replay/service boundary authority tests: human-confirmed Compact Quote
rows (PROD-FIX1-FU1, BLOCKER 2).

The authority defect: PROD-FIX1 let the replay/service boundary accept
``confirmed_assessment_indices`` from the caller. A bare integer index is
NOT proof of confirmation — a direct internal caller could have presented
an UNREVIEWED or REJECTED semantic-eligible assessment as source_type
``HUMAN_CONFIRMED``.

FU1 correction under test:

* BOTH replay entry points (``replay_compact_quote_projection`` and
  ``replay_public_compact_quote_projection``) no longer accept any
  caller-supplied index parameter. The effective human-confirmed
  selection is DERIVED from persisted state by
  ``derive_human_confirmed_assessment_indices``: CONFIRMED run-scoped
  candidate + in-range assessment index + full candidate-to-assessment
  binding (the single shared pure primitive) + human-review eligibility +
  persisted price/currency (enforced by the projection).
* The 8-step review-POST fail-closed validation is unchanged in strength
  (it applies the same shared primitive).
* Machine Price is untouched; historical replay remains zero-live-I/O
  (persisted-state reads only).

Required proofs:
  A. semantic-eligible assessment + candidate UNREVIEWED: attempted
     caller/index injection => NO HUMAN_CONFIRMED row / fail closed
  B. same candidate REJECTED: attempted injection => NO HUMAN_CONFIRMED
     row / fail closed
  C. candidate actually CONFIRMED + exact valid binding: row appears
  D. CONFIRMED candidate with tampered/stale binding: row absent /
     fail closed
  E. CONFIRMED candidate belonging to another run: cannot enter this run
  F. confirm then undo: replay no longer produces the row
  G. armed historical GET: still zero Search/Page/Vendor/ECB/Micron/
     Semantic/network I/O
"""

from __future__ import annotations

import inspect
from contextlib import contextmanager
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import (
    EvidenceDecision,
    IdentityMatchType,
    ResearchRunState,
)
from product_intelligence.execution import (
    replay_compact_quote_projection,
    replay_public_compact_quote_projection,
)
from product_intelligence.execution.compact_quote_replay import (
    derive_human_confirmed_assessment_indices,
)
from product_intelligence.execution import semantic_integration
from product_intelligence.providers.fx import EcbFxProvider
from product_intelligence.providers.http_page import HttpPageFetcher
from product_intelligence.providers.internal_vendor import InternalVendorAdapter
from product_intelligence.providers.serper import SerperSearchProvider
from product_intelligence.research import encode_price_aggregation_result
from product_intelligence.research.aggregation import aggregate_listing_prices
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
from product_intelligence.research.price_result_codec import (
    decode_price_aggregation_result,
)
from product_intelligence.runs import confirm_candidate, reject_candidate, undo_review
from product_intelligence.runs.models import (
    AiAssistedReviewCandidate,
    PriceIntelligenceSnapshot,
    ResearchRun,
)
from product_intelligence.semantic.runtime import SemanticRuntime

MPN = "HCRA-MPN-001"
DESCRIPTION = "Human confirmed replay authority test product"


# ---------------------------------------------------------------------------
# Settings / boundary helpers
# ---------------------------------------------------------------------------


@contextmanager
def _armed_live_boundaries():
    """Arm every live provider/network/semantic boundary (fail-fast).

    Any Search / Page / Vendor / ECB / Micron (page-fetcher driven) /
    Semantic / network touch during replay raises immediately.
    """
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
# Run / assessment / candidate builders (persisted-state fixtures)
# ---------------------------------------------------------------------------


def _semantic_observation(source_url: str) -> ListingObservation:
    return ListingObservation(
        source_url=source_url,
        extraction_method=ExtractionMethod.JSON_LD,
        product_title=f"Great deal {MPN} drive 1890",
        manufacturer_part_number_text="",  # no explicit MPN field
        sku_text=None,
        brand_text=None,
        price_text="1890.00",
        currency_text="USD",
        availability_text="In Stock",
        condition_text="unknown",
        seller_text="Semantic Seller",
        offer_url_text=None,
        raw_reference=None,
    )


def _semantic_assessment(obs: ListingObservation) -> ListingIdentityAssessment:
    norm = NormalizedListingObservation(
        observation=obs,
        price_amount=Decimal("1890.00"),
        currency_code="USD",
        availability=NormalizedAvailability.IN_STOCK,
        condition=NormalizedCondition.UNKNOWN,
        seller_name="Semantic Seller",
        normalization_issues=(),
    )
    return ListingIdentityAssessment(
        normalized_listing=norm,
        requested_part_number=MPN,
        candidate_part_number_raw=MPN,  # TITLE_TEXT: requested MPN in title
        candidate_part_number_compared=MPN,
        candidate_evidence_source=EvidenceSource.TITLE_TEXT,
        match_type=IdentityMatchType.UNKNOWN,
        decision=EvidenceDecision.REJECTED,
        rejection_reason=IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE,
    )


def _accepted_assessment(source_url: str) -> ListingIdentityAssessment:
    obs = ListingObservation(
        source_url=source_url,
        extraction_method=ExtractionMethod.JSON_LD,
        product_title=f"Deterministic listing for {MPN}",
        manufacturer_part_number_text=MPN,
        sku_text=None,
        brand_text=None,
        price_text="1500.00",
        currency_text="EUR",
        availability_text="In Stock",
        condition_text="New",
        seller_text="Det Seller",
        offer_url_text=None,
        raw_reference=None,
    )
    norm = NormalizedListingObservation(
        observation=obs,
        price_amount=Decimal("1500.00"),
        currency_code="EUR",
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


def _make_completed_run(
    *,
    semantic_url: str,
    accepted_url: str,
) -> tuple[ResearchRun, ListingObservation]:
    """A COMPLETED run with a persisted snapshot holding two assessments:

    * index 0: semantic-eligible REJECTED (1890 USD, UNKNOWN condition)
    * index 1: deterministic ACCEPTED (1500 EUR, NEW condition)
    """
    request = ResearchRequest(
        manufacturer_part_number=MPN, description=DESCRIPTION
    )
    run = ResearchRun.objects.create_from_request(request)
    run.transition_to(ResearchRunState.RUNNING)
    run.transition_to(ResearchRunState.COMPLETED)

    obs = _semantic_observation(semantic_url)
    sem = _semantic_assessment(obs)
    acc = _accepted_assessment(accepted_url)

    price_result = aggregate_listing_prices(request, (sem, acc))
    PriceIntelligenceSnapshot.objects.create(
        run=run,
        schema_version=1,
        payload=encode_price_aggregation_result(price_result),
    )
    return run, obs


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


def _decoded_price(run: ResearchRun):
    snapshot = PriceIntelligenceSnapshot.objects.get(run=run)
    return decode_price_aggregation_result(
        snapshot.payload, schema_version=snapshot.schema_version
    )


def _human_rows(run: ResearchRun):
    replay = replay_compact_quote_projection(str(run.id))
    return [r for r in replay.projection.rows if r.source_type == "HUMAN_CONFIRMED"]


# ---------------------------------------------------------------------------
# The injection surface is removed (mechanical proof)
# ---------------------------------------------------------------------------


class TestInjectionSurfaceRemoved(TestCase):
    def test_authorized_replay_accepts_no_caller_supplied_indices(self) -> None:
        params = inspect.signature(replay_compact_quote_projection).parameters
        self.assertNotIn("confirmed_assessment_indices", params)

    def test_public_replay_accepts_no_caller_supplied_indices(self) -> None:
        params = inspect.signature(
            replay_public_compact_quote_projection
        ).parameters
        self.assertNotIn("confirmed_assessment_indices", params)


# ---------------------------------------------------------------------------
# A. UNREVIEWED: attempted injection => NO HUMAN_CONFIRMED row
# ---------------------------------------------------------------------------


class TestUnreviewedInjectionFailsClosed(TestCase):
    def test_unreviewed_candidate_produces_no_row(self) -> None:
        run, obs = _make_completed_run(
            semantic_url="https://unr.example.com/u",
            accepted_url="https://unr.example.com/a",
        )
        cand = _make_candidate(run, obs, 0)
        self.assertEqual(cand.review_state, "UNREVIEWED")

        # Attempted caller/index injection: the replay boundary no longer
        # accepts any index at all; the persisted state (UNREVIEWED) wins.
        rows = _human_rows(run)
        self.assertEqual(rows, [])
        # The derived set is empty — no authority minted from bare indices.
        self.assertEqual(
            derive_human_confirmed_assessment_indices(
                run, _decoded_price(run).assessments
            ),
            frozenset(),
        )
        # The persisted price is NOT presented anywhere as human-confirmed.
        replay = replay_compact_quote_projection(str(run.id))
        for row in replay.projection.rows:
            self.assertNotEqual(row.source_type, "HUMAN_CONFIRMED")

    def test_unreviewed_candidate_public_replay_no_row(self) -> None:
        run, obs = _make_completed_run(
            semantic_url="https://unr-pub.example.com/u",
            accepted_url="https://unr-pub.example.com/a",
        )
        cand = _make_candidate(run, obs, 0)
        self.assertEqual(cand.review_state, "UNREVIEWED")

        replay = replay_public_compact_quote_projection(run=run)
        rows = [r for r in replay.projection.rows if r.source_type == "HUMAN_CONFIRMED"]
        self.assertEqual(rows, [])


# ---------------------------------------------------------------------------
# B. REJECTED: attempted injection => NO HUMAN_CONFIRMED row
# ---------------------------------------------------------------------------


class TestRejectedInjectionFailsClosed(TestCase):
    def test_rejected_candidate_produces_no_row(self) -> None:
        run, obs = _make_completed_run(
            semantic_url="https://rej.example.com/u",
            accepted_url="https://rej.example.com/a",
        )
        cand = _make_candidate(run, obs, 0)
        reject_candidate(cand.id, run_id=run.id)
        cand.refresh_from_db()
        self.assertEqual(cand.review_state, "REJECTED")

        rows = _human_rows(run)
        self.assertEqual(rows, [])
        replay = replay_compact_quote_projection(str(run.id))
        for row in replay.projection.rows:
            self.assertNotEqual(row.source_type, "HUMAN_CONFIRMED")


# ---------------------------------------------------------------------------
# C. CONFIRMED + exact valid binding: row appears
# ---------------------------------------------------------------------------


class TestConfirmedValidBindingProjects(TestCase):
    def test_confirmed_candidate_produces_row(self) -> None:
        run, obs = _make_completed_run(
            semantic_url="https://ok.example.com/u",
            accepted_url="https://ok.example.com/a",
        )
        cand = _make_candidate(run, obs, 0)
        confirm_candidate(cand.id, run_id=run.id)
        cand.refresh_from_db()
        self.assertEqual(cand.review_state, "CONFIRMED")

        rows = _human_rows(run)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        # Identity authority only: price/currency/condition are EXACTLY the
        # persisted normalized values (UNKNOWN condition stays Unknown).
        self.assertEqual(row.price_amount, Decimal("1890.00"))
        self.assertEqual(row.price_currency, "USD")
        self.assertEqual(row.price_original, "$1,890.00 USD")
        self.assertEqual(row.brand_new, "Unknown")
        self.assertIn("Human Confirmed", row.note or "")
        # USD pass-through equivalent (persisted-FX-only contract).
        self.assertEqual(row.usd_equivalent_amount, Decimal("1890.00"))

        # The public (denied-branch) replay derives the same authority
        # from THIS run's own persisted snapshot (FU2 authority
        # ownership: no caller-supplied price result).
        pub = replay_public_compact_quote_projection(run=run)
        pub_rows = [
            r for r in pub.projection.rows if r.source_type == "HUMAN_CONFIRMED"
        ]
        self.assertEqual(len(pub_rows), 1)
        self.assertEqual(pub_rows[0].price_amount, Decimal("1890.00"))
        # And still zero vendor rows on the public branch.
        self.assertNotIn("VENDOR_API", [r.source_type for r in pub.projection.rows])


# ---------------------------------------------------------------------------
# D. CONFIRMED with tampered/stale binding: row absent / fail closed
# ---------------------------------------------------------------------------


class TestConfirmedTamperedBindingFailsClosed(TestCase):
    def test_tampered_candidate_title_produces_no_row(self) -> None:
        run, obs = _make_completed_run(
            semantic_url="https://tamper.example.com/u",
            accepted_url="https://tamper.example.com/a",
        )
        cand = _make_candidate(run, obs, 0)
        confirm_candidate(cand.id, run_id=run.id)

        # Corrupt the persisted binding AFTER confirmation (tampered
        # candidate provenance). The replay boundary must fail closed:
        # the row does not enter the Compact Quote.
        AiAssistedReviewCandidate.objects.filter(id=cand.id).update(
            candidate_title="TAMPERED TITLE THAT MATCHES NOTHING"
        )

        rows = _human_rows(run)
        self.assertEqual(rows, [])
        self.assertEqual(
            derive_human_confirmed_assessment_indices(
                run, _decoded_price(run).assessments
            ),
            frozenset(),
        )

    def test_tampered_source_url_produces_no_row(self) -> None:
        run, obs = _make_completed_run(
            semantic_url="https://tamper2.example.com/u",
            accepted_url="https://tamper2.example.com/a",
        )
        cand = _make_candidate(run, obs, 0)
        confirm_candidate(cand.id, run_id=run.id)
        AiAssistedReviewCandidate.objects.filter(id=cand.id).update(
            source_url="https://attacker.example.com/injected"
        )
        rows = _human_rows(run)
        self.assertEqual(rows, [])

    def test_tampered_evidence_source_produces_no_row(self) -> None:
        run, obs = _make_completed_run(
            semantic_url="https://tamper3.example.com/u",
            accepted_url="https://tamper3.example.com/a",
        )
        cand = _make_candidate(run, obs, 0)
        confirm_candidate(cand.id, run_id=run.id)
        AiAssistedReviewCandidate.objects.filter(id=cand.id).update(
            evidence_source="SKU_FIELD"
        )
        rows = _human_rows(run)
        self.assertEqual(rows, [])

    def test_stale_out_of_range_index_produces_no_row(self) -> None:
        run, obs = _make_completed_run(
            semantic_url="https://stale.example.com/u",
            accepted_url="https://stale.example.com/a",
        )
        cand = _make_candidate(run, obs, 0)
        confirm_candidate(cand.id, run_id=run.id)
        # Forge an out-of-range index at persistence level (stale binding):
        # the service layer would refuse such a write, so this proves the
        # read-side boundary is independently fail-closed.
        AiAssistedReviewCandidate.objects.filter(id=cand.id).update(
            assessment_index=99
        )
        rows = _human_rows(run)
        self.assertEqual(rows, [])


# ---------------------------------------------------------------------------
# E. CONFIRMED candidate belonging to another run: cannot enter this run
# ---------------------------------------------------------------------------


class TestCrossRunCandidateCannotEnter(TestCase):
    def test_confirmed_candidate_of_run_a_cannot_enter_run_b(self) -> None:
        run_a, obs_a = _make_completed_run(
            semantic_url="https://cross-a.example.com/u",
            accepted_url="https://cross-a.example.com/a",
        )
        run_b, obs_b = _make_completed_run(
            semantic_url="https://cross-b.example.com/u",
            accepted_url="https://cross-b.example.com/a",
        )

        cand_a = _make_candidate(run_a, obs_a, 0)
        confirm_candidate(cand_a.id, run_id=run_a.id)
        cand_b = _make_candidate(run_b, obs_b, 0)
        self.assertEqual(cand_b.review_state, "UNREVIEWED")

        # Run A legitimately shows its confirmed row...
        rows_a = _human_rows(run_a)
        self.assertEqual(len(rows_a), 1)
        # ...but run B's replay derives authority ONLY from run B's
        # persisted candidates: A's CONFIRMED candidate cannot enter.
        rows_b = _human_rows(run_b)
        self.assertEqual(rows_b, [])
        # Neither can the derivation helper be pointed at B with A's row:
        # the query is run-scoped.
        derived_b = derive_human_confirmed_assessment_indices(
            run_b, _decoded_price(run_b).assessments
        )
        self.assertEqual(derived_b, frozenset())
        # A's confirmed URL must not leak into B's projection.
        replay_b = replay_compact_quote_projection(str(run_b.id))
        for row in replay_b.projection.rows:
            self.assertNotIn("cross-a.example.com", row.source)

    def test_review_service_refuses_cross_run_confirm(self) -> None:
        from product_intelligence.runs import CrossRunReviewError

        run_a, obs_a = _make_completed_run(
            semantic_url="https://cross-svc-a.example.com/u",
            accepted_url="https://cross-svc-a.example.com/a",
        )
        run_b, obs_b = _make_completed_run(
            semantic_url="https://cross-svc-b.example.com/u",
            accepted_url="https://cross-svc-b.example.com/a",
        )
        cand_a = _make_candidate(run_a, obs_a, 0)
        with self.assertRaises(CrossRunReviewError):
            confirm_candidate(cand_a.id, run_id=run_b.id)
        cand_a.refresh_from_db()
        self.assertEqual(cand_a.review_state, "UNREVIEWED")


# ---------------------------------------------------------------------------
# F. Confirm then undo: replay no longer produces the row
# ---------------------------------------------------------------------------


class TestConfirmThenUndoRemovesRow(TestCase):
    def test_undo_removes_the_row_on_replay(self) -> None:
        run, obs = _make_completed_run(
            semantic_url="https://undo.example.com/u",
            accepted_url="https://undo.example.com/a",
        )
        cand = _make_candidate(run, obs, 0)
        confirm_candidate(cand.id, run_id=run.id)
        self.assertEqual(len(_human_rows(run)), 1)

        undo_review(cand.id, run_id=run.id)
        cand.refresh_from_db()
        self.assertEqual(cand.review_state, "UNREVIEWED")
        self.assertEqual(_human_rows(run), [])


# ---------------------------------------------------------------------------
# G. Armed historical GET: still zero live I/O (with CONFIRMED present)
# ---------------------------------------------------------------------------


class TestArmedHistoricalReplayZeroLive(TestCase):
    def test_authorized_replay_zero_live_with_confirmation(self) -> None:
        run, obs = _make_completed_run(
            semantic_url="https://armed.example.com/u",
            accepted_url="https://armed.example.com/a",
        )
        cand = _make_candidate(run, obs, 0)
        confirm_candidate(cand.id, run_id=run.id)

        with _armed_live_boundaries():
            replay = replay_compact_quote_projection(str(run.id))

        rows = [
            r for r in replay.projection.rows if r.source_type == "HUMAN_CONFIRMED"
        ]
        # The confirmed row is present — recomputed purely from persisted
        # state, with every live boundary armed.
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].price_amount, Decimal("1890.00"))

    def test_public_replay_zero_live_with_confirmation(self) -> None:
        run, obs = _make_completed_run(
            semantic_url="https://armed-pub.example.com/u",
            accepted_url="https://armed-pub.example.com/a",
        )
        cand = _make_candidate(run, obs, 0)
        confirm_candidate(cand.id, run_id=run.id)

        with _armed_live_boundaries():
            replay = replay_public_compact_quote_projection(run=run)

        rows = [
            r for r in replay.projection.rows if r.source_type == "HUMAN_CONFIRMED"
        ]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].price_amount, Decimal("1890.00"))


# ---------------------------------------------------------------------------
# Machine Price stays untouched; derivation is deterministic
# ---------------------------------------------------------------------------


class TestMachinePriceAndDerivationContract(TestCase):
    def test_machine_price_snapshot_unchanged_by_confirmation_and_replay(self) -> None:
        run, obs = _make_completed_run(
            semantic_url="https://mp.example.com/u",
            accepted_url="https://mp.example.com/a",
        )
        snapshot = PriceIntelligenceSnapshot.objects.get(run=run)
        before = (snapshot.schema_version, snapshot.payload)

        cand = _make_candidate(run, obs, 0)
        confirm_candidate(cand.id, run_id=run.id)
        replay = replay_compact_quote_projection(str(run.id))
        self.assertEqual(
            len([r for r in replay.projection.rows if r.source_type == "HUMAN_CONFIRMED"]),
            1,
        )

        snapshot.refresh_from_db()
        self.assertEqual((snapshot.schema_version, snapshot.payload), before)
        # The deterministic bucket row is still the only PUBLIC_LISTING row.
        public_rows = [
            r for r in replay.projection.rows if r.source_type == "PUBLIC_LISTING"
        ]
        self.assertEqual(len(public_rows), 1)
        self.assertEqual(public_rows[0].price_amount, Decimal("1500.00"))

    def test_derivation_requires_persisted_price_currency(self) -> None:
        # A CONFIRMED candidate whose assessment lacks persisted price
        # evidence: the index derives (binding valid) but the projection
        # produces NO row — confirmation cannot create evidence.
        request = ResearchRequest(
            manufacturer_part_number=MPN, description=DESCRIPTION
        )
        run = ResearchRun.objects.create_from_request(request)
        run.transition_to(ResearchRunState.RUNNING)
        run.transition_to(ResearchRunState.COMPLETED)

        obs = _semantic_observation("https://noprice.example.com/u")
        sem = _semantic_assessment(obs)
        # No persisted price/currency on the normalized assessment.
        norm = sem.normalized_listing
        norm_noprice = NormalizedListingObservation(
            observation=obs,
            price_amount=None,
            currency_code=None,
            availability=norm.availability,
            condition=norm.condition,
            seller_name=norm.seller_name,
            normalization_issues=norm.normalization_issues,
        )
        sem_noprice = ListingIdentityAssessment(
            normalized_listing=norm_noprice,
            requested_part_number=MPN,
            candidate_part_number_raw=MPN,
            candidate_part_number_compared=MPN,
            candidate_evidence_source=EvidenceSource.TITLE_TEXT,
            match_type=IdentityMatchType.UNKNOWN,
            decision=EvidenceDecision.REJECTED,
            rejection_reason=IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE,
        )
        price_result = aggregate_listing_prices(request, (sem_noprice,))
        PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=1,
            payload=encode_price_aggregation_result(price_result),
        )
        cand = _make_candidate(run, obs, 0)
        confirm_candidate(cand.id, run_id=run.id)

        # The derivation proves the binding; the index is present...
        derived = derive_human_confirmed_assessment_indices(
            run, _decoded_price(run).assessments
        )
        self.assertEqual(derived, frozenset({0}))
        # ...but the projection produces NO row (no persisted price).
        rows = _human_rows(run)
        self.assertEqual(rows, [])
