"""Research core.

This is where the caller-independent research engine lives: product
resolution, price intelligence, comparable-product research, and evidence
handling. The engine consumes `product_intelligence.domain.ResearchRequest` and
knows nothing about how that request arrived.

The layer stays free of persistence, transports, vendors, and benchmark data:
no Django, no HTTP, no provider, and no import of
`product_intelligence.evaluation`. The run lifecycle is *not* here — it is a
persisted record and lives in `product_intelligence.runs` (AD-025).

Status: PRODUCT-INTEL.2A implemented the deterministic part-number identity
comparison in `identity`, and 2A-FU1 narrowed its normalization so that
separator *position* is preserved rather than deleted. It compares two part
numbers it is handed; it finds no candidates, resolves no product, and reads no
description. Listing work is 3A-3C, pricing is 4A-4B, and comparables are
7A-7C — none of it exists.
"""

from product_intelligence.research.identity import (
    ASCII_WHITESPACE,
    CANONICAL_SEPARATOR,
    PRESERVED_SEPARATORS,
    STRUCTURAL_CHARACTERS,
    PartNumberMatchAssessment,
    compare_part_numbers,
    compare_request_to_candidate,
    normalize_part_number,
)

__all__ = [
    "ASCII_WHITESPACE",
    "CANONICAL_SEPARATOR",
    "PRESERVED_SEPARATORS",
    "STRUCTURAL_CHARACTERS",
    "PartNumberMatchAssessment",
    "compare_part_numbers",
    "compare_request_to_candidate",
    "normalize_part_number",
]
