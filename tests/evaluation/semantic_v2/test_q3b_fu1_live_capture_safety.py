"""Q3-B-FU1 live capture runner: exception redaction + run-level
abort-safety tests.

Mandated properties (all offline: every model call goes through a
scripted, recording test double - no live network call is made
anywhere in this file):

* exception redaction (Blocker 1): an unexpected (non-bounded)
  exception never reaches stdout/stderr - the CLI emits the fixed,
  non-sensitive ``UNEXPECTED_RUNNER_FAILURE`` message with a nonzero
  exit; out-of-vocabulary transport evidence (an unrecognized code, or
  a non-string classification, carrying synthetic secrets) is reduced
  to the bounded ``UNRECOGNIZED_TRANSPORT_CODE`` abort marker and
  never echoed into any message, manifest, capture document, or
  summary; bounded configuration errors do not echo operator input;
  an unexpected transport exception propagates unconverted (never a
  bounded status, never a success) and writes no artifact;
* strict dispatch-stop (Blocker 2): once an abort-class failure is
  observed, no new case is dispatched - proven deterministically with
  a driven bounded-executor stand-in (real ``concurrent.futures``
  primitives, no timing dependence) and re-proven on real worker
  threads;
* cancelled work: submitted-but-not-started work is cancelled at
  abort, is never called, is never fabricated into a response, and is
  distinguished from never-attempted work in the manifest;
* in-flight preservation: work already running when the abort is
  observed runs to completion and its real outcome is preserved in
  the executions, the manifest, and the capture document;
* the manifest distinguishes, for EVERY eligible case: ``completed``
  / ``cancelled`` / ``never_attempted``;
* incomplete coverage fails closed: an aborted / cancelled capture
  replays with NOT_CAPTURED shortfalls, a non-complete coverage flag,
  a verified fail-closed report, and a decision that is never
  QUALIFIED under the DRAFT policy.
"""

from __future__ import annotations

import json
import threading
from collections import Counter
from concurrent.futures import Future
from pathlib import Path

import pytest

from tests.evaluation.semantic_v2._q3a_helpers import (
    CORPUS_PATH,
    POLICY_PATH,
    default_response_for,
    load_corpus_bundle,
    primary_route,
)
from product_intelligence.evaluation.semantic.transport import (
    TransportFailure,
    TransportResult,
)
from product_intelligence.evaluation.semantic_v2 import live_capture as lc
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
    evaluate_thresholds,
    load_policy,
    policy_applies_to,
)
from product_intelligence.evaluation.semantic_v2.report import (
    build_direct_report,
    verify_direct_report,
)
from product_intelligence.evaluation.semantic_v2.live_capture import (
    LiveCaptureConfig,
    LiveCaptureConfigError,
    LiveCaptureRunner,
    build_live_transport,
    main,
    validate_live_capture_config,
)
from product_intelligence.semantic.contract_v2 import (
    build_semantic_prompt_v2,
)

#: Synthetic, never-real secrets: if any of these values appears in an
#: output or artifact, a redaction defect has been proven.
FAKE_API_KEY = "sk-fu1-synthetic-api-key-0123456789abcdef"
FAKE_BEARER = "Bearer fu1.synthetic.token-9f8e7d6c"
FAKE_CRED_URL = (
    "https://fu1-user:fu1-hunter2@secret-host.example/v1/chat/completions"
)
FAKE_REQ_SECRET = "fu1-request-secret-xyz-778899"
SECRETS = (FAKE_API_KEY, FAKE_BEARER, FAKE_CRED_URL, FAKE_REQ_SECRET)

#: The exact manifest shape after FU1 (the Q3-B keys plus the new
#: per-case dispatch distinction).
EXPECTED_MANIFEST_KEYS = {
    "live_manifest_schema_version",
    "run_id",
    "run_status",
    "capture_mode",
    "target_provider",
    "target_model",
    "route_role",
    "corpus_id",
    "corpus_version",
    "corpus_digest",
    "semantic_contract",
    "prompt_version",
    "system_prompt_sha256",
    "generation_parameters",
    "retry_policy",
    "transport_parameters",
    "started_at",
    "finished_at",
    "git_head",
    "captured_by",
    "notes",
    "attempted_case_ids",
    "not_attempted_case_ids",
    "dispatch_states",
    "undocumented_cases",
    "abort",
    "cases",
}

EXPECTED_CASE_KEYS = {
    "attempts",
    "retried",
    "final_status",
    "latency_ms",
    "finish_reason",
    "token_usage",
    "documented",
    "prompt_sha256",
}


@pytest.fixture(scope="module")
def corpus():
    return load_corpus_bundle()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def ok_result(corpus, case, model) -> TransportResult:
    """The label-consistent OK outcome for one case (declared test
    fixture, not model output)."""
    return TransportResult(
        raw_output=default_response_for(case),
        latency_ms=1.0,
        provider_status="200",
        provider_id="fake",
        model_id=model,
        provider_reported_model=model,
        finish_reason="stop",
        token_usage=None,
    )


def abort_failure() -> TransportFailure:
    return TransportFailure(
        error_type="AUTHENTICATION_FAILED",
        transport_status=None,
        http_status=None,
    )


