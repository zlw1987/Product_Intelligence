# Product Intelligence — Current Status

## Current state

**PRODUCT-INTEL.PILOT-RELEASE-2-PROD-FIX1-FU4 (Vendor Paragraph
Entity Decoding + Synnex Availability Wire Type) — IMPLEMENTED /
PENDING FINAL REVIEW**

Bounded append-only corrective follow-up to the FU3 commit (SHA
2f8c693bd428527d17fb7268eee1b0fba5c014e6). FU3 has been independently
source-reviewed, deployed, and production-smoked. The production smoke
run a05a0aec-6f83-43d9-a3be-f9b41797f610 (requested MPN
`MTFDKBA480TFR-1BC1ZABYYR`, Micron 7450 PRO 480GB NVMe M.2 Non-SED)
completed with `ResearchRunState.COMPLETED`, but the persisted Vendor
result was `lookup_status=PARTIAL` / `retrieved_at=2026-09-25
02:16:02+00:00` / `observations=[]` / Ingram -> MALFORMED_SECTION /
CDW -> NOT_FOUND / Synnex EU -> MALFORMED_SECTION (no ResearchFx
Snapshot, because there were no usable Vendor observations). The FU3
outer-envelope fix DID work: the scanner now recognizes exactly
`<p>Ingram Product:` / `<p>CDW Product:` / `<p>Synnex EU Product:`.
The remaining failure was INSIDE the section literal representation —
two exact production-wire differences that FU3 did not cover, corrected
here with the narrowest bounded support. The previous implementation is
retained; no FU3 redesign; no deployment performed in this commit;
final approval remains with ChatGPT after independent GitHub review and
a later production smoke. (Canonical spec: PLAN §26.14.)

1. **Observed paragraph-envelope entity encoding (production-safe
   probe; structure/vocabulary only)** — the exact entity vocabulary
   inside the section values of the observed response (HTTP 200;
   `Content-Type: text/html; charset=utf-8`; approximately 5485 bytes;
   5 lines): Ingram — `&quot;` (166 occurrences), `&nbsp;`, `&cr;`; CDW
   — none; Synnex EU — `&quot;` (154 occurrences). No `&apos;` /
   `&lsquo;` / `&rsquo;` / `&amp;` / `&lt;` / `&gt;` and no numeric
   entity observed. After EXACTLY `&quot;` -> `"` (U+0022), `&nbsp;`
   -> LF (U+000A), `&cr;` -> CR (U+000D) — and nothing else — no
   recognized HTML entity remained and the UNCHANGED strict bounded
   literal parser succeeded: Ingram -> mapping (27 top-level keys),
   CDW -> not_found, Synnex EU -> mapping (2 top-level keys). At probe
   time Ingram mapped to 1515.72 USD CUSTOMER_PRICE OUT_OF_STOCK
   quantity 0 and Synnex to 966.58 EUR LIST_PRICE with
   `UnitPriceAmount` observed as the numeric string "966.58" (the
   existing `_safe_decimal` already supports numeric strings — no new
   generic price behavior) and `AvailabilityTotal` observed as the
   string "0". The old 962.86 EUR observation is historical; the
   962.86 vs 966.58 difference is mutable upstream commercial data, NOT
   an implementation acceptance invariant. The production contract is:
   exact requested MPN + valid finite non-negative price + EUR currency
   + LIST_PRICE + correct availability from the documented
   AvailabilityTotal semantics.
2. **Correction A: exact paragraph entity decoding (bounded)** — on
   the FU3 exact paragraph-envelope path ONLY, the section value text
   is normalized by EXACTLY three bounded literal replacements before
   the unchanged strict parser runs. This is NOT html.unescape, NOT a
   generic entity table, NOT an arbitrary entity regex: no other named
   entity (`&apos;` / `&lsquo;` / `&rsquo;` / `&amp;` / `&lt;` /
   `&gt;` / ...), no numeric entity (`&#...;`), no case/format variant
   is decoded — adversarially tested. The retained plain-text section
   contract is unchanged: literal entity spellings in a plain section
   remain plain text and are never decoded. Unknown/unapproved entity
   forms inside an authoritative literal remain fail-closed (a bare
   entity token outside a string fails the strict grammar ->
   MALFORMED_SECTION; inside a string it is inert raw text, never
   interpreted). A trailing `</p>` after a COMPLETE parsed value
   remains non-data interstitial material exactly as FU3 defined. The
   strict bounded literal grammar, the `{Not Found}` marker, the
   three-label allowlist, duplicate-label first-wins, max body size,
   one-network-call, no-redirect / no-proxy / no-eval / no-
   literal_eval behavior are all unchanged (re-proven). The raw Vendor
   body is never logged, persisted, put into exception detail, or
   exposed to user output.
3. **Correction B: Synnex nested string availability** — the current
   real nested Synnex wire represents
   `OnlineCheck.Item.AvailabilityTotal` as a non-negative integer,
   observed as the ASCII decimal digit STRING `"0"`. A narrow
   Synnex-specific reading (`_synnex_availability_total`) applied to
   the REAL nested path only accepts the existing `_safe_int` readings
   (non-negative int / finite integral Decimal) plus exactly the
   production-observed string form: ASCII decimal digits only,
   non-negative, no sign, no decimal point, no exponent, no whitespace
   coercion, bounded digit length ("0" -> 0, "12" -> 12). The GLOBAL
   `_safe_int` contract is UNCHANGED — it still rejects strings
   everywhere else (Ingram / CDW / flat Synnex compatibility form /
   other code paths). Rejected string forms ("-1" / "+1" / "1.0" /
   "1e2" / " 0 " / "" / "abc" / bool / float / list / dict /
   over-bounded) fail to UNKNOWN with quantity None — no stock state
   is fabricated.
4. **Faithful production-shaped full-adapter test (synthetic)** — the
   new fixture mirrors the CURRENT observed representation: exact `<p>`
   wrapper, `&quot;`-encoded quoted strings, `&nbsp;` / `&cr;` in a
   non-authoritative synthetic Ingram field, CDW `{Not Found}`, nested
   Synnex OnlineCheck with fake SessionId / BuyerAccountId / SystemId
   sentinels, numeric-string `UnitPriceAmount`, digit-string `"0"`
   `AvailabilityTotal`. Deterministic synthetic mapping: Ingram exact
   MPN / 1515.72 USD / CUSTOMER_PRICE / OUT_OF_STOCK / quantity 0;
   Synnex exact MPN / 962.86 EUR (explicitly synthetic) / LIST_PRICE /
   OUT_OF_STOCK / quantity 0; CDW NOT_FOUND; exactly one network call;
   sentinels and entity spellings absent from the normalized response.
5. **Full execution integration + authority proofs (encoded fixture)**
   — REAL `execute_research_run`: one Vendor network call; run
   COMPLETED; ResearchSupplementSnapshot PARTIAL with retrieved_at
   non-null, Ingram observation present, Synnex observation present
   (OUT_OF_STOCK / quantity 0 from the string "0"), CDW NOT_FOUND
   issue present; sensitive metadata absent from the persisted
   supplement; Machine Price immutable (deterministic zero-public-
   search fixture: zero buckets, no vendor values in the artifact);
   Vendor supplemental only (paid search not suppressed; no semantic
   input; no public-search authority; no human-confirmed authority);
   the usable Synnex EUR observation triggers the EXISTING 4D-C
   execution-time currency discovery (exactly EUR + USD requested from
   the deterministic injected FX provider; ResearchFxSnapshot persists
   EUR + USD) — no FX production code modification; Compact Quote
   historical replay (armed fail-fast zero-live Search / Page / Vendor
   / ECB constructor+fetch / semantic / urllib boundaries, exactly as
   the existing FU3 zero-live test): Ingram Vendor row present, Synnex
   Vendor row present, CDW row absent, Synnex USD Equivalent from the
   persisted ResearchFxSnapshot.

**PRODUCT-INTEL.PILOT-RELEASE-2-PROD-FIX1-FU3 (Vendor Paragraph
Envelope) — IMPLEMENTED / PENDING FINAL REVIEW**

Bounded append-only corrective follow-up to the FU2 commit (SHA
ec67f0f2f8f357fb77dd3cc1a5947e50a1b80af2) closing the exact remaining
production defect: on the approved SHA, the production Vendor response
for `MTFDKBA480TFR-1BC1ZABYYR` (run
f3a82fda-f708-4974-806e-d13a18482f96) was persisted as FAILED /
retrieved_at None / zero observations because the section scanner did
not recognize the real OUTER response envelope (defect inside Vendor
response contract recognition, before source mapping, 2A binding,
persistence, or Compact Quote projection). The previous implementation is
retained; ONLY the scanner's section-label recognition is extended with
the observed exact paragraph form, plus directly necessary tests/docs.
Not a feature phase; no 8A caching; no Vendor adapter redesign; no
deployment performed in this commit. Candidate state; final approval
remains with the project lead. (Canonical spec: PLAN §26.13.)

1. **Observed production envelope (structure-only probe, no values
   printed)** — HTTP 200; `Content-Type: text/html; charset=utf-8`;
   approximately 5485 bytes for the observed Micron lookup (5 lines);
   each known section label appears exactly once; each recognized
   section line carries an exact literal `<p>` immediately before the
   known label (the observed three-character line prefix is the HTML
   paragraph opener); the source payload remains bounded literal data.
   Structurally: `<p>Ingram Product: { ... }</p>` /
   `<p>CDW Product: {Not Found}</p>` /
   `<p>Synnex EU Product: { ... }</p>`.
2. **Exact paragraph-prefix scanner support (narrowest possible)** —
   each of the three exact known labels is recognized in exactly two
   outer forms: the existing plain line-anchored form (unchanged) and
   the observed exact paragraph-prefix form. Contract: `optional
   whitespace + optional exact "<p>" + exact bounded known label`.
   Deliberately NOT a generic HTML parser: no other tag (`<div>` /
   `<span>` / `<script>` — adversarially tested), no attributes
   (`<p class="x">`), no nesting (`<p><span>`), no case variants, no
   text before `<p>` on the line, no tag stripping, no HTML unescaping,
   no DOM text search, no BeautifulSoup/HTMLParser, no generic-HTML
   regex scraping. Unknown labels remain untrusted and ignored. The
   strict bounded literal parser remains responsible for the section
   value; malformed content INSIDE a literal still fails that source
   closed; one malformed source does not destroy valid siblings;
   duplicate-label first-wins, max body size, one-network-call,
   no-redirect, no-proxy, and no-eval/literal_eval behavior all
   preserved (re-proven). A trailing observed `</p>` after a COMPLETE
   bounded literal is the already-supported post-literal interstitial
   material (never data). The raw body is never logged or persisted.
3. **Source contracts unchanged (re-proven end-to-end)** — hybrid
   Ingram (`vendorPartNumber` + nested `pricing.customerPrice` /
   `retailPrice` / `currencyCode` + top-level boolean `availability` +
   top-level `Avl_Quantity`) maps the exact-MPN paragraph body to
   1515.72 USD CUSTOMER_PRICE / OUT_OF_STOCK / quantity 0; nested
   Synnex EU (`OnlineCheck.Header.CurrencyCode`,
   `OnlineCheck.Item.ManufacturerItemIdentifier` / `UnitPriceAmount` /
   `AvailabilityTotal`) maps to 962.86 EUR / OUT_OF_STOCK / quantity 0;
   CDW remains `{Not Found}`; SessionId / BuyerAccountId / SystemId
   (fake sentinels in tests) remain stripped by the allowlist and absent
   from the normalized response, the persisted snapshot, logs, and
   exception detail.
4. **Full execution integration (paragraph fixture)** —
   `execute_research_run` with the paragraph-wrapped real structural
   fixture: one Vendor network call; bounded PARTIAL; retrieved_at
   present; both observations persist in the
   ResearchSupplementSnapshot; Machine Price unchanged (zero buckets,
   no vendor values); Vendor supplemental only (paid search not
   suppressed; no semantic input); the usable Synnex EUR observation
   triggers the existing 4D-C execution-time currency discovery (EUR +
   USD requested from the FX provider — no FX production code altered);
   the injected deterministic provider's success persists a
   ResearchFxSnapshot and the Synnex EUR Compact Quote row receives its
   persisted USD Equivalent.
5. **Compact Quote historical replay (armed zero-live)** — Ingram
   Vendor row + Synnex EU Vendor row present, CDW row absent,
   USD Equivalent from the persisted FX snapshot, with armed fail-fast
   Search/Page/Vendor/FX/Semantic/network boundaries (zero live replay
   I/O).
6. **Preserved production evidence** — the Human Confirmed semantic
   listings → Compact Quote architecture proven by run
   f3a82fda-f708-4974-806e-d13a18482f96 remains accepted and
   unchanged. That run's absence of a ResearchFxSnapshot is explained
   by its inputs: frozen 4A had no reportable non-USD bucket; Vendor
   returned zero usable observations due to this parser failure; the
   human-confirmed EUR evidence was added only later through review.
   Historical replay must NOT perform a live ECB call merely because a
   later human confirmation introduces EUR — that zero-live historical
   contract remains frozen. A NEW run after this repair obtains FX
   during execution because the Synnex EUR observation is then a usable
   Vendor observation.

**PRODUCT-INTEL.PILOT-RELEASE-2-PROD-FIX1-FU2 (Public Replay
Persisted-Snapshot Authority) — IMPLEMENTED / PENDING FINAL REVIEW**

Bounded append-only corrective follow-up to the FU1 commit (SHA
681a4a8b67895e510eb277c850c0e83318af17b9) closing the FINAL independent
review blocker for PROD-FIX1. The previous implementation is retained;
ONLY the public replay's price-evidence authority source is corrected,
plus directly necessary tests/docs. Not a feature phase; no 8A caching
implemented; no deployment performed in this commit. Candidate state;
final approval remains with the project lead. (Canonical spec: PLAN
§26.12.)

1. **Public replay persisted-snapshot authority (FINAL BLOCKER)** —
   `replay_public_compact_quote_projection` no longer accepts a
   caller-supplied `PriceAggregationResult` (the `price_result`
   parameter is removed; the only parameter is `run`). The denied
   replay now owns its authority exactly like the authorized replay:
   it loads `PriceIntelligenceSnapshot.objects.get(run=run)`, decodes
   it through the canonical price-result codec, verifies
   `decoded.request == run.to_research_request()`, and uses THAT
   decoded persisted result for the frozen public bucket projection,
   the shared human-confirmed binding derivation, and the
   human-confirmed price/currency/condition evidence. A same-request
   cross-run result (identical source URL / product title / MPN field
   / SKU / evidence source, different persisted price — Run A 1890
   USD vs Run B 999 USD) can no longer substitute for the persisted
   snapshot: confirmation establishes identity authority only over the
   persisted evidence belonging to that same run, and historical
   reports stay immutable. Fail-closed: missing snapshot
   (DoesNotExist — the existing persisted-artifact behavior shared
   with the authorized replay), malformed payload / unsupported schema
   version (`PriceResultCodecError`), request-provenance-corrupt
   snapshot (`CompactQuoteProjectionError`). The view's DENIED branch
   call site is updated to `replay_public_compact_quote_projection(
   run=run)`; the ALLOWED branch is unchanged. Denied branch remains
   vendor-free (no `ResearchSupplementSnapshot` read, no commercial
   supplement codec import, zero live Search/Page/Vendor/ECB/Semantic/
   network work; persisted `ResearchFxSnapshot` still allowed) —
   re-proven with armed fail-fast sentinels including a real persisted
   supplement with a sentinel vendor price. Machine Price untouched
   (snapshots byte-identical before/after both replays on both runs);
   human review state semantics unchanged (UNREVIEWED / REJECTED /
   tampered / stale / cross-run / undo rules re-proven unchanged);
   authorized replay behavior unchanged; the shared binding primitive
   and the 8-step review-POST validation are unchanged in strength.

**PRODUCT-INTEL.PILOT-RELEASE-2-PROD-FIX1-FU1 (Production
Review-Blocker Closure) — IMPLEMENTED / FINAL REVIEW BLOCKER
CORRECTED BY FU2 / PENDING FINAL REVIEW**

Bounded append-only corrective follow-up to the independently reviewed
PROD-FIX1 commit (SHA 8811104e14103c41346c05471b3170c55c97386a). The
previous implementation is retained; ONLY the review blockers below are
corrected, plus directly necessary tests/docs. Not a feature phase; no 8A
caching implemented; no deployment performed in this commit. Candidate
state; final approval remains with the project lead. (Canonical spec:
PLAN §26.11.)

1. **Vendor production-wire fidelity (BLOCKER 1)** — the adapter now
   supports the ACTUAL hybrid production Ingram placement: explicit
   `vendorPartNumber`, nested `pricing` (customerPrice / retailPrice /
   currencyCode), TOP-LEVEL boolean availability signal + TOP-LEVEL
   `Avl_Quantity`. The nested-pricing branch keeps its pricing authority
   (customerPrice present => authoritative; retailPrice fallback only
   when the customerPrice key is absent), keeps the canonical nested
   availability dict, and recognizes the hybrid top-level placement
   through the SAME bounded truth table (contradiction => UNKNOWN fail
   closed; false + 0 => OUT_OF_STOCK/0; true + positive => IN_STOCK);
   unrelated fields (e.g. `vendorName`) stay ignored by the allowlist.
   The full `execute_research_run` integration test now uses the faithful
   hybrid Ingram section and the REAL nested Synnex EU section
   (`OnlineCheck.Header.CurrencyCode`,
   `OnlineCheck.Item.ManufacturerItemIdentifier/UnitPriceAmount/
   AvailabilityTotal`) with fake/redacted SessionId / BuyerAccountId /
   SystemId at their realistic structural locations (the Header block),
   stripped by the allowlist. The flat forms remain separately tested
   compatibility forms and are no longer described as the only/exact
   production wire shape. Proof: exact MPN `MTFDKBA480TFR-1BC1ZABYYR` →
   one Ingram observation (1515.72 USD customer price, OUT_OF_STOCK,
   quantity 0), one Synnex EU observation (962.86 EUR, OUT_OF_STOCK,
   quantity 0), CDW NOT_FOUND.
   Section-scanner/strict-parser consistency: only the three exact
   line-anchored labels establish sections; a COMPLETE bounded literal is
   authoritative; unknown/interstitial text after it is never parsed into
   data and cannot poison the section; malformed content INSIDE a literal
   still fails that source closed (no generic HTML scraping).
