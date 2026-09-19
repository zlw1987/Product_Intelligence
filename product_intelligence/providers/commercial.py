"""Provider-neutral commercial-source boundary (PRODUCT-INTEL.4D-B).

This module defines the generic contracts for structured commercial
observations from a structured commercial provider. It is **not** search
— a commercial lookup takes an exact MPN and returns structured
pricing/availability observations, not discovered URLs.

The boundary is:
* provider-neutral
* stdlib-only
* Django-free
* persistence-free
* research-free
* network-free
* credential-free
* configuration-free

Source-shaped payloads are interpreted in adapter modules. The contracts
here carry only the normalized commercial fields needed downstream.

What this boundary is *not*
---------------------------

**It is not SearchProvider.** A ``SearchProvider`` takes a free-text query
and returns discovered candidate URLs. A ``CommercialSourceProvider`` takes
an exact MPN and returns structured commercial observations with prices,
currencies, and availability. Those are different semantics and must not
be collapsed.

**It is not authority.** A commercial observation is supplemental evidence.
It does not enter frozen 4A Machine Price, frozen Reviewed Price,
deterministic identity authority, semantic authority, or comparable scoring.

**It is not evidence storage.** Nothing here is persisted. The payload
schema for persistence is owned by the codec layer.

**It does not carry business-policy conclusions.** Brand-new status is a
customer/business-policy determination that applies only after frozen 2A
has successfully identity-bound the vendor observation to the requested
product. The provider observes; business policy applies later.

Commercial observation
----------------------

One commercial observation represents pricing/availability evidence from
one named commercial source for one explicit part number. The observation
is provider-neutral: no source-specific nested dict reaches consumers.

``CommercialAvailability`` is a narrow controlled vocabulary:
IN_STOCK, OUT_OF_STOCK, UNKNOWN.

``CommercialPriceBasis`` records which price was used, so a downstream
consumer can distinguish them.

Monetary values
---------------

All monetary values use ``Decimal`` (exact), never binary float.
Prices must be finite and nonnegative.

Sensitive data
--------------

Session identifiers, account identifiers, system identifiers, credentials,
and other transport metadata MUST NOT appear in any commercial observation.
The adapter owns an allowlist of approved fields; unknown upstream fields
are ignored by default.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Protocol


# ---------------------------------------------------------------------------
# Controlled vocabularies
# ---------------------------------------------------------------------------


class CommercialAvailability(str, Enum):
    """Normalized commercial availability state.

    Only three values are permitted for 4D-B:
    IN_STOCK — source indicates stock is available
    OUT_OF_STOCK — source indicates stock is not available
    UNKNOWN — insufficient or contradictory evidence
    """

    IN_STOCK = "IN_STOCK"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    UNKNOWN = "UNKNOWN"


class CommercialPriceBasis(str, Enum):
    """Which price was used as the commercial observation value."""

    CUSTOMER_PRICE = "CUSTOMER_PRICE"
    RETAIL_PRICE_FALLBACK = "RETAIL_PRICE_FALLBACK"
    LIST_PRICE = "LIST_PRICE"


class CommercialNoteKind(str, Enum):
    """Bounded, approved commercial note meanings.

    4D-B recognizes only explicitly approved bounded meanings.
    Free-form note text from the source is dropped unless it maps
    to an approved kind.
    """

    NO_RETURNS = "NO_RETURNS"


class LookupStatus(str, Enum):
    """Overall vendor-commercial lookup outcome."""

    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class SourceOutcome(str, Enum):
    """Per-source outcome within a lookup response."""

    USABLE = "USABLE"
    NOT_FOUND = "NOT_FOUND"
    MALFORMED_SECTION = "MALFORMED_SECTION"
    MISSING_EXPLICIT_MPN = "MISSING_EXPLICIT_MPN"
    MPN_MISMATCH = "MPN_MISMATCH"


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CommercialLookupQuery:
    """One exact-MPN commercial lookup request.

    ``mpn`` is the canonical manufacturer part number as it appears in the
    research request. Surrounding whitespace is removed; interior is untouched.
    """

    mpn: str

    def __post_init__(self) -> None:
        if not isinstance(self.mpn, str):
            raise TypeError(
                f"mpn must be a string, got {type(self.mpn).__name__}"
            )
        object.__setattr__(self, "mpn", self.mpn.strip())
        if not self.mpn:
            raise ValueError(
                "CommercialLookupQuery requires a non-empty MPN; "
                "there is nothing to look up"
            )


# ---------------------------------------------------------------------------
# Single-source observation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CommercialSourceCandidate:
    """One provider-neutral commercial observation from one named source.

    This carries only the normalized fields needed downstream. No raw
    vendor dict, no session/account metadata, no source-specific nested
    structure reaches consumers.

    All monetary values use ``Decimal`` (exact), never binary float.
    Price must be finite and nonnegative.

    Brand-new business policy is NOT carried here. It is a
    customer/business-policy conclusion that applies only after frozen 2A
    has successfully identity-bound the observation to the requested
    product. See SupplementSourceObservation for the bound result.

    Attributes:
        source_name: Human-readable source identifier.
        explicit_candidate_mpn: The MPN the source published for this
            product. Used for frozen 2A identity binding.
        price_amount: The commercial price as a Decimal (finite, nonnegative).
        currency_code: ISO 4217 currency code.
        availability: Normalized availability state.
        quantity: Optional supplemental quantity integer (nonnegative).
        price_basis: Which price basis was used.
        note_kind: Optional bounded approved note meaning.
    """

    source_name: str
    explicit_candidate_mpn: str
    price_amount: Decimal
    currency_code: str
    availability: CommercialAvailability
    price_basis: CommercialPriceBasis
    note_kind: CommercialNoteKind | None = None
    quantity: int | None = None

    def __post_init__(self) -> None:
        # source_name
        if not isinstance(self.source_name, str) or not self.source_name.strip():
            raise ValueError("source_name must be a non-empty string")
        object.__setattr__(self, "source_name", self.source_name.strip())

        # explicit_candidate_mpn
        if not isinstance(self.explicit_candidate_mpn, str):
            raise TypeError(
                f"explicit_candidate_mpn must be a string, got "
                f"{type(self.explicit_candidate_mpn).__name__}"
            )
        mpn = self.explicit_candidate_mpn.strip()
        if not mpn:
            raise ValueError(
                "explicit_candidate_mpn must be non-empty; "
                "a commercial observation without a vendor MPN is unboundable"
            )
        object.__setattr__(self, "explicit_candidate_mpn", mpn)

        # price_amount — Decimal only, finite, nonnegative
        if not isinstance(self.price_amount, Decimal):
            raise TypeError(
                f"price_amount must be a Decimal, got "
                f"{type(self.price_amount).__name__}"
            )
        if not self.price_amount.is_finite():
            raise ValueError(
                "price_amount must be finite; NaN/Infinity rejected"
            )
        if self.price_amount < 0:
            raise ValueError("price_amount must not be negative")

        # currency_code
        if not isinstance(self.currency_code, str):
            raise TypeError(
                f"currency_code must be a string, got "
                f"{type(self.currency_code).__name__}"
            )
        currency = self.currency_code.strip().upper()
        if not currency:
            raise ValueError("currency_code must be non-empty")
        object.__setattr__(self, "currency_code", currency)

        # availability
        if not isinstance(self.availability, CommercialAvailability):
            raise TypeError(
                f"availability must be a CommercialAvailability, got "
                f"{type(self.availability).__name__}"
            )

        # price_basis
        if not isinstance(self.price_basis, CommercialPriceBasis):
            raise TypeError(
                f"price_basis must be a CommercialPriceBasis, got "
                f"{type(self.price_basis).__name__}"
            )

        # note_kind
        if self.note_kind is not None and not isinstance(
            self.note_kind, CommercialNoteKind
        ):
            raise TypeError(
                f"note_kind must be a CommercialNoteKind or None, got "
                f"{type(self.note_kind).__name__}"
            )

        # quantity — int only, bool rejected, nonnegative
        if self.quantity is not None:
            if type(self.quantity) is not int:
                raise TypeError(
                    f"quantity must be an int or None, got "
                    f"{type(self.quantity).__name__}"
                )
            if self.quantity < 0:
                raise ValueError("quantity must not be negative")


# ---------------------------------------------------------------------------
# Source-level issue (for unusable sources)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CommercialSourceIssue:
    """A bounded record of why one source section did not produce a candidate.

    The provider layer does not carry arbitrary detail text. The ``outcome``
    enum provides the bounded classification. Any additional detail is
    added at the orchestration layer after frozen-2A binding.

    Attributes:
        source_name: The source that failed or was not found.
        outcome: The bounded outcome classification.
    """

    source_name: str
    outcome: SourceOutcome

    def __post_init__(self) -> None:
        if not isinstance(self.source_name, str) or not self.source_name.strip():
            raise ValueError("source_name must be a non-empty string")
        object.__setattr__(self, "source_name", self.source_name.strip())

        if not isinstance(self.outcome, SourceOutcome):
            raise TypeError(
                f"outcome must be a SourceOutcome, got "
                f"{type(self.outcome).__name__}"
            )


# ---------------------------------------------------------------------------
# Whole-response result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CommercialSourceResponse:
    """The complete result of one commercial-source lookup.

    Attributes:
        status: Overall lookup status (SUCCESS, PARTIAL, FAILED).
        retrieved_at: When the response was obtained (timezone-aware).
        candidates: Identity-bound usable commercial observations.
        issues: Per-source outcomes for non-usable sources.
    """

    status: LookupStatus
    retrieved_at: datetime | None
    candidates: tuple[CommercialSourceCandidate, ...] = ()
    issues: tuple[CommercialSourceIssue, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, LookupStatus):
            raise TypeError(
                f"status must be a LookupStatus, got "
                f"{type(self.status).__name__}"
            )

        if self.retrieved_at is not None:
            if not isinstance(self.retrieved_at, datetime):
                raise TypeError(
                    f"retrieved_at must be a datetime or None, got "
                    f"{type(self.retrieved_at).__name__}"
                )
            if (
                self.retrieved_at.tzinfo is None
                or self.retrieved_at.utcoffset() is None
            ):
                raise ValueError(
                    "retrieved_at must be timezone-aware when present"
                )

        if isinstance(self.candidates, (str, bytes)):
            raise TypeError("candidates must be a tuple of CommercialSourceCandidate")
        candidates = tuple(self.candidates)
        for i, c in enumerate(candidates):
            if not isinstance(c, CommercialSourceCandidate):
                raise TypeError(
                    f"candidates[{i}] must be a CommercialSourceCandidate, got "
                    f"{type(c).__name__}"
                )
        object.__setattr__(self, "candidates", candidates)

        if isinstance(self.issues, (str, bytes)):
            raise TypeError("issues must be a tuple of CommercialSourceIssue")
        issues = tuple(self.issues)
        for i, issue in enumerate(issues):
            if not isinstance(issue, CommercialSourceIssue):
                raise TypeError(
                    f"issues[{i}] must be a CommercialSourceIssue, got "
                    f"{type(issue).__name__}"
                )
        object.__setattr__(self, "issues", issues)


# ---------------------------------------------------------------------------
# Provider Protocol
# ---------------------------------------------------------------------------


class CommercialSourceProvider(Protocol):
    """The boundary for one commercial-source lookup.

    One synchronous method. A ``Protocol`` rather than a base class so an
    adapter conforms by shape and inherits nothing.

    An implementation is expected to:
    * accept a ``CommercialLookupQuery`` (exact MPN)
    * return a ``CommercialSourceResponse`` with normalized observations
    * keep vendor concerns inside the adapter
    * never expose raw vendor dicts to consumers
    * never import research/persistence/web layers
    """

    def lookup(self, query: CommercialLookupQuery) -> CommercialSourceResponse:
        """Execute one exact-MPN commercial lookup and return observations."""
        ...