def decide_for(corpus, result):
    gates = evaluate_safety_gates(result)
    policy = load_policy(POLICY_PATH)
    te = (
        evaluate_thresholds(policy, result.metrics)
        if policy_applies_to(policy, corpus.corpus_id, corpus.corpus_version)
        else None
    )
    return decide(result, gates, policy, te), policy


def replay_capture(corpus, capture_path):
    direct = load_direct_capture(capture_path)
    verify_direct_capture_against_corpus(direct, corpus)
    return direct, evaluate_direct_for_model(corpus, direct, *direct.target_route)


def SECRET_URL_EXC() -> str:
    """A synthetic hostile exception message: URL with credentials,
    bearer token, API key, and request secret in one blob."""
    return (
        f"GET {FAKE_CRED_URL} 500 - Authorization: {FAKE_BEARER} "
        f"api_key={FAKE_API_KEY} body-secret={FAKE_REQ_SECRET}"
    )


# ---------------------------------------------------------------------------
# Test doubles (declared fixtures, not model output; no network)
# ---------------------------------------------------------------------------


class ScriptedOutcomeTransport:
    """A scripted, recording model stand-in that returns (or raises)
    whatever object the test prescribes per case.

    Cases with no prescribed behavior fail loudly if called: the
    runner is thereby proven never to dispatch beyond the scripted
    boundary, never to retry, and never to do best-of-N (each case is
    consumable exactly once).
    """

    def __init__(self, corpus, model: str, behavior: dict[str, object]) -> None:
        self.model = model
        self.calls: list[str] = []
        self.in_flight = 0
        self.max_in_flight = 0
        self.behavior = behavior
        self._consumed: set[str] = set()
        self._prompt_to_case: dict[str, str] = {}
        for case in corpus.semantic_cases:
            prompt = build_semantic_prompt_v2(case.build_semantic_case())
            self._prompt_to_case[prompt.user_prompt] = case.case_id

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
        self.calls.append(case_id)
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            assert case_id not in self._consumed, (
                f"case {case_id} was called twice - unbounded retry or "
                "best-of-N"
            )
            self._consumed.add(case_id)
            assert case_id in self.behavior, (
                f"case {case_id} was dispatched although no behavior was "
                "scripted for it - the runner crossed the scripted "
                "boundary"
            )
            behavior = self.behavior[case_id]
            if isinstance(behavior, BaseException):
                raise behavior
            return behavior
        finally:
            self.in_flight -= 1


class _BarrierAbortDouble:
    """A real-thread double for the dispatch-stop proof on production
    machinery.

    The two first-dispatched cases both enter ``complete()`` (a
    barrier also held by the test thread), so the test knows both are
    in flight before it releases the abort case; the other case stays
    in flight until released (proving an in-flight outcome is
    preserved). Any dispatch beyond the boundary fails loudly. No
    sleeps: only barrier / event synchronization.
    """

    def __init__(self, corpus, model, ok_case, abort_case, maybe_case,
                 barrier, release) -> None:
        self.model = model
        self.calls: list[str] = []
        self.in_flight = 0
        self.max_in_flight = 0
        self.ok_case = ok_case
        self.abort_case = abort_case
        self.maybe_case = maybe_case
        self.barrier = barrier
        self.release = release
        self._prompt_to_case: dict[str, tuple[str, object]] = {}
        for case in corpus.semantic_cases:
            prompt = build_semantic_prompt_v2(case.build_semantic_case())
            self._prompt_to_case[prompt.user_prompt] = (case.case_id, case)

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ):
        case_id, case = self._prompt_to_case[user_prompt]
        self.calls.append(case_id)
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            if case_id in (self.ok_case, self.abort_case):
                self.barrier.wait(timeout=30)
            if case_id == self.abort_case:
                return abort_failure()
            if case_id == self.ok_case:
                self.release.wait(timeout=30)
                return TransportResult(
                    raw_output=default_response_for(case),
                    latency_ms=1.0,
                    provider_status="200",
                    provider_id="fake",
                    model_id=model,
                    provider_reported_model=model,
                    finish_reason="stop",
                    token_usage=None,
                )
            if case_id == self.maybe_case:
                # Only legal if dispatched BEFORE the abort was
                # observed (the dispatcher had not seen the failure
                # yet); otherwise the test's assertions fail.
                return TransportResult(
                    raw_output=default_response_for(case),
                    latency_ms=1.0,
                    provider_status="200",
                    provider_id="fake",
                    model_id=model,
                    provider_reported_model=model,
                    finish_reason="stop",
                    token_usage=None,
                )
            raise AssertionError(
                f"case {case_id} was dispatched beyond the abort boundary"
            )
        finally:
            self.in_flight -= 1


