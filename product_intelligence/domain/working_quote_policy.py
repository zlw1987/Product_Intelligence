"""Framework-free Working Quote workflow policy.

This domain module owns only workflow classification vocabulary and pure
decision rules. It has no knowledge of Django, persistence, research
assessment classes, providers, execution, or web presentation.

Callers must establish any research-specific facts (for example whether a SKU
is an exact/normalized-exact target match) before invoking this policy.
"""

from __future__ import annotations

from enum import Enum
from typing import Sequence


class WorkingQuoteDisposition(str, Enum):
    AUTO_INCLUDE_UNVERIFIED = "AUTO_INCLUDE_UNVERIFIED"
    CONFIRMED = "CONFIRMED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    HARD_CONFLICT = "HARD_CONFLICT"
    REJECTED = "REJECTED"


_HARD_IDENTITY_CONFLICT_TERMS = (
    "mpn",
    "part number",
    "manufacturer part number",
    "model",
    "suffix",
    "revision",
    "capacity",
    "memory size",
    "form factor",
    "interface",
    "connector",
    "accessory",
    "compatible with",
    "replacement",
    "multipack",
    "multi pack",
    "pack size",
    "pack quantity",
    "product type",
    "manufacturer",
    "brand",
)


def _normalized_conflicts(
    conflicting_attributes: Sequence[str] | None,
) -> tuple[str, ...] | None:
    if conflicting_attributes is None:
        return ()
    if isinstance(conflicting_attributes, (str, bytes)):
        values = (conflicting_attributes,)
    else:
        try:
            values = tuple(conflicting_attributes)
        except TypeError:
            return None

    normalized: list[str] = []
    for raw in values:
        if not isinstance(raw, str):
            return None
        normalized.append(
            " ".join(
                raw.strip().lower().replace("_", " ").replace("-", " ").split()
            )
        )
    return tuple(normalized)


def has_hard_identity_conflict(
    conflicting_attributes: Sequence[str] | None,
) -> bool:
    """Return True for explicit identity-critical conflicts.

    Malformed conflict collections fail closed as hard conflicts. Unknown
    non-identity conflict labels remain reviewable rather than being silently
    promoted to an automatic exclusion.
    """
    normalized = _normalized_conflicts(conflicting_attributes)
    if normalized is None:
        return True

    return any(
        any(term in conflict for term in _HARD_IDENTITY_CONFLICT_TERMS)
        for conflict in normalized
        if conflict
    )


def classify_working_quote_policy(
    *,
    review_state: str,
    semantic_confidence: str,
    strong_sku_identity: bool,
    conflicting_attributes: Sequence[str] | None,
) -> WorkingQuoteDisposition:
    """Classify a binding-valid AI candidate for Working Quote workflow.

    strong_sku_identity must already mean exact/normalized-exact target
    identity under the caller's authoritative identity comparator. This
    function never derives identity itself.
    """
    state = (review_state or "").strip().upper()
    if state == "REJECTED":
        return WorkingQuoteDisposition.REJECTED

    if has_hard_identity_conflict(conflicting_attributes):
        return WorkingQuoteDisposition.HARD_CONFLICT

    if state == "CONFIRMED":
        return WorkingQuoteDisposition.CONFIRMED
    if state != "UNREVIEWED":
        raise ValueError(f"unsupported review state: {review_state!r}")

    confidence = (semantic_confidence or "").strip().upper()
    normalized = _normalized_conflicts(conflicting_attributes)
    has_any_conflict = normalized is None or any(normalized)

    if confidence == "LOW":
        return WorkingQuoteDisposition.LOW_CONFIDENCE
    if confidence == "MEDIUM":
        return WorkingQuoteDisposition.NEEDS_REVIEW
    if confidence == "HIGH":
        if strong_sku_identity and not has_any_conflict:
            return WorkingQuoteDisposition.AUTO_INCLUDE_UNVERIFIED
        return WorkingQuoteDisposition.NEEDS_REVIEW

    return WorkingQuoteDisposition.NEEDS_REVIEW
