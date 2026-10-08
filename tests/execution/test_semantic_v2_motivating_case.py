"""The motivating Micron-shape case (S2-C, group I).

The customer complaint that drives Semantic Authority V2: deterministic
matching refuses a bounded near-miss MPN (one truncated suffix
character), the candidate never reaches the (V1) semantic layer, and the
system finds too few usable market-comparison sources.

Fixture shape (generic near-miss identifiers — NO manufacturer-specific
production logic):

    Requested MPN:  MTFDKCC3T8TGP-1BK1DABYYR
    Candidate MPN:  MTFDKCC3T8TGP-1BK1DABYY   (strict prefix: NM-1)
    Description:    Micron 7500 PRO / 3840GB / U.3 / 15mm / SSD

This test does NOT assert that the two identifiers are automatically
equivalent (they may or may not be — that is the model's semantic
judgment under qualification). It proves the frozen architecture:

1. the frozen deterministic layer does not Machine Verify them;
2. the bounded near-miss logic classifies them into the appropriate
   uncertain semantic entry point (U5 / NM-1);
3. V2 eligibility sends the candidate to Semantic V2;
4. the V2 input carries the corrected structured evidence contract:
   the RAW candidate title reaches the model as labeled raw observation
   text; truly structured candidate product facts are present ONLY where
   the extraction layer actually produced them (the main-flow extractor
   produces none of family / capacity / interface / form factor, so
   those dimensions are explicit absences — NOT structured evidence
   derived from title tokens); the packaging / sales-unit channel is
   explicitly present (OBSERVED) or explicitly absent (UNAVAILABLE — the
   fixture's only candidate commercial fact is a price, and a price is
   never a packaging observation), and that absence is rendered with the
   never-infer rule, not silently interpreted as equivalence; the
   reviewed manufacturer target context (the ESTABLISHED 4D-D alias
   acquisition) is carried target-side with zero identity authority;
5. CUSTOMER_RETRIEVAL_RELATION alone establishes no identity authority;
6. without reviewed manufacturer relationship authority the frozen
   relationship ceiling applies exactly as S2-A defines it;
7. no Machine Price contamination occurs.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import (
    EvidenceDecision,
    ResearchRunState,
)
from product_intelligence.research.micron_packaging_alias import (
    MICRON_7500_REQUESTED_CATALOG_URL,
)
from product_intelligence.research import (
    IdentityRelationshipSignal,
    IdentityStateV2,
    UncertainSubstateV2,
    AuthorityTier,
    ContextProvenance,
    PackagingEvidenceStateV2,
    RelationshipAuthority,
    RelationshipRequirement,
    TargetIdentifierRelationKindV2,
    V2Confidence,
    V2SemanticDecision,
    assess_listing_identity,
    derive_authority_tier,
    derive_identity_state_v2,
    derive_relationship_authority,
    is_v2_semantic_eligible,
    normalize_listing_observation,
    substate_relationship_requirement,
)
from product_intelligence.research.listings import (
    ExtractionMethod,
    ListingObservation,
)
from product_intelligence.research.semantic_decision_v2 import (
    SemanticDecisionRecordV2,
)
from product_intelligence.research.semantic_v2 import (
    SemanticReasonCodeV2,
    build_semantic_match_case_v2,
    build_v2_product_evidence_profile,
)
from product_intelligence.runs.models import (
    AiAssistedReviewCandidate,
    ResearchRun,
    SemanticDecisionRecord as SemanticDecisionRecordRow,
)
from product_intelligence.execution.semantic_decision_persistence import (
    load_semantic_decision,
)
from product_intelligence.execution.semantic_decision_v2_execution import (
    build_semantic_decision_records_v2,
    evaluate_semantic_matches_v2,
    persist_semantic_decision_records_v2,
)
from product_intelligence.research import aggregate_listing_prices
from product_intelligence.semantic.contract_v2 import build_semantic_prompt_v2
from product_intelligence.semantic.runtime_v2 import (
    PRIMARY_MODEL_V2,
    FALLBACK_MODEL_V2,
    SemanticRuntimeV2,
)
from product_intelligence.semantic.transport import FakeSemanticModelTransport

REQUESTED_MPN = "MTFDKCC3T8TGP-1BK1DABYYR"
CANDIDATE_MPN = "MTFDKCC3T8TGP-1BK1DABYY"
DESCRIPTION = "Micron 7500 PRO 3840GB U.3 15mm SSD"
REQUEST = ResearchRequest(REQUESTED_MPN, DESCRIPTION)
CUSTOMER_CTX = frozenset({ContextProvenance.CUSTOMER_RETRIEVAL_RELATION})
RELATION_CTX = frozenset({ContextProvenance.MANUFACTURER_RELATION_AUTHORITY})


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    SemanticDecisionRecordRow.objects.all().delete()
    AiAssistedReviewCandidate.objects.all().delete()
    from product_intelligence.runs.models import (
        PriceIntelligenceSnapshot,
    )

    PriceIntelligenceSnapshot.objects.all().delete()
    ResearchRun.objects.all().delete()


def _candidate_observation(title=None, price="2000"):
    return ListingObservation(
        source_url="https://example.com/7500-pro",
        extraction_method=ExtractionMethod.JSON_LD,
        product_title=title
        or "Micron 7500 PRO 3840GB U.3 15mm SSD " + CANDIDATE_MPN,
        brand_text=None,
        manufacturer_part_number_text=CANDIDATE_MPN,
        sku_text=None,
        price_text=price,
        currency_text="USD",
        availability_text="In stock",
        condition_text="New",
        seller_text=None,
    )


def _assessment(observation=None):
    observation = observation or _candidate_observation()
    return assess_listing_identity(
        REQUEST, normalize_listing_observation(observation)
    )


def _v2_match_response() -> str:
    return json.dumps(
        {
            "decision": "MATCH",
            "confidence": "HIGH",
            "reason_code": "MATCH_EXACT_PRODUCT_CONTEXT",
            "matched_attributes": [
                {"dimension": "PRODUCT_FAMILY", "detail": "7500 PRO"},
                {"dimension": "CAPACITY", "detail": "3840GB"},
                {"dimension": "INTERFACE", "detail": "U.3"},
                {"dimension": "FORM_FACTOR", "detail": "15mm"},
            ],
            "conflicting_attributes": [
                {
                    "dimension": "REVISION_OR_SUFFIX",
                    "detail": "requested suffix R not observed",
                }
            ],
            "missing_critical_attributes": [],
            "conflict_classes": [],
        }
    )


def _v2_runtime(response: str = _v2_match_response()) -> SemanticRuntimeV2:
    return SemanticRuntimeV2(
        primary_transport=FakeSemanticModelTransport(
            responses={"UNKNOWN": response},
            case_ids=("UNKNOWN",),
            provider_reported_model=PRIMARY_MODEL_V2,
        ),
        fallback_transport=FakeSemanticModelTransport(
            responses={"UNKNOWN": response},
            case_ids=("UNKNOWN",),
            provider_reported_model=FALLBACK_MODEL_V2,
        ),
    )


# ===========================================================================
# 1-3. Deterministic layer, near-miss classification, V2 entry point
# ===========================================================================


class TestDeterministicLayerAndEntry:
    def test_the_deterministic_layer_does_not_machine_verify(self) -> None:
        assessment = _assessment()
        # Frozen 3C: explicit MPN mismatch (not established, not the
        # narrow PARTIAL boundary — the truncation ends mid-token).
        assert assessment.decision is EvidenceDecision.REJECTED
        assert assessment.match_type.value != "EXACT"
        assert assessment.match_type.value != "NORMALIZED_EXACT"
        # The Machine Verified tier is deterministic-only: with no
        # semantic outcome, the frozen S2-A derivation is NEEDS_REVIEW
        # (uncertain), never MACHINE_VERIFIED.
        context = derive_identity_state_v2(assessment)
        no_outcome = derive_authority_tier(context)
        assert no_outcome.tier is not AuthorityTier.MACHINE_VERIFIED
        assert context.state is IdentityStateV2.DETERMINISTIC_UNCERTAIN

    def test_the_bounded_near_miss_logic_classifies_u5_nm1(self) -> None:
        context = derive_identity_state_v2(_assessment())
        assert context.substate is UncertainSubstateV2.U5_NEAR_MISS_MPN
        assert context.primary_relationship_signal is (
            IdentityRelationshipSignal.NEAR_MISS_TRUNCATION
        )
        # The frozen near-miss predicates (no Levenshtein, no arbitrary
        # substring authority): strict prefix on the frozen normalized
        # keys, either direction.
        from product_intelligence.research import (
            is_near_miss_truncation,
            is_near_miss_substitution,
            near_miss_shape,
            NearMissShape,
        )

        assert is_near_miss_truncation(
            context.normalized_requested_part_number,
            context.normalized_candidate_part_number,
        )
        assert not is_near_miss_substitution(
            context.normalized_requested_part_number,
            context.normalized_candidate_part_number,
        )
        assert near_miss_shape(
            context.normalized_requested_part_number,
            context.normalized_candidate_part_number,
        ) is NearMissShape.NM1_TRUNCATION

    def test_v2_eligibility_sends_the_candidate_to_semantic_v2(self) -> None:
        assert is_v2_semantic_eligible(_assessment()) is True


# ===========================================================================
# 4. The V2 input carries enough structured context
# ===========================================================================


class TestV2InputRichness:
    def test_the_input_carries_the_corrected_evidence_contract(self) -> None:
        # S2-C-FU1 CORRECTION of the pre-FU1 test that claimed
        # "structured family/capacity/interface/form factor" merely
        # because those tokens occur in the candidate TITLE string. That
        # claim was flawed: token occurrence in raw title text is not
        # structured evidence. This test now proves accurately:
        #
        # A. the RAW candidate title evidence is available to the model
        #    (labeled raw observation text);
        # B. truly structured candidate product facts are present only
        #    where the extraction layer actually produced them — the
        #    main-flow extractor produces none of family / capacity /
        #    interface / form factor, so those dimensions are explicit
        #    absences despite the title tokens;
        # C. packaging / sales-unit evidence is explicitly absent
        #    (UNAVAILABLE): the fixture's only candidate commercial fact
        #    is a price, and a price is never a packaging observation;
        # D. that absence is rendered as an explicit recorded absence
        #    with the never-infer rule — not silently interpreted as
        #    equivalence.
        #
        # (E. customer relation retrieval-only, F. the U5/NM-1 ceiling,
        # and G. no Machine Price contamination are proven by the
        # adjacent test classes, unchanged.)
        assessment = _assessment()
        context = derive_identity_state_v2(assessment)
        profile = build_v2_product_evidence_profile(
            observation=assessment.normalized_listing.observation,
            context_provenances=CUSTOMER_CTX,
            matched_facts=frozenset(),
        )
        case = build_semantic_match_case_v2(
            case_id="candidate-motivating-0",
            request=REQUEST,
            assessment=assessment,
            context=context,
            product_evidence=profile,
            context_provenances=CUSTOMER_CTX,
            reviewed_target_context=None,
        )
        prompt = build_semantic_prompt_v2(case)

        # A. The raw candidate title evidence reaches the model, labeled
        #    as RAW observation text (not as structured evidence).
        assert (
            '- Listing title: "Micron 7500 PRO 3840GB U.3 15mm SSD '
            + CANDIDATE_MPN + '"'
        ) in prompt.user_prompt
        assert "Raw observation text" in prompt.user_prompt

        # B. The truly structured candidate product facts are exactly
        #    what the extraction layer produced: NONE of the
        #    family/capacity/interface/form-factor dimensions is
        #    structured evidence merely because its token occurs in the
        #    title. The published title is the raw channel; the
        #    dimensions are explicit absences.
        product = case.candidate_product
        assert product.raw_title_text == (
            "Micron 7500 PRO 3840GB U.3 15mm SSD " + CANDIDATE_MPN
        )
        assert product.product_family is None
        assert product.generation is None
        assert product.capacity is None
        assert product.interface is None
        assert product.form_factor is None
        assert product.product_role is None
        assert product.accessory_relation is None
        assert product.brand is None
        assert product.revision_or_suffix is None
        assert product.raw_specification_text is None
        for dimension in (
            "product_family",
            "capacity",
            "interface",
            "form_factor",
        ):
            assert f"- {dimension}: (none)" in prompt.user_prompt

        # C. Packaging / sales-unit evidence is explicitly ABSENT: the
        #    candidate commercial facts are price / currency /
        #    availability / condition only, and the sales-unit channel
        #    records the explicit UNAVAILABLE state (never inferred from
        #    the price).
        commercial = case.candidate_commercial
        assert commercial.price.value == "2000"
        assert commercial.currency.value == "USD"
        assert commercial.sales_unit.state is PackagingEvidenceStateV2.UNAVAILABLE
        assert commercial.sales_unit.kind is None
        assert commercial.sales_unit.quantity is None
        assert "- Sales unit / packaging: UNAVAILABLE" in prompt.user_prompt

        # D. Absence is not silently interpreted as equivalence: the
        #    recorded absence renders with the never-infer rule.
        assert "absence is NOT proof of equal sales unit" in prompt.user_prompt
        assert "do not infer a single unit" in prompt.user_prompt

        # The normalized near-miss keys are explicit (unchanged).
        assert REQUESTED_MPN in prompt.user_prompt
        assert CANDIDATE_MPN in prompt.user_prompt
        assert "NEAR_MISS_TRUNCATION" in prompt.user_prompt
        # Commercial evidence is labeled never-identity (unchanged).
        assert "NEVER identity evidence" in prompt.user_prompt
        # The sales-unit distinction is part of the frozen prompt
        # (unchanged).
        assert "PACKAGING_QUANTITY" in prompt.system_prompt

    def test_relationship_provenance_is_carried_and_labeled(self) -> None:
        assessment = _assessment()
        context = derive_identity_state_v2(assessment)
        profile = build_v2_product_evidence_profile(
            observation=assessment.normalized_listing.observation,
            context_provenances=CUSTOMER_CTX,
            matched_facts=frozenset(),
        )
        case = build_semantic_match_case_v2(
            case_id="candidate-motivating-0",
            request=REQUEST,
            assessment=assessment,
            context=context,
            product_evidence=profile,
            context_provenances=CUSTOMER_CTX,
            reviewed_target_context=None,
        )
        prompt = build_semantic_prompt_v2(case)
        assert "CUSTOMER_RETRIEVAL_RELATION" in prompt.user_prompt
        assert "retrieval hint" in prompt.user_prompt
        assert "NOT manufacturer equivalence" in prompt.user_prompt


# ===========================================================================
# 5-6. Customer relation alone: no authority; the frozen ceiling applies
# ===========================================================================


class TestCustomerRelationAndCeiling:
    def test_customer_relation_alone_establishes_no_identity(self) -> None:
        context = derive_identity_state_v2(_assessment())
        # Dimension B: customer retrieval confers ZERO relationship
        # authority (the frozen S2-A rule).
        assert derive_relationship_authority(context, CUSTOMER_CTX) is (
            RelationshipAuthority.NOT_ESTABLISHED
        )
        assert derive_relationship_authority(context, frozenset()) is (
            RelationshipAuthority.NOT_ESTABLISHED
        )

    def test_the_frozen_u5_nm1_requirement_caps_match_high_strong(self) -> None:
        # U5 / NM-1 requires reviewed relationship authority (the
        # frozen S2-A-FU2 table). Even a V2 MATCH + HIGH with STRONG
        # bounded product evidence is capped at NEEDS_REVIEW without it.
        from product_intelligence.research import (
            CandidateProductEvidenceSource,
            ProductEvidenceDimension,
            ProductEvidenceFactV2,
            ProductEvidenceProfileV2,
            SemanticEvaluationV2,
        )

        context = derive_identity_state_v2(_assessment())
        assert substate_relationship_requirement(
            context.substate, context.primary_relationship_signal
        ) is RelationshipRequirement.REVIEWED_RELATION_AUTHORITY_REQUIRED

        strong_profile = ProductEvidenceProfileV2(
            has_usable_product_title=True,
            matched_facts=frozenset(
                {
                    ProductEvidenceFactV2(
                        ProductEvidenceDimension.PRODUCT_FAMILY,
                        frozenset(
                            {CandidateProductEvidenceSource.LISTING_PRODUCT_TITLE}
                        ),
                    ),
                    ProductEvidenceFactV2(
                        ProductEvidenceDimension.CAPACITY,
                        frozenset(
                            {CandidateProductEvidenceSource.LISTING_PRODUCT_TITLE}
                        ),
                    ),
                }
            ),
        )
        match_high = SemanticEvaluationV2.evaluated(
            V2SemanticDecision.MATCH, V2Confidence.HIGH, frozenset()
        )
        # Without reviewed relationship authority: capped.
        without = derive_authority_tier(
            context, match_high, CUSTOMER_CTX, strong_profile
        )
        assert without.tier is AuthorityTier.NEEDS_REVIEW
        # With reviewed manufacturer relationship authority: the
        # requirement is met (capability, under the frozen contract).
        with_relation = derive_authority_tier(
            context, match_high, RELATION_CTX, strong_profile
        )
        assert with_relation.tier is AuthorityTier.AI_ASSISTED_COMPARABLE

    def test_the_recorded_derived_snapshots_show_the_ceiling(self) -> None:
        # End-to-end: the persisted V2 record for the motivating case
        # (customer relation only, V2 MATCH/HIGH) carries the derived
        # NOT_ESTABLISHED / NEEDS_REVIEW snapshots — the frozen ceiling
        # applied exactly as S2-A defines it.
        assessment = _assessment()
        run = ResearchRun.objects.create_from_request(REQUEST)
        outcomes = evaluate_semantic_matches_v2(
            REQUEST,
            (assessment,),
            context_provenances_by_assessment={assessment: CUSTOMER_CTX},
            reviewed_target_context=None,
            runtime_v2=_v2_runtime(),
        )
        assert len(outcomes) == 1
        published = aggregate_listing_prices(REQUEST, (assessment,)).assessments
        records = build_semantic_decision_records_v2(run, published, outcomes)
        assert records[0].relationship_authority is (
            RelationshipAuthority.NOT_ESTABLISHED
        )
        assert records[0].authority_tier is AuthorityTier.NEEDS_REVIEW
        persist_semantic_decision_records_v2(run, records)
        loaded = load_semantic_decision(run.id, 0)
        assert isinstance(loaded, SemanticDecisionRecordV2)
        assert loaded.decision is V2SemanticDecision.MATCH
        assert loaded.confidence is V2Confidence.HIGH
        assert loaded.relationship_authority is (
            RelationshipAuthority.NOT_ESTABLISHED
        )
        assert loaded.authority_tier is AuthorityTier.NEEDS_REVIEW


# ===========================================================================
# 7. No Machine Price contamination (full orchestration)
# ===========================================================================


class TestNoMachinePriceContamination:
    def _json_ld_page(self, payload):
        text = json.dumps(payload)
        return (
            f'<html><body><script type="application/ld+json">{text}'
            "</script></body></html>"
        )

    def _catalog_body(self) -> str:
        # The reviewed 4D-D recorded catalog fixture (the motivating
        # request MPN is a reviewed 7500-family R form: the 4D-D alias
        # acquisition runs on this request and must be served).
        fixtures = Path(__file__).resolve().parents[1] / "fixtures" / "pages"
        return (fixtures / "micron_7500_part_catalog.json").read_text(
            encoding="utf-8"
        )

    def _execute_motivating_run(self) -> None:
        from product_intelligence.execution import execute_research_run
        from product_intelligence.providers.search import SearchProvider

        url_exact = "https://example.com/exact"
        url_near = "https://example.com/near-miss"
        pages = {
            MICRON_7500_REQUESTED_CATALOG_URL: self._catalog_body(),
            url_exact: self._json_ld_page(
                {
                    "@type": "Product",
                    "name": "Micron 7500 PRO 3840GB U.3 15mm SSD",
                    "mpn": REQUESTED_MPN,
                    "offers": {
                        "@type": "Offer",
                        "price": "1000",
                        "priceCurrency": "USD",
                        "itemCondition": "https://schema.org/NewCondition",
                    },
                }
            ),
            url_near: self._json_ld_page(
                {
                    "@type": "Product",
                    "name": "Micron 7500 PRO 3840GB U.3 15mm SSD",
                    "mpn": CANDIDATE_MPN,
                    "offers": {
                        "@type": "Offer",
                        "price": "1500",
                        "priceCurrency": "USD",
                        "itemCondition": "https://schema.org/NewCondition",
                    },
                }
            ),
        }
        search_provider = MagicMock(spec=SearchProvider)

        results = []
        for url in pages:
            result = MagicMock()
            result.source_url = url
            result.title = "Product"
            result.snippet = "Description"
            result.price_hint_text = None
            result.part_number_hint = None
            result.raw_reference = None
            results.append(result)
        from product_intelligence.providers.search import SearchQuery

        response = MagicMock()
        response.provider_id = "test"
        response.query = MagicMock(spec=SearchQuery)
        response.retrieved_at = datetime.now(tz=timezone.utc)
        response.results = tuple(results)
        response.raw_response_reference = None
        search_provider.search.return_value = response

        page_fetcher = MagicMock()

        def _fetch(request):
            from product_intelligence.providers.page import FetchedPage

            body = pages[request.url]
            return FetchedPage(
                requested_url=request.url,
                final_url=request.url,
                retrieved_at=datetime.now(tz=timezone.utc),
                status_code=200,
                body_text=body,
                content_type=(
                    "application/json"
                    if request.url == MICRON_7500_REQUESTED_CATALOG_URL
                    else "text/html"
                ),
                body_byte_count=len(body),
                redirect_count=0,
                fetcher_id="test",
            )

        page_fetcher.fetch.side_effect = _fetch

        run = ResearchRun.objects.create_from_request(REQUEST)
        with patch(
            "product_intelligence.execution.semantic_integration."
            "get_default_runtime",
            side_effect=AssertionError(
                "the V1 path must never be called for this U5 candidate"
            ),
        ), patch(
            "product_intelligence.execution.semantic_decision_v2_execution."
            "get_default_runtime_v2",
            side_effect=[_v2_runtime()],
        ):
            return execute_research_run(
                str(run.id),
                search_provider=search_provider,
                page_fetcher=page_fetcher,
            )

    def test_machine_price_is_deterministic_only(self) -> None:
        result = self._execute_motivating_run()
        assert result.run.current_state == ResearchRunState.COMPLETED
        assert result.snapshot is not None
        buckets = result.snapshot.payload.get("buckets", [])
        # The Machine Price surface contains ONLY the deterministic
        # ACCEPTED listing (1000). The near-miss candidate (1500) —
        # even with a V2 MATCH/HIGH — never enters a 4A bucket.
        assert len(buckets) == 1
        assert str(buckets[0]["low"]) == "1000"
        assert str(buckets[0]["median"]) == "1000"
        assert str(buckets[0]["high"]) == "1000"
        all_prices = [
            str(b.get(k, ""))
            for b in buckets
            for k in ("low", "median", "high", "market_range_low", "market_range_high")
        ]
        assert "1500" not in all_prices
        # No review candidate (V2 persists only; V1 was never called).
        assert AiAssistedReviewCandidate.objects.filter(
            run=result.run
        ).count() == 0
        # The V2 record for the near-miss candidate persisted with the
        # deterministic uncertain context. The candidate was retrieved
        # through the ESTABLISHED 4D-D alias-expanded search (the
        # motivating case): the recorded V2 input carries the customer
        # retrieval relation — and the derived snapshot shows it
        # established nothing (zero identity authority).
        records = list(SemanticDecisionRecordRow.objects.filter(run=result.run))
        assert len(records) == 1
        loaded = load_semantic_decision(result.run.id, records[0].assessment_index)
        assert isinstance(loaded, SemanticDecisionRecordV2)
        assert loaded.decision is V2SemanticDecision.MATCH
        assert loaded.case.substate.value == "U5_NEAR_MISS_MPN"
        assert loaded.case.context_provenances == frozenset(
            {ContextProvenance.CUSTOMER_RETRIEVAL_RELATION}
        )
        assert loaded.relationship_authority is RelationshipAuthority.NOT_ESTABLISHED
        assert loaded.authority_tier is AuthorityTier.NEEDS_REVIEW
        # Machine Verified remains deterministic only: the run's
        # verification status reflects the single deterministic bucket.
        assert result.price_buckets == 1

    def test_the_recorded_input_carries_the_reviewed_target_context(self) -> None:
        # S2-C-FU1: in the full motivating run the ESTABLISHED 4D-D alias
        # acquisition carries the reviewed manufacturer TARGET context
        # into the recorded V2 input — structured/reviewed, target-side
        # only, zero identity authority (the relation kind is bounded to
        # customer retrieval). The candidate-side packaging channel
        # remains explicitly UNAVAILABLE: the reviewed catalog's box
        # quantity is not carried into the main flow's candidate
        # evidence, and the candidate listing publishes no packaging
        # field (the only candidate commercial fact is a price).
        result = self._execute_motivating_run()
        records = list(SemanticDecisionRecordRow.objects.filter(run=result.run))
        assert len(records) == 1
        loaded = load_semantic_decision(result.run.id, records[0].assessment_index)
        assert isinstance(loaded, SemanticDecisionRecordV2)
        reviewed = loaded.case.target.reviewed_context
        assert reviewed is not None
        assert reviewed.manufacturer == "Micron"
        assert reviewed.category == "SSD"
        # The exact source-published base part number (the R-suffix form
        # requested; the base is what the catalog row proves).
        assert reviewed.matched_base_part_number == CANDIDATE_MPN
        assert reviewed.relation_kind is (
            TargetIdentifierRelationKindV2.CUSTOMER_RETRIEVAL_ALIAS
        )
        assert reviewed.relation_family_part_numbers == (
            CANDIDATE_MPN,
            CANDIDATE_MPN + "T",
        )
        assert reviewed.source_name == "Micron 7500 SSD catalog"
        assert reviewed.source_url == MICRON_7500_REQUESTED_CATALOG_URL
        assert reviewed.evidence_body_sha256  # 64-hex digest carried
        # The reviewed context grants nothing: the derived snapshots are
        # unchanged (customer retrieval only, frozen ceiling).
        assert loaded.relationship_authority is RelationshipAuthority.NOT_ESTABLISHED
        assert loaded.authority_tier is AuthorityTier.NEEDS_REVIEW
        # Candidate-side packaging stays explicitly UNAVAILABLE.
        assert (
            loaded.case.candidate_commercial.sales_unit.state
            is PackagingEvidenceStateV2.UNAVAILABLE
        )
        # The raw candidate title reaches the model; no product-dimension
        # fact is derived from its tokens.
        assert loaded.case.candidate_product.raw_title_text is not None
        assert loaded.case.candidate_product.capacity is None
        assert loaded.case.candidate_product.form_factor is None
