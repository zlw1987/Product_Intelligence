"""PRODUCT-INTEL.PILOT-VENDOR-STATUS-UX-A — Vendor API status notice.

Regressions for the bounded "Vendor API status" notice rendered inside the
Quote & Market Summary section (research report).

The notice is display-only and ALLOWED-connection-only:

* Every displayed fact is carried by the run's OWN persisted,
  codec-validated vendor supplement snapshot (the historical replay is the
  sole reader/decoder). Zero vendor/search/LLM/FX live work on GET.
* An unauthorized (DENIED) connection learns NOTHING about the vendor
  snapshot: not its existence, status, sources, prices, or counts. The
  DENIED template context carries no vendor status fact at all, and the
  DENIED route never touches the supplemental artifact access path
  (armed RuntimeError fail-fast, mirroring the frozen 4D-C contract).
* A malformed supplement payload keeps the EXISTING fail-closed behavior:
  "Quote & Market Summary unavailable." — no misleading success, no
  partial-public fallback, no status notice.
* A FAILED lookup displays the accurate bounded message; a specific
  failure cause is shown only when the persisted evidence records a
  bounded per-source result, and is otherwise explicitly stated as not
  recorded (the frozen codec persists no free-text failure cause).

Isolation: every DB-touching case is a ``django.test.TestCase`` (per-test
transaction rollback), so this file introduces no persistent
``ResearchRun`` leakage into the session-scoped test database.
"""

from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import (
    ConfidenceLevel,
    EvidenceDecision,
    IdentityMatchType,
    ResearchRunState,
    VerificationStatus,
)
from product_intelligence.providers.fx import EcbFxProvider, FxRateObservation
from product_intelligence.providers.http_page import HttpPageFetcher
from product_intelligence.providers.internal_vendor import InternalVendorAdapter
from product_intelligence.providers.serper import SerperSearchProvider
from product_intelligence.research import (
    ListingIdentityAssessment,
    ListingObservation,
    PriceAggregateBucket,
    PriceAggregationResult,
    encode_price_aggregation_result,
)
from product_intelligence.research.aggregation import aggregate_listing_prices
from product_intelligence.research.commercial_supplement_codec import (
    ResearchSupplementResult,
    SupplementLookupStatus,
    SupplementPriceBasis,
    SupplementSourceIssue,
    SupplementSourceObservation,
    VendorCommercialResult,
    encode_research_supplement_result,
)
from product_intelligence.research.fx_codec import encode_fx_observation
from product_intelligence.research.listings import ExtractionMethod
from product_intelligence.research.matching import (
    EvidenceSource,
    IdentityRejectionReason,
)
from product_intelligence.research.normalization import (
    NormalizedAvailability,
    NormalizedCondition,
    NormalizedListingObservation,
)
from product_intelligence.runs.models import (
    AiAssistedReviewCandidate,
    ComparableResearchExecution,
    PriceIntelligenceSnapshot,
    ResearchFxSnapshot,
    ResearchRun,
    ResearchSupplementSnapshot,
)
from product_intelligence.semantic.runtime import SemanticRuntime
from product_intelligence.execution import semantic_integration
from product_intelligence.web.vendor_status_presentation import (
    VendorApiStatusPresentation,
    build_vendor_api_status_presentation,
)

ALLOWED_CIDRS = "10.0.0.0/8"
ALLOWED_ADDR = "10.0.0.1"
DENIED_ADDR = "192.0.2.1"  # TEST-NET-1 (RFC 5737) — never assigned

# Recognizable sentinel values (never a real price/source), so a leak is
# detectable in the raw and formatted forms.
SENTINEL_VENDOR_PRICE = "777000.13"
SENTINEL_SOURCE = "VendorStatusProbeSource"

PUBLIC_SOURCE_URL = "https://www.example.com/product/vsux"
PUBLIC_PRICE = Decimal("1500.00")
USD_RATE = Decimal("1.0934")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_settings(cidrs: "str | None" = ALLOWED_CIDRS):
    return type("Settings", (), {"PI_VENDOR_PRICE_ALLOWED_CIDRS": cidrs})()


def _detail_url(run: ResearchRun) -> str:
    return reverse("research-detail", kwargs={"run_id": run.id})


def _get(client: Client, url: str, remote_addr: str) -> "object":
    return client.get(url, REMOTE_ADDR=remote_addr)


def _public_result(run: ResearchRun) -> PriceAggregationResult:
    mpn = run.manufacturer_part_number or "VSUX-MPN"
    obs = ListingObservation(
        source_url=PUBLIC_SOURCE_URL,
        extraction_method=ExtractionMethod.JSON_LD,
        product_title="Vendor Status Product",
        manufacturer_part_number_text=mpn,
        sku_text=None,
        brand_text=None,
        price_text=str(PUBLIC_PRICE),
        currency_text="EUR",
        availability_text="In Stock",
        condition_text="New",
        seller_text="Example Store",
        offer_url_text=None,
        raw_reference=None,
    )
    norm = NormalizedListingObservation(
        observation=obs,
        price_amount=PUBLIC_PRICE,
        currency_code="EUR",
        availability=NormalizedAvailability.IN_STOCK,
        condition=NormalizedCondition.NEW,
        seller_name="Example Store",
        normalization_issues=(),
    )
    assess = ListingIdentityAssessment(
        normalized_listing=norm,
        requested_part_number=mpn,
        candidate_part_number_raw=mpn,
        candidate_part_number_compared=mpn,
        candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
        match_type=IdentityMatchType.EXACT,
        decision=EvidenceDecision.ACCEPTED,
        rejection_reason=None,
    )
    return PriceAggregationResult(
        request=run.to_research_request(),
        assessments=(assess,),
        exclusions=(),
        buckets=(
            PriceAggregateBucket(
                currency_code="EUR",
                condition=NormalizedCondition.NEW,
                assessments=(assess,),
                count=1,
                low=PUBLIC_PRICE,
                median=PUBLIC_PRICE,
                high=PUBLIC_PRICE,
                market_range_low=None,
                market_range_high=None,
                confidence=ConfidenceLevel.LOW,
            ),
        ),
        verification_status=VerificationStatus.VERIFIED,
    )