2. **Human-confirmed authority ownership (BLOCKER 2)** — the single pure
   candidate-to-assessment binding primitive
   (`research.matching.is_review_candidate_binding_valid`) is now shared
   by the web GET presentation, the 8-step review-POST validation (unchanged
   in strength), and both historical replay boundaries — the binding rule
   exists in exactly one place. Both replay entry points
   (`replay_compact_quote_projection`,
   `replay_public_compact_quote_projection`) NO LONGER accept any
   caller-supplied index parameter: the effective human-confirmed
   selection is derived from PERSISTED state by
   `execution.compact_quote_replay.derive_human_confirmed_assessment_indices`,
   which proves each row is (1) an AiAssistedReviewCandidate for THIS run,
   (2) review_state CONFIRMED, (3) mapped to an in-range assessment index,
   (4) fully bound to that assessment (shared primitive), (5) still
   human-review eligible, (6) persisted price/currency exist (enforced by
   the projection). A bare caller integer can never mint HUMAN_CONFIRMED
   authority. The lowest-level pure projection helper
   (`project_human_confirmed_rows`) is retained as an
   already-authorized-selection consumer with that contract stated
   explicitly, keeping its defense-in-depth fail-closed checks.
   Machine Price untouched; human review run-scoped; historical GET
   remains zero-live-I/O.
3. **ECB trust-chain evidence correction (BLOCKER 3)** — NO insecure TLS
   bypass exists or was added; `providers/fx.py` remains unchanged. A
   later SECURE retry from the SAME production Python runtime (without
   installing certifi, without manually installing a certificate,
   without changing fx.py, without disabling TLS verification) succeeded
   and returned official rates: observation date 2026-09-24, USD 1.1367,
   ZAR 18.6836. Confirmed truth: the SSL certificate-chain verification
   failure WAS observed earlier; it was correctly converted to
   FxNetworkError; the run correctly completed without
   ResearchFxSnapshot; a later secure retry succeeded; no application
   change was required; the exact reason for the transient failure has
   NOT been proven; there is currently NO evidence-backed requirement to
   install/update a CA trust store (no such action is recorded as
   outstanding fact). The failure-path regression tests are retained
   (not removed, not weakened).
4. **Reviewed Price wording accuracy (presentation defect)** — the
   Reviewed Price summary sentence no longer states "includes N
   human-confirmed listings" from the validated-CONFIRMED-candidate count
   when fewer are actually price-eligible (e.g. UNKNOWN condition). The
   template now derives the truthful price-contributing counts from the
   reviewed buckets themselves (per-bucket `human_confirmed_count` /
   `deterministic_count` sums) and renders conditionally truthful wording.
   Reviewed-price eligibility is NOT changed to make the count match.

**PRODUCT-INTEL.PILOT-RELEASE-2-PROD-FIX1 (Production Correction) —
IMPLEMENTED / REVIEW BLOCKERS CORRECTED BY FU1 / PENDING FINAL REVIEW**

Bounded production-correction phase fixing defects discovered during real
Product Intelligence production use on the deployed PILOT-RELEASE-2 runtime
(frozen deployed runtime SHA 065320180c17b89c7460164326a0c9f49e01fe3b). Not a
feature phase; no 8A caching implemented; no deployment performed in this
commit. Candidate state; final approval remains with the project lead.

Corrections delivered (details in PLAN §26.10; review-blocker closures in
PLAN §26.11 / FU1 above):

1. **Vendor real-response contract** — the production Vendor API answers
   HTTP 200 / `text/html` with a section-oriented body that is NOT one JSON
   document (`Ingram Product: { ... }` / `CDW Product: {Not Found}` /
   `Synnex EU Product: { ... }`). The Internal Vendor adapter supports that
   bounded contract in addition to the retained canonical JSON wrapper:
   strict recursive-descent literal parsing (no eval / literal_eval), the
   exact `{Not Found}` bounded marker, the three exact section labels only,
   production field placements (canonical nested, the FU1 hybrid
   top-level-availability form, and the flat compatibility form) mapped
   through the SAME allowlist mappers, exact Decimal monetary behavior,
   exactly-one network call, transport/failure behavior preserved, one
   malformed section does not destroy valid siblings. The real Synnex
   sensitive metadata (SessionId / BuyerAccountId / SystemId) is stripped
   by the allowlist and never enters candidates, snapshots, logs, or error
   detail; the raw body is never persisted. Integration proof: exact MPN
   `MTFDKBA480TFR-1BC1ZABYYR` with the faithful hybrid production shape
   yields one Ingram observation (1515.72 USD, customer price,
   OUT_OF_STOCK, quantity 0), one Synnex EU observation (962.86 EUR,
   OUT_OF_STOCK, quantity 0), and a CDW NOT_FOUND issue.
2. **Currency formatting** — the Compact Quote price formatter no longer
   uses the currency code as a fallback prefix and appends it again.
   Known-symbol currencies keep `$1,515.72 USD` / `€962.86 EUR`; no-symbol
   currencies render once (`ZAR 30,999.0`, never `ZAR30,999.0 ZAR`). Decimal
   values and FX math untouched.
3. **AI-assisted semantic matches placement** — presentation-only reorder of
   `research_detail.html`: the section now renders immediately after
   "Compact quote summary" and before the detailed lower-level
   audit/research sections. Semantic eligibility and model behavior
   unchanged.
4. **Confirm Match -> Compact Quote** — a valid run-scoped, human-CONFIRMED
   semantic candidate now contributes a Compact Quote row for that SAME
   ResearchRun (projection-layer extension; frozen 4A artifacts never
   mutated). Identity authority only: price/currency from the persisted
   PriceIntelligenceSnapshot assessment, condition EXACTLY the persisted
   normalized condition (UNKNOWN stays "Unknown"; never upgraded), explicit
   "Human Confirmed" provenance note, persisted FX evidence only. UNREVIEWED
   / REJECTED / invalid-binding / cross-run candidates never enter; Undo
   removes the row on the next GET; historical GET remains zero live I/O.
   Machine Price and the frozen Reviewed Price behavior are unchanged.
5. **Research submit duplicate-click guard** — front-end-only inline JS on
   the new-research form: on valid submit the button is immediately
   disabled and relabeled `Researching…`. UX protection only — NOT a
   backend dedupe guarantee; no run sharing, MPN locking, caching, or
   lifecycle change. Invalid client-side validation leaves the button
   enabled.
6. **ECB / USD Equivalent TLS issue** — investigated, NOT bypassed. The
   production `ssl.SSLCertVerificationError` (unable to get local issuer
   certificate) is the secure verification working as designed; the
   provider classifies it as bounded `FxNetworkError` and orchestration
   keeps FX failure nonfatal (no ResearchFxSnapshot, original non-USD price
   survives, USD Equivalent unavailable) — locked in by regression tests,
   including mechanical no-insecure-bypass guards, all RETAINED by FU1.
   FU1 evidence correction: a later SECURE retry from the same production
   Python runtime (no certifi install, no manual certificate, no fx.py
   change, no disabled TLS verification) succeeded (observation date
   2026-09-24; USD 1.1367; ZAR 18.6836). The exact reason for the
   transient trust-chain failure has NOT been proven; there is currently NO
   evidence-backed requirement to install/update a CA trust store, and no
   such action is recorded as outstanding fact. No code change was
   required; if a future phase wants an explicitly configured trusted CA
   bundle, that is a new configuration contract to be designed and approved
   separately (none exists in the repository today).

**PILOT-RELEASE-1 DEPLOYED / ACCEPTED**

Internal pilot deployment is deployed and accepted on the internal Windows pilot server.

Verified live:
- pilot_check PASS
- Waitress service
- remote browser access
- real Serper execution
- AMAX / nemotron-3-super primary semantic execution
- human review
- comparable research
- persistent SQLite
- Windows service

**PRODUCT-INTEL.PILOT-UX — Semantic qualification APPROVED/FROZEN;
FU3A Production Semantic Runtime Contract APPROVED/FROZEN;
FU3B Semantic Execution Integration APPROVED/FROZEN;
HUMAN-REVIEW Human Review for AI-Assisted Matches APPROVED/FROZEN;
6B Enterprise SSD Category Schema APPROVED / RE-FROZEN;
6C Specification Evidence Extraction & Resolution IMPLEMENTED/APPROVED/FROZEN;
7A Comparable-Product Candidate Discovery IMPLEMENTED / APPROVED / FROZEN;
7B Enterprise SSD Similarity Scoring IMPLEMENTED / APPROVED / FROZEN.**
6D Authoritative Datasheet Specification Enrichment IMPLEMENTED / APPROVED / FROZEN

**PRODUCT-INTEL.4D — Customer Quote Research Expansion:
IMPLEMENTED / APPROVED / FROZEN / COMPLETE**

The complete customer-requirement expansion is closed: every 4D component
is approved and frozen. 4D-D (including correction pass 4D-D-FU1) was
IMPLEMENTED / PENDING FINAL REVIEW as the original candidate, was corrected
by FU1, was independently reviewed afterward, and is now APPROVED / FROZEN
(the candidate narrative below is preserved as history).

4D freeze record (4D-D, the last component frozen):
Frozen SHA: 065320180c17b89c7460164326a0c9f49e01fe3b
Frozen collection baseline: 5097 collected
Final acceptance execution: 5097 passed, 0 failed, 0 skipped,
0 xfailed, 0 deselected (+ 39 subtests passed)

**PILOT-RELEASE-2 (4D Customer Requirement Deployment & UAT) —
DEPLOYED / ACCEPTED**

Deployment/UAT phase, now closed: the already-frozen 4D customer
requirements are deployed to the internal production/pilot Windows
server. The recorded representative 4D production smoke validation
covered: a normal customer quote flow exercising current Price
Intelligence / Compact Quote behavior; Micron 7500 R/T packaging-alias
behavior.
The previously planned broader UAT matrix (direct-source acquisition
using a viable preferred-source case; normal Serper fallback; real
Vendor API commercial evidence; compact quote rendering; non-USD vendor
evidence + persisted ECB USD equivalent; Micron 7500 packaging-alias
BASE/R/T behavior; a non-eligible MPN proving alias abstention; Visual
FoxPro launcher -> browser prefill against the deployed server;
historical report reload causing zero new Search/Vendor/ECB/Micron/
Semantic live work; vendor-price access behavior under the existing
frozen network gate (4D-C-SEC REMOTE_ADDR / PI_VENDOR_PRICE_ALLOWED_
CIDRS, unchanged)) remains a validation reference; the production
records do not claim that every matrix case was separately executed
and evidenced during the 2026-09-23 cutover.

Deployment record:
- Deployed runtime SHA: 065320180c17b89c7460164326a0c9f49e01fe3b — the
  independently reviewed and frozen PRODUCT-INTEL.4D-D-FU1 runtime SHA.
  Deployment is Git-managed and exact-approved-SHA based (local
  `production` branch pinned to independently approved SHAs).
- Production smoke test passed: 2026-09-23.
- 4D is deployed; migrations through
  0010_research_micron_alias_snapshot are deployed (4D migrations
  0008 / 0009 / 0010).
- Production environment details (application path, persistent SQLite,
  service ID / WinSW wrapper, Waitress, port, health endpoint, 4D
  preferred-source configuration with `directmacro.com` enabled,
  Vendor API configuration) are recorded in the operational Confluence
  references and are not duplicated in this repository.
- The deployment relies on the internal server/network perimeter as the
  pilot authorization boundary; no application login/session/OAuth/
  per-user authorization is introduced.

Current pilot authentication decision (unchanged): the pilot server
itself has restricted access; people who can reach this internal server
are currently considered authorized for this pilot. Full application
authentication, login/session identity, OAuth, and per-user
authorization are NOT part of PILOT-RELEASE-2; they remain deferred
future production-hardening concerns (8C). Report UUID is not access
control. No session-based authorization is introduced. The frozen
4D-C-SEC vendor-price network gate is unchanged.

Runtime-vs-docs distinction (binding):
- Runtime freeze / deployed SHA = 065320180c17b89c7460164326a0c9f49e01fe3b.
- The later commits c6ad6ae (PRODUCT-INTEL.4D-CLOSE) and 7ff0ab7
  (PRODUCT-INTEL.4D-CLOSE-FU1) are docs-only project-state closures;
  production does not need to move merely to obtain those
  documentation edits.
- 7ff0ab7 is NOT the production runtime SHA; the deployed production
  runtime at 0653201 is intentional and correct.

**NEXT: PRODUCT-INTEL.8A-PRE (Caching & Freshness Architecture
Audit)** — PLANNED

The production-correction phase PRODUCT-INTEL.PILOT-RELEASE-2-PROD-FIX1
(above) and its bounded review-blocker closures PRODUCT-INTEL.PILOT-
RELEASE-2-PROD-FIX1-FU1 and PRODUCT-INTEL.PILOT-RELEASE-2-PROD-FIX1-FU2
(and the FU3 paragraph-envelope closure and the FU4 vendor paragraph
entity decoding + Synnex availability wire-type closure) are PENDING
FINAL REVIEW and do NOT change the next-architecture-delivery selection
below. 8A caching is NOT implemented in PROD-FIX1, FU1, FU2, FU3, or
FU4.

The previous "post-UAT next is undecided" gate is closed: the
production deployment/smoke evidence now exists and the project lead
has selected the next architecture investigation.

8A-PRE is a READ-ONLY / DESIGN-FIRST phase: it investigates and records
a caching and freshness architecture before any caching
implementation. It is NOT authorization to implement caching, and no
actual TTL values are approved in this closure.

Reason for choosing 8A-PRE: Product Intelligence is now in production,
and evidence classes have materially different freshness requirements.
The design must prevent stale evidence from being presented as current
while also avoiding unnecessary paid/live calls.

The future 8A design must distinguish at minimum:
- market/public prices — short freshness
- Vendor commercial observations — short freshness
- ECB FX rates — tied to persisted official observation date
- product specifications — longer freshness
- comparable research — medium freshness
- deterministic identity/authority evidence — not automatically
  equivalent to market-price freshness
- user/operator forced refresh
- historical reports — immutable replay, NEVER refreshed merely by GET

Later planned (directional; not an approved implementation order):
5A (Structured external API — PLANNED / NON-BLOCKING), 8B (Research
history — PLANNED), 8C (Production hardening — PLANNED). None of them
is NEXT. Authentication/session remains outside the current priority.

```
4D-PRE  Preferred Source Feasibility Audit  (evidence only) — APPROVED / FROZEN
4D-A    Source Acquisition Optimization — APPROVED / FROZEN
4D-B    Internal Vendor Commercial Evidence  — APPROVED / FROZEN
4D-C-A  ECB FX + Compact Quote Projection Foundation — APPROVED / FROZEN
4D-C-SEC Vendor Commercial Price Access Gate — APPROVED / FROZEN
4D-C    Compact Quote Summary (browser rendering) — APPROVED / FROZEN
4D-D-PRE1 Early 4D-D authority feasibility review — APPROVED / FROZEN
4D-D-PRE2 Micron official authority evidence capture — APPROVED / FROZEN
4D-D    Micron Packaging Alias Retrieval — APPROVED / FROZEN
4D-D-FU1 Runtime reachability + query-semantics closure — APPROVED / FROZEN
```

**PRODUCT-INTEL.4D-B — APPROVED / FROZEN**

Frozen SHA: c74c90b0590d1c393419d94a1c107bfe93f7143c
Frozen test baseline: 4299 collected

Internal Vendor API integrated as supplemental commercial evidence.
Key facts:
- Provider-neutral commercial boundary: `providers/commercial.py`
- Concrete adapter: `providers/internal_vendor.py`
- Supplemental persistence: `runs.ResearchSupplementSnapshot` (migration 0008)
- Versioned codec: `research/commercial_supplement_codec.py` (V1)
- At most ONE Vendor API call per ResearchRun
- Frozen 2A identity binding required for each commercial observation
- Brand new by VENDOR_API_POLICY (not source-published condition)
- **NO web exposure** — 4D-B does NOT render vendor commercial prices
- **NO authority expansion** — vendor evidence does NOT enter Machine Price,
  Reviewed Price, semantic authority, or comparable scoring
- Sensitive metadata (SessionId, BuyerAccountId, SystemId) stripped by allowlist
- 4D-C security gate resolved by frozen 4D-C-SEC REMOTE_ADDR-only access policy;
  4D-C browser rendering implemented (PRODUCT-INTEL.4D-C, approved / frozen)

**PRODUCT-INTEL.4D-C-A — APPROVED / FROZEN**

Frozen SHA: 059ade96ff2141684b973e576adcc91a10094707
Frozen test baseline: 4582 collected

ECB FX evidence persistence + Decimal-only USD-equivalent calculation +
deterministic compact quote-summary projection + historical-report replay.
Key facts:
- ECB FX provider: `providers/fx.py` (provider-neutral boundary + ECB adapter)
- FX persistence: `runs.ResearchFxSnapshot` (migration 0009)
- FX codec: `research/fx_codec.py` (V1)
- FX mathematics: `research/fx_math.py` (pure Decimal-only, ECB formula)
- Compact quote projection: `research/compact_quote.py` (data contract + tests)
- **NO browser HTML exposure** — 4D-C-A does NOT render vendor commercial prices
- ECB formula: USD Equivalent = amount_C / rate_C * rate_USD
- Semantic qualification APPROVED AND FROZEN (prompt v1.1, corpus, thresholds)
- Primary route: amax/nemotron-3-super; Fallback route: vllm-262k/Qwen3.6-27B-262K

**PRODUCT-INTEL.4D-C-SEC — APPROVED / FROZEN**

Frozen SHA: 75bfbe3d1b4a8abc12d655cc903298f08e06a8f0
Frozen test baseline: 4693 collected

4D-C-SEC establishes the server-side network access gate. Key facts:
- Configuration: `PI_VENDOR_PRICE_ALLOWED_CIDRS` (environment variable)
  - Comma-separated CIDR notation (IPv4/IPv6)
  - Absent or blank -> DENY (fail-closed default)
  - Example deployment value (never hardcoded): `10.0.0.0/8,192.168.50.0/24,172.16.8.0/21`
- Client address authority: `request.META["REMOTE_ADDR"]` ONLY
  - X-Forwarded-For, X-Real-IP, Forwarded header never trusted
  - Query parameters, cookies, Host header never trusted
  - Report UUID never access control
  - Proxy-aware client IP requires a separately reviewed trusted-proxy contract
- Module: `product_intelligence/web/commercial_access.py`
- Pure parsing function `_parse_allowed_cidrs` separately testable
- `CommercialPriceAccessConfigurationError` for malformed CIDR config
- Malformed CIDR -> entire config fails closed (deny all)
- IPv4 and IPv6 both supported
- Django setting read with lazy import pattern
- No auth, sessions, user models, OAuth, login pages, API tokens
- No changes to research/, providers/, or domain/ layers
- Views integration: `research_detail()` passes `vendor_commercial_access_allowed`
  boolean to template context — NO raw payload, NO vendor rows, NO sensitive metadata
- 4D-C browser rendering implemented (PRODUCT-INTEL.4D-C), approved / frozen;
  the server-side security branch selects authorized full replay vs denied
  public-only replay before any vendor supplemental artifact access
- Full application authentication deferred to 8C
- **NO authority expansion** — FX and projection do NOT enter Machine Price,
  Reviewed Price, semantic authority, or comparable scoring
