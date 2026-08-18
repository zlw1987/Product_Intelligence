# Serper recorded fixtures (PRODUCT-INTEL.2C)

Real, recorded Serper responses used for offline regression testing of
`product_intelligence.providers.serper`. Nothing here is fabricated: each file
is the verbatim response body from one live Serper call, captured during 2C
development.

## `real_verified_mz_ql23t800_organic_search.json`

| Field | Value |
| --- | --- |
| Recording date | 2026-08-17 |
| Provider | Serper (`https://google.serper.dev/search`) |
| Mode | Ordinary Google Search (`type: "search"`), not Google Shopping |
| Query | `MZ-QL23T800` — the manufacturer part number from evaluation corpus case `REAL-0001` (`evaluation/corpus/real_verified.json`), a public Samsung enterprise SSD SKU. No description text was included in the query. |
| Live calls made to produce this fixture | 1 |

**Sanitization performed:** the response was inspected before saving. It
contains no API key, no authorization header, no request-secret, no cookie, no
personal or customer information, and no internal commercial data — Serper's
JSON response body does not echo the request credential. The file is saved
byte-for-byte as returned (`searchParameters`, `organic`, `relatedSearches`,
`credits`), because every field present is public: result titles, snippets,
URLs, star ratings, and the query MPN. Nothing was redacted because nothing
needed to be.

This fixture is consumed only by `tests/providers/test_serper_provider.py`,
offline, via `_map_serper_payload`. The normal `pytest` run makes zero calls
to Serper.