def _persist_price_snapshot(run: ResearchRun, result: PriceAggregationResult) -> None:
    PriceIntelligenceSnapshot.objects.create(
        run=run,
        schema_version=1,
        payload=encode_price_aggregation_result(result),
    )


def _persist_fx(run: ResearchRun) -> None:
    payload = encode_fx_observation(
        provider_id="ECB",
        observation_date=date(2024, 3, 1),
        base_currency="EUR",
        rates=(
            FxRateObservation(currency_code="USD", rate=USD_RATE),
            FxRateObservation(currency_code="EUR", rate=Decimal("1")),
        ),
        retrieved_at=datetime(2024, 3, 1, 12, 0, 0, tzinfo=timezone.utc),
    )
    ResearchFxSnapshot.objects.create(run=run, schema_version=1, payload=payload)


def _vendor_observation(
    run: ResearchRun,
    *,
    source_name: str = SENTINEL_SOURCE,
    price: Decimal = Decimal(SENTINEL_VENDOR_PRICE),
    currency: str = "USD",
    availability: str = "IN_STOCK",
) -> SupplementSourceObservation:
    return SupplementSourceObservation(
        source_name=source_name,
        explicit_candidate_mpn=run.manufacturer_part_number or "VSUX-MPN",
        vendor_mpn_match_type="EXACT",
        price_amount=price,
        currency_code=currency,
        availability=availability,
        price_basis=SupplementPriceBasis.CUSTOMER_PRICE,
        quantity=1,
        note_kind=None,
        brand_new=True,
        brand_new_basis="VENDOR_API_POLICY",
    )


def _persist_supplement(
    run: ResearchRun,
    *,
    lookup_status: str,
    observations: "tuple | None" = None,
    source_issues: "tuple | None" = None,
    retrieved_at: "datetime | None" = None,
) -> None:
    result = ResearchSupplementResult(
        vendor_commercial_result=VendorCommercialResult(
            lookup_status=lookup_status,
            retrieved_at=retrieved_at,
            observations=tuple(observations or ()),
            source_issues=tuple(source_issues or ()),
        ),
    )
    ResearchSupplementSnapshot.objects.create(
        run=run,
        schema_version=1,
        payload=encode_research_supplement_result(result),
    )


def _make_completed_run(
    mpn: str = "VSUX-MPN",
    *,
    with_supplement: bool = True,
    lookup_status: str = SupplementLookupStatus.SUCCESS,
    observations: "tuple | None" = None,
    source_issues: "tuple | None" = None,
    malformed_supplement: bool = False,
    no_price_snapshot: bool = False,
) -> ResearchRun:
    run = ResearchRun.objects.create_from_request(
        ResearchRequest(manufacturer_part_number=mpn, description="Vendor status product")
    )
    run.transition_to(ResearchRunState.RUNNING)
    run.transition_to(ResearchRunState.COMPLETED)
    if not no_price_snapshot:
        _persist_price_snapshot(run, _public_result(run))
        _persist_fx(run)
    if with_supplement:
        if malformed_supplement:
            ResearchSupplementSnapshot.objects.create(
                run=run, schema_version=1, payload={"garbage": True}
            )
        else:
            _persist_supplement(
                run,
                lookup_status=lookup_status,
                observations=observations,
                source_issues=source_issues,
            )
    return run


@contextmanager
def _armed_live_boundaries():
    """Arm every live provider/network/semantic boundary (fail-fast)."""
    import urllib.request

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
    """Arm the exact vendor supplemental artifact access path (fail-fast).

    If the denied route reads ResearchSupplementSnapshot, calls
    decode_research_supplement_result, or calls the authorized replay,
    this raises RuntimeError.
    """

    def _boom(*args, **kwargs):
        raise RuntimeError(
            "denied path touched vendor supplemental artifact access"
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
    ):
        yield


def _db_fingerprint() -> str:
    """A digest of every research table's rows (state of record for the
    zero-DB-mutation proof on historical GET).

    Django adds exactly one non-field instance attribute (``_state``),
    whose repr carries a memory address; it is excluded so the digest
    reflects persisted data only. Every concrete field — including the
    run's state and timestamps — is covered.
    """
    h = hashlib.sha256()
    for model in (
        ResearchRun,
        PriceIntelligenceSnapshot,
        ResearchSupplementSnapshot,
        ResearchFxSnapshot,
        AiAssistedReviewCandidate,
        ComparableResearchExecution,
    ):
        rows = sorted(
            (
                json.dumps(
                    {
                        k: v
                        for k, v in obj.__dict__.items()
                        if k != "_state"
                    },
                    sort_keys=True,
                    default=str,
                )
                for obj in model.objects.all()
            )
        )
        h.update(f"{model._meta.db_table}:{len(rows)}:".encode())
        for row in rows:
            h.update(row.encode())
    return h.hexdigest()


