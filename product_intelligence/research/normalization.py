"""Deterministic listing normalization (PRODUCT-INTEL.3B).

One pure function of one raw observation:

```text
ListingObservation  ->  normalize_listing_observation()  ->  NormalizedListingObservation
```

3A answered "what did the page publish?" and stored the answer as text,
deliberately uninterpreted (`research/listings.py`, `research/extraction.py`).
3B answers a narrower question about that same text: **can this raw value
become a deterministic, comparable representation without guessing?** Where
the answer is no, normalization abstains and records why — it never fabricates
a number, a currency, a stock status, or a condition it cannot support.

What normalization deliberately is not
---------------------------------------

**It is not acceptance.** There is no `accepted` field, no `valid_listing`
flag, no `identity_match`, no confidence, and nothing that says this
observation should be used for a price. That is 3C's decision, made with its
own evidence about the *product*, not this module's evidence about the
*commercial attributes* of one listing. A normalized price does not imply a
valid listing: a listing can normalize perfectly and still be about the wrong
product.

**It is not aggregation.** No min, max, median, average, market range, or
outlier judgement. 3B transforms one observation at a time; 4A counts and
compares many.

**It is not currency conversion.** Normalizing currency means recording that
an amount is in EUR in one consistent representation — never converting EUR to
USD. No exchange rate, live or hardcoded, exists anywhere in this module.

**It does not discard raw evidence.** Every `NormalizedListingObservation`
carries the exact `ListingObservation` it was built from, so a reviewer can
always trace a normalized value back to the raw text that produced it — or
back to the raw text that a normalizer correctly refused to convert.

Why abstention is a first-class outcome
----------------------------------------

Real evidence from 3A's recorded fixtures already makes the case:
`price_text="undefined"` (a failed template, published as structured data),
`price_text="1055.85"` beside a sibling page's `"1,055.85"` (the same money,
two representations), a price with `currency_text=None` (no currency anywhere
on the page), and `availability_text="false"` (no `schema.org` vocabulary
term, and not evidence that the item is out of stock). Converting any of these
with a guess would manufacture certainty the page never published. Recording
`None` plus a `NormalizationIssue` keeps the failure visible and reviewable
instead of silently absent.

Price and currency evidence
-----------------------------

`price_amount` and `currency_code` remain **independently** representable —
either, both, or neither may be present on a given result, and that is
unchanged by anything below. Independent does not mean that one source's
evidence can silently overrule another's, though: raw `price_text` sometimes
carries an unambiguous currency of its own (`"EUR 100"`, `"100 EUR"`,
`"€100"`), and that is real currency evidence, not just a number to strip a
symbol from. It is reconciled against the separately published
`currency_text` conservatively: if only one source names a currency, that
currency is used; if both name the *same* currency, that currency is used; if
they name *different* currencies, neither is chosen — `currency_code` stays
`None` and a `CONFLICTING_CURRENCY` issue records the disagreement, without
discarding an otherwise-valid `price_amount`. `$` and `¥` still never resolve
to a currency by themselves, embedded or not, for the reason `_normalize_currency`
already states: each prices several live currencies. A price carrying a
currency decoration on *both* sides (`"EUR 100 USD"`, `"$100 EUR"`) is never
treated as a clean amount, agreeing or not — accepting it would mean either
silently picking a side or silently declaring an agreement the text does not
actually establish structurally.

Quantity and pack size
-----------------------

The roadmap describes 3B eventually normalizing quantity, pack size, and unit
price. `ListingObservation` (3A) carries no raw `quantity_text` or
`pack_size_text` field, and an audit of every recorded real fixture
(`tests/fixtures/pages/`) found no structured field on any of them whose
semantics mean "this offer sells N units for this price" — no inventory count,
minimum-order quantity, or capacity figure is pack size, and none of the five
fixtures publishes anything else in that shape either. Inventing a field from
title text would be exactly the guess this phase exists to refuse.

Per the phase instructions, that absence is not a blocker and is not solved by
guessing: this module normalizes no quantity, no pack size, and computes no
unit price, and carries no fields for them. The finding is recorded here, in
the phase decision log, and in the 3B completion report, so 3C is not
surprised by it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum

from product_intelligence.research.listings import ListingObservation


class NormalizationIssueCode(str, Enum):
    """Why one field of an observation could not be normalized.

    Small and deliberately not exhaustive: a code exists only because this
    module produces it. `INVALID_QUANTITY`, `INVALID_PACK_SIZE`, and
    `UNIT_PRICE_NOT_COMPUTABLE` are not members — nothing in this module
    computes a quantity, a pack size, or a unit price, because no raw evidence
    for any of them exists yet (see the module docstring). A vocabulary member
    nothing produces would be a placeholder for unbuilt behaviour, which
    `research/listings.py` already establishes is not how this codebase
    grows a vocabulary.
    """

    INVALID_PRICE = "INVALID_PRICE"
    """The text does not represent a single amount at all — no number, or a
    number written in a shape this parser cannot read as one (mismatched or
    absent grouping, a decimal separator this parser refuses to guess at)."""

    AMBIGUOUS_PRICE = "AMBIGUOUS_PRICE"
    """The text plausibly names more than one amount, or names an amount that
    is not this listing's price — a range, two prices, a discount, or a
    recurring financing payment."""

    UNRECOGNIZED_CURRENCY = "UNRECOGNIZED_CURRENCY"
    """The text is not one of the small set of currency codes or symbols this
    module maps conservatively."""

    CONFLICTING_CURRENCY = "CONFLICTING_CURRENCY"
    """An unambiguous currency embedded in `price_text` (e.g. `"EUR 100"`,
    `"£100"`) and the separately published `currency_text` name two
    different currencies. Neither is chosen by guessing; `currency_code`
    stays `None`."""

    UNRECOGNIZED_AVAILABILITY = "UNRECOGNIZED_AVAILABILITY"
    """The text is not a recognized `schema.org` availability value or one of
    the plain-text spellings this module maps conservatively."""

    UNRECOGNIZED_CONDITION = "UNRECOGNIZED_CONDITION"
    """The text is not a recognized `schema.org` condition value or one of the
    plain-text spellings this module maps conservatively."""


@dataclass(frozen=True)
class NormalizationIssue:
    """One field of one observation that could not be normalized, and why.

    This explains only *normalization* — why raw text did not become a
    normalized value. It is never a judgement about the listing itself: no
    product-identity reason, no acceptance/rejection reason, and no
    confidence. Those are 3C's vocabulary, not this one's.
    """

    field: str
    code: NormalizationIssueCode
    raw_value: str
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.field, str) or not self.field.strip():
            raise ValueError("field is required")
        if not isinstance(self.code, NormalizationIssueCode):
            raise TypeError(
                "code must be a NormalizationIssueCode, got "
                f"{type(self.code).__name__}"
            )
        if not isinstance(self.raw_value, str):
            raise TypeError(
                f"raw_value must be a string, got {type(self.raw_value).__name__}"
            )
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("reason is required")


class NormalizedAvailability(str, Enum):
    """A small controlled availability vocabulary, independent of any one
    source's spelling.

    `UNKNOWN` is the correct answer whenever the raw text is absent or is not
    confidently one of the mapped spellings below — including
    `availability_text="false"`, a real value from a recorded fixture that is
    no `schema.org` term and is not evidence of being out of stock. Guessing
    it into `OUT_OF_STOCK` would be exactly the fabricated certainty this
    phase exists to avoid.
    """

    IN_STOCK = "IN_STOCK"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    PREORDER = "PREORDER"
    BACKORDER = "BACKORDER"
    LIMITED = "LIMITED"
    DISCONTINUED = "DISCONTINUED"
    UNKNOWN = "UNKNOWN"


class NormalizedCondition(str, Enum):
    """A small controlled condition vocabulary.

    `UNKNOWN` covers everything not confidently mapped, including marketing
    prose such as `"like new"` or `"open box"` — neither is classified without
    a deliberate, tested policy, which does not exist yet.
    """

    NEW = "NEW"
    USED = "USED"
    REFURBISHED = "REFURBISHED"
    DAMAGED = "DAMAGED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class NormalizedListingObservation:
    """One `ListingObservation`, with its commercial attributes normalized.

    `observation` is the exact raw `ListingObservation` this was built from —
    never a copy, never re-extracted. A reviewer can always get from a
    normalized field back to the raw text that produced it, including when
    that raw text produced nothing: `price_amount` may be `None` while
    `observation.price_text` is `"undefined"`, and `normalization_issues`
    explains the gap.

    Deliberately absent: any acceptance/rejection field, any identity or
    match field, any confidence, any aggregate statistic, any quantity, pack
    size, or unit price (see the module docstring), and any currency
    conversion.
    """

    observation: ListingObservation
    price_amount: Decimal | None
    currency_code: str | None
    availability: NormalizedAvailability
    condition: NormalizedCondition
    seller_name: str | None
    normalization_issues: tuple[NormalizationIssue, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.observation, ListingObservation):
            raise TypeError(
                "observation must be a ListingObservation, got "
                f"{type(self.observation).__name__}"
            )
        if self.price_amount is not None and not isinstance(self.price_amount, Decimal):
            raise TypeError(
                "price_amount must be a Decimal or None, got "
                f"{type(self.price_amount).__name__}; money is never a float here"
            )
        if self.currency_code is not None and not isinstance(self.currency_code, str):
            raise TypeError(
                "currency_code must be a string or None, got "
                f"{type(self.currency_code).__name__}"
            )
        if self.currency_code is not None and self.currency_code not in _KNOWN_CURRENCY_CODES:
            # Referenced lazily: by the time any instance is constructed, the
            # module has finished executing and the constant exists, even
            # though it is defined later in this file, alongside the rest of
            # the price/currency logic it belongs with.
            raise ValueError(
                "currency_code must be one of the codes this module can "
                f"produce, or None; got {self.currency_code!r}. This module "
                "never invents a currency code that its own normalization "
                "logic could not have produced."
            )
        if not isinstance(self.availability, NormalizedAvailability):
            raise TypeError(
                "availability must be a NormalizedAvailability, got "
                f"{type(self.availability).__name__}"
            )
        if not isinstance(self.condition, NormalizedCondition):
            raise TypeError(
                "condition must be a NormalizedCondition, got "
                f"{type(self.condition).__name__}"
            )
        if self.seller_name is not None and not isinstance(self.seller_name, str):
            raise TypeError(
                "seller_name must be a string or None, got "
                f"{type(self.seller_name).__name__}"
            )
        if not isinstance(self.normalization_issues, tuple) or not all(
            isinstance(issue, NormalizationIssue) for issue in self.normalization_issues
        ):
            raise TypeError("normalization_issues must be a tuple of NormalizationIssue")

    @property
    def has_normalization_issues(self) -> bool:
        return bool(self.normalization_issues)


# --------------------------------------------------------------------------
# Price
# --------------------------------------------------------------------------

# Conservative: three-letter ISO 4217 codes actually exercised by this
# module's tests and by real 3A evidence, plus the handful of major-economy
# codes an evaluator would reasonably expect. Not a claim that every
# syntactically three-letter string is a currency — see `_normalize_currency`.
_KNOWN_CURRENCY_CODES: frozenset[str] = frozenset(
    {
        "USD",
        "EUR",
        "GBP",
        "JPY",
        "CAD",
        "AUD",
        "CHF",
        "CNY",
        "INR",
        "MXN",
        "BRL",
        "SEK",
        "NOK",
        "DKK",
        "NZD",
        "SGD",
        "HKD",
        "KRW",
        "ZAR",
    }
)

# Currency symbols this module will strip from a price string when locating
# the numeric amount. Stripping a symbol to find a number is not the same as
# deciding a currency from it — see `_parse_price` and `_normalize_currency`.
_CURRENCY_SYMBOLS = "$€£¥"

_CURRENCY_CODE_ALTERNATION = "|".join(sorted(_KNOWN_CURRENCY_CODES))

# A single unambiguous amount: optionally wrapped by a currency symbol or a
# known ISO code, on *one* side only, with no other characters present.
#
#     1,055.85   ->  comma-grouped, exactly three digits per group
#     1055.85    ->  no grouping
#     1200       ->  a bare integer
#     $1,055.85  ->  a leading symbol
#     EUR 1055.85 -> a leading known code
#     1055.85 EUR -> a trailing known code
#
# The prefix and suffix decoration groups are each independently optional in
# the grammar below, which lets a regex *match* a doubly-wrapped string such
# as `"EUR 100 USD"` or `"$100 EUR"` — one decoration on each side. `_parse_price`
# checks for that explicitly after a match and refuses it rather than picking
# either side's currency; see the module docstring on why an amount wrapped in
# two currency markers is never treated as a clean price/currency pair.
#
# What this deliberately does NOT accept: a second amount anywhere in the
# string, a bare '%', a unit suffix such as '/mo', or a grouping that is not
# exactly three digits per comma (`1,00,055`) — each of those fails to
# `fullmatch` and falls through to the ambiguity/invalid classification in
# `_parse_price` rather than being silently reinterpreted.
_PRICE_PATTERN = re.compile(
    rf"""
    ^
    (?:(?P<prefix_symbol>[{re.escape(_CURRENCY_SYMBOLS)}])
       |(?P<prefix_code>{_CURRENCY_CODE_ALTERNATION})\s+)?
    \s*
    (?P<amount>\d{{1,3}}(?:,\d{{3}})+(?:\.\d+)?|\d+(?:\.\d+)?)
    \s*
    (?:(?P<suffix_symbol>[{re.escape(_CURRENCY_SYMBOLS)}])
       |\s+(?P<suffix_code>{_CURRENCY_CODE_ALTERNATION}))?
    $
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Substrings whose presence means the text names something other than one
# clean purchase price — a range, a financing instalment, a discount, or a
# recurring charge — even when only one number appears syntactically (`"$33/mo"`
# has one number and is still not this product's price). Checked against the
# lowercased text.
_AMBIGUOUS_PRICE_MARKERS: tuple[str, ...] = (
    "from ",
    "as low as",
    "starting at",
    "save",
    "you save",
    "% off",
    "off%",
    "/mo",
    "/yr",
    "/wk",
    "per month",
    "per year",
    "per week",
    "a month",
    "a year",
    " to ",
)

