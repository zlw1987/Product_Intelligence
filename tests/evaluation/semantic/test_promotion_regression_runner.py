"""Promotion-regression runner tests (PRODUCT-INTEL.SEMANTIC.PROMOTION-REGRESSION).

Offline tests for the harness runner with fake transports:

* the frozen eligibility boundary is respected exactly (zero transport
  calls on deterministic ACCEPTED / MPN conflict / no usable evidence;
  exactly one call per eligible case, never more - no retry, no fallback);
* the strict response contract is enforced (prose, fences, unknown keys,
  missing keys, invalid enums, wrong item types, model-identity drift);
* the disposition mapping preserves the frozen execution semantics
  (MATCH -> AI_ASSISTED_MATCH only; NO_MATCH / UNCERTAIN -> no authority);
* the promotion gates are objective facts and fail the right things;
* artifacts save/load with fail-closed integrity verification.

No live network/model calls. No production files modified.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from product_intelligence.evaluation.semantic.promotion_regression import (
    AUTHORITY_OUTCOME_AI_ASSISTED_MATCH_ONLY,
    AUTHORITY_OUTCOME_DETERMINISTIC_ACCEPTED,
    AUTHORITY_OUTCOME_DETERMINISTIC_REJECTED_MPN_CONFLICT,
    AUTHORITY_OUTCOME_DETERMINISTIC_REJECTED_NO_SEMANTIC,
    AUTHORITY_OUTCOME_NO_SEMANTIC_AUTHORITY,
    PROMOTION_REGRESSION_TEMPERATURE,
    PROMOTION_REGRESSION_MAX_TOKENS,
    PromotionRegressionCaseError,
    PromotionRegressionModelAuthorizationError,
    PromotionRegressionError,
    _build_case_prompt,
    _compute_corpus_sha256,
    _compute_prompt_sha256,
    build_case_inputs,
    assess_case,
    get_authorized_model_spec,
    load_promotion_regression_corpus,
    load_run,
    run_promotion_regression,
    save_run,
)
from product_intelligence.semantic.contract import SEMANTIC_PROMPT_VERSION
from product_intelligence.semantic.runtime import SemanticAttemptStatus
from product_intelligence.semantic.transport import (
    FakeSemanticModelTransport,
    TransportFailure,
    TransportResult,
)

NEOTRON_SPEC = get_authorized_model_spec("amax", "nemotron-3-super")
QWEN_SPEC = get_authorized_model_spec("amax", "qwen3.8-27b")

CORPUS = load_promotion_regression_corpus()
CALLED_IDS = tuple(c.case_id for c in CORPUS.cases if c.expected_semantic_call)
NO_CALL_IDS = tuple(c.case_id for c in CORPUS.cases if not c.expected_semantic_call)
assert len(CALLED_IDS) == 16 and len(NO_CALL_IDS) == 6


def _response(
    decision: str,
    confidence: str = "HIGH",
    matched: list | None = None,
    conflicting: list | None = None,
    missing: list | None = None,
    reason: str = "test_reason",
    raw_override: str | None = None,
) -> str:
    if raw_override is not None:
        return raw_override
    payload = {
        "decision": decision,
        "confidence": confidence,
        "matched_attributes": matched if matched is not None else [],
        "conflicting_attributes": conflicting if conflicting is not None else [],
        "missing_critical_attributes": missing if missing is not None else [],
        "reason_code": reason,
    }
    return json.dumps(payload)


def _ideal_responses(model: str) -> dict[str, str]:
    """The corpus-expected decision for every called case (an ideal model)."""
    responses = {}
    for case in CORPUS.cases:
        if case.expected_semantic_call:
            responses[case.case_id] = _response(case.expected_semantic_decision)
    return responses


def _fake(model: str, responses: dict[str, str], **kwargs) -> FakeSemanticModelTransport:
    return FakeSemanticModelTransport(
        case_ids=CALLED_IDS,
        responses=responses,
        provider_reported_model=model,
        **kwargs,
    )


def _run(spec, responses=None, **kwargs):
    model = spec.model
    if responses is None:
        responses = _ideal_responses(model)
    transport = _fake(model, responses, **kwargs)
    run = run_promotion_regression(spec, transport)
    return run, transport


def _gate(run, name: str):
    for g in run.gates:
        if g.name == name:
            return g
    raise AssertionError(f"gate {name} missing")


def _record(run, case_id: str):
    return next(r for r in run.records if r.case_id == case_id)


# ---------------------------------------------------------------------------
# Eligibility boundary: zero calls where forbidden, exactly one where allowed
# ---------------------------------------------------------------------------


class TestEligibilityBoundary:
    def test_exactly_one_call_per_eligible_case(self):
        run, transport = _run(NEOTRON_SPEC)
        assert transport.call_count == len(CALLED_IDS)
        for cid in CALLED_IDS:
            assert _record(run, cid).semantic_call_made is True
        for cid in NO_CALL_IDS:
            assert _record(run, cid).semantic_call_made is False

    def test_deterministic_accepted_never_consulted(self):
        run, _ = _run(NEOTRON_SPEC)
        for cid in ("SPR-0001", "SPR-0002"):
            r = _record(run, cid)
            assert r.deterministic_decision == "ACCEPTED"
            assert r.transport_status is None
            assert r.raw_output is None
            assert r.decision is None
            assert r.disposition is None
            assert r.observed_authority_outcome == AUTHORITY_OUTCOME_DETERMINISTIC_ACCEPTED
            assert r.authority_outcome_match is True

    def test_mpn_conflict_never_consulted_and_never_overturned(self):
        run, _ = _run(NEOTRON_SPEC)
        for cid in ("SPR-0003", "SPR-0004"):
            r = _record(run, cid)
            assert r.deterministic_decision == "REJECTED"
            assert r.deterministic_rejection_reason == "MPN_MISMATCH"
            assert r.transport_status is None
            assert r.decision is None
            assert r.disposition is None
            assert r.observed_authority_outcome == (
                AUTHORITY_OUTCOME_DETERMINISTIC_REJECTED_MPN_CONFLICT
            )
            # The candidate can NEVER become AI_ASSISTED_MATCH: no model is
            # consulted, so no model decision exists to create authority.
            assert r.observed_authority_outcome != AUTHORITY_OUTCOME_AI_ASSISTED_MATCH_ONLY

    def test_no_usable_evidence_never_consulted(self):
        run, _ = _run(NEOTRON_SPEC)
        for cid in ("SPR-0011", "SPR-0012"):
            r = _record(run, cid)
            assert r.transport_status is None
            assert r.decision is None
            assert r.disposition is None
            assert r.observed_authority_outcome == (
                AUTHORITY_OUTCOME_DETERMINISTIC_REJECTED_NO_SEMANTIC
            )

    def test_partial_mpn_cases_are_consulted_and_stay_ai_assisted(self):
        run, _ = _run(NEOTRON_SPEC)
        for cid in ("SPR-0009", "SPR-0010"):
            r = _record(run, cid)
            assert r.deterministic_rejection_reason == "PARTIAL_MPN_ONLY"
            assert r.semantic_call_made is True
            assert r.decision == "UNCERTAIN"
            assert r.disposition == "UNDECIDED"
            assert r.observed_authority_outcome == AUTHORITY_OUTCOME_NO_SEMANTIC_AUTHORITY

    def test_all_cases_realize_declared_deterministic_states(self):
        run, _ = _run(NEOTRON_SPEC)
        for case in CORPUS.cases:
            r = _record(run, case.case_id)
            e = case.expected_deterministic
            assert r.deterministic_decision == e.decision
            assert r.deterministic_rejection_reason == e.rejection_reason
            assert r.deterministic_evidence_source == e.evidence_source
            assert r.deterministic_match_type == e.match_type


# ---------------------------------------------------------------------------
# Disposition mapping and authority outcomes
# ---------------------------------------------------------------------------


class TestDispositionMapping:
    def test_match_maps_to_ai_assisted_match_only(self):
        run, _ = _run(NEOTRON_SPEC)
        match_records = [r for r in run.records if r.decision == "MATCH"]
        assert len(match_records) == 5  # corpus expected-MATCH cases
        for r in match_records:
            assert r.disposition == "AI_ASSISTED_MATCH"
            assert r.observed_authority_outcome == AUTHORITY_OUTCOME_AI_ASSISTED_MATCH_ONLY
            assert r.authority_outcome_match is True
            # Deterministic state stays REJECTED: MATCH never becomes
            # deterministic ACCEPTED.
            assert r.deterministic_decision == "REJECTED"

    def test_no_match_and_uncertain_create_no_authority(self):
        run, _ = _run(NEOTRON_SPEC)
        for r in run.records:
            if r.decision in ("NO_MATCH", "UNCERTAIN"):
                assert r.disposition == "UNDECIDED"
                assert r.observed_authority_outcome == AUTHORITY_OUTCOME_NO_SEMANTIC_AUTHORITY
                assert r.deterministic_decision == "REJECTED"
            if r.decision is None:
                assert r.disposition is None


# ---------------------------------------------------------------------------
# Strict response contract: invalid first response is recorded, never retried
# ---------------------------------------------------------------------------


class TestStrictResponseContract:
    @pytest.mark.parametrize(
        "raw",
        [
            "Sure! Here is the answer:\n"
            '{"decision": "MATCH", "confidence": "HIGH", '
            '"matched_attributes": [], "conflicting_attributes": [], '
            '"missing_critical_attributes": [], "reason_code": "x"}',
            "```json\n"
            '{"decision": "MATCH", "confidence": "HIGH", '
            '"matched_attributes": [], "conflicting_attributes": [], '
            '"missing_critical_attributes": [], "reason_code": "x"}\n```',
            '{"decision": "MAYBE", "confidence": "HIGH", '
            '"matched_attributes": [], "conflicting_attributes": [], '
            '"missing_critical_attributes": [], "reason_code": "x"}',
            '{"decision": "MATCH", "confidence": "CERTAIN", '
            '"matched_attributes": [], "conflicting_attributes": [], '
            '"missing_critical_attributes": [], "reason_code": "x"}',
            '{"decision": "MATCH", "confidence": "HIGH", '
            '"matched_attributes": [], "conflicting_attributes": [], '
            '"missing_critical_attributes": []}',  # missing reason_code
            '{"decision": "MATCH", "confidence": "HIGH", '
            '"matched_attributes": [], "conflicting_attributes": [], '
            '"missing_critical_attributes": [], "reason_code": "x", '
            '"notes": "extra prose"}',  # unknown key
            "[\"MATCH\"]",  # JSON array
            "not json at all",
            "",  # empty
            "   ",  # whitespace only
        ],
    )
    def test_invalid_output_is_recorded_invalid_and_not_retried(self, raw: str):
        responses = _ideal_responses(NEOTRON_SPEC.model)
        responses["SPR-0005"] = raw
        run, transport = _run(NEOTRON_SPEC, responses)
        r = _record(run, "SPR-0005")
        assert r.semantic_call_made is True
        assert r.valid_response is False
        assert r.decision is None
        assert r.disposition is None
        assert r.observed_authority_outcome == AUTHORITY_OUTCOME_NO_SEMANTIC_AUTHORITY
        assert r.transport_status in (
            SemanticAttemptStatus.MALFORMED_JSON.value,
            SemanticAttemptStatus.EMPTY_RESPONSE.value,
        )
        # No retry: still exactly one call per eligible case.
        assert transport.call_count == len(CALLED_IDS)
        # The invalid output fails the run's gate.
        assert _gate(run, "all_semantic_calls_valid").passed is False
        assert run.promotion_gate_passed is False

    def test_schema_invalid_attribute_item_type(self):
        responses = _ideal_responses(NEOTRON_SPEC.model)
        responses["SPR-0005"] = _response(
            "MATCH", matched=[123]
        )  # parse accepts a list; schema validator rejects non-str items
        run, _ = _run(NEOTRON_SPEC, responses)
        r = _record(run, "SPR-0005")
        assert r.valid_response is False
        assert r.transport_status == SemanticAttemptStatus.SCHEMA_INVALID.value

    def test_invalid_output_preserved_raw(self):
        raw = "prose before\n{\"decision\": \"MATCH\", \"confidence\": \"HIGH\", "
        raw += "\"matched_attributes\": [], \"conflicting_attributes\": [], "
        raw += "\"missing_critical_attributes\": [], \"reason_code\": \"x\"}"
        responses = _ideal_responses(NEOTRON_SPEC.model)
        responses["SPR-0005"] = raw
        run, _ = _run(NEOTRON_SPEC, responses)
        assert _record(run, "SPR-0005").raw_output == raw

    def test_valid_output_preserved_raw_exactly(self):
        run, _ = _run(NEOTRON_SPEC)
        r = _record(run, "SPR-0005")
        expected = _response("MATCH")
        assert r.raw_output == expected


# ---------------------------------------------------------------------------
# Model identity and transport failures
# ---------------------------------------------------------------------------


class TestModelIdentityAndTransportFailures:
    def test_identity_mismatch_is_recorded_and_run_fatal(self):
        responses = _ideal_responses(QWEN_SPEC.model)
        transport = FakeSemanticModelTransport(
            case_ids=CALLED_IDS,
            responses=responses,
            provider_reported_model="some-other-model",
        )
        run = run_promotion_regression(NEOTRON_SPEC, transport)
        # NEOTRON spec vs reported other-model: the first called case fails
        # identity and the run aborts (run-fatal, mirroring qualification).
        first = _record(run, CALLED_IDS[0])
        assert first.transport_status == SemanticAttemptStatus.MODEL_IDENTITY_MISMATCH.value
        assert first.model_identity_proven is False
        assert first.valid_response is False
        assert run.run_status == "FAILED_CONFIGURATION"
        assert transport.call_count == 1
        assert _gate(run, "all_semantic_calls_valid").passed is False
        assert run.promotion_gate_passed is False

    def test_identity_none_is_mismatch(self):
        responses = _ideal_responses(NEOTRON_SPEC.model)
        transport = FakeSemanticModelTransport(
            case_ids=CALLED_IDS,
            responses=responses,
            provider_reported_model=None,
        )
        run = run_promotion_regression(NEOTRON_SPEC, transport)
        first = _record(run, CALLED_IDS[0])
        assert first.transport_status == SemanticAttemptStatus.MODEL_IDENTITY_MISMATCH.value
        assert run.run_status == "FAILED_CONFIGURATION"

    def test_transport_failure_is_case_local_and_run_continues(self):
        responses = _ideal_responses(NEOTRON_SPEC.model)
        transport = _fake(
            NEOTRON_SPEC.model,
            responses,
            failure_error_types={"SPR-0007": "TIMEOUT"},
        )
        run = run_promotion_regression(NEOTRON_SPEC, transport)
        r = _record(run, "SPR-0007")
        assert r.semantic_call_made is True
        assert r.transport_status == SemanticAttemptStatus.TIMEOUT.value
        assert r.transport_error_type == "TIMEOUT"
        assert r.valid_response is False
        assert r.decision is None
        assert run.run_status == "COMPLETED"  # TIMEOUT is case-local
        assert transport.call_count == len(CALLED_IDS)
        assert _gate(run, "all_semantic_calls_valid").passed is False

    @pytest.mark.parametrize(
        "error_type,run_status",
        [
            ("PROVIDER_UNAVAILABLE", "FAILED_PROVIDER"),
            ("RATE_LIMITED", "FAILED_PROVIDER"),
            ("AUTHENTICATION_FAILED", "FAILED_CONFIGURATION"),
            ("MODEL_NOT_FOUND", "FAILED_CONFIGURATION"),
        ],
    )
    def test_run_fatal_transport_error_aborts(self, error_type, run_status):
        responses = _ideal_responses(NEOTRON_SPEC.model)
        transport = _fake(
            NEOTRON_SPEC.model, responses, failure_error_types={"SPR-0007": error_type}
        )
        run = run_promotion_regression(NEOTRON_SPEC, transport)
        assert run.run_status == run_status
        # Abort after the failed case: later cases are never attempted.
        failed_index = CALLED_IDS.index("SPR-0007")
        assert transport.call_count == failed_index + 1
        assert _gate(run, "all_semantic_calls_valid").passed is False
        assert run.promotion_gate_passed is False

    def test_case_rejected_is_case_local(self):
        responses = _ideal_responses(NEOTRON_SPEC.model)
        transport = _fake(
            NEOTRON_SPEC.model,
            responses,
            failure_error_types={"SPR-0007": "CASE_REJECTED"},
        )
        run = run_promotion_regression(NEOTRON_SPEC, transport)
        assert run.run_status == "COMPLETED"
        r = _record(run, "SPR-0007")
        assert r.transport_status == SemanticAttemptStatus.CASE_REJECTED.value
        assert r.valid_response is False


# ---------------------------------------------------------------------------
# Unsafe MATCH gating
# ---------------------------------------------------------------------------


class TestUnsafeMatchGates:
    def test_ideal_run_passes_all_gates(self):
        for spec in (NEOTRON_SPEC, QWEN_SPEC):
            run, _ = _run(spec)
            assert run.run_status == "COMPLETED"
            for gate in run.gates:
                assert gate.passed is True, f"{spec.model}: {gate.name} {gate.detail}"
            assert run.promotion_gate_passed is True

    def test_match_on_unsafe_case_fails_gate(self):
        # SPR-0013: accessory trap, expected NO_MATCH, match_is_unsafe.
        responses = _ideal_responses(QWEN_SPEC.model)
        responses["SPR-0013"] = _response("MATCH")
        run, _ = _run(QWEN_SPEC, responses)
        r = _record(run, "SPR-0013")
        assert r.decision == "MATCH"
        assert r.unsafe_match is True
        assert r.false_match is True
        assert r.observed_authority_outcome == AUTHORITY_OUTCOME_AI_ASSISTED_MATCH_ONLY
        assert r.authority_outcome_match is False
        assert _gate(run, "no_unsafe_match").passed is False
        assert _gate(run, "no_unsafe_match").detail == "MATCH on unsafe case(s): SPR-0013"
        assert run.promotion_gate_passed is False

    def test_match_on_expected_uncertain_is_false_match_not_unsafe(self):
        # SPR-0008: expected UNCERTAIN, match_is_unsafe=False.
        responses = _ideal_responses(QWEN_SPEC.model)
        responses["SPR-0008"] = _response("MATCH")
        run, _ = _run(QWEN_SPEC, responses)
        r = _record(run, "SPR-0008")
        assert r.unsafe_match is False
        assert r.false_match is True
        # The no-unsafe-match gate still passes; the false match is a
        # surfaced model-quality fact, not a hard safety gate.
        assert _gate(run, "no_unsafe_match").passed is True
        assert r.decision_matches_expected is False

    def test_no_match_on_expected_match_is_false_negative_not_false_match(self):
        responses = _ideal_responses(QWEN_SPEC.model)
        responses["SPR-0005"] = _response("NO_MATCH")
        run, _ = _run(QWEN_SPEC, responses)
        r = _record(run, "SPR-0005")
        assert r.false_match is False
        assert r.unsafe_match is False
        assert r.decision_matches_expected is False
        assert _gate(run, "no_unsafe_match").passed is True

    def test_gate_names_are_complete(self):
        run, _ = _run(NEOTRON_SPEC)
        names = [g.name for g in run.gates]
        assert names == [
            "deterministic_states_verified",
            "no_semantic_override_of_deterministic_authority",
            "all_semantic_calls_valid",
            "no_unsafe_match",
            "ai_assisted_authority_boundary",
            "provenance_integrity",
        ]


# ---------------------------------------------------------------------------
# Authorization and configuration
# ---------------------------------------------------------------------------


class TestAuthorization:
    def test_fallback_model_is_not_authorized_for_harness(self):
        with pytest.raises(PromotionRegressionModelAuthorizationError):
            get_authorized_model_spec("vllm-262k", "Qwen3.6-27B-262K")

    def test_unknown_model_is_not_authorized(self):
        with pytest.raises(PromotionRegressionModelAuthorizationError):
            get_authorized_model_spec("amax", "not-a-real-model")

    def test_unauthorized_spec_rejected_by_runner(self):
        from product_intelligence.evaluation.semantic.promotion_regression import (
            PromotionRegressionModelSpec,
        )

        rogue = PromotionRegressionModelSpec(
            provider="amax", model="qwen3.6-27b", role="challenger"
        )
        with pytest.raises(PromotionRegressionModelAuthorizationError):
            run_promotion_regression(rogue, FakeSemanticModelTransport())

    @pytest.mark.parametrize(
        "bad", [0, -1, float("nan"), float("inf"), float("-inf"), True, False, "300"]
    )
    def test_invalid_timeout_rejected(self, bad):
        with pytest.raises(PromotionRegressionError):
            run_promotion_regression(
                NEOTRON_SPEC,
                FakeSemanticModelTransport(),
                request_timeout_seconds=bad,  # type: ignore[arg-type]
            )

    def test_defective_case_aborts_run(self):
        with pytest.raises(PromotionRegressionCaseError):
            run_promotion_regression(
                NEOTRON_SPEC,
                FakeSemanticModelTransport(),
                corpus=_mutate_case_state(),
            )


def _mutate_case_state():
    from product_intelligence.evaluation.semantic.promotion_regression import (
        PromotionRegressionCase,
        PromotionRegressionCorpus,
        PromotionRegressionExpectedDeterministic,
    )

    cases = []
    for case in CORPUS.cases:
        if case.case_id == "SPR-0001":
            case = dataclasses.replace(
                case,
                expected_deterministic=PromotionRegressionExpectedDeterministic(
                    decision="REJECTED",
                    rejection_reason="MPN_MISMATCH",
                    evidence_source="EXPLICIT_MPN_FIELD",
                    match_type="UNKNOWN",
                ),
            )
        cases.append(case)
    return PromotionRegressionCorpus(corpus_version=1, cases=tuple(cases))


# ---------------------------------------------------------------------------
# Manifest provenance
# ---------------------------------------------------------------------------


class TestManifestProvenance:
    def test_manifest_fingerprints_and_settings(self):
        run, _ = _run(NEOTRON_SPEC)
        m = run.manifest
        assert m["benchmark_kind"] == "semantic_promotion_regression"
        assert m["corpus_sha256"] == _compute_corpus_sha256()
        assert m["prompt_version"] == SEMANTIC_PROMPT_VERSION
        assert m["provider"] == "amax"
        assert m["model"] == "nemotron-3-super"
        assert m["role"] == "production_primary"
        assert m["requested_provider"] == "amax"
        assert m["requested_model"] == "nemotron-3-super"
        assert m["generation_parameters"] == {
            "temperature": PROMOTION_REGRESSION_TEMPERATURE,
            "max_tokens": PROMOTION_REGRESSION_MAX_TOKENS,
        }
        assert type(m["generation_parameters"]["temperature"]) is float
        assert m["transport_parameters"]["request_timeout_seconds"] == 300.0
        assert m["case_count"] == 22
        assert m["called_case_count"] == 16
        assert m["run_status"] == "COMPLETED"
        assert m["no_winner_declared"] is True
        # git_head is recorded when git is available; a silent None is the
        # bounded fallback (same contract as the qualification runner).
        gh = m["git_head"]
        assert gh is None or (isinstance(gh, str) and len(gh) == 40)
        # Prompt fingerprint covers exactly the called cases, in order.
        real_entries = []
        for case in CORPUS.cases:
            if not case.expected_semantic_call:
                continue
            prompt = _build_case_prompt(case, assess_case(case))
            real_entries.append(
                {
                    "case_id": case.case_id,
                    "system_prompt": prompt.system_prompt,
                    "user_prompt": prompt.user_prompt,
                }
            )
        assert len(real_entries) == 16
        assert [e["case_id"] for e in real_entries] == list(CALLED_IDS)
        assert m["prompt_sha256"] == _compute_prompt_sha256(real_entries)

    def test_prompt_uses_frozen_contract_text(self):
        from product_intelligence.semantic import contract

        case = CORPUS.get_case("SPR-0013")
        prompt = _build_case_prompt(case, assess_case(case))
        assert prompt.system_prompt is contract.SYSTEM_PROMPT
        assert prompt.version == contract.SEMANTIC_PROMPT_VERSION

    def test_record_carries_bounded_provenance_only(self):
        run, _ = _run(NEOTRON_SPEC)
        blob = json.dumps([r.to_dict() for r in run.records])
        # No credentials, no exception text sentinels.
        assert "api_key" not in blob
        assert "SECRET" not in blob


# ---------------------------------------------------------------------------
# Artifacts: save / load round trip with fail-closed integrity
# ---------------------------------------------------------------------------


class TestArtifacts:
    def test_save_and_load_roundtrip(self, tmp_path: Path):
        run, _ = _run(QWEN_SPEC)
        run_dir = save_run(run, output_dir=tmp_path)
        assert (run_dir / "manifest.json").exists()
        assert (run_dir / "results.jsonl").exists()
        assert (run_dir / "summary.md").exists()

        loaded = load_run(run_dir)
        assert loaded.spec == QWEN_SPEC
        assert [r.case_id for r in loaded.records] == [r.case_id for r in run.records]
        for a, b in zip(loaded.records, run.records):
            assert a.to_dict() == b.to_dict()
        assert loaded.manifest == run.manifest
        assert loaded.promotion_gate_passed is run.promotion_gate_passed

    def test_load_detects_manifest_gate_tampering(self, tmp_path: Path):
        run, _ = _run(NEOTRON_SPEC)
        run_dir = save_run(run, output_dir=tmp_path)
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        manifest["gates"]["no_unsafe_match"] = False
        manifest["promotion_gate_passed"] = False
        (run_dir / "manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        from product_intelligence.evaluation.semantic.promotion_regression import (
            PromotionRegressionComparisonError,
        )

        with pytest.raises(PromotionRegressionComparisonError, match="GATE_RECORD_MISMATCH"):
            load_run(run_dir)

    def test_load_detects_corpus_tampering(self, tmp_path: Path):
        run, _ = _run(NEOTRON_SPEC)
        run_dir = save_run(run, output_dir=tmp_path)
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        manifest["corpus_sha256"] = "0" * 64
        (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        from product_intelligence.evaluation.semantic.promotion_regression import (
            PromotionRegressionComparisonError,
        )

        with pytest.raises(
            PromotionRegressionComparisonError, match="CORPUS_SHA256_MISMATCH"
        ):
            load_run(run_dir)

    def test_load_detects_missing_field(self, tmp_path: Path):
        run, _ = _run(NEOTRON_SPEC)
        run_dir = save_run(run, output_dir=tmp_path)
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        del manifest["prompt_sha256"]
        (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        from product_intelligence.evaluation.semantic.promotion_regression import (
            PromotionRegressionComparisonError,
        )

        with pytest.raises(
            PromotionRegressionComparisonError, match="MISSING_REQUIRED_FIELD"
        ):
            load_run(run_dir)

    def test_load_detects_record_count_mismatch(self, tmp_path: Path):
        run, _ = _run(NEOTRON_SPEC)
        run_dir = save_run(run, output_dir=tmp_path)
        lines = (run_dir / "results.jsonl").read_text(encoding="utf-8").strip().splitlines()
        (run_dir / "results.jsonl").write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
        from product_intelligence.evaluation.semantic.promotion_regression import (
            PromotionRegressionComparisonError,
        )

        with pytest.raises(
            PromotionRegressionComparisonError, match="CASE_COUNT_MISMATCH"
        ):
            load_run(run_dir)

    def test_summary_lists_gates_and_per_case_facts(self, tmp_path: Path):
        responses = _ideal_responses(QWEN_SPEC.model)
        responses["SPR-0013"] = _response("MATCH")  # unsafe match
        run, _ = _run(QWEN_SPEC, responses)
        run_dir = save_run(run, output_dir=tmp_path)
        summary = (run_dir / "summary.md").read_text(encoding="utf-8")
        assert "**no_unsafe_match**: FAIL" in summary
        assert "Promotion gate: FAIL" in summary
        assert "SPR-0013" in summary
        assert "UNSAFE_MATCH" in summary
        assert "no winner" in summary.lower()
