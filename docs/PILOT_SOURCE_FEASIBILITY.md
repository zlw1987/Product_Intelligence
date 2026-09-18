# Product Intelligence — Pilot Source Feasibility Audit (4D-PRE)

**Phase:** PRODUCT-INTEL.4D-PRE  
**Status:** COMPLETE — evidence collection only, no production changes  
**Initial audit:** 2026-09-18T00:54:00Z  
**Evidence closure (FU1):** 2026-09-18T02:12:00Z  
**HEAD:** 7b4dc2322c4d8c7d8dc49efa150b3d89b8e90bb0

---

## Purpose

Audit the customer's 12 preferred public websites across TWO independent dimensions:

1. **DISCOVERY** — Can the site-owned mechanism locate a product page from an exact MPN without external search?
2. **POST-DISCOVERY ACQUISITION** — Once a product URL is known, can existing static HTTP + generic 3A extraction reach usable product evidence?

This audit produces **evidence only**. No production code, no tests, no architecture change.

---

## Test Parameters

| Parameter | Value |
| --- | --- |
| MPN 1 | `BCM957608-P2200GQF00` (Broadcom P2200G network adapter) |
| MPN 2 | `MZ-QL23T800` (Samsung PM9A3 3.84TB SSD) |
| Fetcher | `HttpPageFetcher` (stdlib, 10s timeout, 3 redirect max, 5 MiB limit) |
| Extractor | `extract_listing_observations()` (generic 3A: JSON-LD + flat meta) |
| User-Agent | `ProductIntelligenceBot/0.1 (+deterministic listing extraction)` |
| Serper calls | **Zero** (confirmed) |
| Browser automation | **None** (confirmed) |
| Proxies / block bypass | **None** (confirmed) |

---

## Classification Vocabulary

### Discovery dimension

| Value | Meaning |
| --- | --- |
| `DIRECT_SITE` | Site-owned search mechanism deterministically locates the product page from an exact MPN via static HTTP |
| `EXTERNAL_DISCOVERY_REQUIRED` | Site-owned search does not work for static acquisition; external search needed to discover the URL |
| `BLOCKED` | Site prevents access entirely (403, 429, WAF challenge, etc.) |
| `UNKNOWN` | Insufficient evidence to classify |

### Post-discovery acquisition dimension

| Value | Meaning |
| --- | --- |
| `STATIC_USABLE` | Generic 3A extraction produces observations with price and identity evidence |
| `STATIC_PARTIAL` | Static HTTP reaches the page and 3A extracts some evidence, but key fields (identity, price, availability) are missing or incomplete |
| `JS_ONLY` | Page returns HTTP 200 but product data exists only after client-side rendering; static HTML has no extractable product data |
| `BLOCKED` | Cannot reach page via static HTTP |
| `UNKNOWN` | Insufficient evidence to classify |

### Overall recommendation

| Value | Meaning |
| --- | --- |
| `DIRECT` | Discovery = DIRECT_SITE AND Post-discovery ∈ {STATIC_USABLE, STATIC_PARTIAL} |
| `SERPER_FALLBACK` | Discovery = EXTERNAL_DISCOVERY_REQUIRED AND Post-discovery ∈ {STATIC_USABLE, STATIC_PARTIAL} |
| `UNSUITABLE` | Discovery = BLOCKED or Post-discovery = BLOCKED, OR neither discovery nor post-discovery is viable |
| `INSUFFICIENT_EVIDENCE` | Evidence is incomplete for one or both dimensions; a conclusion would be guessing |

**Binding clarification:** DIRECT / SERPER_FALLBACK / UNSUITABLE / INSUFFICIENT_EVIDENCE are **ACQUISITION-FEASIBILITY classifications for 4D-PRE**. They do NOT confer:

- deterministic identity acceptance
- Machine Price eligibility
- Reviewed Price eligibility
- source trust or authority

Those remain governed by existing frozen identity/review/aggregation contracts.

"UNSUITABLE" means unsuitable under the currently approved static-HTTP, no-block-bypass acquisition architecture. It is not a permanent claim that the business source itself has no useful data.

---

## Audit Entries

### cdw.com

| Field | Value |
| --- | --- |
| source / domain | cdw.com |
| **DISCOVERY** | **EXTERNAL_DISCOVERY_REQUIRED** |
| **POST-DISCOVERY ACQUISITION** | **UNKNOWN** |
| direct lookup mechanism | None — React app with empty search form action; all server-side search patterns return 404 |
| tested search shape | `https://www.cdw.com/search?text={mpn}` (404), `https://www.cdw.com/product/find?search={mpn}` (404), `https://www.cdw.com/search-result?text={mpn}` (404), `https://search.cdw.com/?q={mpn}` (404) |
| tested product URL | `https://www.cdw.com/product/broadcom-bcm957608-p2200gqf00/6965735` — returned HTTP 200, 37KB, but a **completely different product** (ADO CORP AFTEFPRO, not Broadcom). Page has `robots: noindex,nofollow`, zero JSON-LD, zero observations. The product ID `6965735` is not deterministic for the Broadcom MPN. |
| stable product URL? | No — the tested product URL pattern did not resolve to the correct product |
| static HTML? | Homepage: HTTP 200, 194KB, React app. Product URL: HTTP 200, 37KB, but wrong product. |
| JS required? | **Yes** — search is entirely client-side (React/Next.js app) |
| bot / blocking behavior | None observed — 404 on search endpoints, not blocking |
| explicit MPN evidence? | No |
| price? | No |
| currency? | No |
| availability? | No |
| condition? | No |
| source-specific extraction needed? | Unknown — cannot confirm product page behavior |
| recommendation | **INSUFFICIENT_EVIDENCE** |
| evidence / notes | Search is entirely client-side (React app, `__NEXT_DATA__` indicators). All four tested search URL patterns return HTTP 404. The known product URL returned a completely different product (wrong ID) with zero structured data. No viable product-evidence path demonstrated. Post-discovery acquisition remains UNKNOWN. |

