"""Adversarial Prompt 2.1 / FU3-binding tests (Q3-B5-P1, T5 + task
item 8).

Every model call is a scripted, recording test double - no live
network call anywhere, no benchmark capture performed.

* T5 (capture infrastructure): the bounded live runner renders the
  byte-exact 2.1 prompt for every eligible case of the 1.1.0 corpus
  (the corpus binding selects the prompt version); the contract-
  negative cases are never rendered / sent / recorded; the written
  document pins the 2.1 prompt axis and the manifest records the REAL
  2.1 system-prompt digest; the runner on the 1.0.0 corpus stays
  byte-frozen 2.0 (old-version replay isolation at the runner level);
  a completed 2.1 run round-trips the strict loader and evaluates to a
  complete no-authority POLICY_PENDING report.
* Silent multi-pack (A9): a grounded-identifier MATCH with the sales-
  unit channel UNAVAILABLE (no cue anywhere) scores CORRECT against
  the label, the recorded absence NEVER derives proven equivalence
  (a sales-unit UNAVAILABLE never means proven equal), no model
  output independently grants product identity or pricing authority,
  and the documented frozen-derivation blindness stands (the R14
  exposure is pinned in the binding/replay file; the separately
  versioned FU3 derivation is the one that caps it).
* Ambiguous packaging cues: a MATCH on a published incompatible
  packaging case (the absolute rule) is a CRITICAL false MATCH and
  fails the packaging / hard-conflict gates; the safe definite answer
  scores CORRECT.
* Generic descriptions: a MATCH on a thin/generic-overlap case (no
  resolution grounded) is a false MATCH detected at qualification
  (never authority); the in-set poles of the ambiguous shapes stay
  DEFENSIBLE.
* Near-miss identifiers: a MATCH on the customer-retrieval-alias
  sales-unit-safety shapes (0018/0022) is a CRITICAL false MATCH in
  the sales-unit-safety metric; the authority-resolved near miss
  (0020) scores CORRECT with the licensed reason code and no
  unauthorized-authority note.
* Internal contradictions: UNCERTAIN naming the contradicted
  dimension (the 2.1 rule, the pre-registered 0037 flip) scores
  CORRECT; the 2.0-era false NO_MATCH on the contradiction is
  detected (FALSE_NO_MATCH, REVIEW - safe direction).
* Old-version replay isolation: the same scripted responses scored
  against the 1.0.0 and the 1.1.0 corpus produce identical per-case
  verdicts (the binding is record identity, not scoring), and each
  version's captures / reports stay bound to their own corpus.
"""

from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest

from tests.evaluation.semantic_v2._q3a_helpers import (
    CORPUS_2_1_PATH,
    CORPUS_PATH,
    POLICY_PATH,
    default_response_for,
    load_corpus_bundle,
    make_response,
    primary_route,
)
from tests.evaluation.semantic_v2._q3a_fu1_helpers import (
    write_direct_capture,
)
from product_intelligence.evaluation.semantic.transport import (
    TransportFailure,
    TransportResult,
)
from product_intelligence.evaluation.semantic_v2 import live_capture as lc
from product_intelligence.evaluation.semantic_v2.canonical import (
    canonical_sha256,
)
from product_intelligence.evaluation.semantic_v2.corpus import (
    CONTRACT_NEGATIVE_CASE_CLASS,
    load_corpus,
)
from product_intelligence.evaluation.semantic_v2.direct_capture import (
    load_direct_capture,
    verify_direct_capture_against_corpus,
)
from product_intelligence.evaluation.semantic_v2.evaluator import (
    evaluate_direct_for_model,
)
from product_intelligence.evaluation.semantic_v2.gates import (
    decide,
    evaluate_safety_gates,
)
from product_intelligence.evaluation.semantic_v2.policy import (
    load_policy,
    policy_applies_to,
    evaluate_thresholds,
)
from product_intelligence.evaluation.semantic_v2.report import (
    build_direct_report,
    verify_direct_report,
)
from product_intelligence.research import (
    IdentityStateAssessmentV2,
    PackagingEvidenceStateV2,
    SALES_UNIT_EVIDENCE_UNAVAILABLE,
)
from product_intelligence.research import semantic_authority_fu3 as fu3
from product_intelligence.semantic.contract_v2 import (
    SYSTEM_PROMPT_V2,
    build_semantic_prompt_v2,
)
from product_intelligence.semantic.contract_v2_1 import (
    SEMANTIC_PROMPT_VERSION_V2_1,
    SYSTEM_PROMPT_V2_1,
    build_semantic_prompt_v2_1,
)