def _status_block(html: str) -> str:
    """The rendered Vendor API status notice region (empty if absent)."""
    marker = 'class="pi-vendor-status '
    start = html.index(marker)
    end = html.index("</div>", start) + len("</div>")
    return html[start:end]


def _quote_section(html: str) -> str:
    """The rendered Quote & Market Summary section (h2 to h2)."""
    start = html.index("<h2>Quote & Market Summary</h2>")
    end = html.index("<h2>Price intelligence</h2>", start)
    return html[start:end]


# Raw codec field names / payload tokens that must never be rendered.
RAW_CODEC_TOKENS = (
    "lookup_status",
    "vendor_commercial_result",
    "price_basis",
    "VENDOR_API_POLICY",
    "CUSTOMER_PRICE",
    "LIST_PRICE",
    "explicit_candidate_mpn",
    "schema_version",
    "SupplementCodecError",
    "Traceback",
)


# ---------------------------------------------------------------------------
# FAILED — the production evidence shape (Micron run): FAILED, no
# observations, no source issues, cause not persisted.
# ---------------------------------------------------------------------------


class TestVendorStatusFailed(TestCase):
    def test_failed_snapshot_allowed_displays_failure_notice(self) -> None:
        """ALLOWED: the exact failure message for a FAILED lookup whose
        persisted evidence records no cause (the production shape)."""
        run = _make_completed_run(
            "VSUX-FAILED",
            lookup_status=SupplementLookupStatus.FAILED,
            observations=(),
            source_issues=(),
        )
        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            _mock_settings(),
        ), _armed_live_boundaries():
            response = _get(Client(), _detail_url(run), ALLOWED_ADDR)
        assert response.status_code == 200
        status = response.context["vendor_api_status"]
        assert isinstance(status, VendorApiStatusPresentation)
        assert status.state == "failed"
        assert status.state_label == "Lookup failed"

        html = response.content.decode()
        section = _quote_section(html)
        assert "Vendor API status:" in section
        assert "Lookup failed" in section
        assert (
            "The internal vendor lookup for this run failed, and no "
            "vendor quote was obtained." in section
        )
        # The accurate bounded statement: the codec persists no cause.
        assert (
            "The specific failure cause was not recorded by the lookup."
            in section
        )
        # No invented reason: the notice itself must not speculate about
        # the cause (configuration, network, part number, timeout, ...).
        status_block = _status_block(html)
        lowered = status_block.lower()
        for invented in ("timeout", "timed out", "configuration", "disabled",
                         "network error", "status code", "exception",
                         "http"):
            assert invented not in lowered, f"invented cause word: {invented}"
        # No raw codec tokens anywhere on the page.
        for token in RAW_CODEC_TOKENS:
            assert token not in html
        # No vendor quote rows and no vendor price.
        assert "(Vendor API)" not in html
        assert SENTINEL_VENDOR_PRICE not in html
        assert "777,000.13" not in html
        # The public row is unaffected.
        assert "€1,500.00 EUR" in html

    def test_failed_snapshot_denied_learns_nothing(self) -> None:
        """DENIED: a FAILED snapshot must leak nothing — not the failure
        status, not the snapshot's existence, not sources or counts — and
        the supplemental artifact access path is never touched."""
        run = _make_completed_run(
            "VSUX-FAILED-DENIED",
            lookup_status=SupplementLookupStatus.FAILED,
            observations=(),
            source_issues=(
                SupplementSourceIssue(
                    source_name=SENTINEL_SOURCE,
                    outcome="MALFORMED_SECTION",
                    detail=None,
                ),
            ),
        )
        with (
            patch(
                "product_intelligence.web.commercial_access._django_settings",
                _mock_settings(),
            ),
            _armed_supplement_boundaries(),
            _armed_live_boundaries(),
        ):
            response = _get(Client(), _detail_url(run), DENIED_ADDR)
        assert response.status_code == 200
        assert response.context["vendor_commercial_access_allowed"] is False
        # No vendor status fact of any kind in the DENIED context.
        assert response.context["vendor_api_status"] is None

        html = response.content.decode()
        # The neutral access notice is the only vendor-related text.
        assert (
            "Internal commercial pricing is unavailable for this "
            "connection." in html
        )
        # Nothing about the FAILED lookup leaks.
        assert "Vendor API status" not in html
        assert "Lookup failed" not in html
        assert "lookup failed" not in html
        assert "not recorded" not in html
        assert "MALFORMED_SECTION" not in html
        assert "could not be read" not in html
        assert SENTINEL_SOURCE not in html
        assert "(Vendor API)" not in html
        assert SENTINEL_VENDOR_PRICE not in html
        assert "777,000.13" not in html
        # The public row is still usable for the DENIED connection.
        assert "€1,500.00 EUR" in html
        assert "Quote & Market Summary unavailable." not in html

    def test_failed_with_bounded_source_issues_allowed(self) -> None:
        """ALLOWED: a FAILED lookup whose persisted evidence DOES record
        bounded per-source results shows those results as the specific,
        evidence-backed cause (never a guess)."""
        run = _make_completed_run(
            "VSUX-FAILED-ISSUES",
            lookup_status=SupplementLookupStatus.FAILED,
            observations=(),
            source_issues=(
                SupplementSourceIssue(
                    source_name="AlphaSource",
                    outcome="NOT_FOUND",
                    detail=None,
                ),
                SupplementSourceIssue(
                    source_name="BetaSource",
                    outcome="MPN_MISMATCH",
                    detail="vendor_mpn_mismatch",
                ),
            ),
        )
        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            _mock_settings(),
        ):
            response = _get(Client(), _detail_url(run), ALLOWED_ADDR)
        assert response.status_code == 200
        html = response.content.decode()
        section = _quote_section(html)
        assert "Lookup failed" in section
        assert "Bounded per-source results recorded by the lookup:" in section
        assert "AlphaSource — not found" in section
        assert (
            "BetaSource — published part number did not match the "
            "requested part number" in section
        )
        # With evidence-backed causes shown, the "not recorded" statement
        # must not also claim the cause is unknown.
        assert "The specific failure cause was not recorded" not in section
        # Raw vocabulary values are never rendered.
        assert "NOT_FOUND" not in html
        assert "MPN_MISMATCH" not in html
        assert "vendor_mpn_mismatch" not in html


