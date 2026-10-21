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

**Which product a visible label is about — the primary-product association.**
A page can carry visible identifiers for *other* products (recommendation
rails, cross-sells, navigation filters) alongside its own. The association of
a visible labeled field with the page's primary product is established only
by the page's own declarations and exact co-references — never by a CSS
class, never by position, never by similarity:

* A region the page declares non-primary — `<nav>`, `<aside>`,
  `role="navigation"`, `role="complementary"` — is other-product content and
  is never main-product identity evidence. Excluded content also remains a
  *structural barrier* to label/value pairing: a label and a value separated
  in the DOM by an excluded region (or by any unrecorded element) are not
  siblings and never pair, so removing the region cannot manufacture a
  pairing the DOM does not contain.
* A region the page declares primary — `<main>` or `role="main"` — is the
  page's own dominant content. When the document declares one, visible
  identity evidence is eligible only from inside it; undeclared content
  outside it is not primary-product evidence.
* When the document declares no primary region, the FU2 page-level contract
  applies: the visible field is associated with the single primary product
  only when the page itself co-references it — the field's value exactly
  equals an identifier the structured product published (SKU / title), a
  visible retailer-identifier field (`Item #` / `Item Number` / `SKU`) whose
  value exactly equals a published identifier is present on the page, the
  field shares a non-document-level block container with a visible occurrence
  of the product's own published title, or the undeclared visible stream
  contains nothing but the product's own fields (a page whose visible body
  publishes only that labeled field is a page about one product). A visible
  labeled value with none of those associations — an unrelated product's
  identifier riding in undeclared body content — is never assigned to the
  primary product, and the enrichment fails closed to no MPN.

None of this adds an identity authority: the structured offer remains the
sole declaration of which product the page is about, the visible label
grammar remains the sole authority for the MPN value, and the association
signals above only decide which product a visible label is about. Every one
of them is an exact, page-published fact (a declaration or a string
equality); none infers.

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
    r"\s*:\s*(?P<value>[A-Za-z0-9][A-Za-z0-9._/#-]{0,127})"
    r"(?:\s+(?P<identifier>(?:item\s+#|item\s+number|sku)\s*:\s*.+))?$",
    re.IGNORECASE,
)

#: Retailer-local identifier labels, recognized ONLY as association anchors
#: (a visible `Item #`/`SKU` field re-publishing the primary product's own
#: structured identifier) and never as MPN authority.
_IDENTIFIER_LABEL_KEYS = frozenset({"item #", "item number", "sku"})
_VISIBLE_IDENTIFIER_INLINE_RE = re.compile(
    r"^(?P<label>item\s+#|item\s+number|sku)"
    r"\s*:\s*(?P<value>[A-Za-z0-9][A-Za-z0-9._/#-]{0,127})$",
    re.IGNORECASE,
)

#: Block-level ancestors that are the document itself, not a product
#: container. Sharing only these between a title occurrence and a labeled
#: field does not associate them (that is the whole body, not a region).
_DOCUMENT_LEVEL_TAGS = frozenset({"html", "body"})
_VISIBLE_MPN_VALUE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/#-]{0,127}$")
_IGNORED_VISIBLE_TEXT_TAGS = frozenset({"script", "style", "noscript", "template"})
_VOID_VISIBLE_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
})
_INLINE_IDENTITY_CHILD_TAGS = frozenset({
    "span", "strong", "b", "em", "i", "small", "code", "label",
})
_SPLIT_IDENTITY_TAG_PAIRS = frozenset({
    ("span", "span"),
    ("th", "td"),
    # Definition-table cell pair: a label cell followed by a value cell in the
    # same row. Verified live (2026-10-20) on the Central Computer product
    # pages, whose visible specification table renders the manufacturer part
    # number as `<td>Manufacturer Part Number</td><td><MPN></td>` — the same
    # local sibling-cell shape as `th`/`td`, which this allowlist already
    # admits. Cross-row cells never pair: both must share the row parent.
    # Tag pair alone is NOT sufficient — the two elements must also be true
    # DOM siblings (the value element's immediately preceding recorded
    # sibling is the label element). An unrecorded element between them —
    # an excluded non-primary region, a container, an over-long element —
    # is a structural barrier that no allowlist entry overrides.
    ("td", "td"),
    ("dt", "dd"),
    ("strong", "span"),
    ("label", "span"),
})

