# PILOT-UX-WORKBENCH-A1 — Visual verification screenshots

Fixture-based previews (synthetic data, no production data, no live paid
calls), captured with headless Chrome at the three required viewports.

## PILOT-UX-WORKBENCH-A1-FU1 regeneration (this revision)

The A1 390px captures were cropped: the capture path's layout viewport was
wider than the requested 390 CSS px (headless Chrome clamps its window to a
minimum width and the captures were cropped to the requested size), so the
right side of the top bar, form, metadata and table was cut off — while the
A1 layout probe, which measured a *different* (CDP device-metrics) path with
a true 390px viewport and overflow-only checks, reported zero findings.
The pixel evidence (A1 `04_intake_empty_390.png`: top bar ran from x=12 to
the image edge x=389 with no background margin) is preserved in the git
history of the previous revision.

This revision regenerates every capture through
`scripts/capture_preview_screenshots.js`, which for every case × viewport:

1. sets `Emulation.setDeviceMetricsOverride(width, mobile = width < 500,
   deviceScaleFactor 1)`,
2. **asserts `window.innerWidth === requested`** (a CSS viewport that
   differs from the requested width fails the run, even when
   `document.scrollWidth == window.innerWidth`),
3. **asserts `<!DOCTYPE html>` is present and `document.compatMode ===
   "CSS1Compat"`** (standards mode; the A1 documents were quirks mode),
4. asserts no page-level horizontal overflow
   (`document.documentElement.scrollWidth <= window.innerWidth`),
5. asserts the expected content is present (and, for the DENIED shot, that
   no vendor label/price appears in any casing),
6. for full-page report shots grows the viewport to the document's full
   height (so no vertical scrollbar participates in the layout), re-asserts
   `innerWidth`, `clientWidth` and `scrollWidth`, and captures,
7. asserts the PNG pixel width equals the requested CSS width.

A shot whose viewport is not proven to be the requested width is NOT
written (a cropped image is worse than no image). The matching audit is
`scripts/layout_probe.js` (the same fidelity gate plus element-level
overflow/clipping/anchor checks); both read the run addresses from the
preview manifest `tmp_preview/preview_urls.json` (no hardcoded UUIDs).

Measured viewport metrics for this revision (all shots: `compatMode =
CSS1Compat`, `doctype = present`, `problems = []`):

| File | Requested | `innerWidth` | `clientWidth` | `scrollWidth` | PNG |
| --- | --- | --- | --- | --- | --- |
| 01_intake_empty_1440.png | 1440 | 1440 | 1440 | 1440 | 1440x900 |
| 02_intake_prefill_1440.png | 1440 | 1440 | 1440 | 1440 | 1440x900 |
| 03_intake_empty_768.png | 768 | 768 | 768 | 768 | 768x900 |
| 04_intake_empty_390.png | 390 | 390 | 390 | 390 | 390x780 |
| 05_report_multiquote_allowed_1440.png | 1440 | 1440 | 1440 | 1440 | 1440x1455 |
| 06_report_multiquote_allowed_768.png | 768 | 768 | 768 | 768 | 768x1799 |
| 07_report_multiquote_allowed_390.png | 390 | 390 | 390 | 390 | 390x2051 |
| 08_report_multiquote_denied_1440.png | 1440 | 1440 | 1440 | 1440 | 1440x1284 |
| 09_report_zeroquote_1440.png | 1440 | 1440 | 1440 | 1440 | 1440x1156 |
| 10_report_zeroquote_390.png | 390 | 390 | 390 | 390 | 390x1718 |
| 11_report_no_evidence_1440.png | 1440 | 1440 | 1440 | 1440 | 1440x974 |
| 12_report_ai_review_1440.png | 1440 | 1440 | 1440 | 1440 | 1440x1663 |
| 13_report_ai_review_390.png | 390 | 390 | 390 | 390 | 390x2216 |
| 14_report_comparable_1440.png | 1440 | 1440 | 1440 | 1440 | 1440x1486 |
| 15_report_running_1440.png | 1440 | 1440 | 1440 | 1440 | 1440x900 |
| 16_report_failed_1440.png | 1440 | 1440 | 1440 | 1440 | 1440x900 |

