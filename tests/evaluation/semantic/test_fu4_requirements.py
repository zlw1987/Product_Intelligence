"""Tests for FU4 requirements - fail-closed closure.

 PRODUCT-INTEL.SEMANTIC.BENCHMARK

All tests are offline. No live network/model calls.
"""

import json
import urllib.error
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from product_intelligence.evaluation.semantic.runner import (
    BenchmarkRunConfig,
    SemanticBenchmarkRunner,
    _get_canonical_full_case_ids,
)
from product_intelligence.evaluation.semantic.transport import (
    FakeSemanticModelTransport,
    OpenAISemanticTransport,
    TransportFailure,
    TransportResult,
)
from product_intelligence.evaluation.semantic.comparison import (
    load_run_comparison,
    _check_run_qualified_for_full_leaderboard,
    _check_provenance_alignment,
    RunComparison,
)


def test_openai_transport_timeout_injection(tmp_path):
    """Test that OpenAISemanticTransport passes correct timeout to opener.open().

    Uses real urllib.request.build_opener() patching to verify the exact
    timeout value passed to opener.open().
    """
    transport = OpenAISemanticTransport(
        base_url="https://api.example.com/v1",
        api_key="test-key",
        request_timeout_seconds=300.0,
    )

    recorded_timeout = None

    class MockResponse:
        status = 200
        def read(self):
            return b'{"choices":[{"message":{"content":"test"}}],"model":"test","created":123,"object":"chat.completion","system_fingerprint":null,"usage":{"prompt_tokens":10,"completion_tokens":5,"total_tokens":15}}'

    mock_response = MockResponse()

    class MockOpener:
        def open(self, req, timeout=None):
            nonlocal recorded_timeout
            recorded_timeout = timeout
            return mock_response

    mock_opener = MockOpener()

    def mock_build_opener(*args):
        return mock_opener

    with patch('urllib.request.build_opener', mock_build_opener):
        result = transport.complete(
            system_prompt="Test",
            user_prompt="Test",
            model="test-model",
        )

        assert recorded_timeout == 300.0, f"Expected timeout=300.0, got {recorded_timeout}"
        assert result is not None

    transport2 = OpenAISemanticTransport(
        base_url="https://api.example.com/v1",
        api_key="test-key",
        request_timeout_seconds=123.0,
    )

    recorded_timeout = None

    with patch('urllib.request.build_opener', mock_build_opener):
        result = transport2.complete(
            system_prompt="Test",
            user_prompt="Test",
            model="test-model",
        )

        assert recorded_timeout == 123.0, f"Expected timeout=123.0, got {recorded_timeout}"
        assert result is not None


def test_empty_body_http_error_classification():
    """Test HTTPError classification survives empty body."""
    transport = OpenAISemanticTransport(
        base_url="https://api.example.com/v1",
        api_key="test-key",
    )

    mock_response = MagicMock()
    mock_response.status = 401
    mock_response.read.return_value = b""

    class MockOpener:
        def open(self, req, timeout=None):
            raise urllib.error.HTTPError(
                url='https://api.example.com/v1/chat/completions',
                code=401,
                msg='Unauthorized',
                hdrs={},
                fp=mock_response,
            )

    mock_opener = MockOpener()

    def mock_build_opener(*args):
        return mock_opener

    with patch('urllib.request.build_opener', mock_build_opener):
        result = transport.complete(
            system_prompt="Test",
            user_prompt="Test",
            model="test-model",
        )

        assert isinstance(result, TransportFailure)
        assert result.error_type == "AUTHENTICATION_FAILED"
        assert result.http_status == 401

    mock_response2 = MagicMock()
    mock_response2.status = 404
    mock_response2.read.return_value = b"not valid json {"

    class MockOpener2:
        def open(self, req, timeout=None):
            raise urllib.error.HTTPError(
                url='https://api.example.com/v1/chat/completions',
                code=404,
                msg='Not Found',
                hdrs={},
                fp=mock_response2,
            )

    mock_opener2 = MockOpener2()

    def mock_build_opener2(*args):
        return mock_opener2

    with patch('urllib.request.build_opener', mock_build_opener2):
        result = transport.complete(
            system_prompt="Test",
            user_prompt="Test",
            model="test-model",
        )

        assert isinstance(result, TransportFailure)
        assert result.error_type == "MODEL_NOT_FOUND"
        assert result.http_status == 404


