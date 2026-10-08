"""S2-C-FU1 — INPUT EVIDENCE FIDELITY (corrected Semantic V2 input).

The pre-freeze S2-C candidate's "FINAL" V2 input did not provide the
structured product / commercial evidence the product goal requires:
``candidate_specs`` was always None, the commercial context was a composed
free-text blob (price / availability / seller / offer), no packaging /
sales-unit channel existed, and the motivating test claimed
family / capacity / interface / form factor were "structured" merely
because the tokens occur in the candidate TITLE.

This file proves the corrected contract (task-mandated properties):

 1. the final V2 input distinguishes structured evidence from raw
    observation text;
 2. candidate structured product evidence is typed / bounded;
 3. commercial / packaging evidence is typed / bounded;
 4. unknown values remain absent, not guessed;
 5. raw title / spec text can reach the model without granting authority;
 6. model matched_attributes cannot become ProductEvidenceFactV2;
 7. model conflict output cannot mutate input evidence;
 8. independently grounded ProductEvidenceFactV2 can still reach STRONG
    under the frozen S2-A rules;
 9. ungrounded / raw text alone cannot reach STRONG;
10. packaging single-unit evidence round-trips if actually observed;
11. pack-quantity evidence round-trips if actually observed;
12. bundle evidence round-trips if actually observed;
13. absent packaging is explicitly absent and is not treated as equal;
14. the motivating Micron fixture no longer claims structured evidence
    merely because tokens exist in the title;
15. the Micron candidate still reaches V2;
16. the Micron relationship ceiling is unchanged;
17. no Machine Price contamination (the V2 wiring owns no path to pricing
    authority — source-level firewall);
18. V2 persistence / replay round-trips the corrected input exactly;
19. V1 replay is unchanged;
20. the Qualification boundary remains False.

Plus the reviewed TARGET context contract (structured / reviewed,
target-side only, zero identity authority) and the 4D-D acquisition
helper that builds it.
"""

from __future__ import annotations

import dataclasses
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.research import (
    AuthorityTier,
    CandidateEvidenceSourceV2,
    CandidateObservationFactV2,
    CandidateProductDimensionV2,
    CandidateProductEvidenceV2,
    CandidateSalesUnitEvidenceV2,
    ContextProvenance,
    ExtractionMethod,
    IdentityStateV2,
    ListingObservation,
    PackagingEvidenceStateV2,
    ProductEvidenceDimension,
    ProductEvidenceFactV2,
    ProductEvidenceProfileV2,
    ProductEvidenceQuality,
    ReviewedTargetContextV2,
    SALES_UNIT_EVIDENCE_UNAVAILABLE,
    SalesUnitKindV2,
    TargetEvidenceV2,
    TargetIdentifierRelationKindV2,
    UncertainSubstateV2,
    assess_listing_identity,
    build_candidate_commercial_evidence_v2,
    build_candidate_product_evidence_v2,
    build_semantic_match_case_v2,
    build_v2_product_evidence_profile,
    derive_authority_tier,
    derive_identity_state_v2,
    derive_product_evidence_quality,
    derive_relationship_authority,
    is_v2_semantic_eligible,
    normalize_listing_observation,
    RelationshipAuthority,
    SemanticEvaluationV2,
    V2Confidence,
    V2SemanticDecision,
)
from product_intelligence.research.micron_packaging_alias import (
    MICRON_7500_CATEGORY,
    MICRON_7500_MANUFACTURER,
    MICRON_7500_POLICY_ID,
    MICRON_7500_REQUESTED_CATALOG_URL,
    MICRON_7500_SOURCE_NAME,
    MicronAliasEligibilityResult,
    MicronAliasEligibilityStatus,
    MicronSsdCategoryEvidence,
    build_packaging_alias_relation,
    extract_micron_7500_catalog_records,
    matched_ssd_category_evidence,
)
from product_intelligence.research.identity import compare_part_numbers
from product_intelligence.research.semantic_decision_v2 import (
    V2_AUTHORITY_QUALIFIED,
    V2_CONTRACT_BINDING,
    encode_v2_payload,
    SemanticDecisionRecordV2,
)
from product_intelligence.research.semantic_decision_codec import (
    SEMANTIC_DECISION_SCHEMA_VERSION,
    decode_semantic_decision_record,
    encode_semantic_decision_record,
)
from product_intelligence.research.semantic_decision_replay import (
    replay_semantic_decision,
)
from product_intelligence.semantic.contract_v2 import (
    SEMANTIC_PROMPT_VERSION_V2,
    build_semantic_prompt_v2,
)

# The motivating Micron-shape near-miss (generic identifiers; the same
# fixture shape the motivating-case file uses).
REQUESTED_MPN = "MTFDKCC3T8TGP-1BK1DABYYR"
CANDIDATE_MPN = "MTFDKCC3T8TGP-1BK1DABYY"
MOTIVATING_TITLE = "Micron 7500 PRO 3840GB U.3 15mm SSD " + CANDIDATE_MPN

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "pages"
    / "micron_7500_part_catalog.json"
)
FIXED_AT = datetime(2026, 9, 22, 23, 20, 25, tzinfo=timezone.utc)
NO_CTX = frozenset()
CUSTOMER_CTX = frozenset({ContextProvenance.CUSTOMER_RETRIEVAL_RELATION})
RELATION_CTX = frozenset({ContextProvenance.MANUFACTURER_RELATION_AUTHORITY})