---

### newegg.com

| Field | Value |
| --- | --- |
| source / domain | newegg.com |
| **DISCOVERY** | **EXTERNAL_DISCOVERY_REQUIRED** |
| **POST-DISCOVERY ACQUISITION** | **JS_ONLY** |
| direct lookup mechanism | Search URL `https://www.newegg.com/p/pl?d={mpn}` returns HTTP 200 but no product data in static HTML |
| tested search shape | `https://www.newegg.com/p/pl?d=BCM957608-P2200GQF00` (200, meta only), `https://www.newegg.com/p/pl?d=MZ-QL23T800` (200, meta only) |
| tested product URL | `https://www.newegg.com/broadcom-bcm957608-p2200gqf00/p/14U-004W-000H3?Item=14U-004W-000H3` |
| product URL HTTP outcome | **200, 243KB** — has `<html>` but **no `<body>` tag** in the static response |
| product URL JSON-LD | 3 blocks: `BreadcrumbList` (5 ListItems), `ImageObject`, `FAQPage` (2 Questions/Answers). **ZERO Product nodes.** |
| product URL observations | **0** |
| product URL meta tags | No product-relevant meta tags (no price, no MPN, no SKU, no brand, no availability, no condition) |
| stable product URL? | URL format exists (`/p/{item}`) but static content is a JS shell |
| JS required? | **Yes** — product data rendered client-side; static HTML has no Product JSON-LD and no `<body>` tag |
| bot / blocking behavior | None — HTTP 200 with full page |
| explicit MPN evidence? | No — not in any structured data in static HTML |
| price? | No |
| currency? | No |
| availability? | No |
| condition? | No |
| source-specific extraction needed? | No — there is no static product data to extract |
| recommendation | **INSUFFICIENT_EVIDENCE** |
| evidence / notes | **Historical 3A evidence confirmed: JS shell.** Known product URL returns HTTP 200, 243KB, but the static HTML is a JavaScript shell (no `<body>` tag, JSON-LD contains only BreadcrumbList/ImageObject/FAQPage). Zero observations. Zero product-relevant meta tags. Even if Serper discovers the URL, the current static HTTP + 3A extraction path cannot reach any product evidence. Post-discovery = JS_ONLY. |

---

### serversupply.com

| Field | Value |
| --- | --- |
| source / domain | serversupply.com |
| **DISCOVERY** | **BLOCKED** |
| **POST-DISCOVERY ACQUISITION** | **BLOCKED** |
| direct lookup mechanism | None — site blocks all automated access |
| tested search shape | `https://www.serversupply.com/search?keyword=BCM957608-P2200GQF00` (403), `https://www.serversupply.com/search?keyword=MZ-QL23T800` (403) |
| stable product URL? | No — cannot reach any page |
| static HTML? | No — all requests return HTTP 403 |
| JS required? | N/A — blocked before any content is served |
| bot / blocking behavior | **HTTP 403** on homepage, bare domain, and search URL |
| explicit MPN evidence? | No |
| price? | No |
| currency? | No |
| availability? | No |
| condition? | No |
| source-specific extraction needed? | No |
| recommendation | **UNSUITABLE** |
| evidence / notes | **Historical 3A evidence confirmed: BLOCKED_403.** Retested for 4D-PRE and FU1: both homepage variants (`www` and bare domain) and search URL all return HTTP 403. Hard block at the HTTP level. |

---

### harddiskdirect.com

| Field | Value |
| --- | --- |
| source / domain | harddiskdirect.com |
| **DISCOVERY** | **EXTERNAL_DISCOVERY_REQUIRED** |
| **POST-DISCOVERY ACQUISITION** | **UNKNOWN** |
| direct lookup mechanism | None — search is AJAX-only; Magento `catalogsearch/result/` endpoint returns 404 |
| tested search shape | `https://harddiskdirect.com/catalogsearch/result/?q={mpn}` (404), `https://harddiskdirect.com/catalogsearch/result/index/?q={mpn}` (404), `https://harddiskdirect.com/?q={mpn}` (200 but static homepage, identical content regardless of query), `https://harddiskdirect.com/search/?q={mpn}` (404) |
| tested own-catalog MPN | `MZ-77E1T0B` (Samsung 870 EVO 1TB) — `https://harddiskdirect.com/?q=MZ-77E1T0B` returned HTTP 200, 588KB (identical homepage), MPN NOT in body, 0 observations |
| homepage structured data | 2 JSON-LD blocks, zero Product nodes |
| stable product URL? | No — cannot discover product URLs via static HTTP |
| static HTML? | Homepage: HTTP 200, 589KB, valid HTML |
| JS required? | **Yes** — search is AJAX-driven; `?q=` parameter on homepage returns static homepage with no search results |
| bot / blocking behavior | None — HTTP 200 on homepage; 404 on search endpoints |
| explicit MPN evidence? | No |
| price? | No |
| currency? | No |
| availability? | No |
| condition? | No |
| source-specific extraction needed? | No |
| recommendation | **INSUFFICIENT_EVIDENCE** |
| evidence / notes | Homepage returns HTTP 200, 589KB, with 2 JSON-LD blocks (no Product nodes). No search form action found in static HTML. `catalogsearch/result/` endpoint returns HTTP 404. Query parameter `?q=` on homepage returns the identical static homepage with no search results rendered. Tested own-catalog MPN `MZ-77E1T0B`: same result. No known product URL was available to test post-discovery acquisition. |