class FakeBoundedExecutor:
    """A deterministic stand-in for the bounded executor (declared
    test fixture; not model output).

    No worker thread ever starts a submitted task on its own: the
    task stays PENDING (i.e. not started) until the test explicitly
    starts it (PENDING -> RUNNING), and it completes only when the
    test finishes it (RUNNING -> outcome). The futures are REAL
    ``concurrent.futures.Future`` objects, so the dispatcher's
    ``wait`` / ``cancel`` / ``result`` primitives are exactly the
    production ones. This proves strict dispatch-stop, cancellation
    of not-yet-started work, and in-flight preservation with
    synchronization only - no timing-dependent sleeps.
    """

    def __init__(self, max_workers: int) -> None:
        self.max_workers = max_workers
        self.submitted: list[tuple[Future, object, tuple]] = []
        self.full = threading.Event()
        self._started: set[int] = set()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def submit(self, fn, *args):
        fut = Future()
        self.submitted.append((fut, fn, args))
        if len(self.submitted) == self.max_workers:
            self.full.set()
        return fut

    def start(self, index: int) -> Future:
        """PENDING -> RUNNING: a worker picked the task up."""
        fut, _, _ = self.submitted[index]
        assert index not in self._started, "the task was already started"
        self._started.add(index)
        assert fut.set_running_or_notify_cancel(), "the task was not pending"
        return fut

    def finish(self, index: int) -> Future:
        """RUNNING -> outcome: the task runs NOW (in the driving
        thread, so the double records its call deterministically) and
        its result is set on the real future."""
        fut, fn, args = self.submitted[index]
        try:
            result = fn(*args)
        except BaseException as exc:
            fut.set_exception(exc)
            return fut
        fut.set_result(result)
        return fut


def _run_in_thread(runner: LiveCaptureRunner) -> tuple[threading.Thread, dict]:
    box: dict = {}

    def target() -> None:
        try:
            box["outcome"] = runner.run()
        except BaseException as exc:  # noqa: BLE001 - surfaced by the test
            box["exception"] = exc

    t = threading.Thread(target=target)
    t.start()
    return t, box


def _join(t: threading.Thread) -> None:
    t.join(timeout=30)
    assert not t.is_alive(), "the run thread deadlocked"


def make_runner(
    corpus,
    tmp_path: Path,
    transport,
    *,
    run_id: str,
    max_concurrency: int = 1,
):
    route = primary_route()
    config = LiveCaptureConfig(
        provider=route[0],
        model=route[1],
        run_id=run_id,
        transport=transport,
        output_dir=tmp_path / "artifacts",
        max_concurrency=max_concurrency,
    )
    return LiveCaptureRunner(config, corpus)


# ===========================================================================
# 1. Exception redaction (Blocker 1)
# ===========================================================================


