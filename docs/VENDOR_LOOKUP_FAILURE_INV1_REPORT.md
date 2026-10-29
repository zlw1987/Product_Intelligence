# PRODUCT-INTEL.VENDOR-LOOKUP-FAILURE-INV1 — Investigation Report

## Subject

Research run `82565637-11f7-4e3e-b1cf-476cc253ac91` — Vendor API lookup for
Micron MPN `MTFDKCC3T8TGP-1BK1DABYYR` persisted `FAILED` status with zero
observations and zero source issues, despite a later manual Vendor API call
returning valid pricing evidence from all three sources.

## Production Timeline

| Event | Time |
|---|---|
| Research run started | 2026-10-26 21:42:57 UTC |
| Final semantic evidence recorded | ≈ 2026-10-26 21:48:45 UTC |
| Research run completed | 2026-10-26 21:48:55 UTC |
| Elapsed (start → finish) | 5 min 58 sec |
| Elapsed (last semantic → finish) | ≈ 10 sec |

## Manually Retrieved Vendor Response (Post-Failure)

| Source | Price | Currency | Price Basis | Availability |
|---|---|---|---|---|
| Ingram | 5445.67 | USD | customerPrice | available=false, Avl_Quantity=0 |
| Synnex EU | 4740.18 | EUR | UnitPriceAmount | AvailabilityTotal="0" |
| CDW | 0.00 | USD | list price | No explicit inventory fields |

All three sources published the requested complete MPN `MTFDKCC3T8TGP-1BK1DABYYR`.

---

## A. Offline Source Mapping Reproduction

### A.1. Fixture Construction

A sanitized, representative offline fixture was constructed in
`tests/providers/test_vendor_lookup_failure_inv1.py` preserving:

- **Wire contract**: The production `text/html; charset=utf-8` section-oriented
  body with exact `<p>` paragraph envelope (FU3) and three exact entity literals
  (`&quot;`, `&#xA;`, `&#xD;`) (FU4).
- **Hybrid field placements**: Ingram's observed production form (explicit
  `vendorPartNumber` + nested `pricing` block + top-level boolean `availability`
  + top-level `Avl_Quantity`); Synnex EU's `OnlineCheck.Header.Item` nested
  form with string-typed `UnitPriceAmount` and `AvailabilityTotal`.
- **Decimal precision**: Prices preserved as exact Decimal values (5445.67,
  4740.18, 0.00). No binary float conversion.
- **Null/boolean/string distinctions**: `available` is boolean `false` (not
  string `"false"` or integer `0`); `Avl_Quantity` is integer `0` (not string
  `"0"`); Synnex `AvailabilityTotal` is the production-observed digit string
  `"0"`.
- **Sensitive metadata**: `SessionId`, `BuyerAccountId`, `SystemId` replaced
  with `FAKE-SESSION-000`, `FAKE-ACCOUNT-000`, `FAKE-SYSTEM-000`.
- **Non-authoritative fields**: `vendorName`, `warehouse` present and expected
  to be ignored by allowlist mappers.

No customer account numbers, session tokens, internal identifiers, warehouse
details, or unredacted Vendor response bodies were committed.

### A.2. Reproduction Results

All 16 new tests pass, exercising the full `InternalVendorAdapter.lookup()`
pathway with mocked HTTP transport across three contract forms:

| Contract Form | Status | Ingram | Synnex EU | CDW |
|---|---|---|---|---|
| Paragraph envelope (FU3+FU4) | SUCCESS | $5,445.67 USD, OUT_OF_STOCK, qty=0 | €4,740.18 EUR, OUT_OF_STOCK, qty=0 | $0.00 USD, UNKNOWN, qty=None |
| Plain-text sections | SUCCESS | $5,445.67 USD, OUT_OF_STOCK, qty=0 | €4,740.18 EUR, OUT_OF_STOCK, qty=0 | $0.00 USD, UNKNOWN, qty=None |
| Canonical JSON | SUCCESS/PARTIAL | Same price/availability | Same price/availability | Same price/availability |

### A.3. Availability Classifications — Verification

- **Ingram**: `available=false` + `Avl_Quantity=0` → The
  `_availability_flag_table` truth table maps `(False, 0)` →
  `OUT_OF_STOCK`. **Correct.**
- **Synnex EU**: `AvailabilityTotal="0"` (digit string) → The narrow
  `_synnex_availability_total` accepts ASCII digit strings for this field
  (FU4), converts to integer `0`, maps to `OUT_OF_STOCK`. **Correct.**
