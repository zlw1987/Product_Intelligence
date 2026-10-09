"""Q3-B bounded live DIRECT_MODEL_QUALIFICATION capture runner tests.

Mandated properties (all offline: every model call in these tests goes
through a scripted, recording test double - no live network call is
made anywhere in this file, and the full pipeline is re-proven under a
blocked socket):

* exact model pinning (only the two frozen route identities; mixed /
  unknown pairs fail closed; generation parameters are the frozen
  pins, not caller-configurable);
* frozen prompt fidelity (every sent prompt is byte-exact output of
  the frozen production V2 prompt builder; the manifest binds the
  REAL system prompt by digest);
* transport boundary (the live transport is imported lazily, only via
  the approved provider-configuration mechanism; no environment is
  read outside that mechanism; an injected transport needs no
  environment at all);
* no credential leakage (no key / endpoint value reaches any
  artifact, manifest, or summary; key presence is a bare bool);
* timeout handling (bounded validation; the configured timeout
  reaches the transport; a timeout is classified and preserved);
* bounded retry behavior (retryable = transient transport
  conditions only; attempts are hard-bounded; the final bounded
  status is recorded);
* no semantic-error retries (an output-contract failure - malformed
  JSON, schema-invalid, empty, invalid response, identity mismatch -
  is final after exactly one call; an unfavorable semantic decision
  is never retried);
* no best-of-N selection (one record per case; the preserved output
  is the only real model response of the case);
* no contract-negative model calls (the 13 contract-negative cases
  are never rendered into a prompt, never sent, never recorded);
* complete eligible-case traversal (all 43 in corpus order; a
  completed run leaves no case unaccounted for);
* failure preservation (bounded statuses verbatim; run-level aborts
  preserve attempted evidence and name the unattempted cases;
  CASE_REJECTED stays case-local);
* independent model capture (one document per pinned model; a
  document never evaluates against the other identity);
* capture schema validation (the written artifact round-trips the
  UNCHANGED frozen direct-capture loader; tamper fails closed);
* offline replay fidelity (a full correct capture replays to 43
  EVALUATED and stays POLICY_PENDING under the DRAFT policy; the
  direct report builds, verifies, and binds the run);
* no production execution imports (no execution / runs / web /
  providers / framework surface enters the process);
* no authority promotion (the marker stays False; artifacts grant no
  authority token);
* no pricing contamination (artifacts name no pricing / review
  surface);
* no network calls during ordinary unit tests (socket blocked).
"""

from __future__ import annotations

import ast
import json
import socket
import sys
import time
from pathlib import Path

import pytest

from tests.evaluation.semantic_v2._q3a_helpers import (
    CORPUS_PATH,
    POLICY_PATH,
    default_response_for,
    fallback_route,
    load_corpus_bundle,
    make_response,
    primary_route,
)
from product_intelligence.evaluation.semantic.transport import (
    TransportFailure,
    TransportResult,
)
from product_intelligence.evaluation.semantic_v2.canonical import (
    canonical_sha256,
)
from product_intelligence.evaluation.semantic_v2.capture import (
    FALLBACK_ROUTE,
    PRIMARY_ROUTE,
    PROMPT_VERSION_V2,
    SEMANTIC_CONTRACT_VERSION_V2,
)
from product_intelligence.evaluation.semantic_v2.direct_capture import (
    DIRECT_CAPTURE_MODE,
    DIRECT_CAPTURE_SCHEMA_VERSION,
    load_direct_capture,
    verify_direct_capture_against_corpus,
)
from product_intelligence.evaluation.semantic_v2.evaluator import (
    QualificationContractError,
    evaluate_direct_for_model,
)
from product_intelligence.evaluation.semantic_v2.gates import (
    decide,
    evaluate_safety_gates,
)
from product_intelligence.evaluation.semantic_v2.policy import (
    evaluate_thresholds,
    load_policy,
    policy_applies_to,
)
from product_intelligence.evaluation.semantic_v2.report import (
    build_direct_report,
    render_markdown,
    verify_direct_report,
)
from product_intelligence.evaluation.semantic_v2 import live_capture as lc
from product_intelligence.evaluation.semantic_v2.live_capture import (
    LiveCaptureConfig,
    LiveCaptureConfigError,
    LiveCaptureRunner,
    build_live_transport,
    main,
    validate_live_capture_config,
)
from product_intelligence.semantic.contract_v2 import (
    SEMANTIC_PROMPT_VERSION_V2,
    SYSTEM_PROMPT_V2,
    build_semantic_prompt_v2,
)

LIVE_MODULE_PATH = (
    Path(__file__).resolve().parents[3]
    / "product_intelligence"
    / "evaluation"
    / "semantic_v2"
    / "live_capture.py"
)


@pytest.fixture(scope="module")
def corpus():
    return load_corpus_bundle()


CAPACITY_CASE = "V2Q-SSD-ATTR-CAPACITY-0024"  # label: NO_MATCH


# ---------------------------------------------------------------------------
# The scripted, recording test double (declared fixtures, not model
# output; no network)
# ---------------------------------------------------------------------------

#: Transport error codes the double can be scripted to fail with.
_TRANSPORT_ERROR_CODES = {
    "TIMEOUT",
    "DNS_ERROR",
    "TLS_ERROR",
    "CONNECTION_ERROR",
    "RATE_LIMITED",
    "HTTP_ERROR",
    "AUTHENTICATION_FAILED",
    "MODEL_NOT_FOUND",
    "PROVIDER_UNAVAILABLE",
    "PROVIDER_NOT_CONFIGURED",
    "INVALID_REQUEST_CONFIGURATION",
    "UNSUPPORTED_PARAMETER",
    "INVALID_PROVIDER_RESPONSE",
    "RESPONSE_DECODE_ERROR",
    "EMPTY_RESPONSE",
    "MALFORMED_JSON",
    "SCHEMA_INVALID",
    "MODEL_IDENTITY_MISMATCH",
    "CASE_REJECTED",
}

_SCHEMA_INVALID_RAW = json.dumps(
    {
        "decision": "NO_MATCH",
        "confidence": "HIGH",
        "reason_code": "NO_MATCH_OTHER",
        "matched_attributes": [],
        "conflicting_attributes": [],
        "missing_critical_attributes": [],
        "conflict_classes": ["NOT_A_CLASS"],
    }
)


