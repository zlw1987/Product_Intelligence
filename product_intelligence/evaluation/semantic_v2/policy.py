"""The DRAFT qualification policy artifact contract (Q3-A).

A qualification policy states the thresholds a model must meet to be
qualified (semantic precision / recall, response validity, coverage).
Q3-A ships the DRAFT policy (``status: DRAFT``,
``approval.approved: false``): the proposed values are a reviewable
proposal, NOT finalized production acceptance thresholds. Without an
APPROVED policy the qualification decision can never be QUALIFIED (the
decision is POLICY_PENDING, even when every threshold would be met).

The policy binds to the exact corpus identity it applies to (a policy
for a different corpus is not applicable - fail closed).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from product_intelligence.evaluation.semantic_v2.canonical import (
    UTC_INSTANT_PATTERN,
)

__all__ = [
    "POLICY_SCHEMA_VERSION",
    "THRESHOLD_NAMES",
    "PolicyDocument",
    "PolicyError",
    "load_policy",
    "policy_applies_to",
    "evaluate_thresholds",
]

POLICY_SCHEMA_VERSION: Final[int] = 1

#: The bounded threshold vocabulary (the spec's configurable surface:
#: semantic precision, recall, response validity, coverage).
THRESHOLD_NAMES: Final[tuple[str, ...]] = (
    "match_precision_min",
    "match_recall_min",
    "valid_structured_response_rate_min",
    "eligible_coverage_min",
)

_POLICY_STATUS: Final[frozenset[str]] = frozenset({"DRAFT", "APPROVED"})


class PolicyError(Exception):
    """Bounded policy-artifact failure."""


@dataclass(frozen=True)
class PolicyDocument:
    policy_id: str
    policy_version: str
    status: str
    approved: bool
    approved_by: str | None
    approved_utc: str | None
    corpus_id: str
    corpus_version: str
    thresholds: dict[str, float]
    rationale: str


def _dec_exact_keys(value: Any, keys: set[str], path: str) -> None:
    if not isinstance(value, dict):
        raise PolicyError(f"{path}: expected an object")
    missing = keys - set(value.keys())
    if missing:
        raise PolicyError(f"{path}: missing keys {sorted(missing)}")
    unknown = set(value.keys()) - keys
    if unknown:
        raise PolicyError(f"{path}: unknown keys {sorted(unknown)}")


def load_policy(path: str | Path) -> PolicyDocument:
    """Load + strictly verify one policy artifact."""
    file = Path(path)
    if not file.is_file():
        raise PolicyError(f"policy file not found: {file}")
    try:
        raw = json.loads(file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PolicyError(f"policy is not valid JSON: {exc}") from exc
    _dec_exact_keys(
        raw,
        {
            "policy_schema_version",
            "policy_id",
            "policy_version",
            "status",
            "approval",
            "applicability",
            "thresholds",
            "rationale",
        },
        "policy document",
    )
    if raw["policy_schema_version"] != POLICY_SCHEMA_VERSION:
        raise PolicyError(
            f"unknown policy schema version {raw['policy_schema_version']!r}"
        )
    _dec_exact_keys(
        raw["approval"],
        {"approved", "approved_by", "approved_utc"},
        "policy approval",
    )
    approved = raw["approval"]["approved"]
    if type(approved) is not bool:
        raise PolicyError("approval.approved must be a bool")
    approved_by = raw["approval"]["approved_by"]
    approved_utc = raw["approval"]["approved_utc"]
    if approved:
        if not isinstance(approved_by, str) or not approved_by:
            raise PolicyError(
                "an approved policy must name who approved it"
            )
        if (
            not isinstance(approved_utc, str)
            or not UTC_INSTANT_PATTERN.match(approved_utc)
        ):
            raise PolicyError(
                "an approved policy must carry the approval instant"
            )
    else:
        if approved_by is not None or approved_utc is not None:
            raise PolicyError(
                "an unapproved policy carries no approver / instant"
            )
    status = raw["status"]
    if status not in _POLICY_STATUS:
        raise PolicyError(f"unknown policy status {status!r}")
    if status == "APPROVED" and not approved:
        raise PolicyError("status APPROVED requires approval.approved true")
    if status == "DRAFT" and approved:
        raise PolicyError("status DRAFT cannot carry an approval")
    _dec_exact_keys(
        raw["applicability"],
        {"corpus_id", "corpus_version"},
        "policy applicability",
    )
    thresholds_raw = raw["thresholds"]
    if not isinstance(thresholds_raw, dict):
        raise PolicyError("policy thresholds must be an object")
    if set(thresholds_raw.keys()) != set(THRESHOLD_NAMES):
        raise PolicyError(
            f"policy thresholds must carry exactly {list(THRESHOLD_NAMES)}"
        )
    thresholds: dict[str, float] = {}
    for name in THRESHOLD_NAMES:
        value = thresholds_raw[name]
        if type(value) is not float or not (0.0 <= value <= 1.0):
            raise PolicyError(
                f"threshold {name} must be a float in [0, 1], "
                f"got {value!r}"
            )
        thresholds[name] = value
    return PolicyDocument(
        policy_id=str(raw["policy_id"]),
        policy_version=str(raw["policy_version"]),
        status=status,
        approved=approved,
        approved_by=approved_by if approved else None,
        approved_utc=approved_utc if approved else None,
        corpus_id=str(raw["applicability"]["corpus_id"]),
        corpus_version=str(raw["applicability"]["corpus_version"]),
        thresholds=thresholds,
        rationale=str(raw["rationale"]),
    )


def policy_applies_to(
    policy: PolicyDocument,
    corpus_id: str,
    corpus_version: str,
) -> bool:
    """Whether one policy applies to one corpus identity."""
    return (
        policy.corpus_id == corpus_id
        and policy.corpus_version == corpus_version
    )


#: Threshold name -> (metric key in the evaluator's metric surface,
#: the bound direction).
_METRIC_KEYS: Final[dict[str, tuple[str, str]]] = {
    "match_precision_min": ("match_precision", "min"),
    "match_recall_min": ("match_recall", "min"),
    "valid_structured_response_rate_min": (
        "valid_structured_response_rate",
        "min",
    ),
    "eligible_coverage_min": ("eligible_coverage", "min"),
}


def evaluate_thresholds(
    policy: PolicyDocument, metrics: dict[str, Any]
) -> dict[str, Any]:
    """Evaluate the policy's thresholds against one metric surface.

    A threshold whose metric is unavailable (insufficient denominator)
    is reported as ``met: null`` - never as met, never hidden.
    """
    counts = metrics["counts"]
    coverage_denominator = counts["eligible_semantic_cases"]
    coverage_value = (
        counts["evaluated_cases"] / coverage_denominator
        if coverage_denominator > 0
        else None
    )
    out: dict[str, Any] = {}
    for name in THRESHOLD_NAMES:
        metric_key, direction = _METRIC_KEYS[name]
        bound = policy.thresholds[name]
        if metric_key == "eligible_coverage":
            value = (
                f"{coverage_value:.6f}"
                if coverage_value is not None
                else None
            )
            status = "computed" if coverage_value is not None else "unavailable"
        else:
            entry = metrics[metric_key]
            value = entry["value"]
            status = entry["status"]
        if value is None:
            met: bool | None = None
        elif direction == "min":
            met = float(value) >= bound
        else:  # pragma: no cover - vocabulary is min-bounded
            met = float(value) <= bound
        out[name] = {
            "bound": f"{bound:.6f}",
            "direction": direction,
            "value": value,
            "status": status,
            "met": met,
        }
    return out