# A rough amount-shaped token, used only to *count* how many amounts appear in
# text that already failed the strict single-amount grammar above. Two or more
# is treated as a range or a list of prices rather than one price.
_ROUGH_AMOUNT_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")


@dataclass(frozen=True)
class _ParsedPrice:
    """Private result of parsing raw price text.

    Not part of the public contract: `normalize_listing_observation` reads
    `amount` and `embedded_currency` and folds `issue` into
    `normalization_issues` itself. Kept separate from `NormalizedListingObservation`
    because an embedded currency is an intermediate fact used for
    reconciliation (see `_reconcile_currency`), not a field of the public
    result.
    """

    amount: Decimal | None
    embedded_currency: str | None
    issue: NormalizationIssue | None


def _embedded_currency_from_decoration(
    symbol: str | None, code: str | None
) -> str | None:
    """The unambiguous currency named by one matched decoration, if any.

    An explicit three-letter code is unambiguous by definition — it is
    already a currency code, not a guess. `€` and `£` are unambiguous
    symbols. `$` and `¥` are present in the grammar (they still locate the
    amount) but never resolve to a currency here, for the same reason
    `_normalize_currency` never maps them: each prices several live
    currencies.
    """
    if code is not None:
        return code.upper()
    if symbol is not None and symbol in _UNAMBIGUOUS_CURRENCY_SYMBOLS:
        return _UNAMBIGUOUS_CURRENCY_SYMBOLS[symbol]
    return None


