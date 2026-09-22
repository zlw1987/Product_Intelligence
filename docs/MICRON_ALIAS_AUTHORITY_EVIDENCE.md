# Micron Official Authority Evidence Capture — PRODUCT-INTEL.4D-D-PRE2

**Phase:** PRODUCT-INTEL.4D-D-PRE2 (evidence collection only — NO production
code, NO alias relation, NO authority runtime, NO search/orchestration/model/
migration/web changes)

**Parent / base:** PRODUCT-INTEL.4D-C frozen at
`4592b8966b703dfd6a72c3067d7b191314ff2968` (4766 collected).

**PRE1 binding conclusion under test:** `NO CURRENT 4D-D ELIGIBILITY AUTHORITY
EXISTS`. PRE2 captures NEW manufacturer-controlled Micron evidence and reviews
whether a 4D-D v1 (SSD-only) authority chain can be built on it.

**Retrieval date:** 2026-09-22 (UTC). All fetches were anonymous public GET
requests made with a plain HTTP client (Python stdlib `urllib`), browser-style
`User-Agent`, no credentials, no cookies, no session tokens, no private
headers. Nothing in any fixture contains account, session, or credential
material.

**Serper was NOT used as runtime evidence for any item in this report.**

---

## 1. Recommendation (final)

```
AUTHORITY_EVIDENCE_SUFFICIENT_FOR_4D_D_SSD_V1
```

Scope conditions attached to that recommendation (all evidence-backed below):

1. **SSD ONLY for 4D-D v1.** The exact-MPN catalog record carries an explicit
   structured `is-ssd = true` attribute and `category = "data-center-ssd"`.
   No generic-Memory anchor was captured or is claimed.
2. **The structured catalog record owns the exact-MPN proof; the reviewed
   policy owns the manufacturer.** The MPN is never accepted from URL-path
   echo alone. For the BASE part, the exact MPN is independently corroborated
   by two Micron-owned structured endpoints (per-part `getproductinfo` and
   family `getpartcatalog`).
3. **The R/T variants are NOT independent catalog parts.** Micron's own
   structured endpoints answer `{"message":"Invalid Partnumber"}` for the R and
   T variants and list no catalog rows for them. The R/T part-detail HTML pages
   exist and carry the requested MPN in `<title>`/meta/og/twitter and in the
   microdata breadcrumb, but those fields are template-injected
   ("dynamic Part Number") and must NOT be treated as independent identity
   evidence for R/T. The 4D-D authority chain must therefore anchor on the
   BASE catalog record (strip trailing R/T → verify base in catalog → verify
   `is-ssd` → verify approved origin/path family), exactly as the reviewed
   policy in §7 proposes.
4. **`MICRON_PACKAGING_ALIAS` is a customer-defined retrieval relation.** No
   official Micron document was found stating that the final R/T on the 7500
   family denotes packaging/shipping variants (§10). The frozen customer
   requirement may define the retrieval relation; nothing in this report
   claims Micron documentation proves R/T packaging semantics.

---

## 2. Exact official URLs tested and HTTP facts

All requested URLs resolved with **HTTP 200**, `final URL == requested URL`
(**zero redirects**, therefore no origin-escape to review). Content-Type is
given per response. Retrieval timestamps are UTC ISO-8601.