# ---------------------------------------------------------------------------
# Helpers (the real frozen 3C chain)
# ---------------------------------------------------------------------------


def _observation(
    title: str | None = MOTIVATING_TITLE,
    *,
    mpn: str | None = CANDIDATE_MPN,
    brand: str | None = None,
    condition: str | None = None,
    price: str | None = "2000",
    currency: str | None = "USD",
    availability: str | None = "In stock",
) -> ListingObservation:
    return ListingObservation(
        source_url="https://example.com/7500-pro",
        extraction_method=ExtractionMethod.JSON_LD,
        product_title=title,
        manufacturer_part_number_text=mpn,
        sku_text=None,
        brand_text=brand,
        price_text=price,
        currency_text=currency,
        availability_text=availability,
        condition_text=condition,
        seller_text=None,
    )


def _request():
    return ResearchRequest(REQUESTED_MPN, "Micron 7500 PRO 3840GB U.3 15mm SSD")


def _assessment(observation=None):
    observation = observation or _observation()
    return assess_listing_identity(
        _request(), normalize_listing_observation(observation)
    )


def _case(
    observation=None,
    *,
    provenances=NO_CTX,
    facts=frozenset(),
    reviewed_target_context=None,
):
    request = _request()
    assessment = _assessment(observation)
    context = derive_identity_state_v2(assessment)
    profile = build_v2_product_evidence_profile(
        observation=assessment.normalized_listing.observation,
        context_provenances=provenances,
        matched_facts=facts,
    )
    return build_semantic_match_case_v2(
        case_id="candidate-fu1-0",
        request=request,
        assessment=assessment,
        context=context,
        product_evidence=profile,
        context_provenances=provenances,
        reviewed_target_context=reviewed_target_context,
    )


def _observed_sales_unit(kind, quantity=None, raw_detail="observed"):
    return CandidateSalesUnitEvidenceV2(
        state=PackagingEvidenceStateV2.OBSERVED,
        kind=kind,
        quantity=quantity,
        raw_detail=raw_detail,
        source=CandidateEvidenceSourceV2.PUBLISHED_STRUCTURED_FIELD,
    )


def _case_with_sales_unit(sales_unit):
    case = _case()
    return dataclasses.replace(
        case,
        candidate_commercial=dataclasses.replace(
            case.candidate_commercial, sales_unit=sales_unit
        ),
    )


def _established_alias_result() -> MicronAliasEligibilityResult:
    """A valid ESTABLISHED 4D-D result built from the real recorded
    catalog fixture (the same construction the 4D-D contract tests use)."""
    body = FIXTURE.read_text(encoding="utf-8")
    records = extract_micron_7500_catalog_records(body)
    record = next(r for r in records if r.part_number == CANDIDATE_MPN)
    match = compare_part_numbers(CANDIDATE_MPN, CANDIDATE_MPN)
    relation = build_packaging_alias_relation(REQUESTED_MPN, CANDIDATE_MPN)
    evidence = matched_ssd_category_evidence(record)
    return MicronAliasEligibilityResult(
        status=MicronAliasEligibilityStatus.ESTABLISHED,
        request=_request(),
        lookup_base_candidate=CANDIDATE_MPN,
        policy_id=MICRON_7500_POLICY_ID,
        manufacturer=MICRON_7500_MANUFACTURER,
        category=MICRON_7500_CATEGORY,
        requested_source_url=MICRON_7500_REQUESTED_CATALOG_URL,
        fetched_final_url=MICRON_7500_REQUESTED_CATALOG_URL,
        retrieved_at=FIXED_AT,
        source_name=MICRON_7500_SOURCE_NAME,
        matched_base_mpn=CANDIDATE_MPN,
        part_number_match=match,
        ssd_category_evidence=MicronSsdCategoryEvidence(
            attr_name=evidence.name, attr_id=evidence.attr_id, attr_value=True
        ),
        alias_relation=relation,
        body_sha256=hashlib.sha256(body.encode("utf-8")).hexdigest(),
    )


# ===========================================================================
# 1-5. Structured vs raw; typed/bounded; unknown stays absent
# ===========================================================================