---

### esaitech.com

| Field | Value |
| --- | --- |
| source / domain | esaitech.com |
| **DISCOVERY** | **EXTERNAL_DISCOVERY_REQUIRED** |
| **POST-DISCOVERY ACQUISITION** | **STATIC_PARTIAL** |
| direct lookup mechanism | Shopify search `action=/search`, `input name=q`, `method=get` — functional server-side mechanism but both test MPNs return "no results" pages |
| tested search shape | `https://esaitech.com/search?q=BCM957608-P2200GQF00` (200, "Sorry, no results"), `https://esaitech.com/search?q=MZ-QL23T800` (200, "Sorry, no results") |
| tested catalog URL | `https://esaitech.com/collections/ssd-solid-state-drives?page=25&variant=45090677588193` (200, 883KB) |
| catalog URL findings | JSON-LD block 0 has parse error (malformed JSON) but body contains `"@type": "Product"`, `"name": "Samsung MZ-QL23T800 PM9A3 3.84TB PCIe 4.0x4 NVMe 2.5-Inch SSD"`, `"url": "https://esaitech.com/products/samsung-mz-ql23t800-pm9a3-3-84tb-pcie-4-0x4-2-5-ssd"` |
| tested product URL | `https://esaitech.com/products/samsung-mz-ql23t800-pm9a3-3-84tb-pcie-4-0x4-2-5-ssd` |
| product URL HTTP outcome | **200, 398KB** |
| product URL observations | **1 (via META)** |
| product URL exact fields | `manufacturer_part_number_text: None`, `sku_text: None`, `product_title: Samsung MZ-QL23T800 PM9A3 3.84TB PCIe 4.0x4 NVMe 2.5-Inch SSD`, `price_text: 745.00`, `currency_text: USD`, `availability_text: None`, `condition_text: None`, `seller_text: None` |
| stable product URL? | Shopify pattern: `/products/<slug>` — deterministic once discovered |
| static HTML? | **Yes** — HTTP 200, 398KB, full static HTML |
| JS required? | No — product page returns usable static data via meta tags |
| bot / blocking behavior | None — HTTP 200 on all requests |
| explicit MPN evidence? | **No** — MPN appears in `product_title` only, not in `manufacturer_part_number_text` or `sku_text` |
| price? | **Yes** — `745.00` |
| currency? | **Yes** — `USD` |
| availability? | No |
| condition? | No |
| source-specific extraction needed? | **Not yet.** Current generic 3A obtains title + price + currency from the Saitech product page. No explicit structured MPN has been demonstrated — `manufacturer_part_number_text` and `sku_text` are both `None`. A later source-specific extractor is justified only if inspection of real recorded source structure demonstrates an explicit manufacturer part-number field or another approved structured field. Until then, title-only MPN evidence does not obtain deterministic 3C acceptance. Note: SERPER_FALLBACK describes acquisition feasibility, not automatic Machine Price eligibility. |
| recommendation | **SERPER_FALLBACK** |
| evidence / notes | **Discovery requires external search.** Site-owned Shopify search returns "no results" for both test MPNs. However, post-discovery acquisition IS viable: known product page returns HTTP 200, 398KB, with 1 META observation containing title (includes MPN in text), price=745.00, currency=USD. MPN is NOT in the structured `manufacturer_part_number_text` field — only in the title. No explicit structured MPN field has been demonstrated. Title-only MPN evidence does not obtain deterministic 3C acceptance. |

---

### serverorbit.com