| # | Requested URL | Final URL | Status | Content-Type | Retrieved (UTC) |
| --- | --- | --- | --- | --- | --- |
| P1 | `https://www.micron.com/products/storage/ssd/data-center-ssd/7500-ssd/part-catalog/part-detail/mtfdkcc3t8tgp-1bk1dabyy` | same | 200 | `text/html;charset=utf-8` | 2026-09-22T23:17:23.934Z |
| P2 | `https://www.micron.com/products/storage/ssd/data-center-ssd/7500-ssd/part-catalog/part-detail/mtfdkcc3t8tgp-1bk1dabyyr` | same | 200 | `text/html;charset=utf-8` | 2026-09-22T23:17:24.724Z |
| P3 | `https://www.micron.com/products/storage/ssd/data-center-ssd/7500-ssd/part-catalog/part-detail/mtfdkcc3t8tgp-1bk1dabyyt` | same | 200 | `text/html;charset=utf-8` | 2026-09-22T23:17:25.551Z |
| J1 | `https://www.micron.com/content/micron/us/en/products/storage/ssd/data-center-ssd/7500-ssd/part-catalog/part-detail/_jcr_content.products.json/getproductinfo/-/-/-/en_US/-/mtfdkcc3t8tgp-1bk1dabyy` | same | 200 | `application/json;charset=utf-8` | 2026-09-22T23:18:27.614Z |
| J2 | same as J1 with `.../mtfdkcc3t8tgp-1bk1dabyyr` | same | 200 | `application/json;charset=utf-8` | 2026-09-22T23:18:27.915Z |
| J3 | same as J1 with `.../mtfdkcc3t8tgp-1bk1dabyyt` | same | 200 | `application/json;charset=utf-8` | 2026-09-22T23:18:28.189Z |
| C1 | `https://www.micron.com/products/storage/ssd/data-center-ssd/7500-ssd` | same | 200 | `text/html;charset=utf-8` | 2026-09-22T23:18:29.301Z |
| D1 | `https://assets.micron.com/adobe/assets/urn:aaid:aem:6c0eb3c2-d749-4212-b2c0-19f0101f9848/renditions/original/as/7500-nvme-ssd-product-brief.pdf` | same | 200 | PDF body (no Content-Type header sent) | 2026-09-22T23:19:40.824Z |
| D2 | `https://assets.micron.com/adobe/assets/urn:aaid:aem:a25db53e-784a-411c-ab92-dbcbc8f8b268/renditions/original/as/7500-ssd-tech-prod-spec.pdf` | same | 200 | PDF body (no Content-Type header sent) | 2026-09-22T23:19:41.234Z |
| C2 | `https://www.micron.com/products/storage/ssd/data-center-ssd/7500-ssd/part-catalog` | same | 200 | `text/html;charset=utf-8` | 2026-09-22T23:20:11.205Z |
| J4 | `https://www.micron.com/content/micron/us/en/products/storage/ssd/data-center-ssd/7500-ssd/part-catalog/_jcr_content.products.json/getpartcatalog/storage/7500-ssd/-/en_US` | same | 200 | `application/json;charset=utf-8` | 2026-09-22T23:20:25.416Z |
| C3 | `https://www.micron.com/sales-support/customer-support/shipping-quantities` | same | 200 | `text/html;charset=utf-8` | 2026-09-22T23:21:04.752Z |

Negative probes (documented, not captured as fixtures):

| Probe | Result |
| --- | --- |
| `https://www.micron.com/content/.../part-detail/_jcr_content.download.json` (per-part Documents accordion endpoint, discovered in P1 HTML `data-apiresource-accordian`) | HTTP 400 Bad Request for anonymous GET, with and without Referer / X-Requested-With |
| `https://www.micron.com/products/.../part-catalog/part-detail/spd-data/<mpn>` (discovered in P1 HTML `data-spdpageurl`) | HTTP 404 Not Found for all three MPNs |

Redirect / origin review: every successful response above kept
`final URL == requested URL`. The only non-`www.micron.com` origins touched
were `assets.micron.com` (Micron AEM asset renditions) for D1/D2, and the two
PDFs were reached **via links published on the captured 7500 product page C1**
(`Download Product Brief` / `Download tech spec` anchors) — i.e.,
Micron-published asset URLs, not third-party hosts. No external API origin is
required by the recommended 4D-D v1 authority chain: the exact-MPN and
category anchors used (§4, §5) all live on `www.micron.com`.

---

## 3. Fixtures recorded (sanitized, immutable, verbatim response bodies)

Location: `tests/fixtures/pages/` (existing recorded-page fixture directory;
see its README for the recording policy). "Sanitized" = anonymous public GET
bodies only; no request headers, cookies, sessions, credentials, or private
data were recorded. SHA256 is of the stored bytes.