class ScriptedTransport:
    """One scripted, recording model stand-in.

    ``scripts`` maps case_id -> tuple of outcome tokens consumed in
    order:

    * a str that is not an error token -> the raw model output
      (provider reports the pinned model);
    * ``"MALFORMED"`` -> raw ``"{broken"``;
    * ``"SCHEMA"`` -> raw JSON that fails the frozen validator;
    * ``"EMPTY"`` -> whitespace raw output;
    * ``"MISMATCH"`` -> well-formed raw, provider reports a different
      model;
    * a str in ``_TRANSPORT_ERROR_CODES`` -> a transport failure with
      that bounded error code.

    Consuming past the end of a case's script raises: the runner is
    thereby proven never to call a case more times than scripted
    (no unbounded retry, no best-of-N second opinion).
    """

    def __init__(
        self,
        corpus,
        scripts: dict[str, tuple[str, ...]] | None = None,
        *,
        sleep_seconds: float = 0.0,
    ) -> None:
        self.calls: list[dict] = []
        self.in_flight = 0
        self.max_in_flight = 0
        self._sleep_seconds = sleep_seconds
        self._prompt_to_case: dict[str, str] = {}
        for case in corpus.semantic_cases:
            prompt = build_semantic_prompt_v2(case.build_semantic_case())
            self._prompt_to_case[prompt.user_prompt] = case.case_id
        if scripts is None:
            scripts = {
                case.case_id: (default_response_for(case),)
                for case in corpus.semantic_cases
            }
        self.scripts = scripts
        self._consumed: dict[str, int] = {}

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ):
        case_id = self._prompt_to_case.get(user_prompt)
        assert case_id is not None, (
            "a prompt that is not the frozen builder output for an "
            "eligible semantic case was sent to the model"
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
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            if self._sleep_seconds:
                time.sleep(self._sleep_seconds)
            index = self._consumed.get(case_id, 0)
            script = self.scripts[case_id]
            assert index < len(script), (
                f"case {case_id} was called {index + 1} times but only "
                f"{len(script)} outcomes were scripted - the runner "
                "called again after a final outcome (unbounded retry / "
                "best-of-N)"
            )
            token = script[index]
            self._consumed[case_id] = index + 1
            if token in _TRANSPORT_ERROR_CODES:
                return TransportFailure(
                    error_type=token, transport_status=None, http_status=None
                )
            if token == "MALFORMED":
                raw = "{broken"
            elif token == "SCHEMA":
                raw = _SCHEMA_INVALID_RAW
            elif token == "EMPTY":
                raw = "   "
            elif token == "MISMATCH":
                # Any well-formed body: identity is checked before
                # parsing, so the label-consistent fixture is not the
                # point - the reported model is.
                raw = make_response("MATCH")
                return TransportResult(
                    raw_output=raw,
                    latency_ms=1.0,
                    provider_status="200",
                    provider_id="fake",
                    model_id=model,
                    provider_reported_model="not-the-pinned-model",
                    finish_reason="stop",
                    token_usage=None,
                )
            else:
                raw = token
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
        finally:
            self.in_flight -= 1


def default_scripts(corpus) -> dict[str, tuple[str, ...]]:
    return {
        case.case_id: (default_response_for(case),)
        for case in corpus.semantic_cases
    }


def one_case_overridden(corpus, case_id: str, script: tuple[str, ...]):
    scripts = default_scripts(corpus)
    scripts[case_id] = script
    return scripts


def do_run(
    corpus,
    tmp_path: Path,
    scripts: dict[str, tuple[str, ...]] | None = None,
    *,
    provider: str | None = None,
    model: str | None = None,
    run_id: str = "q3b-test-001",
    transport: ScriptedTransport | None = None,
    **config_kwargs,
):
    if provider is None and model is None:
        route = primary_route()
    else:
        route = (provider, model)
    transport = transport or ScriptedTransport(corpus, scripts)
    config = LiveCaptureConfig(
        provider=route[0],
        model=route[1],
        run_id=run_id,
        transport=transport,
        output_dir=tmp_path / "artifacts",
        **config_kwargs,
    )
    runner = LiveCaptureRunner(config, corpus)
    outcome = runner.run()
    manifest_path, capture_path = runner.write_artifacts(outcome)
    return runner, outcome, manifest_path, capture_path, transport


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def replay(corpus, capture_path):
    direct = load_direct_capture(capture_path)
    verify_direct_capture_against_corpus(direct, corpus)
    route = direct.target_route
    return direct, evaluate_direct_for_model(corpus, direct, *route)


def direct_pipeline(corpus, capture_path, generated_utc="2026-10-08T00:00:00Z"):
    direct, result = replay(corpus, capture_path)
    gates = evaluate_safety_gates(result)
    policy = load_policy(POLICY_PATH)
    te = (
        evaluate_thresholds(policy, result.metrics)
        if policy_applies_to(policy, corpus.corpus_id, corpus.corpus_version)
        else None
    )
    decision, rationale = decide(result, gates, policy, te)
    report = build_direct_report(
        result=result,
        gates=gates,
        policy=policy,
        threshold_evaluation=te,
        decision=decision,
        rationale=rationale,
        corpus=corpus,
        direct_capture=direct,
        generated_utc=generated_utc,
    )
    return direct, result, gates, policy, decision, rationale, report


# ===========================================================================
# 1. Exact model pinning
# ===========================================================================


class TestModelPinning:
    def test_pinned_primary_route_is_accepted(self) -> None:
        config = LiveCaptureConfig(
            provider=PRIMARY_ROUTE[0],
            model=PRIMARY_ROUTE[1],
            run_id="pin-1",
        )
        validate_live_capture_config(config)
        assert config.route_role == "PRIMARY"

    def test_pinned_fallback_route_is_accepted(self) -> None:
        config = LiveCaptureConfig(
            provider=FALLBACK_ROUTE[0],
            model=FALLBACK_ROUTE[1],
            run_id="pin-2",
        )
        validate_live_capture_config(config)
        assert config.route_role == "FALLBACK"

    @pytest.mark.parametrize(
        ("provider", "model"),
        [
            ("not-a-pinned-provider", PRIMARY_ROUTE[1]),
            (PRIMARY_ROUTE[0], "not-a-pinned-model"),
            (PRIMARY_ROUTE[0], FALLBACK_ROUTE[1]),
            (FALLBACK_ROUTE[0], PRIMARY_ROUTE[1]),
            ("amax ", PRIMARY_ROUTE[1]),  # whitespace is not exact
        ],
        ids=[
            "unknown-provider",
            "unknown-model",
            "primary-provider-fallback-model",
            "fallback-provider-primary-model",
            "whitespace-provider",
        ],
    )
    def test_unpinned_or_mixed_identities_fail_closed(
        self, provider, model
    ) -> None:
        config = LiveCaptureConfig(provider=provider, model=model, run_id="x")
        with pytest.raises(LiveCaptureConfigError, match="frozen V2 pinned"):
            validate_live_capture_config(config)

    def test_generation_parameters_are_the_frozen_pins(self) -> None:
        """The generation envelope is the frozen route's: not a
        caller parameter (no field), and the local constants are
        drift-pinned against the production frozen values."""
        import product_intelligence.semantic.runtime as rt
        import product_intelligence.semantic.runtime_v2 as rt_v2

        assert type(lc.LIVE_TEMPERATURE) is float
        assert lc.LIVE_TEMPERATURE == rt_v2.SEMANTIC_TEMPERATURE_V2
        assert lc.LIVE_TEMPERATURE == rt.SEMANTIC_TEMPERATURE
        assert lc.LIVE_MAX_TOKENS == rt_v2.SEMANTIC_MAX_TOKENS_V2
        assert lc.LIVE_MAX_TOKENS == rt.SEMANTIC_MAX_TOKENS
        assert (
            lc.LIVE_DEFAULT_REQUEST_TIMEOUT_SECONDS
            == rt.DEFAULT_REQUEST_TIMEOUT_SECONDS
        )
        assert (
            lc.LIVE_MAX_REQUEST_TIMEOUT_SECONDS
            == rt.MAX_REQUEST_TIMEOUT_SECONDS
        )
        # Not caller-configurable: the config has no such fields.
        fields = set(LiveCaptureConfig.__dataclass_fields__)
        assert "temperature" not in fields and "max_tokens" not in fields

    def test_classification_mirror_matches_the_frozen_runtime(self) -> None:
        """The live runner's transport-code -> status table is exactly
        the frozen V2 runtime's (drift pin)."""
        import product_intelligence.semantic.runtime_v2 as rt_v2

        mirror = {
            code: status.value
            for code, status in rt_v2._V2_TRANSPORT_ERROR_TO_STATUS.items()
        }
        assert lc.LIVE_TRANSPORT_ERROR_TO_STATUS == mirror


# ===========================================================================
# 2. Frozen prompt fidelity
# ===========================================================================


class TestPromptFidelity:
    def test_every_sent_prompt_is_the_frozen_builder_output(
        self, corpus, tmp_path
    ) -> None:
        _, _, _, capture_path, transport = do_run(corpus, tmp_path)
        assert capture_path is not None
        assert len(transport.calls) == 43
        for call in transport.calls:
            case = corpus.case(call["case_id"])
            prompt = build_semantic_prompt_v2(case.build_semantic_case())
            assert call["system_prompt"] == SYSTEM_PROMPT_V2
            assert call["user_prompt"] == prompt.user_prompt
            assert call["model"] == primary_route()[1]
            assert call["temperature"] == lc.LIVE_TEMPERATURE
            assert call["max_tokens"] == lc.LIVE_MAX_TOKENS

    def test_the_manifest_binds_the_real_system_prompt_by_digest(
        self, corpus, tmp_path
    ) -> None:
        _, _, manifest_path, _, _ = do_run(corpus, tmp_path)
        manifest = read_json(manifest_path)
        assert manifest["system_prompt_sha256"] == canonical_sha256(
            {"text": SYSTEM_PROMPT_V2}
        )
        # The same construction the offline report uses to bind the
        # real frozen text (no drift between manifest and report).
        from product_intelligence.evaluation.semantic_v2.report import (
            _system_prompt_digest,
        )

        assert manifest["system_prompt_sha256"] == _system_prompt_digest()

    def test_the_artifact_carries_the_frozen_contract_identity(
        self, corpus, tmp_path
    ) -> None:
        _, _, manifest_path, capture_path, _ = do_run(corpus, tmp_path)
        document = read_json(capture_path)
        assert document["prompt_version"] == PROMPT_VERSION_V2
        assert document["prompt_version"] == SEMANTIC_PROMPT_VERSION_V2
        assert document["semantic_contract"] == SEMANTIC_CONTRACT_VERSION_V2
        assert document["corpus_id"] == corpus.corpus_id
        assert document["corpus_version"] == corpus.corpus_version
        assert document["corpus_digest"] == corpus.corpus_digest
        manifest = read_json(manifest_path)
        assert manifest["corpus_digest"] == corpus.corpus_digest
        assert manifest["prompt_version"] == PROMPT_VERSION_V2
        # Per-case prompt digests cover exactly the 43 eligible cases.
        assert set(manifest["cases"]) == {
            case.case_id for case in corpus.semantic_cases
        }
        for case in corpus.semantic_cases:
            prompt = build_semantic_prompt_v2(case.build_semantic_case())
            expected = canonical_sha256(
                {
                    "case_id": case.case_id,
                    "system_prompt": prompt.system_prompt,
                    "user_prompt": prompt.user_prompt,
                }
            )
            assert manifest["cases"][case.case_id]["prompt_sha256"] == expected


# ===========================================================================
# 3. Transport boundary
# ===========================================================================


class TestTransportBoundary:
    def test_the_module_imports_no_live_transport_at_module_level(
        self,
    ) -> None:
        """Import purity: the live transport reference is lazy (inside
        transport construction only) - module import loads no network
        client. (If another test already imported the transport we can
        only prove the AST half; global module state is not
        disturbed.)"""
        tree = ast.parse(LIVE_MODULE_PATH.read_text(encoding="utf-8"))
        module_level_modules = set()
        for node in tree.body:
            if isinstance(node, ast.Import):
                module_level_modules.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                module_level_modules.add(node.module)
        assert "product_intelligence.semantic.transport" not in (
            module_level_modules
        )
        assert "product_intelligence.semantic.runtime" not in (
            module_level_modules
        )
        present_before = (
            "product_intelligence.semantic.transport" in sys.modules
        )
        import product_intelligence.evaluation.semantic_v2.live_capture  # noqa: F401

        if not present_before:
            assert (
                "product_intelligence.semantic.transport" not in sys.modules
            )

    def test_transport_construction_uses_the_approved_mechanism(
        self, monkeypatch
    ) -> None:
        monkeypatch.setenv(
            "PI_SEMANTIC_AMAX_BASE_URL", "https://sentinel-endpoint.example"
        )
        monkeypatch.setenv("PI_SEMANTIC_AMAX_API_KEY", "sentinel-key-value")
        transport = build_live_transport("amax", 123.4)
        # The approved provider-configuration mechanism (the FU3A
        # transport factory) is what built it - proven by its exact
        # configured state (values stay in the object, never printed).
        assert transport._base_url == "https://sentinel-endpoint.example"
        assert transport._api_key == "sentinel-key-value"
        assert transport._request_timeout_seconds == 123.4

    def test_an_unconfigured_provider_fails_closed_before_any_call(
        self, corpus, tmp_path, monkeypatch
    ) -> None:
        monkeypatch.delenv("PI_SEMANTIC_AMAX_BASE_URL", raising=False)
        monkeypatch.setenv(
            "PI_SEMANTIC_AMAX_API_KEY", "sentinel-key-value"
        )
        config = LiveCaptureConfig(
            provider=PRIMARY_ROUTE[0],
            model=PRIMARY_ROUTE[1],
            run_id="unconfigured-1",
            output_dir=tmp_path / "artifacts",
        )
        with pytest.raises(LiveCaptureConfigError, match="not configured") as exc:
            LiveCaptureRunner(config, corpus)
        # The failure is bounded: no credential value leaks.
        assert "sentinel-key-value" not in str(exc.value)
        # And nothing was written.
        assert not (tmp_path / "artifacts").exists()

    def test_an_injected_transport_needs_no_environment(
        self, corpus, tmp_path, monkeypatch
    ) -> None:
        monkeypatch.delenv("PI_SEMANTIC_AMAX_BASE_URL", raising=False)
        monkeypatch.delenv("PI_SEMANTIC_AMAX_API_KEY", raising=False)
        monkeypatch.delenv("PI_SEMANTIC_VLLM_262K_BASE_URL", raising=False)
        monkeypatch.delenv("PI_SEMANTIC_VLLM_262K_API_KEY", raising=False)
        _, _, manifest_path, capture_path, _ = do_run(corpus, tmp_path)
        assert capture_path is not None

    def test_the_runner_reads_no_environment_directly(self) -> None:
        """All environment access stays inside the approved transport
        adapter: the runner module names no os.environ read of its
        own."""
        text = LIVE_MODULE_PATH.read_text(encoding="utf-8")
        assert "os.environ" not in text
        tree = ast.parse(text)
        environment_reads = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
            and node.attr == "environ"
        ]
        assert not environment_reads