# ---------------------------------------------------------------------------
# SUCCESS — zero usable observations / with observations
# ---------------------------------------------------------------------------


class TestVendorStatusSuccess(TestCase):
    def test_success_zero_observations_allowed(self) -> None:
        run = _make_completed_run(
            "VSUX-SUCCESS-ZERO",
            lookup_status=SupplementLookupStatus.SUCCESS,
            observations=(),
            source_issues=(),
        )
        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            _mock_settings(),
        ):
            response = _get(Client(), _detail_url(run), ALLOWED_ADDR)
        assert response.status_code == 200
        status = response.context["vendor_api_status"]
        assert status.state == "completed-no-quote"
        section = _quote_section(response.content.decode())
        assert "Completed — no usable vendor quote" in section
        assert (
            "The internal vendor lookup completed, but it produced no "
            "usable identity-bound vendor quote for this run." in section
        )
        assert "(Vendor API)" not in section
        # The public row remains.
        assert "€1,500.00 EUR" in section

    def test_success_zero_observations_with_issues_allowed(self) -> None:
        """The bounded per-source results are the evidence-backed reason
        no usable quote exists (e.g. every source not found)."""
        run = _make_completed_run(
            "VSUX-SUCCESS-ZERO-ISSUES",
            lookup_status=SupplementLookupStatus.SUCCESS,
            observations=(),
            source_issues=(
                SupplementSourceIssue(
                    source_name="AlphaSource",
                    outcome="NOT_FOUND",
                    detail=None,
                ),
                SupplementSourceIssue(
                    source_name="BetaSource",
                    outcome="MISSING_EXPLICIT_MPN",
                    detail=None,
                ),
            ),
        )
        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            _mock_settings(),
        ):
            response = _get(Client(), _detail_url(run), ALLOWED_ADDR)
        assert response.status_code == 200
        section = _quote_section(response.content.decode())
        assert "Completed — no usable vendor quote" in section
        assert "Bounded per-source results recorded by the lookup:" in section
        assert "AlphaSource — not found" in section
        assert "BetaSource — no explicit part number published" in section

    def test_success_with_observations_allowed_compact_status(self) -> None:
        """The usual vendor quotes render (existing behavior intact) with
        the compact successful status alongside them."""
        run = _make_completed_run("VSUX-SUCCESS-ONE", with_supplement=False)
        _persist_supplement(
            run,
            lookup_status=SupplementLookupStatus.SUCCESS,
            observations=(_vendor_observation(run),),
        )
        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            _mock_settings(),
        ), _armed_live_boundaries():
            response = _get(Client(), _detail_url(run), ALLOWED_ADDR)
        assert response.status_code == 200
        html = response.content.decode()
        section = _quote_section(html)
        # Compact successful status.
        assert "Vendor API status:" in section
        assert ">Completed<" in section
        assert (
            "The internal vendor lookup completed; the vendor quote is "
            "shown in the table below." in section
        )
        # The existing vendor quote display is intact: exact label once,
        # sentinel price rendered.
        assert html.count(f"{SENTINEL_SOURCE} (Vendor API)") == 1
        assert "$777,000.13 USD" in html

    def test_success_with_two_observations_plural(self) -> None:
        run = _make_completed_run("VSUX-SUCCESS-TWO", with_supplement=False)
        _persist_supplement(
            run,
            lookup_status=SupplementLookupStatus.SUCCESS,
            observations=(
                _vendor_observation(run, source_name="SourceOne"),
                _vendor_observation(
                    run, source_name="SourceTwo", price=Decimal("123.45")
                ),
            ),
        )
        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            _mock_settings(),
        ):
            response = _get(Client(), _detail_url(run), ALLOWED_ADDR)
        assert response.status_code == 200
        section = _quote_section(response.content.decode())
        assert (
            "The internal vendor lookup completed; the vendor quotes are "
            "shown in the table below." in section
        )
        assert "SourceOne (Vendor API)" in section
        assert "SourceTwo (Vendor API)" in section

    def test_success_denied_unchanged(self) -> None:
        """DENIED: the SUCCESS snapshot changes nothing — no status, no
        source, no price; the public rows render from persisted evidence."""
        run = _make_completed_run("VSUX-SUCCESS-DENIED", with_supplement=False)
        _persist_supplement(
            run,
            lookup_status=SupplementLookupStatus.SUCCESS,
            observations=(_vendor_observation(run),),
        )
        with (
            patch(
                "product_intelligence.web.commercial_access._django_settings",
                _mock_settings(),
            ),
            _armed_supplement_boundaries(),
            _armed_live_boundaries(),
        ):
            response = _get(Client(), _detail_url(run), DENIED_ADDR)
        assert response.status_code == 200
        assert response.context["vendor_api_status"] is None
        html = response.content.decode()
        assert "Vendor API status" not in html
        assert SENTINEL_SOURCE not in html
        assert "777,000.13" not in html
        assert "(Vendor API)" not in html
        assert "Internal commercial pricing is unavailable for this " \
               "connection." in html
        assert "€1,500.00 EUR" in html