class TestExceptionRedaction:
    def test_unexpected_exception_cli_is_fixed_and_non_sensitive(
        self, tmp_path, monkeypatch, capsys
    ) -> None:
        """An unexpected exception's message (carrying synthetic API
        keys, a bearer token, a credentials URL, and a request
        secret) must never reach stdout/stderr: the CLI emits the
        fixed, non-sensitive message and a nonzero exit, and writes no
        artifact."""

        def boom(*args, **kwargs):
            raise RuntimeError(
                f"POST {FAKE_CRED_URL} 401 - Authorization: "
                f"{FAKE_BEARER} api_key={FAKE_API_KEY} "
                f"body-secret={FAKE_REQ_SECRET}"
            )

        monkeypatch.setattr(lc, "load_corpus", boom)
        code = main(
            [
                "capture",
                "--provider", primary_route()[0],
                "--model", primary_route()[1],
                "--corpus", str(CORPUS_PATH),
                "--out-dir", str(tmp_path / "artifacts"),
            ]
        )
        out = capsys.readouterr()
        assert code == 3  # nonzero, distinct from the bounded exit code
        assert out.err == lc.UNEXPECTED_RUNNER_FAILURE_MESSAGE + "\n"
        assert out.out == ""
        for secret in SECRETS:
            assert secret not in out.out, "secret leaked to stdout"
            assert secret not in out.err, "secret leaked to stderr"
        assert "UNEXPECTED_RUNNER_FAILURE" in out.err
        assert not (tmp_path / "artifacts").exists()

    def test_unexpected_transport_exception_propagates_unconverted(
        self, corpus, tmp_path
    ) -> None:
        """An exception raised by the transport is a programming
        defect: it propagates out of run() UNCONVERTED (never a
        bounded status, never a success, never retried) and no
        artifact is written."""
        first = corpus.semantic_cases[0]
        exc = RuntimeError(SECRET_URL_EXC())
        transport = ScriptedOutcomeTransport(
            corpus, primary_route()[1], {first.case_id: exc}
        )
        runner = make_runner(corpus, tmp_path, transport, run_id="fu1-unexp-1")
        with pytest.raises(RuntimeError) as caught:
            runner.run()
        assert caught.value is exc  # identity: not wrapped, not converted
        assert not (tmp_path / "artifacts").exists()
        assert transport.calls == [first.case_id]  # one call, no retry

    def test_out_of_vocabulary_code_aborts_with_bounded_marker_and_no_echo(
        self, corpus, tmp_path
    ) -> None:
        """An unrecognized transport code carrying synthetic secrets
        is a run-level abort recorded ONLY as the bounded
        UNRECOGNIZED_TRANSPORT_CODE marker: no retry, no document
        record, and the transport-provided value is echoed into no
        message, manifest, or summary."""
        first = corpus.semantic_cases[0]
        hostile = f"AUTH_FAILED {FAKE_CRED_URL} {FAKE_BEARER} {FAKE_API_KEY}"
        transport = ScriptedOutcomeTransport(
            corpus,
            primary_route()[1],
            {
                first.case_id: TransportFailure(
                    error_type=hostile, transport_status=None, http_status=None
                )
            },
        )
        runner = make_runner(corpus, tmp_path, transport, run_id="fu1-oov-1")
        outcome = runner.run()
        assert transport.calls == [first.case_id]  # not retried
        assert outcome.abort == (first.case_id, lc.LIVE_UNRECOGNIZED_TRANSPORT_CODE)
        execution = outcome.executions[first.case_id]
        assert execution.final_status == lc.LIVE_UNRECOGNIZED_TRANSPORT_CODE
        assert execution.documented is False
        manifest_path, capture_path = runner.write_artifacts(outcome)
        assert capture_path is None  # nothing in-vocabulary: no document
        manifest = read_json(manifest_path)
        assert manifest["run_status"] == (
            f"ABORTED_{lc.LIVE_UNRECOGNIZED_TRANSPORT_CODE}"
        )
        assert manifest["abort"] == {
            "case_id": first.case_id,
            "code": lc.LIVE_UNRECOGNIZED_TRANSPORT_CODE,
        }
        assert manifest["undocumented_cases"] == {
            first.case_id: lc.LIVE_UNRECOGNIZED_TRANSPORT_CODE
        }
        assert manifest["attempted_case_ids"] == [first.case_id]
        assert len(manifest["not_attempted_case_ids"]) == 42
        blob = (
            manifest_path.read_text(encoding="utf-8")
            + json.dumps(runner.summary(outcome))
        )
        for secret in SECRETS:
            assert secret not in blob, f"secret {secret[:12]}... echoed"
        assert hostile not in blob
        # The marker is outside the frozen policy buckets (they stay
        # exactly the frozen vocabulary).
        assert lc.LIVE_UNRECOGNIZED_TRANSPORT_CODE not in lc.LIVE_ABORT_STATUSES
        assert lc.LIVE_UNRECOGNIZED_TRANSPORT_CODE not in lc.LIVE_FINAL_STATUSES
        assert lc.LIVE_UNRECOGNIZED_TRANSPORT_CODE not in lc.LIVE_RETRYABLE_STATUSES

    def test_non_string_error_type_aborts_with_bounded_marker_and_no_echo(
        self, corpus, tmp_path
    ) -> None:
        """A non-string error classification is out of vocabulary the
        same way: a bounded abort marker, never the value."""
        first = corpus.semantic_cases[0]

        class _MalformedFailure:
            error_type = ("Bearer", FAKE_API_KEY, FAKE_CRED_URL)  # not a str

        transport = ScriptedOutcomeTransport(
            corpus, primary_route()[1], {first.case_id: _MalformedFailure()}
        )
        runner = make_runner(corpus, tmp_path, transport, run_id="fu1-oov-2")
        outcome = runner.run()
        assert transport.calls == [first.case_id]
        assert outcome.abort == (first.case_id, lc.LIVE_UNRECOGNIZED_TRANSPORT_CODE)
        manifest_path, capture_path = runner.write_artifacts(outcome)
        assert capture_path is None
        manifest = read_json(manifest_path)
        blob = manifest_path.read_text(encoding="utf-8")
        for secret in SECRETS:
            assert secret not in blob
        assert manifest["dispatch_states"][first.case_id] == "completed"
        assert all(
            v == "never_attempted"
            for k, v in manifest["dispatch_states"].items()
            if k != first.case_id
        )

    def test_bounded_config_errors_do_not_echo_operator_input(
        self, monkeypatch
    ) -> None:
        for name in (
            "PI_SEMANTIC_AMAX_BASE_URL",
            "PI_SEMANTIC_AMAX_API_KEY",
            "PI_SEMANTIC_VLLM_262K_BASE_URL",
            "PI_SEMANTIC_VLLM_262K_API_KEY",
        ):
            monkeypatch.delenv(name, raising=False)
        route = primary_route()
        # (a) an unpinned provider/model carrying synthetic secrets
        config = LiveCaptureConfig(
            provider=FAKE_API_KEY, model=FAKE_BEARER, run_id="fu1-echo-1"
        )
        with pytest.raises(LiveCaptureConfigError) as caught:
            validate_live_capture_config(config)
        message = str(caught.value)
        assert "frozen V2 pinned" in message  # the bounded diagnostic stays
        for secret in (FAKE_API_KEY, FAKE_BEARER):
            assert secret not in message
        # (b) a hostile run_id
        config = LiveCaptureConfig(
            provider=route[0], model=route[1], run_id=FAKE_CRED_URL
        )
        with pytest.raises(LiveCaptureConfigError) as caught:
            validate_live_capture_config(config)
        assert FAKE_CRED_URL not in str(caught.value)
        # (c) an unknown / unconfigured provider via the transport
        # factory (the raw ValueError is converted, never chained)
        with pytest.raises(LiveCaptureConfigError) as caught:
            build_live_transport(FAKE_REQ_SECRET, 123.4)
        message = str(caught.value)
        assert "not configured" in message
        assert FAKE_REQ_SECRET not in message
        assert caught.value.__cause__ is None  # no raw chain retained

    def test_cli_bounded_errors_keep_exit_2_and_stay_non_sensitive(
        self, tmp_path, capsys
    ) -> None:
        base = [
            "capture",
            "--provider", FAKE_API_KEY,
            "--model", FAKE_BEARER,
            "--corpus", str(CORPUS_PATH),
            "--out-dir", str(tmp_path / "artifacts"),
        ]
        code = main(base)
        out = capsys.readouterr()
        assert code == 2
        assert FAKE_API_KEY not in out.err
        assert FAKE_BEARER not in out.err
        assert "frozen V2 pinned" in out.err
        # A missing corpus file: bounded CorpusError, exit 2 (not the
        # unexpected-failure code).
        route = primary_route()
        code = main(
            [
                "capture",
                "--provider", route[0],
                "--model", route[1],
                "--corpus", str(tmp_path / "missing.json"),
                "--out-dir", str(tmp_path / "artifacts"),
            ]
        )
        out = capsys.readouterr()
        assert code == 2
        assert "corpus file not found" in out.err
        assert "UNEXPECTED_RUNNER_FAILURE" not in out.err
        assert not (tmp_path / "artifacts").exists()

    def test_cli_artifact_collision_is_bounded_exit_2(
        self, corpus, tmp_path, capsys
    ) -> None:
        model = primary_route()[1]
        behavior = {
            case.case_id: ok_result(corpus, case, model)
            for case in corpus.semantic_cases
        }
        runner = make_runner(
            corpus,
            tmp_path,
            ScriptedOutcomeTransport(corpus, model, behavior),
            run_id="fu1-col",
        )
        outcome = runner.run()
        runner.write_artifacts(outcome)
        route = primary_route()
        code = main(
            [
                "capture",
                "--provider", route[0],
                "--model", route[1],
                "--corpus", str(CORPUS_PATH),
                "--out-dir", str(tmp_path / "artifacts"),
                "--run-id", "fu1-col",
            ]
        )
        out = capsys.readouterr()
        assert code == 2
        assert "already exists" in out.err
        assert "UNEXPECTED_RUNNER_FAILURE" not in out.err


