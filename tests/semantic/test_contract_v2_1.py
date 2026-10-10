"""Tests for the separately versioned Prompt 2.1 (Q3-B5-P1, T1).

Covers ``product_intelligence.semantic.contract_v2_1``:

* the exact 2.1 prompt version is pinned and the 2.0 freeze regression
  stands (the REAL frozen 2.0 system-prompt digest reproduces; the 2.0
  builder output is byte-identical per case; the two versions coexist);
* the immutable 2.1 contract identity: the binding moves ONLY the
  prompt axis (2.1) and the authority axis (the separately versioned
  FU3 token per the Q3-B4 AD-Q3B4-5 ordering decision); the semantic
  contract, input schema, and output schema axes are unchanged;
* new-clause presence pins (the corrected identity rules from
  Q3-B3-FU2 revision 2): the two-question instruction with the
  resolution and price-comparability non-assertions; the IDENTIFIER
  RELATIONSHIP RULES (established-only-by list; U2N contributes no
  resolution; U3 partial = family membership, never the complete
  number; U4 description resolution; U5 blocks distinctive alignment
  and is authority-only at part-number resolution); the IDENTITY
  RESOLUTION section (three resolutions; asserts nothing beyond; exact
  identity owned by the deterministic layer and human confirmation;
  no resolution upgrades); the DISTINCTIVE-ALIGNMENT TEST (pinning,
  strictly coarser, supplied-evidence bound, alignment is NOT
  uniqueness); the WHAT A MATCH ASSERTS, PRECISELY clause (asserts
  identity at the stated resolution + no published different-unit;
  does NOT assert unit equality, single unit, or price comparability;
  absence from all three lists = "not determined"); the absolute rule
  with the raw-cue evidence base; the SU-ENT critical condition; the
  three-part missing-critical rule (eligible / unpinned /
  decision-critical, re-anchored to grounding at any resolution); the
  CONDITION clarifying sentence; the internal-contradiction rule; the
  requirement-line corrected trust reading; the DECISION RULES
  grounding-at-resolution MATCH formulation and the five NO_MATCH
  "never on" exclusions; the authorized-relation reason-code tie;
* preserved-clause pins: every [2.0 unchanged] section of the approved
  draft is byte-identical to the frozen 2.0 text (section by section);
* CL-9 absence pin: no confidence-guidance wording may appear (the
  confidence surface is the 2.0 format line plus the one absolute-rule
  sentence only);
* the user-template rendered diff is exactly the two annotated lines
  (per case); determinism (twice-call stability); the builder is
  fail-closed on a foreign version or a foreign system-prompt body.
"""

from __future__ import annotations

import re

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.research import (
    AUTHORITY_CONTRACT_VERSION_V2,
    AUTHORITY_CONTRACT_VERSION_V2_FU3,
    PROMPT_VERSION_V2,
    SEMANTIC_CONTRACT_VERSION_V2,
    SEMANTIC_INPUT_SCHEMA_VERSION_V2,
    SEMANTIC_OUTPUT_SCHEMA_VERSION_V2,
    V2_CONTRACT_BINDING,
    assess_listing_identity,
    derive_identity_state_v2,
    normalize_listing_observation,
    ExtractionMethod,
    ListingObservation,
)
from product_intelligence.research.semantic_v2 import (
    build_semantic_match_case_v2,
    build_v2_product_evidence_profile,
    ContextProvenance,
)
from product_intelligence.semantic.contract_v2 import (
    SEMANTIC_PROMPT_VERSION_V2,
    SYSTEM_PROMPT_V2,
    build_semantic_prompt_v2,
    render_v2_user_prompt,
)
from product_intelligence.semantic.contract_v2_1 import (
    SEMANTIC_PROMPT_VERSION_V2_1,
    SYSTEM_PROMPT_V2_1,
    SemanticPromptV2_1,
    V2_1_CONTRACT_BINDING,
    build_semantic_prompt_v2_1,
    render_v2_1_user_prompt,
)

