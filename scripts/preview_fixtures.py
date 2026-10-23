"""Build fixture-based preview data for the PILOT-UX-WORKBENCH-A1 visual
verification (developer tool, never part of pytest).

Creates a fresh preview SQLite database (via PI_SQLITE_PATH) with
representative runs covering the required visual cases:

  P1  completed, multiple supplier quotes (2 vendor + 1 public + FX)
  P2  completed, source-published $0 quote (B1 verification note)
  P3  completed, no usable price evidence (UNKNOWN verification)
  P4  completed, AI-assisted review candidate (needs review)
  P5  completed, comparable research result (FULL, one candidate)
  P6  running research state
  P7  failed research state
  P8  created research state

All data is synthetic; no production data, no live provider calls.
"""

from __future__ import annotations

import os
import sys
from datetime import date, datetime, timezone
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.core.management import call_command  # noqa: E402
from django.db import connections  # noqa: E402

from product_intelligence.domain import ResearchRequest  # noqa: E402
from product_intelligence.domain.enums import (  # noqa: E402
    ConfidenceLevel,
    EvidenceDecision,
    IdentityMatchType,
    ResearchRunState,
    VerificationStatus,
)
from product_intelligence.research import (  # noqa: E402
    ListingIdentityAssessment,
    ListingObservation,
    PriceAggregateBucket,
    PriceAggregationResult,
    encode_price_aggregation_result,
)
from product_intelligence.research.aggregation import (  # noqa: E402
    PriceAggregationExclusion,
    PriceAggregationExclusionReason,
    aggregate_listing_prices,
)
from product_intelligence.research.fx_codec import encode_fx_observation  # noqa: E402
from product_intelligence.research.listings import ExtractionMethod  # noqa: E402
from product_intelligence.research.matching import (  # noqa: E402
    EvidenceSource,
    IdentityRejectionReason,
)
from product_intelligence.research.normalization import (  # noqa: E402
    NormalizedAvailability,
    NormalizedCondition,
    NormalizedListingObservation,
)
from product_intelligence.providers.fx import FxRateObservation  # noqa: E402
from product_intelligence.runs.models import (  # noqa: E402
    AiAssistedReviewCandidate,
    ComparableResearchExecution,
    ComparableResearchState,
    PriceIntelligenceSnapshot,
    ResearchFxSnapshot,
    ResearchRun,
    ResearchSupplementSnapshot,
)
from product_intelligence.research.commercial_supplement_codec import (  # noqa: E402
    ResearchSupplementResult,
    SupplementLookupStatus,
    SupplementPriceBasis,
    SupplementSourceObservation,
    VendorCommercialResult,
    encode_research_supplement_result,
)
from product_intelligence.research.comparable_result_codec import (  # noqa: E402
    encode_comparable_result,
)
from product_intelligence.research.comparable_research_results import (  # noqa: E402
    AuthorityAttemptResult,
    AuthorityAuditOutcomeKind,
    ComparisonState,
    DatasheetAttemptResult,
    DatasheetAuditOutcomeKind,
    EvidenceLayer,
    EvidenceSourceReference,
    ComparableCandidateResult,
    ComparableResearchResult,
    ComparableResultKind,
    FieldAssessmentResult,
    ProductEnrichmentAudit,
    ResolutionState,
    SourceAuthority,
)


def _fresh_db() -> None:
    name = connections["default"].settings_dict["NAME"]
    if os.path.exists(name):
        os.remove(name)
    call_command("migrate", verbosity=0)


def _base_run(mpn: str, description: str) -> ResearchRun:
    run = ResearchRun.objects.create_from_request(
        ResearchRequest(manufacturer_part_number=mpn, description=description)
    )
    run.transition_to(ResearchRunState.RUNNING)
    return run


