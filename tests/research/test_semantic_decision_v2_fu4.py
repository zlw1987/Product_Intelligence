"""FU4 versioned record / codec / replay integration tests
(PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-B5-P5-R1).

Mandated integration matrix (design section 9.1, rows 1-16 — the R1
record / codec / replay layer) over the REAL codec and replay entry
points (``decode_semantic_decision_record`` /
``encode_semantic_decision_record`` / ``replay_semantic_decision`` —
never only direct FU4 research functions): the claim-based codec
dispatch (FIND-1 / DEC-9), the registered FU4 adapter
(``research/semantic_decision_v2_fu4.py``), the FU4 typed record
(``SemanticDecisionRecordV2FU4``), the strict FU4 payload codec, and the
FU4 zero-live replay with the full derived-agreement proof over the FU4
audit surface.

Every case is an OFFLINE recorded-input construction (the real frozen
3C case chain, the real frozen extractor chain, the real FU4
constructors) with scripted evaluation doubles — NO live call, NO model
capture, NO network.

* **A1 — registration state.** The codec / replay union is exactly
  (V1, 2.0/FU2, 2.1/FU4) — a forged fourth binding is refused; the
  single-adapter pair lookup keeps its first-match semantics
  (registration order V1, V2, V2-FU4); the FU4 binding is drift-pinned
  across every surface that names it; the qualification marker stays
  False everywhere; the adapter module is research-pure and no live
  module references the FU4 record surface.
* **A2 — historical behavior preserved.** Every historical V1 / V2
  payload decodes to the SAME typed record, replays to the SAME
  decision, and re-encodes BYTE-IDENTICAL under the amended codec (the
  DEC-9 behavior-preservation proof, concrete); the historical
  malformed-payload rejections keep the same bounded error class at the
  same stage (modulo the recorded message-path moves).
* **B — the FU4 matrix.** PROVEN_EQUIVALENT over independently
  attested complete compositions; UNPROVEN over missing or incomplete
  evidence; CONTRADICTED over materially different established
  compositions (and the form axis over the default single-unit target);
  the count-only bundle remains UNPROVEN under FU4 while the SAME input
  preserves the historical FU3 behavior (three-token coexistence); the
  EXTRACTION_RESULT_V1 basis with the complete embedded original result
  (the full document inside the payload, round-tripped); conflicting
  secondary extraction cues fail closed; missing / tampered / wrong
  embedded extraction results are refused; the forged self-consistent
  EST record over a marker-free original (the Q3-B5-P4-FU2 false-PROVEN
  shape) is refused at replay; forged attestations; the explicit
  target-evidence shape discriminator; wrong bindings and wrong
  evidence schema versions; duplicate / zero adapter claims fail
  closed; altered stored derived decisions and payload digest
  mismatches; no live network / provider / model invocation; no
  automatic comparable tier for UNPROVEN / CONTRADICTED sales units.
"""

from __future__ import annotations

