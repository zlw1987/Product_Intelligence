"""The bounded LIVE DIRECT_MODEL_QUALIFICATION capture runner (Q3-B).

BENCHMARK-ONLY live infrastructure: it executes the frozen Semantic V2
qualification corpus independently against EXACTLY ONE pinned model
(the frozen primary or the frozen fallback identity - nothing else may
enter the qualification) and writes the approved Q3-A-FU1
``DIRECT_MODEL_QUALIFICATION`` capture document for that model.

What it reuses (never recreates):

* the production V2 prompt builder for the BOUND prompt version over
  the REAL typed corpus case (``CorpusCase.build_semantic_case``):
  corpus 1.0.0 (the frozen 2.0 binding) ->
  ``semantic.contract_v2.build_semantic_prompt_v2``; corpus 1.1.0
  (the separately versioned 2.1 binding) ->
  ``semantic.contract_v2_1.build_semantic_prompt_v2_1`` - every sent
  prompt is byte-exact output of that version's builder, and the
  corpus's binding selects the version (a capture of one prompt
  version can never be rendered from the other corpus);
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
  sent. Out-of-vocabulary transport evidence (an unrecognized code, or
  a non-string classification) is recorded ONLY as the bounded
  ``LIVE_UNRECOGNIZED_TRANSPORT_CODE`` marker: the transport-provided
  value itself is never echoed into any message, manifest, or artifact
  (it may contain URLs, request details, or credentials);
* CASE_REJECTED (a content-policy rejection of the case's own
  content) is CASE-LOCAL per the frozen transport vocabulary: the run
  continues, the case is documented in the manifest sidecar, and no
  record for it enters the capture document (its status is outside the
  direct-capture vocabulary; the case replays as NOT_CAPTURED - a
  coverage shortfall, never a pass);
* an unexpected exception raised by the transport is a programming
  defect: it propagates, is never converted into a bounded status, and
  no capture document is written for the run. The CLI reports it with
  the fixed, non-sensitive ``UNEXPECTED_RUNNER_FAILURE`` message and a
  nonzero exit - the raw exception text may contain provider URLs,
  request details, or credentials, so it is never printed.

Run-level abort boundary (concurrent mode):

* the bounded dispatcher never exceeds ``max_concurrency`` in-flight
  cases and dispatches a new case ONLY while no abort has been
  observed (strict dispatch-stop: once an abort-class failure is
  recorded, no further case is submitted);
* on abort, submitted-but-not-started work is cancelled (it is never
  called and never fabricated into a response); already in-flight work
  runs to completion and its outcome is preserved verbatim;
* the manifest distinguishes, per case: ``completed`` (an outcome was
  preserved), ``cancelled`` (submitted, not started, no model call),
  and ``never_attempted`` (never dispatched, no model call).
  In-flight cases are always collected before the manifest is
  written, so the manifest itself carries only ``completed`` /
  ``cancelled`` / ``never_attempted`` states.

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
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
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
    PROMPT_VERSION_V2_1,
    SEMANTIC_CONTRACT_VERSION_V2,
)
from product_intelligence.evaluation.semantic_v2.corpus import (
    CONTRACT_NEGATIVE_CASE_CLASS,
    CorpusBundle,
    CorpusError,
    load_corpus,
)
from product_intelligence.evaluation.semantic_v2.direct_capture import (
    DIRECT_CAPTURE_MODE,
    DIRECT_CAPTURE_SCHEMA_VERSION,
    DIRECT_EXECUTION_STATUSES,
    DirectCaptureError,
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
from product_intelligence.semantic.contract_v2_1 import (
    SEMANTIC_PROMPT_VERSION_V2_1,
    SYSTEM_PROMPT_V2_1,
    build_semantic_prompt_v2_1,
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
    "LIVE_UNRECOGNIZED_TRANSPORT_CODE",
    "LiveCaptureConfig",
    "LiveCaptureError",
    "LiveCaptureRunner",
    "UNEXPECTED_RUNNER_FAILURE_MESSAGE",
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

#: A bounded run-level ABORT marker for transport evidence outside the
#: classification vocabulary (an unrecognized string code, or a
#: non-string classification): the attempted case is recorded in the
#: manifest ONLY under this code (no capture document record - the
#: frozen schema cannot represent it), the run aborts, and no further
#: case is sent. The transport-provided value itself is never echoed
#: into any message, manifest, or artifact (it may contain URLs,
#: request details, or credentials). Deliberately outside the four
#: policy buckets (which stay exactly the frozen vocabulary).
LIVE_UNRECOGNIZED_TRANSPORT_CODE: Final[str] = "UNRECOGNIZED_TRANSPORT_CODE"

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
        # Bounded: names only the expected and actual TYPE, never a
        # value the caller supplied.
        raise LiveCaptureConfigError(
            f"config must be LiveCaptureConfig, got {type(config).__name__}"
        )
    if (config.provider, config.model) == PRIMARY_ROUTE:
        pass  # frozen primary route identity
    elif (config.provider, config.model) == FALLBACK_ROUTE:
        pass  # frozen fallback route identity
    else:
        # Bounded: the rejected provider/model value is operator
        # input and is NOT echoed (it may contain arbitrary text);
        # only the frozen pinned identities are named.
        raise LiveCaptureConfigError(
            "the target provider/model is not one of the frozen V2 "
            f"pinned route identities ({PRIMARY_ROUTE[0]!r}/"
            f"{PRIMARY_ROUTE[1]!r} or {FALLBACK_ROUTE[0]!r}/"
            f"{FALLBACK_ROUTE[1]!r}); no other model may enter the "
            "frozen V2 qualification (the rejected value is not "
            "echoed)"
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
        # Bounded: the rejected run_id value is operator input and is
        # NOT echoed; only the accepted grammar is stated.
        raise LiveCaptureConfigError(
            "run_id must be 1..128 characters of [A-Za-z0-9._-] "
            "starting and ending with an alphanumeric (the rejected "
            "value is not echoed); each live capture is a distinct "
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
        # Bounded: the provider argument is operator input and is NOT
        # echoed; no credential value or endpoint is named.
        raise LiveCaptureConfigError(
            "the provider is not configured in the server environment "
            "(its base URL / key are absent or unknown); no live call "
            "was made and no artifact was written"
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


def _build_case_entries(
    corpus: CorpusBundle,
) -> tuple[tuple[_CaseEntry, ...], str, str]:
    """Pre-build the EXACT production prompt for every eligible
    semantic case (fail closed before any network call if any case
    cannot be rendered - a corpus/contract violation is never sent to
    a model).

    The prompt version is selected by the corpus's contract binding
    (Q3-B5-P1): corpus 1.0.0 (the frozen 2.0 binding) renders with
    the frozen 2.0 builder; corpus 1.1.0 (the separately versioned
    2.1 binding) renders with the separately versioned 2.1 builder.
    A binding whose prompt axis is neither known version fails
    closed (the loader already refuses such a corpus; this is
    defense in depth). Returns ``(entries, prompt_version,
    system_prompt)``.

    The 13 contract-negative cases are NEVER constructed into a prompt
    and NEVER sent: they cannot build a typed V2 case by definition,
    and a model response for one is a schema-bypass attack.
    """
    axis = corpus.semantic_contract_binding[1]
    if axis == PROMPT_VERSION_V2:
        if SEMANTIC_PROMPT_VERSION_V2 != PROMPT_VERSION_V2:
            raise LiveCaptureConfigError(
                "the frozen prompt version drifted from the direct-capture "
                "pin; the capture cannot proceed on an inconsistent "
                "contract"
            )
        builder = build_semantic_prompt_v2
        system_prompt = SYSTEM_PROMPT_V2
    elif axis == PROMPT_VERSION_V2_1:
        if SEMANTIC_PROMPT_VERSION_V2_1 != PROMPT_VERSION_V2_1:
            raise LiveCaptureConfigError(
                "the separately versioned 2.1 prompt version drifted from "
                "the direct-capture pin; the capture cannot proceed on an "
                "inconsistent contract"
            )
        builder = build_semantic_prompt_v2_1
        system_prompt = SYSTEM_PROMPT_V2_1
    else:
        raise LiveCaptureConfigError(
            "the bound corpus's contract binding names an unknown "
            f"prompt axis {axis!r}; the runner renders only the "
            "known production prompt versions"
        )
    entries: list[_CaseEntry] = []
    for case in corpus.cases:
        if case.case_class == CONTRACT_NEGATIVE_CASE_CLASS:
            continue  # never rendered into a prompt, never sent
        typed = case.build_semantic_case()
        prompt = builder(typed)
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
    return tuple(entries), axis, system_prompt


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
        status = (
            LIVE_TRANSPORT_ERROR_TO_STATUS.get(error_type)
            if isinstance(error_type, str)
            else None
        )
        if status is None:
            # Out-of-vocabulary transport evidence (an unrecognized
            # code, or a non-string classification): a bounded
            # run-level ABORT. The transport-provided value is NEVER
            # echoed into a message, manifest, or artifact - it may
            # contain URLs, request details, or credentials.
            return LIVE_UNRECOGNIZED_TRANSPORT_CODE, None
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
    #: Every eligible case, in corpus order, classified as:
    #: ``completed`` (an outcome was preserved), ``cancelled``
    #: (submitted, not started, cancelled at abort - no model call),
    #: or ``never_attempted`` (never dispatched - no model call).
    dispatch_states: dict[str, str]


class LiveCaptureRunner:
    """One bounded live capture run for EXACTLY ONE pinned model.

    The preflight (config validation, corpus load + digest, prompt
    pre-build for all 43 eligible cases, artifact-path reservation,
    transport construction) completes before any network call. The
    execution loop is bounded by the fixed retry policy. The run ends
    in COMPLETED (every eligible case attempted) or ABORTED_<code>
    (the run-level breakage; the attempted evidence is still
    preserved, the unattempted cases are named).

    Run-level abort boundary: in sequential mode an observed abort
    stops the very next dispatch. In concurrent mode the bounded
    dispatcher holds at most ``max_concurrency`` cases in flight and
    dispatches a new case ONLY while no abort has been observed;
    once an abort is recorded, submitted-but-not-started work is
    cancelled, already in-flight work is collected (its outcome is
    preserved verbatim), and nothing further is dispatched.
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
        # Prompt preflight: the exact production prompt for the bound
        # prompt version (2.0 or 2.1, selected by the corpus's
        # contract binding) for every eligible case, before any
        # network call.
        self._entries, self._prompt_version, self._system_prompt = (
            _build_case_entries(corpus)
        )
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
        dispatch_states: dict[str, str] = {}
        abort: tuple[str, str] | None = None

        def note_abort(entry: _CaseEntry, execution: _CaseExecution) -> None:
            nonlocal abort
            if abort is None and self._is_abort_status(execution.final_status):
                abort = (entry.case_id, execution.final_status)

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
            # Sequential: one case at a time. An observed abort stops
            # the very next dispatch; the remaining cases are never
            # attempted (no model call).
            for entry in self._entries:
                if abort is not None:
                    dispatch_states[entry.case_id] = "never_attempted"
                    continue
                execution = execute_one(entry)
                executions[entry.case_id] = execution
                dispatch_states[entry.case_id] = "completed"
                note_abort(entry, execution)
        else:
            # Bounded concurrent dispatcher (strict dispatch-stop):
            # at most ``max_concurrency`` cases in flight; a new case
            # is submitted only while no abort has been observed. On
            # abort: submitted-but-not-started work is cancelled (it
            # is never called), already in-flight work runs to
            # completion and its outcome is preserved, and nothing
            # further is dispatched.
            next_index = 0
            in_flight: dict[Any, _CaseEntry] = {}

            def collect(fut: Any) -> None:
                entry = in_flight.pop(fut)
                # An unexpected worker exception propagates (a
                # programming defect is never converted into a
                # bounded status); the run then fails with no
                # capture document.
                execution = fut.result()
                executions[entry.case_id] = execution
                dispatch_states[entry.case_id] = "completed"
                note_abort(entry, execution)

            with ThreadPoolExecutor(
                max_workers=config.max_concurrency
            ) as pool:
                while abort is None:
                    if next_index >= len(self._entries):
                        # All cases dispatched: drain to completion.
                        while in_flight:
                            done, _ = wait(
                                list(in_flight),
                                return_when=FIRST_COMPLETED,
                            )
                            for fut in done:
                                collect(fut)
                        break
                    while (
                        next_index < len(self._entries)
                        and len(in_flight) < config.max_concurrency
                    ):
                        entry = self._entries[next_index]
                        next_index += 1
                        in_flight[pool.submit(execute_one, entry)] = entry
                    done, _ = wait(
                        list(in_flight), return_when=FIRST_COMPLETED
                    )
                    for fut in done:
                        collect(fut)
                    if abort is not None:
                        # Strict dispatch-stop: cancel work that has
                        # not started (it is never called and never
                        # fabricated into a response); preserve the
                        # outcome of work already in flight.
                        for fut in list(in_flight):
                            entry = in_flight[fut]
                            if fut.cancel():
                                in_flight.pop(fut)
                                dispatch_states[entry.case_id] = (
                                    "cancelled"
                                )
                        if in_flight:
                            done, _ = wait(list(in_flight))
                            for fut in done:
                                collect(fut)
        for entry in self._entries:
            dispatch_states.setdefault(entry.case_id, "never_attempted")
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
            dispatch_states=dict(dispatch_states),
        )

    @staticmethod
    def _is_abort_status(status: str) -> bool:
        """True iff a bounded case outcome is a run-level abort
        (the frozen abort vocabulary, or out-of-vocabulary transport
        evidence reduced to its bounded marker)."""
        return status in LIVE_ABORT_STATUSES or status == (
            LIVE_UNRECOGNIZED_TRANSPORT_CODE
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
            "prompt_version": self._prompt_version,
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
            "prompt_version": self._prompt_version,
            "system_prompt_sha256": canonical_sha256(
                {"text": self._system_prompt}
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
            "dispatch_states": {
                entry.case_id: outcome.dispatch_states[entry.case_id]
                for entry in self._entries
            },
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
        print(f"  prompt version (bound by the corpus): {runner._prompt_version}")
        print(
            "  system prompt digest: "
            f"{canonical_sha256({'text': runner._system_prompt})[:12]}..."
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


#: The fixed, non-sensitive CLI message for an unexpected (non-bounded)
#: exception. Raw exception text may contain provider URLs, request
#: details, credentials, or other sensitive information, so it is
#: NEVER reported; only this fixed code and text is.
UNEXPECTED_RUNNER_FAILURE_MESSAGE: Final[str] = (
    "error: UNEXPECTED_RUNNER_FAILURE - the live capture runner raised "
    "an unexpected error. Its message is not reported because it may "
    "contain sensitive information (provider URLs, request details, "
    "credentials). The run failed with a nonzero exit; no capture "
    "outcome is implied and no qualification result is granted."
)


def main(argv: list[str] | None = None) -> int:
    """The bounded CLI surface.

    Exit codes: 0 = success (COMPLETED or dry run); 1 = bounded run-
    level abort (evidence preserved, unattempted cases named); 2 =
    bounded preflight / configuration / loader failure (the approved
    bounded error types, whose messages are bounded by construction);
    3 = unexpected non-bounded failure (the fixed, non-sensitive
    ``UNEXPECTED_RUNNER_FAILURE`` message only - never the raw
    exception text).
    """
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except LiveCaptureConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except LiveCaptureError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (CorpusError, DirectCaptureError) as exc:
        # Approved bounded loader errors (strict schema contracts;
        # bounded messages by construction).
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except Exception:
        # Never print a raw arbitrary exception message.
        print(UNEXPECTED_RUNNER_FAILURE_MESSAGE, file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
