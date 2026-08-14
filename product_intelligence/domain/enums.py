"""Controlled vocabularies shared by the Product Intelligence domain.

These enums fix the *vocabulary* used across the system. The logic that
assigns these values (matching, verification, aggregation, run orchestration)
is not implemented in PRODUCT-INTEL.0A.

Design rules encoded here:

* Uncertainty is representable. UNKNOWN / UNVERIFIED / AMBIGUOUS / CONFLICT
  are first-class outcomes, never silently upgraded to a confident answer.
* Exact identity is distinguished from semantic similarity.
* No value names an external provider, transport, or calling system.
"""

from __future__ import annotations

from enum import Enum


class IdentityMatchType(str, Enum):
    """How strongly an observed item is tied to the requested product.

    Semantic similarity is deliberately *not* equivalent to exact identity:
    part numbers differing by one character may be different products.
    """

    EXACT = "EXACT"
    """Part number matched character-for-character."""

    NORMALIZED_EXACT = "NORMALIZED_EXACT"
    """Part numbers matched after deterministic normalization only."""

    PARTIAL = "PARTIAL"
    """Part number overlapped but did not match in full."""

    DESCRIPTION_ONLY = "DESCRIPTION_ONLY"
    """Matched on description/semantics only, with no part-number evidence."""

    CONFLICT = "CONFLICT"
    """Evidence points at incompatible identities."""

    UNKNOWN = "UNKNOWN"
    """Identity has not been established."""


class ConfidenceLevel(str, Enum):
    """Coarse confidence band.

    Coarse on purpose: a numeric score implies a precision the system has not
    earned. A finer-grained score may be introduced later if a phase shows a
    concrete need for it.
    """

    UNKNOWN = "UNKNOWN"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class VerificationStatus(str, Enum):
    """Whether a claim is supported by traceable evidence."""

    VERIFIED = "VERIFIED"
    """Supported by accepted, attributable evidence."""

    UNVERIFIED = "UNVERIFIED"
    """Asserted but not backed by accepted evidence."""

    AMBIGUOUS = "AMBIGUOUS"
    """Evidence supports more than one reading."""

    CONFLICT = "CONFLICT"
    """Evidence is mutually contradictory."""

    UNKNOWN = "UNKNOWN"
    """Nothing usable was established."""


class EvidenceDecision(str, Enum):
    """Whether a piece of evidence was accepted into a conclusion."""

    UNDECIDED = "UNDECIDED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class ResearchRunState(str, Enum):
    """Lifecycle vocabulary for a research attempt.

    The vocabulary is fixed here so documentation, reports, and later code
    agree on the terms. The run entity, its persistence, and its state
    transitions are PRODUCT-INTEL.1A work and do not exist yet.
    """

    CREATED = "CREATED"
    RUNNING = "RUNNING"
    PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
