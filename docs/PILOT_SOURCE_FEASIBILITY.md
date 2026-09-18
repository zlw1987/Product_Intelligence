# Product Intelligence — Pilot Source Feasibility Audit (4D-PRE)

**Phase:** PRODUCT-INTEL.4D-PRE  
**Status:** PLANNED — evidence collection only, no production changes  
**Auditor:** To be completed by pilot operator

---

## Purpose

Audit the customer's 12 preferred public websites to determine per-site:

1. Whether a stable, repeatable direct lookup mechanism exists.
2. Whether the site returns structured product data via plain static HTTP.
3. What evidence is obtainable (MPN, price, currency, availability, condition, seller).
4. Whether direct lookup can reduce Serper credit usage.
5. Recommendation: `DIRECT`, `SERPER_FALLBACK`, or `UNSUITABLE`.

This audit produces **evidence only**. No production code, no tests, no
architecture change is made during 4D-PRE. Findings inform 4D-A design.

---

## Explicit Non-Goals

- **No production code.** This is an evidence/audit worksheet.
- **No scraping infrastructure.** Do not acquire headless browsers, proxy pools,
  or managed scraping services to complete this audit.
- **No per-site adapter.** Do not write extraction code for any site here.
- **No fabrication.** If a site has not been tested, its entry remains PENDING.
  Do not guess findings.
- **No identity authority.** Preferred source status from this audit affects
  acquisition priority only. It does not grant any identity or authority
  advantage over existing 2A/3C contracts.

---

## Audit Methodology

For each site:

1. Select a known MPN that the customer routinely researches.
2. Attempt a direct lookup using the site's primary search or product page URL.
3. Record the mechanism, the response, and what structured data is present.
4. If the site requires JavaScript rendering for product data, record that
   finding. 4D-PRE does not install, implement, or acquire browser/scraping
   infrastructure. Whether browser support is justified is a later 4D-A design
   decision based on the completed audit evidence.
5. If the site blocks automated access (403, CAPTCHA, interstitial), record that.
6. If a stable direct URL pattern exists for a given MPN, record it.
7. Assess whether the generic 3A extraction path (JSON-LD, flat meta) produces
   usable observations from the site's product pages.
8. Recommend: `DIRECT`, `SERPER_FALLBACK`, or `UNSUITABLE`.

---

## Recommendation Vocabulary

| Value | Meaning |
| --- | --- |
| `DIRECT` | Stable direct lookup exists and returns usable structured data via static HTTP. Direct lookup is a viable primary acquisition path. |
| `SERPER_FALLBACK` | Direct lookup exists but is unreliable, partial, or insufficient for all MPNs. Serper remains the primary discovery path; direct lookup may supplement where available. |
| `UNSUITABLE` | No viable direct acquisition path. Site blocks automated access, requires full JS rendering with no static data, or provides no usable product evidence. |

---

## Audit Entries

### cdw.com

| Field | Value |
| --- | --- |
| source / domain | cdw.com |
| direct lookup mechanism | PENDING |
| tested search shape | PENDING |
| stable product URL? | PENDING |
| static HTML? | PENDING |
| JS required? | PENDING |
| bot / blocking behavior | PENDING |
| explicit MPN evidence? | PENDING |
| price? | PENDING |
| currency? | PENDING |
| availability? | PENDING |
| condition? | PENDING |
| source-specific extraction needed? | PENDING |
| recommendation | PENDING |
| evidence / notes | PENDING |

### newegg.com

| Field | Value |
| --- | --- |
| source / domain | newegg.com |
| direct lookup mechanism | PENDING |
| tested search shape | PENDING |
| stable product URL? | PENDING |
| static HTML? | PENDING |
| JS required? | PENDING |
| bot / blocking behavior | PENDING |
| explicit MPN evidence? | PENDING |
| price? | PENDING |
| currency? | PENDING |
| availability? | PENDING |
| condition? | PENDING |
| source-specific extraction needed? | PENDING |
| recommendation | PENDING |
| evidence / notes | PENDING |

*Note: During 3A, `www.newegg.com` returned HTTP 200 with a JS shell
(`JS_SHELL_OR_NO_USEFUL_STATIC_DATA`). It rendered product data client-side.
This may require `SERPER_FALLBACK` or browser rendering — but browser
infrastructure is not acquired in 4D-PRE.*

### serversupply.com

| Field | Value |
| --- | --- |
| source / domain | serversupply.com |
| direct lookup mechanism | PENDING |
| tested search shape | PENDING |
| stable product URL? | PENDING |
| static HTML? | PENDING |
| JS required? | PENDING |
| bot / blocking behavior | PENDING |
| explicit MPN evidence? | PENDING |
| price? | PENDING |
| currency? | PENDING |
| availability? | PENDING |
| condition? | PENDING |
| source-specific extraction needed? | PENDING |
| recommendation | PENDING |
| evidence / notes | PENDING |

*Note: During 3A, `www.serversupply.com` returned `BLOCKED_403` to the
standard-library fetcher. This does not necessarily mean a different approach
would succeed — a 403 at the HTTP layer is an access decision.*

### harddiskdirect.com

| Field | Value |
| --- | --- |
| source / domain | harddiskdirect.com |
| direct lookup mechanism | PENDING |
| tested search shape | PENDING |
| stable product URL? | PENDING |
| static HTML? | PENDING |
| JS required? | PENDING |
| bot / blocking behavior | PENDING |
| explicit MPN evidence? | PENDING |
| price? | PENDING |
| currency? | PENDING |
| availability? | PENDING |
| condition? | PENDING |
| source-specific extraction needed? | PENDING |
| recommendation | PENDING |
| evidence / notes | PENDING |

### esaitech.com

