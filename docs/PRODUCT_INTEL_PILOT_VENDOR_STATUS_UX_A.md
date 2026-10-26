# PRODUCT-INTEL.PILOT-VENDOR-STATUS-UX-A — Vendor API Status Notice +
# Historical Exclusion Investigation (evidence only)

**State:** IMPLEMENTED / PENDING INDEPENDENT (ChatGPT) REVIEW OF THE BRANCH DIFF
**Branch:** `pilot-vendor-status-ux-a` (bounded review branch)
**Baseline:** `0b54054491779ae35c445da0b3244f463524d6ff`
(PRODUCT-INTEL.PILOT-UX-WORKBENCH-A1-FU3 — "Exclusive-Create Safety and
Failure Evidence Closure")
**Baseline collection of record:** 5,927 test nodes (147 files) — re-verified
on the baseline SHA before this phase; baseline full suite green
(5,927 passed, 39 subtests passed, exit 0, 411.17s; the documented
Windows/Python 3.14 subprocess-boundary flake class did not occur).

**No deployment. No merge of divergent main workstreams.** The mainline
semantic-authority V2 workstream (main @ 916296a) is untouched; this branch
roots at the approved pilot-UX baseline only.

---

## Part 1 — Vendor API Status implementation (bounded)

### Problem (verified production evidence)

Micron run `82565637-11f7-4e3e-b1cf-476cc253ac91`:

- ResearchRun COMPLETED; `ResearchSupplementSnapshot` exists.
- Persisted `lookup_status` = FAILED; `observations` = []; `source_issues` = [].
- The report displays the public/AI quote with NO UI explanation of the
  vendor lookup failure. The frozen supplement codec persists **no**
  free-text failure cause, so the exact cause is not recoverable from the
  snapshot — a truthful UI must say so rather than invent a reason.

Samsung run `ce28761a-e81a-4be2-876f-c8980475f26e` shows Vendor quotes,
i.e. missing vendor rows are run-specific, not necessarily a global
configuration failure.

### What changed (four production files + one new test file)

1. `product_intelligence/execution/compact_quote_replay.py` — the ALLOWED
   (authorized) historical replay now exposes the decoded (or absent)
   vendor supplement result on `CompactQuoteReplayResult` as a new
   **additive, defaulted** field `supplemental_result`
   (`ResearchSupplementResult | None = None`). The replay was already the
   sole reader/decoder of `ResearchSupplementSnapshot` on the authorized
   path; it now returns the object it decoded instead of discarding it.
   No request behavior, lookup timeout, source selection, pricing
   authority, review state, codec, or schema changed. The public (DENIED)
   replay (`compact_quote_public_replay.py`) is **untouched** — it still
   never reads the artifact.

2. `product_intelligence/web/vendor_status_presentation.py` (NEW) — pure
   display-only module (no DB, no decode, no providers, no execution/runs/
   codec imports). Maps the decoded result (or `None`) to one of exactly
   five bounded notices:

   | Display state | Trigger (persisted, codec-validated fact) | Wording contract |
   | --- | --- | --- |
   | `not-recorded` | No `ResearchSupplementSnapshot` row for this run | "No vendor lookup was recorded for this research run, so no reason is stated." — never invents a reason |
   | `failed` | `lookup_status` = FAILED | "The internal vendor lookup for this run failed, and no vendor quote was obtained." + either the bounded per-source results recorded in `source_issues` (evidence-backed cause) or, when none are persisted, "The specific failure cause was not recorded by the lookup." |
   | `completed-no-quote` | SUCCESS, zero observations | "The internal vendor lookup completed, but it produced no usable identity-bound vendor quote for this run." (+ bounded per-source results when persisted) |
   | `partial` | PARTIAL | "The internal vendor lookup partially completed: some vendor results were obtained while other sources had bounded failures or were excluded." (+ bounded per-source results when persisted) |
   | `completed` | SUCCESS, ≥ 1 observation | Compact success line; the usual vendor quote rows render as before |

   Display rules: per-source issue lines use only the frozen bounded
   outcome vocabulary rendered as business labels (NOT_FOUND → "not
   found"; MALFORMED_SECTION → "response section could not be read";
   MISSING_EXPLICIT_MPN → "no explicit part number published";
   MPN_MISMATCH(+detail) → "published part number did not match the
   requested part number"); unknown values (unreachable over a
   codec-validated result) fail closed to a neutral label. No raw codec
   field name (`lookup_status`, `vendor_commercial_result`,
   `price_basis`, `explicit_candidate_mpn`, `VENDOR_API_POLICY`, …), no
   exception text, no price, no count of observations beyond the quote
   rows themselves. An unrecognized lookup status (unreachable) renders a
   conservative "status not recorded / no vendor result is claimed"
   notice — never a success or partial-public claim.

3. `product_intelligence/web/views.py` — `research_detail` captures
   `replay.supplemental_result` **inside the ALLOWED branch only** and,
   after the compact quote presentation succeeds, builds the status
   notice via the new display module. For a DENIED request the view never
   reads, decodes, or references the vendor supplemental artifact and the
   context carries `vendor_api_status = None`. On any fail-closed outcome
   (malformed supplement/FX, missing price snapshot, projection error)
   `vendor_api_status` stays `None` — no misleading status accompanies an
   unavailable summary.

4. `product_intelligence/web/templates/web/research_detail.html` — inside
   the `{% if compact_quote %}` branch: DENIED keeps the existing neutral
   notice; ALLOWED renders the compact bordered notice
   (`role="status"`, CSS `--` state modifiers) above the quote stat
   strip. The head `<style>` gains the notice's CSS only. (Template
   note: Django 5.2 single-line `{# #}` comments only — the engine's
   lexer does not strip multi-line template comments; verified against
   the installed Django 5.2.17 `tag_re`.)

