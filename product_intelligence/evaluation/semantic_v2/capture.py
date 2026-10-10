"""The captured-response artifact contract for offline V2 qualification.

A capture file is what a LATER live phase (Q3-B) produces: the raw
model responses of one pinned model against the exact frozen prompt,
with bounded per-attempt provenance. This module defines and strictly
verifies that format so the offline harness can evaluate it without any
network or model access.

Strictness rules (all fail closed):

* exact key sets at every level; bounded enums everywhere;
* attempts mirror the frozen runtime discipline: PRIMARY (the frozen
  primary route) first, at most one FALLBACK (the frozen fallback
  route) second - a capture from any other provider/model is outside
  the V2 pinned route;
* the fallback was entered for an EXECUTION failure only (the frozen
  eligible set); the fallback reason equals the frozen status->reason
  mapping;
* ``raw_output`` is present IFF the attempt status is OK (the runtime
  retains no raw body for failed attempts);
* exactly one record per case id; no record may exist for a
  contract-negative (INPUT_REJECTED) case - a model response for an
  ineligible case is a schema-bypass attack.

A capture document records ONE RUN of the frozen pinned route (primary
attempt; fallback attempt on execution failure only). It is NOT
bound to a single model: qualification is projected PER MODEL from
the same run (the primary model's view counts a fallback-answered
case as its own execution failure; the fallback model's view counts a
primary-answered case as not invoked). A primary-model PASS therefore
never automatically qualifies the fallback.

This schema is the PRODUCTION_ROUTE capture mode (``CAPTURE_MODE``):
its coverage is necessarily the production route's (a successful
primary finalizes the case before any fallback data exists). The
independent DIRECT_MODEL_QUALIFICATION mode - one capture per pinned
model, no routing, no manufactured primary failures - is a SEPARATE
typed schema in ``direct_capture.py``; the two modes are never
reinterpreted across each other (both loaders refuse the other mode's
documents).

The bounded status / fallback tables are MIRRORS of the frozen
production runtime vocabulary (the house pattern: evaluation may not
import the runtime's private tables; the drift pin lives in the test
suite).

This module imports the frozen research contract for the route pins
(authorized by the Q3-A exact-allowlist exception in
``tests/research/test_research_identity_boundaries.py``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Final

from product_intelligence.research import (
    FALLBACK_MODEL_V2,
    FALLBACK_PROVIDER_V2,
    PRIMARY_MODEL_V2,
    PRIMARY_PROVIDER_V2,
    PROMPT_VERSION_V2,
    SEMANTIC_CONTRACT_VERSION_V2,
)
from product_intelligence.evaluation.semantic_v2.canonical import (
    UTC_INSTANT_PATTERN,
    assert_json_native,
    canonical_sha256,
)
from product_intelligence.evaluation.semantic_v2.corpus import (
    CONTRACT_NEGATIVE_CASE_CLASS,
    CorpusBundle,
)
from product_intelligence.semantic.contract_v2_1 import (
    SEMANTIC_PROMPT_VERSION_V2_1,
    V2_1_CONTRACT_BINDING,
)

__all__ = [
    "CAPTURE_SCHEMA_VERSION",
    "CaptureAttempt",
    "CaptureDocument",
    "CaptureError",
    "CaptureIntegrityError",
    "CaptureRecord",
    "CaptureRoute",
    "CAPTURE_STATUS_TO_FALLBACK_REASON",
    "FALLBACK_ELIGIBLE_STATUSES",
    "PROMPT_VERSION_V2_1",
    "V2_1_CONTRACT_BINDING",
    "load_capture",
    "verify_capture_against_corpus",
]

CAPTURE_SCHEMA_VERSION: Final[int] = 1

#: The capture mode of this schema (paired with DIRECT_CAPTURE_MODE in
#: ``direct_capture.py``; reports identify the mode explicitly).
CAPTURE_MODE: Final[str] = "PRODUCTION_ROUTE"

#: The separately versioned Prompt 2.1 identity (Q3-B5-P1): the prompt
#: version axis and the immutable 2.1 contract binding (the Q3-B4
#: AD-Q3B4-5 ordering decision put the separately versioned FU3
#: authority token on the 2.1 binding's authority axis). Re-exported
#: from the semantic layer's Prompt 2.1 owner so the direct-capture /
#: live-runner pins never carry a literal copy (drift-pinned by test).
#: The PRODUCTION_ROUTE capture schema of THIS module stays frozen on
#: the 2.0 prompt: the live runtime executes the frozen 2.0 builder, so
#: a production-route capture naming any other prompt version is
#: outside the contract (fail closed).
PROMPT_VERSION_V2_1: Final[str] = SEMANTIC_PROMPT_VERSION_V2_1

#: The frozen V2 pinned route identities (mirror of the contract data).
CaptureRoute = tuple[str, str]
PRIMARY_ROUTE: Final[CaptureRoute] = (PRIMARY_PROVIDER_V2, PRIMARY_MODEL_V2)
FALLBACK_ROUTE: Final[CaptureRoute] = (
    FALLBACK_PROVIDER_V2,
    FALLBACK_MODEL_V2,
)

#: EXECUTION-failure statuses for which the frozen runtime enters the
#: fallback exactly once (mirror of PRIMARY_FALLBACK_ELIGIBLE_ERRORS in
#: the production runtime; drift-pinned by test).
FALLBACK_ELIGIBLE_STATUSES: Final[frozenset[str]] = frozenset(
    {
        "TIMEOUT",
        "DNS_ERROR",
        "TLS_ERROR",
        "CONNECTION_ERROR",
        "RATE_LIMITED",
        "HTTP_ERROR",
        "PROVIDER_UNAVAILABLE",
        "AUTHENTICATION_FAILED",
        "MODEL_NOT_FOUND",
        "EMPTY_RESPONSE",
        "MALFORMED_JSON",
        "SCHEMA_INVALID",
        "MODEL_IDENTITY_MISMATCH",
        "INVALID_RESPONSE",
    }
)

#: Bounded attempt statuses (mirror of the production runtime's
#: SemanticAttemptStatus vocabulary; drift-pinned by test).
ATTEMPT_STATUSES: Final[frozenset[str]] = frozenset(
    {
        "OK",
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
        "EMPTY_RESPONSE",
        "MALFORMED_JSON",
        "SCHEMA_INVALID",
        "INVALID_RESPONSE",
        "MODEL_IDENTITY_MISMATCH",
        "CASE_REJECTED",
        "UNKNOWN_ERROR",
    }
)

#: The frozen status -> fallback-reason mapping (mirror of the
#: production runtime; drift-pinned by test).
CAPTURE_STATUS_TO_FALLBACK_REASON: Final[dict[str, str]] = {
    "TIMEOUT": "TIMEOUT",
    "DNS_ERROR": "DNS_ERROR",
    "TLS_ERROR": "TLS_ERROR",
    "CONNECTION_ERROR": "CONNECTION_ERROR",
    "RATE_LIMITED": "RATE_LIMITED",
    "HTTP_ERROR": "HTTP_ERROR",
    "AUTHENTICATION_FAILED": "AUTHENTICATION_FAILED",
    "MODEL_NOT_FOUND": "MODEL_NOT_FOUND",
    "PROVIDER_UNAVAILABLE": "PROVIDER_UNAVAILABLE",
    "EMPTY_RESPONSE": "EMPTY_RESPONSE",
    "MALFORMED_JSON": "MALFORMED_JSON",
    "SCHEMA_INVALID": "SCHEMA_INVALID",
    "INVALID_RESPONSE": "INVALID_RESPONSE",
    "MODEL_IDENTITY_MISMATCH": "MODEL_IDENTITY_MISMATCH",
}

#: Bounded fallback reasons (the mirror values).
FALLBACK_REASONS: Final[frozenset[str]] = frozenset(
    CAPTURE_STATUS_TO_FALLBACK_REASON.values()
)


class CaptureError(Exception):
    """Bounded capture-artifact failure."""


class CaptureIntegrityError(CaptureError):
    """The capture does not bind to the corpus / route / contract it
    claims (tamper or version mismatch)."""


@dataclass(frozen=True)
class CaptureAttempt:
    role: str  # "PRIMARY" | "FALLBACK"
    provider: str
    model: str
    status: str
    raw_output: str | None


@dataclass(frozen=True)
class CaptureRecord:
    case_id: str
    attempts: tuple[CaptureAttempt, ...]
    fallback_used: bool
    fallback_reason: str | None

    @property
    def accepted_attempt(self) -> CaptureAttempt | None:
        """The attempt whose raw output is the model's accepted answer,
        per the frozen runtime routing rules (primary OK is final;
        otherwise the fallback attempt, if it succeeded)."""
        first = self.attempts[0]
        if first.status == "OK":
            return first
        if len(self.attempts) == 2 and self.attempts[1].status == "OK":
            return self.attempts[1]
        return None

    @property
    def final_failure_status(self) -> str | None:
        """The bounded status of the last attempt when no attempt
        succeeded (the runtime failure classification), or None when an
        attempt was accepted."""
        if self.accepted_attempt is not None:
            return None
        return self.attempts[-1].status


@dataclass(frozen=True)
class CaptureDocument:
    capture_run_id: str
    captured_at: str
    captured_by: str
    notes: str
    corpus_id: str
    corpus_version: str
    corpus_digest: str
    semantic_contract: str
    prompt_version: str
    records: tuple[CaptureRecord, ...]


def _dec_utc_instant(value: Any, path: str) -> str:
    if not isinstance(value, str) or not UTC_INSTANT_PATTERN.match(value):
        raise CaptureError(
            f"{path}: expected an ISO-8601 UTC instant, got {value!r}"
        )
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        raise CaptureError(
            f"{path}: invalid ISO-8601 UTC instant {value!r}"
        ) from None
    if parsed.utcoffset() is None:
        raise CaptureError(f"{path}: non-UTC instant {value!r}")
    return value


def _dec_exact_keys(value: Any, keys: set[str], path: str) -> None:
    if not isinstance(value, dict):
        raise CaptureError(
            f"{path}: expected an object, got {type(value).__name__}"
        )
    missing = keys - set(value.keys())
    if missing:
        raise CaptureError(f"{path}: missing required keys {sorted(missing)}")
    unknown = set(value.keys()) - keys
    if unknown:
        raise CaptureError(f"{path}: unknown keys {sorted(unknown)}")


def _dec_attempt(raw: Any, index: int, expected_route: CaptureRoute) -> CaptureAttempt:
    path = f"attempts[{index}]"
    _dec_exact_keys(
        raw, {"role", "provider", "model", "status", "raw_output"}, path
    )
    role = raw["role"]
    if role not in {"PRIMARY", "FALLBACK"}:
        raise CaptureError(f"{path}.role must be PRIMARY or FALLBACK")
    if (role, index) not in {("PRIMARY", 0), ("FALLBACK", 1)}:
        raise CaptureError(
            f"{path}: attempts must be PRIMARY first and at most one "
            "FALLBACK second"
        )
    provider = raw["provider"]
    model = raw["model"]
    if (provider, model) != expected_route:
        raise CaptureIntegrityError(
            f"{path}: attempt route {provider!r}/{model!r} is not the "
            f"frozen {role} route {expected_route[0]!r}/{expected_route[1]!r}; "
            "a capture from any other provider/model is outside the V2 "
            "pinned route"
        )
    status = raw["status"]
    if status not in ATTEMPT_STATUSES:
        raise CaptureError(f"{path}.status: unknown bounded status {status!r}")
    raw_output = raw["raw_output"]
    if status == "OK":
        if not isinstance(raw_output, str) or not raw_output.strip():
            raise CaptureError(
                f"{path}.raw_output: an OK attempt must carry the raw "
                "model output (non-empty str)"
            )
    else:
        if raw_output is not None:
            raise CaptureError(
                f"{path}.raw_output: a failed attempt carries no raw "
                "output (the runtime retains no raw body for failures)"
            )
    return CaptureAttempt(
        role=role,
        provider=provider,
        model=model,
        status=status,
        raw_output=raw_output,
    )


def _dec_record(raw: Any, index: int) -> CaptureRecord:
    path = f"records[{index}]"
    _dec_exact_keys(
        raw,
        {"case_id", "attempts", "fallback_used", "fallback_reason"},
        path,
    )
    case_id = raw["case_id"]
    if not isinstance(case_id, str) or not case_id:
        raise CaptureError(f"{path}.case_id must be a non-empty str")
    attempts_raw = raw["attempts"]
    if not isinstance(attempts_raw, list) or not 1 <= len(attempts_raw) <= 2:
        raise CaptureError(
            f"{path}.attempts must carry exactly one or two attempts"
        )
    primary = _dec_attempt(attempts_raw[0], 0, PRIMARY_ROUTE)
    attempts = [primary]
    if len(attempts_raw) == 2:
        attempts.append(_dec_attempt(attempts_raw[1], 1, FALLBACK_ROUTE))
    fallback_used = raw["fallback_used"]
    if type(fallback_used) is not bool:
        raise CaptureError(f"{path}.fallback_used must be a bool")
    if fallback_used != (len(attempts) == 2):
        raise CaptureError(
            f"{path}: fallback_used must agree with the attempt count"
        )
    reason = raw["fallback_reason"]
    if len(attempts) == 1:
        if reason is not None:
            raise CaptureError(
                f"{path}: a single-attempt record carries no fallback reason"
            )
    else:
        if primary.status == "OK":
            raise CaptureIntegrityError(
                f"{path}: the primary attempt is OK, so the frozen "
                "runtime makes the primary answer final - a fallback "
                "attempt after a successful primary is outside the "
                "contract"
            )
        if primary.status not in FALLBACK_ELIGIBLE_STATUSES:
            raise CaptureIntegrityError(
                f"{path}: the primary status {primary.status!r} is not "
                "fallback-eligible; the frozen runtime fails closed "
                "without a second attempt"
            )
        expected_reason = CAPTURE_STATUS_TO_FALLBACK_REASON[primary.status]
        if reason != expected_reason:
            raise CaptureIntegrityError(
                f"{path}: fallback_reason {reason!r} disagrees with the "
                f"frozen mapping for {primary.status!r} "
                f"({expected_reason!r})"
            )
    return CaptureRecord(
        case_id=case_id,
        attempts=tuple(attempts),
        fallback_used=fallback_used,
        fallback_reason=reason,
    )


def load_capture(path: str | Path) -> CaptureDocument:
    """Load + strictly verify one capture document (no corpus yet)."""
    file = Path(path)
    if not file.is_file():
        raise CaptureError(f"capture file not found: {file}")
    try:
        raw = json.loads(file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CaptureError(f"capture is not valid JSON: {exc}") from exc
    _dec_exact_keys(
        raw,
        {
            "capture_schema_version",
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
        },
        "capture document",
    )
    if raw["capture_schema_version"] != CAPTURE_SCHEMA_VERSION:
        raise CaptureError(
            f"unknown capture schema version {raw['capture_schema_version']!r}"
        )
    if raw["semantic_contract"] != SEMANTIC_CONTRACT_VERSION_V2:
        raise CaptureIntegrityError(
            f"capture semantic_contract {raw['semantic_contract']!r} is "
            f"not the frozen {SEMANTIC_CONTRACT_VERSION_V2!r}"
        )
    if raw["prompt_version"] != PROMPT_VERSION_V2:
        raise CaptureIntegrityError(
            f"capture prompt_version {raw['prompt_version']!r} is not the "
            f"frozen {PROMPT_VERSION_V2!r}"
        )
    if not isinstance(raw["corpus_digest"], str) or len(raw["corpus_digest"]) != 64:
        raise CaptureError("capture corpus_digest must be a 64-hex digest")
    records_raw = raw["records"]
    if not isinstance(records_raw, list):
        raise CaptureError("capture records must be a list")
    records = tuple(_dec_record(r, i) for i, r in enumerate(records_raw))
    seen: set[str] = set()
    for record in records:
        if record.case_id in seen:
            raise CaptureError(
                f"duplicate capture record for case {record.case_id!r}"
            )
        seen.add(record.case_id)
    return CaptureDocument(
        capture_run_id=str(raw["capture_run_id"] or ""),
        captured_at=_dec_utc_instant(raw["captured_at"], "captured_at"),
        captured_by=str(raw["captured_by"] or ""),
        notes=str(raw["notes"] or ""),
        corpus_id=str(raw["corpus_id"] or ""),
        corpus_version=str(raw["corpus_version"] or ""),
        corpus_digest=raw["corpus_digest"],
        semantic_contract=raw["semantic_contract"],
        prompt_version=raw["prompt_version"],
        records=records,
    )


def verify_capture_against_corpus(
    capture: CaptureDocument, corpus: CorpusBundle
) -> None:
    """Bind a capture to the exact corpus (fail closed on any mismatch
    or bypass).

    Cross-version replay isolation (Q3-B5-P1): the production-route
    capture's prompt axis (the frozen 2.0 prompt - the live runtime's
    builder) must equal the prompt axis of the corpus's contract
    binding. A 2.0 capture is only interpretable against the corpus
    sealed under the 2.0 binding; it is never reinterpreted against a
    corpus sealed under another prompt version (and a 2.1-prompt
    capture cannot exist in this mode at all - the loader refuses it).
    """
    if (
        capture.corpus_id != corpus.corpus_id
        or capture.corpus_version != corpus.corpus_version
        or capture.corpus_digest != corpus.corpus_digest
    ):
        raise CaptureIntegrityError(
            "capture is bound to a different corpus (id / version / "
            f"digest) than the one presented: corpus={corpus.corpus_id}"
            f"v{corpus.corpus_version}@{corpus.corpus_digest[:12]}... "
            f"capture={capture.corpus_id}v{capture.corpus_version}@"
            f"{capture.corpus_digest[:12]}...; captures are only "
            "interpretable against the exact corpus they were produced "
            "for"
        )
    bound_axis = corpus.semantic_contract_binding[1]
    if capture.prompt_version != bound_axis:
        raise CaptureIntegrityError(
            "capture prompt axis "
            f"{capture.prompt_version!r} does not match the bound "
            f"corpus's contract binding prompt axis {bound_axis!r}; "
            "a capture of one prompt version is never reinterpreted "
            "against a corpus sealed under another (cross-version "
            "replay refusal)"
        )
    by_id = {case.case_id: case for case in corpus.cases}
    for record in capture.records:
        case = by_id.get(record.case_id)
        if case is None:
            raise CaptureIntegrityError(
                f"capture record {record.case_id!r} names a case that is "
                "not in the bound corpus"
            )
        if case.case_class == CONTRACT_NEGATIVE_CASE_CLASS:
            raise CaptureIntegrityError(
                f"capture record {record.case_id!r} carries a model "
                "response for a contract-negative case; the V2 input "
                "contract rejects that payload, so no semantic "
                "evaluation may exist for it (schema-bypass attack)"
            )
