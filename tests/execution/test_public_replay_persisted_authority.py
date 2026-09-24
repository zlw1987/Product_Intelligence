"""FU2 final-review blocker regression: the public (denied) compact quote
replay must own its persisted PriceIntelligenceSnapshot authority.

BLOCKER under test (PROD-FIX1 final independent review):

``replay_public_compact_quote_projection(run=..., price_result=...)``
accepted a CALLER-SUPPLIED PriceAggregationResult and verified only
``price_result.request == run.to_research_request()``. A SAME-REQUEST
cross-run result — identical source URL / product title / MPN field /
SKU / evidence source, different persisted price — could therefore be
passed in for another run: the shared binding primitive
(``is_review_candidate_binding_valid``) legitimately matches Run A's
CONFIRMED candidate against Run B's assessment (the identity/provenance
fields are equal), so Run B's 999 USD could be presented as a
HUMAN_CONFIRMED row for Run A. That violates historical report
immutability, run-scoped evidence authority, and the rule that
confirmation establishes identity authority only over the persisted
evidence belonging to that same run.

FU2 correction under test:

* the public replay's only parameter is ``run``; it loads
  ``PriceIntelligenceSnapshot.objects.get(run=run)``, decodes it through
  the canonical price-result codec, verifies
  ``decoded.request == run.to_research_request()``, and uses THAT
  decoded persisted result for the frozen public bucket projection, the
  human-confirmed binding derivation, and the human-confirmed
  price/currency/condition evidence;
* no API surface exists through which supplying another run's
  PriceAggregationResult can change what this run's public replay shows;
* missing / malformed / request-provenance-corrupt persisted snapshots
  fail closed (existing persisted-artifact behavior);
* the denied branch still NEVER reads ResearchSupplementSnapshot and the
  historical public replay remains zero-live-I/O;
* the authorized replay and Machine Price are unchanged.

Required proofs:
  1. Run A: valid CONFIRMED candidate, persisted human-review-eligible
     assessment at 1890 USD.
  2. Run B: SAME ResearchRequest, SAME source URL, SAME product title,
     SAME MPN field, SAME SKU, SAME evidence source, DIFFERENT persisted
     normalized price (999 USD).
  3. Public replay for Run A shows Run A's persisted 1890 USD.
  4. No API surface accepts Run B's PriceAggregationResult for Run A.
  5. Run B's public replay independently shows its own 999 USD.
  6. Request-provenance-corrupt snapshot on Run A fails closed.
  7. Missing snapshot fails closed (existing persisted-artifact
     behavior).
  8. Public replay never reads ResearchSupplementSnapshot.
  9. Public replay remains zero-live-I/O.
  10. Authorized replay behavior unchanged (shows 1890 for Run A).
  11. Machine Price snapshot byte-identical.
"""

from __future__ import annotations