#: Element and ARIA-role declarations that mark a region non-primary.
#:
#: `<nav>` is the HTML navigation landmark; `<aside>` is content
#: "tangentially related to the page's main content" (HTML spec) — the
#: declared home of recommendation rails and sidebars. `role="navigation"`
#: and `role="complementary"` carry the same declarations on any element.
#: The structured offer is the page's primary product, and the visible
#: labeled-MPN path may only enrich that product from primary content. A
#: labeled identifier inside a declared non-primary region belongs to whatever
#: other product the region is about (verified 2026-10-20: a recommendation
#: `<aside>` carrying its own `Manufacturer Part Number` row must not be read
#: as the main product's MPN). Exclusion is by declaration only — never by
#: CSS class — so a class like `recommended` neither helps nor hurts; and a
#: page that declares nothing keeps exactly the FU2 behavior.
_NON_PRIMARY_REGION_TAGS = frozenset({"nav", "aside"})
_NON_PRIMARY_REGION_ROLES = frozenset({"navigation", "complementary"})

#: How many bounded visible identity elements one document may record. The
#: bound's job is to refuse pathological element proliferation — a 5 MiB
#: document can carry millions of one-character leaf elements — not to
#: fine-tune per-site chrome. Calibration of record (2026-10-20): the heaviest
#: committed product fixture records 519 elements; the verified live product
#: pages record 384 (ServerOrbit) and 2,704 / 2,706 (Central Computer, both
#: Samsung DDR5 module pages). The previous bound of 2,048 sat between real
#: product pages and rejected them wholesale, erasing the visible labeled MPN
#: that the pages publish after their navigation chrome. 16,384 is 6x the
#: heaviest verified live product page and 32x the heaviest committed fixture,
#: still 300x below the pathological worst case, and a page that saturates it
#: fails closed for visible identity exactly as before (no other behavior
#: changes: the structured offer mechanisms are untouched).
MAX_VISIBLE_IDENTITY_ELEMENTS = 16384
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
    child_tags: list[str] | None = None
    #: Inside a declared non-primary region (nav/aside/role): this element
    #: records nothing and contributes no text, so other-product labels
    #: cannot enter the visible identity stream.
    excluded: bool = False
    #: This frame itself opened a declared non-primary region; its end tag
    #: decrements the region depth exactly once, when the frame is popped.
    is_region: bool = False
    #: This frame itself opened a declared PRIMARY region (`<main>` or
    #: `role="main"`); its end tag decrements the primary depth exactly once.
    is_primary_region: bool = False
    #: Opened inside a declared primary region: this element is eligible
    #: primary-product evidence when the document declares a primary region.
    inside_primary: bool = False
    #: The enclosing frame, kept so a recorded element can prove DOM
    #: containment (primary-region scope, title/field shared-container
    #: association). `None` at the document root.
    parent: "_VisibleTextFrame | None" = None
    #: Frame id of the last completed DOM child that was recorded — or
    #: `None` when that child was not recorded (excluded region, container,
    #: over-long text, empty) or no child has completed yet. A `None` here
    #: is a structural barrier: the next child is not a true sibling of any
    #: earlier recorded child.
    last_recorded_child: int | None = None