# ===========================================================================
# 2. Strict dispatch-stop, cancellation, in-flight preservation
#    (Blocker 2)
# ===========================================================================


class TestAbortDispatchBoundary:
    def test_no_new_dispatch_after_observed_abort_on_real_threads(
        self, corpus, tmp_path
    ) -> None:
        """On production machinery (real ThreadPoolExecutor workers):
        the abort case returns while the other dispatched case is
        still in flight; the in-flight outcome is preserved, nothing
        beyond the boundary is dispatched (any further call fails
        loudly), and the concurrency bound holds. Synchronization
        only (barrier + event); no sleeps."""
        e0, e1, e2 = corpus.semantic_cases[:3]
        rest = corpus.semantic_cases[3:]
        model = primary_route()[1]
        barrier = threading.Barrier(3)  # two workers + this thread
        release = threading.Event()
        transport = _BarrierAbortDouble(
            corpus,
            model,
            e0.case_id,
            e1.case_id,
            e2.case_id,
            barrier,
            release,
        )
        runner = make_runner(
            corpus,
            tmp_path,
            transport,
            run_id="fu1-abort-rt",
            max_concurrency=2,
        )
        run_t, box = _run_in_thread(runner)
        barrier.wait(timeout=30)  # both dispatched cases in flight
        release.set()  # let the in-flight OK case finish
        _join(run_t)
        assert "exception" not in box
        outcome = box["outcome"]

        counts = Counter(transport.calls)
        assert counts[e0.case_id] == 1
        assert counts[e1.case_id] == 1
        assert counts[e2.case_id] <= 1  # only legal pre-abort-observation
        for case in rest:
            assert counts[case.case_id] == 0  # never dispatched
        assert transport.max_in_flight <= 2  # the bound holds

        assert outcome.abort == (e1.case_id, "AUTHENTICATION_FAILED")
        e0ex = outcome.executions[e0.case_id]
        assert e0ex.final_status == "OK"
        assert e0ex.raw_output == default_response_for(e0)  # preserved
        assert outcome.executions[e1.case_id].final_status == (
            "AUTHENTICATION_FAILED"
        )
        ds = outcome.dispatch_states
        assert ds[e0.case_id] == "completed"
        assert ds[e1.case_id] == "completed"
        if counts[e2.case_id]:
            assert ds[e2.case_id] == "completed"
        else:
            assert ds[e2.case_id] in ("cancelled", "never_attempted")
        for case in rest:
            assert ds[case.case_id] in ("cancelled", "never_attempted")
            assert case.case_id not in outcome.executions

        manifest_path, capture_path = runner.write_artifacts(outcome)
        manifest = read_json(manifest_path)
        assert manifest["run_status"] == "ABORTED_AUTHENTICATION_FAILED"
        attempted = [c.case_id for c in (e0, e1, e2) if counts[c.case_id]]
        assert manifest["attempted_case_ids"] == attempted
        assert manifest["dispatch_states"] == ds
        document = read_json(capture_path)
        assert [r["case_id"] for r in document["records"]] == attempted
        # Fail-closed replay: the unattempted tail is a coverage
        # shortfall, never a pass.
        direct, result = replay_capture(corpus, capture_path)
        rcounts = result.metrics["counts"]
        assert rcounts["not_captured"] == 43 - len(attempted)
        (decision, _), _ = decide_for(corpus, result)
        assert decision in ("POLICY_PENDING", "INCOMPLETE_COVERAGE")
        assert decision != "QUALIFIED"

    def test_cancelled_pending_work_is_never_called_and_is_distinguished(
        self, corpus, tmp_path, monkeypatch
    ) -> None:
        """Deterministic (driven bounded executor): e0 returns the
        abort while e1 sits PENDING (submitted, not started). The
        dispatcher must cancel e1 (never called, never fabricated),
        submit nothing else, and distinguish e1 as ``cancelled`` from
        the ``never_attempted`` tail in the manifest."""
        e0, e1 = corpus.semantic_cases[:2]
        model = primary_route()[1]
        transport = ScriptedOutcomeTransport(
            corpus, model, {e0.case_id: abort_failure()}
        )
        fake = FakeBoundedExecutor(max_workers=2)
        monkeypatch.setattr(lc, "ThreadPoolExecutor", lambda max_workers: fake)
        runner = make_runner(
            corpus, tmp_path, transport, run_id="fu1-cancel-1",
            max_concurrency=2,
        )
        run_t, box = _run_in_thread(runner)
        assert fake.full.wait(timeout=30)  # e0, e1 submitted; nothing more yet
        fake.finish(0)  # e0 returns the abort; e1 stays PENDING
        _join(run_t)
        assert "exception" not in box
        outcome = box["outcome"]

        assert len(fake.submitted) == 2  # STRICT dispatch-stop
        assert transport.calls == [e0.case_id]  # e1 was never called
        assert outcome.abort == (e0.case_id, "AUTHENTICATION_FAILED")
        assert outcome.executions[e0.case_id].final_status == (
            "AUTHENTICATION_FAILED"
        )
        assert e1.case_id not in outcome.executions  # no fabricated outcome
        ds = outcome.dispatch_states
        assert ds[e0.case_id] == "completed"
        assert ds[e1.case_id] == "cancelled"
        for case in corpus.semantic_cases[2:]:
            assert ds[case.case_id] == "never_attempted"
        assert outcome.not_attempted_case_ids == tuple(
            case.case_id for case in corpus.semantic_cases[1:]
        )

        manifest_path, capture_path = runner.write_artifacts(outcome)
        manifest = read_json(manifest_path)
        assert manifest["run_status"] == "ABORTED_AUTHENTICATION_FAILED"
        assert manifest["dispatch_states"] == ds
        assert manifest["attempted_case_ids"] == [e0.case_id]
        assert manifest["not_attempted_case_ids"] == [
            case.case_id for case in corpus.semantic_cases[1:]
        ]
        assert e1.case_id not in manifest["cases"]  # no evidence invented
        document = read_json(capture_path)
        assert [r["case_id"] for r in document["records"]] == [e0.case_id]
        record = document["records"][0]
        assert record["execution_status"] == "AUTHENTICATION_FAILED"
        assert record["raw_output"] is None  # never fabricated
        # The cancelled case replays as NOT_CAPTURED (shortfall).
        direct, result = replay_capture(corpus, capture_path)
        victim = next(o for o in result.outcomes if o.case_id == e1.case_id)
        assert victim.state == "NOT_CAPTURED"
        (decision, _), _ = decide_for(corpus, result)
        assert decision in ("POLICY_PENDING", "INCOMPLETE_COVERAGE")
        assert decision != "QUALIFIED"

    def test_in_flight_work_is_preserved_when_the_abort_is_observed(
        self, corpus, tmp_path, monkeypatch
    ) -> None:
        """Deterministic: e0 returns the abort while e1 is RUNNING
        (already started). e1 cannot be cancelled; it must run to
        completion and its REAL outcome must be preserved in the
        executions, the manifest, and the capture document - while
        nothing further is dispatched."""
        e0, e1 = corpus.semantic_cases[:2]
        model = primary_route()[1]
        transport = ScriptedOutcomeTransport(
            corpus,
            model,
            {e0.case_id: abort_failure(), e1.case_id: ok_result(corpus, e1, model)},
        )
        fake = FakeBoundedExecutor(max_workers=2)
        monkeypatch.setattr(lc, "ThreadPoolExecutor", lambda max_workers: fake)
        runner = make_runner(
            corpus, tmp_path, transport, run_id="fu1-inflight-1",
            max_concurrency=2,
        )
        run_t, box = _run_in_thread(runner)
        assert fake.full.wait(timeout=30)
        fake.start(0)
        fake.start(1)  # both RUNNING (in flight)
        fake.finish(0)  # the abort is observed while e1 is in flight
        fake.finish(1)  # e1 completes with its real outcome
        _join(run_t)
        assert "exception" not in box
        outcome = box["outcome"]

        assert len(fake.submitted) == 2  # STRICT dispatch-stop
        assert transport.calls == [e0.case_id, e1.case_id]
        assert outcome.abort == (e0.case_id, "AUTHENTICATION_FAILED")
        e1ex = outcome.executions[e1.case_id]
        assert e1ex.final_status == "OK"
        assert e1ex.raw_output == default_response_for(e1)  # preserved verbatim
        ds = outcome.dispatch_states
        assert ds[e0.case_id] == "completed"
        assert ds[e1.case_id] == "completed"  # in-flight -> completed
        for case in corpus.semantic_cases[2:]:
            assert ds[case.case_id] == "never_attempted"

        manifest_path, capture_path = runner.write_artifacts(outcome)
        manifest = read_json(manifest_path)
        assert manifest["cases"][e1.case_id]["final_status"] == "OK"
        assert manifest["cases"][e1.case_id]["documented"] is True
        document = read_json(capture_path)
        assert [r["case_id"] for r in document["records"]] == [
            e0.case_id,
            e1.case_id,
        ]
        e1record = document["records"][1]
        assert e1record["execution_status"] == "OK"
        assert e1record["raw_output"] == default_response_for(e1)
        # The in-flight case is scored as-is at replay; the run is
        # still incomplete and fail-closed.
        direct, result = replay_capture(corpus, capture_path)
        e1outcome = next(o for o in result.outcomes if o.case_id == e1.case_id)
        assert e1outcome.state == "EVALUATED"
        (decision, _), _ = decide_for(corpus, result)
        assert decision in ("POLICY_PENDING", "INCOMPLETE_COVERAGE")
        assert decision != "QUALIFIED"

    def test_out_of_vocabulary_code_stops_the_concurrent_dispatch(
        self, corpus, tmp_path, monkeypatch
    ) -> None:
        """The unrecognized-code abort is a dispatch-stop too:
        deterministic, no echo, cancelled tail distinguished."""
        e0, e1 = corpus.semantic_cases[:2]
        model = primary_route()[1]
        hostile = f"STRANGE_CODE {FAKE_CRED_URL} {FAKE_API_KEY}"
        transport = ScriptedOutcomeTransport(
            corpus,
            model,
            {
                e0.case_id: TransportFailure(
                    error_type=hostile, transport_status=None, http_status=None
                )
            },
        )
        fake = FakeBoundedExecutor(max_workers=2)
        monkeypatch.setattr(lc, "ThreadPoolExecutor", lambda max_workers: fake)
        runner = make_runner(
            corpus, tmp_path, transport, run_id="fu1-oov-cc",
            max_concurrency=2,
        )
        run_t, box = _run_in_thread(runner)
        assert fake.full.wait(timeout=30)
        fake.finish(0)
        _join(run_t)
        assert "exception" not in box
        outcome = box["outcome"]

        assert len(fake.submitted) == 2  # STRICT dispatch-stop
        assert transport.calls == [e0.case_id]
        assert outcome.abort == (e0.case_id, lc.LIVE_UNRECOGNIZED_TRANSPORT_CODE)
        manifest_path, capture_path = runner.write_artifacts(outcome)
        assert capture_path is None
        manifest_text = manifest_path.read_text(encoding="utf-8")
        for secret in (FAKE_CRED_URL, FAKE_API_KEY, hostile):
            assert secret not in manifest_text
        manifest = read_json(manifest_path)
        assert manifest["run_status"] == (
            f"ABORTED_{lc.LIVE_UNRECOGNIZED_TRANSPORT_CODE}"
        )
        assert manifest["dispatch_states"][e1.case_id] == "cancelled"

    def test_sequential_abort_marks_the_rest_never_attempted(
        self, corpus, tmp_path
    ) -> None:
        """Sequential mode keeps its behavior: the run stops at the
        abort; the tail is ``never_attempted`` (never ``cancelled`` -
        sequential work is never submitted before it starts)."""
        e0, second = corpus.semantic_cases[:2]
        model = primary_route()[1]
        behavior = {
            case.case_id: ok_result(corpus, case, model)
            for case in corpus.semantic_cases
        }
        behavior[second.case_id] = abort_failure()
        transport = ScriptedOutcomeTransport(corpus, model, behavior)
        runner = make_runner(
            corpus, tmp_path, transport, run_id="fu1-seq-1", max_concurrency=1
        )
        outcome = runner.run()
        assert transport.calls == [e0.case_id, second.case_id]  # stopped
        assert outcome.abort == (second.case_id, "AUTHENTICATION_FAILED")
        assert outcome.dispatch_states[e0.case_id] == "completed"
        assert outcome.dispatch_states[second.case_id] == "completed"
        for case in corpus.semantic_cases[2:]:
            assert outcome.dispatch_states[case.case_id] == "never_attempted"
        assert "cancelled" not in outcome.dispatch_states.values()
        assert outcome.not_attempted_case_ids == tuple(
            case.case_id for case in corpus.semantic_cases[2:]
        )
        manifest_path, capture_path = runner.write_artifacts(outcome)
        manifest = read_json(manifest_path)
        assert manifest["run_status"] == "ABORTED_AUTHENTICATION_FAILED"
        assert manifest["dispatch_states"] == outcome.dispatch_states

    def test_a_completed_concurrent_run_marks_every_case_completed(
        self, corpus, tmp_path
    ) -> None:
        model = primary_route()[1]
        behavior = {
            case.case_id: ok_result(corpus, case, model)
            for case in corpus.semantic_cases
        }
        transport = ScriptedOutcomeTransport(corpus, model, behavior)
        runner = make_runner(
            corpus, tmp_path, transport, run_id="fu1-full-1", max_concurrency=4
        )
        outcome = runner.run()
        assert outcome.abort is None
        assert outcome.not_attempted_case_ids == ()
        assert set(outcome.dispatch_states) == {
            case.case_id for case in corpus.semantic_cases
        }
        assert all(
            v == "completed" for v in outcome.dispatch_states.values()
        )
        assert transport.max_in_flight <= 4  # the bound holds
        manifest_path, capture_path = runner.write_artifacts(outcome)
        manifest = read_json(manifest_path)
        assert manifest["run_status"] == "COMPLETED"
        assert manifest["dispatch_states"] == outcome.dispatch_states
        document = read_json(capture_path)
        assert [r["case_id"] for r in document["records"]] == [
            case.case_id for case in corpus.semantic_cases
        ]