### Security invariant (preserved + re-pinned)

- The server-side `REMOTE_ADDR`/CIDR gate (`web/commercial_access.py`) is
  unchanged and remains the only authorization mechanism; forwarded
  headers are never trusted.
- DENIED connections learn nothing about the vendor snapshot: no
  existence, status, source names, prices, counts, configuration, or
  error text. The DENIED route still never touches the artifact access
  path (armed-`RuntimeError` regressions re-pinned in the new suite).
- Historical GET remains read-only: zero vendor/search/LLM/FX live calls
  (armed boundary sentinels), zero DB mutations (row-level digest
  fingerprint of all six research tables before/after, including
  payloads and the run's state/timestamps).
- No new web-layer research/execution/runs imports were needed — the
  symbol-level web boundary guards pass unmodified
  (`tests/web/test_web_boundaries.py`, 159 nodes).

### Tests (all additive — `tests/web/test_vendor_status_ux_a.py`, 25 nodes)

- FAILED snapshot: exact failure message ALLOWED-only; bounded
  evidence-backed per-source cause variant; DENIED learns nothing
  (armed supplement boundaries + sentinel source/price absence +
  context `vendor_api_status is None`).
- SUCCESS zero observations (with and without bounded per-source
  issues); SUCCESS with 1 observation (compact status + existing vendor
  row display intact, exact-once label); SUCCESS with 2 (plural);
  PARTIAL (with and without usable observations); DENIED variants armed.
- NOT_ATTEMPTED (no snapshot): "no reason is stated", no invented cause
  words, ALLOWED + DENIED.
- Malformed snapshot: ALLOWED keeps the EXISTING fail-closed behavior
  ("Quote & Market Summary unavailable.", no status notice, no
  partial-public fallback, no error text); DENIED unaffected (armed).
- Coexistence: public + human-confirmed AI rows remain usable in the same
  summary over a well-formed FAILED lookup (real confirm POST flow);
  source-published $0 vendor price keeps its exact existing display
  contract (the B1 verification note stays in the row's Market Use cell,
  not the status).
- Read-only: zero-network (armed providers/urllib/semantic) +
  zero-DB-mutation (table-row digests) on GET, both branches.
- Pure presentation unit pins: exact state/label/lines for every category,
  fail-closed on an unrecognized status, and a sweep asserting no raw
  codec token and no price appears in any status line.

Existing baseline preserved: **0 deleted, 0 renamed, 0 skipped, 0
xfailed, 0 deselected, 0 weakened** — collection 5,927 → 5,959 (+32 = 25 new
regression nodes + 7 new auto-generated boundary-guard instances over the
new web module), node-level diff of record below.

### Validation (exact)

Collection (node-level diff of record, `tmp_baseline_collection.txt` →
`tmp_after_collection.txt`): **5,927 → 5,959 (+32; 0 removed, 0 renamed)**.
Breakdown of the +32: 25 NEW nodes in
`tests/web/test_vendor_status_ux_a.py`; 6 new guard INSTANCES in
`tests/web/test_web_boundaries.py` (its per-web-file parametrized guards now
also cover the new `vendor_status_presentation.py` module — additive
coverage, no guard weakened); 1 new guard INSTANCE in
`tests/providers/test_provider_boundaries.py` (`test_nothing_is_wired_to_the
_search_boundary_yet` parametrizes over every web-layer file and asserts it
imports no provider — the new module passes it).

- `python -m pytest` full suite over the 5,959 collection, TWO runs (fresh
  interpreters):
  - Run 1: **14 failed, 5,945 passed + 39 subtests passed, exit 1 in
    391.58s.** 13 of the 14 are `OSError: [WinError 6] "The handle is
    invalid"` at subprocess Popen pipe setup BEFORE any project code runs —
    the documented Windows/Python 3.14 clean-interpreter subprocess-boundary
    flake class (the same 11 boundary-import guards + 2
    `test_preview_fixtures_safety` subprocess nodes recorded in the
    A1-FU2 / A1-FU3 evidence). The 14th,
    `tests/web/test_price_report.py::TestCorruptSnapshot::test_corrupt_
    payload_shows_unavailable`, is a PRE-EXISTING probabilistic test flake
    proven unrelated to this phase: the test asserts the string `"109"`
    is absent from the whole rendered page, but the page renders the run's
    OWN random UUID (`Request identifier`), and this run's UUID
    `b94a77e9-1a31-4f8a-87aa-d10969ba5fa2` contains `109`. Deterministic
    reproduction on the UNMODIFIED baseline worktree at the same UUID:
    the identical corrupt-snapshot page contains `109` exactly twice (both
    the run's UUID); on this branch the same page renders no vendor status
    block at all (corrupt price snapshot → no compact section). It passed
    in 40/40 isolated re-runs on the baseline and in the isolated batch
    here.
  - Run 2: **13 failed, 5,946 passed + 39 subtests passed, exit 1 in
    426.41s** — all 13 are the WinError 6 flake class nodes above (the
    UUID flake did not recur), i.e. every non-flaked node passed and the
    collection delta is fully accounted.
  - The 14 flaked nodes re-run in ISOLATION without modifying tests:
    **14 passed, exit 0 in 4.89s.** The failed full runs are NOT called
    green; no allowlist was expanded; no test was touched.
- Baseline (pre-change) full suite on the same worktree: **5,927 passed +
  39 subtests passed, 0 failed, exit 0 in 411.17s** (`tmp_baseline_full_
  run.txt`).
- `python manage.py check` → "System check identified no issues (0
  silenced)", exit 0.
- `python manage.py makemigrations --check --dry-run` → "No changes
  detected", exit 0 (no model change — the phase is presentation-only).
- `git diff --check` → clean.

---

## Part 2 — Separate evidence-only investigation (historical
exclusions). NO matching rule, extractor, or authority changed in this
phase.