def _public_assessment(
    run: ResearchRun,
    *,
    source_url: str,
    price: Decimal,
    currency: str,
    availability: NormalizedAvailability = NormalizedAvailability.IN_STOCK,
    title: str = "Preview Product",
):
    mpn = run.manufacturer_part_number or "PREVIEW"
    obs = ListingObservation(
        source_url=source_url,
        extraction_method=ExtractionMethod.JSON_LD,
        product_title=title,
        manufacturer_part_number_text=mpn,
        sku_text=None,
        brand_text=None,
        price_text=str(price),
        currency_text=currency,
        availability_text="In Stock"
        if availability is NormalizedAvailability.IN_STOCK
        else "Out of Stock",
        condition_text="New",
        seller_text="Preview Store",
        offer_url_text=None,
        raw_reference=None,
    )
    norm = NormalizedListingObservation(
        observation=obs,
        price_amount=price,
        currency_code=currency,
        availability=availability,
        condition=NormalizedCondition.NEW,
        seller_name="Preview Store",
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
    return obs, assess


def _persist_price(run: ResearchRun, result: PriceAggregationResult) -> None:
    PriceIntelligenceSnapshot.objects.create(
        run=run, schema_version=1, payload=encode_price_aggregation_result(result)
    )


def _persist_fx(run: ResearchRun) -> None:
    payload = encode_fx_observation(
        provider_id="ECB",
        observation_date=date(2026, 10, 1),
        base_currency="EUR",
        rates=(
            FxRateObservation(currency_code="USD", rate=Decimal("1.09")),
            FxRateObservation(currency_code="EUR", rate=Decimal("1.0")),
        ),
        retrieved_at=datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc),
    )
    ResearchFxSnapshot.objects.create(run=run, schema_version=1, payload=payload)


def _persist_vendor(run: ResearchRun) -> None:
    observations = (
        SupplementSourceObservation(
            source_name="Ingram",
            explicit_candidate_mpn=run.manufacturer_part_number,
            vendor_mpn_match_type="EXACT",
            price_amount=Decimal("2023.27"),
            currency_code="USD",
            availability="IN_STOCK",
            price_basis=SupplementPriceBasis.CUSTOMER_PRICE,
            quantity=1,
            note_kind=None,
            brand_new=True,
            brand_new_basis="VENDOR_API_POLICY",
        ),
        SupplementSourceObservation(
            source_name="CDW",
            explicit_candidate_mpn=run.manufacturer_part_number,
            vendor_mpn_match_type="EXACT",
            price_amount=Decimal("1999.99"),
            currency_code="USD",
            availability="OUT_OF_STOCK",
            price_basis=SupplementPriceBasis.CUSTOMER_PRICE,
            quantity=1,
            note_kind=None,
            brand_new=True,
            brand_new_basis="VENDOR_API_POLICY",
        ),
        SupplementSourceObservation(
            source_name="Synnex EU",
            explicit_candidate_mpn=run.manufacturer_part_number,
            vendor_mpn_match_type="EXACT",
            price_amount=Decimal("1705.35"),
            currency_code="EUR",
            availability="IN_STOCK",
            price_basis=SupplementPriceBasis.CUSTOMER_PRICE,
            quantity=1,
            note_kind="NO_RETURNS",
            brand_new=True,
            brand_new_basis="VENDOR_API_POLICY",
        ),
    )
    result = ResearchSupplementResult(
        vendor_commercial_result=VendorCommercialResult(
            lookup_status=SupplementLookupStatus.SUCCESS,
            retrieved_at=datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc),
            observations=observations,
            source_issues=(),
        ),
    )
    ResearchSupplementSnapshot.objects.create(
        run=run,
        schema_version=1,
        payload=encode_research_supplement_result(result),
    )