# ===========================================================================
# 3. Manifest shape (new dispatch distinction; old keys intact)
# ===========================================================================


class TestManifestShape:
    def test_the_manifest_shape_is_exact(self, corpus, tmp_path) -> None:
        model = primary_route()[1]
        behavior = {
            case.case_id: ok_result(corpus, case, model)
            for case in corpus.semantic_cases
        }
        transport = ScriptedOutcomeTransport(corpus, model, behavior)
        runner = make_runner(
            corpus, tmp_path, transport, run_id="fu1-shape-1",
            max_concurrency=3,
        )
        outcome = runner.run()
        manifest_path, _ = runner.write_artifacts(outcome)
        manifest = read_json(manifest_path)
        assert set(manifest) == EXPECTED_MANIFEST_KEYS
        assert len(manifest["dispatch_states"]) == 43
        assert set(manifest["dispatch_states"].values()) == {"completed"}
        for entry in manifest["cases"].values():
            assert set(entry) == EXPECTED_CASE_KEYS

    def test_dispatch_states_are_a_bounded_vocabulary(self, corpus, tmp_path) -> None:
        e0, e1 = corpus.semantic_cases[:2]
        model = primary_route()[1]
        transport = ScriptedOutcomeTransport(
            corpus,
            model,
            {e0.case_id: ok_result(corpus, e0, model), e1.case_id: abort_failure()},
        )
        runner = make_runner(corpus, tmp_path, transport, run_id="fu1-vocab-1")
        outcome = runner.run()
        assert set(outcome.dispatch_states.values()) <= {
            "completed",
            "cancelled",
            "never_attempted",
        }


