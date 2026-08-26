"""Live runner contract tests — PRODUCT-INTEL semantic qualification.

Offline regression tests protecting the benchmark runner contract exposed
during Qwen3.6 qualification debugging.

No live network/model calls. No production files modified.
"""

from __future__ import annotations

import io
import json
import math
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from product_intelligence.evaluation.semantic.comparison import (
    _check_provenance_alignment,
    _check_run_qualified_for_full_leaderboard,
    _compute_gates_passed,
    ProvenanceCheckResult,
    RunComparison,
)
from product_intelligence.evaluation.semantic.runner import (
    BenchmarkRunConfig,
    SemanticBenchmarkRunner,
)
from product_intelligence.evaluation.semantic.transport import (
    FakeSemanticModelTransport,
    OpenAISemanticTransport,
    TransportFailure,
    TransportResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SEMANTIC_JSON = (
    '{"decision": "MATCH", "confidence": "HIGH", '
    '"matched_attributes": ["mpn"], "conflicting_attributes": [], '
    '"missing_critical_attributes": [], "reason_code": "exact_mpn"}'
)


def _smoke_responses(valid: set[str] | None = None) -> dict[str, str]:
    """Return strict-valid JSON for listed smoke case IDs."""
    from product_intelligence.evaluation.semantic.model_catalog import GPT_OSS_SMOKE_CASE_IDS
    if valid is None:
        valid = set(GPT_OSS_SMOKE_CASE_IDS)
    return {cid: _SEMANTIC_JSON for cid in valid}


# ---------------------------------------------------------------------------
# 1. BenchmarkRunConfig timeout validation
# ---------------------------------------------------------------------------


class TestBenchmarkRunConfigTimeoutValidation:
    """Timeout validation rejects invalid values, accepts valid ones."""

    @pytest.fixture
    def _transport(self):
        return FakeSemanticModelTransport()

    @pytest.mark.parametrize("bad_val", [0, -1, float("nan"), float("inf"), float("-inf"), True, False])
    def test_rejected(self, bad_val, _transport):
        with pytest.raises(ValueError):
            BenchmarkRunConfig(
                provider="amax", model="minimax-m2.7",
                case_selection="FULL", transport=_transport,
                request_timeout_seconds=bad_val,  # type: ignore[arg-type]
            )

    def test_accepted_small(self, _transport):
        config = BenchmarkRunConfig(
            provider="amax", model="minimax-m2.7",
            case_selection="FULL", transport=_transport,
            request_timeout_seconds=0.1,
        )
        assert config.request_timeout_seconds == 0.1

    def test_accepted_300(self, _transport):
        config = BenchmarkRunConfig(
            provider="amax", model="minimax-m2.7",
            case_selection="FULL", transport=_transport,
            request_timeout_seconds=300.0,
        )
        assert config.request_timeout_seconds == 300.0


# ---------------------------------------------------------------------------
# 2-3. REAL OpenAISemanticTransport HTTP 200 path + variants
# ---------------------------------------------------------------------------

class TestRealTransportHttp200:
    """Through the *real* OpenAISemanticTransport code path, with urllib patched."""

    def _make_response(self, body: dict, *, status: int = 200) -> _MockResp:
        return _MockResp(
            status=status,
            body=json.dumps(body).encode("utf-8"),
        )

    def _transport_with_mock(self, body: dict, *, status: int = 200) -> tuple[OpenAISemanticTransport, unittest.mock._patch]:
        """Build transport with urllib patched for the duration of complete()."""
        import unittest.mock

        resp = self._make_response(body, status=status)
        opener_mock = unittest.mock.MagicMock()
        opener_mock.open = unittest.mock.MagicMock(side_effect=_open_ok(resp))
        patcher = unittest.mock.patch(
            "urllib.request.build_opener", return_value=opener_mock,
        )
        patcher.start()
        transport = OpenAISemanticTransport(base_url="https://example.com/v1")
        return transport, patcher

    # -- 2. canonical 200 --

    def test_http200_canonical(self):
        body = {
            "model": "Qwen3.6-27B-262K",
            "choices": [{
                "message": {
                    "content": _SEMANTIC_JSON,
                    "reasoning": "SECRET_REASONING_SENTINEL",
                },
                "finish_reason": "stop",
            }],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 200,
                "total_tokens": 300,
            },
        }
        t, patcher = self._transport_with_mock(body)
        try:
            result = t.complete(
                system_prompt="sys", user_prompt="usr", model="Qwen3.6-27B-262K",
            )
        finally:
            patcher.stop()
        assert isinstance(result, TransportResult)
        assert result.provider_reported_model == "Qwen3.6-27B-262K"
        assert result.finish_reason == "stop"
        assert result.raw_output == _SEMANTIC_JSON  # exact message.content
        assert result.token_usage == {"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300}
        assert "SECRET_REASONING_SENTINEL" not in result.raw_output
        assert "SECRET_REASONING_SENTINEL" not in json.dumps(result.to_dict())

    # -- 3. variants --

    def test_finish_reason_length_preserved(self):
        body = {
            "model": "Qwen3.6-27B-262K",
            "choices": [{"message": {"content": _SEMANTIC_JSON}, "finish_reason": "length"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }
        t, patcher = self._transport_with_mock(body)
        try:
            result = t.complete(
                system_prompt="sys", user_prompt="usr", model="Qwen3.6-27B-262K",
            )
        finally:
            patcher.stop()
        assert isinstance(result, TransportResult)
        assert result.finish_reason == "length"

    def test_missing_finish_reason_is_none(self):
        body = {
            "model": "Qwen3.6-27B-262K",
            "choices": [{"message": {"content": _SEMANTIC_JSON}}],
        }
        t, patcher = self._transport_with_mock(body)
        try:
            result = t.complete(
                system_prompt="sys", user_prompt="usr", model="Qwen3.6-27B-262K",
            )
        finally:
            patcher.stop()
        assert isinstance(result, TransportResult)
        assert result.finish_reason is None

    def test_missing_top_level_model_is_none(self):
        body = {
            "choices": [{"message": {"content": _SEMANTIC_JSON}}],
        }
        t, patcher = self._transport_with_mock(body)
        try:
            result = t.complete(
                system_prompt="sys", user_prompt="usr", model="Qwen3.6-27B-262K",
            )
        finally:
            patcher.stop()
        assert isinstance(result, TransportResult)
        assert result.provider_reported_model is None


# ---------------------------------------------------------------------------
# 4. Durable responses.jsonl provenance
# ---------------------------------------------------------------------------

class TestDurableResponsesJsonl:
    """responses.jsonl persists finish_reason, provider_reported_model, no reasoning."""

    def _run_and_save(self, transport, tmp_path: Path) -> Path:
        runner = SemanticBenchmarkRunner(transport=transport)
        config = BenchmarkRunConfig(
            provider="amax", model="gpt-oss-20b",
            case_selection="SMOKE", transport=transport, output_dir=tmp_path,
        )
        result = runner.run(config)
        return runner.save_run(result)

    def test_finish_reason_stop_persists(self, tmp_path):
        transport = FakeSemanticModelTransport(
            case_ids=("SMQ-0001",),
            responses=_smoke_responses({"SMQ-0001"}),
            finish_reason="stop",
        )
        run_dir = self._run_and_save(transport, tmp_path)
        entries = _read_jsonl(run_dir / "responses.jsonl")
        rec = entries["SMQ-0001"]
        assert rec["finish_reason"] == "stop"

    def test_finish_reason_length_persists(self, tmp_path):
        transport = FakeSemanticModelTransport(
            case_ids=("SMQ-0001",),
            responses=_smoke_responses({"SMQ-0001"}),
            finish_reason="length",
        )
        run_dir = self._run_and_save(transport, tmp_path)
        entries = _read_jsonl(run_dir / "responses.jsonl")
        rec = entries["SMQ-0001"]
        assert rec["finish_reason"] == "length"

    def test_finish_reason_none_persists_null(self, tmp_path):
        transport = FakeSemanticModelTransport(
            case_ids=("SMQ-0001",),
            responses=_smoke_responses({"SMQ-0001"}),
            finish_reason=None,
        )
        run_dir = self._run_and_save(transport, tmp_path)
        entries = _read_jsonl(run_dir / "responses.jsonl")
        rec = entries["SMQ-0001"]
        assert rec["finish_reason"] is None

    def test_provider_reported_model_persists(self, tmp_path):
        transport = FakeSemanticModelTransport(
            case_ids=("SMQ-0001",),
            responses=_smoke_responses({"SMQ-0001"}),
            finish_reason="stop",
            provider_reported_model="gpt-oss-20b",
        )
        run_dir = self._run_and_save(transport, tmp_path)
        entries = _read_jsonl(run_dir / "responses.jsonl")
        rec = entries["SMQ-0001"]
        assert rec["provider_reported_model"] == "gpt-oss-20b"

    def test_reasoning_sentinel_never_persists(self, tmp_path):
        import unittest.mock

        body = {
            "model": "gpt-oss-20b",
            "choices": [{
                "message": {
                    "content": _SEMANTIC_JSON,
                    "reasoning": "SECRET_REASONING_SENTINEL",
                },
                "finish_reason": "stop",
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
            },
        }

        resp = _MockResp(
            status=200,
            body=json.dumps(body).encode("utf-8"),
        )

        opener_mock = unittest.mock.MagicMock()
        opener_mock.open = unittest.mock.MagicMock(
            side_effect=_open_ok(resp)
        )

        transport = OpenAISemanticTransport(
            base_url="https://example.com/v1"
        )
        runner = SemanticBenchmarkRunner(transport=transport)

        config = BenchmarkRunConfig(
            provider="amax",
            model="gpt-oss-20b",
            case_selection="SMOKE",
            transport=transport,
            output_dir=tmp_path,
        )

        with unittest.mock.patch(
            "urllib.request.build_opener",
            return_value=opener_mock,
        ):
            result = runner.run(config)

        run_dir = runner.save_run(result)

        jsonl_text = (
            run_dir / "responses.jsonl"
        ).read_text(encoding="utf-8")

        assert "SECRET_REASONING_SENTINEL" not in jsonl_text


# ---------------------------------------------------------------------------
# 5-6. REAL HTTPError paths
# ---------------------------------------------------------------------------

class TestRealHttpErrorPaths:
    """Through the real OpenAISemanticTransport HTTPError branch."""

    def _error_transport(self, status: int, body: dict | str = "") -> tuple[OpenAISemanticTransport, unittest.mock._patch]:
        import unittest.mock
        err = _make_http_error(status, body)
        patcher = unittest.mock.patch(
            "urllib.request.build_opener",
            return_value=unittest.mock.MagicMock(
                open=unittest.mock.MagicMock(side_effect=err),
            ),
        )
        patcher.start()
        transport = OpenAISemanticTransport(base_url="https://example.com/v1")
        return transport, patcher

    # -- 5. HTTPError 400 UNSUPPORTED_PARAMETER --

    def test_http400_unsupported_parameter(self):
        t, patcher = self._error_transport(400, {
            "error": {
                "message": (
                    "litellm.UnsupportedParamsError: openai does not support "
                    "parameters: ['reasoning_effort']"
                ),
            },
        })
        try:
            result = t.complete(
                system_prompt="sys", user_prompt="usr", model="Qwen3.6-27B-262K",
            )
        finally:
            patcher.stop()
        assert isinstance(result, TransportFailure)
        assert result.error_type == "UNSUPPORTED_PARAMETER"
        assert result.http_status == 400

    def test_http400_unsupported_no_raw_persisted(self):
        """Raw provider error message is NOT persisted."""
        t, patcher = self._error_transport(400, {
            "error": {"message": "litellm.UnsupportedParamsError: SECRET_KEY_LEAK"},
        })
        try:
            result = t.complete(
                system_prompt="sys", user_prompt="usr", model="Qwen3.6-27B-262K",
            )
        finally:
            patcher.stop()
        d = result.to_dict() if isinstance(result, TransportFailure) else {}
        assert "SECRET_KEY_LEAK" not in json.dumps(d)

    # -- 6. status-only fallback --

    @pytest.mark.parametrize(
        ("status", "body", "expected"),
        [
            (401, "", "AUTHENTICATION_FAILED"),
            (404, "malformed", "MODEL_NOT_FOUND"),
            (429, "", "RATE_LIMITED"),
            (503, "", "PROVIDER_UNAVAILABLE"),
            (400, "malformed", "HTTP_ERROR"),
        ],
    )
    def test_status_only_fallback(self, status, body, expected):
        t, patcher = self._error_transport(status, body)
        try:
            result = t.complete(
                system_prompt="sys", user_prompt="usr", model="Qwen3.6-27B-262K",
            )
        finally:
            patcher.stop()
        assert isinstance(result, TransportFailure)
        assert result.error_type == expected


# ---------------------------------------------------------------------------
# 7. Fatal abort contract
# ---------------------------------------------------------------------------

class TestFatalAbortContract:
    """Run-fatal errors abort after one call."""

    def _run_fatal(self, error_type: str) -> tuple[SemanticBenchmarkRunner, BenchmarkRunConfig]:
        from product_intelligence.evaluation.semantic.model_catalog import GPT_OSS_SMOKE_CASE_IDS
        transport = FakeSemanticModelTransport(
            case_ids=GPT_OSS_SMOKE_CASE_IDS,
            failure_error_types={GPT_OSS_SMOKE_CASE_IDS[0]: error_type},
        )
        runner = SemanticBenchmarkRunner(transport=transport)
        config = BenchmarkRunConfig(
            provider="amax", model="gpt-oss-20b",
            case_selection="SMOKE", transport=transport,
        )
        return runner, config

    def test_unsupported_parameter_fatal(self):
        runner, config = self._run_fatal("UNSUPPORTED_PARAMETER")
        result = runner.run(config)
        transport = config.transport
        assert transport.call_count == 1
        assert result.manifest["run_status"] == "FAILED_CONFIGURATION"
        assert result.manifest["qualification_eligible"] is False
        assert result.manifest["attempted_case_count"] == 1

    def test_rate_limited_fatal(self):
        runner, config = self._run_fatal("RATE_LIMITED")
        result = runner.run(config)
        transport = config.transport
        assert transport.call_count == 1
        assert result.manifest["run_status"] == "FAILED_PROVIDER"
        assert result.manifest["qualification_eligible"] is False


# ---------------------------------------------------------------------------
# 8. Later-response provider model drift
# ---------------------------------------------------------------------------

class TestProviderModelDrift:
    """Second response reports a different model → MODEL_IDENTITY_MISMATCH."""

    def test_drift_aborts(self):
        from product_intelligence.evaluation.semantic.model_catalog import GPT_OSS_SMOKE_CASE_IDS

        class DriftTransport(FakeSemanticModelTransport):
            def complete(self, *, system_prompt, user_prompt, model, **kw):
                self.call_count += 1
                cid = self._case_ids[self.call_count - 1] if self.call_count <= len(self._case_ids) else "UNKNOWN"
                if cid == self._case_ids[0]:
                    return TransportResult(
                        raw_output=_SEMANTIC_JSON, latency_ms=1.0,
                        provider_status="200", provider_id="fake", model_id=model,
                        provider_reported_model=model,  # matches
                    )
                return TransportResult(
                    raw_output=_SEMANTIC_JSON, latency_ms=1.0,
                    provider_status="200", provider_id="fake", model_id=model,
                    provider_reported_model="different-model",  # DRIFT
                )

        ids = GPT_OSS_SMOKE_CASE_IDS
        t = DriftTransport(case_ids=ids)
        runner = SemanticBenchmarkRunner(transport=t)
        config = BenchmarkRunConfig(
            provider="amax", model="gpt-oss-20b",
            case_selection="SMOKE", transport=t,
        )
        result = runner.run(config)

        assert t.call_count == 2  # exactly two calls, no third
        assert result.manifest["run_status"] == "FAILED_CONFIGURATION"
        # second response should carry the mismatch error
        second_id = ids[1]
        assert result.responses[second_id]["error"]["error_type"] == "MODEL_IDENTITY_MISMATCH"


# ---------------------------------------------------------------------------
# 9. _compute_gates_passed
# ---------------------------------------------------------------------------


class TestComputeGatesPassed:
    def test_all_true(self):
        assert _compute_gates_passed({"a": True, "b": True}) is True

    def test_one_false(self):
        assert _compute_gates_passed({"a": True, "b": False}) is False

    def test_empty(self):
        assert _compute_gates_passed({}) is False


# ---------------------------------------------------------------------------
# 10-11. Provenance checks (generation + timeout)
# ---------------------------------------------------------------------------

class TestProvenanceChecks:
    """Generation and timeout provenance via _check_provenance_alignment."""

    @pytest.fixture
    def canonical_full_ids(self):
        from product_intelligence.evaluation.semantic.runner import _get_canonical_full_case_ids
        return _get_canonical_full_case_ids()

    def _reference(self, canonical_full_ids, **overrides):
        base = dict(
            provider="amax", model="minimax-m2.7", role="primary_candidate",
            case_selection="FULL", case_count=len(canonical_full_ids),
            run_status="COMPLETED", qualification_eligible=True,
            qualification_gates_applicable=True, gates_passed=True,
            valid_output_rate=1.0, match_precision=1.0, match_recall=1.0,
            accuracy=1.0, false_match_count=0, safety_cost=0,
            benchmark_kind="semantic_model_qualification",
            schema_version="1.0", corpus_version=1,
            corpus_sha256="aaaa", prompt_version="1.0", prompt_sha256="bbbb",
            case_ids=canonical_full_ids,
            request_timeout_seconds=300.0,
            temperature=0.0, max_tokens=32768,
        )
        base.update(overrides)
        return RunComparison(**base)

    # -- 10. generation provenance --

    def test_generation_compatible(self, canonical_full_ids):
        ref = self._reference(canonical_full_ids)
        cand = self._reference(canonical_full_ids)
        results = _check_provenance_alignment(ref, cand)
        assert all(r.passed for r in results)

    def test_max_tokens_mismatch(self, canonical_full_ids):
        ref = self._reference(canonical_full_ids)
        cand = self._reference(canonical_full_ids, max_tokens=4096)
        results = _check_provenance_alignment(ref, cand)
        errors = [r.error_code for r in results if not r.passed]
        assert "MAX_TOKENS_MISMATCH" in errors

    def test_temperature_mismatch(self, canonical_full_ids):
        ref = self._reference(canonical_full_ids)
        cand = self._reference(canonical_full_ids, temperature=0.7)
        results = _check_provenance_alignment(ref, cand)
        errors = [r.error_code for r in results if not r.passed]
        assert "TEMPERATURE_MISMATCH" in errors

    def test_missing_generation_provenance(self, canonical_full_ids):
        ref = self._reference(canonical_full_ids)
        cand = self._reference(canonical_full_ids, temperature=None)
        results = _check_provenance_alignment(ref, cand)
        errors = [r.error_code for r in results if not r.passed]
        assert "MISSING_GENERATION_PROVENANCE" in errors

    # -- 11. timeout provenance --

    def test_timeout_compatible(self, canonical_full_ids):
        ref = self._reference(canonical_full_ids)
        cand = self._reference(canonical_full_ids)
        results = _check_provenance_alignment(ref, cand)
        assert all(r.passed for r in results)

    def test_timeout_mismatch(self, canonical_full_ids):
        ref = self._reference(canonical_full_ids)
        cand = self._reference(canonical_full_ids, request_timeout_seconds=120.0)
        results = _check_provenance_alignment(ref, cand)
        errors = [r.error_code for r in results if not r.passed]
        assert "REQUEST_TIMEOUT_MISMATCH" in errors

    def test_missing_timeout_provenance(self, canonical_full_ids):
        ref = self._reference(canonical_full_ids)
        cand = self._reference(canonical_full_ids, request_timeout_seconds=None)
        results = _check_provenance_alignment(ref, cand)
        errors = [r.error_code for r in results if not r.passed]
        assert "MISSING_REQUEST_TIMEOUT_PROVENANCE" in errors

    def test_both_missing_timeout_fail_closed(self, canonical_full_ids):
        ref = self._reference(canonical_full_ids, request_timeout_seconds=None)
        cand = self._reference(canonical_full_ids, request_timeout_seconds=None)
        results = _check_provenance_alignment(ref, cand)
        errors = [r.error_code for r in results if not r.passed]
        assert "MISSING_REQUEST_TIMEOUT_PROVENANCE" in errors


# ---------------------------------------------------------------------------
# 12. Canonical FULL single-run eligibility
# ---------------------------------------------------------------------------

class TestCanonicalFullEligibility:
    """_check_run_qualified_for_full_leaderboard — exact canonical FULL → PASS."""

    @pytest.fixture
    def canonical_full_ids(self):
        from product_intelligence.evaluation.semantic.runner import _get_canonical_full_case_ids
        return _get_canonical_full_case_ids()

    def _comp(self, canonical_full_ids, **overrides):
        base = dict(
            provider="amax", model="minimax-m2.7", role="primary_candidate",
            case_selection="FULL", case_count=len(canonical_full_ids),
            run_status="COMPLETED", qualification_eligible=True,
            qualification_gates_applicable=True, gates_passed=True,
            valid_output_rate=1.0, match_precision=1.0, match_recall=1.0,
            accuracy=1.0, false_match_count=0, safety_cost=0,
            benchmark_kind="semantic_model_qualification",
            schema_version="1.0", corpus_version=1,
            corpus_sha256="aaaa", prompt_version="1.0", prompt_sha256="bbbb",
            case_ids=canonical_full_ids,
            request_timeout_seconds=300.0,
            temperature=0.0, max_tokens=32768,
        )
        base.update(overrides)
        return RunComparison(**base)

    def test_exact_canonical_pass(self, canonical_full_ids):
        comp = self._comp(canonical_full_ids)
        result = _check_run_qualified_for_full_leaderboard(comp)
        assert result.passed is True

    def test_one_case_count_mismatch(self, canonical_full_ids):
        comp = self._comp(canonical_full_ids, case_count=1)
        result = _check_run_qualified_for_full_leaderboard(comp)
        assert result.passed is False
        assert result.error_code == "CASE_COUNT_MISMATCH"

    def test_missing_case_id(self, canonical_full_ids):
        shortened = canonical_full_ids[:-1]

        comp = self._comp(
            canonical_full_ids,
            case_ids=shortened,
            # Deliberately retain canonical count so the test
            # reaches the ID-set validation gate.
            case_count=len(canonical_full_ids),
        )

        result = _check_run_qualified_for_full_leaderboard(comp)

        assert result.passed is False
        assert result.error_code == "CASE_ID_SET_MISMATCH"

    def test_reversed_order_mismatch(self, canonical_full_ids):
        comp = self._comp(canonical_full_ids, case_ids=canonical_full_ids[::-1])
        result = _check_run_qualified_for_full_leaderboard(comp)
        assert result.passed is False
        assert result.error_code == "CASE_ID_ORDER_MISMATCH"


# ---------------------------------------------------------------------------
# 13. SMOKE attempted-case persisted artifacts (from disk)
# ---------------------------------------------------------------------------

class TestSmokeAttemptedCaseArtifacts:
    """Open saved files FROM DISK and verify attempted_case_count."""

    def _run_fatal_smoke(self, error_case_idx: int, tmp_path: Path) -> Path:
        from product_intelligence.evaluation.semantic.model_catalog import GPT_OSS_SMOKE_CASE_IDS
        smoke_ids = GPT_OSS_SMOKE_CASE_IDS

        valid = set(smoke_ids)
        failure_map: dict[str, str] = {}
        # Build responses for cases before the failure
        for i, cid in enumerate(smoke_ids):
            if i < error_case_idx:
                valid.add(cid)
            elif i == error_case_idx:
                failure_map[cid] = "UNSUPPORTED_PARAMETER"

        transport = FakeSemanticModelTransport(
            case_ids=smoke_ids,
            responses={cid: _SEMANTIC_JSON for cid in valid},
            failure_error_types=failure_map,
        )
        runner = SemanticBenchmarkRunner(transport=transport)
        config = BenchmarkRunConfig(
            provider="amax", model="gpt-oss-20b",
            case_selection="SMOKE", transport=transport, output_dir=tmp_path,
        )
        result = runner.run(config)
        return runner.save_run(result)

    def test_fatal_case_1(self, tmp_path):
        run_dir = self._run_fatal_smoke(0, tmp_path)

        # manifest.json FROM DISK
        manifest = json.loads((run_dir / "manifest.json").read_text())
        assert manifest["case_count"] == 5
        assert manifest["attempted_case_count"] == 1

        # evaluation.json FROM DISK
        ev = json.loads((run_dir / "evaluation.json").read_text())
        assert ev["attempted_case_count"] == 1
        assert ev["invalid_response_count"] == 1

        # summary.md FROM DISK
        summary = (run_dir / "summary.md").read_text()
        assert "Cases attempted: 1" in summary

    def test_fatal_case_2_after_one_valid(self, tmp_path):
        run_dir = self._run_fatal_smoke(1, tmp_path)

        manifest = json.loads((run_dir / "manifest.json").read_text())
        assert manifest["case_count"] == 5
        assert manifest["attempted_case_count"] == 2

        ev = json.loads((run_dir / "evaluation.json").read_text())
        assert ev["attempted_case_count"] == 2
        # denominator is 2, not 5
        assert ev["valid_response_count"] + ev["invalid_response_count"] == 2


# ---------------------------------------------------------------------------
# 14. CLI timeout contract
# ---------------------------------------------------------------------------


class TestCliTimeoutContract:
    """CLI --request-timeout-seconds default and explicit."""

    def test_default_timeout(self):
        from product_intelligence.evaluation.semantic.cli import create_parser
        parser = create_parser()
        args = parser.parse_args(["run", "--provider", "amax", "--model", "minimax-m2.7"])
        assert args.request_timeout_seconds == 300.0

    def test_explicit_timeout(self):
        from product_intelligence.evaluation.semantic.cli import create_parser
        parser = create_parser()
        args = parser.parse_args([
            "run", "--provider", "amax", "--model", "minimax-m2.7",
            "--request-timeout-seconds", "123",
        ])
        assert args.request_timeout_seconds == 123.0


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


class _MockResp:
    """Minimal response that supports context-manager protocol."""
    def __init__(self, status: int, body: bytes):
        self.status = status
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass


def _open_ok(resp: _MockResp):
    """Factory returning a callable that yields resp from opener.open()."""
    def _call(req, **kw):
        return resp
    return _call


def _make_http_error(status: int, body: dict | str) -> urllib.error.HTTPError:
    """Build an HTTPError with a JSON body that supports read()."""
    if isinstance(body, dict):
        raw = json.dumps(body).encode("utf-8")
    else:
        raw = str(body).encode("utf-8")
    err = urllib.error.HTTPError(
        url="https://example.com/v1/chat/completions",
        code=status,
        msg=f"HTTP {status}",
        hdrs={},
        fp=None,
    )
    # Patch read so the transport can decode the body
    err.read = lambda: raw
    return err


def _read_jsonl(path: Path) -> dict[str, dict]:
    """Read responses.jsonl from disk and return dict keyed by case_id."""
    entries: dict[str, dict] = {}
    for line in path.read_text().strip().splitlines():
        if line:
            rec = json.loads(line)
            entries[rec["case_id"]] = rec
    return entries
