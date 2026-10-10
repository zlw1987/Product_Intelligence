"""The DIRECT_MODEL_QUALIFICATION captured-response artifact contract
(Q3-A-FU1).

A direct-model capture is a BENCHMARK-ONLY artifact: it targets EXACTLY
ONE pinned provider/model and records that model's own execution of each
eligible semantic case. It is not a production route: there is no
primary-before-fallback requirement, no fallback attempt, no production
routing, and no production execution or pricing authority. Both frozen
route identities (amax / qwen3.8-27b and vllm-262k / Qwen3.6-27B-262K)
may be qualified INDEPENDENTLY, one capture per model, without
manufacturing any primary failure.

Strictness rules (all fail closed):

* exact key sets at every level; bounded enums everywhere;
* the document names its mode explicitly (``capture_mode`` =
  DIRECT_MODEL_QUALIFICATION) and its own schema version; a
  PRODUCTION_ROUTE capture (``capture.py``) is a different typed schema
  and is refused by this loader - the two modes are never reinterpreted
  across each other;
* the target provider/model must be EXACTLY one of the frozen V2 pinned
  route identities (mirrors re-imported from ``capture.py``; no other
  model may enter the frozen V2 qualification);
* each record carries ONE bounded execution status and the raw model
  output when (and only when) the status is OK;
* exactly one record per case id; no record may name a case that is not
  in the bound corpus or a contract-negative (INPUT_REJECTED) case - a
  model response for an ineligible case is a schema-bypass attack;
* a capture records ONE RUN of ONE model with its own run id and
  provenance.

The frozen contract / prompt identities and the pinned route mirrors
come from ``capture.py`` (the Q3-A allowlisted module) so this module
stays research-independent: least privilege, no new exception.

This module imports no research surface, no execution surface, no
network, and no AI transport.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Final

from product_intelligence.evaluation.semantic_v2.canonical import (
    UTC_INSTANT_PATTERN,
)
from product_intelligence.evaluation.semantic_v2.capture import (
    FALLBACK_ELIGIBLE_STATUSES,
    FALLBACK_ROUTE,
    PRIMARY_ROUTE,
    PROMPT_VERSION_V2,
    PROMPT_VERSION_V2_1,
    SEMANTIC_CONTRACT_VERSION_V2,
)
from product_intelligence.evaluation.semantic_v2.corpus import (
    CONTRACT_NEGATIVE_CASE_CLASS,
    CorpusBundle,
)

__all__ = [
    "DIRECT_CAPTURE_MODE",
    "DIRECT_CAPTURE_SCHEMA_VERSION",
    "DIRECT_EXECUTION_STATUSES",
    "DIRECT_KNOWN_PROMPT_VERSIONS",
    "DirectCaptureDocument",
    "DirectCaptureError",
    "DirectCaptureIntegrityError",
    "DirectCaptureRecord",
    "load_direct_capture",
    "verify_direct_capture_against_corpus",
]

CAPTURE_MODE_PRODUCTION_ROUTE: Final[str] = "PRODUCTION_ROUTE"
DIRECT_CAPTURE_MODE: Final[str] = "DIRECT_MODEL_QUALIFICATION"

DIRECT_CAPTURE_SCHEMA_VERSION: Final[int] = 1

#: The prompt versions a DIRECT_MODEL_QUALIFICATION capture may name:
#: the frozen 2.0 prompt (corpus 1.0.0, the Q3-A/Q3-B context) and the
#: separately versioned 2.1 prompt (corpus 1.1.0, the Q3-B5-P1
#: requalification context). The capture's prompt axis must agree with
#: the prompt axis of the bound corpus's contract binding
#: (``verify_direct_capture_against_corpus``); a mismatch is a
#: cross-version reinterpretation and fails closed. The
#: PRODUCTION_ROUTE capture schema (``capture.py``) stays 2.0-only: it
#: mirrors the live runtime, which executes the frozen 2.0 builder.
DIRECT_KNOWN_PROMPT_VERSIONS: Final[frozenset[str]] = frozenset(
    {PROMPT_VERSION_V2, PROMPT_VERSION_V2_1}
)

#: Bounded direct-model execution statuses: OK plus the frozen
#: runtime's execution-failure vocabulary (mirror of
#: ``FALLBACK_ELIGIBLE_STATUSES`` - the statuses for which the runtime
#: retains no raw body). Pre-execution configuration statuses
#: (PROVIDER_NOT_CONFIGURED / INVALID_REQUEST_CONFIGURATION /
#: UNSUPPORTED_PARAMETER) and CASE_REJECTED / UNKNOWN_ERROR are not
#: model-execution outcomes of a pinned target and are refused.
DIRECT_EXECUTION_STATUSES: Final[frozenset[str]] = frozenset(
    {"OK"} | FALLBACK_ELIGIBLE_STATUSES
)


class DirectCaptureError(Exception):
    """Bounded direct-capture-artifact failure."""


class DirectCaptureIntegrityError(DirectCaptureError):
    """The direct capture does not bind to the model identity / corpus /
    contract it claims (cross-mode, tamper, or version mismatch)."""


@dataclass(frozen=True)
class DirectCaptureRecord:
    case_id: str
    execution_status: str  # bounded; "OK" iff raw_output is present
    raw_output: str | None


@dataclass(frozen=True)
class DirectCaptureDocument:
    capture_mode: str
    direct_capture_schema_version: int
    target_provider: str
    target_model: str
    corpus_id: str
    corpus_version: str
    corpus_digest: str
    semantic_contract: str
    prompt_version: str
    capture_run_id: str
    captured_at: str
    captured_by: str
    notes: str
    records: tuple[DirectCaptureRecord, ...]

    @property
    def target_route(self) -> tuple[str, str]:
        """The single pinned identity this capture belongs to."""
        return (self.target_provider, self.target_model)


_DOCUMENT_KEYS = frozenset(
    {
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
)

_RECORD_KEYS = frozenset({"case_id", "execution_status", "raw_output"})


def _dec_utc_instant(value: Any, path: str) -> str:
    if not isinstance(value, str) or not UTC_INSTANT_PATTERN.match(value):
        raise DirectCaptureError(
            f"{path}: expected an ISO-8601 UTC instant, got {value!r}"
        )
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        raise DirectCaptureError(
            f"{path}: invalid ISO-8601 UTC instant {value!r}"
        ) from None
    if parsed.utcoffset() is None:
        raise DirectCaptureError(f"{path}: non-UTC instant {value!r}")
    return value


def _dec_exact_keys(value: Any, keys: set[str], path: str) -> None:
    if not isinstance(value, dict):
        raise DirectCaptureError(
            f"{path}: expected an object, got {type(value).__name__}"
        )
    missing = keys - set(value.keys())
    if missing:
        raise DirectCaptureError(
            f"{path}: missing required keys {sorted(missing)}"
        )
    unknown = set(value.keys()) - keys
    if unknown:
        raise DirectCaptureError(f"{path}: unknown keys {sorted(unknown)}")


def _dec_record(raw: Any, index: int) -> DirectCaptureRecord:
    path = f"records[{index}]"
    _dec_exact_keys(raw, set(_RECORD_KEYS), path)
    case_id = raw["case_id"]
    if not isinstance(case_id, str) or not case_id:
        raise DirectCaptureError(
            f"{path}.case_id must be a non-empty str"
        )
    status = raw["execution_status"]
    if status not in DIRECT_EXECUTION_STATUSES:
        raise DirectCaptureError(
            f"{path}.execution_status: unknown bounded status {status!r}"
        )
    raw_output = raw["raw_output"]
    if status == "OK":
        if not isinstance(raw_output, str) or not raw_output.strip():
            raise DirectCaptureError(
                f"{path}.raw_output: an OK record must carry the raw "
                "model output (non-empty str)"
            )
    else:
        if raw_output is not None:
            raise DirectCaptureError(
                f"{path}.raw_output: a failed record carries no raw "
                "output (the runtime retains no raw body for failures)"
            )
    return DirectCaptureRecord(
        case_id=case_id,
        execution_status=status,
        raw_output=raw_output,
    )


def load_direct_capture(path: str | Path) -> DirectCaptureDocument:
    """Load + strictly verify one direct-model capture document (no
    corpus yet). Fails closed on any shape, mode, identity, or version
    mismatch - including the cross-mode presentation of a
    PRODUCTION_ROUTE capture."""
    file = Path(path)
    if not file.is_file():
        raise DirectCaptureError(f"direct capture file not found: {file}")
    try:
        raw = json.loads(file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DirectCaptureError(
            f"direct capture is not valid JSON: {exc}"
        ) from exc
    if not isinstance(raw, dict):
        raise DirectCaptureError(
            "direct capture document must be a JSON object"
        )
    # Cross-mode signature: a PRODUCTION_ROUTE document is a different
    # typed schema; it is refused, never reinterpreted.
    if "capture_schema_version" in raw and "capture_mode" not in raw:
        raise DirectCaptureIntegrityError(
            "cross-mode: a PRODUCTION_ROUTE capture document was "
            "presented to the direct-model loader; the two capture "
            "modes are separate typed schemas and are never "
            "reinterpreted across modes"
        )
    _dec_exact_keys(raw, set(_DOCUMENT_KEYS), "direct capture document")
    mode = raw["capture_mode"]
    if mode == CAPTURE_MODE_PRODUCTION_ROUTE:
        raise DirectCaptureIntegrityError(
            "cross-mode: capture_mode is PRODUCTION_ROUTE; production-"
            "route captures are loaded and evaluated by the production-"
            "route harness and are never reinterpreted as direct-model "
            "captures"
        )
    if mode != DIRECT_CAPTURE_MODE:
        raise DirectCaptureError(
            f"unknown capture mode {mode!r} (expected "
            f"{DIRECT_CAPTURE_MODE!r})"
        )
    schema_version = raw["direct_capture_schema_version"]
    if schema_version != DIRECT_CAPTURE_SCHEMA_VERSION:
        raise DirectCaptureError(
            "unknown direct capture schema version "
            f"{schema_version!r} (expected {DIRECT_CAPTURE_SCHEMA_VERSION})"
        )
    provider = raw["target_provider"]
    model = raw["target_model"]
    if not isinstance(provider, str) or not provider:
        raise DirectCaptureError(
            "target_provider must be a non-empty str"
        )
    if not isinstance(model, str) or not model:
        raise DirectCaptureError("target_model must be a non-empty str")
    if (provider, model) == PRIMARY_ROUTE:
        pass  # frozen primary route identity
    elif (provider, model) == FALLBACK_ROUTE:
        pass  # frozen fallback route identity
    else:
        raise DirectCaptureIntegrityError(
            f"target {provider!r}/{model!r} is not one of the frozen V2 "
            f"pinned route identities {PRIMARY_ROUTE[0]!r}/"
            f"{PRIMARY_ROUTE[1]!r} or {FALLBACK_ROUTE[0]!r}/"
            f"{FALLBACK_ROUTE[1]!r}; no other model may enter the "
            "frozen V2 qualification"
        )
    if raw["semantic_contract"] != SEMANTIC_CONTRACT_VERSION_V2:
        raise DirectCaptureIntegrityError(
            f"direct capture semantic_contract {raw['semantic_contract']!r} "
            f"is not the frozen {SEMANTIC_CONTRACT_VERSION_V2!r}"
        )
    if raw["prompt_version"] not in DIRECT_KNOWN_PROMPT_VERSIONS:
        raise DirectCaptureIntegrityError(
            f"direct capture prompt_version {raw['prompt_version']!r} is "
            f"not one of the known V2 prompt versions "
            f"{sorted(DIRECT_KNOWN_PROMPT_VERSIONS)!r}; any other prompt "
            "axis is outside the frozen V2 qualification (the prompt "
            "axis must then be verified against the bound corpus's "
            "contract binding)"
        )
    if (
        not isinstance(raw["corpus_digest"], str)
        or len(raw["corpus_digest"]) != 64
    ):
        raise DirectCaptureError(
            "direct capture corpus_digest must be a 64-hex digest"
        )
    run_id = raw["capture_run_id"]
    if not isinstance(run_id, str) or not run_id:
        raise DirectCaptureError(
            "capture_run_id must be a non-empty str (each direct "
            "capture is a distinct run with its own provenance)"
        )
    records_raw = raw["records"]
    if not isinstance(records_raw, list):
        raise DirectCaptureError("direct capture records must be a list")
    records = tuple(
        _dec_record(r, i) for i, r in enumerate(records_raw)
    )
    seen: set[str] = set()
    for record in records:
        if record.case_id in seen:
            raise DirectCaptureError(
                f"duplicate direct capture record for case "
                f"{record.case_id!r}"
            )
        seen.add(record.case_id)
    return DirectCaptureDocument(
        capture_mode=mode,
        direct_capture_schema_version=schema_version,
        target_provider=provider,
        target_model=model,
        corpus_id=str(raw["corpus_id"] or ""),
        corpus_version=str(raw["corpus_version"] or ""),
        corpus_digest=raw["corpus_digest"],
        semantic_contract=raw["semantic_contract"],
        prompt_version=raw["prompt_version"],
        capture_run_id=run_id,
        captured_at=_dec_utc_instant(raw["captured_at"], "captured_at"),
        captured_by=str(raw["captured_by"] or ""),
        notes=str(raw["notes"] or ""),
        records=records,
    )


def verify_direct_capture_against_corpus(
    capture: DirectCaptureDocument, corpus: CorpusBundle
) -> None:
    """Bind a direct capture to the exact corpus (fail closed on any
    mismatch or bypass). Missing semantic cases are NOT a load error:
    they surface as NOT_CAPTURED at evaluation (coverage shortfall,
    never a pass).

    Cross-version replay isolation (Q3-B5-P1): the capture's prompt
    axis must equal the prompt axis of the corpus's contract binding.
    A 2.0 capture is only interpretable against the corpus sealed under
    the 2.0 binding, and a 2.1 capture only against the corpus sealed
    under the 2.1 binding - a capture never follows a corpus version
    move, and a corpus never reinterprets a capture of a different
    prompt version."""
    if (
        capture.corpus_id != corpus.corpus_id
        or capture.corpus_version != corpus.corpus_version
        or capture.corpus_digest != corpus.corpus_digest
    ):
        raise DirectCaptureIntegrityError(
            "direct capture is bound to a different corpus (id / "
            f"version / digest) than the one presented: corpus="
            f"{corpus.corpus_id}v{corpus.corpus_version}@"
            f"{corpus.corpus_digest[:12]}... "
            f"capture={capture.corpus_id}v{capture.corpus_version}@"
            f"{capture.corpus_digest[:12]}...; captures are only "
            "interpretable against the exact corpus they were produced "
            "for"
        )
    bound_axis = corpus.semantic_contract_binding[1]
    if capture.prompt_version != bound_axis:
        raise DirectCaptureIntegrityError(
            "direct capture prompt axis "
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
            raise DirectCaptureIntegrityError(
                f"direct capture record {record.case_id!r} names a case "
                "that is not in the bound corpus"
            )
        if case.case_class == CONTRACT_NEGATIVE_CASE_CLASS:
            raise DirectCaptureIntegrityError(
                f"direct capture record {record.case_id!r} carries a "
                "model response for a contract-negative case; the V2 "
                "input contract rejects that payload, so no semantic "
                "evaluation may exist for it (schema-bypass attack)"
            )
