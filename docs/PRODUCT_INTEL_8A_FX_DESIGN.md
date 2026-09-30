# PRODUCT-INTEL.8A-FX-DESIGN — FX Cache Lookup Identity & Freshness Closure

**Status:** DELIVERED (read-only / design-only). This document resolves the
8A-PRE open item (the 8A-PRE §8 sketch's "one open item": the exact
miss/hit boundary) and proposes the smallest FX-only implementation slice.
It authorizes NO implementation, approves NO TTL values, changes NO
production code, test, model, migration, or frozen contract, and commits
NOTHING.

**Authoritative starting SHA:** `55d1879a03da3dc6163a28c9524b5ef0396b76b3`
**Predecessor:** `docs/PRODUCT_INTEL_8A_PRE_CACHING_FRESHNESS_AUDIT.md`
(8A-PRE, APPROVED / COMPLETE as a design audit only).

**Design basis:** all material conclusions below were re-derived from the
actual production source, tests, and canonical plan at the starting SHA
(cited inline). The 8A-PRE audit was used only as a starting pointer; every
conclusion it carried into this design was re-verified against code.

---

## 0. Executive summary of the resolved problem

8A-PRE proposed an FX cache identity of
`provider_id + observation_date + base_currency + document hash`. That
identity is a valid **STORED CONTENT / PROVENANCE** identity, but it is NOT a
**PRE-FETCH LOOKUP** key: immediately before
`fx_provider.fetch_rates(...)` (orchestration line 1385) the caller does not
know the document's `observation_date` (the XML `time` attribute, parsed only
after the network call — `providers/fx.py::_parse_ecb_xml`) nor any document
hash (the raw body is discarded after parsing; nothing is hashed today).
A cache keyed on those values would require a live fetch before the lookup —
defeating the cache.

The resolution: the pre-fetch lookup key is the **feed identity**
("the latest daily ECB euro reference document"), and content identity
(`observation_date` + canonical content digest) is established **post-fetch**
and used as the store's uniqueness key. Freshness is a separate, bounded
policy: a stored document is reusable only while it carries a live proof from
the current UTC day (the feed's own publication granularity — not a numeric
TTL). The requested currency set is deliberately NOT in the key: the provider
contract already fetches the full document and projects requested currencies
after parsing, so the full daily document is stored once and projected per
run.

Nothing downstream of the acquisition step changes: currency discovery,
reportability rules, per-run `ResearchFxSnapshot` publication, codec
validation, failure boundaries, and all authority decisions execute exactly
as today. The cache substitutes only the external acquisition step.

---

## 1. Current pre-fetch information boundary (Question A)

### 1.1 The exact point in code

`_try_fetch_fx_rates` (`product_intelligence/execution/orchestration.py:1325`)
is called from `execute_research_run` at line 608 — AFTER:

* `claim_execution` succeeded (line 551; atomic CREATED→RUNNING, so at most
  one execution of THIS run can reach the FX step — the existing
  duplicate-execution protection, `runs/execution_claims.py::claim_execution`);
* the full public pipeline completed (direct/search → fetch → extract →
  normalize → match → semantic → frozen-4A aggregate), producing
  `aggregation_result`;
* the 4D-B vendor lookup completed (or abstained), producing
  `supplemental_payload`;

and BEFORE the atomic final publication transaction (line 615:
`PriceIntelligenceSnapshot` + review candidates + optional
`ResearchSupplementSnapshot` + optional `ResearchFxSnapshot` +
`complete_execution`).

Inside `_try_fetch_fx_rates`, the sequence is:

1. line 1363: `required_currencies = _get_required_fx_currencies(
   aggregation_result, supplemental_payload=supplemental_payload)`
2. line 1369-1374: if `required_currencies` is empty → return `None`
   (USD-only run: ZERO ECB calls — frozen,
   `test_public_usd_only_no_vendor_non_usd_zero_fx_calls`);
3. line 1378-1380: if `fx_provider is None` → construct default
   `EcbFxProvider()`;
4. line 1385: `observation_set = fx_provider.fetch_rates(
   requested_currencies=required_currencies)` ← **THE POINT**;
5. line 1388-1397: `FxProviderError` → log + return `None` (NONFATAL —
   frozen, `test_fx_failure_is_nonfatal_while_provider_is_invoked`);
6. line 1399-1418: any other exception propagates (programming defect is
   fatal — frozen, the explicit NOTE at 1399);
7. line 1404-1413: `encode_fx_observation(...)` (fx_codec V1) → payload dict.

### 1.2 Deterministic inputs available at the point