# ---------------------------------------------------------------------------
# PARTIAL
# ---------------------------------------------------------------------------


class TestVendorStatusPartial(TestCase):
    def test_partial_allowed(self) -> None:
        run = _make_completed_run("VSUX-PARTIAL", with_supplement=False)
        _persist_supplement(
            run,
            lookup_status=SupplementLookupStatus.PARTIAL,
            observations=(_vendor_observation(run),),
            source_issues=(
                SupplementSourceIssue(
                    source_name="OtherSource",
                    outcome="NOT_FOUND",
                    detail=None,
                ),
            ),
        )
        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            _mock_settings(),
        ):
            response = _get(Client(), _detail_url(run), ALLOWED_ADDR)
        assert response.status_code == 200
        status = response.context["vendor_api_status"]
        assert status.state == "partial"
        section = _quote_section(response.content.decode())
        assert "Partially completed" in section
        assert (
            "The internal vendor lookup partially completed: some vendor "
            "results were obtained while other sources had bounded "
            "failures or were excluded." in section
        )
        assert "OtherSource — not found" in section
        # The obtained vendor result still renders as the usual row.
        assert f"{SENTINEL_SOURCE} (Vendor API)" in section

    def test_partial_no_observations_allowed(self) -> None:
        run = _make_completed_run(
            "VSUX-PARTIAL-ZERO",
            lookup_status=SupplementLookupStatus.PARTIAL,
            observations=(),
            source_issues=(
                SupplementSourceIssue(
                    source_name="OtherSource",
                    outcome="MALFORMED_SECTION",
                    detail=None,
                ),
            ),
        )
        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            _mock_settings(),
        ):
            response = _get(Client(), _detail_url(run), ALLOWED_ADDR)
        assert response.status_code == 200
        section = _quote_section(response.content.decode())
        assert "Partially completed" in section
        assert "No usable vendor quote was obtained for this run." in section
        assert "OtherSource — response section could not be read" in section

    def test_partial_denied_learns_nothing(self) -> None:
        run = _make_completed_run("VSUX-PARTIAL-DENIED", with_supplement=False)
        _persist_supplement(
            run,
            lookup_status=SupplementLookupStatus.PARTIAL,
            observations=(_vendor_observation(run),),
            source_issues=(
                SupplementSourceIssue(
                    source_name="OtherSource",
                    outcome="NOT_FOUND",
                    detail=None,
                ),
            ),
        )
        with (
            patch(
                "product_intelligence.web.commercial_access._django_settings",
                _mock_settings(),
            ),
            _armed_supplement_boundaries(),
            _armed_live_boundaries(),
        ):
            response = _get(Client(), _detail_url(run), DENIED_ADDR)
        assert response.status_code == 200
        assert response.context["vendor_api_status"] is None
        html = response.content.decode()
        assert "Vendor API status" not in html
        assert "Partially completed" not in html
        assert "OtherSource" not in html
        assert SENTINEL_SOURCE not in html
        assert "777,000.13" not in html
        assert "€1,500.00 EUR" in html


# ---------------------------------------------------------------------------
# NOT_ATTEMPTED — no supplemental snapshot for this run
# ---------------------------------------------------------------------------


class TestVendorStatusNotRecorded(TestCase):
    def test_not_recorded_allowed(self) -> None:
        run = _make_completed_run("VSUX-NONE", with_supplement=False)
        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            _mock_settings(),
        ):
            response = _get(Client(), _detail_url(run), ALLOWED_ADDR)
        assert response.status_code == 200
        status = response.context["vendor_api_status"]
        assert status.state == "not-recorded"
        section = _quote_section(response.content.decode())
        status_block = _status_block(response.content.decode())
        assert "Vendor API status:" in section
        assert ">Not recorded<" in status_block
        assert (
            "No vendor lookup was recorded for this research run, so no "
            "reason is stated." in status_block
        )
        # No reason is invented: the notice itself must not speculate
        # about why the lookup is absent (configuration, part number,
        # availability).
        lowered = status_block.lower()
        for invented in ("configuration", "configured", "disabled",
                         "no mpn", "not configured", "unavailable"):
            assert invented not in lowered, f"invented reason: {invented}"

    def test_not_recorded_denied(self) -> None:
        run = _make_completed_run("VSUX-NONE-DENIED", with_supplement=False)
        with (
            patch(
                "product_intelligence.web.commercial_access._django_settings",
                _mock_settings(),
            ),
            _armed_supplement_boundaries(),
            _armed_live_boundaries(),
        ):
            response = _get(Client(), _detail_url(run), DENIED_ADDR)
        assert response.status_code == 200
        assert response.context["vendor_api_status"] is None
        html = response.content.decode()
        assert "Vendor API status" not in html
        assert "Not recorded" not in html
        assert "Internal commercial pricing is unavailable for this " \
               "connection." in html
        assert "€1,500.00 EUR" in html