- Historical replay: zero live FX calls, zero live Vendor API calls
- USD Equivalent is DISPLAY-SUPPLEMENTAL only
- ECB formula: USD Equivalent = amount_C / rate_C * rate_USD

**PRODUCT-INTEL.4D-C — APPROVED / FROZEN**

Frozen SHA: 4592b8966b703dfd6a72c3067d7b191314ff2968
Frozen test baseline: 4766 collected

Compact Quote Browser Rendering. Frozen prerequisites: 4D-C-A (SHA
059ade96ff2141684b973e576adcc91a10094707, 4582 collected) and 4D-C-SEC
(SHA 75bfbe3d1b4a8abc12d655cc903298f08e06a8f0, 4693 collected). Key facts:
- Server-side security branch in `research_detail()` occurs BEFORE any
  Vendor supplemental artifact is read, decoded, or projected
- ALLOWED: frozen 4D-C-A `replay_compact_quote_projection(str(run.id))`
  (complete projection; may read PriceIntelligenceSnapshot,
  ResearchFxSnapshot, ResearchSupplementSnapshot; zero live provider /
  network / semantic work; fail-closed behavior unchanged)
- DENIED: new public-only bounded read-side service
  `execution/compact_quote_public_replay.py` —
  `replay_public_compact_quote_projection`: PUBLIC_LISTING rows only via
  frozen `project_public_rows` + persisted FX evidence; NEVER reads
  ResearchSupplementSnapshot and never imports/calls vendor API,
  search, page, semantic, or ECB live provider paths
- Compact summary is built only when the existing
  PriceIntelligenceSnapshot decoded AND passed the existing request
  provenance check (`decoded.request == run.to_research_request()`);
  otherwise existing report error behavior is preserved
- New display-only web module `web/compact_quote_presentation.py`:
  vendor source labels `Ingram (Vendor API)` / `CDW (Vendor API)` /
  `Synnex EU (Vendor API)` (suffix appended once, never duplicated);
  public sources display hostname with leading `www.` stripped and the
  full SAFE source URL (from the paired frozen 4A bucket-member
  assessment, deterministic iteration order) as the link target via the
  reused `presentation._is_safe_href_url` helper; vendor rows never
  receive a URL; mapping mismatch fails closed (no guessed links)
- Template context never contains Vendor rows on the denied path — the
  `vendor_commercial_access_allowed` boolean is used only for the
  neutral notice, never as the row-hiding mechanism
- "Compact quote summary" table (Source / Price / USD Equivalent /
  Inventory / Brand New / Note) rendered near the top of the report,
  before the detailed Price Intelligence audit/evidence sections;
  existing sections untouched (additive only)
- No-data states: "No compact quote evidence is available." (zero rows)
  and "Compact quote summary unavailable." (expected persisted-artifact
  / projection failure only; programming errors propagate)
- REMOTE_ADDR-only authorization preserved (4D-C-SEC frozen policy);
  no forwarded-header logic added
- NO authority expansion: Vendor rows remain SUPPLEMENTAL DISPLAY ONLY
  (not Machine Price, Reviewed Price, deterministic/semantic identity,
  or comparable scoring); public compact rows derive only from frozen
  4A bucket membership; excluded listings never enter compact rows
- Web execution allowlist extended ONLY with
  `replay_compact_quote_projection` and
  `replay_public_compact_quote_projection` (public package API);
  web research allowlist extended ONLY with
  `compact_quote.{CompactQuoteProjection, CompactQuoteRow,
  CompactQuoteProjectionError}`, `fx_codec.FxCodecError`,
  `commercial_supplement_codec.SupplementCodecError`
- Frozen 4D-C-A `replay_compact_quote_projection()` behavior unchanged;
  the new service is additive

**PRODUCT-INTEL.4D-D-PRE1 — APPROVED / FROZEN**

Early 4D-D authority feasibility review. Binding conclusion at the time:
`NO CURRENT 4D-D ELIGIBILITY AUTHORITY EXISTS` (no reviewed manufacturer
authority chain available for packaging-alias retrieval; the requirement
remained customer-ruled and retrieval-only).

**PRODUCT-INTEL.4D-D-PRE2 — APPROVED / FROZEN**

Evidence SHA: 1cb65a3d6002006af9e1c77906a6de6b5a3fd42c

Micron official authority evidence capture (evidence only; no production
code). Recorded 12 sanitized anonymous-GET fixtures under
`tests/fixtures/pages/` plus `docs/MICRON_ALIAS_AUTHORITY_EVIDENCE.md`.
Recommendation: `AUTHORITY_EVIDENCE_SUFFICIENT_FOR_4D_D_SSD_V1`, scoped:
SSD only; the structured BASE catalog record owns the exact-MPN proof and
the `is-ssd` category proof; R/T per-part endpoints return
`Invalid Partnumber` and R/T page metadata is template echo — neither is
authority; no official R/T packaging-semantic statement exists.

**PRODUCT-INTEL.4D-D — APPROVED / FROZEN** (including correction pass
4D-D-FU1; the original candidate state — IMPLEMENTED / PENDING FINAL
REVIEW until corrected — is historical; see the FU1 approval record below)

Frozen SHA: 065320180c17b89c7460164326a0c9f49e01fe3b
Frozen collection baseline: 5097 collected
Final acceptance execution: 5097 passed, 0 failed, 0 skipped, 0 xfailed,
0 deselected (+ 39 subtests passed)

Micron Packaging Alias Retrieval, v1 scope: **Micron 7500 SSD ONLY** (not
generic Micron memory, not DRAM, not any other family; extending requires
additional reviewed authority policies and recorded manufacturer evidence).

Authority split (binding):

```
Micron catalog (reviewed 4D-D-PRE2 family-catalog endpoint):
    manufacturer / category / source-published BASE authority

Customer rule (final uppercase R/T strip, base must re-derive):
    R/T retrieval relation only (MICRON_PACKAGING_ALIAS)
    — never identity, never pricing authority
```

Key implementation facts:

- Pure research contracts: `research/micron_packaging_alias.py` — reviewed v1
  policy constants (policy id `micron-7500-ssd-part-catalog-v1`,
  manufacturer `Micron`, category `SSD`, exact reviewed catalog URL,
  approved origin `https://www.micron.com`), deterministic fail-closed
catalog-record extraction over the recorded fixture shape, `is-ssd == True`
(category evidence from the matched row's own structured attribute — never
inferred from description/URL/prefix/model knowledge), customer-rule
lookup-base derivation (final uppercase R/T only; lowercase and degenerate
inputs abstain), self-validating `MicronPackagingAliasRelation` and
`MicronAliasEligibilityResult` (every authority-bearing binding re-derived
at construction; frozen 2A `compare_part_numbers` used only for catalog-row
matching and reference labeling — frozen 2A/3C semantics unchanged, family
forms are NEVER established under 2A), `find_alias_reference` (read-side
reference labeling against alias identifiers only).
- Execution authority acquisition: `execution/micron_alias_authority.py` —
module-private reviewed v1 policy (no environment/DB/caller injection);
ONE reviewed family-catalog fetch per direct-insufficient non-empty-MPN
run through the existing PageFetcher protocol; bounded status vocabulary
(ESTABLISHED / NO_REQUESTED_MPN / INVALID_LOOKUP_BASE / NO_AUTHORITY_MATCH /
AMBIGUOUS_AUTHORITY_MATCH / CATEGORY_NOT_SSD / FETCH_FAILED / SOURCE_REFUSED /
HOST_ESCAPED / PARSE_FAILED); origin boundary (scheme downgrade, host
escape, port change, unparseable all fail closed); only the expected
provider classes are downgraded (`PageFetchError` -> FETCH_FAILED,
`UnsafeFetchTargetError` -> SOURCE_REFUSED) — no broad `Exception` catch
exists (FU1): a bare `Exception` or `RuntimeError` propagates to the
catastrophic boundary, and dependency-contract defects (fetcher without a
callable `fetch`; `fetch` returning a non-`FetchedPage` / contract-invalid
object) propagate `TypeError` rather than receiving a bounded status;
R/T detail endpoints are never fetched (not authority).
- Orchestration wiring (`execution/orchestration.py`, additive): the alias
  step runs only when fallback search is required AND the request MPN is
  non-empty; the bounded audit is persisted (its own pre-search durability
  step) BEFORE the ONE paid search; only an ESTABLISHED result changes the
  query (to `build_alias_expanded_search_query` — frozen OR shape: one
  parenthesized OR group `("REQUESTED" OR "ALIAS1" OR "ALIAS2")`, requested
  MPN first, established aliases in deterministic relation order, plus the
  ordinary description; the group alone when there is no description — an
  AND grouping would require every identifier simultaneously and defeat the
  recall purpose); every other result keeps the ordinary frozen query;
  `build_search_query` is unchanged; direct-sufficient runs perform zero
  Micron authority fetch and zero paid search; default runtime wiring (FU1):
  with no explicitly injected page fetcher the ordinary candidate fetcher
  is the frozen HTML-only default `HttpPageFetcher` and the ONE Micron
  authority fetch uses a lazily created JSON-configured `HttpPageFetcher`
  (explicit additive `accepted_media_types`/`accept_header` constructor
  capability; default configuration byte-equivalent to frozen 3A behavior,
  default `application/json` refusal unchanged) — the reviewed catalog
  endpoint publishes `application/json;charset=utf-8` (PRE2), so the HTML
  only default could never reach ESTABLISHED in the real runtime; an
  explicitly injected fetcher governs the authority fetch as well
  (deterministic fake-provider tests); semantic
  firewall: with an ESTABLISHED alias-expanded search, non-ACCEPTED
  assessments from that search batch are excluded from
  `evaluate_semantic_matches` (no AI_ASSISTED_MATCH / review candidates /
  Reviewed Price path membership) while remaining in frozen 4A input and
  exclusions; direct and ordinary non-alias assessments retain frozen
  semantic behavior; deterministic exact requested-MPN listings keep normal
  frozen 4A behavior.
- Persistence: `runs.ResearchMicronAliasSnapshot` (migration 0010) —
OneToOne per run (absent when acquisition was not performed),
`schema_version` 1, opaque codec-owned JSON payload, body SHA-256 (never
the catalog body), cascade with the run.
- Codec: `research/micron_alias_codec.py` (V1) — strict key sets, rejects
extra/missing keys and unknown versions, deterministic UTC second
precision, decode reconstructs the self-validating result so a tampered
payload cannot re-label a foreign manufacturer/category/URL/origin as v1
authority (fail closed).
- Web: `web/micron_alias_presentation.py` (display-only; consumes the
decoded persisted audit structurally per the frozen web-aggregation import
boundary) + a separate, clearly labeled "Micron packaging alias evidence"
section in `web/research_detail.html` rendered ONLY from the persisted
snapshot on historical GET (zero live Micron / search / vendor / FX /
semantic / network work, armed-fail-fast proven by
`tests/web/test_micron_alias_report.py`); alias reference rows are
persisted EXCLUDED assessments only — separate section, never Compact /
Machine / Reviewed / Comparable authority; fail-closed on codec error or
request-provenance mismatch (no partial alias data, main report unaffected).
- Boundary allowlists extended exactly: web research allowlist gains
`micron_alias_codec.{MicronAliasCodecError, decode_micron_alias_snapshot}`
and `micron_packaging_alias.{MicronAliasEligibilityStatus,
MicronAliasEligibilityResult, find_alias_reference}`; web runs-model import
guard gains `ResearchMicronAliasSnapshot`; model inventories in
`test_provider_boundaries.py`, `test_research_identity_boundaries.py`,
`test_web_boundaries.py`, `test_research_run_boundaries.py`, and
`test_comparable_research_execution.py` updated to the exact supersets.
- Final-acceptance hardening (this session, disclosed):
  `providers/http_page.py` — secure-transport setup failure
  (`ssl.SSLError` at TLS-context creation, an environmental
  Windows/Python-3.14 flake) is now classified as the adapter's bounded
  `PageFetchError` like every other transport failure (previously it
  escaped the classification); fetch semantics unchanged. Kept in FU1 as a
  separately tested transport-classification fix (regression: `_build_opener`
  OSError -> `PageFetchError`; non-OSError programming errors propagate).
  Frozen test doubles updated where 4D-D's documented pre-search authority
  fetch is visible to them: 4D-A same-URL dedup proofs are now per-URL
  (strengthened) and account for the one bounded authority fetch; the
  FX full-persistence double supplies the `FetchedPage`-required
  `retrieved_at` it was missing (the FX path is now actually exercised);
  the web REAL-0001 fetch proof is per-URL (strengthened) and accounts for
  the one bounded authority fetch.
- FU1 corrections (this session, disclosed; supersede the authority-module
  bounded-surface wording above): the interim 4D-D pass had bounded
  uncallable fetchers, unclassified bare-`Exception` fetch failures, and
  non-conforming fetch results to `FETCH_FAILED`; independent review
  classified these as dependency/programming contract defects, and FU1
  removes that broad catch entirely (only `PageFetchError` /
  `UnsafeFetchTargetError` are downgraded; bare `Exception`, `RuntimeError`,
  non-callable `fetch`, and non-`FetchedPage` returns propagate). Frozen
  test doubles that relied on the old bounded surface were corrected to
  contract-conforming `FetchedPage` returns / classified transport errors
  (4C-B evidence-write tests, 4D-A network-error fetcher, 4C-B credential
  placeholder fetcher, execution REAL-0001 per-URL fetch proof): intent and
  assertions preserved, none deleted, renamed, skipped, xfailed, or
  deselected.

**PRODUCT-INTEL.4D-D-FU1 — APPROVED / FROZEN**

Runtime reachability + query-semantics closure for 4D-D (append-only
correction on top of the 4D-D implementation commit; the 4D-D scope,
policy, status vocabulary, persistence, codec, web, and firewall semantics
are unchanged). Fixes three independently verified source-level acceptance
blockers:

- BLOCKER 1 — real default runtime reachability: the production authority
  endpoint returns `Content-Type: application/json;charset=utf-8` (PRE2),
  but the real default `HttpPageFetcher` accepted exactly `text/html` /
  `application/xhtml+xml`, so `MICRON_PACKAGING_ALIAS` was unreachable in
  the real default runtime (authority fetch -> content-type refusal ->
  FETCH_FAILED -> ordinary query). Fix: ADDITIVE immutable
  `accepted_media_types` / `accept_header` constructor configuration on the
  existing `HttpPageFetcher` (no second HTTP/provider abstraction; no
  browser; no requests/httpx; no cookie/proxy/auth). Default configuration
  is exactly the frozen 3A behavior (`application/json` still refused by
  default; the default refusal regression remains). JSON mode accepts
  exactly `application/json` (parameters and casing ignored) and nothing
  else, sends `Accept: application/json`, and keeps every SSRF / redirect /
  credential / timeout / size bound. Default orchestration wiring:
  `execute_research_run(page_fetcher=None)` now keeps the HTML-only default
  candidate fetcher and lazily creates the JSON-configured authority
  fetcher ONLY when fallback search is required AND the request MPN is
  non-empty (direct-sufficient runs never instantiate or fetch it); an
  explicitly injected fetcher governs the authority fetch as well (existing
  deterministic fake-provider tests preserved). Mandatory real-adapter
  integration: the REAL `HttpPageFetcher` with network internals safely
  monkeypatched/offline (public DNS fixture + controlled opener returning
  the PRE2-recorded catalog bytes with the recorded Content-Type) reaches
  ESTABLISHED for `MTFDKCC3T8TGP-1BK1DABYYR` (matched base
  `MTFDKCC3T8TGP-1BK1DABYY`, manufacturer Micron, category SSD); the
  default HTML-only real fetcher refuses the SAME recorded bytes
  (`PageFetchError` / bounded FETCH_FAILED); the default production wiring
  end-to-end (`page_fetcher=None`) sends `Accept: application/json` for the
  catalog, persists ESTABLISHED, and issues exactly ONE paid search.
- BLOCKER 2 — alias query semantics: `build_alias_expanded_search_query`
  now emits the FROZEN OR shape `("REQUESTED" OR "ALIAS1" OR "ALIAS2")
  description` (group alone without a description), requested MPN first,
  aliases in deterministic relation order, exactly ONE
  `SearchProvider.search()` call, `build_search_query` unchanged. Exact
  canonical strings (description `Micron 7500 3.84TB datacenter SSD`):

  ```
  BASE:  ("MTFDKCC3T8TGP-1BK1DABYY" OR "MTFDKCC3T8TGP-1BK1DABYYR" OR "MTFDKCC3T8TGP-1BK1DABYYT") Micron 7500 3.84TB datacenter SSD
  BASER: ("MTFDKCC3T8TGP-1BK1DABYYR" OR "MTFDKCC3T8TGP-1BK1DABYY" OR "MTFDKCC3T8TGP-1BK1DABYYT") Micron 7500 3.84TB datacenter SSD
  BASET: ("MTFDKCC3T8TGP-1BK1DABYYT" OR "MTFDKCC3T8TGP-1BK1DABYY" OR "MTFDKCC3T8TGP-1BK1DABYYR") Micron 7500 3.84TB datacenter SSD
  ```

- BLOCKER 3 — broad exception catch removed: the authority module no
  longer contains `except Exception` (in any form). Expected bounded
  transport failures are the explicit `PageFetchError` (-> FETCH_FAILED) /
  `UnsafeFetchTargetError` (-> SOURCE_REFUSED) classes; a bare
  `Exception("programming defect")` and a `RuntimeError` propagate to the
  catastrophic boundary. Dependency-contract defects (non-callable
  `fetch`; non-`FetchedPage` / contract-invalid return) propagate
  `TypeError` and are never given a bounded authority status.
- HTTP_PAGE opener-OSError change (14981e3): KEPT and now separately
  regression-tested as a transport-classification fix (`_build_opener`
  OSError -> bounded `PageFetchError`; non-OSError programming errors
  still propagate). It does not, and is not claimed to, solve the Micron
  JSON reachability issue (that is BLOCKER 1).

Production files changed (FU1): `providers/http_page.py` (additive
media-type capability, defaults unchanged), `execution/orchestration.py`
(default JSON authority fetcher wiring, additive),
`execution/micron_alias_authority.py` (broad catch removed; dependency
contract defects propagate), `execution/search_query.py` (OR query shape in
`build_alias_expanded_search_query`; `build_search_query` byte-identical).

Independent review of the pushed FU1 commit (ChatGPT, acting as project
lead / independent architecture reviewer) is complete and approved
PRODUCT-INTEL.4D-D-FU1. PRODUCT-INTEL.4D-D (including 4D-D-FU1) is
APPROVED / FROZEN:

Frozen SHA: 065320180c17b89c7460164326a0c9f49e01fe3b
Frozen collection baseline: 5097 collected
Final acceptance execution: 5097 passed, 0 failed, 0 skipped, 0 xfailed,
0 deselected (+ 39 subtests passed)

**Acceptance evidence (this session, candidate pass — historical; the
final accepted execution at 5097 followed the FU1 correction):**