import inspect
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import (
    EvidenceDecision,
    IdentityMatchType,
    VerificationStatus,
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
from product_intelligence.research.aggregation import (
    PriceAggregationResult,
    aggregate_listing_prices,
)
from product_intelligence.research.compact_quote import (
    CompactQuoteProjectionError,
)
from product_intelligence.research.listings import ExtractionMethod, ListingObservation
from product_intelligence.research.matching import (
    EvidenceSource,
    IdentityRejectionReason,
    ListingIdentityAssessment,
    is_review_candidate_binding_valid,
)
from product_intelligence.research.normalization import (
    NormalizedAvailability,
    NormalizedCondition,
    NormalizedListingObservation,
)
from product_intelligence.research.price_result_codec import (
    PriceResultCodecError,
    decode_price_aggregation_result,
)
from product_intelligence.runs import confirm_candidate
from product_intelligence.runs.models import (
    AiAssistedReviewCandidate,
    PriceIntelligenceSnapshot,
    ResearchRun,
    ResearchSupplementSnapshot,
)
from product_intelligence.research.commercial_supplement_codec import (
    ResearchSupplementResult,
    SupplementAvailability,
    SupplementLookupStatus,
    SupplementPriceBasis,
    SupplementSourceObservation,
    VendorCommercialResult,
    encode_research_supplement_result,
)
from product_intelligence.semantic.runtime import SemanticRuntime

MPN = "FU2-PUB-AUTH-MPN"
DESCRIPTION = "FU2 public replay persisted authority test product"
# SAME across both runs: the listing identity/provenance binding is
# identical; only the run FK and the persisted price differ.
SHARED_SOURCE_URL = "https://listing.example.com/fu2-shared-listing"
SHARED_TITLE = f"Great deal {MPN} enterprise SSD"
SHARED_SKU = "ENT-SSD-480-FU2-SKU"
SENTINEL_VENDOR_PRICE = "91827.43"


# ---------------------------------------------------------------------------
# Armed boundaries (fail-fast sentinels)
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


@contextmanager
def _armed_supplement_boundaries():
    """Arm the exact supplemental artifact access path used by the
    authorized replay. If the public (denied) replay reads
    ResearchSupplementSnapshot, calls decode_research_supplement_result,
    or falls back to the authorized replay, this raises RuntimeError."""

    def _boom(*args, **kwargs):
        raise RuntimeError(
            "public replay touched vendor supplemental artifact access"
        )

    with (
        patch.object(ResearchSupplementSnapshot.objects, "get", side_effect=_boom),
        patch.object(
            ResearchSupplementSnapshot.objects, "filter", side_effect=_boom
        ),
        patch(
            "product_intelligence.research.commercial_supplement_codec"
            ".decode_research_supplement_result",
            side_effect=_boom,
        ),
        patch(
            "product_intelligence.web.views.replay_compact_quote_projection",
            side_effect=_boom,
        ),
        patch(
            "product_intelligence.execution.compact_quote_replay"
            ".replay_compact_quote_projection",
            side_effect=_boom,
        ),
    ):
        yield


# ---------------------------------------------------------------------------
# Same-request cross-run fixtures
# ---------------------------------------------------------------------------


def _shared_observation(price: Decimal) -> ListingObservation:
    """One listing observation with the SHARED identity/provenance fields.

    Same source URL, same product title, same (absent) MPN field, same
    SKU, same evidence source across both runs — only the persisted
    price differs. The assessment is semantic-eligible: REJECTED with
    NO_EXPLICIT_MPN_EVIDENCE + SKU_FIELD (the page published a SKU but no
    explicit MPN field; SKU evidence outranks title evidence).
    """
    return ListingObservation(
        source_url=SHARED_SOURCE_URL,
        extraction_method=ExtractionMethod.JSON_LD,
        product_title=SHARED_TITLE,
        manufacturer_part_number_text="",  # no explicit MPN field (both runs)
        sku_text=SHARED_SKU,  # SAME SKU (both runs)
        brand_text=None,
        price_text=str(price),
        currency_text="USD",
        availability_text="In Stock",
        condition_text="unknown",
        seller_text="Semantic Seller",
        offer_url_text=None,
        raw_reference=None,
    )


def _shared_assessment(obs: ListingObservation) -> ListingIdentityAssessment:
    price = Decimal(obs.price_text)
    norm = NormalizedListingObservation(
        observation=obs,
        price_amount=price,
        currency_code="USD",
        availability=NormalizedAvailability.IN_STOCK,
        condition=NormalizedCondition.UNKNOWN,
        seller_name="Semantic Seller",
        normalization_issues=(),
    )
    return ListingIdentityAssessment(
        normalized_listing=norm,
        requested_part_number=MPN,
        candidate_part_number_raw=SHARED_SKU,  # SKU_FIELD: raw = published SKU
        candidate_part_number_compared=SHARED_SKU,  # compared == raw (non-MPN source)
        candidate_evidence_source=EvidenceSource.SKU_FIELD,
        match_type=IdentityMatchType.UNKNOWN,
        decision=EvidenceDecision.REJECTED,
        rejection_reason=IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE,
    )


def _make_same_request_run(price: Decimal) -> tuple[ResearchRun, ListingObservation]:
    """A COMPLETED run for the SAME request with the SHARED listing
    identity, one persisted human-review-eligible assessment at
    ``price`` USD, and a CONFIRMED candidate bound to it."""
    request = ResearchRequest(
        manufacturer_part_number=MPN, description=DESCRIPTION
    )
    run = ResearchRun.objects.create_from_request(request)
    from product_intelligence.domain.enums import ResearchRunState

    run.transition_to(ResearchRunState.RUNNING)
    run.transition_to(ResearchRunState.COMPLETED)

    obs = _shared_observation(price)
    assess = _shared_assessment(obs)

    price_result = aggregate_listing_prices(request, (assess,))
    PriceIntelligenceSnapshot.objects.create(
        run=run,
        schema_version=1,
        payload=encode_price_aggregation_result(price_result),
    )

    # The persisted human-review-eligible assessment + CONFIRMED binding.
    candidate = AiAssistedReviewCandidate.objects.create(
        run=run,
        assessment_index=0,
        source_url=obs.source_url,
        target_mpn=MPN,
        target_description=DESCRIPTION,
        candidate_title=obs.product_title or "",
        candidate_mpn_field=obs.manufacturer_part_number_text or "",
        candidate_sku=obs.sku_text or "",
        evidence_source="SKU_FIELD",
        actual_provider="amax",
        actual_model="nemotron-3-super",
        prompt_version="v1.1",
    )
    confirm_candidate(candidate.id, run_id=run.id)
    candidate.refresh_from_db()
    assert candidate.review_state == "CONFIRMED"
    return run, obs


def _decoded_price(run: ResearchRun) -> PriceAggregationResult:
    snapshot = PriceIntelligenceSnapshot.objects.get(run=run)
    return decode_price_aggregation_result(
        snapshot.payload, schema_version=snapshot.schema_version
    )


def _public_human_rows(run: ResearchRun) -> list:
    replay = replay_public_compact_quote_projection(run=run)
    return [r for r in replay.projection.rows if r.source_type == "HUMAN_CONFIRMED"]


# ---------------------------------------------------------------------------
# The exploit premise is real: the shared binding primitive matches
# cross-run when the identity fields are identical (which is why the
# replay must own the snapshot, not the caller).
# ---------------------------------------------------------------------------


class TestCrossRunBorrowPremise(TestCase):
    def test_fixture_has_same_request_same_binding_different_price(self) -> None:
        run_a, obs_a = _make_same_request_run(Decimal("1890.00"))
        run_b, obs_b = _make_same_request_run(Decimal("999.00"))

        # SAME ResearchRequest
        self.assertEqual(
            run_a.to_research_request(), run_b.to_research_request()
        )
        # SAME source URL / title / MPN field / SKU / evidence source
        self.assertEqual(obs_a.source_url, obs_b.source_url)
        self.assertEqual(obs_a.product_title, obs_b.product_title)
        self.assertEqual(obs_a.manufacturer_part_number_text,
                         obs_b.manufacturer_part_number_text)
        self.assertEqual(obs_a.sku_text, obs_b.sku_text)
        self.assertEqual(
            _decoded_price(run_a).assessments[0].candidate_evidence_source,
            _decoded_price(run_b).assessments[0].candidate_evidence_source,
        )
        # DIFFERENT persisted normalized price
        self.assertEqual(
            _decoded_price(run_a).assessments[0].normalized_listing.price_amount,
            Decimal("1890.00"),
        )
        self.assertEqual(
            _decoded_price(run_b).assessments[0].normalized_listing.price_amount,
            Decimal("999.00"),
        )

    def test_binding_primitive_legitimately_matches_across_same_request_runs(
        self,
    ) -> None:
        """Non-vacuity proof of the blocker premise: with identical
        identity/provenance fields, Run A's CONFIRMED candidate binds
        against Run B's assessment, and the shared derivation would mint
        index 0 for Run A over Run B's evidence. The ONLY thing that
        prevents the borrow is the replay owning the persisted snapshot
        (proven in the tests below)."""
        run_a, _ = _make_same_request_run(Decimal("1890.00"))
        run_b, _ = _make_same_request_run(Decimal("999.00"))

        cand_a = AiAssistedReviewCandidate.objects.get(run=run_a)
        run_b_assessments = _decoded_price(run_b).assessments

        self.assertTrue(
            is_review_candidate_binding_valid(cand_a, run_b_assessments[0])
        )
        self.assertEqual(
            derive_human_confirmed_assessment_indices(
                run_a, run_b_assessments
            ),
            frozenset({0}),
        )


# ---------------------------------------------------------------------------
# 3. + 5. Each run's public replay shows its OWN persisted price
# ---------------------------------------------------------------------------


class TestEachRunShowsOwnPersistedEvidence(TestCase):
    def test_run_a_public_replay_shows_run_a_persisted_1890(self) -> None:
        run_a, _ = _make_same_request_run(Decimal("1890.00"))
        _make_same_request_run(Decimal("999.00"))  # Run B exists in the DB

        rows = _public_human_rows(run_a)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.price_amount, Decimal("1890.00"))
        self.assertEqual(row.price_currency, "USD")
        self.assertEqual(row.price_original, "$1,890.00 USD")
        self.assertIn("Human Confirmed", row.note or "")
        # Run B's price can appear nowhere in Run A's projection.
        for r in replay_public_compact_quote_projection(run=run_a).projection.rows:
            self.assertNotEqual(r.price_amount, Decimal("999.00"))
            self.assertNotIn("999", r.price_original)

    def test_run_b_public_replay_shows_run_b_own_999(self) -> None:
        _make_same_request_run(Decimal("1890.00"))  # Run A exists in the DB
        run_b, _ = _make_same_request_run(Decimal("999.00"))

        rows = _public_human_rows(run_b)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.price_amount, Decimal("999.00"))
        self.assertEqual(row.price_currency, "USD")
        self.assertEqual(row.price_original, "$999.00 USD")
        # Run A's price can appear nowhere in Run B's projection.
        for r in replay_public_compact_quote_projection(run=run_b).projection.rows:
            self.assertNotEqual(r.price_amount, Decimal("1890.00"))
            self.assertNotIn("1,890", r.price_original)