# ---------------------------------------------------------------------------
# Malformed payload — existing fail-closed behavior preserved
# ---------------------------------------------------------------------------


class TestVendorStatusFailClosed(TestCase):
    def test_malformed_supplement_allowed_no_status_no_partial(self) -> None:
        """The EXISTING fail-closed contract: a malformed vendor
        supplemental payload yields "Quote & Market Summary unavailable."
        — no status notice (no misleading success), no partial-public
        fallback."""
        run = _make_completed_run(
            "VSUX-MALFORMED",
            malformed_supplement=True,
        )
        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            _mock_settings(),
        ):
            response = _get(Client(), _detail_url(run), ALLOWED_ADDR)
        assert response.status_code == 200
        assert response.context["vendor_api_status"] is None
        assert response.context["compact_quote"] is None
        html = response.content.decode()
        assert "Quote & Market Summary unavailable." in html
        assert "Vendor API status" not in html
        assert "€1,500.00 EUR" not in html.split(
            "Quote & Market Summary"
        )[-1].split("Price intelligence")[0]
        assert "(Vendor API)" not in html
        assert "777,000.13" not in html
        for token in ("SupplementCodecError", "garbage", "Traceback"):
            assert token not in html
        # The detailed existing report still renders.
        assert "Price aggregation status:" in html

    def test_malformed_supplement_denied_irrelevant(self) -> None:
        run = _make_completed_run(
            "VSUX-MALFORMED-DENIED",
            malformed_supplement=True,
        )
        with (
            patch(
                "product_intelligence.web.commercial_access._django_settings",
                _mock_settings(),
            ),
            _armed_supplement_boundaries(),
            _armed_live_boundaries(),
        ):
            response = _get(Client(), _detail_url(run), DENIED_ADDR)
        assert response.status_code == 200
        assert response.context["vendor_api_status"] is None
        html = response.content.decode()
        assert "USD Equivalent" in html
        assert "€1,500.00 EUR" in html
        assert "Quote & Market Summary unavailable." not in html
        assert "Vendor API status" not in html


# ---------------------------------------------------------------------------
# Coexistence: public + AI rows remain usable over a FAILED lookup; the
# $0 vendor display contract stays intact alongside the status.
# ---------------------------------------------------------------------------