import ast
import dataclasses
import hashlib
import json
import sys
import uuid
from pathlib import Path

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.research import (
    AttemptOutcome,
    AttemptRole,
    AuthorityTier,
    CandidateEvidenceSourceV2,
    CandidateProductEvidenceSource,
    CandidateSalesUnitEvidenceV2,
    ConflictClass,
    ExtractionMethod,
    IdentityStateAssessmentV2,
    ListingObservation,
    PackagingEvidenceStateV2,
    ProductEvidenceDimension,
    ProductEvidenceFactV2,
    ProductEvidenceProfileV2,
    ProductEvidenceQuality,
    PRICING_ELIGIBLE_TIERS,
    RelationshipAuthority,
    SalesUnitKindV2,
    SemanticDecisionAttempt,
    SemanticEvaluationStateV2,
    SemanticEvaluationV2,
    SemanticReasonCodeV2,
    V1_CONTRACT_BINDING,
    V2Confidence,
    V2SemanticDecision,
    V2_CONTRACT_BINDING,
    assess_listing_identity,
    build_semantic_match_case_v2,
    build_v2_product_evidence_profile,
    canonical_sha256,
    decode_semantic_decision_record,
    derive_identity_state_v2,
    encode_semantic_decision_record,
    normalize_listing_observation,
    registered_semantic_contract_adapter,
    replay_semantic_decision,
    supported_contract_bindings,
)
from product_intelligence.research import (
    semantic_decision_v2_fu4 as sdv4,
)
from product_intelligence.research import semantic_authority_fu4 as fu4
from product_intelligence.research import semantic_authority_fu3 as fu3
from product_intelligence.research import semantic_decision_v1 as sdv1
from product_intelligence.research import semantic_decision_v2 as sdv2
from product_intelligence.research.semantic_authority_fu4 import (
    AUTHORITY_CONTRACT_VERSION_V2_FU4,
    AuthorityDecisionV2FU4,
    AuthorityRuleV2FU4,
    BundleCompositionStateV2FU4,
    EvidenceSideV2FU4,
    CompletenessBasisV2FU4,
    CompositionCompletenessAttestationV2FU4,
    QuantityCompletenessAttestationV2FU4,
    QuantityNonMaterialityReasonV2FU4,
    SalesUnitAuthorityV2,
    TargetSalesUnitEvidenceSourceV2,
    TargetSalesUnitEvidenceV2,
    TargetSalesUnitFormV2,
    TargetSalesUnitEvidenceV2FU4,
    candidate_composition_from_channel,
    candidate_composition_from_extraction,
    derive_authority_tier_for_contract_fu4,
)
from product_intelligence.research.semantic_authority_fu3 import (
    IdentityResolutionBoundV2,
)
from product_intelligence.research.sales_unit_extraction import (
    extract_and_map_sales_unit_evidence,
)
from product_intelligence.research.semantic_decision_codec import (
    SemanticDecisionCodecError,
)
from product_intelligence.research.semantic_decision_record import (
    SemanticDecisionReplayError,
)
from product_intelligence.research.sales_unit_extraction import (
    SalesUnitExtractionState,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "product_intelligence"
ADAPTER_PATH = PACKAGE_ROOT / "research" / "semantic_decision_v2_fu4.py"

RUN_ID = str(uuid.uuid4())
SOURCE_URL = "https://example.com/test-product"
REQUEST = ResearchRequest("ABC-123", "A test product")
TITLE = "ABC-123 1TB NVMe Drive"
CLAUSE = "2x RAM + 1x CPU"
CLAUSE_B = "2x SSD + 1x cable"

EST_RAW_DETAIL = f"bundle: {CLAUSE}, complete list"
COUNT_ONLY_RAW_DETAIL = "bundle of 3"

STARTED = "2026-02-10T12:00:00Z"
FINISHED = "2026-02-10T12:00:03.250000Z"


# ---------------------------------------------------------------------------
# Offline recorded-input construction (the real frozen chains)
# ---------------------------------------------------------------------------


def _observation(title: str | None = None):
    return ListingObservation(
        source_url=SOURCE_URL,
        extraction_method=ExtractionMethod.JSON_LD,
        product_title=title or TITLE,
        brand_text=None,
        manufacturer_part_number_text=None,
        sku_text=None,
        price_text="100",
        currency_text="USD",
        availability_text="In stock",
        condition_text="New",
        seller_text=None,
    )


def _assessment(title: str | None = None):
    return assess_listing_identity(
        REQUEST, normalize_listing_observation(_observation(title))
    )


def _context() -> IdentityStateAssessmentV2:
    return derive_identity_state_v2(_assessment())


def _strong_profile():
    return ProductEvidenceProfileV2(
        has_usable_product_title=True,
        matched_facts=frozenset(
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
        ),
    )


def _base_case(case_id: str = "fu4-integration-0"):
    assessment = _assessment()
    context = derive_identity_state_v2(assessment)
    profile = build_v2_product_evidence_profile(
        observation=assessment.normalized_listing.observation,
        context_provenances=frozenset(),
        matched_facts=frozenset(
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
        ),
    )
    return build_semantic_match_case_v2(
        case_id=case_id,
        request=REQUEST,
        assessment=assessment,
        context=context,
        product_evidence=profile,
        context_provenances=frozenset(),
        reviewed_target_context=None,
    )


def _case_with_channel(
    channel: CandidateSalesUnitEvidenceV2,
    case_id: str = "fu4-integration-0",
):
    """A real frozen-chain case whose recorded sales-unit channel is
    ``channel`` (the documented offline shape — the frozen live builder
    records UNAVAILABLE; the channel is the derivation input)."""
    case = _base_case(case_id)
    return dataclasses.replace(
        case,
        candidate_commercial=dataclasses.replace(
            case.candidate_commercial, sales_unit=channel
        ),
    )


def _bundle_channel(
    quantity: int | None,
    raw_detail: str,
    source: CandidateEvidenceSourceV2 = (
        CandidateEvidenceSourceV2.PUBLISHED_STRUCTURED_FIELD
    ),
) -> CandidateSalesUnitEvidenceV2:
    return CandidateSalesUnitEvidenceV2(
        state=PackagingEvidenceStateV2.OBSERVED,
        kind=SalesUnitKindV2.BUNDLE,
        quantity=quantity,
        raw_detail=raw_detail,
        source=source,
    )


def _extract(title: str, structured: str | None = None):
    return extract_and_map_sales_unit_evidence(
        _observation(title), structured
    )


def _canon(document: dict[str, object]) -> str:
    return canonical_sha256(document)


def _clause_digest(clause: str) -> str:
    return hashlib.sha256(clause.encode("utf-8")).hexdigest()


def _make_target_attestation(
    clause: str,
    basis: CompletenessBasisV2FU4 = (
        CompletenessBasisV2FU4.REVIEWED_COMPOSITION_ATTESTATION
    ),
    text: str = (
        "review determination: the requested part is sold as exactly "
        "this bundle"
    ),
) -> CompositionCompletenessAttestationV2FU4:
    document = {
        "schema_version": 3,
        "subject_side": EvidenceSideV2FU4.TARGET.value,
        "basis": basis.value,
        "source": TargetSalesUnitEvidenceSourceV2.REVIEWED_TARGET_CONTEXT.value,
        "clause_digest": _clause_digest(clause),
        "attestation_text": text,
    }
    return CompositionCompletenessAttestationV2FU4(
        3,
        EvidenceSideV2FU4.TARGET,
        basis,
        TargetSalesUnitEvidenceSourceV2.REVIEWED_TARGET_CONTEXT,
        _clause_digest(clause),
        text,
        _canon(document),
    )


def _make_target_fu4(
    clause: str,
    state: BundleCompositionStateV2FU4,
    quantity: int | None,
    attestation: CompositionCompletenessAttestationV2FU4 | None = None,
) -> TargetSalesUnitEvidenceV2FU4:
    document = {
        "schema_version": 3,
        "form": TargetSalesUnitFormV2.BUNDLE.value,
        "quantity": quantity,
        "source": TargetSalesUnitEvidenceSourceV2.REVIEWED_TARGET_CONTEXT.value,
        "composition_clause": clause,
        "composition_state": state.value,
        "completeness_attestation": (
            attestation.canonical() if attestation is not None else None
        ),
    }
    return TargetSalesUnitEvidenceV2FU4(
        3,
        TargetSalesUnitFormV2.BUNDLE,
        quantity,
        TargetSalesUnitEvidenceSourceV2.REVIEWED_TARGET_CONTEXT,
        clause,
        state,
        attestation,
        _canon(document),
    )


def _make_quantity_attestation(
    subject_side: EvidenceSideV2FU4,
    text: str = (
        "review determination: the subject source structurally publishes "
        "no bundle counts for this offer shape"
    ),
) -> QuantityCompletenessAttestationV2FU4:
    document = {
        "schema_version": 3,
        "subject_side": subject_side.value,
        "reason": (
            QuantityNonMaterialityReasonV2FU4.
            SUBJECT_SOURCE_STRUCTURALLY_WITHOUT_BUNDLE_COUNTS.value
        ),
        "source": (
            TargetSalesUnitEvidenceSourceV2.REVIEWED_TARGET_CONTEXT.value
        ),
        "attestation_text": text,
    }
    return QuantityCompletenessAttestationV2FU4(
        3,
        subject_side,
        QuantityNonMaterialityReasonV2FU4.
        SUBJECT_SOURCE_STRUCTURALLY_WITHOUT_BUNDLE_COUNTS,
        TargetSalesUnitEvidenceSourceV2.REVIEWED_TARGET_CONTEXT,
        text,
        _canon(document),
    )


def _match_evaluation(
    conflicts: frozenset[ConflictClass] = frozenset(),
) -> SemanticEvaluationV2:
    return SemanticEvaluationV2.evaluated(
        V2SemanticDecision.MATCH, V2Confidence.HIGH, conflicts
    )


def _primary_ok() -> SemanticDecisionAttempt:
    return SemanticDecisionAttempt(
        AttemptRole.PRIMARY,
        1,
        sdv4.PRIMARY_PROVIDER_V2_FU4,
        sdv4.PRIMARY_MODEL_V2_FU4,
        AttemptOutcome.OK,
    )


def _fu4_record(
    *,
    case,
    ctx: IdentityStateAssessmentV2,
    channel: CandidateSalesUnitEvidenceV2,
    evaluation: SemanticEvaluationV2 | None = None,
    target_evidence=None,
    candidate_composition=None,
    quantity_attestation=None,
    derived_override: AuthorityDecisionV2FU4 | None = None,
    evaluation_state=SemanticEvaluationStateV2.EVALUATED,
    decision=V2SemanticDecision.MATCH,
    confidence=V2Confidence.HIGH,
    reason_code=SemanticReasonCodeV2.MATCH_DESCRIPTION_AND_ATTRIBUTES,
    conflict_classes=frozenset(),
    attempts=(_primary_ok(),),
    fallback_used=False,
    actual_provider=sdv4.PRIMARY_PROVIDER_V2_FU4,
    actual_model=sdv4.PRIMARY_MODEL_V2_FU4,
) -> sdv4.SemanticDecisionRecordV2FU4:
    """Build a FU4 record whose derived section is the FU4
    RE-DERIVATION over exactly the recorded inputs (the same inputs the
    replay re-presents) — the shape a legitimate writer produces."""
    evaluation = (
        evaluation
        if evaluation is not None
        else _match_evaluation(conflict_classes)
    )
    decision_fu4 = derived_override or fu4.derive_authority_tier_fu4(
        ctx,
        channel,
        evaluation,
        case.context_provenances,
        case.product_evidence,
        None,
        target_unit_evidence=target_evidence,
        candidate_composition=candidate_composition,
        quantity_attestation=quantity_attestation,
    )
    return sdv4.SemanticDecisionRecordV2FU4.build(
        run_id=RUN_ID,
        assessment_index=0,
        source_url=case.candidate_source_url,
        case=case,
        evaluation_state=evaluation_state,
        decision=decision,
        confidence=confidence,
        reason_code=reason_code,
        conflict_classes=conflict_classes,
        matched_attributes=(),
        conflicting_attributes=(),
        missing_critical_attributes=(),
        attempts=attempts,
        fallback_used=fallback_used,
        fallback_reason=None,
        error_type=None,
        actual_provider=actual_provider,
        actual_model=actual_model,
        evaluation_started_at=STARTED,
        evaluation_finished_at=FINISHED,
        product_evidence_quality=decision_fu4.product_evidence_quality,
        relationship_authority=decision_fu4.relationship_authority,
        authority_tier=decision_fu4.tier,
        fired_rules=decision_fu4.fired_rules,
        identity_resolution_bound=decision_fu4.identity_resolution_bound,
        sales_unit_authority=decision_fu4.sales_unit_authority,
        quantity_axis_state=decision_fu4.quantity_axis_state,
        candidate_composition_state=decision_fu4.candidate_composition_state,
        target_composition_state=decision_fu4.target_composition_state,
        candidate_completeness_attestation_digest=(
            decision_fu4.candidate_completeness_attestation_digest
        ),
        target_completeness_attestation_digest=(
            decision_fu4.target_completeness_attestation_digest
        ),
        quantity_attestation_digest=decision_fu4.quantity_attestation_digest,
        candidate_composition=candidate_composition,
        target_evidence=target_evidence,
        quantity_attestation=quantity_attestation,
    )


def _roundtrip(record) -> tuple:
    """encode → universal decode → re-encode (byte-identical) →
    universal zero-live replay."""
    payload = encode_semantic_decision_record(record)
    decoded = decode_semantic_decision_record(
        payload, schema_version=sdv4.SEMANTIC_V2_FU4_ADAPTER.envelope_schema_version
    )
    assert decoded == record
    assert encode_semantic_decision_record(decoded) == payload
    replay = replay_semantic_decision(decoded)
    return payload, decoded, replay


def _recompute_output_digest(payload: dict) -> str:
    """The FU4 output digest over a (possibly tampered) payload's
    output sections — the shape a FORGER who recomputes the section
    digest (but not the derivation) would produce."""
    return canonical_sha256(
        {
            "evaluation": payload["evaluation"],
            "execution": payload["execution"],
            "authority": payload["authority"],
            "derived": payload["derived"],
        }
    )


def _candidate_doc_canonical_form(doc: dict) -> dict:
    """The candidate payload document in the record's ``canonical()``
    form (the nested self-digests stripped — the embedded attestation's
    ``attestation_digest`` and the embedded result's ``result_digest``
    are not part of the candidate's ``evidence_digest`` base)."""
    stripped = {k: v for k, v in doc.items() if k != "evidence_digest"}
    att = stripped.get("completeness_attestation")
    if isinstance(att, dict):
        stripped = dict(stripped)
        stripped["completeness_attestation"] = {
            k: v for k, v in att.items() if k != "attestation_digest"
        }
    result = stripped.get("extraction_result")
    if isinstance(result, dict):
        stripped = dict(stripped)
        stripped["extraction_result"] = {
            k: v for k, v in result.items() if k != "result_digest"
        }
    return stripped


# ===========================================================================
# A1. Registration state (the codec / replay union, the drift pins, the
#     isolation firewall)
# ===========================================================================


class TestA1RegistrationState:
    def test_the_codec_registry_is_exactly_the_three_registered_bindings(
        self,
    ) -> None:
        # R1 row 1: the codec registry knows EXACTLY (V1, 2.0/FU2,
        # 2.1/FU4); the replay union is the same; a forged fourth
        # binding (the harness-only 2.1/FU3) is refused by both.
        assert supported_contract_bindings() == (
            V1_CONTRACT_BINDING,
            V2_CONTRACT_BINDING,
            sdv4.V2_FU4_CONTRACT_BINDING,
        )
        from product_intelligence.research.semantic_decision_replay import (
            SUPPORTED_CONTRACT_BINDINGS,
        )

        assert SUPPORTED_CONTRACT_BINDINGS == supported_contract_bindings()
        assert ("V2", "2.1", 1, 1, fu3.AUTHORITY_CONTRACT_VERSION_V2_FU3) not in (
            SUPPORTED_CONTRACT_BINDINGS
        )
        # Registration order preserved: V1, V2, V2-FU4 — the public
        # single-adapter pair lookup KEEPS its first-match semantics.
        import product_intelligence.research.semantic_decision_codec as codec

        registry = codec._REGISTERED_SEMANTIC_CONTRACT_ADAPTERS
        assert registry == (
            sdv1.SEMANTIC_V1_ADAPTER,
            sdv2.SEMANTIC_V2_ADAPTER,
            sdv4.SEMANTIC_V2_FU4_ADAPTER,
        )
        assert (
            registered_semantic_contract_adapter(1, "V1")
            is sdv1.SEMANTIC_V1_ADAPTER
        )
        assert (
            registered_semantic_contract_adapter(1, "V2")
            is sdv2.SEMANTIC_V2_ADAPTER
        )
        # A forged fourth binding decodes to nothing (no adapter claims
        # it).
        forged = dict(
            json.loads(
                json.dumps(
                    encode_semantic_decision_record(
                        _fu4_record(
                            case=_case_with_channel(
                                _bundle_channel(None, COUNT_ONLY_RAW_DETAIL)
                            ),
                            ctx=_context(),
                            channel=_bundle_channel(None, COUNT_ONLY_RAW_DETAIL),
                        )
                    )
                )
            )
        )
        forged["contract"]["authority_contract_version"] = (
            "SEMANTIC_AUTHORITY_V2_S2A_FU9"
        )
        with pytest.raises(SemanticDecisionCodecError, match="no registered"):
            decode_semantic_decision_record(
                forged, schema_version=1
            )

    def test_the_fu4_binding_is_drift_pinned(self) -> None:
        # R1 row 1 (binding identity): the FU4 record binding is
        # composed from the frozen exports and matches the semantic
        # layer's 2.1 owner on every axis except the authority token.
        from product_intelligence.semantic.contract_v2_1 import (
            SEMANTIC_PROMPT_VERSION_V2_1,
            V2_1_CONTRACT_BINDING,
        )

        assert sdv4.V2_FU4_CONTRACT_BINDING == (
            "V2",
            "2.1",
            1,
            1,
            AUTHORITY_CONTRACT_VERSION_V2_FU4,
        )
        assert sdv4.SEMANTIC_CONTRACT_VERSION_V2_FU4 == (
            sdv2.SEMANTIC_CONTRACT_VERSION_V2
        )
        assert sdv4.SEMANTIC_CONTRACT_VERSION_V2_FU4 == "V2"
        assert sdv4.PROMPT_VERSION_V2_FU4 == (
            SEMANTIC_PROMPT_VERSION_V2_1
        )
        assert sdv4.PROMPT_VERSION_V2_FU4 == "2.1"
        assert sdv4.SEMANTIC_INPUT_SCHEMA_VERSION_V2_FU4 == (
            sdv2.SEMANTIC_INPUT_SCHEMA_VERSION_V2
        ) == 1
        assert sdv4.SEMANTIC_OUTPUT_SCHEMA_VERSION_V2_FU4 == (
            sdv2.SEMANTIC_OUTPUT_SCHEMA_VERSION_V2
        ) == 1
        # The FU4 binding moves ONLY the authority axis relative to the
        # existing 2.1 (FU3) binding.
        assert sdv4.V2_FU4_CONTRACT_BINDING[:4] == V2_1_CONTRACT_BINDING[:4]
        assert sdv4.V2_FU4_CONTRACT_BINDING[4] != (
            V2_1_CONTRACT_BINDING[4]
        )
        # The route mirror is the SAME frozen qualified route the V2
        # adapter pins (drift-pinned to the runtime).
        from product_intelligence.semantic import runtime_v2

        assert (
            sdv4.PRIMARY_PROVIDER_V2_FU4,
            sdv4.PRIMARY_MODEL_V2_FU4,
        ) == (
            sdv2.PRIMARY_PROVIDER_V2,
            sdv2.PRIMARY_MODEL_V2,
        ) == (
            runtime_v2.PRIMARY_PROVIDER_V2,
            runtime_v2.PRIMARY_MODEL_V2,
        )
        assert (
            sdv4.FALLBACK_PROVIDER_V2_FU4,
            sdv4.FALLBACK_MODEL_V2_FU4,
        ) == (
            sdv2.FALLBACK_PROVIDER_V2,
            sdv2.FALLBACK_MODEL_V2,
        ) == (
            runtime_v2.FALLBACK_PROVIDER_V2,
            runtime_v2.FALLBACK_MODEL_V2,
        )
        # The evidence-schema pins drift with the FU4 contract.
        assert sdv4.BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4 == 3
        from product_intelligence.research.sales_unit_extraction import (
            SALES_UNIT_EXTRACTION_SCHEMA_VERSION,
        )

        assert SALES_UNIT_EXTRACTION_SCHEMA_VERSION == 1
        # The adapter speaks the universal envelope format.
        assert (
            sdv4.SEMANTIC_V2_FU4_ADAPTER.envelope_schema_version
            == sdv2.SEMANTIC_V2_ADAPTER.envelope_schema_version
            == 1
        )

    def test_the_qualification_marker_stays_false_everywhere(self) -> None:
        # R1 acceptance 5: registration is NOT qualification — the two
        # frozen locations stay False, the FU4 adapter's mirror stays
        # False, and the live record type still pins the FU2 token.
        assert sdv4.V2_FU4_AUTHORITY_QUALIFIED is False
        assert sdv2.V2_AUTHORITY_QUALIFIED is False
        from product_intelligence.semantic import runtime_v2

        assert runtime_v2.V2_AUTHORITY_QUALIFIED is False
        assert runtime_v2.SEMANTIC_PROMPT_VERSION_V2 == "2.0"
        assert sdv2.V2_CONTRACT_BINDING == V2_CONTRACT_BINDING
        assert sdv2.SEMANTIC_V2_ADAPTER.supported_bindings == (
            V2_CONTRACT_BINDING,
        )
        # The harness remains R2's surface: exactly two production
        # bindings, no 1.2.0 artifact.
        from product_intelligence.evaluation.semantic_v2 import (
            corpus as harness_corpus,
        )
        from product_intelligence.evaluation.semantic_v2 import (
            fixtures as harness_fixtures,
        )

        assert len(harness_corpus.BINDING_CORPUS_VERSIONS) == 2
        assert not hasattr(harness_fixtures, "CORPUS_VERSION_2_1_FU4")

    def _imported_modules(self, path: Path) -> set[str]:
        modules: set[str] = set()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                modules.add(node.module)
        return modules

    def test_the_adapter_module_is_research_pure(self) -> None:
        # R1 acceptance 5 (the FU4 suite's A4 research-purity
        # discipline, extended to the registered adapter): stdlib + the
        # research package surface only — no Django, no persistence, no
        # providers, no web, no execution, no benchmark, no production
        # semantic runtime, no I/O, no clock, no mutable global state.
        modules = self._imported_modules(ADAPTER_PATH)
        disallowed = {
            module
            for module in modules
            if module.split(".")[0] != "product_intelligence"
            and module.split(".")[0] not in sys.stdlib_module_names
        }
        assert not disallowed, f"the FU4 adapter imports {sorted(disallowed)}"
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
            assert not offending, f"the FU4 adapter imports {sorted(offending)}"
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
            "decimal",
            "statistics",
            "math",
            "difflib",
        ):
            offending = {
                module
                for module in modules
                if module == io_module or module.startswith(io_module + ".")
            }
            assert not offending, f"the FU4 adapter performs I/O: {offending}"
        source = ADAPTER_PATH.read_text(encoding="utf-8")
        for clock_token in (
            "utcnow",
            "datetime.now",
            "time.time",
            "time.monotonic",
        ):
            assert clock_token not in source
        from tests.domain.test_domain_boundaries import (
            CALLER_TOKENS,
            VENDOR_TOKENS,
            _find_tokens,
        )

        assert not _find_tokens(source, VENDOR_TOKENS)
        assert not _find_tokens(source, CALLER_TOKENS)
        import importlib

        module = importlib.import_module(
            "product_intelligence.research.semantic_decision_v2_fu4"
        )
        mutable = {
            name: type(value).__name__
            for name, value in vars(module).items()
            if not name.startswith("__") and isinstance(value, (dict, list, set))
        }
        assert not mutable, f"the FU4 adapter has mutable global state: {mutable}"

    def test_no_live_module_references_the_fu4_record_surface(self) -> None:
        # R1 acceptance 5: no production module outside the research
        # contract surface references the FU4 RECORD surface (the
        # adapter module, its record / replay types, or its binding
        # constant) — the live runtime, persistence, pricing, and
        # presentation are unchanged by the registration.
        fu4_record_symbol = (
            "product_intelligence.research.semantic_decision_v2_fu4"
        )
        lexical_markers = (
            "semantic_decision_v2_fu4",
            "SemanticDecisionRecordV2FU4",
            "SemanticDecisionReplayV2FU4",
            "SEMANTIC_V2_FU4_ADAPTER",
            "V2_FU4_CONTRACT_BINDING",
            "replay_v2_fu4_record",
            "encode_v2_fu4_payload",
        )
        allowed_paths = {
            ADAPTER_PATH,
            PACKAGE_ROOT / "research" / "__init__.py",
            PACKAGE_ROOT / "research" / "semantic_decision_codec.py",
        }
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
                    if module == fu4_record_symbol
                    or module.startswith(fu4_record_symbol + ".")
                }
                assert not offending, (
                    f"{path} imports the FU4 record surface"
                )
                source = path.read_text(encoding="utf-8")
                for marker in lexical_markers:
                    assert marker not in source, (
                        f"{path.name} references the FU4 record surface "
                        f"({marker!r}); the registration wires no live "
                        "path"
                    )