| Fixture | Source | Bytes | SHA256 |
| --- | --- | --- | --- |
| `micron_7500_part_detail_base.html` | P1 | 259,911 | `ecad996fa6f162db592b66eb024afb4e8d08d8234f30715763c1022c305ae184` |
| `micron_7500_part_detail_r.html` | P2 | 259,937 | `235570b251e0b38b6a089a10315e00629ed478845eda2eae8bed6b64d200f5ec` |
| `micron_7500_part_detail_t.html` | P3 | 259,937 | `6c8014a5c8ac4f7c8dff0b76731d55400438fbcbb38affd1db6bc3fe23958910` |
| `micron_7500_getproductinfo_base.json` | J1 | 1,232 | `e7edaec36f0c33d2a9294773a33c6718cad7317d8c2f43dafb38cf365ac0da14` |
| `micron_7500_getproductinfo_r.json` | J2 | 54 | `74f57811780d78623e1da3586a53fed2f0bd2f507fd185946550f2f3424d7d66` |
| `micron_7500_getproductinfo_t.json` | J3 | 54 | `74f57811780d78623e1da3586a53fed2f0bd2f507fd185946550f2f3424d7d66` |
| `micron_7500_product_page.html` | C1 | 277,936 | `2d1ab35f2ba492335f801bd7a96b820f799f8fb465306652f0963be8578ca4d6` |
| `micron_7500_product_brief.pdf` | D1 | 318,063 | `f6782b305f93dc98e9e05635e34411439baa601620e5ba4f42578838618795e7` |
| `micron_7500_tech_prod_spec.pdf` | D2 | 328,747 | `5a772d686095472455194207fd575350a6ef685d063dc366682379245b14cc1f` |
| `micron_7500_part_catalog_page.html` | C2 | 268,932 | `a06a963c8fd9b03afd6390a3c6246c11bea9e2af5086b8da94f460877a7d085c` |
| `micron_7500_part_catalog.json` | J4 | 24,060 | `160d4fe97a5df5249e8f6404f6b005c0515fab4def1b4668fdaf87c727600743` |
| `micron_shipping_quantities.html` | C3 | 258,137 | `0c342ade9fd6817a9ee392357352f71d567b22a9bd2dfd97393ac938a6fef7ab` |

Determinism note (for the "static enough for runtime" question, §11): the
part-detail HTML pages are **server-side rendered** (the MPN appears in the
raw HTML without any JS), and repeated anonymous GETs of all three pages
returned byte-identical bodies (SHA256 matching the fixtures above) across
3–4 repeats spaced ~2 s apart. One transient byte-difference (same length) was
observed on the very first repeat-fetch window, consistent with an AEM edge
cache refresh; all subsequent repeats were identical. The structured JSON
endpoints (J1/J4) returned byte-identical bodies on immediate repeat (cached
AEM model responses; J1 even carries a stable `fetched-at` value across
repeats).

---

## 4. Exact MPN structural anchors found (raw response, per page)

The raw HTML of each part-detail page contains the exact, uppercase MPN in
eight source-published locations (verified by exact-case string search over
the fixture bytes; 26 case-insensitive hits total per page, the remainder
being the lowercase URL path inside `canonical`/`og:url` — which is NOT
counted here):

**BASE — `micron_7500_part_detail_base.html`, MPN `MTFDKCC3T8TGP-1BK1DABYY`:**

1. `<title>MTFDKCC3T8TGP-1BK1DABYY 7500 NVMeTM SSD part detail | Micron Technology Inc.</title>`
2. `<meta name="description" content="Discover all you need to know about Micron's part detail number MTFDKCC3T8TGP-1BK1DABYY with product specs, downloadable datasheets, and more."/>`
3. `<meta name="title" content="MTFDKCC3T8TGP-1BK1DABYY 7500 NVMeTM SSD part detail"/>`
4. `<meta property="og:title" content="MTFDKCC3T8TGP-1BK1DABYY 7500 NVMeTM SSD part detail"/>`
5. `<meta property="og:description" content="...part detail number MTFDKCC3T8TGP-1BK1DABYY..."/>`
6. `<meta property="twitter:title" content="MTFDKCC3T8TGP-1BK1DABYY 7500 NVMeTM SSD part detail"/>`
7. `<meta property="twitter:description" content="...part detail number MTFDKCC3T8TGP-1BK1DABYY..."/>`
8. Microdata `schema.org/BreadcrumbList`, position 8 (active page item):
   `<span itemprop="name">MTFDKCC3T8TGP-1BK1DABYY</span>` inside
   `<ol class="cmp-breadcrumb__list" itemscope itemtype="http://schema.org/BreadcrumbList">`

**R — `micron_7500_part_detail_r.html`, MPN `MTFDKCC3T8TGP-1BK1DABYYR`:**
identical eight locations (title / meta description / meta title / og:title /
og:description / twitter:title / twitter:description / breadcrumb
`itemprop="name"` span) with the exact string `MTFDKCC3T8TGP-1BK1DABYYR`.

