"""Tests for the S2-A-FU3 authority contract firewall foundation
(PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-B4-FU1).

Covers ``product_intelligence.research.semantic_authority_fu3`` — the
separately versioned authority contract ``SEMANTIC_AUTHORITY_V2_S2A_FU3``
(Q3-B4 decision document, Option B + Option D, foundation phase only):

* F1. OLD-TOKEN INVARIANCE — the frozen S2-A module is byte-unchanged
   (file-level digest pin), the frozen token / binding / rule vocabulary /
   tables stand, and per-binding dispatch under the old token is
   byte-identical to the frozen derivation (never an FU3 result).
* F2. NEW TOKEN + FAIL-CLOSED — the FU3 token is separately versioned;
   unknown / blank / non-string contract tokens fail closed; the live V2
   record / adapter / replay surface still knows only the old binding and
   refuses an FU3-bound record.
* F3. IDENTITY RESOLUTION BOUND — independently derived from recorded
   deterministic + reviewed evidence only (the model never sets it): the
   exact 14-row table (U1 identity vs compatibility wording; U2E vs U2N;
   U3 shared-prefix variants; U4 description-only; U5 authority split;
   verified / conflict / unevaluable); customer retrieval has zero bound
   authority; description / family matching never becomes part-number
   identity; unknown combinations fail closed.
* F4. SALES-UNIT AUTHORITY — explicit provenance, fail-closed default:
   UNAVAILABLE is never proven; observed single unit / pack quantity /
   tray / bundle against the default single-unit target and against
   explicit target-side evidence; model claims never establish authority;
   the recorded channel drives the derivation (case-level entry).
* F5. RESTRICT-ONLY CEILING + FUTURE QUALIFIED-STATE SIMULATION —
   MATCH + HIGH + STRONG (+ reviewed relation where required) + unproven
   unit: AI_ASSISTED under the old token, NEEDS_REVIEW +
   CEILING_SALES_UNIT_NOT_PROVEN under FU3; proven unit stands;
   published incompatible packaging stays HARD_CONFLICT (supersedes
   human confirmation); the ceiling fires only on the automatic tier and
   never lifts (exhaustive restrict-only enumeration); human confirmation
   is explicit, auditable, and above the ceiling; a generic semantic
   MATCH never infers unit confirmation.
* F6. REACHABILITY ISOLATION — no live runtime / pricing / persistence
   module references the FU3 contract; the V2 qualification marker stays
   False; the live V2 execution derives under the frozen token; the FU3
   module is research-pure (imports, no I/O, no clock, no vendor/caller
   tokens, no mutable globals).

Every case is a recorded-input construction through the REAL frozen 3C
chain (``normalize_listing_observation`` + ``assess_listing_identity`` +
``derive_identity_state_v2``) with scripted semantic evaluations — zero
live model calls, zero network calls.
"""

from __future__ import annotations

import ast
import dataclasses
import hashlib
import sys
from pathlib import Path

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.research import (
    AUTHORITY_CONTRACT_VERSION_V2,
    AuthorityRuleV2,
    AuthorityTier,
    CandidateEvidenceSourceV2,
    CandidateProductEvidenceSource,
    CandidateSalesUnitEvidenceV2,
    ConflictClass,
    ContextProvenance,
    ExtractionMethod,
    HumanReviewStateV2,
    IdentityRelationshipSignal,
    IdentityStateAssessmentV2,
    IdentityStateV2,
    ListingObservation,
    PackagingEvidenceStateV2,
    ProductEvidenceDimension,
    ProductEvidenceFactV2,
    ProductEvidenceProfileV2,
    ProductEvidenceQuality,
    RelationshipAuthority,
    RelationshipRequirement,
    SALES_UNIT_EVIDENCE_UNAVAILABLE,
    SalesUnitKindV2,
    SemanticEvaluationStateV2,
    SemanticEvaluationV2,
    SUBSTATE_RELATIONSHIP_REQUIREMENTS,
    UncertainSubstateV2,
    UnevaluableSubstateV2,
    V2Confidence,
    V2SemanticDecision,
    VerifiedSubstateV2,
    assess_listing_identity,
    derive_authority_tier,
    derive_identity_state_v2,
    normalize_listing_observation,
)
from product_intelligence.research import semantic_authority_fu3 as fu3
from product_intelligence.research.semantic_authority_fu3 import (
    AUTHORITY_CONTRACT_VERSION_V2_FU3,
    AuthorityDecisionV2FU3,
    AuthorityRuleV2FU3,
    IDENTITY_RESOLUTION_BOUND_TABLE,
    IdentityResolutionBoundV2,
    KNOWN_AUTHORITY_CONTRACT_TOKENS,
    SalesUnitAuthorityV2,
    TargetSalesUnitEvidenceSourceV2,
    TargetSalesUnitEvidenceV2,
    TargetSalesUnitFormV2,
    UnknownAuthorityContractTokenError,
    derive_authority_tier_for_contract,
    derive_authority_tier_fu3,
    derive_identity_resolution_bound,
    derive_sales_unit_authority,
    identity_resolution_bound,
    is_known_authority_contract_token,
    sales_unit_authority_from_channel,
)
from product_intelligence.research.semantic_v2 import SemanticMatchCaseV2

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "product_intelligence"
FROZEN_MODULE_PATH = PACKAGE_ROOT / "research" / "semantic_authority_v2.py"
FU3_MODULE_PATH = PACKAGE_ROOT / "research" / "semantic_authority_fu3.py"

REQUEST_MPN = "ABC-123"

# The exact frozen S2-A module digest at the Q3-B4 starting SHA
# (4b2ed6c5ef368dd75b8ae2f86fc1e1ae58c21550). The old token's derivation is
# byte-frozen: any edit to the file fails F1.
FROZEN_MODULE_SHA256 = (
    "78301d308e0a5e748c2a22cd8785c673b7c2230b54cc60f4714ee2da6b74d8a5"
)


# -- Recorded-input construction (the real frozen 3C chain) ---------------


