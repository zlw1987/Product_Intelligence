# Recorded page fixtures (PRODUCT-INTEL.3A)

Real public product pages, fetched once each on **2026-08-17** by
`product_intelligence.providers.http_page.HttpPageFetcher`, and used for offline
regression testing of `product_intelligence.research.extraction`.

Nothing here is fabricated. Every fixture is derived from one live fetch of one
public URL, and every retained fragment is copied **verbatim** from the document
that fetch returned. A synthetic edge case is never placed in this directory —
those live in `tests/research/test_listing_extraction.py`, written inline and
labelled synthetic, so a reader can never mistake one for a recording.

## How the URLs were chosen

From the ten organic results in the existing recorded search fixture,
`tests/fixtures/providers/serper/real_verified_mz_ql23t800_organic_search.json`
(evaluation corpus case `REAL-0001`, the public Samsung enterprise SSD SKU
`MZ-QL23T800`). **No new search call was made in 3A.** Seven of those ten URLs
were fetched: the manufacturer page, four independent retailer/distributor
pages, and two large marketplaces as diagnostic samples.

## Reduction policy

Four of the five fixtures are **reduced**. The live documents run from 198 KB to
850 KB, and almost all of that is navigation, styling, scripts, images, reviews,
and marketing copy that no extractor reads. Retaining it would turn this
repository into an archive of other people's websites without improving a single
test.

What is retained is what reproduces the extraction behaviour: the
`application/ld+json` blocks, the relevant `meta` tags, and — for one fixture —
real visible-text price markup that must *not* be read as a price. Each file
carries an HTML comment stating what was kept and what was removed. Each
reduction was verified by running the extractor over the full document and over
the reduced fixture and confirming the observations are identical.

What is removed: scripts, stylesheets, images, navigation, reviews, related
products (except where explicitly retained as price noise), and marketing prose.

What was never present to remove: no cookie, no session token, no
authentication material, no personal or customer information, no internal
commercial data. These are anonymous GETs of public pages; the fetcher sends no
credential and stores no header other than `Content-Type`.

## Inventory

| File | Source | Outcome | Form |
| --- | --- | --- | --- |
| `samsung_us_pm9a3_mz_ql23t800.html` | `www.samsung.com` (manufacturer) | `STATIC_FETCH_OK` | Reduced from 198 KB |
| `oempcworld_pm9a3_mz_ql23t800.html` | `oempcworld.com` (retailer) | `STATIC_FETCH_OK` | Reduced from 850 KB |
| `exxactcorp_pm9a3_mz_ql23t800.html` | `www.exxactcorp.com` (retailer) | `STATIC_FETCH_OK` | Reduced from 596 KB |
| `newegg_pm9a3_mz_ql23t800.html` | `www.newegg.com` (marketplace) | `STATIC_FETCH_OK`, no product data | Reduced from 203 KB |
| `fusionww_access_restricted.html` | `www.fusionww.com` (distributor) | Soft block, HTTP 200 | **Full**, 1.9 KB |

### `samsung_us_pm9a3_mz_ql23t800.html`

The manufacturer-controlled page. Publishes a `schema.org` `Product` with
`sku: "MZ-QL23T800"` — the manufacturer part number, in the `sku` field rather
than in `mpn`, which is why 3A preserves both fields separately and compares
neither.

Its `Offer` publishes **`"price": "undefined"`** — a template that failed,
served as well-formed structured data. It is retained exactly as published, and
it is the single clearest piece of evidence for why 3A stores raw text: a
converting extractor would raise or silently drop the offer, and neither
outcome would be visible to a reviewer. Deciding what `"undefined"` means is
3B's, with a recorded reason.

Both `ld+json` blocks are kept. The `BreadcrumbList` is retained deliberately —
it proves a non-`Product` sibling node is ignored rather than mistaken for an
offer.

### `oempcworld_pm9a3_mz_ql23t800.html`

A storefront page publishing the same offer twice, in two representations:
`"1055.85"` in a JSON-LD `Offer`, and `"1,055.85"` in `og:price:amount`. This is
the evidence behind the precedence rule — meta extraction runs only when JSON-LD
produced nothing, so one offer does not become two observations.

Its `sku` is `"501489"`, the retailer's internal number, and it publishes no
`mpn` at all. The part number appears only inside the product title. Nothing in
3A infers it from there.

Retained as price noise, verbatim from the live page: four additional
`<span class="price">` elements belonging to recommended products
(`$8.85`, `$6.85`, `$13.75`, `$129.98`), written in **identical markup** to the
product's own price element, plus one financing-configuration fragment carrying
a `price_per_term` of `$527.92` and plan bounds of `$35.00`–`$30,000.00`. The
full page contains fourteen distinct dollar amounts. A first-match, a
lowest-match, and a largest-match visible-text rule each return a wrong number
from this page with complete confidence, which is why no such rule exists.

### `exxactcorp_pm9a3_mz_ql23t800.html`

The page that justifies the `META` extraction path. It publishes **no
`application/ld+json` at all**, and its whole product record is in flat meta
tags: `mpn`, `sku`, `brand`, `price`, `availability`. Without a meta path, a
page that plainly states its part number and its price would yield nothing.

Three of its values are instructive and are preserved exactly as published:
`mpn` is `"mpn:MZ-QL23T800"` — prefix included, because stripping it is a
normalization rule and 3A makes none; `availability` is `"false"`, which is no
`schema.org` vocabulary term; and there is **no currency anywhere on the page**,
so the observation carries a price with no currency. All three are 3B's problems
and all three are visible rather than guessed at.

### `newegg_pm9a3_mz_ql23t800.html`

A successful fetch that yields nothing. HTTP 200, ~203 KB of markup, and no
product structured data: the only `ld+json` nodes are a `BreadcrumbList` and an
`ImageObject`, and `og:type` is `"website"` rather than `"product"`. The price
does not appear anywhere in the static document — the product data is rendered
client-side.

This fixture exists to keep "zero observations" a tested outcome. A page this
extractor cannot read is recorded as unreadable, not filled in from a search
snippet.

### `fusionww_access_restricted.html`

Kept **in full** because it is 1.9 KB and reducing it would remove the point.

The site returned **HTTP 200** with an "Access Restricted" interstitial: a soft
block, invisible to any classifier that only looks at status codes. Its
`ld+json` is a `WebAPI` node whose description tells an automated reader to use
a different service instead of crawling the site, and the page body repeats the
instruction.

That content is **data, not instruction** (§19). It was read, classified, and
recorded; the API it advertises was not called, and nothing in this repository
acts on text found in a fetched page. The extractor's correct output here is
zero observations, because a `WebAPI` node is not an offer — and the fixture is
kept so that stays true.