- Focused 4D-D matrix (7 files): 258 passed.
- Collection: 4766 (frozen 4D-C baseline) + 258 (explicit new focused 4D-D
test nodes) + 1 (new explicit 4D-D model-field inventory test in
`test_research_run_boundaries.py`) + 27 (automatic parameterized expansion
in existing boundary scans: domain +2, providers +4, research identity +8,
runs +4, web +9 — one node per new production file per scanning
parametrize) = **5052** collected. (Correction of an earlier report's
arithmetic: 5052 − 258 = 4794, not 4785; 4794 = 4766 + 28 where the +28 is
the 1 explicit inventory test + 27 automatic expansions above.)
- FINAL full suite (zero deselection, no skip/xfail injection): 5052
collected, 5042 passed (+39 subtests), 10 failed — exactly 10 of the 11
fixed Windows/Python-3.14 subprocess-boundary allowlist nodes, each with
the observed signature `subprocess.Popen -> _winapi.DuplicateHandle ->
OSError: [WinError 6] The handle is invalid`; 0 skipped, 0 xfailed,
0 deselected. The 11th allowlist node
(`tests/domain/test_domain_boundaries.py::test_domain_imports_without_django_network_or_llm_dependencies`)
passed in the final run (non-deterministic by nature).
- `python manage.py check`: System check identified no issues (0 silenced).
- `python manage.py makemigrations --check --dry-run`: No changes detected.
- Frozen 2A/3C/4A/semantic/HUMAN-REVIEW/vendor-commercial/compact-quote
files byte-identical to the parent (mechanically verified).
- Process disclosure: an earlier interrupted 4D-D diagnostic session used
`--deselect` once (530 passed, 7 deselected — diagnostic boundary run only,
no test modified); the final acceptance suite used zero deselection.
- Historical marker: the 5052-collection numbers above record the
  candidate pass (pre-FU1). Final approval/freeze happened only after
  independent review of the pushed FU1 commit — APPROVED / FROZEN at
  SHA 065320180c17b89c7460164326a0c9f49e01fe3b, 5097 collected,
  5097 passed (see the 4D-D-FU1 approval record above).

Semantic qualification is APPROVED AND FROZEN:
- Semantic qualification corpus, prompt v1.1, evaluator mathematics,
  qualification thresholds, expected decisions, and safety gates approved
- Prompt v1.1 FULL SHA256: f50e5584659f953ce73a97ccc8bc1ff487fbeeb37e2e0a72e52210613aeab1ff
- Corpus SHA256: 3c21d6fcd4eefa5cc383792abfd9308bd5c03315834c8ffdffd0f6a2b3619ca1

**Two models passed the formal FULL qualification gates.** They are the
qualified production route:

| Role | Provider | Model |
| --- | --- | --- |
| PRIMARY | `amax` | `nemotron-3-super` |
| FALLBACK | `vllm-262k` | `Qwen3.6-27B-262K` |

Generation settings are fixed at `temperature=0.0`, `max_tokens=32768`.

FU3A — Production Semantic Runtime Contract — **APPROVED / FROZEN**
(corrective history: FU3A2B/C/D/E/F; FU3A2F was the final corrective pass —
ChatGPT's review of the final FU3A2F `runtime.py` and `test_runtime.py`
approved the contract):

FU3B — Semantic execution integration — **APPROVED / FROZEN**
(corrective history: FU3B was the execution-wiring pass; MiniMax M2.7 Thinking
independently reviewed the final FU3B implementation and found no production-code
or safety-contract blocker; ChatGPT performed the final approval/freeze review):
- `product_intelligence/semantic/contract.py` is the single source of truth for
  prompt v1.1, the decision vocabulary, the response schema, and the strict
  parser/validator. The evaluation harness re-exports those same objects;
  production does not depend on `evaluation.semantic.*`.
- `product_intelligence/semantic/transport.py` is the single source of truth
  for the transport implementation (HTTP call, error classification,
  `SemanticModelTransport`/`OpenAISemanticTransport`/`FakeSemanticModelTransport`);
  `evaluation/semantic/transport.py` re-exports it rather than keeping a copy.
- `product_intelligence/semantic/runtime.py` pins the qualified route
  (validation rejects any other provider/model/temperature/max_tokens before a
  transport call — temperature is checked by exact type, `type(x) is float`,
  so `0`/`False` are rejected even though numerically equal to `0.0`), falls
  back on an EXPLICIT allowlist of execution failures, requires exact
  provider-reported model identity, records per-attempt provenance, and never
  converts a programming exception into a fallback.
- The fallback allowlist and error taxonomy are complete over every code the
  canonical transport can return (`INVALID_PROVIDER_RESPONSE` is fallback
  eligible like `MALFORMED_JSON`/`SCHEMA_INVALID`; `CASE_REJECTED` is a known,
  non-fallback-eligible code — neither is lost into `UNKNOWN_ERROR`).
- `SemanticRuntimeResult` fully self-validates: every typed field is checked
  by exact type (not merely truthy-equal), and a failure's `error_type` is
  mechanically bound to what its attempts actually recorded.
- Importing `product_intelligence.semantic` pulls in no evaluation module, no
  Django, and no network client. The live transport is resolved lazily.

**The frozen semantic runtime is wired into execution** behind the semantic integration boundary for explicitly eligible candidates. The frozen runtime exists
and is tested offline; it is called from the research pipeline through `evaluate_semantic_matches` — that
wiring was FU3B, now implemented and approved.

AI_ASSISTED_MATCH remains outside existing 4A aggregation.

A semantic MATCH is represented by:
    original ListingIdentityAssessment.decision == REJECTED
    +
    AiAssistedMatchResult.disposition == AI_ASSISTED_MATCH

There is no AI_ASSISTED_MATCH ListingIdentityAssessment.

Existing 4A sees the original deterministic REJECTED assessment and
excludes it as IDENTITY_NOT_ACCEPTED.

Only EvidenceDecision.ACCEPTED automatically enters 4A Machine Price.

## Project facts (already delivered outside repo)

- FoxPro launcher: **Manually integrated outside this repository — delivered,
  not pending.** The client code is maintained in the existing Visual FoxPro
  sales-order application. The server-side GET prefill contract is implemented
  and localhost UAT passed.
- 4C-B-FU corrective: Exact structural duplicate ListingObservation
  deduplication implemented in `execution/orchestration._deduplicate_exact_observations`.

## FU3B — Semantic execution integration

**APPROVED / FROZEN**

FU3B wires the frozen FU3A semantic runtime into real research execution:

- Deterministic matching remains first authority; deterministic `ACCEPTED` bypasses semantic
- Explicit `MPN_MISMATCH` bypasses semantic
- Semantic eligible:
  - `NO_EXPLICIT_MPN_EVIDENCE + TITLE_TEXT`
  - `NO_EXPLICIT_MPN_EVIDENCE + SKU_FIELD`
  - `PARTIAL_MPN_ONLY`
- Not semantic-enabled in FU3B:
  - `NO_EXPLICIT_MPN_EVIDENCE + NONE`
  - description-only / `UNDECIDED`
- Bounded semantic failure leaves run usable
- Programming/config exceptions propagate to existing catastrophic boundary
- AI-assisted matches retained in `ExecutionResult.ai_assisted_matches`
- `ai_assisted_match_count` is derived
- `AiAssistedMatchResult` mechanically binds provenance
- `SEMANTIC` execution evidence uses bounded controlled detail codes
- Migration 0005 is choices-only metadata
- `AI_ASSISTED_MATCH` remains entirely outside 4A
- `PriceIntelligenceSnapshot` remains deterministic-only

## Phase ownership