@dataclass
class _VisibleIdentityElement:
    """One recorded bounded visible element, in document order.

    Carries the pairing structure (true DOM sibling adjacency) and the
    association facts (primary-region scope, containment) the primary-product
    evidence gate needs. It is not itself identity evidence: only an approved
    label on it, or a label adjacent to a value on it, ever is.
    """

    frame_id: int
    parent_id: int | None
    tag: str
    text: str
    inside_primary_region: bool
    #: The immediately preceding recorded DOM sibling (same parent), or
    #: `None` when there was none or an unrecorded element sat between —
    #: the structural barrier that keeps excluded regions (and containers)
    #: from collapsing nonadjacent siblings into a fake pairing.
    prev_sibling_frame_id: int | None
    #: The element's frame, retained for DOM-containment walks only.
    frame: _VisibleTextFrame


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
        self.visible_identity_elements: list[_VisibleIdentityElement] = []
        self._in_json_ld = False
        self._buffer: list[str] = []
        self._ignored_visible_text_depth = 0
        self._visible_frames: list[_VisibleTextFrame] = []
        self._next_visible_frame_id = 1
        self._visible_capture_disabled = False
        self._non_primary_region_depth = 0
        self._primary_region_depth = 0
        #: The document declares at least one primary region (`<main>` or
        #: `role="main"`); when so, visible identity evidence is eligible
        #: only from inside a declared primary region.
        self.primary_region_declared = False
        #: Document-level (no enclosing frame) sibling state.
        self._root_last_recorded_child: int | None = None

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
        recorded_frame_id: int | None = None
        if not frame.excluded:
            # Declared non-primary regions record nothing and contribute no
            # text, so other-product labels cannot enter the visible identity
            # stream; failing closed, the enrichment simply never sees them.
            if frame.text_len <= MAX_VISIBLE_IDENTITY_ELEMENT_TEXT:
                text = " ".join(frame.parts).strip()
                if text:
                    child_tags = frame.child_tags or []
                    should_record = (
                        not child_tags
                        or all(tag in _INLINE_IDENTITY_CHILD_TAGS for tag in child_tags)
                    )
                    if should_record:
                        if len(self.visible_identity_elements) >= MAX_VISIBLE_IDENTITY_ELEMENTS:
                            self._disable_visible_capture()
                            return
                        prev_sibling = (
                            frame.parent.last_recorded_child
                            if frame.parent is not None
                            else self._root_last_recorded_child
                        )
                        self.visible_identity_elements.append(
                            _VisibleIdentityElement(
                                frame_id=frame.frame_id,
                                parent_id=frame.parent_id,
                                tag=frame.tag,
                                text=text,
                                inside_primary_region=frame.inside_primary,
                                prev_sibling_frame_id=prev_sibling,
                                frame=frame,
                            )
                        )
                        recorded_frame_id = frame.frame_id

                    # Propagate leaf text one level only. This lets inline
                    # children combine inside their immediate field container,
                    # but prevents a body/section ancestor from concatenating
                    # unrelated product facts into fake MPN evidence.
                    if not child_tags:
                        self._append_visible_piece(text)
        # Every completed DOM child updates its parent's sibling state —
        # recorded children link the chain, unrecorded ones (excluded
        # regions, containers, over-long or empty elements) break it. That
        # is what keeps an excluded region a structural barrier to pairing.
        state = recorded_frame_id
        if frame.parent is not None:
            frame.parent.last_recorded_child = state
        else:
            self._root_last_recorded_child = state

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

        # A declared non-primary region opens here (element tag or ARIA
        # role). Everything from this frame down the stack is excluded from
        # visible identity evidence; the depth is returned when the region
        # frame is popped. See `_NON_PRIMARY_REGION_TAGS` for why.
        declares_region = (
            tag in _NON_PRIMARY_REGION_TAGS
            or attributes.get("role", "").strip().casefold()
            in _NON_PRIMARY_REGION_ROLES
        )
        if declares_region:
            self._non_primary_region_depth += 1

        # A declared primary region opens here (`<main>` or `role="main"`).
        # The HTML spec reserves `<main>` for the dominant content of the
        # document — the page's own declaration of where the primary product
        # lives. See the module docstring's association rules for why.
        declares_primary = (
            tag == "main"
            or attributes.get("role", "").strip().casefold() == "main"
        )
        if declares_primary:
            self._primary_region_depth += 1
            self.primary_region_declared = True

        parent_id = (
            self._visible_frames[-1].frame_id
            if self._visible_frames
            else None
        )
        parent = self._visible_frames[-1] if self._visible_frames else None
        if parent is not None:
            if parent.child_tags is None:
                parent.child_tags = []
            parent.child_tags.append(tag)

        frame = _VisibleTextFrame(
            tag=tag,
            frame_id=self._next_visible_frame_id,
            parent_id=parent_id,
            parts=[],
            child_tags=[],
            excluded=self._non_primary_region_depth > 0,
            is_region=declares_region,
            is_primary_region=declares_primary,
            inside_primary=self._primary_region_depth > 0,
            parent=parent,
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
            if frame.is_region:
                self._non_primary_region_depth -= 1
            if frame.is_primary_region:
                self._primary_region_depth -= 1

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
    elements: list[_VisibleIdentityElement],
) -> tuple[str, str] | None:
    """Extract one unambiguous MPN from exact bounded visible field labels.

    An inline element containing an approved label, colon, and identifier is
    accepted. A split label and value are accepted only for a small allowlist
    of local sibling tag pairs that are TRUE DOM siblings: the value element's
    immediately preceding recorded sibling must be the label element. An
    excluded region or any other unrecorded element between the two is a
    structural barrier — removing an element can never manufacture a pairing
    the DOM does not contain. Generic Part Number and retailer identifiers
    such as Item # or SKU are intentionally not authoritative. A trailing
    Item #/SKU after an inline Model # is ignored rather than being mistaken
    for part of the MPN.

    Different authoritative labeled values fail closed.
    """
    found: list[tuple[str, str]] = []
    next_by_prev: dict[int, _VisibleIdentityElement] = {
        element.prev_sibling_frame_id: element
        for element in elements
        if element.prev_sibling_frame_id is not None
    }

    for element in elements:
        inline = _VISIBLE_MPN_INLINE_RE.fullmatch(element.text)
        if inline is not None:
            value = _bounded_visible_mpn_value(inline.group("value"))
            if value is not None:
                found.append((inline.group("label").strip(), value))
            continue

        label = element.text.rstrip(":").strip()
        if label.casefold() not in _VISIBLE_MPN_LABEL_KEYS:
            continue
        partner = next_by_prev.get(element.frame_id)
        if partner is None:
            continue
        if (element.tag, partner.tag) not in _SPLIT_IDENTITY_TAG_PAIRS:
            continue

        value = _bounded_visible_mpn_value(partner.text)
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