# ===========================================================================
# 4. No credential leakage
# ===========================================================================


class TestNoCredentialLeakage:
    def test_artifacts_contain_no_credential_or_endpoint_material(
        self, corpus, tmp_path, monkeypatch
    ) -> None:
        monkeypatch.setenv(
            "PI_SEMANTIC_AMAX_BASE_URL", "https://secret-endpoint.example"
        )
        monkeypatch.setenv("PI_SEMANTIC_AMAX_API_KEY", "secret-key-value")
        _, _, manifest_path, capture_path, _ = do_run(corpus, tmp_path)
        capture_text = capture_path.read_text(encoding="utf-8")
        manifest_text = manifest_path.read_text(encoding="utf-8")
        for text in (capture_text, manifest_text):
            assert "secret-key-value" not in text
            assert "secret-endpoint.example" not in text
            assert "Authorization" not in text
            assert "Bearer" not in text
        manifest = read_json(manifest_path)
        # Key presence is a bare bool - never the value - and the
        # transport section carries no other field at all.
        assert manifest["transport_parameters"]["api_key_configured"] in (
            True,
            False,
        )
        transport_params = manifest["transport_parameters"]
        assert set(transport_params) == {
            "request_timeout_seconds",
            "max_concurrency",
            "transport_class",
            "api_key_configured",
        }

    def test_the_summary_is_secret_free(self, corpus, tmp_path) -> None:
        runner, outcome, _, _, _ = do_run(corpus, tmp_path)
        summary = json.dumps(runner.summary(outcome))
        for token in ("Authorization", "Bearer", "api_key", "http"):
            assert token not in summary, f"summary names {token!r}"