# ---------------------------------------------------------------------------
# 4. No API surface accepts a caller-supplied PriceAggregationResult
# ---------------------------------------------------------------------------


class TestNoCallerPriceResultSurface(TestCase):
    def test_public_replay_signature_accepts_only_run(self) -> None:
        params = inspect.signature(
            replay_public_compact_quote_projection
        ).parameters
        self.assertEqual(set(params), {"run"})
        self.assertEqual(params["run"].kind, inspect.Parameter.KEYWORD_ONLY)

    def test_supplying_run_b_decoded_result_is_rejected_type_error(self) -> None:
        """There is no way to pass Run B's decoded PriceAggregationResult
        to Run A's public replay: the parameter does not exist."""
        run_a, _ = _make_same_request_run(Decimal("1890.00"))
        run_b, _ = _make_same_request_run(Decimal("999.00"))
        run_b_decoded = _decoded_price(run_b)

        with self.assertRaises(TypeError):
            replay_public_compact_quote_projection(
                run=run_a, price_result=run_b_decoded  # type: ignore[call-arg]
            )

    def test_run_a_replay_invariant_under_run_b_result_existence(self) -> None:
        """Behavioral proof: even with Run B's decoded result constructed
        and available in-process, Run A's public replay presents exactly
        Run A's persisted 1890 USD HUMAN_CONFIRMED row — the borrowed
        999 USD scenario is impossible at this boundary."""
        run_a, _ = _make_same_request_run(Decimal("1890.00"))
        run_b, _ = _make_same_request_run(Decimal("999.00"))
        run_b_decoded = _decoded_price(run_b)  # exists in-process
        self.assertEqual(
            run_b_decoded.assessments[0].normalized_listing.price_amount,
            Decimal("999.00"),
        )

        replay_a = replay_public_compact_quote_projection(run=run_a)
        human_rows = [
            r for r in replay_a.projection.rows if r.source_type == "HUMAN_CONFIRMED"
        ]
        self.assertEqual(len(human_rows), 1)
        self.assertEqual(human_rows[0].price_amount, Decimal("1890.00"))
        self.assertNotIn(
            Decimal("999.00"),
            [r.price_amount for r in replay_a.projection.rows],
        )