NO_CTX = frozenset()


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
        reviewed_target_context=None,
    )


def _sections(doc: str) -> dict[str, list[str]]:
    headers = (
        "TASK",
        "WHAT YOU ARE NOT ASKED TO DO",
        "WHAT YOU SHOULD DETERMINE",
        "EVIDENCE CLASSES (how to read the input)",
        "IDENTIFIER EVIDENCE RULES",
        "IDENTIFIER RELATIONSHIP RULES",
        "IDENTITY RESOLUTION",
        "DISTINCTIVE-ALIGNMENT TEST",
        "READING THE DETERMINISTIC IDENTITY CONTEXT",
        "CONTEXT PROVENANCE RULES",
        "PRODUCT EVIDENCE RULES",
        "PHYSICAL PRODUCT vs COMMERCIAL SALES UNIT",
        "COMMERCIAL SALES-UNIT RULES",
        "CONFLICT CLASSES (structured; use exactly these values)",
        "MISSING-CRITICAL ATTRIBUTES RULES",
        "INTERNAL CONTRADICTION RULE",
        "DECISION RULES",
        "RESPONSE FORMAT",
    )
    secs: dict[str, list[str]] = {}
    cur = None
    for line in doc.split("\n"):
        if line in headers:
            cur = line
            secs[cur] = []
        elif cur is not None:
            secs[cur].append(line)
    return secs


# ===========================================================================
# Version and binding pins
# ===========================================================================


class TestVersionAndBinding:
    def test_the_exact_prompt_version_is_pinned(self) -> None:
        assert SEMANTIC_PROMPT_VERSION_V2_1 == "2.1"
        assert SEMANTIC_PROMPT_VERSION_V2_1 != SEMANTIC_PROMPT_VERSION_V2

    def test_the_frozen_2_0_axis_is_unchanged(self) -> None:
        assert SEMANTIC_PROMPT_VERSION_V2 == "2.0"
        assert PROMPT_VERSION_V2 == "2.0"

    def test_the_2_1_binding_moves_only_prompt_and_authority_axes(self) -> None:
        # The immutable 2.1 contract identity (Q3-B4 AD-Q3B4-5: the
        # separately versioned FU3 token precedes the 2.1 binding).
        assert V2_1_CONTRACT_BINDING == (
            SEMANTIC_CONTRACT_VERSION_V2,
            SEMANTIC_PROMPT_VERSION_V2_1,
            SEMANTIC_INPUT_SCHEMA_VERSION_V2,
            SEMANTIC_OUTPUT_SCHEMA_VERSION_V2,
            AUTHORITY_CONTRACT_VERSION_V2_FU3,
        )
        # Axis by axis against the frozen 2.0 binding: ONLY the prompt
        # axis (2.1) and the authority axis (the separately versioned
        # FU3 token) move; the semantic contract, input schema, and
        # output schema axes are unchanged (the seven strict response
        # keys stand).
        assert V2_1_CONTRACT_BINDING[0] == V2_CONTRACT_BINDING[0]
        assert V2_1_CONTRACT_BINDING[2] == V2_CONTRACT_BINDING[2]
        assert V2_1_CONTRACT_BINDING[3] == V2_CONTRACT_BINDING[3]
        assert V2_1_CONTRACT_BINDING[1] == "2.1"
        assert V2_CONTRACT_BINDING[1] == "2.0"
        assert V2_1_CONTRACT_BINDING[4] == AUTHORITY_CONTRACT_VERSION_V2_FU3
        assert V2_CONTRACT_BINDING[4] == AUTHORITY_CONTRACT_VERSION_V2
        assert (
            AUTHORITY_CONTRACT_VERSION_V2_FU3 != AUTHORITY_CONTRACT_VERSION_V2
        )

    def test_the_2_1_builder_constructs_only_2_1(self) -> None:
        prompt = build_semantic_prompt_v2_1(_case(title="Has ABC-123 in the title"))
        assert prompt.version == "2.1"
        assert prompt.system_prompt == SYSTEM_PROMPT_V2_1

    def test_a_foreign_version_cannot_be_constructed(self) -> None:
        case = _case(title="Has ABC-123 in the title")
        with pytest.raises(ValueError, match="version"):
            SemanticPromptV2_1(
                version="2.0",
                system_prompt=SYSTEM_PROMPT_V2_1,
                user_prompt=render_v2_1_user_prompt(case),
                case=case,
            )

    def test_a_foreign_system_prompt_body_cannot_be_constructed(self) -> None:
        case = _case(title="Has ABC-123 in the title")
        with pytest.raises(ValueError, match="system_prompt"):
            SemanticPromptV2_1(
                version="2.1",
                system_prompt=SYSTEM_PROMPT_V2,  # the frozen 2.0 body
                user_prompt=render_v2_1_user_prompt(case),
                case=case,
            )

    def test_the_2_0_builder_stays_byte_frozen_per_case(self) -> None:
        for case in (
            _case(title="Has ABC-123 in the title"),
            _case(mpn="ABC-124"),  # near-miss: DETERMINISTIC_UNCERTAIN
            _case(sku="OTHER-SKU", title="Something else"),
            _case(
                title="Something",
                provenances=frozenset(
                    {ContextProvenance.CUSTOMER_RETRIEVAL_RELATION}
                ),
            ),
        ):
            prompt = build_semantic_prompt_v2(case)
            assert prompt.version == "2.0"
            assert prompt.system_prompt == SYSTEM_PROMPT_V2
            assert prompt.user_prompt == render_v2_user_prompt(case)


