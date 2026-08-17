"""Controlled vocabularies for the evaluation corpus.

These are **evaluation** vocabularies. They describe the class of answer a
corpus case considers correct. They do not describe how a future resolver
reaches that answer, and they are not runtime domain vocabularies: nothing here
is imported by ``product_intelligence.domain``, and nothing here may leak into
it.

Why ``IdentityMatchType`` is not reused
--------------------------------------

``IdentityMatchType`` (domain) answers "by what mechanism was an observed item
tied to the request?" — character-for-character, after normalization,
partially, and so on. An evaluation expectation answers a different question:
"what class of answer is correct for this request?" A corpus case that says the
correct answer is the Samsung PM9A3 3.84TB SSD is deliberately silent about
whether a resolver should reach it by exact comparison or by deterministic
normalization — that is a later phase's design decision, not evaluation truth.
Reusing the runtime enum would smuggle that decision into the benchmark.
"""

from __future__ import annotations

from enum import Enum


class CaseKind(str, Enum):
    """Whether a case describes a real product or a constructed situation."""

    REAL_VERIFIED = "REAL_VERIFIED"
    """Identity backed by a recorded authoritative source."""

    SYNTHETIC = "SYNTHETIC"
    """Deliberately constructed to exercise a behaviour or edge condition.

    A synthetic case is never a claim about a real product, even when its input
    is derived from a real part number.
    """


class ExpectedResolution(str, Enum):
    """The class of answer the corpus considers correct for a case.

    Deliberately small: four values, no numeric score, no ranking, no
    threshold. Anything finer would be a claim about an algorithm that does not
    exist yet.
    """

    EXACT_IDENTITY = "EXACT_IDENTITY"
    """Exactly one canonical identity is the correct answer.

    Says nothing about the matching mechanism. The case records *which* product
    is correct; how a resolver arrives there is out of scope for the corpus.
    """

    AMBIGUOUS = "AMBIGUOUS"
    """More than one identity plausibly satisfies the request.

    A single identity must not be reported as settled. Offering candidates is
    fine; choosing one without evidence is the failure.
    """

    CONFLICT = "CONFLICT"
    """The supplied information points at incompatible identities.

    The correct behaviour is to report the conflict, not to quietly discard
    whichever side is inconvenient.
    """

    UNKNOWN = "UNKNOWN"
    """Nothing in the request supports an identity.

    Includes fictitious and unverifiable part numbers. An invented
    manufacturer or product is the failure mode this value guards.
    """


# The resolutions that require the system *not* to settle on one identity. Named
# here so every consumer reads the same list instead of re-deriving it.
ABSTAINING_RESOLUTIONS = frozenset(
    {
        ExpectedResolution.AMBIGUOUS,
        ExpectedResolution.CONFLICT,
        ExpectedResolution.UNKNOWN,
    }
)


class ChallengeTag(str, Enum):
    """Why a case is in the corpus — the condition it exercises.

    Tags describe the *shape of the request*, not a product category. A
    fine-grained product taxonomy is phase 6 work and must not start here.
    """

    EXACT_INPUT = "EXACT_INPUT"
    """Correct part number with a compatible description."""

    MPN_ONLY_INPUT = "MPN_ONLY_INPUT"
    """Correct part number, no description at all."""

    DESCRIPTION_ONLY_INPUT = "DESCRIPTION_ONLY_INPUT"
    """No part number. A strong description is still not part-number evidence."""

    SURROUNDING_WHITESPACE = "SURROUNDING_WHITESPACE"
    """Leading/trailing whitespace around either supplied value."""

    NEAR_MISS_MPN = "NEAR_MISS_MPN"
    """A one-character mutation of a known part number."""

    DESCRIPTION_MPN_CONFLICT = "DESCRIPTION_MPN_CONFLICT"
    """Part number and description name different products."""

    PARTIAL_MPN = "PARTIAL_MPN"
    """Truncated or incomplete part number."""

    PUNCTUATION_VARIANT = "PUNCTUATION_VARIANT"
    """A formatting variant of a known part number (case, separators)."""

    ACCESSORY_CONFUSION = "ACCESSORY_CONFUSION"
    """An accessory for a product, which must not become the product."""

    AMBIGUOUS_DESCRIPTION = "AMBIGUOUS_DESCRIPTION"
    """A description that plausibly refers to several products."""

    UNKNOWN_PRODUCT = "UNKNOWN_PRODUCT"
    """A fictitious or intentionally unverifiable identity."""

    CONFLICTING_BRAND = "CONFLICTING_BRAND"
    """Brand information pointing in incompatible directions."""


# The adversarial coverage the synthetic corpus must keep. A benchmark that
# quietly loses a challenge class stops measuring the failure it was built for,
# so the set is named here and asserted by the tests.
#
# It is deliberately *not* enforced by the corpus validator: the validator must
# be able to validate any corpus, including a single file or a subset, and a
# coverage rule would make that impossible.
REQUIRED_SYNTHETIC_CHALLENGE_TAGS = frozenset(ChallengeTag)


class ProvenanceKind(str, Enum):
    """Where a case's expected truth comes from."""

    MANUFACTURER = "MANUFACTURER"
    """A manufacturer-controlled source (product page, datasheet, ordering info)."""

    SYNTHETIC_CONSTRUCTION = "SYNTHETIC_CONSTRUCTION"
    """The case was constructed for evaluation. It has no external source.

    Synthetic cases must never carry source-shaped provenance: a fabricated
    citation is worse than none, because a later reviewer would trust it.
    """


# Provenance kinds that may back a REAL_VERIFIED expectation. Only
# manufacturer-controlled sources qualify today. Marketplace, reseller,
# aggregator, and model-generated claims are not authoritative for identity,
# and admitting another kind is a deliberate decision for a later phase — not
# something to widen in passing.
AUTHORITATIVE_PROVENANCE_KINDS = frozenset({ProvenanceKind.MANUFACTURER})