**T — `micron_7500_part_detail_t.html`, MPN `MTFDKCC3T8TGP-1BK1DABYYT`:**
identical eight locations with the exact string `MTFDKCC3T8TGP-1BK1DABYYT`.

**Structured-JSON anchors (Micron-owned endpoints discovered inside the
captured HTML):**

- `micron_7500_getproductinfo_base.json` (J1 — endpoint published in P1 HTML
  `data-apiresource` attribute):
  - `"part-title": "MTFDKCC3T8TGP-1BK1DABYY"` (exact case)
  - `"part-number": "mtfdkcc3t8tgp-1bk1dabyy"`
  - `"product-tag": "micron:products/storage/ssd/data-center-ssd/7500-ssd/mtfdkcc3t8tgp-1bk1dabyy"`
  - `"data-source": "DATABASE"`, plus 12 concrete detail values
    (`Capacity 3840GB`, `Product Name 7500 PRO`, `Module Version U.3`,
    `Technology TLC`, `Module Box Qty 20`, `Part Status Code Production`, ...)
    that cannot be templated from the URL.
- `micron_7500_part_catalog.json` (J4 — endpoint published in C2 HTML
  `data-apiresource` attribute), one of 24 catalog rows:
  - `"part-number": "MTFDKCC3T8TGP-1BK1DABYY"` (exact case)
  - `"part-key": "mtfdkcc3t8tgp-1bk1dabyy"`
  - `"part-name": "7500 4TB U.3 SSD"`
  - `attr[]` including `{"name":"SSD","id":"is-ssd","value":true}`,
    `{"name":"Capacity","id":"capacity","value":"3840GB"}`,
    `{"name":"Product Name","id":"product_name","value":"7500 PRO"}`,
    `{"name":"Module Box Qty","id":"mod_box_qty","value":"20"}`

**The R/T asymmetry (documented, not glossed over):**

- J2 (`.../getproductinfo/.../mtfdkcc3t8tgp-1bk1dabyyr`) returned exactly:
  `{"message":"Invalid Partnumber","response-code":"200"}` (54 bytes).
- J3 (`.../getproductinfo/.../mtfdkcc3t8tgp-1bk1dabyyt`) returned the identical
  body (same SHA256).
- J4 (`getpartcatalog`, 24 rows) contains **no row** for either the R or the T
  part number.
- The P1/P2/P3 HTML carries the comment `<!-- Updated logic for title and link
  to update dynamic Part Number -->` immediately above the breadcrumb span, and
  the Adobe data layer template is `dc:title: "{1} {2} part detail"` (with
  `dc:description` similarly `{1}`-parameterized). This is direct
  source-published evidence that the title/meta/breadcrumb MPN on a
  part-detail page is **template-injected from the requested part number**.

Consequence: for R and T, the raw HTML metadata containing the exact MPN is
best characterized as a **request-echo inside a Micron-published template**,
not as an independent catalog assertion. For BASE, the exact MPN is
independently corroborated by two structured catalog records (J1, J4) with
concrete, non-templatable values. This asymmetry is the core finding of PRE2
and is binding for the 4D-D v1 authority design: **the catalog record (base)
owns the MPN proof; the R/T pages never do.**

---

## 5. SSD / category structural anchors (exact raw evidence)

Mechanically attributable, source-published SSD category evidence:

1. **Structured catalog attribute (strongest):** J4 row for
   `MTFDKCC3T8TGP-1BK1DABYY` —
   `"attr": [ ... { "name": "SSD", "id": "is-ssd", "value": true }, ... ]`
   This is an explicit boolean product-type flag in Micron's own parts catalog
   data source.
2. **Structured per-part record:** J1 — `"category": "data-center-ssd"`,
   `"sub-category": "7500-ssd"`, `"product_name": "7500 PRO"`,
   `"part-name": "7500 4TB U.3 SSD"` (J4).
3. **Microdata breadcrumb** (all three part-detail pages, identical chain):
   position 4 `<span itemprop="name">SSD</span>` (link
   `/products/storage/ssd`), position 5 `Data center SSD`, position 6
   `7500 NVMe SSD`, position 7 `7500 NVMe SSD part catalog`, position 8 the
   part number.
4. **Visible family eyebrow** (part-detail pages):
   `<span class="cmp-title__eyebrow-text">7500 NVMeTM SSD</span>`.
5. **Titles:** `<title>... 7500 NVMeTM SSD part detail | Micron Technology
   Inc.</title>`; product page C1 `<title>7500 NVMe SSD | Micron Technology
   Inc.</title>`.