# ===========================================================================
# The 2.0 freeze regression (the REAL digest reproduces)
# ===========================================================================


class TestFrozen2_0Regression:
    def test_the_real_frozen_2_0_system_prompt_digest_reproduces(self) -> None:
        from product_intelligence.evaluation.semantic_v2.canonical import (
            canonical_sha256,
        )

        assert canonical_sha256({"text": SYSTEM_PROMPT_V2}) == (
            "c0cc98bdd6d357e81d4692218f18d354351fc2833267b3062b7cd74b18445a84"
        )

    def test_the_2_1_text_is_separately_versioned(self) -> None:
        assert SYSTEM_PROMPT_V2_1 != SYSTEM_PROMPT_V2
        assert SYSTEM_PROMPT_V2_1.startswith(
            "You are a product commercial-equivalence evaluation assistant.\n"
        )


# ===========================================================================
# Preserved-clause pins: every [2.0 unchanged] section is byte-identical
# ===========================================================================


class TestPreserved2_0Sections:
    s20 = None
    s21 = None

    @classmethod
    def setup_class(cls) -> None:
        cls.s20 = _sections(SYSTEM_PROMPT_V2)
        cls.s21 = _sections(SYSTEM_PROMPT_V2_1)

    def test_the_task_section_is_byte_identical(self) -> None:
        assert self.s20["TASK"] == self.s21["TASK"]

    def test_the_not_asked_section_is_byte_identical(self) -> None:
        assert (
            self.s20["WHAT YOU ARE NOT ASKED TO DO"]
            == self.s21["WHAT YOU ARE NOT ASKED TO DO"]
        )

    def test_the_determine_section_keeps_its_last_three_lines(self) -> None:
        assert (
            self.s20["WHAT YOU SHOULD DETERMINE"][1:]
            == self.s21["WHAT YOU SHOULD DETERMINE"][1:]
        )
        # The first line is the 2.1 correction (the two questions with
        # resolution + price comparability stated).
        assert (
            self.s20["WHAT YOU SHOULD DETERMINE"][0]
            != self.s21["WHAT YOU SHOULD DETERMINE"][0]
        )

    def test_the_evidence_classes_section_differs_only_by_the_raw_cue_sentence(
        self,
    ) -> None:
        e20, e21 = self.s20["EVIDENCE CLASSES (how to read the input)"], self.s21[
            "EVIDENCE CLASSES (how to read the input)"
        ]
        assert e20[0] == e21[0]  # STRUCTURED FACT
        assert e20[1] == e21[1]  # RAW OBSERVATION TEXT
        assert e21[2].startswith(e20[2])  # COMMERCIAL gains the raw-cue sentence
        assert e20[3:] == e21[3:]  # the rest is byte-identical

    def test_the_context_provenance_section_gains_two_appended_sentences(self) -> None:
        p20, p21 = self.s20["CONTEXT PROVENANCE RULES"], self.s21[
            "CONTEXT PROVENANCE RULES"
        ]
        assert len(p20) == len(p21)
        assert p21[0].startswith(p20[0])
        assert p21[1].startswith(p20[1])
        assert p21[2] == p20[2]  # MANUFACTURER_PRODUCT_CONTEXT unchanged

    def test_the_product_evidence_section_is_byte_identical(self) -> None:
        assert (
            self.s20["PRODUCT EVIDENCE RULES"] == self.s21["PRODUCT EVIDENCE RULES"]
        )

    def test_the_conflict_classes_section_gains_the_condition_sentence(self) -> None:
        c20 = self.s20["CONFLICT CLASSES (structured; use exactly these values)"]
        c21 = self.s21["CONFLICT CLASSES (structured; use exactly these values)"]
        assert c20[:3] == c21[:3]  # the three bounded lists
        assert c21[3].startswith(c20[3])  # the paragraph + CONDITION sentence
        assert c20[4:] == c21[4:]

    def test_the_response_format_section_gains_exactly_one_line(self) -> None:
        r20, r21 = self.s20["RESPONSE FORMAT"], self.s21["RESPONSE FORMAT"]
        assert r21[: len(r20)] == r20  # byte-identical through the 2.0 text
        assert len(r21) == len(r20) + 1  # exactly the authorized-relation tie

    def test_the_replaced_2_0_sections_are_gone(self) -> None:
        assert "IDENTIFIER EVIDENCE RULES" not in self.s21
        assert "PHYSICAL PRODUCT vs COMMERCIAL SALES UNIT" not in self.s21

    def test_the_new_sections_are_present(self) -> None:
        for header in (
            "IDENTIFIER RELATIONSHIP RULES",
            "IDENTITY RESOLUTION",
            "DISTINCTIVE-ALIGNMENT TEST",
            "READING THE DETERMINISTIC IDENTITY CONTEXT",
            "COMMERCIAL SALES-UNIT RULES",
            "MISSING-CRITICAL ATTRIBUTES RULES",
            "INTERNAL CONTRADICTION RULE",
        ):
            assert header in self.s21
            assert header not in self.s20


