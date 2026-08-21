"""Versioned codec for ``PriceAggregationResult`` (PRODUCT-INTEL.4B).

Encodes a ``PriceAggregationResult`` into a versioned JSON-serialisable
``dict`` and decodes the persisted payload back into the canonical contract
object.

This module is **pure research-layer serialisation**. It may import stdlib,
domain contracts/enums, and existing research contracts. It must not import
Django, ``runs``, ``web``, ``execution``, ``providers``, ``evaluation``,
network libraries, or filesystem libraries.

No ``dataclasses.asdict``, no pickle, no generic object framework, no float.

The codec lives in ``research/`` because it transforms research-layer
contracts to and from JSON. It is serialisation discipline, not persistence
logic. The ``runs/`` layer stores the JSON; this layer interprets it.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.errors import DomainValidationError
from product_intelligence.domain.enums import (
    ConfidenceLevel,
    EvidenceDecision,
    IdentityMatchType,
    VerificationStatus,
)
from product_intelligence.research.aggregation import (
    PriceAggregateBucket,
    PriceAggregationExclusion,
    PriceAggregationExclusionReason,
    PriceAggregationResult,
)
from product_intelligence.research.listings import (
    ExtractionMethod,
    ListingObservation,
)
from product_intelligence.research.matching import (
    EvidenceSource,
    IdentityRejectionReason,
    ListingIdentityAssessment,
)
from product_intelligence.research.normalization import (
    NormalizationIssue,
    NormalizationIssueCode,
    NormalizedAvailability,
    NormalizedCondition,
    NormalizedListingObservation,
)

# ---------------------------------------------------------------------------
# Public constants and exceptions
# ---------------------------------------------------------------------------

PRICE_RESULT_SCHEMA_VERSION = 1
"""Current (and only supported) V1 schema version."""


class PriceResultCodecError(ValueError):
    """Raised when a persisted payload cannot be decoded.

    Covers: unsupported schema version, malformed payload, unknown enums,
    invalid Decimal values, out-of-range assessment indexes, and any other
    structural failure during decode.

    Never includes raw payload content in the message if it may contain
    external text (titles, seller names, raw MPNs from untrusted pages).
    """

# ---------------------------------------------------------------------------
# Enum registries — exact value → enum member
# ---------------------------------------------------------------------------

# These are the exhaustive sets of enum values the codec accepts for decode.
# Unknown values raise PriceResultCodecError — no best-effort migration.

_STRING_ENUMS: dict[type, dict[str, object]] = {
    ConfidenceLevel: {m.value: m for m in ConfidenceLevel},
    EvidenceDecision: {m.value: m for m in EvidenceDecision},
    IdentityMatchType: {m.value: m for m in IdentityMatchType},
    VerificationStatus: {m.value: m for m in VerificationStatus},
    EvidenceSource: {m.value: m for m in EvidenceSource},
    IdentityRejectionReason: {m.value: m for m in IdentityRejectionReason},
    ExtractionMethod: {m.value: m for m in ExtractionMethod},
    NormalizationIssueCode: {m.value: m for m in NormalizationIssueCode},
    NormalizedAvailability: {m.value: m for m in NormalizedAvailability},
    NormalizedCondition: {m.value: m for m in NormalizedCondition},
    PriceAggregationExclusionReason: {
        m.value: m for m in PriceAggregationExclusionReason
    },
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _enc_enum(value: object) -> str:
    """Encode an enum member as its .value string."""
    return value.value  # type: ignore[attr-defined]


def _dec_enum(
    cls: type, raw: object, path: str
) -> object:
    """Decode a string into an enum member, or raise."""
    if not isinstance(raw, str):
        raise PriceResultCodecError(
            f"{path}: expected string for {cls.__name__}, got {type(raw).__name__}"
        )
    mapping = _STRING_ENUMS[cls]
    if raw not in mapping:
        raise PriceResultCodecError(
            f"{path}: unknown {cls.__name__} value {raw!r}"
        )
    return mapping[raw]


def _dec_decimal(raw: object, path: str) -> Decimal:
    """Decode a Decimal from a string, or raise.

    Rejects float, int, NaN, Infinity, -Infinity, malformed text.
    """
    if isinstance(raw, bool):
        raise PriceResultCodecError(
            f"{path}: expected Decimal string, got bool"
        )
    if isinstance(raw, (int, float)):
        raise PriceResultCodecError(
            f"{path}: Decimal must be stored as a string, got "
            f"{type(raw).__name__}; float/int values lose precision"
        )
    if not isinstance(raw, str):
        raise PriceResultCodecError(
            f"{path}: expected Decimal string, got {type(raw).__name__}"
        )
    try:
        value = Decimal(raw)
    except InvalidOperation:
        raise PriceResultCodecError(
            f"{path}: malformed Decimal string"
        ) from None

    if not value.is_finite():
        raise PriceResultCodecError(
            f"{path}: Decimal must be finite; got {raw!r}"
        )

    return value


def _dec_optional_decimal(raw: object | None, path: str) -> Decimal | None:
    if raw is None:
        return None
    return _dec_decimal(raw, path)


def _dec_int(raw: object, path: str) -> int:
    """Decode an integer, rejecting bool."""
    if isinstance(raw, bool):
        raise PriceResultCodecError(
            f"{path}: expected int, got bool"
        )
    if not isinstance(raw, int):
        raise PriceResultCodecError(
            f"{path}: expected int, got {type(raw).__name__}"
        )
    return raw


def _dec_str(raw: object, path: str) -> str:
    if not isinstance(raw, str):
        raise PriceResultCodecError(
            f"{path}: expected string, got {type(raw).__name__}"
        )
    return raw


def _dec_optional_str(raw: object | None, path: str) -> str | None:
    if raw is None:
        return None
    return _dec_str(raw, path)


def _dec_mapping(raw: object, path: str) -> dict[str, object]:
    """Require a dict/mapping, raise on anything else."""
    if not isinstance(raw, dict):
        raise PriceResultCodecError(
            f"{path}: expected mapping, got {type(raw).__name__}"
        )
    return raw


def _dec_list(raw: object, path: str) -> list[object]:
    """Require a list, raise on anything else."""
    if not isinstance(raw, list):
        raise PriceResultCodecError(
            f"{path}: expected list, got {type(raw).__name__}"
        )
    return raw


def _dec_required_key(
    data: dict[str, object], key: str, path: str
) -> object:
    """Get a required key, raise if missing."""
    if key not in data:
        raise PriceResultCodecError(
            f"{path}: missing required key {key!r}"
        )
    return data[key]


def _check_no_extra_keys(
    data: dict[str, object], allowed: set[str], path: str
) -> None:
    """Reject unknown extra keys."""
    extra = set(data.keys()) - allowed
    if extra:
        raise PriceResultCodecError(
            f"{path}: unexpected keys {sorted(extra)}"
        )


def _validate_assessment_index(
    idx: object, assessments_len: int, path: str
) -> int:
    """Validate an assessment index reference."""
    index = _dec_int(idx, path)
    if index < 0 or index >= assessments_len:
        raise PriceResultCodecError(
            f"{path}: assessment index {index} out of range "
            f"[0, {assessments_len - 1}]"
        )
    return index


# ---------------------------------------------------------------------------
# Encode — V1
# ---------------------------------------------------------------------------

# These functions each return a plain dict/list/str/int/None that is directly
# JSON-serialisable. No Decimal, no Enum, no dataclass objects.


def _enc_request(obj: ResearchRequest) -> dict[str, str]:
    return {
        "manufacturer_part_number": obj.manufacturer_part_number,
        "description": obj.description,
    }


def _enc_extraction_method(method: ExtractionMethod) -> str:
    return _enc_enum(method)


def _enc_listing_observation(obs: ListingObservation) -> dict[str, object]:
    return {
        "source_url": obs.source_url,
        "extraction_method": _enc_extraction_method(obs.extraction_method),
        "product_title": obs.product_title,
        "manufacturer_part_number_text": obs.manufacturer_part_number_text,
        "sku_text": obs.sku_text,
        "brand_text": obs.brand_text,
        "price_text": obs.price_text,
        "currency_text": obs.currency_text,
        "availability_text": obs.availability_text,
        "condition_text": obs.condition_text,
        "seller_text": obs.seller_text,
        "offer_url_text": obs.offer_url_text,
        "raw_reference": obs.raw_reference,
    }


def _enc_normalization_issue(issue: NormalizationIssue) -> dict[str, object]:
    return {
        "field": issue.field,
        "code": _enc_enum(issue.code),
        "raw_value": issue.raw_value,
        "reason": issue.reason,
    }


def _enc_normalized_listing(
    norm: NormalizedListingObservation,
) -> dict[str, object]:
    return {
        "observation": _enc_listing_observation(norm.observation),
        "price_amount": str(norm.price_amount) if norm.price_amount is not None else None,
        "currency_code": norm.currency_code,
        "availability": _enc_enum(norm.availability),
        "condition": _enc_enum(norm.condition),
        "seller_name": norm.seller_name,
        "normalization_issues": [
            _enc_normalization_issue(i) for i in norm.normalization_issues
        ],
    }


def _enc_assessment(assess: ListingIdentityAssessment) -> dict[str, object]:
    return {
        "normalized_listing": _enc_normalized_listing(assess.normalized_listing),
        "requested_part_number": assess.requested_part_number,
        "candidate_part_number_raw": assess.candidate_part_number_raw,
        "candidate_part_number_compared": assess.candidate_part_number_compared,
        "candidate_evidence_source": _enc_enum(assess.candidate_evidence_source),
        "match_type": _enc_enum(assess.match_type),
        "decision": _enc_enum(assess.decision),
        "rejection_reason": (
            _enc_enum(assess.rejection_reason)
            if assess.rejection_reason is not None
            else None
        ),
    }


def encode_price_aggregation_result(
    result: PriceAggregationResult,
) -> dict[str, object]:
    """Encode a ``PriceAggregationResult`` into a V1 JSON-serialisable dict.

    The returned dict contains only native JSON types: str, int, list, dict,
    None. No ``Decimal``, ``Enum``, or dataclass objects leak into the payload.

    Assessments are stored **once** in the top-level ``assessments`` array.
    Bucket and exclusion membership references them by integer index rather
    than duplicating the nested evidence.

    Raises ``TypeError`` if the input is not a ``PriceAggregationResult``
    (caller defect).
    """
    if not isinstance(result, PriceAggregationResult):
        raise TypeError(
            f"expected PriceAggregationResult, got {type(result).__name__}"
        )

    # Build canonical assessment list and value→index mapping.
    # 4A membership is value-based: a bucket may hold an assessment equal
    # by value to one in the top-level tuple but distinct by identity.
    # Frozen dataclasses derive __eq__ and __hash__ from fields, so we
    # use the assessment object itself as the dict key. Python dict then
    # uses hash + equality correctly, so hash collisions are handled.
    assessments_encoded: list[dict[str, object]] = []
    assessments_by_value: dict[ListingIdentityAssessment, int] = {}
    for i, assess in enumerate(result.assessments):
        assessments_encoded.append(_enc_assessment(assess))
        assessments_by_value[assess] = i

    # Buckets reference assessments by index within the bucket's own
    # assessment tuple. We must map those to global canonical indexes.
    # Use the assessment object as dict key (hash + equality).
    buckets_encoded: list[dict[str, object]] = []
    for bucket in result.buckets:
        bucket_indexes: list[int] = []
        for assess in bucket.assessments:
            if assess not in assessments_by_value:
                # This can happen if a bucket references an assessment
                # not in the top-level tuple — should not occur for a
                # valid PriceAggregationResult, but fail clearly.
                raise TypeError(
                    "bucket references an assessment not present in the "
                    "top-level assessments tuple"
                )
            bucket_indexes.append(assessments_by_value[assess])
        buckets_encoded.append({
            "currency_code": bucket.currency_code,
            "condition": _enc_enum(bucket.condition),
            "assessment_indexes": bucket_indexes,
            "count": bucket.count,
            "low": str(bucket.low),
            "median": str(bucket.median),
            "high": str(bucket.high),
            "market_range_low": (
                str(bucket.market_range_low)
                if bucket.market_range_low is not None
                else None
            ),
            "market_range_high": (
                str(bucket.market_range_high)
                if bucket.market_range_high is not None
                else None
            ),
            "confidence": _enc_enum(bucket.confidence),
        })

    # Exclusions reference assessments by global canonical index.
    exclusions_encoded: list[dict[str, object]] = []
    for excl in result.exclusions:
        if excl.assessment not in assessments_by_value:
            raise TypeError(
                "exclusion references an assessment not present in the "
                "top-level assessments tuple"
            )
        assessment_index = assessments_by_value[excl.assessment]
        exclusions_encoded.append({
            "assessment_index": assessment_index,
            "reason": _enc_enum(excl.reason),
        })

    return {
        "request": _enc_request(result.request),
        "assessments": assessments_encoded,
        "buckets": buckets_encoded,
        "exclusions": exclusions_encoded,
        "verification_status": _enc_enum(result.verification_status),
    }


# ---------------------------------------------------------------------------
# Decode — V1
# ---------------------------------------------------------------------------


def _dec_listing_observation(
    data: dict[str, object], path: str
) -> ListingObservation:
    _check_no_extra_keys(
        data,
        {
            "source_url", "extraction_method", "product_title",
            "manufacturer_part_number_text", "sku_text", "brand_text",
            "price_text", "currency_text", "availability_text",
            "condition_text", "seller_text", "offer_url_text",
            "raw_reference",
        },
        path,
    )
    # V1 requires all keys to be present; nullable means value is null, not absent.
    return ListingObservation(
        source_url=_dec_str(_dec_required_key(data, "source_url", path), f"{path}.source_url"),
        extraction_method=_dec_enum(
            ExtractionMethod,
            _dec_required_key(data, "extraction_method", path),
            f"{path}.extraction_method",
        ),
        product_title=_dec_optional_str(
            _dec_required_key(data, "product_title", path),
            f"{path}.product_title",
        ),
        manufacturer_part_number_text=_dec_optional_str(
            _dec_required_key(data, "manufacturer_part_number_text", path),
            f"{path}.manufacturer_part_number_text",
        ),
        sku_text=_dec_optional_str(
            _dec_required_key(data, "sku_text", path),
            f"{path}.sku_text",
        ),
        brand_text=_dec_optional_str(
            _dec_required_key(data, "brand_text", path),
            f"{path}.brand_text",
        ),
        price_text=_dec_optional_str(
            _dec_required_key(data, "price_text", path),
            f"{path}.price_text",
        ),
        currency_text=_dec_optional_str(
            _dec_required_key(data, "currency_text", path),
            f"{path}.currency_text",
        ),
        availability_text=_dec_optional_str(
            _dec_required_key(data, "availability_text", path),
            f"{path}.availability_text",
        ),
        condition_text=_dec_optional_str(
            _dec_required_key(data, "condition_text", path),
            f"{path}.condition_text",
        ),
        seller_text=_dec_optional_str(
            _dec_required_key(data, "seller_text", path),
            f"{path}.seller_text",
        ),
        offer_url_text=_dec_optional_str(
            _dec_required_key(data, "offer_url_text", path),
            f"{path}.offer_url_text",
        ),
        raw_reference=_dec_optional_str(
            _dec_required_key(data, "raw_reference", path),
            f"{path}.raw_reference",
        ),
    )


def _dec_normalization_issue(
    data: dict[str, object], path: str
) -> NormalizationIssue:
    _check_no_extra_keys(
        data,
        {"field", "code", "raw_value", "reason"},
        path,
    )
    return NormalizationIssue(
        field=_dec_str(_dec_required_key(data, "field", path), f"{path}.field"),
        code=_dec_enum(
            NormalizationIssueCode,
            _dec_required_key(data, "code", path),
            f"{path}.code",
        ),
        raw_value=_dec_str(_dec_required_key(data, "raw_value", path), f"{path}.raw_value"),
        reason=_dec_str(_dec_required_key(data, "reason", path), f"{path}.reason"),
    )


def _dec_normalized_listing(
    data: dict[str, object], path: str
) -> NormalizedListingObservation:
    _check_no_extra_keys(
        data,
        {
            "observation", "price_amount", "currency_code",
            "availability", "condition", "seller_name",
            "normalization_issues",
        },
        path,
    )
    observation = _dec_listing_observation(
        _dec_mapping(_dec_required_key(data, "observation", path), f"{path}.observation"),
        f"{path}.observation",
    )
    # V1 requires all keys; nullable means value is null, not absent.
    price_amount = _dec_optional_decimal(
        _dec_required_key(data, "price_amount", path),
        f"{path}.price_amount",
    )
    currency_code = _dec_optional_str(
        _dec_required_key(data, "currency_code", path),
        f"{path}.currency_code",
    )
    availability = _dec_enum(
        NormalizedAvailability,
        _dec_required_key(data, "availability", path),
        f"{path}.availability",
    )
    condition = _dec_enum(
        NormalizedCondition,
        _dec_required_key(data, "condition", path),
        f"{path}.condition",
    )
    seller_name = _dec_optional_str(
        _dec_required_key(data, "seller_name", path),
        f"{path}.seller_name",
    )
    issues_raw = _dec_list(
        _dec_required_key(data, "normalization_issues", path),
        f"{path}.normalization_issues",
    )
    normalization_issues = tuple(
        _dec_normalization_issue(
            _dec_mapping(item, f"{path}.normalization_issues[{i}]"),
            f"{path}.normalization_issues[{i}]",
        )
        for i, item in enumerate(issues_raw)
    )

    return NormalizedListingObservation(
        observation=observation,
        price_amount=price_amount,
        currency_code=currency_code,
        availability=availability,
        condition=condition,
        seller_name=seller_name,
        normalization_issues=normalization_issues,
    )


def _dec_assessment(
    data: dict[str, object], path: str
) -> ListingIdentityAssessment:
    _check_no_extra_keys(
        data,
        {
            "normalized_listing", "requested_part_number",
            "candidate_part_number_raw", "candidate_part_number_compared",
            "candidate_evidence_source", "match_type", "decision",
            "rejection_reason",
        },
        path,
    )
    return ListingIdentityAssessment(
        normalized_listing=_dec_normalized_listing(
            _dec_mapping(
                _dec_required_key(data, "normalized_listing", path),
                f"{path}.normalized_listing",
            ),
            f"{path}.normalized_listing",
        ),
        requested_part_number=_dec_str(
            _dec_required_key(data, "requested_part_number", path),
            f"{path}.requested_part_number",
        ),
        candidate_part_number_raw=_dec_str(
            _dec_required_key(data, "candidate_part_number_raw", path),
            f"{path}.candidate_part_number_raw",
        ),
        candidate_part_number_compared=_dec_str(
            _dec_required_key(data, "candidate_part_number_compared", path),
            f"{path}.candidate_part_number_compared",
        ),
        candidate_evidence_source=_dec_enum(
            EvidenceSource,
            _dec_required_key(data, "candidate_evidence_source", path),
            f"{path}.candidate_evidence_source",
        ),
        match_type=_dec_enum(
            IdentityMatchType,
            _dec_required_key(data, "match_type", path),
            f"{path}.match_type",
        ),
        decision=_dec_enum(
            EvidenceDecision,
            _dec_required_key(data, "decision", path),
            f"{path}.decision",
        ),
        rejection_reason=(
            _dec_enum(
                IdentityRejectionReason,
                _dec_required_key(data, "rejection_reason", path),
                f"{path}.rejection_reason",
            )
            if _dec_required_key(data, "rejection_reason", path) is not None
            else None
        ),
    )


def _dec_request(data: dict[str, object], path: str) -> ResearchRequest:
    _check_no_extra_keys(
        data,
        {"manufacturer_part_number", "description"},
        path,
    )
    raw_mpn = _dec_str(
        _dec_required_key(data, "manufacturer_part_number", path),
        f"{path}.manufacturer_part_number",
    )
    raw_description = _dec_str(
        _dec_required_key(data, "description", path),
        f"{path}.description",
    )
    # ResearchRequest constructor strips surrounding whitespace.
    # The V1 encoder stores already-canonical values, so if the constructor
    # changes them, the stored payload is corrupt.
    request = ResearchRequest(
        manufacturer_part_number=raw_mpn,
        description=raw_description,
    )
    if request.manufacturer_part_number != raw_mpn:
        raise PriceResultCodecError(
            f"{path}.manufacturer_part_number was altered by constructor "
            "normalization; stored V1 payload is corrupt"
        )
    if request.description != raw_description:
        raise PriceResultCodecError(
            f"{path}.description was altered by constructor normalization; "
            "stored V1 payload is corrupt"
        )
    return request


def _decode_v1_payload(
    payload: dict[str, object],
) -> PriceAggregationResult:
    """Decode a V1 payload into a validated ``PriceAggregationResult``.

    Internal function. All nested constructor calls live inside a single
    validation boundary in ``decode_price_aggregation_result``.

    Raises ``PriceResultCodecError`` for any structural violation.
    Raises ``TypeError``, ``ValueError``, or ``DomainValidationError``
    when persisted data violates a constructor contract — the caller
    (``decode_price_aggregation_result``) wraps those.
    """

    # --- Top-level structure ---
    _check_no_extra_keys(
        payload,
        {"request", "assessments", "buckets", "exclusions", "verification_status"},
        "top-level",
    )

    # --- Request ---
    request_data = _dec_mapping(
        _dec_required_key(payload, "request", "top-level"),
        "request",
    )
    request = _dec_request(request_data, "request")

    # --- Assessments (canonical list, stored once) ---
    assessments_raw = _dec_list(
        _dec_required_key(payload, "assessments", "top-level"),
        "assessments",
    )
    assessments: list[ListingIdentityAssessment] = []
    for i, item in enumerate(assessments_raw):
        assessments.append(
            _dec_assessment(
                _dec_mapping(item, f"assessments[{i}]"),
                f"assessments[{i}]",
            )
        )

    # --- Buckets ---
    buckets_raw = _dec_list(
        _dec_required_key(payload, "buckets", "top-level"),
        "buckets",
    )
    buckets: list[PriceAggregateBucket] = []
    for i, bucket_data in enumerate(buckets_raw):
        bd = _dec_mapping(bucket_data, f"buckets[{i}]")
        _check_no_extra_keys(
            bd,
            {
                "currency_code", "condition", "assessment_indexes",
                "count", "low", "median", "high",
                "market_range_low", "market_range_high", "confidence",
            },
            f"buckets[{i}]",
        )

        currency_code = _dec_str(
            _dec_required_key(bd, "currency_code", f"buckets[{i}]"),
            f"buckets[{i}].currency_code",
        )
        condition = _dec_enum(
            NormalizedCondition,
            _dec_required_key(bd, "condition", f"buckets[{i}]"),
            f"buckets[{i}].condition",
        )
        assessment_indexes_raw = _dec_list(
            _dec_required_key(bd, "assessment_indexes", f"buckets[{i}]"),
            f"buckets[{i}].assessment_indexes",
        )
        # Validate all indexes are valid non-negative ints in range.
        assessment_indexes: list[int] = []
        for j, idx in enumerate(assessment_indexes_raw):
            assessment_indexes.append(
                _validate_assessment_index(
                    idx, len(assessments),
                    f"buckets[{i}].assessment_indexes[{j}]",
                )
            )

        # Check for duplicate indexes within this bucket.
        if len(assessment_indexes) != len(set(assessment_indexes)):
            raise PriceResultCodecError(
                f"buckets[{i}]: duplicate assessment index in bucket"
            )

        count = _dec_int(_dec_required_key(bd, "count", f"buckets[{i}]"), f"buckets[{i}].count")
        low = _dec_decimal(_dec_required_key(bd, "low", f"buckets[{i}]"), f"buckets[{i}].low")
        median = _dec_decimal(
            _dec_required_key(bd, "median", f"buckets[{i}]"),
            f"buckets[{i}].median",
        )
        high = _dec_decimal(
            _dec_required_key(bd, "high", f"buckets[{i}]"),
            f"buckets[{i}].high",
        )
        market_range_low = _dec_optional_decimal(
            _dec_required_key(bd, "market_range_low", f"buckets[{i}]"),
            f"buckets[{i}].market_range_low",
        )
        market_range_high = _dec_optional_decimal(
            _dec_required_key(bd, "market_range_high", f"buckets[{i}]"),
            f"buckets[{i}].market_range_high",
        )
        confidence = _dec_enum(
            ConfidenceLevel,
            _dec_required_key(bd, "confidence", f"buckets[{i}]"),
            f"buckets[{i}].confidence",
        )

        # Resolve assessment references into actual objects.
        bucket_assessments = tuple(assessments[idx] for idx in assessment_indexes)

        buckets.append(
            PriceAggregateBucket(
                currency_code=currency_code,
                condition=condition,
                assessments=bucket_assessments,
                count=count,
                low=low,
                median=median,
                high=high,
                market_range_low=market_range_low,
                market_range_high=market_range_high,
                confidence=confidence,
            )
        )

    # --- Exclusions ---
    exclusions_raw = _dec_list(
        _dec_required_key(payload, "exclusions", "top-level"),
        "exclusions",
    )
    exclusions: list[PriceAggregationExclusion] = []
    for i, excl_data in enumerate(exclusions_raw):
        ed = _dec_mapping(excl_data, f"exclusions[{i}]")
        _check_no_extra_keys(
            ed,
            {"assessment_index", "reason"},
            f"exclusions[{i}]",
        )
        assessment_index = _validate_assessment_index(
            _dec_required_key(ed, "assessment_index", f"exclusions[{i}]"),
            len(assessments),
            f"exclusions[{i}].assessment_index",
        )
        reason = _dec_enum(
            PriceAggregationExclusionReason,
            _dec_required_key(ed, "reason", f"exclusions[{i}]"),
            f"exclusions[{i}].reason",
        )
        exclusions.append(
            PriceAggregationExclusion(
                assessment=assessments[assessment_index],
                reason=reason,
            )
        )

    # --- Verification status ---
    verification_status = _dec_enum(
        VerificationStatus,
        _dec_required_key(payload, "verification_status", "top-level"),
        "verification_status",
    )

    # --- Final construction through normal __post_init__ ---
    # This re-validates all 4A invariants: duplicate assessment rules,
    # bucket statistics, bucket membership, exclusions, multiplicity,
    # request provenance, unique bucket keys, verification status.
    return PriceAggregationResult(
        request=request,
        assessments=tuple(assessments),
        exclusions=tuple(exclusions),
        buckets=tuple(buckets),
        verification_status=verification_status,
    )


def decode_price_aggregation_result(
    payload: object,
    *,
    schema_version: int,
) -> PriceAggregationResult:
    """Decode a persisted payload into a ``PriceAggregationResult``.

    The payload is treated as untrusted/corruptible state. Decoding is strict:

    * Unsupported ``schema_version`` raises ``PriceResultCodecError``.
    * Missing keys, extra keys, wrong types, unknown enums, and invalid
      Decimal values all raise ``PriceResultCodecError``.
    * Assessment indexes must be valid non-negative integers in range.
    * Duplicate bucket indexes are rejected.
    * The final ``PriceAggregationResult`` is constructed through its normal
      ``__post_init__`` which re-validates all invariants.

    Returns a fully validated ``PriceAggregationResult`` or raises.
    Never returns a partially decoded object.

    Every nested constructor — ``ResearchRequest``, ``ListingObservation``,
    ``NormalizationIssue``, ``NormalizedListingObservation``,
    ``ListingIdentityAssessment``, ``PriceAggregateBucket``,
    ``PriceAggregationExclusion``, and ``PriceAggregationResult`` — is
    protected. Any ``TypeError``, ``ValueError``, or ``DomainValidationError``
    from persisted data that violates a contract is wrapped as
    ``PriceResultCodecError``.
    """

    # --- Schema version gate ---
    if isinstance(schema_version, bool) or not isinstance(schema_version, int):
        raise PriceResultCodecError(
            f"schema_version must be int, got {type(schema_version).__name__}"
        )
    if schema_version != PRICE_RESULT_SCHEMA_VERSION:
        raise PriceResultCodecError(
            f"unsupported schema_version {schema_version}; "
            f"only version {PRICE_RESULT_SCHEMA_VERSION} is supported"
        )

    # --- Payload structure ---
    if not isinstance(payload, dict):
        raise PriceResultCodecError(
            f"payload must be a mapping, got {type(payload).__name__}"
        )

    # --- Single validation boundary for all nested constructors ---
    try:
        return _decode_v1_payload(payload)
    except PriceResultCodecError:
        raise
    except (DomainValidationError, TypeError, ValueError):
        raise PriceResultCodecError(
            "stored price result violates the V1 contract"
        ) from None
