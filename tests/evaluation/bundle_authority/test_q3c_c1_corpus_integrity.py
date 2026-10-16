"""Q3-C-C1: FU4 Bundle authority qualification corpus schema +
integrity validator — the focused adversarial test suite.

Design of record:
``docs/PRODUCT_INTEL_Q3C_FU4_BUNDLE_AUTHORITY_QUALIFICATION_DESIGN.md``
(section 9.3 — the C1 required tests: strict-decode refusals, missing /
extra keys, unknown enums, incoherent labels, wrong seal, tampered
per-case / corpus digests, cross-version / cross-binding refusal, the
constructor-as-validator rows, the regeneration property, the
sealed-raw stage-coherence rows, the authority-separation proofs).

Fixture discipline (task section 8): minimal SYNTHETIC fixtures only —
they exercise the schema and validator behavior. They are NOT
independently labeled qualification cases: their expected fields are
assembled from the frozen contract chain inside this TEST module (the
R1 suite's fixture pattern) for assembly consistency, and they never
leave this module (no corpus artifact is committed at C1; the sealed
v1.0.0 population is the C2 deliverable under the section 8.2
two-identity workflow). Synthetic fixture success is schema /
validator behavior only — never real-market qualification.

Authority separation (the tested contract): the corpus decoder never
imports or executes the FU4 authority derivation, the R1 replay, or any
model — proven here by the import scan (the exact research symbol
allowlist + the forbidden derivation symbols) and the monkeypatched
no-execution probe. The test module itself MAY execute the frozen
chain to assemble fixtures (the established R1 / R2 pattern) — that is
fixture assembly, not label determination by the decoder.

F-9 / F-10 trust boundary (Q3-C-C1-FU2): the test-local expected
values assembled in this module (_expected_from_decision, _payload_
record, and every helper that reads a frozen FU4 / R1 output) are
SYNTHETIC DECODER FIXTURES ONLY. They exist to exercise schema /
validator behavior and the sealed-raw shapes; they are NOT
independently labeled expected outcomes, and nothing here promotes a
valid schema or an internally consistent sealed corpus into authentic
published evidence, independent human review, or physical product
truth (design section 3.2 - five distinct layers, no automatic trust
promotion, no qualification case created by this suite). C2 authoring
and labeling tools MUST NOT reuse these helpers (or their outputs) as
an independent expected-label source: the C2 label is established
under the design section 4.6 / 8.2 two-identity workflow from the
recorded source content + the approved design rows, never from the
implementation's own output.

Every rejected input produces a deterministic, explicit failure: the
bounded ``BundleAuthorityCorpusError`` family with a bounded
``failure_stage`` + the exact check / path / observed value in the
reason. No permissive compatibility mode exists.
"""

from __future__ import annotations

import ast
import copy
import dataclasses
import hashlib
import json
import os
import re
import sys
from pathlib import Path

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.research import (
    PRICING_ELIGIBLE_TIERS,
    ProductEvidenceDimension,
    ProductEvidenceFactV2,
    CandidateProductEvidenceSource,
    SemanticEvaluationStateV2,
    assess_listing_identity,
    build_semantic_match_case_v2,
    build_v2_product_evidence_profile,
    derive_identity_state_v2,
    normalize_listing_observation,
    TargetSalesUnitEvidenceV2,
    TargetSalesUnitFormV2,
    TargetSalesUnitEvidenceSourceV2,
)
from product_intelligence.research import semantic_authority_fu4 as fu4
from product_intelligence.research import semantic_decision_v2_fu4 as sdv4
from product_intelligence.research import semantic_v2 as s2c
from product_intelligence.research.listings import ListingObservation
from product_intelligence.research.extraction import ExtractionMethod
from product_intelligence.research.sales_unit_extraction import (
    extract_and_map_sales_unit_evidence,
    extract_sales_unit_evidence,
    sales_unit_channel_from_extraction,
)
from product_intelligence.research import SemanticReasonCodeV2
from product_intelligence.research.semantic_decision_codec import (
    decode_semantic_decision_record,
    encode_semantic_decision_record,
)
from tests.research.test_semantic_decision_v2_fu4 import (
    CLAUSE,
    COUNT_ONLY_RAW_DETAIL,
    EST_RAW_DETAIL,
    FINISHED,
    SOURCE_URL,
    STARTED,
    TITLE,
    _base_case,
    _bundle_channel,
    _case_with_channel,
    _context,
    _make_target_attestation,
    _make_target_fu4,
    _match_evaluation,
    _observation,
    _primary_ok,
)

