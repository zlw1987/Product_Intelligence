"""Deterministic raw listing extraction (PRODUCT-INTEL.3A).

One pure function of a document and the URL it came from:

```text
extract_listing_observations(document, source_url=...) -> ListingObservation, ...
```

It fetches nothing. The document arrives as a string — normally a
`FetchedPage.body_text` — and the caller supplies the URL, because a research
primitive does not open connections and does not generate provenance. The
extraction layer and the fetch layer therefore import neither each other nor a
shared type: they meet in whatever code holds both, which is what keeps the
research core testable with a string literal and free of a network stack.

What it will and will not read
------------------------------

**Structured offer data, plus bounded labeled identity enrichment.** The
offer/price record still comes from exactly the same two mechanisms, in order:

1. `application/ld+json` blocks — `schema.org` `Product` nodes and the
   `Offer` / `AggregateOffer` attached to them;
2. flat `<meta>` tags — the `name="price"` / `name="mpn"` / `name="sku"`
   family and the OpenGraph `og:price:amount` / `og:price:currency` pair.

After one of those mechanisms has produced an observation, a deliberately
narrow identity-only enrichment may fill a *missing* manufacturer part number
from an exact visible field label such as `Model #:` or
`Manufacturer Part Number:`. It never creates a listing by itself, never
overwrites a structured MPN, never reads a visible price, and fails closed when
authoritative visible labels disagree. Retailer identifiers such as `Item #`
and `SKU` are explicitly not manufacturer-part-number labels.

Both were added because sampled real pages publish them. The meta mechanism in
particular is not speculative: one retailer page in the recorded fixtures
carries **no JSON-LD at all** and publishes its entire product record —
`mpn`, `sku`, `brand`, `price`, `availability` — in flat meta tags. Without
that path, a page that plainly states its part number and its price would
produce nothing.

**Never arbitrary rendered price text.** The bounded identity-label exception
above does not widen price extraction: there is deliberately no scan of visible
HTML for currency-shaped substrings, and there never may be. One sampled retail
page contains fourteen distinct dollar amounts in its markup: a free-shipping
threshold, a financing minimum, a rewards balance, several unrelated
recommended products, and — somewhere among them — the actual price of the
product the page is about. First-match, lowest-match, and largest-match rules
each pick a wrong number from that page, and each does it with total
confidence. A price this system reports has to trace to a field a page
deliberately published as the price, or it does not exist.

The same reasoning rules out reading a price out of a search snippet: the
recorded search fixture behind this phase contains snippets reading
`"$2,135.00 $2,700.00 You Save: $565.00"` and
`"$2,145.00 As low as $102.98/mo"`. A current price, a struck-through list
price, a saving, and a monthly payment instalment are four different numbers,
and nothing in the text says which is which.

**Never a number.** Values are lifted out as the source wrote them. JSON is
parsed with `parse_float=str` and `parse_int=str`, so a price written as the
JSON number `1055.85` arrives as the text `"1055.85"` rather than as a float
that has already lost its representation. Nothing here converts, rounds,
strips a currency symbol, or does arithmetic — that is 3B.

**Never a decision.** No listing is accepted or rejected, no part number is
compared (the 2A comparator is not called from here), no observation is
deduplicated, no offer is ranked, and no confidence is assigned.

Precedence, and why meta does not simply run as well
-----------------------------------------------------

Meta extraction runs **only when JSON-LD produced no observation for the
document**. One sampled page publishes the same single offer in both places —
`"1055.85"` in a JSON-LD `Offer` and `"1,055.85"` in `og:price:amount`.
Emitting both would turn one offer into two observations of one page, and 4A
counts observations. One document, one structured offer mechanism: the richer
structured source when it exists, the flat one when it does not. The bounded
visible-label pass is enrichment of a missing identity field on those same
observations; it is not a third offer mechanism and cannot add an observation.

Robustness rules, each with a real reason
------------------------------------------

* A JSON-LD block that does not parse is skipped, and its siblings are
  unaffected. A single broken block on a page is common, and losing an entire
  page's data to it would be an outage caused by someone else's typo.
* A node that is not a `Product` is ignored rather than guessed at. The sampled
  pages carry `Organization`, `BreadcrumbList`, `ImageObject`, and `WebAPI`
  nodes; none of them is an offer.
* Traversal is depth-bounded. Untrusted JSON can nest arbitrarily, and a
  recursive walk over it is a stack overflow waiting for the page that supplies
  one.
* A `Product` with no offer still yields one observation. A manufacturer page
  that publishes a part number and no price is exactly the evidence a
  manufacturer page should contribute, and dropping it would leave only
  retailers.
* An `AggregateOffer` yields an observation with **no** `price_text`. It
  publishes a low and a high across several sellers, which is a range and not a
  price; picking either end would be the lowest-wins rule wearing a schema
  name. The whole node is preserved in `raw_reference` for 3B to revisit with
  its own rules.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from html.parser import HTMLParser

from product_intelligence.research.listings import ExtractionMethod, ListingObservation

#: How deep a JSON-LD structure is walked before traversal stops. Real product
#: nodes are three or four levels deep; this is far above anything legitimate
#: and far below anything that threatens the interpreter.
MAX_JSON_LD_DEPTH = 24

#: How many `ld+json` blocks one document may contribute. Sampled pages carry
#: one to three; a document offering hundreds is not a product page.
MAX_JSON_LD_BLOCKS = 50

#: `schema.org` types treated as describing a product. Compared case-insensitively
#: against the bare type name, so `https://schema.org/Product` and `Product` are
#: the same claim.
PRODUCT_TYPES: frozenset[str] = frozenset({"product", "productmodel", "individualproduct"})

#: Offer container types. `AggregateOffer` is recognized so it can be recorded
#: *without* a price — see the module docstring.
OFFER_TYPES: frozenset[str] = frozenset({"offer"})
AGGREGATE_OFFER_TYPES: frozenset[str] = frozenset({"aggregateoffer"})

#: Flat `<meta name=...>` keys observed on a real retailer page that publishes
#: no JSON-LD. Each maps to one raw observation field.
META_NAME_FIELDS: dict[str, str] = {
    "mpn": "manufacturer_part_number_text",
    "sku": "sku_text",
    "brand": "brand_text",
    "price": "price_text",
    "availability": "availability_text",
    "condition": "condition_text",
    "priceCurrency": "currency_text",
}

#: OpenGraph product keys, observed on a real storefront page. `og:price:amount`
#: is a price the page published as its price, which is the only kind this
#: module reads.
META_PROPERTY_FIELDS: dict[str, str] = {
    "og:title": "product_title",
    "og:price:amount": "price_text",
    "og:price:currency": "currency_text",
    "product:price:amount": "price_text",
    "product:price:currency": "currency_text",
    "product:retailer_part_no": "manufacturer_part_number_text",
}


#: Exact visible labels that are permitted to establish a missing manufacturer
#: part number on an observation that already exists from JSON-LD or META.
#: These are field labels, not free-text keywords. Retailer-local identifiers
#: such as "Item #" and "SKU" are intentionally absent.
_VISIBLE_MPN_LABELS: tuple[str, ...] = (
    "MPN",
    "Manufacturer Part Number",
    "Manufacturer Part #",
    "Mfr Part Number",
    "Mfr Part #",
    "Model Number",
    "Model #",
)
_VISIBLE_MPN_LABEL_KEYS = frozenset(label.casefold() for label in _VISIBLE_MPN_LABELS)
_VISIBLE_MPN_INLINE_RE = re.compile(
    r"^(?P<label>manufacturer\s+part\s+number|manufacturer\s+part\s+#|"
    r"mfr\s+part\s+number|mfr\s+part\s+#|model\s+number|model\s+#|mpn)"
    r"\s*:\s*(?P<value>.+)$",
    re.IGNORECASE,
)
_VISIBLE_MPN_VALUE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/#-]{0,127}$")
_IGNORED_VISIBLE_TEXT_TAGS = frozenset({"script", "style", "noscript", "template"})
_VOID_VISIBLE_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
})

MAX_VISIBLE_IDENTITY_ELEMENTS = 2048
MAX_VISIBLE_IDENTITY_ELEMENT_TEXT = 256
MAX_VISIBLE_IDENTITY_DEPTH = 64


@dataclass
class _VisibleTextFrame:
    """One bounded visible element under construction."""

    tag: str
    frame_id: int
    parent_id: int | None
    parts: list[str]
    text_len: int = 0


class _StructuredDataCollector(HTMLParser):
    """Collect structured data plus bounded visible identity containers.

    JSON-LD and META remain the only offer/price extraction mechanisms. Visible
    element text is retained only for exact labeled MPN recovery. The collector
    records bounded element containers and sibling relationships so a label is
    never paired with arbitrary later page text.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.json_ld_blocks: list[str] = []
        self.meta_tags: list[dict[str, str]] = []
        self.visible_identity_elements: list[tuple[int | None, str]] = []
        self._in_json_ld = False
        self._buffer: list[str] = []
        self._ignored_visible_text_depth = 0
        self._visible_frames: list[_VisibleTextFrame] = []
        self._next_visible_frame_id = 1
        self._visible_capture_disabled = False

    def _disable_visible_capture(self) -> None:
        self._visible_capture_disabled = True
        self._visible_frames.clear()
        self.visible_identity_elements.clear()

    def _append_visible_piece(self, value: str) -> None:
        if self._visible_capture_disabled or not self._visible_frames:
            return
        text = " ".join(value.split())
        if not text:
            return
        frame = self._visible_frames[-1]
        extra = len(text) + (1 if frame.parts else 0)
        if frame.text_len + extra > MAX_VISIBLE_IDENTITY_ELEMENT_TEXT:
            frame.parts.clear()
            frame.text_len = MAX_VISIBLE_IDENTITY_ELEMENT_TEXT + 1
            return
        frame.parts.append(text)
        frame.text_len += extra

    def _finalize_visible_frame(self, frame: _VisibleTextFrame) -> None:
        if self._visible_capture_disabled:
            return
        if frame.text_len > MAX_VISIBLE_IDENTITY_ELEMENT_TEXT:
            return
        text = " ".join(frame.parts).strip()
        if not text:
            return
        if len(self.visible_identity_elements) >= MAX_VISIBLE_IDENTITY_ELEMENTS:
            self._disable_visible_capture()
            return
        self.visible_identity_elements.append((frame.parent_id, text))
        self._append_visible_piece(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {name.lower(): (value or "") for name, value in attrs}

        if tag == "script":
            declared = attributes.get("type", "").split(";", 1)[0].strip().lower()
            if declared == "application/ld+json":
                self._in_json_ld = True
                self._buffer = []
            else:
                self._ignored_visible_text_depth += 1
            return

        if tag in _IGNORED_VISIBLE_TEXT_TAGS:
            self._ignored_visible_text_depth += 1
            return

        if tag == "meta":
            self.meta_tags.append(attributes)

        if (
            self._ignored_visible_text_depth
            or self._visible_capture_disabled
            or tag in _VOID_VISIBLE_TAGS
        ):
            return

        if len(self._visible_frames) >= MAX_VISIBLE_IDENTITY_DEPTH:
            self._disable_visible_capture()
            return

        parent_id = (
            self._visible_frames[-1].frame_id
            if self._visible_frames
            else None
        )
        frame = _VisibleTextFrame(
            tag=tag,
            frame_id=self._next_visible_frame_id,
            parent_id=parent_id,
            parts=[],
        )
        self._next_visible_frame_id += 1
        self._visible_frames.append(frame)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "meta":
            self.meta_tags.append(
                {name.lower(): (value or "") for name, value in attrs}
            )

    def handle_data(self, data: str) -> None:
        if self._in_json_ld:
            self._buffer.append(data)
            return
        if self._ignored_visible_text_depth == 0:
            self._append_visible_piece(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._in_json_ld:
            self._in_json_ld = False
            if len(self.json_ld_blocks) < MAX_JSON_LD_BLOCKS:
                self.json_ld_blocks.append("".join(self._buffer))
            self._buffer = []
            return

        if tag in _IGNORED_VISIBLE_TEXT_TAGS:
            if self._ignored_visible_text_depth:
                self._ignored_visible_text_depth -= 1
            return

        if (
            self._ignored_visible_text_depth
            or self._visible_capture_disabled
            or not self._visible_frames
        ):
            return

        match_index = None
        for index in range(len(self._visible_frames) - 1, -1, -1):
            if self._visible_frames[index].tag == tag:
                match_index = index
                break
        if match_index is None:
            return

        while len(self._visible_frames) > match_index:
            frame = self._visible_frames.pop()
            self._finalize_visible_frame(frame)

def _parse_document(document: str) -> _StructuredDataCollector:
    """Run the collector over untrusted markup, keeping whatever it reached.

    `HTMLParser` is lenient, but it is being handed arbitrary bytes from the
    open web. If it raises part-way through, what it already collected is still
    real and is returned: a page that breaks a parser at 90% is better evidence
    than no page at all, and the alternative is losing a valid `Product` node to
    malformed markup a thousand lines below it.
    """
    collector = _StructuredDataCollector()
    try:
        collector.feed(document)
        collector.close()
    except Exception:  # noqa: BLE001 - untrusted input; keep the partial result
        pass
    return collector


def _bounded_visible_mpn_value(value: str) -> str | None:
    """Return a visible labeled identifier only when it fits the bounded grammar."""
    candidate = value.strip()
    if not _VISIBLE_MPN_VALUE_RE.fullmatch(candidate):
        return None
    return candidate


def _extract_visible_mpn_evidence(
    elements: list[tuple[int | None, str]],
) -> tuple[str, str] | None:
    """Extract one unambiguous MPN from exact bounded visible field labels.

    An inline element containing an approved label, colon, and identifier is
    accepted. A split label and value are accepted only when the two finalized
    sibling elements share the same parent. Generic Part Number and retailer
    identifiers such as Item # or SKU are intentionally not authoritative.

    Different authoritative labeled values fail closed.
    """
    found: list[tuple[str, str]] = []

    for index, (parent_id, text) in enumerate(elements):
        inline = _VISIBLE_MPN_INLINE_RE.fullmatch(text)
        if inline is not None:
            value = _bounded_visible_mpn_value(inline.group("value"))
            if value is not None:
                found.append((inline.group("label").strip(), value))
            continue

        label = text.rstrip(":").strip()
        if label.casefold() not in _VISIBLE_MPN_LABEL_KEYS:
            continue
        if index + 1 >= len(elements):
            continue

        next_parent_id, next_text = elements[index + 1]
        if next_parent_id != parent_id:
            continue

        value = _bounded_visible_mpn_value(next_text)
        if value is not None:
            found.append((label, value))

    if not found:
        return None

    by_value: dict[str, tuple[str, str]] = {}
    for label, value in found:
        by_value.setdefault(value.casefold(), (label, value))

    if len(by_value) != 1:
        return None

    return next(iter(by_value.values()))

def _page_visible_mpn_is_unambiguous(
    observations: list[ListingObservation],
) -> bool:
    """Return whether one page-level visible MPN can safely enrich all rows.

    A visible field is page-level evidence. It may be applied only when every
    structured observation lacks an MPN and all observations identify the same
    product by the non-price tuple (title, SKU, brand). Multiple offers for that
    same product remain eligible; multiple Product nodes or an identity-free
    set fail closed.
    """
    if not observations:
        return False
    if any(
        observation.manufacturer_part_number_text is not None
        for observation in observations
    ):
        return False

    signatures = {
        (
            observation.product_title,
            observation.sku_text,
            observation.brand_text,
        )
        for observation in observations
    }
    if len(signatures) != 1:
        return False

    only_signature = next(iter(signatures))
    return any(value is not None for value in only_signature)


def _enrich_observation_with_visible_mpn(
    observation: ListingObservation,
    *,
    label: str,
    value: str,
) -> ListingObservation:
    """Fill only a missing MPN and mark the mixed extraction provenance."""
    if observation.manufacturer_part_number_text is not None:
        return observation

    if observation.extraction_method is ExtractionMethod.JSON_LD:
        enriched_method = ExtractionMethod.JSON_LD_WITH_VISIBLE_MPN
    elif observation.extraction_method is ExtractionMethod.META:
        enriched_method = ExtractionMethod.META_WITH_VISIBLE_MPN
    else:
        return observation

    return replace(
        observation,
        extraction_method=enriched_method,
        manufacturer_part_number_text=value,
    )


def _type_names(node: dict) -> set[str]:
    """The bare, lowercased `@type` names on a node.

    Handles the string form, the list form, and the fully-qualified URL form,
    all of which appear in the sampled pages.
    """
    declared = node.get("@type")
    values = declared if isinstance(declared, list) else [declared]
    names: set[str] = set()
    for value in values:
        if isinstance(value, str):
            names.add(value.rsplit("/", 1)[-1].rsplit("#", 1)[-1].strip().lower())
    return names


def _iter_nodes(value: object, depth: int = 0):
    """Yield every mapping inside a parsed JSON-LD structure, depth-bounded.

    Covers the three real shapes at once: a single object, a top-level list of
    objects, and an object wrapping an `@graph` list. Nested mappings are
    yielded too, so a `Product` inside a `BreadcrumbList` item or an `@graph`
    entry is still found.
    """
    if depth > MAX_JSON_LD_DEPTH:
        return
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _iter_nodes(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_nodes(child, depth + 1)


def _text(value: object) -> str | None:
    """Lift a scalar out of a JSON-LD value as text, or give up.

    `parse_float=str` / `parse_int=str` mean numbers already arrive as their
    source text, so a `str` here is the page's own representation. A `bool` is
    rendered by `schema.org` publishers as `"true"` / `"false"` and is kept in
    that spelling. Anything else — a list, a nested object in a scalar position
    — is not a value this module knows how to read, and guessing which element
    of a list was meant is exactly the kind of decision it must not make.
    """
    if isinstance(value, str):
        return value or None
    if isinstance(value, bool):
        return "true" if value else "false"
    return None


def _named_text(value: object) -> str | None:
    """Read a field that is either a string or an object with a `name`.

    `brand` and `seller` both appear in both forms; the sampled pages use
    `{"@type": "Brand", "name": "Samsung"}`.
    """
    direct = _text(value)
    if direct is not None:
        return direct
    if isinstance(value, dict):
        return _text(value.get("name"))
    return None


def _offer_nodes(product: dict) -> list[dict]:
    """Every offer container attached to a product, in published order.

    A single object, a list, and an `AggregateOffer` wrapping nested `offers`
    are all handled. Nesting is followed one level: an aggregate that carries
    its own concrete offers publishes those offers, and reading them is not
    inference.
    """
    found: list[dict] = []

    def collect(value: object, depth: int = 0) -> None:
        if depth > 2:
            return
        if isinstance(value, list):
            for child in value:
                collect(child, depth)
            return
        if not isinstance(value, dict):
            return
        types = _type_names(value)
        if types & AGGREGATE_OFFER_TYPES:
            nested = value.get("offers")
            if nested is not None:
                before = len(found)
                collect(nested, depth + 1)
                if len(found) > before:
                    # The aggregate's concrete offers were published; the
                    # wrapper adds no observation of its own.
                    return
            found.append(value)
            return
        if types & OFFER_TYPES or "price" in value or "priceCurrency" in value:
            found.append(value)

    collect(product.get("offers"))
    return found


def _observation_from_product(
    product: dict, offer: dict | None, *, source_url: str
) -> ListingObservation:
    """Build one observation from a product node and at most one of its offers."""
    is_aggregate = bool(offer is not None and _type_names(offer) & AGGREGATE_OFFER_TYPES)

    price_text: str | None = None
    currency_text: str | None = None
    availability_text: str | None = None
    condition_text: str | None = None
    seller_text: str | None = None
    offer_url_text: str | None = None

    if offer is not None:
        # An aggregate publishes a low and a high across sellers. That is a
        # range, not a price, and neither end is this product's price.
        if not is_aggregate:
            price_text = _text(offer.get("price"))
        currency_text = _text(offer.get("priceCurrency"))
        availability_text = _text(offer.get("availability"))
        condition_text = _text(offer.get("itemCondition"))
        seller_text = _named_text(offer.get("seller"))
        offer_url_text = _text(offer.get("url"))

    raw_node = dict(product)
    if offer is not None:
        raw_node["offers"] = offer

    return ListingObservation(
        source_url=source_url,
        extraction_method=ExtractionMethod.JSON_LD,
        product_title=_text(product.get("name")),
        manufacturer_part_number_text=_text(product.get("mpn")),
        sku_text=_text(product.get("sku")),
        brand_text=_named_text(product.get("brand")),
        price_text=price_text,
        currency_text=currency_text,
        availability_text=availability_text,
        condition_text=condition_text,
        seller_text=seller_text,
        offer_url_text=offer_url_text,
        raw_reference=json.dumps(raw_node, ensure_ascii=False, sort_keys=True),
    )


def _extract_from_json_ld(
    blocks: list[str], *, source_url: str
) -> list[ListingObservation]:
    """Map every `Product` node in every parseable block to observations."""
    observations: list[ListingObservation] = []

    for block in blocks:
        text = block.strip()
        if not text:
            continue
        try:
            # Numbers are kept as their source text: a price written as the JSON
            # number 1055.85 must not become a float on the way in, because the
            # float has already discarded how the page wrote it.
            parsed = json.loads(text, parse_float=str, parse_int=str)
        except (ValueError, RecursionError):
            # One malformed block, skipped. Its siblings are untouched.
            continue

        # Scoped to this block, and only valid while `parsed` holds the tree
        # alive: object ids are reused once a structure is freed, so a
        # collection shared across blocks would discard later products that
        # happened to land on a released address.
        seen: set[int] = set()

        for node in _iter_nodes(parsed):
            if not _type_names(node) & PRODUCT_TYPES:
                continue
            # The same product node can be reachable twice in one `@graph` that
            # also nests it; identity, not equality, so two genuinely distinct
            # products with identical content stay two products.
            if id(node) in seen:
                continue
            seen.add(id(node))

            offers = _offer_nodes(node)
            if not offers:
                observations.append(
                    _observation_from_product(node, None, source_url=source_url)
                )
                continue
            for offer in offers:
                observations.append(
                    _observation_from_product(node, offer, source_url=source_url)
                )

    return observations


def _extract_from_meta(
    meta_tags: list[dict[str, str]], *, source_url: str
) -> list[ListingObservation]:
    """Map flat product meta tags to at most one observation.

    Flat meta describes the page's one product; there is no structure in which a
    second could be expressed. If the tags carry nothing this module recognizes
    as product data, no observation is produced — a page with only `og:title`
    and an image is not a listing, and inventing one from a title would be the
    guess this phase exists to avoid.
    """
    collected: dict[str, str] = {}
    for tag in meta_tags:
        content = tag.get("content")
        if content is None:
            continue
        name = (tag.get("name") or "").strip()
        prop = (tag.get("property") or "").strip()

        # Some publishers put OpenGraph keys in `name` and some in `property`;
        # both real sampled pages disagree with each other about which.
        for key, mapping in ((name, META_NAME_FIELDS), (prop, META_NAME_FIELDS)):
            if key in mapping and mapping[key] not in collected:
                collected[mapping[key]] = content
        for key in (name, prop):
            lowered = key.lower()
            if lowered in META_PROPERTY_FIELDS:
                field = META_PROPERTY_FIELDS[lowered]
                if field not in collected:
                    collected[field] = content

    identifying = {
        "manufacturer_part_number_text",
        "sku_text",
        "price_text",
    }
    if not identifying & collected.keys():
        return []

    raw_reference = json.dumps(collected, ensure_ascii=False, sort_keys=True)
    return [
        ListingObservation(
            source_url=source_url,
            extraction_method=ExtractionMethod.META,
            raw_reference=raw_reference,
            **collected,
        )
    ]


def extract_listing_observations(
    document: str, *, source_url: str
) -> tuple[ListingObservation, ...]:
    """Extract raw listing observations from one document.

    `document` is the page as text — normally `FetchedPage.body_text`.
    `source_url` is where it came from — normally `FetchedPage.final_url`, the
    address the document actually arrived from rather than the one that was
    requested. Both are supplied by the caller: this function performs no I/O
    and generates no provenance.

    Returns a tuple in published order, possibly empty. **Zero observations is a
    valid answer**, and it is the right one for a page that publishes no
    structured product data at all — three of the seven real pages sampled for
    this phase are in exactly that position, one of them a page that returned
    HTTP 200 and an access-restriction notice.

    Raises `TypeError` for a wrong argument type and `ValueError` for a blank
    `source_url`. It does not raise for malformed content: unparseable markup and
    broken JSON are things pages do, not caller defects.
    """
    if not isinstance(document, str):
        raise TypeError(f"document must be a string, got {type(document).__name__}")
    if not isinstance(source_url, str):
        raise TypeError(
            f"source_url must be a string, got {type(source_url).__name__}"
        )
    if not source_url.strip():
        raise ValueError(
            "source_url is required; an observation nobody can re-open is not "
            "evidence"
        )

    collector = _parse_document(document)

    observations = _extract_from_json_ld(
        collector.json_ld_blocks, source_url=source_url
    )
    if not observations:
        # Only when the richer source produced nothing — see the module
        # docstring on why both structured mechanisms never run for one
        # document.
        observations = _extract_from_meta(
            collector.meta_tags,
            source_url=source_url,
        )

    # Production recall correction: some retailers publish the manufacturer's
    # identifier as a visible labeled field (for example Model #:) while their
    # JSON-LD exposes only the retailer-local SKU/Item number. The visible pass
    # may fill ONLY a missing MPN on an observation that already exists. It
    # cannot create an offer, cannot alter price/currency/condition, and fails
    # closed on conflicting labeled values.
    visible_mpn = _extract_visible_mpn_evidence(
        collector.visible_identity_elements
    )
    if (
        visible_mpn is not None
        and _page_visible_mpn_is_unambiguous(observations)
    ):
        label, value = visible_mpn
        observations = [
            _enrich_observation_with_visible_mpn(
                observation,
                label=label,
                value=value,
            )
            for observation in observations
        ]

    return tuple(observations)