def _parse_price(raw_value: str) -> _ParsedPrice:
    """Parse unambiguous price text into a `Decimal`, or abstain with a reason.

    Never guesses between a US-style and a European-style number: a comma
    that is not grouping digits by exactly three, or a period used as a
    thousands separator, fails to match and is refused rather than
    reinterpreted.

    An explicit, unambiguous currency decorating the amount (`"EUR 100"`,
    `"100 EUR"`, `"€100"`) is reported back as `embedded_currency` so the
    caller can reconcile it against a separately published `currency_text`.
    A price wrapped in decoration on *both* sides (`"EUR 100 USD"`, `"$100
    EUR"`) is never treated as a clean amount, whether or not the two
    decorations agree — see the module docstring.
    """
    text = raw_value.strip()

    match = _PRICE_PATTERN.match(text)
    if match:
        has_prefix = (
            match.group("prefix_symbol") is not None
            or match.group("prefix_code") is not None
        )
        has_suffix = (
            match.group("suffix_symbol") is not None
            or match.group("suffix_code") is not None
        )
        if has_prefix and has_suffix:
            return _ParsedPrice(
                amount=None,
                embedded_currency=None,
                issue=NormalizationIssue(
                    field="price",
                    code=NormalizationIssueCode.AMBIGUOUS_PRICE,
                    raw_value=raw_value,
                    reason=(
                        "the text carries a currency decoration on both sides "
                        "of the amount (for example a leading code and a "
                        "trailing symbol); no single amount/currency pair is "
                        "chosen by guessing, even when the two decorations "
                        "appear to agree"
                    ),
                ),
            )
        try:
            amount = Decimal(match.group("amount").replace(",", ""))
        except InvalidOperation:  # pragma: no cover - the grammar above already guards this
            pass
        else:
            embedded_currency = _embedded_currency_from_decoration(
                match.group("prefix_symbol") or match.group("suffix_symbol"),
                match.group("prefix_code") or match.group("suffix_code"),
            )
            return _ParsedPrice(
                amount=amount, embedded_currency=embedded_currency, issue=None
            )

    lowered = text.lower()
    is_ambiguous = any(marker in lowered for marker in _AMBIGUOUS_PRICE_MARKERS)
    if not is_ambiguous:
        amounts_found = _ROUGH_AMOUNT_RE.findall(text)
        is_ambiguous = len(amounts_found) >= 2

    if is_ambiguous:
        return _ParsedPrice(
            amount=None,
            embedded_currency=None,
            issue=NormalizationIssue(
                field="price",
                code=NormalizationIssueCode.AMBIGUOUS_PRICE,
                raw_value=raw_value,
                reason=(
                    "the text plausibly names more than one amount, or an "
                    "amount that is not a single purchase price (a range, a "
                    "discount, or a recurring payment); no amount is chosen "
                    "by guessing"
                ),
            ),
        )

    return _ParsedPrice(
        amount=None,
        embedded_currency=None,
        issue=NormalizationIssue(
            field="price",
            code=NormalizationIssueCode.INVALID_PRICE,
            raw_value=raw_value,
            reason="the text does not represent a single unambiguous amount",
        ),
    )