At 390 the top bar and cards now end at x≈377 with the page background
visible at the right edge (A1 original: top bar ran to the image edge).
The 8-column quote table (min-width 54rem) scrolls horizontally ONLY inside
its `.spec-table-wrapper` (designed `overflow-x: auto` container); no
page-level horizontal overflow exists at 390/768/1440.

## Server and data setup

`scripts/preview_fixtures.py` builds a fresh, disposable preview SQLite
database. FU1: it now REQUIRES an explicit `PI_PREVIEW_DB_DIR` (a
designated, disposable preview directory), plans a new uniquely named
`preview_<utc stamp>_<token>.sqlite3` file inside it, fails closed if that
file already exists, rejects the repository root and production/staging/
deployment-like directory names, canonicalizes all paths before
verification, and never deletes, truncates, overwrites or replaces any
existing database (a pre-existing `PI_SQLITE_PATH` is overridden, not
honored). Example:

    set PI_PREVIEW_DB_DIR=C:\dev\Product_Intelligence_A1\tmp_preview
    python scripts\preview_fixtures.py

The script writes the run addresses to `<preview-dir>/preview_urls.json`.
Two dev servers are then started against that database: port 8101 with
`PI_VENDOR_PRICE_ALLOWED_CIDRS=127.0.0.1/32` (vendor ALLOWED) and port 8102
without that variable (vendor DENIED, fail-closed default).

## Cases

| File | Case | Viewport |
| --- | --- | --- |
| 01_intake_empty_1440.png | research intake, empty input | desktop 1440 |
| 02_intake_prefill_1440.png | intake with FoxPro-style prefilled MPN + description | desktop 1440 |
| 03_intake_empty_768.png | research intake, empty input | tablet 768 |
| 04_intake_empty_390.png | research intake, empty input | mobile 390 |
| 05_report_multiquote_allowed_1440.png | completed report, 3 vendor + 1 public quote, FX evidence (ALLOWED connection) | desktop 1440 |
| 06_report_multiquote_allowed_768.png | same | tablet 768 |
| 07_report_multiquote_allowed_390.png | same | mobile 390 |
| 08_report_multiquote_denied_1440.png | same run from a DENIED connection (vendor data absent, neutral notice) | desktop 1440 |
| 09_report_zeroquote_1440.png | completed report with a source-published $0 quote (B1 verification note) | desktop 1440 |
| 10_report_zeroquote_390.png | same, with the quote table's designed horizontal scroll moved fully right so the B1 zero-price note (Market Use column, attached to its row) is visible | mobile 390 |
| 11_report_no_evidence_1440.png | completed report, no usable price evidence (UNKNOWN status, excluded listing) | desktop 1440 |
| 12_report_ai_review_1440.png | completed report with an AI-assisted review candidate (needs review) | desktop 1440 |
| 13_report_ai_review_390.png | same | mobile 390 |
| 14_report_comparable_1440.png | completed report with a comparable research result (FULL, one candidate) | desktop 1440 |
| 15_report_running_1440.png | running research state | desktop 1440 |
| 16_report_failed_1440.png | failed research state (retry action) | desktop 1440 |

The multi-quote fixture (P1) contains exactly 3 vendor observations
(Ingram, CDW, Synnex EU — the A1 README/docstring line "2 vendor + 1
public" misstated the generated fixture) + 1 public quote + FX evidence.
The 3-vendor + 1-public row count is what the ALLOWED captures show and
what the DENIED forbid-list ("Ingram (Vendor API)", "CDW (Vendor API)",
"Synnex EU (Vendor API)", all three vendor prices) pins.

Programmatic layout audit: `scripts/layout_probe.js` drives headless
Chrome over raw CDP (no dependencies) and reports, per case x viewport,
viewport fidelity (requested vs `innerWidth` / `clientWidth` /
`scrollWidth` / `visualViewport.width` / `compatMode` / doctype),
page-level horizontal overflow, elements escaping the viewport without an
`overflow-x: auto/scroll` ancestor, clipped text (overflow hidden /
ellipsis), unresolved in-page anchors, h1 count, and focusable element
count. It exits non-zero on any finding. Result for this revision:
22/22 case-viewport combinations pass (10 cases × their widths, incl.
390/768/1440).

Disclosure: the implementing model in this session has no image input, so
pixel-level visual review of these captures is left to the independent
reviewer; the layout audit above (with the FU1 viewport-fidelity gate) is
the programmatic substitute, and the measured metrics table is committed
next to it.