# ===========================================================================
# 5. Timeout handling
# ===========================================================================


class TestTimeoutHandling:
    @pytest.mark.parametrize(
        "timeout",
        [0, -1, 3600.1, float("inf"), float("nan"), "abc", True],
        ids=["zero", "negative", "above-bound", "inf", "nan", "str", "bool"],
    )
    def test_invalid_timeouts_fail_closed(self, timeout) -> None:
        config = LiveCaptureConfig(
            provider=PRIMARY_ROUTE[0],
            model=PRIMARY_ROUTE[1],
            run_id="t-1",
            request_timeout_seconds=timeout,
        )
        with pytest.raises(LiveCaptureConfigError, match="request_timeout"):
            validate_live_capture_config(config)

    def test_valid_timeouts_are_accepted(self) -> None:
        for timeout in (1.0, 300.0, 3600.0):
            config = LiveCaptureConfig(
                provider=PRIMARY_ROUTE[0],
                model=PRIMARY_ROUTE[1],
                run_id="t-2",
                request_timeout_seconds=timeout,
            )
            validate_live_capture_config(config)  # no raise

    def test_a_timeout_failure_is_classified_and_preserved(
        self, corpus, tmp_path
    ) -> None:
        # TIMEOUT is retryable: the bounded policy re-attempts the
        # identical request up to max_attempts (3); the final bounded
        # status is recorded verbatim.
        scripts = one_case_overridden(
            corpus, CAPACITY_CASE, ("TIMEOUT", "TIMEOUT", "TIMEOUT")
        )
        _, _, manifest_path, capture_path, transport = do_run(
            corpus, tmp_path, scripts
        )
        document = read_json(capture_path)
        record = next(
            r for r in document["records"] if r["case_id"] == CAPACITY_CASE
        )
        assert record["execution_status"] == "TIMEOUT"
        assert record["raw_output"] is None
        assert len(transport.calls) == 45  # 43 + two bounded retries
        case_info = read_json(manifest_path)["cases"][CAPACITY_CASE]
        assert case_info["final_status"] == "TIMEOUT"
        assert case_info["attempts"] == 3
        assert case_info["retried"] is True


# ===========================================================================
# 6. Bounded retry behavior
# ===========================================================================


class TestBoundedRetry:
    def test_retryable_then_success_records_the_single_real_output(
        self, corpus, tmp_path
    ) -> None:
        good = default_response_for(corpus.case(CAPACITY_CASE))
        scripts = one_case_overridden(
            corpus, CAPACITY_CASE, ("CONNECTION_ERROR", good)
        )
        _, _, manifest_path, capture_path, transport = do_run(
            corpus, tmp_path, scripts
        )
        document = read_json(capture_path)
        record = next(
            r for r in document["records"] if r["case_id"] == CAPACITY_CASE
        )
        # The first attempt produced NO model output; the only real
        # response (the second attempt) is what is preserved.
        assert record["execution_status"] == "OK"
        assert record["raw_output"] == good
        case_calls = [
            c for c in transport.calls if c["case_id"] == CAPACITY_CASE
        ]
        assert len(case_calls) == 2
        manifest = read_json(manifest_path)
        assert manifest["cases"][CAPACITY_CASE]["attempts"] == 2
        assert manifest["cases"][CAPACITY_CASE]["retried"] is True

    def test_retries_are_hard_bounded(self, corpus, tmp_path) -> None:
        # Four TIMEOUT tokens scripted; the policy allows 3 attempts
        # total, so the fourth must never be consumed (the double
        # raises on over-consumption).
        scripts = one_case_overridden(
            corpus,
            CAPACITY_CASE,
            ("TIMEOUT", "TIMEOUT", "TIMEOUT", "TIMEOUT"),
        )
        _, _, manifest_path, capture_path, transport = do_run(
            corpus, tmp_path, scripts
        )
        case_calls = [
            c for c in transport.calls if c["case_id"] == CAPACITY_CASE
        ]
        assert len(case_calls) == 3
        record = next(
            r
            for r in read_json(capture_path)["records"]
            if r["case_id"] == CAPACITY_CASE
        )
        assert record["execution_status"] == "TIMEOUT"
        assert (
            read_json(manifest_path)["cases"][CAPACITY_CASE]["attempts"] == 3
        )

    @pytest.mark.parametrize(
        "code",
        sorted(lc.LIVE_RETRYABLE_STATUSES),
        ids=sorted(lc.LIVE_RETRYABLE_STATUSES),
    )
    def test_every_retryable_status_is_retried_then_recorded(
        self, corpus, tmp_path, code
    ) -> None:
        good = default_response_for(corpus.case(CAPACITY_CASE))
        scripts = one_case_overridden(corpus, CAPACITY_CASE, (code, good))
        _, _, _, capture_path, transport = do_run(corpus, tmp_path, scripts)
        case_calls = [
            c for c in transport.calls if c["case_id"] == CAPACITY_CASE
        ]
        assert len(case_calls) == 2
        record = next(
            r
            for r in read_json(capture_path)["records"]
            if r["case_id"] == CAPACITY_CASE
        )
        assert record["execution_status"] == "OK"

    def test_max_attempts_bound_is_enforced(self) -> None:
        for bad in (0, 4, True):
            config = LiveCaptureConfig(
                provider=PRIMARY_ROUTE[0],
                model=PRIMARY_ROUTE[1],
                run_id="m-1",
                max_attempts=bad,
            )
            with pytest.raises(LiveCaptureConfigError, match="max_attempts"):
                validate_live_capture_config(config)
        for good in (1, 2, 3):
            config = LiveCaptureConfig(
                provider=PRIMARY_ROUTE[0],
                model=PRIMARY_ROUTE[1],
                run_id="m-2",
                max_attempts=good,
            )
            validate_live_capture_config(config)  # no raise

    def test_the_retry_policy_is_complete_and_disjoint(self) -> None:
        """Every bounded status belongs to EXACTLY one policy bucket;
        the retryable bucket is the transient transport set only (no
        output-contract failure, no semantic outcome may be retried)."""
        buckets = (
            lc.LIVE_RETRYABLE_STATUSES,
            lc.LIVE_FINAL_STATUSES,
            lc.LIVE_ABORT_STATUSES,
            lc.LIVE_CASE_LOCAL_STATUSES,
        )
        universe = set().union(*buckets)
        assert not (
            lc.LIVE_RETRYABLE_STATUSES
            & (lc.LIVE_FINAL_STATUSES | lc.LIVE_ABORT_STATUSES | lc.LIVE_CASE_LOCAL_STATUSES)
        )
        assert not (lc.LIVE_FINAL_STATUSES & (lc.LIVE_ABORT_STATUSES | lc.LIVE_CASE_LOCAL_STATUSES))
        assert lc.LIVE_ABORT_STATUSES.isdisjoint(lc.LIVE_CASE_LOCAL_STATUSES)
        # The retryable set never contains an output/semantic outcome.
        assert "OK" not in lc.LIVE_RETRYABLE_STATUSES
        assert "MALFORMED_JSON" not in lc.LIVE_RETRYABLE_STATUSES
        assert "SCHEMA_INVALID" not in lc.LIVE_RETRYABLE_STATUSES
        assert "EMPTY_RESPONSE" not in lc.LIVE_RETRYABLE_STATUSES
        assert "INVALID_RESPONSE" not in lc.LIVE_RETRYABLE_STATUSES
        assert "MODEL_IDENTITY_MISMATCH" not in lc.LIVE_RETRYABLE_STATUSES
        assert "HTTP_ERROR" not in lc.LIVE_RETRYABLE_STATUSES
        # Every in-document status is covered by the policy universe.
        from product_intelligence.evaluation.semantic_v2.direct_capture import (
            DIRECT_EXECUTION_STATUSES,
        )

        assert DIRECT_EXECUTION_STATUSES <= universe
        # The policy universe is exactly the direct-capture vocabulary
        # plus the three out-of-vocabulary statuses the transport can
        # still report per case (PROVIDER_NOT_CONFIGURED is
        # pre-execution: a construction-time configuration failure,
        # not a per-case policy bucket).
        assert universe == DIRECT_EXECUTION_STATUSES | {
            "INVALID_REQUEST_CONFIGURATION",
            "UNSUPPORTED_PARAMETER",
            "CASE_REJECTED",
        }