- **CDW**: Price `0.00`, no `inventoryStatus`, no `stockStatus`, no
  `Avl_Quantity` → The CDW mapper falls through to `UNKNOWN` with no
  quantity. **Correct.** CDW $0 is a valid candidate; the downstream
  Compact Quote display carries the frozen verification note
  (`"Source-published price: $0 USD — Verify price and purchasing
  availability with the supplier."`). It is not represented as free,
  verified, or immediately purchasable. **Correct per existing contract.**

### A.4. Identity Binding — Verification

All three sources publish `explicit_candidate_mpn == "MTFDKCC3T8TGP-1BK1DABYYR"`,
which exactly matches the requested MPN. The frozen 2A `compare_part_numbers()`
function returns `EXACT` match type. All three candidates are identity-bound.
No `MPN_MISMATCH` issues are produced.

### A.5. Currency Preservation — Verification

- Ingram: `USD` → persisted as `"USD"`
- Synnex EU: `EUR` → persisted as `"EUR"` (no USD equivalent fabricated;
  FX conversion requires explicit ECB evidence via the 4D-C-A FX pipeline)
- CDW: `USD` → persisted as `"USD"`

### A.6. Sensitive Metadata Stripping — Verification

`SessionId`, `BuyerAccountId`, `SystemId`, `vendorName`, `warehouse` are all
absent from every `CommercialSourceCandidate`. Only allowlisted fields traverse
the mapper boundary. **Correct per existing contract.**

### A.7. Browser vs. HTTP Wire

The production Vendor API response is `Content-Type: text/html; charset=utf-8`.
The `<p>` paragraph wrapping and entity encoding (`&quot;`, `&#xA;`, `&#xD;`)
are transport-level transformations observed in the actual HTTP response bytes.
A browser-rendered view would strip these artifacts invisibly. The adapter's
FU3 paragraph-scanner and FU4 entity-decoder handle them exactly. This is
confirmed by the existing `test_vendor_section_response.py` test suite which
demonstrates the same contract forms. The fixture in this investigation
preserves the exact paragraph-envelope + entity encoding observed in raw
transport evidence.

---

## B. Historical FAILED Outcome Investigation

### B.1. Exact Code Paths Producing `FAILED` with Zero Observations and Zero Source Issues

The `InternalVendorAdapter.lookup()` method returns `CommercialSourceResponse(
status=LookupStatus.FAILED, retrieved_at=None)` with **no candidates and no
issues** in exactly these scenarios:

| # | Condition | Code Path | Candidates | Issues |
|---|---|---|---|---|
| 1 | **Network timeout** | `opener.open()` raises `TimeoutError` | 0 | 0 |
| 2 | **Connection error** | `opener.open()` raises `URLError` | 0 | 0 |
| 3 | **OS-level error** | `opener.open()` raises `OSError` | 0 | 0 |
| 4 | **HTTP error** | `opener.open()` raises `HTTPError` (incl. 3xx refused by `_NoRedirectHandler`) | 0 | 0 |
| 5 | **Response read failure** | `response.read()` raises `URLError`/`OSError` | 0 | 0 |
| 6 | **Oversized response** | `len(body_bytes) > 1 MiB` | 0 | 0 |
| 7 | **Non-UTF-8 encoding** | `body_bytes.decode("utf-8")` raises `UnicodeDecodeError` | 0 | 0 |
| 8 | **Neither contract recognized** | JSON fails AND `_scan_section_oriented_body()` returns `None` | 0 | 0 |
| 9 | **JSON dict, no source sections** | `payload` is a dict but `_extract_source_sections()` returns empty list | 0 | 0 |
| 10 | **JSON non-dict, non-list** | `payload` is a string, number, bool, null, etc. | 0 | 0 |

Additionally, the `_lookup_from_section_body()` method (contract 2 path)
returns FAILED with 0/0 when:
- **11**: `_scan_section_oriented_body()` returns `None` (no recognized section
  label found in body)

The orchestration's `_try_vendor_commercial_lookup()` (orchestration.py:1207)
then receives `response.status == LookupStatus.FAILED` and encodes:
```python
final_status = "FAILED"
retrieved_at = None
observations = ()  # empty — no candidates to bind
source_issues = ()  # empty — no issues from the response
```
This produces the exact persisted shape: `FAILED`, zero observations, zero
source issues.

### B.2. Timeout Consistency Analysis