def test_single_run_missing_timeout_fail_closed(tmp_path):
    """Test that a single run missing request_timeout_seconds fails closed."""
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    manifest = {
        "benchmark_kind": "semantic_model_qualification",
        "schema_version": "1.0",
        "runner_version": "1.0",
        "corpus_version": 1,
        "corpus_sha256": "abc123",
        "prompt_version": "1.0",
        "prompt_sha256": "def456",
        "provider": "amax",
        "model": "minimax-m2.7",
        "role": "generative",
        "generation_parameters": {
            "temperature": 0.0,
            "max_tokens": 32768,
        },
        "transport_parameters": {},  # Empty - no timeout
        "case_selection": "FULL",
        "case_ids": ["SMQ-0001"],
        "case_count": 1,
        "start_timestamp": "2025-01-01T00:00:00+00:00",
        "finish_timestamp": "2025-01-01T00:00:01+00:00",
        "git_head": "test",
        "transport_type": "FakeSemanticModelTransport",
        "run_status": "COMPLETED",
        "qualification_eligible": True,
        "qualification_gates_applicable": True,
    }

    with open(run_dir / "manifest.json", "w") as f:
        json.dump(manifest, f)

    evaluation = {
        "valid_output_rate": 1.0,
        "decision_accuracy": 1.0,
        "match_precision": 1.0,
        "match_recall": 1.0,
        "false_match_count": 0,
        "safety_cost": 0,
        "gates_passed": {
            "decision_accuracy": True,
            "match_precision": True,
            "match_recall": True,
            "safety_cost": True,
        },
    }

    with open(run_dir / "evaluation.json", "w") as f:
        json.dump(evaluation, f)

    comp = load_run_comparison(run_dir / "manifest.json")

    result = _check_run_qualified_for_full_leaderboard(comp)
    assert result.passed == False
    assert result.error_code == "MISSING_REQUEST_TIMEOUT_PROVENANCE"


def test_single_run_missing_generation_fail_closed(tmp_path):
    """Test that a single run missing generation parameters fails closed."""
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    manifest = {
        "benchmark_kind": "semantic_model_qualification",
        "schema_version": "1.0",
        "runner_version": "1.0",
        "corpus_version": 1,
        "corpus_sha256": "abc123",
        "prompt_version": "1.0",
        "prompt_sha256": "def456",
        "provider": "amax",
        "model": "minimax-m2.7",
        "role": "generative",
        "generation_parameters": {},  # Empty - no temperature or max_tokens
        "transport_parameters": {
            "request_timeout_seconds": 300.0,
        },
        "case_selection": "FULL",
        "case_ids": ["SMQ-0001"],
        "case_count": 1,
        "start_timestamp": "2025-01-01T00:00:00+00:00",
        "finish_timestamp": "2025-01-01T00:00:01+00:00",
        "git_head": "test",
        "transport_type": "FakeSemanticModelTransport",
        "run_status": "COMPLETED",
        "qualification_eligible": True,
        "qualification_gates_applicable": True,
    }

    with open(run_dir / "manifest.json", "w") as f:
        json.dump(manifest, f)

    evaluation = {
        "valid_output_rate": 1.0,
        "decision_accuracy": 1.0,
        "match_precision": 1.0,
        "match_recall": 1.0,
        "false_match_count": 0,
        "safety_cost": 0,
        "gates_passed": {
            "decision_accuracy": True,
            "match_precision": True,
            "match_recall": True,
            "safety_cost": True,
        },
    }

    with open(run_dir / "evaluation.json", "w") as f:
        json.dump(evaluation, f)

    comp = load_run_comparison(run_dir / "manifest.json")

    result = _check_run_qualified_for_full_leaderboard(comp)
    assert result.passed == False
    assert result.error_code == "MISSING_GENERATION_PROVENANCE"


