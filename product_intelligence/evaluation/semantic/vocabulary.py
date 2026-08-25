"""Semantic match decision vocabulary (PRODUCT-INTEL.SEMANTIC).

This module defines the decision vocabulary and validation logic for
semantic match qualification. It is used by offline evaluators to validate
model responses and compute metrics.

No live model integration is required for this phase.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SemanticDecision(str, Enum):
    """Semantic match decision.

    The three decisions are mutually exclusive:

    * `MATCH` — the candidate is very likely the target product
    * `NO_MATCH` — the candidate is definitely not the target product
    * `UNCERTAIN` — insufficient evidence to determine match or no-match
    """

    MATCH = "MATCH"
    NO_MATCH = "NO_MATCH"
    UNCERTAIN = "UNCERTAIN"


class ConfidenceLevel(str, Enum):
    """Confidence in the semantic match decision."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# Semantic decision vocabulary matches EvidenceDecision where applicable:
#
# SemanticDecision   |  EvidenceDecision
# -------------------|------------------
# MATCH              |  ACCEPTED (high confidence)
# NO_MATCH           |  REJECTED (high confidence)
# UNCERTAIN          |  UNDECIDED (low confidence)
#
# However, they are separate vocabularies because:
# * Semantic match may be used for cases deterministic 3C cannot resolve
# * A future semantic MATCH may not immediately become deterministic ACCEPTED
# * The semantic evaluator may operate at a different confidence threshold

# ---------------------------------------------------------------------------
# Output contract for semantic matchers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SemanticMatchResponse:
    """Structured response from a semantic match model.

    This is the contract that semantic matchers must produce. The evaluator
    validates responses against this schema.
    """

    decision: SemanticDecision
    confidence: ConfidenceLevel
    matched_attributes: tuple[str, ...]
    conflicting_attributes: tuple[str, ...]
    missing_critical_attributes: tuple[str, ...]
    reason_code: str

    def __post_init__(self) -> None:
        """Validate the response structure."""
        if not isinstance(self.decision, SemanticDecision):
            raise TypeError(
                f"decision must be SemanticDecision, got {type(self.decision).__name__}"
            )
        if not isinstance(self.confidence, ConfidenceLevel):
            raise TypeError(
                f"confidence must be ConfidenceLevel, got {type(self.confidence).__name__}"
            )
        if not isinstance(self.matched_attributes, tuple):
            raise TypeError(
                f"matched_attributes must be tuple, got {type(self.matched_attributes).__name__}"
            )
        if not isinstance(self.conflicting_attributes, tuple):
            raise TypeError(
                f"conflicting_attributes must be tuple, got {type(self.conflicting_attributes).__name__}"
            )
        if not isinstance(self.missing_critical_attributes, tuple):
            raise TypeError(
                f"missing_critical_attributes must be tuple, got {type(self.missing_critical_attributes).__name__}"
            )
        if not isinstance(self.reason_code, str):
            raise TypeError(
                f"reason_code must be str, got {type(self.reason_code).__name__}"
            )
        if not self.reason_code:
            raise ValueError("reason_code must be non-empty")


# ---------------------------------------------------------------------------
# Case class vocabulary
# ---------------------------------------------------------------------------


class SemanticCaseClass(str, Enum):
    """Categories of semantic match cases."""

    TITLE_EXACT_MPN = "title_exact_mpn"
    """Exact MPN in title, product description matches."""

    BASE_MPN_ONLY = "base_mpn_only"
    """Base MPN without suffix."""

    DIFFERENT_CAPACITY = "different_capacity"
    """Same family, different capacity."""

    DIFFERENT_FORM_FACTOR = "different_form_factor"
    """Same family, different form factor."""

    DIFFERENT_INTERFACE = "different_interface"
    """Same family, different interface."""

    SUFFIX_MISSING = "suffix_missing"
    """Suffix/revision not established."""

    OEM_REVISION_VARIANT = "oem_revision_variant"
    """OEM/revision variant ambiguity."""

    ACCESSORY_TRAP = "accessory_trap"
    """Accessory/tray/caddy wording."""

    COMPATIBLE_WITH_TRAP = "compatible_with_trap"
    """Compatible-with wording."""

    REPLACEMENT_TRAP = "replacement_trap"
    """Replacement/caddy wording."""

    MULTIPLY_PACK_TRAP = "multipack_trap"
    """Single vs multipack."""

    BRAND_FAMILY_ONLY = "brand_family_only"
    """Same brand/family only."""

    SPECIFICATION_RICH = "specification_rich"
    """No usable MPN, rich specs."""

    DRIVE_VS_ENCLOSE = "drive_vs_enclosure"
    """Drive vs enclosure/accessory."""

    def description(self) -> str:
        """Return a human-readable description of this case class."""
        descriptions = {
            SemanticCaseClass.TITLE_EXACT_MPN: "Exact MPN in title, product description matches",
            SemanticCaseClass.BASE_MPN_ONLY: "Base MPN without suffix",
            SemanticCaseClass.DIFFERENT_CAPACITY: "Same family, different capacity",
            SemanticCaseClass.DIFFERENT_FORM_FACTOR: "Same family, different form factor",
            SemanticCaseClass.DIFFERENT_INTERFACE: "Same family, different interface",
            SemanticCaseClass.SUFFIX_MISSING: "Suffix/revision not established",
            SemanticCaseClass.OEM_REVISION_VARIANT: "OEM/revision variant ambiguity",
            SemanticCaseClass.ACCESSORY_TRAP: "Accessory/tray/caddy wording",
            SemanticCaseClass.COMPATIBLE_WITH_TRAP: "Compatible-with wording",
            SemanticCaseClass.REPLACEMENT_TRAP: "Replacement/caddy wording",
            SemanticCaseClass.MULTIPLY_PACK_TRAP: "Single vs multipack",
            SemanticCaseClass.BRAND_FAMILY_ONLY: "Same brand/family only",
            SemanticCaseClass.SPECIFICATION_RICH: "No usable MPN, rich specs",
            SemanticCaseClass.DRIVE_VS_ENCLOSE: "Drive vs enclosure/accessory",
        }
        return descriptions[self]