# ===========================================================================
# New-clause presence pins (Q3-B3-FU2 revision 2, the corrected rules)
# ===========================================================================


class TestNewClausePins:
    def test_the_two_question_instruction_with_resolution_and_non_assertions(
        self,
    ) -> None:
        assert (
            "at what RESOLUTION the identification is grounded"
            in SYSTEM_PROMPT_V2_1
        )
        assert (
            "A MATCH at family or description resolution is not a claim of "
            "part-number identity, and a MATCH with an unproven sales unit "
            "is not a claim of price comparability"
            in SYSTEM_PROMPT_V2_1
        )

    def test_identifier_relationship_established_only_by(self) -> None:
        assert (
            "An identifier relationship is ESTABLISHED only by"
            in SYSTEM_PROMPT_V2_1
        )
        assert (
            "a customer-retrieval relation, and a manufacturer product "
            "context never establish it by themselves"
            in SYSTEM_PROMPT_V2_1
        )

    def test_u2n_contributes_no_resolution(self) -> None:
        assert (
            "It contributes no resolution. The decision rests entirely on "
            "the product evidence under the DISTINCTIVE-ALIGNMENT TEST, at "
            "DESCRIPTION resolution"
            in SYSTEM_PROMPT_V2_1
        )

    def test_u3_partial_prefix_family_membership_limitations(self) -> None:
        assert (
            "It grounds the candidate's claim of FAMILY MEMBERSHIP in the "
            "requested part's number family — NOT the specific variant"
            in SYSTEM_PROMPT_V2_1
        )
        assert (
            "a family prefix can be shared by more than one part"
            in SYSTEM_PROMPT_V2_1
        )
        assert (
            "does NOT assert that the candidate is the specific requested "
            "part number"
            in SYSTEM_PROMPT_V2_1
        )
        assert (
            "never a NO_MATCH on the prefix alone" in SYSTEM_PROMPT_V2_1
        )

    def test_u4_generic_vs_distinctive_description(self) -> None:
        assert (
            "the same description can be published by different products, "
            "and the supplied evidence does not show that it is not here"
            in SYSTEM_PROMPT_V2_1
        )

    def test_u5_blocks_distinctive_alignment_and_authority_only(self) -> None:
        assert (
            "it BLOCKS the DISTINCTIVE-ALIGNMENT TEST" in SYSTEM_PROMPT_V2_1
        )
        assert (
            "Equivalence is established ONLY by "
            "MANUFACTURER_RELATION_AUTHORITY explicitly establishing the "
            "specific relationship"
            in SYSTEM_PROMPT_V2_1
        )
        assert (
            "a MATCH on this ground is at PART-NUMBER resolution for the "
            "specifically related part"
            in SYSTEM_PROMPT_V2_1
        )
        assert (
            "do not assert MPN_IDENTITY on an unproven difference"
            in SYSTEM_PROMPT_V2_1
        )
        assert (
            "a customer-retrieval relation and a manufacturer product "
            "context never establish it"
            in SYSTEM_PROMPT_V2_1
        )

    def test_the_identity_resolution_section(self) -> None:
        assert (
            "PART-NUMBER resolution: the exact requested MPN published "
            "with identity wording"
            in SYSTEM_PROMPT_V2_1
        )
        assert (
            "FAMILY+DESCRIPTION resolution: a consistent partial form of "
            "the requested identifier (U3)"
            in SYSTEM_PROMPT_V2_1
        )
        assert (
            "DESCRIPTION resolution: no candidate identifier (U4) or a "
            "different retailer SKU (U2)"
            in SYSTEM_PROMPT_V2_1
        )
        assert (
            "It does NOT assert that the candidate is the specific "
            "requested part number, and it does NOT assert that no other "
            "product shares the published description or family"
            in SYSTEM_PROMPT_V2_1
        )
        assert (
            "Exact product identity is owned by the deterministic layer "
            "and by human confirmation"
            in SYSTEM_PROMPT_V2_1
        )
        assert (
            "alignment of attributes never upgrades the resolution"
            in SYSTEM_PROMPT_V2_1
        )

    def test_the_distinctive_alignment_test(self) -> None:
        assert (
            "credited from structured facts AND raw observation text "
            "(credit ALL supplied evidence on both sides before judging)"
            in SYSTEM_PROMPT_V2_1
        )
        assert (
            "publishes a value strictly coarser than the conveyed one"
            in SYSTEM_PROMPT_V2_1
        )
        assert (
            "the test is judged only on the SUPPLIED EVIDENCE"
            in SYSTEM_PROMPT_V2_1
        )
        assert "Alignment is NOT uniqueness" in SYSTEM_PROMPT_V2_1
        assert (
            "A dimension the request does not convey is not "
            "decision-critical for identity (never name it missing)"
            in SYSTEM_PROMPT_V2_1
        )

    def test_what_a_match_asserts_precisely(self) -> None:
        assert "WHAT A MATCH ASSERTS, PRECISELY" in SYSTEM_PROMPT_V2_1
        assert (
            "does NOT assert price comparability of the commercial sales "
            "unit unless published packaging evidence establishes the same "
            "commercial unit"
            in SYSTEM_PROMPT_V2_1
        )
        assert (
            "the price-comparability question remains OPEN for human or "
            "reviewed confirmation"
            in SYSTEM_PROMPT_V2_1
        )
        assert (
            'means "not determined on the supplied evidence"'
            in SYSTEM_PROMPT_V2_1
        )
        assert (
            'as "proven single unit", "proven equal unit", or '
            '"pricing-comparable"'
            in SYSTEM_PROMPT_V2_1
        )

    def test_sales_unit_unavailable_never_means_proven_equal(self) -> None:
        assert (
            "do not read UNAVAILABLE as \"single unit\"" in SYSTEM_PROMPT_V2_1
        )
        assert (
            "Do not report PACKAGING_QUANTITY or BUNDLE in "
            "missing_critical_attributes solely because the channel is "
            "UNAVAILABLE"
            in SYSTEM_PROMPT_V2_1
        )

    def test_the_absolute_rule_with_the_raw_cue_evidence_base(self) -> None:
        assert (
            "ABSOLUTE RULE — PUBLISHED INCOMPATIBLE PACKAGING IS A HARD "
            "CONFLICT"
            in SYSTEM_PROMPT_V2_1
        )
        assert (
            "in the structured sales-unit channel or published in raw "
            "observation text"
            in SYSTEM_PROMPT_V2_1
        )
        assert (
            "No confidence, provenance, or attribute alignment overrides "
            "this rule"
            in SYSTEM_PROMPT_V2_1
        )
        assert (
            "A packaging cue published in raw observation text"
            in SYSTEM_PROMPT_V2_1
        )

    def test_the_su_ent_critical_condition(self) -> None:
        assert (
            "MISSING SALES UNIT, CRITICAL (MATCH BLOCKED)"
            in SYSTEM_PROMPT_V2_1
        )
        assert (
            "must block MATCH with UNCERTAIN, reporting PACKAGING_QUANTITY "
            "and/or BUNDLE in missing_critical_attributes"
            in SYSTEM_PROMPT_V2_1
        )
        assert (
            "guessing packaging or product equivalence is forbidden"
            in SYSTEM_PROMPT_V2_1
        )

    def test_the_three_part_missing_critical_rule(self) -> None:
        assert "(1) ELIGIBLE:" in SYSTEM_PROMPT_V2_1
        assert "(2) UNPINNED:" in SYSTEM_PROMPT_V2_1
        assert "(3) DECISION-CRITICAL:" in SYSTEM_PROMPT_V2_1
        # Part 1: request-conveyed only; the never-named dimensions.
        assert (
            "BRAND, REVISION_OR_SUFFIX, and CONDITION are never named "
            "missing"
            in SYSTEM_PROMPT_V2_1
        )
        # Part 2: strictly coarser pins nothing; credit first.
        assert (
            "no matching value and no strictly-coarser value"
            in SYSTEM_PROMPT_V2_1
        )
        assert (
            "A value published on the candidate and uncontradicted is "
            "credited, NOT missing"
            in SYSTEM_PROMPT_V2_1
        )
        # Part 3: re-anchored to grounding at any resolution; G1 gaps not
        # decision-critical.
        assert (
            "the supplied evidence grounds equivalence at any resolution "
            "ONLY with D pinned"
            in SYSTEM_PROMPT_V2_1
        )
        assert (
            "attribute gaps are NOT decision-critical: the part number (or "
            "the authority-established relation) is the ground"
            in SYSTEM_PROMPT_V2_1
        )

    def test_the_internal_contradiction_rule(self) -> None:
        assert "INTERNAL CONTRADICTION RULE" in SYSTEM_PROMPT_V2_1
        assert (
            "that dimension is UNPINNED in both directions on the supplied "
            "evidence"
            in SYSTEM_PROMPT_V2_1
        )
        assert (
            "do not return NO_MATCH on an internally contradictory "
            "dimension alone"
            in SYSTEM_PROMPT_V2_1
        )

    def test_the_requirement_line_trust_reading(self) -> None:
        assert (
            'The "Relationship requirement" line is DOWNSTREAM '
            "AUTHORITY-TIER POLICY"
            in SYSTEM_PROMPT_V2_1
        )
        assert (
            "it marks which published identifier claims the authority "
            "layer does not yet trust for automatic pricing"
            in SYSTEM_PROMPT_V2_1
        )

    def test_the_decision_rules_match_grounding_at_resolution(self) -> None:
        assert (
            "the product evidence grounds commercial equivalence at the "
            "resolution of its strongest identifier ground"
            in SYSTEM_PROMPT_V2_1
        )

    def test_the_no_match_never_on_exclusions(self) -> None:
        assert (
            "Never return NO_MATCH on missing evidence alone, on an "
            "internally contradictory dimension alone, on a "
            "customer-retrieval relation, on a different retailer SKU, or "
            "on a consistent partial form alone"
            in SYSTEM_PROMPT_V2_1
        )

    def test_the_condition_clarifying_sentence(self) -> None:
        assert (
            "CONDITION may be reported as a conflicting attribute on any "
            "decision; it never blocks a MATCH and is never an identity "
            "conflict"
            in SYSTEM_PROMPT_V2_1
        )

    def test_the_authorized_relation_reason_code_tie(self) -> None:
        assert (
            "MATCH_AUTHORIZED_IDENTIFIER_RELATION may be used only when "
            "the CONTEXT PROVENANCE section explicitly lists "
            "MANUFACTURER_RELATION_AUTHORITY"
            in SYSTEM_PROMPT_V2_1
        )

    def test_no_chain_of_thought_surface(self) -> None:
        assert (
            "There is no chain-of-thought field and no hidden-reasoning "
            "field"
            in SYSTEM_PROMPT_V2_1
        )

    def test_the_response_schema_is_the_frozen_seven_keys(self) -> None:
        # The 2.1 output contract is the frozen 2.0 output contract:
        # seven strict keys, 17 reason codes, 12 dimensions.
        for key in (
            '"decision"',
            '"confidence"',
            '"reason_code"',
            '"matched_attributes"',
            '"conflicting_attributes"',
            '"missing_critical_attributes"',
            '"conflict_classes"',
        ):
            assert key in SYSTEM_PROMPT_V2_1
        reason_codes_20 = re.findall(
            r"(?:MATCH|UNCERTAIN|NO_MATCH)_[A-Z_]+", SYSTEM_PROMPT_V2
        )
        reason_codes_21 = re.findall(
            r"(?:MATCH|UNCERTAIN|NO_MATCH)_[A-Z_]+", SYSTEM_PROMPT_V2_1
        )
        assert len(set(reason_codes_20)) == 17
        assert set(reason_codes_21) == set(reason_codes_20)
        assert (
            "The bounded attribute dimensions are: PRODUCT_FAMILY, "
            "GENERATION, CAPACITY, INTERFACE, FORM_FACTOR, PRODUCT_ROLE, "
            "ACCESSORY_RELATION, PACKAGING_QUANTITY, BUNDLE, BRAND, "
            "REVISION_OR_SUFFIX, CONDITION."
            in SYSTEM_PROMPT_V2_1
        )