# ===========================================================================
# 4. Fail-closed reporting for incomplete coverage
# ===========================================================================


class TestFailClosedReporting:
    def test_an_aborted_concurrent_capture_reports_incomplete_coverage(
        self, corpus, tmp_path, monkeypatch
    ) -> None:
        """An aborted capture with cancelled / never-attempted tail
        builds a VERIFIED direct report whose coverage is explicitly
        incomplete and whose decision is fail-closed (never
        QUALIFIED under the DRAFT policy)."""
        e0, e1 = corpus.semantic_cases[:2]
        model = primary_route()[1]
        transport = ScriptedOutcomeTransport(
            corpus,
            model,
            {e0.case_id: abort_failure(), e1.case_id: ok_result(corpus, e1, model)},
        )
        fake = FakeBoundedExecutor(max_workers=2)
        monkeypatch.setattr(lc, "ThreadPoolExecutor", lambda max_workers: fake)
        runner = make_runner(
            corpus, tmp_path, transport, run_id="fu1-report-1",
            max_concurrency=2,
        )
        run_t, box = _run_in_thread(runner)
        assert fake.full.wait(timeout=30)
        fake.start(0)
        fake.start(1)
        fake.finish(0)
        fake.finish(1)
        _join(run_t)
        assert "exception" not in box
        outcome = box["outcome"]
        manifest_path, capture_path = runner.write_artifacts(outcome)

        direct, result = replay_capture(corpus, capture_path)
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
            generated_utc="2026-10-09T00:00:00Z",
        )
        verify_direct_report(report, corpus)  # must verify (fail-closed data)
        assert policy.status == "DRAFT"
        assert decision != "QUALIFIED"
        assert report["decision"] != "QUALIFIED"
        assert report["coverage"]["complete"] is False
        assert report["coverage"]["evaluated_cases"] == 1  # the in-flight OK
        assert report["coverage"]["not_captured"] == 41
        # The abort case is preserved as a runtime failure, not scored.
        assert e0.case_id in report["coverage"]["runtime_failure_case_ids"]
        assert e1.case_id not in report["coverage"]["runtime_failure_case_ids"]
        assert report["authority"]["granted"] is False
        assert report["authority"]["v2_authority_qualified"] is False
        # The manifest sidecar names the abort + the preserved states.
        manifest = read_json(manifest_path)
        assert manifest["run_status"] == "ABORTED_AUTHENTICATION_FAILED"
        assert manifest["dispatch_states"][e0.case_id] == "completed"
        assert manifest["dispatch_states"][e1.case_id] == "completed"
        assert all(
            v == "never_attempted"
            for k, v in manifest["dispatch_states"].items()
            if k not in (e0.case_id, e1.case_id)
        )