def _visible_labeled_fields(
    elements: list[_VisibleIdentityElement],
) -> list[tuple[str, tuple[_VisibleIdentityElement, ...]]]:
    """Every complete approved labeled field: (value, its elements).

    A field is one inline labeled element, or a true-adjacent split label +
    value pair. An incomplete label (no adjacent value partner) is not a
    field: it carries no value and does not count as product content.
    """
    next_by_prev: dict[int, _VisibleIdentityElement] = {
        element.prev_sibling_frame_id: element
        for element in elements
        if element.prev_sibling_frame_id is not None
    }
    fields: list[tuple[str, tuple[_VisibleIdentityElement, ...]]] = []
    for element in elements:
        inline = _VISIBLE_MPN_INLINE_RE.fullmatch(element.text)
        if inline is not None:
            value = _bounded_visible_mpn_value(inline.group("value"))
            if value is not None:
                fields.append((value, (element,)))
            continue
        label = element.text.rstrip(":").strip()
        if label.casefold() not in _VISIBLE_MPN_LABEL_KEYS:
            continue
        partner = next_by_prev.get(element.frame_id)
        if partner is None:
            continue
        if (element.tag, partner.tag) not in _SPLIT_IDENTITY_TAG_PAIRS:
            continue
        value = _bounded_visible_mpn_value(partner.text)
        if value is not None:
            fields.append((value, (element, partner)))
    return fields