# ===========================================================================
# 7. No semantic-error retries / 8. No best-of-N
# ===========================================================================


class TestNoSemanticErrorRetries:
    @pytest.mark.parametrize(
        ("token", "status"),
        [
            ("MALFORMED", "MALFORMED_JSON"),
            ("SCHEMA", "SCHEMA_INVALID"),
            ("EMPTY", "EMPTY_RESPONSE"),
            ("MISMATCH", "MODEL_IDENTITY_MISMATCH"),
            ("INVALID_PROVIDER_RESPONSE", "INVALID_RESPONSE"),
            ("RESPONSE_DECODE_ERROR", "MALFORMED_JSON"),
            ("HTTP_ERROR", "HTTP_ERROR"),
        ],
        ids=[
            "malformed-json",
            "schema-invalid",
            "empty-response",
            "identity-mismatch",
            "invalid-provider-response",
            "response-decode-error",
            "http-error",
        ],
    )
    def test_an_output_or_identity_failure_is_final_after_one_call(
        self, corpus, tmp_path, token, status
    ) -> None:
        # Even though a good response is scripted second, the runner
        # must never send it: the first bounded outcome is final.
        good = default_response_for(corpus.case(CAPACITY_CASE))
        scripts = one_case_overridden(
            corpus, CAPACITY_CASE, (token, good)
        )
        _, _, manifest_path, capture_path, transport = do_run(
            corpus, tmp_path, scripts
        )
        case_calls = [
            c for c in transport.calls if c["case_id"] == CAPACITY_CASE
        ]
        assert len(case_calls) == 1, f"{token} was retried"
        record = next(
            r
            for r in read_json(capture_path)["records"]
            if r["case_id"] == CAPACITY_CASE
        )
        assert record["execution_status"] == status
        assert record["raw_output"] is None
        assert (
            read_json(manifest_path)["cases"][CAPACITY_CASE]["attempts"]
            == 1
        )

    def test_an_unfavorable_semantic_decision_is_never_retried(
        self, corpus, tmp_path
    ) -> None:
        """The capacity case's label is NO_MATCH. A model that answers
        MATCH (schema-valid, semantically wrong) is final: exactly one
        call, the wrong answer preserved, and the offline replay
        scores FALSE_MATCH on THAT answer - a later (scripted) correct
        answer is never sent and never selected."""
        wrong = make_response("MATCH")
        right = default_response_for(corpus.case(CAPACITY_CASE))
        scripts = one_case_overridden(
            corpus, CAPACITY_CASE, (wrong, right)
        )
        _, _, _, capture_path, transport = do_run(corpus, tmp_path, scripts)
        case_calls = [
            c for c in transport.calls if c["case_id"] == CAPACITY_CASE
        ]
        assert len(case_calls) == 1
        record = next(
            r
            for r in read_json(capture_path)["records"]
            if r["case_id"] == CAPACITY_CASE
        )
        assert record["raw_output"] == wrong
        _, result = replay(corpus, capture_path)
        outcome = next(
            o for o in result.outcomes if o.case_id == CAPACITY_CASE
        )
        assert outcome.verdict == "FALSE_MATCH"

    def test_a_successful_first_attempt_never_gets_a_second_call(
        self, corpus, tmp_path
    ) -> None:
        good = default_response_for(corpus.case(CAPACITY_CASE))
        scripts = one_case_overridden(
            corpus, CAPACITY_CASE, (good, make_response("NO_MATCH"))
        )
        _, _, _, capture_path, transport = do_run(corpus, tmp_path, scripts)
        case_calls = [
            c for c in transport.calls if c["case_id"] == CAPACITY_CASE
        ]
        assert len(case_calls) == 1
        record = next(
            r
            for r in read_json(capture_path)["records"]
            if r["case_id"] == CAPACITY_CASE
        )
        assert record["raw_output"] == good


class TestNoBestOfN:
    def test_exactly_one_record_per_case(self, corpus, tmp_path) -> None:
        _, _, _, capture_path, _ = do_run(corpus, tmp_path)
        document = read_json(capture_path)
        ids = [r["case_id"] for r in document["records"]]
        assert len(ids) == 43
        assert len(set(ids)) == 43
        # The frozen loader itself rejects duplicates (the schema is
        # one record per case).
        tampered = json.loads(json.dumps(document))
        tampered["records"].append(dict(tampered["records"][0]))
        path = tmp_path / "dup.json"
        path.write_text(json.dumps(tampered), encoding="utf-8")
        with pytest.raises(Exception, match="duplicate"):
            load_direct_capture(path)

    def test_an_invalid_output_is_never_replaced_by_a_later_one(
        self, corpus, tmp_path
    ) -> None:
        """MALFORMED_JSON is a final output-contract outcome: the case
        is recorded as MALFORMED_JSON (RUNTIME_FAILURE at replay),
        never silently re-sent and never swapped for a later
        well-formed answer."""
        good = default_response_for(corpus.case(CAPACITY_CASE))
        scripts = one_case_overridden(
            corpus, CAPACITY_CASE, ("MALFORMED", good)
        )
        _, _, _, capture_path, _ = do_run(corpus, tmp_path, scripts)
        record = next(
            r
            for r in read_json(capture_path)["records"]
            if r["case_id"] == CAPACITY_CASE
        )
        assert record["execution_status"] == "MALFORMED_JSON"
        _, result = replay(corpus, capture_path)
        outcome = next(
            o for o in result.outcomes if o.case_id == CAPACITY_CASE
        )
        assert outcome.state == "RUNTIME_FAILURE"
        assert outcome.runtime_failure_status == "MALFORMED_JSON"


# ===========================================================================
# 9. No contract-negative model calls
# ===========================================================================


class TestContractNegativeExclusion:
    def test_no_contract_negative_case_is_ever_rendered_or_sent(
        self, corpus, tmp_path
    ) -> None:
        _, _, manifest_path, capture_path, transport = do_run(corpus, tmp_path)
        negative_ids = {
            c.case_id for c in corpus.contract_negative_cases
        }
        assert len(negative_ids) == 13
        sent_ids = {call["case_id"] for call in transport.calls}
        assert not (sent_ids & negative_ids)
        document = read_json(capture_path)
        assert not ({r["case_id"] for r in document["records"]} & negative_ids)
        manifest = read_json(manifest_path)
        assert not (set(manifest["cases"]) & negative_ids)

    def test_the_document_records_exactly_the_43_eligible_cases(
        self, corpus, tmp_path
    ) -> None:
        _, _, _, capture_path, _ = do_run(corpus, tmp_path)
        document = read_json(capture_path)
        assert len(document["records"]) == 43
        assert {r["case_id"] for r in document["records"]} == {
            c.case_id for c in corpus.semantic_cases
        }


