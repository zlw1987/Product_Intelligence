"""Tests for the FINAL Prompt V2 (S2-C, group D).

Covers ``product_intelligence.semantic.contract_v2``:

* the exact prompt version is pinned (``2.0``);
* the prompt instructs COMMERCIAL SEMANTIC EQUIVALENCE (not string
  matching, not price estimation, not machine-verified decisions);
* the explicit NOT-asked-to rules (no price estimation; no Machine
  Verified status; no overriding deterministic HARD_CONFLICT; no
  inferring manufacturer authority; no turning customer aliases into
  manufacturer equivalence; no market-aggregation decisions);
* the explicit behavioral rules (exact MPN strong-but-not-only; missing
  candidate MPN is not automatically NO_MATCH; title MPN may be
  compatibility/reference wording; careful SKU interpretation; near-miss
  identifiers are not automatically equivalent; customer retrieval
  relations are retrieval hints only; labeled manufacturer relationship
  authority is stronger evidence; same physical product with different
  pack quantity / bundle is not pricing-comparable as the same sales
  unit; accessory vs product is a material conflict; insufficient
  evidence -> UNCERTAIN);
* no chain-of-thought field and no free-form hidden reasoning surface in
  the demanded response schema;
* the user prompt renders the exact V2 input's five sections, with the
  customer relation labeled retrieval-only and the commercial context
  labeled never-identity.
"""

from __future__ import annotations

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.research import (
    ExtractionMethod,
    ListingObservation,
    ContextProvenance,
    ProductEvidenceProfileV2,
    assess_listing_identity,
    derive_identity_state_v2,
    normalize_listing_observation,
)
from product_intelligence.research.semantic_v2 import (
    build_semantic_match_case_v2,
    build_v2_product_evidence_profile,
)
from product_intelligence.semantic.contract_v2 import (
    SEMANTIC_PROMPT_VERSION_V2,
    SYSTEM_PROMPT_V2,
    build_semantic_prompt_v2,
    render_v2_user_prompt,
)

REQUEST = ResearchRequest("ABC-123", "A test product")
NO_CTX = frozenset()
CUSTOMER_CTX = frozenset({ContextProvenance.CUSTOMER_RETRIEVAL_RELATION})
RELATION_CTX = frozenset({ContextProvenance.MANUFACTURER_RELATION_AUTHORITY})


def _case(
    mpn=None,
    sku=None,
    title="Test Product",
    provenances=NO_CTX,
    req_mpn="ABC-123",
    description="A test product",
):
    request = ResearchRequest(req_mpn, description)
    observation = ListingObservation(
        source_url="https://example.com/product",
        extraction_method=ExtractionMethod.JSON_LD,
        product_title=title,
        brand_text=None,
        manufacturer_part_number_text=mpn,
        sku_text=sku,
        price_text="100",
        currency_text="USD",
        availability_text="In stock",
        condition_text="New",
        seller_text=None,
    )
    normalized = normalize_listing_observation(observation)
    assessment = assess_listing_identity(request, normalized)
    context = derive_identity_state_v2(assessment)
    profile = build_v2_product_evidence_profile(
        observation=observation,
        context_provenances=provenances,
        matched_facts=frozenset(),
    )
    return build_semantic_match_case_v2(
        case_id="candidate-test-0",
        request=request,
        assessment=assessment,
        context=context,
        product_evidence=profile,
        context_provenances=provenances,
    )


# ===========================================================================
# Version pin
# ===========================================================================


class TestPromptVersionPin:
    def test_the_exact_prompt_version_is_pinned(self) -> None:
        assert SEMANTIC_PROMPT_VERSION_V2 == "2.0"

    def test_the_prompt_carries_the_pinned_version(self) -> None:
        prompt = build_semantic_prompt_v2(_case(title="Has ABC-123 in the title"))
        assert prompt.version == "2.0"
        assert prompt.system_prompt == SYSTEM_PROMPT_V2

    def test_the_prompt_is_deterministic(self) -> None:
        case = _case(title="Has ABC-123 in the title")
        first = build_semantic_prompt_v2(case)
        second = build_semantic_prompt_v2(case)
        assert first.system_prompt == second.system_prompt
        assert first.user_prompt == second.user_prompt
        assert first.case is case

    def test_a_foreign_version_cannot_be_constructed(self) -> None:
        from product_intelligence.semantic.contract_v2 import SemanticPromptV2

        case = _case(title="Has ABC-123 in the title")
        with pytest.raises(ValueError, match="version"):
            SemanticPromptV2(
                version="1.1",
                system_prompt=SYSTEM_PROMPT_V2,
                user_prompt="x",
                case=case,
            )


# ===========================================================================
# Task framing
# ===========================================================================