# --------------------------------------------------------------------------
# Currency
# --------------------------------------------------------------------------

# Symbols mapped to a currency only where the symbol is not shared by several
# live currencies. `$` and `¥` are deliberately absent — both are used by
# multiple currencies and mapping either to one guess would be exactly the
# inference §8/§9 of the phase instructions forbid.
_UNAMBIGUOUS_CURRENCY_SYMBOLS: dict[str, str] = {
    "€": "EUR",
    "£": "GBP",
}


def _normalize_currency(raw_value: str) -> tuple[str | None, NormalizationIssue | None]:
    text = raw_value.strip()

    if text in _UNAMBIGUOUS_CURRENCY_SYMBOLS:
        return _UNAMBIGUOUS_CURRENCY_SYMBOLS[text], None

    if re.fullmatch(r"[A-Za-z]{3}", text) and text.upper() in _KNOWN_CURRENCY_CODES:
        return text.upper(), None

    return None, NormalizationIssue(
        field="currency",
        code=NormalizationIssueCode.UNRECOGNIZED_CURRENCY,
        raw_value=raw_value,
        reason=(
            "not one of the currency codes or unambiguous symbols this module "
            "maps conservatively; a symbol such as '$' is not globally unique "
            "and is never guessed at"
        ),
    )


def _reconcile_currency(
    embedded_currency: str | None, currency_from_text: str | None
) -> tuple[str | None, NormalizationIssue | None]:
    """Combine an amount's embedded currency with the separately published
    `currency_text`, conservatively.

    Price and currency remain independently representable — either, both, or
    neither may be present, and that is unchanged by this reconciliation. What
    changes is that an unambiguous currency embedded in `price_text` is now
    real evidence, and evidence is never silently discarded: if both sources
    are present and agree, that currency is used; if they disagree, the
    disagreement itself is recorded and `currency_code` stays `None` rather
    than one side winning arbitrarily.
    """
    if embedded_currency is not None and currency_from_text is not None:
        if embedded_currency == currency_from_text:
            return embedded_currency, None
        return None, NormalizationIssue(
            field="currency",
            code=NormalizationIssueCode.CONFLICTING_CURRENCY,
            raw_value=f"price_text implies {embedded_currency!r}, currency_text is {currency_from_text!r}",
            reason=(
                "the currency embedded in price_text and the separately "
                "published currency_text name two different currencies; "
                "neither is chosen by guessing"
            ),
        )

    if embedded_currency is not None:
        return embedded_currency, None

    return currency_from_text, None