class TestStructuredVsRawDistinction:
    def test_final_input_distinguishes_structured_from_raw_observation(self) -> None:
        # 1. The same text is carried TWICE with different classes when it
        # is both a published field and the title: the title is RAW
        # observation text; only the extractor's published fields become
        # structured facts (brand here).
        observation = _observation(brand="Micron", condition="New")
        case = _case(observation)
        product = case.candidate_product
        assert product.brand == CandidateObservationFactV2(
            value="Micron",
            source=CandidateEvidenceSourceV2.PUBLISHED_STRUCTURED_FIELD,
        )
        assert product.raw_title_text == MOTIVATING_TITLE
        prompt = build_semantic_prompt_v2(case)
        # The structured fact renders with its source label ...
        assert '- brand: "Micron" [published structured field]' in prompt.user_prompt
        # ... and the title renders ONLY under the raw-observation label.
        assert f'- Listing title: "{MOTIVATING_TITLE}"' in prompt.user_prompt
        assert "Raw observation text" in prompt.user_prompt
        assert "NOT structured evidence" in prompt.user_prompt
        # The authority section is distinct from both.
        assert "authority-side" in prompt.user_prompt

    def test_candidate_structured_product_evidence_is_typed_bounded(self) -> None:
        # 2. The nine bounded dimensions are the only structured
        # product-evidence positions (typed facts or explicit absence);
        # the dimension vocabulary is bounded and mirrors the model's
        # observation dimensions' product half.
        assert {d.value for d in CandidateProductDimensionV2} == {
            "PRODUCT_FAMILY",
            "GENERATION",
            "CAPACITY",
            "INTERFACE",
            "FORM_FACTOR",
            "PRODUCT_ROLE",
            "ACCESSORY_RELATION",
            "BRAND",
            "REVISION_OR_SUFFIX",
        }
        case = _case()
        product = case.candidate_product
        for name in (
            "product_family",
            "generation",
            "capacity",
            "interface",
            "form_factor",
            "product_role",
            "accessory_relation",
            "brand",
            "revision_or_suffix",
        ):
            value = getattr(product, name)
            assert value is None or isinstance(value, CandidateObservationFactV2), (
                name
            )
        # A fact with an unknown source or an empty value fails closed.
        with pytest.raises(ValueError):
            CandidateObservationFactV2(
                value="",
                source=CandidateEvidenceSourceV2.PUBLISHED_STRUCTURED_FIELD,
            )
        with pytest.raises(TypeError):
            CandidateObservationFactV2(  # type: ignore[arg-type]
                value="x", source="MODEL_CLAIM"
            )
        # A dimension slot that is neither a fact nor None fails closed.
        with pytest.raises(TypeError):
            CandidateProductEvidenceV2(  # type: ignore[arg-type]
                product_family="3840GB",
                generation=None,
                capacity=None,
                interface=None,
                form_factor=None,
                product_role=None,
                accessory_relation=None,
                brand=None,
                revision_or_suffix=None,
                raw_title_text=None,
                raw_specification_text=None,
            )

    def test_candidate_commercial_packaging_evidence_is_typed_bounded(self) -> None:
        # 3. Commercial fields are typed facts; the sales-unit channel is
        # a bounded object with an explicit state (never a free-text blob).
        case = _case(_observation(condition="New"))
        commercial = case.candidate_commercial
        assert commercial.condition == CandidateObservationFactV2(
            value="New",
            source=CandidateEvidenceSourceV2.PUBLISHED_STRUCTURED_FIELD,
        )
        assert isinstance(commercial.sales_unit, CandidateSalesUnitEvidenceV2)
        assert commercial.sales_unit.state is PackagingEvidenceStateV2.UNAVAILABLE
        # The bounded kinds are exactly the required four.
        assert {k.value for k in SalesUnitKindV2} == {
            "SINGLE_UNIT",
            "PACK_QUANTITY",
            "TRAY_OR_FACTORY_PACK",
            "BUNDLE",
        }
        # Invalid channel states fail closed at construction.
        with pytest.raises(ValueError):
            CandidateSalesUnitEvidenceV2(
                state=PackagingEvidenceStateV2.UNAVAILABLE,
                kind=SalesUnitKindV2.SINGLE_UNIT,
                quantity=None,
                raw_detail=None,
                source=None,
            )
        with pytest.raises(ValueError):
            CandidateSalesUnitEvidenceV2(
                state=PackagingEvidenceStateV2.OBSERVED,
                kind=SalesUnitKindV2.PACK_QUANTITY,
                quantity=None,
                raw_detail="2-pack",
                source=CandidateEvidenceSourceV2.PUBLISHED_STRUCTURED_FIELD,
            )
        with pytest.raises(ValueError):
            CandidateSalesUnitEvidenceV2(
                state=PackagingEvidenceStateV2.OBSERVED,
                kind=SalesUnitKindV2.SINGLE_UNIT,
                quantity=1,
                raw_detail="1 each",
                source=CandidateEvidenceSourceV2.PUBLISHED_STRUCTURED_FIELD,
            )
        with pytest.raises(ValueError):
            CandidateSalesUnitEvidenceV2(
                state=PackagingEvidenceStateV2.OBSERVED,
                kind=SalesUnitKindV2.BUNDLE,
                quantity=0,
                raw_detail="bundle",
                source=CandidateEvidenceSourceV2.PUBLISHED_STRUCTURED_FIELD,
            )
        with pytest.raises(ValueError):
            CandidateSalesUnitEvidenceV2(
                state=PackagingEvidenceStateV2.OBSERVED,
                kind=SalesUnitKindV2.BUNDLE,
                quantity=True,  # type: ignore[arg-type]
                raw_detail="bundle",
                source=CandidateEvidenceSourceV2.PUBLISHED_STRUCTURED_FIELD,
            )

    def test_unknown_values_remain_absent_not_guessed(self) -> None:
        # 4. An observation with only a title (no brand, no commercial
        # fields) yields ZERO structured facts and the explicit packaging
        # absence — nothing is guessed, including no "single unit".
        observation = _observation(
            title="Some product", mpn=None, brand=None, condition=None,
            price=None, currency=None, availability=None,
        )
        product = build_candidate_product_evidence_v2(observation)
        for name in (
            "product_family",
            "generation",
            "capacity",
            "interface",
            "form_factor",
            "product_role",
            "accessory_relation",
            "brand",
            "revision_or_suffix",
        ):
            assert getattr(product, name) is None
        assert product.raw_title_text == "Some product"
        assert product.raw_specification_text is None
        commercial = build_candidate_commercial_evidence_v2(observation)
        assert commercial.condition is None
        assert commercial.price is None
        assert commercial.currency is None
        assert commercial.availability is None
        assert commercial.seller is None
        assert commercial.offer_url is None
        assert commercial.sales_unit is SALES_UNIT_EVIDENCE_UNAVAILABLE

    def test_raw_title_reaches_the_model_without_granting_authority(self) -> None:
        # 5. A title full of identity-dimension tokens does not change
        # the authority-side profile: quality derives from the frozen
        # evidence bar (usable title, zero grounded facts -> LIMITED),
        # not from what the raw text contains.
        case = _case()
        assert case.candidate_product.raw_title_text == MOTIVATING_TITLE
        assert case.product_evidence.matched_facts == frozenset()
        quality = derive_product_evidence_quality(
            case.product_evidence, NO_CTX
        )
        assert quality is ProductEvidenceQuality.LIMITED
        prompt = build_semantic_prompt_v2(case)
        assert MOTIVATING_TITLE in prompt.user_prompt
        assert "- Grounded matched-attribute facts: (none)" in prompt.user_prompt


