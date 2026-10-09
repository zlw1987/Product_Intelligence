"""The bounded LIVE DIRECT_MODEL_QUALIFICATION capture runner (Q3-B).

BENCHMARK-ONLY live infrastructure: it executes the frozen Semantic V2
qualification corpus independently against EXACTLY ONE pinned model
(the frozen primary or the frozen fallback identity - nothing else may
enter the qualification) and writes the approved Q3-A-FU1
``DIRECT_MODEL_QUALIFICATION`` capture document for that model.

What it reuses (never recreates):

* the frozen production V2 prompt builder
  (``semantic.contract_v2.build_semantic_prompt_v2``) over the REAL
  typed corpus case (``CorpusCase.build_semantic_case``);
* the approved direct-capture schema (``direct_capture.py``) - the
  written document loads and verifies through the unchanged
  ``load_direct_capture`` / ``verify_direct_capture_against_corpus``;
* the frozen production V2 parser composition
  (``evaluator.classify_raw_response``) for per-attempt
  classification, exactly as the production runtime boundary classifies;
* the approved provider transport / configuration mechanism
  (``semantic.transport.get_openai_transport_for_provider``), read from
  the server environment - no credential is ever stored, printed, or
  written to an artifact.

What it is NOT:

* no production orchestration is imported or invoked (no execution /
  runs / web / search-provider / framework surface);
* no production fallback routing: one capture targets exactly one
  pinned model; the primary and the fallback are captured
  INDEPENDENTLY by two separate runs - a primary failure is never
  simulated, never retried onto the fallback, and no response is ever
  transferred between model identities;
* no authority: the capture is evidence only. It grants no
  qualification, no pricing authority, and no human-review authority;
  the qualification policy stays DRAFT and the offline evaluator
  decides (POLICY_PENDING at best until an approved policy exists).

Retry policy (FIXED before collection; documented and bounded):

* an attempt that produces NO model output and fails with a TRANSIENT
  transport condition (``LIVE_RETRYABLE_STATUSES``: TIMEOUT, DNS_ERROR,
  TLS_ERROR, CONNECTION_ERROR, RATE_LIMITED, PROVIDER_UNAVAILABLE) may
  be retried with the IDENTICAL request, at most ``max_attempts``
  times in total (1..3);
* an attempt that receives a provider response body, or a definitive
  per-case output/identity failure (``LIVE_FINAL_STATUSES``: OK,
  HTTP_ERROR, EMPTY_RESPONSE, MALFORMED_JSON, SCHEMA_INVALID,
  INVALID_RESPONSE, MODEL_IDENTITY_MISMATCH), is FINAL for the case:
  exactly one bounded outcome is recorded and the case is never called
  again - a semantic decision is never retried, and a response is
  never cherry-picked between attempts;
* an attempt that breaks the run-level identity / configuration
  (``LIVE_ABORT_STATUSES``: AUTHENTICATION_FAILED, MODEL_NOT_FOUND,
  INVALID_REQUEST_CONFIGURATION, UNSUPPORTED_PARAMETER) or reports an
  unknown transport code aborts the run after recording the attempted
  case (bounded, in-vocabulary evidence only); no further case is
  sent;
* CASE_REJECTED (a content-policy rejection of the case's own
  content) is CASE-LOCAL per the frozen transport vocabulary: the run
  continues, the case is documented in the manifest sidecar, and no
  record for it enters the capture document (its status is outside the
  direct-capture vocabulary; the case replays as NOT_CAPTURED - a
  coverage shortfall, never a pass);
* an unexpected exception raised by the transport is a programming
  defect: it propagates, is never converted into a bounded status, and
  no capture document is written for the run.

Artifacts (stored separately from the corpus labels):

* ``<run_id>__direct__<provider>_<model>.json`` - the strict
  DIRECT_MODEL_QUALIFICATION capture document (the frozen schema);
* ``<run_id>__direct__<provider>_<model>__manifest.json`` - the
  runner manifest sidecar (run identity, fixed retry policy, bounded
  per-case attempt evidence, prompt digests; evidence only - the
  evaluator never reads it).

The transport is imported LAZILY inside transport construction only:
importing this module loads no network client, and no live call
happens until the operator explicitly runs it.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

from product_intelligence.evaluation.semantic_v2.canonical import (
    UTC_INSTANT_PATTERN,
    canonical_sha256,
)
from product_intelligence.evaluation.semantic_v2.capture import (
    FALLBACK_ROUTE,
    PRIMARY_ROUTE,
    PROMPT_VERSION_V2,
    SEMANTIC_CONTRACT_VERSION_V2,
)
from product_intelligence.evaluation.semantic_v2.corpus import (
    CONTRACT_NEGATIVE_CASE_CLASS,
    CorpusBundle,
    load_corpus,
)
from product_intelligence.evaluation.semantic_v2.direct_capture import (
    DIRECT_CAPTURE_MODE,
    DIRECT_CAPTURE_SCHEMA_VERSION,
    DIRECT_EXECUTION_STATUSES,
    load_direct_capture,
    verify_direct_capture_against_corpus,
)
from product_intelligence.evaluation.semantic_v2.evaluator import (
    classify_raw_response,
)
from product_intelligence.semantic.contract_v2 import (
    SEMANTIC_PROMPT_VERSION_V2,
    SYSTEM_PROMPT_V2,
    build_semantic_prompt_v2,
)

__all__ = [
    "LIVE_ABORT_STATUSES",
    "LIVE_CASE_LOCAL_STATUSES",
    "LIVE_DEFAULT_CONCURRENCY",
    "LIVE_DEFAULT_MAX_ATTEMPTS",
    "LIVE_DEFAULT_REQUEST_TIMEOUT_SECONDS",
    "LIVE_FINAL_STATUSES",
    "LIVE_MAX_CONCURRENCY",
    "LIVE_MAX_REQUEST_TIMEOUT_SECONDS",
    "LIVE_MAX_TOKENS",
    "LIVE_MANIFEST_SCHEMA_VERSION",
    "LIVE_RETRYABLE_STATUSES",
    "LIVE_TEMPERATURE",
    "LIVE_TRANSPORT_ERROR_TO_STATUS",
    "LiveCaptureAbortError",
    "LiveCaptureConfig",
    "LiveCaptureError",
    "LiveCaptureRunner",
    "build_live_transport",
    "main",
    "validate_live_capture_config",
]

# ---------------------------------------------------------------------------
# Pinned generation parameters (NOT caller-configurable; drift-pinned
# against the frozen production V2 route by test)
# ---------------------------------------------------------------------------

#: The frozen generation temperature (exact float - the same discipline
#: as the pinned production route; int/bool are rejected by
#: construction: this is a module constant, not a parameter).
LIVE_TEMPERATURE: Final[float] = 0.0

#: The frozen generation max_tokens (the same value the pinned
#: production route runs at).
LIVE_MAX_TOKENS: Final[int] = 32768

#: Bounded request timeout (seconds): the qualified default and the
#: hard bound (mirrors of the frozen runtime configuration bounds;
#: drift-pinned by test).
LIVE_DEFAULT_REQUEST_TIMEOUT_SECONDS: Final[float] = 300.0
LIVE_MAX_REQUEST_TIMEOUT_SECONDS: Final[float] = 3600.0

#: Bounded per-case attempts: the fixed default policy and the hard
#: bound. A case is attempted at most this many times.
LIVE_DEFAULT_MAX_ATTEMPTS: Final[int] = 3
LIVE_MAX_ATTEMPTS_BOUND: Final[int] = 3

#: Bounded concurrency: the fixed default (sequential) and the hard
#: bound.
LIVE_DEFAULT_CONCURRENCY: Final[int] = 1
LIVE_MAX_CONCURRENCY_BOUND: Final[int] = 4

#: The runner manifest sidecar version (evidence artifact; distinct
#: from the frozen direct-capture schema version it accompanies).
LIVE_MANIFEST_SCHEMA_VERSION: Final[int] = 1

# ---------------------------------------------------------------------------
# The FIXED retry policy (see the module docstring; drift-pinned by
# test against the frozen transport / runtime vocabularies)
# ---------------------------------------------------------------------------

#: Bounded transport-error code -> direct-capture execution status
#: (mirror of the frozen V2 runtime's classification table; the codes
#: outside the direct vocabulary map to their runtime names and are
#: handled by the abort / case-local buckets below).
LIVE_TRANSPORT_ERROR_TO_STATUS: Final[dict[str, str]] = {
    "TIMEOUT": "TIMEOUT",
    "DNS_ERROR": "DNS_ERROR",
    "TLS_ERROR": "TLS_ERROR",
    "CONNECTION_ERROR": "CONNECTION_ERROR",
    "RATE_LIMITED": "RATE_LIMITED",
    "HTTP_ERROR": "HTTP_ERROR",
    "AUTHENTICATION_FAILED": "AUTHENTICATION_FAILED",
    "MODEL_NOT_FOUND": "MODEL_NOT_FOUND",
    "PROVIDER_UNAVAILABLE": "PROVIDER_UNAVAILABLE",
    "PROVIDER_NOT_CONFIGURED": "PROVIDER_NOT_CONFIGURED",
    "INVALID_REQUEST_CONFIGURATION": "INVALID_REQUEST_CONFIGURATION",
    "UNSUPPORTED_PARAMETER": "UNSUPPORTED_PARAMETER",
    "INVALID_PROVIDER_RESPONSE": "INVALID_RESPONSE",
    "RESPONSE_DECODE_ERROR": "MALFORMED_JSON",
    "EMPTY_RESPONSE": "EMPTY_RESPONSE",
    "MALFORMED_JSON": "MALFORMED_JSON",
    "SCHEMA_INVALID": "SCHEMA_INVALID",
    "MODEL_IDENTITY_MISMATCH": "MODEL_IDENTITY_MISMATCH",
    "CASE_REJECTED": "CASE_REJECTED",
}

#: TRANSIENT transport conditions with NO model output: the only
#: statuses a case may be retried for (identical request, bounded).
LIVE_RETRYABLE_STATUSES: Final[frozenset[str]] = frozenset(
    {
        "TIMEOUT",
        "DNS_ERROR",
        "TLS_ERROR",
        "CONNECTION_ERROR",
        "RATE_LIMITED",
        "PROVIDER_UNAVAILABLE",
    }
)

#: Definitive per-case outcomes (a response body was received, or the
#: provider definitively rejected the request / identity): recorded
#: as-is, NEVER retried, run continues.
LIVE_FINAL_STATUSES: Final[frozenset[str]] = frozenset(
    {
        "OK",
        "HTTP_ERROR",
        "EMPTY_RESPONSE",
        "MALFORMED_JSON",
        "SCHEMA_INVALID",
        "INVALID_RESPONSE",
        "MODEL_IDENTITY_MISMATCH",
    }
)

#: Run-level identity / configuration breakage: the case is recorded
#: (when its status is in the direct vocabulary), the run ABORTS, and
#: no further case is sent.
LIVE_ABORT_STATUSES: Final[frozenset[str]] = frozenset(
    {
        "AUTHENTICATION_FAILED",
        "MODEL_NOT_FOUND",
        "INVALID_REQUEST_CONFIGURATION",
        "UNSUPPORTED_PARAMETER",
    }
)

#: Case-local policy rejection (frozen transport vocabulary): the run
#: continues; the case is documented in the manifest only (its status
#: is outside the direct-capture vocabulary, so no document record
#: exists for it - it replays as NOT_CAPTURED, never a pass).
LIVE_CASE_LOCAL_STATUSES: Final[frozenset[str]] = frozenset(
    {"CASE_REJECTED"}
)

_RUN_ID_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[A-Za-z0-9](?:[A-Za-z0-9._-]{0,126}[A-Za-z0-9])?$"
)


class LiveCaptureError(Exception):
    """Bounded live-capture failure (no raw provider body, no
    exception text from the transport, no credential value)."""


class LiveCaptureConfigError(LiveCaptureError):
    """A preflight configuration / identity failure: nothing was
    sent to the model and no artifact is written."""


# ---------------------------------------------------------------------------
# Run configuration (the route is pinned; only the bounded execution
# envelope is operator-selectable)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LiveCaptureConfig:
    """Configuration for ONE bounded live direct-model capture run.

    The target must be EXACTLY one of the frozen V2 pinned route
    identities. The generation parameters are the frozen pinned
    constants (not fields - they cannot be substituted by a caller).
    No API key, base URL, or other credential material is a field:
    the transport adapter reads the server environment.
    """

    provider: str
    model: str
    request_timeout_seconds: float = LIVE_DEFAULT_REQUEST_TIMEOUT_SECONDS
    max_attempts: int = LIVE_DEFAULT_MAX_ATTEMPTS
    max_concurrency: int = LIVE_DEFAULT_CONCURRENCY
    run_id: str = ""
    captured_by: str = "Q3-B live capture runner"
    notes: str = (
        "Q3-B bounded live capture (DIRECT_MODEL_QUALIFICATION); fixed "
        "retry policy: transient transport failures only, bounded "
        "attempts, no semantic-error retries"
    )
    output_dir: str | Path = "semantic_v2_live_captures"
    transport: Any | None = field(default=None, compare=False, repr=False)

    @property
    def route_role(self) -> str:
        """PRIMARY or FALLBACK (the frozen route identity this run
        targets - one run captures exactly one model)."""
        if (self.provider, self.model) == PRIMARY_ROUTE:
            return "PRIMARY"
        return "FALLBACK"


def validate_live_capture_config(config: LiveCaptureConfig) -> None:
    """Fail closed on any configuration that is not the pinned route
    with a bounded execution envelope (before any transport is built
    or called)."""
    if not isinstance(config, LiveCaptureConfig):
        raise TypeError(
            f"config must be LiveCaptureConfig, got {type(config).__name__}"
        )
    if (config.provider, config.model) == PRIMARY_ROUTE:
        pass  # frozen primary route identity
    elif (config.provider, config.model) == FALLBACK_ROUTE:
        pass  # frozen fallback route identity
    else:
        raise LiveCaptureConfigError(
            f"target {config.provider!r}/{config.model!r} is not one of "
            f"the frozen V2 pinned route identities "
            f"{PRIMARY_ROUTE[0]!r}/{PRIMARY_ROUTE[1]!r} or "
            f"{FALLBACK_ROUTE[0]!r}/{FALLBACK_ROUTE[1]!r}; no other "
            "model may enter the frozen V2 qualification"
        )

    timeout = config.request_timeout_seconds
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
        raise LiveCaptureConfigError(
            f"request_timeout_seconds must be a number, "
            f"got {type(timeout).__name__}"
        )
    if not math.isfinite(timeout):
        raise LiveCaptureConfigError(
            f"request_timeout_seconds must be finite, got {timeout}"
        )
    if timeout <= 0:
        raise LiveCaptureConfigError(
            f"request_timeout_seconds must be > 0, got {timeout}"
        )
    if timeout > LIVE_MAX_REQUEST_TIMEOUT_SECONDS:
        raise LiveCaptureConfigError(
            f"request_timeout_seconds must be <= "
            f"{LIVE_MAX_REQUEST_TIMEOUT_SECONDS}, got {timeout}"
        )

    for name, value, bound in (
        ("max_attempts", config.max_attempts, LIVE_MAX_ATTEMPTS_BOUND),
        ("max_concurrency", config.max_concurrency, LIVE_MAX_CONCURRENCY_BOUND),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            raise LiveCaptureConfigError(
                f"{name} must be an int, got {type(value).__name__}"
            )
        if value < 1 or value > bound:
            raise LiveCaptureConfigError(
                f"{name} must be in 1..{bound}, got {value}"
            )

    if not isinstance(config.run_id, str) or not _RUN_ID_PATTERN.match(
        config.run_id
    ):
        raise LiveCaptureConfigError(
            "run_id must be 1..128 characters of [A-Za-z0-9._-] "
            "starting and ending with an alphanumeric "
            f"(got {config.run_id!r}); each live capture is a distinct "
            "run with its own provenance"
        )

    for name, value in (
        ("captured_by", config.captured_by),
        ("notes", config.notes),
    ):
        if not isinstance(value, str):
            raise LiveCaptureConfigError(
                f"{name} must be a str, got {type(value).__name__}"
            )


def build_live_transport(
    provider: str, request_timeout_seconds: float
) -> Any:
    """Build the approved provider transport from the server
    environment (the existing FU3A transport / configuration
    mechanism). The live transport module is imported LAZILY here -
    never at module import time.

    Raises ``LiveCaptureConfigError`` (bounded, no credential value)
    when the provider is not configured.
    """
    from product_intelligence.semantic.transport import (
        get_openai_transport_for_provider,
    )

    try:
        return get_openai_transport_for_provider(
            provider,
            request_timeout_seconds=request_timeout_seconds,
        )
    except ValueError:
        raise LiveCaptureConfigError(
            f"provider {provider!r} is not configured in the server "
            "environment (its base URL / key are absent or unknown); "
            "no live call was made and no artifact was written"
        ) from None


# ---------------------------------------------------------------------------
# Prompt preflight + per-attempt classification
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _CaseEntry:
    case_id: str
    system_prompt: str
    user_prompt: str
    prompt_sha256: str


def _utc_now_iso() -> str:
    """A bounded ISO-8601 UTC instant (microsecond precision, 'Z') -
    the grammar the capture schema verifies (self-checked here)."""
    instant = (
        datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"
    )
    assert UTC_INSTANT_PATTERN.match(instant)
    return instant


def _build_case_entries(corpus: CorpusBundle) -> tuple[_CaseEntry, ...]:
    """Pre-build the EXACT frozen V2 prompt for every eligible semantic
    case (fail closed before any network call if any case cannot be
    rendered - a corpus/contract violation is never sent to a model).

    The 13 contract-negative cases are NEVER constructed into a prompt
    and NEVER sent: they cannot build a typed V2 case by definition,
    and a model response for one is a schema-bypass attack.
    """
    if SEMANTIC_PROMPT_VERSION_V2 != PROMPT_VERSION_V2:
        raise LiveCaptureConfigError(
            "the frozen prompt version drifted from the direct-capture "
            "pin; the capture cannot proceed on an inconsistent "
            "contract"
        )
    entries: list[_CaseEntry] = []
    for case in corpus.cases:
        if case.case_class == CONTRACT_NEGATIVE_CASE_CLASS:
            continue  # never rendered into a prompt, never sent
        typed = case.build_semantic_case()
        prompt = build_semantic_prompt_v2(typed)
        entries.append(
            _CaseEntry(
                case_id=case.case_id,
                system_prompt=prompt.system_prompt,
                user_prompt=prompt.user_prompt,
                prompt_sha256=canonical_sha256(
                    {
                        "case_id": case.case_id,
                        "system_prompt": prompt.system_prompt,
                        "user_prompt": prompt.user_prompt,
                    }
                ),
            )
        )
    return tuple(entries)


def _interpret_outcome(
    outcome: Any, pinned_model: str
) -> tuple[str, str | None]:
    """Classify ONE transport outcome into a bounded direct-capture
    execution status + the raw output when (and only when) the status
    is OK.

    Duck-typed over the transport contract (a failure carries
    ``error_type``; a success carries ``raw_output`` /
    ``provider_reported_model``) - no transport class is imported.
    The OK path reuses the FROZEN production V2 parser composition
    (``classify_raw_response``): identity first, then emptiness, then
    parse + validate - exactly the production runtime boundary
    discipline.
    """
    error_type = getattr(outcome, "error_type", None)
    if error_type is not None:
        if not isinstance(error_type, str):
            raise LiveCaptureError(
                "transport returned a non-string error classification; "
                "this is outside the bounded transport vocabulary and "
                "aborts the run (no capture document is written)"
            )
        status = LIVE_TRANSPORT_ERROR_TO_STATUS.get(error_type)
        if status is None:
            raise LiveCaptureError(
                f"transport returned the unrecognized error code "
                f"{error_type!r}; the bounded classification table does "
                "not cover it, so the run aborts (no capture document "
                "is written)"
            )
        return status, None

    reported = getattr(outcome, "provider_reported_model", None)
    if reported is None or reported != pinned_model:
        # The provider has not proven it ran the pinned model.
        return "MODEL_IDENTITY_MISMATCH", None
    raw_output = getattr(outcome, "raw_output", None)
    if not isinstance(raw_output, str) or not raw_output.strip():
        return "EMPTY_RESPONSE", None
    _validated, failure = classify_raw_response(raw_output)
    if failure is not None:
        return failure, None  # MALFORMED_JSON / SCHEMA_INVALID; no raw kept
    return "OK", raw_output


# ---------------------------------------------------------------------------
# The runner
# ---------------------------------------------------------------------------


@dataclass
class _CaseExecution:
    case_id: str
    attempts: int
    final_status: str
    raw_output: str | None
    latency_ms: float | None
    finish_reason: str | None
    token_usage: dict[str, int] | None
    documented: bool  # True iff a record enters the capture document


@dataclass
class _RunOutcome:
    executions: dict[str, _CaseExecution]
    not_attempted_case_ids: tuple[str, ...]
    abort: tuple[str, str] | None  # (case_id, bounded code)
    started_at: str
    finished_at: str


class LiveCaptureRunner:
    """One bounded live capture run for EXACTLY ONE pinned model.

    The preflight (config validation, corpus load + digest, prompt
    pre-build for all 43 eligible cases, artifact-path reservation,
    transport construction) completes before any network call. The
    execution loop is bounded by the fixed retry policy. The run ends
    in COMPLETED (every eligible case attempted) or ABORTED_<code>
    (the run-level breakage; the attempted evidence is still
    preserved, the unattempted cases are named).
    """

    def __init__(
        self,
        config: LiveCaptureConfig,
        corpus: CorpusBundle,
        *,
        dry_run: bool = False,
    ) -> None:
        validate_live_capture_config(config)
        self._config = config
        self._corpus = corpus
        self._dry_run = dry_run
        # Prompt preflight: the exact frozen V2 prompt for every
        # eligible case, before any network call.
        self._entries = _build_case_entries(corpus)
        # Artifact paths are reserved up front: an existing artifact
        # is never overwritten (evidence is append-only).
        stem = self.artifact_stem
        out_dir = Path(config.output_dir)
        self._capture_path = out_dir / f"{stem}.json"
        self._manifest_path = out_dir / f"{stem}__manifest.json"
        if not dry_run and (
            self._capture_path.exists() or self._manifest_path.exists()
        ):
            raise LiveCaptureConfigError(
                f"an artifact for run {config.run_id!r} already exists "
                f"({self._capture_path} or {self._manifest_path}); live "
                "captures are append-only - choose a new run id"
            )
        self._transport = config.transport
        if not dry_run and self._transport is None:
            self._transport = build_live_transport(
                config.provider, config.request_timeout_seconds
            )

    # -- identity ----------------------------------------------------------

    @property
    def artifact_stem(self) -> str:
        return (
            f"{self._config.run_id}__direct__"
            f"{self._config.provider}_{self._config.model}"
        )

    @property
    def capture_path(self) -> Path:
        return self._capture_path

    @property
    def manifest_path(self) -> Path:
        return self._manifest_path

    # -- execution ---------------------------------------------------------

    def run(self) -> _RunOutcome:
        """Execute every eligible case (bounded) and return the run
        outcome. ``dry_run`` runners never execute (no transport)."""
        if self._dry_run:
            raise LiveCaptureConfigError(
                "a dry-run runner performs the preflight only; it has "
                "no execution"
            )
        config = self._config
        started_at = _utc_now_iso()
        executions: dict[str, _CaseExecution] = {}
        abort: tuple[str, str] | None = None
        abort_flag = threading.Event()

        def execute_one(entry: _CaseEntry) -> _CaseExecution:
            attempts = 0
            while True:
                attempts += 1
                started = time.perf_counter()
                outcome = self._transport.complete(
                    system_prompt=entry.system_prompt,
                    user_prompt=entry.user_prompt,
                    model=config.model,
                    temperature=LIVE_TEMPERATURE,
                    max_tokens=LIVE_MAX_TOKENS,
                )
                latency_ms = (time.perf_counter() - started) * 1000.0
                status, raw = _interpret_outcome(outcome, config.model)

                if status in LIVE_RETRYABLE_STATUSES and attempts < config.max_attempts:
                    continue  # identical request, bounded

                finish_reason = getattr(outcome, "finish_reason", None)
                if finish_reason is not None and not isinstance(
                    finish_reason, str
                ):
                    finish_reason = None
                token_usage = getattr(outcome, "token_usage", None)
                if token_usage is not None and not isinstance(
                    token_usage, dict
                ):
                    token_usage = None
                return _CaseExecution(
                    case_id=entry.case_id,
                    attempts=attempts,
                    final_status=status,
                    raw_output=raw,
                    latency_ms=latency_ms,
                    finish_reason=finish_reason,
                    token_usage=token_usage,
                    documented=status in DIRECT_EXECUTION_STATUSES,
                )

        if config.max_concurrency == 1:
            for entry in self._entries:
                if abort_flag.is_set():
                    break
                execution = execute_one(entry)
                executions[entry.case_id] = execution
                if execution.final_status in LIVE_ABORT_STATUSES:
                    abort = (entry.case_id, execution.final_status)
                    abort_flag.set()
        else:
            with ThreadPoolExecutor(
                max_workers=config.max_concurrency
            ) as pool:
                futures = {}
                for entry in self._entries:
                    if abort_flag.is_set():
                        break
                    futures[pool.submit(execute_one, entry)] = entry
                for future, entry in futures.items():
                    # An unknown-code / non-string classification
                    # propagates (a programming defect is never
                    # converted into a bounded status).
                    execution = future.result()
                    executions[entry.case_id] = execution
                    if execution.final_status in LIVE_ABORT_STATUSES:
                        abort = (entry.case_id, execution.final_status)
                        abort_flag.set()
        return _RunOutcome(
            executions=executions,
            not_attempted_case_ids=tuple(
                entry.case_id
                for entry in self._entries
                if entry.case_id not in executions
            ),
            abort=abort,
            started_at=started_at,
            finished_at=_utc_now_iso(),
        )

    # -- artifacts ---------------------------------------------------------

    def _capture_document(self, outcome: _RunOutcome) -> dict[str, Any]:
        records = []
        for entry in self._entries:  # corpus order, deterministic
            execution = outcome.executions.get(entry.case_id)
            if execution is None or not execution.documented:
                continue  # unattempted / case-local: no document record
            records.append(
                {
                    "case_id": entry.case_id,
                    "execution_status": execution.final_status,
                    "raw_output": execution.raw_output,
                }
            )
        return {
            "capture_mode": DIRECT_CAPTURE_MODE,
            "direct_capture_schema_version": DIRECT_CAPTURE_SCHEMA_VERSION,
            "target_provider": self._config.provider,
            "target_model": self._config.model,
            "corpus_id": self._corpus.corpus_id,
            "corpus_version": self._corpus.corpus_version,
            "corpus_digest": self._corpus.corpus_digest,
            "semantic_contract": SEMANTIC_CONTRACT_VERSION_V2,
            "prompt_version": PROMPT_VERSION_V2,
            "capture_run_id": self._config.run_id,
            "captured_at": outcome.finished_at,
            "captured_by": self._config.captured_by,
            "notes": self._config.notes,
            "records": records,
        }

    def _manifest_document(self, outcome: _RunOutcome) -> dict[str, Any]:
        if outcome.abort is not None:
            run_status = f"ABORTED_{outcome.abort[1]}"
        else:
            run_status = "COMPLETED"
        git_head: str | None = None
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0:
                git_head = result.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            git_head = None
        cases = {}
        for entry in self._entries:
            execution = outcome.executions.get(entry.case_id)
            if execution is None:
                continue
            cases[entry.case_id] = {
                "attempts": execution.attempts,
                "retried": execution.attempts > 1,
                "final_status": execution.final_status,
                "latency_ms": execution.latency_ms,
                "finish_reason": execution.finish_reason,
                "token_usage": execution.token_usage,
                "documented": execution.documented,
                "prompt_sha256": entry.prompt_sha256,
            }
        transport = self._transport
        api_key_configured = False
        if transport is not None:
            api_key_configured = bool(
                getattr(transport, "_api_key", None) is not None
            )
        return {
            "live_manifest_schema_version": LIVE_MANIFEST_SCHEMA_VERSION,
            "run_id": self._config.run_id,
            "run_status": run_status,
            "capture_mode": DIRECT_CAPTURE_MODE,
            "target_provider": self._config.provider,
            "target_model": self._config.model,
            "route_role": self._config.route_role,
            "corpus_id": self._corpus.corpus_id,
            "corpus_version": self._corpus.corpus_version,
            "corpus_digest": self._corpus.corpus_digest,
            "semantic_contract": SEMANTIC_CONTRACT_VERSION_V2,
            "prompt_version": PROMPT_VERSION_V2,
            "system_prompt_sha256": canonical_sha256(
                {"text": SYSTEM_PROMPT_V2}
            ),
            "generation_parameters": {
                "temperature": repr(LIVE_TEMPERATURE),
                "max_tokens": LIVE_MAX_TOKENS,
            },
            "retry_policy": {
                "max_attempts": self._config.max_attempts,
                "retryable_statuses": sorted(LIVE_RETRYABLE_STATUSES),
                "final_statuses": sorted(LIVE_FINAL_STATUSES),
                "abort_statuses": sorted(LIVE_ABORT_STATUSES),
                "case_local_statuses": sorted(LIVE_CASE_LOCAL_STATUSES),
                "delay_seconds": 0,
            },
            "transport_parameters": {
                "request_timeout_seconds": self._config.request_timeout_seconds,
                "max_concurrency": self._config.max_concurrency,
                "transport_class": (
                    type(transport).__name__ if transport is not None else None
                ),
                "api_key_configured": api_key_configured,
            },
            "started_at": outcome.started_at,
            "finished_at": outcome.finished_at,
            "git_head": git_head,
            "captured_by": self._config.captured_by,
            "notes": self._config.notes,
            "attempted_case_ids": [
                entry.case_id
                for entry in self._entries
                if entry.case_id in outcome.executions
            ],
            "not_attempted_case_ids": list(outcome.not_attempted_case_ids),
            "undocumented_cases": {
                case_id: case["final_status"]
                for case_id, case in cases.items()
                if not case["documented"]
            },
            "abort": (
                {
                    "case_id": outcome.abort[0],
                    "code": outcome.abort[1],
                }
                if outcome.abort is not None
                else None
            ),
            "cases": cases,
        }

    def write_artifacts(self, outcome: _RunOutcome) -> tuple[Path, Path | None]:
        """Write the capture document (when any in-vocabulary evidence
        exists) + the manifest sidecar, then self-verify the document
        through the UNCHANGED strict loader (fail closed).

        Returns ``(manifest_path, capture_path_or_None)``.
        """
        out_dir = Path(self._config.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        manifest = self._manifest_document(outcome)
        self._manifest_path.write_text(
            json.dumps(manifest, indent=1, sort_keys=True, ensure_ascii=True)
            + "\n",
            encoding="utf-8",
        )
        capture: dict[str, Any] | None = None
        documented = [
            entry.case_id
            for entry in self._entries
            if outcome.executions.get(entry.case_id) is not None
            and outcome.executions[entry.case_id].documented
        ]
        if documented:
            capture = self._capture_document(outcome)
            self._capture_path.write_text(
                json.dumps(
                    capture, indent=1, sort_keys=True, ensure_ascii=True
                )
                + "\n",
                encoding="utf-8",
            )
            # Self-verification through the frozen schema (the artifact
            # we just wrote must load and bind to the corpus exactly).
            document = load_direct_capture(self._capture_path)
            verify_direct_capture_against_corpus(document, self._corpus)
        return self._manifest_path, (
            self._capture_path if capture is not None else None
        )

    def summary(self, outcome: _RunOutcome) -> dict[str, Any]:
        """A bounded, secret-free summary of the run (for CLI output)."""
        statuses: dict[str, int] = {}
        for execution in outcome.executions.values():
            statuses[execution.final_status] = (
                statuses.get(execution.final_status, 0) + 1
            )
        if outcome.abort is not None:
            run_status = f"ABORTED_{outcome.abort[1]}"
        else:
            run_status = "COMPLETED"
        return {
            "run_id": self._config.run_id,
            "target": f"{self._config.provider}/{self._config.model}",
            "route_role": self._config.route_role,
            "run_status": run_status,
            "corpus_digest": self._corpus.corpus_digest,
            "eligible_cases": len(self._entries),
            "attempted_cases": len(outcome.executions),
            "not_attempted_cases": len(outcome.not_attempted_case_ids),
            "status_counts": statuses,
            "manifest_path": str(self._manifest_path),
            "capture_path": (
                str(self._capture_path)
                if any(
                    outcome.executions.get(entry.case_id) is not None
                    and outcome.executions[entry.case_id].documented
                    for entry in self._entries
                )
                else None
            ),
        }


# ---------------------------------------------------------------------------
# CLI (developer/operator surface; the live call happens only when the
# operator explicitly runs ``capture`` without ``--dry-run``)
# ---------------------------------------------------------------------------


def _generate_run_id(provider: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"q3b-{stamp}-{provider}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m product_intelligence.evaluation.semantic_v2.live_capture",
        description=(
            "Q3-B bounded live DIRECT_MODEL_QUALIFICATION capture runner "
            "(benchmark-only; one pinned model per run; no production "
            "routing, no authority)"
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser(
        "capture",
        help="execute one bounded live capture run for one pinned model",
    )
    p.add_argument(
        "--provider",
        required=True,
        help="the pinned provider identity (validated against the frozen route)",
    )
    p.add_argument(
        "--model",
        required=True,
        help="the pinned model identity (validated against the frozen route)",
    )
    p.add_argument(
        "--corpus",
        required=True,
        help="the digest-sealed qualification corpus (corpus_v1.json)",
    )
    p.add_argument(
        "--run-id",
        default=None,
        help="distinct run id (generated when omitted)",
    )
    p.add_argument("--captured-by", default="Q3-B live capture runner")
    p.add_argument("--notes", default=None)
    p.add_argument(
        "--out-dir", default="semantic_v2_live_captures"
    )
    p.add_argument(
        "--max-attempts",
        type=int,
        default=LIVE_DEFAULT_MAX_ATTEMPTS,
        help=f"bounded per-case attempts, 1..{LIVE_MAX_ATTEMPTS_BOUND}",
    )
    p.add_argument(
        "--max-concurrency",
        type=int,
        default=LIVE_DEFAULT_CONCURRENCY,
        help=f"bounded concurrency, 1..{LIVE_MAX_CONCURRENCY_BOUND}",
    )
    p.add_argument(
        "--request-timeout",
        type=float,
        default=LIVE_DEFAULT_REQUEST_TIMEOUT_SECONDS,
        help=f"bounded request timeout seconds (<= {LIVE_MAX_REQUEST_TIMEOUT_SECONDS})",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="perform the full preflight only; no transport is built and no model call is made",
    )
    p.set_defaults(func=_cmd_capture)
    return parser


def _cmd_capture(args: argparse.Namespace) -> int:
    config = LiveCaptureConfig(
        provider=args.provider,
        model=args.model,
        request_timeout_seconds=args.request_timeout,
        max_attempts=args.max_attempts,
        max_concurrency=args.max_concurrency,
        run_id=args.run_id or _generate_run_id(args.provider),
        captured_by=args.captured_by,
        notes=(
            args.notes
            if args.notes is not None
            else LiveCaptureConfig.notes
        ),
        output_dir=args.out_dir,
    )
    corpus = load_corpus(args.corpus)
    runner = LiveCaptureRunner(config, corpus, dry_run=args.dry_run)
    if args.dry_run:
        entries = runner._entries
        print(f"dry run: {config.provider}/{config.model} "
              f"(route role {config.route_role})")
        print(f"  corpus: {corpus.corpus_id} v{corpus.corpus_version} "
              f"@{corpus.corpus_digest[:12]}...")
        print(f"  eligible semantic cases: {len(entries)}")
        print(
            "  system prompt digest: "
            f"{canonical_sha256({'text': SYSTEM_PROMPT_V2})[:12]}..."
        )
        print(
            "  retry policy: max_attempts="
            f"{config.max_attempts}, concurrency={config.max_concurrency}, "
            f"timeout={config.request_timeout_seconds}s; retryable="
            + ",".join(sorted(LIVE_RETRYABLE_STATUSES))
        )
        print("  no transport built; no model call made; no artifact written")
        return 0
    outcome = runner.run()
    manifest_path, capture_path = runner.write_artifacts(outcome)
    summary = runner.summary(outcome)
    print(f"run {summary['run_id']}: {summary['run_status']}")
    print(
        f"  target: {summary['target']} ({summary['route_role']}), "
        f"corpus @{summary['corpus_digest'][:12]}..."
    )
    print(
        f"  attempted {summary['attempted_cases']}/"
        f"{summary['eligible_cases']} eligible cases; "
        f"not attempted: {summary['not_attempted_cases']}"
    )
    print("  status counts: " + ", ".join(
        f"{k}={v}" for k, v in sorted(summary["status_counts"].items())
    ))
    print(f"  manifest: {manifest_path}")
    print(f"  capture document: {capture_path}")
    if outcome.abort is not None:
        print(
            "  ABORTED at case "
            f"{outcome.abort[0]} with bounded code {outcome.abort[1]}; "
            "the attempted evidence is preserved and the unattempted "
            "cases are named in the manifest"
        )
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:  # bounded CLI surface: one clear failure
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