# ===========================================================================
# 10. Complete eligible-case traversal
# ===========================================================================


class TestCompleteTraversal:
    def test_all_43_cases_are_attempted_in_corpus_order(
        self, corpus, tmp_path
    ) -> None:
        _, _, _, capture_path, transport = do_run(corpus, tmp_path)
        corpus_order = [c.case_id for c in corpus.semantic_cases]
        assert [c["case_id"] for c in transport.calls] == corpus_order
        document = read_json(capture_path)
        assert [r["case_id"] for r in document["records"]] == corpus_order

    def test_a_completed_run_leaves_no_case_unaccounted_for(
        self, corpus, tmp_path
    ) -> None:
        runner, outcome, manifest_path, capture_path, _ = do_run(
            corpus, tmp_path
        )
        manifest = read_json(manifest_path)
        assert manifest["run_status"] == "COMPLETED"
        assert manifest["not_attempted_case_ids"] == []
        assert manifest["undocumented_cases"] == {}
        assert manifest["abort"] is None
        assert len(manifest["attempted_case_ids"]) == 43
        assert runner.summary(outcome)["run_status"] == "COMPLETED"


# ===========================================================================
# 11. Failure preservation
# ===========================================================================


class TestFailurePreservation:
    @pytest.mark.parametrize(
        ("token", "status"),
        [
            ("SCHEMA", "SCHEMA_INVALID"),
            ("EMPTY", "EMPTY_RESPONSE"),
            ("MISMATCH", "MODEL_IDENTITY_MISMATCH"),
            ("HTTP_ERROR", "HTTP_ERROR"),
        ],
        ids=[
            "schema-invalid",
            "empty-response",
            "identity-mismatch",
            "http-error",
        ],
    )
    def test_failure_classifications_are_preserved_verbatim(
        self, corpus, tmp_path, token, status
    ) -> None:
        scripts = one_case_overridden(corpus, CAPACITY_CASE, (token,))
        _, _, _, capture_path, _ = do_run(corpus, tmp_path, scripts)
        document = read_json(capture_path)
        record = next(
            r for r in document["records"] if r["case_id"] == CAPACITY_CASE
        )
        assert record["execution_status"] == status
        assert record["raw_output"] is None
        _, result = replay(corpus, capture_path)
        outcome = next(
            o for o in result.outcomes if o.case_id == CAPACITY_CASE
        )
        assert outcome.state == "RUNTIME_FAILURE"
        assert outcome.runtime_failure_status == status
        assert outcome.model_decision is None  # never a semantic call

    def test_a_run_abort_preserves_the_attempted_evidence(
        self, corpus, tmp_path
    ) -> None:
        """OK on the first case, AUTHENTICATION_FAILED on the second:
        the run aborts (no third call), the attempted evidence is
        preserved, and the 41 unattempted cases are named - the
        replay can never pass (41 NOT_CAPTURED)."""
        second = corpus.semantic_cases[1]
        scripts = one_case_overridden(
            corpus, second.case_id, ("AUTHENTICATION_FAILED",)
        )
        runner, outcome, manifest_path, capture_path, transport = do_run(
            corpus, tmp_path, scripts
        )
        manifest = read_json(manifest_path)
        assert manifest["run_status"] == "ABORTED_AUTHENTICATION_FAILED"
        assert manifest["abort"] == {
            "case_id": second.case_id,
            "code": "AUTHENTICATION_FAILED",
        }
        assert manifest["attempted_case_ids"] == [
            corpus.semantic_cases[0].case_id,
            second.case_id,
        ]
        assert len(manifest["not_attempted_case_ids"]) == 41
        # Only the two attempted, in-vocabulary records exist.
        document = read_json(capture_path)
        assert {r["case_id"] for r in document["records"]} == {
            corpus.semantic_cases[0].case_id,
            second.case_id,
        }
        assert len(transport.calls) == 2  # no call after the abort
        _, result = replay(corpus, capture_path)
        counts = result.metrics["counts"]
        assert counts["evaluated_cases"] == 1
        assert counts["runtime_failure_count"] == 1
        assert counts["not_captured"] == 41
        decision, _ = self._decide(corpus, capture_path)
        # Under the DRAFT policy POLICY_PENDING outranks
        # INCOMPLETE_COVERAGE; either way it is never a pass.
        assert decision in ("POLICY_PENDING", "INCOMPLETE_COVERAGE")
        assert decision != "QUALIFIED"

    def _decide(self, corpus, capture_path):
        from product_intelligence.evaluation.semantic_v2.evaluator import (
            evaluate_direct_for_model,
        )

        direct = load_direct_capture(capture_path)
        result = evaluate_direct_for_model(
            corpus, direct, *direct.target_route
        )
        gates = evaluate_safety_gates(result)
        policy = load_policy(POLICY_PATH)
        te = evaluate_thresholds(policy, result.metrics)
        return decide(result, gates, policy, te)

    def test_an_out_of_vocabulary_abort_writes_manifest_only(
        self, corpus, tmp_path
    ) -> None:
        """INVALID_REQUEST_CONFIGURATION breaks the run before any
        in-vocabulary record can exist for the failing case: the
        manifest documents the bounded code, no capture document is
        written (nothing can be misread as a pass), and the unattempted
        cases are named."""
        first = corpus.semantic_cases[0]
        scripts = one_case_overridden(
            corpus, first.case_id, ("INVALID_REQUEST_CONFIGURATION",)
        )
        runner, outcome, manifest_path, capture_path, _ = do_run(
            corpus, tmp_path, scripts
        )
        assert capture_path is None
        manifest = read_json(manifest_path)
        assert manifest["run_status"] == "ABORTED_INVALID_REQUEST_CONFIGURATION"
        assert manifest["undocumented_cases"] == {
            first.case_id: "INVALID_REQUEST_CONFIGURATION"
        }
        assert manifest["attempted_case_ids"] == [first.case_id]
        assert len(manifest["not_attempted_case_ids"]) == 42

    def test_case_rejected_is_case_local_and_replays_not_captured(
        self, corpus, tmp_path
    ) -> None:
        """A content-policy rejection is case-local (frozen transport
        vocabulary): the run continues, the case is documented in the
        manifest only (its status is outside the direct-capture
        vocabulary, so it has no document record), and it replays as
        NOT_CAPTURED - a coverage shortfall, never a pass."""
        victim = corpus.semantic_cases[4]
        scripts = one_case_overridden(
            corpus, victim.case_id, ("CASE_REJECTED",)
        )
        _, outcome, manifest_path, capture_path, transport = do_run(
            corpus, tmp_path, scripts
        )
        assert len(transport.calls) == 43  # the run continued
        manifest = read_json(manifest_path)
        assert manifest["run_status"] == "COMPLETED"
        assert manifest["undocumented_cases"] == {
            victim.case_id: "CASE_REJECTED"
        }
        document = read_json(capture_path)
        assert len(document["records"]) == 42
        _, result = replay(corpus, capture_path)
        victim_outcome = next(
            o for o in result.outcomes if o.case_id == victim.case_id
        )
        assert victim_outcome.state == "NOT_CAPTURED"
        decision, _ = self._decide(corpus, capture_path)
        # Under the DRAFT policy POLICY_PENDING outranks
        # INCOMPLETE_COVERAGE; either way it is never a pass.
        assert decision in ("POLICY_PENDING", "INCOMPLETE_COVERAGE")
        assert decision != "QUALIFIED"