def _visible_identifier_anchor(
    elements: list[_VisibleIdentityElement], targets: frozenset[str]
) -> bool:
    """Whether the page visibly re-publishes the primary product's own
    structured identifier in a retailer-identifier field.

    An `Item #:` / `Item Number:` / `SKU:` field whose value exactly equals one
    of the product's published identifiers — or the trailing `Item #` group of
    an inline labeled field — is the page's own co-reference tying the visible
    body to the structured product. It is an association anchor only: these
    labels never gain MPN authority.
    """
    next_by_prev: dict[int, _VisibleIdentityElement] = {
        element.prev_sibling_frame_id: element
        for element in elements
        if element.prev_sibling_frame_id is not None
    }
    for element in elements:
        inline = _VISIBLE_MPN_INLINE_RE.fullmatch(element.text)
        if inline is not None:
            trailing = inline.group("identifier")
            if (
                trailing is not None
                and trailing.rstrip().rsplit(":", 1)[-1].strip() in targets
            ):
                return True
            continue
        ident = _VISIBLE_IDENTIFIER_INLINE_RE.fullmatch(element.text)
        if ident is not None and ident.group("value") in targets:
            return True
        label = element.text.rstrip(":").strip().casefold()
        if label in _IDENTIFIER_LABEL_KEYS:
            partner = next_by_prev.get(element.frame_id)
            if (
                partner is not None
                and (element.tag, partner.tag) in _SPLIT_IDENTITY_TAG_PAIRS
                and partner.text in targets
            ):
                return True
    return False


def _identifier_field_element_ids(
    elements: list[_VisibleIdentityElement], targets: frozenset[str]
) -> set[int]:
    """Frame ids of the elements that form a product identifier field (both
    halves of a split field, the one element of an inline field) — product
    content for the product-only test, never MPN evidence by themselves."""
    ids: set[int] = set()
    next_by_prev: dict[int, _VisibleIdentityElement] = {
        element.prev_sibling_frame_id: element
        for element in elements
        if element.prev_sibling_frame_id is not None
    }
    for element in elements:
        if _VISIBLE_MPN_INLINE_RE.fullmatch(element.text) is not None:
            continue  # a labeled-field element; covered by the fields themselves
        ident = _VISIBLE_IDENTIFIER_INLINE_RE.fullmatch(element.text)
        if ident is not None and ident.group("value") in targets:
            ids.add(element.frame_id)
            continue
        label = element.text.rstrip(":").strip().casefold()
        if label in _IDENTIFIER_LABEL_KEYS:
            partner = next_by_prev.get(element.frame_id)
            if (
                partner is not None
                and (element.tag, partner.tag) in _SPLIT_IDENTITY_TAG_PAIRS
                and partner.text in targets
            ):
                ids.add(element.frame_id)
                ids.add(partner.frame_id)
    return ids


def _shares_non_document_block_ancestor(
    a: _VisibleIdentityElement, b: _VisibleIdentityElement
) -> bool:
    """Whether two elements sit inside one common block container that is not
    the document itself (`<html>`/`<body>`).

    The locality test for the title co-reference: a visible occurrence of the
    product's own published title associates a labeled field only when the two
    are in the same region of the page, not merely on the same body.
    """
    ancestors: set[int] = set()
    node: _VisibleTextFrame | None = a.frame.parent
    while node is not None:
        ancestors.add(node.frame_id)
        node = node.parent
    node = b.frame.parent
    while node is not None:
        if node.frame_id in ancestors:
            while node is not None and node.tag in _INLINE_IDENTITY_CHILD_TAGS:
                node = node.parent
            return node is not None and node.tag not in _DOCUMENT_LEVEL_TAGS
        node = node.parent
    return False


def _primary_product_targets(
    observations: list[ListingObservation],
) -> tuple[bool, frozenset[str]]:
    """The frozen page-level gate, plus the primary product's published
    identifiers (title, SKU) used only as exact co-reference targets.

    Eligible only when every structured observation lacks an MPN, all
    observations identify the same product by the non-price tuple (title, SKU,
    brand), and that product publishes at least one identifier. Multiple offers
    for the same product remain eligible; multiple Product nodes or an
    identity-free set fail closed.
    """
    if not observations:
        return False, frozenset()
    if any(
        observation.manufacturer_part_number_text is not None
        for observation in observations
    ):
        return False, frozenset()

    signatures = {
        (
            observation.product_title,
            observation.sku_text,
            observation.brand_text,
        )
        for observation in observations
    }
    if len(signatures) != 1:
        return False, frozenset()

    title, sku, _brand = next(iter(signatures))
    if title is None and sku is None:
        return False, frozenset()

    return True, frozenset(value for value in (title, sku) if value)