No generic-Memory category anchor was captured for these MPNs, and none is
claimed. 4D-D v1 must be scoped **SSD ONLY**, which the evidence supports.

---

## 6. 7500 product brief and part-number structure (supporting evidence)

Captured the official 7500 product brief (D1) linked from the 7500 product
page (C1, "Download Product Brief"). Page 3, section **"Micron 7500 SSD Part
Numbers"** publishes:

- Example structure: `MT FD K CC 960 T GP - 1 BK 4 J AB YY`
- "Micron 7500 SSD part number information is provided below for
  configuration-dependent values (shown in bold). Other part number values in
  the example part number are fixed. See the parts catalog at micron.com/7500
  for more information."
- Drive Capacity: `960 = 960GB`, `1T9 = 1.92TB`, **`3T8 = 3.84TB`**,
  `7T6 = 7.68TB`, `15T3 = 15.36TB` (and MAX densities)
- Security Features: `D = OCP 2.0 + Opal 2.01`, `J = OCP 2.0 + Non-SED`
- Sector Size: `1 = 512 bytes`, `4 = 4096 bytes`
- Product Family: **`GP = 7500 PRO`**, `GQ = 7500 MAX`

This supports (a) the family/category reading of the MPN family and (b) the
specific customer MPN prefix (`3T8` → 3.84 TB, `GP` → 7500 PRO — matching the
J1/J4 values `Capacity 3840GB`, `Product Name 7500 PRO`). It is **supporting
family evidence only**: neither the brief nor the tech spec publishes the full
exact customer MPNs, and no exact-MPN proof is derived from the pattern.

Also captured the official 7500 tech product spec (D2, "Download tech spec").
Page 2, **"Part Numbering Information" / "Figure 1: Part Number"**, publishes
`MT FD K CC 960 T GP - 1 BK 4 J AB YY ES` with field definitions identical to
the brief, plus `ES` = "Extended Firmware Features". **No R/T field is
defined.**

---

## 7. Manufacturer authority policy (proposed, reviewed scope)

Manufacturer is established by a **reviewed authority policy**, not hostname
inference. The policy under review for 4D-D v1:

```
manufacturer = "Micron"
approved origin = https://www.micron.com
category = SSD
approved path family =
    /products/storage/ssd/.../part-catalog/part-detail/<mpn>
```

Rationale grounded in captured evidence:

- `https://www.micron.com` is Micron's official corporate/product domain
  (page titles end "Micron Technology Inc."; `twitter:site =
  https://twitter.com/MicronTech`; `product-tag` values are
  `micron:products/...`). The part-detail and catalog records in §4/§5 are
  Micron-published catalog data on that origin.
- The policy may own `manufacturer = Micron` **because** the source is an
  explicitly reviewed Micron-controlled product catalog origin + path family.
- The policy does **NOT** own the MPN. The exact-MPN proof must always come
  from a captured/verified document or structured record (BASE: J1
  `part-title` and/or J4 `part-number` row; the part-detail HTML metadata is
  admissible only insofar as it is corroborated by those structured records for
  the base part, and is never admissible as independent identity evidence for
  an R/T request).