# ===========================================================================
# 12. Independent model capture
# ===========================================================================


class TestIndependentModelCapture:
    def test_two_models_produce_two_separate_independent_documents(
        self, corpus, tmp_path
    ) -> None:
        _, _, _, p_path, _ = do_run(corpus, tmp_path / "a", run_id="q3b-p")
        f_route = fallback_route()
        _, _, _, f_path, _ = do_run(
            corpus,
            tmp_path / "b",
            provider=f_route[0],
            model=f_route[1],
            run_id="q3b-f",
        )
        p_doc, p_result = replay(corpus, p_path)
        f_doc, f_result = replay(corpus, f_path)
        assert p_doc.target_route == primary_route()
        assert f_doc.target_route == f_route
        assert p_result.metrics["counts"]["evaluated_cases"] == 43
        assert f_result.metrics["counts"]["evaluated_cases"] == 43
        # Separate runs, separate identities.
        assert p_doc.capture_run_id != f_doc.capture_run_id
        assert p_doc.target_provider != f_doc.target_provider

    def test_a_document_never_transfers_to_the_other_identity(
        self, corpus, tmp_path
    ) -> None:
        _, _, _, p_path, _ = do_run(corpus, tmp_path)
        p_doc = load_direct_capture(p_path)
        with pytest.raises(
            QualificationContractError, match="bound to"
        ):
            evaluate_direct_for_model(
                corpus, p_doc, *fallback_route()
            )


# ===========================================================================
# 13. Capture schema validation
# ===========================================================================


class TestCaptureSchemaValidation:
    def test_the_written_document_round_trips_the_frozen_loader(
        self, corpus, tmp_path
    ) -> None:
        _, _, _, capture_path, _ = do_run(corpus, tmp_path)
        document = load_direct_capture(capture_path)  # must not raise
        verify_direct_capture_against_corpus(document, corpus)
        raw = read_json(capture_path)
        assert set(raw) == {
            "capture_mode",
            "direct_capture_schema_version",
            "target_provider",
            "target_model",
            "corpus_id",
            "corpus_version",
            "corpus_digest",
            "semantic_contract",
            "prompt_version",
            "capture_run_id",
            "captured_at",
            "captured_by",
            "notes",
            "records",
        }
        assert raw["capture_mode"] == DIRECT_CAPTURE_MODE
        assert raw["direct_capture_schema_version"] == (
            DIRECT_CAPTURE_SCHEMA_VERSION
        )
        for record in raw["records"]:
            assert set(record) == {"case_id", "execution_status", "raw_output"}

    def test_a_tampered_corpus_digest_fails_closed_at_verification(
        self, corpus, tmp_path
    ) -> None:
        _, _, _, capture_path, _ = do_run(corpus, tmp_path)
        document = read_json(capture_path)
        document["corpus_digest"] = "f" * 64
        path = tmp_path / "tampered.json"
        path.write_text(json.dumps(document), encoding="utf-8")
        loaded = load_direct_capture(path)  # shape is still valid...
        with pytest.raises(Exception, match="different corpus"):
            verify_direct_capture_against_corpus(loaded, corpus)
        with pytest.raises(QualificationContractError):
            evaluate_direct_for_model(
                corpus, loaded, *loaded.target_route
            )

    def test_a_tampered_record_status_fails_closed_at_load(
        self, corpus, tmp_path
    ) -> None:
        _, _, _, capture_path, _ = do_run(corpus, tmp_path)
        document = read_json(capture_path)
        document["records"][0]["execution_status"] = "CASE_REJECTED"
        path = tmp_path / "tampered.json"
        path.write_text(json.dumps(document), encoding="utf-8")
        with pytest.raises(Exception, match="unknown bounded status"):
            load_direct_capture(path)


# ===========================================================================
# 14. Offline replay fidelity
# ===========================================================================


class TestOfflineReplayFidelity:
    def test_a_full_correct_capture_replays_to_43_evaluated(
        self, corpus, tmp_path
    ) -> None:
        _, _, _, capture_path, _ = do_run(corpus, tmp_path)
        _, result = replay(corpus, capture_path)
        counts = result.metrics["counts"]
        assert counts["eligible_semantic_cases"] == 43
        assert counts["evaluated_cases"] == 43
        assert counts["not_captured"] == 0
        assert counts["runtime_failure_count"] == 0
        assert counts["capture_integrity_failures"] == 0
        assert counts["not_invoked"] == 0
        rate = result.metrics["valid_structured_response_rate"]
        assert rate["numerator"] == 43 and rate["denominator"] == 43

    def test_the_replay_decision_stays_policy_pending(
        self, corpus, tmp_path
    ) -> None:
        _, _, _, capture_path, _ = do_run(corpus, tmp_path)
        _, result, gates, policy, decision, rationale, report = (
            direct_pipeline(corpus, capture_path)
        )
        assert policy.status == "DRAFT"
        assert decision == "POLICY_PENDING"
        assert decision != "QUALIFIED"
        assert all(g.passed for g in gates.values())
        assert report["authority"]["granted"] is False
        assert report["authority"]["v2_authority_qualified"] is False
        render_markdown(report)  # renders (still offline)

    def test_the_direct_report_builds_verifies_and_binds_the_run(
        self, corpus, tmp_path
    ) -> None:
        runner, _, _, capture_path, _ = do_run(
            corpus, tmp_path, run_id="q3b-replay-1"
        )
        _, _, _, _, _, _, report = direct_pipeline(corpus, capture_path)
        verify_direct_report(report, corpus)  # must not raise
        assert report["report_kind"] == (
            "SEMANTIC_V2_DIRECT_MODEL_QUALIFICATION_OFFLINE"
        )
        assert report["capture_mode"] == DIRECT_CAPTURE_MODE
        capture_section = report["capture"]
        assert capture_section["capture_run_id"] == "q3b-replay-1"
        assert report["corpus"]["corpus_digest"] == corpus.corpus_digest
        assert report["contract"]["system_prompt_digest"] == canonical_sha256(
            {"text": SYSTEM_PROMPT_V2}
        )
        assert report["model"]["provider"] == primary_route()[0]
        assert report["model"]["model"] == primary_route()[1]


# ===========================================================================
# 15. No production execution imports
# ===========================================================================


class TestNoProductionExecutionImports:
    def test_running_the_live_capture_pulls_no_production_surface(
        self, corpus, tmp_path
    ) -> None:
        prefixes = (
            "product_intelligence.execution",
            "product_intelligence.runs",
            "product_intelligence.web",
            "product_intelligence.providers",
        )
        before = {
            name
            for name in sys.modules
            if name.startswith(prefixes) or name.split(".")[0] == "django"
        }
        do_run(corpus, tmp_path)
        after = {
            name
            for name in sys.modules
            if name.startswith(prefixes) or name.split(".")[0] == "django"
        }
        assert after == before

    def test_the_module_imports_no_forbidden_surface(self) -> None:
        tree = ast.parse(LIVE_MODULE_PATH.read_text(encoding="utf-8"))
        forbidden_prefixes = (
            "product_intelligence.execution",
            "product_intelligence.runs",
            "product_intelligence.web",
            "product_intelligence.providers",
            "product_intelligence.research",
        )
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            else:
                continue
            for name in names:
                assert not any(
                    name.startswith(prefix) for prefix in forbidden_prefixes
                ), f"live_capture imports {name}"
                if name.split(".")[0] == "django":
                    pytest.fail(f"live_capture imports django: {name}")


# ===========================================================================
# 16. No authority promotion
# ===========================================================================


