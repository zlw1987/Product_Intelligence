"""The raw listing observation contract (PRODUCT-INTEL.3A).

One immutable record of **what a page appears to publish about one offer**,
before anything is normalized, compared, accepted, or counted.

```text
FetchedPage  ->  extract_listing_observations()  ->  ListingObservation, ...
```

Every field except `source_url` and `extraction_method` is optional raw text,
kept as the page wrote it.

Why every value stays text
--------------------------

The temptation at this boundary is to convert on the way in — a `Decimal` for
the price, an enum for the condition, a `bool` for availability — because the
page evidently means a number and a state. Three real pages sampled while
building this phase say otherwise:

* one publishes `"price": "undefined"` inside an otherwise well-formed
  `schema.org` `Offer`. It is a template that failed, and it is *published
  structured data*. `Decimal("undefined")` raises; a converting extractor would
  either crash on a live page or silently drop the whole offer;
* one publishes `"1055.85"` in JSON-LD and `"1,055.85"` in an OpenGraph meta
  tag — the same money, written two ways, on one page;
* one publishes a price with **no currency anywhere on the page**, and another
  publishes `availability` as the string `"false"` rather than any `schema.org`
  vocabulary term.

Those are not exotic. They are what four ordinary retail pages did on the first
day anyone looked. Converting here would mean each of them either fails or is
guessed at inside a parser, with no place to record which. Keeping them as text
moves the decision to 3B, where "unparseable price" and "no currency" are
outcomes with reasons attached rather than exceptions in the middle of a fetch.

What a `ListingObservation` deliberately is not
-----------------------------------------------

**It is not a price.** `price_text` is characters a page published in a price
position. It is not a number, not a currency amount, not a unit price, not
this product's market price, and not comparable with another observation.
Arithmetic on it is 4A's, after 3B has made it a number and 3C has decided the
listing is even about the right product.

**It is not an identity claim.** `manufacturer_part_number_text` is what the
page published in an MPN field, character for character — one real page writes
it as `mpn:MZ-QL23T800`, prefix included, and that prefix is preserved rather
than stripped, because stripping it is a normalization rule and this is not the
layer that makes those. Nothing here compares it to a request. The 2A
comparator exists and is not called from extraction: an extractor that decided
identity would be judging its own evidence.

**It is not accepted.** There is no `accepted` flag, no rejection reason, no
score, and no confidence. Accept/reject with recorded reasons is 3C, and a
field for it here would be filled in by whoever got there first.

**It is not deduplicated.** Two observations from one page are two
observations. A page publishing several offers really is publishing several
offers, and collapsing them would silently reduce a count 4A depends on.

**It is not evidence storage.** Nothing here is persisted, and this is not
`EvidenceReference` — that domain contract carries an accept/reject decision and
a confidence level, which is precisely what a raw observation must not have yet.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from enum import Enum


class ExtractionMethod(Enum):
    """How an observation was obtained from a document.

    Provenance, not trustworthiness. A reviewer must be able to see which
    mechanism produced a field, and that is all this says: JSON-LD is not
    "reliable" and meta is not "weak". A price in a `schema.org` `Offer` is
    still one page's claim, and one of the real pages behind this phase proves
    it by publishing the literal string `undefined` there.

    Two members, because two mechanisms are implemented. A third, for a
    narrowly scoped per-source strategy, is described in the plan document and
    is deliberately not declared here: a vocabulary member nothing produces is a
    placeholder for unbuilt behaviour.
    """

    JSON_LD = "JSON_LD"
    META = "META"


@dataclass(frozen=True)
class ListingObservation:
    """One offer as one page published it, uninterpreted.

    All text fields are **untrusted external content** (§19). They are data to
    be analysed, never instructions to be followed — one real page sampled for
    this phase publishes structured data whose description tells an automated
    reader to go use a different service instead, which is exactly the shape
    that rule exists for.

    `source_url` is the page the observation came from and is required: an
    observation nobody can re-open is not evidence. It is kept as the caller
    supplied it — normally a `FetchedPage.final_url`, which is where the
    document actually came from rather than where something claimed it was.

    `offer_url_text` is a URL the *offer itself* published, when it published
    one. It is raw text and is not validated as a URL, because it is an
    observation and one real page writes it as a relative path. It matters
    because a page can carry several offers for several variants at several
    addresses: without it, two observations from one page are indistinguishable
    in their traceability.

    `extraction_method` records the mechanism, per `ExtractionMethod`.

    `raw_reference` preserves the structured node the observation came from, so
    a reviewer can check the mapping against the source. It follows AD-040: it
    is an opaque string, kept for humans and tests, and no business rule may
    parse it. Fields this contract deliberately does not carry — a GTIN, a
    category, a description, a price-valid-until date — survive in here, which
    is why the contract can stay small without discarding evidence.

    Deliberately absent: any numeric price, any currency enum, any quantity,
    pack size, or unit price, any condition or availability vocabulary, any
    normalized seller, any accept/reject decision, any score, and any
    confidence. Each belongs to a later phase that makes the decision with
    rules and records a reason (3B, 3C, 4A).
    """

    source_url: str
    extraction_method: ExtractionMethod
    product_title: str | None = None
    manufacturer_part_number_text: str | None = None
    sku_text: str | None = None
    brand_text: str | None = None
    price_text: str | None = None
    currency_text: str | None = None
    availability_text: str | None = None
    condition_text: str | None = None
    seller_text: str | None = None
    offer_url_text: str | None = None
    raw_reference: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source_url, str):
            raise TypeError(
                f"source_url must be a string, got {type(self.source_url).__name__}"
            )
        source_url = self.source_url.strip()
        if not source_url:
            raise ValueError(
                "source_url is required; an observation nobody can re-open is not "
                "evidence"
            )
        object.__setattr__(self, "source_url", source_url)

        if not isinstance(self.extraction_method, ExtractionMethod):
            raise TypeError(
                "extraction_method must be an ExtractionMethod, got "
                f"{type(self.extraction_method).__name__}"
            )

        for field in fields(self):
            if field.name in ("source_url", "extraction_method", "raw_reference"):
                continue
            value = getattr(self, field.name)
            if value is None:
                continue
            if not isinstance(value, str):
                raise TypeError(
                    f"{field.name} must be a string or None, got "
                    f"{type(value).__name__}; a page observation is text, and "
                    "converting it is a later phase's decision"
                )
            # Surrounding whitespace is removed so that "the page said nothing
            # here" has one representation. The *interior* is never touched:
            # `"1,055.85"`, `"mpn:MZ-QL23T800"`, and `"undefined"` are all
            # preserved exactly, because they are what has to be reviewed.
            object.__setattr__(self, field.name, value.strip() or None)

        if self.raw_reference is not None and not isinstance(self.raw_reference, str):
            raise TypeError(
                "raw_reference must be a string or None, got "
                f"{type(self.raw_reference).__name__}; preserved material is an "
                "opaque reference, not a structure for business logic to read"
            )

    @property
    def has_price_text(self) -> bool:
        """Whether the page published something in a price position.

        Not whether a price is known. `"undefined"` and `"Call for pricing"` both
        make this `True`, and both are the reason 3B exists.
        """
        return self.price_text is not None

    @property
    def has_published_part_number(self) -> bool:
        """Whether the page published an MPN field — not whether it matches."""
        return self.manufacturer_part_number_text is not None