- **Explicitly rejected (circular):** "the URL is on micron.com, therefore the
  arbitrary requested MPN is a Micron part." The captured `Invalid
  Partnumber` responses for arbitrary-but-similar strings would defeat that
  rule; the structured record check is what defeats it mechanically.
- `assets.micron.com` is a Micron AEM asset origin (document PDFs). It is
  acceptable as a **document** origin for family/category support (linked from
  Micron-published pages), but the recommended 4D-D v1 MPN/category authority
  chain does not require it.
- Redirect behavior: no redirect occurred on any captured URL; the policy's
  "stay within approved origin" check is trivially satisfied and remains a
  required runtime assertion for future captures.

---

## 8. Proof that URL-path echo is NOT being used as MPN authority

1. The lowercase MPN inside `rel="canonical"` / `og:url` / `data-apiresource`
   URLs was explicitly excluded from the §4 anchor count (only non-URL,
   non-path fields are listed as evidence).
2. The raw HTML itself proves the title/meta/breadcrumb values are
   template-injected from the request ("dynamic Part Number" comment;
   `"{1} {2} part detail"` data-layer template). A page is therefore rendered
   for ANY string in the path — which is exactly why the structured
   `getproductinfo`/`getpartcatalog` record (which says `Invalid Partnumber`
   for R/T) is the only non-circular identity anchor.
3. The fixture filenames contain the MPN only as local naming; no anchor in
   §4 is derived from a filename.
4. No Serper snippet, no search result, no browser address-bar text is used
   anywhere in this report.

---

## 9. Micron structured endpoints discovered

| Endpoint (www.micron.com) | Discovered in | Behavior |
| --- | --- | --- |
| `/_jcr_content.products.json/getproductinfo/-/-/-/en_US/-/<mpn-lower>` (per-part record) | P1 HTML `data-apiresource` | 200 + full record for BASE; 200 + `{"message":"Invalid Partnumber"}` for R and T |
| `/_jcr_content.products.json/getpartcatalog/storage/7500-ssd/-/en_US` (family catalog, 24 rows) | C2 HTML `data-apiresource` | 200; rows carry `part-number`, `part-name`, 13 `attr[]` entries incl. `is-ssd` |
| `/_jcr_content.download.json` (per-part Documents accordion) | P1 HTML `data-apiresource-accordian` | 400 Bad Request anonymously (not capturable without a session; not required) |
| `/part-catalog/part-detail/spd-data/<mpn-lower>` (SPD data page) | P1 HTML `data-spdpageurl` | 404 for all three MPNs |

These are standard Adobe AEM model endpoints published in the page's own HTML
attributes — i.e., the mechanism Micron uses to populate the part-detail page
client-side. Runtime 4D-D v1 may use `getproductinfo` (per requested/base
MPN) and/or `getpartcatalog` (family) as the structured-record source, both on
the approved origin.

---

## 10. R/T packaging semantics — official documentation search result

Sources checked (all official, all captured or probed above):

- 7500 product brief (D1): part-number section defines capacity/security/
  sector-size/family fields only. **No R/T definition.**
- 7500 tech product spec (D2): Figure 1 defines fields + `ES` suffix only.
  **No R/T definition.**
- 7500 part catalog (J4/C2): 24 base part rows; R/T not listed as parts.
  **No R/T definition.**
- Shipping Quantities page, doc CSN-04 (C3): "All Micron® semiconductor parts
  are shipped either in product-specific trays or tubes or product-specific
  tape-and-reel packages." + "For Micron memory products, use the following
  charts to determine the order quantity best suited to your needs. For more
  part number information, refer to Micron's Part Numbering Guides."
  **No R/T suffix definition for the 7500 SSD family.** (The page's own
  Part Numbering Guides are the memory-product guides; none was found that
  documents a trailing R/T packaging meaning for this SSD family. Micron's
  tech-docs search API is Base64-gzip encoded and was not reverse-engineered
  for PRE2; the guides referenced from CSN-04 were not located among the
  captured 7500 product-page document set.)

**Conclusion:** No official Micron statement was found that the final R/T on
the 7500 SSD family denotes packaging/shipping variants. Per the task rule,
this does NOT invalidate the customer requirement: the frozen customer rule
may define the retrieval relation `MICRON_PACKAGING_ALIAS` (manufacturer +
category eligibility independently established, §4–§7). This report makes no
claim that Micron documentation proves R/T packaging semantics, and the 4D-D
implementation must label alias rows as a customer-defined retrieval relation,
not as manufacturer-published packaging data.

---

## 11. Blocking behavior / JS dependency

- No bot-wall, no login, no CAPTCHA, no cookie requirement on any captured URL
  (all anonymous GETs, HTTP 200).
- The part-detail **identity metadata** (title/meta/og/twitter/breadcrumb,
  §4) and the **family eyebrow** are in the raw server-rendered HTML — no JS
  required.
- The **product detail values** (capacity, product name, specs) are loaded
  client-side from `getproductinfo` (J1) — that endpoint is directly fetchable
  anonymously (§9), so the full authority chain is achievable with plain HTTP
  GETs and no browser.
- The part-catalog table rows are loaded client-side from `getpartcatalog`
  (J4) — also directly fetchable anonymously.
- The per-part "Documents" accordion (`download.json`) returned 400 to
  anonymous GETs — a soft JS/session dependency. It is NOT required for the
  4D-D v1 MPN/category authority (document retrieval for 6D-style datasheet
  enrichment is a separate, already-solved capability).

---

## 12. Determinism / runtime suitability verdict

- Three part-detail HTML pages: byte-stable across repeated anonymous GETs
  (§3 note); MPN metadata server-side rendered; no redirect.
- `getproductinfo` / `getpartcatalog` JSON: byte-stable on repeat (AEM-cached
  model responses), stable Content-Type `application/json;charset=utf-8`.
- Caveat recorded: one transient cache-refresh byte-difference was observed
  on first refetch of the HTML pages; a runtime fetcher must treat the
  response as point-in-time evidence (record retrieved_at + SHA256 per
  capture, as this report does) rather than assuming permanent immutability.
- Verdict: **static/simple-HTTP suitable** for the 4D-D v1 authority chain
  (no browser, no JS, no session, no redirect).

---

## 13. Customer rule vs. manufacturer evidence (explicit distinction)

| Item | Authority | Evidence |
| --- | --- | --- |
| "final R/T may identify packaging variants" | **Customer rule** (frozen requirement) | Not manufacturer-documented (§10) |
| `MICRON_PACKAGING_ALIAS` retrieval relation | **Customer rule** | Permitted because Micron + SSD eligibility is independently established (§4–§7) |
| Manufacturer = Micron | **Reviewed policy** over approved origin/path family | §7 |
| Category = SSD | **Manufacturer structured record** | `is-ssd: true` (J4), `category: "data-center-ssd"` (J1), breadcrumb/title (§5) |
| Exact base MPN identity | **Manufacturer structured record** | J1 `part-title`, J4 `part-number` row (§4) |
| Exact R/T MPN "proof" | **None independent** — R/T are template echoes of the request | §4 asymmetry; J2/J3 `Invalid Partnumber` |
| Alias row may enter Machine Price / Reviewed Price / deterministic identity | **Forbidden by 4D-D design** | PLAN §26.7 (retrieval/relation only) |

---

## 14. 4D-D v1 authority chain implied by this evidence (for the design phase — NOT implemented here)

For a requested MPN on an approved Micron origin/path family:

1. Policy check: origin `https://www.micron.com`, path family
   `/products/storage/ssd/.../part-catalog/part-detail/<mpn>` (or the
   equivalent structured-record URL form).