class TestNoAuthorityPromotion:
    def test_the_qualification_marker_remains_false(
        self, corpus, tmp_path
    ) -> None:
        from product_intelligence.research import V2_AUTHORITY_QUALIFIED
        import product_intelligence.semantic.runtime_v2 as rt_v2

        do_run(corpus, tmp_path)  # a full live-capture run
        assert V2_AUTHORITY_QUALIFIED is False
        assert rt_v2.V2_AUTHORITY_QUALIFIED is False
        # The runner does not even reference the marker: it cannot
        # move it.
        assert "V2_AUTHORITY_QUALIFIED" not in (
            LIVE_MODULE_PATH.read_text(encoding="utf-8")
        )

    def test_the_artifacts_grant_no_authority_token(
        self, corpus, tmp_path
    ) -> None:
        _, _, manifest_path, capture_path, _ = do_run(corpus, tmp_path)
        for path in (manifest_path, capture_path):
            text = path.read_text(encoding="utf-8")
            for token in (
                "MACHINE_VERIFIED",
                "HUMAN_CONFIRMED",
                "AI_ASSISTED_MATCH",
                "QUALIFIED",
            ):
                assert token not in text, f"{path.name} names {token}"


# ===========================================================================
# 17. No pricing contamination
# ===========================================================================


class TestNoPricingContamination:
    def test_the_artifacts_name_no_pricing_or_review_surface(
        self, corpus, tmp_path
    ) -> None:
        _, _, manifest_path, capture_path, _ = do_run(corpus, tmp_path)
        for path in (manifest_path, capture_path):
            text = path.read_text(encoding="utf-8").lower()
            for token in (
                "price",
                "aggregation",
                "ai_assisted_review",
                "machine price",
                "reviewed price",
            ):
                assert token not in text, f"{path.name} names {token!r}"


# ===========================================================================
# 18. No network calls during ordinary unit tests
# ===========================================================================


class TestNoNetworkInOrdinaryTests:
    def test_the_full_fake_pipeline_makes_no_network_call(
        self, corpus, tmp_path, monkeypatch
    ) -> None:
        def refuse(*args, **kwargs):
            raise AssertionError("ordinary unit tests must not use the network")

        monkeypatch.setattr(socket, "socket", refuse)
        monkeypatch.setattr(socket, "create_connection", refuse)
        monkeypatch.setattr(socket, "getaddrinfo", refuse)

        # Both models, end to end: capture, artifacts, load, replay,
        # report - zero sockets.
        for sub, route, run_id in (
            ("a", primary_route(), "q3b-net-p"),
            ("b", fallback_route(), "q3b-net-f"),
        ):
            _, _, manifest_path, capture_path, _ = do_run(
                corpus,
                tmp_path / sub,
                provider=route[0],
                model=route[1],
                run_id=run_id,
            )
            assert capture_path is not None
            direct, result, gates, policy, decision, rationale, report = (
                direct_pipeline(corpus, capture_path)
            )
            assert result.metrics["counts"]["evaluated_cases"] == 43
            assert decision == "POLICY_PENDING"
            verify_direct_report(report, corpus)
            read_json(manifest_path)

    def test_a_dry_run_builds_no_transport_and_writes_nothing(
        self, corpus, tmp_path, monkeypatch
    ) -> None:
        monkeypatch.delenv("PI_SEMANTIC_AMAX_BASE_URL", raising=False)
        transport = ScriptedTransport(corpus)
        config = LiveCaptureConfig(
            provider=PRIMARY_ROUTE[0],
            model=PRIMARY_ROUTE[1],
            run_id="dry-1",
            transport=transport,
            output_dir=tmp_path / "artifacts",
        )
        runner = LiveCaptureRunner(config, corpus, dry_run=True)
        assert len(runner._entries) == 43
        assert transport.calls == []
        assert not (tmp_path / "artifacts").exists()

    def test_the_cli_dry_run_is_offline_and_bounded(
        self, tmp_path, monkeypatch
    ) -> None:
        monkeypatch.delenv("PI_SEMANTIC_AMAX_BASE_URL", raising=False)
        monkeypatch.delenv("PI_SEMANTIC_AMAX_API_KEY", raising=False)
        exit_code = main(
            [
                "capture",
                "--provider",
                PRIMARY_ROUTE[0],
                "--model",
                PRIMARY_ROUTE[1],
                "--corpus",
                str(CORPUS_PATH),
                "--out-dir",
                str(tmp_path / "artifacts"),
                "--dry-run",
            ]
        )
        assert exit_code == 0
        assert not (tmp_path / "artifacts").exists()

    def test_the_cli_refuses_an_unpinned_route_before_any_call(
        self, tmp_path
    ) -> None:
        exit_code = main(
            [
                "capture",
                "--provider",
                "not-a-pinned-provider",
                "--model",
                "not-a-pinned-model",
                "--corpus",
                str(CORPUS_PATH),
                "--out-dir",
                str(tmp_path / "artifacts"),
            ]
        )
        assert exit_code == 2
        assert not (tmp_path / "artifacts").exists()


# ===========================================================================
# 19. Bounded concurrency
# ===========================================================================


class TestBoundedConcurrency:
    def test_concurrency_bound_is_enforced(self) -> None:
        for bad in (0, 5, True):
            config = LiveCaptureConfig(
                provider=PRIMARY_ROUTE[0],
                model=PRIMARY_ROUTE[1],
                run_id="c-1",
                max_concurrency=bad,
            )
            with pytest.raises(
                LiveCaptureConfigError, match="max_concurrency"
            ):
                validate_live_capture_config(config)
        for good in (1, 2, 3, 4):
            config = LiveCaptureConfig(
                provider=PRIMARY_ROUTE[0],
                model=PRIMARY_ROUTE[1],
                run_id="c-2",
                max_concurrency=good,
            )
            validate_live_capture_config(config)  # no raise

    def test_concurrent_execution_never_exceeds_the_bound(
        self, corpus, tmp_path
    ) -> None:
        transport = ScriptedTransport(corpus, sleep_seconds=0.01)
        config = LiveCaptureConfig(
            provider=PRIMARY_ROUTE[0],
            model=PRIMARY_ROUTE[1],
            run_id="q3b-conc-1",
            transport=transport,
            output_dir=tmp_path / "artifacts",
            max_concurrency=3,
        )
        runner = LiveCaptureRunner(config, corpus)
        outcome = runner.run()
        manifest_path, capture_path = runner.write_artifacts(outcome)
        assert transport.max_in_flight <= 3
        assert transport.max_in_flight > 1  # it actually overlapped
        document = read_json(capture_path)
        assert [r["case_id"] for r in document["records"]] == [
            c.case_id for c in corpus.semantic_cases
        ]
        assert read_json(manifest_path)["transport_parameters"][
            "max_concurrency"
        ] == 3

    def test_a_concurrent_run_matches_a_sequential_run(
        self, corpus, tmp_path
    ) -> None:
        transport = ScriptedTransport(corpus, sleep_seconds=0.005)
        config = LiveCaptureConfig(
            provider=PRIMARY_ROUTE[0],
            model=PRIMARY_ROUTE[1],
            run_id="q3b-eq-1",
            transport=transport,
            output_dir=tmp_path / "conc",
            max_concurrency=4,
        )
        runner = LiveCaptureRunner(config, corpus)
        outcome = runner.run()
        _, conc_capture = runner.write_artifacts(outcome)
        _, _, _, seq_capture, _ = do_run(
            corpus, tmp_path / "seq", run_id="q3b-eq-1"
        )
        conc = read_json(conc_capture)
        seq = read_json(seq_capture)
        for key in ("records", "target_provider", "target_model", "corpus_digest"):
            assert conc[key] == seq[key]