class TestTaskFraming:
    def test_instructs_commercial_semantic_equivalence(self) -> None:
        assert "COMMERCIAL SEMANTIC EQUIVALENCE" in SYSTEM_PROMPT_V2
        assert "same commercially comparable product" in SYSTEM_PROMPT_V2

    def test_does_not_grant_machine_authority(self) -> None:
        assert "machine verified" in SYSTEM_PROMPT_V2.lower()
        assert (
            "you cannot make a candidate \"machine verified\""
            in SYSTEM_PROMPT_V2
        )
        assert "Do not decide or override deterministic identity status" in (
            SYSTEM_PROMPT_V2
        )

    def test_no_price_estimation(self) -> None:
        assert "Do not estimate, infer, or compare prices" in SYSTEM_PROMPT_V2

    def test_no_overriding_deterministic_hard_conflict(self) -> None:
        assert (
            "you cannot override a deterministic hard conflict"
            in SYSTEM_PROMPT_V2.lower()
        )

    def test_no_inferring_manufacturer_authority(self) -> None:
        assert "Do not infer manufacturer authority" in SYSTEM_PROMPT_V2

    def test_no_customer_alias_to_manufacturer_equivalence(self) -> None:
        assert (
            "Do not turn customer retrieval relations, aliases, or "
            "compatibility/SEO wording into manufacturer equivalence or "
            "identity authority"
        ) in SYSTEM_PROMPT_V2

    def test_no_market_aggregation_decisions(self) -> None:
        assert (
            "Do not decide final market aggregation or any pricing outcome"
            in SYSTEM_PROMPT_V2
        )


# ===========================================================================
# Explicit behavioral rules
# ===========================================================================


class TestBehavioralRules:
    def test_exact_mpn_is_strong_but_not_only_evidence(self) -> None:
        assert (
            "Exact MPN equality is strong evidence but is not the only "
            "evidence of commercial equivalence"
        ) in SYSTEM_PROMPT_V2

    def test_missing_mpn_is_not_automatically_no_match(self) -> None:
        assert (
            "A missing candidate MPN is not automatically NO_MATCH"
        ) in SYSTEM_PROMPT_V2

    def test_title_mpn_compatibility_reference_distinction(self) -> None:
        assert (
            "A target MPN appearing in the listing title may be product "
            "identity OR compatibility / reference / SEO wording"
        ) in SYSTEM_PROMPT_V2
        assert "Inspect the wording context" in SYSTEM_PROMPT_V2

    def test_sku_evidence_interpreted_carefully(self) -> None:
        assert (
            "SKU evidence must be interpreted carefully" in SYSTEM_PROMPT_V2
        )

    def test_near_miss_identifiers_not_automatically_equivalent(self) -> None:
        assert (
            "Near-miss identifiers (truncated, or exactly one character "
            "substituted) are NOT automatically equivalent"
        ) in SYSTEM_PROMPT_V2

    def test_customer_relation_is_retrieval_hint_only(self) -> None:
        assert (
            "CUSTOMER_RETRIEVAL_RELATION, when present, is a RETRIEVAL "
            "HINT ONLY"
        ) in SYSTEM_PROMPT_V2
        assert (
            "It is NOT manufacturer equivalence, it is NOT identity "
            "authority, and it confers no product authority"
        ) in SYSTEM_PROMPT_V2

    def test_manufacturer_relation_authority_is_labeled_stronger(self) -> None:
        assert (
            "MANUFACTURER_RELATION_AUTHORITY, when explicitly present, is "
            "stronger evidence"
        ) in SYSTEM_PROMPT_V2

    def test_sales_unit_packaging_distinction(self) -> None:
        assert (
            "PHYSICAL-PRODUCT equivalence from COMMERCIAL SALES-UNIT / "
            "PACKAGING equivalence"
        ) in SYSTEM_PROMPT_V2
        assert "NOT pricing-comparable as the same sales unit" in SYSTEM_PROMPT_V2
        assert (
            '"Same physical drive" never implies "same comparable price unit"'
        ) in SYSTEM_PROMPT_V2

    def test_packaging_quantity_conflict_is_named(self) -> None:
        assert "PACKAGING_QUANTITY" in SYSTEM_PROMPT_V2
        assert "tray/factory pack" in SYSTEM_PROMPT_V2

    def test_accessory_is_a_material_conflict(self) -> None:
        assert (
            "ACCESSORY_RELATION / PRODUCT_ROLE conflict" in SYSTEM_PROMPT_V2
        )

    def test_insufficient_evidence_is_uncertain_not_a_guess(self) -> None:
        assert (
            "If evidence is insufficient, output UNCERTAIN rather than "
            "guessing"
        ) in SYSTEM_PROMPT_V2
        assert (
            "A false MATCH is materially worse than UNCERTAIN"
            in SYSTEM_PROMPT_V2
        )

    def test_no_chain_of_thought_field(self) -> None:
        assert "chain-of-thought" in SYSTEM_PROMPT_V2
        assert "hidden-reasoning" in SYSTEM_PROMPT_V2
        # The demanded response schema has exactly the six bounded keys —
        # no reasoning surface exists in it.
        import re

        schema_block = SYSTEM_PROMPT_V2.split("RESPONSE FORMAT", 1)[1]
        keys = re.findall(r'"([a-z_]+)"\s*:', schema_block)
        assert keys == [
            "decision",
            "confidence",
            "reason_code",
            "matched_attributes",
            "dimension",
            "detail",
            "conflicting_attributes",
            "dimension",
            "detail",
            "missing_critical_attributes",
            "conflict_classes",
        ]
        # No reasoning/chain-of-thought surface exists in the schema.
        assert "thought" not in keys and "reasoning" not in keys


