# PRODUCT-INTEL.PILOT-UX-WORKBENCH-A1 — Mandatory Initial Audit

Bounded UI-only redesign of the research intake and the top of the research
report (the "quote workbench"). This audit documents the existing UI
contracts, form actions, render branches, and security boundaries that the
redesign must preserve. It was produced from the exact B1 baseline before any
template change.

## 1. Baseline

* Repository: `zlw1987/Product_Intelligence`
* Mandatory baseline: `c0b7b6d1288f46dd2fa833be3faf1a4a0728fd52`
  (PRODUCT-INTEL.PILOT-VALUE-PRICE-QUALITY-B1 — source-published
  zero-price verification notice in the Quote & Market Summary).
* Baseline collection re-verified in this worktree: **5,861 tests**
  (144 files; 669 in `tests/web`).
* Development isolation: dedicated worktree checked out at the baseline SHA
  on a new review branch. The main worktree and its untracked files are
  untouched.
* Environment: Python 3.14.7 venv (the workstation venv already used by the
  B1 line), Django 5.2.17, pytest 9.1.1. No dependency changes in this
  phase.

## 2. Routes and form actions (unchanged by this phase)

| Method | URL | View | Contract |
| --- | --- | --- | --- |
| GET/POST | `/research/new` | `research_new` | Prefill-only GET (query `mpn` / `description`); POST -> `ResearchRequest` -> `ResearchRun(CREATED)` -> synchronous `execute_research_run` -> 302 to the report. Invalid POST re-renders the form with the domain error. |
| GET | `/research/<uuid:run_id>` | `research_detail` | Historical report. Read-only: loads rows, decodes persisted snapshots, renders. Zero live provider/vendor/FX/semantic/search work (armed-sentinel tests). |
| POST | `/research/<uuid>/retry` | `research_retry` | FAILED runs only; creates a new run and executes it. |
| POST | `/research/<uuid>/review/<uuid>` | `research_review` | Human review actions `confirm` / `reject` / `remove` / `undo`; 8-step fail-closed binding validation before any runs-service write. |
| POST | `/research/<uuid>/comparables` | `research_comparables` | Comparable trigger; idempotent; bounded error redirects. |
| GET | `/healthz` | `healthz` | Operational probe. |
| GET | `/` | redirect | RedirectView to `research-new`. |

CSRF enforcement (cookie-based, no sessions) is on for every POST; tests use
`Client(enforce_csrf_checks=True)` to pin that.

## 3. UI inventory at B1

### 3.1 `web/base.html` (the only shared stylesheet)

* Inline `<style>` block, no static files, no build pipeline, no CDN.
* `:root { color-scheme: light dark; }`
* `body { max-width: var(--pi-page-max-width, 44rem); ... }` — the narrow
  reading column is the base default.
* Generic element styling (h1/h2, label, input, textarea, button, dl,
  .notice, .errors, .absent, .evidence-entry, .bucket-entry,
  .comparable-candidate, .spec-table(-wrapper), footer).
* Header: `<h1><a href="/research/new">Product Intelligence</a></h1>`.
* Footer: the evidence disclaimer paragraph.

### 3.2 `web/research_new.html` (intake)

* `<h2>New research request</h2>` + purpose paragraph.
* Form `#research-new-form` (POST, `{% url 'research-new' %}`, `novalidate`),
  `{% csrf_token %}`, non-field errors `<ul class="errors">`, per-field
  error lists, `{{ field }}`, optional `.help` text.
* Submit button `#research-submit-button` with exact label
  `Run Market Research`.
* Inline duplicate-click guard (PROD-FIX1, UX only — not backend dedupe):
  on `submit` the guard checks `form.checkValidity()` first (if invalid the
  button stays enabled), then sets `button.disabled = true` and
  `button.textContent = "Researching\u2026"`.
* Notice: "Submitting records the request and gives it a durable report
  address."