| Field | Value |
| --- | --- |
| source / domain | serverorbit.com |
| **DISCOVERY** | **EXTERNAL_DISCOVERY_REQUIRED** |
| **POST-DISCOVERY ACQUISITION** | **UNKNOWN** |
| direct lookup mechanism | None — Magento `catalogsearch/result/` endpoint returns 404; search is AJAX-driven |
| tested search shape | `https://serverorbit.com/catalogsearch/result/?q=BCM957608-P2200GQF00` (404), `https://serverorbit.com/catalogsearch/result/index/?q=BCM957608-P2200GQF00` (404), `https://serverorbit.com/?s=BCM957608-P2200GQF00` (200, static homepage, 0 obs) |
| tested category URL | `https://serverorbit.com/network-devices/network-adapter/?items_per_page=48&sort_by=price&sort_order=desc` (200, 580KB, 0 obs) |
| category URL findings | JSON-LD: `BreadcrumbList`, `Organization` — zero Product nodes. BCM reference in body is for `BCM57608` (HPE P73511-001), NOT for `BCM957608-P2200GQF00`. Zero observations. |
| tested product URLs | `https://serverorbit.com/broadcom-bcm957608-p2200gqf00-400-gbe-dual-port-qsfp112-pcie-5-0-x16-oct-network-adapter.html` (fetch error), `https://serverorbit.com/network-devices/network-adapter/broadcom-bcm957608-p2200gqf00.html` (fetch error) |
| stable product URL? | No — guessed URL patterns failed |
| static HTML? | Homepage and category page: HTTP 200, valid HTML |
| JS required? | Likely — `cm-ajax` CSS classes on forms; category page returned zero product observations despite having 580KB of content |
| bot / blocking behavior | None — HTTP 200 on all URLs; 404 on search endpoints |
| explicit MPN evidence? | No |
| price? | No |
| currency? | No |
| availability? | No |
| condition? | No |
| source-specific extraction needed? | Unknown |
| recommendation | **INSUFFICIENT_EVIDENCE** |
| evidence / notes | Discovery: AJAX-only search (catalogsearch returns 404). Post-discovery: the known category URL returned HTTP 200, 580KB, but zero Product JSON-LD nodes and zero observations. The BCM reference in the body is for BCM57608 (different product), not BCM957608-P2200GQF00. Two guessed product URL patterns both failed. No known product URL with confirmed BCM957608-P2200GQF00 content was available for testing. |

---

### directmacro.com

| Field | Value |
| --- | --- |
| source / domain | directmacro.com |
| **DISCOVERY** | **DIRECT_SITE** |
| **POST-DISCOVERY ACQUISITION** | **STATIC_PARTIAL** |
| direct lookup mechanism | **YES** — Magento search: `https://directmacro.com/catalogsearch/result/?q={mpn}` |
| tested search shape | `https://directmacro.com/catalogsearch/result/?q=BCM957608-P2200GQF00` (200, 1.7MB, 6 obs), `https://directmacro.com/catalogsearch/result/?q=MZ-QL23T800` (200, 1.8MB, 10 obs) |
| stable product URL? | **Not a synthesis rule** — site-owned search deterministically discovers product links from exact MPN; returned product links appear stable in tested samples. No URL-slug-synthesis rule has been proven; 4D-A must follow the returned site link, not manufacture a slug |
| static HTML? | **YES** — HTTP 200, 1.7–1.9MB, full static HTML with JSON-LD |
| JS required? | **No** — search results and product data available in static HTML |
| bot / blocking behavior | None — HTTP 200 on all requests |
| source-specific extraction needed? | **No — and must not be used to weaken frozen 3C.** Generic 3A correctly preserves DirectMacro's published `sku` as `sku_text`. The `sku` field MUST remain SKU evidence. A DirectMacro-specific adapter/extractor MUST NOT relabel a schema.org `sku` field as manufacturer MPN merely because its string equals the requested MPN. Frozen 3C remains authoritative: SKU-only evidence is not deterministic ACCEPTED identity. A later source-specific strategy may extract an explicit manufacturer part number ONLY if real site-controlled evidence demonstrates a distinct field whose semantics are manufacturer part number. Otherwise the SKU/title evidence remains non-deterministic identity evidence. Note: DIRECT means DIRECT ACQUISITION feasibility, not automatic Machine Price eligibility. |
| recommendation | **DIRECT** |
| evidence / notes | **ONLY DIRECT candidate.** Search form action confirmed: `action="https://directmacro.com/catalogsearch/result/"`, `input name=q`, `method=get`. |

#### Exact generic 3A field report — DirectMacro

**BCM957608-P2200GQF00 — Search results page:**

| Field | Value |
| --- | --- |
| `manufacturer_part_number_text` | **None** |
| `sku_text` | `BCM957608-P2200GQF00` |
| `product_title` | `BCM957608-P2200GQF00 - Broadcom 400GbE Dual-Port QSFP112 PCI` |
| `brand_text` | `Broadcom` |
| `price_text` | `2120.002` |
| `currency_text` | `USD` |
| `availability_text` | `http://schema.org/InStock` |
| `condition_text` | `None` |
| `seller_text` | `None` |

**BCM957608-P2200GQF00 — Individual product page:**

| Field | Value |
| --- | --- |
| `manufacturer_part_number_text` | **None** |
| `sku_text` | `BCM957608-P2200GQF00` |
| `product_title` | `BCM957608-P2200GQF00 - Broadcom 400GbE Dual-Port QSFP112 PCI` |
| `brand_text` | `Broadcom` |
| `price_text` | **None** |
| `currency_text` | **None** |
| `availability_text` | **None** |
| `condition_text` | **None** |
| `seller_text` | **None** |

**MZ-QL23T800 — Search results page:**

| Field | Value |
| --- | --- |
| `manufacturer_part_number_text` | **None** |
| `sku_text` | `MZ-QL23T800` |
| `product_title` | `MZ-QL23T800 - Samsung PM9A3 3.84TB PCI-Express 4.0 x4 NVMe (` |
| `brand_text` | `Samsung` |
| `price_text` | `2376` |
| `currency_text` | `USD` |
| `availability_text` | `http://schema.org/InStock` |
| `condition_text` | `None` |
| `seller_text` | `None` |