# ===========================================================================
# 6-9. The model cannot self-promote; grounded facts still reach STRONG
# ===========================================================================


class TestAuthorityBoundaryIntact:
    def test_model_matched_attributes_cannot_become_product_evidence_fact(self) -> None:
        # 6. The live builder's signature has no parameter for model
        # output: a V2 MATCH/HIGH with rich matched_attributes leaves the
        # authority-side profile (and quality) unchanged.
        import inspect

        parameters = inspect.signature(
            build_v2_product_evidence_profile
        ).parameters
        assert "matched_attributes" not in parameters
        assert "response" not in parameters
        assert "model" not in {n for n in parameters}

        case = _case()
        response = SemanticEvaluationV2.evaluated(
            V2SemanticDecision.MATCH, V2Confidence.HIGH, frozenset()
        )
        tier = derive_authority_tier(
            derive_identity_state_v2(_assessment()),
            response,
            NO_CTX,
            case.product_evidence,
        )
        assert tier.product_evidence_quality is ProductEvidenceQuality.LIMITED

    def test_model_conflict_output_cannot_mutate_input_evidence(self) -> None:
        # 7. The input case is frozen end to end: a structured NO_MATCH
        # output (conflict classes, conflicting attributes) changes the
        # RECORD's output section only — the recorded input evidence is
        # byte-identical before and after, and direct mutation fails.
        case = _case()
        before = case.canonical()
        record = _record_for(case, V2SemanticDecision.NO_MATCH)
        assert record.case.canonical() == before
        with pytest.raises(dataclasses.FrozenInstanceError):
            record.case.candidate_product = None  # type: ignore[misc]
        with pytest.raises(dataclasses.FrozenInstanceError):
            case.candidate_commercial.sales_unit = SALES_UNIT_EVIDENCE_UNAVAILABLE  # type: ignore[misc]

    def test_independently_grounded_facts_still_reach_strong(self) -> None:
        # 8. Under the FROZEN S2-A bar, independently grounded bounded
        # facts (title-grounded, two distinct hard dimensions) still
        # reach STRONG — FU1 did not move the authority side.
        from product_intelligence.research import (
            CandidateProductEvidenceSource,
        )

        grounded = frozenset(
            {
                ProductEvidenceFactV2(
                    ProductEvidenceDimension.CAPACITY,
                    frozenset({CandidateProductEvidenceSource.LISTING_PRODUCT_TITLE}),
                ),
                ProductEvidenceFactV2(
                    ProductEvidenceDimension.INTERFACE,
                    frozenset({CandidateProductEvidenceSource.LISTING_PRODUCT_TITLE}),
                ),
            }
        )
        case = _case(facts=grounded)
        assert case.product_evidence.matched_facts == grounded
        assert (
            derive_product_evidence_quality(case.product_evidence, NO_CTX)
            is ProductEvidenceQuality.STRONG
        )

    def test_raw_text_alone_cannot_reach_strong(self) -> None:
        # 9. A usable title with rich raw text but ZERO grounded facts is
        # LIMITED, never STRONG; a reviewed-context-grounded fact without
        # a grounding provenance fails closed; customer retrieval grounds
        # nothing.
        case = _case()
        assert (
            derive_product_evidence_quality(case.product_evidence, NO_CTX)
            is ProductEvidenceQuality.LIMITED
        )
        from product_intelligence.research import (
            CandidateProductEvidenceSource,
        )

        reviewed_fact = ProductEvidenceFactV2(
            ProductEvidenceDimension.CAPACITY,
            frozenset({CandidateProductEvidenceSource.REVIEWED_PRODUCT_CONTEXT}),
        )
        with pytest.raises(ValueError, match="reviewed product provenance"):
            build_v2_product_evidence_profile(
                observation=_assessment().normalized_listing.observation,
                context_provenances=CUSTOMER_CTX,
                matched_facts=frozenset({reviewed_fact}),
            )


# ===========================================================================
# 10-13. Packaging channel: observed round-trips; absent is explicit
# ===========================================================================