# --------------------------------------------------------------------------
# Availability
# --------------------------------------------------------------------------

_SCHEMA_ORG_PREFIXES: tuple[str, ...] = (
    "https://schema.org/",
    "http://schema.org/",
    "schema.org/",
)


def _strip_schema_org_prefix(text: str) -> str:
    lowered = text.lower()
    for prefix in _SCHEMA_ORG_PREFIXES:
        if lowered.startswith(prefix):
            return text[len(prefix) :]
    return text


# Deliberately excludes `"true"` / `"false"` — a real recorded fixture
# publishes `availability_text="false"`, which is no `schema.org` term and is
# not evidence of any particular stock state.
_AVAILABILITY_MAP: dict[str, NormalizedAvailability] = {
    "instock": NormalizedAvailability.IN_STOCK,
    "in stock": NormalizedAvailability.IN_STOCK,
    "instoreonly": NormalizedAvailability.IN_STOCK,
    "onlineonly": NormalizedAvailability.IN_STOCK,
    "outofstock": NormalizedAvailability.OUT_OF_STOCK,
    "out of stock": NormalizedAvailability.OUT_OF_STOCK,
    "soldout": NormalizedAvailability.OUT_OF_STOCK,
    "sold out": NormalizedAvailability.OUT_OF_STOCK,
    "preorder": NormalizedAvailability.PREORDER,
    "pre-order": NormalizedAvailability.PREORDER,
    "pre order": NormalizedAvailability.PREORDER,
    "presale": NormalizedAvailability.PREORDER,
    "backorder": NormalizedAvailability.BACKORDER,
    "back-order": NormalizedAvailability.BACKORDER,
    "back order": NormalizedAvailability.BACKORDER,
    "limitedavailability": NormalizedAvailability.LIMITED,
    "limited availability": NormalizedAvailability.LIMITED,
    "discontinued": NormalizedAvailability.DISCONTINUED,
}