**MZ-QL23T800 — Individual product page:**

| Field | Value |
| --- | --- |
| `manufacturer_part_number_text` | `MZ-QL23T800` |
| `sku_text` | `MZ-QL23T800` |
| `product_title` | `MZ-QL23T800 - Samsung PM9A3 3.84TB PCI-Express 4.0 x4 NVMe (` |
| `brand_text` | `Samsung` |
| `price_text` | **None** |
| `currency_text` | **None** |
| `availability_text` | **None** |
| `condition_text` | **None** |
| `seller_text` | **None** |

#### DirectMacro identity analysis

- **BCM957608-P2200GQF00:** No explicit MPN field exists in either search results OR product page JSON-LD. Only `sku_text` matches the requested MPN. The JSON-LD structure uses `sku` (not `mpn`) for the Broadcom product.
- **MZ-QL23T800:** Search results page has only `sku_text`. Individual product page has `manufacturer_part_number_text: MZ-QL23T800` AND `sku_text: MZ-QL23T800`.

Per frozen 3C contract: **SKU-only evidence is NOT automatically accepted even when the SKU string equals the requested MPN.**

Therefore:
- For **BCM957608-P2200GQF00**, current deterministic Machine Price identity path rejects it (only SKU evidence from both search results and product page).
- For **MZ-QL23T800**, the product page provides explicit MPN evidence, but the search results page does not. Price is on search results, not on the product page.

**DirectMacro remains DIRECT for acquisition, but Machine Price does NOT automatically gain deterministic identity authority for the Broadcom MPN.**

---

### dihuni.com

| Field | Value |
| --- | --- |
| source / domain | dihuni.com |
| **DISCOVERY** | **BLOCKED** |
| **POST-DISCOVERY ACQUISITION** | **BLOCKED** |
| direct lookup mechanism | None — Sucuri WAF JavaScript challenge blocks all access |
| tested search shape | `https://www.dihuni.com/?q={mpn}` (307), `https://dihuni.com/catalogsearch/result/?q={mpn}` (307), homepage `https://www.dihuni.com/` (307), `https://dihuni.com/` (307) |
| stable product URL? | No — cannot reach any page |
| static HTML? | No — HTTP 307 with Sucuri challenge page |
| JS required? | **Yes** — Sucuri WAF returns an encrypted JavaScript challenge that must be executed |
| bot / blocking behavior | **HTTP 307** on all requests. No Location header. Response body: `<html><title>You are being redirected...</title><noscript>Javascript is required. Please enable javascript before you are allowed to see this page.</noscript><script>...sucuri_cloudproxy_js...` — confirmed Sucuri CloudProxy WAF JavaScript challenge |
| explicit MPN evidence? | No |
| price? | No |
| currency? | No |
| availability? | No |
| condition? | No |
| source-specific extraction needed? | No |
| recommendation | **UNSUITABLE** |
| evidence / notes | All HTTP requests to both `www.dihuni.com` and `dihuni.com` return HTTP 307. The response body is a Sucuri CloudProxy JavaScript challenge page (`sucuri_cloudproxy_js`, encrypted redirect script, `<noscript>Javascript is required`). This is definitively a bot protection mechanism. No content is served without executing the JavaScript challenge. |

---

### centralcomputer.com

| Field | Value |
| --- | --- |
| source / domain | centralcomputer.com |
| **DISCOVERY** | **EXTERNAL_DISCOVERY_REQUIRED** |
| **POST-DISCOVERY ACQUISITION** | **UNKNOWN** |
| direct lookup mechanism | Search URL `https://www.centralcomputer.com/catalogsearch/result/?q={mpn}` returns HTTP 200 with MPN in body text, but generic 3A produces **0 observations** from the search results page |
| tested search shape | `https://www.centralcomputer.com/catalogsearch/result/?q=BCM957608-P2200GQF00` (200, 398KB, 0 obs, MPN in body), `https://www.centralcomputer.com/catalogsearch/result/?q=MZ-QL23T800` (200, 459KB, 0 obs, MPN in body), `https://www.centralcomputer.com/catalogsearch/result/?q=samsung+pm9a3` (200, 679KB, 0 obs) |
| tested product URLs | `https://www.centralcomputer.com/samsung-mz-ql23t800-3-84tb-pm9a3-internal-ssd.html` (fetch error), `https://www.centralcomputer.com/samsung-pm9a3-3-84tb.html` (fetch error) |
| category page | `https://www.centralcomputer.com/all-products.html` — HTTP 200, 1.97MB, 60 JSON-LD observations with title/price/currency/availability. These are category listing products, NOT the specific target MPNs. No BCM957608-P2200GQF00 or MZ-QL23T800 confirmed in those observations. |
| stable product URL? | No — known product URL patterns returned errors; cannot confirm target MPNs are in catalog |
| static HTML? | **Yes** — category pages and search results return HTTP 200 with full static HTML |
| JS required? | Partially — search results are server-rendered but product-specific pages are not reachable via guessed URLs |
| bot / blocking behavior | None — HTTP 200 on search and category pages; fetch errors on specific product URLs |
| explicit MPN evidence? | No — not in any 3A observations |
| price? | On category pages (not target products) |
| currency? | On category pages (USD) |
| availability? | On category pages (InStock) |
| condition? | No |
| source-specific extraction needed? | Unknown — cannot confirm target product pages are reachable |
| recommendation | **INSUFFICIENT_EVIDENCE** |
| evidence / notes | Search results pages return HTTP 200 with the MPN present in body text (meta title: `Search results for: '{mpn}'`), but generic 3A produces zero observations from search results. Two guessed product URL patterns for MZ-QL23T800 returned fetch errors. Category page `all-products.html` has rich JSON-LD (60 observations) but these are not the target MPNs. Cannot confirm that BCM957608-P2200GQF00 or MZ-QL23T800 product pages are reachable via static HTTP, nor that they contain usable structured data. |