| Phase | Description | Status |
| --- | --- | --- |
| PILOT-RELEASE-1 | Internal pilot deployment | **DEPLOYED / ACCEPTED** |
| PILOT-RELEASE-2 | 4D Customer Requirement Deployment & UAT | **DEPLOYED / ACCEPTED** (deployed runtime SHA 065320180c17b89c7460164326a0c9f49e01fe3b; production smoke passed 2026-09-23; migrations through 0010 deployed) |
| PILOT-RELEASE-2-PROD-FIX1 | Production quote-workflow defect corrections (Vendor real-response contract, currency formatting, semantic-section placement, Confirm Match -> Compact Quote, submit guard, ECB/TLS non-bypass) | **IMPLEMENTED / REVIEW BLOCKERS CORRECTED BY FU1 / PENDING FINAL REVIEW** (no deployment in this commit) |
| PILOT-RELEASE-2-PROD-FIX1-FU1 | Bounded review-blocker closure (vendor hybrid production-wire fidelity + section-scanner consistency, human-confirmed authority ownership at the replay boundary, ECB evidence correction, Reviewed Price wording accuracy) | **IMPLEMENTED / FINAL REVIEW BLOCKER CORRECTED BY FU2 / PENDING FINAL REVIEW** (no deployment in this commit; canonical spec PLAN §26.11) |
| PILOT-RELEASE-2-PROD-FIX1-FU2 | Final review-blocker closure (public/denied historical replay binds to the run's own persisted PriceIntelligenceSnapshot; caller-supplied price results removed as an authority input) | **IMPLEMENTED / PENDING FINAL REVIEW** (no deployment in this commit; canonical spec PLAN §26.12) |
| PILOT-RELEASE-2-PROD-FIX1-FU3 | Bounded production defect closure (vendor section scanner: exact observed `<p>` paragraph-prefix envelope — narrow literal, NOT a generic HTML parser) | **IMPLEMENTED / PENDING FINAL REVIEW** (no deployment in this commit; canonical spec PLAN §26.13) |
| 8A-PRE | Caching & Freshness Architecture Audit | **PLANNED** (next delivery; READ-ONLY / DESIGN-FIRST, not caching implementation) |
| 4D-PRE | Preferred Source Feasibility Audit | Implemented (evidence only, frozen) |
| 4D-A | Source Acquisition Optimization | Implemented (frozen) |
| 4D-B | Internal Vendor Commercial Evidence | **Implemented (approved / frozen)** |
| 4D-C-A | ECB FX + Compact Quote Projection Foundation | **IMPLEMENTED / APPROVED / FROZEN** |
| 4D-C-SEC | Vendor Commercial Price Access Gate | **IMPLEMENTED / APPROVED / FROZEN** |
| 4D-C | Compact Quote Summary (browser rendering) | **IMPLEMENTED / APPROVED / FROZEN** |
| 4D-D | Micron Packaging Alias Retrieval (incl. 4D-D-FU1) | **Implemented (approved / frozen)**; PRE1 + PRE2 frozen; frozen SHA 065320180c17b89c7460164326a0c9f49e01fe3b; frozen baseline 5097 collected |
| 4C-A | Execution ownership/lifecycle/evidence primitives | Implemented (frozen) |
| 4C-B | Backend research execution | Implemented (frozen) |
| 4C-B-FU | Exact duplicate deduplication | Implemented (frozen) |
| 4C-C | Web execution/retry integration | Implemented (frozen) |
| 5A | Structured external API | Planned (not implemented; non-blocking for the current FoxPro/browser workflow) |
| 5B | FoxPro launcher | Server-side implemented; client integrated outside repo, UAT passed |
| PILOT-UX | Pilot UX polish + semantic qualification | **FROZEN** |
| HUMAN-REVIEW | Human review for AI-assisted semantic matches | Implemented (frozen)
| 6A | Product Specification Framework | Implemented (frozen)
| 6B | Enterprise SSD Category Schema | Implemented (approved / re-frozen)
| 6C | Specification Evidence Extraction & Resolution | Implemented (frozen)
| 6D | Authoritative Datasheet Specification Enrichment | Implemented (approved / frozen)
| 7A | Comparable-Product Candidate Discovery | Implemented (frozen)
| 7B | Enterprise SSD Similarity Scoring | Implemented (approved / frozen)
| 7C | Comparable-Product Presentation | **IMPLEMENTED / APPROVED / FROZEN** — 7C-PRE1 FROZEN; 7C-PRE2 FROZEN; 7C-A FROZEN; 7C-B FROZEN; 7C-C FROZEN
| SAP | SAP launcher integration | Future |


## Implementation snapshot

| Component | Package | Status |
| --- | --- | --- |
| Domain contracts + vocabularies | `domain/` | Implemented |
| Evaluation corpus + loader | `evaluation/` | Implemented |
| Semantic match corpus + evaluator | `evaluation/semantic/` | **Implemented (frozen)** |
| Semantic match prompt template v1.1 | `evaluation/semantic/prompt.py` | **Implemented (frozen)** |
| Semantic match export/import | `evaluation/semantic/` | **Implemented** |
| Semantic match transport | `evaluation/semantic/transport.py` | **Implemented** |
| Semantic match model catalog | `evaluation/semantic/model_catalog.py` | **Implemented** |
| Semantic match benchmark runner | `evaluation/semantic/runner.py` | **Implemented** |
| Semantic match CLI | `evaluation/semantic/cli.py` | **Implemented** |
| Semantic match comparison | `evaluation/semantic/comparison.py` | **Implemented** |
| Semantic match tests | `tests/evaluation/semantic/` | **Implemented (frozen)** |
| Semantic neutral contract (canonical) | `semantic/contract.py` | **Implemented (frozen, FU3A)** |
| Semantic neutral transport (canonical) | `semantic/transport.py` | **Implemented (frozen, FU3A)** |
| Semantic production runtime | `semantic/runtime.py` | **Implemented (frozen, FU3A)** |
| Semantic runtime tests | `tests/semantic/test_runtime.py` | **Implemented** |
| Semantic transport tests | `tests/semantic/test_transport.py` | **Implemented** |
| Semantic runtime boundaries | `tests/semantic/test_runtime_boundaries.py` | **Implemented** |
| Semantic contract sharing proof | `tests/semantic/test_contract_sharing.py` | **Implemented** |
| Semantic execution integration | `execution/semantic_integration.py` | **Implemented (frozen, FU3B)** |
| EvidenceDecision.AI_ASSISTED_MATCH | `domain/enums.py` | **Reserved (frozen semantic identity disposition, FU3A)** |
| Persisted run lifecycle | `runs/` | Implemented (ResearchRun) |
| Execution evidence model | `runs/` | Implemented (ExecutionEvidenceRecord) |
| Execution claim service | `runs/` | Implemented (claim_execution) |
| Execution completion service | `runs/` | Implemented (complete_execution) |
| Retry service | `runs/` | Implemented (retry_run) |
| Price intelligence snapshot | `runs/` | Implemented (PriceIntelligenceSnapshot) |
| Standalone web shell | `web/` | Implemented |
| Part-number comparison | `research/identity` | Implemented |
| Search provider boundary | `providers/search.py` | Implemented |
| Serper adapter | `providers/serper.py` | Implemented |
| Page fetch + extraction | `providers/http_page.py` + `research/listings.py` | Implemented |
| Listing normalization | `research/normalization.py` | Implemented |
| MPN matching + rejection | `research/matching.py` | Implemented |
| Price aggregation (frozen) | `research/aggregation.py` | **Implemented (frozen)** |
| Versioned codec | `research/price_result_codec.py` | Implemented |
| Price report presentation | `web/presentation.py` | Implemented |
| Research orchestration | `execution/` | **Implemented (frozen)** |
| Web execution wiring | `web/` | **Implemented (frozen)** |
| Structured API | — | 5A (not implemented) |
| FoxPro launcher | — | Server-side implemented; client integrated outside repo, UAT passed |
| SAP launcher | — | Future |
| Human review candidate model | `runs/` (AiAssistedReviewCandidate) | **Implemented (frozen, HUMAN-REVIEW)**
| Human review service | `runs/ai_assisted_review.py` | **Implemented (frozen, HUMAN-REVIEW)**
| Reviewed price aggregation | `research/aggregation.py` (aggregate_reviewed_listing_prices) | **Implemented (frozen, HUMAN-REVIEW)**
| Human review web view + URLs | `web/views.py` + `web/urls.py` | **Implemented (frozen, HUMAN-REVIEW)**
| Human review candidate presentation | `web/presentation.py` | **Implemented (frozen, HUMAN-REVIEW)**
| Product Specification Framework (6A) | `research/specifications.py` | **Implemented (frozen)**
| Enterprise SSD Category Schema (6B) | `research/enterprise_ssd.py` | **Implemented (approved / re-frozen)**
| Enterprise SSD Specification Extraction (6C) | `research/enterprise_ssd_extraction.py` | **Implemented (frozen)**
| Specification Evidence Execution (6C) | `execution/specification_evidence.py` | **Implemented (frozen)**
| Comparable-Candidate Contracts (7A) | `research/comparable_candidates.py` | **Implemented (frozen)**
| Enterprise SSD Candidate Extraction (7A) | `research/enterprise_ssd_candidate_extraction.py` | **Implemented (frozen)**
| Comparable Discovery Execution (7A) | `execution/comparable_discovery.py` | **Implemented (frozen)**
| Enterprise SSD Similarity Scoring (7B) | `research/enterprise_ssd_similarity.py` | **Implemented (approved / frozen)**
| Comparable Similarity Execution (7B) | `execution/comparable_similarity.py` | **Implemented (approved / frozen)**
| Comparable Research Results + Codec (7C-A) | `research/comparable_research_results.py` + `research/comparable_result_codec.py` | **Implemented (frozen)**
| Comparable Research Orchestration (7C-B) | `execution/comparable_orchestration.py` | **Implemented (frozen)**
| Comparable Web Trigger & Presentation (7C-C) | `web/views.py` + `web/comparable_presentation.py` | **Implemented (frozen)**
| Document Provider Boundary (6D) | `providers/document.py` | **Implemented (approved / frozen)**
| HTTP PDF Fetcher (6D) | `providers/http_pdf.py` | **Implemented (approved / frozen)**
| Datasheet Table Interpretation (6D) | `research/enterprise_ssd_datasheet.py` | **Implemented (approved / frozen)**
| Specification Enrichment Execution (6D) | `execution/specification_enrichment.py` | **Implemented (approved / frozen)**
| Commercial Source Boundary (4D-B) | `providers/commercial.py` | **Implemented (approved / frozen)** |
| Internal Vendor Adapter (4D-B) | `providers/internal_vendor.py` | **Implemented (approved / frozen)** |
| Supplemental Snapshot Model (4D-B) | `runs/models.py` (ResearchSupplementSnapshot) | **Implemented (approved / frozen)** |
| Supplemental Codec (4D-B) | `research/commercial_supplement_codec.py` | **Implemented (approved / frozen)** |
| ECB FX Provider (4D-C-A) | `providers/fx.py` | **Implemented (approved / frozen)** |
| FX Snapshot Model (4D-C-A) | `runs/models.py` (ResearchFxSnapshot) | **Implemented (approved / frozen)** |
| FX Codec (4D-C-A) | `research/fx_codec.py` | **Implemented (approved / frozen)** |
| FX Mathematics (4D-C-A) | `research/fx_math.py` | **Implemented (approved / frozen)** |
| Compact Quote Projection (4D-C-A) | `research/compact_quote.py` | **Implemented (approved / frozen)** |
| Commercial Price Access Gate (4D-C-SEC) | `web/commercial_access.py` | **Implemented (approved / frozen)** |
| Compact Quote Public Replay (4D-C) | `execution/compact_quote_public_replay.py` | **Implemented (approved / frozen)** |
| Compact Quote Browser Presentation (4D-C) | `web/compact_quote_presentation.py` | **Implemented (approved / frozen)** |
| Micron 7500 Packaging Alias Contracts (4D-D) | `research/micron_packaging_alias.py` | **Implemented (approved / frozen)** |
| Micron Alias Snapshot Codec (4D-D) | `research/micron_alias_codec.py` | **Implemented (approved / frozen)** |
| Micron Alias Authority Acquisition (4D-D) | `execution/micron_alias_authority.py` | **Implemented (approved / frozen)** |
| Alias Snapshot Model (4D-D) | `runs/models.py` (ResearchMicronAliasSnapshot) + migration 0010 | **Implemented (approved / frozen)** |
| Alias Browser Presentation (4D-D) | `web/micron_alias_presentation.py` | **Implemented (approved / frozen)** |

## Research orchestration

Base 4C orchestration contract: **frozen**
FU3B semantic execution extension: **APPROVED / FROZEN**

Implementation snapshot:

- Research orchestration: Base 4C frozen; FU3B semantic extension frozen
- Semantic execution integration: Implemented / APPROVED / FROZEN

## Web layer architecture

The web layer may import only the public execution API and the approved read-side research symbols:

```
web  ->  product_intelligence.execution  (execute_research_run, ExecutionError,
         ComparableResearchExecutionError, execute_comparable_research_with_default_providers)
web  ->  product_intelligence.runs  (ClaimExecutionFailed, retry_run, ResearchRun,
         confirm_candidate, reject_candidate, undo_review, review errors,
         trigger_comparable_research, ComparableResearchTriggerError,
         ComparableResearchClaimError)
web  ->  product_intelligence.research.price_result_codec
         (PriceResultCodecError, decode_price_aggregation_result)
web  ->  product_intelligence.research.aggregation
         (PriceAggregationResult, aggregate_reviewed_listing_prices)
web  ->  product_intelligence.research.matching
         (ListingIdentityAssessment, is_human_review_eligible_assessment)
web  ->  product_intelligence.research.comparable_result_codec
         (ComparableResultCodecError, decode_comparable_result)          # 7C-C
web  ->  product_intelligence.research.comparable_research_results
         (ComparableResultKind, AuthorityAttemptResult, ComparableCandidateResult,
          ComparableResearchResult, DatasheetAttemptResult,
          EvidenceSourceReference, FieldAssessmentResult, ProductEnrichmentAudit)  # 7C-C
web  ->  product_intelligence.research.enterprise_ssd
         (ENTERPRISE_SSD_SCHEMA)                                          # 7C-C
web  ->  product_intelligence.runs.models
         (ResearchRun, PriceIntelligenceSnapshot, AiAssistedReviewCandidate,
          ComparableResearchExecution, ComparableResearchState)            # 7C-C
```

**Narrow 7C-C read-side exception:**

The general prohibition on `product_intelligence.research.identity` remains.
However, the ONE narrow exception is:

```
views.py  ->  product_intelligence.research.identity  (compare_part_numbers)
```

This is allowed **solely** for persisted comparable-result / parent binding
validation in `views._validate_comparable_result_parent_binding()`. It is
the frozen 2A part-number comparison primitive used read-side only.
`comparable_presentation.py` (pure display) must NOT import this symbol.

The web layer MUST NOT import:
- `product_intelligence.execution.orchestration` (or any execution submodule)
- `product_intelligence.execution` (bare module import)
- `product_intelligence.providers` (or any provider submodule)
- `product_intelligence.runs.execution_claims` (internal)
- `product_intelligence.research.identity` (research decision primitive,
  except the ONE narrow views.py exception documented above)
- Any unapproved symbol from approved research modules

Web writes review state through the runs-owned review service
(`runs/ai_assisted_review.py`). Web may perform approved read-side
composition and binding validation as enforced by boundary tests.
Web must not bypass providers, must not own execution internals,
and must not carry research semantics.

`comparable_presentation.py` is DISPLAY-ONLY: it reuses the authoritative
URL safety helper from `presentation._is_safe_href_url` (no duplication),
imports only research contracts/schema for presentation, and contains no
runs, execution, providers, Django ORM, or research decision primitives.

## FoxPro ownership

FoxPro source code is NOT maintained in this repository. This repository
owns only the launcher-facing HTTP intake contract:

```
GET /research/new?mpn=<encoded>&description=<encoded>
```

The project lead maintains the FoxPro client code manually in the existing
Visual FoxPro sales-order application.

## Human Review authority model

HUMAN-REVIEW is IMPLEMENTED / APPROVED / FROZEN.

Required authority layers:

1. Deterministic identity
   ListingIdentityAssessment.decision == ACCEPTED
   remains the only automatic existing-4A identity authority.

2. Semantic match
   original ListingIdentityAssessment.decision == REJECTED
   +
   AiAssistedMatchResult.disposition == AI_ASSISTED_MATCH

   Snapshot assessment itself is never AI_ASSISTED_MATCH.

3. Human review overlay
   run-scoped AiAssistedReviewCandidate
   states:
       UNREVIEWED
       CONFIRMED
       REJECTED
   actions:
       Confirm
       Reject
       Undo

   Human confirmation never mutates snapshot assessment.

4. Machine Price
   deterministic ACCEPTED only.

5. Reviewed Price
   deterministic ACCEPTED
   +
   human-CONFIRMED semantic-eligible listings.

   Preserve origin:
       DETERMINISTIC
       HUMAN_CONFIRMED

6. Human confirmation changes identity authority only.
   Existing deterministic non-identity price eligibility remains:
       Decimal price
       comparable currency
       known condition

7. Candidate binding fails closed:
   exact run/snapshot assessment + provenance must match before mutation.

8. Candidate creation is run-scoped and participates in final publication.

9. No reviewer identity/authentication/audit identity was introduced.


## Eligibility boundary

Eligible original deterministic assessments ONLY:

    REJECTED
    + NO_EXPLICIT_MPN_EVIDENCE
    + TITLE_TEXT

    REJECTED
    + NO_EXPLICIT_MPN_EVIDENCE
    + SKU_FIELD

    REJECTED
    + PARTIAL_MPN_ONLY

Not eligible:

    ACCEPTED
    UNDECIDED
    MPN_MISMATCH
    NO_EXPLICIT_MPN_EVIDENCE + NONE
    any other non-semantic-eligible state


## Validation results

### PROD-FIX1-FU4 CANDIDATE ACCEPTANCE SNAPSHOT (PENDING FINAL REVIEW)

| Metric | Count |
| --- | --- |
| Collected | 5347 |
| Passed | 5336 |
| Failed | 11 (exactly the fixed allowlist; non-deterministic) |
| Unexpected failures | 0 |
| Skipped | 0 |
| Xfailed | 0 |
| Deselected | 0 |
| Subtests passed | 39 |

Full-suite execution of the final FU4 tree (zero deselection, no
skip/xfail injection; JUnit report): 5347 tests + 39 subtests
executed; 5336 passed, 11 failed — the 11 failures are EXACTLY the
members of the fixed eleven-node Windows/Python 3.14 subprocess-boundary
flake allowlist (every one failed in this run), each with the recorded
signature `subprocess.run -> Popen -> _winapi.DuplicateHandle ->
OSError: [WinError 6] The handle is invalid` (2) / `[WinError 50] The
request is not supported` (9), and NO node outside that allowlist
failed. The allowlist is non-deterministic by nature, exactly as
recorded for every prior phase; the fixed allowlist remains exactly
11 nodes (not expanded).

Collection accounting: 5326 FU3 baseline + 21 FU4 net-new nodes
= 5347 collected. Net-new: tests/providers/test_vendor_section_
response.py +15 (TestParagraphEntityDecoding: exact `&quot;` /
`&nbsp;` / `&cr;` decoding on the paragraph path, plain-form non-
decoding, adversarial unapproved named/numeric/case-variant entity
non-decoding with fail-closed parsing, faithful production-shaped full
adapter mapping; TestSynnexAvailabilityTotalString: `"0"` -> OOS/0,
positive digit string -> IN_STOCK/qty, int/Decimal readings unchanged,
string grammar rejections, over-bounded length, flat-form scope, global
`_safe_int` still rejects strings), tests/execution/test_4d_b_vendor_
section_integration.py +6 (TestVendorParagraphEntitySectionIntegration:
full execute_research_run on the encoded fixture, persisted-snapshot
sensitive-metadata + entity-spelling absence, Machine Price
immutability, armed zero-live Compact Quote replay rows, execution-time
4D-C FX currency discovery EUR + USD with persisted ResearchFxSnapshot,
supplemental-only vendor authority). No boundary parameterization
expansion (no new production files; only existing files modified).

All 5326 FU3 baseline nodes remain collected. No existing test
deleted, renamed, skipped, xfailed, deselected, or weakened. Exact
disclosed test-file touches (safety contracts preserved):

* `tests/providers/test_vendor_section_response.py` — module docstring
  notes the FU4 observed entity encoding and Synnex availability wire
  type; NEW fixture `SECTION_BODY_PARAGRAPH_ENTITY` (production-shaped
  encoded wire; fake sentinels only; deterministic synthetic values);
  NEW class `TestParagraphEntityDecoding` (7 nodes); NEW class
  `TestSynnexAvailabilityTotalString` (8 nodes); `_safe_int` added to
  the test-only private import list. No existing node altered.
* `tests/execution/test_4d_b_vendor_section_integration.py` — module
  docstring notes the FU4 encoded-wire proofs; NEW fixture
  `SECTION_BODY_PARAGRAPH_ENTITY` (same synthetic payload as
  `SECTION_BODY_PARAGRAPH` with the observed entity encoding plus the
  production-observed Synnex numeric-string price and digit-string
  availability); NEW class `TestVendorParagraphEntitySectionIntegration`
  (6 nodes). No existing node altered.

`python manage.py check`: System check identified no issues
(0 silenced). `python manage.py makemigrations --check --dry-run`:
No changes detected.

### PROD-FIX1-FU3 CANDIDATE ACCEPTANCE SNAPSHOT (PENDING FINAL REVIEW)

| Metric | Count |
| --- | --- |
| Collected | 5326 |
| Passed | 5324 |
| Failed | 2 (exactly fixed-allowlist members; non-deterministic) |
| Unexpected failures | 0 |
| Skipped | 0 |
| Xfailed | 0 |
| Deselected | 0 |
| Subtests passed | 39 |

Definitive full-suite execution of the final FU3 tree (zero
deselection, no skip/xfail injection; JUnit report): 5326 tests +
39 subtests executed; 5324 passed, 2 failed — both failures are
members of the fixed eleven-node Windows/Python 3.14
subprocess-boundary flake allowlist, each with the recorded signature
`subprocess.Popen -> OSError: [WinError 6] The handle is invalid`
(verified per-failure from the JUnit report), and NO node outside that
allowlist failed. An earlier full execution of the same tree in this
session observed 11 failures — again EXACTLY members of the fixed
allowlist (every one of the 11 nodes failed once in that run), all
other nodes green. The allowlist is non-deterministic by nature, exactly
as recorded for every prior phase; the fixed allowlist remains exactly
11 nodes (not expanded).

The 2 failed nodes in the definitive execution (both
fixed-allowlist members):

1. `tests/domain/test_domain_boundaries.py::test_domain_imports_without_django_network_or_llm_dependencies`
2. `tests/evaluation/test_evaluation_boundaries.py::test_loading_the_corpus_imports_no_framework_or_provider`

Collection accounting: 5298 FU2 baseline + 28 FU3 net-new nodes
= 5326 collected. Net-new: tests/providers/test_vendor_section_
response.py +22 (TestParagraphEnvelope: exact `<p>` label recognition
per source, leading-whitespace tolerance, the full adversarial HTML
boundary set, trailing `</p>` interstitial proof, malformed-in-literal
fail-closed, duplicate-label policy, mixed plain/paragraph forms,
oversized paragraph body), tests/execution/test_4d_b_vendor_section_
integration.py +6 (TestVendorParagraphSectionIntegration: full
execute_research_run paragraph integration, persisted-snapshot
sensitive-metadata absence, Machine Price immutability, armed zero-
live Compact Quote replay rows, execution-time 4D-C FX currency
discovery EUR + USD with persisted ResearchFxSnapshot, supplemental-
only vendor authority). No boundary parameterization expansion (no new
production files; only existing files modified).

All 5298 FU2 baseline nodes remain collected. No existing test
deleted, renamed, skipped, xfailed, deselected, or weakened. Exact
disclosed test-file touches (safety contracts preserved):

* `tests/providers/test_vendor_section_response.py` — module docstring
  notes the FU3 observed paragraph envelope; NEW class
  `TestParagraphEnvelope` (22 nodes) + NEW faithful single-line-per-
  section paragraph fixture `SECTION_BODY_HYBRID_PARAGRAPH` (fake
  sentinels only). No existing node altered.
* `tests/execution/test_4d_b_vendor_section_integration.py` — module
  docstring notes the FU3 paragraph proofs; NEW fixture
  `SECTION_BODY_PARAGRAPH` (same synthetic source payload as the FU1
  fixture, ONLY the outer `<p>` envelope added), NEW
  `_RecordingFxProvider` (test-only, records requested currency sets),
  NEW class `TestVendorParagraphSectionIntegration` (6 nodes).
  No existing node altered.

`python manage.py check`: System check identified no issues
(0 silenced). `python manage.py makemigrations --check --dry-run`:
No changes detected.

### PROD-FIX1-FU2 CANDIDATE ACCEPTANCE SNAPSHOT (PENDING FINAL REVIEW)

| Metric | Count |
| --- | --- |
| Collected | 5298 |
| Passed | 5296 |
| Failed | 2 (exactly the fixed allowlist; non-deterministic) |
| Unexpected failures | 0 |
| Skipped | 0 |
| Xfailed | 0 |
| Deselected | 0 |
| Subtests passed | 39 |

Definitive full-suite execution of the final FU2 tree (zero
deselection, no skip/xfail injection): 5296 passed, 2 failed — both
failures are members of the fixed eleven-node Windows/Python 3.14
subprocess-boundary flake allowlist, each with the recorded signature
`subprocess.Popen -> _winapi.DuplicateHandle/CreateProcess ->
OSError: [WinError 6/50]` (verified per-failure from the JUnit
report), and NO node outside that allowlist failed. Three earlier
full executions of the same tree in this session observed 11, 2, and
1 failures respectively — in every case EXACTLY members of the fixed
allowlist, all other nodes green. The allowlist is non-deterministic
by nature, exactly as recorded for every prior phase; the fixed
allowlist remains exactly 11 nodes (not expanded).

The 2 failed nodes in the definitive execution (both
fixed-allowlist members):

1. `tests/domain/test_domain_boundaries.py::test_domain_imports_without_django_network_or_llm_dependencies`
2. `tests/evaluation/test_evaluation_boundaries.py::test_loading_the_corpus_imports_no_framework_or_provider`

The full fixed allowlist (all observed failures across the session's
four full executions were subset members of this list, never outside
it):

1. `tests/domain/test_domain_boundaries.py::test_domain_imports_without_django_network_or_llm_dependencies`
2. `tests/evaluation/test_evaluation_boundaries.py::test_loading_the_corpus_imports_no_framework_or_provider`
3. `tests/providers/test_provider_boundaries.py::test_importing_the_provider_boundary_pulls_in_no_third_party_dependency`
4. `tests/providers/test_provider_boundaries.py::test_importing_the_page_boundary_pulls_in_no_third_party_dependency`
5. `tests/providers/test_provider_boundaries.py::test_http_pdf_imports_no_third_party_dependency`
6. `tests/research/test_enterprise_ssd_boundaries.py::test_importing_enterprise_ssd_pulls_in_no_third_party`
7. `tests/research/test_enterprise_ssd_boundaries.py::test_importing_enterprise_ssd_does_not_load_django`
8. `tests/research/test_listing_normalization_boundaries.py::test_importing_the_research_core_still_pulls_in_no_third_party_dependency`
9. `tests/research/test_research_identity_boundaries.py::test_importing_the_research_core_pulls_in_no_third_party_dependency`
10. `tests/research/test_specification_boundaries.py::test_importing_specifications_pulls_in_no_third_party_dependency`
11. `tests/runs/test_research_run_boundaries.py::test_the_domain_still_imports_without_django_present`

All 11 are boundary/import-guard tests that spawn a subprocess to
prove isolated imports; the failure occurs at
`subprocess.Popen -> _winapi.DuplicateHandle` before any project code
runs. No FU2 production or test file is imported by any of them.

Collection accounting: 5281 FU1 baseline + 17 FU2 net-new nodes
= 5298 collected. Net-new: tests/execution/test_public_replay_persisted_
authority.py +15 (NEW FILE: same-request cross-run 1890/999 borrow
premise, per-run persisted-evidence isolation, no-caller-price-result
signature proof, corrupt/missing snapshot fail-closed, denied-boundary
preservation, authorized-replay-unchanged + Machine Price
byte-identity), tests/execution/test_compact_quote_public_replay.py
+2 (missing-snapshot and malformed-price-payload fail-closed). No
boundary parameterization expansion (no new production files; only
existing files modified).

All 5281 FU1 baseline nodes remain collected. No existing test
deleted, renamed, skipped, xfailed, deselected, or weakened. Exact
disclosed test-file touches (safety contracts preserved):

* `tests/execution/test_public_replay_persisted_authority.py` — NEW
  FILE (15 nodes) proving the FU2 blocker regression.
* `tests/execution/test_compact_quote_public_replay.py` — call sites
  updated to the FU2 signature (the persisted snapshot is now
  established as the run's artifact; the replay receives only the
  run). `test_provenance_mismatch_is_refused` now proves the same
  contract against a request-provenance-CORRUPT PERSISTED snapshot
  (stronger: the corruption lives in the artifact, not in a supplied
  object). `test_duck_typed_price_result_is_refused` now proves the
  stronger contract that NO parameter accepts any caller-supplied
  price result (signature + TypeError + persisted-snapshot-only
  authority). `test_wrong_run_type_is_programming_error` updated to
  the FU2 signature. Two new fail-closed nodes added (missing
  snapshot, malformed price payload). The module-boundary AST test's
  runs.models allowlist gains exactly `PriceIntelligenceSnapshot`
  (the intentional persisted-authority read); all other guards
  unchanged. No node renamed, deleted, or weakened.
* `tests/execution/test_human_confirmed_replay_authority.py` — three
  call sites drop the removed `price_result=` keyword argument
  (UNREVIEWED public replay, CONFIRMED public replay, armed
  zero-live public replay); every assertion preserved byte-for-byte
  (same expected rows / prices / zero-live behavior). No node renamed
  or deleted.
* `tests/web/test_compact_quote_report.py`, `tests/web/
  test_web_boundaries.py`, and all other web/execution tests —
  UNCHANGED (view-level denied-branch tests already persist the run's
  PriceIntelligenceSnapshot; the authorized branch is untouched).

`python manage.py check`: System check identified no issues
(0 silenced). `python manage.py makemigrations --check --dry-run`:
No changes detected.

### PROD-FIX1-FU1 CANDIDATE ACCEPTANCE SNAPSHOT (PENDING FINAL REVIEW)

| Metric | Count |
| --- | --- |
| Collected | 5281 |
| Passed | 5281 |
| Failed | 0 |
| Skipped | 0 |
| Xfailed | 0 |
| Deselected | 0 |
| Subtests passed | 39 |

Definitive full-suite execution of the final FU1 tree (zero
deselection, no skip/xfail injection): 5281 passed, 0 failed,
39 subtests passed. During validation, two earlier full executions
of the same tree observed 10 and 11 failures respectively — in both
cases EXACTLY members of the fixed eleven-node Windows/Python 3.14
subprocess-boundary flake allowlist (observed signature
`subprocess.Popen -> _winapi.DuplicateHandle/CreateProcess ->
OSError: [WinError 6/50]`), with NO node outside that allowlist
failing and all three executions otherwise green. The allowlist is
non-deterministic by nature, exactly as recorded for every prior
phase; the fixed allowlist remains exactly 11 nodes (not expanded).

Collection accounting: 5247 PROD-FIX1 baseline + 34 FU1 net-new nodes
= 5281 collected. Net-new: tests/providers/test_vendor_section_response.py
+15 (12 hybrid production-placement adapter tests incl. the full
adapter-level unknown-label/interstitial-between-known-sections proof;
3 section-value interstitial/strictness parser tests),
tests/execution/test_human_confirmed_replay_authority.py +17 (NEW FILE:
replay/service boundary authority proofs A–G plus injection-surface
removal and Machine Price / no-persisted-price proofs),
tests/web/test_human_confirmed_compact_quote.py +2 (focused Reviewed
Price wording regressions). No boundary parameterization expansion (no
new production files; only existing files modified).

All 5247 baseline nodes remain collected. No existing test deleted,
skipped, xfailed, deselected, or weakened. Exact disclosed test-file
touches:

* `tests/providers/test_vendor_section_response.py` — module docstring
  and fixture comments corrected (flat forms described as separately
  tested COMPATIBILITY forms, not the only/exact production wire
  shape); `test_trailing_garbage_rejected` INPUT corrected from
  `{'a': 1} trailing junk` (a complete literal + interstitial text, now
  correctly ignored per the documented contract) to
  `{'a': 1 trailing junk` (an INCOMPLETE literal — still rejected;
  name and fail-closed intent preserved, strictness retained);
  new hybrid/interstitial tests added.
* `tests/execution/test_4d_b_vendor_section_integration.py` — the
  SECTION_BODY fixture corrected from the simplified flat
  "production-equivalent" shape to the faithful hybrid production shape
  (Ingram: nested pricing + top-level boolean availability + top-level
  Avl_Quantity + unrelated ignored fields; Synnex EU: REAL nested
  OnlineCheck form with fake/redacted SessionId / BuyerAccountId /
  SystemId in the Header block). All seven assertions of the seven
  existing tests are preserved and now run against the faithful shape.
* `tests/web/test_web_boundaries.py` — the web research-import
  allowlist gains exactly one symbol:
  `research.matching.is_review_candidate_binding_valid` (the single
  shared binding primitive now consumed by web/presentation.py).
  Guard strength unchanged (still an explicit symbol-level allowlist).
* `tests/providers/test_fx_tls_verification.py` — docstring-only
  evidence correction (BLOCKER 3): no longer records an outstanding
  CA-trust-store installation as fact (a later secure retry from the
  same production runtime succeeded; the transient root cause is
  unproven). Every assertion byte-identical.
* `tests/web/test_human_confirmed_compact_quote.py` — two focused
  wording regression tests ADDED (no existing test altered).
* `tests/execution/test_human_confirmed_replay_authority.py` — NEW FILE
  (17 nodes).

### PROD-FIX1 CANDIDATE ACCEPTANCE SNAPSHOT (PENDING FINAL REVIEW)

| Metric | Count |
| --- | --- |
| Collected | 5247 |
| Passed | 5247 |
| Failed | 0 |
| Skipped | 0 |
| Xfailed | 0 |
| Deselected | 0 |
| Subtests passed | 39 |

Collection accounting: frozen 4D-D baseline 5097 + 150 new PROD-FIX1
nodes (test_vendor_section_response.py 70, test_compact_quote_human_
confirmed.py 21, test_compact_quote_currency_formatting.py 16,
test_human_confirmed_compact_quote.py 15, test_research_submit_guard.py
10, test_fx_tls_verification.py 9, test_4d_b_vendor_section_integration.
py 7, test_fx_tls_production_chain.py 2). No boundary parameterization
expansion (no new production files; only existing files modified). No
existing test deleted, renamed, skipped, xfailed, deselected, or
weakened.

### 4D-D FINAL ACCEPTANCE SNAPSHOT (IMPLEMENTED / APPROVED / FROZEN)

| Metric | Count |
| --- | --- |
| Collected | 5097 |
| Passed | 5097 |
| Failed | 0 |
| Skipped | 0 |
| Xfailed | 0 |
| Deselected | 0 |
| Subtests passed | 39 |

Frozen SHA: 065320180c17b89c7460164326a0c9f49e01fe3b. With this
acceptance, PRODUCT-INTEL.4D (all components) is closed as
IMPLEMENTED / APPROVED / FROZEN / COMPLETE. The 5052-collection
candidate-pass evidence recorded in the 4D-D section above is preserved
as history.

### HISTORICAL FU3A2F FREEZE SNAPSHOT

| Metric | Count |
| --- | --- |
| Collected | 2158 |
| Passed | 2151 |
| Failed | 7 |
| (+ 39 subtests) | — |

### HISTORICAL FU3B FINAL REVIEW SNAPSHOT

| Metric | Count |
| --- | --- |
| Collected | 2212 |
| Passed | 2206 |
| Failed | 6 |

The six failures were exactly:

- `tests/evaluation/test_evaluation_boundaries.py::test_loading_the_corpus_imports_no_framework_or_provider`
- `tests/providers/test_provider_boundaries.py::test_importing_the_provider_boundary_pulls_in_no_third_party_dependency`
- `tests/providers/test_provider_boundaries.py::test_importing_the_page_boundary_pulls_in_no_third_party_dependency`
- `tests/research/test_listing_normalization_boundaries.py::test_importing_the_research_core_still_pulls_in_no_third_party_dependency`
- `tests/research/test_research_identity_boundaries.py::test_importing_the_research_core_pulls_in_no_third_party_dependency`
- `tests/runs/test_research_run_boundaries.py::test_the_domain_still_imports_without_django_present`

### 6B IMPLEMENTATION SNAPSHOT (APPROVED / RE-FROZEN)

| Metric | Count |
| --- | --- |
| Collected | 2782 |
| Passed | 2772 |
| Failed | 10 |
| Unexpected failures | 0 |

Evidence-backed corrective change (project-lead approved, re-frozen):
- Real Seagate Nytro 5050 manufacturer evidence demonstrated "2.5in"
  as an exact formatting equivalent of the existing 2.5-inch canonical form.
- Added: "2.5in" -> "2.5-inch" to _FORM_FACTOR_MAP.
- No schema version bump (field meaning, canonical value, enum unchanged).
- Regression test added: test_2_5_in_no_space.

The ten failures are the fixed approved Windows / Python 3.14
subprocess-boundary flake allowlist (all boundary/import-guard tests):

1. `tests/domain/test_domain_boundaries.py::test_domain_imports_without_django_network_or_llm_dependencies`
2. `tests/evaluation/test_evaluation_boundaries.py::test_loading_the_corpus_imports_no_framework_or_provider`
3. `tests/providers/test_provider_boundaries.py::test_importing_the_provider_boundary_pulls_in_no_third_party_dependency`
4. `tests/providers/test_provider_boundaries.py::test_importing_the_page_boundary_pulls_in_no_third_party_dependency`
5. `tests/research/test_enterprise_ssd_boundaries.py::test_importing_enterprise_ssd_pulls_in_no_third_party`
6. `tests/research/test_enterprise_ssd_boundaries.py::test_importing_enterprise_ssd_does_not_load_django`
7. `tests/research/test_listing_normalization_boundaries.py::test_importing_the_research_core_still_pulls_in_no_third_party_dependency`
8. `tests/research/test_research_identity_boundaries.py::test_importing_the_research_core_pulls_in_no_third_party_dependency`
9. `tests/research/test_specification_boundaries.py::test_importing_specifications_pulls_in_no_third_party_dependency`
10. `tests/runs/test_research_run_boundaries.py::test_the_domain_still_imports_without_django_present`

Observed failure signature (all 10 nodes):

    subprocess.Popen
    -> _winapi.DuplicateHandle
    -> OSError: [WinError 6] The handle is invalid

    or

    subprocess.Popen
    -> _winapi.CreateProcess
    -> OSError: [WinError 50] The request is not supported

These are environment-specific subprocess-boundary limitations on this Windows /
Python 3.14 workstation, not application defects. No node outside the fixed
ten-node allowlist fails. No test is skipped, xfailed, or weakened.

### 7A IMPLEMENTATION SNAPSHOT (APPROVED / FROZEN)

| Metric | Count |
| --- | --- |
| Collected | 3006 |
| Passed | 2996 |
| Failed | 10 (fixed approved allowlist only, non-deterministic) |
| Unexpected failures | 0 |

The ten failures are the fixed approved Windows / Python 3.14
subprocess-boundary flake allowlist (identical to 6C baseline).

7A implementation (contract-corrected pass):
- New production modules:
  - `research/comparable_candidates.py` (candidate contracts)
  - `research/enterprise_ssd_candidate_extraction.py` (pure extraction)
  - `execution/comparable_discovery.py` (execution + result audit)
- New test modules:
  - `tests/research/test_enterprise_ssd_candidate_extraction.py` (21 tests)
  - `tests/research/test_comparable_candidates.py` (38 tests)
  - `tests/execution/test_comparable_discovery.py` (27 tests)
- Total new tests: 86 (+ 16 boundary test nodes for new production files)
- Collection delta: 2904 -> 3006 (+102)
- Real Seagate fixture: 81 observations, 1 TARGET_SELF, 80 candidates
- No frozen file modifications
- No pre-7A test deletions
- Research boundary clean (no provider imports in research/)

Contract corrections applied in review-closure pass:
- Raw MPN (`manufacturer_part_number_raw`) preserved verbatim (not stripped)
- Raw title (`product_name_raw`) preserved verbatim (not stripped/blank-to-None)
- Bounded JS string decoder (no `.encode().decode("unicode_escape")` corruption)
- `ComparableCandidateAssessment` stores `target_identity: ProductIdentity` by exact type (`type(x) is ProductIdentity` — subclasses rejected)
- `__post_init__` re-derives disposition from target + observation
- `ComparableCandidate` requires all evidence to bind to the exact same `target_identity` object (cross-target evidence rejected)
- `deduplicate_candidate_assessments` rejects same-key assessments from different target identities
- `ComparableCandidateDiscoveryResult` enforces exact `assessment.observation is obs`
- `ComparableCandidateDiscoveryResult` enforces exact `assessment.target_identity is result.target_identity`
- `ComparableCandidateDiscoveryResult` enforces AUTHORITATIVE-only result invariant
- `ComparableCandidateDiscoveryResult` rejects foreign assessments in candidate evidence
- Real E2E crosses frozen 6C -> 7A (not synthetic all-UNKNOWN spec set)
- All bare-pass tests replaced with real adversarial coverage
- No skip/xfail/deselect/bare-pass in any 7A test

### 7B IMPLEMENTATION SNAPSHOT (IMPLEMENTED / APPROVED / FROZEN)

**Frozen 7A baseline:** 3006 collected.

| Metric | Count |
| --- | --- |
| Total collected | 3102 |
| Passed | 3092 |
| Failed | 10 (fixed approved allowlist only, non-deterministic) |
| Unexpected failures | 0 |
| Skipped | 0 |
| Xfailed | 0 |
| Deselected | 0 |

The ten failures are the fixed approved Windows / Python 3.14
subprocess-boundary flake allowlist (all boundary/import-guard tests).

**Collection accounting:**

| Component | Nodes |
| --- | --- |
| Frozen 7A baseline | 3006 |
| 7B research tests (`test_enterprise_ssd_similarity.py`) | 54 |
| 7B execution tests (`test_comparable_similarity.py`) | 34 |
| Boundary guard nodes | 8 |
| **Total** | **3102** |

7B implementation:
- New production modules:
  - `research/enterprise_ssd_similarity.py` (pure similarity scoring)
  - `execution/comparable_similarity.py` (execution + batch result)
- New test modules:
  - `tests/research/test_enterprise_ssd_similarity.py` (54 tests)
  - `tests/execution/test_comparable_similarity.py` (34 tests)
- Total new 7B tests: 88
- Collection delta: 3006 -> 3102 (+96)
- One modified test: `tests/research/test_listing_normalization_boundaries.py`
  (Decimal allowlist addition for new module)
- Real Seagate fixture: 81 observations -> 80 candidates -> 80 similarities
- Real Seagate vertical slice: frozen 6C -> frozen 7A -> 7B
- Known sibling XP15360SE70015 scored: 1 scoreable field (Form Factor)
- All 80 candidates have evidence_coverage = 1/12
- Real Form Factor exact match: field_similarity = 1
- Fetch count: 1 (one fetch per source, not 80)
- No frozen file modifications
- No pre-7B test deletions
- Research boundary clean (no provider imports in research/)
- 7B boundary: no SearchProvider, no LLM, no title parsing, no Interface splitting

Contract corrections (7B corrective implementation):
- SpecificationSimilarityFieldAssessment recomputes actual field similarity
  from raw resolutions; rejects wrong-but-in-range supplied score
- EnterpriseSsdSimilarityResult moved from research to execution layer
- Exact ComparableCandidateDiscoveryResult type enforced (no duck typing,
  TypeError BEFORE any fetch)
- Source outcomes retained in result (not discarded)
- 7B ComparableSimilaritySourceOutcome uses exact 7A ComparableCandidateSource
  descriptor object (not flattened source_name/source_url/source_authority)
- final_url structurally validated by require_fetchable_url()
- Candidate spec provenance audit: every observation traced to a FETCHED
  7B source outcome (product_identity, source_name, source_authority,
  source_url==final_url, retrieved_at all verified)
- ComparableCandidateSpecificationProfile enforces exact bridge output
  (rejects enriched identity with injected metadata)
- Exact scalar types enforced (bool/int/float substitutes rejected)
- Non-authoritative bridge test uses TEST-ONLY object.__setattr__ tampering
- 7A source binding: EnterpriseSsdSimilarityResult.__post_init__ derives
  canonical EXTRACTED source descriptors from the frozen 7A result and
  enforces exact object identity for every 7B source outcome. Copied/
  value-equal substitutes are rejected. Missing or extra outcomes rejected.

Key design decisions:
- VERIFIED-only scoring (UNKNOWN/UNVERIFIED/CONFLICT are NOT mismatches)
- 12-field equal weight (no domain-business weights in 7B v1)
- DECIMAL: min(target, candidate) / max(target, candidate)
- TEXT/ENUM/BOOLEAN: exact canonical equality (1 or 0)
- evidence_coverage = scored_field_count / 12
- observed_similarity = mean of scored field similarities
- evidence_weighted_similarity = sum of scored similarities / 12
- Self-validating EnterpriseSsdCandidateSimilarity (re-derives all fields,
  exact scalar types)
- Self-validating EnterpriseSsdSimilarityResult (execution-owned, exact
  discovery_result type, retained source outcomes, 7A source binding,
  provenance audit)
- Field score self-validation (SpecificationSimilarityFieldAssessment
  recomputes and rejects wrong supplied score)
- Candidate ProductIdentity bridge: EXACT, no manufacturer guessed,
  rejects non-AUTHORITATIVE evidence
- One-fetch-per-source execution (document held, extraction per identity)
- 7B source descriptor identity binding (exact 7A ComparableCandidateSource
  object reused in 7B outcome, enforced at result construction)
- No duck typing for ComparableCandidateDiscoveryResult
- No provenance string mutation (no .strip() on source_name/source_url)
- PageFetcher remains a structural protocol check (hasattr(page_fetcher, "fetch"));
  this is a protocol verification, not discovery-result authority

Evidence sparsity conclusion:
- Current candidate specification evidence is too sparse for useful
  differentiation (only 1 of 12 fields scoreable per candidate)
- This is a limitation of frozen 6C extraction capability (only
  "Form Factor" label mapped), not a 7B failure
- Candidate specification enrichment required before useful 7C presentation

No skip/xfail/deselect/bare-pass in any 7B test


### 6C IMPLEMENTATION SNAPSHOT (APPROVED / FROZEN)

| Metric | Count |
| --- | --- |
| Collected | 2904 |
| Passed | 2894 |
| Failed | 10 (fixed approved allowlist only, non-deterministic) |
| Unexpected failures | 0 |

The ten failures are the fixed approved Windows / Python 3.14
subprocess-boundary flake allowlist (identical to 6B baseline).

Corrective pass (final evidence-backed closure):
- Speculative extraction mechanisms removed:
  - JSON-LD Product additionalProperty/PropertyValue pairs (no real evidence)
  - HTML specification tables (no real evidence)
  - HTML definition lists (dt/dd pairs) (no real evidence)
- Embedded JavaScript JSON product data extraction implemented:
  - Structural anchor: var supportSpecsData = JSON.parse('...') (exact variable name)
  - Real evidence: Seagate Nytro 5050 support page (XP15360SE70005)
  - Array of 81 product records with skuNumber + features[]
  - Exact MPN match selection, no cross-record leak
  - Label mapping: "Form Factor" -> physical_form_factor (only proven label)
- Provenance trace: multiplicity-aware (each EXTRACTED outcome contributes
  capacity equal to observation_count)
- Raw value exact preservation (extractor does not strip/clean)
- final_url validated through require_fetchable_url contract
- Duplicate requested_url removed from SpecificationSourceOutcome
  (requested URL is always source.source_url)
- Real Seagate fixture: VERIFIED (raw "2.5in" -> canonical "2.5-inch" -> VERIFIED)
- Samsung PM9A3: still NO_OBSERVATIONS (spec table JS-rendered)
- No LLM implemented
- No persistence/web

## Next delivery priority

**8A-PRE**: PLANNED — Caching & Freshness Architecture Audit (next
delivery priority). READ-ONLY / DESIGN-FIRST: investigate and record a
caching and freshness architecture before any caching implementation.
NOT authorization to implement caching; no actual TTL values are
approved in the PILOT-RELEASE-2 documentation closure. Chosen because
Product Intelligence is now in production and evidence classes have
materially different freshness requirements: the design must prevent
stale evidence from being presented as current while avoiding
unnecessary paid/live calls. The future 8A design must distinguish at
minimum: market/public prices (short freshness); Vendor commercial
observations (short freshness); ECB FX rates (tied to persisted
official observation date); product specifications (longer
freshness); comparable research (medium freshness); deterministic
identity/authority evidence (not automatically equivalent to
market-price freshness); user/operator forced refresh; historical
reports (immutable replay, NEVER refreshed merely by GET).

**PILOT-RELEASE-2**: DEPLOYED / ACCEPTED — 4D Customer Requirement
Deployment & UAT. The already-frozen 4D customer requirements are
deployed to the internal production/pilot Windows server; the recorded
representative 4D production smoke validation covered a normal customer
quote flow exercising current Price Intelligence / Compact Quote
behavior and Micron 7500 R/T packaging-alias behavior. The previously
planned broader UAT matrix (direct-source acquisition using a viable
preferred-source case; normal Serper fallback; real Vendor API
commercial evidence; compact quote rendering; non-USD vendor evidence +
persisted ECB USD equivalent; Micron 7500 packaging-alias BASE/R/T
behavior; a non-eligible MPN proving alias abstention; Visual FoxPro
launcher -> browser prefill against the deployed server; historical
report reload causing zero new Search/Vendor/ECB/Micron/Semantic live
work; vendor-price access behavior under the existing frozen network
gate (4D-C-SEC REMOTE_ADDR / PI_VENDOR_PRICE_ALLOWED_CIDRS, unchanged))
remains a validation reference; the production records do not claim
that every matrix case was separately executed and evidenced during
the 2026-09-23 cutover.
Deployment record: deployed runtime SHA
065320180c17b89c7460164326a0c9f49e01fe3b (the independently reviewed
and frozen PRODUCT-INTEL.4D-D-FU1 runtime SHA; deployment is
Git-managed and exact-approved-SHA based); production smoke test
passed 2026-09-23; 4D is deployed; migrations through
0010_research_micron_alias_snapshot are deployed (4D migrations
0008 / 0009 / 0010). Production environment details are recorded in
the operational Confluence references and are not duplicated here.
Runtime-vs-docs: the later commits c6ad6ae and 7ff0ab7 are docs-only
project-state closures; production does not need to move merely to
obtain those documentation edits; 7ff0ab7 is not the production
runtime SHA. Authentication: the current pilot server
has restricted access and people who can reach this internal server are
currently considered authorized for this pilot; full application
authentication, login/session identity, OAuth, and per-user authorization
are NOT part of PILOT-RELEASE-2 and remain deferred future
production-hardening concerns (8C); report UUID is not access control; no
session-based authorization is introduced.

**PILOT-RELEASE-1**: DEPLOYED / ACCEPTED

**4D-PRE**: APPROVED / FROZEN (evidence only) — Preferred Source
         Feasibility Audit;
         audit 12 customer preferred sites;
         record per-site: direct lookup mechanism, static HTML capability,
         JS requirements, blocking behavior, MPN/price/currency evidence;
         recommendation: DIRECT / SERPER_FALLBACK / UNSUITABLE;
         no production code changes;
         evidence recorded in docs/PILOT_SOURCE_FEASIBILITY.md

**4D**: IMPLEMENTED / APPROVED / FROZEN / COMPLETE — Customer Quote
       Research Expansion;
       4D-PRE (feasibility audit) -> 4D-A (source optimization) ->
       4D-B (vendor commercial evidence) -> 4D-C (compact quote + FX) ->
       4D-D (Micron packaging alias, APPROVED / FROZEN including
       4D-D-FU1, frozen SHA 065320180c17b89c7460164326a0c9f49e01fe3b,
       frozen baseline 5097 collected, final acceptance 5097 passed /
       0 failed, v1 scope Micron 7500 SSD only);
       no frozen phase reopened; no frozen boundary weakened;
       4D-B triggered the §19 security gate, resolved by the frozen
       4D-C-SEC REMOTE_ADDR-only network gate;
       full application authentication remains a deferred 8C
       production-hardening concern; the current restricted internal
       pilot deployment assumes reachability = authorized for this pilot

**HUMAN-REVIEW**: IMPLEMENTED / APPROVED / FROZEN

**5A**: PLANNED / NOT IMPLEMENTED / non-blocking (not needed for the
current FoxPro/browser workflow; not the next delivery)

**5B**: Server-side implemented; client integrated outside repo; localhost UAT passed

**6A**: IMPLEMENTED / APPROVED / FROZEN —
         Product Specification Framework (framework only, no extraction)
         Corrective pass: evidence-derived constructor enforcement,
         deep immutability (MappingProxyType), schema/definition key
         consistency.

**6B**: IMPLEMENTED / APPROVED / RE-FROZEN —
         First Category-Specific Specification Schema;
         Enterprise SSD finalized; 12-field schema v1;
         strict deterministic normalization with exact-definition identity
         enforcement, strict thousands-grouping grammar, explicit IOPS unit;
         evidence-backed correction: "2.5in" -> "2.5-inch" (re-frozen);
         no extraction; no resolution; no authority inference

**6C**: IMPLEMENTED / APPROVED / FROZEN —
         Specification Evidence Extraction & Resolution;
         explicit approved-source descriptors (source_url validated at construction);
         existing PageFetcher acquisition (protocol imported, not duplicated);
         deterministic structured extraction (var supportSpecsData = JSON.parse('...'));
         structural assignment binding (only the JSON.parse directly assigned
         to supportSpecsData is extracted);
         source authority supplied explicitly, never hostname-inferred;
         frozen 6B normalization (with evidence-backed "2.5in" correction);
         frozen 6A resolution;
         complete ProductSpecificationSet with explicit UNKNOWN;
         source outcomes preserve complete source descriptor + self-consistency;
         requested_url removed (always source.source_url);
         provenance trace enforcement (multiplicity-aware);
         final_url validation through require_fetchable_url;
         raw value exact preservation (no stripping by extractor);
         no LLM implemented;
         no persistence/web;
         real manufacturer fixture: Seagate Nytro 5050 (XP15360SE70005)
         - embedded JSON data extraction works (1 observation);
         - Form Factor raw value "2.5in" extracted correctly;
         - frozen 6B normalization: "2.5in" -> "2.5-inch" -> VERIFIED;
         Samsung PM9A3: still NO_OBSERVATIONS (JS-rendered spec table);
         7A follows 6C

**7A**: IMPLEMENTED / APPROVED / FROZEN —
        Comparable-Product Candidate Discovery;
        evidence-backed candidate discovery from approved manufacturer catalog sources;
        explicit AUTHORITATIVE source required (SECONDARY rejected);
        no SearchProvider, no LLM, no spec filtering, no scoring/ranking;
        var supportSpecsData = JSON.parse('...') is first real mechanism;
        raw candidate evidence preserved (ComparableCandidateObservation);
        target-self exclusion uses frozen 2A compare_part_numbers();
        normalized-exact candidate dedup uses frozen 2A normalize_part_number();
        ProductIdentity NOT reused for discovered candidates;
        self-auditing ComparableCandidateDiscoveryResult;
        real Seagate vertical slice: 81 records -> 81 observations -> 1 TARGET_SELF -> 80 candidates;
        no persistence/web;

**7B**: IMPLEMENTED / APPROVED / FROZEN —
        Enterprise SSD Similarity Scoring;
        deterministic field-level similarity evidence;
        VERIFIED-only scoring (UNKNOWN/UNVERIFIED/CONFLICT never mismatch);
        candidate ProductIdentity bridge (EXACT, no manufacturer guess);
        12-field equal-weight (no business weights);
        DECIMAL min/max ratio, TEXT/ENUM/BOOLEAN exact equality;
        evidence_coverage = scored/12, evidence_weighted = sum/12;
        one-fetch-per-source execution (not one-fetch-per-candidate);
        frozen 6C extraction reuse per candidate identity;
        real Seagate fixture: 80 candidates, 1 scoreable field each (Form Factor);
        evidence too sparse for useful differentiation (candidate spec enrichment needed);
        6D completed the candidate-specification enrichment identified after the
7B freeze. 7C is IMPLEMENTED / APPROVED / FROZEN. 4D is
IMPLEMENTED / APPROVED / FROZEN / COMPLETE; PILOT-RELEASE-2 is
DEPLOYED / ACCEPTED; 8A-PRE is the next delivery.

**7C-A**: COMPARABLE RESEARCH RESULTS + CODEC — IMPLEMENTED / APPROVED / FROZEN

**7C-B**: COMPARABLE RESEARCH ORCHESTRATION — IMPLEMENTED / APPROVED / FROZEN
        Frozen primitives composed into one bounded execution pipeline:
        claim ComparableResearchExecution
            -> exact parent ResearchRun request
            -> PRE1 authority acquisition
            -> target frozen 6C specification extraction
            -> frozen 7A candidate discovery
            -> candidate ProductIdentity bridge (frozen 7B)
            -> candidate 6C from HELD authoritative support documents
            -> ONE frozen 6D batch enrichment (target + candidates)
            -> frozen 6C + 6D composition
            -> pure frozen 7B similarity scoring
            -> pure ComparableResearchResult projection
            -> frozen V1 comparable codec
            -> atomic ComparableResearchExecution completion
        Exact bounded failure handling (PRE1 incomplete, codec errors,
        programming exceptions); no web/presentation routes; zero
        modifications to frozen contracts;
        real Seagate fixture vertical slice: 80 candidates, 7 scoreable
        fields per candidate (Form Factor + 6 Datasheet fields),
        evidence layers SUPPORT_PAGE/DATASHEET_PDF classified by
        object-identity pools, codec V1 round-trip verified;

**7C-C**: COMPARABLE WEB TRIGGER & PRESENTATION — IMPLEMENTED / APPROVED / FROZEN
        Web trigger route POST /research/<uuid>/comparables (research-comparables);
        default-provider adapter execute_comparable_research_with_default_providers();
        pure presentation module comparable_presentation.py (DISPLAY ONLY);
        comparable section AFTER existing review content in template;
        child selection: active (PENDING/RUNNING) > COMPLETED > FAILED (deterministic);
        result decode via frozen V1 codec + parent binding via frozen 2A comparison
        (binding validation in views._validate_comparable_result_parent_binding(),
        NOT in display-only comparable_presentation);
        candidate order exactly preserved (no ranking/sorting); ALL retained;
        Decimal values string-exact; labels/units from ENTERPRISE_SSD_SCHEMA;
        UNVERIFIED values visibly marked "Unverified — <value>";
        VERIFIED/CONFLICT/UNKNOWN resolution states branch correctly;
        complete AuthorityAttemptDisplay provenance (policy_id, outcome,
        requested_source_url, fetched_final_url, retrieved_at, matching_mpn);
        complete DatasheetAttemptDisplay provenance (outcome, source_name,
        source_url, final_url, retrieved_at, observation_count);
        complete EvidenceSourceReference provenance (source_name, source_url,
        evidence_layer, source_authority, retrieved_at);
        URL safety: reuses authoritative presentation._is_safe_href_url
        (no duplication in comparable_presentation);
        unsafe URLs: escaped text with no href;
        GET research_detail read-only: no trigger/executor/provider calls;
        CSRF: POST enforced with Django CSRF middleware;
        boundary tests updated for new research/execution/runs imports;
        boundary: comparable_presentation imports no runs/execution/providers/Django;
        views.py may import only compare_part_numbers (narrow 7C-C exception);
        new test count: 38 (7 runtime + 29 presentation + 39 report + 6 boundary = 81
        total test nodes in FU scope; 38 net new after accounting for strengthened
        existing nodes and removed duplicates);
        collection delta: 3812 -> 3850 (+38);

**6D**: IMPLEMENTED / APPROVED / FROZEN —
        Authoritative Datasheet Specification Enrichment;
        added AFTER 7B freeze because frozen 7B revealed only 1/12
        candidate evidence coverage;
        provider-neutral document/PDF boundary;
        concrete HttpPdfFetcher (stdlib urllib, bounded, no browser);
        pure research table interpretation (no PDF parser dependency);
        MPN -> table -> column -> row binding;
        six-field allowlist: capacity, sequential_read, sequential_write,
        random_read_iops, random_write_iops, endurance_dwpd;
        unit incorporation from structural row header when cell lacks unit;
        frozen 6B normalization (no modification required);
        frozen 6A resolution (VERIFIED for AUTHORITATIVE evidence);
        complete ProductSpecificationSet with explicit UNKNOWN;
        self-auditing SpecificationEnrichmentResult;
        one-fetch-per-datasheet deduplication;
        compose_6c_6d_specifications: merges 6C + 6D normalized evidence,
        re-resolves via frozen 6A (does NOT copy resolved values);
        physical_form_factor preserved VERIFIED from frozen 6C;
        candidate composition: scored_field_count=7, evidence_coverage=7/12;
        runtime dependency: pdfplumber>=0.11.0 (execution layer only);
        pdfplumber for PDF table extraction (execution layer only);
        real Seagate PDF fixture: Nytro 5550/5350 datasheet (8 pages);
        no LLM, no semantic model, no title parsing, no Interface splitting

### 6D IMPLEMENTATION SNAPSHOT (IMPLEMENTED / APPROVED / FROZEN)

**Frozen 7B baseline:** 3102 collected.

Total collected | 3353
Passed          | 3352
Failed          | 1
Unexpected failures | 0
Skipped         | 0
Xfailed         | 0
Deselected      | 0
Subtests passed | 39
Warnings        | 2

The single observed failure was:
tests/evaluation/test_evaluation_boundaries.py::test_loading_the_corpus_imports_no_framework_or_provider

It is a member of the fixed approved 11-node Windows/Python 3.14
subprocess-boundary flake allowlist. No node outside that allowlist failed.

**Allowlist expansion evidence (node 11):**
- `tests/providers/test_provider_boundaries.py::test_http_pdf_imports_no_third_party_dependency`
- Exact pytest failure: `subprocess.Popen -> _winapi.DuplicateHandle -> OSError: [WinError 6] The handle is invalid`
- Direct CMD semantic check: `[]` (stdlib urllib only, no third-party dependency)
- Project-lead approval: accepted as the 11th fixed environment-flake node

**Collection accounting (6D corrective closure):**

| Component | Nodes |
| --- | --- |
| Frozen 7B baseline | 3102 |
| 6D datasheet link extractor tests (`test_datasheet_link_extractor.py`) | 19 |
| 6D provider document tests (`test_document_provider.py`) | 29 |
| 6D HTTP PDF tests (`test_http_pdf.py`) | 20 |
| 6D research datasheet tests (`test_enterprise_ssd_datasheet.py`) | 70 |
| 6D execution enrichment tests (`test_specification_enrichment.py`) | 68 |
| 6D boundary guard tests (`test_specification_enrichment_boundaries.py`) | 17 |
| 6D provider boundary additions (`test_provider_boundaries.py`) | 4 |
| Boundary guard nodes from existing tests (parameterization expansion) | 24 |
| **Total** | **3353** |

Collection delta: 3102 -> 3353 (+251)

**Parameterization expansion derivation (24 nodes from existing tests):**

All 24 boundary guard nodes from existing tests are derived from actual parameterized
test expansion when new 6D production modules are added to directory-scanned sets:

- `test_provider_boundaries.py`:
  - 5 parametrize × GENERIC_BOUNDARY_MODULES: +1 each (document.py added) = +5
  - 1 parametrize × _python_files(PROVIDERS_ROOT): +2 (document.py, http_pdf.py) = +2
  - 1 parametrize × INNER_ROOTS: +2 (enterprise_ssd_datasheet.py, datasheet_link_extractor.py in research/) = +2
  - 1 parametrize × ADAPTER_MODULES: +1 (http_pdf.py) = +1
  Subtotal: +10

- `test_research_identity_boundaries.py`:
  - 4 parametrize × _python_files(RESEARCH_ROOT): +2 each = +8
  Subtotal: +8

- `test_research_run_boundaries.py`:
  - 1 parametrize × (_python_files(DOMAIN_ROOT) + _python_files(RESEARCH_ROOT)): +2 = +2
  Subtotal: +2

- `test_web_boundaries.py`:
  - 1 parametrize × INNER_ROOTS: +2 = +2
  Subtotal: +2

- `test_domain_boundaries.py`:
  - 1 parametrize × (_python_files(DOMAIN_ROOT) + _python_files(RESEARCH_ROOT)): +2 = +2
  Subtotal: +2

Grand total parameterization expansion: 10 + 8 + 2 + 2 + 2 = 24

6D production modules:
- `product_intelligence/providers/document.py` (provider-neutral boundary)
- `product_intelligence/providers/http_pdf.py` (concrete PDF fetcher)
- `product_intelligence/research/datasheet_link_extractor.py` (support-record datasheet-link extraction)
- `product_intelligence/research/enterprise_ssd_datasheet.py` (pure table interpretation)
- `product_intelligence/execution/specification_enrichment.py` (execution + result + composition + authority chain + batch)

6D test modules:
- `tests/research/test_datasheet_link_extractor.py` (19 tests) — real fixture
- `tests/providers/test_document_provider.py` (29 tests)
- `tests/providers/test_http_pdf.py` (20 tests)
- `tests/research/test_enterprise_ssd_datasheet.py` (70 tests)
- `tests/execution/test_specification_enrichment.py` (68 tests)
- `tests/research/test_specification_enrichment_boundaries.py` (17 tests)

**Corrective changes applied (6D review-closure pass):**
- Authority chain: `derive_datasheet_source()` derives datasheet URLs from
  frozen 7A EXTRACTED AUTHORITATIVE source via supportSpecsData extraction
- Real fixture: test_datasheet_link_extractor uses actual frozen Seagate HTML
  fixture (not synthetic replica)
- Batch execution: `enrich_enterprise_ssd_specifications_batch()` provides
  shared PDF fetch across product identities (1 fetch for 3 identities)
- Parser error taxonomy: only explicit verified exception classes caught
  (pdfplumber.utils.exceptions.PdfminerException, pdfminer.pdfparser.PDFSyntaxError);
  no module-name substring matching; RuntimeError propagates
- Result self-audit: empty-evidence hole closed (ENRICHED + positive count
  + zero raw observations rejected); ambiguous duplicate provenance rejected
- FetchedDocument URL contract: embedded credentials rejected for both
  requested_url and final_url
- Provider boundary guards: document.py (generic) and http_pdf.py (adapter)
  added to test_provider_boundaries.py guard sets
- Real frozen 6C composition: actual frozen 6C extraction from real HTML
  fixture + 6D enrichment from real PDF fixture
- Real frozen 7B vertical slice: full chain 6C + 6D -> 7A -> 7B with
  real Seagate fixtures (XP15360SE70015, XP3840SE70005 candidates)
- Real one-fetch proof: batch primitive proves 1 support page + 1 PDF for
  3 identities sharing one datasheet
- Type correction: `_find_mpn_column_global` return annotation corrected to
  `tuple[int, int, int, int, int] | None` (was missing row_idx)
- Adversarial result tests: 10 real constructor rejection tests using
  tampered frozen objects
- Parser exception monkeypatch tests: 5 tests proving pdfminer exceptions
  -> PARSE_FAILED, RuntimeError -> propagates, MPN ambiguity -> propagates

Real evidence:
- PDF source: Seagate Nytro 5550/5350 Datasheet
- PDF URL: /content/dam/seagate/en/content-fragments/products/datasheets/enterprise-rebranding/nytro-5550-5350-ssd/nytro-5550-5350-ssd-DS2099-4-2410US-en_US.pdf
- PDF SHA256: b449dc488c0a3aa6d28b6e0ac2373a7fc42d7780cc1a437439c823b39833010c
- PDF byte size: 201,997
- Parser: pdfplumber (via pdfminer.six)
- 8 pages, 15 tables across product families
- XP15360SE70005: 6 ENRICHED observations (all VERIFIED)
- XP15360SE70015: 6 ENRICHED observations (same column)
- XP3840SE70005: 6 ENRICHED observations (different column)
- Support-record extraction: exact skuNumber -> exact datasheet path
- All three SKUs share identical datasheet path (real fixture proven)

7B vertical slice evidence:
- Frozen 7A discovery: 81 records -> 80 candidates
- Required candidates found: XP15360SE70015, XP3840SE70005
- 7B bridge establish_candidate_product_identity: EXACT match
- Frozen 6C candidate evidence: physical_form_factor VERIFIED (from supportSpecsData)
- 6D candidate enrichment: 6 VERIFIED observations per candidate (capacity, sequential_read,
  sequential_write, random_read_iops, random_write_iops, endurance_dwpd)
- compose_6c_6d_specifications: merges 6C normalized evidence + 6D normalized evidence,
  re-resolves via frozen 6A (does NOT copy resolved values directly)
- Required candidates post-composition: scored_field_count=7, evidence_coverage=7/12
- XP15360SE70015:
  - scored_field_count = 7
  - evidence_coverage = Decimal(7)/Decimal(12)
  - observed_similarity = Decimal(1)
  - evidence_weighted_similarity = Decimal(7)/Decimal(12)
  - All 7 scored fields: field_similarity = 1 (exact match on all)
  - 5 non-scored fields: BOTH_NOT_VERIFIED
- XP3840SE70005:
  - scored_field_count = 7
  - evidence_coverage = Decimal(7)/Decimal(12)
  - observed_similarity = (Decimal('3.84')/Decimal('15.36') + 5 + Decimal('6900')/Decimal('7200')) / 7
    = Decimal('6.208333333333333333333333333333333333333') / 7
    = Decimal('0.8869047619047619047619047619047619047619')
  - evidence_weighted_similarity = Decimal('6.208333333333333333333333333333333333333') / 12
    = Decimal('0.5173611111111111111111111111111111111111')
  - capacity: SCORED, field_similarity = Decimal('0.25') (3.84 vs 15.36)
  - sequential_write: SCORED, field_similarity = Decimal('0.9583333333333333333333333333') (6900 vs 7200)
  - sequential_read, random_read_iops, random_write_iops, endurance_dwpd: SCORED, field_similarity = 1
  - physical_form_factor: SCORED, field_similarity = 1
  - 5 non-scored fields: BOTH_NOT_VERIFIED
- physical_form_factor remains SCORED for both candidates (preserved from frozen 6C)
- Batch one-fetch: 1 support page + 1 PDF for 3 identities (batch proof)
- Vertical slice test strengthened: asserts exact observed_similarity,
  evidence_weighted_similarity, and per-field field_similarity for both candidates

Strengthened vertical slice test (`test_real_7b_vertical_slice_with_enrichment`):
- Asserts exact scored_field_count = 7 (not >= 1)
- Asserts exact evidence_coverage = Decimal(7)/Decimal(12) (not > 0)
- Asserts exact observed_similarity per candidate
- Asserts exact evidence_weighted_similarity per candidate
- Asserts exact field_similarity for all 12 fields per candidate
- Asserts physical_form_factor SCORED (preserved from 6C)
- Asserts all 6 6D fields SCORED
- Asserts all 5 remaining fields BOTH_NOT_VERIFIED
- All assertions pass against real Seagate fixtures

New runtime dependency (declared in requirements.txt):
- pdfplumber>=0.11.0 (transitively pulls pdfminer.six): pure Python PDF table extraction
- Used in execution layer only; research layer remains parser-free
- Installed versions: pdfplumber 0.11.10, pdfminer.six 20260107
- Import boundary proof:
  - `import product_intelligence.research.enterprise_ssd_datasheet` loads zero third-party packages
  - `import product_intelligence.execution.specification_enrichment` loads pdfplumber + pdfminer.six
    (transitive through Django model imports in execution/__init__.py)
- Both packages explicitly imported in specification_enrichment.py:
  - `import pdfplumber` (open PDFs, extract tables)
  - `from pdfminer.pdfparser import PDFSyntaxError` and `from pdfplumber.utils.exceptions import PdfminerException` (bounded parser exception taxonomy)
- Both pdfplumber and pdfminer.six are explicitly declared runtime
  dependencies. pdfminer.six is also a dependency of pdfplumber, but is
  directly declared because 6D directly relies on its parser exception
  taxonomy.

No frozen file modifications.
No pre-6D test deletions.
No skip/xfail/deselect/bare-pass in any 6D test.

## Semantic qualification harness

**APPROVED / FROZEN**

The semantic qualification corpus, prompt v1.1, evaluator mathematics,
qualification thresholds, expected decisions, and safety gates are APPROVED AND FROZEN.

- Prompt v1.1 SHA256: f50e5584659f953ce73a97ccc8bc1ff487fbeeb37e2e0a72e52210613aeab1ff
- Corpus SHA256: 3c21d6fcd4eefa5cc383792abfd9308bd5c03315834c8ffdffd0f6a2b3619ca1

Do NOT modify:
- evaluation/semantic_corpus/cases.json truth labels or case contents
- SEMANTIC_PROMPT_VERSION = "1.1"
- semantic system/user prompt semantics
- semantic evaluator formulas
- qualification gates
- production research/matching.py
- production aggregation (4A FROZEN)
- production execution authority (frozen 4C/FU3B execution semantics preserved;
  future explicitly approved phases may extend)

Since FU3A2 the frozen prompt text, decision vocabulary, response schema and
strict parser/validator physically live in
`product_intelligence/semantic/contract.py`. `evaluation/semantic/prompt.py`,
`vocabulary.py` and `evaluator.py` re-export those same objects. The freeze
applies to the behaviour wherever it lives; the extraction was proved
behaviour-preserving by the two SHA256 fingerprints above.

## Model qualification runner

**IMPLEMENTED**

Semantic qualification harness infrastructure is implemented:

* transport.py - Abstract transport interface + OpenAI-compatible HTTP
* model_catalog.py - Explicit model catalog (8 primary + 1 smoke + 3 skip)
* runner.py - Benchmark runner with durable artifacts
* cli.py - CLI for list-models, run, evaluate, compare
* comparison.py - Offline comparison utility

All tests use fake transports / recorded responses. No live network calls.

**Two models have passed the formal FULL qualification gates**:
`amax/nemotron-3-super` (primary) and `vllm-262k/Qwen3.6-27B-262K` (fallback).
They are the pinned production route.

## FU3A — Production Semantic Runtime Contract

**APPROVED / FROZEN.** (Corrective history: FU3A2B, FU3A2C, FU3A2D, FU3A2E,
FU3A2F — labels for the corrective path to this freeze, not separate durable
phases. FU3A2F was the final corrective pass; ChatGPT's independent review of
the final FU3A2F `runtime.py` and `test_runtime.py` approved the contract.)

Both `semantic/contract.py` and `EvidenceDecision.AI_ASSISTED_MATCH` are now
frozen as part of this approval.

### Single source of truth

`product_intelligence/semantic/contract.py` is the canonical implementation of:

* Prompt v1.1 (`SEMANTIC_PROMPT_VERSION`, `SYSTEM_PROMPT`,
  `USER_PROMPT_TEMPLATE`, `SemanticPrompt`, `build_prompt`)
* `SemanticDecision`, `ConfidenceLevel`, `SemanticMatchResponse`
* `parse_raw_output`, `validate_response`, `RawOutputParseError`

`evaluation/semantic/prompt.py`, `vocabulary.py` and `evaluator.py` re-export
those objects. Sharing is proved by object identity, not by an import
statement (`tests/semantic/test_contract_sharing.py`). Production does not
import `product_intelligence.evaluation.semantic.*`.

`product_intelligence/semantic/transport.py` is likewise the canonical
transport implementation (HTTP call, error classification, all three
transport classes); `evaluation/semantic/transport.py` re-exports it rather
than keeping a second copy — proved by object identity in
`tests/semantic/test_contract_sharing.py`, same as the contract.

### Import boundary

Importing `product_intelligence.semantic` loads no
`product_intelligence.evaluation.*` module, no Django, and no network client
(`requests`, `urllib`, `urllib3`, `httpx`, `aiohttp`). `evaluation.semantic.transport`
is NOT whitelisted: the live transport is imported lazily inside transport
construction. Enforced by `tests/semantic/test_runtime_boundaries.py`, which
inspects real post-import `sys.modules` state from a clean module state — and
(FU3A2D) also restores each evicted module's *parent-package attribute*, not
only its `sys.modules` entry, so a test that reimports
`product_intelligence.semantic` cannot leave `product_intelligence.semantic`
(attribute access) and `sys.modules["product_intelligence.semantic"]`
pointing at two different objects for the rest of the test session.

### Pinned qualified route

| Setting | Value |
| --- | --- |
| Primary | `amax` / `nemotron-3-super` |
| Fallback | `vllm-262k` / `Qwen3.6-27B-262K` |
| temperature | `0.0` (exact float — `type(x) is float`, so `0`/`False` are rejected) |
| max_tokens | `32768` |

`SemanticRuntimeConfig` keeps these fields for compatibility, but
`validate_runtime_config` rejects any deviation before a transport is built or
called — by exact type where numeric equality alone would be insufficient
(`0`/`False` are numerically `== 0.0` but are not the qualified float). Only
`request_timeout_seconds` is configurable, and an unreadable or non-finite
environment value (`PI_SEMANTIC_REQUEST_TIMEOUT_SECONDS=abc`/`nan`/`inf`) fails
closed rather than silently defaulting.

### Fallback policy

Fallback uses an EXPLICIT allowlist (`PRIMARY_FALLBACK_ELIGIBLE_ERRORS`), never
"anything outside a deny set", so an unrecognised error code cannot silently
buy a second paid model call. Both lookup tables the runtime and
`SemanticRuntimeResult` index (`_PRIMARY_STATUS_TO_ERROR_TYPE`,
`_FALLBACK_STATUS_TO_ERROR_TYPE`) are complete over every non-OK status, and
every code the canonical transport's `ALL_ERROR_TYPES` can return has an
intentional mapping — proved by
`tests/semantic/test_runtime.py::TestEveryCanonicalTransportCodeHasAnIntentionalMapping`.

Eligible: `TIMEOUT`, `DNS_ERROR`, `TLS_ERROR`, `CONNECTION_ERROR`,
`RATE_LIMITED`, `HTTP_ERROR`, `PROVIDER_UNAVAILABLE`, `AUTHENTICATION_FAILED`,
`MODEL_NOT_FOUND`, `EMPTY_RESPONSE`, `MALFORMED_JSON`, `SCHEMA_INVALID`,
`MODEL_IDENTITY_MISMATCH`, `INVALID_RESPONSE` (FU3A2D: a malformed HTTP-200
provider envelope is an execution/output-contract failure of the same kind as
`MALFORMED_JSON`/`SCHEMA_INVALID`, and now buys one fallback attempt the same
way they do).

Not eligible: `INVALID_REQUEST_CONFIGURATION`, `UNSUPPORTED_PARAMETER`,
`PROVIDER_NOT_CONFIGURED`, `CASE_REJECTED` (FU3A2D: a content-policy rejection
of the case's own content — retrying the identical content against a
different model would not help — kept as its own known bounded status,
distinct from `UNKNOWN_ERROR`), an invalid `SemanticRuntimeConfig`, any
genuinely unrecognised error code, and programming exceptions.

A valid primary decision (`MATCH`, `NO_MATCH`, `UNCERTAIN`) is FINAL: exactly
one primary call, zero fallback calls.

### Model identity

Exact provider-reported model identity is mandatory. A primary that reports the
wrong model, or reports no model at all, falls back exactly once. A fallback
that reports the wrong model or no model is a final semantic failure — there is
no third provider.

### Provenance and safety

`SemanticRuntimeResult` carries the requested primary route, a tuple of frozen
`SemanticAttempt` records (provider, model, bounded status, latency), the
fallback flag and reason, and the bounded final error type. On ANY final
failure `actual_provider` and `actual_model` are `None`. No raw response, no
provider body, no exception text, no API key, and no chain-of-thought is
retained. Programming exceptions propagate rather than becoming a fallback.

`SemanticRuntimeResult` is fully self-validating (FU3A2D): every typed field
(`decision`, `confidence`, `error_type`, `fallback_reason`, `fallback_used`,
and the three attribute tuples) is checked by exact type, not merely accepted
and left to fail later inside `to_dict()`. A failure's `error_type` is
mechanically bound to what its attempts actually recorded — a one-attempt
failure's `error_type` must equal `_PRIMARY_STATUS_TO_ERROR_TYPE[first.status]`,
a two-attempt failure's must equal
`_FALLBACK_STATUS_TO_ERROR_TYPE[second.status]` — so a result cannot claim,
say, `PRIMARY_MODEL_NOT_FOUND` for an attempt that actually timed out.

### Relationship to 4A

The original deterministic assessment remains REJECTED.
The parallel AiAssistedMatchResult carries disposition AI_ASSISTED_MATCH.
Existing 4A sees the REJECTED assessment and excludes it as
IDENTITY_NOT_ACCEPTED.


## Known issues / debt

- FU3A Production Semantic Runtime Contract: APPROVED / FROZEN
- FU3B Semantic Execution Integration: APPROVED / FROZEN
- This Windows / Python 3.14 workstation has a fixed eleven-node subprocess-boundary
  flake allowlist. These nodes may fail independently between runs with
  OSError: [WinError 6/50] from subprocess.run(..., capture_output=True).
  No node outside the fixed eleven-node allowlist fails.
  Environment limitation, not a product defect.

**Current fixed Windows/Python 3.14 subprocess-boundary allowlist:**
11 exact nodes.

Node 11 (`tests/providers/test_provider_boundaries.py::test_http_pdf_imports_no_third_party_dependency`)
was qualified and approved during 6D. Historical snapshots retain the failure
counts actually observed at the time they were frozen (10 for 6B/6C/7A/7B).

## AD-059 — Authoritative Datasheet Specification Enrichment (6D)

**Status**: Accepted (6D implementation)

**Why added AFTER 7B**: Frozen 7B revealed that candidate specification
evidence from frozen 6C extraction is too sparse for useful differentiation.
All 80 Seagate candidates had evidence_coverage = 1/12 (only Form Factor).
6D extends specification evidence capability by adding manufacturer PDF
datasheet extraction without reopening frozen 6C extraction semantics.

**Architecture**:
- Provider-neutral document boundary (`providers/document.py`)
- Concrete HTTP PDF fetcher (`providers/http_pdf.py`, stdlib urllib)
- Pure research table interpretation (`research/enterprise_ssd_datasheet.py`)
- Execution enrichment composition (`execution/specification_enrichment.py`)
- pdfplumber for PDF table extraction (execution layer only)
- MPN -> table -> column -> row binding (exact raw equality)
- Unit incorporation from row header when cell lacks unit
- Six-field allowlist: capacity, sequential_read, sequential_write,
  random_read_iops, random_write_iops, endurance_dwpd
- Support-record datasheet-link extraction (`research/datasheet_link_extractor.py`)
- AUTHORITATIVE-only enforcement (SECONDARY rejected)
- Bounded model-row grammar (3 exact forms)
- Bounded spec-row grammar (6 exact regex patterns)
- Whole-PDF MPN uniqueness (global across all tables)
- Raw MPN exactness (no strip before comparison)
- Bounded parser exception handling (pdfminer/pdfplumber only)
- Fully self-auditing result (raw->outcome->normalized->resolution)
- 6C + 6D evidence composition primitive

**Constraints**:
- No LLM, no semantic model
- No title parsing
- No Interface splitting
- No frozen 6B modification
- No frozen 6C modification
- No frozen 7B modification
- Research layer is pure (no PDF parser, no I/O, no network)
- No frozen file modifications (verified)
- No pre-6D test deletions (verified)
- No skip/xfail/deselect/bare-pass in any 6D test (verified)

**Evidence**:
- Real Seagate Nytro 5550/5350 datasheet PDF fixture
- SHA256: b449dc488c0a3aa6d28b6e0ac2373a7fc42d7780cc1a437439c823b39833010c
- 201,997 bytes, 8 pages, 15 tables
- XP15360SE70005: 6 VERIFIED observations
- XP15360SE70015: 6 VERIFIED observations (same column)
- XP3840SE70005: 6 VERIFIED observations (different column)
- Support-record extraction: exact skuNumber -> exact datasheet path
- 6C + 6D composition: physical_form_factor preserved VERIFIED from 6C
- Candidate composition results (both candidates):
  - scored_field_count: 7 (1 from 6C + 6 from 6D)
  - evidence_coverage: 7/12
  - XP15360SE70015: observed_similarity=1 (all 7 fields match target)
  - XP3840SE70005: observed_similarity≈0.887 (capacity, sequential_write differ)

**Runtime dependency**:
- BOTH pdfplumber and pdfminer.six are explicitly declared runtime dependencies.
- pdfplumber for PDF table extraction (execution layer only)
- pdfminer.six for bounded parser exception taxonomy (execution layer only)
- pdfminer.six is also a transitive dependency of pdfplumber, but is directly
  declared for explicit import boundary control
- Research layer remains parser-free

**Test counts (actual collected)**:
| Module | Nodes |
| --- | --- |
| `test_datasheet_link_extractor.py` | 19 |
| `test_document_provider.py` | 29 |
| `test_http_pdf.py` | 20 |
| `test_enterprise_ssd_datasheet.py` | 70 |
| `test_specification_enrichment.py` | 68 |
| `test_specification_enrichment_boundaries.py` | 17 |
| `test_provider_boundaries.py` (6D additions) | 4 |
| **6D total** | **227** |

**Frozen**: PRODUCT-INTEL.6D approved by project lead.