# ===========================================================================
# A2. Historical V1 / V2 behavior preserved under the amended codec
#     (R1 rows 17, 18 — the DEC-9 behavior-preservation proof, concrete)
# ===========================================================================


def _v1_match_record():
    from tests.research.test_semantic_decision_record import _match_record

    return _match_record()


def _v1_runtime_failure_record():
    from tests.research.test_semantic_decision_replay import (
        _runtime_failure_record,
    )

    return _runtime_failure_record()


def _v1_not_evaluated_record():
    from tests.research.test_semantic_decision_record import (
        _build,
    )

    return _build(
        evaluation_state=SemanticEvaluationStateV2.NOT_EVALUATED,
        decision=None,
        confidence=None,
        reason_code=None,
        matched_attributes=(),
        attempts=(),
        started=None,
        finished=None,
    )


def _v2_match_record():
    from tests.research.test_semantic_decision_v2 import (
        _build_record,
    )

    return _build_record(
        decision=V2SemanticDecision.MATCH, confidence=V2Confidence.HIGH
    )


def _v2_no_match_record():
    from tests.research.test_semantic_decision_v2 import (
        _build_record,
    )

    return _build_record(
        decision=V2SemanticDecision.NO_MATCH,
        confidence=V2Confidence.MEDIUM,
        reason_code=SemanticReasonCodeV2.NO_MATCH_CAPACITY,
        conflict_classes=frozenset({ConflictClass.CAPACITY}),
        matched_attributes=(),
    )


class TestA2HistoricalBehaviorPreserved:
    @pytest.mark.parametrize(
        "make_record, binding",
        [
            (_v1_match_record, V1_CONTRACT_BINDING),
            (_v1_runtime_failure_record, V1_CONTRACT_BINDING),
            (_v1_not_evaluated_record, V1_CONTRACT_BINDING),
            (_v2_match_record, V2_CONTRACT_BINDING),
            (_v2_no_match_record, V2_CONTRACT_BINDING),
        ],
        ids=[
            "v1_match",
            "v1_runtime_failure",
            "v1_not_evaluated",
            "v2_match",
            "v2_no_match",
        ],
    )
    def test_historical_payload_encode_decode_replay_byte_identical(
        self, make_record, binding
    ) -> None:
        # R1 row 17: every historical fixture decodes to the SAME typed
        # record, replays to the SAME decision, and re-encodes
        # BYTE-IDENTICAL under the amended codec (the claim-based
        # dispatch resolves to the same adapter — the claiming set is a
        # singleton for every historical binding).
        record = make_record()
        payload = encode_semantic_decision_record(record)
        decoded = decode_semantic_decision_record(payload, schema_version=1)
        assert decoded == record
        assert type(decoded) is type(record)
        assert encode_semantic_decision_record(decoded) == payload
        replay = replay_semantic_decision(decoded)
        assert replay.record is decoded
        assert replay.contract_binding == binding

    def test_historical_malformed_payloads_rejected_unchanged(self) -> None:
        # R1 row 18: the malformed-payload rejections keep the bounded
        # error class and stage.
        # (a) Unknown enum under the V1 binding (adapter-level stage —
        #     the claiming set is the singleton V1 adapter).
        from product_intelligence.research import canonical_sha256

        v1 = _v1_match_record()
        payload = json.loads(json.dumps(encode_semantic_decision_record(v1)))
        payload["evaluation"]["decision"] = "MAYBE"
        payload["integrity"]["output_digest"] = canonical_sha256(
            {
                "evaluation": payload["evaluation"],
                "execution": payload["execution"],
                "derived": payload["derived"],
            }
        )
        with pytest.raises(SemanticDecisionCodecError, match="unknown"):
            decode_semantic_decision_record(payload, schema_version=1)
        # (b) Tampered evaluation with a stale output digest (V2).
        v2 = _v2_match_record()
        payload2 = json.loads(json.dumps(encode_semantic_decision_record(v2)))
        payload2["evaluation"]["confidence"] = "LOW"
        with pytest.raises(SemanticDecisionCodecError):
            decode_semantic_decision_record(payload2, schema_version=1)
        # (c) A V1-shaped body under the V2 contract name — zero
        #     adapters claim (V2, 1.1, 1, 1, FU2): refused at the
        #     codec's binding-disambiguation gate (previously: the V2
        #     adapter's strict check; the error class is unchanged).
        payload3 = json.loads(json.dumps(encode_semantic_decision_record(v1)))
        payload3["contract"]["semantic_contract_version"] = "V2"
        with pytest.raises(SemanticDecisionCodecError, match="no registered"):
            decode_semantic_decision_record(payload3, schema_version=1)
        # (d) A V2-shaped body under the V1 contract name — the same
        #     zero-claim refusal.
        payload4 = json.loads(json.dumps(encode_semantic_decision_record(v2)))
        payload4["contract"]["semantic_contract_version"] = "V1"
        with pytest.raises(SemanticDecisionCodecError, match="no registered"):
            decode_semantic_decision_record(payload4, schema_version=1)
        # (e) An extra top-level key (adapter-level stage — the
        #     singleton adapter's strict key check).
        payload5 = json.loads(json.dumps(encode_semantic_decision_record(v2)))
        payload5["junk"] = {"x": 1}
        with pytest.raises(SemanticDecisionCodecError, match="unexpected keys"):
            decode_semantic_decision_record(payload5, schema_version=1)
        # (f) A float anywhere (envelope-level stage — unchanged).
        payload6 = json.loads(json.dumps(encode_semantic_decision_record(v2)))
        payload6["evaluation"]["confidence"] = 1.5
        with pytest.raises(SemanticDecisionCodecError, match="float"):
            decode_semantic_decision_record(payload6, schema_version=1)
        # (g) An unknown semantic contract (dispatch-level stage — the
        #     historical message path stands).
        payload7 = json.loads(json.dumps(encode_semantic_decision_record(v2)))
        payload7["contract"]["semantic_contract_version"] = "V9"
        with pytest.raises(
            SemanticDecisionCodecError,
            match="unsupported semantic contract version 'V9'",
        ):
            decode_semantic_decision_record(payload7, schema_version=1)
        # (h) The 2.1/FU3 harness-only binding — STILL refused by the
        #     codec (no adapter claims it; unchanged by R1).
        payload8 = json.loads(json.dumps(encode_semantic_decision_record(v2)))
        payload8["contract"]["prompt_version"] = "2.1"
        payload8["contract"]["authority_contract_version"] = (
            fu3.AUTHORITY_CONTRACT_VERSION_V2_FU3
        )
        with pytest.raises(SemanticDecisionCodecError, match="no registered"):
            decode_semantic_decision_record(payload8, schema_version=1)


# ===========================================================================
# B. The FU4 matrix over the real codec / replay entry points
# ===========================================================================