---

### memory4less.com

| Field | Value |
| --- | --- |
| source / domain | memory4less.com |
| **DISCOVERY** | **BLOCKED** |
| **POST-DISCOVERY ACQUISITION** | **BLOCKED** |
| direct lookup mechanism | None — site blocks all automated access |
| tested search shape | `https://www.memory4less.com/catalogsearch/result/?q=BCM957608-P2200GQF00` (403), `https://www.memory4less.com/catalogsearch/result/?q=MZ-QL23T800` (403) |
| stable product URL? | No — cannot reach any page |
| static HTML? | No — HTTP 403 on all requests |
| JS required? | N/A — blocked before any content is served |
| bot / blocking behavior | **HTTP 403** on homepage and search URL |
| explicit MPN evidence? | No |
| price? | No |
| currency? | No |
| availability? | No |
| condition? | No |
| source-specific extraction needed? | No |
| recommendation | **UNSUITABLE** |
| evidence / notes | Both homepage and search URL return HTTP 403. Hard block at the HTTP level. |

---

### fs.com

| Field | Value |
| --- | --- |
| source / domain | fs.com |
| **DISCOVERY** | **BLOCKED** |
| **POST-DISCOVERY ACQUISITION** | **BLOCKED** |
| direct lookup mechanism | None — AWS WAF JavaScript challenge blocks all access |
| tested search shape | `https://www.fs.com/products/all.html?keyword=BCM957608-P2200GQF00` (202, 2KB WAF challenge), `https://www.fs.com/products/all.html?keyword=MZ-QL23T800` (202, 2KB WAF challenge) |
| stable product URL? | No — cannot reach any page |
| static HTML? | No — HTTP 202 with AWS WAF challenge page (`awsWafCookieDomainList`, `gokuProps` encryption key/iv) |
| JS required? | **Yes** — AWS WAF returns an encrypted JavaScript challenge |
| bot / blocking behavior | **HTTP 202** with AWS WAF challenge page on all requests |
| explicit MPN evidence? | No |
| price? | No |
| currency? | No |
| availability? | No |
| condition? | No |
| source-specific extraction needed? | No |
| recommendation | **UNSUITABLE** |
| evidence / notes | All requests return HTTP 202 with a 2KB AWS WAF challenge page containing JavaScript challenge infrastructure. Actual website content not served until challenge is solved. |

---

### naddod.com

| Field | Value |
| --- | --- |
| source / domain | naddod.com |
| **DISCOVERY** | **EXTERNAL_DISCOVERY_REQUIRED** |
| **POST-DISCOVERY ACQUISITION** | **UNKNOWN** |
| direct lookup mechanism | None — search endpoints return 404; homepage ignores query parameters |
| tested search shape | `https://www.naddod.com/catalogsearch/result/?q={mpn}` (404), `https://www.naddod.com/catalogsearch/result/index/?q={mpn}` (404), `https://www.naddod.com/?q={mpn}` (200, static homepage, 0 obs), `https://www.naddod.com/search/?q={mpn}` (404) |
| tested product URL | `https://www.naddod.com/network-adapter/broadcom-400-gbe-dual-port-qsfp112-pci-express-5-0-copper-network-adapter-11201924.html` (fetch error), `https://www.naddod.com/broadcom-400-gbe-dual-port-qsfp112-11201924.html` (fetch error) |
| stable product URL? | No — known product URL returned fetch error |
| static HTML? | Homepage: HTTP 200, 208KB, client-side rendering framework |
| JS required? | Likely — framework indicators suggest client-side rendering; no search form in static HTML |
| bot / blocking behavior | None — HTTP 200 on homepage; 404 on search endpoints |
| explicit MPN evidence? | No |
| price? | No |
| currency? | No |
| availability? | No |
| condition? | No |
| source-specific extraction needed? | No |
| recommendation | **INSUFFICIENT_EVIDENCE** |
| evidence / notes | Client-side rendered site. All search endpoint patterns fail (404). Homepage `?q=` returns static homepage with zero observations. Two known product URL patterns both returned fetch errors. Post-discovery acquisition remains UNKNOWN. |

---

## Summary

### Corrected classification matrix