2. If the request ends in `R` or `T`, derive the base by stripping exactly
   one final character; the base must be non-empty and distinct.
3. Fetch the BASE structured record (`getproductinfo` for the base MPN and/or
   the base row in `getpartcatalog`). Require: record exists (not
   `Invalid Partnumber`), exact base MPN present in `part-title`/`part-number`
   (case-exact uppercase form), and `is-ssd == true` / SSD category anchor.
4. Only then is `manufacturer = Micron` + `category = SSD` established, and
   only then may the `MICRON_PACKAGING_ALIAS` relation generate retrieval
   aliases (base, base+R, base+T) for search/recall. Alias rows remain
   labeled reference rows; they never enter Machine Price, Reviewed Price,
   deterministic/semantic identity, or comparable scoring.
5. An R/T page's own HTML metadata is NOT sufficient to satisfy step 3.

No code implementing steps 1–5 exists in this repository. PRE2 is evidence
only.

---

## 15. 4D-C documentation correction (factual, accompanying this commit)

Stale post-freeze status lines in `docs/PRODUCT_INTELLIGENCE_PLAN.md` and
`docs/PRODUCT_INTELLIGENCE_STATUS.md` (which still read
`IMPLEMENTED / PENDING FINAL REVIEW`) were corrected to the frozen state:

- `PRODUCT-INTEL.4D-C — APPROVED / FROZEN`
- Frozen SHA: `4592b8966b703dfd6a72c3067d7b191314ff2968`
- Frozen test baseline: `4766 collected`

4D-D status lines now read `PLANNED / AUTHORITY EVIDENCE UNDER REVIEW`
(pre-PRE2 review of this document). No 4D-D redesign was performed.

---

## 16. Files changed in this evidence commit

- Added: 12 fixtures under `tests/fixtures/pages/` (§3)
- Added: `docs/MICRON_ALIAS_AUTHORITY_EVIDENCE.md` (this file)
- Modified: `docs/PRODUCT_INTELLIGENCE_PLAN.md` (4D-C/4D-D status lines only)
- Modified: `docs/PRODUCT_INTELLIGENCE_STATUS.md` (4D-C/4D-D status lines only)
- Modified: NO file under `product_intelligence/` or `tests/*.py`

---

*End of PRE2 evidence report.*