class TestPackagingChannel:
    def _round_trip(self, case):
        record = _record_for(case, V2SemanticDecision.MATCH)
        payload = encode_v2_payload(record)
        decoded = decode_semantic_decision_record(
            payload, schema_version=SEMANTIC_DECISION_SCHEMA_VERSION
        )
        assert decoded.case == record.case
        return decoded

    def test_packaging_single_unit_round_trips_if_observed(self) -> None:
        # 10.
        su = _observed_sales_unit(SalesUnitKindV2.SINGLE_UNIT, raw_detail="1 each")
        decoded = self._round_trip(_case_with_sales_unit(su))
        assert decoded.case.candidate_commercial.sales_unit == su

    def test_pack_quantity_round_trips_if_observed(self) -> None:
        # 11.
        su = _observed_sales_unit(
            SalesUnitKindV2.PACK_QUANTITY, quantity=2, raw_detail="2-pack"
        )
        decoded = self._round_trip(_case_with_sales_unit(su))
        assert decoded.case.candidate_commercial.sales_unit == su
        assert (
            decoded.case.candidate_commercial.sales_unit.quantity == 2
        )

    def test_bundle_round_trips_if_observed(self) -> None:
        # 12.
        su = _observed_sales_unit(
            SalesUnitKindV2.BUNDLE, quantity=3, raw_detail="bundle of 3"
        )
        decoded = self._round_trip(_case_with_sales_unit(su))
        assert decoded.case.candidate_commercial.sales_unit == su

    def test_absent_packaging_is_explicitly_absent_not_equal(self) -> None:
        # 13. The live builder records the explicit UNAVAILABLE state (not
        # None-by-omission, not "single unit"), and the prompt renders the
        # never-infer rule.
        case = _case()
        assert case.candidate_commercial.sales_unit.state is (
            PackagingEvidenceStateV2.UNAVAILABLE
        )
        assert case.candidate_commercial.sales_unit.kind is None
        assert case.candidate_commercial.sales_unit.quantity is None
        assert case.candidate_commercial.sales_unit.raw_detail is None
        prompt = build_semantic_prompt_v2(case)
        assert "- Sales unit / packaging: UNAVAILABLE" in prompt.user_prompt
        assert "absence is NOT proof of equal sales unit" in prompt.user_prompt
        assert "do not infer a single unit" in prompt.user_prompt
        # The persisted input carries the explicit state.
        record = _record_for(case, V2SemanticDecision.MATCH)
        payload = encode_v2_payload(record)
        assert payload["case"]["candidate"]["commercial"]["sales_unit"] == {
            "state": "UNAVAILABLE",
            "kind": None,
            "quantity": None,
            "raw_detail": None,
            "source": None,
        }


# ===========================================================================
# 14-16. The motivating Micron fixture, corrected
# ===========================================================================


class TestMotivatingFixtureCorrected:
    def test_title_tokens_are_not_structured_evidence(self) -> None:
        # 14. The motivating candidate's title carries the family /
        # capacity / interface / form-factor tokens; the corrected
        # contract does NOT turn any of them into a structured fact.
        case = _case()
        product = case.candidate_product
        assert "3840GB" in product.raw_title_text
        assert "U.3" in product.raw_title_text
        assert "15mm" in product.raw_title_text
        assert "7500 PRO" in product.raw_title_text
        assert product.product_family is None
        assert product.capacity is None
        assert product.interface is None
        assert product.form_factor is None
        prompt = build_semantic_prompt_v2(case)
        for dimension in ("product_family", "capacity", "interface", "form_factor"):
            assert f"- {dimension}: (none)" in prompt.user_prompt

    def test_motivating_candidate_still_reaches_v2(self) -> None:
        # 15. U5 / NM-1: eligible, V2 entry point, bounded context.
        assessment = _assessment()
        assert is_v2_semantic_eligible(assessment) is True
        case = _case()
        assert case.identity_state is IdentityStateV2.DETERMINISTIC_UNCERTAIN
        assert case.substate is UncertainSubstateV2.U5_NEAR_MISS_MPN

    def test_motivating_relationship_ceiling_unchanged(self) -> None:
        # 16. The frozen U5/NM-1 ceiling: MATCH/HIGH + STRONG product
        # evidence is capped at NEEDS_REVIEW without reviewed relationship
        # authority — customer retrieval (and the reviewed TARGET context,
        # which is not a candidate-side provenance class) changes nothing.
        from product_intelligence.research import (
            CandidateProductEvidenceSource,
        )

        grounded = frozenset(
            {
                ProductEvidenceFactV2(
                    ProductEvidenceDimension.CAPACITY,
                    frozenset({CandidateProductEvidenceSource.LISTING_PRODUCT_TITLE}),
                ),
                ProductEvidenceFactV2(
                    ProductEvidenceDimension.INTERFACE,
                    frozenset({CandidateProductEvidenceSource.LISTING_PRODUCT_TITLE}),
                ),
            }
        )
        ctx = derive_identity_state_v2(_assessment())
        match_high = SemanticEvaluationV2.evaluated(
            V2SemanticDecision.MATCH, V2Confidence.HIGH, frozenset()
        )
        strong_profile = build_v2_product_evidence_profile(
            observation=_assessment().normalized_listing.observation,
            context_provenances=NO_CTX,
            matched_facts=grounded,
        )
        customer = derive_authority_tier(
            ctx, match_high, CUSTOMER_CTX, strong_profile
        )
        assert customer.tier is AuthorityTier.NEEDS_REVIEW
        assert customer.relationship_authority is RelationshipAuthority.NOT_ESTABLISHED
        with_relation = derive_authority_tier(
            ctx, match_high, RELATION_CTX, strong_profile
        )
        assert with_relation.tier is AuthorityTier.AI_ASSISTED_COMPARABLE