| Source | Discovery | Post-discovery | Recommendation |
| --- | --- | --- | --- |
| **directmacro.com** | **DIRECT_SITE** | **STATIC_PARTIAL** | **DIRECT** |
| cdw.com | EXTERNAL_DISCOVERY_REQUIRED | UNKNOWN | INSUFFICIENT_EVIDENCE |
| newegg.com | EXTERNAL_DISCOVERY_REQUIRED | JS_ONLY | INSUFFICIENT_EVIDENCE |
| serversupply.com | BLOCKED | BLOCKED | UNSUITABLE |
| harddiskdirect.com | EXTERNAL_DISCOVERY_REQUIRED | UNKNOWN | INSUFFICIENT_EVIDENCE |
| esaitech.com | EXTERNAL_DISCOVERY_REQUIRED | STATIC_PARTIAL | SERPER_FALLBACK |
| serverorbit.com | EXTERNAL_DISCOVERY_REQUIRED | UNKNOWN | INSUFFICIENT_EVIDENCE |
| dihuni.com | BLOCKED | BLOCKED | UNSUITABLE |
| centralcomputer.com | EXTERNAL_DISCOVERY_REQUIRED | UNKNOWN | INSUFFICIENT_EVIDENCE |
| memory4less.com | BLOCKED | BLOCKED | UNSUITABLE |
| fs.com | BLOCKED | BLOCKED | UNSUITABLE |
| naddod.com | EXTERNAL_DISCOVERY_REQUIRED | UNKNOWN | INSUFFICIENT_EVIDENCE |

### A. Zero-Serper discovery candidates

| Source | Note |
| --- | --- |
| **directmacro.com** | Only site with deterministic MPN→URL via site-owned search. **However:** for BCM957608-P2200GQF00, current frozen 3C grants NO deterministic automatic identity (only SKU evidence, no explicit MPN field). For MZ-QL23T800, the product page has explicit MPN but price is on search results, not the product page. |

### B. Sites requiring external discovery

cdw.com, newegg.com, harddiskdirect.com, esaitech.com, serverorbit.com, centralcomputer.com, naddod.com

### C. Sites with usable post-discovery static evidence

| Source | Evidence |
| --- | --- |
| **directmacro.com** | Search results: title, SKU, brand, price, currency, availability (6–10 obs). Product pages: title, MPN (MZ only), SKU, brand — but NO price. |
| **esaitech.com** | Product page (from known URL): title, price=745.00, currency=USD (1 META observation). MPN only in title text. |

### D. Sites with post-discovery JS/browser gap

| Source | Evidence |
| --- | --- |
| **newegg.com** | HTTP 200, 243KB, but JSON-LD contains BreadcrumbList/ImageObject/FAQPage only. No `<body>` tag in static response. Zero Product nodes. Zero observations. |

### E. Sites blocked by access controls

| Source | Block Type |
| --- | --- |
| serversupply.com | HTTP 403 |
| dihuni.com | HTTP 307 + Sucuri WAF JavaScript challenge |
| memory4less.com | HTTP 403 |
| fs.com | HTTP 202 + AWS WAF JavaScript challenge |

### F. Sites still lacking evidence (INSUFFICIENT_EVIDENCE)

| Source | Missing Evidence |
| --- | --- |
| cdw.com | Post-discovery: known product URL returned wrong product; no viable product page URL pattern confirmed |
| harddiskdirect.com | Post-discovery: no known product URL available for testing |
| serverorbit.com | Post-discovery: category page had 0 observations; guessed product URLs failed |
| centralcomputer.com | Post-discovery: search results have 0 obs; guessed product URLs returned errors; cannot confirm target MPNs are in catalog |
| naddod.com | Post-discovery: known product URL returned fetch error |

### G. DirectMacro — Special identity note

DirectMacro provides zero-Serper direct acquisition of price, currency, and availability data from search results. However:

- **Current frozen 3C does NOT grant deterministic automatic Machine Price identity for BCM957608-P2200GQF00** — only SKU evidence exists (no explicit `manufacturer_part_number_text` field in either search results or product page JSON-LD).
- **MZ-QL23T800** has explicit MPN on the product page but price is on the search results page, not the product page.
- Machine Price remains deterministic-only and requires price-bearing evidence whose identity is ACCEPTED under frozen 3C and whose other frozen 4A eligibility rules pass. Human review can affect Reviewed Price only, never Machine Price. A later source-specific extractor may help only by exposing a real site-controlled explicit manufacturer-part-number field; it may not promote SKU/title evidence or otherwise bypass frozen 3C.

DirectMacro is **DIRECT for acquisition**, but **zero-credit Machine Price authority is NOT automatic**.

### H. Recommendation totals

| Recommendation | Count | Sites |
| --- | --- | --- |
| **DIRECT** | 1 | directmacro.com |
| **SERPER_FALLBACK** | 1 | esaitech.com |
| **UNSUITABLE** | 4 | serversupply.com, dihuni.com, memory4less.com, fs.com |
| **INSUFFICIENT_EVIDENCE** | 6 | cdw.com, newegg.com, harddiskdirect.com, serverorbit.com, centralcomputer.com, naddod.com |

### I. Correction log (FU1 changes from initial audit)