@pytest.fixture(scope="module")
def corpus_2_0():
    return load_corpus(CORPUS_PATH)


@pytest.fixture(scope="module")
def corpus_2_1():
    return load_corpus(CORPUS_2_1_PATH)


def _outcome(result, case_id: str):
    return next(o for o in result.outcomes if o.case_id == case_id)


def _assessment(typed) -> IdentityStateAssessmentV2:
    """The recorded deterministic context of one typed V2 case (the
    FU3 derivations take the recorded assessment, never the model
    output)."""
    return IdentityStateAssessmentV2(
        state=typed.identity_state,
        substate=typed.substate,
        relationship_signals=typed.relationship_signals,
        normalized_requested_part_number=(
            typed.normalized_requested_part_number
        ),
        normalized_candidate_part_number=(
            typed.normalized_candidate_part_number
        ),
    )


def _decide(corpus, result, policy):
    gates = evaluate_safety_gates(result)
    te = (
        evaluate_thresholds(policy, result.metrics)
        if policy_applies_to(
            policy, corpus.corpus_id, corpus.corpus_version
        )
        else None
    )
    decision, rationale = decide(result, gates, policy, te)
    return decision, rationale, gates


# ---------------------------------------------------------------------------
# The scripted, recording 2.1 transport double (declared fixtures, not
# model output; no network)
# ---------------------------------------------------------------------------


