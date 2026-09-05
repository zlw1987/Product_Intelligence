# Specification Evidence Fixtures

## Real Manufacturer Fixtures

### real_samsung_pm9a3_mz_ql23t800.html

- **Source**: Samsung Business (manufacturer-controlled)
- **Source URL**: https://www.samsung.com/us/business/memory-storage/nvme-ssd/pm9a3-nvme-u-2-ssd-3-8tb-sku-mz-ql23t800/
- **Retrieval date**: 2026-09-04T19:39:16.717697+00:00 (actual HTTP retrieval)
- **Product identity**: Samsung PM9A3 NVMe U.2 3.84TB (MZ-QL23T800)
- **Authority**: AUTHORITATIVE
- **Fixture type**: REDUCED
- **Content retained**:
  - Two JSON-LD application/ld+json blocks (Product + BreadcrumbList) — verbatim from live page
  - `__NEXT_DATA__` script payload — the structured JSON embedded in static HTML
    (reduced to essential product metadata: product variants, defaultModelCode, category/type)
- **Content removed**: Navigation, styles, images, marketing copy (~200 KB), all
  JavaScript files, staticData UI config, reviews, delivery, trade-in data
- **Extraction result**: NO_OBSERVATIONS
  - JSON-LD Product: has name, sku, brand, offers, color — NO additionalProperty
  - JSON-LD BreadcrumbList: navigation breadcrumbs — not a Product
  - `__NEXT_DATA__`: valid JSON but contains only product variant metadata and UI config
    — NO specification label/value records for MZ-QL23T800
  - HTML body: no tables, no definition lists, no spec-related structures
  - Spec table is rendered by Next.js React components — not accessible via static HTTP
- **Why AUTHORITATIVE**: Samsung Business is the manufacturer's own product page

### real_seagate_nytro_5050_xp15360se70005.html

- **Source**: Seagate Technology (manufacturer-controlled support page)
- **Source URL**: https://www.seagate.com/support/enterprise-storage/solid-state-drives/nytro-5050/
- **Retrieval date**: 2026-09-04T20:42:23.551927+00:00 (actual HTTP retrieval)
- **Product identity**: Seagate Nytro 5050 NVMe SSD (XP15360SE70005 / Nytro 5350H 15.36TB)
- **Authority**: AUTHORITATIVE
- **Fixture type**: REDUCED
- **Content retained**: `var supportSpecsData = JSON.parse('[...]')` — the complete
  embedded JSON product data table with 81 records.
  Each record has: `skuNumber` (MPN), `title`, `features` (title/value/order triples).
- **Content removed**: Navigation, styles, images, marketing copy, all other
  scripts, tracking pixels, JSON-LD (WebPage/Organization), eCommerce config,
  analytics (~796 KB reduced to ~82 KB essential product data)
- **Extraction result**: 1 observation (Form Factor)
  - Raw value: "2.5in" (no space between number and unit)
  - Schema key: physical_form_factor (mapped via "Form Factor" -> physical_form_factor)
  - Normalization: "2.5in" -> "2.5-inch" (evidence-backed 6B correction)
  - Resolution state: VERIFIED (AUTHORITATIVE source, single canonical value)
- **Structure**: Embedded JavaScript JSON variable
  (`var supportSpecsData = JSON.parse('...')`) in a `<script>` tag.
  Array of 81 product records. Each record has `skuNumber` and `features[]`.
  MPN is in the `skuNumber` field. Features are title/value pairs.
- **Why AUTHORITATIVE**: Seagate is the manufacturer's own support page
- **SHA256**: 529298b0a440a5f652672cacf40cbd476f3d185b4837063fef58752d6192ddef
- **Size**: 81947 bytes

## Synthetic Fixtures (SUPERSEDED / DEVELOPMENT ARTIFACTS)

**WARNING**: These synthetic fixtures use extraction mechanisms that are
**NOT supported by production 6C**. They exist only as historical development
artifacts. The production 6C extraction mechanism accepts ONLY:

    var supportSpecsData = JSON.parse('...')

The following synthetic fixtures are **superseded** and are NOT tested
by production extraction:

### synthetic_jsonld_product.html

- **Purpose**: Historical test for JSON-LD additionalProperty/PropertyValue extraction
- **Status**: SUPERSEDED — JSON-LD extraction removed (no real manufacturer evidence)
- **Fields**: Capacity, Storage Protocol, PCIe Generation, Interface Connector,
  Endurance, Sequential Read, Random Read IOPS, Power Loss Protection,
  PCIe Lane Count, Unknown Field (ignored)
- **Includes**: BreadcrumbList sibling (should be ignored), 10 spec fields
  (9 recognized + 1 unknown)

### synthetic_html_table.html

- **Purpose**: Historical test for HTML table (label/value row) extraction
- **Status**: SUPERSEDED — HTML table extraction removed (no real manufacturer evidence)
- **Fields**: All 12 Enterprise SSD schema fields
- **Includes**: Rows with >2 cells (ignored), rows with 1 cell (ignored)

### synthetic_definition_list.html

- **Purpose**: Historical test for HTML definition list (dl/dt/dd) extraction
- **Status**: SUPERSEDED — definition list extraction removed (no real manufacturer evidence)
- **Fields**: All 12 Enterprise SSD schema fields
- **Includes**: Unknown labels (ignored)