# ===========================================================================
# User-prompt rendering (the exact V2 input, five sections)
# ===========================================================================


class TestUserPromptRendering:
    def test_renders_all_five_sections(self) -> None:
        case = _case(title="Has ABC-123 in the title")
        prompt = render_v2_user_prompt(case)
        assert "TARGET PRODUCT:" in prompt
        assert "CANDIDATE LISTING:" in prompt
        assert "DETERMINISTIC IDENTITY CONTEXT" in prompt
        assert "CONTEXT PROVENANCE:" in prompt
        assert "PRODUCT EVIDENCE" in prompt

    def test_target_section(self) -> None:
        prompt = render_v2_user_prompt(_case(title="Has ABC-123 in the title"))
        assert "- Requested manufacturer part number (MPN): ABC-123" in prompt
        assert "- Requested description: A test product" in prompt

    def test_candidate_section_with_absent_facts_explicit(self) -> None:
        prompt = render_v2_user_prompt(_case(title="Has ABC-123 in the title"))
        assert "- Source URL: https://example.com/product" in prompt
        assert "- Title: Has ABC-123 in the title" in prompt
        assert "- Published MPN field: (not published)" in prompt
        assert "- Published SKU: (not published)" in prompt
        assert "- Candidate evidence source: TITLE_TEXT" in prompt
        # Price/package observations are context, explicitly labeled.
        assert "Price: 100 USD" in prompt
        assert "NEVER identity evidence" in prompt

    def test_deterministic_context_section(self) -> None:
        prompt = render_v2_user_prompt(_case(title="Has ABC-123 in the title"))
        assert "- Identity state: DETERMINISTIC_UNCERTAIN" in prompt
        assert "- Substate: U1_TITLE_MPN" in prompt
        assert "- Primary identifier relationship signal: TITLE_MPN_TOKEN" in prompt
        assert "- Normalized requested MPN: ABC-123" in prompt
        assert "- Relationship requirement: NOT_REQUIRED" in prompt

    def test_u5_context_section_for_a_near_miss(self) -> None:
        case = _case(mpn="ABC-124")
        prompt = render_v2_user_prompt(case)
        assert "- Substate: U5_NEAR_MISS_MPN" in prompt
        assert (
            "- Primary identifier relationship signal: NEAR_MISS_SUBSTITUTION"
            in prompt
        )
        assert "- Normalized candidate MPN: ABC-124" in prompt
        assert (
            "- Relationship requirement: REVIEWED_RELATION_AUTHORITY_REQUIRED"
            in prompt
        )

    def test_customer_relation_labeled_retrieval_only(self) -> None:
        prompt = render_v2_user_prompt(
            _case(title="Has ABC-123 in the title", provenances=CUSTOMER_CTX)
        )
        assert (
            "CUSTOMER_RETRIEVAL_RELATION: a project-defined retrieval hint"
            in prompt
        )
        assert "NOT manufacturer equivalence" in prompt
        assert "confers no product authority" in prompt
        # It is never described as equivalence/authority.
        assert "MANUFACTURER_RELATION_AUTHORITY" not in prompt

    def test_relation_authority_labeled_stronger(self) -> None:
        prompt = render_v2_user_prompt(
            _case(title="Has ABC-123 in the title", provenances=RELATION_CTX)
        )
        assert (
            "MANUFACTURER_RELATION_AUTHORITY: a reviewed authoritative source"
            in prompt
        )
        assert "stronger, labeled manufacturer relationship authority" in prompt

    def test_no_provenance_rendered_as_none(self) -> None:
        prompt = render_v2_user_prompt(
            _case(title="Has ABC-123 in the title", provenances=NO_CTX)
        )
        section = prompt.split("CONTEXT PROVENANCE:", 1)[1].split(
            "PRODUCT EVIDENCE", 1
        )[0]
        assert "- (none)" in section

    def test_product_evidence_section_labeled_authority_side(self) -> None:
        prompt = render_v2_user_prompt(
            _case(title="Has ABC-123 in the title")
        )
        assert (
            "you may observe it but must NOT create, upgrade, or assert "
            "new product evidence"
        ) in prompt
        assert "- Usable product title: yes" in prompt
        assert "- Grounded matched-attribute facts: (none)" in prompt

    def test_absent_description_renders_explicitly(self) -> None:
        case = _case(description="")
        prompt = render_v2_user_prompt(case)
        assert "- Requested description: (not provided)" in prompt