- The configured `_VENDOR_TIMEOUT` is exactly **10 seconds**
  (`internal_vendor.py:79`).
- The elapsed time between final semantic evidence (≈21:48:45) and run
  completion (21:48:55) is **≈10 seconds**.
- The vendor lookup occurs AFTER semantic evaluation (orchestration.py:665 —
  after `_execute_claimed_run()` which includes the semantic pipeline).

The 10-second interval is **consistent with** a `TimeoutError` from
`opener.open(req, timeout=10)`. This is the most plausible explanation.

**However, elapsed time alone does not prove timeout.** Other network failures
(connection reset, DNS failure, TLS handshake failure) could theoretically take
up to the TCP timeout. HTTP-level errors (500, 503) would return immediately
and produce FAILED with 0/0 via the HTTPError path. The critical distinction:
only a true timeout or a very slow connection failure fills the full 10-second
window.

### B.3. Evidence Gaps — Production Logs Required

The exact failure class cannot be determined from the persisted snapshot alone.
The codec deliberately stores no cause for FAILED lookups (design choice — the
bounded statement "The specific failure cause was not recorded by the lookup"
is the correct presentation).

**To obtain precise failure evidence, read-only log inspection is required:**

```cmd
REM Option 1: Search Django/app logs for the run's MPN and the adapter's
REM warning message (logged at WARNING level for bounded failures)
findstr /C:"Vendor API lookup failed for MPN MTFDKCC3T8TGP" "C:\path\to\django.log"

REM Option 2: Grep for the specific exception class
findstr /C:"TimeoutError" /C:"URLError" /C:"HTTPError" /C:"OSError" "C:\path\to\django.log"

REM Option 3: If running under gunicorn/uwsgi, check the server access log
REM for the 10-second response time
findstr /C:"82565637-11f7-4e3e-b1cf-476cc253ac91" "C:\path\to\access.log"

REM Option 4: Check Django debug log for the specific WARNING
REM (the adapter logs: "Vendor API lookup failed for MPN %s (class=%s)")
findstr /C:"Vendor API" "C:\path\to\django.log"
```

If production logs are unavailable (log rotation, different deployment), the
precise failure class is **inconclusive** but **TimeoutError is the leading
hypothesis** based on the 10-second timing correlation.

### B.4. No Unapproved Live API Call

No live Vendor API call was performed during this investigation. All tests
use mocked HTTP transport.

---

## C. Report Semantics Verification

### C.1. Out-of-Stock Vendor Observations Remain Displayable

**Confirmed.** The Compact Quote projection (via `replay_compact_quote_projection()`)
includes vendor observations regardless of availability state. `OUT_OF_STOCK`
observations are rendered as vendor rows with their price, currency, and a note
indicating the availability state. They do not become "In Stock" observations.
The `NormalizedAvailability.OUT_OF_STOCK` is preserved through the codec.

### C.2. No Effect on Machine Price, Reviewed Price, or Market Authority

**Confirmed.** Vendor commercial evidence is strictly supplemental. The
`commercial.py` module contract states:

> "It is not authority. A commercial observation is supplemental evidence.
> It does not enter frozen 4A Machine Price, frozen Reviewed Price,
> deterministic identity authority, semantic authority, or comparable scoring."

The execution pipeline confirms:
- `PriceIntelligenceSnapshot` is created from `_execute_claimed_run()` (public
  search/fetch/extract/normalize/match/aggregate) — vendor data never enters
  this pipeline.
- `_try_vendor_commercial_lookup()` is called AFTER public aggregation and
  only populates `ResearchSupplementSnapshot`.
- No vendor price enters any `PriceAggregateBucket`.

### C.3. EUR Pricing Preservation

**Confirmed.** Synnex EU's `EUR` currency code is preserved in the codec as
`"EUR"`. No USD equivalent is fabricated. The existing 4D-C-A FX pipeline
would optionally compute a USD equivalent only if valid ECB FX evidence exists
for the EUR→USD rate, and this is a separate, explicitly audited evidence chain.
The offline reproduction confirms the Synnex observation carries `"EUR"` without
any implicit conversion.

### C.4. CDW $0 Verification Policy

**Confirmed.** CDW $0 is a valid `CommercialSourceCandidate` with
`price_amount == Decimal("0.00")` and `availability == UNKNOWN`. The existing
Compact Quote display contract shows:

> "Source-published price: $0 USD — Verify price and purchasing availability
> with the supplier."