Method: every claim below is tied to (a) frozen source in this branch at
the baseline SHA, or (b) committed recorded fixtures with retrieval
provenance, or (c) the result of running the frozen primitives
read-only. Where durable evidence is absent from the repository, that
absence is stated — nothing is back-filled by assumption.

### Case 1 — Samsung `M321RYGA0PB2-CCP`, Central Computers $4,099.99

**Observed:** the page currently publishes Manufacturer Part Number
`M321RYGA0PB2-CCP`; the historical extraction used retailer SKU
`MEMSAM59664S`; the listing was excluded from Machine Price.

**Frozen mechanism (source):**

- 3A extraction (`research/extraction.py`) records
  `manufacturer_part_number_text` ONLY from approved MPN channels:
  JSON-LD `mpn`, flat meta `name="mpn"`, meta property
  `product:retailer_part_no`, or the bounded visible-label set
  `_VISIBLE_MPN_LABELS` = ("MPN", "Manufacturer Part Number",
  "Manufacturer Part #", "Mfr Part Number", "Mfr Part #", "Model
  Number", "Model #"). The source states: "Retailer-local identifiers
  such as 'Item #' and 'SKU' are intentionally absent." SKU comes from
  JSON-LD `sku` / meta `name="sku"` into `sku_text`.
- 3C evidence priority (`research/matching.py::_find_evidence`):
  explicit MPN field **>** SKU field **>** title text **>** none.
- 3C rule (same module, `assess_listing_identity`): "SKU or title only:
  never automatically accepted" — a SKU_FIELD observation returns
  `REJECTED / NO_EXPLICIT_MPN_EVIDENCE` with `match_type = UNKNOWN`
  **before the 2A comparator is ever run**; the SKU string is never
  compared to the requested MPN by deterministic matching.
- 4A (`research/aggregation.py`): only `ACCEPTED` assessments form price
  buckets (Machine Price); the rejected listing is kept in `exclusions`
  with `IDENTITY_NOT_ACCEPTED` — evidence preserved with its reason.

**Diagnosis:** at retrieval time the Central Computers listing yielded
`manufacturer_part_number_text = None` + `sku_text = MEMSAM59664S` —
i.e. the page did not expose the MPN through any approved channel (the
published MPN was under a label/structure the bounded extractor does not
recognize, or the page state at retrieval differed from the current
publishing). The SKU-only path then rejected the listing by frozen 3C
design. The exclusion is correct behavior of the frozen rules over the
historical field report; it is not a matching defect.

**Durable evidence available in the repository:** the committed
DirectMacro fixture records the identical mechanism in the field report
(`tests/fixtures/pages/directmacro_bcm957608_p2200gqf00_search.html`
header + `tests/fixtures/pages/README.md`: "the Broadcom product
publishes **only** `sku`, not `mpn`. Frozen 3C rejects SKU-only evidence
as `REJECTED / NO_EXPLICIT_MPN_EVIDENCE`"). **No Central Computers page
fixture and no persisted execution evidence for this listing exist in
the repository** — the exact historical field report for
`MEMSAM59664S` cannot be re-verified from this branch.

**Proposed extractor correction — STOP (not implemented).** If the
currently published page exposes the MPN only under a visible label
outside the approved set, the correction would be a bounded extension of
`_VISIBLE_MPN_LABELS` (or the structured-channel mapping) — an
authority-sensitive extraction rule change. Before implementation it
requires, at minimum: (1) an actual fetched HTML fixture of the Central
Computers page committed under `tests/fixtures/pages/` with retrieval
provenance (URL, HTTP facts, retrieved-at, SHA-256) per the fixture
README policy; (2) the exact label/channel the page uses; (3) precise
expected behavior (observation gains
`manufacturer_part_number_text = "M321RYGA0PB2-CCP"` → 3C EXACT →
ACCEPTED → 4A bucket); (4) impact analysis — label-collision risk (a
"Part Number" label could be a retailer part number on other sites; the
page-level enrichment rule
`_page_visible_mpn_is_unambiguous` requires a single distinct value and
an identity-free single-product page), re-extraction of historical runs
is NOT automatic (historical GETs stay read-only), and the
SKU-first-evidence runs remain rejected; (5) positive + negative
regression tests over the fixture. Without (1) there is no durable
source to correct against — this phase stops here.

### Case 2 — Samsung eBay product 21078017544 (hyphen asymmetry)

**Observed:** title/model use `M321RYGA0PB2-CCP`; the page's explicit MPN
uses `M321RYGA0PB2CCP` (no hyphen). The listing was excluded.

**Precise frozen comparison behavior (verified by running the frozen
primitives, read-only):**

- `_find_evidence` selects the explicit MPN field over the title →
  candidate `M321RYGA0PB2CCP` (`EXPLICIT_MPN_FIELD`; the narrow `mpn:`
  wrapper cleanup `_clean_mpn_field_wrapper` only strips an `mpn:`-style
  prefix and never touches hyphens).
- Frozen 2A (`research/identity.py`), `compare_part_numbers("M321RYGA0PB2-CCP", "M321RYGA0PB2CCP")`:
  - `EXACT` — no (character-for-character differ).
  - `NORMALIZED_EXACT` — no. `normalize_part_number` is structure
    preserving: it folds ASCII case and collapses internal whitespace
    runs to one canonical separator, and "every other character is kept,
    in place". The docstring pins the exact rule: "a value with a
    boundary the other does not have is a different identifier, and
    `ABC-123` therefore does not match `ABC123`." Keys:
    `M321RYGA0PB2-CCP` vs `M321RYGA0PB2CCP` → differ.
  - Result: `UNKNOWN` (verified output above).
- 3C narrow PARTIAL (`_classify_partial`): requires one normalized key to
  be a strict prefix of the other ending at a preserved separator
  (`- _ / .` or whitespace-derived). `M321RYGA0PB2CCP` is not a prefix
  of `M321RYGA0PB2-CCP` (they diverge at index 12: `C` vs `-`) → not
  PARTIAL (verified by code path; no prefix relation exists).
- Final 3C verdict: `REJECTED / MPN_MISMATCH` (explicit field carried
  part-number content; 2A did not establish).
- The hyphenated title form would be `EXACT` against the request
  (verified) — but title evidence is recorded only ("never used for
  automatic acceptance") and is preempted by the explicit field anyway.
- Consequence for review paths: `is_human_review_eligible_assessment`
  explicitly excludes `REJECTED + MPN_MISMATCH` — so this listing is
  also not a semantic/human-review candidate. It is a full deterministic
  exclusion, retained in `exclusions` with its reason.

**Assessment:** the exclusion is the frozen 2A structure-preservation
rule working exactly as documented: the hyphen is data, not noise.
Do **not** strip hyphens (globally or in a "hyphen-insensitive" mode):
`ABC-123` vs `ABC123` are different identifier structures in this
system, and separator position is load-bearing in Micron's own 7500
family (field boundaries per the part-number structure in
`docs/MICRON_ALIAS_AUTHORITY_EVIDENCE.md` §6). If business judgment
establishes that the eBay explicit field is a typographic variant of the
same MPN, the authority-consistent options are (a) a reviewed,
bounded, source-scoped alias relation of the 4D-D customer-rule class
(evidence-first, retrieval/annotation only — never automatic identity),
or (b) a 2A normalization rule change with its own evaluation-corpus
adjudication under the "evaluation truth does not move" governance
(`evaluation/README.md`, class A–D). Both are STOP items outside this
phase; no eBay fixture for product 21078017544 is committed to the
repository, so no correction has durable source evidence yet.

### Case 3 — DirectMacro SKU_FIELD-only observations

**Observed:** DirectMacro listings for the requested MPN were excluded
from Machine Price.

**Durable evidence (committed fixture, verified):**
`tests/fixtures/pages/directmacro_bcm957608_p2200gqf00_search.html`
(4D-A; source
`https://directmacro.com/catalogsearch/result/?q=BCM957608-P2200GQF00`,
HTTP 200 static HTML) and `tests/fixtures/pages/README.md` record the
exact 3A field report (verified against the live page at 4D-PRE):
`manufacturer_part_number_text: None` — no explicit `mpn` field in the
JSON-LD; `sku_text: BCM957608-P2200GQF00` — the retailer publishes the
requested MPN string **only inside its `sku` field**; price
`2120.002 USD`, availability In Stock. The fixture's own JSON-LD shows
`"sku": "BCM957608-P2200GQF00"` with no `mpn` key.

**Why these cannot automatically become Machine Price (frozen rules):**

1. 3C (`assess_listing_identity`): SKU_FIELD evidence returns
   `REJECTED / NO_EXPLICIT_MPN_EVIDENCE` before any comparison — "SKU or
   title only: never automatically accepted."
2. 4A: Machine Price buckets contain only `ACCEPTED` assessments; the
   SKU-only listing is retained in `exclusions` as
   `IDENTITY_NOT_ACCEPTED` (evidence preserved with reason).
3. Authority rationale (CLAUDE.md frozen rules): deterministic code
   owns identity; a retailer `sku` is a retailer-defined identifier
   namespace. The page gives no authority to equate the retailer's SKU
   with the manufacturer MPN — and even when the SKU string happens to
   equal the requested MPN (as here), accepting string-equal SKUs as
   EXACT identity would be a NEW matching rule with global blast radius
   (retailers also use internal codes in `sku`; one character can mean a
   different product). 3C deliberately never compares the SKU to the
   request.
4. The designed, non-authority path exists and is pinned:
   `REJECTED + NO_EXPLICIT_MPN_EVIDENCE + SKU_FIELD` is human-review
   eligible (`is_human_review_eligible_assessment`); the semantic
   runtime may assess it (advisory only); a human CONFIRM may add ONE
   Compact Quote row for the same run (identity authority only,
   "Quote only — AI-assisted" market use, persisted price/currency as-is)
   — which still never enters Machine Price, Reviewed Price, or 4A
   buckets (frozen PROD-FIX1 semantics).

**Conclusion:** no rule change is required for correctness; "automatic
Machine Price from SKU-only evidence" would violate the frozen identity
authority. Any future change is authority-sensitive and STOPped pending
its own design + evaluation adjudication.

### Case 4 — Micron `MTFDKCC3T8TGP-1BK1DABYYR`: three distinct
identifiers

**Observed:** the requested MPN carries a trailing `R`; historical
behavior excluded catalog/variant confusion by design.

**The three identifiers, distinguished on committed evidence:**

1. **Full requested MPN** — `MTFDKCC3T8TGP-1BK1DABYYR`. The customer's
   request string; the identity the report is bound to
   (`ResearchRun.manufacturer_part_number`); the only string that may
   appear as the requested part number in 2A comparisons.
2. **Manufacturer-published base MPN** — `MTFDKCC3T8TGP-1BK1DABYY`.
   Published by Micron's structured 7500 parts catalog — committed
   fixture `tests/fixtures/pages/micron_7500_part_catalog.json`
   (`getpartcatalog`, retrieved 2026-09-22, 24 rows; row for
   `part-number: MTFDKCC3T8TGP-1BK1DABYY`, `is-ssd: true`, 3840 GB,
   7500 PRO, U.3) and per-part `getproductinfo`
   (`micron_7500_getproductinfo_base.json`). Verified against the
   committed catalog: the R and T variants are **not** catalog rows;
   Micron's own endpoint answers `{"message":"Invalid Partnumber"}` for
   them (`docs/MICRON_ALIAS_AUTHORITY_EVIDENCE.md` §4). The R/T
   part-detail HTML pages carry the requested MPN in
   title/meta/breadcrumb, but the page source marks that field as
   template-injected ("Updated logic for title and link to update
   dynamic Part Number"; data-layer `dc:title: "{1} {2} part detail"`)
   — a request echo, not independent identity evidence.
3. **Customer-defined retrieval alias** — the
   `MICRON_PACKAGING_ALIAS` relation (frozen customer requirement,
   4D-D). No official Micron document defines a trailing R/T packaging
   meaning for the 7500 SSD family (`MICRON_ALIAS_AUTHORITY_EVIDENCE.md`
   §10), so the relation is explicitly customer-defined, never
   manufacturer-published. The runtime (`research/micron_packaging_alias.py`)
   derives the lookup-base candidate by stripping **exactly one** final
   uppercase `R`/`T` (`derive_lookup_base_candidate` — verified:
   `MTFDKCC3T8TGP-1BK1DABYYR` → `MTFDKCC3T8TGP-1BK1DABYY`), requires the
   base to be a manufacturer-structured catalog record with SSD category
   evidence, and then may generate the retrieval family
   `(base, base+R, base+T)` for search recall only. Alias/reference rows
   are labeled "Customer-defined packaging alias reference — excluded
   from pricing authority" and never enter Machine Price, Reviewed
   Price, deterministic or semantic identity authority, compact quote,
   or comparable scoring (template + 4D-D design §13–14).

**Why the distinction matters for exclusions:** 2A compares the R-variant
against the base as `UNKNOWN` (verified — the trailing character is
data), so a listing publishing only the R (or only the base) is not
auto-accepted against the other; the alias machinery's sole job is
retrieval recall anchored on the base record, which is why
`NOT_ATTEMPTED`-style and base-anchored catalog behavior is
deterministic and auditable. No rule change is proposed; the recorded
exclusions follow from these frozen distinctions.

### STOP (authority-sensitive changes)

Per the task instruction, this phase implements NO extractor, matching,
normalization, or alias-authority change. The corrections sketched for
Cases 1–2 are STOPped until each has: actual fetched HTML fixtures (or
equivalent durable source evidence) committed with retrieval provenance;
precise expected behavior; impact analysis; and regression tests —
reviewed and approved as their own bounded phases.

---

## Files changed in this phase

- `product_intelligence/execution/compact_quote_replay.py` (additive
  field + docstring)
- `product_intelligence/web/vendor_status_presentation.py` (NEW)
- `product_intelligence/web/views.py` (ALLOWED-branch capture + context)
- `product_intelligence/web/templates/web/research_detail.html`
  (notice block + CSS)
- `tests/web/test_vendor_status_ux_a.py` (NEW, 25 nodes)
- `docs/PRODUCT_INTEL_PILOT_VENDOR_STATUS_UX_A.md` (this document)

No model/migration change; no frozen codec/schema change; no provider,
orchestration, matching, extraction, or aggregation change; no test
deleted, renamed, skipped, xfailed, deselected, or weakened.