# ---------------------------------------------------------------------------
# 6. + 7. Corrupt / missing persisted price artifact fails closed
# ---------------------------------------------------------------------------


class TestPersistedArtifactFailClosed(TestCase):
    def test_request_provenance_corrupt_snapshot_fails_closed(self) -> None:
        """A persisted snapshot whose decoded request does not match the
        run's request fails closed (no partial or borrowed summary)."""
        run = ResearchRun.objects.create_from_request(
            ResearchRequest(manufacturer_part_number=MPN, description=DESCRIPTION)
        )
        from product_intelligence.domain.enums import ResearchRunState

        run.transition_to(ResearchRunState.RUNNING)
        run.transition_to(ResearchRunState.COMPLETED)

        foreign_request = ResearchRequest(
            manufacturer_part_number="FU2-PROV-FORIGN-MPN", description="other"
        )
        foreign_result = PriceAggregationResult(
            request=foreign_request,
            assessments=(),
            buckets=(),
            exclusions=(),
            verification_status=VerificationStatus.UNKNOWN,
        )
        PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=1,
            payload=encode_price_aggregation_result(foreign_result),
        )

        with self.assertRaises(CompactQuoteProjectionError) as ctx:
            replay_public_compact_quote_projection(run=run)
        self.assertIn("provenance", str(ctx.exception))

    def test_missing_snapshot_fails_closed_existing_artifact_behavior(self) -> None:
        """No persisted price artifact => DoesNotExist propagates (the
        existing persisted-artifact behavior shared with the authorized
        replay; the web view maps it to 'summary unavailable')."""
        run = ResearchRun.objects.create_from_request(
            ResearchRequest(manufacturer_part_number=MPN, description=DESCRIPTION)
        )
        from product_intelligence.domain.enums import ResearchRunState

        run.transition_to(ResearchRunState.RUNNING)
        run.transition_to(ResearchRunState.COMPLETED)
        self.assertFalse(
            PriceIntelligenceSnapshot.objects.filter(run=run).exists()
        )

        with self.assertRaises(PriceIntelligenceSnapshot.DoesNotExist):
            replay_public_compact_quote_projection(run=run)

    def test_malformed_snapshot_payload_fails_closed(self) -> None:
        run = ResearchRun.objects.create_from_request(
            ResearchRequest(manufacturer_part_number=MPN, description=DESCRIPTION)
        )
        from product_intelligence.domain.enums import ResearchRunState

        run.transition_to(ResearchRunState.RUNNING)
        run.transition_to(ResearchRunState.COMPLETED)
        PriceIntelligenceSnapshot.objects.create(
            run=run, schema_version=1, payload={"garbage": True}
        )

        with self.assertRaises(PriceResultCodecError):
            replay_public_compact_quote_projection(run=run)

    def test_unsupported_schema_version_fails_closed(self) -> None:
        run, _ = _make_same_request_run(Decimal("1890.00"))
        snapshot = PriceIntelligenceSnapshot.objects.get(run=run)
        payload = snapshot.payload
        PriceIntelligenceSnapshot.objects.filter(run=run).update(
            schema_version=99
        )

        with self.assertRaises(PriceResultCodecError):
            replay_public_compact_quote_projection(run=run)
        # Restore (test hygiene only — no production state escapes a
        # Django TestCase rollback).
        PriceIntelligenceSnapshot.objects.filter(run=run).update(
            schema_version=1, payload=payload
        )