class TestB1Fu4ProvenPath:
    @pytest.mark.parametrize(
        "quantity_shape",
        ["consistent", "both_unpublished", "attested_not_material"],
    )
    def test_fu4_proven_equivalent_over_independently_attested_complete_compositions(
        self, quantity_shape: str
    ) -> None:
        # R1 row 1: PROVEN_EQUIVALENT over independently attested
        # complete compositions — the candidate's PUBLISHED
        # completeness statement (its own source) and the target's
        # REVIEW attestation (a different, independent support) — over
        # every satisfied quantity-axis state.
        ctx = _context()
        if quantity_shape == "consistent":
            chan = _bundle_channel(2, EST_RAW_DETAIL)
            target = _make_target_fu4(
                CLAUSE,
                BundleCompositionStateV2FU4.ESTABLISHED,
                2,
                _make_target_attestation(CLAUSE),
            )
            qty_att = None
        elif quantity_shape == "both_unpublished":
            chan = _bundle_channel(None, EST_RAW_DETAIL)
            target = _make_target_fu4(
                CLAUSE,
                BundleCompositionStateV2FU4.ESTABLISHED,
                None,
                _make_target_attestation(CLAUSE),
            )
            qty_att = None
        else:  # attested_not_material (candidate side missing the count)
            chan = _bundle_channel(None, EST_RAW_DETAIL)
            target = _make_target_fu4(
                CLAUSE,
                BundleCompositionStateV2FU4.ESTABLISHED,
                2,
                _make_target_attestation(CLAUSE),
            )
            qty_att = _make_quantity_attestation(EvidenceSideV2FU4.CANDIDATE)
        case = _case_with_channel(chan)
        candidate = candidate_composition_from_channel(chan)
        assert candidate is not None
        assert candidate.state is BundleCompositionStateV2FU4.ESTABLISHED
        assert candidate.completeness_attestation is not None
        record = _fu4_record(
            case=case,
            ctx=ctx,
            channel=chan,
            target_evidence=target,
            candidate_composition=candidate,
            quantity_attestation=qty_att,
        )
        payload, decoded, replay = _roundtrip(record)
        decision = replay.authority_decision
        assert decision.sales_unit_authority is (
            SalesUnitAuthorityV2.PROVEN_EQUIVALENT
        )
        # The Q3-B4 §4.1 invariant's safe direction: PROVEN lets the
        # automatic tier stand (MATCH + HIGH + STRONG + clean).
        assert decision.tier is AuthorityTier.AI_ASSISTED_COMPARABLE
        assert not (
            decision.fired_rules
            & {
                AuthorityRuleV2FU4.CEILING_SALES_UNIT_NOT_PROVEN,
                AuthorityRuleV2FU4.CEILING_SALES_UNIT_CONTRADICTED,
            }
        )
        # The bundle-axis audit fields are RECORDED, never silent.
        assert decision.candidate_composition_state is (
            BundleCompositionStateV2FU4.ESTABLISHED
        )
        assert decision.target_composition_state is (
            BundleCompositionStateV2FU4.ESTABLISHED
        )
        expected_axis = {
            "consistent": fu4.BundleQuantityAxisStateV2FU4.CONSISTENT,
            "both_unpublished": fu4.BundleQuantityAxisStateV2FU4.
            BOTH_UNPUBLISHED,
            "attested_not_material": fu4.BundleQuantityAxisStateV2FU4.
            ATTESTED_NOT_MATERIAL,
        }[quantity_shape]
        assert decision.quantity_axis_state is expected_axis
        assert decision.candidate_completeness_attestation_digest == (
            candidate.completeness_attestation.attestation_digest
        )
        assert decision.target_completeness_attestation_digest == (
            target.completeness_attestation.attestation_digest
        )
        assert decision.quantity_attestation_digest == (
            qty_att.attestation_digest if qty_att is not None else None
        )
        # The stored derived section agrees with the re-derivation
        # field for field (the replay's agreement proof ran).
        assert decoded == record
        assert (
            replay.contract_binding == sdv4.V2_FU4_CONTRACT_BINDING
        )


class TestB2Fu4UnprovenPath:
    def test_fu4_unproven_over_missing_evidence(self) -> None:
        # R1 row 2 (missing): a count-only bundle publication carries
        # NO composition evidence — over a same-form bundle target
        # (matching form, composition ABSENT on the candidate side)
        # the unit is UNPROVEN, the would-be comparable tier capped at
        # NEEDS_REVIEW.
        ctx = _context()
        chan = _bundle_channel(3, COUNT_ONLY_RAW_DETAIL)
        case = _case_with_channel(chan)
        uncounted_target = TargetSalesUnitEvidenceV2(
            TargetSalesUnitFormV2.BUNDLE, None,
            TargetSalesUnitEvidenceSourceV2.REVIEWED_TARGET_CONTEXT,
        )
        record = _fu4_record(
            case=case,
            ctx=ctx,
            channel=chan,
            target_evidence=uncounted_target,
            candidate_composition=None,
            quantity_attestation=None,
        )
        payload, decoded, replay = _roundtrip(record)
        decision = replay.authority_decision
        assert decision.sales_unit_authority is SalesUnitAuthorityV2.UNPROVEN
        assert decision.tier is AuthorityTier.NEEDS_REVIEW
        assert AuthorityRuleV2FU4.CEILING_SALES_UNIT_NOT_PROVEN in (
            decision.fired_rules
        )
        assert decision.tier not in PRICING_ELIGIBLE_TIERS
        # The bundle-axis audit fields are recorded (the axis state
        # over the missing candidate composition; the frozen target
        # reads composition-ABSENT — D18).
        assert decision.candidate_composition_state is (
            BundleCompositionStateV2FU4.ABSENT
        )
        assert decision.target_composition_state is (
            BundleCompositionStateV2FU4.ABSENT
        )
        assert decoded == record

    def test_fu4_unproven_over_incomplete_evidence(self) -> None:
        # R1 row 2 (incomplete): a SYNTACTICALLY_VALID composition
        # (textually valid, completeness-unknown — NO attestation)
        # never proves, even against an attested-equal target.
        ctx = _context()
        chan = _bundle_channel(None, f"bundle: {CLAUSE}")
        case = _case_with_channel(chan)
        candidate = candidate_composition_from_channel(chan)
        assert candidate is not None
        assert candidate.state is BundleCompositionStateV2FU4.SYNTACTICALLY_VALID
        assert candidate.completeness_attestation is None
        target = _make_target_fu4(
            CLAUSE,
            BundleCompositionStateV2FU4.ESTABLISHED,
            None,
            _make_target_attestation(CLAUSE),
        )
        record = _fu4_record(
            case=case,
            ctx=ctx,
            channel=chan,
            target_evidence=target,
            candidate_composition=candidate,
            quantity_attestation=None,
        )
        payload, decoded, replay = _roundtrip(record)
        decision = replay.authority_decision
        assert decision.sales_unit_authority is SalesUnitAuthorityV2.UNPROVEN
        assert decision.tier is AuthorityTier.NEEDS_REVIEW
        assert AuthorityRuleV2FU4.CEILING_SALES_UNIT_NOT_PROVEN in (
            decision.fired_rules
        )
        assert decision.candidate_composition_state is (
            BundleCompositionStateV2FU4.SYNTACTICALLY_VALID
        )
        assert decision.target_composition_state is (
            BundleCompositionStateV2FU4.ESTABLISHED
        )


class TestB3Fu4ContradictedPath:
    def test_fu4_contradicted_over_materially_different_established_compositions(
        self,
    ) -> None:
        # R1 row 3: two ESTABLISHED clauses with a materially
        # established difference (U17) ⇒ CONTRADICTED ⇒ the
        # would-be AI_ASSISTED_COMPARABLE capped at NEEDS_REVIEW with
        # CEILING_SALES_UNIT_CONTRADICTED — the Q3-B4 §4.1 invariant
        # at record level.
        ctx = _context()
        chan = _bundle_channel(None, f"bundle: {CLAUSE}, complete list")
        case = _case_with_channel(chan)
        candidate = candidate_composition_from_channel(chan)
        assert candidate is not None
        assert candidate.state is BundleCompositionStateV2FU4.ESTABLISHED
        target = _make_target_fu4(
            CLAUSE_B,
            BundleCompositionStateV2FU4.ESTABLISHED,
            None,
            _make_target_attestation(CLAUSE_B),
        )
        record = _fu4_record(
            case=case,
            ctx=ctx,
            channel=chan,
            target_evidence=target,
            candidate_composition=candidate,
            quantity_attestation=None,
        )
        payload, decoded, replay = _roundtrip(record)
        decision = replay.authority_decision
        assert decision.sales_unit_authority is (
            SalesUnitAuthorityV2.CONTRADICTED
        )
        assert decision.tier is AuthorityTier.NEEDS_REVIEW
        assert AuthorityRuleV2FU4.CEILING_SALES_UNIT_CONTRADICTED in (
            decision.fired_rules
        )
        assert decision.tier not in PRICING_ELIGIBLE_TIERS
        assert decision.candidate_composition_state is (
            BundleCompositionStateV2FU4.ESTABLISHED
        )
        assert decision.target_composition_state is (
            BundleCompositionStateV2FU4.ESTABLISHED
        )

    def test_fu4_contradicted_form_axis_over_default_single_unit_target(
        self,
    ) -> None:
        # R1 row 3 (the form axis, U9): a bundle candidate is never
        # equivalent to the default single-unit target — CONTRADICTED
        # before any composition is read (the corpus 0034 shape).
        ctx = _context()
        chan = _bundle_channel(None, "GPU + power cables + bracket kit")
        case = _case_with_channel(chan)
        record = _fu4_record(
            case=case,
            ctx=ctx,
            channel=chan,
            target_evidence=None,
            candidate_composition=None,
            quantity_attestation=None,
        )
        payload, decoded, replay = _roundtrip(record)
        decision = replay.authority_decision
        assert decision.sales_unit_authority is (
            SalesUnitAuthorityV2.CONTRADICTED
        )
        assert decision.tier is AuthorityTier.NEEDS_REVIEW
        assert AuthorityRuleV2FU4.CEILING_SALES_UNIT_CONTRADICTED in (
            decision.fired_rules
        )


class TestB4CountOnlyCoexistence:
    def test_count_only_bundle_remains_unproven_under_fu4(self) -> None:
        # R1 row 4: the SAME count-only bundle inputs that the frozen
        # FU3 count rule treats as PROVEN (equal published counts)
        # remain UNPROVEN under the FU4 contract (a published count
        # alone is not the complete identity of a bundle — the P2-FU1
        # rule survives registration).
        ctx = _context()
        chan = _bundle_channel(3, COUNT_ONLY_RAW_DETAIL)
        case = _case_with_channel(chan)
        same_count_target = TargetSalesUnitEvidenceV2(
            TargetSalesUnitFormV2.BUNDLE, 3,
            TargetSalesUnitEvidenceSourceV2.REVIEWED_TARGET_CONTEXT,
        )
        record = _fu4_record(
            case=case,
            ctx=ctx,
            channel=chan,
            target_evidence=same_count_target,
            candidate_composition=None,
            quantity_attestation=None,
        )
        payload, decoded, replay = _roundtrip(record)
        decision = replay.authority_decision
        assert decision.sales_unit_authority is SalesUnitAuthorityV2.UNPROVEN
        assert decision.tier is AuthorityTier.NEEDS_REVIEW
        # The frozen FU3 target record is replayed under its explicit
        # discriminator (read as composition-ABSENT — D18).
        assert decoded.target_evidence == same_count_target
        assert payload["authority"]["target_evidence"]["schema"] == "frozen_fu3"

    def test_same_count_only_input_preserves_historical_fu3_behavior(
        self,
    ) -> None:
        # R1 row 5: the SAME recorded count-only bundle inputs preserve
        # the historical FU3 behavior (the frozen count-based
        # derivation — PROVEN_EQUIVALENT over equal published counts)
        # through the FU4 superset dispatch's FU3 arm (delegation
        # identity), while the FU2 arm refuses a unit input as contract
        # misuse — documented per-binding behavior, never drift (the A7
        # extension to three tokens).
        ctx = _context()
        chan = _bundle_channel(3, COUNT_ONLY_RAW_DETAIL)
        same_count_target = TargetSalesUnitEvidenceV2(
            TargetSalesUnitFormV2.BUNDLE, 3,
            TargetSalesUnitEvidenceSourceV2.REVIEWED_TARGET_CONTEXT,
        )
        evaluation = _match_evaluation()
        case = _case_with_channel(chan)
        fu3_decision = derive_authority_tier_for_contract_fu4(
            fu3.AUTHORITY_CONTRACT_VERSION_V2_FU3,
            ctx,
            evaluation,
            frozenset(),
            case.product_evidence,
            None,
            sales_unit_channel=chan,
            target_unit_evidence=same_count_target,
        )
        assert fu3_decision.sales_unit_authority is (
            SalesUnitAuthorityV2.PROVEN_EQUIVALENT
        )
        assert fu3_decision.tier is AuthorityTier.AI_ASSISTED_COMPARABLE
        # The FU2 arm has no sales-unit input at all: passing one is
        # contract misuse (the frozen rule, preserved).
        with pytest.raises(ValueError, match="no sales-unit input"):
            derive_authority_tier_for_contract_fu4(
                AUTHORITY_CONTRACT_VERSION_V2_FU2_TOKEN(),
                ctx,
                evaluation,
                frozenset(),
                case.product_evidence,
                None,
                sales_unit_channel=chan,
            )
        # And the FU4 arm over the SAME recorded inputs (full codec /
        # replay round trip) is the corrected D6 conjunction: UNPROVEN.
        record = _fu4_record(
            case=case,
            ctx=ctx,
            channel=chan,
            target_evidence=same_count_target,
            candidate_composition=None,
            quantity_attestation=None,
        )
        _payload, _decoded, replay = _roundtrip(record)
        assert replay.authority_decision.sales_unit_authority is (
            SalesUnitAuthorityV2.UNPROVEN
        )


