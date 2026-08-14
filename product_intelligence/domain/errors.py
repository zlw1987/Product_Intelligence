"""Domain-level error types."""

from __future__ import annotations


class DomainValidationError(ValueError):
    """Raised when a domain contract is constructed with invalid input.

    This covers contract-level validation only (presence, type, obviously
    malformed values). It is not a product-resolution or research failure:
    those outcomes are represented by status/confidence values, not exceptions,
    because "unknown" is a legitimate research result.
    """
