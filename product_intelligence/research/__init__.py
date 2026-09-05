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

PRODUCT-INTEL.4A added `aggregation`: `aggregate_listing_prices`, which
takes a ``ResearchRequest`` and pre-built ``ListingIdentityAssessment``
values, classifies each as price-eligible or excluded, groups eligible
prices by (currency, known-condition), and computes deterministic
statistics (count/low/median/high/market-range) per group. No FX,
no outlier removal, no availability policy, no unit price. UNKNOWN
condition is excluded. Multiple non-comparable buckets produce
AMBIGUOUS. The result retains every input assessment.

PRODUCT-INTEL.4B added `price_result_codec`: versioned encode/decode of
``PriceAggregationResult`` as opaque JSON for persistence in
``PriceIntelligenceSnapshot``. Strict schema, Decimal preserved as strings,
fail-closed decode wrapping constructor failures as ``PriceResultCodecError``.

PRODUCT-INTEL.6A added `specifications`: the Product Specification Framework —
deterministic, caller-independent, Django-free specification resolution. Defines
SpecificationDefinition, SpecificationValue, SpecificationObservation,
NormalizedSpecificationObservation, SpecificationResolution, CategorySchema,
ProductSpecificationSet, and resolve_specification(). No extraction, no LLM call,
no persistence, no network, no category-specific fields.

PRODUCT-INTEL.6B added `enterprise_ssd`: the first category-specific schema
using the frozen 6A framework. 12-field Enterprise SSD schema v1 with
strict deterministic normalization. No extraction, no resolution, no
authority inference, no manufacturer-specific rules.

PRODUCT-INTEL.6C added `enterprise_ssd_extraction`: deterministic structured
extraction of Enterprise SSD specification observations from document text.
Supports embedded JavaScript JSON product data arrays (JSON.parse patterns).
No arbitrary text mining, no LLM, no JavaScript execution. Composite values
preserved. Only labels demonstrated by real manufacturer fixtures are mapped.
6C execution (`execution/specification_evidence.py`) composes extraction
with PageFetcher acquisition, 6B normalization, and 6A resolution.
"""

from product_intelligence.research.aggregation import (
    PriceAggregateBucket,
    PriceAggregationExclusion,
    PriceAggregationExclusionReason,
    PriceAggregationResult,
    aggregate_listing_prices,
)
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
from product_intelligence.research.price_result_codec import (
    PRICE_RESULT_SCHEMA_VERSION,
    PriceResultCodecError,
    decode_price_aggregation_result,
    encode_price_aggregation_result,
)
from product_intelligence.research.enterprise_ssd import (
    ENTERPRISE_SSD_SCHEMA,
    ENTERPRISE_SSD_SCHEMA_ID,
    ENTERPRISE_SSD_SCHEMA_VERSION,
    normalize_enterprise_ssd_observation,
    normalize_enterprise_ssd_observations,
)
from product_intelligence.research.enterprise_ssd_extraction import (
    extract_enterprise_ssd_specification_observations,
)
from product_intelligence.research.specifications import (
    CategorySchema,
    NormalizedSpecificationObservation,
    ProductSpecificationSet,
    ResolutionState,
    SourceAuthority,
    SpecificationDefinition,
    SpecificationObservation,
    SpecificationResolution,
    SpecificationValue,
    SpecificationValueKind,
    resolve_specification,
)

__all__ = [
    "ASCII_WHITESPACE",
    "CANONICAL_SEPARATOR",
    "ENTERPRISE_SSD_SCHEMA",
    "ENTERPRISE_SSD_SCHEMA_ID",
    "ENTERPRISE_SSD_SCHEMA_VERSION",
    "PRESERVED_SEPARATORS",
    "PRICE_RESULT_SCHEMA_VERSION",
    "STRUCTURAL_CHARACTERS",
    "CategorySchema",
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
    "NormalizedSpecificationObservation",
    "PartNumberMatchAssessment",
    "PriceAggregateBucket",
    "PriceAggregationExclusion",
    "PriceAggregationExclusionReason",
    "PriceAggregationResult",
    "PriceResultCodecError",
    "ProductSpecificationSet",
    "ResolutionState",
    "SourceAuthority",
    "SpecificationDefinition",
    "SpecificationObservation",
    "SpecificationResolution",
    "SpecificationValue",
    "SpecificationValueKind",
    "aggregate_listing_prices",
    "assess_listing_identity",
    "assess_listing_identities",
    "compare_part_numbers",
    "compare_request_to_candidate",
    "decode_price_aggregation_result",
    "encode_price_aggregation_result",
    "extract_listing_observations",
    "extract_enterprise_ssd_specification_observations",
    "normalize_enterprise_ssd_observation",
    "normalize_enterprise_ssd_observations",
    "normalize_listing_observation",
    "normalize_listing_observations",
    "normalize_part_number",
    "resolve_specification",
]