from product_intelligence.evaluation.bundle_authority import corpus as fam
from product_intelligence.evaluation.bundle_authority import (
    cli as fam_cli,
)
from product_intelligence.evaluation.bundle_authority import (
    fixtures as fam_fixtures,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
FAMILY_PACKAGE_ROOT = (
    REPO_ROOT / "product_intelligence" / "evaluation" / "bundle_authority"
)

# ---------------------------------------------------------------------------
# Fixture constants (synthetic, test-local — never a qualification seal)
# ---------------------------------------------------------------------------

FIXTURE_RUN_ID = "3f2c1a9e-6b4d-4e8f-9a2c-1d5e7f9b3c6a"
CREATED_UTC = "2026-01-01T00:00:00Z"
LABEL_AUTHOR = "c1-fixture-author"
LABEL_REVIEWER = "c1-fixture-reviewer"
LABEL_AUTHOR_UTC = "2026-01-02T00:00:00Z"
LABEL_REVIEWER_UTC = "2026-01-03T00:00:00Z"


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


# ---------------------------------------------------------------------------
# The family sealed document forms (the frozen codec's convention - the
# canonical document WITH the self-verifying digests)
# ---------------------------------------------------------------------------


def _att_sealed_doc(att):
    if att is None:
        return None
    return {
        **att.canonical(),
        "attestation_digest": att.attestation_digest,
    }


def _result_sealed_doc(result):
    if result is None:
        return None
    return {
        **result.canonical(),
        "result_digest": result.result_digest,
    }


def _candidate_sealed_doc(record):
    if record is None:
        return None
    doc = dict(record.canonical())
    doc["completeness_attestation"] = _att_sealed_doc(
        record.completeness_attestation
    )
    doc["extraction_result"] = _result_sealed_doc(record.extraction_result)
    doc["evidence_digest"] = record.evidence_digest
    return doc


def _target_sealed_doc(record):
    if record is None:
        return None
    doc = dict(record.canonical())
    doc["completeness_attestation"] = _att_sealed_doc(
        record.completeness_attestation
    )
    doc["evidence_digest"] = record.evidence_digest
    return doc


def _qty_att_sealed_doc(att):
    if att is None:
        return None
    return {
        **att.canonical(),
        "attestation_digest": att.attestation_digest,
    }


def _reseal_candidate_doc(doc):
    """Recompute the record's ``evidence_digest`` over the tampered
    document's canonical form (the embedded documents' self-digests
    excluded - the frozen digest discipline), for the sealed-raw
    fixtures that need a self-consistent tamper."""
    form = {k: v for k, v in doc.items() if k != "evidence_digest"}
    att = form.get("completeness_attestation")
    if isinstance(att, dict):
        form["completeness_attestation"] = {
            k: v for k, v in att.items() if k != "attestation_digest"
        }
    res = form.get("extraction_result")
    if isinstance(res, dict):
        form["extraction_result"] = {
            k: v for k, v in res.items() if k != "result_digest"
        }
    doc["evidence_digest"] = fam.canonical_sha256(form)
    return doc


def _reseal_target_doc(doc):
    form = {k: v for k, v in doc.items() if k != "evidence_digest"}
    att = form.get("completeness_attestation")
    if isinstance(att, dict):
        form["completeness_attestation"] = {
            k: v for k, v in att.items() if k != "attestation_digest"
        }
    doc["evidence_digest"] = fam.canonical_sha256(form)
    return doc


# ---------------------------------------------------------------------------
# Document projections (the family canonical forms of the frozen typed
# values — the same projections the decoder round-trips against)
# ---------------------------------------------------------------------------


def _identity_assessment_document(assessment) -> dict:
    return {
        "state": assessment.state.value,
        "substate": assessment.substate.value,
        "relationship_signals": sorted(
            s.value for s in assessment.relationship_signals
        ),
        "normalized_requested_part_number": assessment.normalized_requested_part_number,
        "normalized_candidate_part_number": assessment.normalized_candidate_part_number,
    }


def _evaluation_document(evaluation) -> dict:
    return {
        "evaluation_state": evaluation.evaluation_state.value,
        "decision": evaluation.decision.value if evaluation.decision else None,
        "confidence": evaluation.confidence.value if evaluation.confidence else None,
        "conflict_classes": sorted(c.value for c in evaluation.conflict_classes),
    }


def _profile_document(profile) -> dict:
    return {
        "has_usable_product_title": profile.has_usable_product_title,
        "matched_facts": sorted(
            (
                {
                    "dimension": fact.dimension.value,
                    "sources": sorted(s.value for s in fact.sources),
                }
                for fact in profile.matched_facts
            ),
            key=lambda fact: (fact["dimension"], fact["sources"]),
        ),
    }


def _label(
    *,
    provenance: str = "DESIGN_TABLE_GROUNDED",
    grounding: str = (
        "C1 validator fixture assembled over the frozen contract chain "
        "(P3 design section 5 U19 / U12 shape)"
    ),
    rationale: str = (
        "Synthetic C1 decoder fixture; assembled for schema / validator "
        "behavior only - not an independently labeled qualification case"
    ),
    author: str = LABEL_AUTHOR,
    reviewer: str = LABEL_REVIEWER,
) -> dict:
    return {
        "labeling_provenance": provenance,
        "grounding_citation": grounding,
        "author": author,
        "author_utc": LABEL_AUTHOR_UTC,
        "reviewer": reviewer,
        "reviewer_utc": LABEL_REVIEWER_UTC,
        "review_status": "REVIEWED",
        "independence_attestation": fam.INDEPENDENCE_ATTESTATION,
        "rationale": rationale,
    }


def _expected_from_decision(decision, *, replay: str, textual_relation):
    ceiling = None
    for rule in decision.fired_rules:
        if rule.value.startswith("CEILING_SALES_UNIT"):
            ceiling = rule.value
    return {
        "outcome": "DERIVED",
        "unit": decision.sales_unit_authority.value,
        "quantity_axis": (
            decision.quantity_axis_state.value
            if decision.quantity_axis_state is not None
            else None
        ),
        "candidate_composition_state": (
            decision.candidate_composition_state.value
            if decision.candidate_composition_state is not None
            else None
        ),
        "target_composition_state": (
            decision.target_composition_state.value
            if decision.target_composition_state is not None
            else None
        ),
        "textual_relation": textual_relation,
        "tier": decision.tier.value,
        "expected_ceiling": ceiling,
        "pricing_eligible": decision.tier in PRICING_ELIGIBLE_TIERS,
        "replay": replay,
        "refusal": None,
        "semantic_identity_note": None,
    }


def _payload_record(
    *, case, channel, evaluation, target_evidence, candidate_composition,
    quantity_attestation, decision,
):
    return sdv4.SemanticDecisionRecordV2FU4.build(
        run_id=FIXTURE_RUN_ID,
        assessment_index=0,
        source_url=case.candidate_source_url,
        case=case,
        evaluation_state=SemanticEvaluationStateV2.EVALUATED,
        decision=evaluation.decision,
        confidence=evaluation.confidence,
        reason_code=SemanticReasonCodeV2.MATCH_DESCRIPTION_AND_ATTRIBUTES,
        conflict_classes=evaluation.conflict_classes,
        matched_attributes=(),
        conflicting_attributes=(),
        missing_critical_attributes=(),
        attempts=(_primary_ok(),),
        fallback_used=False,
        fallback_reason=None,
        error_type=None,
        actual_provider=sdv4.PRIMARY_PROVIDER_V2_FU4,
        actual_model=sdv4.PRIMARY_MODEL_V2_FU4,
        evaluation_started_at=STARTED,
        evaluation_finished_at=FINISHED,
        product_evidence_quality=decision.product_evidence_quality,
        relationship_authority=decision.relationship_authority,
        authority_tier=decision.tier,
        fired_rules=decision.fired_rules,
        identity_resolution_bound=decision.identity_resolution_bound,
        sales_unit_authority=decision.sales_unit_authority,
        quantity_axis_state=decision.quantity_axis_state,
        candidate_composition_state=decision.candidate_composition_state,
        target_composition_state=decision.target_composition_state,
        candidate_completeness_attestation_digest=(
            decision.candidate_completeness_attestation_digest
        ),
        target_completeness_attestation_digest=(
            decision.target_completeness_attestation_digest
        ),
        quantity_attestation_digest=decision.quantity_attestation_digest,
        candidate_composition=candidate_composition,
        target_evidence=target_evidence,
        quantity_attestation=quantity_attestation,
    )


def _synthesize_case(
    *,
    case_id: str,
    matrix_row: str,
    channel,
    candidate_composition,
    candidate_basis: str,
    extraction_evidence,
    target_evidence_schema: str,
    target_evidence_document,
    quantity_attestation_document,
    case,
    assessment,
    evaluation,
    decision,
    surface: str,
    evidence_kind: str = "SYNTHETIC",
    tags: tuple[str, ...] = (),
    candidate_source_block=None,
    target_source_block=None,
    candidate_att_source=None,
    target_att_source=None,
    published_quantity=None,
    expected=None,
    label=None,
    v2_case_document=None,
    payload_document=None,
    payload_target_typed=None,
    payload_quantity_typed=None,
):
    """Assemble one synthetic family case document (the 16-key exact
    shape) from frozen-chain parts. The keyword overrides let the
    adversarial rows splice sealed-raw defects into otherwise-sound
    cases."""
    if candidate_source_block is None:
        candidate_source_block = {
            "title_text": TITLE,
            "structured_fields": {"packaging": channel.raw_detail},
            "source_url": None,
            "retrieved_utc": None,
            "raw_reference": None,
            "archive": None,
            "archive_digest": None,
            "recording_attestation": fam.SYNTHETIC_RECORDING_ATTESTATION,
        }
    if target_source_block is None:
        target_source_block = {
            "title_text": "Requested bundle review record (by-construction)",
            "structured_fields": {"specification": f"Bundle contents: {CLAUSE}"},
            "source_url": None,
            "retrieved_utc": None,
            "raw_reference": None,
            "archive": None,
            "archive_digest": None,
            "recording_attestation": fam.SYNTHETIC_RECORDING_ATTESTATION,
        }
    if candidate_att_source is None:
        embedded = (
            candidate_composition.completeness_attestation
            if candidate_composition is not None
            else None
        )
        candidate_att_source = (
            {
                "state": "PUBLISHED_STATEMENT",
                "verbatim": embedded.attestation_text,
                "location": "structured field 'packaging'",
            }
            if embedded is not None
            else {"state": "ABSENT", "verbatim": None, "location": None}
        )
    if target_att_source is None:
        target_typed = (
            target_evidence_document
            if isinstance(target_evidence_document, dict)
            else None
        )
        embedded = None
        if target_typed is not None and target_typed.get(
            "completeness_attestation"
        ) is not None:
            embedded = target_typed["completeness_attestation"]
        target_att_source = (
            {
                "state": (
                    "PUBLISHED_STATEMENT"
                    if embedded.get("basis")
                    == "PUBLISHED_COMPLETENESS_STATEMENT"
                    else "REVIEWED_DETERMINATION"
                ),
                "verbatim": embedded.get("attestation_text"),
                "anchor": (
                    "manufacturer bundle specification (recorded review anchor)"
                    if embedded.get("basis")
                    == "REVIEWED_COMPOSITION_ATTESTATION"
                    else None
                ),
            }
            if embedded is not None
            else {"state": "ABSENT", "verbatim": None, "anchor": None}
        )
    if published_quantity is None:
        target_qty = None
        if isinstance(target_evidence_document, dict):
            target_qty = target_evidence_document.get("quantity")
        published_quantity = {
            "candidate": channel.quantity,
            "target": target_qty,
            "citation": "the channel + target record quantity fields (verbatim, never inferred)",
        }
    if v2_case_document is None:
        v2_case_document = case.canonical()
    recorded_case = {"v2_case_document": v2_case_document}
    if surface in ("RECORD", "BOTH"):
        if payload_document is not None:
            recorded_case["payload_document"] = payload_document
        else:
            recorded_case["payload_document"] = encode_semantic_decision_record(
                _payload_record(
                    case=case,
                    channel=channel,
                    evaluation=evaluation,
                    target_evidence=payload_target_typed,
                    candidate_composition=candidate_composition,
                    quantity_attestation=payload_quantity_typed,
                    decision=decision,
                )
            )
    if expected is None:
        expected = _expected_from_decision(
            decision,
            replay=(
                "REPLAY_PASS" if surface in ("RECORD", "BOTH") else "NOT_APPLICABLE"
            ),
            textual_relation="T-AGREE",
        )
    if label is None:
        label = _label()
    return {
        "case_id": case_id,
        "case_category": "memory_kit",
        "matrix_row": matrix_row,
        "challenge_tags": list(tags),
        "evidence_kind": evidence_kind,
        "track": "A",
        "surface": surface if surface != "B" else None,
        "source": {"target": target_source_block, "candidate": candidate_source_block},
        "recorded_case": recorded_case,
        "derivation_inputs": {
            "channel": channel.canonical(),
            "candidate_composition": (
                _candidate_sealed_doc(candidate_composition)
                if candidate_composition is not None
                else None
            ),
            "candidate_basis": candidate_basis,
            "extraction_evidence": extraction_evidence,
            "target_evidence": {
                "schema": target_evidence_schema,
                "document": target_evidence_document,
            },
            "quantity_attestation": quantity_attestation_document,
        },
        "scripted_context": {
            "identity_assessment": _identity_assessment_document(assessment),
            "evaluation": _evaluation_document(evaluation),
            "context_provenances": sorted(
                p.value for p in case.context_provenances
            ),
            "product_evidence": _profile_document(case.product_evidence),
            "human_review": None,
        },
        "published_quantity": published_quantity,
        "completeness_attestation_source": {
            "candidate": candidate_att_source,
            "target": target_att_source,
        },
        "expected": expected,
        "label": label,
    }


def _typed_target_source(value: str):
    from product_intelligence.research import TargetSalesUnitEvidenceSourceV2

    return TargetSalesUnitEvidenceSourceV2(value)


# ---------------------------------------------------------------------------
# The synthetic fixtures (sound shapes + the sealed-raw defect splices)
# ---------------------------------------------------------------------------


def _frozen_case_parts(
    *,
    observation=None,
    request=None,
    channel=None,
    case_id="c1-fu2-1",
):
    """A REAL frozen-chain V2 case + its deterministic context over a
    custom observation / request (the R1 ``_base_case`` assembly,
    parameterized). Fixture assembly only: this MAY execute the frozen
    chain in this TEST module (the established R1 / R2 pattern); the
    corpus decoder never does, and the expected values it would produce
    are SYNTHETIC DECODER FIXTURES ONLY (see the module docstring's
    F-9 / F-10 warning) - never an independently labeled source.
    """
    if observation is None:
        observation = _observation()
    if request is None:
        request = ResearchRequest("ABC-123", "A test product")
    if channel is None:
        channel = _bundle_channel(None, EST_RAW_DETAIL)
    assessment = assess_listing_identity(
        request, normalize_listing_observation(observation)
    )
    context = derive_identity_state_v2(assessment)
    profile = build_v2_product_evidence_profile(
        observation=observation,
        context_provenances=frozenset(),
        matched_facts=frozenset(
            {
                ProductEvidenceFactV2(
                    ProductEvidenceDimension.CAPACITY,
                    frozenset(
                        {CandidateProductEvidenceSource.LISTING_PRODUCT_TITLE}
                    ),
                ),
                ProductEvidenceFactV2(
                    ProductEvidenceDimension.INTERFACE,
                    frozenset(
                        {CandidateProductEvidenceSource.LISTING_PRODUCT_TITLE}
                    ),
                ),
            }
        ),
    )
    case = build_semantic_match_case_v2(
        case_id=case_id,
        request=request,
        assessment=assessment,
        context=context,
        product_evidence=profile,
        context_provenances=frozenset(),
        reviewed_target_context=None,
    )
    case = dataclasses.replace(
        case,
        candidate_commercial=dataclasses.replace(
            case.candidate_commercial, sales_unit=channel
        ),
    )
    return {"case": case, "context": context, "evaluation": _match_evaluation()}


def _proven_parts(*, case_id="FA4-PROV-001", channel_kw=None):
    """The A1-shape sound parts: both sides independently attested,
    byte-identical closed clauses, neither side publishes a count."""
    raw_detail = (channel_kw or {}).get("raw_detail", EST_RAW_DETAIL)
    quantity = (channel_kw or {}).get("quantity", None)
    channel = _bundle_channel(quantity, raw_detail)
    case = _case_with_channel(channel, case_id="c1-proven-1")
    candidate = fu4.candidate_composition_from_channel(channel)
    target_att = _make_target_attestation(CLAUSE)
    target = _make_target_fu4(
        CLAUSE, fu4.BundleCompositionStateV2FU4.ESTABLISHED, None, target_att
    )
    assessment = _context()
    evaluation = _match_evaluation()
    decision = fu4.derive_authority_tier_fu4(
        assessment,
        channel,
        evaluation,
        case.context_provenances,
        case.product_evidence,
        None,
        target_unit_evidence=target,
        candidate_composition=candidate,
        quantity_attestation=None,
    )
    return {
        "case": case,
        "channel": channel,
        "candidate": candidate,
        "target": target,
        "target_att": target_att,
        "assessment": assessment,
        "evaluation": evaluation,
        "decision": decision,
    }


def _proven_case(*, case_id="FA4-PROV-001", surface="BOTH", **overrides):
    parts = _proven_parts(case_id=case_id)
    return _synthesize_case(
        case_id=case_id,
        matrix_row="A1",
        channel=parts["channel"],
        candidate_composition=parts["candidate"],
        candidate_basis="RECORDED_CHANNEL",
        extraction_evidence=None,
        target_evidence_schema="fu4_v3",
        target_evidence_document=_target_sealed_doc(parts["target"]),
        quantity_attestation_document=None,
        case=parts["case"],
        assessment=parts["assessment"],
        evaluation=parts["evaluation"],
        decision=parts["decision"],
        surface=surface,
        payload_target_typed=parts["target"],
        **overrides,
    )


def _count_only_parts(*, case_id="FA4-UNPR-001"):
    """The B1-shape sound parts: count-only bundle channel, candidate
    composition ABSENT, target bundle of the same count (frozen record),
    no attestation anywhere."""
    channel = _bundle_channel(3, COUNT_ONLY_RAW_DETAIL)
    case = _case_with_channel(channel, case_id="c1-unproven-1")
    candidate = fu4.candidate_composition_from_channel(channel)
    target = _make_target_fu4(
        None, fu4.BundleCompositionStateV2FU4.ABSENT, 3, None
    )
    assessment = _context()
    evaluation = _match_evaluation()
    decision = fu4.derive_authority_tier_fu4(
        assessment,
        channel,
        evaluation,
        case.context_provenances,
        case.product_evidence,
        None,
        target_unit_evidence=target,
        candidate_composition=candidate,
        quantity_attestation=None,
    )
    return {
        "case": case,
        "channel": channel,
        "candidate": candidate,
        "target": target,
        "assessment": assessment,
        "evaluation": evaluation,
        "decision": decision,
    }


def _count_only_case(*, case_id="FA4-UNPR-001", surface="DERIVATION", **overrides):
    parts = _count_only_parts(case_id=case_id)
    expected = _expected_from_decision(
        parts["decision"],
        replay=(
            "REPLAY_PASS" if surface in ("RECORD", "BOTH") else "NOT_APPLICABLE"
        ),
        textual_relation=None,
    )
    candidate_source_block = {
        "title_text": TITLE,
        "structured_fields": {"packaging": COUNT_ONLY_RAW_DETAIL},
        "source_url": None,
        "retrieved_utc": None,
        "raw_reference": None,
        "archive": None,
        "archive_digest": None,
        "recording_attestation": fam.SYNTHETIC_RECORDING_ATTESTATION,
    }
    target_source_block = {
        "title_text": "Requested bundle review record (by-construction)",
        "structured_fields": {"specification": "bundle of 3 (count only)"},
        "source_url": None,
        "retrieved_utc": None,
        "raw_reference": None,
        "archive": None,
        "archive_digest": None,
        "recording_attestation": fam.SYNTHETIC_RECORDING_ATTESTATION,
    }
    return _synthesize_case(
        case_id=case_id,
        matrix_row="B1",
        channel=parts["channel"],
        candidate_composition=parts["candidate"],
        candidate_basis="RECORDED_CHANNEL",
        extraction_evidence=None,
        target_evidence_schema="fu4_v3",
        target_evidence_document=_target_sealed_doc(parts["target"]),
        quantity_attestation_document=None,
        case=parts["case"],
        assessment=parts["assessment"],
        evaluation=parts["evaluation"],
        decision=parts["decision"],
        surface=surface,
        payload_target_typed=parts["target"],
        candidate_source_block=candidate_source_block,
        target_source_block=target_source_block,
        candidate_att_source={"state": "ABSENT", "verbatim": None, "location": None},
        target_att_source={"state": "ABSENT", "verbatim": None, "anchor": None},
        expected=expected,
        **overrides,
    )


def _sealed_refusal_expected(*, stage, error_type=None, replay="NOT_APPLICABLE"):
    return {
        "outcome": "REFUSED",
        "unit": None,
        "quantity_axis": None,
        "candidate_composition_state": None,
        "target_composition_state": None,
        "textual_relation": None,
        "tier": None,
        "expected_ceiling": None,
        "pricing_eligible": None,
        "replay": replay,
        "refusal": {"stage": stage, "error_type": error_type},
        "semantic_identity_note": None,
    }


def _sealed_case(
    *, base, case_id=None, stage, error_type=None, replay="NOT_APPLICABLE",
    outcome="REFUSED", label=None, **overrides,
):
    """A sealed-raw defect case: the base sound parts + a labeled
    refusal + the defect splices in ``overrides`` (the tampered
    documents). The base case's digest is recomputed by the sealer."""
    case_id = case_id or "FA4-ADV-001"
    expected = _sealed_refusal_expected(
        stage=stage, error_type=error_type, replay=replay
    )
    if label is None:
        label = _label(
            provenance="ADVERSARIAL_CONSTRUCTION",
            grounding=(
                "C1 sealed-raw fixture: the defect shape is the recorded "
                "adversarial construction (P3 design section 9 row shape)"
            ),
            rationale=(
                "Synthetic C1 sealed-raw decoder fixture; the labeled "
                "refusal stage is the independent expectation of the "
                "defect shape - not a qualification case"
            ),
        )
    return _synthesize_case(
        case_id=case_id,
        matrix_row=overrides.pop("matrix_row", "D2"),
        channel=base["channel"],
        candidate_composition=overrides.pop(
            "candidate_composition", base["candidate"]
        ),
        candidate_basis=overrides.pop("candidate_basis", "RECORDED_CHANNEL"),
        extraction_evidence=overrides.pop("extraction_evidence", None),
        target_evidence_schema=overrides.pop("target_evidence_schema", "fu4_v3"),
        target_evidence_document=overrides.pop(
            "target_evidence_document", _target_sealed_doc(base["target"])
        ),
        quantity_attestation_document=overrides.pop("quantity_attestation_document", None),
        case=base["case"],
        assessment=base["assessment"],
        evaluation=base["evaluation"],
        decision=base["decision"],
        surface=overrides.pop("surface", "DERIVATION"),
        expected=expected,
        label=label,
        **overrides,
    )


def _raw_for_decode(case):
    """A raw case document for the direct per-case decoder: the builder
    adds the real ``case_digest`` at seal time; the decoder's phase 1
    requires the key present, so the direct-decode tests carry a
    placeholder (the digest check is the final phase)."""
    case = dict(case)
    case.setdefault("case_digest", "0" * 64)
    return case


def _seal(tmp_path: Path, cases, *, created_utc=CREATED_UTC):
    """Build + write the family corpus file + manifest in the family
    storage layout under a temp repo root (the digest re-verification
    resolves cited archives against that root)."""
    document = fam_fixtures.build_corpus_document(created_utc, tuple(cases))
    manifest = fam.build_manifest_document(document)
    base = tmp_path / "evaluation" / "fu4_bundle_authority_qualification"
    base.mkdir(parents=True, exist_ok=True)
    corpus_file = base / "corpus_v1.json"
    manifest_file = base / "manifest_v1.json"
    corpus_file.write_bytes(fam_fixtures.corpus_bytes(document))
    manifest_file.write_bytes(fam.canonically_serialize(manifest))
    return corpus_file, manifest_file


def _decode_ok(cases, tmp_path, **seal_kw):
    corpus_file, manifest_file = _seal(tmp_path, cases, **seal_kw)
    bundle = fam.load_bundle(corpus_file, manifest_file)
    return bundle, corpus_file


def _set_path(document, path, value):
    """Set a value along a dotted key path (fixture tampering)."""
    node = document
    keys = path.split(".")
    for key in keys[:-1]:
        node = node[key]
    node[keys[-1]] = value
    return document


def _seal_then_tamper(tmp_path, cases, tamper_fn):
    """Seal the corpus, then tamper the SEALED document in place (no
    digest recomputation) - the digest-integrity tests' shape: the
    mutation lands inside the sealed bytes, so only the digests can
    catch it."""
    corpus_file, manifest_file = _seal(tmp_path, cases)
    document = json.loads(corpus_file.read_text(encoding="utf-8"))
    tamper_fn(document)
    corpus_file.write_bytes(fam.canonically_serialize(document))
    return corpus_file, manifest_file


# ---------------------------------------------------------------------------
# The sound synthetic fixtures load (the positive control surface)
# ---------------------------------------------------------------------------


class TestSoundCasesLoad:
    def test_proven_case_loads_with_typed_evidence(self, tmp_path):
        case = _proven_case()
        bundle, _ = _decode_ok([case], tmp_path)
        loaded = bundle.cases[0]
        assert loaded.case_id == "FA4-PROV-001"
        assert loaded.evidence.v2_case is not None
        assert (
            loaded.evidence.candidate_composition.state
            is fu4.BundleCompositionStateV2FU4.ESTABLISHED
        )
        assert (
            loaded.evidence.target_evidence.composition_state
            is fu4.BundleCompositionStateV2FU4.ESTABLISHED
        )
        # The payload decoded through the REAL universal codec.
        assert loaded.evidence.payload_record is not None
        assert loaded.evidence.payload_record.case == loaded.evidence.v2_case
        assert loaded.expected["unit"] == "PROVEN_EQUIVALENT"

    def test_count_only_case_loads(self, tmp_path):
        case = _count_only_case()
        bundle, _ = _decode_ok([case], tmp_path)
        loaded = bundle.cases[0]
        assert (
            loaded.evidence.candidate_composition.state
            is fu4.BundleCompositionStateV2FU4.ABSENT
        )
        assert loaded.expected["unit"] == "UNPROVEN"
        assert loaded.evidence.payload_record is None

    def test_payload_is_the_exact_codec_round_trip(self, tmp_path):
        case = _proven_case()
        payload_doc = copy.deepcopy(case["recorded_case"]["payload_document"])
        bundle, _ = _decode_ok([case], tmp_path)
        decoded = decode_semantic_decision_record(
            payload_doc, schema_version=payload_doc["schema_version"]
        )
        assert bundle.cases[0].evidence.payload_record == decoded

    def test_loaded_case_document_round_trips(self, tmp_path):
        case = _proven_case()
        bundle, _ = _decode_ok([case], tmp_path)
        sealed = dict(case)
        sealed["case_digest"] = bundle.cases[0].case_digest
        assert bundle.cases[0].document == sealed
        assert fam.canonically_serialize(bundle.document) == (
            fam.canonically_serialize(
                fam_fixtures.build_corpus_document(CREATED_UTC, (case,))
            )
        )


# ---------------------------------------------------------------------------
# Structural integrity (task section 7: missing / extra keys, wrong types,
# invalid enums, duplicate ids, invalid corpus / binding identity, invalid
# schema version)
# ---------------------------------------------------------------------------

_TOP_LEVEL_KEYS = sorted(fam._CASE_KEYS)


class TestStructuralIntegrity:
    def _sound_case(self):
        return _proven_case()

    @pytest.mark.parametrize("key", _TOP_LEVEL_KEYS)
    def test_missing_required_top_level_key(self, key):
        case = _raw_for_decode(self._sound_case())
        del case[key]
        with pytest.raises(fam.BundleAuthoritySchemaError) as exc:
            fam.decode_corpus_case_document(case)
        assert "missing required keys" in exc.value.reason
        assert key in exc.value.reason

    def test_unexpected_extra_top_level_key(self):
        case = _raw_for_decode(self._sound_case())
        case["extra_field"] = "x"
        with pytest.raises(fam.BundleAuthoritySchemaError) as exc:
            fam.decode_corpus_case_document(case)
        assert "unknown keys" in exc.value.reason

    @pytest.mark.parametrize(
        "path, value",
        [
            ("case_id", 123),
            ("case_category", []),
            ("matrix_row", None),
            ("challenge_tags", "forged_attestation"),
            ("evidence_kind", 1),
            ("track", None),
            ("surface", 7),
            ("source", "candidate"),
            ("recorded_case", None),
            ("derivation_inputs", []),
            ("scripted_context", {}),
            ("published_quantity", {"candidate": 3}),
            ("completeness_attestation_source", "candidate"),
            ("expected", None),
            ("label", None),
            ("case_digest", "zz" * 32),
            ("published_quantity.candidate", "3"),
            ("published_quantity.citation", None),
            ("label.author", None),
            ("expected.pricing_eligible", "true"),
        ],
    )
    def test_wrong_field_type(self, path, value):
        case = _raw_for_decode(self._sound_case())
        _set_path(case, path, value)
        with pytest.raises(fam.BundleAuthorityCorpusError) as exc:
            fam.decode_corpus_case_document(case)
        assert exc.value.failure_stage in (
            fam._STAGE_SCHEMA,
            fam._STAGE_DIGEST,
        )

    @pytest.mark.parametrize(
        "path, value",
        [
            ("evidence_kind", "REAL"),
            ("track", "C"),
            ("surface", "BOTH_X"),
            ("matrix_row", "Z1"),
            ("expected.outcome", "PROVEN"),
            ("expected.unit", "MATCH"),
            ("expected.quantity_axis", "AGREED"),
            ("expected.candidate_composition_state", "UNKNOWN"),
            ("expected.textual_relation", "T-MAYBE"),
            ("expected.tier", "VERIFIED"),
            ("expected.expected_ceiling", "CEILING_PRICE"),
            ("expected.replay", "PASS"),
            ("expected.refusal.stage", "LOADER"),
            ("expected.refusal.error_type", "BOOM"),
            ("label.labeling_provenance", "GUESS"),
            ("label.review_status", "UNREVIEWED"),
            ("derivation_inputs.candidate_basis", "MODEL"),
            ("derivation_inputs.target_evidence.schema", "fu5"),
            ("completeness_attestation_source.candidate.state", "REVIEWED"),
            ("completeness_attestation_source.target.state", "PUBLISHED"),
            ("derivation_inputs.channel.kind", "CRATE"),
            ("derivation_inputs.channel.state", "OBSERVED_X"),
        ],
    )
    def test_invalid_enum(self, path, value):
        case = _raw_for_decode(self._sound_case())
        if path.startswith("expected.refusal"):
            case["expected"]["refusal"] = {
                "stage": "CONSTRUCTION",
                "error_type": None,
            }
        _set_path(case, path, value)
        with pytest.raises(fam.BundleAuthoritySchemaError) as exc:
            fam.decode_corpus_case_document(case)
        assert "expected one of" in exc.value.reason or (
            "must match" in exc.value.reason
        )

    @pytest.mark.parametrize(
        "case_id",
        [
            "fa4-prov-001",
            "FA4-XXXX-001",
            "FA4-PROV-1",
            "FA4-PROV-0001",
            "FA4-PROV-00A",
            "V2Q-PROV-001",
        ],
    )
    def test_invalid_case_id(self, case_id):
        case = _raw_for_decode(self._sound_case())
        case["case_id"] = case_id
        with pytest.raises(fam.BundleAuthoritySchemaError) as exc:
            fam.decode_corpus_case_document(case)
        assert "case-id grammar" in exc.value.reason

    def test_duplicate_case_id(self, tmp_path):
        case_a = _proven_case()
        case_b = _count_only_case(case_id="FA4-PROV-001")
        with pytest.raises(fam.BundleAuthoritySchemaError) as exc:
            _decode_ok([case_a, case_b], tmp_path)
        assert "duplicate case id" in exc.value.reason

    @pytest.mark.parametrize(
        "path, value",
        [
            ("corpus_id", "PI-SEMANTIC-V2-QUALIFICATION"),
            ("corpus_label", "semantic-v2-qualification-v1"),
            ("corpus_schema_version", 2),
            ("created_utc", "2026-01-01T00:00:00"),
        ],
    )
    def test_invalid_corpus_identity(self, tmp_path, path, value):
        case = self._sound_case()
        document = fam_fixtures.build_corpus_document(CREATED_UTC, (case,))
        _set_path(document, path, value)
        document["corpus_digest"] = fam.corpus_state_digest(document)
        with pytest.raises(fam.BundleAuthorityCorpusError):
            _seal_and_load(document, tmp_path)

    def test_invalid_binding_identity_cross_family(self, tmp_path):
        case = self._sound_case()
        document = fam_fixtures.build_corpus_document(CREATED_UTC, (case,))
        document["semantic_contract_binding"] = ["V2", "2.0", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU2"]
        document["corpus_digest"] = fam.corpus_state_digest(document)
        with pytest.raises(fam.BundleAuthoritySealError) as exc:
            _seal_and_load(document, tmp_path)
        assert "exact registered FU4 binding" in exc.value.reason

    def test_invalid_binding_identity_fu3(self, tmp_path):
        case = self._sound_case()
        document = fam_fixtures.build_corpus_document(CREATED_UTC, (case,))
        document["semantic_contract_binding"] = ["V2", "2.1", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU3"]
        document["corpus_digest"] = fam.corpus_state_digest(document)
        with pytest.raises(fam.BundleAuthoritySealError):
            _seal_and_load(document, tmp_path)

    def test_invalid_binding_shape(self, tmp_path):
        case = self._sound_case()
        document = fam_fixtures.build_corpus_document(CREATED_UTC, (case,))
        document["semantic_contract_binding"] = ["V2", "2.1", 1, 1]
        document["corpus_digest"] = fam.corpus_state_digest(document)
        with pytest.raises(fam.BundleAuthoritySealError):
            _seal_and_load(document, tmp_path)

    def test_invalid_corpus_version_not_sealed_under_binding(self, tmp_path):
        case = self._sound_case()
        document = fam_fixtures.build_corpus_document(CREATED_UTC, (case,))
        document["corpus_version"] = "1.1.0"
        document["corpus_digest"] = fam.corpus_state_digest(document)
        with pytest.raises(fam.BundleAuthoritySealError) as exc:
            _seal_and_load(document, tmp_path)
        assert "cross-version refusal" in exc.value.reason

    def test_surface_track_mismatch_track_b_with_surface(self):
        case = _raw_for_decode(self._sound_case())
        case["track"] = "B"
        # surface stays "BOTH" - a track B case carries no Track A surface
        with pytest.raises(fam.BundleAuthoritySchemaError) as exc:
            fam.decode_corpus_case_document(case)
        assert "no Track A" in exc.value.reason

    def test_surface_track_mismatch_track_a_without_surface(self):
        case = _raw_for_decode(self._sound_case())
        case["surface"] = None
        with pytest.raises(fam.BundleAuthoritySchemaError):
            fam.decode_corpus_case_document(case)


def _seal_and_load(document, tmp_path):
    base = tmp_path / "evaluation" / "fu4_bundle_authority_qualification"
    base.mkdir(parents=True, exist_ok=True)
    file = base / "corpus_v1.json"
    file.write_bytes(fam.canonically_serialize(document))
    return fam.load_corpus(file)


# ---------------------------------------------------------------------------
# Digest integrity (task section 7: modified case content / label /
# reviewer / source reference, modified manifest, incorrect corpus digest,
# incorrect case count, reordered cases)
# ---------------------------------------------------------------------------


class TestDigestIntegrity:
    def test_modified_case_content_fails_the_case_digest(self, tmp_path):
        corpus_file, _ = _seal_then_tamper(
            tmp_path, [_proven_case()],
            lambda doc: _set_path(doc["cases"][0], "case_category", "other_category"),
        )
        with pytest.raises(fam.BundleAuthorityDigestError) as exc:
            fam.load_corpus(corpus_file)
        assert "case_digest does not verify" in exc.value.reason

    def test_modified_expected_label_fails_the_case_digest(self, tmp_path):
        corpus_file, _ = _seal_then_tamper(
            tmp_path, [_proven_case()],
            lambda doc: _set_path(
                doc["cases"][0], "expected.textual_relation", "T-DIFF-MATERIAL"
            ),
        )
        with pytest.raises(fam.BundleAuthorityDigestError) as exc:
            fam.load_corpus(corpus_file)
        assert "case_digest does not verify" in exc.value.reason

    def test_modified_reviewer_identity_fails_the_case_digest(self, tmp_path):
        corpus_file, _ = _seal_then_tamper(
            tmp_path, [_proven_case()],
            lambda doc: _set_path(
                doc["cases"][0], "label.reviewer", "c1-fixture-reviewer-2"
            ),
        )
        with pytest.raises(fam.BundleAuthorityDigestError) as exc:
            fam.load_corpus(corpus_file)
        assert "case_digest does not verify" in exc.value.reason

    def test_modified_source_reference_fails_the_case_digest(self, tmp_path):
        corpus_file, _ = _seal_then_tamper(
            tmp_path, [_proven_case()],
            lambda doc: _set_path(
                doc["cases"][0],
                "source.candidate.structured_fields.packaging",
                "bundle: 2x RAM + 1x CPU, complete list (updated)",
            ),
        )
        with pytest.raises(fam.BundleAuthorityDigestError) as exc:
            fam.load_corpus(corpus_file)
        assert "case_digest does not verify" in exc.value.reason

    def test_incorrect_corpus_digest_fails(self, tmp_path):
        case = _proven_case()
        document = fam_fixtures.build_corpus_document(CREATED_UTC, (case,))
        document["corpus_digest"] = "0" * 64
        with pytest.raises(fam.BundleAuthorityDigestError) as exc:
            _seal_and_load(document, tmp_path)
        assert "corpus_digest does not verify" in exc.value.reason

    def test_reordered_cases_fail_the_corpus_digest(self, tmp_path):
        case_a = _proven_case()
        case_b = _count_only_case(case_id="FA4-UNPR-002")
        document = fam_fixtures.build_corpus_document(CREATED_UTC, (case_a, case_b))
        # Reorder the sealed case list WITHOUT re-sealing: the corpus
        # digest binds the order (ordering is contractually significant).
        document["cases"] = [document["cases"][1], document["cases"][0]]
        with pytest.raises(fam.BundleAuthorityDigestError) as exc:
            _seal_and_load(document, tmp_path)
        assert "corpus_digest does not verify" in exc.value.reason

    def test_resealed_reorder_loads_under_its_own_digest(self, tmp_path):
        case_a = _proven_case()
        case_b = _count_only_case(case_id="FA4-UNPR-002")
        document = fam_fixtures.build_corpus_document(CREATED_UTC, (case_a, case_b))
        document["cases"] = [document["cases"][1], document["cases"][0]]
        document["corpus_digest"] = fam.corpus_state_digest(document)
        bundle = _seal_and_load(document, tmp_path)
        assert [c.case_id for c in bundle.cases] == ["FA4-UNPR-002", "FA4-PROV-001"]

    @pytest.mark.parametrize(
        "path, value",
        [
            ("manifest_digest", "0" * 64),
            ("statement", "tampered statement"),
            ("lineage.derived_from_corpus_version", "0.9.0"),
            ("lineage.derived_from_corpus_digest", "0" * 64),
            ("case_count", 3),
            ("corpus_digest", "0" * 64),
            ("corpus_version", "1.1.0"),
            ("corpus_id", "PI-SEMANTIC-V2-QUALIFICATION"),
            ("semantic_contract_binding", ["V2", "2.0", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU2"]),
            ("manifest_schema_version", 2),
        ],
    )
    def test_modified_manifest_fails(self, tmp_path, path, value):
        case = _proven_case()
        corpus_file, manifest_file = _seal(tmp_path, [case])
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        _set_path(manifest, path, value)
        manifest_file.write_bytes(fam.canonically_serialize(manifest))
        with pytest.raises((fam.BundleAuthorityManifestError, fam.BundleAuthoritySchemaError)):
            fam.load_bundle(corpus_file, manifest_file)

    def test_modified_manifest_case_projection_fails(self, tmp_path):
        case = _proven_case()
        corpus_file, manifest_file = _seal(tmp_path, [case])
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        manifest["cases"][0]["case_digest"] = "f" * 64
        manifest_file.write_bytes(fam.canonically_serialize(manifest))
        with pytest.raises(fam.BundleAuthorityManifestError) as exc:
            fam.load_bundle(corpus_file, manifest_file)
        assert "projection disagrees" in exc.value.reason

    def test_non_canonical_serialization_rejected(self, tmp_path):
        case = _proven_case()
        document = fam_fixtures.build_corpus_document(CREATED_UTC, (case,))
        base = tmp_path / "evaluation" / "fu4_bundle_authority_qualification"
        base.mkdir(parents=True, exist_ok=True)
        file = base / "corpus_v1.json"
        file.write_bytes(
            (json.dumps(document, indent=2, sort_keys=True) + "\n").encode()
        )
        with pytest.raises(fam.BundleAuthoritySchemaError) as exc:
            fam.load_corpus(file)
        assert "stable canonical serialization" in exc.value.reason


# ---------------------------------------------------------------------------
# Provenance integrity (task section 7: side association, cross-listing
# substitution, missing / mismatched extraction, attestation grounding,
# model-claim disguise, forged reviewer association)
# ---------------------------------------------------------------------------


class TestProvenanceIntegrity:
    def test_candidate_evidence_attached_to_target_rejected(self, tmp_path):
        # The candidate's clause is published ONLY in the target's sealed
        # source block - the candidate side association fails.
        case = _proven_case()
        case["source"]["candidate"]["structured_fields"] = {}
        with pytest.raises(fam.BundleAuthorityEvidenceError) as exc:
            _decode_ok([case], tmp_path)
        assert "CANDIDATE source block" in exc.value.reason

    def test_target_evidence_attached_to_candidate_rejected(self, tmp_path):
        # The target's clause is published ONLY in the candidate's sealed
        # source block - the target side association fails.
        case = _proven_case()
        case["source"]["target"]["structured_fields"] = {
            "specification": "nothing bundle-like here"
        }
        with pytest.raises(fam.BundleAuthorityEvidenceError) as exc:
            _decode_ok([case], tmp_path)
        assert "TARGET source block" in exc.value.reason

    def test_cross_listing_substitution_sealed_raw_loads(self, tmp_path):
        # Listing A's record over listing B's channel (same source class /
        # form / quantity, different raw_detail): the sealed defect is
        # labeled at the presentation gate, where the implementation
        # observes it; the loader's corroborative gate checks fire.
        channel_a = _bundle_channel(None, EST_RAW_DETAIL)
        channel_b = _bundle_channel(None, "bundle: 1x SSD + 1x cable, complete list")
        record_a = fu4.candidate_composition_from_channel(channel_a)
        parts_b = _proven_parts()
        target = parts_b["target"]
        case = _sealed_case(
            base=parts_b,
            case_id="FA4-ADV-002",
            stage="PRESENTATION_GATE",
            matrix_row="D3",
            candidate_composition=record_a,
            candidate_source_block={
                "title_text": TITLE,
                "structured_fields": {"packaging": "bundle: 1x SSD + 1x cable, complete list"},
                "source_url": None,
                "retrieved_utc": None,
                "raw_reference": None,
                "archive": None,
                "archive_digest": None,
                "recording_attestation": fam.SYNTHETIC_RECORDING_ATTESTATION,
            },
            target_att_source={
                "state": "REVIEWED_DETERMINATION",
                "verbatim": target.completeness_attestation.attestation_text,
                "anchor": "manufacturer bundle specification (recorded review anchor)",
            },
            candidate_att_source={
                "state": "PUBLISHED_STATEMENT",
                "verbatim": record_a.completeness_attestation.attestation_text,
                "location": "structured field 'packaging'",
            },
        )
        # The presented channel is listing B's; the record binds A's.
        _set_path(case, "derivation_inputs.channel", channel_b.canonical())
        # The recorded case carries B's channel (the case-internal
        # channel equality holds - the defect is the record's binding).
        case_b = _case_with_channel(channel_b, case_id="c1-cross-1")
        _set_path(case, "recorded_case.v2_case_document", case_b.canonical())
        _set_path(case, "published_quantity.candidate", None)
        bundle, _ = _decode_ok([case], tmp_path)
        assert bundle.cases[0].expected["outcome"] == "REFUSED"

    def test_cross_listing_substitution_over_sound_label_rejected(self, tmp_path):
        channel_a = _bundle_channel(None, EST_RAW_DETAIL)
        channel_b = _bundle_channel(None, "bundle: 1x SSD + 1x cable, complete list")
        record_a = fu4.candidate_composition_from_channel(channel_a)
        parts_b = _proven_parts()
        case = _proven_case()
        case["derivation_inputs"]["channel"] = channel_b.canonical()
        case["derivation_inputs"]["candidate_composition"] = _candidate_sealed_doc(record_a)
        case_b = _case_with_channel(channel_b, case_id="c1-cross-1")
        case["recorded_case"]["v2_case_document"] = case_b.canonical()
        case["completeness_attestation_source"]["candidate"] = {
            "state": "ABSENT", "verbatim": None, "location": None
        }
        with pytest.raises(fam.BundleAuthorityEvidenceError):
            _decode_ok([case], tmp_path)

    def test_extraction_basis_missing_embedded_result_sealed_raw(self, tmp_path):
        _, parts = _extraction_case()
        record_doc = copy.deepcopy(_candidate_sealed_doc(parts["candidate"]))
        record_doc["extraction_result"] = None
        # Keep the record document self-consistent minus the embedding so
        # the observed refusal is the constructor's embedded-original
        # requirement (the B9-i sealed-raw shape).
        record_doc = _reseal_candidate_doc(record_doc)
        case = _sealed_case(
            base=parts,
            case_id="FA4-ADV-003",
            stage="CONSTRUCTION",
            error_type="CONSTRUCTOR",
            matrix_row="B9",
            candidate_basis="EXTRACTION_RESULT_V1",
            extraction_evidence={
                "input_document": None,
                "result_document": _result_sealed_doc(parts["result"]),
            },
            candidate_source_block=parts["candidate_source_block"],
        )
        _set_path(case, "derivation_inputs.candidate_composition", record_doc)
        bundle, _ = _decode_ok([case], tmp_path)
        assert bundle.cases[0].expected["refusal"]["stage"] == "CONSTRUCTION"

    def test_extraction_basis_missing_embedded_result_over_sound_label_rejected(
        self, tmp_path
    ):
        case, parts = _extraction_case()
        record_doc = copy.deepcopy(_candidate_sealed_doc(parts["candidate"]))
        record_doc["extraction_result"] = None
        record_doc = _reseal_candidate_doc(record_doc)
        case["derivation_inputs"]["candidate_composition"] = record_doc
        with pytest.raises(fam.BundleAuthorityEvidenceError):
            _decode_ok([case], tmp_path)

    def test_extraction_input_digest_mismatch_sealed_raw(self, tmp_path):
        case, parts = _extraction_case()
        case2 = _sealed_case(
            base=parts,
            case_id="FA4-ADV-004",
            stage="CONSTRUCTION",
            matrix_row="D6",
            candidate_basis="EXTRACTION_RESULT_V1",
            extraction_evidence={
                "input_document": {"altered": "examined input"},
                "result_document": _result_sealed_doc(parts["result"]),
            },
            candidate_source_block=parts["candidate_source_block"],
        )
        bundle, _ = _decode_ok([case2], tmp_path)
        assert bundle.cases[0].expected["refusal"]["stage"] == "CONSTRUCTION"

    def test_extraction_input_digest_mismatch_over_sound_label_rejected(self, tmp_path):
        case, parts = _extraction_case()
        case["derivation_inputs"]["extraction_evidence"] = {
            "input_document": {"altered": "examined input"},
            "result_document": _result_sealed_doc(parts["result"]),
        }
        with pytest.raises(fam.BundleAuthorityEvidenceError) as exc:
            _decode_ok([case], tmp_path)
        assert "input_digest" in exc.value.reason

    def test_missing_completeness_attestation_sealed_raw(self, tmp_path):
        parts = _proven_parts()
        record_doc = copy.deepcopy(_candidate_sealed_doc(parts["candidate"]))
        record_doc["completeness_attestation"] = None
        record_doc = _reseal_candidate_doc(record_doc)
        case = _sealed_case(
            base=parts,
            case_id="FA4-ADV-005",
            stage="CONSTRUCTION",
            matrix_row="B2",
            candidate_source_block={
                "title_text": TITLE,
                "structured_fields": {"packaging": EST_RAW_DETAIL},
                "source_url": None,
                "retrieved_utc": None,
                "raw_reference": None,
                "archive": None,
                "archive_digest": None,
                "recording_attestation": fam.SYNTHETIC_RECORDING_ATTESTATION,
            },
            candidate_att_source={"state": "ABSENT", "verbatim": None, "location": None},
        )
        _set_path(case, "derivation_inputs.candidate_composition", record_doc)
        bundle, _ = _decode_ok([case], tmp_path)
        assert bundle.cases[0].expected["refusal"]["stage"] == "CONSTRUCTION"

    def test_model_claim_disguised_as_publisher_evidence_rejected(
        self, tmp_path
    ):
        # A self-consistent "published" completeness statement the sealed
        # candidate source never published: the sound-labeled case is
        # refused at the corpus level (a model claim cannot ride into a
        # sealed sound case), and the same documents are sealable ONLY
        # under the presentation-gate label (the ungrounded statement is
        # observed at the association layer, never as publisher evidence).
        parts = _proven_parts()
        att_doc = copy.deepcopy(
            parts["candidate"].completeness_attestation.canonical(),
        )
        att_doc["attestation_text"] = "complete per the model review"
        att_doc["attestation_digest"] = fam.canonical_sha256(
            {k: v for k, v in att_doc.items() if k != "attestation_digest"}
        )
        record_doc = copy.deepcopy(_candidate_sealed_doc(parts["candidate"]))
        record_doc["completeness_attestation"] = att_doc
        record_doc = _reseal_candidate_doc(record_doc)
        sound_case = _proven_case()
        sound_case["derivation_inputs"]["candidate_composition"] = record_doc
        sound_case["completeness_attestation_source"]["candidate"]["verbatim"] = (
            "complete per the model review"
        )
        with pytest.raises(fam.BundleAuthorityEvidenceError) as exc:
            _decode_ok([sound_case], tmp_path)
        assert "span-grounded" in exc.value.reason

        sealed_case = _sealed_case(
            base=parts,
            case_id="FA4-ADV-006",
            stage="PRESENTATION_GATE",
            matrix_row="D18",
            candidate_source_block={
                "title_text": TITLE,
                "structured_fields": {"packaging": EST_RAW_DETAIL},
                "source_url": None,
                "retrieved_utc": None,
                "raw_reference": None,
                "archive": None,
                "archive_digest": None,
                "recording_attestation": fam.SYNTHETIC_RECORDING_ATTESTATION,
            },
            candidate_att_source={
                "state": "PUBLISHED_STATEMENT",
                "verbatim": "complete per the model review",
                "location": "structured field 'packaging'",
            },
        )
        _set_path(sealed_case, "derivation_inputs.candidate_composition", record_doc)
        bundle, _ = _decode_ok([sealed_case], tmp_path)
        assert bundle.cases[0].expected["refusal"]["stage"] == "PRESENTATION_GATE"

    def test_forged_reviewer_association_same_identity(self, tmp_path):
        case = _proven_case()
        case["label"]["reviewer"] = case["label"]["author"]
        with pytest.raises(fam.BundleAuthorityLabelError) as exc:
            _decode_ok([case], tmp_path)
        assert "distinct" in exc.value.reason

    def test_forged_reviewer_association_model_named(self, tmp_path):
        case = _proven_case()
        case["label"]["rationale"] = "the reviewer is qwen"
        with pytest.raises(fam.BundleAuthorityLabelError) as exc:
            _decode_ok([case], tmp_path)
        assert "qwen" in exc.value.reason


def _extraction_case():
    """One sound EXTRACTION-basis fixture: the frozen P2 chain over a
    marker-carrying title (evidence ACQUISITION - the recorded original
    result is the v3 embedding), the mapped channel as the presented
    channel, the same attested target as the PROVEN fixture. The
    recorded V2 case is built from the SAME extended-title observation
    the sealed candidate source block records (the mandatory provenance
    binding: the recorded case and the sealed source describe one
    listing)."""
    title = f"{TITLE} - bundle: {CLAUSE}, complete list"
    result, channel = extract_and_map_sales_unit_evidence(_observation(title), None)
    candidate = fu4.candidate_composition_from_extraction(result)
    parts = _frozen_case_parts(observation=_observation(title), case_id="c1-extraction-1")
    case = dataclasses.replace(
        parts["case"],
        candidate_commercial=dataclasses.replace(
            parts["case"].candidate_commercial, sales_unit=channel
        ),
    )
    target = _proven_parts()["target"]
    assessment = parts["context"]
    evaluation = parts["evaluation"]
    decision = fu4.derive_authority_tier_fu4(
        assessment,
        channel,
        evaluation,
        case.context_provenances,
        case.product_evidence,
        None,
        target_unit_evidence=target,
        candidate_composition=candidate,
        quantity_attestation=None,
    )
    candidate_source_block = {
        "title_text": title,
        "structured_fields": {},
        "source_url": None,
        "retrieved_utc": None,
        "raw_reference": None,
        "archive": None,
        "archive_digest": None,
        "recording_attestation": fam.SYNTHETIC_RECORDING_ATTESTATION,
    }
    base = {
        "case": case,
        "channel": channel,
        "candidate": candidate,
        "target": target,
        "assessment": assessment,
        "evaluation": evaluation,
        "decision": decision,
        "result": result,
        "candidate_source_block": candidate_source_block,
    }
    case_doc = _synthesize_case(
        case_id="FA4-PROV-002",
        matrix_row="A1",
        channel=channel,
        candidate_composition=candidate,
        candidate_basis="EXTRACTION_RESULT_V1",
        extraction_evidence={
            "input_document": None,
            "result_document": _result_sealed_doc(result),
        },
        target_evidence_schema="fu4_v3",
        target_evidence_document=_target_sealed_doc(target),
        quantity_attestation_document=None,
        case=case,
        assessment=assessment,
        evaluation=evaluation,
        decision=decision,
        surface="DERIVATION",
        candidate_source_block=candidate_source_block,
        payload_target_typed=target,
    )
    return case_doc, base


# ---------------------------------------------------------------------------
# Sealed-raw defect scoping (the stage-coherence rule: the labeled
# refusal stage must be coherent with what the loader can observe
# WITHOUT executing the derivation)
# ---------------------------------------------------------------------------


class TestSealedRawScoping:
    def test_constructor_stage_defect_loads_as_sealed_raw(self, tmp_path):
        # B8 shape: a candidate record whose source is a frozen enum
        # member not permitted on the composition surface.
        parts = _proven_parts()
        record_doc = copy.deepcopy(_candidate_sealed_doc(parts["candidate"]))
        record_doc["source"] = "SPECIFICATION_TEXT"
        record_doc = _reseal_candidate_doc(record_doc)
        case = _sealed_case(
            base=parts,
            case_id="FA4-ADV-007",
            stage="CONSTRUCTION",
            error_type="CONSTRUCTOR",
            matrix_row="B8",
        )
        _set_path(case, "derivation_inputs.candidate_composition", record_doc)
        bundle, _ = _decode_ok([case], tmp_path)
        assert bundle.cases[0].expected["refusal"]["stage"] == "CONSTRUCTION"

    def test_attestation_laundering_loads_as_sealed_raw(self, tmp_path):
        # D14 shape: a candidate-side record carrying a
        # REVIEWED_COMPOSITION_ATTESTATION basis (a review attests the
        # target side, never the candidate listing).
        parts = _proven_parts()
        att_doc = copy.deepcopy(
            parts["candidate"].completeness_attestation.canonical(),
        )
        att_doc["basis"] = "REVIEWED_COMPOSITION_ATTESTATION"
        att_doc["attestation_digest"] = fam.canonical_sha256(
            {k: v for k, v in att_doc.items() if k != "attestation_digest"}
        )
        record_doc = copy.deepcopy(_candidate_sealed_doc(parts["candidate"]))
        record_doc["completeness_attestation"] = att_doc
        record_doc = _reseal_candidate_doc(record_doc)
        case = _sealed_case(
            base=parts,
            case_id="FA4-ADV-008",
            stage="CONSTRUCTION",
            matrix_row="D14",
        )
        _set_path(case, "derivation_inputs.candidate_composition", record_doc)
        bundle, _ = _decode_ok([case], tmp_path)
        assert bundle.cases[0].expected["refusal"]["stage"] == "CONSTRUCTION"

    def test_codec_stage_defect_loads_as_sealed_raw(self, tmp_path):
        # D16 shape: a forged mixed-axis payload (V2, 2.0, 1, 1, FU4) -
        # no registered adapter claims it; the codec refuses.
        case = _proven_case(case_id="FA4-ADV-009", surface="RECORD")
        payload_doc = copy.deepcopy(case["recorded_case"]["payload_document"])
        payload_doc["contract"]["prompt_version"] = "2.0"
        expected = _sealed_refusal_expected(
            stage="CODEC_DECODE", error_type="CODEC", replay="REPLAY_REFUSED"
        )
        _set_path(case, "expected", expected)
        _set_path(case, "recorded_case.payload_document", payload_doc)
        bundle, _ = _decode_ok([case], tmp_path)
        assert bundle.cases[0].expected["refusal"]["stage"] == "CODEC_DECODE"

    def test_replay_stage_self_consistent_shape_loads(self, tmp_path):
        # A fully sound record labeled REPLAY_REFUSED: the loader must
        # accept it (the defect lives in the derived section, which only
        # the replay - never the decoder - observes). This proves the
        # decoder does NOT execute the derivation / replay to confirm
        # labels.
        case = _proven_case(case_id="FA4-ADV-010", surface="BOTH")
        expected = _sealed_refusal_expected(
            stage="REPLAY_AGREEMENT", error_type="REPLAY", replay="REPLAY_REFUSED"
        )
        _set_path(case, "expected", expected)
        bundle, _ = _decode_ok([case], tmp_path)
        assert bundle.cases[0].expected["refusal"]["stage"] == "REPLAY_AGREEMENT"

    def test_corpus_integrity_channel_mismatch_loads_as_sealed_raw(self, tmp_path):
        # D6-ii shape: the derivation channel differs from the recorded
        # case's channel - the case-document-integrity observation the
        # family loader owns.
        parts = _proven_parts()
        channel_b = _bundle_channel(
            None, "bundle: 1x SSD + 1x cable, complete list"
        )
        case = _sealed_case(
            base=parts,
            case_id="FA4-ADV-011",
            stage="CORPUS_INTEGRITY",
            matrix_row="D6",
            candidate_source_block={
                "title_text": TITLE,
                "structured_fields": {
                    "packaging": "bundle: 1x SSD + 1x cable, complete list"
                },
                "source_url": None,
                "retrieved_utc": None,
                "raw_reference": None,
                "archive": None,
                "archive_digest": None,
                "recording_attestation": fam.SYNTHETIC_RECORDING_ATTESTATION,
            },
            candidate_att_source={
                "state": "ABSENT",
                "verbatim": None,
                "location": None,
            },
            target_att_source={"state": "ABSENT", "verbatim": None, "anchor": None},
        )
        # The presented (derivation) channel is listing B's; the record
        # still binds listing A's content, and the candidate clause is
        # listing A's (ungrounded in B's sealed block - the gate layer
        # corroborates).
        record_a = parts["candidate"]
        _set_path(case, "derivation_inputs.channel", channel_b.canonical())
        _set_path(case, "derivation_inputs.candidate_composition", _candidate_sealed_doc(record_a))
        bundle, _ = _decode_ok([case], tmp_path)
        assert bundle.cases[0].expected["refusal"]["stage"] == "CORPUS_INTEGRITY"

    def test_incoherent_construction_label_over_sound_documents(self, tmp_path):
        case = _proven_case(case_id="FA4-ADV-012", surface="DERIVATION")
        expected = _sealed_refusal_expected(
            stage="CONSTRUCTION", error_type="CONSTRUCTOR"
        )
        _set_path(case, "expected", expected)
        with pytest.raises(fam.BundleAuthorityLabelError) as exc:
            _decode_ok([case], tmp_path)
        assert "not observable" in exc.value.reason

    def test_incoherent_corpus_integrity_label_without_defect(self, tmp_path):
        case = _proven_case(case_id="FA4-ADV-013", surface="DERIVATION")
        expected = _sealed_refusal_expected(stage="CORPUS_INTEGRITY")
        _set_path(case, "expected", expected)
        with pytest.raises(fam.BundleAuthorityLabelError) as exc:
            _decode_ok([case], tmp_path)
        assert "defect is not present" in exc.value.reason

    def test_incoherent_gate_label_over_constructor_defect(self, tmp_path):
        parts = _proven_parts()
        record_doc = copy.deepcopy(_candidate_sealed_doc(parts["candidate"]))
        record_doc["source"] = "SPECIFICATION_TEXT"
        record_doc = _reseal_candidate_doc(record_doc)
        case = _sealed_case(
            base=parts,
            case_id="FA4-ADV-014",
            stage="PRESENTATION_GATE",
            matrix_row="B8",
        )
        _set_path(case, "derivation_inputs.candidate_composition", record_doc)
        with pytest.raises(fam.BundleAuthorityLabelError) as exc:
            _decode_ok([case], tmp_path)
        assert "self-consistent sealed shapes" in exc.value.reason

    def test_incoherent_codec_label_over_derivation_surface(self, tmp_path):
        parts = _proven_parts()
        record_doc = copy.deepcopy(_candidate_sealed_doc(parts["candidate"]))
        record_doc["source"] = "SPECIFICATION_TEXT"
        record_doc = _reseal_candidate_doc(record_doc)
        case = _sealed_case(
            base=parts,
            case_id="FA4-ADV-015",
            stage="CODEC_DECODE",
            matrix_row="B8",
        )
        _set_path(case, "derivation_inputs.candidate_composition", record_doc)
        with pytest.raises(fam.BundleAuthorityLabelError) as exc:
            _decode_ok([case], tmp_path)
        assert "record surface" in exc.value.reason

    def test_error_type_must_match_stage(self, tmp_path):
        case = _proven_case(case_id="FA4-ADV-016", surface="DERIVATION")
        expected = _sealed_refusal_expected(
            stage="CONSTRUCTION", error_type="CODEC"
        )
        _set_path(case, "expected", expected)
        with pytest.raises(fam.BundleAuthoritySchemaError) as exc:
            _decode_ok([case], tmp_path)
        assert "error class of stage" in exc.value.reason

    def test_corpus_integrity_stage_names_no_error_class(self, tmp_path):
        case = _proven_case(case_id="FA4-ADV-017", surface="DERIVATION")
        expected = _sealed_refusal_expected(
            stage="CORPUS_INTEGRITY", error_type="CONSTRUCTOR"
        )
        _set_path(case, "expected", expected)
        with pytest.raises(fam.BundleAuthoritySchemaError):
            _decode_ok([case], tmp_path)

    def test_quantity_attestation_wrong_missing_side_loads_as_sealed_raw(
        self, tmp_path
    ):
        # D15-i shape: the quantity attestation's subject is not the
        # actually-missing side (the construction-level integrity error
        # the frozen derivation's admissibility rule enforces).
        case, parts = _quantity_attestation_case(subject="TARGET")
        att_doc = copy.deepcopy(_qty_att_sealed_doc(parts["quantity_attestation"]))
        att_doc["subject_side"] = "CANDIDATE"
        att_doc["attestation_digest"] = fam.canonical_sha256(
            {k: v for k, v in att_doc.items() if k != "attestation_digest"}
        )
        sealed = _sealed_case(
            base=parts,
            case_id="FA4-ADV-018",
            stage="CONSTRUCTION",
            matrix_row="D15",
            quantity_attestation_document=att_doc,
        )
        bundle, _ = _decode_ok([sealed], tmp_path)
        assert bundle.cases[0].expected["refusal"]["stage"] == "CONSTRUCTION"

    def test_quantity_attestation_over_symmetric_axis_loads_as_sealed_raw(
        self, tmp_path
    ):
        # D15-ii shape: the attestation is presented over a non-
        # asymmetric published axis (both sides publish) - the contract
        # misuse.
        parts = _quantity_attestation_parts(symmetry="both_publish")
        att_doc = _qty_att_sealed_doc(parts["quantity_attestation"])
        sealed = _sealed_case(
            base=parts,
            case_id="FA4-ADV-019",
            stage="CONSTRUCTION",
            matrix_row="D15",
            quantity_attestation_document=att_doc,
        )
        bundle, _ = _decode_ok([sealed], tmp_path)
        assert bundle.cases[0].expected["refusal"]["stage"] == "CONSTRUCTION"


def _quantity_attestation_parts(*, symmetry="asymmetric"):
    """The A6-shape parts: a published candidate count over attested
    agreed clauses + a silent (asymmetric) or equal (symmetric) target
    count, with the review-constructed quantity attestation on the
    missing side (the only case family where a quantity attestation is
    admissible)."""
    raw_detail = f"bundle of 3: {CLAUSE}, complete list"
    channel = _bundle_channel(3, raw_detail)
    case = _case_with_channel(channel, case_id="c1-quantity-1")
    candidate = fu4.candidate_composition_from_channel(channel)
    target_qty = None if symmetry == "asymmetric" else 3
    target = _make_target_fu4(
        CLAUSE, fu4.BundleCompositionStateV2FU4.ESTABLISHED, target_qty,
        _make_target_attestation(CLAUSE),
    )
    assessment = _context()
    evaluation = _match_evaluation()
    qty_att = _make_quantity_attestation_doc(
        fu4.EvidenceSideV2FU4.TARGET if symmetry == "asymmetric"
        else fu4.EvidenceSideV2FU4.CANDIDATE
    )
    if symmetry == "asymmetric":
        decision = fu4.derive_authority_tier_fu4(
            assessment,
            channel,
            evaluation,
            case.context_provenances,
            case.product_evidence,
            None,
            target_unit_evidence=target,
            candidate_composition=candidate,
            quantity_attestation=qty_att,
        )
    else:
        # The frozen chain itself refuses this presentation (contract
        # misuse over a non-asymmetric axis - the D15-ii point): the
        # sealed-raw fixture carries no derived decision.
        decision = None
    return {
        "case": case,
        "channel": channel,
        "candidate": candidate,
        "target": target,
        "assessment": assessment,
        "evaluation": evaluation,
        "decision": decision,
        "quantity_attestation": qty_att,
    }


def _make_quantity_attestation_doc(subject_side):
    from product_intelligence.research import (
        QuantityNonMaterialityReasonV2FU4,
        TargetSalesUnitEvidenceSourceV2,
    )

    document = {
        "schema_version": 3,
        "subject_side": subject_side.value,
        "reason": QuantityNonMaterialityReasonV2FU4
        .SUBJECT_SOURCE_STRUCTURALLY_WITHOUT_BUNDLE_COUNTS.value,
        "source": TargetSalesUnitEvidenceSourceV2.REVIEWED_TARGET_CONTEXT.value,
        "attestation_text": (
            "review determination: the subject source structurally "
            "publishes no bundle counts for this offer shape"
        ),
    }
    document["attestation_digest"] = fam.canonical_sha256(
        {k: v for k, v in document.items() if k != "attestation_digest"}
    )
    return fu4.QuantityCompletenessAttestationV2FU4(
        3,
        subject_side,
        QuantityNonMaterialityReasonV2FU4
        .SUBJECT_SOURCE_STRUCTURALLY_WITHOUT_BUNDLE_COUNTS,
        TargetSalesUnitEvidenceSourceV2.REVIEWED_TARGET_CONTEXT,
        document["attestation_text"],
        document["attestation_digest"],
    )


def _quantity_attestation_case(*, subject="TARGET"):
    parts = _quantity_attestation_parts()
    channel = parts["channel"]
    case_doc = _synthesize_case(
        case_id="FA4-PROV-003",
        matrix_row="A6",
        channel=channel,
        candidate_composition=parts["candidate"],
        candidate_basis="RECORDED_CHANNEL",
        extraction_evidence=None,
        target_evidence_schema="fu4_v3",
        target_evidence_document=_target_sealed_doc(parts["target"]),
        quantity_attestation_document=_qty_att_sealed_doc(parts["quantity_attestation"]),
        case=parts["case"],
        assessment=parts["assessment"],
        evaluation=parts["evaluation"],
        decision=parts["decision"],
        surface="DERIVATION",
        payload_target_typed=parts["target"],
    )
    return case_doc, parts


# ---------------------------------------------------------------------------
# Label governance (task section 7: no automatic expected-label
# generation, no implicit PROVEN default, no fallback to semantic MATCH,
# no pricing eligibility determination, the two-identity rule, the
# anti-derivation scan, the expected-axis coherence pre-checks)
# ---------------------------------------------------------------------------


class TestLabelGovernance:
    def test_no_implicit_proven_default(self, tmp_path):
        case = _proven_case(case_id="FA4-ADV-020")
        _set_path(case, "expected.unit", None)
        with pytest.raises(fam.BundleAuthorityLabelError) as exc:
            _decode_ok([case], tmp_path)
        assert "no default is ever filled in" in exc.value.reason

    def test_no_pricing_default(self, tmp_path):
        case = _proven_case(case_id="FA4-ADV-021")
        _set_path(case, "expected.pricing_eligible", None)
        with pytest.raises(fam.BundleAuthorityLabelError) as exc:
            _decode_ok([case], tmp_path)
        assert "never null" in exc.value.reason

    def test_no_fallback_to_semantic_match(self, tmp_path):
        # The scripted MATCH context never supplies the unit label: a
        # DERIVED case with no labeled unit is refused (the decoder has
        # no semantic-MATCH fallback path).
        case = _proven_case(case_id="FA4-ADV-022")
        del case["expected"]["unit"]
        with pytest.raises(fam.BundleAuthoritySchemaError):
            _decode_ok([case], tmp_path)

    def test_derived_requires_tier(self, tmp_path):
        case = _proven_case(case_id="FA4-ADV-023")
        _set_path(case, "expected.tier", None)
        with pytest.raises(fam.BundleAuthorityLabelError):
            _decode_ok([case], tmp_path)

    def test_derived_carries_no_refusal(self, tmp_path):
        case = _proven_case(case_id="FA4-ADV-024")
        _set_path(
            case,
            "expected.refusal",
            {"stage": "CONSTRUCTION", "error_type": "CONSTRUCTOR"},
        )
        with pytest.raises(fam.BundleAuthorityLabelError):
            _decode_ok([case], tmp_path)

    def test_refused_carries_no_unit(self, tmp_path):
        case = _proven_case(case_id="FA4-ADV-025", surface="DERIVATION")
        expected = _sealed_refusal_expected(stage="CONSTRUCTION")
        expected["unit"] = "PROVEN_EQUIVALENT"
        _set_path(case, "expected", expected)
        with pytest.raises(fam.BundleAuthorityLabelError) as exc:
            _decode_ok([case], tmp_path)
        assert "derives no unit" in exc.value.reason

    def test_refused_requires_refusal(self, tmp_path):
        case = _proven_case(case_id="FA4-ADV-026", surface="DERIVATION")
        expected = _sealed_refusal_expected(stage="CONSTRUCTION")
        expected["refusal"] = None
        _set_path(case, "expected", expected)
        with pytest.raises(fam.BundleAuthorityLabelError) as exc:
            _decode_ok([case], tmp_path)
        assert "names its refusal" in exc.value.reason

    def test_proven_requires_established_states(self, tmp_path):
        case = _proven_case(case_id="FA4-ADV-027")
        _set_path(case, "expected.candidate_composition_state", "SYNTACTICALLY_VALID")
        with pytest.raises(fam.BundleAuthorityLabelError) as exc:
            _decode_ok([case], tmp_path)
        assert "both composition states ESTABLISHED" in exc.value.reason

    def test_proven_requires_satisfied_quantity_axis(self, tmp_path):
        case = _proven_case(case_id="FA4-ADV-028")
        _set_path(case, "expected.quantity_axis", "CONTRADICTED")
        with pytest.raises(fam.BundleAuthorityLabelError) as exc:
            _decode_ok([case], tmp_path)
        assert "quantity axis" in exc.value.reason

    def test_pricing_eligible_requires_proven_unit(self, tmp_path):
        case = _proven_case(case_id="FA4-ADV-029")
        _set_path(case, "expected.unit", "UNPROVEN")
        _set_path(case, "expected.expected_ceiling", "CEILING_SALES_UNIT_NOT_PROVEN")
        _set_path(case, "expected.tier", "NEEDS_REVIEW")
        _set_path(case, "expected.pricing_eligible", True)
        with pytest.raises(fam.BundleAuthorityLabelError) as exc:
            _decode_ok([case], tmp_path)
        assert "PROVEN_EQUIVALENT" in exc.value.reason

    def test_pricing_eligible_requires_pricing_tier(self, tmp_path):
        case = _proven_case(case_id="FA4-ADV-030")
        _set_path(case, "expected.tier", "NEEDS_REVIEW")
        _set_path(case, "expected.pricing_eligible", True)
        with pytest.raises(fam.BundleAuthorityLabelError) as exc:
            _decode_ok([case], tmp_path)
        assert "pricing-eligible tier set" in exc.value.reason

    def test_ceiling_keys_to_its_unit_state(self, tmp_path):
        case = _proven_case(case_id="FA4-ADV-031")
        _set_path(case, "expected.unit", "CONTRADICTED")
        _set_path(case, "expected.tier", "NEEDS_REVIEW")
        _set_path(case, "expected.pricing_eligible", False)
        _set_path(
            case, "expected.expected_ceiling", "CEILING_SALES_UNIT_NOT_PROVEN"
        )
        with pytest.raises(fam.BundleAuthorityLabelError) as exc:
            _decode_ok([case], tmp_path)
        assert "keys exactly to unit UNPROVEN" in exc.value.reason

    def test_semantic_identity_note_track_ab_rule(self, tmp_path):
        case = _proven_case(case_id="FA4-ADV-032")
        case["track"] = "A_B"
        with pytest.raises(fam.BundleAuthorityLabelError) as exc:
            _decode_ok([case], tmp_path)
        assert "semantic-axis statement" in exc.value.reason

    def test_semantic_identity_note_absent_for_track_a(self, tmp_path):
        case = _proven_case(case_id="FA4-ADV-033")
        _set_path(case, "expected.semantic_identity_note", "a match context")
        with pytest.raises(fam.BundleAuthorityLabelError) as exc:
            _decode_ok([case], tmp_path)
        assert "no semantic-identity note" in exc.value.reason

    def test_author_must_differ_from_reviewer(self, tmp_path):
        case = _proven_case(case_id="FA4-ADV-034")
        case["label"]["reviewer"] = case["label"]["author"]
        with pytest.raises(fam.BundleAuthorityLabelError) as exc:
            _decode_ok([case], tmp_path)
        assert "distinct" in exc.value.reason

    @pytest.mark.parametrize(
        "path, text",
        [
            ("label.rationale", "the expected outcome came from the model output"),
            ("label.rationale", "verified against qwen's response"),
            ("label.rationale", "matches the implementation output"),
            ("label.rationale", "the replay agreement shows it"),
            ("label.rationale", "derive_sales_unit_authority said so"),
            ("label.grounding_citation", "GPT-4 judged this PROVEN"),
            ("label.grounding_citation", "per the model-generated extraction"),
        ],
    )
    def test_anti_derivation_label_scan(self, tmp_path, path, text):
        case = _proven_case(case_id="FA4-ADV-035")
        _set_path(case, path, text)
        with pytest.raises(fam.BundleAuthorityLabelError) as exc:
            _decode_ok([case], tmp_path)
        assert "independent of any model or" in exc.value.reason

    def test_independence_attestation_must_be_fixed(self, tmp_path):
        case = _proven_case(case_id="FA4-ADV-036")
        _set_path(case, "label.independence_attestation", "independent, promise")
        with pytest.raises(fam.BundleAuthorityLabelError) as exc:
            _decode_ok([case], tmp_path)
        assert "fixed independence attestation" in exc.value.reason

    def test_review_status_must_be_reviewed(self, tmp_path):
        case = _proven_case(case_id="FA4-ADV-037")
        _set_path(case, "label.review_status", "UNREVIEWED")
        with pytest.raises(fam.BundleAuthoritySchemaError):
            _decode_ok([case], tmp_path)

    def test_label_utc_instants_strict(self, tmp_path):
        case = _proven_case(case_id="FA4-ADV-038")
        _set_path(case, "label.author_utc", "2026-01-02T00:00:00")
        with pytest.raises(fam.BundleAuthoritySchemaError):
            _decode_ok([case], tmp_path)


# ---------------------------------------------------------------------------
# Authority separation (task section 7: no automatic expected-label
# generation, no implicit PROVEN_EQUIVALENT default, no fallback to
# semantic MATCH, no pricing eligibility determination, no import or
# execution of the production authority evaluator) + the import boundary
# (design section 9.3 acceptance) + the vocabulary drift pins
# ---------------------------------------------------------------------------

#: The exact research symbol allowlist of the family loader (the C1
#: import-scan acceptance: the package imports ONLY the frozen research
#: public surface - constructors, record types, bounded vocabularies, the
#: house canonical digest, the universal codec, the frozen P2 channel
#: mapping - and nothing else).
ALLOWED_RESEARCH_SYMBOLS = frozenset(
    {
        # canonical / codec (the record surface + the house discipline)
        "canonical_sha256",
        "decode_semantic_decision_record",
        "registered_envelope_schema_versions",
        # the exact FU4 binding (the seal registry)
        "V2_FU4_CONTRACT_BINDING",
        # FU4 evidence records + constructors-as-validators (no derivation)
        "BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4",
        "BundleCompositionEvidenceIntegrityError",
        "BundleCompositionStateV2FU4",
        "BundleQuantityAxisStateV2FU4",
        "CandidateBundleCompositionEvidenceV2FU4",
        "CandidateCompositionEvidenceBasisV2FU4",
        "CompletenessBasisV2FU4",
        "CompositionCompletenessAttestationV2FU4",
        "EvidenceSideV2FU4",
        "QuantityCompletenessAttestationV2FU4",
        "QuantityNonMaterialityReasonV2FU4",
        "TargetSalesUnitEvidenceV2FU4",
        # FU3 data (the frozen firewall records + the unit vocabulary)
        "SalesUnitAuthorityV2",
        "TargetSalesUnitEvidenceSourceV2",
        "TargetSalesUnitEvidenceV2",
        "TargetSalesUnitFormV2",
        "AuthorityRuleV2FU4",
        # the frozen P2 extraction (evidence acquisition - the recorded
        # original result; NOT label determination)
        "SALES_UNIT_EXTRACTION_SCHEMA_VERSION",
        "SalesUnitCueDisposition",
        "SalesUnitCueField",
        "SalesUnitCueReason",
        "SalesUnitCueV1",
        "SalesUnitExtractionIntegrityError",
        "SalesUnitExtractionResult",
        "SalesUnitExtractionState",
        "SalesUnitIdentifierFieldNoteV1",
        "sales_unit_channel_from_extraction",
        # the frozen S2-A / S2-C data (context, evaluation, tiers, pricing
        # set as DATA, the V2 case contract)
        "AuthorityTier",
        "ConflictClass",
        "ContextProvenance",
        "PRICING_ELIGIBLE_TIERS",
        "IdentityRelationshipSignal",
        "IdentityStateAssessmentV2",
        "IdentityStateV2",
        "ProductEvidenceDimension",
        "ProductEvidenceFactV2",
        "ProductEvidenceProfileV2",
        "CandidateProductEvidenceSource",
        "RelationshipRequirement",
        "SemanticEvaluationStateV2",
        "SemanticEvaluationV2",
        "V2Confidence",
        "V2SemanticDecision",
        "substate_relationship_requirement",
        "VerifiedSubstateV2",
        "UncertainSubstateV2",
        "ConflictSubstateV2",
        "UnevaluableSubstateV2",
        # the frozen S2-C case contract (research.semantic_v2)
        "CandidateCommercialEvidenceV2",
        "CandidateEvidenceSourceV2",
        "CandidateObservationFactV2",
        "CandidateProductDimensionV2",
        "CandidateProductEvidenceV2",
        "CandidateSalesUnitEvidenceV2",
        "PackagingEvidenceStateV2",
        "ReviewedTargetContextV2",
        "SalesUnitKindV2",
        "SemanticMatchCaseV2",
        "TargetEvidenceV2",
        "TargetIdentifierRelationKindV2",
    }
)

#: The label-determining surface the family package must never import
#: (the implementation-output prohibition of design section 4.6, made
#: mechanical over the C1 package).
FORBIDDEN_RESEARCH_SYMBOLS = frozenset(
    {
        "derive_sales_unit_authority_fu4",
        "derive_sales_unit_authority_fu4_case",
        "derive_authority_tier_fu4",
        "derive_authority_tier_for_contract_fu4",
        "derive_sales_unit_authority",
        "derive_authority_tier",
        "sales_unit_authority_from_channel",
        "derive_authority_tier_for_contract",
        "replay_semantic_decision",
        "extract_sales_unit_evidence",
        "extract_and_map_sales_unit_evidence",
        "candidate_composition_from_extraction",
        "candidate_composition_from_channel",
        "extract_published_bundle_clause",
        "classify_clause_closure",
        "AuthorityDecisionV2FU4",
        "AuthorityDecisionV2FU3",
        "SemanticDecisionRecordV2FU4",
        "SEMANTIC_V2_FU4_ADAPTER",
        "V2_FU4_AUTHORITY_QUALIFIED",
    }
)

_ALLOWED_IMPORT_ROOTS = (
    "product_intelligence.research",
    "product_intelligence.domain",
    "product_intelligence.evaluation.bundle_authority",
)
_FORBIDDEN_IMPORT_PREFIXES = (
    "product_intelligence.evaluation.semantic_v2",
    "product_intelligence.execution",
    "product_intelligence.runs",
    "product_intelligence.web",
    "product_intelligence.providers",
    "product_intelligence.semantic",
    "django",
)


def _family_python_files():
    return sorted(FAMILY_PACKAGE_ROOT.rglob("*.py"))


def _imported_names(path: Path) -> set:
    names = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and not node.level and node.module:
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
    return names


def _imported_modules(path: Path) -> set:
    modules = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            modules.add(node.module)
    return modules


class TestAuthoritySeparation:
    def test_family_package_has_source_files_to_check(self):
        assert _family_python_files()

    @pytest.mark.parametrize("path", _family_python_files(), ids=lambda p: p.name)
    def test_imports_only_the_allowed_surface(self, path):
        modules = _imported_modules(path)
        offending = set()
        for module in modules:
            root = module.split(".")[0]
            if root in sys.stdlib_module_names or module.startswith("_"):
                continue
            if module.startswith("product_intelligence"):
                if not module.startswith(_ALLOWED_IMPORT_ROOTS):
                    offending.add(module)
                continue
            offending.add(module)
        assert not offending, f"{path.name} imports outside the allowed surface: {sorted(offending)}"

    @pytest.mark.parametrize("path", _family_python_files(), ids=lambda p: p.name)
    def test_imports_no_forbidden_boundary(self, path):
        modules = _imported_modules(path)
        offending = {
            module
            for module in modules
            for prefix in _FORBIDDEN_IMPORT_PREFIXES
            if module == prefix or module.startswith(prefix + ".")
        }
        assert not offending, (
            f"{path.name} imports a forbidden boundary {sorted(offending)} "
            "(no semantic_v2 harness module, no execution / runs / web / "
            "providers, no prompt owner, no Django)"
        )

    def test_corpus_module_research_symbols_are_the_exact_allowed_set(self):
        corpus_file = FAMILY_PACKAGE_ROOT / "corpus.py"
        research_names = set()
        for node in ast.walk(ast.parse(corpus_file.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.ImportFrom)
                and not node.level
                and node.module is not None
                and node.module.startswith("product_intelligence.research")
            ):
                research_names.update(alias.name for alias in node.names)
        unexpected = research_names - ALLOWED_RESEARCH_SYMBOLS
        assert not unexpected, (
            f"corpus.py imports research symbols outside the C1 allowlist: "
            f"{sorted(unexpected)} (the import boundary must be widened by "
            "an explicit recorded decision, never silently)"
        )
        # Drift pin: every allowlisted symbol is a real frozen export.
        import product_intelligence.research as research
        import product_intelligence.research.semantic_v2 as research_semantic_v2

        missing = [
            name
            for name in sorted(ALLOWED_RESEARCH_SYMBOLS)
            if not hasattr(research, name) and not hasattr(research_semantic_v2, name)
        ]
        assert not missing, f"allowlist names missing from the frozen research surface: {missing}"

    @pytest.mark.parametrize("path", _family_python_files(), ids=lambda p: p.name)
    def test_imports_no_label_determining_surface(self, path):
        names = _imported_names(path)
        offending = names & FORBIDDEN_RESEARCH_SYMBOLS
        assert not offending, (
            f"{path.name} imports the label-determining surface {sorted(offending)}; "
            "the corpus decoder never imports or invokes the FU4 authority "
            "derivation, the R1 replay, or the construction entry points "
            "(design section 4.6 item 2)"
        )

    def test_decoder_never_executes_the_authority_derivation(self, tmp_path, monkeypatch):
        # The behavioral half of the prohibition: assemble the sealed
        # corpus FIRST, then replace every production authority entry
        # point with a raising sentinel and re-verify - the decoder
        # never touched them.
        case = _proven_case()

        def _sentinel(*args, **kwargs):
            raise AssertionError(
                "the corpus decoder invoked a production authority entry "
                "point (the label-determining surface)"
            )

        monkeypatch.setattr(fu4, "derive_sales_unit_authority_fu4", _sentinel)
        monkeypatch.setattr(fu4, "derive_sales_unit_authority_fu4_case", _sentinel)
        monkeypatch.setattr(fu4, "derive_authority_tier_fu4", _sentinel)
        monkeypatch.setattr(fu4, "derive_authority_tier_for_contract_fu4", _sentinel)
        import product_intelligence.research.semantic_decision_replay as replay

        monkeypatch.setattr(replay, "replay_semantic_decision", _sentinel)
        bundle, _ = _decode_ok([case], tmp_path)
        assert bundle.cases[0].expected["unit"] == "PROVEN_EQUIVALENT"

    def test_no_expected_label_generation(self, tmp_path):
        # A DERIVED expectation missing its unit is refused - never
        # filled in (no implicit PROVEN_EQUIVALENT default, no
        # implementation-derived label).
        case = _proven_case(case_id="FA4-ADV-040")
        _set_path(case, "expected.unit", None)
        with pytest.raises(fam.BundleAuthorityLabelError) as exc:
            _decode_ok([case], tmp_path)
        assert "no default is ever filled in" in exc.value.reason

    def test_no_pricing_eligibility_determination(self, tmp_path):
        # A DERIVED expectation missing its pricing consequence is
        # refused - never computed from the tier.
        case = _proven_case(case_id="FA4-ADV-041")
        _set_path(case, "expected.pricing_eligible", None)
        with pytest.raises(fam.BundleAuthorityLabelError) as exc:
            _decode_ok([case], tmp_path)
        assert "never null" in exc.value.reason


class TestVocabularyDriftPins:
    """Every bounded contract vocabulary is drift-pinned to the frozen
    research exports (design section 9.3 acceptance: no literal
    copies - the P1 discipline)."""

    def test_unit_vocabulary_is_the_frozen_fu3_axis(self):
        from product_intelligence.research import SalesUnitAuthorityV2

        assert fam.UNIT_VALUES == frozenset(u.value for u in SalesUnitAuthorityV2)

    def test_composition_state_vocabulary_is_frozen(self):
        assert fam.COMPOSITION_STATE_VALUES == frozenset(
            s.value for s in fu4.BundleCompositionStateV2FU4
        )

    def test_quantity_axis_vocabulary_is_frozen(self):
        assert fam.QUANTITY_AXIS_VALUES == frozenset(
            s.value for s in fu4.BundleQuantityAxisStateV2FU4
        )

    def test_tier_vocabulary_is_frozen(self):
        from product_intelligence.research import AuthorityTier

        assert fam.TIER_VALUES == frozenset(t.value for t in AuthorityTier)

    def test_ceiling_vocabulary_is_the_two_frozen_sales_unit_ceilings(self):
        assert fam.CEILING_VALUES == frozenset(
            {
                "CEILING_SALES_UNIT_NOT_PROVEN",
                "CEILING_SALES_UNIT_CONTRADICTED",
            }
        )

    def test_pricing_eligible_tier_set_is_frozen(self):
        assert fam.PRICING_ELIGIBLE_TIER_VALUES == frozenset(
            t.value for t in PRICING_ELIGIBLE_TIERS
        )

    def test_candidate_basis_vocabulary_is_frozen_plus_none(self):
        assert fam.CANDIDATE_BASIS_VALUES == (
            frozenset(b.value for b in fu4.CandidateCompositionEvidenceBasisV2FU4)
            | {"NONE"}
        )

    def test_evidence_kind_vocabulary_matches_the_semantic_family(self):
        from product_intelligence.evaluation.semantic_v2.fixtures import (
            EVIDENCE_KINDS as SEMANTIC_EVIDENCE_KINDS,
        )

        assert fam.EVIDENCE_KINDS == frozenset(SEMANTIC_EVIDENCE_KINDS)

    def test_fu4_binding_is_the_registered_binding(self):
        from product_intelligence.research import V2_FU4_CONTRACT_BINDING

        assert fam.FU4_BINDING == tuple(V2_FU4_CONTRACT_BINDING)

    def test_seal_registry_is_exactly_the_fu4_seal(self):
        assert fam.BINDING_AUTHORITY_CORPUS_VERSIONS == {
            fam.FU4_BINDING: fam.FIRST_CORPUS_VERSION
        }

    def test_channel_vocabularies_are_frozen(self):
        from product_intelligence.research import (
            CandidateEvidenceSourceV2,
            PackagingEvidenceStateV2,
            SalesUnitKindV2,
        )

        assert fam._CHANNEL_STATE_VALUES == frozenset(
            s.value for s in PackagingEvidenceStateV2
        )
        assert fam._CHANNEL_KIND_VALUES == frozenset(
            k.value for k in SalesUnitKindV2
        )
        assert fam._CANDIDATE_EVIDENCE_SOURCE_VALUES == frozenset(
            s.value for s in CandidateEvidenceSourceV2
        )

    def test_extraction_vocabularies_are_frozen(self):
        from product_intelligence.research import (
            SalesUnitCueDisposition,
            SalesUnitCueField,
            SalesUnitCueReason,
            SalesUnitExtractionState,
        )

        assert fam._CUE_FIELD_VALUES == frozenset(f.value for f in SalesUnitCueField)
        assert fam._CUE_DISPOSITION_VALUES == frozenset(
            d.value for d in SalesUnitCueDisposition
        )
        assert fam._CUE_REASON_VALUES == frozenset(r.value for r in SalesUnitCueReason)
        assert fam._EXTRACTION_STATE_VALUES == frozenset(
            s.value for s in SalesUnitExtractionState
        )


# ---------------------------------------------------------------------------
# The manifest integrity (task section 5: the twelve checks) + the
# declared source-file digest consistency + historical preservation
# ---------------------------------------------------------------------------


class TestManifestIntegrity:
    def test_manifest_rebuilds_reproducibly(self, tmp_path):
        case = _proven_case()
        corpus_file, manifest_file = _seal(tmp_path, [case])
        bundle = fam.load_bundle(corpus_file, manifest_file)
        rebuilt = fam.build_manifest_document(bundle.document)
        assert json.loads(manifest_file.read_text(encoding="utf-8")) == rebuilt

    def test_manifest_refuses_a_different_corpus(self, tmp_path):
        case_a = _proven_case()
        case_b = _count_only_case()
        corpus_a, manifest_a = _seal(tmp_path / "a", [case_a])
        _seal(tmp_path / "b", [case_b])
        # self-consistent control:
        fam.load_bundle(corpus_a, manifest_a)
        # now present manifest A over corpus B (the cross-corpus refusal)
        corpus_b = (
            tmp_path
            / "b"
            / "evaluation"
            / "fu4_bundle_authority_qualification"
            / "corpus_v1.json"
        )
        with pytest.raises(fam.BundleAuthorityManifestError) as exc:
            fam.load_bundle(corpus_b, manifest_a)
        assert "does not match" in exc.value.reason

    def test_missing_manifest_file_refused(self, tmp_path):
        case = _proven_case()
        corpus_file, _ = _seal(tmp_path, [case])
        with pytest.raises(fam.BundleAuthorityManifestError):
            fam.load_bundle(corpus_file, tmp_path / "nope" / "manifest.json")


class TestSourceArchiveDigestConsistency:
    def _recorded_fixture_case(self, tmp_path, archive_bytes):
        archive_rel = "tests/fixtures/pages/c1-fixture-page.html"
        # the cited archive is repo-relative; stage it under the temp root
        cited_file = tmp_path / archive_rel
        cited_file.parent.mkdir(parents=True, exist_ok=True)
        cited_file.write_bytes(archive_bytes)
        digest = _sha256_bytes(archive_bytes)
        parts = _proven_parts()
        case = _proven_case(case_id="FA4-PROV-001")
        for side in ("candidate", "target"):
            block = case["source"][side]
            # The candidate side cites the recorded page of the
            # RECORDED listing itself (the mandatory provenance
            # binding: the candidate block's source_url is the
            # name-authoritative counterpart of the recorded case's
            # candidate URL). The target side cites the recorded
            # target document (no case-field counterpart - documented
            # limitation).
            block["source_url"] = (
                SOURCE_URL if side == "candidate" else "https://example.com/recorded-page"
            )
            block["retrieved_utc"] = "2026-01-01T12:00:00Z"
            block["raw_reference"] = "recorded-page-0001"
            block["archive"] = archive_rel
            block["archive_digest"] = digest
            block["recording_attestation"] = (
                "recorded from the cited source at the recorded instant "
                "(c1 fixture attestation)"
            )
        case["evidence_kind"] = "RECORDED_FIXTURE"
        return case

    def test_declared_archive_digest_verifies(self, tmp_path):
        page = b"<html><body>recorded page</body></html>"
        case = self._recorded_fixture_case(tmp_path, page)
        bundle, _ = _decode_ok([case], tmp_path)
        assert bundle.cases[0].evidence_kind == "RECORDED_FIXTURE"

    def test_substituted_archive_file_fails(self, tmp_path):
        case = self._recorded_fixture_case(tmp_path, b"original page")
        corpus_file, manifest_file = _seal(tmp_path, [case])
        # substitute the cited file AFTER sealing (the declared digest
        # no longer verifies - the source file moved or was substituted)
        cited = tmp_path / "tests/fixtures/pages/c1-fixture-page.html"
        cited.write_bytes(b"substituted page")
        with pytest.raises(fam.BundleAuthorityDigestError) as exc:
            fam.load_bundle(corpus_file, manifest_file)
        assert "archive_digest" in exc.value.reason

    def test_missing_archive_file_fails(self, tmp_path):
        case = self._recorded_fixture_case(tmp_path, b"original page")
        corpus_file, manifest_file = _seal(tmp_path, [case])
        (tmp_path / "tests/fixtures/pages/c1-fixture-page.html").unlink()
        with pytest.raises(fam.BundleAuthorityDigestError) as exc:
            fam.load_bundle(corpus_file, manifest_file)
        assert "missing" in exc.value.reason

    def test_synthetic_case_carrying_retrieval_metadata_rejected(self, tmp_path):
        case = _proven_case(case_id="FA4-PROV-002")
        case["source"]["candidate"]["source_url"] = "https://example.com/x"
        with pytest.raises(fam.BundleAuthoritySchemaError) as exc:
            _decode_ok([case], tmp_path)
        assert "by-construction" in exc.value.reason

    def test_recorded_fixture_case_missing_retrieval_metadata_rejected(
        self, tmp_path
    ):
        case = _proven_case(case_id="FA4-PROV-003")
        case["evidence_kind"] = "RECORDED_FIXTURE"
        with pytest.raises(fam.BundleAuthoritySchemaError) as exc:
            _decode_ok([case], tmp_path)
        assert "retrieval metadata" in exc.value.reason

    def test_real_market_archive_layout_enforced(self, tmp_path):
        page = b"<html><body>real market page</body></html>"
        case = self._recorded_fixture_case(tmp_path, page)
        case["evidence_kind"] = "REAL_MARKET"
        case["source"]["candidate"]["archive"] = "tests/fixtures/pages/x.html"
        with pytest.raises(fam.BundleAuthoritySchemaError) as exc:
            _decode_ok([case], tmp_path)
        assert "sources/ layout" in exc.value.reason


class TestHistoricalPreservation:
    """The family must leave the semantic family's committed artifacts
    byte-identical (defense in depth over the A1 / R2 pin tables). The
    1.0.0 / 1.1.0 artifacts + the DRAFT policy are file-digest pinned
    (the A1 CORPUS_ARTIFACT_PINS literals, working-tree bytes); the
    1.2.0 seal is pinned by its inner document digests (the R2 suite's
    CORPUS_1_2_0_DIGEST / MANIFEST_1_2_0_DIGEST literals)."""

    SEMANTIC_ARTIFACT_FILE_PINS = {
        "evaluation/semantic_v2_qualification/corpus_v1.json": (
            "ffb407b3e440f08ae5e92f8fe4444d23d46744753dee8088fc8e6fea79a8430b"
        ),
        "evaluation/semantic_v2_qualification/manifest_v1.json": (
            "caa5d76ffdce92a4de1b7f9e04dfef640518b3d0ec1580ec916cedf27f607c44"
        ),
        "evaluation/semantic_v2_qualification/corpus_2_1.json": (
            "6f5254c8772ea34547ef8a8315ce4f2352df48d8c2121ed431248d047777bff9"
        ),
        "evaluation/semantic_v2_qualification/manifest_2_1.json": (
            "f37956e45b3d873e583d6f2f42ac7e6f5393110b8ea64e95a9a98e1c02d36ac7"
        ),
        "evaluation/semantic_v2_qualification/policy/"
        "qualification_policy_draft_1.json": (
            "6bc30d3781b7cac27e8dd767849ca53e6d4141095ca972d528ffbee2e4cdc111"
        ),
    }
    SEMANTIC_1_2_0_INNER_DIGESTS = {
        "evaluation/semantic_v2_qualification/corpus_2_1_fu4.json": (
            ("corpus_digest", "582b35bbee93959eaa5a598fa579cd99229e550e37f3c6cd970f7774ed9d1b91")
        ),
        "evaluation/semantic_v2_qualification/manifest_2_1_fu4.json": (
            ("manifest_digest", "972ba35428d1dfc0a4b07d2027d9186577cf398a3ba4dc96dc61865b9843d8d7")
        ),
    }

    @pytest.mark.parametrize(
        "rel", sorted(SEMANTIC_ARTIFACT_FILE_PINS), ids=lambda r: r.rsplit("/", 1)[-1]
    )
    def test_semantic_family_artifact_is_byte_identical(self, rel):
        file = REPO_ROOT / rel
        assert file.is_file(), f"the committed artifact {rel} is missing"
        actual = _sha256_bytes(file.read_bytes())
        assert actual == self.SEMANTIC_ARTIFACT_FILE_PINS[rel], (
            f"{rel} moved (working-tree digest {actual}); the family "
            "leaves every historical corpus / manifest / policy byte-identical"
        )

    @pytest.mark.parametrize(
        "rel", sorted(SEMANTIC_1_2_0_INNER_DIGESTS), ids=lambda r: r.rsplit("/", 1)[-1]
    )
    def test_semantic_1_2_0_seal_digests_stand(self, rel):
        file = REPO_ROOT / rel
        assert file.is_file(), f"the committed artifact {rel} is missing"
        document = json.loads(file.read_text(encoding="utf-8"))
        field, expected = self.SEMANTIC_1_2_0_INNER_DIGESTS[rel]
        assert document[field] == expected, (
            f"{rel} inner {field} moved; the 1.2.0 seal is byte-frozen "
            "by its document digest"
        )

    def test_family_package_is_research_importer_only_for_corpus_module(self):
        # Least privilege: at C1 ONLY the loader module requires the
        # frozen research surface (the guard allowlist is exactly that
        # one file - the fixtures / cli / __init__ stay independent).
        for name in ("__init__.py", "fixtures.py", "cli.py"):
            path = FAMILY_PACKAGE_ROOT / name
            modules = _imported_modules(path)
            research_modules = {
                m for m in modules if m.startswith("product_intelligence.research")
            }
            assert not research_modules, (
                f"{name} imports the research surface at C1 (least "
                f"privilege: {sorted(research_modules)})"
            )

    def test_no_corpus_artifact_is_committed_at_c1(self):
        # Recorded C2 correction (in place, intent preserved +
        # tightened): the C1 state pin ("the family artifact directory
        # does not exist") is stale at the C2 endpoint - C2 creates the
        # family directory with the DRAFT governance artifacts (the
        # DRAFT policy, the family README, the challenge log, the
        # reviewer handoff). The preserved contract, tightened for the
        # C2 draft endpoint: NO SEALED corpus artifact is committed
        # before the independent review completes - corpus_v1.json and
        # manifest_v1.json must be ABSENT (a seal over the unreviewed
        # DRAFT population would be a false seal; the family loader
        # refuses DRAFT labels by design, so no loadable draft corpus
        # can be committed).
        family_dir = (
            REPO_ROOT / "evaluation" / "fu4_bundle_authority_qualification"
        )
        if family_dir.exists():
            # The C2 draft endpoint: governance artifacts present, the
            # seal absent.
            assert not (family_dir / "corpus_v1.json").exists(), (
                "a sealed corpus_v1.json is committed before the "
                "independent review completes (a false seal)"
            )
            assert not (family_dir / "manifest_v1.json").exists(), (
                "a sealed manifest_v1.json is committed before the "
                "independent review completes (a false seal)"
            )
        # The C1 endpoint state (directory absent) is still the valid
        # alternative - either state satisfies "no false seal".



# ---------------------------------------------------------------------------
# The empty-seal demonstration (design section 9.3 deliverable: a 0-case
# corpus builds, seals, loads, and regenerates byte-for-byte)
# ---------------------------------------------------------------------------


class TestEmptySealDemonstration:
    def test_zero_case_corpus_builds_seals_loads_and_regenerates(self, tmp_path):
        # Recorded C2 correction (in place, intent preserved): at the
        # C2 endpoint the declared fixtures case set is the DRAFT
        # population (the corrected 94-case population of record at the
        # C1-FU3 endpoint, review pending), so the 0-case builder
        # property is demonstrated over the EXPLICIT empty case set
        # (the builder's own integrity property, unchanged).
        document = fam_fixtures.build_corpus_document(CREATED_UTC, cases=())
        assert document["cases"] == []
        bytes_ = fam_fixtures.corpus_bytes(document)
        base = tmp_path / "evaluation" / "fu4_bundle_authority_qualification"
        base.mkdir(parents=True)
        corpus_file = base / "corpus_v1.json"
        corpus_file.write_bytes(bytes_)
        manifest = fam.build_manifest_document(document)
        manifest_file = base / "manifest_v1.json"
        manifest_file.write_bytes(fam.canonically_serialize(manifest))
        bundle = fam.load_bundle(corpus_file, manifest_file)
        assert bundle.corpus_id == fam.CORPUS_ID
        assert bundle.corpus_version == fam.FIRST_CORPUS_VERSION
        assert bundle.cases == ()
        # byte-for-byte regeneration (the P1 property, family version)
        assert fam.canonically_serialize(bundle.document) == bytes_
        assert fam.canonically_serialize(
            fam.build_manifest_document(bundle.document)
        ) == fam.canonically_serialize(manifest)

    def test_cli_corpus_build_writes_the_seal(self, tmp_path, capsys):
        # Recorded C2 correction (in place, intent preserved +
        # strengthened): at the C2 endpoint the declared case set is
        # the DRAFT population (independent review pending), so the
        # CLI corpus-build MUST REFUSE to seal it (fail closed - the
        # seal gate is closed until the two-identity review of design
        # section 8.2 completes). A seal command that wrote artifacts
        # over the unreviewed population would be a false seal.
        out_dir = tmp_path / "out"
        exit_code = fam_cli.main(
            ["corpus-build", "--out-dir", str(out_dir), "--created-utc", CREATED_UTC]
        )
        assert exit_code == 1, (
            "corpus-build over the DRAFT population must fail closed "
            "(the seal gate is closed until independent review)"
        )
        err = capsys.readouterr().err
        assert "DRAFT" in err or "review" in err.lower(), (
            f"the bounded refusal must name the unreviewed label "
            f"state, got: {err!r}"
        )
        assert not (out_dir / "corpus_v1.json").exists(), (
            "no corpus artifact may be written over an unreviewed "
            "population (no false seal)"
        )
        assert not (out_dir / "manifest_v1.json").exists()

    def _zero_case_seal(self, out_dir: Path) -> Path:
        # The 0-case seal written directly (the CLI corpus-build path
        # over the DRAFT population is fail-closed at the C2 endpoint -
        # see test_cli_corpus_build_writes_the_seal). Recorded C2
        # correction: the digest / manifest round-trip property is
        # demonstrated over the explicit 0-case seal (intent
        # preserved).
        document = fam_fixtures.build_corpus_document(CREATED_UTC, cases=())
        base = out_dir
        base.mkdir(parents=True, exist_ok=True)
        corpus_file = base / "corpus_v1.json"
        corpus_file.write_bytes(fam_fixtures.corpus_bytes(document))
        manifest = fam.build_manifest_document(document)
        (base / "manifest_v1.json").write_bytes(
            fam.canonically_serialize(manifest)
        )
        return corpus_file

    def test_cli_corpus_digest_and_manifest_verify(self, tmp_path, capsys):
        out_dir = tmp_path / "out"
        self._zero_case_seal(out_dir)
        capsys.readouterr()
        exit_code = fam_cli.main(
            ["corpus-digest", "--corpus", str(out_dir / "corpus_v1.json")]
        )
        assert exit_code == 0
        bundle = fam.load_bundle(
            out_dir / "corpus_v1.json", out_dir / "manifest_v1.json"
        )
        assert bundle.corpus_digest in capsys.readouterr().out
        exit_code = fam_cli.main(
            [
                "corpus-manifest",
                "--corpus",
                str(out_dir / "corpus_v1.json"),
                "--verify",
                str(out_dir / "manifest_v1.json"),
            ]
        )
        assert exit_code == 0

    def test_cli_corpus_digest_refuses_tampered_seal(self, tmp_path, capsys):
        out_dir = tmp_path / "out"
        self._zero_case_seal(out_dir)
        capsys.readouterr()
        corpus_file = out_dir / "corpus_v1.json"
        document = json.loads(corpus_file.read_text(encoding="utf-8"))
        document["corpus_label"] = "tampered"
        document["corpus_digest"] = fam.corpus_state_digest(document)
        corpus_file.write_bytes(fam.canonically_serialize(document))
        exit_code = fam_cli.main(["corpus-digest", "--corpus", str(corpus_file)])
        assert exit_code == 1
        assert "corpus_label" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# Q3-C-C1-FU2 (finding F-1): the mandatory provenance binding — the
# recorded V2 case document is bound field-by-field to the sealed source
# blocks. EVERY tamper below re-seals the corpus: all per-case / corpus /
# manifest digests are recomputed over the mutated bytes, so the digests
# CANNOT catch the substitution — only the field binding can. That is the
# adversarial property under test.
# ---------------------------------------------------------------------------

FU2_URL_B = "https://example.com/other-listing"
FU2_OFFER_B = "https://example.com/other-offer"
FU2_TITLE_B = "ABC-123 2TB NVMe Drive"
FU2_TITLE_CODEPOINT = "ABC-123 1TB NVMe Driv\u0435"  # Cyrillic U+0435, visually identical


def _recorded_fixture_case_doc(tmp_path, *, observation=None, case_id="FA4-PROV-001"):
    """A sound RECORDED_FIXTURE family case document: the candidate
    block cites the recorded listing page with the name-authoritative
    counterpart URL (source_url == the recorded case's candidate URL),
    both sides cite the staged archive file by path + declared digest."""
    if observation is None:
        observation = _observation()
    parts = _frozen_case_parts(observation=observation)
    channel = parts["case"].candidate_commercial.sales_unit
    archive_rel = "tests/fixtures/pages/fu2-recorded-page.html"
    page = b"<html><body>recorded page</body></html>"
    cited = tmp_path / archive_rel
    cited.parent.mkdir(parents=True, exist_ok=True)
    cited.write_bytes(page)
    digest = _sha256_bytes(page)
    attestation = (
        "recorded from the cited source at the recorded instant "
        "(c1-fu2 fixture attestation)"
    )
    target = _make_target_fu4(
        CLAUSE, fu4.BundleCompositionStateV2FU4.ESTABLISHED, None,
        _make_target_attestation(CLAUSE),
    )
    candidate = fu4.candidate_composition_from_channel(channel)
    decision = fu4.derive_authority_tier_fu4(
        parts["context"],
        channel,
        parts["evaluation"],
        parts["case"].context_provenances,
        parts["case"].product_evidence,
        None,
        target_unit_evidence=target,
        candidate_composition=candidate,
        quantity_attestation=None,
    )
    candidate_block = {
        "title_text": parts["case"].candidate_product.raw_title_text,
        "structured_fields": {"packaging": EST_RAW_DETAIL},
        "source_url": parts["case"].candidate_source_url,
        "retrieved_utc": "2026-01-01T12:00:00Z",
        "raw_reference": "recorded-page-0002",
        "archive": archive_rel,
        "archive_digest": digest,
        "recording_attestation": attestation,
    }
    target_block = {
        "title_text": "Requested bundle review record (by-construction)",
        "structured_fields": {"specification": f"Bundle contents: {CLAUSE}"},
        "source_url": "https://example.com/recorded-page",
        "retrieved_utc": "2026-01-01T12:00:00Z",
        "raw_reference": "recorded-page-0003",
        "archive": archive_rel,
        "archive_digest": digest,
        "recording_attestation": attestation,
    }
    return _synthesize_case(
        case_id=case_id,
        matrix_row="A1",
        channel=channel,
        candidate_composition=candidate,
        candidate_basis="RECORDED_CHANNEL",
        extraction_evidence=None,
        target_evidence_schema="fu4_v3",
        target_evidence_document=_target_sealed_doc(target),
        quantity_attestation_document=None,
        case=parts["case"],
        assessment=parts["context"],
        evaluation=parts["evaluation"],
        decision=decision,
        surface="DERIVATION",
        evidence_kind="RECORDED_FIXTURE",
        candidate_source_block=candidate_block,
        target_source_block=target_block,
    )


def _real_market_case_doc(
    tmp_path,
    *,
    case_id="FA4-PROV-001",
    rel_dir=None,
    stage_bytes=b"<html><body>real market page</body></html>",
):
    """A REAL_MARKET family case document citing the approved per-case
    layout ``sources/<case_id>/...`` (the files are staged under the
    given root unless ``stage_bytes`` is None - the decode-level layout
    rows need no files)."""
    parts = _frozen_case_parts()
    channel = parts["case"].candidate_commercial.sales_unit
    sources_prefix = "evaluation/fu4_bundle_authority_qualification/sources"
    if rel_dir is None:
        rel_dir = f"{sources_prefix}/{case_id}"
    cand_rel = f"{rel_dir}/candidate_raw_content.html"
    tgt_rel = f"{rel_dir}/target_raw_content.html"
    if stage_bytes is not None:
        for rel in (cand_rel, tgt_rel):
            file = tmp_path / rel
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(stage_bytes)
    digest = _sha256_bytes(stage_bytes) if stage_bytes is not None else "0" * 64
    attestation = (
        "recorded from the cited source at the recorded instant "
        "(c1-fu2 attestation)"
    )
    target = _make_target_fu4(
        CLAUSE, fu4.BundleCompositionStateV2FU4.ESTABLISHED, None,
        _make_target_attestation(CLAUSE),
    )
    candidate = fu4.candidate_composition_from_channel(channel)
    decision = fu4.derive_authority_tier_fu4(
        parts["context"],
        channel,
        parts["evaluation"],
        parts["case"].context_provenances,
        parts["case"].product_evidence,
        None,
        target_unit_evidence=target,
        candidate_composition=candidate,
        quantity_attestation=None,
    )
    candidate_block = {
        "title_text": parts["case"].candidate_product.raw_title_text,
        "structured_fields": {"packaging": EST_RAW_DETAIL},
        "source_url": parts["case"].candidate_source_url,
        "retrieved_utc": "2026-01-01T12:00:00Z",
        "raw_reference": "real-market-0001",
        "archive": cand_rel,
        "archive_digest": digest,
        "recording_attestation": attestation,
    }
    target_block = {
        "title_text": "Requested bundle review record (by-construction)",
        "structured_fields": {"specification": f"Bundle contents: {CLAUSE}"},
        "source_url": "https://example.com/recorded-page",
        "retrieved_utc": "2026-01-01T12:00:00Z",
        "raw_reference": "real-market-0002",
        "archive": tgt_rel,
        "archive_digest": digest,
        "recording_attestation": attestation,
    }
    return _synthesize_case(
        case_id=case_id,
        matrix_row="A1",
        channel=channel,
        candidate_composition=candidate,
        candidate_basis="RECORDED_CHANNEL",
        extraction_evidence=None,
        target_evidence_schema="fu4_v3",
        target_evidence_document=_target_sealed_doc(target),
        quantity_attestation_document=None,
        case=parts["case"],
        assessment=parts["context"],
        evaluation=parts["evaluation"],
        decision=decision,
        surface="DERIVATION",
        evidence_kind="REAL_MARKET",
        candidate_source_block=candidate_block,
        target_source_block=target_block,
    )


def _seal_document(tmp_path, document):
    """Seal one corpus document + its manifest under the family layout
    (all digests recomputed over the exact document bytes)."""
    base = tmp_path / "evaluation" / "fu4_bundle_authority_qualification"
    base.mkdir(parents=True, exist_ok=True)
    corpus_file = base / "corpus_v1.json"
    manifest_file = base / "manifest_v1.json"
    corpus_file.write_bytes(fam.canonically_serialize(document))
    manifest_file.write_bytes(
        fam.canonically_serialize(fam.build_manifest_document(document))
    )
    return corpus_file, manifest_file


def _splice_recorded_case(case_doc, new_case, *, new_context=None):
    """Splice a foreign recorded V2 case document into the family case
    (the substitution shape) + keep the scripted context coherent with
    the recorded case when the context changed."""
    _set_path(case_doc, "recorded_case.v2_case_document", new_case.canonical())
    if new_context is not None:
        _set_path(
            case_doc,
            "scripted_context.identity_assessment",
            _identity_assessment_document(new_context),
        )
        _set_path(
            case_doc,
            "scripted_context.product_evidence",
            _profile_document(new_case.product_evidence),
        )
    return case_doc


class TestProvenanceBinding:
    """F-1: the recorded V2 case document <-> the sealed source blocks.
    Every row re-seals (digests recomputed) before loading: a mismatch
    is a case-document-integrity failure (L_CASE_DOCUMENT), rejected for
    a sound DERIVED case; the sealed-raw stage-coherence rows below
    preserve the REFUSED contract."""

    def test_candidate_title_substitution_detected_after_full_reseal(self, tmp_path):
        case = _proven_case(case_id="FA4-PROV-001", surface="DERIVATION")
        parts_b = _frozen_case_parts(observation=_observation(FU2_TITLE_B))
        _splice_recorded_case(case, parts_b["case"])
        corpus_file, manifest_file = _seal(tmp_path, [case])
        with pytest.raises(fam.BundleAuthorityEvidenceError) as exc:
            fam.load_bundle(corpus_file, manifest_file)
        assert "CASEDOC_CANDIDATE_TITLE" in exc.value.reason

    def test_candidate_title_codepoint_substitution_detected(self, tmp_path):
        # Unicode codepoint distinction (F-7): a visually identical
        # Cyrillic codepoint in the recorded title is NOT the sealed
        # title - exact codepoint equality, never normalization.
        case = _proven_case(case_id="FA4-PROV-001", surface="DERIVATION")
        parts_b = _frozen_case_parts(
            observation=_observation(FU2_TITLE_CODEPOINT)
        )
        _splice_recorded_case(case, parts_b["case"])
        corpus_file, manifest_file = _seal(tmp_path, [case])
        with pytest.raises(fam.BundleAuthorityEvidenceError) as exc:
            fam.load_bundle(corpus_file, manifest_file)
        assert "CASEDOC_CANDIDATE_TITLE" in exc.value.reason

    def test_candidate_source_url_substitution_detected_after_full_reseal(self, tmp_path):
        case = _recorded_fixture_case_doc(tmp_path)  # bound to the recorded URL
        parts_b = _frozen_case_parts(
            observation=dataclasses.replace(_observation(), source_url=FU2_URL_B)
        )
        _splice_recorded_case(case, parts_b["case"])
        corpus_file, manifest_file = _seal(tmp_path, [case])
        with pytest.raises(fam.BundleAuthorityEvidenceError) as exc:
            fam.load_bundle(corpus_file, manifest_file)
        assert "CASEDOC_CANDIDATE_SOURCE_URL" in exc.value.reason

    def test_candidate_mpn_field_substitution_detected(self, tmp_path):
        # The recorded case carries an MPN field the sealed candidate
        # source never published (the structured_fields key is absent).
        case = _proven_case(case_id="FA4-PROV-001", surface="DERIVATION")
        parts_b = _frozen_case_parts(
            observation=dataclasses.replace(
                _observation(), manufacturer_part_number_text="ABC-12"
            )
        )
        _splice_recorded_case(case, parts_b["case"], new_context=parts_b["context"])
        corpus_file, manifest_file = _seal(tmp_path, [case])
        with pytest.raises(fam.BundleAuthorityEvidenceError) as exc:
            fam.load_bundle(corpus_file, manifest_file)
        assert "CASEDOC_CANDIDATE_MPN_FIELD" in exc.value.reason

    def test_candidate_sku_substitution_detected(self, tmp_path):
        case = _proven_case(case_id="FA4-PROV-001", surface="DERIVATION")
        parts_b = _frozen_case_parts(
            observation=dataclasses.replace(_observation(), sku_text="SKU-OTHER")
        )
        _splice_recorded_case(case, parts_b["case"], new_context=parts_b["context"])
        corpus_file, manifest_file = _seal(tmp_path, [case])
        with pytest.raises(fam.BundleAuthorityEvidenceError) as exc:
            fam.load_bundle(corpus_file, manifest_file)
        assert "CASEDOC_CANDIDATE_SKU" in exc.value.reason

    def test_candidate_offer_url_substitution_detected(self, tmp_path):
        case = _proven_case(case_id="FA4-PROV-001", surface="DERIVATION")
        parts_b = _frozen_case_parts(
            observation=dataclasses.replace(_observation(), offer_url_text=FU2_OFFER_B)
        )
        _splice_recorded_case(case, parts_b["case"])
        corpus_file, manifest_file = _seal(tmp_path, [case])
        with pytest.raises(fam.BundleAuthorityEvidenceError) as exc:
            fam.load_bundle(corpus_file, manifest_file)
        assert "CASEDOC_CANDIDATE_OFFER_URL" in exc.value.reason

    def test_candidate_whole_listing_substitution_detected(self, tmp_path):
        # The composite candidate substitution: the recorded case is
        # rebuilt from a wholly different listing (URL + title + SKU +
        # offer). The first binding check (the raw title) reports it.
        case = _proven_case(case_id="FA4-PROV-001", surface="DERIVATION")
        parts_b = _frozen_case_parts(
            observation=dataclasses.replace(
                _observation(),
                source_url=FU2_URL_B,
                product_title=FU2_TITLE_B,
                sku_text="SKU-OTHER",
                offer_url_text=FU2_OFFER_B,
            )
        )
        _splice_recorded_case(case, parts_b["case"], new_context=parts_b["context"])
        corpus_file, manifest_file = _seal(tmp_path, [case])
        with pytest.raises(fam.BundleAuthorityEvidenceError) as exc:
            fam.load_bundle(corpus_file, manifest_file)
        assert "provenance binding" in exc.value.reason

    def test_candidate_spec_text_unpublished_rejected(self, tmp_path):
        # The recorded case carries raw specification text the sealed
        # candidate source never published (the name-exact key absent).
        case = _proven_case(case_id="FA4-PROV-001", surface="DERIVATION")
        base = _frozen_case_parts()["case"]
        case_b = dataclasses.replace(
            base,
            candidate_product=dataclasses.replace(
                base.candidate_product,
                raw_specification_text="2x RAM + 1x CPU (sealed spec)",
            ),
        )
        _splice_recorded_case(case, case_b)
        corpus_file, manifest_file = _seal(tmp_path, [case])
        with pytest.raises(fam.BundleAuthorityEvidenceError) as exc:
            fam.load_bundle(corpus_file, manifest_file)
        assert "CASEDOC_CANDIDATE_SPEC_TEXT" in exc.value.reason

    def test_candidate_spec_text_structured_field_mapping_sounds(self, tmp_path):
        # The structured-field mapping positive arm: the sealed candidate
        # source records the name-exact key + the recorded case carries
        # the same text -> the binding holds and the corpus loads.
        case = _proven_case(case_id="FA4-PROV-001", surface="DERIVATION")
        spec = "2x RAM + 1x CPU (sealed spec)"
        base = _frozen_case_parts()["case"]
        case_b = dataclasses.replace(
            base,
            candidate_product=dataclasses.replace(
                base.candidate_product, raw_specification_text=spec
            ),
        )
        _splice_recorded_case(case, case_b)
        _set_path(
            case,
            "source.candidate.structured_fields",
            {"packaging": EST_RAW_DETAIL, "raw_specification_text": spec},
        )
        bundle, _ = _decode_ok([case], tmp_path)
        assert (
            bundle.cases[0].evidence.v2_case.candidate_product.raw_specification_text
            == spec
        )

    def test_target_mpn_binding_when_recorded_sounds(self, tmp_path):
        # The target block name-exactly records the request anchor: the
        # recorded target MPN agrees -> the binding holds.
        case = _proven_case(case_id="FA4-PROV-001", surface="DERIVATION")
        _set_path(
            case,
            "source.target.structured_fields",
            {
                "specification": f"Bundle contents: {CLAUSE}",
                "mpn": case["recorded_case"]["v2_case_document"]["target"]["mpn"],
            },
        )
        bundle, _ = _decode_ok([case], tmp_path)
        assert (
            bundle.cases[0].evidence.v2_case.target.mpn
            == case["recorded_case"]["v2_case_document"]["target"]["mpn"]
        )

    def test_target_mpn_contradiction_rejected(self, tmp_path):
        case = _proven_case(case_id="FA4-PROV-001", surface="DERIVATION")
        _set_path(
            case,
            "source.target.structured_fields",
            {
                "specification": f"Bundle contents: {CLAUSE}",
                "mpn": "ABC-999",
            },
        )
        corpus_file, manifest_file = _seal(tmp_path, [case])
        with pytest.raises(fam.BundleAuthorityEvidenceError) as exc:
            fam.load_bundle(corpus_file, manifest_file)
        assert "CASEDOC_TARGET_MPN" in exc.value.reason

    def test_target_description_contradiction_rejected(self, tmp_path):
        case = _proven_case(case_id="FA4-PROV-001", surface="DERIVATION")
        _set_path(
            case,
            "source.target.structured_fields",
            {
                "specification": f"Bundle contents: {CLAUSE}",
                "description_raw_text": "A different product",
            },
        )
        corpus_file, manifest_file = _seal(tmp_path, [case])
        with pytest.raises(fam.BundleAuthorityEvidenceError) as exc:
            fam.load_bundle(corpus_file, manifest_file)
        assert "CASEDOC_TARGET_DESCRIPTION" in exc.value.reason

    def test_unrecorded_target_description_is_not_compared(self, tmp_path):
        # Documented limitation: the caller-published request anchor has
        # NO authoritative counterpart unless the target block records
        # the name-exact key. A different recorded description over a
        # block that records no such key is not a contradiction (the
        # recorded deterministic context is unchanged - same request MPN).
        case = _proven_case(case_id="FA4-PROV-001", surface="DERIVATION")
        parts_b = _frozen_case_parts(
            request=ResearchRequest("ABC-123", "A different product")
        )
        _splice_recorded_case(case, parts_b["case"])
        bundle, _ = _decode_ok([case], tmp_path)
        assert (
            bundle.cases[0].evidence.v2_case.target.description_raw_text
            == "A different product"
        )

    def test_null_recorded_title_with_sealed_title_rejected(self, tmp_path):
        # Nullable-field case: the sealed source published a title, the
        # recorded case omits it (never silently reconciled).
        case = _proven_case(case_id="FA4-PROV-001", surface="DERIVATION")
        base = _frozen_case_parts()["case"]
        case_b = dataclasses.replace(
            base,
            candidate_product=dataclasses.replace(
                base.candidate_product, raw_title_text=None
            ),
        )
        _splice_recorded_case(case, case_b)
        corpus_file, manifest_file = _seal(tmp_path, [case])
        with pytest.raises(fam.BundleAuthorityEvidenceError) as exc:
            fam.load_bundle(corpus_file, manifest_file)
        assert "CASEDOC_CANDIDATE_TITLE" in exc.value.reason

    def test_null_sealed_title_with_recorded_title_rejected(self, tmp_path):
        # Nullable-field case: the recorded case carries a title the
        # sealed source never published.
        case = _proven_case(case_id="FA4-PROV-001", surface="DERIVATION")
        _set_path(case, "source.candidate.title_text", None)
        corpus_file, manifest_file = _seal(tmp_path, [case])
        with pytest.raises(fam.BundleAuthorityEvidenceError) as exc:
            fam.load_bundle(corpus_file, manifest_file)
        assert "CASEDOC_CANDIDATE_TITLE" in exc.value.reason

    def test_joint_absence_title_loads(self, tmp_path):
        # Nullable-field case: explicit JOINT absence is the documented
        # sound shape (neither side carries a title).
        case = _proven_case(case_id="FA4-PROV-001", surface="DERIVATION")
        base = _frozen_case_parts()["case"]
        case_b = dataclasses.replace(
            base,
            candidate_product=dataclasses.replace(
                base.candidate_product, raw_title_text=None
            ),
        )
        _splice_recorded_case(case, case_b)
        _set_path(case, "source.candidate.title_text", None)
        bundle, _ = _decode_ok([case], tmp_path)
        assert bundle.cases[0].evidence.v2_case.candidate_product.raw_title_text is None

    def test_sealed_sku_key_with_null_recorded_sku_rejected(self, tmp_path):
        # Nullable-field case: the sealed source records the name-exact
        # sku key, the recorded case omits the SKU (a silent omission is
        # a contradiction - never filled in).
        case = _proven_case(case_id="FA4-PROV-001", surface="DERIVATION")
        _set_path(
            case,
            "source.candidate.structured_fields",
            {"packaging": EST_RAW_DETAIL, "sku": "SKU-1"},
        )
        corpus_file, manifest_file = _seal(tmp_path, [case])
        with pytest.raises(fam.BundleAuthorityEvidenceError) as exc:
            fam.load_bundle(corpus_file, manifest_file)
        assert "CASEDOC_CANDIDATE_SKU" in exc.value.reason

    def test_structured_field_mapping_with_changed_context_sounds(self, tmp_path):
        # The structured-field mapping positive arm over a CHANGED
        # deterministic context (the recorded MPN near-miss + SKU are
        # name-exactly recorded by the sealed source).
        observation = dataclasses.replace(
            _observation(),
            manufacturer_part_number_text="ABC-12",
            sku_text="SKU-OTHER",
        )
        parts_b = _frozen_case_parts(observation=observation)
        case = _proven_case(case_id="FA4-PROV-001", surface="DERIVATION")
        _splice_recorded_case(case, parts_b["case"], new_context=parts_b["context"])
        _set_path(
            case,
            "source.candidate.structured_fields",
            {
                "packaging": EST_RAW_DETAIL,
                "mpn_field": "ABC-12",
                "sku": "SKU-OTHER",
            },
        )
        bundle, _ = _decode_ok([case], tmp_path)
        assert bundle.cases[0].evidence.v2_case.candidate_mpn_field == "ABC-12"
        assert bundle.cases[0].evidence.v2_case.candidate_sku == "SKU-OTHER"

    # -- sealed-raw stage coherence over a provenance mismatch --------

    def test_provenance_mismatch_loads_as_corpus_integrity_sealed_raw(self, tmp_path):
        # The REFUSED / NON_CONSTRUCTIBLE contract is preserved: the
        # same substitution is sealable under the CORPUS_INTEGRITY label
        # (the defect IS a case-document-integrity observation).
        parts = _proven_parts()
        case = _sealed_case(
            base=parts,
            case_id="FA4-ADV-101",
            stage="CORPUS_INTEGRITY",
            matrix_row="D2",
        )
        parts_b = _frozen_case_parts(observation=_observation(FU2_TITLE_B))
        _splice_recorded_case(case, parts_b["case"])
        bundle, _ = _decode_ok([case], tmp_path)
        assert bundle.cases[0].expected["outcome"] == "REFUSED"
        assert bundle.cases[0].expected["refusal"]["stage"] == "CORPUS_INTEGRITY"

    def test_provenance_mismatch_rejected_under_presentation_gate_label(self, tmp_path):
        # The distinction between CASE_DOCUMENT integrity and
        # presentation-gate failures: a provenance mismatch under a
        # PRESENTATION_GATE label is incoherent (the mismatch is
        # observed at the loader, earlier than the gate).
        parts = _proven_parts()
        case = _sealed_case(
            base=parts,
            case_id="FA4-ADV-102",
            stage="PRESENTATION_GATE",
            error_type="PRESENTATION",
            matrix_row="D3",
        )
        parts_b = _frozen_case_parts(observation=_observation(FU2_TITLE_B))
        _splice_recorded_case(case, parts_b["case"])
        with pytest.raises(fam.BundleAuthorityLabelError) as exc:
            _decode_ok([case], tmp_path)
        assert "self-consistent sealed shapes" in exc.value.reason

    def test_provenance_mismatch_rejected_under_construction_label(self, tmp_path):
        # A CONSTRUCTION label requires a constructor-level observation;
        # a pure provenance mismatch (fully constructible documents) is
        # observed at no construction layer - incoherent.
        parts = _proven_parts()
        case = _sealed_case(
            base=parts,
            case_id="FA4-ADV-103",
            stage="CONSTRUCTION",
            error_type="CONSTRUCTOR",
            matrix_row="D2",
        )
        parts_b = _frozen_case_parts(observation=_observation(FU2_TITLE_B))
        _splice_recorded_case(case, parts_b["case"])
        with pytest.raises(fam.BundleAuthorityLabelError) as exc:
            _decode_ok([case], tmp_path)
        assert "not observable" in exc.value.reason


# ---------------------------------------------------------------------------
# Q3-C-C1-FU2 (findings F-2 / F-5 + the archive filesystem safety): the
# per-case REAL_MARKET archive association, resolved-path containment,
# and the bounded shallow-path / resolution handling.
# ---------------------------------------------------------------------------


class TestArchiveAssociationAndSafety:
    def test_real_market_own_case_layout_loads(self, tmp_path):
        case = _real_market_case_doc(tmp_path)
        bundle, _ = _decode_ok([case], tmp_path)
        assert bundle.cases[0].evidence_kind == "REAL_MARKET"

    def test_real_market_cross_case_reference_rejected(self, tmp_path):
        # Case A's archive reference cites case B's source directory:
        # a schema failure at decode (the recorded layout is contract
        # data - deterministic, no file access needed).
        prefix = "evaluation/fu4_bundle_authority_qualification/sources"
        case = _real_market_case_doc(
            tmp_path, rel_dir=f"{prefix}/FA4-OTHER-001", stage_bytes=None
        )
        with pytest.raises(fam.BundleAuthoritySchemaError) as exc:
            fam.decode_corpus_case_document(_raw_for_decode(case))
        assert "own case's sources/" in exc.value.reason

    @pytest.mark.parametrize(
        "archive",
        [
            "evaluation/fu4_bundle_authority_qualification/"
            "sources/FA4-PROV-001/../FA4-OTHER-001/x.html",
            "/etc/passwd",
            "C:/temp/x.html",
            "C:\\temp\\x.html",
        ],
        ids=["dotdot-traversal", "absolute", "windows-drive", "windows-backslash"],
    )
    def test_archive_path_shape_refused(self, archive):
        case = _proven_case(case_id="FA4-PROV-001", surface="DERIVATION")
        case["evidence_kind"] = "REAL_MARKET"
        for side in ("candidate", "target"):
            block = case["source"][side]
            block["source_url"] = SOURCE_URL
            block["retrieved_utc"] = "2026-01-01T12:00:00Z"
            block["raw_reference"] = "r"
            block["archive_digest"] = "0" * 64
            block["recording_attestation"] = "att"
        case["source"]["candidate"]["archive"] = archive
        case["source"]["target"]["archive"] = (
            "evaluation/fu4_bundle_authority_qualification/"
            "sources/FA4-PROV-001/target_raw_content.html"
        )
        with pytest.raises(fam.BundleAuthoritySchemaError) as exc:
            fam.decode_corpus_case_document(_raw_for_decode(case))
        assert "repo-relative POSIX path" in exc.value.reason

    @pytest.mark.parametrize(
        "raw",
        (
            ["C:/fu2_shallow_corpus.json", "C:/one/fu2_shallow_corpus.json"]
            if os.name == "nt"
            else ["/fu2_shallow_corpus.json", "/one/fu2_shallow_corpus.json"]
        ),
        ids=["depth-1", "depth-2"],
    )
    def test_shallow_corpus_path_is_a_bounded_error(self, raw):
        # F-5: the shallow path used to raise an unhandled IndexError
        # from the parents[2] repo-root derivation; it is now the
        # established bounded corpus error (the cited archives cannot
        # be located -> the declared digests cannot verify).
        with pytest.raises(fam.BundleAuthorityDigestError) as exc:
            fam._repo_root_of(Path(raw))
        assert "three path components" in exc.value.reason

    def test_symlink_escape_outside_root_rejected(self, tmp_path):
        # The containment defense: a forger who controls the archive can
        # always match its declared digest - the resolved path must stay
        # inside the authorized source root. The corpus root here is the
        # "inner" directory; the symlink target sits OUTSIDE it.
        inner = tmp_path / "inner"
        case = _real_market_case_doc(inner)
        outside_dir = tmp_path / "outside_root"
        outside_dir.mkdir(parents=True, exist_ok=True)
        outside = outside_dir / "secret.html"
        outside.write_bytes(b"outside content")
        link = inner / case["source"]["candidate"]["archive"]
        link.unlink()
        try:
            os.symlink(outside, link)
        except OSError:
            pytest.skip("symlink creation not permitted on this platform")
        case["source"]["candidate"]["archive_digest"] = _sha256_bytes(
            outside.read_bytes()
        )
        document = fam_fixtures.build_corpus_document(CREATED_UTC, (case,))
        corpus_file = (
            inner
            / "evaluation"
            / "fu4_bundle_authority_qualification"
            / "corpus_v1.json"
        )
        corpus_file.write_bytes(fam.canonically_serialize(document))
        with pytest.raises(fam.BundleAuthorityDigestError) as exc:
            fam.load_corpus(corpus_file)
        assert "resolves outside the repository root" in exc.value.reason

    def test_symlink_cross_case_association_rejected(self, tmp_path):
        # F-2 at the load level: case A's archive RESOLVES to case B's
        # source directory through a symlink (the string cites A's own
        # path + a matching digest - only the resolved containment can
        # catch it).
        case_a = _real_market_case_doc(tmp_path, case_id="FA4-PROV-001")
        case_b = _real_market_case_doc(tmp_path, case_id="FA4-UNPR-002")
        sources = "evaluation/fu4_bundle_authority_qualification/sources"
        b_file = tmp_path / f"{sources}/FA4-UNPR-002/candidate_raw_content.html"
        a_link = tmp_path / f"{sources}/FA4-PROV-001/candidate_raw_content.html"
        a_link.unlink()
        try:
            os.symlink(b_file, a_link)
        except OSError:
            pytest.skip("symlink creation not permitted on this platform")
        case_a["source"]["candidate"]["archive_digest"] = _sha256_bytes(
            b_file.read_bytes()
        )
        corpus_file, manifest_file = _seal(tmp_path, [case_a, case_b])
        with pytest.raises(fam.BundleAuthorityDigestError) as exc:
            fam.load_bundle(corpus_file, manifest_file)
        assert "resolves outside its own case's sources directory" in exc.value.reason


# ---------------------------------------------------------------------------
# Q3-C-C1-FU2 (findings F-6 / F-7): the committed regression coverage the
# C1 loader gained over - label revisions, duplicate JSON keys, NaN /
# Infinity, line-ending states, the manifest byte contract, and Unicode
# codepoint distinctions. Every row exercises the actual public
# loader / validator entry points.
# ---------------------------------------------------------------------------


def _valid_revision(case_id="FA4-PROV-001", *, revision=1, reason_class="A"):
    case_doc = _proven_case(case_id=case_id, surface="DERIVATION")
    digest = fam.case_state_digest(case_doc)
    return {
        "revision": revision,
        "case_id": case_id,
        "utc": "2026-01-04T00:00:00Z",
        "reason_class": reason_class,
        "statement": "label wording corrected under the two-identity workflow",
        "digest_before": digest,
        "digest_after": digest,
    }


class TestLabelRevisionRegression:
    @pytest.mark.parametrize("count", [1, 2], ids=["one-revision", "two-revisions"])
    def test_valid_label_revisions_load(self, tmp_path, count):
        case = _proven_case(case_id="FA4-PROV-001")
        revisions = [
            _valid_revision(reason_class="A" if i == 1 else "B", revision=i)
            for i in range(1, count + 1)
        ]
        document = fam_fixtures.build_corpus_document(
            CREATED_UTC, (case,), tuple(revisions)
        )
        corpus_file, manifest_file = _seal_document(tmp_path, document)
        bundle = fam.load_bundle(corpus_file, manifest_file)
        assert bundle.document["label_revisions"] == revisions

    def test_label_revision_unknown_case_id_rejected(self, tmp_path):
        case = _proven_case(case_id="FA4-PROV-001")
        revisions = [_valid_revision(case_id="FA4-PROV-999")]
        document = fam_fixtures.build_corpus_document(
            CREATED_UTC, (case,), tuple(revisions)
        )
        corpus_file, _ = _seal_document(tmp_path, document)
        with pytest.raises(fam.BundleAuthoritySchemaError) as exc:
            fam.load_corpus(corpus_file)
        assert "is not a corpus case" in exc.value.reason

    @pytest.mark.parametrize(
        "reason_class", ["E", None, "a"], ids=["unknown", "null", "lowercase"]
    )
    def test_label_revision_invalid_reason_class_rejected(self, tmp_path, reason_class):
        case = _proven_case(case_id="FA4-PROV-001")
        revisions = [_valid_revision(reason_class=reason_class)]
        document = fam_fixtures.build_corpus_document(
            CREATED_UTC, (case,), tuple(revisions)
        )
        corpus_file, _ = _seal_document(tmp_path, document)
        with pytest.raises(fam.BundleAuthoritySchemaError) as exc:
            fam.load_corpus(corpus_file)
        assert "reason_class" in exc.value.reason

    @pytest.mark.parametrize(
        "numbers",
        [[2], [1, 3], [1, 1]],
        ids=["gap-at-start", "gap-in-middle", "duplicate-number"],
    )
    def test_label_revision_nonsequential_numbers_rejected(self, tmp_path, numbers):
        case = _proven_case(case_id="FA4-PROV-001")
        revisions = [_valid_revision(revision=n) for n in numbers]
        document = fam_fixtures.build_corpus_document(
            CREATED_UTC, (case,), tuple(revisions)
        )
        corpus_file, _ = _seal_document(tmp_path, document)
        with pytest.raises(fam.BundleAuthoritySchemaError) as exc:
            fam.load_corpus(corpus_file)
        if numbers == [1, 1]:
            assert "not unique" in exc.value.reason
        else:
            assert "numbered 1..N without gaps" in exc.value.reason

    def test_revision_tamper_with_stale_manifest_rejected(self, tmp_path):
        # The corpus digest covers label_revisions: tampering a revision
        # and re-sealing the corpus loads the corpus under its own
        # recomputed digest, but the STALE manifest (bound to the
        # pre-tamper corpus digest) must fail.
        case = _proven_case(case_id="FA4-PROV-001")
        document = fam_fixtures.build_corpus_document(
            CREATED_UTC, (case,), (_valid_revision(),)
        )
        corpus_file, manifest_file = _seal_document(tmp_path, document)
        tampered = json.loads(corpus_file.read_text(encoding="utf-8"))
        tampered["label_revisions"][0]["statement"] = "tampered revision"
        tampered["corpus_digest"] = fam.corpus_state_digest(tampered)
        corpus_file.write_bytes(fam.canonically_serialize(tampered))
        # the tampered corpus alone loads under its own recomputed digest
        fam.load_corpus(corpus_file)
        # the stale manifest disagrees with the tampered corpus digest
        with pytest.raises(fam.BundleAuthorityManifestError) as exc:
            fam.load_bundle(corpus_file, manifest_file)
        assert "corpus_digest" in exc.value.reason


class TestLoaderByteContractRegression:
    def _sound_corpus_file(self, tmp_path):
        case = _proven_case(case_id="FA4-PROV-001")
        document = fam_fixtures.build_corpus_document(CREATED_UTC, (case,))
        base = tmp_path / "evaluation" / "fu4_bundle_authority_qualification"
        base.mkdir(parents=True, exist_ok=True)
        corpus_file = base / "corpus_v1.json"
        corpus_file.write_bytes(fam.canonically_serialize(document))
        return corpus_file

    def test_duplicate_json_keys_rejected(self, tmp_path):
        # A hidden duplicate key (last-wins parse) changes the byte
        # count: the file no longer equals its own canonical
        # re-serialization -> a deterministic tamper refusal.
        corpus_file = self._sound_corpus_file(tmp_path)
        raw = corpus_file.read_bytes()
        idx = raw.index(b'"corpus_id"')
        line = raw[raw.rfind(b"\n", 0, idx) + 1 : raw.index(b"\n", idx) + 1]
        assert raw.count(line) == 1
        corpus_file.write_bytes(raw.replace(line, line + line, 1))
        with pytest.raises(fam.BundleAuthoritySchemaError) as exc:
            fam.load_corpus(corpus_file)
        assert "stable canonical serialization" in exc.value.reason

    @pytest.mark.parametrize(
        "value", [float("nan"), float("inf")], ids=["NaN", "Infinity"]
    )
    def test_nan_and_infinity_rejected(self, tmp_path, value):
        # json.loads accepts the NaN / Infinity tokens; the canonical
        # re-serialization matches (both sides emit the token); the
        # strict decode refuses the float value itself - a bounded,
        # deterministic schema error, never a silent float.
        case = _proven_case(case_id="FA4-PROV-001", surface="DERIVATION")
        document = fam_fixtures.build_corpus_document(CREATED_UTC, (case,))
        document["cases"][0]["published_quantity"]["candidate"] = value
        raw = (
            json.dumps(document, indent=1, sort_keys=True, ensure_ascii=True)
            + "\n"
        ).encode("utf-8")
        base = tmp_path / "evaluation" / "fu4_bundle_authority_qualification"
        base.mkdir(parents=True, exist_ok=True)
        corpus_file = base / "corpus_v1.json"
        corpus_file.write_bytes(raw)
        with pytest.raises(fam.BundleAuthoritySchemaError) as exc:
            fam.load_corpus(corpus_file)
        assert "expected an int" in exc.value.reason

    def test_mixed_line_endings_rejected(self, tmp_path):
        corpus_file = self._sound_corpus_file(tmp_path)
        raw = corpus_file.read_bytes()
        corpus_file.write_bytes(raw.replace(b"\n", b"\r\n", 1))
        with pytest.raises(fam.BundleAuthoritySchemaError) as exc:
            fam.load_corpus(corpus_file)
        assert "stable canonical serialization" in exc.value.reason

    def test_exact_crlf_expansion_loads(self, tmp_path):
        # The documented autocrlf working-tree state: the EXACT CRLF
        # expansion of the canonical bytes is the only tolerated byte
        # variant (positive control).
        corpus_file = self._sound_corpus_file(tmp_path)
        raw = corpus_file.read_bytes()
        corpus_file.write_bytes(raw.replace(b"\n", b"\r\n"))
        bundle = fam.load_corpus(corpus_file)
        assert bundle.cases[0].case_id == "FA4-PROV-001"

    def test_non_canonical_manifest_bytes_rejected(self, tmp_path):
        corpus_file, manifest_file = _seal(tmp_path, [_proven_case()])
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        manifest_file.write_bytes(
            (json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=True) + "\n")
            .encode("utf-8")
        )
        with pytest.raises(fam.BundleAuthorityManifestError) as exc:
            fam.load_bundle(corpus_file, manifest_file)
        assert "stable canonical serialization" in exc.value.reason

    def test_non_ascii_bytes_rejected(self, tmp_path):
        # Unicode codepoint distinction at the FILE level: the canonical
        # form is ASCII (ensure_ascii); raw UTF-8 codepoints in the file
        # bytes are a serialization violation.
        case = _proven_case(case_id="FA4-PROV-001", surface="DERIVATION")
        case["case_category"] = "caf\u00e9 memory kit"
        document = fam_fixtures.build_corpus_document(CREATED_UTC, (case,))
        raw = (
            json.dumps(document, indent=1, sort_keys=True, ensure_ascii=False)
            + "\n"
        ).encode("utf-8")
        base = tmp_path / "evaluation" / "fu4_bundle_authority_qualification"
        base.mkdir(parents=True, exist_ok=True)
        corpus_file = base / "corpus_v1.json"
        corpus_file.write_bytes(raw)
        with pytest.raises(fam.BundleAuthoritySchemaError) as exc:
            fam.load_corpus(corpus_file)
        assert "stable canonical serialization" in exc.value.reason


# ---------------------------------------------------------------------------
# Q3-C-C1-FU2 (finding F-8): the execution boundary. REFUSED cases over
# EXACTLY the self-consistent sound shapes (PRESENTATION_GATE /
# REPLAY_AGREEMENT) load without the decoder executing the derivation /
# replay - stage coherence proves the documents are self-consistent
# below the construction layer only; it does NOT prove the actual
# authority outcome (actual derivation / replay correctness remains an
# E1 responsibility).
# ---------------------------------------------------------------------------


class TestExecutionBoundaryRefusals:
    def test_presentation_gate_refusal_over_sound_documents_loads(self, tmp_path):
        case = _proven_case(case_id="FA4-ADV-110", surface="DERIVATION")
        expected = _sealed_refusal_expected(
            stage="PRESENTATION_GATE", error_type="PRESENTATION"
        )
        _set_path(case, "expected", expected)
        bundle, _ = _decode_ok([case], tmp_path)
        assert bundle.cases[0].expected["outcome"] == "REFUSED"
        assert bundle.cases[0].expected["refusal"]["stage"] == "PRESENTATION_GATE"

    def test_refused_gate_labels_load_without_executing_the_authority_chain(
        self, tmp_path, monkeypatch
    ):
        # The documents are assembled FIRST (the test module MAY execute
        # the frozen chain to assemble fixtures); only the LOAD runs
        # under the sentinels.
        case_gate = _proven_case(case_id="FA4-ADV-111", surface="DERIVATION")
        _set_path(
            case_gate,
            "expected",
            _sealed_refusal_expected(
                stage="PRESENTATION_GATE", error_type="PRESENTATION"
            ),
        )
        case_replay = _proven_case(case_id="FA4-ADV-112", surface="BOTH")
        _set_path(
            case_replay,
            "expected",
            _sealed_refusal_expected(
                stage="REPLAY_AGREEMENT",
                error_type="REPLAY",
                replay="REPLAY_REFUSED",
            ),
        )

        def _sentinel(*args, **kwargs):
            raise AssertionError(
                "the corpus decoder invoked a production authority entry "
                "point (the label-determining surface)"
            )

        monkeypatch.setattr(fu4, "derive_sales_unit_authority_fu4", _sentinel)
        monkeypatch.setattr(fu4, "derive_sales_unit_authority_fu4_case", _sentinel)
        monkeypatch.setattr(fu4, "derive_authority_tier_fu4", _sentinel)
        monkeypatch.setattr(fu4, "derive_authority_tier_for_contract_fu4", _sentinel)
        import product_intelligence.research.semantic_decision_replay as replay

        monkeypatch.setattr(replay, "replay_semantic_decision", _sentinel)

        bundle, _ = _decode_ok([case_gate, case_replay], tmp_path)
        by_id = {case.case_id: case for case in bundle.cases}
        assert by_id["FA4-ADV-111"].expected["refusal"]["stage"] == "PRESENTATION_GATE"
        assert by_id["FA4-ADV-112"].expected["refusal"]["stage"] == "REPLAY_AGREEMENT"
        # Stage coherence over sound documents is NOT an authority
        # outcome: the loaded expectation is the independently recorded
        # label, verified for structural coherence only.


# ---------------------------------------------------------------------------
# Q3-C-C1-FU3 (the Q3-C-D1-FU1 adjudications of record, design section
# 9.11): the validator corrections - (a) the section 4.4 PROVEN
# coherence scoping over the presented channel form (C2-F1); (b) the
# identity-assessment decode over the empty normalized part numbers
# where the frozen constructor permits (the C1 identity-context
# defect); (c) the allowed NONE-basis recorded-extraction-result state
# + the new case-document-integrity refusal over the recorded-result /
# presented-channel mismatch (C2-F6); (d) the W9 coherence-separation
# statement (the checks use frozen contract data only); the W1
# exact-reason pins over the stage-coherence rejections.
# ---------------------------------------------------------------------------

_NONBUNDLE_FORMS = (
    # (kind, quantity, raw_detail, target form, target quantity, target
    # schema) - the three OBSERVED non-Bundle channel forms + their
    # frozen FU3 delegation rows (U1 / U3 / U8 PROVEN).
    (
        "SINGLE_UNIT", None, "single unit",
        "SINGLE_UNIT", None, "absent",
    ),
    (
        "PACK_QUANTITY", 4, "pack of 4",
        "PACK_QUANTITY", 4, "frozen_fu3",
    ),
    (
        "TRAY_OR_FACTORY_PACK", 25, "tray of 25",
        "TRAY_OR_FACTORY_PACK", 25, "frozen_fu3",
    ),
)


def _nonbundle_channel(kind, quantity, raw_detail):
    return s2c.CandidateSalesUnitEvidenceV2(
        state=s2c.PackagingEvidenceStateV2.OBSERVED,
        kind=s2c.SalesUnitKindV2(kind),
        quantity=quantity,
        raw_detail=raw_detail,
        source=s2c.CandidateEvidenceSourceV2.PUBLISHED_STRUCTURED_FIELD,
    )


def _unavailable_channel():
    return s2c.CandidateSalesUnitEvidenceV2(
        state=s2c.PackagingEvidenceStateV2.UNAVAILABLE,
        kind=None,
        quantity=None,
        raw_detail=None,
        source=None,
    )


def _fu3_target(form, quantity):
    return TargetSalesUnitEvidenceV2(
        TargetSalesUnitFormV2(form),
        quantity,
        TargetSalesUnitEvidenceSourceV2.REVIEWED_TARGET_CONTEXT,
    )


def _nonbundle_proven_parts(kind, quantity, raw_detail, form, tqty, case_id):
    """A sound non-Bundle-channel delegated FU3 PROVEN case (the
    A-DELE row shape) - fixture assembly over the frozen chain (the
    recorded FU3 row: U1 / U3 / U8 PROVEN under the FU4 token)."""
    channel = _nonbundle_channel(kind, quantity, raw_detail)
    base = _frozen_case_parts(channel=channel, case_id=case_id)
    evaluation = base["evaluation"]
    target = _fu3_target(form, tqty)
    decision = fu4.derive_authority_tier_fu4(
        base["context"],
        channel,
        evaluation,
        base["case"].context_provenances,
        base["case"].product_evidence,
        None,
        target_unit_evidence=target,
        candidate_composition=None,
        quantity_attestation=None,
    )
    # Contract re-reading (recorded, never a label source): the frozen
    # non-bundle delegation rows are PROVEN (P3 U1 / U3 / U8) with the
    # bundle-axis audit fields EXACTLY None (P3 D11).
    assert decision.sales_unit_authority.value == "PROVEN_EQUIVALENT", (
        f"the frozen non-bundle row over {kind} is not PROVEN "
        f"(got {decision.sales_unit_authority.value})"
    )
    assert decision.quantity_axis_state is None
    assert decision.candidate_composition_state is None
    assert decision.target_composition_state is None
    return {
        "case": base["case"],
        "channel": channel,
        "target": target,
        "assessment": base["context"],
        "evaluation": evaluation,
        "decision": decision,
    }


def _nonbundle_proven_case(idx, case_id, *, expected=None):
    kind, quantity, raw_detail, form, tqty, schema = _NONBUNDLE_FORMS[idx]
    parts = _nonbundle_proven_parts(kind, quantity, raw_detail, form, tqty, case_id)
    if expected is None:
        # The frozen P3 D11 delegation: the non-bundle PROVEN expected
        # carries EXACTLY null on the Bundle-axis fields (incl. the
        # textual-relation axis) - the C2-F1 adjudicated shape.
        expected = _expected_from_decision(
            parts["decision"], replay="NOT_APPLICABLE", textual_relation=None
        )
    target_doc = (
        None
        if schema == "absent"
        else {
            "form": form,
            "quantity": tqty,
            "source": TargetSalesUnitEvidenceSourceV2.REVIEWED_TARGET_CONTEXT.value,
        }
    )
    candidate_source_block = {
        "title_text": TITLE,
        "structured_fields": {"packaging": raw_detail},
        "source_url": None,
        "retrieved_utc": None,
        "raw_reference": None,
        "archive": None,
        "archive_digest": None,
        "recording_attestation": fam.SYNTHETIC_RECORDING_ATTESTATION,
    }
    target_source_block = {
        "title_text": "Requested product specification (by-construction)",
        "structured_fields": {"specification": f"sales unit: {raw_detail}"},
        "source_url": None,
        "retrieved_utc": None,
        "raw_reference": None,
        "archive": None,
        "archive_digest": None,
        "recording_attestation": fam.SYNTHETIC_RECORDING_ATTESTATION,
    }
    return _synthesize_case(
        case_id=case_id,
        matrix_row="A-DELE",
        channel=parts["channel"],
        candidate_composition=None,
        candidate_basis="NONE",
        extraction_evidence=None,
        target_evidence_schema=schema,
        target_evidence_document=target_doc,
        quantity_attestation_document=None,
        case=parts["case"],
        assessment=parts["assessment"],
        evaluation=parts["evaluation"],
        decision=parts["decision"],
        surface="DERIVATION",
        expected=expected,
        candidate_source_block=candidate_source_block,
        target_source_block=target_source_block,
    )



def _genuine_extraction(title, structured):
    """The genuine frozen P2 recorded extraction over the sealed text
    (evidence acquisition - design section 4.6 item 3): the canonical
    examined-input document + the sealed self-verifying result."""
    observation = _observation(title)
    result = extract_sales_unit_evidence(observation, structured)
    input_document = {
        "extraction_method": observation.extraction_method.value,
        "fields": {
            name: getattr(observation, name)
            for name in (
                "availability_text",
                "brand_text",
                "condition_text",
                "currency_text",
                "manufacturer_part_number_text",
                "offer_url_text",
                "price_text",
                "product_title",
                "sku_text",
                "source_url",
            )
        },
        "structured_packaging_field": structured,
    }
    assert fam.canonical_sha256(input_document) == result.input_digest
    return (
        {
            "input_document": input_document,
            "result_document": _result_sealed_doc(result),
        },
        result,
    )


def _recorded_result_case(
    case_id, *, title, structured, presented_channel, extra_structured=None
):
    """The allowed C2-F6 state shape: candidate composition record
    NULL + basis NONE + a PRESENT recorded extraction result over
    (title, structured) + the presented channel (sound or mismatching
    against the frozen P2 mapping of the result)."""
    parts = _frozen_case_parts(channel=presented_channel, case_id=case_id)
    evaluation = parts["evaluation"]
    target = _make_target_fu4(
        CLAUSE, fu4.BundleCompositionStateV2FU4.ESTABLISHED, None,
        _make_target_attestation(CLAUSE),
    )
    decision = fu4.derive_authority_tier_fu4(
        parts["context"],
        presented_channel,
        evaluation,
        parts["case"].context_provenances,
        parts["case"].product_evidence,
        None,
        target_unit_evidence=target,
        candidate_composition=None,
        quantity_attestation=None,
    )
    expected = _expected_from_decision(
        decision, replay="NOT_APPLICABLE", textual_relation=None
    )
    evidence, result = _genuine_extraction(title, structured)
    structured_fields = {
        "packaging": presented_channel.raw_detail
        if presented_channel.raw_detail is not None
        else structured
    }
    if extra_structured is not None:
        structured_fields["alternate_listing_text"] = extra_structured
    candidate_source_block = {
        "title_text": title,
        "structured_fields": structured_fields,
        "source_url": None,
        "retrieved_utc": None,
        "raw_reference": None,
        "archive": None,
        "archive_digest": None,
        "recording_attestation": fam.SYNTHETIC_RECORDING_ATTESTATION,
    }
    target_source_block = {
        "title_text": "Requested product specification (by-construction)",
        "structured_fields": {"specification": f"Bundle contents: {CLAUSE}"},
        "source_url": None,
        "retrieved_utc": None,
        "raw_reference": None,
        "archive": None,
        "archive_digest": None,
        "recording_attestation": fam.SYNTHETIC_RECORDING_ATTESTATION,
    }
    case = _synthesize_case(
        case_id=case_id,
        matrix_row="B6",
        channel=presented_channel,
        candidate_composition=None,
        candidate_basis="NONE",
        extraction_evidence=evidence,
        target_evidence_schema="fu4_v3",
        target_evidence_document=_target_sealed_doc(target),
        quantity_attestation_document=None,
        case=parts["case"],
        assessment=parts["context"],
        evaluation=evaluation,
        decision=decision,
        surface="DERIVATION",
        expected=expected,
        candidate_source_block=candidate_source_block,
        target_source_block=target_source_block,
    )
    return case, result


class TestC1FU3Corrections:
    # -- (a) the C2-F1 PROVEN coherence scoping -------------------------

    @pytest.mark.parametrize(
        "idx", range(len(_NONBUNDLE_FORMS)), ids=lambda i: _NONBUNDLE_FORMS[i][0]
    )
    def test_nonbundle_proven_over_exactly_null_bundle_axes_loads(
        self, idx, tmp_path
    ):
        case = _nonbundle_proven_case(idx, f"FA4-ADV-{130 + idx}")
        bundle, _ = _decode_ok([case], tmp_path)
        loaded = bundle.cases[0]
        assert loaded.expected["unit"] == "PROVEN_EQUIVALENT"
        # The frozen P3 D11 delegation: the Bundle-axis fields are
        # EXACTLY null on the expected axes.
        for field in (
            "quantity_axis",
            "candidate_composition_state",
            "target_composition_state",
            "textual_relation",
        ):
            assert loaded.expected[field] is None, field

    @pytest.mark.parametrize(
        "field, value",
        [
            ("quantity_axis", "BOTH_UNPUBLISHED"),
            ("candidate_composition_state", "ESTABLISHED"),
            ("target_composition_state", "ESTABLISHED"),
            ("textual_relation", "T-AGREE"),
        ],
        ids=lambda v: v,
    )
    def test_nonbundle_proven_over_nonnull_bundle_axis_is_refused(
        self, field, value, tmp_path
    ):
        case = _nonbundle_proven_case(1, "FA4-ADV-134")
        _set_path(case, f"expected.{field}", value)
        with pytest.raises(fam.BundleAuthorityLabelError) as exc:
            _decode_ok([case], tmp_path)
        # The W1 exact-reason pin: the misstated delegation is named.
        assert (
            f"unit PROVEN_EQUIVALENT over a non-Bundle channel (the "
            f"frozen P3 D11 delegation) requires the Bundle-axis "
            f"fields EXACTLY null on the expected axes; {field} must "
            f"be null, got {value!r} (the misstated delegation)"
        ) in exc.value.reason

    def test_bundle_proven_over_null_bundle_axis_is_still_refused(
        self, tmp_path
    ):
        # The scoping does not weaken the Bundle-channel branch: a
        # BUNDLE-form PROVEN expectation with an unsatisfied quantity
        # axis is still incoherent (the pre-C1-FU3 contract stands).
        case = _proven_case(case_id="FA4-ADV-135", surface="DERIVATION")
        _set_path(case, "expected.quantity_axis", None)
        with pytest.raises(fam.BundleAuthorityLabelError) as exc:
            _decode_ok([case], tmp_path)
        assert (
            "unit PROVEN_EQUIVALENT over a Bundle-channel case "
            "requires the quantity axis"
        ) in exc.value.reason

    def test_bundle_proven_over_unestablished_state_is_still_refused(
        self, tmp_path
    ):
        case = _proven_case(case_id="FA4-ADV-136", surface="DERIVATION")
        _set_path(case, "expected.target_composition_state", "ABSENT")
        with pytest.raises(fam.BundleAuthorityLabelError) as exc:
            _decode_ok([case], tmp_path)
        assert (
            "unit PROVEN_EQUIVALENT over a Bundle-channel case requires "
            "both composition states ESTABLISHED"
        ) in exc.value.reason

    # -- (b) the identity-context decode over the empty normalized
    #      part numbers (the C1 identity-context defect) ---------------

    def test_u4_no_mpn_identity_context_decodes(self, tmp_path):
        # The frozen derivation over a no-identifier observation yields
        # U4_NO_MPN with the EMPTY normalized candidate part number
        # (the constructor is the arbiter - type check only).
        observation = _observation("1TB NVMe Drive")
        parts = _frozen_case_parts(
            observation=observation, channel=_unavailable_channel()
        )
        assert parts["context"].substate.value == "U4_NO_MPN"
        assert parts["context"].normalized_candidate_part_number == ""
        evaluation = parts["evaluation"]
        target = _make_target_fu4(
            CLAUSE, fu4.BundleCompositionStateV2FU4.ESTABLISHED, None,
            _make_target_attestation(CLAUSE),
        )
        decision = fu4.derive_authority_tier_fu4(
            parts["context"],
            _unavailable_channel(),
            evaluation,
            parts["case"].context_provenances,
            parts["case"].product_evidence,
            None,
            target_unit_evidence=target,
            candidate_composition=None,
            quantity_attestation=None,
        )
        case = _synthesize_case(
            case_id="FA4-ADV-137",
            matrix_row="B-DELE",
            channel=_unavailable_channel(),
            candidate_composition=None,
            candidate_basis="NONE",
            extraction_evidence=None,
            target_evidence_schema="fu4_v3",
            target_evidence_document=_target_sealed_doc(target),
            quantity_attestation_document=None,
            case=parts["case"],
            assessment=parts["context"],
            evaluation=evaluation,
            decision=decision,
            surface="DERIVATION",
            candidate_source_block={
                "title_text": "1TB NVMe Drive",
                "structured_fields": {},
                "source_url": None,
                "retrieved_utc": None,
                "raw_reference": None,
                "archive": None,
                "archive_digest": None,
                "recording_attestation": fam.SYNTHETIC_RECORDING_ATTESTATION,
            },
        )
        bundle, _ = _decode_ok([case], tmp_path)
        identity = bundle.cases[0].evidence.identity_assessment
        assert identity.substate.value == "U4_NO_MPN"
        assert identity.normalized_candidate_part_number == ""

    def test_e1_no_target_mpn_identity_context_decodes(self):
        # Symmetrically: the empty normalized REQUESTED part number
        # (E1_NO_TARGET_MPN) the frozen IdentityStateAssessmentV2
        # constructor permits (type check only) decodes over the
        # loader's identity-assessment surface. (A complete V2 case
        # document can never carry the E1 state - the frozen case
        # constructor admits the semantic entry point only - so the
        # decode-level surface is the correct observation point.)
        doc = {
            "state": "DETERMINISTIC_UNEVALUABLE",
            "substate": "E1_NO_TARGET_MPN",
            "relationship_signals": ["NO_RELATION"],
            "normalized_requested_part_number": "",
            "normalized_candidate_part_number": "ABC-123",
        }
        assessment = fam._decode_identity_assessment(doc, path="identity")
        assert assessment.substate.value == "E1_NO_TARGET_MPN"
        assert assessment.normalized_requested_part_number == ""
        # The round-trip projection identity holds over the empty
        # normalized requested part number (the constructor is the
        # arbiter - no other identity constraint moved).
        projection = {
            "state": assessment.state.value,
            "substate": assessment.substate.value,
            "relationship_signals": sorted(
                s.value for s in assessment.relationship_signals
            ),
            "normalized_requested_part_number": assessment.normalized_requested_part_number,
            "normalized_candidate_part_number": assessment.normalized_candidate_part_number,
        }
        assert projection == doc

    @pytest.mark.parametrize(
        "path",
        [
            "scripted_context.identity_assessment.normalized_candidate_part_number",
            "recorded_case.v2_case_document.deterministic_identity_context."
            "normalized_candidate_part_number",
            "scripted_context.identity_assessment.normalized_requested_part_number",
        ],
        ids=lambda p: p.split(".")[-1] + "@" + p.split(".")[0],
    )
    def test_identity_part_number_type_validation_is_preserved(
        self, path, tmp_path
    ):
        # The correction permits the empty STRING exactly where the
        # frozen constructor permits it; the strict type validation
        # stands (a non-string is still refused).
        case = _proven_case(case_id="FA4-ADV-139", surface="DERIVATION")
        _set_path(case, path, 123)
        with pytest.raises(fam.BundleAuthoritySchemaError) as exc:
            _decode_ok([case], tmp_path)
        assert "expected a str" in exc.value.reason

    # -- (c) the C2-F6 allowed recorded-extraction-result state --------

    def test_none_basis_recorded_result_over_matching_mapping_loads(
        self, tmp_path
    ):
        # The allowed state: candidate composition record null, basis
        # NONE, the recorded result present, the presented channel
        # EXACTLY the frozen P2 mapping of that result (the canonical
        # UNAVAILABLE over AMBIGUOUS_CUE).
        case, result = _recorded_result_case(
            "FA4-ADV-140",
            title=TITLE,
            structured="bundle of 3",
            presented_channel=_unavailable_channel(),
        )
        assert result.state.value == "AMBIGUOUS_CUE"
        assert (
            sales_unit_channel_from_extraction(result).canonical()
            == case["derivation_inputs"]["channel"]
        )
        bundle, _ = _decode_ok([case], tmp_path)
        loaded = bundle.cases[0]
        assert loaded.evidence.candidate_composition is None
        assert loaded.evidence.extraction_result is not None
        assert loaded.evidence.extraction_result.state is result.state
        assert loaded.expected["unit"] == "UNPROVEN"

    def test_none_basis_recorded_result_over_mismatching_mapping_rejected(
        self, tmp_path
    ):
        # The recorded result was not the result the presented channel
        # was mapped from - a sound DERIVED case is refused (strict).
        case, _ = _recorded_result_case(
            "FA4-ADV-141",
            title=TITLE,
            structured="bundle of 3",
            presented_channel=_bundle_channel(
                None, "bundle: 2x RAM + 1x CPU, complete list"
            ),
            extra_structured="bundle of 3",
        )
        with pytest.raises(fam.BundleAuthorityEvidenceError) as exc:
            _decode_ok([case], tmp_path)
        assert (
            "the presented channel is not the frozen P2 mapping of the "
            "case's recorded extraction result"
        ) in exc.value.reason

    def test_recorded_result_mismatch_sealed_raw_corpus_integrity_loads(
        self, tmp_path
    ):
        # The mismatch labeled CORPUS_INTEGRITY (the loader-only
        # observation point) is coherent over the sealed documents.
        case, _ = _recorded_result_case(
            "FA4-ADV-142",
            title=TITLE,
            structured="bundle of 3",
            presented_channel=_bundle_channel(
                None, "bundle: 2x RAM + 1x CPU, complete list"
            ),
            extra_structured="bundle of 3",
        )
        _set_path(
            case, "expected", _sealed_refusal_expected(stage="CORPUS_INTEGRITY")
        )
        bundle, _ = _decode_ok([case], tmp_path)
        assert (
            bundle.cases[0].expected["refusal"]["stage"] == "CORPUS_INTEGRITY"
        )

    def test_recorded_result_mismatch_under_gate_label_is_incoherent(
        self, tmp_path
    ):
        # W1 exact-reason pin: the stage-coherence refusal over the
        # mismatch names the fired observation deterministically.
        case, _ = _recorded_result_case(
            "FA4-ADV-143",
            title=TITLE,
            structured="bundle of 3",
            presented_channel=_bundle_channel(
                None, "bundle: 2x RAM + 1x CPU, complete list"
            ),
            extra_structured="bundle of 3",
        )
        _set_path(
            case,
            "expected",
            _sealed_refusal_expected(
                stage="PRESENTATION_GATE", error_type="PRESENTATION"
            ),
        )
        with pytest.raises(fam.BundleAuthorityLabelError) as exc:
            _decode_ok([case], tmp_path)
        assert (
            "case FA4-ADV-143: the labeled PRESENTATION_GATE defect "
            "requires exactly the self-consistent sealed shapes (no "
            "constructor- / codec- / case-document-integrity "
            "observation), but fired: CASEDOC_RECORDED_RESULT_CHANNEL_"
            "MAPPING (CASE_DOCUMENT) (incoherent label)"
        ) == exc.value.reason

    # -- (c) the preserved negative contracts --------------------------

    def test_extraction_basis_still_requires_the_record_and_evidence(
        self, tmp_path
    ):
        # EXTRACTION_RESULT_V1 without the candidate composition record
        # is still incoherent (the negative contract stands).
        case, _ = _recorded_result_case(
            "FA4-ADV-144",
            title=TITLE,
            structured="bundle of 3",
            presented_channel=_unavailable_channel(),
        )
        _set_path(case, "derivation_inputs.candidate_basis", "EXTRACTION_RESULT_V1")
        with pytest.raises(fam.BundleAuthorityEvidenceError) as exc:
            _decode_ok([case], tmp_path)
        assert "EXTRACTION_RESULT_V1" in exc.value.reason

    def test_recorded_channel_basis_still_carries_no_extraction_evidence(
        self, tmp_path
    ):
        # RECORDED_CHANNEL + a present recorded result is still
        # incoherent (the negative contract stands).
        case, _ = _recorded_result_case(
            "FA4-ADV-145",
            title=TITLE,
            structured="bundle of 3",
            presented_channel=_unavailable_channel(),
        )
        _set_path(case, "derivation_inputs.candidate_basis", "RECORDED_CHANNEL")
        with pytest.raises(fam.BundleAuthorityEvidenceError) as exc:
            _decode_ok([case], tmp_path)
        assert "RECORDED_CHANNEL" in exc.value.reason

    def test_none_basis_still_carries_no_candidate_record(self, tmp_path):
        # NONE + a present candidate composition record is still
        # incoherent (the negative contract stands).
        case, _ = _recorded_result_case(
            "FA4-ADV-146",
            title=TITLE,
            structured="bundle of 3",
            presented_channel=_unavailable_channel(),
        )
        record = fu4.candidate_composition_from_channel(
            _bundle_channel(None, EST_RAW_DETAIL)
        )
        _set_path(
            case, "derivation_inputs.candidate_composition", _candidate_sealed_doc(record)
        )
        with pytest.raises(fam.BundleAuthorityEvidenceError) as exc:
            _decode_ok([case], tmp_path)
        assert "NONE carries no candidate composition record" in exc.value.reason

    # -- (d) the W1 exact-reason pins over the stage-coherence rule ----

    def test_corpus_integrity_label_without_defect_is_incoherent(self, tmp_path):
        case = _proven_case(case_id="FA4-ADV-147", surface="DERIVATION")
        _set_path(
            case, "expected", _sealed_refusal_expected(stage="CORPUS_INTEGRITY")
        )
        with pytest.raises(fam.BundleAuthorityLabelError) as exc:
            _decode_ok([case], tmp_path)
        assert (
            "case FA4-ADV-147: the labeled CORPUS_INTEGRITY defect is "
            "not present - no case-document-integrity check fired over "
            "the sealed documents (an incoherent label is a "
            "corpus-integrity failure, never a test failure)"
        ) == exc.value.reason

    def test_codec_decode_label_over_derivation_surface_is_incoherent(
        self, tmp_path
    ):
        case = _proven_case(case_id="FA4-ADV-148", surface="DERIVATION")
        _set_path(
            case,
            "expected",
            _sealed_refusal_expected(stage="CODEC_DECODE", error_type="CODEC"),
        )
        with pytest.raises(fam.BundleAuthorityLabelError) as exc:
            _decode_ok([case], tmp_path)
        assert (
            "case FA4-ADV-148: the CODEC_DECODE stage requires the "
            "record surface, got 'DERIVATION'"
        ) == exc.value.reason

    def test_construction_label_over_case_document_defect_is_incoherent(
        self, tmp_path
    ):
        # The D6-ii shape: the channel mismatch is the loader's
        # case-document-integrity observation (a gate-layer
        # corroboration may also fire) - no construction-layer
        # observation fires, so a CONSTRUCTION label is incoherent
        # (the W1 exact reason pin).
        parts = _proven_parts()
        channel_b = _bundle_channel(
            None, "bundle: 1x SSD + 1x cable, complete list"
        )
        case = _sealed_case(
            base=parts,
            case_id="FA4-ADV-149",
            stage="CONSTRUCTION",
            error_type="CONSTRUCTOR",
            matrix_row="D6",
            candidate_source_block={
                "title_text": TITLE,
                "structured_fields": {
                    "packaging": "bundle: 1x SSD + 1x cable, complete list"
                },
                "source_url": None,
                "retrieved_utc": None,
                "raw_reference": None,
                "archive": None,
                "archive_digest": None,
                "recording_attestation": fam.SYNTHETIC_RECORDING_ATTESTATION,
            },
            candidate_att_source={
                "state": "ABSENT", "verbatim": None, "location": None
            },
            target_att_source={"state": "ABSENT", "verbatim": None, "anchor": None},
        )
        _set_path(case, "derivation_inputs.channel", channel_b.canonical())
        _set_path(
            case,
            "derivation_inputs.candidate_composition",
            _candidate_sealed_doc(parts["candidate"]),
        )
        with pytest.raises(fam.BundleAuthorityLabelError) as exc:
            _decode_ok([case], tmp_path)
        assert (
            "case FA4-ADV-149: the labeled CONSTRUCTION defect is not "
            "observable - no frozen constructor / codec / "
            "construction-level coherence check fired over the "
            "sealed documents (the defect would be caught at no "
            "construction layer; incoherent label)"
        ) == exc.value.reason

    # -- (e) the W9 no-implementation-oracle boundary -------------------

    def test_coherence_checks_name_the_frozen_contract_data_only(self):
        # The W9 adjudication of record, named in the module contract:
        # the coherence checks use frozen contract data only - never
        # the FU4 derivation, the R1 replay, or any model.
        doc = re.sub(r"\s+", " ", fam.__doc__ or "")
        assert "W9 coherence separation" in doc
        assert "FROZEN CONTRACT DATA AND CONSTRUCTORS ONLY" in doc
        assert "NEVER calculate an expected label from the FU4 derivation" in doc

    def test_derived_load_invokes_no_authority_oracle(self, tmp_path, monkeypatch):
        # A sound DERIVED case over the allowed C2-F6 state loads with
        # the derivation / replay / model sentinels in place: the
        # coherence checks read the frozen contract data (incl. the
        # frozen P2 mapping) only - never an implementation oracle.
        case, _ = _recorded_result_case(
            "FA4-ADV-150",
            title=TITLE,
            structured="bundle of 3",
            presented_channel=_unavailable_channel(),
        )

        def _sentinel(*args, **kwargs):
            raise AssertionError(
                "the corpus decoder invoked a production authority entry "
                "point (the label-determining surface)"
            )

        monkeypatch.setattr(fu4, "derive_sales_unit_authority_fu4", _sentinel)
        monkeypatch.setattr(fu4, "derive_sales_unit_authority_fu4_case", _sentinel)
        monkeypatch.setattr(fu4, "derive_authority_tier_fu4", _sentinel)
        monkeypatch.setattr(fu4, "derive_authority_tier_for_contract_fu4", _sentinel)
        import product_intelligence.research.semantic_decision_replay as replay

        monkeypatch.setattr(replay, "replay_semantic_decision", _sentinel)

        bundle, _ = _decode_ok([case], tmp_path)
        assert bundle.cases[0].expected["unit"] == "UNPROVEN"