class ScriptedTransport2_1:
    """One scripted, recording model stand-in for the 2.1 runner.

    ``scripts`` maps case_id -> raw output string (the label-consistent
    fixture by default). Any prompt that is not the byte-exact 2.1
    builder output for an eligible semantic case fails loudly (the
    runner is proven to send only frozen-builder output).
    """

    def __init__(
        self,
        corpus,
        scripts: dict[str, str] | None = None,
    ) -> None:
        self.calls: list[dict] = []
        self._prompt_to_case: dict[str, str] = {}
        for case in corpus.semantic_cases:
            prompt = build_semantic_prompt_v2_1(case.build_semantic_case())
            self._prompt_to_case[prompt.user_prompt] = case.case_id
        if scripts is None:
            scripts = {
                case.case_id: default_response_for(case)
                for case in corpus.semantic_cases
            }
        self.scripts = scripts

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> TransportResult:
        assert system_prompt == SYSTEM_PROMPT_V2_1, (
            "a system prompt that is not the separately versioned 2.1 "
            "text was sent to the model"
        )
        case_id = self._prompt_to_case.get(user_prompt)
        assert case_id is not None, (
            "a user prompt that is not the frozen 2.1 builder output "
            "for an eligible semantic case was sent to the model"
        )
        self.calls.append(
            {
                "case_id": case_id,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        raw = self.scripts[case_id]
        return TransportResult(
            raw_output=raw,
            latency_ms=1.0,
            provider_status="200",
            provider_id="fake",
            model_id=model,
            provider_reported_model=model,
            finish_reason="stop",
            token_usage=None,
        )


def _run_2_1(
    corpus,
    tmp_path: Path,
    scripts: dict[str, str] | None = None,
    provider: str | None = None,
    model: str | None = None,
) -> lc.LiveCaptureRunner:
    route = primary_route()
    config = lc.LiveCaptureConfig(
        provider=provider or route[0],
        model=model or route[1],
        max_attempts=1,
        run_id="q3b5p1-test-fixture",
        captured_by="Q3-B5-P1 test fixture (not a model response)",
        notes=(
            "Q3-B5-P1 adversarial test fixture: scripted responses, "
            "no live call"
        ),
        output_dir=tmp_path,
        transport=ScriptedTransport2_1(corpus, scripts),
    )
    runner = lc.LiveCaptureRunner(config, corpus)
    outcome = runner.run()
    assert outcome.abort is None
    runner.write_artifacts(outcome)
    return runner


# ===========================================================================
# T5. Capture infrastructure: the runner on the 1.1.0 corpus
# ===========================================================================


class TestRunner2_1PromptFidelity:
    def test_the_runner_renders_the_byte_exact_2_1_prompt(
        self, corpus_2_1, tmp_path
    ) -> None:
        runner = _run_2_1(corpus_2_1, tmp_path)
        transport = runner._config.transport
        assert len(transport.calls) == 43
        for call in transport.calls:
            case = corpus_2_1.case(call["case_id"])
            expected = build_semantic_prompt_v2_1(case.build_semantic_case())
            assert call["system_prompt"] == SYSTEM_PROMPT_V2_1
            assert call["user_prompt"] == expected.user_prompt
            assert call["temperature"] == lc.LIVE_TEMPERATURE
            assert call["max_tokens"] == lc.LIVE_MAX_TOKENS

    def test_the_document_and_manifest_pin_the_2_1_identity(
        self, corpus_2_1, tmp_path
    ) -> None:
        runner = _run_2_1(corpus_2_1, tmp_path)
        doc = json.loads(runner.capture_path.read_text(encoding="utf-8"))
        assert doc["prompt_version"] == "2.1"
        assert doc["semantic_contract"] == "V2"
        assert doc["corpus_version"] == "1.1.0"
        manifest = json.loads(runner.manifest_path.read_text(encoding="utf-8"))
        assert manifest["prompt_version"] == "2.1"
        assert manifest["system_prompt_sha256"] == canonical_sha256(
            {"text": SYSTEM_PROMPT_V2_1}
        )
        # The manifest shape is unchanged (the Q3-B key set + the FU1
        # dispatch_states key); only the recorded pin values moved.
        assert manifest["live_manifest_schema_version"] == 1
        assert manifest["generation_parameters"] == {
            "temperature": "0.0",
            "max_tokens": 32768,
        }
        # The written artifact round-trips the strict loader and binds
        # to the 1.1.0 corpus exactly.
        capture = load_direct_capture(runner.capture_path)
        assert capture.prompt_version == SEMANTIC_PROMPT_VERSION_V2_1
        verify_direct_capture_against_corpus(capture, corpus_2_1)

    def test_contract_negatives_are_never_rendered_sent_or_recorded(
        self, corpus_2_1, tmp_path
    ) -> None:
        runner = _run_2_1(corpus_2_1, tmp_path)
        cn_ids = {
            c.case_id
            for c in corpus_2_1.cases
            if c.case_class == CONTRACT_NEGATIVE_CASE_CLASS
        }
        assert len(cn_ids) == 13
        sent = {call["case_id"] for call in runner._config.transport.calls}
        assert not (sent & cn_ids)
        doc = json.loads(runner.capture_path.read_text(encoding="utf-8"))
        recorded = {r["case_id"] for r in doc["records"]}
        assert not (recorded & cn_ids)
        assert recorded == sent

    def test_the_runner_on_the_1_0_0_corpus_stays_byte_frozen_2_0(
        self, corpus_2_0, tmp_path
    ) -> None:
        """Old-version replay isolation at the runner level: the same
        runner over the historical corpus renders the frozen 2.0
        builder output byte-exactly and pins 2.0."""
        route = primary_route()
        transport_calls: list[dict] = []

        class ScriptedTransport2_0:
            def __init__(self) -> None:
                self._map = {
                    build_semantic_prompt_v2(
                        c.build_semantic_case()
                    ).user_prompt: c.case_id
                    for c in corpus_2_0.semantic_cases
                }

            def complete(self, *, system_prompt, user_prompt, model,
                         temperature, max_tokens):
                assert system_prompt == SYSTEM_PROMPT_V2
                case_id = self._map[user_prompt]
                transport_calls.append(
                    {"case_id": case_id, "system_prompt": system_prompt}
                )
                return TransportResult(
                    raw_output=default_response_for(
                        corpus_2_0.case(case_id)
                    ),
                    latency_ms=1.0,
                    provider_status="200",
                    provider_id="fake",
                    model_id=model,
                    provider_reported_model=model,
                    finish_reason="stop",
                    token_usage=None,
                )

        config = lc.LiveCaptureConfig(
            provider=route[0],
            model=route[1],
            max_attempts=1,
            run_id="q3b5p1-frozen-2_0-fixture",
            output_dir=tmp_path,
            transport=ScriptedTransport2_0(),
        )
        runner = lc.LiveCaptureRunner(config, corpus_2_0)
        outcome = runner.run()
        assert outcome.abort is None
        runner.write_artifacts(outcome)
        doc = json.loads(runner.capture_path.read_text(encoding="utf-8"))
        assert doc["prompt_version"] == "2.0"
        assert len(transport_calls) == 43
        assert all(
            c["system_prompt"] == SYSTEM_PROMPT_V2 for c in transport_calls
        )

    def test_a_completed_2_1_run_evaluates_to_complete_no_authority(
        self, corpus_2_1, tmp_path
    ) -> None:
        runner = _run_2_1(corpus_2_1, tmp_path)
        capture = load_direct_capture(runner.capture_path)
        result = evaluate_direct_for_model(
            corpus_2_1, capture, *capture.target_route
        )
        policy = load_policy(POLICY_PATH)
        decision, rationale, gates = _decide(corpus_2_1, result, policy)
        assert decision == "POLICY_PENDING"
        assert result.metrics["counts"]["evaluated_cases"] == 43
        assert all(g.passed for g in gates.values())
        report = build_direct_report(
            result=result,
            gates=gates,
            policy=policy,
            threshold_evaluation=None,
            decision=decision,
            rationale=rationale,
            corpus=corpus_2_1,
            direct_capture=capture,
            generated_utc="2026-10-09T00:00:00Z",
        )
        verify_direct_report(report, corpus_2_1)
        assert report["authority"]["granted"] is False
        assert report["authority"]["v2_authority_qualified"] is False
        # No model output independently grants product identity
        # authority: the report names no tier and grants nothing.
        text = json.dumps(report)
        assert "AI_ASSISTED_COMPARABLE" not in text
        assert "MACHINE_VERIFIED" not in text
        assert "HUMAN_CONFIRMED" not in text


# ===========================================================================
# Task item 8a. Silent multi-pack (A9): UNAVAILABLE never means proven
# equal; no model output grants identity / pricing authority
# ===========================================================================


class TestSilentMultiPack:
    G1_CASES = (
        "V2Q-SSD-U1-MATCH-0001",
        "V2Q-SSD-U2E-MATCH-0006",
        "V2Q-SSD-SEO-MATCH-0038",
        "V2Q-SSD-U1-PRODCTX-0041",
    )

    def test_the_recorded_absence_never_derives_proven_equivalent(
        self, corpus_2_1
    ) -> None:
        # Every one of the eleven expected-MATCH cases carries the
        # explicit UNAVAILABLE channel (no packaging published
        # anywhere - the silent shape). A MATCH answer there is
        # CORRECT against the label...
        for case_id in self.G1_CASES:
            case = corpus_2_1.case(case_id)
            assert (
                case.input_payload["candidate"]["commercial"][
                    "sales_unit"
                ]["state"]
                == "UNAVAILABLE"
            )
            typed = case.build_semantic_case()
            assert typed.candidate_commercial.sales_unit.state is (
                PackagingEvidenceStateV2.UNAVAILABLE
            )
            # ...and the recorded absence NEVER derives proven
            # equivalence: the sales-unit authority is UNPROVEN
            # regardless of what the model says (the derivation takes
            # no model input).
            assert (
                fu3.derive_sales_unit_authority(typed)
                is fu3.SalesUnitAuthorityV2.UNPROVEN
            )
            # And an UNPROVEN unit can never hold the automatic
            # comparable tier under the separately versioned
            # derivation (the firewall stands even for the strongest
            # part-number ground - MATCH + HIGH + clean, no reviewed
            # relation required for these shapes).
            from product_intelligence.research import (
                AuthorityTier,
                ProductEvidenceProfileV2,
                ProductEvidenceQuality,
                ProductEvidenceDimension,
                ProductEvidenceFactV2,
                CandidateProductEvidenceSource,
                SemanticEvaluationV2,
                V2SemanticDecision,
                V2Confidence,
            )

            strong = ProductEvidenceProfileV2(
                has_usable_product_title=True,
                matched_facts=frozenset(
                    {
                        ProductEvidenceFactV2(
                            ProductEvidenceDimension.CAPACITY,
                            frozenset(
                                {
                                    CandidateProductEvidenceSource.LISTING_PRODUCT_TITLE
                                }
                            ),
                        ),
                        ProductEvidenceFactV2(
                            ProductEvidenceDimension.INTERFACE,
                            frozenset(
                                {
                                    CandidateProductEvidenceSource.LISTING_PRODUCT_TITLE
                                }
                            ),
                        ),
                    }
                ),
            )
            evaluation = SemanticEvaluationV2.evaluated(
                V2SemanticDecision.MATCH,
                V2Confidence.HIGH,
                frozenset(),
            )
            decision = fu3.derive_authority_tier_fu3(
                _assessment(typed),
                SALES_UNIT_EVIDENCE_UNAVAILABLE,
                evaluation,
                typed.context_provenances,
                strong,
            )
            assert decision.sales_unit_authority is (
                fu3.SalesUnitAuthorityV2.UNPROVEN
            )
            assert decision.tier is not AuthorityTier.AI_ASSISTED_COMPARABLE

    def test_a_silent_multi_pack_match_scores_correct_and_grants_nothing(
        self, corpus_2_1, tmp_path
    ) -> None:
        runner = _run_2_1(corpus_2_1, tmp_path)
        capture = load_direct_capture(runner.capture_path)
        result = evaluate_direct_for_model(
            corpus_2_1, capture, *capture.target_route
        )
        for case_id in self.G1_CASES:
            o = _outcome(result, case_id)
            assert o.state == "EVALUATED"
            assert o.verdict == "CORRECT"
            assert o.model_decision == "MATCH"
        # The false-MATCH metrics stay zero; the report grants no
        # authority (persist-only posture unchanged).
        assert result.metrics["false_match_count"] == 0
        assert result.metrics["sales_unit_safety_false_match_count"] == 0


# ===========================================================================
# Task item 8b. Ambiguous packaging cues (the absolute rule, N-1)
# ===========================================================================


class TestAmbiguousPackagingCues:
    def test_a_match_on_published_incompatible_packaging_is_critical(
        self, corpus_2_1, tmp_path
    ) -> None:
        # 0032: OBSERVED tray, expected NO_MATCH (PACKAGING_QUANTITY),
        # sales-unit-safety flagged. A MATCH on the absolute-rule case
        # is the CRITICAL false MATCH the corpus exists to catch.
        path = write_direct_capture(
            tmp_path / "d.json",
            corpus_2_1,
            decisions={"V2Q-SSD-SU-TRAY-0032": "MATCH"},
        )
        result = evaluate_direct_for_model(
            corpus_2_1, load_direct_capture(path), *primary_route()
        )
        o = _outcome(result, "V2Q-SSD-SU-TRAY-0032")
        assert o.verdict == "FALSE_MATCH"
        assert o.severity == "CRITICAL"
        gates = evaluate_safety_gates(result)
        assert not gates[
            "zero_false_match_on_packaging_quantity_conflicts"
        ].passed
        assert not gates[
            "zero_false_match_on_always_hard_conflicts"
        ].passed
        policy = load_policy(POLICY_PATH)
        decision, _rationale, _gates = _decide(corpus_2_1, result, policy)
        assert decision == "NOT_QUALIFIED"

    def test_the_safe_definite_answer_on_the_absolute_rule_case(
        self, corpus_2_1, tmp_path
    ) -> None:
        # The label-consistent NO_MATCH (PACKAGING_QUANTITY) scores
        # CORRECT and keeps every gate green.
        path = write_direct_capture(tmp_path / "d.json", corpus_2_1)
        result = evaluate_direct_for_model(
            corpus_2_1, load_direct_capture(path), *primary_route()
        )
        for case_id in (
            "V2Q-SSD-SU-TRAY-0032",
            "V2Q-SSD-SU-MULTI-0033",
            "V2Q-GPU-SU-BUNDLE-0034",
        ):
            o = _outcome(result, case_id)
            assert o.verdict == "CORRECT"
            assert o.model_decision == "NO_MATCH"
        gates = evaluate_safety_gates(result)
        assert all(g.passed for g in gates.values())


# ===========================================================================
# Task item 8c. Generic descriptions (distinctive alignment fails)
# ===========================================================================


class TestGenericDescriptions:
    def test_a_match_on_generic_overlap_is_detected_not_authoritative(
        self, corpus_2_1, tmp_path
    ) -> None:
        # 0015: "NVMe SSD" vs requested "3.84TB U.3 NVMe data center
        # SSD" - CAPACITY and FORM_FACTOR unpinned (generic overlap; no
        # resolution grounded). A MATCH is a 2.1 contract violation:
        # the harness scores it FALSE_MATCH (HIGH - no published hard
        # conflict in the label), and nothing about it can become
        # authority (persist-only, unqualified).
        path = write_direct_capture(
            tmp_path / "d.json",
            corpus_2_1,
            decisions={"V2Q-SSD-U4-THIN-0015": "MATCH"},
        )
        result = evaluate_direct_for_model(
            corpus_2_1, load_direct_capture(path), *primary_route()
        )
        o = _outcome(result, "V2Q-SSD-U4-THIN-0015")
        assert o.verdict == "FALSE_MATCH"
        assert o.severity == "HIGH"
        assert result.metrics["false_match_count"] == 1
        policy = load_policy(POLICY_PATH)
        decision, _rationale, _gates = _decide(corpus_2_1, result, policy)
        # No gate fails (the label carries no expected hard conflict),
        # so the failure is visible in the scored verdict + metric -
        # and the decision can never be QUALIFIED (the policy is not
        # applicable to 1.1.0 and the draft is unapproved).
        assert decision != "QUALIFIED"
        assert decision == "POLICY_PENDING"

    def test_the_uncertain_answer_on_generic_overlap_scores_correct(
        self, corpus_2_1, tmp_path
    ) -> None:
        path = write_direct_capture(tmp_path / "d.json", corpus_2_1)
        result = evaluate_direct_for_model(
            corpus_2_1, load_direct_capture(path), *primary_route()
        )
        for case_id in ("V2Q-SSD-U4-THIN-0015", "V2Q-SSD-UNPROVEN-FORM-0043",
                        "V2Q-DIMM-U2N-THIN-0009"):
            o = _outcome(result, case_id)
            assert o.verdict in ("CORRECT", "DEFENSIBLE"), case_id
            assert o.model_decision == "UNCERTAIN", case_id

    def test_the_in_set_match_pole_stays_defensible(
        self, corpus_2_1, tmp_path
    ) -> None:
        # 0043 (AMBIGUOUS {MATCH, UNCERTAIN}): a MATCH answer is inside
        # the label's acceptable set (R13/R15 - neither direction is a
        # failure), and it grants no authority.
        path = write_direct_capture(
            tmp_path / "d.json",
            corpus_2_1,
            decisions={"V2Q-SSD-UNPROVEN-FORM-0043": "MATCH"},
        )
        result = evaluate_direct_for_model(
            corpus_2_1, load_direct_capture(path), *primary_route()
        )
        o = _outcome(result, "V2Q-SSD-UNPROVEN-FORM-0043")
        assert o.verdict == "DEFENSIBLE"
        assert o.severity is None


# ===========================================================================
# Task item 8d. Near-miss identifiers (U5)
# ===========================================================================


class TestNearMissIdentifiers:
    def test_a_match_on_the_alias_sales_unit_safety_case_is_critical(
        self, corpus_2_1, tmp_path
    ) -> None:
        # 0018 (the motivating Micron pair: …YYR vs …YY,
        # customer-retrieval-only, the R/T suffix may carry the
        # packaging question) and 0022 (the synthetic alias twin): a
        # MATCH is the CRITICAL false MATCH in the sales-unit-safety
        # metric.
        path = write_direct_capture(
            tmp_path / "d.json",
            corpus_2_1,
            decisions={
                "V2Q-SSD-U5NM1-MICRON-0018": "MATCH",
                "V2Q-SSD-U5NM1-ALIAS-0022": "MATCH",
            },
        )
        result = evaluate_direct_for_model(
            corpus_2_1, load_direct_capture(path), *primary_route()
        )
        for case_id in ("V2Q-SSD-U5NM1-MICRON-0018", "V2Q-SSD-U5NM1-ALIAS-0022"):
            o = _outcome(result, case_id)
            assert o.verdict == "FALSE_MATCH"
            assert o.severity == "CRITICAL"
        assert result.metrics["sales_unit_safety_false_match_count"] == 2
        assert result.metrics["near_miss_false_match_count"] == 2

    def test_the_customer_retrieval_alias_confers_zero_authority(
        self, corpus_2_1, tmp_path
    ) -> None:
        # The alias makes the variant question concrete while conferring
        # ZERO equivalence authority: the identity-resolution bound of
        # the recorded context is NONE (a MATCH on this bound is the
        # CRITICAL false-MATCH shape), and an unauthorized
        # MATCH_AUTHORIZED_IDENTIFIER_RELATION claim is flagged.
        case = corpus_2_1.case("V2Q-SSD-U5NM1-MICRON-0018")
        typed = case.build_semantic_case()
        assert fu3.derive_identity_resolution_bound(
            _assessment(typed), typed.context_provenances
        ) is fu3.IdentityResolutionBoundV2.NONE

        path = write_direct_capture(
            tmp_path / "d.json",
            corpus_2_1,
            raw_overrides={
                "V2Q-SSD-U5NM1-MICRON-0018": make_response(
                    "MATCH",
                    reason_code="MATCH_AUTHORIZED_IDENTIFIER_RELATION",
                )
            },
        )
        result = evaluate_direct_for_model(
            corpus_2_1, load_direct_capture(path), *primary_route()
        )
        o = _outcome(result, "V2Q-SSD-U5NM1-MICRON-0018")
        assert "UNAUTHORIZED_AUTHORITY_CLAIM" in o.notes
        assert "CUSTOMER_ALIAS_PROMOTION" in o.notes
        gates = evaluate_safety_gates(result)
        assert not gates["zero_unauthorized_authority_promotion"].passed
        assert not gates["zero_customer_alias_authority_promotion"].passed

    def test_the_authority_resolved_near_miss_scores_correct(
        self, corpus_2_1, tmp_path
    ) -> None:
        # 0020: MANUFACTURER_RELATION_AUTHORITY in the input licenses
        # MATCH_AUTHORIZED_IDENTIFIER_RELATION (part-number resolution
        # for the specifically related part); the label-consistent
        # answer scores CORRECT with no unauthorized-authority note.
        path = write_direct_capture(tmp_path / "d.json", corpus_2_1)
        result = evaluate_direct_for_model(
            corpus_2_1, load_direct_capture(path), *primary_route()
        )
        o = _outcome(result, "V2Q-SSD-U5NM2-RELAUTH-0020")
        assert o.verdict == "CORRECT"
        assert o.model_reason_code == "MATCH_AUTHORIZED_IDENTIFIER_RELATION"
        assert "UNAUTHORIZED_AUTHORITY_CLAIM" not in o.notes
        # And the bound of the recorded context is PART_NUMBER (the
        # labeled authority is the ground).
        typed = corpus_2_1.case("V2Q-SSD-U5NM2-RELAUTH-0020").build_semantic_case()
        assert fu3.derive_identity_resolution_bound(
            _assessment(typed), typed.context_provenances
        ) is fu3.IdentityResolutionBoundV2.PART_NUMBER


# ===========================================================================
# Task item 8e. Internal contradictions (the 0037 flip)
# ===========================================================================


class TestInternalContradictions:
    def test_uncertain_naming_the_contradicted_dimension_scores_correct(
        self, corpus_2_1, tmp_path
    ) -> None:
        # 0037: title 3.84TB vs specification text 7.68TB - CAPACITY
        # unpinned in both directions. The 2.1 rule (approved decision
        # 7): UNCERTAIN naming the dimension; the pre-registered flip
        # from the 2.0 false NO_MATCH is CORRECT.
        path = write_direct_capture(tmp_path / "d.json", corpus_2_1)
        result = evaluate_direct_for_model(
            corpus_2_1, load_direct_capture(path), *primary_route()
        )
        o = _outcome(result, "V2Q-SSD-CONTRA-0037")
        assert o.verdict == "CORRECT"
        assert o.model_decision == "UNCERTAIN"

    def test_the_2_0_false_no_match_shape_is_detected(
        self, corpus_2_1, tmp_path
    ) -> None:
        # The 2.0-era answer (NO_MATCH on the contradiction alone) is
        # a false NO_MATCH: safe direction, REVIEW severity, never a
        # gate failure, never authority.
        path = write_direct_capture(
            tmp_path / "d.json",
            corpus_2_1,
            decisions={"V2Q-SSD-CONTRA-0037": "NO_MATCH"},
        )
        result = evaluate_direct_for_model(
            corpus_2_1, load_direct_capture(path), *primary_route()
        )
        o = _outcome(result, "V2Q-SSD-CONTRA-0037")
        assert o.verdict == "FALSE_NO_MATCH"
        assert o.severity == "REVIEW"
        gates = evaluate_safety_gates(result)
        assert all(g.passed for g in gates.values())


# ===========================================================================
# Task item 8f. Old-version replay isolation (scoring is binding-agnostic;
# the identity is not)
# ===========================================================================


class TestOldVersionReplayIsolation:
    def test_identical_responses_score_identically_on_both_versions(
        self, corpus_2_0, corpus_2_1, tmp_path
    ) -> None:
        # The re-seal moved the binding, not the truth: the same
        # scripted responses (label-consistent fixtures) produce
        # identical per-case verdicts on the 1.0.0 and the 1.1.0
        # corpus.
        decisions = {
            "V2Q-SSD-U5NM1-MICRON-0018": "MATCH",
            "V2Q-SSD-SU-TRAY-0032": "MATCH",
            "V2Q-SSD-CONTRA-0037": "NO_MATCH",
            "V2Q-SSD-U4-THIN-0015": "MATCH",
        }
        r10 = evaluate_direct_for_model(
            corpus_2_0,
            load_direct_capture(
                write_direct_capture(tmp_path / "a.json", corpus_2_0,
                                     decisions=decisions)
            ),
            *primary_route(),
        )
        r11 = evaluate_direct_for_model(
            corpus_2_1,
            load_direct_capture(
                write_direct_capture(tmp_path / "b.json", corpus_2_1,
                                     decisions=decisions)
            ),
            *primary_route(),
        )
        v10 = {
            o.case_id: (o.state, o.verdict, o.severity, o.model_decision)
            for o in r10.outcomes
        }
        v11 = {
            o.case_id: (o.state, o.verdict, o.severity, o.model_decision)
            for o in r11.outcomes
        }
        assert v10 == v11
        # But the record identities differ (the binding is the report's
        # contract identity, never the scoring input).
        assert r10.semantic_contract_binding != r11.semantic_contract_binding
        assert r10.corpus_digest != r11.corpus_digest

    def test_the_offline_2_1_pipeline_makes_no_network_call(
        self, corpus_2_1, tmp_path, monkeypatch
    ) -> None:
        def refuse(*args, **kwargs):
            raise AssertionError("offline replay must not use the network")

        monkeypatch.setattr(socket, "socket", refuse)
        monkeypatch.setattr(socket, "create_connection", refuse)
        monkeypatch.setattr(socket, "getaddrinfo", refuse)
        path = write_direct_capture(tmp_path / "d.json", corpus_2_1)
        result = evaluate_direct_for_model(
            corpus_2_1, load_direct_capture(path), *primary_route()
        )
        policy = load_policy(POLICY_PATH)
        decision, _rationale, _gates = _decide(corpus_2_1, result, policy)
        assert decision == "POLICY_PENDING"
        assert result.metrics["counts"]["evaluated_cases"] == 43