def test_canonical_full_case_ids_validation():
    """Test that canonical FULL case IDs validation works via comparison."""
    canonical_case_ids = _get_canonical_full_case_ids()
    
    # Create a RunComparison with wrong case_ids (63 cases instead of 64)
    comp = RunComparison(
        provider="amax",
        model="minimax-m2.7",
        role="generative",
        case_selection="FULL",
        case_count=63,
        run_status="COMPLETED",
        qualification_eligible=True,
        qualification_gates_applicable=True,
        gates_passed=True,
        valid_output_rate=1.0,
        match_precision=1.0,
        match_recall=1.0,
        accuracy=1.0,
        false_match_count=0,
        safety_cost=0,
        request_timeout_seconds=300.0,
        temperature=0.0,
        max_tokens=32768,
        corpus_sha256="abc123",
        prompt_sha256="def456",
        case_ids=tuple(f"SMQ-{i:04d}" for i in range(1, 64)),
        benchmark_kind="semantic_model_qualification",
        schema_version="1.0",
    )
    
    ref_comp = RunComparison(
        provider="amax",
        model="minimax-m2.7",
        role="generative",
        case_selection="FULL",
        case_count=64,
        run_status="COMPLETED",
        qualification_eligible=True,
        qualification_gates_applicable=True,
        gates_passed=True,
        valid_output_rate=1.0,
        match_precision=1.0,
        match_recall=1.0,
        accuracy=1.0,
        false_match_count=0,
        safety_cost=0,
        request_timeout_seconds=300.0,
        temperature=0.0,
        max_tokens=32768,
        corpus_sha256="abc123",
        prompt_sha256="def456",
        case_ids=canonical_case_ids,
        benchmark_kind="semantic_model_qualification",
        schema_version="1.0",
    )
    
    results = _check_provenance_alignment(ref_comp, comp)
    failures = [r for r in results if not r.passed]
    assert any("CASE_COUNT" in str(f.error_code) for f in failures), \
        f"Expected CASE_COUNT_MISMATCH, got: {[(r.error_code, r.detail) for r in failures]}"


def test_wrong_order_case_ids_fail():
    """Test that wrong order case_ids fails pairwise alignment check."""
    canonical_case_ids = _get_canonical_full_case_ids()
    wrong_order = canonical_case_ids[::-1]
    
    ref_comp = RunComparison(
        provider="amax",
        model="minimax-m2.7",
        role="generative",
        case_selection="FULL",
        case_count=64,
        run_status="COMPLETED",
        qualification_eligible=True,
        qualification_gates_applicable=True,
        gates_passed=True,
        valid_output_rate=1.0,
        match_precision=1.0,
        match_recall=1.0,
        accuracy=1.0,
        false_match_count=0,
        safety_cost=0,
        request_timeout_seconds=300.0,
        temperature=0.0,
        max_tokens=32768,
        corpus_sha256="abc123",
        prompt_sha256="def456",
        case_ids=canonical_case_ids,
        benchmark_kind="semantic_model_qualification",
        schema_version="1.0",
    )
    
    wrong_comp = RunComparison(
        provider="amax",
        model="minimax-m2.7",
        role="generative",
        case_selection="FULL",
        case_count=64,
        run_status="COMPLETED",
        qualification_eligible=True,
        qualification_gates_applicable=True,
        gates_passed=True,
        valid_output_rate=1.0,
        match_precision=1.0,
        match_recall=1.0,
        accuracy=1.0,
        false_match_count=0,
        safety_cost=0,
        request_timeout_seconds=300.0,
        temperature=0.0,
        max_tokens=32768,
        corpus_sha256="abc123",
        prompt_sha256="def456",
        case_ids=wrong_order,
        benchmark_kind="semantic_model_qualification",
        schema_version="1.0",
    )
    
    results = _check_provenance_alignment(ref_comp, wrong_comp)
    failures = [r for r in results if not r.passed]
    assert any("CASE_ID_ORDER" in str(f.error_code) for f in failures), \
        f"Expected CASE_ID_ORDER_MISMATCH, got: {[(r.error_code, r.detail) for r in failures]}"


