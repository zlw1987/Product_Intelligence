"""Binding / adapter / replay + the sales-unit-blindness proof
(Q3-B5-P1, T2).

* the separately versioned 2.1 binding is drift-pinned across every
  surface that names it (the semantic layer's 2.1 owner, the capture
  pins, the corpus loader's known bindings);
* cross-version replay refusal in both directions: a corpus version is
  only interpretable under the production binding it was sealed with
  (1.0.0 <-> the frozen 2.0 binding; 1.1.0 <-> the separately
  versioned 2.1 binding); a capture of one prompt version is never
  reinterpreted against a corpus sealed under another; a report of one
  version fails against the other version's corpus;
* the production V2 persistence adapter is unchanged: the live record
  type and the codec registry still know exactly the V1 + frozen 2.0
  bindings - the 2.1 binding is qualification-record identity (bound
  into the separately versioned FU3 authority token per the Q3-B4
  AD-Q3B4-5 ordering decision), NOT a registered production record
  binding; no production record can currently carry it;
* the sales-unit-blindness of the frozen derivation is pinned as a
  DOCUMENTED PROPERTY (Q3-B3-FU2 section 3.3 / Q3-B4 DEFECT-2): a
  SU-UNK MATCH and a SU-EQ MATCH of identical decision / confidence /
  quality / conflicts / substate / provenances derive IDENTICAL tiers
  and IDENTICAL pricing eligibility under the frozen derivation - and
  the separately versioned FU3 derivation is the one that distinguishes
  them (the restrict-only ceiling), while the frozen derivation is
  byte- and behavior-unchanged.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from tests.evaluation.semantic_v2._q3a_helpers import (
    CORPUS_2_1_PATH,
    CORPUS_PATH,
    POLICY_PATH,
    load_corpus_bundle,
    primary_route,
    write_capture,
)
from tests.evaluation.semantic_v2._q3a_fu1_helpers import (
    write_direct_capture,
)
from product_intelligence.domain import ResearchRequest
from product_intelligence.evaluation.semantic_v2.capture import (
    CaptureIntegrityError,
    PROMPT_VERSION_V2,
    PROMPT_VERSION_V2_1,
    V2_1_CONTRACT_BINDING,
    load_capture,
    verify_capture_against_corpus,
)
from product_intelligence.evaluation.semantic_v2.corpus import (
    CorpusIntegrityError,
    KNOWN_PRODUCTION_BINDINGS,
    load_corpus,
)
from product_intelligence.evaluation.semantic_v2.direct_capture import (
    DIRECT_KNOWN_PROMPT_VERSIONS,
    DirectCaptureIntegrityError,
    load_direct_capture,
    verify_direct_capture_against_corpus,
)
from product_intelligence.evaluation.semantic_v2.evaluator import (
    QualificationContractError,
    evaluate_direct_for_model,
    evaluate_for_model,
)
from product_intelligence.evaluation.semantic_v2.policy import load_policy
from product_intelligence.evaluation.semantic_v2.report import (
    ReportError,
    verify_direct_report,
    verify_report,
)
from product_intelligence.research import (
    AUTHORITY_CONTRACT_VERSION_V2,
    AuthorityTier,
    CandidateProductEvidenceSource,
    ContextProvenance,
    ExtractionMethod,
    IdentityStateAssessmentV2,
    ListingObservation,
    ProductEvidenceDimension,
    ProductEvidenceFactV2,
    ProductEvidenceProfileV2,
    ProductEvidenceQuality,
    PRICING_ELIGIBLE_TIERS,
    SALES_UNIT_EVIDENCE_UNAVAILABLE,
    SemanticEvaluationV2,
    V2Confidence,
    V2SemanticDecision,
    V2_CONTRACT_BINDING,
    V2_AUTHORITY_QUALIFIED,
    assess_listing_identity,
    build_semantic_match_case_v2,
    build_v2_product_evidence_profile,
    derive_identity_state_v2,
    normalize_listing_observation,
)
from product_intelligence.research import semantic_authority_fu3 as fu3
from product_intelligence.research.semantic_decision_replay import (
    SUPPORTED_CONTRACT_BINDINGS,
)
from product_intelligence.semantic.contract_v2 import (
    SEMANTIC_PROMPT_VERSION_V2,
)
from product_intelligence.semantic.contract_v2_1 import (
    SEMANTIC_PROMPT_VERSION_V2_1,
)

REQUEST_MPN = "ABC-123"
TITLE_SOURCES = frozenset({CandidateProductEvidenceSource.LISTING_PRODUCT_TITLE})


# ===========================================================================
# Drift pins: the 2.1 identity is one constant on every surface
# ===========================================================================


class TestBindingDriftPins:
    def test_the_2_1_binding_is_drift_pinned(self) -> None:
        assert V2_1_CONTRACT_BINDING == (
            "V2",
            "2.1",
            1,
            1,
            "SEMANTIC_AUTHORITY_V2_S2A_FU3",
        )
        assert V2_1_CONTRACT_BINDING[4] == fu3.AUTHORITY_CONTRACT_VERSION_V2_FU3
        assert PROMPT_VERSION_V2_1 == SEMANTIC_PROMPT_VERSION_V2_1 == "2.1"
        assert PROMPT_VERSION_V2 == SEMANTIC_PROMPT_VERSION_V2 == "2.0"
        assert KNOWN_PRODUCTION_BINDINGS == frozenset(
            {tuple(V2_CONTRACT_BINDING), tuple(V2_1_CONTRACT_BINDING)}
        )
        assert DIRECT_KNOWN_PROMPT_VERSIONS == frozenset(
            {"2.0", "2.1"}
        )

    def test_the_frozen_2_0_binding_is_unchanged(self) -> None:
        assert V2_CONTRACT_BINDING == (
            "V2",
            "2.0",
            1,
            1,
            "SEMANTIC_AUTHORITY_V2_S2A_FU2",
        )
        assert AUTHORITY_CONTRACT_VERSION_V2 == "SEMANTIC_AUTHORITY_V2_S2A_FU2"
        assert V2_AUTHORITY_QUALIFIED is False


# ===========================================================================
# The production adapter is unchanged: the 2.1 binding is not a
# registered production record binding
# ===========================================================================


class TestProductionAdapterUnchanged:
    def test_the_codec_registry_still_knows_exactly_the_v1_and_2_0_bindings(
        self,
    ) -> None:
        assert tuple(V2_1_CONTRACT_BINDING) not in {
            tuple(b) for b in SUPPORTED_CONTRACT_BINDINGS
        }
        assert tuple(V2_CONTRACT_BINDING) in {
            tuple(b) for b in SUPPORTED_CONTRACT_BINDINGS
        }

    def test_the_live_v2_record_type_still_pins_the_frozen_binding(self) -> None:
        from product_intelligence.research.semantic_decision_v2 import (
            AUTHORITY_CONTRACT_VERSION_V2 as adapter_token,
            PROMPT_VERSION_V2 as adapter_prompt,
            V2_CONTRACT_BINDING as adapter_binding,
            V2_AUTHORITY_QUALIFIED as adapter_marker,
        )

        assert adapter_token == "SEMANTIC_AUTHORITY_V2_S2A_FU2"
        assert adapter_prompt == "2.0"
        assert adapter_binding == V2_CONTRACT_BINDING
        assert adapter_marker is False

    def test_an_fu3_bound_payload_is_refused_by_the_production_codec(
        self,
    ) -> None:
        from product_intelligence.research.semantic_decision_codec import (
            SemanticDecisionCodecError,
            decode_semantic_decision_record,
        )
        from product_intelligence.research.semantic_decision_v2 import (
            SEMANTIC_V2_ADAPTER,
        )

        # A V2-shaped payload whose binding carries the separately
        # versioned FU3 token: the universal envelope dispatches to the
        # registered V2 adapter, whose strict contract check refuses
        # the foreign prompt axis / authority token (no registered
        # adapter owns the 2.1 binding - it is qualification-record
        # identity, not a production record binding).
        payload = {
            "envelope_schema_version": 1,
            "schema_version": 1,
            "contract": {
                "semantic_contract_version": "V2",
                "prompt_version": "2.1",
                "input_schema_version": 1,
                "output_schema_version": 1,
                "authority_contract_version": fu3.AUTHORITY_CONTRACT_VERSION_V2_FU3,
            },
            "binding": {
                "run_id": "00000000-0000-0000-0000-000000000000",
                "assessment_index": 0,
                "source_url": "https://example.com/x",
            },
        }
        with pytest.raises(SemanticDecisionCodecError):
            decode_semantic_decision_record(payload, schema_version=1)
        assert SEMANTIC_V2_ADAPTER.supported_bindings == (
            V2_CONTRACT_BINDING,
        )


# ===========================================================================
# Cross-version corpus loading (both directions, fail closed)
# ===========================================================================


def _write_corpus(tmp_path: Path, doc: dict) -> Path:
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


class TestCrossVersionCorpusRefusal:
    @pytest.fixture(scope="class")
    def doc_2_1(self):
        return json.loads(CORPUS_2_1_PATH.read_text(encoding="utf-8"))

    @pytest.fixture(scope="class")
    def doc_2_0(self):
        return json.loads(CORPUS_PATH.read_text(encoding="utf-8"))

    def test_1_0_0_under_the_2_1_binding_fails_closed(
        self, tmp_path, doc_2_1
    ) -> None:
        doc = deepcopy(doc_2_1)
        doc["corpus_version"] = "1.0.0"
        with pytest.raises(CorpusIntegrityError, match="sealed under"):
            load_corpus(_write_corpus(tmp_path, doc))

    def test_2_1_prompt_axis_with_the_frozen_token_fails_closed(
        self, tmp_path, doc_2_1
    ) -> None:
        doc = deepcopy(doc_2_1)
        doc["semantic_contract_binding"] = [
            "V2",
            "2.1",
            1,
            1,
            "SEMANTIC_AUTHORITY_V2_S2A_FU2",
        ]
        with pytest.raises(CorpusIntegrityError, match="known production"):
            load_corpus(_write_corpus(tmp_path, doc))

    def test_1_1_0_under_the_2_0_binding_fails_closed(
        self, tmp_path, doc_2_0
    ) -> None:
        doc = deepcopy(doc_2_0)
        doc["corpus_version"] = "1.1.0"
        with pytest.raises(CorpusIntegrityError, match="sealed under"):
            load_corpus(_write_corpus(tmp_path, doc))

    def test_an_unknown_future_binding_fails_closed(
        self, tmp_path, doc_2_1
    ) -> None:
        doc = deepcopy(doc_2_1)
        doc["semantic_contract_binding"] = [
            "V2",
            "2.2",
            1,
            1,
            "SEMANTIC_AUTHORITY_V2_S2A_FU3",
        ]
        with pytest.raises(CorpusIntegrityError, match="known production"):
            load_corpus(_write_corpus(tmp_path, doc))


# ===========================================================================
# Cross-version capture refusal (both directions, both modes)
# ===========================================================================


class TestCrossVersionCaptureRefusal:
    @pytest.fixture(scope="class")
    def corpus_2_0(self):
        return load_corpus(CORPUS_PATH)

    @pytest.fixture(scope="class")
    def corpus_2_1(self):
        return load_corpus(CORPUS_2_1_PATH)

    def test_a_2_0_direct_capture_refused_against_the_1_1_0_corpus(
        self, tmp_path, corpus_2_0, corpus_2_1
    ) -> None:
        # Untampered: a 2.0 capture is bound to the 1.0.0 corpus identity
        # and is refused against the 1.1.0 re-seal (different corpus).
        path = write_direct_capture(tmp_path / "d.json", corpus_2_0)
        capture = load_direct_capture(path)
        with pytest.raises(
            DirectCaptureIntegrityError, match="different corpus"
        ):
            verify_direct_capture_against_corpus(capture, corpus_2_1)
        # Tampered (the cross-version attack): the corpus identity is
        # moved to the 1.1.0 re-seal while the prompt axis stays 2.0 -
        # the axis cross-check refuses it.
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        doc["corpus_version"] = corpus_2_1.corpus_version
        doc["corpus_digest"] = corpus_2_1.corpus_digest
        Path(path).write_text(json.dumps(doc), encoding="utf-8")
        tampered = load_direct_capture(path)
        with pytest.raises(
            DirectCaptureIntegrityError, match="prompt axis"
        ):
            verify_direct_capture_against_corpus(tampered, corpus_2_1)
        with pytest.raises(QualificationContractError):
            evaluate_direct_for_model(corpus_2_1, tampered, *primary_route())

    def test_a_2_1_direct_capture_refused_against_the_1_0_0_corpus(
        self, tmp_path, corpus_2_0, corpus_2_1
    ) -> None:
        # Untampered: a 2.1 capture is bound to the 1.1.0 corpus identity
        # and is refused against the 1.0.0 corpus (different corpus).
        path = write_direct_capture(
            tmp_path / "d.json", corpus_2_1, prompt_version="2.1"
        )
        capture = load_direct_capture(path)
        assert capture.prompt_version == "2.1"
        with pytest.raises(
            DirectCaptureIntegrityError, match="different corpus"
        ):
            verify_direct_capture_against_corpus(capture, corpus_2_0)
        # Tampered (the cross-version attack): the corpus identity is
        # moved back to 1.0.0 while the prompt axis stays 2.1.
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        doc["corpus_version"] = corpus_2_0.corpus_version
        doc["corpus_digest"] = corpus_2_0.corpus_digest
        Path(path).write_text(json.dumps(doc), encoding="utf-8")
        tampered = load_direct_capture(path)
        with pytest.raises(
            DirectCaptureIntegrityError, match="prompt axis"
        ):
            verify_direct_capture_against_corpus(tampered, corpus_2_0)
        with pytest.raises(QualificationContractError):
            evaluate_direct_for_model(corpus_2_0, tampered, *primary_route())

    def test_a_2_1_direct_capture_loads_and_verifies_on_its_corpus(
        self, tmp_path, corpus_2_1
    ) -> None:
        path = write_direct_capture(tmp_path / "d.json", corpus_2_1)
        capture = load_direct_capture(path)
        assert capture.prompt_version == "2.1"
        verify_direct_capture_against_corpus(capture, corpus_2_1)  # no raise

    def test_an_unknown_prompt_axis_fails_closed_at_load(
        self, tmp_path, corpus_2_0
    ) -> None:
        path = write_direct_capture(
            tmp_path / "d.json", corpus_2_0, prompt_version="2.2"
        )
        with pytest.raises(
            DirectCaptureIntegrityError, match="prompt_version"
        ):
            load_direct_capture(path)

    def test_the_production_route_loader_stays_2_0_only(
        self, tmp_path, corpus_2_1
    ) -> None:
        # A production-route capture naming the 2.1 prompt is outside
        # the frozen production schema (the live runtime executes the
        # frozen 2.0 builder) - refused at load.
        path = write_capture(
            tmp_path / "c.json", corpus_2_1
        )
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        doc["prompt_version"] = "2.1"
        Path(path).write_text(json.dumps(doc), encoding="utf-8")
        with pytest.raises(CaptureIntegrityError, match="prompt_version"):
            load_capture(path)

    def test_a_2_0_production_capture_refused_against_the_1_1_0_corpus(
        self, tmp_path, corpus_2_1
    ) -> None:
        # A 2.0-prompt capture bound to the 1.1.0 corpus identity
        # (version / digest moved, prompt axis frozen): the corpus
        # binding says 2.1 - cross-version reinterpretation refused.
        path = write_capture(tmp_path / "c.json", corpus_2_1)
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        doc["prompt_version"] = "2.0"
        Path(path).write_text(json.dumps(doc), encoding="utf-8")
        capture = load_capture(path)
        with pytest.raises(CaptureIntegrityError, match="prompt axis"):
            verify_capture_against_corpus(capture, corpus_2_1)
        with pytest.raises(QualificationContractError):
            evaluate_for_model(corpus_2_1, capture, *primary_route())


# ===========================================================================
# Cross-version report refusal (both directions)
# ===========================================================================


class TestCrossVersionReportRefusal:
    def test_the_committed_2_0_baseline_refused_on_the_1_1_0_corpus(
        self,
    ) -> None:
        from tests.evaluation.semantic_v2._q3a_helpers import (
            BASELINE_REPORT_DIR,
        )

        c11 = load_corpus(CORPUS_2_1_PATH)
        for path in sorted(BASELINE_REPORT_DIR.glob("*__report.json")):
            report = json.loads(path.read_text(encoding="utf-8"))
            with pytest.raises(ReportError):
                verify_report(report, c11)

    def test_the_committed_2_1_baseline_refused_on_the_1_0_0_corpus(
        self,
    ) -> None:
        from tests.evaluation.semantic_v2._q3a_helpers import (
            BASELINE_2_1_REPORT_DIR,
        )

        c10 = load_corpus(CORPUS_PATH)
        for path in sorted(BASELINE_2_1_REPORT_DIR.glob("*__report.json")):
            report = json.loads(path.read_text(encoding="utf-8"))
            with pytest.raises(ReportError):
                verify_report(report, c10)
            with pytest.raises(ReportError):
                verify_direct_report(report, c10)


# ===========================================================================
# The sales-unit-blindness of the FROZEN derivation (Q3-B3-FU2 section
# 3.3 / Q3-B4 DEFECT-2) - pinned as a documented property, and the
# separately versioned FU3 derivation as the one that distinguishes
# ===========================================================================


def _u1_assessment() -> IdentityStateAssessmentV2:
    """A recorded U1 (exact title MPN, identity wording) assessment -
    the A9 / row-11(a) shape: the strongest part-number ground."""
    observation = ListingObservation(
        source_url="https://example.com/product",
        extraction_method=ExtractionMethod.JSON_LD,
        product_title="Has ABC-123 in the title",
        brand_text=None,
        manufacturer_part_number_text=None,
        sku_text=None,
        price_text="100",
        currency_text="USD",
        availability_text="In stock",
        condition_text="New",
        seller_text=None,
    )
    normalized = normalize_listing_observation(observation)
    request = ResearchRequest(REQUEST_MPN, "A test product")
    assessment = assess_listing_identity(request, normalized)
    return derive_identity_state_v2(assessment)


def _strong_profile() -> ProductEvidenceProfileV2:
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


def _match_eval() -> SemanticEvaluationV2:
    return SemanticEvaluationV2.evaluated(
        V2SemanticDecision.MATCH,
        V2Confidence.HIGH,
        frozenset(),
    )


class TestSalesUnitBlindnessDocumentedProperty:
    """Q3-B3-FU2 section 3.3 (T2): a SU-UNK MATCH and a SU-EQ MATCH of
    identical decision / confidence / quality / conflicts / substate /
    provenances derive IDENTICAL tiers and IDENTICAL pricing
    eligibility under the FROZEN derivation - the architectural
    limitation 2.1 states and does not fix. The separately versioned
    FU3 derivation (the Q3-B4 firewall) is the one that distinguishes
    them; the frozen derivation is byte- and behavior-unchanged."""

    def test_the_frozen_derivation_is_structurally_sales_unit_blind(
        self,
    ) -> None:
        from product_intelligence.research import (
            CandidateEvidenceSourceV2,
            CandidateSalesUnitEvidenceV2,
            PackagingEvidenceStateV2,
            SalesUnitKindV2,
        )

        assessment = _u1_assessment()  # A9 / row-11(a) shape: the
        # strongest part-number ground (U1 identity wording).
        profile = _strong_profile()  # the future-qualified-state input
        evaluation = _match_eval()  # MATCH + HIGH + clean
        no_ctx = frozenset()

        # Under the FROZEN token the contract has NO sales-unit input
        # at all: passing one is contract misuse (fail closed), and the
        # two recorded channel states (the live UNAVAILABLE absence vs
        # an OBSERVED proven single unit) are therefore indistinguishable
        # to the derivation by construction.
        with pytest.raises(ValueError, match="no sales-unit input"):
            fu3.derive_authority_tier_for_contract(
                fu3.AUTHORITY_CONTRACT_VERSION_V2,
                assessment,
                evaluation,
                no_ctx,
                profile,
                None,
                sales_unit_channel=SALES_UNIT_EVIDENCE_UNAVAILABLE,
            )
        frozen = fu3.derive_authority_tier_for_contract(
            fu3.AUTHORITY_CONTRACT_VERSION_V2,
            assessment,
            evaluation,
            no_ctx,
            profile,
            None,
        )
        # The R14 exposure under the frozen token (future qualified
        # state: STRONG + HIGH + clean + U1 NOT_REQUIRED): the tier is
        # the pricing-eligible automatic comparable - identically for a
        # proven single unit and for a recorded absence (the tier cannot
        # tell them apart).
        assert frozen.tier is AuthorityTier.AI_ASSISTED_COMPARABLE
        assert frozen.tier in PRICING_ELIGIBLE_TIERS
        assert frozen.product_evidence_quality is ProductEvidenceQuality.STRONG

        # The separately versioned FU3 derivation distinguishes the two
        # recorded states (the firewall): SU-UNK caps at NEEDS_REVIEW
        # (not pricing-eligible), SU-EQ stands.
        su_eq_channel = CandidateSalesUnitEvidenceV2(
            state=PackagingEvidenceStateV2.OBSERVED,
            kind=SalesUnitKindV2.SINGLE_UNIT,
            quantity=None,
            raw_detail="published packaging field",
            source=CandidateEvidenceSourceV2.PUBLISHED_STRUCTURED_FIELD,
        )
        fu3_unk = fu3.derive_authority_tier_for_contract(
            fu3.AUTHORITY_CONTRACT_VERSION_V2_FU3,
            assessment,
            evaluation,
            no_ctx,
            profile,
            None,
            sales_unit_channel=SALES_UNIT_EVIDENCE_UNAVAILABLE,
        )
        fu3_eq = fu3.derive_authority_tier_for_contract(
            fu3.AUTHORITY_CONTRACT_VERSION_V2_FU3,
            assessment,
            evaluation,
            no_ctx,
            profile,
            None,
            sales_unit_channel=su_eq_channel,
        )
        assert fu3_unk.sales_unit_authority is fu3.SalesUnitAuthorityV2.UNPROVEN
        assert fu3_unk.tier is AuthorityTier.NEEDS_REVIEW
        assert fu3_unk.tier not in PRICING_ELIGIBLE_TIERS
        assert (
            fu3.AuthorityRuleV2FU3.CEILING_SALES_UNIT_NOT_PROVEN
            in fu3_unk.fired_rules
        )
        assert fu3_eq.sales_unit_authority is (
            fu3.SalesUnitAuthorityV2.PROVEN_EQUIVALENT
        )
        assert fu3_eq.tier is AuthorityTier.AI_ASSISTED_COMPARABLE

    def test_unavailable_never_derives_proven_equivalent(self) -> None:
        # The recorded absence is never equivalence - the fail-closed
        # default for every target-side shape.
        assert (
            fu3.derive_sales_unit_authority(_case_for_channel_check())
            is fu3.SalesUnitAuthorityV2.UNPROVEN
        )

    def test_the_model_response_never_feeds_the_unit_authority(self) -> None:
        # The sales-unit derivation takes the RECORDED channel and the
        # optional target-side evidence only: a model MATCH that claims
        # "packaging matched" in matched_attributes changes nothing
        # (the inputs are typed; there is no model-claim parameter).
        import inspect

        params = inspect.signature(
            fu3.sales_unit_authority_from_channel
        ).parameters
        assert set(params) == {"channel", "target_evidence"}


def _case_for_channel_check():
    """A minimal recorded V2 input carrying the explicit UNAVAILABLE
    channel (the live builder's always state)."""
    observation = ListingObservation(
        source_url="https://example.com/product",
        extraction_method=ExtractionMethod.JSON_LD,
        product_title="Has ABC-123 in the title",
        brand_text=None,
        manufacturer_part_number_text=None,
        sku_text=None,
        price_text="100",
        currency_text="USD",
        availability_text="In stock",
        condition_text="New",
        seller_text=None,
    )
    normalized = normalize_listing_observation(observation)
    request = ResearchRequest(REQUEST_MPN, "A test product")
    assessment = assess_listing_identity(request, normalized)
    context = derive_identity_state_v2(assessment)
    profile = build_v2_product_evidence_profile(
        observation=observation,
        context_provenances=frozenset(),
        matched_facts=frozenset(),
    )
    return build_semantic_match_case_v2(
        case_id="channel-check-0",
        request=request,
        assessment=assessment,
        context=context,
        product_evidence=profile,
        context_provenances=frozenset(),
        reviewed_target_context=None,
    )