def build() -> None:
    _fresh_db()
    urls: list[str] = []

    # P1 — completed, multiple supplier quotes (ALLOWED server shows vendors)
    run = _base_run("MTFDKCC3T8TGP-1BK1DABYY", "480GB NVMe M.2 solid state drive")
    obs, assess = _public_assessment(
        run,
        source_url="https://www.example.com/ssd/mtfdkcc3t8tgp",
        price=Decimal("1500.00"),
        currency="EUR",
    )
    norm = assess.normalized_listing
    result = PriceAggregationResult(
        request=run.to_research_request(),
        assessments=(assess,),
        exclusions=(),
        buckets=(
            PriceAggregateBucket(
                currency_code="EUR",
                condition=NormalizedCondition.NEW,
                assessments=(assess,),
                count=1,
                low=Decimal("1500.00"),
                median=Decimal("1500.00"),
                high=Decimal("1500.00"),
                market_range_low=None,
                market_range_high=None,
                confidence=ConfidenceLevel.LOW,
            ),
        ),
        verification_status=VerificationStatus.VERIFIED,
    )
    _persist_price(run, result)
    _persist_fx(run)
    _persist_vendor(run)
    run.transition_to(ResearchRunState.COMPLETED)
    urls.append(("P1 multi-supplier (ALLOWED server)", f"/research/{run.id}"))

    # P2 — completed, source-published $0 quote (B1 note)
    run = _base_run("ZERO-OFFER-MPN", "zero price preview drive")
    obs, assess = _public_assessment(
        run,
        source_url="https://zero-offer.example/product/zero",
        price=Decimal("0"),
        currency="USD",
    )
    _persist_price(run, aggregate_listing_prices(run.to_research_request(), (assess,)))
    run.transition_to(ResearchRunState.COMPLETED)
    urls.append(("P2 source-published $0 quote", f"/research/{run.id}"))

    # P3 — completed, no usable price evidence (UNKNOWN)
    run = _base_run("NO-EVIDENCE-MPN", "no price evidence preview")
    mpn = run.manufacturer_part_number
    obs = ListingObservation(
        source_url="https://example.com/wrong-product",
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
    result = PriceAggregationResult(
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
    _persist_price(run, result)
    run.transition_to(ResearchRunState.COMPLETED)
    urls.append(("P3 no usable price evidence", f"/research/{run.id}"))

    # P4 — completed, AI-assisted review candidate (needs review)
    run = _base_run("AI-REVIEW-MPN", "AI review preview drive")
    obs = ListingObservation(
        source_url="https://example.com/product/ai-review",
        extraction_method=ExtractionMethod.JSON_LD,
        manufacturer_part_number_text="",
        sku_text=None,
        product_title="AI review candidate for AI-REVIEW-MPN",
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
        seller_name="Preview Seller",
        normalization_issues=(),
    )
    assess = ListingIdentityAssessment(
        normalized_listing=norm,
        requested_part_number="AI-REVIEW-MPN",
        candidate_part_number_raw="AI-REVIEW-MPN",
        candidate_part_number_compared="AI-REVIEW-MPN",
        candidate_evidence_source=EvidenceSource.TITLE_TEXT,
        match_type=IdentityMatchType.UNKNOWN,
        decision=EvidenceDecision.REJECTED,
        rejection_reason=IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE,
    )
    _persist_price(run, aggregate_listing_prices(run.to_research_request(), (assess,)))
    AiAssistedReviewCandidate.objects.create(
        run=run,
        assessment_index=0,
        source_url=obs.source_url,
        target_mpn=run.manufacturer_part_number,
        target_description=run.description,
        candidate_title=obs.product_title,
        candidate_mpn_field="",
        candidate_sku="",
        evidence_source="TITLE_TEXT",
        actual_provider="amax",
        actual_model="nemotron-3-super",
        prompt_version="v1.1",
    )
    run.transition_to(ResearchRunState.COMPLETED)
    urls.append(("P4 AI review candidate", f"/research/{run.id}"))

    # P5 — completed, comparable research result (FULL, one candidate)
    run = _base_run("COMP-TARGET-MPN", "comparable preview drive")
    _persist_price(
        run,
        PriceAggregationResult(
            request=run.to_research_request(),
            assessments=(),
            exclusions=(),
            buckets=(),
            verification_status=VerificationStatus.UNKNOWN,
        ),
    )
    run.transition_to(ResearchRunState.COMPLETED)
    from product_intelligence.research.enterprise_ssd import ENTERPRISE_SSD_SCHEMA

    keys = list(ENTERPRISE_SSD_SCHEMA.definitions.keys())

    def _evidence():
        return (
            EvidenceSourceReference(
                source_name="TestSource",
                source_url="https://example.com/support",
                evidence_layer=EvidenceLayer.SUPPORT_PAGE,
                source_authority=SourceAuthority.AUTHORITATIVE,
                retrieved_at="2024-01-01T00:00:00+00:00",
            ),
        )

    assessments = []
    for idx, key in enumerate(keys):
        if idx < 7:
            assessments.append(
                FieldAssessmentResult(
                    definition_key=key,
                    comparison_state=ComparisonState.SCORED,
                    target_resolution_state=ResolutionState.VERIFIED,
                    candidate_resolution_state=ResolutionState.VERIFIED,
                    field_similarity=Decimal("1"),
                    target_value="test",
                    candidate_value="test",
                    target_evidence=_evidence(),
                    candidate_evidence=_evidence(),
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
    total = len(keys)
    candidate = ComparableCandidateResult(
        candidate_mpn="CAND-001",
        candidate_normalized_mpn="CAND-001",
        scored_field_count=7,
        evidence_coverage=Decimal(7) / Decimal(total),
        observed_similarity=Decimal("1"),
        evidence_weighted_similarity=Decimal(7) / Decimal(total),
        field_assessments=tuple(assessments),
        enrichment_audit=ProductEnrichmentAudit(
            product_mpn="CAND-001",
            attempts=(DatasheetAttemptResult(outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE),),
        ),
    )
    full = ComparableResearchResult(
        kind=ComparableResultKind.FULL,
        target_mpn=run.manufacturer_part_number,
        target_manufacturer="Preview Corp",
        target_enrichment_audit=ProductEnrichmentAudit(
            product_mpn=run.manufacturer_part_number,
            attempts=(DatasheetAttemptResult(outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE),),
        ),
        authority_audit=(
            AuthorityAttemptResult(
                policy_id="preview-policy",
                outcome=AuthorityAuditOutcomeKind.MATCHED,
                requested_source_url="https://example.com/support",
                fetched_final_url="https://example.com/support",
                retrieved_at=datetime.now(timezone.utc).isoformat(),
                matching_mpn=run.manufacturer_part_number,
            ),
        ),
        candidates=(candidate,),
    )
    ComparableResearchExecution.objects.create(
        parent_run=run,
        state=ComparableResearchState.COMPLETED,
        active_slot=None,
        started_at=datetime(2026, 10, 2, 9, 0, 0, tzinfo=timezone.utc),
        finished_at=datetime(2026, 10, 2, 9, 2, 0, tzinfo=timezone.utc),
        result_payload=encode_comparable_result(full),
        result_schema_version=1,
    )
    urls.append(("P5 comparable result", f"/research/{run.id}"))

    # P6 — running
    run = _base_run("RUNNING-MPN", "running preview")
    urls.append(("P6 running state", f"/research/{run.id}"))

    # P7 — failed
    run = _base_run("FAILED-MPN", "failed preview")
    run.transition_to(ResearchRunState.FAILED)
    urls.append(("P7 failed state", f"/research/{run.id}"))

    # P8 — created
    run = ResearchRun.objects.create_from_request(
        ResearchRequest(manufacturer_part_number="CREATED-MPN", description="created preview")
    )
    urls.append(("P8 created state", f"/research/{run.id}"))

    print()
    for label, url in urls:
        print(f"{label}: {url}")
    print()


if __name__ == "__main__":
    build()