* Fields (from `forms.py`): `manufacturer_part_number` (TextInput,
  `autofocus`, `autocomplete="off"`) and `description` (Textarea, rows=4).
  Both individually optional; the "at least one" rule is enforced by the
  domain `ResearchRequest` contract and its message ("A research request
  requires at least a manufacturer part number or a product description.")
  is re-rendered as a non-field error.

### 3.3 `web/research_detail.html` (report)

Page structure at B1 (in source order):

1. `<style>` — declares `:root { --pi-page-max-width: 70rem; }` (B2-FU1
   desktop width; the intake page keeps the 44rem base default).
2. `<h2>Research request</h2>` + `<dl>`: Request identifier
   (`<code>{{ run.id }}</code>`), State, MPN (or `Not supplied`),
   Description (or `Not supplied`), Created (always), Started / Finished
   (conditional on the persisted timestamps).
3. State notices:
   * `?start_error=1` -> "not ready to execute" notice (error class).
   * `?retry_error=1` -> "could not be restarted" notice.
   * CREATED -> "Research request created. Research has not started."
   * RUNNING -> "Research is currently running. ..."
   * FAILED -> "Research did not complete successfully. ..." + retry form
     (POST `research-retry`, button `Retry Research`).
4. `<h2>Quote & Market Summary</h2>` — only when a compact quote
   presentation exists or is explicitly unavailable:
   * DENIED-connection notice (exact string): "Internal commercial pricing
     is unavailable for this connection."
   * `<dl>`: Quotes found / In stock / Lowest in-stock quote (value +
     source, or `.absent` "Unavailable") / Observed quote span (USD
     equivalent) (or "Unavailable").
   * FX evidence `<dl class="fx-evidence">`: ECB reference date / Rates
     retrieved / FX acquisition ("Retrieved live during this research run"
     or "Reused from the canonical ECB observation cache").
   * `<h3>Comparable public market</h3>`: count sentence with
     `<strong>{{ public_market_count }}</strong> comparable NEW listing(s)`;
     observed span; median OR median note ("Not shown — fewer than 3
     comparable NEW listings." / "Not combined — multiple non-comparable
     currency groups. See Advanced Evidence & Audit.").
   * Quote table: `<div class="spec-table-wrapper">` >
     `<table class="spec-table">`, 8 columns: Source / Price / USD
     Equivalent / Availability / Condition / Match / Evidence / Market Use /
     Actions. Row id `quote-row-<candidate_id>` for AI-bound rows; notes
     render under Market Use in a `<small>`; the B1 zero-price
     verification note rides in `row.note` and must stay visibly attached
     to its row.
   * No rows -> "No quote evidence is available."
   * `compact_quote_unavailable` -> "Quote & Market Summary unavailable."
5. `<h2>AI-assisted evidence & review</h2>` — only when candidates exist;
   the advisory disclaimer paragraph ("AI confidence is a workflow tier,
   not a calibrated probability. ..."); subsections AI-assisted quote
   evidence / evidence without usable quote price / Possible matches —
   needs review / low-confidence `<details>` / Automatically excluded
   identity conflicts / rejected `<details>` / unavailable; each candidate
   is the `web/_ai_candidate_card.html` include with its review form
   (POST `research-review`, CSRF token, action-specific buttons).
6. `<h2>Micron packaging alias evidence</h2>` — only when a persisted alias
   snapshot decoded (or explicitly unavailable); status paragraph + audit
   table + reference table (when established) + bounded notices.
7. `<details class="audit-details">` "Advanced Evidence & Audit — Price
   intelligence" containing `<h2>Price intelligence</h2>`: snapshot_error /
   no-snapshot ("No research result available.") / UNKNOWN / VERIFIED
   (buckets, contributing evidence, exclusions) / AMBIGUOUS rendering;
   snapshot stored-at notice.
8. `?comparable_start_error=1` notice.
9. `<details class="audit-details">` "Advanced Evidence & Audit — Reviewed
   price" containing `<h2>Reviewed price</h2>` (only when
   `reviewed_result and confirmed_count > 0`).
10. `<h2>Comparable products</h2>` — child-state notices, retry form,
    decoded comparable presentation (NO_REQUESTED_MPN / NO_AUTHORITY_MATCH /
    AMBIGUOUS_AUTHORITY / FULL with candidate `<details>` and the spec
    comparison table), or the trigger form / "available for completed
    research runs" notice.
11. Closing link: "Create another research request" -> `/research/new`.

### 3.4 Render branches and context variables (views.py, unchanged)

`research_detail` assembles: `run`, `report_presentation`, `snapshot_error`,
`snapshot_created_at`, `has_snapshot`, `start_error`, `retry_error`,
`review_candidates` + the six AI bucket lists, `reviewed_result` +
`confirmed_count` + `reviewed_confirmed_price_count` +
`reviewed_deterministic_price_count`, `comparable_child` +
`comparable_presentation` + `comparable_decode_error` +
`comparable_binding_error` + `comparable_start_error`, `compact_quote` +
`compact_quote_unavailable`, `fx_evidence`,
`vendor_commercial_access_allowed` (boolean only — never the row-hiding
mechanism), `micron_alias` + `micron_alias_unavailable`.

## 4. Security boundaries that constrain the UI

1. **Vendor commercial price gate (4D-C-SEC).** The decision is made
   server-side from REMOTE_ADDR vs `PI_VENDOR_PRICE_ALLOWED_CIDRS` before
   any vendor artifact is read. DENIED: public-only replay; the projection
   contains no vendor rows; no vendor string (label, price, currency) may
   appear anywhere in the HTML — armed sentinel tests prove the DENIED path
   never touches `ResearchSupplementSnapshot`. ALLOWED: vendor rows render
   with exact labels, e.g. "Ingram (Vendor API)" appears exactly once on the
   page.
2. **Historical GET is read-only / zero-live.** Armed `urllib`, Serper,
   page-fetch, vendor, FX, semantic sentinels must all be untouched.
3. **URL safety.** `presentation._is_safe_href_url` (http/https only,
   hostname, no userinfo, no HTML-breaking chars) decides linkability;
   unsafe URLs render as plain text and the raw string never becomes an
   `href`. No `|safe` anywhere in these templates.
4. **Auto-escaping.** MPN/description/listing text are untrusted; tests
   pin escaped rendering (`&lt;script&gt;` etc.).
5. **State/timestamp honesty.** A CREATED run page must not contain the
   words "Started"/"Finished", nor "$", "0.00", "$0", "N/A", "Median"/
   "median", or "109". No fabricated certainty.
6. **CSRF** on every POST form (intake, retry, review, comparables).
7. **Duplicate-submit guard** is front-end-only and its exact DOM/JS shape
   is pinned (ids, first `<script>` on the page being the guard, ordering of
   validity check before disable, literal `Researching\u2026`).

## 5. Test-pinned UI contracts (the hard keep list)

Exact-string DOM contracts the redesign must keep rendering:

* Intake: `id="research-new-form"`, `id="research-submit-button"`, button
  text exactly `Run Market Research` (not disabled initially),
  `form.addEventListener("submit"`, `button.disabled = true`,
  `Researching\u2026`, `form.checkValidity` positioned before the disable,
  guard is the page's first inline `<script>` with no `src=`,
  `name="manufacturer_part_number"` / `name="description"`,
  prefill `value="..."`, `csrfmiddlewaretoken`, "at least a manufacturer
  part" on the empty-pair error.
* Report header: run id, MPN, description, state value (e.g. `CREATED`),
  created timestamp `Y-m-d H:i:s T`, "Not supplied", "Research request
  created.", "Research has not started.", "did not complete" (FAILED),
  "Retry" (FAILED), "not ready to execute" (start_error), "could not be
  restarted" (retry_error).
* Layout (test_report_layout.py): the detail page declares
  `--pi-page-max-width: Nrem` with `44 < N <= 100`; the `body` rule keeps
  `var(--pi-page-max-width, 44rem)`; the intake page declares no
  `--pi-page-max-width` at all; `.spec-table-wrapper` rule keeps
  `overflow-x: auto`; `.spec-table` rule keeps `width: 100%`.
* Quote section: bare headings `<h2>Quote & Market Summary</h2>` and
  `<h2>Price intelligence</h2>` (exact, no attributes); `<dt>Quotes
  found</dt>`, "Lowest in-stock quote", "Comparable public market",
  `<strong>{count}</strong>` + "comparable NEW listing"; `<th>Source</th>`
  ... `<th>Actions</th>`; the 8-column table with exact header cell texts
  `Source | Price | USD Equivalent | Availability | Condition | Match /
  Evidence | Market Use | Actions` and exactly 8 cells per data row in that
  column order; vendor labels exact-once; the literal text "None" must not
  appear in the quote section; "No quote evidence is available.";
  "Quote & Market Summary unavailable."; "Internal commercial pricing is
  unavailable for this connection."; the B1 zero-price note text; median
  gate (no numeric median in the primary summary below 3 NEW listings).
* Section order (template source + rendered): `Quote & Market Summary`
  before `AI-assisted evidence & review` before `Micron packaging alias
  evidence` before `Price intelligence` before `Reviewed price` before
  `Comparable products`; `<h2>Comparable products</h2>` after
  `<h2>Reviewed price</h2>` in the template source.
* AI review: `id="ai-candidate-<uuid>"`, `id="quote-row-<uuid>"`,
  "Review / Verify", `name="action" value="confirm|reject|remove|undo"`,
  "Verify / Confirm", "Possible matches — needs review", "Other possible
  sources — low confidence (N)", "Automatically excluded identity
  conflicts", "Automatically excluded — explicit identity conflict.",
  "Review evidence unavailable.", "AI confidence is a workflow tier, not a
  calibrated probability."
* Micron: `<h2>Micron packaging alias evidence</h2>` only when a snapshot
  exists (count==0 otherwise); status strings; "Micron alias evidence
  unavailable."; the "officially" word must not appear in the section.
* FX: "ECB reference date", "Rates retrieved", "Retrieved live during this
  research run", "Reused from the canonical ECB observation cache"; no
  store digests/row ids/cache keys in HTML.
* Price intelligence: "No research result available.", "Price aggregation
  status:", "VERIFIED"/"AMBIGUOUS"/"UNKNOWN", bucket dl labels (`<dt>
  Median</dt>` only with >=3), "Sample size is too small (N
  observation(s)) ...", "snapshot stored at", "Excluded listings",
  "Exclusion reason", "does not match", "Stored price result unavailable".
* Comparable: "Comparable research is queued.", "... currently running.",
  "... did not complete successfully", "Retry Comparable Research",
  "Comparable products", "Comparable research is available for completed
  research runs.", "Research Comparable Products", kind notices, spec
  table columns, "Conflict"/"Unknown"/"Unverified — " resolution display.
* Boundary: the web package must not import providers / execution
  submodules / research identity (except the one pinned views.py
  exception); no vendor names in web/ source.

## 6. Known test debt (pre-existing, not introduced here)

* Session-scoped test database (tests/conftest.py creates one test DB for
  the whole session; non-TestCase pytest functions rely on
  `human_review_db_isolation`-style explicit cleanup). Order-dependent
  leakage of `ResearchRun` rows between pytest-function tests is a known
  baseline defect. New A1 tests use `django.test.TestCase` (transaction
  rollback) or the existing scoped fixtures and leak nothing.
* Windows/Python 3.14 workstation: the `tests/domain/test_domain_boundaries.py`
  subprocess test can flake with `OSError: [WinError 6]` (documented
  flake class, unrelated to web files).

## 7. Design-system plan (A1)

* Single shared inline stylesheet in `web/base.html` (no new assets, no
  build step, no CDN, no framework).
* Light theme by default (`color-scheme: light`), system font stack,
  navy headings/navigation, slate neutrals, restrained teal accent for the
  primary action and links; consistent radii/spacing/focus rings; distinct
  neutral treatments for error / warning / success / unknown / unavailable
  (text + left border, no colorful status badges, no gradients, no
  decorative charts).
* Page A (intake): compact navy top bar; a bounded intake card with
  eyebrow "Market research intake", purpose line, prominent MPN field,
  explicitly optional description field, non-field error banner, primary
  teal action "Run Market Research"; guard script unchanged in contract.
* Page B (report top): a report header card (title = MPN or
  description-or-Not-supplied, status line, secondary metadata grid with
  request id + timestamps, New research link, retry action on FAILED);
  Quote & Market Summary elevated to the primary business area (stat row
  for quotes found / in stock / lowest in-stock / quote span, public
  market line, FX evidence line, then the 8-column quote table with
  consistent alignment and numeric formatting helpers); the lower sections
  (AI review, Micron, Advanced Evidence & Audit, Reviewed price,
  Comparable) keep their headings, conditionals, form ownership, and
  endpoints, with only shared-token visual polish.
* New tests: `tests/web/test_workbench_a1.py` (and, where a contract is
  presentation-adjacent, additive nodes in existing suites) covering
  intake prefill/validation/guard, all five report states, zero-price
  note, safe/unsafe URLs, vendor ALLOWED/DENIED no-leak, AI review
  availability + CSRF + historical rendering, comparable states, markup
  structure/landmarks, and narrow-viewport overflow behavior.