class TestVendorStatusCoexistence(TestCase):
    def _make_run_with_semantic_candidate(self) -> tuple[ResearchRun, ListingObservation]:
        """A COMPLETED run with one deterministic NEW bucket and one
        human-review-eligible semantic assessment (built exactly like the
        frozen HUMAN-REVIEW fixtures)."""
        mpn = "VSUX-CONFIRM"
        description = "Vendor status confirmed candidate product"
        request = ResearchRequest(manufacturer_part_number=mpn, description=description)
        run = ResearchRun.objects.create_from_request(request)
        run.transition_to(ResearchRunState.RUNNING)
        run.transition_to(ResearchRunState.COMPLETED)

        pub_obs = ListingObservation(
            source_url=PUBLIC_SOURCE_URL,
            extraction_method=ExtractionMethod.JSON_LD,
            product_title="Confirmed Candidate Product",
            manufacturer_part_number_text=mpn,
            sku_text=None,
            brand_text=None,
            price_text=str(PUBLIC_PRICE),
            currency_text="EUR",
            availability_text="In Stock",
            condition_text="New",
            seller_text="Example Store",
            offer_url_text=None,
            raw_reference=None,
        )
        pub_norm = NormalizedListingObservation(
            observation=pub_obs,
            price_amount=PUBLIC_PRICE,
            currency_code="EUR",
            availability=NormalizedAvailability.IN_STOCK,
            condition=NormalizedCondition.NEW,
            seller_name="Example Store",
            normalization_issues=(),
        )
        pub_assess = ListingIdentityAssessment(
            normalized_listing=pub_norm,
            requested_part_number=mpn,
            candidate_part_number_raw=mpn,
            candidate_part_number_compared=mpn,
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.EXACT,
            decision=EvidenceDecision.ACCEPTED,
            rejection_reason=None,
        )

        sem_obs = ListingObservation(
            source_url="https://semantic-confirmed.example.com/c",
            extraction_method=ExtractionMethod.JSON_LD,
            product_title=f"Brand new {mpn} enterprise 1635",
            manufacturer_part_number_text="",
            sku_text=None,
            brand_text=None,
            price_text="1635.00",
            currency_text="USD",
            availability_text="In Stock",
            condition_text="New",
            seller_text="Semantic Seller",
            offer_url_text=None,
            raw_reference=None,
        )
        sem_norm = NormalizedListingObservation(
            observation=sem_obs,
            price_amount=Decimal("1635.00"),
            currency_code="USD",
            availability=NormalizedAvailability.IN_STOCK,
            condition=NormalizedCondition.NEW,
            seller_name="Semantic Seller",
            normalization_issues=(),
        )
        sem_assess = ListingIdentityAssessment(
            normalized_listing=sem_norm,
            requested_part_number=mpn,
            candidate_part_number_raw=mpn,
            candidate_part_number_compared=mpn,
            candidate_evidence_source=EvidenceSource.TITLE_TEXT,
            match_type=IdentityMatchType.UNKNOWN,
            decision=EvidenceDecision.REJECTED,
            rejection_reason=IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE,
        )

        price_result = aggregate_listing_prices(request, (pub_assess, sem_assess))
        PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=1,
            payload=encode_price_aggregation_result(price_result),
        )
        _persist_fx(run)
        return run, sem_obs

    def test_public_and_ai_rows_usable_when_vendor_failed(self) -> None:
        """A well-formed FAILED vendor lookup never takes down the
        public or human-confirmed AI rows: both remain usable in the same
        summary, next to the failure notice."""
        run, sem_obs = self._make_run_with_semantic_candidate()
        _persist_supplement(
            run,
            lookup_status=SupplementLookupStatus.FAILED,
            observations=(),
            source_issues=(),
        )
        # The semantic assessment is index 1 (accepted public first).
        candidate = AiAssistedReviewCandidate.objects.create(
            run=run,
            assessment_index=1,
            source_url=sem_obs.source_url,
            target_mpn=run.manufacturer_part_number,
            target_description="Vendor status confirmed candidate product",
            candidate_title=sem_obs.product_title or "",
            candidate_mpn_field=sem_obs.manufacturer_part_number_text or "",
            candidate_sku=sem_obs.sku_text or "",
            evidence_source="TITLE_TEXT",
            actual_provider="amax",
            actual_model="nemotron-3-super",
            prompt_version="v1.1",
        )
        review_url = reverse(
            "research-review",
            kwargs={"run_id": run.id, "candidate_id": candidate.id},
        )
        client = Client()
        response = client.post(review_url, {"action": "confirm"}, follow=False)
        assert response.status_code == 302

        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            _mock_settings(),
        ), _armed_live_boundaries():
            response = _get(client, _detail_url(run), ALLOWED_ADDR)
        assert response.status_code == 200
        assert response.context["vendor_api_status"].state == "failed"

        rows = list(response.context["compact_quote"].rows)
        prices = [r.price for r in rows]
        # The human-confirmed AI quote row remains usable.
        assert "$1,635.00 USD" in prices
        human_rows = [r for r in rows if r.note == "Human Confirmed"]
        assert len(human_rows) == 1
        # The public row remains usable.
        assert "€1,500.00 EUR" in prices
        # No vendor row (the FAILED lookup produced no evidence).
        assert all(r.source_type != "VENDOR_API" for r in rows)

        html = response.content.decode()
        section = _quote_section(html)
        assert (
            "The specific failure cause was not recorded by the lookup."
            in section
        )
        # The unified business summary still counts the usable rows.
        assert "<dd>2</dd>" in section

    def test_vendor_zero_price_row_and_status_coexist(self) -> None:
        """A source-published zero vendor price keeps its exact existing
        display contract ($0 USD + verification note in the row) while the
        compact successful status renders alongside."""
        run = _make_completed_run("VSUX-ZERO", with_supplement=False)
        _persist_supplement(
            run,
            lookup_status=SupplementLookupStatus.SUCCESS,
            observations=(
                _vendor_observation(run, price=Decimal("0")),
            ),
        )
        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            _mock_settings(),
        ):
            response = _get(Client(), _detail_url(run), ALLOWED_ADDR)
        assert response.status_code == 200
        rows = list(response.context["compact_quote"].rows)
        assert len(rows) == 2  # vendor zero row + public row
        vendor_row = rows[0]
        assert vendor_row.source_type == "VENDOR_API"
        assert vendor_row.price == "$0 USD"
        assert vendor_row.note is not None
        assert "Source-published price: $0 USD — Verify price and " \
               "purchasing availability with the supplier." in vendor_row.note
        html = response.content.decode()
        section = _quote_section(html)
        assert ">Completed<" in section
        assert (
            "The internal vendor lookup completed; the vendor quote is "
            "shown in the table below." in section
        )
        # The $0 note stays in the row's Market Use cell, not the status.
        status = _status_block(html)
        assert "Verify price and purchasing availability" not in status
        # The frozen no-fabricated-availability wording is intact.
        for forbidden in ("free", "Free", "recommended", "purchasable"):
            assert forbidden not in vendor_row.note


# ---------------------------------------------------------------------------
# Historical GET: zero network calls, zero DB mutations (both branches)
# ---------------------------------------------------------------------------


class TestVendorStatusReadOnly(TestCase):
    def test_allowed_get_zero_network_zero_db_mutations(self) -> None:
        run = _make_completed_run(
            "VSUX-RO-ALLOWED",
            lookup_status=SupplementLookupStatus.FAILED,
            observations=(),
            source_issues=(),
        )
        before = _db_fingerprint()
        with (
            patch(
                "product_intelligence.web.commercial_access._django_settings",
                _mock_settings(),
            ),
            _armed_live_boundaries(),
        ):
            response = _get(Client(), _detail_url(run), ALLOWED_ADDR)
        after = _db_fingerprint()
        assert response.status_code == 200
        assert response.context["vendor_api_status"].state == "failed"
        # Zero DB mutations: every research table is byte-identical.
        assert before == after
        # The run's own state and timestamps are untouched.
        run.refresh_from_db()
        assert run.state == "COMPLETED"

    def test_denied_get_zero_network_zero_db_mutations(self) -> None:
        run = _make_completed_run("VSUX-RO-DENIED", with_supplement=False)
        _persist_supplement(
            run,
            lookup_status=SupplementLookupStatus.SUCCESS,
            observations=(_vendor_observation(run),),
        )
        before = _db_fingerprint()
        with (
            patch(
                "product_intelligence.web.commercial_access._django_settings",
                _mock_settings(),
            ),
            _armed_live_boundaries(),
            _armed_supplement_boundaries(),
        ):
            response = _get(Client(), _detail_url(run), DENIED_ADDR)
        after = _db_fingerprint()
        assert response.status_code == 200
        assert response.context["vendor_api_status"] is None
        assert before == after
        run.refresh_from_db()
        assert run.state == "COMPLETED"