def _page_visible_mpn_is_unambiguous(
    observations: list[ListingObservation],
) -> bool:
    """Return whether one page-level visible MPN can safely enrich all rows."""
    ok, _targets = _primary_product_targets(observations)
    return ok


def _visible_mpn_for_primary_product(
    elements: list[_VisibleIdentityElement],
    observations: list[ListingObservation],
    primary_region_declared: bool,
) -> tuple[str, str] | None:
    """The visible labeled MPN, restricted to evidence the page associates
    with its primary product — or `None` when it does not (fail closed).

    When the document declares a primary region, the association IS the
    declaration: only evidence inside `<main>`/`role="main"` is eligible. When
    it does not, the FU2 page-level contract applies and an undeclared labeled
    field is eligible only through an exact page-published co-reference: its
    value equals a published identifier; the page re-publishes a published
    identifier in a visible `Item #`/`SKU` field; the field shares a
    non-document block container with a visible occurrence of the published
    title; or the undeclared visible stream contains nothing but the product's
    own fields. A value with no such association is another product's evidence
    and is never assigned to the primary product.
    """
    ok, targets = _primary_product_targets(observations)
    if not ok or not elements:
        return None

    if primary_region_declared:
        pool = [e for e in elements if e.inside_primary_region]
        if not pool:
            return None
        return _extract_visible_mpn_evidence(pool)

    fields = _visible_labeled_fields(elements)
    if not fields:
        return None

    title = next(
        (
            observation.product_title
            for observation in observations
            if observation.product_title
        ),
        None,
    )
    identifier_anchor = _visible_identifier_anchor(elements, targets)
    title_anchors = [e for e in elements if title is not None and e.text == title]

    covered: set[int] = set()
    for _value, field_elements in fields:
        covered.update(e.frame_id for e in field_elements)
    covered.update(_identifier_field_element_ids(elements, targets))
    bare_targets = [e for e in elements if e.text in targets]
    covered.update(e.frame_id for e in bare_targets)
    # Region coverage, scoped to one table: an element that sits inside the
    # same <table> as an anchor element is part of that table's product data
    # display (the other rows of the specification table beside the MPN row),
    # so it counts as product content for the product-only test. A generic
    # wrapper div does NOT count: chrome and a recommendation rail sharing an
    # arbitrary container are still unassociated body content.
    element_by_id = {e.frame_id: e for e in elements}
    anchor_frames = [element_by_id[fid].frame for fid in covered]
    table_ids: set[int] = set()
    for frame in anchor_frames:
        node: _VisibleTextFrame | None = frame.parent
        while node is not None:
            if node.tag == "table":
                table_ids.add(node.frame_id)
            node = node.parent
    if table_ids:
        for element in elements:
            node = element.frame.parent
            while node is not None:
                if node.frame_id in table_ids:
                    covered.add(element.frame_id)
                    break
                node = node.parent
    product_only = all(e.frame_id in covered for e in elements)

    eligible: list[_VisibleIdentityElement] = []
    for value, field_elements in fields:
        if value in targets or identifier_anchor or product_only:
            eligible.extend(field_elements)
            continue
        if title_anchors and any(
            _shares_non_document_block_ancestor(e, anchor)
            for e in field_elements
            for anchor in title_anchors
        ):
            eligible.extend(field_elements)

    if not eligible:
        return None

    return _extract_visible_mpn_evidence(eligible)


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
    # cannot create an offer, cannot alter price/currency/condition, fails
    # closed on conflicting labeled values, and — because the visible stream
    # is page-level — admits only evidence the page's own declarations and
    # exact co-references associate with the primary product (see
    # `_visible_mpn_for_primary_product`).
    visible_mpn = _visible_mpn_for_primary_product(
        collector.visible_identity_elements,
        observations,
        primary_region_declared=collector.primary_region_declared,
    )
    if visible_mpn is not None:
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