def test_attempted_case_ids_count_persistence(tmp_path):
    """Test that attempted_case_ids and attempted_case_count are persisted."""
    canonical_case_ids = _get_canonical_full_case_ids()
    
    transport = FakeSemanticModelTransport(
        responses={
            case_id: '{"decision": "MATCH", "confidence": "HIGH", "matched_attributes": [], "conflicting_attributes": [], "missing_critical_attributes": [], "reason_code": "test"}'
            for case_id in canonical_case_ids
        },
    )

    runner = SemanticBenchmarkRunner(transport=transport)
    config = BenchmarkRunConfig(
        provider="amax",
        model="minimax-m2.7",
        case_selection="FULL",
        transport=transport,
        output_dir=tmp_path,
    )

    result = runner.run(config)
    run_dir = runner.save_run(result)

    manifest_path = run_dir / "manifest.json"
    with open(manifest_path, "r") as f:
        manifest = json.load(f)

    assert "attempted_case_ids" in manifest
    assert "attempted_case_count" in manifest
    assert manifest["attempted_case_count"] == len(canonical_case_ids)
    assert len(manifest["attempted_case_ids"]) == len(canonical_case_ids)

    assert manifest["attempted_case_ids"] == manifest["case_ids"]
    assert manifest["attempted_case_count"] == manifest["case_count"]


def test_fatal_abort_attempted_count(tmp_path):
    """Test that attempted_case_count reflects fatal abort.
    
    Use a transport that fails with a RUN-FATAL error type to trigger early abort.
    """
    from product_intelligence.evaluation.semantic.transport import TransportFailure
    
    canonical_case_ids = _get_canonical_full_case_ids()

    class FatalErrorTransport(FakeSemanticModelTransport):
        def complete(self, *args, **kwargs):
            result = super().complete(*args, **kwargs)
            if isinstance(result, TransportFailure) and result.error_type == "CONNECTION_ERROR":
                return TransportFailure(
                    error_type="AUTHENTICATION_FAILED",
                    transport_status=result.transport_status,
                    http_status=result.http_status,
                )
            return result

    transport = FatalErrorTransport(
        responses={
            case_id: '{"decision": "MATCH", "confidence": "HIGH", "matched_attributes": [], "conflicting_attributes": [], "missing_critical_attributes": [], "reason_code": "test"}'
            for case_id in canonical_case_ids
        },
        case_ids=canonical_case_ids,  # Pass case_ids for call index fallback
        failure_error_types={"SMQ-0001": "AUTHENTICATION_FAILED"},
    )

    runner = SemanticBenchmarkRunner(transport=transport)
    config = BenchmarkRunConfig(
        provider="amax",
        model="minimax-m2.7",
        case_selection="FULL",
        transport=transport,
        output_dir=tmp_path,
    )

    result = runner.run(config)
    run_dir = runner.save_run(result)

    manifest_path = run_dir / "manifest.json"
    with open(manifest_path, "r") as f:
        manifest = json.load(f)

    assert manifest["attempted_case_count"] == 1
    assert len(manifest["attempted_case_ids"]) == 1
    assert manifest["attempted_case_ids"][0] == "SMQ-0001"
    assert manifest["run_status"] == "FAILED_CONFIGURATION"
