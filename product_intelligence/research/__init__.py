"""Research core.

This is where the caller-independent research engine lives: product
resolution, price intelligence, comparable-product research, and evidence
handling. The engine consumes `product_intelligence.domain.ResearchRequest` and
knows nothing about how that request arrived.

The layer stays free of persistence, transports, vendors, and benchmark data:
no Django, no HTTP, no provider, and no import of
`product_intelligence.evaluation`. The run lifecycle is *not* here — it is a
persisted record and lives in `product_intelligence.runs` (AD-025).

That rule is why extraction takes a document *string* rather than a
`FetchedPage`: the fetch boundary lives in `providers/`, and the two halves of
the 3A slice meet in whatever code holds both rather than by one importing the
other. The core can therefore be exercised with a string literal, and it opens
no socket to do it.

Status: PRODUCT-INTEL.2A implemented the deterministic part-number identity
comparison in `identity`, and 2A-FU1 narrowed its normalization so that
separator *position* is preserved rather than deleted. It compares two part
numbers it is handed; it finds no candidates, resolves no product, and reads no
description.

PRODUCT-INTEL.3A added `listings` and `extraction`: the raw
`ListingObservation` contract and the deterministic extractor that reads
`schema.org` JSON-LD and flat product meta tags out of a document. It observes
text and converts nothing — no `Decimal`, no currency, no vocabulary, no
arithmetic. Extraction never calls the 2A comparator: an extractor that decided
identity would be judging its own evidence.

PRODUCT-INTEL.3B added `normalization`: `normalize_listing_observation`, which
turns a raw `ListingObservation`'s commercial attributes — price, currency,
availability, condition, seller — into a deterministic, comparable
`NormalizedListingObservation`, or abstains with a recorded
`NormalizationIssue` when the raw text cannot be converted without guessing.
Money becomes `Decimal` only here, never in extraction. No currency is
converted, no listing is accepted or rejected, and no aggregate is computed —
those are 3C and 4A.

PRODUCT-INTEL.3C added `matching`: `assess_listing_identity`, which decides
whether a normalised listing belongs to the requested product. It uses the
existing 2A comparator on explicit MPN fields only, after narrow ``mpn:``
wrapper cleanup. SKU and title text alone never produce ACCEPTED. PARTIAL
matches are explicitly rejected. No LLM call, no persistence, no orchestration.

Pricing is 4A-4B, and comparables are 7A-7C — neither exists.
"""

from product_intelligence.research.extraction import extract_listing_observations
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
from product_intelligence.research.listings import (
    ExtractionMethod,
    ListingObservation,
)
from product_intelligence.research.matching import (
    EvidenceSource,
    IdentityRejectionReason,
    ListingIdentityAssessment,
    assess_listing_identity,
    assess_listing_identities,
)
from product_intelligence.research.normalization import (
    NormalizationIssue,
    NormalizationIssueCode,
    NormalizedAvailability,
    NormalizedCondition,
    NormalizedListingObservation,
    normalize_listing_observation,
    normalize_listing_observations,
)

__all__ = [
    "ASCII_WHITESPACE",
    "CANONICAL_SEPARATOR",
    "PRESERVED_SEPARATORS",
    "STRUCTURAL_CHARACTERS",
    "EvidenceSource",
    "ExtractionMethod",
    "IdentityRejectionReason",
    "ListingIdentityAssessment",
    "ListingObservation",
    "NormalizationIssue",
    "NormalizationIssueCode",
    "NormalizedAvailability",
    "NormalizedCondition",
    "NormalizedListingObservation",
    "PartNumberMatchAssessment",
    "assess_listing_identity",
    "assess_listing_identities",
    "compare_part_numbers",
    "compare_request_to_candidate",
    "extract_listing_observations",
    "normalize_listing_observation",
    "normalize_listing_observations",
    "normalize_part_number",
]