# ===========================================================================
# CL-9: no confidence-guidance wording (the confidence surface is the
# 2.0 format line plus the one absolute-rule sentence only)
# ===========================================================================


class TestNoConfidenceGuidance:
    def test_confidence_lines_are_the_2_0_set_plus_exactly_one(self) -> None:
        lines_20 = [
            line
            for line in SYSTEM_PROMPT_V2.split("\n")
            if "confidence" in line.lower()
        ]
        lines_21 = [
            line
            for line in SYSTEM_PROMPT_V2_1.split("\n")
            if "confidence" in line.lower()
        ]
        # Every 2.0 confidence line stands unchanged in 2.1...
        for line in lines_20:
            assert line in lines_21
        # ...and 2.1 gains exactly ONE confidence line: the absolute
        # rule's no-override sentence (not a guidance sentence).
        assert len(lines_21) == len(lines_20) + 1
        new = [line for line in lines_21 if line not in lines_20]
        assert len(new) == 1
        assert new[0].startswith(
            "- ABSOLUTE RULE — PUBLISHED INCOMPATIBLE PACKAGING IS A HARD "
            "CONFLICT"
        )
        assert (
            "No confidence, provenance, or attribute alignment "
            "overrides this rule" in new[0]
        )

    def test_no_confidence_mapping_instructions(self) -> None:
        # No line maps a decision / evidence shape to a confidence level
        # (the removed revision-0 guidance category, CL-9).
        pattern = re.compile(
            r"(use|return|choose|set|should be|is)\s+"
            r"(HIGH|MEDIUM|LOW)\b",
            re.IGNORECASE,
        )
        for line in SYSTEM_PROMPT_V2_1.split("\n"):
            assert not pattern.search(line), f"confidence guidance: {line}"