def _observation(
    mpn: str | None = None,
    sku: str | None = None,
    title: str | None = "Test Product",
) -> ListingObservation:
    return ListingObservation(
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


def _assess(
    mpn: str | None = None,
    sku: str | None = None,
    title: str | None = "Test Product",
    req_mpn: str = REQUEST_MPN,
    description: str = "A test product",
):
    normalized = normalize_listing_observation(
        _observation(mpn=mpn, sku=sku, title=title)
    )
    request = ResearchRequest(
        manufacturer_part_number=req_mpn, description=description
    )
    return assess_listing_identity(request, normalized)


def _v2(
    mpn: str | None = None,
    sku: str | None = None,
    title: str | None = "Test Product",
    req_mpn: str = REQUEST_MPN,
    description: str = "A test product",
) -> IdentityStateAssessmentV2:
    return derive_identity_state_v2(
        _assess(mpn=mpn, sku=sku, title=title, req_mpn=req_mpn, description=description)
    )


def _eval(
    decision: V2SemanticDecision,
    confidence: V2Confidence,
    conflicts: frozenset[ConflictClass] = frozenset(),
) -> SemanticEvaluationV2:
    return SemanticEvaluationV2.evaluated(decision, confidence, conflicts)


def _match(high: bool = True, conflicts=frozenset()) -> SemanticEvaluationV2:
    return _eval(
        V2SemanticDecision.MATCH,
        V2Confidence.HIGH if high else V2Confidence.MEDIUM,
        conflicts,
    )


NO_CTX = frozenset()
PRODUCT_CTX = frozenset({ContextProvenance.MANUFACTURER_PRODUCT_CONTEXT})
RELATION_CTX = frozenset({ContextProvenance.MANUFACTURER_RELATION_AUTHORITY})
CUSTOMER_CTX = frozenset({ContextProvenance.CUSTOMER_RETRIEVAL_RELATION})

TITLE_SOURCES = frozenset(
    {CandidateProductEvidenceSource.LISTING_PRODUCT_TITLE}
)


def _strong_profile() -> ProductEvidenceProfileV2:
    """A bounded STRONG product-evidence profile: a usable title plus two
    matched facts on two distinct hard product dimensions, grounded in the
    listing title (never a model claim). The future qualified-state
    simulation input (dimension A = STRONG)."""
    return ProductEvidenceProfileV2(
        has_usable_product_title=True,
        matched_facts=frozenset(
            {
                ProductEvidenceFactV2(
                    ProductEvidenceDimension.CAPACITY, TITLE_SOURCES
                ),
                ProductEvidenceFactV2(
                    ProductEvidenceDimension.INTERFACE, TITLE_SOURCES
                ),
            }
        ),
    )


def _channel(kind: SalesUnitKindV2, quantity: int | None = None) -> (
    CandidateSalesUnitEvidenceV2
):
    """An OBSERVED recorded sales-unit channel with explicit provenance."""
    return CandidateSalesUnitEvidenceV2(
        state=PackagingEvidenceStateV2.OBSERVED,
        kind=kind,
        quantity=quantity,
        raw_detail="published packaging field",
        source=CandidateEvidenceSourceV2.PUBLISHED_STRUCTURED_FIELD,
    )


UNAVAILABLE = SALES_UNIT_EVIDENCE_UNAVAILABLE


def _target(
    form: TargetSalesUnitFormV2,
    quantity: int | None = None,
    source: TargetSalesUnitEvidenceSourceV2 = (
        TargetSalesUnitEvidenceSourceV2.REVIEWED_TARGET_CONTEXT
    ),
) -> TargetSalesUnitEvidenceV2:
    return TargetSalesUnitEvidenceV2(form=form, quantity=quantity, source=source)


# ===========================================================================
# F1. OLD-TOKEN INVARIANCE (the frozen S2-A-FU2 contract)
# ===========================================================================


class TestOldTokenInvariance:
    def test_the_frozen_s2a_module_is_byte_unchanged(self) -> None:
        digest = hashlib.sha256(FROZEN_MODULE_PATH.read_bytes()).hexdigest()
        assert digest == FROZEN_MODULE_SHA256, (
            "the frozen S2-A authority contract module changed; the old "
            "token's derivation is byte-frozen (S2-A-FU2) — the FU3 "
            "amendment lives behind its own token and module, never in "
            "place"
        )

    def test_the_frozen_token_is_unchanged(self) -> None:
        assert AUTHORITY_CONTRACT_VERSION_V2 == "SEMANTIC_AUTHORITY_V2_S2A_FU2"
        assert fu3.AUTHORITY_CONTRACT_VERSION_V2 is AUTHORITY_CONTRACT_VERSION_V2

    def test_the_frozen_v2_binding_is_unchanged(self) -> None:
        from product_intelligence.research.semantic_decision_v2 import (
            SEMANTIC_V2_ADAPTER,
            V2_CONTRACT_BINDING,
        )

        assert V2_CONTRACT_BINDING == (
            "V2",
            "2.0",
            1,
            1,
            "SEMANTIC_AUTHORITY_V2_S2A_FU2",
        )
        # The live V2 adapter knows exactly ONE binding: the old one.
        assert SEMANTIC_V2_ADAPTER.supported_bindings == (V2_CONTRACT_BINDING,)

    def test_the_frozen_rule_vocabulary_is_unchanged(self) -> None:
        assert [rule.value for rule in AuthorityRuleV2] == [
            "STATE_POLICY_DETERMINISTIC",
            "SEMANTIC_OUTCOME_MATRIX",
            "INELIGIBLE_STATE_IGNORES_SEMANTIC",
            "RUNTIME_FAILURE",
            "CEILING_REVIEWABLE_CONFLICT",
            "CEILING_NEAR_MISS_SUBSTITUTION_WITHOUT_RELATION_AUTHORITY",
            "CEILING_IDENTIFIER_RELATIONSHIP_NOT_ESTABLISHED",
            "HARD_CONFLICT_SUPERSEDES",
            "HUMAN_CONFIRMED_APPLIED",
            "HUMAN_REJECTED_APPLIED",
            "HARD_CONFLICT_SUPERSEDES_HUMAN",
            "HUMAN_OUTCOME_NOT_APPLICABLE",
        ]

    def test_the_frozen_tables_are_unchanged(self) -> None:
        from product_intelligence.research import (
            SEMANTIC_OUTCOME_TIER_MATRIX,
            semantic_outcome_tier,
        )

        assert len(SEMANTIC_OUTCOME_TIER_MATRIX) == 27
        assert len(SUBSTATE_RELATIONSHIP_REQUIREMENTS) == 14
        # The only pricing-eligible semantic row is unchanged.
        assert (
            semantic_outcome_tier(
                V2SemanticDecision.MATCH,
                V2Confidence.HIGH,
                ProductEvidenceQuality.STRONG,
            )
            is AuthorityTier.AI_ASSISTED_COMPARABLE
        )

    def test_old_token_dispatch_is_identical_to_the_frozen_derivation(self) -> None:
        """Per-binding replay dispatch: the old token re-derives through
        the UNCHANGED frozen derivation — every (state, evaluation,
        provenance, profile, human) combination yields exactly the frozen
        result (type and value), never an FU3 result."""
        profiles = (None, _strong_profile())
        evaluations = (
            None,
            SemanticEvaluationV2.runtime_failure(),
            _match(),
            _match(high=False),
            _eval(V2SemanticDecision.NO_MATCH, V2Confidence.HIGH),
            _eval(V2SemanticDecision.UNCERTAIN, V2Confidence.HIGH),
            _eval(
                V2SemanticDecision.NO_MATCH,
                V2Confidence.HIGH,
                frozenset({ConflictClass.PACKAGING_QUANTITY}),
            ),
        )
        provenance_sets = (NO_CTX, PRODUCT_CTX, RELATION_CTX, CUSTOMER_CTX)
        humans = (None, HumanReviewStateV2.CONFIRMED, HumanReviewStateV2.REJECTED)

        shapes = {
            "u1": _v2(title=f"Has {REQUEST_MPN} in the title"),
            "u2e": _v2(sku=REQUEST_MPN),
            "u2n": _v2(sku="RETAIL-SKU-1"),
            "u3": _v2(mpn="ABC"),
            "u4": _v2(title="Usable title without any MPN"),
            "u5_nm1": _v2(mpn=f"{REQUEST_MPN}X"),
            "u5_nm2": _v2(mpn="ABC-124"),
            "c1": _v2(mpn="ZZZ-000"),
            "v_exact": _v2(mpn=REQUEST_MPN),
        }
        # E1 / E2 assessments: no requested MPN / no candidate evidence.
        e1 = derive_identity_state_v2(
            _assess(req_mpn="", description="description only")
        )
        e2 = _v2(title=None)
        counts = 0
        for name, assessment_v2 in {**shapes, "e1": e1, "e2": e2}.items():
            # E2 contradicts a title-bearing profile; keep it state-valid.
            profile_options = (None,) if name == "e2" else profiles
            for profile in profile_options:
                for evaluation in evaluations:
                    for provenances in provenance_sets:
                        for human in humans:
                            expected = derive_authority_tier(
                                assessment_v2,
                                evaluation,
                                provenances,
                                profile,
                                human,
                            )
                            actual = derive_authority_tier_for_contract(
                                AUTHORITY_CONTRACT_VERSION_V2,
                                assessment_v2,
                                evaluation,
                                provenances,
                                profile,
                                human,
                            )
                            assert type(actual) is type(expected)
                            assert not isinstance(actual, AuthorityDecisionV2FU3)
                            assert actual == expected
                            counts += 1
        # 10 states x 2 profiles + the E2 state (default profile only) x
        # 7 evaluations x 4 provenance sets x 3 human overlays.
        assert counts == 10 * 2 * 7 * 4 * 3 + 1 * 1 * 7 * 4 * 3

    def test_old_token_dispatch_refuses_sales_unit_inputs(self) -> None:
        """The frozen FU2 contract has no sales-unit input: passing one
        under the old token is contract misuse and fails closed (the
        firewall can never be silently applied to old-binding records)."""
        assessment_v2 = _v2(title=f"Has {REQUEST_MPN} in the title")
        with pytest.raises(ValueError, match="no sales-unit input"):
            derive_authority_tier_for_contract(
                AUTHORITY_CONTRACT_VERSION_V2,
                assessment_v2,
                sales_unit_channel=UNAVAILABLE,
            )
        with pytest.raises(ValueError, match="no sales-unit input"):
            derive_authority_tier_for_contract(
                AUTHORITY_CONTRACT_VERSION_V2,
                assessment_v2,
                target_unit_evidence=_target(TargetSalesUnitFormV2.SINGLE_UNIT),
            )


# ===========================================================================
# F2. NEW TOKEN + FAIL-CLOSED
# ===========================================================================


class TestFu3TokenAndFailClosed:
    def test_the_fu3_token_is_separately_versioned(self) -> None:
        assert AUTHORITY_CONTRACT_VERSION_V2_FU3 == "SEMANTIC_AUTHORITY_V2_S2A_FU3"
        assert (
            AUTHORITY_CONTRACT_VERSION_V2_FU3 != AUTHORITY_CONTRACT_VERSION_V2
        )
        assert KNOWN_AUTHORITY_CONTRACT_TOKENS == frozenset(
            {AUTHORITY_CONTRACT_VERSION_V2, AUTHORITY_CONTRACT_VERSION_V2_FU3}
        )
        assert is_known_authority_contract_token(AUTHORITY_CONTRACT_VERSION_V2)
        assert is_known_authority_contract_token(AUTHORITY_CONTRACT_VERSION_V2_FU3)

    @pytest.mark.parametrize(
        "token",
        [
            "SEMANTIC_AUTHORITY_V2_S2A_FU9",
            "SEMANTIC_AUTHORITY_V2_S2A_FU1",
            "SEMANTIC_AUTHORITY_V3_S2A_FU3",
            "semantics_authority_v2_s2a_fu3",  # near-miss spelling
            "SEMANTIC_AUTHORITY_V2_S2A_FU3 ",  # trailing whitespace
            " SEMANTIC_AUTHORITY_V2_S2A_FU3",  # leading whitespace
            "",
            "V2",
            "1.1",
        ],
    )
    def test_unknown_tokens_are_not_known(self, token: str) -> None:
        assert not is_known_authority_contract_token(token)

    def test_dispatch_on_unknown_tokens_fails_closed(self) -> None:
        assessment_v2 = _v2(title=f"Has {REQUEST_MPN} in the title")
        with pytest.raises(UnknownAuthorityContractTokenError):
            derive_authority_tier_for_contract(
                "SEMANTIC_AUTHORITY_V2_S2A_FU9",
                assessment_v2,
                sales_unit_channel=UNAVAILABLE,
            )
        with pytest.raises(UnknownAuthorityContractTokenError):
            derive_authority_tier_for_contract("", assessment_v2)
        with pytest.raises(UnknownAuthorityContractTokenError):
            derive_authority_tier_for_contract(
                "SEMANTIC_AUTHORITY_V2_S2A_FU3 ", assessment_v2
            )
        assert issubclass(UnknownAuthorityContractTokenError, ValueError)

    def test_dispatch_on_non_string_token_fails_closed(self) -> None:
        assessment_v2 = _v2(title=f"Has {REQUEST_MPN} in the title")
        with pytest.raises(TypeError):
            derive_authority_tier_for_contract(  # type: ignore[arg-type]
                None, assessment_v2
            )
        with pytest.raises(TypeError):
            derive_authority_tier_for_contract(  # type: ignore[arg-type]
                42, assessment_v2
            )
        with pytest.raises(TypeError):
            is_known_authority_contract_token(  # type: ignore[arg-type]
                None
            )

    def test_fu3_dispatch_requires_the_recorded_channel(self) -> None:
        """Fail-closed: the FU3 derivation needs the recorded sales-unit
        channel (the V2 input always carries one explicitly); a caller who
        omits it gets an error, never a silent tier."""
        assessment_v2 = _v2(title=f"Has {REQUEST_MPN} in the title")
        with pytest.raises(ValueError, match="sales-unit channel"):
            derive_authority_tier_for_contract(
                AUTHORITY_CONTRACT_VERSION_V2_FU3, assessment_v2
            )

    def test_the_live_v2_adapter_still_refuses_an_fu3_binding(self) -> None:
        """A record bound to the FU3 token is outside the CURRENT live V2
        adapter: the exact-binding replay gate refuses it (never silently
        reinterpreted) and the V2 record type cannot even be constructed
        under it (the frozen exact-token check)."""
        from product_intelligence.research.semantic_decision_replay import (
            replay_semantic_decision,
        )
        from product_intelligence.research.semantic_decision_record import (
            SemanticDecisionReplayError,
        )
        from product_intelligence.research.semantic_decision_v2 import (
            SemanticDecisionRecordV2,
        )

        class _RawRecord:
            pass

        raw = _RawRecord()
        (
            raw.semantic_contract_version,
            raw.prompt_version,
            raw.input_schema_version,
            raw.output_schema_version,
            raw.authority_contract_version,
        ) = ("V2", "2.0", 1, 1, AUTHORITY_CONTRACT_VERSION_V2_FU3)
        with pytest.raises(
            SemanticDecisionReplayError, match="refuses to reinterpret"
        ):
            replay_semantic_decision(raw)

        # The V2 record pins the old token at construction (frozen check):
        # an FU3-bound record cannot exist under the current adapter.
        from tests.research.test_semantic_decision_v2 import _build_record, _case

        record = _build_record(decision=V2SemanticDecision.MATCH, confidence=V2Confidence.HIGH)
        with pytest.raises(ValueError, match="authority_contract_version"):
            dataclasses.replace(
                record,
                authority_contract_version=AUTHORITY_CONTRACT_VERSION_V2_FU3,
            )
        assert record.authority_contract_version == AUTHORITY_CONTRACT_VERSION_V2


# ===========================================================================
# F3. IDENTITY RESOLUTION BOUND (independently derived, model-free)
# ===========================================================================


class TestIdentityResolutionBound:
    def test_the_bound_table_covers_exactly_the_permitted_combinations(self) -> None:
        """Completeness (import-self-checked, re-proven here): the bound
        table keys are EXACTLY the (sub-state, primary signal)
        combinations the frozen derivation permits — the same key set as
        the frozen relationship-requirement table."""
        keys = {(entry[0], entry[1]) for entry in IDENTITY_RESOLUTION_BOUND_TABLE}
        assert len(IDENTITY_RESOLUTION_BOUND_TABLE) == len(keys) == 14
        assert keys == {
            (entry_substate, entry_signal)
            for entry_substate, entry_signal, _req in SUBSTATE_RELATIONSHIP_REQUIREMENTS
        }

    def test_exact_mpn_is_part_number_bound(self) -> None:
        v_exact = _v2(mpn=REQUEST_MPN)
        assert v_exact.substate is VerifiedSubstateV2.V_EXACT
        assert derive_identity_resolution_bound(v_exact) is (
            IdentityResolutionBoundV2.PART_NUMBER
        )

    def test_normalized_exact_is_part_number_bound(self) -> None:
        normalized = _v2(mpn=REQUEST_MPN.lower())
        assert normalized.substate is VerifiedSubstateV2.V_NORMALIZED_EXACT
        assert derive_identity_resolution_bound(normalized) is (
            IdentityResolutionBoundV2.PART_NUMBER
        )

    def test_u1_identity_wording_is_part_number_bound(self) -> None:
        u1 = _v2(title=f"Has {REQUEST_MPN} in the title")
        assert u1.substate is UncertainSubstateV2.U1_TITLE_MPN
        assert not u1.has_signal(IdentityRelationshipSignal.COMPATIBILITY_WORDING)
        assert derive_identity_resolution_bound(u1) is (
            IdentityResolutionBoundV2.PART_NUMBER
        )
        # The bound is independent of the relationship provenances.
        assert derive_identity_resolution_bound(u1, RELATION_CTX) is (
            IdentityResolutionBoundV2.PART_NUMBER
        )

    def test_u1_compatibility_wording_is_description_bound(self) -> None:
        """U1 + COMPAT: the title token is not an identifier ground; the
        decision rests on product evidence -> DESCRIPTION."""
        u1_compat = _v2(title=f"{REQUEST_MPN} compatible NVMe drive")
        assert u1_compat.substate is UncertainSubstateV2.U1_TITLE_MPN
        assert u1_compat.has_signal(IdentityRelationshipSignal.COMPATIBILITY_WORDING)
        assert derive_identity_resolution_bound(u1_compat) is (
            IdentityResolutionBoundV2.DESCRIPTION
        )
        # Even with manufacturer relationship authority present (the
        # compatibility wording is a title fact, not a relationship fact).
        assert derive_identity_resolution_bound(u1_compat, RELATION_CTX) is (
            IdentityResolutionBoundV2.DESCRIPTION
        )

    def test_u2_sku_equals_target_is_part_number_bound(self) -> None:
        u2e = _v2(sku=REQUEST_MPN)
        assert u2e.substate is UncertainSubstateV2.U2_SKU_ONLY
        assert u2e.has_signal(IdentityRelationshipSignal.SKU_EQUALS_TARGET)
        assert derive_identity_resolution_bound(u2e) is (
            IdentityResolutionBoundV2.PART_NUMBER
        )

    def test_u2_different_retailer_sku_is_description_bound(self) -> None:
        """Different retailer SKU with matching specifications: the SKU is
        neither conflict nor ground -> DESCRIPTION (never PART_NUMBER)."""
        u2n = _v2(sku="RETAIL-SKU-1")
        assert u2n.substate is UncertainSubstateV2.U2_SKU_ONLY
        assert u2n.has_signal(IdentityRelationshipSignal.SKU_NOT_TARGET)
        assert derive_identity_resolution_bound(u2n) is (
            IdentityResolutionBoundV2.DESCRIPTION
        )
        # Manufacturer relationship authority does not re-grade a
        # different retailer SKU into part-number ground.
        assert derive_identity_resolution_bound(u2n, RELATION_CTX) is (
            IdentityResolutionBoundV2.DESCRIPTION
        )

    def test_u3_shared_prefix_variants_are_family_description_bound(self) -> None:
        """U3 partial boundary: the shared prefix is never the complete
        number it truncates -> FAMILY_DESCRIPTION for the shared-prefix
        variant shapes, with or without relationship authority."""
        u3 = _v2(mpn="ABC")
        assert u3.substate is UncertainSubstateV2.U3_PARTIAL_BOUNDARY
        assert derive_identity_resolution_bound(u3) is (
            IdentityResolutionBoundV2.FAMILY_DESCRIPTION
        )
        assert derive_identity_resolution_bound(u3, RELATION_CTX) is (
            IdentityResolutionBoundV2.FAMILY_DESCRIPTION
        )
        assert derive_identity_resolution_bound(u3, CUSTOMER_CTX) is (
            IdentityResolutionBoundV2.FAMILY_DESCRIPTION
        )

    def test_u4_description_only_is_description_bound(self) -> None:
        u4 = _v2(title="Usable title without any MPN")
        assert u4.substate is UncertainSubstateV2.U4_NO_MPN
        assert derive_identity_resolution_bound(u4) is (
            IdentityResolutionBoundV2.DESCRIPTION
        )
        u4_empty = _v2(
            mpn="mpn:", title="Usable title with empty MPN field"
        )
        assert u4_empty.substate is UncertainSubstateV2.U4_NO_MPN
        assert u4_empty.has_signal(IdentityRelationshipSignal.EMPTY_MPN_FIELD)
        assert derive_identity_resolution_bound(u4_empty) is (
            IdentityResolutionBoundV2.DESCRIPTION
        )
        # Not part-number ground even under full reviewed authority.
        assert derive_identity_resolution_bound(u4, RELATION_CTX) is (
            IdentityResolutionBoundV2.DESCRIPTION
        )

    @pytest.mark.parametrize(
        "provenances,expected",
        [
            (NO_CTX, IdentityResolutionBoundV2.NONE),
            (PRODUCT_CTX, IdentityResolutionBoundV2.NONE),
            (CUSTOMER_CTX, IdentityResolutionBoundV2.NONE),
            (RELATION_CTX, IdentityResolutionBoundV2.PART_NUMBER),
        ],
        ids=["none", "product-context", "customer-retrieval", "relation-authority"],
    )
    def test_u5_authority_split(
        self, provenances: frozenset[ContextProvenance], expected: IdentityResolutionBoundV2
    ) -> None:
        """U5 near-miss: PART_NUMBER only for the specifically related
        part — the labeled manufacturer relationship authority is the
        ground. Customer-retrieval relations have ZERO bound authority;
        product context grounds no identifier relation."""
        for mpn, label in ((f"{REQUEST_MPN}X", "nm1"), ("ABC-124", "nm2")):
            u5 = _v2(mpn=mpn)
            assert u5.substate is UncertainSubstateV2.U5_NEAR_MISS_MPN, label
            assert derive_identity_resolution_bound(u5, provenances) is expected, (
                label,
                provenances,
            )

    def test_customer_retrieval_alias_never_establishes_a_bound(self) -> None:
        """0018/0022 shape: the customer-retrieval alias makes the variant
        question concrete while conferring zero equivalence authority."""
        u5 = _v2(mpn=f"{REQUEST_MPN}X")
        bound = derive_identity_resolution_bound(u5, CUSTOMER_CTX)
        assert bound is IdentityResolutionBoundV2.NONE

    def test_conflict_and_unevaluable_states_are_none_bound(self) -> None:
        c1 = _v2(mpn="ZZZ-000")
        assert c1.state is IdentityStateV2.DETERMINISTIC_CONFLICT
        assert derive_identity_resolution_bound(c1) is IdentityResolutionBoundV2.NONE

        e1 = derive_identity_state_v2(
            _assess(req_mpn="", description="description only")
        )
        assert e1.state is IdentityStateV2.DETERMINISTIC_UNEVALUABLE
        assert derive_identity_resolution_bound(e1) is IdentityResolutionBoundV2.NONE

        e2 = _v2(title=None)
        assert e2.state is IdentityStateV2.DETERMINISTIC_UNEVALUABLE
        assert derive_identity_resolution_bound(e2) is IdentityResolutionBoundV2.NONE

    def test_the_pure_lookup_fails_closed_on_unknown_combinations(self) -> None:
        with pytest.raises(ValueError, match="no frozen identity-resolution bound"):
            identity_resolution_bound(
                UncertainSubstateV2.U1_TITLE_MPN,
                IdentityRelationshipSignal.EXACT,
            )
        with pytest.raises(ValueError, match="no frozen identity-resolution bound"):
            identity_resolution_bound(
                UncertainSubstateV2.U4_NO_MPN,
                IdentityRelationshipSignal.NEAR_MISS_TRUNCATION,
            )
        with pytest.raises(TypeError):
            identity_resolution_bound(  # type: ignore[arg-type]
                "U1_TITLE_MPN", IdentityRelationshipSignal.TITLE_MPN_TOKEN
            )
        with pytest.raises(TypeError):
            identity_resolution_bound(
                UncertainSubstateV2.U1_TITLE_MPN, "TITLE_MPN_TOKEN"  # type: ignore[arg-type]
            )

    def test_the_derivation_fails_closed_on_foreign_inputs(self) -> None:
        with pytest.raises(TypeError):
            derive_identity_resolution_bound("not an assessment")  # type: ignore[arg-type]
        with pytest.raises(TypeError):
            derive_identity_resolution_bound(
                _v2(title=f"Has {REQUEST_MPN} in the title"), "not a frozenset"  # type: ignore[arg-type]
            )

    def test_model_output_never_sets_the_bound(self) -> None:
        """The bound is a pure function of the recorded deterministic
        state + reviewed provenances: the function takes NO semantic
        evaluation input, so a MATCH of any shape cannot move it."""
        import inspect

        parameters = inspect.signature(
            derive_identity_resolution_bound
        ).parameters
        assert set(parameters) == {"assessment_v2", "context_provenances"}

        u4 = _v2(title="Usable title without any MPN")
        # There is no evaluation parameter to pass a MATCH through; the
        # bound is identical regardless of what the model answered.
        assert derive_identity_resolution_bound(u4) is (
            IdentityResolutionBoundV2.DESCRIPTION
        )
        assert derive_identity_resolution_bound(u4, RELATION_CTX) is (
            IdentityResolutionBoundV2.DESCRIPTION
        )

    def test_description_matching_never_becomes_deterministic_exact_identity(
        self,
    ) -> None:
        """Even a fully qualified future state (STRONG + HIGH + MATCH +
        reviewed relation) cannot raise the bound above its table value:
        the tier may be capped, the bound may be recorded, but the
        deterministic exact-identity tier (MACHINE_VERIFIED) is reachable
        only from the frozen verified states."""
        for name, assessment_v2, bound in (
            ("u3", _v2(mpn="ABC"), IdentityResolutionBoundV2.FAMILY_DESCRIPTION),
            ("u4", _v2(title="Usable title without any MPN"), IdentityResolutionBoundV2.DESCRIPTION),
        ):
            decision = derive_authority_tier_fu3(
                assessment_v2,
                UNAVAILABLE,
                _match(),
                RELATION_CTX,
                _strong_profile(),
            )
            assert decision.identity_resolution_bound is bound
            assert decision.tier is not AuthorityTier.MACHINE_VERIFIED, name


# ===========================================================================
# F4. SALES-UNIT AUTHORITY (explicit provenance, fail-closed default)
# ===========================================================================


class TestSalesUnitAuthority:
    def test_unavailable_channel_is_never_proven(self) -> None:
        """Absence is a recorded absence: UNAVAILABLE is UNPROVEN for EVERY
        target-side evidence shape — it never becomes proven equivalent."""
        targets = (
            None,
            _target(TargetSalesUnitFormV2.SINGLE_UNIT),
            _target(TargetSalesUnitFormV2.PACK_QUANTITY, quantity=4),
            _target(TargetSalesUnitFormV2.TRAY_OR_FACTORY_PACK),
            _target(TargetSalesUnitFormV2.BUNDLE),
        )
        for target in targets:
            assert sales_unit_authority_from_channel(UNAVAILABLE, target) is (
                SalesUnitAuthorityV2.UNPROVEN
            )

    def test_observed_single_unit(self) -> None:
        single = _channel(SalesUnitKindV2.SINGLE_UNIT)
        # Default single-unit target (the Q1(a) contract default).
        assert sales_unit_authority_from_channel(single) is (
            SalesUnitAuthorityV2.PROVEN_EQUIVALENT
        )
        assert sales_unit_authority_from_channel(
            single, _target(TargetSalesUnitFormV2.SINGLE_UNIT)
        ) is SalesUnitAuthorityV2.PROVEN_EQUIVALENT
        # Target-side evidence establishing a different form contradicts.
        assert sales_unit_authority_from_channel(
            single, _target(TargetSalesUnitFormV2.PACK_QUANTITY, quantity=4)
        ) is SalesUnitAuthorityV2.CONTRADICTED
        assert sales_unit_authority_from_channel(
            single, _target(TargetSalesUnitFormV2.TRAY_OR_FACTORY_PACK)
        ) is SalesUnitAuthorityV2.CONTRADICTED
        assert sales_unit_authority_from_channel(
            single, _target(TargetSalesUnitFormV2.BUNDLE)
        ) is SalesUnitAuthorityV2.CONTRADICTED

    def test_observed_pack_quantity(self) -> None:
        pack4 = _channel(SalesUnitKindV2.PACK_QUANTITY, quantity=4)
        # Against the default single-unit target: CONTRADICTED (the
        # absolute rule's derivation-level twin).
        assert sales_unit_authority_from_channel(pack4) is (
            SalesUnitAuthorityV2.CONTRADICTED
        )
        # Proven only with the SAME established pack quantity.
        assert sales_unit_authority_from_channel(
            pack4, _target(TargetSalesUnitFormV2.PACK_QUANTITY, quantity=4)
        ) is SalesUnitAuthorityV2.PROVEN_EQUIVALENT
        assert sales_unit_authority_from_channel(
            pack4, _target(TargetSalesUnitFormV2.PACK_QUANTITY, quantity=2)
        ) is SalesUnitAuthorityV2.CONTRADICTED
        assert sales_unit_authority_from_channel(
            pack4, _target(TargetSalesUnitFormV2.SINGLE_UNIT)
        ) is SalesUnitAuthorityV2.CONTRADICTED
        assert sales_unit_authority_from_channel(
            pack4, _target(TargetSalesUnitFormV2.TRAY_OR_FACTORY_PACK)
        ) is SalesUnitAuthorityV2.CONTRADICTED

    def test_observed_tray_and_bundle(self) -> None:
        tray = _channel(SalesUnitKindV2.TRAY_OR_FACTORY_PACK, quantity=20)
        bundle = _channel(SalesUnitKindV2.BUNDLE)
        # Default single-unit target: CONTRADICTED.
        assert sales_unit_authority_from_channel(tray) is (
            SalesUnitAuthorityV2.CONTRADICTED
        )
        assert sales_unit_authority_from_channel(bundle) is (
            SalesUnitAuthorityV2.CONTRADICTED
        )
        # Matching established kind: PROVEN (quantities agree when both
        # are published).
        assert sales_unit_authority_from_channel(
            tray, _target(TargetSalesUnitFormV2.TRAY_OR_FACTORY_PACK, quantity=20)
        ) is SalesUnitAuthorityV2.PROVEN_EQUIVALENT
        assert sales_unit_authority_from_channel(
            tray, _target(TargetSalesUnitFormV2.TRAY_OR_FACTORY_PACK)
        ) is SalesUnitAuthorityV2.PROVEN_EQUIVALENT
        assert sales_unit_authority_from_channel(
            _channel(SalesUnitKindV2.TRAY_OR_FACTORY_PACK),
            _target(TargetSalesUnitFormV2.TRAY_OR_FACTORY_PACK, quantity=20),
        ) is SalesUnitAuthorityV2.PROVEN_EQUIVALENT
        assert sales_unit_authority_from_channel(
            bundle, _target(TargetSalesUnitFormV2.BUNDLE)
        ) is SalesUnitAuthorityV2.PROVEN_EQUIVALENT
        # Published quantity disagreement: CONTRADICTED.
        assert sales_unit_authority_from_channel(
            tray, _target(TargetSalesUnitFormV2.TRAY_OR_FACTORY_PACK, quantity=10)
        ) is SalesUnitAuthorityV2.CONTRADICTED
        # Cross-kind: CONTRADICTED.
        assert sales_unit_authority_from_channel(
            tray, _target(TargetSalesUnitFormV2.BUNDLE)
        ) is SalesUnitAuthorityV2.CONTRADICTED
        assert sales_unit_authority_from_channel(
            bundle, _target(TargetSalesUnitFormV2.TRAY_OR_FACTORY_PACK)
        ) is SalesUnitAuthorityV2.CONTRADICTED

    def test_the_target_form_vocabulary_mirrors_the_candidate_channel(self) -> None:
        assert {form.value for form in TargetSalesUnitFormV2} == {
            kind.value for kind in SalesUnitKindV2
        }

    def test_target_evidence_requires_explicit_bounded_provenance(self) -> None:
        evidence = _target(
            TargetSalesUnitFormV2.PACK_QUANTITY,
            quantity=4,
            source=TargetSalesUnitEvidenceSourceV2.REQUEST_DESCRIPTION,
        )
        assert evidence.source is TargetSalesUnitEvidenceSourceV2.REQUEST_DESCRIPTION
        with pytest.raises(TypeError):
            TargetSalesUnitEvidenceV2(
                form=TargetSalesUnitFormV2.PACK_QUANTITY,
                quantity=4,
                source="a model claim",  # type: ignore[arg-type]
            )
        with pytest.raises(TypeError):
            TargetSalesUnitEvidenceV2(
                form="PACK_QUANTITY",  # type: ignore[arg-type]
                quantity=4,
                source=TargetSalesUnitEvidenceSourceV2.REVIEWED_TARGET_CONTEXT,
            )

    def test_target_evidence_quantity_rules_fail_closed(self) -> None:
        # PACK_QUANTITY requires the bounded positive quantity.
        with pytest.raises(ValueError, match="quantity"):
            _target(TargetSalesUnitFormV2.PACK_QUANTITY)
        with pytest.raises(ValueError, match="quantity"):
            _target(TargetSalesUnitFormV2.PACK_QUANTITY, quantity=0)
        with pytest.raises(ValueError, match="quantity"):
            _target(TargetSalesUnitFormV2.PACK_QUANTITY, quantity="4")  # type: ignore[arg-type]
        # SINGLE_UNIT carries no quantity.
        with pytest.raises(ValueError, match="no quantity"):
            _target(TargetSalesUnitFormV2.SINGLE_UNIT, quantity=1)
        # Tray / bundle quantities are optional but bounded when present.
        _target(TargetSalesUnitFormV2.TRAY_OR_FACTORY_PACK)
        _target(TargetSalesUnitFormV2.TRAY_OR_FACTORY_PACK, quantity=20)
        with pytest.raises(ValueError, match="quantity"):
            _target(TargetSalesUnitFormV2.BUNDLE, quantity=0)

    def test_the_channel_derivation_fails_closed_on_foreign_inputs(self) -> None:
        with pytest.raises(TypeError):
            sales_unit_authority_from_channel("not a channel")  # type: ignore[arg-type]
        with pytest.raises(TypeError):
            sales_unit_authority_from_channel(UNAVAILABLE, "not evidence")  # type: ignore[arg-type]
        # A hand-built OBSERVED channel cannot smuggle in a None kind.
        with pytest.raises(ValueError):
            CandidateSalesUnitEvidenceV2(
                state=PackagingEvidenceStateV2.OBSERVED,
                kind=None,
                quantity=None,
                raw_detail="x",
                source=CandidateEvidenceSourceV2.PUBLISHED_STRUCTURED_FIELD,
            )

    def test_model_claims_never_establish_sales_unit_authority(self) -> None:
        """A model 'packaging matched' claim (matched_attributes) has no
        path into the derivation: the inputs are the recorded channel and
        the explicit target-side evidence only. A MATCH that claims
        packaging agreement on an UNAVAILABLE channel stays UNPROVEN."""
        import inspect

        parameters = inspect.signature(sales_unit_authority_from_channel).parameters
        assert set(parameters) == {"channel", "target_evidence"}

        assessment_v2 = _v2(title=f"Has {REQUEST_MPN} in the title")
        decision = derive_authority_tier_fu3(
            assessment_v2,
            UNAVAILABLE,
            _match(),  # the model may claim whatever; the channel decides
            NO_CTX,
            _strong_profile(),
        )
        assert decision.sales_unit_authority is SalesUnitAuthorityV2.UNPROVEN
        assert decision.tier is AuthorityTier.NEEDS_REVIEW

    def test_case_level_derivation_reads_the_recorded_channel(self) -> None:
        """The FU3 specification entry point: over a recorded Semantic
        MatchCaseV2 the derivation is a pure function of the input's
        explicit channel (zero live work, replayable)."""
        from tests.research.test_semantic_decision_v2 import _case

        default_case = _case()  # live shape: the channel is UNAVAILABLE
        assert default_case.candidate_commercial.sales_unit.state is (
            PackagingEvidenceStateV2.UNAVAILABLE
        )
        assert derive_sales_unit_authority(default_case) is (
            SalesUnitAuthorityV2.UNPROVEN
        )

        observed = _case()
        replaced = dataclasses.replace(
            observed,
            candidate_commercial=dataclasses.replace(
                observed.candidate_commercial,
                sales_unit=_channel(SalesUnitKindV2.SINGLE_UNIT),
            ),
        )
        assert isinstance(replaced, SemanticMatchCaseV2)
        assert derive_sales_unit_authority(replaced) is (
            SalesUnitAuthorityV2.PROVEN_EQUIVALENT
        )
        pack_case = dataclasses.replace(
            observed,
            candidate_commercial=dataclasses.replace(
                observed.candidate_commercial,
                sales_unit=_channel(SalesUnitKindV2.PACK_QUANTITY, quantity=4),
            ),
        )
        assert derive_sales_unit_authority(pack_case) is (
            SalesUnitAuthorityV2.CONTRADICTED
        )
        assert derive_sales_unit_authority(
            pack_case,
            _target(TargetSalesUnitFormV2.PACK_QUANTITY, quantity=4),
        ) is SalesUnitAuthorityV2.PROVEN_EQUIVALENT

    def test_case_level_derivation_fails_closed_on_foreign_input(self) -> None:
        with pytest.raises(TypeError):
            derive_sales_unit_authority("not a case")  # type: ignore[arg-type]


# ===========================================================================
# F5. RESTRICT-ONLY CEILING + FUTURE QUALIFIED-STATE SIMULATION
# ===========================================================================


class TestRestrictOnlyCeiling:
    # -- The §4.1 invariant composition: qualified + STRONG + HIGH +
    #    (reviewed relation where the frozen requirement asks for it) --

    def test_exact_mpn_unknown_packaging_invariant_row(self) -> None:
        """Row 1 / row 11(a): exact title MPN, silent multi-pack shape
        (channel UNAVAILABLE), STRONG product evidence, MATCH + HIGH.
        Under the OLD token the tier is the R14 exposure (AI_ASSISTED);
        under FU3 the restrict-only ceiling holds it at NEEDS_REVIEW."""
        u1 = _v2(title=f"Has {REQUEST_MPN} in the title")
        old = derive_authority_tier_for_contract(
            AUTHORITY_CONTRACT_VERSION_V2, u1, _match(), NO_CTX, _strong_profile()
        )
        new = derive_authority_tier_for_contract(
            AUTHORITY_CONTRACT_VERSION_V2_FU3,
            u1,
            _match(),
            NO_CTX,
            _strong_profile(),
            sales_unit_channel=UNAVAILABLE,
        )
        assert old.tier is AuthorityTier.AI_ASSISTED_COMPARABLE
        assert isinstance(new, AuthorityDecisionV2FU3)
        assert new.tier is AuthorityTier.NEEDS_REVIEW
        assert AuthorityRuleV2FU3.CEILING_SALES_UNIT_NOT_PROVEN in new.fired_rules
        assert new.sales_unit_authority is SalesUnitAuthorityV2.UNPROVEN
        assert new.identity_resolution_bound is IdentityResolutionBoundV2.PART_NUMBER
        # Restrict only: the rest of the audit trail is the frozen one.
        assert new.frozen_fired_rules == old.fired_rules
        assert new.product_evidence_quality is old.product_evidence_quality
        assert new.relationship_authority is old.relationship_authority

    @pytest.mark.parametrize(
        "name,provenances",
        [
            ("u1", NO_CTX),
            ("u2e", NO_CTX),
            ("u4", NO_CTX),
            ("u2n", RELATION_CTX),
            ("u3", RELATION_CTX),
            ("u5_nm1", RELATION_CTX),
            ("u5_nm2", RELATION_CTX),
        ],
        ids=["u1", "u2e", "u4", "u2n", "u3", "u5_nm1", "u5_nm2"],
    )
    def test_qualified_state_simulations_never_auto_price_on_unproven_unit(
        self, name: str, provenances: frozenset[ContextProvenance]
    ) -> None:
        """The §4.1 invariant as a unit test, per identifier shape:
        MATCH + HIGH + STRONG + reviewed relation (where required) +
        unproven unit never reaches the automatic pricing-eligible tier
        under FU3 — while the old token documents the pre-fix exposure
        for the shapes whose frozen requirement is satisfied."""
        builders = {
            "u1": lambda: _v2(title=f"Has {REQUEST_MPN} in the title"),
            "u2e": lambda: _v2(sku=REQUEST_MPN),
            "u4": lambda: _v2(title="Usable title without any MPN"),
            "u2n": lambda: _v2(sku="RETAIL-SKU-1"),
            "u3": lambda: _v2(mpn="ABC"),
            "u5_nm1": lambda: _v2(mpn=f"{REQUEST_MPN}X"),
            "u5_nm2": lambda: _v2(mpn="ABC-124"),
        }
        assessment_v2 = builders[name]()  # type: ignore[assignment]
        old = derive_authority_tier(
            assessment_v2, _match(), provenances, _strong_profile()
        )
        new = derive_authority_tier_fu3(
            assessment_v2, UNAVAILABLE, _match(), provenances, _strong_profile()
        )
        assert new.tier is not AuthorityTier.AI_ASSISTED_COMPARABLE, name
        assert new.tier is AuthorityTier.NEEDS_REVIEW, name
        assert new.sales_unit_authority is SalesUnitAuthorityV2.UNPROVEN
        if old.tier is AuthorityTier.AI_ASSISTED_COMPARABLE:
            # The ceiling fired (old token auto-priced; FU3 did not).
            assert (
                AuthorityRuleV2FU3.CEILING_SALES_UNIT_NOT_PROVEN
                in new.fired_rules
            ), name
            assert new.frozen_fired_rules == old.fired_rules
        else:
            # Already restricted by the frozen requirement ceiling: the
            # FU3 audit trail is exactly the frozen one (no redundant
            # rule) and the tier is unchanged.
            assert (
                AuthorityRuleV2FU3.CEILING_SALES_UNIT_NOT_PROVEN
                not in new.fired_rules
            ), name
            assert new.tier is old.tier, name
            assert new.frozen_fired_rules == old.fired_rules, name

    def test_u3_shared_prefix_variant_never_prices(self) -> None:
        """Row 3: U3 shared-prefix variants — the requirement ceiling
        (no reviewed relation) AND, with a reviewed relation added, the
        unit ceiling both hold the tier at NEEDS_REVIEW; the bound stays
        FAMILY_DESCRIPTION (the prefix is never the complete number)."""
        u3 = _v2(mpn="ABC")
        without_relation = derive_authority_tier_fu3(
            u3, UNAVAILABLE, _match(), NO_CTX, _strong_profile()
        )
        assert without_relation.tier is AuthorityTier.NEEDS_REVIEW
        assert without_relation.identity_resolution_bound is (
            IdentityResolutionBoundV2.FAMILY_DESCRIPTION
        )
        assert AuthorityRuleV2FU3.CEILING_IDENTIFIER_RELATIONSHIP_NOT_ESTABLISHED in (
            without_relation.fired_rules
        )
        with_relation = derive_authority_tier_fu3(
            u3, UNAVAILABLE, _match(), RELATION_CTX, _strong_profile()
        )
        assert with_relation.tier is AuthorityTier.NEEDS_REVIEW
        assert AuthorityRuleV2FU3.CEILING_SALES_UNIT_NOT_PROVEN in (
            with_relation.fired_rules
        )

    def test_manufacturer_authorized_near_miss_unknown_packaging(self) -> None:
        """Row 6: U5 NM-2 + MANUFACTURER_RELATION_AUTHORITY + MATCH + HIGH
        + STRONG: the frozen NM-2 ceiling is cleared by the authority and
        the requirement is satisfied (old token: AI_ASSISTED) — but the
        unit is unproven, so FU3 caps at NEEDS_REVIEW. Identifier
        authority does not establish commercial-unit equivalence."""
        u5 = _v2(mpn="ABC-124")
        assert u5.near_miss_substitution_active
        old = derive_authority_tier(
            u5, _match(), RELATION_CTX, _strong_profile()
        )
        assert old.tier is AuthorityTier.AI_ASSISTED_COMPARABLE
        new = derive_authority_tier_fu3(
            u5, UNAVAILABLE, _match(), RELATION_CTX, _strong_profile()
        )
        assert new.tier is AuthorityTier.NEEDS_REVIEW
        assert AuthorityRuleV2FU3.CEILING_SALES_UNIT_NOT_PROVEN in new.fired_rules
        assert new.identity_resolution_bound is IdentityResolutionBoundV2.PART_NUMBER
        # Unit proven (OBSERVED SINGLE_UNIT): the automatic tier stands.
        proven = derive_authority_tier_fu3(
            u5,
            _channel(SalesUnitKindV2.SINGLE_UNIT),
            _match(),
            RELATION_CTX,
            _strong_profile(),
        )
        assert proven.tier is AuthorityTier.AI_ASSISTED_COMPARABLE
        assert AuthorityRuleV2FU3.CEILING_SALES_UNIT_NOT_PROVEN not in proven.fired_rules
        assert proven.sales_unit_authority is SalesUnitAuthorityV2.PROVEN_EQUIVALENT

    def test_customer_retrieval_alias_unknown_packaging(self) -> None:
        """Row 7: U5 NM-1 + CUSTOMER_RETRIEVAL_RELATION only — zero
        relationship authority: the requirement ceiling holds the tier
        (old token too), the bound is NONE, and a MATCH on this shape is
        the CRITICAL false-MATCH corpus guards against. The unit ceiling
        adds nothing the frozen requirement already restricted (no
        redundant rule)."""
        u5 = _v2(mpn=f"{REQUEST_MPN}X")
        old = derive_authority_tier(u5, _match(), CUSTOMER_CTX, _strong_profile())
        assert old.tier is AuthorityTier.NEEDS_REVIEW
        new = derive_authority_tier_fu3(
            u5, UNAVAILABLE, _match(), CUSTOMER_CTX, _strong_profile()
        )
        assert new.tier is AuthorityTier.NEEDS_REVIEW
        assert new.identity_resolution_bound is IdentityResolutionBoundV2.NONE
        assert AuthorityRuleV2FU3.CEILING_SALES_UNIT_NOT_PROVEN not in new.fired_rules
        assert new.frozen_fired_rules == old.fired_rules

    def test_different_retailer_sku_matching_specifications(self) -> None:
        """Row 4: U2 + SKU_NOT_TARGET with a reviewed relation (requirement
        satisfied, old token auto-prices at STRONG + HIGH + MATCH) — the
        bound is DESCRIPTION and the unit ceiling holds FU3 at
        NEEDS_REVIEW."""
        u2n = _v2(sku="RETAIL-SKU-1")
        old = derive_authority_tier(u2n, _match(), RELATION_CTX, _strong_profile())
        assert old.tier is AuthorityTier.AI_ASSISTED_COMPARABLE
        new = derive_authority_tier_fu3(
            u2n, UNAVAILABLE, _match(), RELATION_CTX, _strong_profile()
        )
        assert new.tier is AuthorityTier.NEEDS_REVIEW
        assert new.identity_resolution_bound is IdentityResolutionBoundV2.DESCRIPTION
        assert AuthorityRuleV2FU3.CEILING_SALES_UNIT_NOT_PROVEN in new.fired_rules

    @pytest.mark.parametrize(
        "kind,quantity",
        [
            (SalesUnitKindV2.PACK_QUANTITY, 4),
            (SalesUnitKindV2.TRAY_OR_FACTORY_PACK, 20),
            (SalesUnitKindV2.BUNDLE, None),
        ],
        ids=["pack-of-4", "tray-of-20", "bundle"],
    )
    def test_published_incompatible_packaging_stays_hard_conflict(
        self, kind: SalesUnitKindV2, quantity: int | None
    ) -> None:
        """Row 8: published incompatible packaging — the model applies the
        absolute rule (NO_MATCH + the packaging conflict class) and the
        frozen HARD_CONFLICT supersession excludes the candidate in BOTH
        tokens, including against an explicit human confirmation."""
        u1 = _v2(title=f"Has {REQUEST_MPN} in the title")
        evaluation = _eval(
            V2SemanticDecision.NO_MATCH,
            V2Confidence.HIGH,
            frozenset(
                {
                    ConflictClass.PACKAGING_QUANTITY
                    if kind is not SalesUnitKindV2.BUNDLE
                    else ConflictClass.BUNDLE
                }
            ),
        )
        channel = _channel(kind, quantity)
        old = derive_authority_tier(u1, evaluation, NO_CTX, None, None)
        assert old.tier is AuthorityTier.HARD_CONFLICT
        new = derive_authority_tier_fu3(u1, channel, evaluation, NO_CTX, None, None)
        assert new.tier is AuthorityTier.HARD_CONFLICT
        assert new.sales_unit_authority is SalesUnitAuthorityV2.CONTRADICTED
        assert AuthorityRuleV2FU3.CEILING_SALES_UNIT_NOT_PROVEN not in new.fired_rules
        assert AuthorityRuleV2FU3.HARD_CONFLICT_SUPERSEDES in new.fired_rules
        # HARD_CONFLICT supersedes HUMAN_CONFIRMED (frozen precedence).
        confirmed = derive_authority_tier_fu3(
            u1, channel, evaluation, NO_CTX, None, HumanReviewStateV2.CONFIRMED
        )
        assert confirmed.tier is AuthorityTier.HARD_CONFLICT
        assert confirmed.tier is not AuthorityTier.HUMAN_CONFIRMED
        assert AuthorityRuleV2FU3.HARD_CONFLICT_SUPERSEDES_HUMAN in confirmed.fired_rules

    def test_internal_contradiction_is_never_no_match_and_never_auto_priced(self) -> None:
        """Row 9: conflicting title/specification evidence — the 2.1
        contract answers UNCERTAIN naming the unpinned dimension and never
        asserts the conflict class; the tier is NEEDS_REVIEW under BOTH
        tokens (the ceiling has no automatic tier to restrict) and the
        bound records DESCRIPTION ground only."""
        u4 = _v2(title="Usable title without any MPN")
        evaluation = _eval(V2SemanticDecision.UNCERTAIN, V2Confidence.HIGH)
        old = derive_authority_tier(u4, evaluation, NO_CTX, _strong_profile())
        assert old.tier is AuthorityTier.NEEDS_REVIEW
        new = derive_authority_tier_fu3(
            u4, UNAVAILABLE, evaluation, NO_CTX, _strong_profile()
        )
        assert new.tier is AuthorityTier.NEEDS_REVIEW
        assert new.tier is old.tier
        assert AuthorityRuleV2FU3.CEILING_SALES_UNIT_NOT_PROVEN not in new.fired_rules
        assert new.identity_resolution_bound is IdentityResolutionBoundV2.DESCRIPTION

    def test_proven_unit_stands_under_fu3(self) -> None:
        """OBSERVED SINGLE_UNIT (PROVEN_EQUIVALENT) against the default
        single-unit target: the automatic tier stands — the ceiling is a
        restrict-only guard on the unproven state, not a blanket cap."""
        for name, assessment_v2 in (
            ("u1", _v2(title=f"Has {REQUEST_MPN} in the title")),
            ("u2e", _v2(sku=REQUEST_MPN)),
            ("u4", _v2(title="Usable title without any MPN")),
        ):
            decision = derive_authority_tier_fu3(
                assessment_v2,
                _channel(SalesUnitKindV2.SINGLE_UNIT),
                _match(),
                NO_CTX,
                _strong_profile(),
            )
            assert decision.tier is AuthorityTier.AI_ASSISTED_COMPARABLE, name
            assert decision.sales_unit_authority is (
                SalesUnitAuthorityV2.PROVEN_EQUIVALENT
            )
            assert AuthorityRuleV2FU3.CEILING_SALES_UNIT_NOT_PROVEN not in decision.fired_rules

    def test_contradicted_unit_does_not_fire_the_ceiling(self) -> None:
        """The ceiling is UNPROVEN-only: a model that violates the
        absolute rule (MATCH with no conflict class on published
        incompatible packaging) is a decision-level contract violation for
        qualification to catch — the derivation records CONTRADICTED and
        applies the frozen tier, never inventing a conflict."""
        u1 = _v2(title=f"Has {REQUEST_MPN} in the title")
        old = derive_authority_tier(u1, _match(), NO_CTX, _strong_profile())
        assert old.tier is AuthorityTier.AI_ASSISTED_COMPARABLE
        decision = derive_authority_tier_fu3(
            u1,
            _channel(SalesUnitKindV2.PACK_QUANTITY, quantity=4),
            _match(),
            NO_CTX,
            _strong_profile(),
        )
        assert decision.sales_unit_authority is SalesUnitAuthorityV2.CONTRADICTED
        assert decision.tier is AuthorityTier.AI_ASSISTED_COMPARABLE
        assert AuthorityRuleV2FU3.CEILING_SALES_UNIT_NOT_PROVEN not in decision.fired_rules

    # -- Human confirmation: explicit, auditable, above the ceiling ------

    def test_explicit_human_confirmation_bypasses_the_ceiling(self) -> None:
        """Row 10: the same silent-multi-pack candidate after an explicit
        human CONFIRM — the overlay applies above the automatic tier
        exactly as with the frozen NM-2 ceiling; precedence
        HARD_CONFLICT > HUMAN_CONFIRMED > AI is unchanged."""
        u1 = _v2(title=f"Has {REQUEST_MPN} in the title")
        without = derive_authority_tier_fu3(
            u1, UNAVAILABLE, _match(), NO_CTX, _strong_profile()
        )
        assert without.tier is AuthorityTier.NEEDS_REVIEW
        confirmed = derive_authority_tier_fu3(
            u1,
            UNAVAILABLE,
            _match(),
            NO_CTX,
            _strong_profile(),
            HumanReviewStateV2.CONFIRMED,
        )
        assert confirmed.tier is AuthorityTier.HUMAN_CONFIRMED
        assert AuthorityRuleV2FU3.HUMAN_CONFIRMED_APPLIED in confirmed.fired_rules
        assert AuthorityRuleV2FU3.CEILING_SALES_UNIT_NOT_PROVEN not in confirmed.fired_rules
        rejected = derive_authority_tier_fu3(
            u1,
            UNAVAILABLE,
            _match(),
            NO_CTX,
            _strong_profile(),
            HumanReviewStateV2.REJECTED,
        )
        assert rejected.tier is AuthorityTier.HUMAN_REJECTED

    def test_a_semantic_match_never_infers_unit_confirmation(self) -> None:
        """Without an explicit human_review input, no combination of
        decision / confidence / bound / provenances produces
        HUMAN_CONFIRMED — a generic semantic MATCH is not unit
        confirmation (and is not any confirmation)."""
        u1 = _v2(title=f"Has {REQUEST_MPN} in the title")
        decision = derive_authority_tier_fu3(
            u1, UNAVAILABLE, _match(), RELATION_CTX, _strong_profile()
        )
        assert decision.tier is not AuthorityTier.HUMAN_CONFIRMED
        assert AuthorityRuleV2FU3.HUMAN_CONFIRMED_APPLIED not in decision.fired_rules

    def test_human_confirmation_above_a_frozen_requirement_ceiling(self) -> None:
        """U3 + no relation (frozen requirement ceiling) + explicit
        CONFIRM: HUMAN_CONFIRMED stands — the FU3 ceiling is
        automatic-tier-only and the frozen human overlay precedence is
        unchanged."""
        u3 = _v2(mpn="ABC")
        decision = derive_authority_tier_fu3(
            u3,
            UNAVAILABLE,
            _match(),
            NO_CTX,
            _strong_profile(),
            HumanReviewStateV2.CONFIRMED,
        )
        assert decision.tier is AuthorityTier.HUMAN_CONFIRMED
        assert AuthorityRuleV2FU3.CEILING_SALES_UNIT_NOT_PROVEN not in decision.fired_rules

    # -- Restrict-only: the ceiling can only ever lower the AI tier ------

    def test_the_ceiling_is_restrict_only_exhaustively(self) -> None:
        """Exhaustive enumeration over every semantic-entry state, every
        evaluation shape, every provenance class, every channel state, and
        every human overlay: the FU3 tier is EXACTLY the frozen tier,
        except that a frozen AI_ASSISTED_COMPARABLE with an UNPROVEN unit
        becomes NEEDS_REVIEW (with the fired ceiling rule). Nothing is
        ever lifted; no other rule is ever added or removed."""
        states = {
            "u1": _v2(title=f"Has {REQUEST_MPN} in the title"),
            "u2e": _v2(sku=REQUEST_MPN),
            "u2n": _v2(sku="RETAIL-SKU-1"),
            "u3": _v2(mpn="ABC"),
            "u4": _v2(title="Usable title without any MPN"),
            "u4e": _v2(mpn="mpn:", title="Usable title with empty MPN field"),
            "u5_nm1": _v2(mpn=f"{REQUEST_MPN}X"),
            "u5_nm2": _v2(mpn="ABC-124"),
        }
        evaluations = (
            None,
            SemanticEvaluationV2.runtime_failure(),
            _match(),
            _match(high=False),
            _eval(V2SemanticDecision.NO_MATCH, V2Confidence.HIGH),
            _eval(
                V2SemanticDecision.NO_MATCH,
                V2Confidence.HIGH,
                frozenset({ConflictClass.PACKAGING_QUANTITY}),
            ),
            _eval(V2SemanticDecision.UNCERTAIN, V2Confidence.HIGH),
            _eval(
                V2SemanticDecision.MATCH,
                V2Confidence.HIGH,
                frozenset({ConflictClass.BRAND}),
            ),
        )
        channels = (
            UNAVAILABLE,
            _channel(SalesUnitKindV2.SINGLE_UNIT),
            _channel(SalesUnitKindV2.PACK_QUANTITY, quantity=4),
            _channel(SalesUnitKindV2.TRAY_OR_FACTORY_PACK, quantity=20),
        )
        humans = (None, HumanReviewStateV2.CONFIRMED, HumanReviewStateV2.REJECTED)
        checked = 0
        for name, assessment_v2 in states.items():
            for evaluation in evaluations:
                for provenances in (NO_CTX, PRODUCT_CTX, RELATION_CTX, CUSTOMER_CTX):
                    for channel in channels:
                        for human in humans:
                            frozen = derive_authority_tier(
                                assessment_v2, evaluation, provenances, None, human
                            )
                            fu3_decision = derive_authority_tier_fu3(
                                assessment_v2,
                                channel,
                                evaluation,
                                provenances,
                                None,
                                human,
                            )
                            unit = sales_unit_authority_from_channel(channel)
                            expected_tier = frozen.tier
                            expected_rules = frozenset(
                                AuthorityRuleV2FU3(rule.value)
                                for rule in frozen.fired_rules
                            )
                            if (
                                frozen.tier is AuthorityTier.AI_ASSISTED_COMPARABLE
                                and unit is SalesUnitAuthorityV2.UNPROVEN
                            ):
                                expected_tier = AuthorityTier.NEEDS_REVIEW
                                expected_rules = expected_rules | frozenset(
                                    {
                                        AuthorityRuleV2FU3.CEILING_SALES_UNIT_NOT_PROVEN
                                    }
                                )
                            assert fu3_decision.tier is expected_tier, (
                                name,
                                evaluation,
                                provenances,
                                channel,
                                human,
                            )
                            assert fu3_decision.fired_rules == expected_rules
                            assert fu3_decision.frozen_fired_rules == (
                                frozenset(
                                    AuthorityRuleV2(rule.value)
                                    for rule in fu3_decision.fired_rules
                                    if rule is not AuthorityRuleV2FU3.CEILING_SALES_UNIT_NOT_PROVEN
                                )
                            )
                            checked += 1
        assert checked == 8 * 8 * 4 * 4 * 3

    def test_the_ceiling_never_touches_the_deterministic_tiers(self) -> None:
        """MACHINE_VERIFIED (verified states) and HARD_CONFLICT /
        EXCLUDED (conflict / unevaluable states) are outside the ceiling's
        reach — the deterministic path never consults the semantic layer
        and the 4A / firewall behavior is byte-unchanged."""
        v_exact = _v2(mpn=REQUEST_MPN)
        decision = derive_authority_tier_fu3(
            v_exact, UNAVAILABLE, None, NO_CTX, None
        )
        assert decision.tier is AuthorityTier.MACHINE_VERIFIED
        assert AuthorityRuleV2FU3.CEILING_SALES_UNIT_NOT_PROVEN not in decision.fired_rules
        # The machine tier carries the PART_NUMBER bound and, for a
        # verified state, the unit question is orthogonal to 4A.
        assert decision.identity_resolution_bound is IdentityResolutionBoundV2.PART_NUMBER

        c1 = _v2(mpn="ZZZ-000")
        conflict = derive_authority_tier_fu3(c1, UNAVAILABLE, None, NO_CTX, None)
        assert conflict.tier is AuthorityTier.HARD_CONFLICT
        assert AuthorityRuleV2FU3.CEILING_SALES_UNIT_NOT_PROVEN not in conflict.fired_rules

        e2 = _v2(title=None)
        unevaluable = derive_authority_tier_fu3(e2, UNAVAILABLE, None, NO_CTX, None)
        assert unevaluable.tier is AuthorityTier.EXCLUDED_LOW_CONFIDENCE
        assert AuthorityRuleV2FU3.CEILING_SALES_UNIT_NOT_PROVEN not in unevaluable.fired_rules

    def test_runtime_failure_stays_semantic_unavailable(self) -> None:
        u1 = _v2(title=f"Has {REQUEST_MPN} in the title")
        decision = derive_authority_tier_fu3(
            u1,
            UNAVAILABLE,
            SemanticEvaluationV2.runtime_failure(),
            NO_CTX,
            _strong_profile(),
        )
        assert decision.tier is AuthorityTier.SEMANTIC_UNAVAILABLE
        assert AuthorityRuleV2FU3.CEILING_SALES_UNIT_NOT_PROVEN not in decision.fired_rules

    def test_the_ceiling_can_not_be_bypassed_by_qualified_state(self) -> None:
        """The full §4.1 composition at once — qualified route simulated
        (STRONG profile reachable), MATCH + HIGH, reviewed relation where
        required, UNAVAILABLE channel: no argument order, provenance set,
        or profile shape re-opens AI_ASSISTED_COMPARABLE under FU3."""
        shapes = (
            _v2(title=f"Has {REQUEST_MPN} in the title"),
            _v2(sku=REQUEST_MPN),
            _v2(title="Usable title without any MPN"),
            _v2(sku="RETAIL-SKU-1"),
            _v2(mpn="ABC"),
            _v2(mpn=f"{REQUEST_MPN}X"),
            _v2(mpn="ABC-124"),
        )
        for assessment_v2 in shapes:
            for provenances in (NO_CTX, RELATION_CTX, CUSTOMER_CTX | PRODUCT_CTX):
                decision = derive_authority_tier_fu3(
                    assessment_v2,
                    UNAVAILABLE,
                    _match(),
                    provenances,
                    _strong_profile(),
                )
                assert decision.tier is not AuthorityTier.AI_ASSISTED_COMPARABLE
                assert decision.sales_unit_authority is SalesUnitAuthorityV2.UNPROVEN


class TestFu3DecisionDataContract:
    def test_the_rule_vocabulary_is_the_frozen_set_plus_exactly_one(self) -> None:
        frozen_values = {rule.value for rule in AuthorityRuleV2}
        fu3_values = {rule.value for rule in AuthorityRuleV2FU3}
        assert fu3_values == frozen_values | {"CEILING_SALES_UNIT_NOT_PROVEN"}
        assert len(AuthorityRuleV2FU3) == len(AuthorityRuleV2) + 1

    def test_the_decision_is_immutable_and_fail_closed(self) -> None:
        u1 = _v2(title=f"Has {REQUEST_MPN} in the title")
        decision = derive_authority_tier_fu3(
            u1, UNAVAILABLE, _match(), NO_CTX, _strong_profile()
        )
        assert dataclasses.is_dataclass(decision)
        with pytest.raises(dataclasses.FrozenInstanceError):
            decision.tier = AuthorityTier.HUMAN_CONFIRMED  # type: ignore[misc]
        # A hand-built decision cannot express the firewall violation:
        # AI_ASSISTED + UNPROVEN is un-constructible.
        with pytest.raises(ValueError, match="unproven"):
            AuthorityDecisionV2FU3(
                tier=AuthorityTier.AI_ASSISTED_COMPARABLE,
                fired_rules=frozenset(
                    {AuthorityRuleV2FU3.SEMANTIC_OUTCOME_MATRIX}
                ),
                product_evidence_quality=ProductEvidenceQuality.STRONG,
                relationship_authority=RelationshipAuthority.NOT_ESTABLISHED,
                identity_resolution_bound=IdentityResolutionBoundV2.PART_NUMBER,
                sales_unit_authority=SalesUnitAuthorityV2.UNPROVEN,
            )
        # The ceiling rule must accompany UNPROVEN + NEEDS_REVIEW.
        with pytest.raises(ValueError, match="ceiling"):
            AuthorityDecisionV2FU3(
                tier=AuthorityTier.NEEDS_REVIEW,
                fired_rules=frozenset(
                    {
                        AuthorityRuleV2FU3.SEMANTIC_OUTCOME_MATRIX,
                        AuthorityRuleV2FU3.CEILING_SALES_UNIT_NOT_PROVEN,
                    }
                ),
                product_evidence_quality=ProductEvidenceQuality.STRONG,
                relationship_authority=RelationshipAuthority.NOT_ESTABLISHED,
                identity_resolution_bound=IdentityResolutionBoundV2.PART_NUMBER,
                sales_unit_authority=SalesUnitAuthorityV2.PROVEN_EQUIVALENT,
            )
        # Non-empty rule trail is mandatory (frozen discipline).
        with pytest.raises(ValueError):
            AuthorityDecisionV2FU3(
                tier=AuthorityTier.NEEDS_REVIEW,
                fired_rules=frozenset(),
                product_evidence_quality=ProductEvidenceQuality.STRONG,
                relationship_authority=RelationshipAuthority.NOT_ESTABLISHED,
                identity_resolution_bound=IdentityResolutionBoundV2.PART_NUMBER,
                sales_unit_authority=SalesUnitAuthorityV2.UNPROVEN,
            )
        with pytest.raises(TypeError):
            AuthorityDecisionV2FU3(
                tier=AuthorityTier.NEEDS_REVIEW,  # type: ignore[arg-type]
                fired_rules="not a frozenset",  # type: ignore[arg-type]
                product_evidence_quality=ProductEvidenceQuality.STRONG,
                relationship_authority=RelationshipAuthority.NOT_ESTABLISHED,
                identity_resolution_bound=IdentityResolutionBoundV2.PART_NUMBER,
                sales_unit_authority=SalesUnitAuthorityV2.UNPROVEN,
            )

    def test_the_bound_table_entries_are_immutable(self) -> None:
        assert isinstance(IDENTITY_RESOLUTION_BOUND_TABLE, tuple)
        for entry in IDENTITY_RESOLUTION_BOUND_TABLE:
            assert isinstance(entry, tuple) and len(entry) == 3
        with pytest.raises(TypeError):
            IDENTITY_RESOLUTION_BOUND_TABLE[0] = IDENTITY_RESOLUTION_BOUND_TABLE[0]

    def test_the_module_has_no_mutable_global_state(self) -> None:
        mutable = {
            name: type(value).__name__
            for name, value in vars(fu3).items()
            if not name.startswith("__") and isinstance(value, (dict, list, set))
        }
        assert not mutable, f"mutable global state found: {mutable}"


# ===========================================================================
# F6. REACHABILITY ISOLATION (no live wiring, no pricing path)
# ===========================================================================


class TestReachabilityIsolation:
    def _imported_modules(self, path: Path) -> set[str]:
        modules: set[str] = set()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                modules.add(node.module)
        return modules

    def test_no_live_module_references_the_fu3_contract(self) -> None:
        """The FU3 contract is unreachable from the live V2 runtime
        wiring, persistence, pricing, and presentation: no production
        module outside the research contract surface references it
        (AST import scan + lexical scan of the module name and every
        FU3-specific public symbol)."""
        fu3_symbol = "product_intelligence.research.semantic_authority_fu3"
        lexical_markers = (
            "semantic_authority_fu3",
            "AuthorityDecisionV2FU3",
            "derive_authority_tier_fu3",
            "IdentityResolutionBoundV2",
            "SalesUnitAuthorityV2",
            "CEILING_SALES_UNIT_NOT_PROVEN",
            "S2A_FU3",
        )
        allowed_paths = {FU3_MODULE_PATH, PACKAGE_ROOT / "research" / "__init__.py"}
        for layer in ("research", "execution", "semantic", "runs", "web", "providers"):
            root = PACKAGE_ROOT / layer
            assert root.is_dir()
            for path in sorted(root.rglob("*.py")):
                if path in allowed_paths:
                    continue
                imported = self._imported_modules(path)
                offending = {
                    module
                    for module in imported
                    if module == fu3_symbol or module.startswith(fu3_symbol + ".")
                }
                assert not offending, f"{path} imports the FU3 contract module"
                source = path.read_text(encoding="utf-8")
                for marker in lexical_markers:
                    assert marker not in source, (
                        f"{path.name} references the FU3 contract surface "
                        f"({marker!r}); the new token is unreachable from "
                        "live wiring"
                    )

    def test_the_fu3_module_is_research_pure(self) -> None:
        source = FU3_MODULE_PATH.read_text(encoding="utf-8")
        modules = self._imported_modules(FU3_MODULE_PATH)
        disallowed = {
            module
            for module in modules
            if module.split(".")[0] != "product_intelligence"
            and module.split(".")[0] not in sys.stdlib_module_names
        }
        assert not disallowed, f"the FU3 contract imports {sorted(disallowed)}"
        for forbidden in (
            "django",
            "product_intelligence.runs",
            "product_intelligence.providers",
            "product_intelligence.evaluation",
            "product_intelligence.web",
            "product_intelligence.execution",
            "product_intelligence.semantic",
        ):
            offending = {
                module
                for module in modules
                if module == forbidden or module.startswith(forbidden + ".")
            }
            assert not offending, f"the FU3 contract imports {sorted(offending)}"
        for io_module in (
            "requests",
            "httpx",
            "urllib",
            "socket",
            "ssl",
            "http",
            "pathlib",
            "sqlite3",
            "os",
            "shutil",
            "tempfile",
            "subprocess",
            "webbrowser",
            "time",
            "datetime",
            "decimal",
            "statistics",
            "math",
        ):
            offending = {
                module
                for module in modules
                if module == io_module or module.startswith(io_module + ".")
            }
            assert not offending, f"the FU3 contract performs I/O: {offending}"
        for clock_token in ("utcnow", "datetime.now", "time.time", "time.monotonic"):
            assert clock_token not in source

    def test_the_live_v2_execution_still_derives_under_the_frozen_token(self) -> None:
        from product_intelligence.research.semantic_decision_v2 import (
            AUTHORITY_CONTRACT_VERSION_V2 as adapter_token,
            V2_AUTHORITY_QUALIFIED,
        )

        assert adapter_token == "SEMANTIC_AUTHORITY_V2_S2A_FU2"
        assert V2_AUTHORITY_QUALIFIED is False

        from product_intelligence.semantic import runtime_v2

        assert runtime_v2.V2_AUTHORITY_QUALIFIED is False
        assert runtime_v2.SEMANTIC_PROMPT_VERSION_V2 == "2.0"

    def test_no_v2_pricing_path_is_activated(self) -> None:
        """Machine Price / Reviewed Price behavior is byte-unchanged: the
        frozen aggregation surface owns no FU3 symbol and no V2 tier
        input, and the FU3 ceiling tier (NEEDS_REVIEW) is not
        pricing-eligible under the frozen summary contract."""
        from product_intelligence.research import PRICING_ELIGIBLE_TIERS
        from product_intelligence.research.aggregation import (
            aggregate_reviewed_listing_prices,
        )

        assert AuthorityTier.NEEDS_REVIEW not in PRICING_ELIGIBLE_TIERS
        assert aggregate_reviewed_listing_prices.__module__ == (
            "product_intelligence.research.aggregation"
        )
        for path in (
            PACKAGE_ROOT / "research" / "aggregation.py",
            PACKAGE_ROOT / "research" / "matching.py",
        ):
            source = path.read_text(encoding="utf-8")
            assert "SalesUnitAuthorityV2" not in source
            assert "semantic_authority_fu3" not in source

    def test_the_fu3_module_names_no_vendor_or_caller_system(self) -> None:
        from tests.domain.test_domain_boundaries import (
            CALLER_TOKENS,
            VENDOR_TOKENS,
            _find_tokens,
        )

        source = FU3_MODULE_PATH.read_text(encoding="utf-8")
        assert not _find_tokens(source, VENDOR_TOKENS)
        assert not _find_tokens(source, CALLER_TOKENS)