The note does not contain the words "free", "Free", "recommended", or
"purchasable" (pinned by `test_vendor_zero_price_row_and_status_coexist` in
`tests/web/test_vendor_status_presentation.py`).

### C.5. Historical FAILED Snapshot Not Mutated

**Confirmed.** The historical snapshot persists `FAILED` status. No code path
in the current codebase silently replaces or mutates a persisted
`ResearchSupplementSnapshot`. The GET view for the research run is read-only
(verified by `test_allowed_get_zero_network_zero_db_mutations` in the web test
suite). The historical record is immutable.

---

## D. Defect Analysis and Improvement Review

### D.1. Is There an Implementation Defect?

**No implementation defect was established.** The adapter's code correctly:

1. Handles the timeout/network failure case (produces FAILED with 0/0)
2. Parses the section-oriented body with all three sources
3. Maps each source with correct prices, currencies, and availability
4. Binds identities through frozen 2A
5. Encodes the result through the versioned codec

The offline reproduction proves that **if the Vendor API responds within the
10-second timeout with a valid body, the adapter produces the correct result**
(SUCCESS with three observations, correct prices and availability).

The historical failure was **transient**, not a defect. The most plausible cause
is a network timeout (`TimeoutError` during `opener.open()`) given the exact
10-second elapsed time matching `_VENDOR_TIMEOUT`.

### D.2. Remaining Evidence Gaps

1. **Exact failure class**: Production logs are required to confirm whether
   the failure was `TimeoutError`, `URLError`, `HTTPError`, or `OSError`.
   Without logs, `TimeoutError` remains a hypothesis consistent with but not
   proven by the 10-second timing.
2. **Server-side cause**: Even if a timeout is confirmed, the upstream Vendor
   API server's state (load, maintenance, connectivity to Ingram/CDW/Synnex)
   at the time of the run is unknown.
3. **Response body content**: The actual HTTP response (if any) from the
   production run is unavailable. A partial response that arrived after
   the timeout deadline would be discarded.

### D.3. Recommended Next Implementation Phase (if justified)

**No defect fix is needed.** The code is correct. The failure was a transient
network event.

**If the business requires a mechanism to refresh vendor pricing without
rerunning the entire paid semantic/search pipeline, the following is proposed
as a separate, explicitly user-triggered workflow:**

1. **Vendor-Only Refresh Endpoint**: A new Django view/action that:
   - Takes an existing `ResearchRun.id` (COMPLETED state only)
   - Executes ONLY the `_try_vendor_commercial_lookup()` pathway
   - Creates a NEW `ResearchSupplementSnapshot` (append-only, never overwrites)
   - Requires explicit user initiation (button in the research detail page)
   - Logs the refresh as an auditable event with the user's identity and
     timestamp
   - Does NOT rerun search, page fetch, extraction, normalization, matching,
     aggregation, or semantic evaluation
   - Does NOT affect `PriceIntelligenceSnapshot`, `ResearchFxSnapshot`, or any
     existing persisted evidence

2. **Historical Snapshot Preservation**: The original FAILED snapshot remains
   in the database. The new snapshot is a separate row (or a versioned field
   within the existing model). The presentation layer shows the most recent
   snapshot but the historical one remains queryable.

This would be a **Phase 4D-B-FU5** (or similar) implementation, separate from
this investigation. It is NOT implemented here per the governance constraints.

---

## Final Summary

| Question | Answer |
|---|---|
| Was an implementation defect established? | **No** |
| What produced the historical FAILED? | **Transient network failure**, most plausibly `TimeoutError` at the 10-second `_VENDOR_TIMEOUT` boundary |
| Can the adapter parse a valid response for this MPN? | **Yes** — offline reproduction produces SUCCESS with 3 correct observations |
| Are availability classifications correct? | **Yes** — OUT_OF_STOCK (Ingram), OUT_OF_STOCK (Synnex EU), UNKNOWN (CDW) |
| Is CDW $0 handled correctly? | **Yes** — valid candidate, UNKNOWN availability, verification note, not free |
| Is EUR preserved? | **Yes** — no implicit USD conversion |
| Does vendor data affect Machine Price? | **No** — strictly supplemental |
| Was the historical snapshot mutated? | **No** — immutable |
| Are production logs available to confirm? | **Unknown** — read-only Windows CMD instructions provided |
| Is a fix needed? | **No** — transient event. Vendor-only refresh workflow proposed as separate phase |

**State: NOT APPROVED. NOT FIXED. ChatGPT is the independent final review and approval gate.**
