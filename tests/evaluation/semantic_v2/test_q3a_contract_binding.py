"""Q3-A contract-binding and production-fidelity tests.

Mandated properties 9-12 (unknown semantic contract fails closed;
prompt version mismatch fails closed; production prompt fidelity;
production parser fidelity) plus the contract-negative surface and the
capture-binding attacks.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from tests.evaluation.semantic_v2._q3a_helpers import (
    load_corpus_bundle,
    make_response,
    primary_route,
    write_capture,
)
from product_intelligence.evaluation.semantic_v2.capture import (
    CaptureError,
    CaptureIntegrityError,
    load_capture,
)
from product_intelligence.evaluation.semantic_v2.corpus import (
    CorpusIntegrityError,
    load_corpus,
)
from product_intelligence.evaluation.semantic_v2.evaluator import (
    classify_raw_response,
    evaluate_for_model,
    QualificationContractError,
)
from product_intelligence.research import V2_CONTRACT_BINDING
from product_intelligence.semantic.contract_v2 import (
    SEMANTIC_PROMPT_VERSION_V2,
    SYSTEM_PROMPT_V2,
    build_semantic_prompt_v2,
)
from product_intelligence.research.semantic_v2 import (
    parse_semantic_response_v2,
    validate_semantic_response_v2,
)


@pytest.fixture(scope="module")
def corpus():
    return load_corpus_bundle()


def _write(tmp_path: Path, doc: dict, name: str = "corpus.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


# ===========================================================================
# 9. Unknown semantic contract fails closed
# ===========================================================================


class TestUnknownSemanticContract:
    def test_a_corpus_bound_to_a_foreign_contract_fails_closed(
        self, corpus, tmp_path
    ) -> None:
        doc = deepcopy(corpus.document)
        doc["semantic_contract_binding"] = [
            "V3", "2.0", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU2",
        ]
        with pytest.raises(CorpusIntegrityError, match="binding"):
            load_corpus(_write(tmp_path, doc))

    def test_a_corpus_bound_to_the_v1_contract_fails_closed(
        self, corpus, tmp_path
    ) -> None:
        doc = deepcopy(corpus.document)
        doc["semantic_contract_binding"] = [
            "V1", "1.1", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU2",
        ]
        with pytest.raises(CorpusIntegrityError):
            load_corpus(_write(tmp_path, doc))

    def test_a_capture_named_for_a_foreign_contract_fails_closed(
        self, corpus, tmp_path
    ) -> None:
        path = write_capture(tmp_path / "c.json", corpus)
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        doc["semantic_contract"] = "V9"
        Path(path).write_text(json.dumps(doc), encoding="utf-8")
        with pytest.raises(CaptureIntegrityError, match="semantic_contract"):
            load_capture(path)

    def test_the_corpus_binds_to_the_frozen_production_binding(self, corpus):
        assert list(corpus.semantic_contract_binding) == list(
            V2_CONTRACT_BINDING
        )
        assert corpus.semantic_contract_binding[0] == "V2"
        assert corpus.semantic_contract_binding[1] == "2.0"


# ===========================================================================
# 10. Prompt version mismatch fails closed
# ===========================================================================


class TestPromptVersionMismatch:
    def test_a_capture_named_for_prompt_1_1_fails_closed(
        self, corpus, tmp_path
    ) -> None:
        path = write_capture(tmp_path / "c.json", corpus)
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        doc["prompt_version"] = "1.1"
        Path(path).write_text(json.dumps(doc), encoding="utf-8")
        with pytest.raises(CaptureIntegrityError, match="prompt_version"):
            load_capture(path)

    def test_a_capture_named_for_a_future_prompt_fails_closed(
        self, corpus, tmp_path
    ) -> None:
        path = write_capture(tmp_path / "c.json", corpus)
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        doc["prompt_version"] = "2.1"
        Path(path).write_text(json.dumps(doc), encoding="utf-8")
        with pytest.raises(CaptureIntegrityError):
            load_capture(path)

    def test_a_corpus_bound_to_a_future_prompt_fails_closed(
        self, corpus, tmp_path
    ) -> None:
        doc = deepcopy(corpus.document)
        doc["semantic_contract_binding"] = ["V2", "2.1", 1, 1,
                                            "SEMANTIC_AUTHORITY_V2_S2A_FU2"]
        with pytest.raises(CorpusIntegrityError):
            load_corpus(_write(tmp_path, doc))

    def test_the_prompt_version_is_the_frozen_2_0(self) -> None:
        assert SEMANTIC_PROMPT_VERSION_V2 == "2.0"
        assert V2_CONTRACT_BINDING[1] == "2.0"


# ===========================================================================
# 11. Production prompt fidelity
# ===========================================================================


class TestProductionPromptFidelity:
    def test_the_report_binds_the_real_system_prompt_digest(self, corpus):
        from product_intelligence.evaluation.semantic_v2.canonical import (
            canonical_sha256,
        )
        from product_intelligence.evaluation.semantic_v2.evaluator import (
            evaluate_no_capture,
        )
        from product_intelligence.evaluation.semantic_v2.gates import (
            decide,
            evaluate_safety_gates,
        )
        from product_intelligence.evaluation.semantic_v2.report import (
            build_report,
        )

        result = evaluate_no_capture(
            corpus, "amax", "qwen3.8-27b"
        )
        gates = evaluate_safety_gates(result)
        decision, rationale = decide(result, gates, None, None)
        report = build_report(
            result=result,
            gates=gates,
            policy=None,
            threshold_evaluation=None,
            decision=decision,
            rationale=rationale,
            corpus=corpus,
            generated_utc="2026-10-08T00:00:00Z",
        )
        assert report["contract"]["system_prompt_digest"] == (
            canonical_sha256({"text": SYSTEM_PROMPT_V2})
        )
        assert report["contract"]["prompt_version"] == "2.0"

    def test_every_case_prompt_renders_deterministically_via_production(
        self, corpus
    ) -> None:
        for case in corpus.semantic_cases:
            typed = case.build_semantic_case()
            first = build_semantic_prompt_v2(typed)
            second = build_semantic_prompt_v2(typed)
            assert first.user_prompt == second.user_prompt
            assert first.system_prompt == SYSTEM_PROMPT_V2
            assert first.version == "2.0"
            # The rendered prompt carries the case identity.
            assert case.case_id in first.user_prompt

    def test_the_harness_never_carries_a_prompt_copy(self, corpus) -> None:
        """The harness reports prompt identity by digest of the real
        frozen text; no module in the harness package embeds the prompt
        body (a copy could drift from the frozen prompt)."""
        import product_intelligence.evaluation.semantic_v2 as package_root

        marker = (
            "You are a product commercial-equivalence evaluation assistant"
        )
        for path in Path(package_root.__path__[0]).glob("*.py"):
            text = Path(path).read_text(encoding="utf-8")
            assert marker not in text, (
                f"{path.name} embeds a copy of the frozen prompt; the "
                "harness must bind the real prompt by reference/digest"
            )


# ===========================================================================
# 12. Production parser fidelity
# ===========================================================================


class TestProductionParserFidelity:
    def test_the_classifier_composes_the_production_parser(
        self, monkeypatch
    ) -> None:
        """classify_raw_response must call the real production
        parse_semantic_response_v2 / validate_semantic_response_v2 -
        proven by sentinel wrappers (no recreated parser)."""
        import product_intelligence.evaluation.semantic_v2.evaluator as ev

        calls = {"parse": 0, "validate": 0}
        real_parse = ev.parse_semantic_response_v2
        real_validate = ev.validate_semantic_response_v2

        def spy_parse(raw):
            calls["parse"] += 1
            return real_parse(raw)

        def spy_validate(parsed):
            calls["validate"] += 1
            return real_validate(parsed)

        monkeypatch.setattr(ev, "parse_semantic_response_v2", spy_parse)
        monkeypatch.setattr(ev, "validate_semantic_response_v2", spy_validate)
        raw = make_response("MATCH")
        response, failure = ev.classify_raw_response(raw)
        assert failure is None
        assert response is not None
        assert calls["parse"] == 1
        assert calls["validate"] == 1

    def test_a_valid_response_is_the_production_validated_object(self) -> None:
        raw = make_response(
            "NO_MATCH",
            conflicting=(("CAPACITY", "3840 vs 7680"),),
            conflict_classes=("CAPACITY",),
        )
        response, failure = classify_raw_response(raw)
        assert failure is None
        direct = validate_semantic_response_v2(parse_semantic_response_v2(raw))
        assert response == direct
        assert response.decision.value == "NO_MATCH"

    def test_invalid_json_is_malformed(self) -> None:
        for raw in ("not json", "{", "[]", "", "   ", "```json{}```"):
            response, failure = classify_raw_response(raw)
            assert response is None
            assert failure == "MALFORMED_JSON", raw

    def test_unknown_response_field_is_rejected(self) -> None:
        raw = json.dumps(
            {
                "decision": "MATCH",
                "confidence": "HIGH",
                "reason_code": "MATCH_EXACT_PRODUCT_CONTEXT",
                "matched_attributes": [],
                "conflicting_attributes": [],
                "missing_critical_attributes": [],
                "conflict_classes": [],
                "chain_of_thought": "I decided this because...",
            }
        )
        response, failure = classify_raw_response(raw)
        assert response is None
        assert failure == "MALFORMED_JSON"

    def test_missing_response_field_is_rejected(self) -> None:
        raw = json.dumps(
            {
                "decision": "MATCH",
                "confidence": "HIGH",
                "reason_code": "MATCH_EXACT_PRODUCT_CONTEXT",
                "matched_attributes": [],
                "conflicting_attributes": [],
                "conflict_classes": [],
            }
        )
        response, failure = classify_raw_response(raw)
        assert response is None
        assert failure == "MALFORMED_JSON"

    def test_unknown_conflict_class_is_rejected(self) -> None:
        raw = json.dumps(
            {
                "decision": "NO_MATCH",
                "confidence": "HIGH",
                "reason_code": "NO_MATCH_OTHER",
                "matched_attributes": [],
                "conflicting_attributes": [],
                "missing_critical_attributes": [],
                "conflict_classes": ["INVENTED_CLASS"],
            }
        )
        response, failure = classify_raw_response(raw)
        assert response is None
        assert failure == "SCHEMA_INVALID"

    def test_unknown_decision_is_rejected(self) -> None:
        raw = json.dumps(
            {
                "decision": "PROBABLY",
                "confidence": "HIGH",
                "reason_code": "MATCH_EXACT_PRODUCT_CONTEXT",
                "matched_attributes": [],
                "conflicting_attributes": [],
                "missing_critical_attributes": [],
                "conflict_classes": [],
            }
        )
        response, failure = classify_raw_response(raw)
        assert response is None
        assert failure == "SCHEMA_INVALID"

    def test_incoherent_reason_conflict_pair_is_rejected(self) -> None:
        # NO_MATCH_CAPACITY without the CAPACITY conflict class.
        raw = json.dumps(
            {
                "decision": "NO_MATCH",
                "confidence": "HIGH",
                "reason_code": "NO_MATCH_CAPACITY",
                "matched_attributes": [],
                "conflicting_attributes": [],
                "missing_critical_attributes": [],
                "conflict_classes": [],
            }
        )
        response, failure = classify_raw_response(raw)
        assert response is None
        assert failure == "SCHEMA_INVALID"

    def test_match_carrying_a_hard_conflict_is_rejected(self) -> None:
        raw = json.dumps(
            {
                "decision": "MATCH",
                "confidence": "HIGH",
                "reason_code": "MATCH_EXACT_PRODUCT_CONTEXT",
                "matched_attributes": [],
                "conflicting_attributes": [],
                "missing_critical_attributes": [],
                "conflict_classes": ["CAPACITY"],
            }
        )
        response, failure = classify_raw_response(raw)
        assert response is None
        assert failure == "SCHEMA_INVALID"

    def test_unknown_attribute_dimension_is_rejected(self) -> None:
        raw = json.dumps(
            {
                "decision": "MATCH",
                "confidence": "HIGH",
                "reason_code": "MATCH_EXACT_PRODUCT_CONTEXT",
                "matched_attributes": [
                    {"dimension": "INVENTED_DIMENSION", "detail": "x"}
                ],
                "conflicting_attributes": [],
                "missing_critical_attributes": [],
                "conflict_classes": [],
            }
        )
        response, failure = classify_raw_response(raw)
        assert response is None
        assert failure == "SCHEMA_INVALID"

    def test_an_invalid_captured_response_is_not_substituted(
        self, corpus, tmp_path
    ) -> None:
        """The offline evaluator must not silently substitute an
        expected answer for an invalid model response: the case becomes
        a bounded integrity failure, not an evaluation."""
        case_id = "V2Q-SSD-ATTR-CAPACITY-0024"
        path = write_capture(
            tmp_path / "c.json",
            corpus,
            attempts_overrides={
                case_id: [
                    {
                        "role": "PRIMARY",
                        "provider": "amax",
                        "model": "qwen3.8-27b",
                        "status": "OK",
                        "raw_output": "this is not json",
                    }
                ]
            },
        )
        capture = load_capture(path)
        result = evaluate_for_model(corpus, capture, *primary_route())
        outcome = next(o for o in result.outcomes if o.case_id == case_id)
        assert outcome.state == "CAPTURE_INTEGRITY_FAILURE"
        assert outcome.verdict == "INTEGRITY_FAILED"
        assert outcome.model_decision is None
        assert "NOT substituted" in outcome.notes[0]
        # The integrity failure is a hard safety gate input.
        assert (
            result.metrics["counts"]["capture_integrity_failures"] == 1
        )


# ===========================================================================
# Capture route / corpus binding attacks
# ===========================================================================


class TestCaptureBinding:
    def test_a_capture_attempt_for_an_unpinned_model_fails_closed(
        self, corpus, tmp_path
    ) -> None:
        path = write_capture(tmp_path / "c.json", corpus)
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        doc["records"][0]["attempts"][0]["model"] = "some-other-model"
        Path(path).write_text(json.dumps(doc), encoding="utf-8")
        with pytest.raises(
            CaptureIntegrityError, match="frozen PRIMARY route"
        ):
            load_capture(path)

    def test_a_capture_attempt_for_a_foreign_provider_fails_closed(
        self, corpus, tmp_path
    ) -> None:
        path = write_capture(tmp_path / "c.json", corpus)
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        doc["records"][0]["attempts"][0]["provider"] = "other-provider"
        Path(path).write_text(json.dumps(doc), encoding="utf-8")
        with pytest.raises(CaptureIntegrityError, match="frozen PRIMARY route"):
            load_capture(path)

    def test_an_unpinned_fallback_attempt_fails_closed(
        self, corpus, tmp_path
    ) -> None:
        case_id = "V2Q-SSD-ATTR-CAPACITY-0024"
        path = write_capture(
            tmp_path / "c.json",
            corpus,
            attempts_overrides={
                case_id: [
                    {
                        "role": "PRIMARY",
                        "provider": "amax",
                        "model": "qwen3.8-27b",
                        "status": "TIMEOUT",
                        "raw_output": None,
                    },
                    {
                        "role": "FALLBACK",
                        "provider": "amax",
                        "model": "qwen3.8-27b",
                        "status": "OK",
                        "raw_output": make_response("MATCH"),
                    },
                ]
            },
        )
        with pytest.raises(
            CaptureIntegrityError, match="frozen FALLBACK route"
        ):
            load_capture(path)

    def test_a_capture_bound_to_a_mutated_corpus_digest_fails_closed(
        self, corpus, tmp_path
    ) -> None:
        path = write_capture(tmp_path / "c.json", corpus)
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        doc["corpus_digest"] = "0" * 64
        Path(path).write_text(json.dumps(doc), encoding="utf-8")
        capture = load_capture(path)
        with pytest.raises(QualificationContractError):
            evaluate_for_model(corpus, capture, *primary_route())

    def test_a_capture_record_for_a_contract_negative_case_fails_closed(
        self, corpus, tmp_path
    ) -> None:
        cn_id = "V2Q-CN-VERIFIED-0044"
        path = write_capture(tmp_path / "c.json", corpus)
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        doc["records"].append(
            {
                "case_id": cn_id,
                "attempts": [
                    {
                        "role": "PRIMARY",
                        "provider": "amax",
                        "model": "qwen3.8-27b",
                        "status": "OK",
                        "raw_output": make_response("MATCH"),
                    }
                ],
                "fallback_used": False,
                "fallback_reason": None,
            }
        )
        Path(path).write_text(json.dumps(doc), encoding="utf-8")
        capture = load_capture(path)
        from product_intelligence.evaluation.semantic_v2.capture import (
            verify_capture_against_corpus,
        )

        with pytest.raises(
            CaptureIntegrityError, match="schema-bypass attack"
        ):
            verify_capture_against_corpus(capture, corpus)
        with pytest.raises(QualificationContractError):
            evaluate_for_model(corpus, capture, *primary_route())

    def test_a_capture_record_for_an_unknown_case_fails_closed(
        self, corpus, tmp_path
    ) -> None:
        path = write_capture(tmp_path / "c.json", corpus)
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        doc["records"].append(
            {
                "case_id": "V2Q-NO-SUCH-CASE",
                "attempts": [
                    {
                        "role": "PRIMARY",
                        "provider": "amax",
                        "model": "qwen3.8-27b",
                        "status": "OK",
                        "raw_output": make_response("MATCH"),
                    }
                ],
                "fallback_used": False,
                "fallback_reason": None,
            }
        )
        Path(path).write_text(json.dumps(doc), encoding="utf-8")
        capture = load_capture(path)
        from product_intelligence.evaluation.semantic_v2.capture import (
            verify_capture_against_corpus,
        )

        with pytest.raises(CaptureIntegrityError, match="not in the bound corpus"):
            verify_capture_against_corpus(capture, corpus)

    def test_a_fallback_after_a_successful_primary_fails_closed(
        self, corpus, tmp_path
    ) -> None:
        case_id = "V2Q-SSD-ATTR-CAPACITY-0024"
        path = write_capture(tmp_path / "c.json", corpus)
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        record = next(r for r in doc["records"] if r["case_id"] == case_id)
        record["attempts"].append(
            {
                "role": "FALLBACK",
                "provider": "vllm-262k",
                "model": "Qwen3.6-27B-262K",
                "status": "OK",
                "raw_output": make_response("NO_MATCH"),
            }
        )
        record["fallback_used"] = True
        record["fallback_reason"] = "TIMEOUT"
        Path(path).write_text(json.dumps(doc), encoding="utf-8")
        with pytest.raises(
            CaptureIntegrityError, match="final - a fallback"
        ):
            load_capture(path)

    def test_a_raw_output_on_a_failed_attempt_fails_closed(
        self, corpus, tmp_path
    ) -> None:
        case_id = "V2Q-SSD-ATTR-CAPACITY-0024"
        path = write_capture(
            tmp_path / "c.json",
            corpus,
            attempts_overrides={
                case_id: [
                    {
                        "role": "PRIMARY",
                        "provider": "amax",
                        "model": "qwen3.8-27b",
                        "status": "TIMEOUT",
                        "raw_output": "leaked raw body",
                    }
                ]
            },
        )
        with pytest.raises(CaptureError, match="carries no raw"):
            load_capture(path)

    def test_an_unknown_attempt_status_fails_closed(
        self, corpus, tmp_path
    ) -> None:
        case_id = "V2Q-SSD-ATTR-CAPACITY-0024"
        path = write_capture(
            tmp_path / "c.json",
            corpus,
            attempts_overrides={
                case_id: [
                    {
                        "role": "PRIMARY",
                        "provider": "amax",
                        "model": "qwen3.8-27b",
                        "status": "SOME_NEW_STATUS",
                        "raw_output": None,
                    }
                ]
            },
        )
        with pytest.raises(CaptureError, match="unknown bounded status"):
            load_capture(path)