| Field | Value |
| --- | --- |
| source / domain | esaitech.com |
| direct lookup mechanism | PENDING |
| tested search shape | PENDING |
| stable product URL? | PENDING |
| static HTML? | PENDING |
| JS required? | PENDING |
| bot / blocking behavior | PENDING |
| explicit MPN evidence? | PENDING |
| price? | PENDING |
| currency? | PENDING |
| availability? | PENDING |
| condition? | PENDING |
| source-specific extraction needed? | PENDING |
| recommendation | PENDING |
| evidence / notes | PENDING |

### serverorbit.com

| Field | Value |
| --- | --- |
| source / domain | serverorbit.com |
| direct lookup mechanism | PENDING |
| tested search shape | PENDING |
| stable product URL? | PENDING |
| static HTML? | PENDING |
| JS required? | PENDING |
| bot / blocking behavior | PENDING |
| explicit MPN evidence? | PENDING |
| price? | PENDING |
| currency? | PENDING |
| availability? | PENDING |
| condition? | PENDING |
| source-specific extraction needed? | PENDING |
| recommendation | PENDING |
| evidence / notes | PENDING |

### directmacro.com

| Field | Value |
| --- | --- |
| source / domain | directmacro.com |
| direct lookup mechanism | PENDING |
| tested search shape | PENDING |
| stable product URL? | PENDING |
| static HTML? | PENDING |
| JS required? | PENDING |
| bot / blocking behavior | PENDING |
| explicit MPN evidence? | PENDING |
| price? | PENDING |
| currency? | PENDING |
| availability? | PENDING |
| condition? | PENDING |
| source-specific extraction needed? | PENDING |
| recommendation | PENDING |
| evidence / notes | PENDING |

### dihuni.com

| Field | Value |
| --- | --- |
| source / domain | dihuni.com |
| direct lookup mechanism | PENDING |
| tested search shape | PENDING |
| stable product URL? | PENDING |
| static HTML? | PENDING |
| JS required? | PENDING |
| bot / blocking behavior | PENDING |
| explicit MPN evidence? | PENDING |
| price? | PENDING |
| currency? | PENDING |
| availability? | PENDING |
| condition? | PENDING |
| source-specific extraction needed? | PENDING |
| recommendation | PENDING |
| evidence / notes | PENDING |

### centralcomputer.com

| Field | Value |
| --- | --- |
| source / domain | centralcomputer.com |
| direct lookup mechanism | PENDING |
| tested search shape | PENDING |
| stable product URL? | PENDING |
| static HTML? | PENDING |
| JS required? | PENDING |
| bot / blocking behavior | PENDING |
| explicit MPN evidence? | PENDING |
| price? | PENDING |
| currency? | PENDING |
| availability? | PENDING |
| condition? | PENDING |
| source-specific extraction needed? | PENDING |
| recommendation | PENDING |
| evidence / notes | PENDING |

### memory4less.com

| Field | Value |
| --- | --- |
| source / domain | memory4less.com |
| direct lookup mechanism | PENDING |
| tested search shape | PENDING |
| stable product URL? | PENDING |
| static HTML? | PENDING |
| JS required? | PENDING |
| bot / blocking behavior | PENDING |
| explicit MPN evidence? | PENDING |
| price? | PENDING |
| currency? | PENDING |
| availability? | PENDING |
| condition? | PENDING |
| source-specific extraction needed? | PENDING |
| recommendation | PENDING |
| evidence / notes | PENDING |

### fs.com

| Field | Value |
| --- | --- |
| source / domain | fs.com |
| direct lookup mechanism | PENDING |
| tested search shape | PENDING |
| stable product URL? | PENDING |
| static HTML? | PENDING |
| JS required? | PENDING |
| bot / blocking behavior | PENDING |
| explicit MPN evidence? | PENDING |
| price? | PENDING |
| currency? | PENDING |
| availability? | PENDING |
| condition? | PENDING |
| source-specific extraction needed? | PENDING |
| recommendation | PENDING |
| evidence / notes | PENDING |

### naddod.com

| Field | Value |
| --- | --- |
| source / domain | naddod.com |
| direct lookup mechanism | PENDING |
| tested search shape | PENDING |
| stable product URL? | PENDING |
| static HTML? | PENDING |
| JS required? | PENDING |
| bot / blocking behavior | PENDING |
| explicit MPN evidence? | PENDING |
| price? | PENDING |
| currency? | PENDING |
| availability? | PENDING |
| condition? | PENDING |
| source-specific extraction needed? | PENDING |
| recommendation | PENDING |
| evidence / notes | PENDING |

---

## Summary Template (to be completed after all sites audited)

| Source | Recommendation | Key Finding |
| --- | --- | --- |
| cdw.com | PENDING | PENDING |
| newegg.com | PENDING | PENDING |
| serversupply.com | PENDING | PENDING |
| harddiskdirect.com | PENDING | PENDING |
| esaitech.com | PENDING | PENDING |
| serverorbit.com | PENDING | PENDING |
| directmacro.com | PENDING | PENDING |
| dihuni.com | PENDING | PENDING |
| centralcomputer.com | PENDING | PENDING |
| memory4less.com | PENDING | PENDING |
| fs.com | PENDING | PENDING |
| naddod.com | PENDING | PENDING |

---

## Notes

- Existing 3A findings (from the `MZ-QL23T800` sample) are noted inline where
  relevant. They are not assumed to represent the full picture for all MPNs
  on a given site.
- 4D-PRE does not acquire any new infrastructure. Manual browser inspection and
  standard-library fetch tests are sufficient.
- Findings from this audit inform 4D-A design. The exact fallback trigger
  (e.g., "N direct results means skip Serper") is a 4D-A design decision
  after evidence exists — it is NOT pre-decided here.