def AUTHORITY_CONTRACT_VERSION_V2_FU2_TOKEN() -> str:
    from product_intelligence.research import (
        AUTHORITY_CONTRACT_VERSION_V2,
    )

    return AUTHORITY_CONTRACT_VERSION_V2


class TestB5ExtractionBasis:
    def test_extraction_result_v1_with_complete_embedded_original_result(
        self,
    ) -> None:
        # R1 row 6: the EXTRACTION_RESULT_V1 candidate record embeds
        # the EXACT original ``SalesUnitExtractionResult`` (schema v1)
        # — the full document (schema_version 1, both self-verifying
        # digests, every cue with its full provenance) is INSIDE the
        # payload's authority section, round-trips through the codec,
        # and the genuine association replays to PROVEN over the
        # attested-equal target.
        result, chan = _extract(f"bundle: {CLAUSE}, complete list")
        assert result.state is SalesUnitExtractionState.OBSERVED_UNAMBIGUOUS
        case = _case_with_channel(chan)
        ctx = _context()
        candidate = candidate_composition_from_extraction(result)
        assert candidate is not None
        assert candidate.basis is fu4.CandidateCompositionEvidenceBasisV2FU4. \
            EXTRACTION_RESULT_V1
        assert candidate.state is BundleCompositionStateV2FU4.ESTABLISHED
        assert candidate.extraction_result is result
        target = _make_target_fu4(
            CLAUSE,
            BundleCompositionStateV2FU4.ESTABLISHED,
            None,
            _make_target_attestation(CLAUSE),
        )
        record = _fu4_record(
            case=case,
            ctx=ctx,
            channel=chan,
            target_evidence=target,
            candidate_composition=candidate,
            quantity_attestation=None,
        )
        payload, decoded, replay = _roundtrip(record)
        # The embedded original result's FULL document is in the
        # payload (self-versioned + digest-sealed).
        stored = payload["authority"]["candidate_composition"]
        assert stored["basis"] == "EXTRACTION_RESULT_V1"
        embedded = stored["extraction_result"]
        assert embedded is not None
        assert embedded["schema_version"] == 1
        assert embedded["result_digest"] == result.result_digest
        assert embedded["input_digest"] == result.input_digest
        assert embedded["cues"] == [
            {
                "field": cue.field.value,
                "source": cue.source.value,
                "raw_field_value": cue.raw_field_value,
                "cue_text": cue.cue_text,
                "cue_start": cue.cue_start,
                "cue_end": cue.cue_end,
                "kind": cue.kind.value if cue.kind is not None else None,
                "quantity": cue.quantity,
                "disposition": cue.disposition.value,
                "reason": (
                    cue.reason.value if cue.reason is not None else None
                ),
            }
            for cue in result.cues
        ]
        assert stored["extraction_result_digest"] == result.result_digest
        assert stored["extraction_input_digest"] == result.input_digest
        # The round trip reconstructs the exact typed embedding.
        assert decoded.candidate_composition is not None
        assert (
            decoded.candidate_composition.extraction_result is not None
        )
        assert (
            decoded.candidate_composition.extraction_result.canonical()
            == result.canonical()
        )
        assert replay.authority_decision.sales_unit_authority is (
            SalesUnitAuthorityV2.PROVEN_EQUIVALENT
        )

    def test_conflicting_secondary_extraction_cues_fail_closed(self) -> None:
        # R1 row 7: the B12 shape at record level — a genuine
        # CONTRADICTED_PUBLISHED EXTRACTION record (identical primary
        # clause, conflicting secondary cues across the title and the
        # structured field) stands over its own mapped channel
        # (UNPROVEN over every bundle target); a forged swapped /
        # dropped secondary cue in the stored document is refused.
        title_a = f"bundle: {CLAUSE}, bundle: {CLAUSE_B}"
        result_a, chan_a = _extract(title_a)
        record_a = candidate_composition_from_extraction(result_a)
        assert record_a is not None
        assert record_a.state is BundleCompositionStateV2FU4.CONTRADICTED_PUBLISHED
        case = _case_with_channel(chan_a)
        ctx = _context()
        bundle_target = TargetSalesUnitEvidenceV2(
            TargetSalesUnitFormV2.BUNDLE, None,
            TargetSalesUnitEvidenceSourceV2.REVIEWED_TARGET_CONTEXT,
        )
        # The genuine record: full codec / replay round trip, UNPROVEN.
        record = _fu4_record(
            case=case,
            ctx=ctx,
            channel=chan_a,
            target_evidence=bundle_target,
            candidate_composition=record_a,
            quantity_attestation=None,
        )
        _payload, _decoded, replay = _roundtrip(record)
        assert replay.authority_decision.sales_unit_authority is (
            SalesUnitAuthorityV2.UNPROVEN
        )
        # The forged swapped secondary cue: a self-consistent document
        # that claims a composition the embedded original never
        # determined — its own digests verify (decode ACCEPTS the
        # self-consistent shape), and the replay's re-derivation
        # (the presentation gate's re-composition over the embedded
        # original) REFUSES it: no unit is derived from the forgery.
        swapped_doc = dict(
            json.loads(json.dumps(sdv4.encode_v2_fu4_payload(record)))
        )
        forged_candidate = dict(
            swapped_doc["authority"]["candidate_composition"]
        )
        forged_candidate["additional_clauses"] = ["swapped-clause"]
        forged_candidate["evidence_digest"] = _canon(
            _candidate_doc_canonical_form(forged_candidate)
        )
        swapped_doc["authority"]["candidate_composition"] = forged_candidate
        swapped_doc["integrity"]["output_digest"] = _recompute_output_digest(
            swapped_doc
        )
        swapped_decoded = decode_semantic_decision_record(
            swapped_doc, schema_version=1
        )
        with pytest.raises(SemanticDecisionReplayError):
            replay_semantic_decision(swapped_decoded)
        # The forged dropped-cue document (claiming a clean single
        # clause — state SYNTACTICALLY_VALID, the additional cues
        # dropped) is self-consistent (the CONTRADICTED_PUBLISHED shape
        # carries no attestation, so the state matrix stands): decode
        # ACCEPTS it, and the replay's re-derivation (the re-composition
        # over the embedded original is CONTRADICTED_PUBLISHED, not the
        # claimed state) REFUSES it — no unit is derived from the
        # forgery.
        dropped = dict(json.loads(json.dumps(_payload)))
        dropped_candidate = dict(
            dropped["authority"]["candidate_composition"]
        )
        dropped_candidate["state"] = "SYNTACTICALLY_VALID"
        dropped_candidate["additional_clauses"] = []
        dropped_candidate["evidence_digest"] = _canon(
            _candidate_doc_canonical_form(dropped_candidate)
        )
        dropped["authority"]["candidate_composition"] = dropped_candidate
        dropped["integrity"]["output_digest"] = _recompute_output_digest(
            dropped
        )
        dropped_decoded = decode_semantic_decision_record(
            dropped, schema_version=1
        )
        with pytest.raises(SemanticDecisionReplayError):
            replay_semantic_decision(dropped_decoded)

    def test_missing_embedded_extraction_result_refused(self) -> None:
        # R1 row 8 (missing): an EXTRACTION_RESULT_V1 candidate
        # document with ``extraction_result: null`` is un-constructible
        # (an extraction record whose original result is missing) —
        # the decode refuses it; a RECORDED_CHANNEL document with a
        # non-null embedding is refused symmetrically.
        result, chan = _extract(f"bundle: {CLAUSE}, complete list")
        record = candidate_composition_from_extraction(result)
        case = _case_with_channel(chan)
        ctx = _context()
        full = _fu4_record(
            case=case,
            ctx=ctx,
            channel=chan,
            target_evidence=None,
            candidate_composition=record,
            quantity_attestation=None,
        )
        payload = json.loads(json.dumps(sdv4.encode_v2_fu4_payload(full)))
        # (a) the embedding removed out of band.
        payload["authority"]["candidate_composition"]["extraction_result"] = (
            None
        )
        with pytest.raises(SemanticDecisionCodecError):
            decode_semantic_decision_record(payload, schema_version=1)
        # (b) a RECORDED_CHANNEL document carrying an embedding is
        # basis-incoherent.
        recorded = candidate_composition_from_channel(chan)
        recorded_case = _case_with_channel(chan, "fu4-recorded-1")
        recorded_record = _fu4_record(
            case=recorded_case,
            ctx=ctx,
            channel=chan,
            target_evidence=None,
            candidate_composition=recorded,
            quantity_attestation=None,
        )
        payload2 = json.loads(
            json.dumps(sdv4.encode_v2_fu4_payload(recorded_record))
        )
        assert (
            payload2["authority"]["candidate_composition"]["extraction_result"]
            is None
        )
        payload2["authority"]["candidate_composition"]["extraction_result"] = {
            **result.canonical(),
            "result_digest": result.result_digest,
        }
        with pytest.raises(SemanticDecisionCodecError):
            decode_semantic_decision_record(payload2, schema_version=1)

    def test_tampered_embedded_extraction_result_refused(self) -> None:
        # R1 row 8 (tampered): (a) a cue field tamper — the record's
        # own evidence digest refuses; (b) the stored result_digest
        # tampered — the embedded original's own integrity
        # re-verification refuses; (c) a cue-span tamper (cue_text no
        # longer a substring at the recorded span) — the frozen cue
        # constructor refuses.
        result, chan = _extract(f"bundle: {CLAUSE}, complete list")
        record = candidate_composition_from_extraction(result)
        case = _case_with_channel(chan)
        ctx = _context()
        full = _fu4_record(
            case=case,
            ctx=ctx,
            channel=chan,
            target_evidence=None,
            candidate_composition=record,
            quantity_attestation=None,
        )
        base = json.loads(json.dumps(sdv4.encode_v2_fu4_payload(full)))
        # (a) out-of-band cue field tamper (the embedding is inside the
        #     record's evidence digest).
        tampered_a = json.loads(json.dumps(base))
        tampered_a["authority"]["candidate_composition"]["extraction_result"][
            "cues"
        ][0]["cue_text"] = "bundle: something else"
        with pytest.raises(SemanticDecisionCodecError):
            decode_semantic_decision_record(tampered_a, schema_version=1)
        # (b) the embedded result's stored result_digest tampered
        #     (a value not covered by the embedding's canonical).
        tampered_b = json.loads(json.dumps(base))
        tampered_b["authority"]["candidate_composition"][
            "extraction_result"
        ]["result_digest"] = "0" * 64
        with pytest.raises(SemanticDecisionCodecError):
            decode_semantic_decision_record(tampered_b, schema_version=1)
        # (c) a cue span that no longer contains the cue text.
        tampered_c = json.loads(json.dumps(base))
        cues = tampered_c["authority"]["candidate_composition"][
            "extraction_result"
        ]["cues"]
        cues[0]["cue_end"] = cues[0]["cue_start"] + 1
        with pytest.raises(SemanticDecisionCodecError):
            decode_semantic_decision_record(tampered_c, schema_version=1)

    def test_wrong_extraction_result_with_identical_primary_clause_refused(
        self,
    ) -> None:
        # R1 row 9: the Q3-B5-P4-FU2 false-PROVEN shape at record
        # level — a self-consistent, hand-forged ESTABLISHED document
        # whose embedded original is the marker-FREE publication
        # (claiming a completeness attestation the publication never
        # made; its primary clause is identical; the frozen P2 mapping
        # is content-identical). The record's own digests verify —
        # decode ACCEPTS the self-consistent shape, and the replay's
        # re-derivation (the presentation gate's re-composition over
        # the embedded original) REFUSES it: no unit is derived, no
        # PROVEN ever stands over the forgery.
        result_est, chan = _extract(f"bundle: {CLAUSE}, complete list")
        result_sv, chan_sv = _extract(f"bundle: {CLAUSE}")
        assert chan == chan_sv  # the marker sits beyond raw_detail
        record_est = candidate_composition_from_extraction(result_est)
        assert record_est is not None
        assert record_est.state is BundleCompositionStateV2FU4.ESTABLISHED
        case = _case_with_channel(chan)
        ctx = _context()
        # The genuine record replays (PROVEN over the attested-equal
        # target) — the control.
        target = _make_target_fu4(
            CLAUSE,
            BundleCompositionStateV2FU4.ESTABLISHED,
            None,
            _make_target_attestation(CLAUSE),
        )
        genuine = _fu4_record(
            case=case,
            ctx=ctx,
            channel=chan,
            target_evidence=target,
            candidate_composition=record_est,
            quantity_attestation=None,
        )
        _p, _d, replay = _roundtrip(genuine)
        assert replay.authority_decision.sales_unit_authority is (
            SalesUnitAuthorityV2.PROVEN_EQUIVALENT
        )
        # The forged document: the genuine EST document with the
        # marker-free original swapped into the embedding (its anchors
        # follow the swapped original; the evidence digest is
        # recomputed — the forgery is self-consistent).
        forged_doc = json.loads(
            json.dumps(
                sdv4.encode_v2_fu4_payload(genuine)
            )
        )
        cand = forged_doc["authority"]["candidate_composition"]
        cand["extraction_result"] = {
            **result_sv.canonical(),
            "result_digest": result_sv.result_digest,
        }
        cand["extraction_result_digest"] = result_sv.result_digest
        cand["extraction_input_digest"] = result_sv.input_digest
        cand["evidence_digest"] = _canon(_candidate_doc_canonical_form(cand))
        forged_doc["integrity"]["output_digest"] = (
            _recompute_output_digest(forged_doc)
        )
        # Decode accepts the self-consistent shape (the digest alone
        # proves nothing — the B12 pin).
        decoded = decode_semantic_decision_record(
            forged_doc, schema_version=1
        )
        assert decoded.candidate_composition is not None
        assert (
            decoded.candidate_composition.state
            is BundleCompositionStateV2FU4.ESTABLISHED
        )
        # Replay fails closed: the re-composition over the embedded
        # original is SYNTACTICALLY_VALID without the attestation.
        with pytest.raises(SemanticDecisionReplayError):
            replay_semantic_decision(decoded)
        # And the marker-free GENUINE record over the same channel
        # derives UNPROVEN (the safe direction stands).
        record_sv = candidate_composition_from_extraction(result_sv)
        assert record_sv is not None
        assert record_sv.state is BundleCompositionStateV2FU4.SYNTACTICALLY_VALID
        sv_record = _fu4_record(
            case=_case_with_channel(chan_sv, "fu4-sv-1"),
            ctx=ctx,
            channel=chan_sv,
            target_evidence=target,
            candidate_composition=record_sv,
            quantity_attestation=None,
        )
        _p2, _d2, replay2 = _roundtrip(sv_record)
        assert replay2.authority_decision.sales_unit_authority is (
            SalesUnitAuthorityV2.UNPROVEN
        )

    def test_forged_completeness_attestation_refused(self) -> None:
        # R1 row 10 (attestation laundering): a completeness
        # attestation whose stored ``attestation_digest`` does not
        # match its content is un-constructible — the decode refuses
        # it (the constructor re-verifies the digest).
        result, chan = _extract(f"bundle: {CLAUSE}, complete list")
        record = candidate_composition_from_extraction(result)
        case = _case_with_channel(chan)
        ctx = _context()
        full = _fu4_record(
            case=case,
            ctx=ctx,
            channel=chan,
            target_evidence=None,
            candidate_composition=record,
            quantity_attestation=None,
        )
        payload = json.loads(json.dumps(sdv4.encode_v2_fu4_payload(full)))
        att = payload["authority"]["candidate_composition"][
            "completeness_attestation"
        ]
        att["attestation_text"] = "a different verbatim statement"
        # The document is now internally inconsistent: the attestation
        # digest no longer verifies over its content.
        with pytest.raises(SemanticDecisionCodecError):
            decode_semantic_decision_record(payload, schema_version=1)

    def test_forged_quantity_attestation_fails_closed(self) -> None:
        # R1 row 10 (quantity laundering): (a) a tampered quantity
        # attestation digest is refused at decode; (b) a
        # self-consistent attestation whose subject side is NOT the
        # actually-missing side is accepted by the record's own checks
        # (it verifies its own digest) but the replay's re-derivation
        # refuses it (the derivation enforces the side match — no
        # derivation input, no decision).
        chan = _bundle_channel(None, EST_RAW_DETAIL)
        case = _case_with_channel(chan)
        ctx = _context()
        candidate = candidate_composition_from_channel(chan)
        target = _make_target_fu4(
            CLAUSE,
            BundleCompositionStateV2FU4.ESTABLISHED,
            2,
            _make_target_attestation(CLAUSE),
        )
        legitimate = _make_quantity_attestation(EvidenceSideV2FU4.CANDIDATE)
        legitimate_record = _fu4_record(
            case=case,
            ctx=ctx,
            channel=chan,
            target_evidence=target,
            candidate_composition=candidate,
            quantity_attestation=legitimate,
        )
        payload = json.loads(
            json.dumps(sdv4.encode_v2_fu4_payload(legitimate_record))
        )
        # (a) the stored attestation digest tampered (out of band —
        #     the output digest is recomputed so the ONLY violation is
        #     the attestation's own self-verification).
        payload["authority"]["quantity_attestation"][
            "attestation_digest"
        ] = "0" * 64
        payload["integrity"]["output_digest"] = _recompute_output_digest(
            payload
        )
        with pytest.raises(SemanticDecisionCodecError):
            decode_semantic_decision_record(payload, schema_version=1)
        # (b) the wrong-subject-side forgery: the derived section is
        #     computed WITHOUT the attestation (the honest shape),
        #     while the authority section carries a self-consistent
        #     attestation subjecting the TARGET side (the actually-
        #     present side) over the asymmetric axis.
        forged_att = _make_quantity_attestation(EvidenceSideV2FU4.TARGET)
        honest_record = _fu4_record(
            case=case,
            ctx=ctx,
            channel=chan,
            target_evidence=target,
            candidate_composition=candidate,
            quantity_attestation=None,
        )
        forged = json.loads(
            json.dumps(sdv4.encode_v2_fu4_payload(honest_record))
        )
        forged["authority"]["quantity_attestation"] = {
            **forged_att.canonical(),
            "attestation_digest": forged_att.attestation_digest,
        }
        forged["integrity"]["output_digest"] = _recompute_output_digest(
            forged
        )
        decoded = decode_semantic_decision_record(forged, schema_version=1)
        assert decoded.quantity_attestation == forged_att
        with pytest.raises(SemanticDecisionReplayError):
            replay_semantic_decision(decoded)


