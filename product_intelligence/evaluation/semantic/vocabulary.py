"""Semantic match decision vocabulary (PRODUCT-INTEL.SEMANTIC).

This module defines the decision vocabulary and validation logic for
semantic match qualification. It is used by offline evaluators to validate
model responses and compute metrics.

Single source of truth (FU3A2)
------------------------------
``SemanticDecision``, ``ConfidenceLevel`` and ``SemanticMatchResponse`` are
NOT defined here. They are re-exported from the neutral production contract
``product_intelligence.semantic.contract`` so that production and evaluation
share one implementation object rather than two identical copies.

The names below are the *same objects* as the contract's; ``is`` comparison
holds. Only evaluation-specific vocabulary (``SemanticCaseClass``) is
defined locally.

No live model integration is required for this phase.
"""

from __future__ import annotations

from enum import Enum

# Canonical contract objects - re-exported, never re-implemented.
from product_intelligence.semantic.contract import (
    ConfidenceLevel,
    SemanticDecision,
    SemanticMatchResponse,
)


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


__all__ = [
    "SemanticDecision",
    "ConfidenceLevel",
    "SemanticMatchResponse",
    "SemanticCaseClass",
]