# ---------------------------------------------------------------------------
# 8. + 9. Denied boundary preserved: no supplement read, zero live I/O
# ---------------------------------------------------------------------------


class TestDeniedBoundaryPreserved(TestCase):
    def test_public_replay_never_reads_supplement(self) -> None:
        """A real ResearchSupplementSnapshot exists for Run A with the
        sentinel vendor price; the exact supplemental access paths used
        by the authorized replay are armed. The public replay still
        succeeds with Run A's own 1890 USD and no vendor data."""
        run_a, _ = _make_same_request_run(Decimal("1890.00"))
        result = ResearchSupplementResult(
            vendor_commercial_result=VendorCommercialResult(
                lookup_status=SupplementLookupStatus.SUCCESS,
                retrieved_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
                observations=(
                    SupplementSourceObservation(
                        source_name="Ingram",
                        explicit_candidate_mpn=MPN,
                        vendor_mpn_match_type="EXACT",
                        price_amount=Decimal(SENTINEL_VENDOR_PRICE),
                        currency_code="USD",
                        availability=SupplementAvailability.IN_STOCK,
                        price_basis=SupplementPriceBasis.CUSTOMER_PRICE,
                        quantity=1,
                        note_kind=None,
                        brand_new=True,
                        brand_new_basis="VENDOR_API_POLICY",
                    ),
                ),
                source_issues=(),
            ),
        )
        ResearchSupplementSnapshot.objects.create(
            run=run_a,
            schema_version=1,
            payload=encode_research_supplement_result(result),
        )

        with _armed_supplement_boundaries():
            replay = replay_public_compact_quote_projection(run=run_a)

        self.assertNotIn(
            "VENDOR_API", [r.source_type for r in replay.projection.rows]
        )
        for row in replay.projection.rows:
            self.assertNotEqual(row.price_amount, Decimal(SENTINEL_VENDOR_PRICE))
        human_rows = [
            r for r in replay.projection.rows if r.source_type == "HUMAN_CONFIRMED"
        ]
        self.assertEqual(len(human_rows), 1)
        self.assertEqual(human_rows[0].price_amount, Decimal("1890.00"))

    def test_public_replay_zero_live_io_with_confirmed(self) -> None:
        """Every live boundary armed; the historical public replay with a
        CONFIRMED candidate performs zero Search/Page/Vendor/ECB/Micron/
        Semantic/network work and still presents Run A's 1890 USD."""
        run_a, _ = _make_same_request_run(Decimal("1890.00"))

        with _armed_live_boundaries():
            replay = replay_public_compact_quote_projection(run=run_a)

        human_rows = [
            r for r in replay.projection.rows if r.source_type == "HUMAN_CONFIRMED"
        ]
        self.assertEqual(len(human_rows), 1)
        self.assertEqual(human_rows[0].price_amount, Decimal("1890.00"))


