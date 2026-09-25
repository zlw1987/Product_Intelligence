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

4D-A added the DirectMacro search results fixture:
`directmacro_bcm957608_p2200gqf00_search.html`, captured from DirectMacro's
site-owned search mechanism (`/catalogsearch/result/?q=<MPN>`). One explicit
static HTTP fetch was performed against DirectMacro only, with no proxy, no
login, no browser, and no Serper call. The fixture is reduced to the one
Broadcom product relevant to the BCM957608-P2200GQF00 MPN.

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
| `directmacro_bcm957608_p2200gqf00_search.html` | `directmacro.com` (preferred source) | `STATIC_FETCH_OK`, SKU-only identity | **4D-A reduced**, 2.1 KB |
| `micron_7500_product_page.html` | `www.micron.com` (manufacturer) | `STATIC_FETCH_OK` | **4D-D-PRE2 verbatim**, 277,936 B |
| `micron_7500_part_catalog_page.html` | `www.micron.com` (manufacturer) | `STATIC_FETCH_OK` | **4D-D-PRE2 verbatim**, 268,932 B |
| `micron_7500_part_detail_base.html` | `www.micron.com` (manufacturer) | `STATIC_FETCH_OK` | **4D-D-PRE2 verbatim**, 259,911 B |
| `micron_7500_part_detail_r.html` | `www.micron.com` (manufacturer) | `STATIC_FETCH_OK` | **4D-D-PRE2 verbatim**, 259,937 B |
| `micron_7500_part_detail_t.html` | `www.micron.com` (manufacturer) | `STATIC_FETCH_OK` | **4D-D-PRE2 verbatim**, 259,937 B |
| `micron_shipping_quantities.html` | `www.micron.com` (manufacturer) | `STATIC_FETCH_OK` | **4D-D-PRE2 verbatim**, 258,137 B |
| `micron_7500_part_catalog.json` | `www.micron.com` (structured catalog endpoint) | `STATIC_FETCH_OK` | **4D-D-PRE2 verbatim**, 24,060 B |
| `micron_7500_getproductinfo_base.json` | `www.micron.com` (per-part structured endpoint) | `STATIC_FETCH_OK` | **4D-D-PRE2 verbatim**, 1,232 B |
| `micron_7500_getproductinfo_r.json` | `www.micron.com` (per-part structured endpoint) | `Invalid Partnumber` | **4D-D-PRE2 verbatim**, 54 B |
| `micron_7500_getproductinfo_t.json` | `www.micron.com` (per-part structured endpoint) | `Invalid Partnumber` | **4D-D-PRE2 verbatim**, 54 B |
| `micron_7500_product_brief.pdf` | `assets.micron.com` (manufacturer-published document) | `STATIC_FETCH_OK` | **4D-D-PRE2 verbatim**, 318,063 B |
| `micron_7500_tech_prod_spec.pdf` | `assets.micron.com` (manufacturer-published document) | `STATIC_FETCH_OK` | **4D-D-PRE2 verbatim**, 328,747 B |

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

### `directmacro_bcm957608_p2200gqf00_search.html`

4D-PRE / 4D-A evidence. DirectMacro is the only site classified as DIRECT
(discoverable via site-owned search + static HTML extraction).

This is a reduced fixture capturing the ONE Broadcom P2200G product from the
DirectMacro search results page for `BCM957608-P2200GQF00`. Other search-result
products from the real page are omitted.

Exact 3A extraction (verified against live page, 4D-PRE):

- `manufacturer_part_number_text`: **None** — no explicit `mpn` field
- `sku_text`: `BCM957608-P2200GQF00`
- `product_title`: contains MPN in title text
- `brand_text`: `Broadcom`
- `price_text`: `2120.002`
- `currency_text`: `USD`
- `availability_text`: `http://schema.org/InStock`
- `condition_text`: **None**

This proves the 4D-PRE finding: DirectMacro provides price, currency, and
availability evidence from the search results page, but the Broadcom product
publishes **only** `sku`, not `mpn`. Frozen 3C rejects SKU-only evidence as
`REJECTED / NO_EXPLICIT_MPN_EVIDENCE`, so the listing is excluded from 4A for
`IDENTITY_NOT_ACCEPTED`. This fixture is used to verify that the 4D-A direct
acquisition path correctly falls back to search when SKU-only evidence does not
produce a valid 4A bucket.

### Micron 7500 SSD fixtures (4D-D-PRE2)

Recorded on **2026-09-22** by anonymous public GET requests (plain stdlib
HTTP client, no credentials, no cookies, no session tokens). These are the
evidence-only fixtures for PRODUCT-INTEL.4D-D-PRE2: full provenance —
requested URLs, final URLs, status codes, content types, retrieval
timestamps, and SHA256 of every stored byte — is recorded in
`docs/MICRON_ALIAS_AUTHORITY_EVIDENCE.md` (§2 URL facts, §3 fixture table).

They are **verbatim** (not reduced): each file is the exact response body.
They carry no cookie, session, credential, or personal data.

What each fixture is used for:

- `micron_7500_part_catalog.json` (family catalog, 24 rows) — the 4D-D v1
  runtime authority source. The row for `MTFDKCC3T8TGP-1BK1DABYY` publishes
  the exact base MPN in `part-number` and carries
  `{"name":"SSD","id":"is-ssd","value":true}` in `attr`.
- `micron_7500_part_catalog_page.html` — the part-catalog HTML page that
  publishes the catalog endpoint in its own `data-apiresource` attribute.
- `micron_7500_getproductinfo_base.json` — the per-part structured record
  for the BASE part (real `DATABASE` record, `part-title` in exact case,
  `category: "data-center-ssd"`).
- `micron_7500_getproductinfo_r.json` / `micron_7500_getproductinfo_t.json` —
  regression evidence that the R and T variants are **not** independent
  catalog parts: both return exactly
  `{"message":"Invalid Partnumber","response-code":"200"}`. The 4D-D
  authority chain must therefore anchor on the BASE family-catalog record,
  never on R/T per-part endpoints or R/T page metadata.
- `micron_7500_product_page.html` — the 7500 family product page; publishes
  the product-brief / tech-spec document links.
- `micron_7500_part_detail_base.html` / `_r.html` / `_t.html` — the three
  part-detail pages. Server-rendered; the MPN appears in title/meta/og/
  twitter/breadcrumb. The R/T pages prove the metadata is template-injected
  ("dynamic Part Number" comment, `{1} {2} part detail` data-layer
  template) and is never treated as independent identity authority.
- `micron_shipping_quantities.html` — Micron shipping-quantities support page
  (doc CSN-04); checked for an official R/T suffix definition — none exists.
- `micron_7500_product_brief.pdf` / `micron_7500_tech_prod_spec.pdf` —
  Micron-published 7500 family documents. Their part-numbering sections
  define capacity/security/sector/family fields and (in the tech spec) an
  `ES` suffix only; **no R/T field is defined** in either.