# ---------------------------------------------------------------------------
# Pure presentation unit pins (no database)
# ---------------------------------------------------------------------------


def _result(
    lookup_status: str,
    observations: tuple = (),
    source_issues: tuple = (),
) -> ResearchSupplementResult:
    return ResearchSupplementResult(
        vendor_commercial_result=VendorCommercialResult(
            lookup_status=lookup_status,
            retrieved_at=None,
            observations=observations,
            source_issues=source_issues,
        ),
    )


class TestVendorStatusPresentationUnit:
    def test_not_recorded_shape(self) -> None:
        p = build_vendor_api_status_presentation(None)
        assert p.state == "not-recorded"
        assert p.state_label == "Not recorded"
        assert p.lines == (
            "No vendor lookup was recorded for this research run, so no "
            "reason is stated.",
        )

    def test_failed_no_evidence_shape(self) -> None:
        p = build_vendor_api_status_presentation(
            _result(SupplementLookupStatus.FAILED)
        )
        assert p.state == "failed"
        assert p.state_label == "Lookup failed"
        assert "The specific failure cause was not recorded by the lookup." \
            in p.lines

    def test_partial_shape(self) -> None:
        p = build_vendor_api_status_presentation(
            _result(
                SupplementLookupStatus.PARTIAL,
                source_issues=(
                    SupplementSourceIssue(
                        source_name="S", outcome="NOT_FOUND", detail=None
                    ),
                ),
            )
        )
        assert p.state == "partial"
        assert "S — not found" in p.lines
        assert "No usable vendor quote was obtained for this run." in p.lines

    def test_success_shapes(self) -> None:
        zero = build_vendor_api_status_presentation(
            _result(SupplementLookupStatus.SUCCESS)
        )
        assert zero.state == "completed-no-quote"
        one = build_vendor_api_status_presentation(
            _result(
                SupplementLookupStatus.SUCCESS,
                observations=(
                    SupplementSourceObservation(
                        source_name="S",
                        explicit_candidate_mpn="MPN",
                        vendor_mpn_match_type="EXACT",
                        price_amount=Decimal("1.00"),
                        currency_code="USD",
                        availability="IN_STOCK",
                        price_basis=SupplementPriceBasis.CUSTOMER_PRICE,
                        quantity=1,
                        note_kind=None,
                        brand_new=True,
                        brand_new_basis="VENDOR_API_POLICY",
                    ),
                ),
            )
        )
        assert one.state == "completed"
        assert one.lines == (
            "The internal vendor lookup completed; the vendor quote is "
            "shown in the table below.",
        )

    def test_unknown_status_fails_closed(self) -> None:
        class _Bogus:
            lookup_status = "SOMETHING_ELSE"
            observations = ()
            source_issues = ()

        class _BogusResult:
            vendor_commercial_result = _Bogus()

        p = build_vendor_api_status_presentation(_BogusResult())
        # Never claims success or a partial-public state.
        assert p.state == "not-recorded"
        assert "No vendor result is claimed." in p.lines[0]

    def test_status_lines_never_carry_raw_codec_tokens_or_prices(self) -> None:
        observation = SupplementSourceObservation(
            source_name="S",
            explicit_candidate_mpn="MPN",
            vendor_mpn_match_type="EXACT",
            price_amount=Decimal("999999.99"),
            currency_code="USD",
            availability="IN_STOCK",
            price_basis=SupplementPriceBasis.CUSTOMER_PRICE,
            quantity=1,
            note_kind=None,
            brand_new=True,
            brand_new_basis="VENDOR_API_POLICY",
        )
        for result in (
            None,
            _result(SupplementLookupStatus.FAILED),
            _result(
                SupplementLookupStatus.FAILED,
                source_issues=(
                    SupplementSourceIssue(
                        source_name="S",
                        outcome="MPN_MISMATCH",
                        detail="vendor_mpn_mismatch",
                    ),
                ),
            ),
            _result(SupplementLookupStatus.SUCCESS),
            _result(
                SupplementLookupStatus.SUCCESS, observations=(observation,)
            ),
            _result(
                SupplementLookupStatus.PARTIAL,
                observations=(observation,),
                source_issues=(
                    SupplementSourceIssue(
                        source_name="S", outcome="NOT_FOUND", detail=None
                    ),
                ),
            ),
        ):
            p = build_vendor_api_status_presentation(result)
            joined = "\n".join(p.lines)
            for token in RAW_CODEC_TOKENS:
                assert token not in joined
            # The status notice never carries a price.
            assert "999,999.99" not in joined
            assert "999999.99" not in joined
