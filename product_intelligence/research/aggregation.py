"""Deterministic price aggregation (PRODUCT-INTEL.4A).

Given a ``ResearchRequest`` and a sequence of ``ListingIdentityAssessment``
values (produced by 3C), this module decides which prices are
demonstrably comparable and computes the deterministic aggregate for each
comparable group.

```text
ResearchRequest + tuple[ListingIdentityAssessment, ...]
        ↓
  price-eligibility assessment
        ↓
  comparable buckets  (currency + known-condition)
        ↓
  deterministic statistics  (count / low / median / high)
        ↓
  PriceAggregationResult
```

What 4A is not
----------------

**It does not discover listings.** It consumes pre-built
``ListingIdentityAssessment`` values. No search, no fetch, no extraction,
no normalization, and no MPN comparison.

**It does not decide identity.** It trusts the 3C
``EvidenceDecision`` on each assessment. A REJECTED or UNDECIDED listing
is excluded — never second-guessed.

**It does not convert currencies.** No FX rates, no ``$`` means ``USD``,
no defaulting, no guessing. Prices are grouped by exact normalized
currency code and never share arithmetic across currencies.

**It does not remove outliers.** An extreme but identity-accepted,
normalized, comparable price stays in the bucket and expands the
observed low/high. There is no timestamped price corpus to justify a
threshold, and removing one silently would manufacture a prettier band.

**It does not compute unit price.** 3B normalized no quantity, no pack
size, and no unit price because no recorded fixture publishes raw
evidence for any of them. 4A does not invent one by parsing prose,
titles, or URLs. It aggregates the normalized *offer price* — not a
unit-normalized price.

**It does not enforce availability.** 3B normalizes availability, but 4A
does not use it as an arithmetic eligibility rule. An OUT_OF_STOCK price
is not automatically excluded; UNKNOWN availability is not assumed to
mean "in stock". Availability remains reachable through the evidence chain.

**It does not deduplicate market listings.** Broad listing deduplication
(URL canonicalization, seller entity resolution, cross-site matching) is
not implemented. Only exact duplicate *input values* are refused to
prevent a caller from double-counting the same assessment.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Final

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import (
    ConfidenceLevel,
    EvidenceDecision,
    VerificationStatus,
)
from product_intelligence.research.listings import ListingObservation
from product_intelligence.research.matching import ListingIdentityAssessment
from product_intelligence.research.normalization import (
    NormalizedCondition,
    NormalizedListingObservation,
)

# ---------------------------------------------------------------------------
# Exclusion-reason vocabulary
# ---------------------------------------------------------------------------


class PriceAggregationExclusionReason(str, Enum):
    """Why one identity-accepted listing was excluded from price arithmetic.

    The four members correspond to the eligibility checks in
    ``_determine_eligibility``, in the order they fire:

    1. ``IDENTITY_NOT_ACCEPTED`` — 3C did not accept this listing.
    2. ``NO_NUMERIC_PRICE`` — identity accepted but no Decimal price.
    3. ``NO_COMPARABLE_CURRENCY`` — price present but currency absent or
       conflicted (3B produced ``currency_code=None``).
    4. ``UNKNOWN_CONDITION`` — price and currency present but condition
       was not confidently mapped by 3B.

    Reason precedence is the eligibility order above. If identity is
    rejected AND price is missing, the reason is
    ``IDENTITY_NOT_ACCEPTED`` because price arithmetic was never eligible.

    Finer detail remains in the 3B ``NormalizationIssue`` chain, reachable
    through the assessment → normalized listing → issues.
    """

    IDENTITY_NOT_ACCEPTED = "IDENTITY_NOT_ACCEPTED"
    NO_NUMERIC_PRICE = "NO_NUMERIC_PRICE"
    NO_COMPARABLE_CURRENCY = "NO_COMPARABLE_CURRENCY"
    UNKNOWN_CONDITION = "UNKNOWN_CONDITION"


# ---------------------------------------------------------------------------
# PriceAggregationExclusion
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PriceAggregationExclusion:
    """One listing identity assessment excluded from price arithmetic.

    Retains the exact ``ListingIdentityAssessment`` so a reviewer can trace
    why it was not used. The exclusion reason is the 4A-level classification;
    the underlying 3B ``NormalizationIssue`` values provide finer detail.
    """

    assessment: ListingIdentityAssessment
    reason: PriceAggregationExclusionReason

    def __post_init__(self) -> None:
        if not isinstance(self.assessment, ListingIdentityAssessment):
            raise TypeError(
                "assessment must be a ListingIdentityAssessment, got "
                f"{type(self.assessment).__name__}"
            )
        if not isinstance(self.reason, PriceAggregationExclusionReason):
            raise TypeError(
                "reason must be a PriceAggregationExclusionReason, got "
                f"{type(self.reason).__name__}"
            )

        # -- Consistency: reason must match the underlying assessment --
        normalized = self.assessment.normalized_listing
        reason = self.reason

        if reason is PriceAggregationExclusionReason.IDENTITY_NOT_ACCEPTED:
            if self.assessment.decision is EvidenceDecision.ACCEPTED:
                raise ValueError(
                    "IDENTITY_NOT_ACCEPTED requires a non-ACCEPTED decision, "
                    f"but the assessment is {self.assessment.decision.value}"
                )

        if reason is PriceAggregationExclusionReason.NO_NUMERIC_PRICE:
            # Must have ACCEPTED identity but no price.
            if self.assessment.decision is not EvidenceDecision.ACCEPTED:
                raise ValueError(
                    "NO_NUMERIC_PRICE requires ACCEPTED identity, "
                    f"but the assessment is {self.assessment.decision.value}; "
                    "identity must be the first exclusion checked"
                )
            if normalized.price_amount is not None:
                raise ValueError(
                    "NO_NUMERIC_PRICE requires a missing price, "
                    f"but price_amount is {normalized.price_amount}"
                )

        if reason is PriceAggregationExclusionReason.NO_COMPARABLE_CURRENCY:
            # Must have ACCEPTED identity and a price, but no currency.
            if self.assessment.decision is not EvidenceDecision.ACCEPTED:
                raise ValueError(
                    "NO_COMPARABLE_CURRENCY requires ACCEPTED identity, "
                    f"but the assessment is {self.assessment.decision.value}"
                )
            if normalized.price_amount is None:
                raise ValueError(
                    "NO_COMPARABLE_CURRENCY requires a present price, "
                    "but price_amount is None; price must be checked "
                    "before currency in the eligibility order"
                )
            if normalized.currency_code is not None:
                raise ValueError(
                    "NO_COMPARABLE_CURRENCY requires a missing currency, "
                    f"but currency_code is {normalized.currency_code!r}"
                )

        if reason is PriceAggregationExclusionReason.UNKNOWN_CONDITION:
            # Must have ACCEPTED identity, a price, a currency, but UNKNOWN
            # condition.
            if self.assessment.decision is not EvidenceDecision.ACCEPTED:
                raise ValueError(
                    "UNKNOWN_CONDITION requires ACCEPTED identity, "
                    f"but the assessment is {self.assessment.decision.value}"
                )
            if normalized.price_amount is None:
                raise ValueError(
                    "UNKNOWN_CONDITION requires a present price, "
                    "but price_amount is None"
                )
            if normalized.currency_code is None:
                raise ValueError(
                    "UNKNOWN_CONDITION requires a present currency, "
                    "but currency_code is None"
                )
            if normalized.condition is not NormalizedCondition.UNKNOWN:
                raise ValueError(
                    "UNKNOWN_CONDITION requires UNKNOWN condition, "
                    f"but condition is {normalized.condition.value}"
                )


# ---------------------------------------------------------------------------
# PriceAggregateBucket
# ---------------------------------------------------------------------------


def _compute_median(sorted_prices: tuple[Decimal, ...]) -> Decimal:
    """Compute exact Decimal median of a sorted sequence.

    Never converts through float. For even counts, uses the exact
    Decimal midpoint of the two middle values.
    """
    n = len(sorted_prices)
    if n % 2 == 1:
        return sorted_prices[n // 2]
    # Even count: exact midpoint
    mid = n // 2
    return (sorted_prices[mid - 1] + sorted_prices[mid]) / Decimal("2")


@dataclass(frozen=True)
class PriceAggregateBucket:
    """One comparable-price group from the aggregation.

    A bucket groups observations that share the same currency code and the
    same known condition. Arithmetic is performed only within a bucket:
    ``USD`` + ``EUR`` never share one median, and ``NEW`` + ``USED`` never
    mix.

    All monetary values are ``Decimal``. Binary floating point never enters
    price arithmetic.

    The bucket is self-validating: ``__post_init__`` recomputes all statistics
    from the retained assessments and rejects fabricated states.
    """

    currency_code: str
    condition: NormalizedCondition
    assessments: tuple[ListingIdentityAssessment, ...]
    count: int
    low: Decimal
    median: Decimal
    high: Decimal
    market_range_low: Decimal | None
    market_range_high: Decimal | None
    confidence: ConfidenceLevel

    def __post_init__(self) -> None:
        # -- Type checks --
        if not isinstance(self.currency_code, str) or not self.currency_code:
            raise ValueError("currency_code must be a non-empty string")

        if not isinstance(self.condition, NormalizedCondition):
            raise TypeError(
                "condition must be a NormalizedCondition, got "
                f"{type(self.condition).__name__}"
            )

        if not isinstance(self.assessments, tuple):
            raise TypeError(
                "assessments must be a tuple, got "
                f"{type(self.assessments).__name__}"
            )

        # Bucket must have at least one assessment.
        if not self.assessments:
            raise ValueError(
                "a bucket must contain at least one assessment; "
                "zero-observation buckets are not comparable"
            )

        # -- Type checks for monetary fields --
        # Money is Decimal, never int, float, bool, or str.
        for monetary_name in ("low", "median", "high"):
            val = getattr(self, monetary_name)
            if not isinstance(val, Decimal):
                raise TypeError(
                    f"{monetary_name} must be Decimal, got "
                    f"{type(val).__name__}"
                )

        # Type checks for optional monetary fields.
        if self.market_range_low is not None:
            if not isinstance(self.market_range_low, Decimal):
                raise TypeError(
                    "market_range_low must be Decimal or None, got "
                    f"{type(self.market_range_low).__name__}"
                )
        if self.market_range_high is not None:
            if not isinstance(self.market_range_high, Decimal):
                raise TypeError(
                    "market_range_high must be Decimal or None, got "
                    f"{type(self.market_range_high).__name__}"
                )

        # count must be int but not bool (bool is a subclass of int).
        if isinstance(self.count, bool) or not isinstance(self.count, int):
            raise TypeError(
                f"count must be int, got {type(self.count).__name__}"
            )

        # confidence must be the exact ConfidenceLevel enum.
        if not isinstance(self.confidence, ConfidenceLevel):
            raise TypeError(
                f"confidence must be ConfidenceLevel, got "
                f"{type(self.confidence).__name__}"
            )

        # -- Market range must be paired --
        # Both None or both Decimal; never one-sided.
        range_low_is_none = self.market_range_low is None
        range_high_is_none = self.market_range_high is None
        if range_low_is_none != range_high_is_none:
            raise ValueError(
                "market_range_low and market_range_high must be either "
                "both None or both Decimal; a one-sided range is impossible"
            )

        # Every member must be an accepted ListingIdentityAssessment with
        # a Decimal price, matching currency, and matching condition.
        prices: list[Decimal] = []
        for i, assessment in enumerate(self.assessments):
            if not isinstance(assessment, ListingIdentityAssessment):
                raise TypeError(
                    f"assessments[{i}] must be ListingIdentityAssessment, got "
                    f"{type(assessment).__name__}"
                )

            # Must be 3C-accepted.
            if assessment.decision is not EvidenceDecision.ACCEPTED:
                raise ValueError(
                    f"assessments[{i}] has decision "
                    f"{assessment.decision.value}; "
                    "only ACCEPTED listings contribute to a bucket"
                )

            norm = assessment.normalized_listing

            # Must have a Decimal price (not float).
            if norm.price_amount is None:
                raise ValueError(
                    f"assessments[{i}] has no price_amount; "
                    "every bucket member must have a numeric price"
                )
            if not isinstance(norm.price_amount, Decimal):
                raise TypeError(
                    f"assessments[{i}].price_amount is "
                    f"{type(norm.price_amount).__name__}; "
                    "money is never a float in a bucket"
                )

            # Must match bucket currency.
            if norm.currency_code != self.currency_code:
                raise ValueError(
                    f"assessments[{i}] has currency {norm.currency_code!r} "
                    f"but bucket currency is {self.currency_code!r}; "
                    "all members must share the bucket's currency"
                )

            # Must match bucket condition.
            if norm.condition != self.condition:
                raise ValueError(
                    f"assessments[{i}] has condition {norm.condition.value} "
                    f"but bucket condition is {self.condition.value}; "
                    "all members must share the bucket's condition"
                )

            # Condition must not be UNKNOWN.
            if norm.condition is NormalizedCondition.UNKNOWN:
                raise ValueError(
                    f"assessments[{i}] has UNKNOWN condition; "
                    "UNKNOWN condition is excluded from aggregation"
                )

            prices.append(norm.price_amount)

        # -- Refuse exact duplicate assessment values (value-based, not
        #    identity-based). Shared invariant with PriceAggregationResult   --
        #    and aggregate_listing_prices.                                    --
        _refuse_duplicate_assessments(self.assessments)

        # -- Recompute and verify statistics --
        sorted_prices = tuple(sorted(prices))
        expected_count = len(sorted_prices)
        expected_low = sorted_prices[0]
        expected_median = _compute_median(sorted_prices)
        expected_high = sorted_prices[-1]

        if self.count != expected_count:
            raise ValueError(
                f"count is {self.count} but there are {expected_count} "
                "assessments with numeric prices; count must equal "
                "len(assessments)"
            )

        if self.low != expected_low:
            raise ValueError(
                f"low is {self.low} but recomputed minimum is "
                f"{expected_low}; statistics must be reproducible "
                "from retained assessments"
            )

        if self.median != expected_median:
            raise ValueError(
                f"median is {self.median} but recomputed median is "
                f"{expected_median}; median must be the exact Decimal "
                "recomputation, never stored independently"
            )

        if self.high != expected_high:
            raise ValueError(
                f"high is {self.high} but recomputed maximum is "
                f"{expected_high}; statistics must be reproducible "
                "from retained assessments"
            )

        # -- Market range: present only for count >= 3 --
        expected_has_range = expected_count >= 3
        actual_has_range = (
            self.market_range_low is not None
            and self.market_range_high is not None
        )
        if expected_has_range and not actual_has_range:
            raise ValueError(
                f"bucket has {expected_count} observations (>= 3) but "
                "market_range_low/high are None; a bucket with three or "
                "more comparable prices must publish the observed range"
            )
        if not expected_has_range and actual_has_range:
            raise ValueError(
                f"bucket has {expected_count} observations (< 3) but "
                "market_range_low/high are present; fewer than three "
                "comparable prices must not claim a market range"
            )
        if expected_has_range:
            if self.market_range_low != expected_low:
                raise ValueError(
                    f"market_range_low is {self.market_range_low} but "
                    f"low is {expected_low}; range_low must equal low "
                    "when both are present"
                )
            if self.market_range_high != expected_high:
                raise ValueError(
                    f"market_range_high is {self.market_range_high} but "
                    f"high is {expected_high}; range_high must equal high "
                    "when both are present"
                )

        # -- Confidence: LOW for 1-2, MEDIUM for 3+ --
        expected_confidence = (
            ConfidenceLevel.MEDIUM if expected_count >= 3 else ConfidenceLevel.LOW
        )
        if self.confidence != expected_confidence:
            raise ValueError(
                f"confidence is {self.confidence.value} but count is "
                f"{expected_count} (expected {expected_confidence.value}); "
                "confidence must follow the count policy"
            )

        # 4A never produces HIGH confidence — count alone has not earned it.
        if self.confidence is ConfidenceLevel.HIGH:
            raise ValueError(
                "4A must not produce HIGH confidence; a larger count alone "
                "has not earned HIGH without source-independence scoring, "
                "freshness modelling, cross-source deduplication, or an "
                "empirically validated outlier policy"
            )


# ---------------------------------------------------------------------------
# PriceAggregationResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PriceAggregationResult:
    """The complete result of one price aggregation.

    Retains every input ``ListingIdentityAssessment`` so no evidence is lost.
    Each assessment appears exactly once: contributing to one
    ``PriceAggregateBucket`` or retained in one ``PriceAggregationExclusion``.

    The overall ``verification_status`` describes the aggregate conclusion:

    * ``UNKNOWN`` — zero comparable buckets (no price to report).
    * ``VERIFIED`` — exactly one comparable bucket.
    * ``AMBIGUOUS`` — more than one internally valid but non-comparable
      bucket (e.g. USD/NEW and EUR/NEW).

    There is no single ``market_price`` field. When multiple buckets exist,
    choosing one would be a business policy 4A does not have.
    """

    request: ResearchRequest
    assessments: tuple[ListingIdentityAssessment, ...]
    exclusions: tuple[PriceAggregationExclusion, ...]
    buckets: tuple[PriceAggregateBucket, ...]
    verification_status: VerificationStatus

    def __post_init__(self) -> None:
        # -- Type checks --
        if not isinstance(self.request, ResearchRequest):
            raise TypeError(
                "request must be a ResearchRequest, got "
                f"{type(self.request).__name__}"
            )
        if not isinstance(self.assessments, tuple):
            raise TypeError(
                "assessments must be a tuple, got "
                f"{type(self.assessments).__name__}"
            )
        for i, a in enumerate(self.assessments):
            if not isinstance(a, ListingIdentityAssessment):
                raise TypeError(
                    f"assessments[{i}] must be ListingIdentityAssessment, got "
                    f"{type(a).__name__}"
                )
        if not isinstance(self.exclusions, tuple):
            raise TypeError(
                "exclusions must be a tuple, got "
                f"{type(self.exclusions).__name__}"
            )
        for i, e in enumerate(self.exclusions):
            if not isinstance(e, PriceAggregationExclusion):
                raise TypeError(
                    f"exclusions[{i}] must be PriceAggregationExclusion, got "
                    f"{type(e).__name__}"
                )
        if not isinstance(self.buckets, tuple):
            raise TypeError(
                "buckets must be a tuple, got "
                f"{type(self.buckets).__name__}"
            )
        for i, b in enumerate(self.buckets):
            if not isinstance(b, PriceAggregateBucket):
                raise TypeError(
                    f"buckets[{i}] must be PriceAggregateBucket, got "
                    f"{type(b).__name__}"
                )
        if not isinstance(self.verification_status, VerificationStatus):
            raise TypeError(
                "verification_status must be a VerificationStatus, got "
                f"{type(self.verification_status).__name__}"
            )

        # -- Refuse exact duplicate input values (value-based, not
        #    identity-based). This is the same invariant the normal builder
        #    enforces, so a fabricated result cannot bypass it.             --
        _refuse_duplicate_assessments(self.assessments)

        # -- Every input assessment must appear exactly once (bucket or
        #    exclusion). No assessment disappears. No assessment is counted
        #    twice. Multiplicity is preserved using Counter so that a bucket
        #    containing the same object twice is caught.                --
        output_counts: Counter[ListingIdentityAssessment] = Counter()
        for bucket in self.buckets:
            for assessment in bucket.assessments:
                output_counts[assessment] += 1

        for exclusion in self.exclusions:
            output_counts[exclusion.assessment] += 1

        # Build the expected counter from input.
        input_counts: Counter[ListingIdentityAssessment] = Counter(self.assessments)

        # Check: every input assessment appears at least once.
        for assessment in self.assessments:
            if output_counts[assessment] == 0:
                raise ValueError(
                    "one or more input assessment(s) do not appear in any "
                    "bucket or exclusion; no evidence is silently dropped"
                )

        # Check: no output evidence was not present in input.
        for assessment in output_counts:
            if input_counts[assessment] == 0:
                raise ValueError(
                    "one or more assessments in buckets/exclusions were not "
                    "supplied as input; the result must not invent evidence"
                )

        # Check multiplicity: every input assessment appears exactly once.
        for assessment, count in output_counts.items():
            if count != input_counts[assessment]:
                raise ValueError(
                    f"assessment appears {count} time(s) in output but "
                    f"{input_counts[assessment]} time(s) in input; "
                    "every input assessment must appear exactly once"
                )

        # -- Unique bucket keys --
        # At most one bucket per exact (currency_code, condition).
        bucket_keys: set[tuple[str, NormalizedCondition]] = set()
        for bucket in self.buckets:
            key = (bucket.currency_code, bucket.condition)
            if key in bucket_keys:
                raise ValueError(
                    f"duplicate bucket key ({bucket.currency_code!r}, "
                    f"{bucket.condition.value}); "
                    "at most one bucket per currency+condition group"
                )
            bucket_keys.add(key)

        # -- Request provenance --
        # Every assessment's requested_part_number must equal the result's
        # request.manufacturer_part_number exactly.
        expected_mpn = self.request.manufacturer_part_number
        for assessment in self.assessments:
            if assessment.requested_part_number != expected_mpn:
                raise ValueError(
                    f"assessment belongs to request MPN "
                    f"{assessment.requested_part_number!r} but this result's "
                    f"request has MPN {expected_mpn!r}; "
                    "all assessments must belong to the same request"
                )

        # -- Verification status must be consistent with buckets --
        n_buckets = len(self.buckets)
        status = self.verification_status

        if n_buckets == 0:
            if status is not VerificationStatus.UNKNOWN:
                raise ValueError(
                    f"zero buckets requires UNKNOWN status, "
                    f"got {status.value}"
                )
        elif n_buckets == 1:
            if status is not VerificationStatus.VERIFIED:
                raise ValueError(
                    f"one bucket requires VERIFIED status, "
                    f"got {status.value}"
                )
        else:
            # Multiple non-comparable buckets -> AMBIGUOUS
            if status is not VerificationStatus.AMBIGUOUS:
                raise ValueError(
                    f"{n_buckets} buckets require AMBIGUOUS status, "
                    f"got {status.value}; "
                    "multiple valid but non-comparable buckets do not "
                    "produce VERIFIED or UNKNOWN"
                )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _refuse_duplicate_assessments(
    assessments: tuple[ListingIdentityAssessment, ...],
) -> None:
    """Raise ``ValueError`` if any two assessments are equal by value.

    Frozen dataclasses derive ``__hash__`` and ``__eq__`` from their fields,
    so two separately constructed but equal-by-value assessments collide in a
    ``Counter``. This catches the duplicate-value invariant shared by both the
    normal builder (``aggregate_listing_prices``) and the direct constructor of
    ``PriceAggregationResult``.
    """
    assessment_counts: Counter[ListingIdentityAssessment] = Counter(assessments)
    for _assessment, count in assessment_counts.items():
        if count > 1:
            raise ValueError(
                "one or more assessments are exact duplicates of a previously "
                "supplied assessment (by value); the same assessment must not "
                "be counted twice"
            )


def _determine_eligibility(
    assessment: ListingIdentityAssessment,
) -> PriceAggregationExclusionReason | None:
    """Return the exclusion reason, or ``None`` if the listing is eligible.

    Checks are in fixed precedence order:

    1. Identity must be ACCEPTED (3C).
    2. Normalized price must be a Decimal (3B).
    3. Normalized currency must be present.
    4. Condition must not be UNKNOWN.

    The first failing check wins. For example, a rejected listing with no
    price is excluded for ``IDENTITY_NOT_ACCEPTED``, not
    ``NO_NUMERIC_PRICE``, because price arithmetic was never eligible.
    """
    normalized = assessment.normalized_listing

    if assessment.decision is not EvidenceDecision.ACCEPTED:
        return PriceAggregationExclusionReason.IDENTITY_NOT_ACCEPTED

    if normalized.price_amount is None:
        return PriceAggregationExclusionReason.NO_NUMERIC_PRICE

    if normalized.currency_code is None:
        return PriceAggregationExclusionReason.NO_COMPARABLE_CURRENCY

    if normalized.condition is NormalizedCondition.UNKNOWN:
        return PriceAggregationExclusionReason.UNKNOWN_CONDITION

    return None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def aggregate_listing_prices(
    request: ResearchRequest,
    assessments: tuple[ListingIdentityAssessment, ...],
) -> PriceAggregationResult:
    """Compute deterministic price aggregates over identity-accepted listings.

    Pure and deterministic: the same request and assessments always produce
    the same result. No I/O, no Django, no provider call, no clock, no
    environment access, and no LLM call.

    Args:
        request: The canonical research request. Every assessment must have
            been produced for this same request (its ``requested_part_number``
            must equal ``request.manufacturer_part_number`` exactly).
        assessments: Pre-built 3C identity assessments. Must be a tuple with
            no exact duplicate values.

    Returns:
        A ``PriceAggregationResult`` with buckets, exclusions, and an overall
        ``VerificationStatus``.

    Raises:
        TypeError: If arguments are the wrong type.
        ValueError: If assessments are from different requests, contain
            exact duplicates, or are otherwise structurally invalid.
    """
    if not isinstance(request, ResearchRequest):
        raise TypeError(
            f"request must be a ResearchRequest, got {type(request).__name__}"
        )
    if not isinstance(assessments, tuple):
        raise TypeError(
            f"assessments must be a tuple, got {type(assessments).__name__}"
        )

    # -- Validate every assessment belongs to this request --
    expected_mpn = request.manufacturer_part_number
    for i, assessment in enumerate(assessments):
        if not isinstance(assessment, ListingIdentityAssessment):
            raise TypeError(
                f"assessments[{i}] must be ListingIdentityAssessment, got "
                f"{type(assessment).__name__}"
            )
        if assessment.requested_part_number != expected_mpn:
            raise ValueError(
                f"assessments[{i}] was produced for request MPN "
                f"{assessment.requested_part_number!r} but this request "
                f"has MPN {expected_mpn!r}; "
                "assessments from different requests must not be mixed"
            )

    # -- Refuse exact duplicate input values --
    # (shared helper, also used by PriceAggregationResult.__post_init__)
    _refuse_duplicate_assessments(assessments)

    # -- Classify each assessment as eligible or excluded --
    exclusions: list[PriceAggregationExclusion] = []
    # Bucket key: (currency_code, condition) -> list of assessments
    bucket_groups: dict[tuple[str, NormalizedCondition], list[ListingIdentityAssessment]] = {}

    for assessment in assessments:
        reason = _determine_eligibility(assessment)
        if reason is not None:
            exclusions.append(
                PriceAggregationExclusion(
                    assessment=assessment,
                    reason=reason,
                )
            )
        else:
            norm = assessment.normalized_listing
            assert norm.price_amount is not None  # eligibility guarantees this
            assert norm.currency_code is not None  # eligibility guarantees this
            assert norm.condition is not NormalizedCondition.UNKNOWN
            key = (norm.currency_code, norm.condition)
            bucket_groups.setdefault(key, []).append(assessment)

    # -- Build buckets from each group --
    buckets: list[PriceAggregateBucket] = []
    for (currency_code, condition), group_assessments in sorted(bucket_groups.items()):
        # Extract and sort prices
        prices = tuple(
            sorted(
                a.normalized_listing.price_amount
                for a in group_assessments
            )
        )
        count = len(prices)
        low = prices[0]
        median = _compute_median(prices)
        high = prices[-1]

        market_range_low = low if count >= 3 else None
        market_range_high = high if count >= 3 else None

        confidence = ConfidenceLevel.MEDIUM if count >= 3 else ConfidenceLevel.LOW

        buckets.append(
            PriceAggregateBucket(
                currency_code=currency_code,
                condition=condition,
                assessments=tuple(group_assessments),
                count=count,
                low=low,
                median=median,
                high=high,
                market_range_low=market_range_low,
                market_range_high=market_range_high,
                confidence=confidence,
            )
        )

    # -- Overall verification status --
    n_buckets = len(buckets)
    if n_buckets == 0:
        verification_status = VerificationStatus.UNKNOWN
    elif n_buckets == 1:
        verification_status = VerificationStatus.VERIFIED
    else:
        verification_status = VerificationStatus.AMBIGUOUS

    return PriceAggregationResult(
        request=request,
        assessments=assessments,
        exclusions=tuple(exclusions),
        buckets=tuple(buckets),
        verification_status=verification_status,
    )