| Source | Initial | Corrected | Reason |
| --- | --- | --- | --- |
| cdw.com | SERPER_FALLBACK | INSUFFICIENT_EVIDENCE | Known product URL returned wrong product; post-discovery UNKNOWN |
| newegg.com | SERPER_FALLBACK | INSUFFICIENT_EVIDENCE | Known product URL: JS_ONLY (HTTP 200, BreadcrumbList/FAQPage JSON-LD, no Product nodes, zero obs) |
| harddiskdirect.com | SERPER_FALLBACK | INSUFFICIENT_EVIDENCE | No known product URL available; post-discovery UNKNOWN |
| esaitech.com | SERPER_FALLBACK | SERPER_FALLBACK (unchanged) | Post-discovery confirmed: STATIC_PARTIAL (1 META obs: title, price=745.00, currency=USD) |
| serverorbit.com | SERPER_FALLBACK | INSUFFICIENT_EVIDENCE | Category page had 0 obs; BCM reference was for different MPN; guessed product URLs failed |
| dihuni.com | UNSUITABLE | UNSUITABLE (confirmed) | Sucuri WAF challenge definitively proven |
| centralcomputer.com | SERPER_FALLBACK | INSUFFICIENT_EVIDENCE | Target MPN product pages returned errors; cannot confirm MPNs are in catalog |
| naddod.com | SERPER_FALLBACK | INSUFFICIENT_EVIDENCE | Known product URL returned error; post-discovery UNKNOWN |
| directmacro.com | DIRECT | DIRECT (confirmed) | Exact field report added; SKU-only identity noted for BCM |
| serversupply.com | UNSUITABLE | UNSUITABLE (unchanged) | Confirmed |
| memory4less.com | UNSUITABLE | UNSUITABLE (unchanged) | Confirmed |
| fs.com | UNSUITABLE | UNSUITABLE (unchanged) | Confirmed |

### J. Zero Serper confirmation

- **Serper calls made:** 0
- **Serper credits consumed:** 0
- **Serper live smoke script:** NOT executed
- **Browser automation:** NONE installed or used
- **Proxy/rotating UA:** NONE used
- **Block bypass:** NONE attempted
- **CAPTCHA solving:** NONE attempted
- **Login/account creation:** NONE performed

### K. Exact newly tested URLs (FU1)

| URL | MPN | Outcome |
| --- | --- | --- |
| `https://esaitech.com/collections/ssd-solid-state-drives?page=25&variant=45090677588193` | MZ-QL23T800 | 200, 883KB, 0 obs; MPN in body JSON-LD |
| `https://esaitech.com/products/samsung-mz-ql23t800-pm9a3-3-84tb-pcie-4-0x4-2-5-ssd` | MZ-QL23T800 | 200, 398KB, **1 obs (META): title, price=745.00, currency=USD** |
| `https://www.newegg.com/broadcom-bcm957608-p2200gqf00/p/14U-004W-000H3?Item=14U-004W-000H3` | BCM957608-P2200GQF00 | 200, 243KB, **0 obs** (BreadcrumbList/ImageObject/FAQPage JSON-LD only) |
| `https://serverorbit.com/network-devices/network-adapter/?items_per_page=48&sort_by=price&sort_order=desc` | BCM957608-P2200GQF00 | 200, 580KB, **0 obs** (BCM ref is BCM57608, not target MPN) |
| `https://harddiskdirect.com/?q=MZ-77E1T0B` | MZ-77E1T0B | 200, 589KB (identical homepage, MPN not in body, 0 obs) |
| `https://www.cdw.com/product/broadcom-bcm957608-p2200gqf00/6965735` | BCM957608-P2200GQF00 | 200, 37KB, **0 obs** (wrong product: ADO CORP) |
| `https://www.naddod.com/network-adapter/broadcom-400-gbe-dual-port-qsfp112-pci-express-5-0-copper-network-adapter-11201924.html` | BCM957608-P2200GQF00 | Fetch error |
| `https://dihuni.com/` | — | 307, Sucuri WAF challenge (confirmed) |
| `https://www.dihuni.com/` | — | 307, Sucuri WAF challenge (confirmed) |

### L. Files changed

Only:
- `docs/PILOT_SOURCE_FEASIBILITY.md` (this file)

No production code, tests, config, requirements, migrations, scripts, PLAN.md, or STATUS.md were modified.

### M. No commit/push

Working directory has one uncommitted modified file. No `git add`, `git commit`, or `git push` was executed.

---

## Notes

- All evidence was collected using the existing `HttpPageFetcher` with its honest `ProductIntelligenceBot/0.1` User-Agent.
- 403, 429, 307, and 202 responses were recorded as evidence, not retried or worked around.
- The `directmacro.com` finding remains the most actionable: it is the only DIRECT candidate with functional zero-Serper acquisition.
- The corrected INSUFFICIENT_EVIDENCE count (6 sites) is higher than the initial audit because post-discovery evidence was required for every SERPER_FALLBACK claim, and most sites lacked a known product URL or had JS-only pages.
- Only `esaitech.com` survived the FU1 correction as SERPER_FALLBACK: external discovery needed + confirmed STATIC_PARTIAL post-discovery (price, currency, title via meta tags).
- No percentage Serper savings estimate is provided — execution policy for direct results thresholds, fallback triggers, and concurrency is a 4D-A design decision.
- The DirectMacro SKU-only identity issue is critical for 4D-A: whether `sku_text` matching the requested MPN is sufficient for Machine Price acceptance depends on frozen 3C rules, which currently do NOT auto-accept SKU-only evidence.