class TestB6TargetEvidenceDiscriminator:
    def test_wrong_target_evidence_discriminator_refused(self) -> None:
        # R1 row 11: the EXPLICIT bounded shape discriminator (DEC-8) —
        # an unknown discriminator is a codec error; a document whose
        # shape does not reconstruct is a codec error; a valid
        # ``frozen_fu3`` document round-trips under its explicit
        # shape (no inference).
        chan = _bundle_channel(3, COUNT_ONLY_RAW_DETAIL)
        case = _case_with_channel(chan)
        ctx = _context()
        frozen_target = TargetSalesUnitEvidenceV2(
            TargetSalesUnitFormV2.BUNDLE, 3,
            TargetSalesUnitEvidenceSourceV2.REVIEWED_TARGET_CONTEXT,
        )
        record = _fu4_record(
            case=case,
            ctx=ctx,
            channel=chan,
            target_evidence=frozen_target,
            candidate_composition=None,
            quantity_attestation=None,
        )
        base = json.loads(json.dumps(sdv4.encode_v2_fu4_payload(record)))
        # (a) an unknown discriminator value.
        bad_schema = json.loads(json.dumps(base))
        bad_schema["authority"]["target_evidence"]["schema"] = "fu4_v2"
        bad_schema["integrity"]["output_digest"] = _recompute_output_digest(
            bad_schema
        )
        with pytest.raises(
            SemanticDecisionCodecError,
            match="unknown target-evidence shape discriminator",
        ):
            decode_semantic_decision_record(bad_schema, schema_version=1)
        # (b) a ``frozen_fu3`` document with an extra key.
        extra_key = json.loads(json.dumps(base))
        extra_key["authority"]["target_evidence"]["document"]["schema_version"] = (
            3
        )
        extra_key["integrity"]["output_digest"] = _recompute_output_digest(
            extra_key
        )
        with pytest.raises(SemanticDecisionCodecError):
            decode_semantic_decision_record(extra_key, schema_version=1)
        # (c) a ``fu4_v3`` document whose stored evidence_digest does
        #     not verify (the reconstructed record's round trip fails).
        good_target = _make_target_fu4(
            CLAUSE,
            BundleCompositionStateV2FU4.ESTABLISHED,
            None,
            _make_target_attestation(CLAUSE),
        )
        est_case = _case_with_channel(
            _bundle_channel(None, EST_RAW_DETAIL), "fu4-tgt-1"
        )
        est_record = _fu4_record(
            case=est_case,
            ctx=ctx,
            channel=est_case.candidate_commercial.sales_unit,
            target_evidence=good_target,
            candidate_composition=candidate_composition_from_channel(
                est_case.candidate_commercial.sales_unit
            ),
            quantity_attestation=None,
        )
        tampered_target = json.loads(
            json.dumps(sdv4.encode_v2_fu4_payload(est_record))
        )
        tampered_target["authority"]["target_evidence"]["document"][
            "evidence_digest"
        ] = "0" * 64
        tampered_target["integrity"]["output_digest"] = (
            _recompute_output_digest(tampered_target)
        )
        with pytest.raises(SemanticDecisionCodecError):
            decode_semantic_decision_record(tampered_target, schema_version=1)
        # (d) the control: the valid frozen_fu3 document round-trips.
        decoded = decode_semantic_decision_record(base, schema_version=1)
        assert decoded.target_evidence == frozen_target
        assert base["authority"]["target_evidence"]["schema"] == "frozen_fu3"
        assert base["authority"]["target_evidence"]["document"] == {
            "form": "BUNDLE",
            "quantity": 3,
            "source": "REVIEWED_TARGET_CONTEXT",
        }