| # | Input | Where from | Semantically relevant to FX cache lookup? |
|---|-------|-----------|------------------------------------------|
| 1 | Resolved provider object | `fx_provider` param or default `EcbFxProvider()` (line 1378-1380) | **YES — feed identity.** In production the web layer calls `execute_research_run(str(run.id))` with NO `fx_provider` (`web/views.py:259`, `:771`), so the resolved provider is always the default `EcbFxProvider`, whose endpoint is the module constant `_ECB_STATISTICS_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"` (`providers/fx.py:226-227`), whose parse hard-codes `provider_id="ECB"` and `base_currency="EUR"` (`providers/fx.py` `_parse_ecb_xml` return), and which has NO environment/configuration surface (verified: zero `os.environ`/`getenv` in `providers/fx.py`; no FX key in `config/settings.py`). The feed is fully, deterministically known pre-fetch. |
| 2 | `required_currencies` (frozenset) | `_get_required_fx_currencies` (line 1250): non-USD currencies from frozen-4A public buckets + non-USD currencies from USABLE vendor observations, always `| {"USD"}` when non-empty | **NO — not key material.** It is (a) run-specific (derived from THIS run's evidence), (b) the input to a post-parse PROJECTION (the provider fetches the full document and filters after parsing — `providers/fx.py` `fetch_rates` docstring: "Fetches the full ECB document and optionally filters to ``requested_currencies`` after parsing"), and (c) its non-emptiness is the existing call gate. It must not enter the cache key (see §3.4). |
| 3 | Current UTC wall-clock time | Available (`datetime.now(timezone.utc)` — the same clock the adapter uses for `retrieved_at`, `providers/fx.py` `fetch_rates`); NOT currently used anywhere in the FX path (verified: zero `today`/date-comparison references in `providers/fx.py`, `research/fx_codec.py`, `research/fx_math.py`, `research/compact_quote.py`, and the orchestration FX block) | **POLICY input only** — freshness/revalidation decision (§5). Never content identity. |
| 4 | Run identity `claimed_run` (UUID) | `execute_research_run`'s claimed run | **NO — run-scoped identity.** Used inside `_try_fetch_fx_rates` ONLY for log messages (lines 1371, 1395, 1422). Must not enter the key (FU2 run-scoped-authority discipline; a key containing run identity would make the cache per-run and useless). |
| 5 | Request identity (MPN + description) | `run.to_research_request()` (line 543) | **NO** — irrelevant to a public official-rate document; containing it would poison the key namespace. |
| 6 | `aggregation_result` / `supplemental_payload` | Pipeline outputs | **NO** — only their currency projections (input 2) are FX-relevant. |
| 7 | Existing persisted evidence (other runs' `ResearchFxSnapshot` rows) | DB | **NO — must NOT be read as evidence.** FU2 (`AD-062`, `compact_quote_public_replay.py`): cross-run reads of another run's snapshot as current evidence was a BLOCKED authority defect. The proposed cache is a separate feed-keyed store (§3), not a read of other runs' snapshots. |
| 8 | Claim state | `claim_execution` already succeeded | **Context, not key material** — guarantees single execution per run reaches this point. |

### 1.3 What is UNKNOWN pre-fetch (discovered only by a live document)

* **`observation_date`** — the XML `time` attribute of the first Cube with a
  time (`providers/fx.py` `_parse_ecb_xml`); the moving pointer of the
  "latest daily" feed.
* **Document content** — the full rate set (values + currency coverage).
* **Any content hash** — nothing is hashed in the current FX path.
* **`retrieved_at`** — stamped by the adapter clock at fetch time.
* **Whether a newer observation was published** since the last fetch.

**Boundary statement:** the only cache-relevant identity the caller knows
pre-fetch is the FEED identity (input 1), plus the wall-clock (input 3) for
policy. Everything else is post-fetch. Any lookup key must be composable from
feed identity alone.

---

## 2. ECB "latest daily" temporal semantics (Question B)

### 2.1 What the repository encodes

* The endpoint is a **moving pointer**: one fixed URL always serving the
  most recently published daily document (`_ECB_STATISTICS_URL`,
  `providers/fx.py:226-227`). There is no per-date endpoint in code (no
  `eurofxref-hist-*` usage anywhere — verified by repo-wide grep).
* `observation_date` is a property of the document, not of the fetch. The
  parser reads it from the document (`time` attribute) and performs NO
  comparison against the current date (verified: zero date-comparison in the
  entire FX path).
* `retrieved_at` is a property of the fetch (adapter clock), timezone-aware
  UTC (`providers/fx.py` `fetch_rates`; `FxObservationSet.__post_init__`
  requires aware datetimes).
* **Production evidence that the two dates differ is already in the
  record:** `AD-061` (PLAN decision log) records the post-FU1 secure retry
  from the production runtime: fetch on 2026-09-25 returned **observation
  date 2026-09-24** (USD 1.1367, ZAR 18.6836). The system persisted and
  displayed that cross-day document without complaint.
* PLAN §26.5 freezes the semantic: "Official ECB daily / working-day
  reference data is the intended source"; "FX rate is itself evidence,
  carrying: source, retrieved/rate date, rate"; "Historical report reload
  must use persisted FX evidence."

### 2.2 Consequences for a cache (each scenario)

| Scenario | Latest document's observation_date | Correct cache behavior |
|---|---|---|
| Weekday before the daily publication (ECB publishes ~16:00 CET ≈ 14:00–15:00 UTC) | previous working day | The feed legitimately serves a cross-day document. A cache asserting `observation_date == today` would miss/fail incorrectly. **Forbidden** (task constraint; matches the AD-061 production reality). |
| Weekday after publication | today (working day) | New content identity → new store row on the first live fetch of the day; same-day reuse after that. |
| Weekend | last working day (e.g. Friday) | Same content as Friday. Under the §5 proof window: at most one live fetch per UTC day that has non-USD runs; the document is re-proven each day it is needed. No staleness claim beyond the label (observation date shown). |
| ECB holiday | last working day before holiday | Same as weekend. The system has no ECB holiday calendar and must not need one: the policy keys on document content + proof time, never on a predicted publication calendar. |
| Other older-than-today cases (delayed publication) | older working day | Same mechanism. Delayed publication is invisible to the cache: it simply re-proves the older document until a newer one appears in a live fetch. |
| Temporary provider outage | unchanged (unknown) | Live fetch fails with `FxNetworkError` → NONFATAL (frozen boundary) → run completes without a snapshot, exactly as today; prior store artifacts are RETAINED (never deleted/overwritten by a failed refresh). No same-day proof exists → no same-day reuse → every run of the day attempts live (today's behavior). |
| Correction / republished rate for an observation date | same date, different content | Different content digest → a NEW store row for the same `observation_date` (the uniqueness key includes the digest, §3.2). Latest-selection (`max observation_date`, tie → `max last_proven_at`, §5.3) serves the most recently live-verified revision. The superseded revision remains as history — a correction can never destroy evidence, and no row is ever mutated in content. |
| Application/server timezone differences | document property | The policy uses UTC only (system canonical: `TIME_ZONE = "UTC"` in `config/settings.py`; all persisted timestamps are UTC-aware; the adapter's own `retrieved_at` is `datetime.now(timezone.utc)`). Server-local time never enters a key, a digest, or the proof window. `observation_date` is compared as a document date, never against a local clock. |

**Design consequence:** the cache must never encode "today" as an identity
dimension. It encodes (a) the feed, (b) the document's own
`observation_date` + content, and (c) WHEN the system last proved that
document was what the feed served.

---

## 3. Pre-fetch lookup-key contract (Question C, part 1)

### 3.1 Four separated concepts (binding)

Per the task, these four are distinct contracts and are NOT collapsed:

1. **PRE-FETCH LOOKUP IDENTITY** — what the caller can address BEFORE any
   network call. §3.2.
2. **STORED ARTIFACT / CONTENT IDENTITY** — what makes one stored daily
   document distinct from another. §3.3.
3. **INTEGRITY / PROVENANCE IDENTITY** — what proves a stored document is
   what the provider actually served, and when. §3.4.
4. **FRESHNESS / REVALIDATION POLICY** — when a stored document may be served
   instead of a live fetch. §5.

### 3.2 PRE-FETCH LOOKUP KEY

For the first slice there is exactly ONE known feed, and the lookup key is:

```
fx_cache_pre_fetch_key = (feed_id)
```

where `feed_id` is a stable identifier for the external source, defined for
the first slice as **`"ecb:eurofxref-daily"`** and bound (by test, not by
assumption) to the adapter's deterministic facts:

* endpoint URL = the `_ECB_STATISTICS_URL` constant (`providers/fx.py:226-227`);
* `provider_id` = `"ECB"` (hard-coded in `_parse_ecb_xml`);
* `base_currency` = `"EUR"` (hard-coded in `_parse_ecb_xml`);
* semantics = "latest daily" moving-pointer document.

`feed_id` is an execution-layer notion (it names a source); the constant
lives next to the endpoint it binds (proposed: additive constant in
`providers/fx.py`, open decision §13.6). `provider_id` and `base_currency`
are invariants OF the known feed, not per-lookup variables: any future feed
with different values is a different `feed_id`.

**Not in the pre-fetch key** (and why):

* `observation_date` — unknown pre-fetch (§1.3).
* document/content hash — unknown pre-fetch (§1.3).
* `required_currencies` — run-specific projection input; the provider
  contract already fetches the full document and filters after parsing
  (§3.5).
* run/request identity — run-scoped; would make the cache per-run.
* wall-clock date — a policy input (§5), not identity.

The lookup is therefore: *given the feed, which stored document (if any)
satisfies the freshness policy right now?*

### 3.3 STORED ARTIFACT / CONTENT IDENTITY (post-fetch uniqueness key)

```
fx_store_content_key = (feed_id, observation_date, content_sha256,
                        provider_id, base_currency)
```

* `observation_date` — from the document (`time` attribute).
* `content_sha256` — a canonical digest of the FULL parsed daily rate set:
  SHA-256 over the JSON encoding of the sorted
  `[(currency_code, rate_as_decimal_string), ...]` list, computed by a new
  pure research function (proposed `research/fx_cache_contract.py`,
  §11.2). Digesting the parsed canonical form — not the raw XML bytes — is
  deliberate: raw bodies are never persisted anywhere in this repository
  (verified repo-wide; 8A-PRE §1.2), and the parsed set is exactly what the
  system consumes. The content-addressing discipline follows the existing
  precedent `ResearchMicronAliasSnapshot` ("carries the body SHA-256, never
  the catalog body", `runs/models.py:1289+`).
* `provider_id` / `base_currency` — stored explicitly and re-validated on
  read (defense against a feed contract drift: a document whose
  provider/base no longer matches the feed invariants is excluded, §9).
* The digest makes the 8A-PRE "document hash" a real, computable,
  content-addressing field — while moving it OUT of the pre-fetch key, where
  it could never be known.

Uniqueness: DB `UniqueConstraint` on
`(feed_id, observation_date, content_sha256)`. Same document re-fetched →
same key (idempotent). Corrected revision of the same date → different
digest → different row (history preserved, §2.2).

The stored PAYLOAD is the full document encoded with the EXISTING fx_codec
V1 shape (`provider_id`, `observation_date`, `base_currency`, `rates` [ALL],
`retrieved_at` [original]) — codec reused, not forked; decode is the
existing fail-closed `decode_fx_observation`.

### 3.4 INTEGRITY / PROVENANCE IDENTITY (per store row)

* `original_retrieved_at` — IMMUTABLE. The time this content was first
  fetched live. Never overwritten by re-proof.
* `last_proven_at` — the time the feed was last LIVE-verified to serve this
  exact content. Mutable, convergent (§8).
* `created_at` — row insertion time.
* `content_sha256` — content integrity.
* codec `schema_version` (= 1, the reused V1) — payload integrity.
* `feed_id` — source binding (endpoint + provider + base invariants).
* (The endpoint URL itself is part of the `feed_id` binding and is not a
  separate column; fetcher behavior parameters — timeout 10 s, 512 KiB
  bound — are acquisition behavior, not content identity, and are excluded.)

### 3.5 Requested-currency-set question (critical answer)

**Answer: (1) — store/cache the full ECB daily document ONCE and project
requested currencies afterward.** Do not cache per currency set.

Derived from the actual provider contract, not assumed:

* `EcbFxProvider.fetch_rates` ALREADY fetches the full document and filters
  after parsing ("Fetches the full ECB document and optionally filters to
  ``requested_currencies`` after parsing" — `providers/fx.py` `fetch_rates`
  docstring; the filter is `tuple(r for r in ... if r.currency_code in
  requested_upper)`). The network artifact IS the full document; the
  filtered set is a projection of it.
* The `FxProvider` protocol explicitly supports the unfiltered form:
  "If None, the provider returns its full rate set" (`providers/fx.py`
  `FxProvider.fetch_rates`). So the execution layer can call
  `fetch_rates(requested_currencies=None)` and project itself — the
  projection is the same pure filter, preserving document order, sharing the
  same single `retrieved_at`. The run's persisted `ResearchFxSnapshot`
  payload is BYTE-IDENTICAL to today's (same provider_id, observation_date,
  base_currency, same rate entries in the same order, same retrieved_at) —
  no frozen codec/payload change, no existing-test breakage.
* Per-currency-set caching would multiply store rows by the combinatorics of
  requested sets across runs (every new combination of public-bucket and
  vendor currencies is a new key), store strictly LESS information per row,
  and create the possibility of two rows for the same observation date
  disagreeing in coverage — with no integrity benefit, because any subset is
  derivable from the full set.
* The full document always contains `USD` (the formula anchor,
  `research/fx_math.py` requires `rate_USD` for every non-USD conversion),
  as the ECB publishes it daily (verified in test fixtures:
  `tests/providers/test_fx_provider.py` `test_usd_rate_parsed`,
  `test_minimal_document`; `test_eur_not_in_rates` documents that EUR itself
  is the implicit base and may be absent — the projection handles that
  exactly as `fx_math` already does: `rate_EUR = 1` by definition).
* Reuse is still safe when a required currency is ABSENT from the cached
  full document (e.g. a currency the ECB no longer publishes): the
  read-time coverage check (§5.2) falls back to a live fetch; if the live
  document also lacks it, `fx_math` returns the existing fail-closed
  "rate for {C} not available" result — unchanged.

**Safer AND simpler: full-document storage + per-run projection.**

---

## 4. Post-fetch content/provenance identity contract (Question C, part 2)

Post-fetch, the system holds a parsed `FxObservationSet` (full document) and
derives, in order:

1. **Content identity:** `(observation_date, content_sha256)` — the digest
   is computed over the full parsed rate set BEFORE projection (§3.3).
2. **Feed binding check:** `provider_id == "ECB"` and
   `base_currency == "EUR"` must hold (they are hard-coded by the adapter
   today; the check makes the binding explicit and fail-closed for any
   future provider drift). A mismatch is a programming/contract defect
   (§9, fatal — it would mean the cache and the provider disagree about
   what the feed is).
3. **Integrity record:** `original_retrieved_at` (from the parse result's
   `retrieved_at`), `last_proven_at = now(UTC)`, `created_at = now(UTC)`.
4. **Store upsert** (§8: deterministic unique key + convergent re-proof).
5. **Projection:** `rates_for_run = [r for r in full if r.currency_code in
   required_currencies]` (document order preserved; identical to the
   provider's own filter).
6. **Run payload:** `encode_fx_observation(provider_id, observation_date,
   base_currency, rates_for_run, retrieved_at=original_retrieved_at)` —
   V1, byte-identical to today's live-path output.
7. **Run publication:** the run's own `ResearchFxSnapshot` inside the
   existing atomic transaction, with the additive `acquisition` label (§7).

The contract: **a store row is written ONLY from a successful live fetch**
(no other write path exists), and **a store row is served ONLY after full
read-time re-validation** (codec decode + feed invariants + coverage, §5.2).
The store is never the source of a rate value that the provider did not
return.

---

## 5. Freshness / revalidation state model (Question D)

### 5.1 Four distinct states (never conflated)

| State | Definition | Established by | Lifetime |
|---|---|---|---|
| `VALID_HISTORICAL` | The row is a codec-valid official observation for its persisted `observation_date` (positive finite Decimal rates, ISO date, feed invariants). | Decode + validation on read. | Permanent (until a correction supersedes it as LATEST; the row itself stays valid history). |
| `LATEST_KNOWN` | The row is the maximum of `(observation_date, last_proven_at)` among all VALID rows of the feed in the store. | Store-internal comparison at read. | Until a newer row is proven. |
| `PROVEN_LATEST_AS_OF_T` | A live fetch at time T returned THIS row's content — i.e., as of T the feed was serving this document. | Live success (insert or re-proof). | A statement **as of T**. It does NOT mean "no newer observation exists" — only "the feed served this at T". |
| `NOT_CHECKED_RECENTLY` | No live fetch has occurred since T (or the last one failed). Whether a newer observation exists is UNKNOWN. | Absence of proof. | The honest default between proofs. |

A row is always `VALID_HISTORICAL` (if well-formed) and is
`LATEST_KNOWN` at most until superseded; `PROVEN_LATEST_AS_OF_T` degrades to
`NOT_CHECKED_RECENTLY` as time passes WITHOUT becoming "invalid".
"System has simply not checked recently" is NEVER represented as
"system checked and found nothing newer" — the proof timestamp is the only
thing that ever claims the latter, and it always carries its `as-of` time.

### 5.2 Reuse (CACHE_HIT) conditions — bounded policy, no numeric TTL

A run may serve a store row instead of fetching live **iff ALL hold**:

1. **Feed gate:** the resolved provider is the built-in ECB feed
   (`isinstance(resolved_provider, EcbFxProvider)`). Any other protocol
   implementation (including all test fakes) bypasses the cache entirely
   and behaves exactly as today. (This keeps every existing test
   green by construction — §12.)
2. **Candidate selection:** the `LATEST_KNOWN` row of the feed exists.
3. **Read-time validation:** `decode_fx_observation(payload)` succeeds
   (fail-closed V1 codec), feed invariants hold
   (`provider_id == "ECB"`, `base_currency == "EUR"`), and the full stored
   rate set covers EVERY currency in `required_currencies`.
4. **Proof window (the bounded policy):** the row carries a live proof from
   the **current UTC day**: `last_proven_at`'s UTC calendar date ==
   `now(UTC)`'s calendar date.

Otherwise the run performs the LIVE path (§4). There is no numeric
duration anywhere: the window is a calendar-day equality anchored on the
feed's own publication granularity (at most one new document per working
day, plus rare corrections), using the system's canonical UTC day
(`TIME_ZONE = "UTC"`; the adapter's own clock is UTC). The 8A-PRE
constraint is honored: the cache does not fail or miss merely because
`observation_date != today` — the proof window is about WHEN the feed was
checked, never about what date the document carries.

**Residuals of the policy (documented, not hidden):**

* Intra-day publication/correction: if the ECB publishes (or corrects)
  after the day's only live proof, same-day runs serve the previously proven
  document. Bounded by (a) the feed's once-daily publication cadence,
  (b) the label: the report shows the document's `observation_date` and the
  original `retrieved_at` (§7), (c) display-supplemental authority only,
  and (d) automatic elimination on the next UTC day (proof window expires →
  mandatory live proof).
* Weekend/holiday: at most one live fetch per UTC day that has non-USD
  runs; the re-proven document may be several days old in `observation_date`
  — which is the feed's true latest, and is labeled as such.

### 5.3 Live path and re-proof

* A live fetch always (re)proves the content it returned:
  * content unseen → INSERT new row (`original_retrieved_at =
    last_proven_at = now`).
  * content already stored (unique-key collision) → convergent conditional
    UPDATE of `last_proven_at = now` only (content fields untouched,
    `original_retrieved_at` immutable).
* Latest-selection tie-break: `ORDER BY observation_date DESC,
  last_proven_at DESC` — the most recently live-verified revision of the
  newest date wins (corrections, §2.2).
* A failed live fetch writes NOTHING (no negative cache — 8A-PRE §5.8
  preserved) and deletes/overwrites NOTHING (prior artifacts retained).

---

## 6. retrieved_at / cache-served semantics (Question E)

| Fact | Value | Stored where | Mutability |
|---|---|---|---|
| Original provider `retrieved_at` | The adapter-clock time of the LIVE fetch that produced this content | Store row `payload.retrieved_at` + `original_retrieved_at`; and — unchanged — in EVERY run served from it, in the run's `ResearchFxSnapshot` V1 payload `retrieved_at` field | IMMUTABLE. A cache hit NEVER rewrites it. A re-proof of the same content does not touch it (only `last_proven_at` moves). |
| Cache insertion time | Store row `created_at` | Store row | Immutable |
| Cache-served time | The moment THIS run's evidence row was persisted | The run's own `ResearchFxSnapshot.created_at` (written in the existing atomic publication, milliseconds after the cache read, same run) together with `acquisition = "CACHE_HIT"` | Immutable |
| Current run snapshot | A NEW OneToOne `ResearchFxSnapshot` for this run | `runs.ResearchFxSnapshot` (publication step unchanged) | Per-run, as today |
| User-facing evidence age | Computed from `observation_date` ("ECB reference date") and original `retrieved_at` ("rates retrieved"), plus the acquisition label ("reused from cache, served <date>") | Report display (web layer, §11.7) | Rendered, never stored-as-fact |

**Invariant (binding):** a cache hit must not make old evidence look freshly
retrieved. The V1 payload semantics are unchanged — `retrieved_at` means
"when the provider observation was actually fetched" — and the acquisition
label (§7) makes the distinction explicit at the only place a user could be
misled (the report). The cache-served time is separately and derivably
visible (`created_at` of the run's own snapshot row).

---

## 7. LIVE / CACHE_HIT / REPLAY provenance contract (Question F)

### 7.1 Three disjoint labels

* **LIVE** — this run's FX evidence was acquired by a live provider fetch
  during this run (the only label that exists today, implicit).
* **CACHE_HIT** — this run's FX evidence was served from the store during
  this run; the payload carries the ORIGINAL `retrieved_at`; the row carries
  `acquisition = "CACHE_HIT"`.
* **REPLAY** — a later `GET /research/<uuid>` of a persisted run. This is a
  READ-PATH property (the frozen zero-live replay,
  `compact_quote_replay.py` / `compact_quote_public_replay.py`: "FX: from
  persisted ResearchFxSnapshot only (never live)"), NOT an acquisition
  property. It is never stored; it is what the GET path is. The audit chain
  for a replayed row is: report → this run's `ResearchFxSnapshot`
  (`acquisition` tells you LIVE or CACHE_HIT) → for CACHE_HIT, the store row
  proven by a live fetch.

### 7.2 Carrier decision: `ResearchFxSnapshot` gets ONE additive column

**Proposed (recommended): an additive model column, not a codec change, not
an evidence-vocabulary change.**

```
ResearchFxSnapshot.acquisition = CharField(
    max_length=16, choices=[("LIVE", "LIVE"), ("CACHE_HIT", "CACHE_HIT")],
    default="LIVE", editable=False)
```

Reasoning against the alternatives:

* **FX codec V2 (payload-level provenance):** would modify the frozen
  4D-C-A codec (`research/fx_codec.py` — V1 is strict: exactly six top-level
  keys, `schema_version` must equal 1). If the LIVE path kept writing V1,
  payload version would no longer mean "schema" but "schema + acquisition
  mode" (muddled); if it wrote V2, every existing assertion
  `fx_snapshot.schema_version == 1` (e.g.
  `tests/execution/test_fx_execution_integration.py:349,530`) would have to
  change — a test-modification cost with zero semantic gain. Rejected for
  the first slice.
* **`ExecutionEvidenceRecord` (the 8A-PRE §8.4 proposal):** requires a NEW
  `ExecutionStage` member (there is NO FX stage today —
  `domain/evidence.py` `ExecutionStage` = SEARCH/FETCH/EXTRACT/NORMALIZE/
  MATCH/AGGREGATE/SEMANTIC), a new detail code, `_VALID_COMBINATIONS`
  entries in `execution/evidence_writer.py`, reader support, and a change
  to a frozen domain vocabulary file — strictly more frozen-contract
  surface than one additive model column. It would also make FX appear in
  the per-run attempt log where it never has (the FX step today writes NO
  evidence record at all — verified: no FX stage calls in
  `orchestration.py`). Rejected for the first slice; the 8A-PRE §7.5
  open item is hereby answered with this recommendation.
* **Model column:** the model already owns run-level metadata outside the
  payload (`schema_version`, `created_at`); "how this run's evidence row was
  acquired" is exactly that class of fact. Default `"LIVE"` makes every
  existing row (all historically live) truthful without a data
  backfill. One additive migration operation; zero codec change; zero
  replay-path change (they decode the payload as before); zero existing-test
  breakage (the column is not asserted anywhere today).

The per-run snapshot is STILL published on every cache hit (publication step
unchanged — the architectural constraint is honored: a cache hit skips only
the network acquisition).

### 7.3 Display (web, additive)

The report shows, where FX evidence exists (both ALLOWED and DENIED replay
branches read this run's own snapshot — the DENIED branch already permits
persisted FX: `compact_quote_public_replay.py:35,147`):

* "ECB reference date: <observation_date>" (closes the 8A-PRE §2.4 display
  gap — the date is persisted today but rendered nowhere; verified: no
  `observation_date` in `web/templates/web/research_detail.html`),
* "rates retrieved: <original retrieved_at>",
* acquisition label: "retrieved during this research run" (LIVE) vs
  "reused from cache (served <created_at>)" (CACHE_HIT).

Presentation-only; no projection/authority change; `CompactQuoteReplayResult`
already carries the decoded `fx_snapshot` (`compact_quote_replay.py:67-78`)
so the view already has the data; only the `acquisition` field must be
surfaced alongside the row (additive view/replay plumbing).

---

## 8. Concurrency / idempotency design (Question G)

Precondition facts (verified): single-node deployment (Waitress + SQLite,
`config/settings.py`; "SQLite is pilot-only"); `claim_execution` prevents two
executions of the SAME run, but different runs (e.g. two users, or a run and
its retry) can execute concurrently — the model docstrings explicitly note
transitions are not atomic across processes and that "the honest fix (a
conditional update, row locking, or both) belongs to the phase that first
introduces a concurrent writer" (`runs/models.py` `ResearchRun`
docstring). The FX store is the first cross-run shared writer.

| Race | Behavior |
|---|---|
| Two runs miss the cache simultaneously (first non-USD runs of the UTC day) | BOTH perform the live fetch (duplicate call to the free, bounded endpoint — accepted; at pilot scale this is at most a handful of runs; no lock machinery per the repository's own "machinery guarding against a scenario" discipline). |
| Both fetch the same document; both try to persist | Deterministic unique key `(feed_id, observation_date, content_sha256)`: exactly one INSERT wins; the loser gets `IntegrityError` → re-reads the winner's row → performs the convergent conditional re-proof UPDATE. Final state: ONE row. |
| Duplicate content | Cannot exist as two rows (unique key). Same-day re-fetch of identical content = re-proof of the existing row, not a new row. |
| Process crash after live fetch, before cache persistence | The row simply doesn't exist yet; the next run's proof-window check fails (no same-day proof) → live fetch again. No partial row (single INSERT), no corruption, no lost run (the crashed run is terminalized by the existing boundary or retried via `retry_run`). |
| Cache row written, but the current run's atomic publication later fails | The run is FAILED by the existing outer boundary (orchestration lines 661-675); the store row REMAINS — deliberately: it is a valid, live-proven feed artifact, not run-scoped evidence (no cascade to a run; deleting it would destroy a proven observation because of an unrelated run failure). A later run may legally reuse it (same-day proof holds). |
| Stale cache entry while another process re-proves it | Re-proof mutates only `last_proven_at` (convergent: all concurrent re-provers of the same content write the same UTC-date value; last-write-wins is harmless). A correction inserts a NEW row (different digest). Readers always select `max(observation_date, last_proven_at)` → the most recently live-verified revision. Content is never mutated in place, so a reader can never observe a torn/mixed document. SQLite serializes writers (single-writer); Django's default behavior already applies to all existing writes. |
| Same-date correction race (two runs fetch pre- and post-correction) | Two rows, same `observation_date`, different digests. Both remain. Selection tie-break `last_proven_at` serves the more recently verified revision; the superseded revision stays as `VALID_HISTORICAL` audit material. |

**No distributed lock, no `SELECT ... FOR UPDATE`** (a no-op on SQLite per
`runs/ai_assisted_review.py:254`), no advisory machinery: deterministic
uniqueness + idempotent upsert + convergent conditional update is sufficient
and matches the repository's stated concurrency philosophy.

---

## 9. Failure taxonomy (Question H)

The existing boundary is preserved verbatim: FX acquisition failure is
display-supplemental and NONFATAL (`orchestration.py:1388-1397`;
PLAN §26.5 "If FX is unavailable, original price remains valid and USD
Equivalent displays unavailable"; `tests/execution/test_fx_tls_production_
chain.py`).

| Failure | Classification | Behavior (first slice) |
|---|---|---|
| Live fetch raises `FxProviderError` (network/parse/timeout) | Bounded provider failure (existing) | `return None` — run completes, NO `ResearchFxSnapshot`, USD Equivalent "Unavailable". **Exactly today.** The store is untouched: prior artifacts RETAINED (never deleted/overwritten by a failed refresh). |
| Cache SELECT fails (DB error at read) | Cache availability event | Candidate = none → LIVE path. Bounded log. The run's evidence, if obtained, is LIVE (or absent). NOT classified as a provider failure. |
| Corrupted cached payload (`FxCodecError` on read) / unsupported codec version / feed-invariant violation (`provider_id != "ECB"`, `base_currency != "EUR"`) / required-currency coverage gap in the stored full set | Cache integrity event | The candidate row is EXCLUDED (never served), loud bounded log (class name only — no raw payload, per the evidence-discipline of `domain/evidence.py`), row NOT deleted (forensics). → LIVE path. If the live path also fails → no snapshot (today's behavior). This is a fallback to a STRICTER path (more work, full validation), not a misclassification: the run's `acquisition` label records what actually happened (LIVE or none). Per the task's constraint, storage corruption is NOT silently turned into an "ordinary FX provider failure" — it is a distinct, logged cache event, and the only way it can affect the run is by removing a reuse candidate. |
| Live success, cache INSERT/UPDATE fails (DB error) | Cache availability event | The run STILL publishes its `ResearchFxSnapshot` from the live data (`acquisition="LIVE"`). Bounded log. The cache is best-effort: a cache write failure can never degrade the run's evidence. |
| Programming defect in cache code (`TypeError`, `ValueError`, `AssertionError`, unexpected `AttributeError`, …) | Fatal (existing discipline) | PROPAGATES to the single post-claim catastrophic boundary (orchestration lines 661-675) → run terminalized FAILED → `ExecutionError`. Mirrors the frozen FX NOTE (`orchestration.py:1399-1401`: "Any exception other than FxProviderError is a programming / contract defect ... MUST NOT be silently downgraded"). The ONLY exceptions caught inside the cache path are the two named, bounded classes: `IntegrityError` (unique-key race → re-read) and `FxCodecError` (candidate exclusion). Everything else is fatal. |
| Provider/cache feed-binding disagreement (a live `EcbFxProvider` fetch returns `provider_id != "ECB"` or `base != "EUR"`) | Programming/contract defect | Fatal (propagate) — it means the adapter's own hard-coded contract broke; serving or storing such content would poison the feed. (Cannot happen with the current hard-coded adapter; the check is defense-in-depth for the store's integrity.) |
| Live fetch returns a document lacking a required currency | Bounded (existing) | The run proceeds; `fx_math` returns the existing fail-closed "rate for {C} not available in FX evidence" (`research/fx_math.py`). Unchanged. |

**Explicitly NOT in the first slice:** negative caching of failures (8A-PRE
§5.8), cross-day serving of an older artifact after a failed live refresh
(open decision §13.3 — the store RETAINS the artifact; it is not SERVED
without a same-day proof).

---

## 10. Authority-safety proof (Question I)

**Claim:** the proposed cache cannot change Machine Price, Reviewed Price,
deterministic identity, semantic identity, public 4A market authority, vendor
authority, human-confirmed authority, or HARD_CONFLICT handling. It
substitutes only FX evidence ACQUISITION; it never substitutes or reuses an
authority decision.

Proof by structural enumeration (all citations at the starting SHA):

1. **Position in the pipeline.** The cache sits strictly INSIDE
   `_try_fetch_fx_rates` (step 6 of 7), replacing only step 4 of §1.1's
   sequence (the network call). Its inputs are the already-computed
   `aggregation_result` + `supplemental_payload`; its output is the same
   `fx_payload` dict shape. Every authority decision (2A/3C identity,
   semantic eligibility + provenance, frozen-4A aggregation, reviewed
   aggregation, vendor binding, working-quote policy) completes BEFORE the
   FX step and is an INPUT to it — none is re-derivable from FX data.
2. **FX is display-supplemental only (frozen).** `orchestration.py:599-605`
   ("FX evidence does NOT affect Machine Price, Reviewed Price,
   deterministic identity, or any existing pipeline statistics");
   `runs/models.py` `ResearchFxSnapshot` docstring ("DISPLAY-SUPPLEMENTAL
   only. The original source price amount and currency remain
   authoritative"); PLAN §26.5 ("USD Equivalent is a supplemental display
   value"; conversion "MUST NOT be moved into frozen 3B normalization or
   frozen 4A aggregation"); AD-046 (no FX conversion in normalization),
   AD-049 (no FX conversion in 4A). The ONLY consumer of FX data is
   `compute_usd_equivalent` inside compact-quote projection
   (`research/compact_quote.py:32-35,402-412`) — a display value.
3. **Machine Price (4A) is byte-independent of FX.**
   `PriceIntelligenceSnapshot` is encoded BEFORE the FX step
   (`orchestration.py:583`) and contains no FX field (frozen V1 price codec).
   A cache hit changes nothing in that payload. (Regression test planned:
   snapshot bytes identical across live/cached/absent FX paths — §12.)
4. **Reviewed Price / human confirmation.** Derived from the price snapshot
   + `AiAssistedReviewCandidate` state (8-step fail-closed POST validation;
   `derive_human_confirmed_assessment_indices`). FX enters only as the
   persisted display conversion for human-confirmed rows (AD-060 item 4:
   "persisted FX evidence only"). A cache hit serves the SAME persisted-evidence
   contract (the run's own snapshot, §7).
5. **Vendor authority.** `supplemental_payload` is computed BEFORE the FX
   step and is an input to currency discovery, not an output of it. The
   4D-C-SEC presentation gate (`web/commercial_access.py`) is untouched; the
   DENIED replay branch still never reads the supplement (FU2). The store
   contains NO vendor data (FX feed only — sensitivity class excluded by
   8A-PRE §5.2).
6. **Semantic identity.** The semantic runtime (pinned route, prompt v1.1,
   per-response model-identity proof) has no FX input and no store access.
   8A-PRE §4-D ("semantic response caching — DO NOT BUILD") stands.
7. **HARD_CONFLICT / working-quote policy.** Operates on identity
   assessments (`research/working_quote_policy.py`); no FX input.
8. **Per-run evidence ownership (FU2 discipline).** A cache hit publishes
   the run's OWN `ResearchFxSnapshot` in the run's OWN atomic transaction;
   the report GET replays ONLY this run's snapshot (frozen zero-live
   replay). The store is feed data, not run evidence: it is readable during
   EXECUTION of a claimed run and is NEVER read on the GET path. The store
   contains no run/request/MPN/URL data — nothing that could carry
   cross-run authority.
9. **Content trust chain.** A store row exists only because a live,
   bounded, TLS-verified `EcbFxProvider` fetch produced it (no other write
   path); its digest binds the content; every read re-validates through the
   fail-closed V1 codec + feed invariants + coverage before serving. The
   store can therefore supply at most "what the provider itself served" —
   no new values, no new authority, no fabrication (AD-009 "unknown beats
   fabricated certainty" preserved: an unusable candidate falls back to
   live or to the existing "Unavailable" display).
10. **Failure boundaries.** Cache-side failures degrade to the live path
    (strictly more validation, never less); fatal defects propagate exactly
    as the frozen FX NOTE requires (§9). A cache can never make a FAILED run
    COMPLETED with evidence it did not acquire — publication is unchanged.

**QED:** the cache substitutes only the acquisition of FX evidence.

---

## 11. Smallest proposed FX-only implementation slice (Question J)

**Proposed phase:** `PRODUCT-INTEL.8A-FX` — "ECB FX observation store:
same-day live-proof reuse of the full daily document." NOT implemented here.

### 11.1 New model / store (`runs/` — the only model-owning package)

`FxObservationStore` (name — open decision §13.11), new table, migration
0011 (the first operation of the single new migration file):

| Field | Type | Contract |
|---|---|---|
| `id` | UUID pk (default `uuid4`, editable=False) | Row identity (referential stability for re-proof updates) |
| `feed_id` | CharField(64) | Pre-fetch lookup key; first slice: exactly `"ecb:eurofxref-daily"` |
| `provider_id` | CharField(16) | Feed invariant; must decode to `"ECB"` |
| `base_currency` | CharField(3) | Feed invariant; must decode to `"EUR"` |
| `observation_date` | DateField | Document's `time` attribute |
| `content_sha256` | CharField(64) | Canonical digest of the full parsed rate set (§3.3) |
| `payload` | JSONField | Full document encoded with the REUSED fx_codec V1 (`schema_version=1`, ALL rates, original `retrieved_at`) |
| `original_retrieved_at` | DateTimeField (editable=False) | IMMUTABLE first live-fetch time of this content |
| `last_proven_at` | DateTimeField (editable=False) | Last live verification; mutable ONLY via the convergent conditional re-proof UPDATE |
| `created_at` | DateTimeField (default `timezone.now`, editable=False) | Insertion time |

Constraints:
* `UniqueConstraint(fields=["feed_id", "observation_date", "content_sha256"])`
* index `(feed_id, observation_date, last_proven_at)` (latest selection)
* `CheckConstraint` for non-empty feed/provider/base fields (mirrors the
  existing snapshot constraint style)

NO relationship to `ResearchRun` (deliberate: not run-scoped, not
cascade-deleted with runs — §8).

### 11.2 Pure contracts (`research/` — stdlib-only, no Django/I/O)

NEW module `research/fx_cache_contract.py`:

* `fx_document_content_sha256(rates: tuple[FxRateEntry-ish ...]) -> str` —
  the canonical digest: sorted `(currency_code, str(rate))` list → JSON
  (`sort_keys=True`) → SHA-256 hex. Pure, deterministic, order-insensitive.
  (Input type: the decoded full rate set or provider observations — defined
  over `(str, Decimal)` pairs to avoid importing the provider module into
  research; the execution layer adapts.)
* `project_required_rates(full_rates, required: frozenset[str]) -> tuple` —
  the documented projection (document order preserved; upper-cased
  comparison), mirroring the provider's own filter so live and cached
  outputs are byte-identical.
* `is_same_utc_day(dt: datetime, now: datetime) -> bool` — the proof-window
  predicate (UTC calendar-date equality; tz-aware inputs required).
* Store-payload codec: **NONE NEW** — the store's payload IS the existing
  `encode_fx_observation` / `decode_fx_observation` V1 (reused, not forked;
  `research/fx_codec.py` UNCHANGED).

### 11.3 Feed-identity constant (`providers/`, additive)

`providers/fx.py`: add `FX_FEED_ID_ECB_DAILY = "ecb:eurofxref-daily"`
(next to `_ECB_STATISTICS_URL`) + docstring note binding it to the
endpoint/provider/base invariants. NO behavior change. (Placement — open
decision §13.6.) A mirror-lock test proves the constant's binding facts
against the adapter (endpoint URL value, parsed `provider_id`,
`base_currency`) so the binding cannot drift silently.

### 11.4 Cache service (`execution/` — owns lookup + I/O)

NEW module `execution/fx_observation_cache.py` (execution may import
domain/research/providers/runs — verified layer rule, `execution/__init__.py`
docstring + `tests/web/test_web_boundaries.py` allowlists unaffected):

* `try_reuse_latest_observation(required) -> FxObservationSet | None` —
  candidate selection (`order_by("-observation_date", "-last_proven_at")`),
  read-time validation (§5.2 items 3-4), projection, and returns the
  `FxObservationSet` (original `retrieved_at`) or `None`. Catches ONLY
  `FxCodecError` (exclusion) + DB read errors (→ `None`, bounded log).
* `record_live_observation(feed_id, full_set) -> None` — upsert: INSERT the
  row; on `IntegrityError` → conditional UPDATE
  (`filter(id=..., last_proven_at=<read value>).update(last_proven_at=now)`,
  convergent); on other DB errors → bounded log, return (best-effort).
* Both functions raise NOTHING for bounded events; programming defects
  propagate (no broad `except` — the same discipline as
  `providers/fx.py`'s explicit NOTE).

### 11.5 Orchestration lookup location (exact)

`execution/orchestration.py::_try_fetch_fx_rates` — between provider
resolution (line 1378-1380) and the fetch (line 1385). The changed block:

```
required_currencies            # UNCHANGED (currency discovery still runs first)
if not required_currencies:    # UNCHANGED (USD-only zero-call gate)
    return None
provider resolution            # UNCHANGED
if isinstance(resolved, EcbFxProvider):          # FEED GATE
    hit = try_reuse_latest_observation(required) # pre-fetch lookup
    if hit is not None:                          # CACHE_HIT PATH
        payload = encode_fx_observation(hit...)  # V1, original retrieved_at
        acquisition = "CACHE_HIT"
        return (payload, acquisition)            # log: reused, obs date
    # else fall through to LIVE
full = resolved.fetch_rates(requested_currencies=None)   # LIVE PATH:
                                                         # full document (one
                                                         # network call, same
                                                         # endpoint/bounds)
# feed-binding check (provider_id/base invariants) — defect => propagate
record_live_observation(FX_FEED_ID_ECB_DAILY, full)      # best-effort upsert
projected = project_required_rates(full, required)       # == today's filter
payload = encode_fx_observation(projected, retrieved_at=full.retrieved_at)
acquisition = "LIVE"
return (payload, acquisition)
```

* `FxProviderError` handling: UNCHANGED (around the live call only; a cache
  hit cannot raise it). Non-`FxProviderError` propagation: UNCHANGED
  discipline.
* The function's return type gains the `acquisition` label (internal
  detail; the caller threads it into publication).
* For non-`EcbFxProvider` providers (all test fakes): the ENTIRE cache
  branch is skipped and the current code path runs byte-for-byte
  (`fetch_rates(requested_currencies=required)` as today) — every existing
  FX test stays green by construction.

Caller (`execute_research_run`, line 638-644):
`ResearchFxSnapshot.objects.create(run=..., schema_version=1,
payload=fx_payload, acquisition=acquisition)` — additive kwarg only.

### 11.6 Additive model change (second operation of migration 0011)

`ResearchFxSnapshot.acquisition` — exactly as §7.2 (default `"LIVE"`,
`editable=False`). No backfill needed (the default is historically true:
every existing row was acquired live — verified: no cache exists today).

### 11.7 Display (web, additive, presentation-only)

* `views.py` `research_detail`: surface `fx_row.acquisition` + the decoded
  `observation_date`/`retrieved_at` into template context (the replay
  result already carries the decoded snapshot; the view holds the row).
* `research_detail.html`: FX evidence line under the Compact Quote
  summary: reference date + rates-retrieved time + acquisition label.
  ALLOWED and DENIED branches alike (both already read this run's FX
  snapshot; no vendor data involved — 4D-C-SEC untouched).
* NO change to projection contracts, replay fail-closed behavior, or the
  zero-live GET invariant (the store is never read on GET).

### 11.8 Paths summary

* **LIVE:** as today, except the full document is fetched
  (`requested_currencies=None`) and projected at the caller (run payload
  byte-identical), plus the best-effort store record.
* **CACHE_HIT:** store read → validate → project → encode V1 (original
  `retrieved_at`) → publish run snapshot with `acquisition="CACHE_HIT"` →
  display label. ZERO network.
* **Refresh/revalidation:** implicit — the proof window (§5.2 item 4)
  forces a live proof on the first non-USD run of each UTC day; every live
  success (re)proves; there is no explicit "refresh trigger" and no
  background worker (excluded by the task).
* **Failure behavior:** §9 taxonomy.

### 11.9 Explicitly excluded from this slice

Page caching; Serper/search caching; vendor caching (permanent exclusion
stands — sensitivity); semantic-response caching; market-listing freshness
repair; `ListingObservation` codec changes (the per-observation
`retrieved_at` gap stays a separate 8A decision, 8A-PRE §7.4); any general
cache framework; Redis/Celery (CLAUDE.md binding); background refresh
workers; negative caching; cross-day failure-serve; cache of any second
feed; retention/cleanup policy (the store is naturally bounded at ~1 row
per working day + corrections — cleanup is a later decision).

---

## 12. Exact expected files / tests / migration impact (implementation phase)

### 12.1 Files expected to change (at implementation, for reviewer approval)

| File | Change |
|---|---|
| `product_intelligence/runs/models.py` | ADD `FxObservationStore` model; ADD `ResearchFxSnapshot.acquisition` column. No existing field/semantics modified. |
| `product_intelligence/runs/migrations/0011_*.py` | NEW — the only new migration (CreateModel + AddField). `makemigrations --check` must report "No changes detected" after. |
| `product_intelligence/research/fx_cache_contract.py` | NEW pure module (§11.2). |
| `product_intelligence/providers/fx.py` | ADD `FX_FEED_ID_ECB_DAILY` constant + docstring note. No behavior change. |
| `product_intelligence/execution/fx_observation_cache.py` | NEW cache service (§11.4). |
| `product_intelligence/execution/orchestration.py` | `_try_fetch_fx_rates` gains the cache branch + full-document fetch for the gated ECB path; caller threads `acquisition` into the FX snapshot create. No other orchestration logic touched. |
| `product_intelligence/web/views.py` | ADD context fields for the FX evidence line (acquisition + observation date + retrieved at). |
| `product_intelligence/web/templates/web/research_detail.html` | ADD FX evidence display line. |
| `docs/PRODUCT_INTELLIGENCE_PLAN.md` | NEW canonical section (proposed §26.18) + decision-log entry (AD-064) + roadmap status — at implementation. |
| `docs/PRODUCT_INTELLIGENCE_STATUS.md` | Phase section + ownership-table row — at implementation. |
| `docs/PRODUCT_INTEL_8A_FX_DESIGN.md` | THIS document (design record; committed at implementation with the phase). |

### 12.2 Tests required (new nodes only; NO existing test modified)

* **`tests/research/test_fx_cache_contract.py`** (new): digest
  determinism / order-insensitivity / correction-sensitivity (one rate
  changed → different digest); projection order preservation and
  equivalence with the provider's own filter (mirror-lock over the full
  fixture set); same-UTC-day predicate (midnight boundary, aware-only
  inputs, naive rejected); stdlib-only boundary guard (existing research
  boundary test auto-covers the new module via file scan).
* **`tests/runs/test_fx_observation_store.py`** (new): unique constraint
  (same content twice → one row); correction rows coexist (same date, two
  digests); latest-selection ordering (`observation_date` then
  `last_proven_at`); `original_retrieved_at` immutability vs re-proof
  updates; no run cascade (deleting a run leaves store rows);
  `ResearchFxSnapshot.acquisition` default LIVE + choices.
* **`tests/execution/test_fx_cache_orchestration.py`** (new; production-
  shaped with real `EcbFxProvider` + mocked `urllib.request.urlopen`, the
  existing `test_fx_transport.py` pattern):
  * no store row → LIVE (one fetch; row inserted; snapshot
    `acquisition=LIVE`);
  * same-day proven row covering `required` → CACHE_HIT (ZERO urlopen —
    armed fail-fast sentinel, the existing `_RaisingProvider` pattern);
  * row proven YESTERDAY (stale proof window) → LIVE;
  * weekend case: Friday document proven Saturday → served Saturday with
    `observation_date=Friday` (no today-assertion anywhere);
  * mid-day publication case: two rows (Fri + Mon), Monday proven →
    Monday served;
  * correction case: same date, two digests, later `last_proven_at`
    served;
  * corrupted candidate payload (`FxCodecError`) → excluded → LIVE, never
    served; row not deleted;
  * row missing a required currency → LIVE fallback;
  * coverage check with a currency absent from both cache and live →
    existing `fx_math` "unavailable" reason;
  * USD-only run → ZERO fetches AND ZERO store reads (gate before lookup);
  * injected non-ECB fake provider → cache bypassed, byte-for-byte current
    behavior (call_count, payload, schema_version all as today);
  * **payload byte-identity:** run snapshot payload under LIVE
    (full-fetch+project) == payload under today's filter path == payload
    under CACHE_HIT (same content) — the frozen 4D-C-A V1 contract
    unchanged;
  * live fetch failure (armed `FxNetworkError`) with stale row → NO
    snapshot, run COMPLETED (frozen failure boundary), store unchanged
    (artifact retained);
  * live fetch failure with no row → today's exact behavior;
  * cache write failure after live success → run publishes LIVE snapshot
    (bounded log; no crash);
  * programming defect simulation in cache code (forced `TypeError`) →
    run terminalized FAILED / `ExecutionError` (NOT downgraded to a
    provider failure);
  * concurrency: two threads racing the same document → one row, both runs
    publish their own snapshots (SQLite in-process; the cross-process
    variant is covered by the unique-key contract).
* **`tests/execution/test_fx_cache_authority.py`** (new; zero-authority-
  leakage proofs, the frozen-fixture pattern):
  * Machine Price snapshot bytes identical across LIVE / CACHE_HIT /
    FX-absent paths (non-USD fixture);
  * compact-quote `usd_equivalent` identical LIVE vs CACHE_HIT (same
    document);
  * historical replay of a CACHE_HIT run: ZERO live I/O (armed
    Search/Page/Vendor/ECB/semantic/urlopen sentinels — the existing
    `test_full_replay_entry_point_zero_live_boundaries` pattern), renders
    the label;
  * DENIED-branch replay unchanged (no supplement read; FX label renders
    from this run's own snapshot);
  * vendor/semantic/human-review/HARD_CONFLICT fixtures re-proven
    unaffected (existing suites must pass unmodified — the primary proof).
* **`tests/providers/test_fx_provider.py`** (ADD nodes only): feed-
  constant mirror-lock (endpoint value, `provider_id`, `base_currency`
  binding); `fetch_rates(None)` full-set behavior re-proven.
* **Existing suites:** `tests/research/test_fx_codec.py`,
  `tests/research/test_fx_math.py`, `tests/providers/test_fx_transport.py`,
  `tests/execution/test_fx_currency_discovery.py`,
  `tests/execution/test_fx_execution_integration.py`,
  `tests/execution/test_fx_tls_production_chain.py`, all replay/
  web-boundary/architecture-guard suites — UNMODIFIED and green.
* **Governance commands (at implementation):** `python -m pytest` (full;
  collection must be ≥ 5633 + new nodes, zero deletions), `python
  manage.py check`, `python manage.py makemigrations --check --dry-run`
  ("No changes detected").

### 12.3 Migration impact

Exactly ONE new migration (`0011`), two additive operations
(CreateModel `FxObservationStore`, AddField `ResearchFxSnapshot.
acquisition` with default). No existing migration modified. No data
backfill (the default is historically true). The store is empty at
migrate-time (first rows appear on the first live fetch after deploy).

---

## 13. Open decisions requiring reviewer (ChatGPT) approval

1. **Provenance carrier.** Recommended: additive
   `ResearchFxSnapshot.acquisition` column (§7.2). Alternatives rejected
   with reasons: FX codec V2 (frozen-codec churn + existing
   `schema_version == 1` test assertions) and evidence-vocabulary FX stage
   (frozen domain file + writer/reader + combination matrix; FX has never
   been an evidence-log "attempt"). Confirm or direct a different carrier.
2. **Proof window.** Recommended: same-UTC-calendar-day live proof
   (`last_proven_at` date == now date) (§5.2) — a semantic bound tied to
   the feed's once-daily publication cadence, with NO numeric duration.
   Confirm this is an acceptable "bounded policy" and accept the documented
   intra-day publication/correction residual (labeled; display-supplemental;
   self-clearing next UTC day).
3. **Cross-day serve on live failure.** Recommended: RETAIN but do NOT
   serve without a same-day proof (first slice) — preserves the frozen
   failure tests' observable behavior. Alternative: serve the retained
   artifact with an explicit "last verified <t>" label (strictly more
   display value; changes failure-path observable behavior; larger test
   surface). Decide.
4. **Full-document fetch for the gated ECB path.** Recommended:
   `fetch_rates(requested_currencies=None)` + caller projection (run
   payload byte-identical; protocol already supports None). Confirm no
   objection to the orchestration-side projection replacing the
   provider-side filter for the ECB feed only.
5. **Feed gate.** Recommended: cache active ONLY for
   `isinstance(resolved, EcbFxProvider)`; every other provider (all test
   fakes) bypasses the cache and runs the current byte-for-byte path.
   Confirm (this is what keeps the existing 5633-node suite green without
   modification).
6. **Feed-constant placement.** Recommended: `FX_FEED_ID_ECB_DAILY` in
   `providers/fx.py` (next to the endpoint it binds), mirror-locked by
   test. Alternative: define in `execution/` (keeps providers diff at
   zero). Decide.
7. **Display scope.** Recommended: include the FX evidence line
   (reference date + retrieved time + acquisition label) in this slice —
   required for §18 "A report must show how old its evidence is" and for
   making cache hits visible rather than invisible. Alternative: defer
   display to a display-only FU (NOT recommended: an invisible cache hit
   cannot be audited by the user).
8. **Store retention/cleanup.** Recommended: none in this slice (~1 row
   per working day + corrections; pilot-scale). Confirm deferral of any
   retention policy to a later 8A decision.
9. **Corrupted-candidate handling.** Recommended: exclude + loud bounded
   log + no deletion + live fallback (§9). Confirm (alternative: fatal on
   selected-candidate corruption — stricter, but converts a recoverable
   cache event into a failed run for display-supplemental data).
10. **Concurrency posture.** Recommended: unique-key idempotent upsert +
    convergent conditional re-proof; NO locks; accept bounded duplicate
    live fetches among concurrent first-runs of a day (§8). Confirm.
11. **Naming.** Store model name (`FxObservationStore` proposed) and
    label values (`LIVE` / `CACHE_HIT`; `REPLAY` is read-path-only, never
    stored). Confirm or rename.
12. **Documentation governance drift (flagged, NOT silently resolved).**
    `docs/PRODUCT_INTELLIGENCE_STATUS.md` (phase-ownership table: "8A-PRE …
    **PLANNED** (next delivery)") and the PLAN roadmap ("NEXT —
    PRODUCT-INTEL.8A-PRE … PLANNED") still list 8A-PRE as planned, while
    the 8A-PRE audit document exists in the tree (untracked) and this
    phase's instruction records 8A-PRE as APPROVED / COMPLETE. At
    implementation approval, STATUS + PLAN must be updated (docs-only) to
    record: 8A-PRE complete (audit delivered), 8A-FX-DESIGN complete (this
    document), the AD-064 decision entry, and the new phase state. No
    material architecture conflict — a state-lag in the volatile document.
13. **8A-PRE §7.1 store-shape items now answered** for reviewer
    confirmation: ownership (research pure contracts / runs model /
    execution lookup — unchanged from 8A-PRE §4), key fields (§3.3),
    sensitivity class (FX = non-sensitive public official; vendor remains
    excluded), and the "last_used_at" question — answered as: NO mutable
    usage counter on the store row (usage is auditable per run via each
    run's snapshot `acquisition`; a `last_used_at` would be a second
    mutable column with no consumer). Retention bound: open (§13.8).

---

## 14. Git governance evidence (this design phase)

Collected at completion of this phase (see §14.1 for the live commands'
output at report time):

* `git rev-parse HEAD` → **`55d1879a03da3dc6163a28c9524b5ef0396b76b3`**
  (the authoritative starting SHA — unchanged).
* `git status --short` → untracked entries ONLY: the pre-existing
  evaluation artifacts (`b2_b3_full.txt`, `b2_b3_full_junit.xml`,
  `nemotron_full_evaluation.json`, `nemotron_full_manifest.json`,
  `nemotron_full_responses.jsonl`, `qwen38_run1_responses.jsonl`,
  `qwen38_run2_responses.jsonl`), the 8A-PRE audit document, and THIS
  design document (`docs/PRODUCT_INTEL_8A_FX_DESIGN.md` — newly written,
  untracked, NOT committed, following the 8A-PRE deliverable precedent).
* `git diff --stat` → **empty** (zero tracked-file changes).
* `git diff --name-status` → **empty**.

Explicit statements:

* Production files changed? **NO** (zero edits to any tracked file).
* Tests changed / deleted / renamed? **NO**.
* Tests skipped / xfail / deselected? **NO** (no test run was needed or
  performed; the frozen 5633-node B1 baseline stands).
* Models / migrations changed? **NO** (no model or migration file touched;
  `makemigrations --check` state is therefore unchanged from the SHA).
* Frozen authority contract changed? **NO** (4D-C-A codec/persistence,
  4A/3B/2A, semantic route, vendor, human review, replay, evidence
  vocabulary — all read-only).
* Implementation performed? **NO** (design only; the §11 slice is proposed,
  not built).
* Committed / pushed / deployed? **NO**.

**Design delivered. STOP — no implementation performed, none authorized.**