# ===========================================================================
# 17. Authority firewall (source-level; the full-orchestration no-Machine-
#     Price proof lives in the motivating-case file)
# ===========================================================================


class TestAuthorityFirewall:
    def test_v2_wiring_imports_no_pricing_surface(self) -> None:
        # 17 (source-level half): the V2 execution wiring has no import
        # path to the 4A aggregation, the review-candidate service, or the
        # price codec — a V2 outcome cannot reach Machine Price.
        import product_intelligence.execution.semantic_decision_v2_execution as mod

        source = Path(mod.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "research.aggregation",
            "execution.aggregation",
            "price_result_codec",
            "ai_assisted_review",
        ):
            assert forbidden not in source


# ===========================================================================
# 18-20. Persistence / replay / V1 unchanged / qualification boundary
# ===========================================================================


class TestPersistenceReplayAndBoundary:
    def test_v2_persistence_replay_round_trips_the_corrected_input_exactly(self) -> None:
        # 18.
        case = _case(
            _observation(brand="Micron", condition="New"),
            reviewed_target_context=_reviewed_context(),
        )
        record = _record_for(case, V2SemanticDecision.MATCH)
        row = encode_semantic_decision_record(record)
        decoded = decode_semantic_decision_record(
            row, schema_version=SEMANTIC_DECISION_SCHEMA_VERSION
        )
        assert decoded == record
        assert decoded.case == case
        replay = replay_semantic_decision(record)
        assert replay.case == case
        assert replay.contract_binding == V2_CONTRACT_BINDING
        assert (
            replay.case.target.reviewed_context is not None
        )
        assert (
            replay.case.candidate_commercial.sales_unit.state
            is PackagingEvidenceStateV2.UNAVAILABLE
        )

    def test_v1_replay_is_unchanged(self) -> None:
        # 19. The V1 adapter still owns the V1 prompt-input shape (the
        # free-text candidate_specs is a V1 contract rule, untouched) and
        # the universal dispatch replays it under the V1 binding.
        from product_intelligence.research import (
            AttemptOutcome,
            AttemptRole,
            ProductEvidenceProfileV2 as _Profile,
            SemanticDecisionAttempt,
            SemanticDecisionRecordV1,
            SemanticEvaluationStateV2,
            derive_relationship_authority as _dra,
            substate_relationship_requirement,
        )
        from product_intelligence.research.semantic_decision_v1 import (
            FALLBACK_MODEL_V1,
            FALLBACK_PROVIDER_V1,
            PRIMARY_MODEL_V1,
            PRIMARY_PROVIDER_V1,
        )

        assessment = _assessment()
        context = derive_identity_state_v2(assessment)
        profile = build_v2_product_evidence_profile(
            observation=assessment.normalized_listing.observation,
            context_provenances=NO_CTX,
            matched_facts=frozenset(),
        )
        evaluation = SemanticEvaluationV2.evaluated(
            V2SemanticDecision.MATCH, V2Confidence.HIGH, frozenset()
        )
        tier = derive_authority_tier(context, evaluation, NO_CTX, profile)
        record = SemanticDecisionRecordV1.build(
            run_id="ffffffff-ffff-ffff-ffff-ffffffffffff",
            assessment_index=0,
            source_url=assessment.normalized_listing.observation.source_url,
            identity_state=context.state,
            substate=context.substate,
            relationship_signals=context.relationship_signals,
            normalized_requested_part_number=context.normalized_requested_part_number,
            normalized_candidate_part_number=context.normalized_candidate_part_number,
            relationship_requirement=substate_relationship_requirement(
                context.substate, context.primary_relationship_signal
            ),
            product_evidence=profile,
            product_evidence_quality=derive_product_evidence_quality(
                profile, NO_CTX
            ),
            context_provenances=NO_CTX,
            case_id="candidate-v1-0",
            target_mpn=REQUESTED_MPN,
            target_description="Micron 7500 PRO 3840GB U.3 15mm SSD",
            candidate_title=MOTIVATING_TITLE,
            candidate_mpn_field=CANDIDATE_MPN,
            candidate_sku=None,
            candidate_specs=None,
            evidence_source=assessment.candidate_evidence_source.value,
            evaluation_state=SemanticEvaluationStateV2.EVALUATED,
            decision=V2SemanticDecision.MATCH,
            confidence=V2Confidence.HIGH,
            conflict_classes=frozenset(),
            reason_code="exact_mpn_match",
            matched_attributes=("mpn",),
            conflicting_attributes=(),
            missing_critical_attributes=(),
            attempts=(
                SemanticDecisionAttempt(
                    AttemptRole.PRIMARY, 1, PRIMARY_PROVIDER_V1, PRIMARY_MODEL_V1,
                    AttemptOutcome.OK,
                ),
            ),
            fallback_used=False,
            fallback_reason=None,
            error_type=None,
            actual_provider=PRIMARY_PROVIDER_V1,
            actual_model=PRIMARY_MODEL_V1,
            evaluation_started_at="2026-02-10T12:00:00Z",
            evaluation_finished_at="2026-02-10T12:00:03Z",
            relationship_authority=tier.relationship_authority,
            authority_tier=tier.tier,
            fired_rules=tier.fired_rules,
        )
        row = encode_semantic_decision_record(record)
        assert row["contract"]["semantic_contract_version"] == "V1"
        decoded = decode_semantic_decision_record(
            row, schema_version=SEMANTIC_DECISION_SCHEMA_VERSION
        )
        assert decoded == record
        replay = replay_semantic_decision(record)
        assert replay.contract_binding == (
            "V1",
            "1.1",
            1,
            1,
            "SEMANTIC_AUTHORITY_V2_S2A_FU2",
        )

    def test_qualification_boundary_remains_false(self) -> None:
        # 20.
        assert V2_AUTHORITY_QUALIFIED is False
        assert SEMANTIC_PROMPT_VERSION_V2 == "2.0"
        assert V2_CONTRACT_BINDING == ("V2", "2.0", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU2")


# ===========================================================================
# Reviewed target context (target-side structured/reviewed evidence)
# ===========================================================================


def _reviewed_context(
    **overrides,
) -> ReviewedTargetContextV2:
    kwargs = dict(
        manufacturer="Micron",
        category="SSD",
        matched_base_part_number=CANDIDATE_MPN,
        relation_kind=TargetIdentifierRelationKindV2.CUSTOMER_RETRIEVAL_ALIAS,
        relation_family_part_numbers=(CANDIDATE_MPN, CANDIDATE_MPN + "T"),
        source_name="Micron 7500 SSD catalog",
        source_url="https://www.micron.com/catalog",
        retrieved_at="2026-02-10T12:00:00Z",
        evidence_body_sha256="ab" * 32,
    )
    kwargs.update(overrides)
    return ReviewedTargetContextV2(**kwargs)


class TestReviewedTargetContext:
    def test_the_alias_helper_builds_the_context_from_established(self) -> None:
        from product_intelligence.execution.semantic_decision_v2_execution import (
            reviewed_target_context_from_alias_result,
        )

        result = _established_alias_result()
        ctx = reviewed_target_context_from_alias_result(result)
        assert ctx is not None
        assert ctx.manufacturer == "Micron"
        assert ctx.category == "SSD"
        assert ctx.matched_base_part_number == CANDIDATE_MPN
        assert ctx.relation_kind is TargetIdentifierRelationKindV2.CUSTOMER_RETRIEVAL_ALIAS
        # The relation's family members other than the requested R form:
        # the base and the T form (full source-form part numbers).
        assert ctx.relation_family_part_numbers == (CANDIDATE_MPN, CANDIDATE_MPN + "T")
        assert ctx.source_name == "Micron 7500 SSD catalog"
        assert ctx.source_url == MICRON_7500_REQUESTED_CATALOG_URL
        assert ctx.retrieved_at == "2026-09-22T23:20:25Z"
        assert ctx.evidence_body_sha256 == hashlib.sha256(
            FIXTURE.read_bytes()
        ).hexdigest()

    def test_the_alias_helper_returns_none_for_non_established(self) -> None:
        from product_intelligence.execution.semantic_decision_v2_execution import (
            reviewed_target_context_from_alias_result,
        )

        result = _established_alias_result()
        # NO_AUTHORITY_MATCH is a POST-fetch state: it keeps the fetch
        # provenance but none of the authority fields.
        not_established = dataclasses.replace(
            result,
            status=MicronAliasEligibilityStatus.NO_AUTHORITY_MATCH,
            manufacturer=None,
            category=None,
            matched_base_mpn=None,
            part_number_match=None,
            ssd_category_evidence=None,
            alias_relation=None,
        )
        assert (
            reviewed_target_context_from_alias_result(not_established) is None
        )

    def test_established_result_missing_a_reviewed_field_fails_closed(self) -> None:
        from product_intelligence.execution.semantic_decision_v2_execution import (
            reviewed_target_context_from_alias_result,
        )

        result = _established_alias_result()
        corrupted = dataclasses.replace(result, body_sha256=None)
        with pytest.raises(ValueError, match="fail closed"):
            reviewed_target_context_from_alias_result(corrupted)

    def test_the_context_is_target_side_and_grants_no_authority(self) -> None:
        # The reviewed target context is recorded in section A of the
        # input; it is NOT a ContextProvenance member and does not change
        # the frozen relationship-authority derivation (dimension B still
        # derives from candidate-side provenances only).
        ctx = _reviewed_context()
        case = _case(reviewed_target_context=ctx)
        assert case.target.reviewed_context is ctx
        context = derive_identity_state_v2(_assessment())
        assert derive_relationship_authority(context, CUSTOMER_CTX) is (
            RelationshipAuthority.NOT_ESTABLISHED
        )
        assert case.context_provenances == NO_CTX
        # The prompt labels it reviewed / target-side / zero authority.
        prompt = build_semantic_prompt_v2(case)
        assert (
            "- Reviewed manufacturer target context (STRUCTURED/REVIEWED; "
            "target-side only; zero identity authority):"
        ) in prompt.user_prompt
        assert "NOT manufacturer-stated" in prompt.user_prompt

    def test_absent_reviewed_context_is_explicit(self) -> None:
        case = _case()
        assert case.target.reviewed_context is None
        prompt = build_semantic_prompt_v2(case)
        assert (
            "- Reviewed manufacturer target context: "
            "(none carried by the execution flow)"
        ) in prompt.user_prompt

    def test_the_context_fails_closed_on_bad_values(self) -> None:
        with pytest.raises(ValueError):
            _reviewed_context(retrieved_at="yesterday")
        with pytest.raises(ValueError):
            _reviewed_context(retrieved_at="2026-02-10T12:00:00+02:00")
        with pytest.raises(ValueError):
            _reviewed_context(evidence_body_sha256="AB" * 32)
        with pytest.raises(ValueError):
            _reviewed_context(evidence_body_sha256="abc")
        with pytest.raises(ValueError):
            _reviewed_context(relation_family_part_numbers=())
        with pytest.raises(ValueError):
            _reviewed_context(
                relation_family_part_numbers=("R", "R")
            )
        with pytest.raises(TypeError):
            ReviewedTargetContextV2(  # type: ignore[arg-type]
                manufacturer="Micron",
                category="SSD",
                matched_base_part_number=CANDIDATE_MPN,
                relation_kind="MANUFACTURER_STATED",
                relation_family_part_numbers=("R", "T"),
                source_name="s",
                source_url="u",
                retrieved_at="2026-02-10T12:00:00Z",
                evidence_body_sha256="ab" * 32,
            )

    def test_target_section_distinguishes_structured_from_raw(self) -> None:
        target = _case(reviewed_target_context=_reviewed_context()).target
        assert isinstance(target, TargetEvidenceV2)
        assert target.mpn == REQUESTED_MPN
        assert target.description_raw_text == (
            "Micron 7500 PRO 3840GB U.3 15mm SSD"
        )
        assert target.reviewed_context is not None
        encoded = target.canonical()
        assert encoded["mpn"] == REQUESTED_MPN
        assert encoded["description_raw_text"] is not None
        assert encoded["reviewed_context"]["relation_kind"] == (
            "CUSTOMER_RETRIEVAL_ALIAS"
        )
        # Absent description is explicit None, never "".
        no_desc = TargetEvidenceV2(
            mpn=REQUESTED_MPN,
            description_raw_text=None,
            reviewed_context=None,
        )
        assert no_desc.canonical()["description_raw_text"] is None


# ---------------------------------------------------------------------------
# Record helper (a valid MATCH record for one case)
# ---------------------------------------------------------------------------


def _record_for(case, decision) -> SemanticDecisionRecordV2:
    from product_intelligence.research import (
        AttemptOutcome,
        AttemptRole,
        SemanticDecisionAttempt,
        SemanticEvaluationStateV2,
    )
    from product_intelligence.research.semantic_decision_v2 import (
        PRIMARY_MODEL_V2,
        PRIMARY_PROVIDER_V2,
    )
    from product_intelligence.research.semantic_v2 import (
        SemanticReasonCodeV2,
    )

    evaluation = SemanticEvaluationV2.evaluated(
        decision, V2Confidence.HIGH, frozenset()
    )
    context = case_substate_assessment(case)
    tier = derive_authority_tier(
        context,
        evaluation,
        case.context_provenances,
        case.product_evidence,
    )
    reason_code = (
        SemanticReasonCodeV2.MATCH_DESCRIPTION_AND_ATTRIBUTES
        if decision is V2SemanticDecision.MATCH
        else SemanticReasonCodeV2.NO_MATCH_OTHER
    )
    if decision is V2SemanticDecision.NO_MATCH:
        from product_intelligence.research import ConflictClass

        evaluation = SemanticEvaluationV2.evaluated(
            decision, V2Confidence.HIGH, frozenset({ConflictClass.OTHER_MATERIAL_CONFLICT})
        )
        tier = derive_authority_tier(
            context,
            evaluation,
            case.context_provenances,
            case.product_evidence,
        )
    return SemanticDecisionRecordV2.build(
        run_id="ffffffff-ffff-ffff-ffff-ffffffffffff",
        assessment_index=0,
        source_url=case.candidate_source_url,
        case=case,
        evaluation_state=SemanticEvaluationStateV2.EVALUATED,
        decision=decision,
        confidence=V2Confidence.HIGH,
        reason_code=reason_code,
        conflict_classes=evaluation.conflict_classes,
        matched_attributes=(),
        conflicting_attributes=(),
        missing_critical_attributes=(),
        attempts=(
            SemanticDecisionAttempt(
                AttemptRole.PRIMARY, 1, PRIMARY_PROVIDER_V2, PRIMARY_MODEL_V2,
                AttemptOutcome.OK,
            ),
        ),
        fallback_used=False,
        fallback_reason=None,
        error_type=None,
        actual_provider=PRIMARY_PROVIDER_V2,
        actual_model=PRIMARY_MODEL_V2,
        evaluation_started_at="2026-02-10T12:00:00Z",
        evaluation_finished_at="2026-02-10T12:00:03.250000Z",
        product_evidence_quality=tier.product_evidence_quality,
        relationship_authority=tier.relationship_authority,
        authority_tier=tier.tier,
        fired_rules=tier.fired_rules,
    )


def case_substate_assessment(case):
    """The S2-A context the case carries (the case constructor already
    proved it is a legitimate context)."""
    from product_intelligence.research import IdentityStateAssessmentV2

    return IdentityStateAssessmentV2(
        state=case.identity_state,
        substate=case.substate,
        relationship_signals=case.relationship_signals,
        normalized_requested_part_number=case.normalized_requested_part_number,
        normalized_candidate_part_number=case.normalized_candidate_part_number,
    )