class TestB7BindingAndSchemaRejection:
    def test_foreign_route_in_an_fu4_record_is_refused(self) -> None:
        # R1 row 14: an FU4 record whose primary / fallback attempt
        # names any provider / model outside the pinned route is un-
        # constructible (the V2-style route pin, mirrored in the FU4
        # adapter) and undecodable.
        chan = _bundle_channel(None, COUNT_ONLY_RAW_DETAIL)
        case = _case_with_channel(chan)
        ctx = _context()
        record = _fu4_record(
            case=case,
            ctx=ctx,
            channel=chan,
            target_evidence=None,
            candidate_composition=None,
            quantity_attestation=None,
        )
        # (a) at construction: the route pin refuses the foreign
        #     attempt.
        with pytest.raises(ValueError, match="pinned"):
            sdv4.SemanticDecisionRecordV2FU4.build(
                run_id=RUN_ID,
                assessment_index=0,
                source_url=case.candidate_source_url,
                case=case,
                evaluation_state=SemanticEvaluationStateV2.EVALUATED,
                decision=V2SemanticDecision.MATCH,
                confidence=V2Confidence.HIGH,
                reason_code=SemanticReasonCodeV2.MATCH_DESCRIPTION_AND_ATTRIBUTES,
                conflict_classes=frozenset(),
                matched_attributes=(),
                conflicting_attributes=(),
                missing_critical_attributes=(),
                attempts=(
                    SemanticDecisionAttempt(
                        AttemptRole.PRIMARY, 1, "foreign",
                        "model-x", AttemptOutcome.OK,
                    ),
                ),
                fallback_used=False,
                fallback_reason=None,
                error_type=None,
                actual_provider="foreign",
                actual_model="model-x",
                evaluation_started_at=STARTED,
                evaluation_finished_at=FINISHED,
                product_evidence_quality=record.product_evidence_quality,
                relationship_authority=record.relationship_authority,
                authority_tier=record.authority_tier,
                fired_rules=record.fired_rules,
                identity_resolution_bound=record.identity_resolution_bound,
                sales_unit_authority=record.sales_unit_authority,
                quantity_axis_state=record.quantity_axis_state,
                candidate_composition_state=record.candidate_composition_state,
                target_composition_state=record.target_composition_state,
                candidate_completeness_attestation_digest=(
                    record.candidate_completeness_attestation_digest
                ),
                target_completeness_attestation_digest=(
                    record.target_completeness_attestation_digest
                ),
                quantity_attestation_digest=record.quantity_attestation_digest,
                candidate_composition=None,
                target_evidence=None,
                quantity_attestation=None,
            )
        # (b) at decode: a stored payload whose attempts name a foreign
        #     route is refused (the record constructor is the
        #     validator; the bounded codec error wraps it).
        foreign = json.loads(json.dumps(sdv4.encode_v2_fu4_payload(record)))
        foreign["execution"]["attempts"][0]["provider"] = "foreign"
        foreign["execution"]["attempts"][0]["model"] = "model-x"
        foreign["execution"]["actual_provider"] = "foreign"
        foreign["execution"]["actual_model"] = "model-x"
        with pytest.raises(SemanticDecisionCodecError):
            decode_semantic_decision_record(foreign, schema_version=1)

    def test_wrong_binding_payloads_refused(self) -> None:
        # R1 rows 2 / 12 / 16: the claim-based disambiguation refuses
        # every cross-axis combination — a 2.0-prompt axis under the
        # FU4 token (a forged (V2, 2.0, 1, 1, FU4) binding); a 2.1-
        # prompt axis under the FU2 token; unknown / future /
        # misspelled / case-variant tokens — zero claims, fail closed,
        # never best-effort, never under the nearest known contract.
        chan = _bundle_channel(None, COUNT_ONLY_RAW_DETAIL)
        case = _case_with_channel(chan)
        ctx = _context()
        record = _fu4_record(
            case=case,
            ctx=ctx,
            channel=chan,
            target_evidence=None,
            candidate_composition=None,
            quantity_attestation=None,
        )
        base = json.loads(json.dumps(sdv4.encode_v2_fu4_payload(record)))
        for prompt, authority in (
            ("2.0", AUTHORITY_CONTRACT_VERSION_V2_FU4),  # forged 2.0/FU4
            ("2.1", "SEMANTIC_AUTHORITY_V2_S2A_FU2"),  # 2.1 under FU2
            ("2.1", "SEMANTIC_AUTHORITY_V2_S2A_FU9"),  # future token
            ("2.1", "SEMANTIC_AUTHORITY_V2_S2A_fu4"),  # case variant
            ("2.1", " SEMANTIC_AUTHORITY_V2_S2A_FU4"),  # whitespace
            ("2.1", ""),  # empty
            ("2.2", AUTHORITY_CONTRACT_VERSION_V2_FU4),  # phantom prompt
        ):
            forged = json.loads(json.dumps(base))
            forged["contract"]["prompt_version"] = prompt
            forged["contract"]["authority_contract_version"] = authority
            with pytest.raises(
                SemanticDecisionCodecError, match="no registered"
            ):
                decode_semantic_decision_record(
                    forged, schema_version=1
                )
        # The record's own exact-binding check stands at construction:
        # a FU4 record bound to the 2.0 prompt is un-constructible.
        with pytest.raises(ValueError, match="prompt_version"):
            dataclasses.replace(
                record, prompt_version="2.0"
            )
        # The envelope axis is independent: an unknown envelope
        # version fails before any dispatch.
        with pytest.raises(
            SemanticDecisionCodecError, match="unsupported schema_version"
        ):
            decode_semantic_decision_record(base, schema_version=2)

    def test_wrong_evidence_schema_version_refused(self) -> None:
        # R1 rows 3 / 4: a candidate document with a future (4) or
        # superseded (2 / 1) evidence schema version is refused — a
        # superseded schema is never silently reinterpreted (both the
        # strict key-set layer and the constructor pin fire); the
        # embedded extraction result's schema version pin stands.
        result, chan = _extract(f"bundle: {CLAUSE}, complete list")
        record = candidate_composition_from_extraction(result)
        case = _case_with_channel(chan)
        ctx = _context()
        full = _fu4_record(
            case=case,
            ctx=ctx,
            channel=chan,
            target_evidence=None,
            candidate_composition=record,
            quantity_attestation=None,
        )
        base = json.loads(json.dumps(sdv4.encode_v2_fu4_payload(full)))
        # (a) a FUTURE evidence schema version (4): the constructor
        #     pin refuses it (the key set is otherwise complete).
        future = json.loads(json.dumps(base))
        future["authority"]["candidate_composition"]["schema_version"] = 4
        with pytest.raises(SemanticDecisionCodecError):
            decode_semantic_decision_record(future, schema_version=1)
        # (b) a SUPERSEDED v2-shaped document: the v2 key set has no
        #     ``extraction_result`` — the exact key-set check refuses
        #     the missing key (and a v2 value would be un-constructible
        #     through the pin regardless).
        v2shaped = json.loads(json.dumps(base))
        del v2shaped["authority"]["candidate_composition"]["extraction_result"]
        with pytest.raises(SemanticDecisionCodecError, match="missing"):
            decode_semantic_decision_record(v2shaped, schema_version=1)
        v2value = json.loads(json.dumps(base))
        v2value["authority"]["candidate_composition"]["schema_version"] = 2
        with pytest.raises(SemanticDecisionCodecError):
            decode_semantic_decision_record(v2value, schema_version=1)
        # (c) the embedded extraction result's schema pin (a result
        #     document claiming extraction schema 2).
        wrong_result = json.loads(json.dumps(base))
        wrong_result["authority"]["candidate_composition"][
            "extraction_result"
        ]["schema_version"] = 2
        with pytest.raises(
            SemanticDecisionCodecError,
            match="extraction schema version",
        ):
            decode_semantic_decision_record(wrong_result, schema_version=1)

    def test_duplicate_adapter_claims_fail_closed(self, monkeypatch) -> None:
        # R1 row 16 (the disambiguation gate itself): two adapters
        # claiming one binding is a registry inconsistency — refused
        # with the distinct bounded contract-registry-defect error
        # (never first-match, never adapter failover). The registry
        # is a frozen module-level tuple: the double claim is
        # injected by substitution and restored.
        import product_intelligence.research.semantic_decision_codec as codec

        chan = _bundle_channel(None, COUNT_ONLY_RAW_DETAIL)
        case = _case_with_channel(chan)
        ctx = _context()
        record = _fu4_record(
            case=case,
            ctx=ctx,
            channel=chan,
            target_evidence=None,
            candidate_composition=None,
            quantity_attestation=None,
        )
        payload = json.loads(json.dumps(sdv4.encode_v2_fu4_payload(record)))
        real_registry = codec._REGISTERED_SEMANTIC_CONTRACT_ADAPTERS
        try:
            monkeypatch.setattr(
                codec,
                "_REGISTERED_SEMANTIC_CONTRACT_ADAPTERS",
                (
                    sdv1.SEMANTIC_V1_ADAPTER,
                    sdv2.SEMANTIC_V2_ADAPTER,
                    sdv4.SEMANTIC_V2_FU4_ADAPTER,
                    sdv4.SEMANTIC_V2_FU4_ADAPTER,
                ),
            )
            with pytest.raises(
                SemanticDecisionCodecError, match="registry defect"
            ):
                decode_semantic_decision_record(payload, schema_version=1)
            # The historical V2 binding under a double V2 claim is
            # refused the same way (never first-match).
            v2_payload = json.loads(
                json.dumps(
                    sdv2.encode_v2_payload(
                        _v2_match_record()
                    )
                )
            )
            monkeypatch.setattr(
                codec,
                "_REGISTERED_SEMANTIC_CONTRACT_ADAPTERS",
                (
                    sdv1.SEMANTIC_V1_ADAPTER,
                    sdv2.SEMANTIC_V2_ADAPTER,
                    sdv2.SEMANTIC_V2_ADAPTER,
                ),
            )
            with pytest.raises(
                SemanticDecisionCodecError, match="registry defect"
            ):
                decode_semantic_decision_record(
                    v2_payload, schema_version=1
                )
        finally:
            codec._REGISTERED_SEMANTIC_CONTRACT_ADAPTERS = real_registry