def _normalize_availability(
    raw_value: str,
) -> tuple[NormalizedAvailability, NormalizationIssue | None]:
    stripped = _strip_schema_org_prefix(raw_value.strip())
    key = stripped.strip().lower()

    mapped = _AVAILABILITY_MAP.get(key)
    if mapped is not None:
        return mapped, None

    return NormalizedAvailability.UNKNOWN, NormalizationIssue(
        field="availability",
        code=NormalizationIssueCode.UNRECOGNIZED_AVAILABILITY,
        raw_value=raw_value,
        reason=(
            "not a recognized schema.org availability value or a conservative "
            "plain-text spelling; unrecognized text is never guessed into a "
            "confident stock state"
        ),
    )


# --------------------------------------------------------------------------
# Condition
# --------------------------------------------------------------------------

_CONDITION_MAP: dict[str, NormalizedCondition] = {
    "newcondition": NormalizedCondition.NEW,
    "new": NormalizedCondition.NEW,
    "usedcondition": NormalizedCondition.USED,
    "used": NormalizedCondition.USED,
    "refurbishedcondition": NormalizedCondition.REFURBISHED,
    "refurbished": NormalizedCondition.REFURBISHED,
    "refurb": NormalizedCondition.REFURBISHED,
    "damagedcondition": NormalizedCondition.DAMAGED,
    "damaged": NormalizedCondition.DAMAGED,
}


