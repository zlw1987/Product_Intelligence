# PILOT-UX-WORKBENCH-A1 — Visual verification screenshots

Fixture-based previews (synthetic data, no production data, no live paid
calls), captured with headless Chrome at the three required viewports.

Server setup: `python scripts/preview_fixtures.py` builds a throwaway
preview SQLite DB (via `PI_SQLITE_PATH`) with the eight runs listed
below. Two dev servers: port 8101 with
`PI_VENDOR_PRICE_ALLOWED_CIDRS=127.0.0.1/32` (vendor ALLOWED) and port
8102 without that variable (vendor DENIED, fail-closed default).

| File | Case | Viewport |
| --- | --- | --- |
| 01_intake_empty_1440.png | research intake, empty input | desktop 1440 |
| 02_intake_prefill_1440.png | intake with FoxPro-style prefilled MPN + description | desktop 1440 |
| 03_intake_empty_768.png | research intake, empty input | tablet 768 |
| 04_intake_empty_390.png | research intake, empty input | mobile 390 |
| 05_report_multiquote_allowed_1440.png | completed report, 2 vendor + 1 public quote, FX evidence (ALLOWED connection) | desktop 1440 |
| 06_report_multiquote_allowed_768.png | same | tablet 768 |
| 07_report_multiquote_allowed_390.png | same | mobile 390 |
| 08_report_multiquote_denied_1440.png | same run from a DENIED connection (vendor data absent, neutral notice) | desktop 1440 |
| 09_report_zeroquote_1440.png | completed report with a source-published $0 quote (B1 verification note) | desktop 1440 |
| 10_report_zeroquote_390.png | same | mobile 390 |
| 11_report_no_evidence_1440.png | completed report, no usable price evidence (UNKNOWN status, excluded listing) | desktop 1440 |
| 12_report_ai_review_1440.png | completed report with an AI-assisted review candidate (needs review) | desktop 1440 |
| 13_report_ai_review_390.png | same | mobile 390 |
| 14_report_comparable_1440.png | completed report with a comparable research result (FULL, one candidate) | desktop 1440 |
| 15_report_running_1440.png | running research state | desktop 1440 |
| 16_report_failed_1440.png | failed research state (retry action) | desktop 1440 |

Programmatic layout audit: `scripts/layout_probe.js` drives headless
Chrome over raw CDP (no dependencies) and reports, per case x viewport,
page-level horizontal overflow, elements escaping the viewport without an
`overflow-x: auto/scroll` ancestor, clipped text (overflow hidden /
ellipsis), unresolved in-page anchors, h1 count, and focusable element
count. Result for this revision: zero findings on every captured case.

Disclosure: the implementing model in this session has no image input, so
pixel-level visual review of these captures is left to the independent
reviewer; the layout audit above is the programmatic substitute.