class TestB8AlteredDerivedAndDigests:
    def test_altered_stored_derived_decision_fails_closed(self) -> None:
        # R1 row 13: the full tamper discipline over the derived
        # section — (a) a stored exposure that is UN-CONSTRUCTIBLE as
        # an FU4 decision (AI_ASSISTED_COMPARABLE + UNPROVEN) is
        # undecodable even with the section digest recomputed (the
        # record's constructor invariants); (b) a stored derived field
        # that is constructible but DISAGREES with the re-derivation
        # (recomputed section digest) decodes and fails closed at the
        # replay's derived-agreement proof, naming the field; (c) a
        # stored derived field with a STALE section digest is refused
        # at decode.
        chan = _bundle_channel(3, COUNT_ONLY_RAW_DETAIL)
        case = _case_with_channel(chan)
        ctx = _context()
        record = _fu4_record(
            case=case,
            ctx=ctx,
            channel=chan,
            target_evidence=None,
            candidate_composition=None,
            quantity_attestation=None,
        )
        base = json.loads(json.dumps(sdv4.encode_v2_fu4_payload(record)))
        # (a) the un-constructible exposure (the Q3-B4 §4.1 invariant
        #     at record level): the derived section claims
        #     AI_ASSISTED_COMPARABLE over the UNPROVEN unit.
        forged = json.loads(json.dumps(base))
        forged["derived"]["authority_tier"] = (
            AuthorityTier.AI_ASSISTED_COMPARABLE.value
        )
        forged["derived"]["fired_rules"] = sorted(
            set(forged["derived"]["fired_rules"])
            - {"CEILING_SALES_UNIT_NOT_PROVEN"}
        )
        forged["integrity"]["output_digest"] = _recompute_output_digest(
            forged
        )
        with pytest.raises(SemanticDecisionCodecError):
            decode_semantic_decision_record(forged, schema_version=1)
        # (b) a constructible disagreement: the quantity axis state
        #     altered to a different DETERMINED state (the unit /
        #     tier / rules stand — a valid FU4 decision shape) with
        #     the section digest recomputed: decode accepts, the
        #     replay's re-derivation disagrees and refuses.
        disagree = json.loads(json.dumps(base))
        assert disagree["derived"]["quantity_axis_state"] is None
        disagree["derived"]["quantity_axis_state"] = "CONSISTENT"
        disagree["integrity"]["output_digest"] = _recompute_output_digest(
            disagree
        )
        decoded = decode_semantic_decision_record(
            disagree, schema_version=1
        )
        with pytest.raises(
            SemanticDecisionReplayError,
            match="quantity_axis_state",
        ):
            replay_semantic_decision(decoded)
        # (c) the same alteration with the STALE section digest:
        #     refused at decode.
        stale = json.loads(json.dumps(base))
        stale["derived"]["quantity_axis_state"] = "CONSISTENT"
        with pytest.raises(SemanticDecisionCodecError):
            decode_semantic_decision_record(stale, schema_version=1)

    def test_payload_digest_mismatch_refused(self) -> None:
        # R1 row 14: the integrity section is the record's own
        # tamper anchor — a mismatched stored input / output digest is
        # refused at decode; the whole-payload canonical digest moves
        # with any tamper (the row-level anchor's property).
        from product_intelligence.research import canonical_payload_digest

        chan = _bundle_channel(None, COUNT_ONLY_RAW_DETAIL)
        case = _case_with_channel(chan)
        ctx = _context()
        record = _fu4_record(
            case=case,
            ctx=ctx,
            channel=chan,
            target_evidence=None,
            candidate_composition=None,
            quantity_attestation=None,
        )
        base = json.loads(json.dumps(sdv4.encode_v2_fu4_payload(record)))
        assert canonical_payload_digest(base) == canonical_payload_digest(
            json.loads(json.dumps(base))
        )
        bad_input = json.loads(json.dumps(base))
        bad_input["integrity"]["input_digest"] = "0" * 64
        with pytest.raises(SemanticDecisionCodecError):
            decode_semantic_decision_record(bad_input, schema_version=1)
        bad_output = json.loads(json.dumps(base))
        bad_output["integrity"]["output_digest"] = "f" * 64
        with pytest.raises(SemanticDecisionCodecError):
            decode_semantic_decision_record(bad_output, schema_version=1)
        # The whole-artifact anchor moves with any tamper.
        tampered = json.loads(json.dumps(base))
        tampered["derived"]["sales_unit_authority"] = "PROVEN_EQUIVALENT"
        assert canonical_payload_digest(tampered) != (
            canonical_payload_digest(base)
        )

    def test_replayed_authority_disagreement_refused(self) -> None:
        # R1 row 13 (the forged-snapshot direction): a derived
        # section computed over DIFFERENT authority evidence than the
        # section stores (a self-consistent snapshot — its own digests
        # verify — that is not the derivation of the recorded
        # evidence): decode accepts, the replay's re-derivation
        # agreement proof refuses (no tamper shape yields a passed
        # replay).
        chan = _bundle_channel(None, EST_RAW_DETAIL)
        case = _case_with_channel(chan)
        ctx = _context()
        candidate = candidate_composition_from_channel(chan)
        est_target = _make_target_fu4(
            CLAUSE,
            BundleCompositionStateV2FU4.ESTABLISHED,
            None,
            _make_target_attestation(CLAUSE),
        )
        # The derived section is computed WITHOUT the target (the
        # form axis: CONTRADICTED over the default single unit), while
        # the authority section stores the attested-equal target (the
        # derivation over it: PROVEN).
        honest_derived = fu4.derive_authority_tier_fu4(
            ctx,
            chan,
            _match_evaluation(),
            frozenset(),
            case.product_evidence,
            None,
            target_unit_evidence=None,
            candidate_composition=candidate,
            quantity_attestation=None,
        )
        record = _fu4_record(
            case=case,
            ctx=ctx,
            channel=chan,
            target_evidence=est_target,
            candidate_composition=candidate,
            quantity_attestation=None,
            derived_override=honest_derived,
        )
        decoded = decode_semantic_decision_record(
            sdv4.encode_v2_fu4_payload(record), schema_version=1
        )
        with pytest.raises(SemanticDecisionReplayError):
            replay_semantic_decision(decoded)


class TestB9ZeroLiveAndFirewall:
    def test_no_live_network_provider_or_model_invocation(self) -> None:
        # R1 row 19: the FU4 record / codec / replay path performs
        # zero live AI calls, zero provider calls, and zero network
        # calls — armed fail-fast sentinels on the live surfaces
        # (the historical V1 / V2 payloads too, under the amended
        # codec).
        from unittest import mock

        chan = _bundle_channel(None, EST_RAW_DETAIL)
        case = _case_with_channel(chan)
        ctx = _context()
        candidate = candidate_composition_from_channel(chan)
        target = _make_target_fu4(
            CLAUSE,
            BundleCompositionStateV2FU4.ESTABLISHED,
            None,
            _make_target_attestation(CLAUSE),
        )
        record = _fu4_record(
            case=case,
            ctx=ctx,
            channel=chan,
            target_evidence=target,
            candidate_composition=candidate,
            quantity_attestation=None,
        )
        sentinels = [
            mock.patch(
                "product_intelligence.semantic.runtime.SemanticRuntime.evaluate",
                side_effect=AssertionError(
                    "live semantic/provider/network call made"
                ),
            ),
            mock.patch(
                "product_intelligence.semantic.transport."
                "get_openai_transport_for_provider",
                side_effect=AssertionError(
                    "live semantic/provider/network call made"
                ),
            ),
            mock.patch(
                "urllib.request.urlopen",
                side_effect=AssertionError(
                    "live semantic/provider/network call made"
                ),
            ),
        ]
        try:
            for sentinel in sentinels:
                sentinel.start()
            payload = sdv4.encode_v2_fu4_payload(record)
            decoded = decode_semantic_decision_record(
                payload, schema_version=1
            )
            replay = replay_semantic_decision(decoded)
            assert replay.authority_decision.sales_unit_authority is (
                SalesUnitAuthorityV2.PROVEN_EQUIVALENT
            )
            # The historical paths under the amended codec too.
            for historical in (
                _v1_match_record(),
                _v2_match_record(),
            ):
                hpayload = encode_semantic_decision_record(historical)
                hdecoded = decode_semantic_decision_record(
                    hpayload, schema_version=1
                )
                assert replay_semantic_decision(hdecoded).record is hdecoded
        finally:
            for sentinel in reversed(sentinels):
                sentinel.stop()

    def test_no_automatic_comparable_tier_for_unproven_or_contradicted_units(
        self,
    ) -> None:
        # R1 row 20: the exhaustive restrict-only sweep over the FU4
        # decision type — AI_ASSISTED_COMPARABLE with an UNPROVEN or a
        # CONTRADICTED unit is UN-CONSTRUCTIBLE (the exposure is not
        # merely un-derivable); the restrict-only ceilings fire only
        # with their unit state on NEEDS_REVIEW; and over the
        # registered record (full codec / replay round trip) no
        # UNPROVEN / CONTRADICTED sales unit ever holds the
        # automatic comparable tier.
        base_decision = dict(
            tier=AuthorityTier.AI_ASSISTED_COMPARABLE,
            fired_rules=frozenset(
                {
                    AuthorityRuleV2FU4.STATE_POLICY_DETERMINISTIC,
                    AuthorityRuleV2FU4.SEMANTIC_OUTCOME_MATRIX,
                }
            ),
            product_evidence_quality=ProductEvidenceQuality.STRONG,
            relationship_authority=RelationshipAuthority.NOT_APPLICABLE,
            identity_resolution_bound=IdentityResolutionBoundV2.
            PART_NUMBER,
            quantity_axis_state=None,
            candidate_composition_state=None,
            target_composition_state=None,
            candidate_completeness_attestation_digest=None,
            target_completeness_attestation_digest=None,
            quantity_attestation_digest=None,
        )
        for unit in (
            SalesUnitAuthorityV2.UNPROVEN,
            SalesUnitAuthorityV2.CONTRADICTED,
        ):
            # The exposure is un-constructible at the decision level…
            with pytest.raises(ValueError):
                AuthorityDecisionV2FU4(
                    sales_unit_authority=unit, **base_decision
                )
            # …and at the record level: the derived section must be a
            # VALID FU4 decision — forging the exposed shape (an
            # AI_ASSISTED_COMPARABLE tier over the UNPROVEN /
            # CONTRADICTED unit, ceiling rule removed) is un-constructible
            # at the decision level (the same invariants the record's
            # constructor re-runs), hence undecodable (the decode-level
            # direction is pinned by TestB8AlteredDerivedAndDigests).
            chan = _bundle_channel(None, COUNT_ONLY_RAW_DETAIL)
            case = _case_with_channel(chan)
            ctx = _context()
            honest = fu4.derive_authority_tier_fu4(
                ctx,
                chan,
                _match_evaluation(),
                frozenset(),
                case.product_evidence,
                None,
                target_unit_evidence=None,
                candidate_composition=None,
                quantity_attestation=None,
            )
            with pytest.raises(ValueError):
                dataclasses.replace(
                    honest,
                    tier=AuthorityTier.AI_ASSISTED_COMPARABLE,
                    fired_rules=honest.fired_rules
                    - {
                        AuthorityRuleV2FU4.CEILING_SALES_UNIT_NOT_PROVEN,
                        AuthorityRuleV2FU4.CEILING_SALES_UNIT_CONTRADICTED,
                    },
                )
            # …and the registered record over a genuine UNPROVEN /
            # CONTRADICTED shape holds the cap tier, never the
            # automatic comparable.
            for target_evidence, expected_unit in (
                (None, SalesUnitAuthorityV2.CONTRADICTED),
                (
                    TargetSalesUnitEvidenceV2(
                        TargetSalesUnitFormV2.BUNDLE, None,
                        TargetSalesUnitEvidenceSourceV2.REVIEWED_TARGET_CONTEXT,
                    ),
                    SalesUnitAuthorityV2.UNPROVEN,
                ),
            ):
                record = _fu4_record(
                    case=case,
                    ctx=ctx,
                    channel=chan,
                    target_evidence=target_evidence,
                    candidate_composition=None,
                    quantity_attestation=None,
                )
                _p, _d, replay = _roundtrip(record)
                assert replay.authority_decision.sales_unit_authority is (
                    expected_unit
                )
                assert replay.authority_decision.tier is (
                    AuthorityTier.NEEDS_REVIEW
                )
                assert replay.authority_decision.tier not in (
                    PRICING_ELIGIBLE_TIERS
                )
        # The restrict-only rules fire only with their unit state on
        # NEEDS_REVIEW (the constructor invariants).
        for rule, unit in (
            (
                AuthorityRuleV2FU4.CEILING_SALES_UNIT_NOT_PROVEN,
                SalesUnitAuthorityV2.UNPROVEN,
            ),
            (
                AuthorityRuleV2FU4.CEILING_SALES_UNIT_CONTRADICTED,
                SalesUnitAuthorityV2.CONTRADICTED,
            ),
        ):
            with pytest.raises(ValueError):
                AuthorityDecisionV2FU4(
                    **{
                        **base_decision,
                        "tier": AuthorityTier.NEEDS_REVIEW,
                        "fired_rules": frozenset({rule}),
                        "sales_unit_authority": (
                            SalesUnitAuthorityV2.PROVEN_EQUIVALENT
                        ),
                    }
                )
            AuthorityDecisionV2FU4(
                **{
                    **base_decision,
                    "tier": AuthorityTier.NEEDS_REVIEW,
                    "fired_rules": frozenset({rule}),
                    "sales_unit_authority": unit,
                }
            )