# ---------------------------------------------------------------------------
# 10. + 11. Authorized replay unchanged; Machine Price byte-identical
# ---------------------------------------------------------------------------


class TestAuthorizedReplayAndMachinePriceUnchanged(TestCase):
    def test_authorized_replay_run_a_still_shows_1890(self) -> None:
        """The authorized replay is unchanged by FU2: it loads the same
        persisted snapshot and presents Run A's 1890 USD
        HUMAN_CONFIRMED row."""
        run_a, _ = _make_same_request_run(Decimal("1890.00"))
        _make_same_request_run(Decimal("999.00"))

        replay = replay_compact_quote_projection(str(run_a.id))
        human_rows = [
            r for r in replay.projection.rows if r.source_type == "HUMAN_CONFIRMED"
        ]
        self.assertEqual(len(human_rows), 1)
        self.assertEqual(human_rows[0].price_amount, Decimal("1890.00"))
        self.assertNotIn(
            Decimal("999.00"),
            [r.price_amount for r in replay.projection.rows],
        )

    def test_machine_price_snapshot_byte_identical(self) -> None:
        """Both historical replays (public + authorized) for both runs
        leave every PriceIntelligenceSnapshot byte-identical."""
        run_a, _ = _make_same_request_run(Decimal("1890.00"))
        run_b, _ = _make_same_request_run(Decimal("999.00"))

        snap_a = PriceIntelligenceSnapshot.objects.get(run=run_a)
        snap_b = PriceIntelligenceSnapshot.objects.get(run=run_b)
        before_a = (snap_a.schema_version, snap_a.payload)
        before_b = (snap_b.schema_version, snap_b.payload)

        replay_public_compact_quote_projection(run=run_a)
        replay_public_compact_quote_projection(run=run_b)
        replay_compact_quote_projection(str(run_a.id))
        replay_compact_quote_projection(str(run_b.id))

        snap_a.refresh_from_db()
        snap_b.refresh_from_db()
        self.assertEqual((snap_a.schema_version, snap_a.payload), before_a)
        self.assertEqual((snap_b.schema_version, snap_b.payload), before_b)