# ===========================================================================
# The user-template rendered diff: exactly the two annotated lines
# ===========================================================================


class TestUserTemplateDiff:
    @pytest.mark.parametrize(
        "case",
        [
            pytest.param(
                _case(title="Has ABC-123 in the title"), id="title-mpn"
            ),
            pytest.param(
                _case(mpn="ABC-124"), id="near-miss-mpn"
            ),
            pytest.param(
                _case(sku="OTHER-SKU", title="Something else"),
                id="different-sku",
            ),
            pytest.param(
                _case(
                    title="Something",
                    provenances=frozenset(
                        {
                            ContextProvenance.CUSTOMER_RETRIEVAL_RELATION,
                            ContextProvenance.MANUFACTURER_PRODUCT_CONTEXT,
                        }
                    ),
                ),
                id="provenances",
            ),
        ],
    )
    def test_the_rendered_diff_is_exactly_two_lines(self, case) -> None:
        text_2_0 = render_v2_user_prompt(case)
        text_2_1 = render_v2_1_user_prompt(case)
        lines_2_0 = text_2_0.split("\n")
        lines_2_1 = text_2_1.split("\n")
        assert len(lines_2_0) == len(lines_2_1)
        diffs = [
            i
            for i, (a, b) in enumerate(zip(lines_2_0, lines_2_1))
            if a != b
        ]
        assert len(diffs) == 2
        # Section-C header line.
        assert lines_2_0[diffs[0]] == (
            "DETERMINISTIC IDENTITY CONTEXT (frozen deterministic layer "
            "output; you cannot override it):"
        )
        assert lines_2_1[diffs[0]] == (
            "DETERMINISTIC IDENTITY CONTEXT (frozen deterministic layer "
            "output; the identifier facts are established; the "
            "relationship requirement line is downstream authority-tier "
            "policy, not your decision input):"
        )
        # The requirement line (the rendered value is preserved).
        assert lines_2_0[diffs[1]].startswith("- Relationship requirement: ")
        assert lines_2_1[diffs[1]] == (
            "- Relationship requirement (downstream authority-tier policy, "
            "not your decision input): "
            + lines_2_0[diffs[1]][len("- Relationship requirement: "):]
        )

    def test_the_rendering_is_deterministic(self) -> None:
        case = _case(title="Has ABC-123 in the title")
        first = render_v2_1_user_prompt(case)
        second = render_v2_1_user_prompt(case)
        assert first == second

    def test_the_builder_is_deterministic(self) -> None:
        case = _case(title="Has ABC-123 in the title")
        first = build_semantic_prompt_v2_1(case)
        second = build_semantic_prompt_v2_1(case)
        assert first.system_prompt == second.system_prompt
        assert first.user_prompt == second.user_prompt
        assert first.case is case


# ===========================================================================
# The draft carries no reviewer annotations
# ===========================================================================


class TestNoDraftAnnotations:
    def test_no_reviewer_markers_remain_in_the_prompt_text(self) -> None:
        for marker in (
            "[2.0 unchanged",
            "[2.1 NEW",
            "[2.1 CHANGED",
            "(R1",
            "(R2",
            "confidence-guidance sentence is NOT present",
        ):
            assert marker not in SYSTEM_PROMPT_V2_1, marker