def _normalize_condition(
    raw_value: str,
) -> tuple[NormalizedCondition, NormalizationIssue | None]:
    stripped = _strip_schema_org_prefix(raw_value.strip())
    key = stripped.strip().lower()

    mapped = _CONDITION_MAP.get(key)
    if mapped is not None:
        return mapped, None

    return NormalizedCondition.UNKNOWN, NormalizationIssue(
        field="condition",
        code=NormalizationIssueCode.UNRECOGNIZED_CONDITION,
        raw_value=raw_value,
        reason=(
            "not a recognized schema.org condition value or a conservative "
            "plain-text spelling; marketing prose such as 'like new' or "
            "'open box' is never classified without a deliberate, tested policy"
        ),
    )


# --------------------------------------------------------------------------
# Seller
# --------------------------------------------------------------------------

_INTERNAL_WHITESPACE_RUN = re.compile(r"\s+")


def _normalize_seller(raw_value: str) -> str | None:
    """Low-risk representation cleanup only — never entity resolution.

    Surrounding whitespace is removed and an internal whitespace run collapses
    to one space. Nothing else changes: no case folding, no punctuation
    removal, and no decision that two spellings name the same seller
    (`"Amazon.com"` and `"Amazon"` stay two different strings here).
    """
    cleaned = _INTERNAL_WHITESPACE_RUN.sub(" ", raw_value.strip()).strip()
    return cleaned or None


# --------------------------------------------------------------------------
# Public entry points
# --------------------------------------------------------------------------


def normalize_listing_observation(
    observation: ListingObservation,
) -> NormalizedListingObservation:
    """Normalize one raw observation's commercial attributes.

    Pure and deterministic: the same `ListingObservation` always produces the
    same `NormalizedListingObservation`. No I/O, no Django, no provider call,
    no clock, no environment access, and no identity comparison — this
    function normalizes representation, and decides nothing about whether the
    listing belongs to any requested product.
    """
    if not isinstance(observation, ListingObservation):
        raise TypeError(
            f"observation must be a ListingObservation, got {type(observation).__name__}"
        )

    issues: list[NormalizationIssue] = []

    price_amount: Decimal | None = None
    embedded_currency: str | None = None
    if observation.price_text is not None:
        parsed_price = _parse_price(observation.price_text)
        price_amount = parsed_price.amount
        embedded_currency = parsed_price.embedded_currency
        if parsed_price.issue is not None:
            issues.append(parsed_price.issue)

    currency_from_text: str | None = None
    if observation.currency_text is not None:
        currency_from_text, currency_issue = _normalize_currency(observation.currency_text)
        if currency_issue is not None:
            issues.append(currency_issue)

    # Reconciled rather than taken from currency_text alone: an unambiguous
    # currency embedded in price_text (e.g. "EUR 100") is real evidence too,
    # and evidence that disagrees with currency_text must not be silently
    # discarded in either direction.
    currency_code, conflict_issue = _reconcile_currency(
        embedded_currency, currency_from_text
    )
    if conflict_issue is not None:
        issues.append(conflict_issue)

    availability = NormalizedAvailability.UNKNOWN
    if observation.availability_text is not None:
        availability, availability_issue = _normalize_availability(
            observation.availability_text
        )
        if availability_issue is not None:
            issues.append(availability_issue)

    condition = NormalizedCondition.UNKNOWN
    if observation.condition_text is not None:
        condition, condition_issue = _normalize_condition(observation.condition_text)
        if condition_issue is not None:
            issues.append(condition_issue)

    seller_name: str | None = None
    if observation.seller_text is not None:
        seller_name = _normalize_seller(observation.seller_text)

    return NormalizedListingObservation(
        observation=observation,
        price_amount=price_amount,
        currency_code=currency_code,
        availability=availability,
        condition=condition,
        seller_name=seller_name,
        normalization_issues=tuple(issues),
    )


def normalize_listing_observations(
    observations,
) -> tuple[NormalizedListingObservation, ...]:
    """Normalize an iterable of raw observations, one at a time.

    Not orchestration: no fetching, no searching, no persistence. Each
    observation is normalized independently — this is a small convenience
    wrapper around `normalize_listing_observation`, not an aggregation step.
    """
    return tuple(normalize_listing_observation(observation) for observation in observations)
