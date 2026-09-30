# PRODUCT-INTEL.8A-FX-DESIGN-FU1 — Freshness Proof & Canonical Feed
# Eligibility Closure

**Status:** DELIVERED (narrow corrective design, read-only). This document
corrects two BLOCKED items of
`docs/PRODUCT_INTEL_8A_FX_DESIGN.md` (the prior 8A-FX-DESIGN, reviewed, NOT
yet approved for implementation):

* **BLOCKER 1** — the prior same-UTC-day proof window (§5.2 item 4,
  `is_same_utc_day`) is UNSOUND and is replaced by a proof-instant +
  ECB-calendar-closure interval predicate.
* **BLOCKER 2** — the prior `isinstance(EcbFxProvider)` feed gate
  (prior §11.5, §13.5) is a test-preservation class hack and is replaced by
  an explicit canonical-feed eligibility contract anchored at the
  canonical-default construction site.

Everything else in the prior design that is NOT touched by these two
corrections (the four-part identity split §3, full-document storage +
projection §3.5, store model §11.1, retrieved_at immutability §6, the
`ResearchFxSnapshot.acquisition` carrier §7, concurrency core §8, failure
taxonomy §9, authority-safety proof §10) stands as written, EXCEPT where
explicitly amended below. This is a zero-diff phase: no implementation, no
test change, no model/migration, no commit.

**Authoritative starting SHA:** `55d1879a03da3dc6163a28c9524b5ef0396b76b3`

**Re-review performed for this FU1 (fresh, not from the prior report):**
`providers/fx.py` (URL constant L226-228; `FxProvider.fetch_rates`
`requested_currencies: frozenset[str] | None` L190-203, "If None, the
provider returns its full rate set"; `EcbFxProvider.fetch_rates` L399-420,
"Fetches the full ECB document and optionally filters to
``requested_currencies`` after parsing", filter at L471);
`execution/orchestration.py` (`_try_fetch_fx_rates` L1325-1425: discovery
L1363, USD-only gate L1369-1374, **canonical default construction site
L1377-1380** `if fx_provider is None: fx_provider = EcbFxProvider()`, fetch
L1383-1386, FxProviderError boundary L1388-1397, programming-defect NOTE
L1399-1401, encode L1404-1413); `runs/models.py`
(`ResearchFxSnapshot` L1210-1285, OneToOne run pk, V1-only payload,
`created_at`); `research/fx_codec.py` (strict V1: exactly six top-level
keys, `schema_version` must equal 1, fail-closed);
`execution/compact_quote_replay.py` (`CompactQuoteReplayResult` L64-79
carries `fx_snapshot`; FX read L248-255 "from persisted ResearchFxSnapshot
only (never live)"); `web/views.py` L259 and L771 (BOTH production call
sites — new research and retry — invoke
`execute_research_run(str(run.id))` with NO `fx_provider` argument);
FX tests (`tests/execution/test_fx_execution_integration.py` — all
orchestration-level FX tests inject `_FakeFxProvider` /
`_TlsFailingFxProvider`-style objects; `tests/providers/test_fx_transport.py`
L55-110 — repo precedent for mocking `urllib.request.urlopen` directly
against the canonical `EcbFxProvider`; `tests/research/test_fx_codec.py`
`test_wrong_schema_version` uses `99`); `requirements.txt` (minimal: no
freezegun, no calendar library); repo-wide grep: **zero** existing
`zoneinfo`/`ZoneInfo`/`freezegun` usage.

---

## 1. Exact flaw in the prior same-day rule

Prior rule (8A-FX-DESIGN §5.2 item 4, §11.2 `is_same_utc_day`):

```
reuse iff date(last_proven_at, UTC) == date(now, UTC)
```

**Flaw (primary — the reviewer's counterexample, confirmed sound):**
"a live fetch happened sometime today (UTC)" does NOT imply "the feed has
not since published a newer official observation". ECB updates the euro
reference rates on **working days, except TARGET closing days**, normally at
approximately 16:00 CET. The prior rule's proof instant T is discarded to a
date; every later N on the same UTC date passes the predicate regardless of
whether a publication event fell in (T, N]. Concrete unsound sequence,
all under the prior rule:

1. T = Monday 09:00 UTC (10:00 CET) — live fetch; the feed still carries
   the PREVIOUS working day's document (Monday's ~16:00 CET publication,
   ≈14:00/15:00 UTC, has not happened yet). Row proven, `observation_date`
   = previous working day.
2. ECB publishes Monday's document ≈14:00–15:00 UTC.
3. N = Monday 16:00 UTC — `date(T) == date(N)` → prior rule serves the
   PREVIOUS working day's rates as "latest known" for the rest of the UTC
   day. The run is labeled CACHE_HIT with an `observation_date` that is NOT
   the latest official observation. This is exactly "stale data presented
   as current" (PLAN §18) in the freshness dimension: the label shows an
   old date, but the acquisition semantics ("this is the latest official
   observation") are false.

**Flaw (secondary — timezone misalignment):** the prior rule used UTC
calendar days while the publication contract is defined in CET/CEST. At
Friday 23:30 UTC = Saturday 01:30 CET (winter), the UTC rule treats the
moment as "Saturday" (a new UTC day begins at Friday 24:00 UTC = Saturday
01:00 CET) — and conversely a Friday 23:59 UTC proof is "today-eligible"
for Friday 23:59 UTC uses whose ECB-calendar day is already Saturday while
the interval (T, N] still contains Friday CET business-day time in which a
delayed Friday publication could land. The UTC-day boundary does not track
the publication-day boundary.

**Flaw (structural — state collapse):** `PROVEN_LATEST_AS_OF_T` was stored
with the instant (`last_proven_at` DateTimeField, prior §11.1 — the storage
was correct) but CONSUMED as a date. A proof is a statement about the world
**at instant T** ("at T, the feed was serving this document"), not about a
whole day. Collapsing T to date(T) converts a point-in-time proof into a
false day-long claim. The four-state model requires the proof to retain its
actual instant.

**What the prior rule got right (kept):** the proof must be a LIVE fetch
event; reuse requires the row to be validated on read; business-day
publication timing is the invalidation source; the cache must never assert
`observation_date == today`.

---

## 2. Corrected freshness state transition model

The four states are preserved, with the proof now an **instant-parameterized
relation**, never a date flag:

| State | Definition (corrected) |
|---|---|
| `VALID_HISTORICAL` | The row is a codec-V1-valid official observation for its persisted `observation_date` (positive finite Decimal rates, ISO date, feed invariants `provider_id="ECB"`, `base_currency="EUR"`). Established by decode + validation on every read. Permanent until superseded as LATEST_KNOWN; the row itself never becomes invalid. |
| `LATEST_KNOWN` | The row is the maximum of `(observation_date, last_proven_at)` among all VALID rows of the feed (selection rule unchanged from prior §5.3; tie → most recently proven revision wins). |
| `PROVEN_LATEST_AS_OF_T` | **T is the actual aware UTC instant** `last_proven_at` at which the canonical live acquisition verified "the feed was serving exactly this content (this `observation_date` + this `content_sha256`)". The state is permanent **as of T**; it makes NO claim about any time after T. |
| `NOT_CHECKED_SINCE_T` (renamed from NOT_CHECKED_RECENTLY — the corrected name is exact) | At use-instant N, the stored proof T does not cover the interval [T, N]: `P(T, N) = false` (§3.2). The feed MAY have published in [T, N]; the system has not checked. This is the honest state between proofs — it is computed per (T, N) pair, never stored as a row flag. |

**Reuse is not a row state; it is the relation** `REUSABLE(T, N) =
P(T, N) ∧ VALID ∧ COVERAGE` (§3.2). A row transitions in reuse-sufficiency
deterministically: sufficient while no ECB working day enters [T, N];
insufficient from the first instant an ECB working day does. The row's
stored fields do not change at that transition — only the relation to N
does.

**Transition table:**

```
INSERT (canonical live success, new content)
    -> VALID_HISTORICAL + PROVEN_LATEST_AS_OF_{now} + LATEST_KNOWN
       (unless a newer row exists -> VALID_HISTORICAL only)
RE-PROOF (canonical live success, identical content, T1 > T0)
    -> last_proven_at := T1   (convergent UPDATE; original_retrieved_at,
       payload, created_at UNTOUCHED)
       PROVEN_LATEST_AS_OF_{T1}
SUPERSEDE (canonical live success, newer observation_date or corrected
           same-date content)
    -> new row inserted; old row: VALID_HISTORICAL, no longer LATEST_KNOWN
USE AT N with REUSABLE(T,N)
    -> CACHE_HIT served (row untouched by the read)
USE AT N with P(T,N) false
    -> live path; on live success the row is (re-)proven (see above)
LIVE FAILURE
    -> nothing written, nothing deleted, nothing re-proven; prior
       artifacts retained (prior §5.3/§9, unchanged)
```

No state is ever "expired" in storage; expiration exists only in the
(T, N) relation. This is the direct repair of the structural flaw (§1):
`PROVEN_LATEST_AS_OF_T` retains the actual proof instant T.

---

## 3. Corrected proof predicate — exact contract

### 3.1 The only publication fact the policy relies on

From ECB's stated contract (task-given; consistent with the in-repo
production evidence AD-061, where a 2026-09-25 fetch carried
`observation_date` 2026-09-24):

> Euro FX reference rates are updated on **working days, except TARGET
> closing days** (normally ≈16:00 CET).

From this, the policy consumes EXACTLY two deterministic consequences:

* **C1 (closure):** Saturday and Sunday are NEVER working days, in any
  year, under any DST arrangement. Hence **no publication event can occur
  at any instant whose ECB-calendar day is Saturday or Sunday.**
* **C2 (working-day risk):** at any instant whose ECB-calendar day is
  Monday–Friday, a publication event is NOT excludable by the policy
  (publication timing ≈16:00 CET is approximate; delayed publication is
  possible; corrections are possible). A working-day instant is therefore
  always treated as "publication possible".

The policy deliberately uses NEITHER the ≈16:00 CET time NOR the 14:15 CET
fixing time NOR any TARGET closing-day list. Consequence: the v1 predicate
is sound under the stated contract with zero timing assumptions and zero
calendar data.

**ECB-calendar day** = the calendar day in the zone of the publication
contract: `Europe/Brussels` (CET/CEST; the ECB's home zone). A constant in
the execution layer (see §3.3); the pure predicate receives the zone as a
parameter so tests can pin fixed offsets (§13).

### 3.2 The predicate (deterministic, pure)

```
P(T, N) :=  for every ECB-calendar day d that overlaps the closed
            interval [T, N] (i.e. some instant of day d lies in [T, N]),
            d is a Saturday or a Sunday.

REUSABLE(T, N, row, required) :=
            T <= N
  ∧  P(T, N)                                   # no publication possible in [T,N]
  ∧  row is LATEST_KNOWN of the feed           # prior §5.3 selection
  ∧  decode_fx_observation(row.payload) OK     # VALID_HISTORICAL, fail-closed V1
  ∧  row.provider_id == "ECB" and row.base_currency == "EUR"   # feed invariants
  ∧  required ⊆ {c : (c, _) in row.full_rates}                # coverage
```

Equivalent closed form (what the implementation computes): let
`d_T = T.astimezone(ECB_ZONE).date()`, `d_N = N.astimezone(ECB_ZONE).date()`.
`P` holds iff `d_T.weekday() ∈ {SAT, SUN}`, `d_N.weekday() ∈ {SAT, SUN}`,
and every date strictly between is also SAT/SUN — i.e. **T and N lie in
the same ECB weekend stretch `[Saturday 00:00 CET/CEST, Monday 00:00
CET/CEST)`**. (Walking the date range is specified rather than the closed
form; both are equivalent and the walk is self-evidently correct.)

Because the interval is CLOSED at T, a proof T on a working day is NEVER
sufficient for any N ≥ T (T's own day is in [T, N]) — this kills the
delayed-publication edge identified in §1 (a Friday 23:50 CET proof cannot
cover Saturday 00:10 CET, because a delayed Friday publication is not
excludable).

**Effect — what v1 reuses and what it does not:**

* **ECB working days (Mon–Fri, incl. TARGET closing days): NO reuse, ever.**
  Every non-USD run performs the live fetch — byte-for-byte today's
  behavior. (A TARGET closing day is indistinguishable from a working day
  to v1 and is treated as risky — conservative; the closing calendar is
  NOT needed, see §3.4.)
* **ECB weekend stretches (Sat 00:00 → Mon 00:00 CET/CEST): reuse after
  proof.** The first non-USD run of the stretch live-fetches and proves the
  (last working day's) document; every subsequent non-USD run in the
  stretch is a CACHE_HIT serving that document — which is GENUINELY the
  latest official observation (C1: nothing can be published in the
  stretch). No false freshness is possible in a reuse window: by
  construction, every reuse interval contains zero ECB working days.
* DST: handled by the zone conversion (the weekend stretch shifts with
  CET/CEST; §13 P8 pins this).
* Server/application timezone: irrelevant — T and N are stored/compared as
  aware UTC instants; the zone is applied only inside `P`.

### 3.3 Placement and shape of the contract

* `research/fx_cache_contract.py` (NEW, pure, stdlib-only — replaces the
  prior `is_same_utc_day`; no other prior function changes):
  * `no_publication_possible_between(t: datetime, n: datetime, zone) -> bool`
    — the `P` predicate; requires tz-aware inputs (naive → `TypeError`),
    `t <= n` (`t > n` → `ValueError`; both propagate as programming
    defects per the frozen discipline); `zone` is a parameter (any
    `datetime.tzinfo` — `timezone` fixed offsets in tests,
    `ZoneInfo("Europe/Brussels")` in production).
  * `fx_document_content_sha256(...)` and `project_required_rates(...)` —
    unchanged from prior §11.2.
* `execution/fx_observation_cache.py` (NEW): holds
  `ECB_CALENDAR_ZONE = ZoneInfo("Europe/Brussels")` (execution may do I/O;
  research stays import-pure — the zone OBJECT is constructed here, the
  predicate there), and the service entry points
  * `try_reuse_latest_observation(required, *, now) -> FxObservationSet | None`
    — selection + full `REUSABLE` evaluation at `now` (tz-aware UTC;
    default `timezone.now()`; tests pin it);
  * `record_live_observation(feed_id, full_set, *, now) -> None`
    — unchanged upsert from prior §11.4 (INSERT on new content; convergent
    conditional `last_proven_at` UPDATE on identical content; best-effort
    DB errors logged, never raised).
* The instant `now` is an EXPLICIT parameter (default = wall clock), not a
  hidden global: deterministic testability without new dependencies (no
  freezegun in `requirements.txt`; none needed — the repo's existing
  urlopen-mock pattern + pinned `now` covers the integration layer).

### 3.4 Calendar-knowledge question (explicitly required)

Does v1 require knowledge of the ECB publication schedule / TARGET
calendar?

* **v1: NO.** Only C1 (weekends are closure — a day-of-week fact) and C2
  (working days are risky — a blanket conservative treatment) are used.
  The ≈16:00 CET time, the 14:15 CET fixing, and the TARGET closing-day
  list are all UNNEEDED.
* **Business-day reuse (v2 candidate) WOULD require one of:**
  (i) a **deterministic calendar contract** — TARGET closing days +
  a guaranteed publication-completion time per working day — i.e. an
  **external data dependency** (a maintained, versioned calendar store or
  fetch, with its own provenance/retention decisions) PLUS acceptance of
  the same-working-day **correction residual** (a corrected document
  published after the proof but before N would be missed; the prior
  design's "latest revision wins" only helps for corrections observed in a
  live fetch); or
  (ii) accepting the 14:15-CET-fixing structural fact as a timing
  assumption (the fixing precedes any publication of that day's rate) —
  still leaves the correction residual and adds DST-aware time
  computation; or
  (iii) **deferring** business-day reuse.
* **Recommendation: (iii) — defer.** The smallest robust v1 is
  closure-only; the calendar question is a separate, larger design
  (data surface + maintenance + versioning) that v1's honesty does not
  depend on. Recorded as reviewer decision D3 (§14).

---

## 4. Working-day / pre-publication / post-publication behavior

All instants below in ECB time (CET/CEST). "Live" = canonical live fetch
(one bounded call, exactly today's provider behavior). "Prove" = insert or
convergent re-proof of the fetched content.

| Moment | Feed state | v1 behavior | Soundness basis |
|---|---|---|---|
| Working day, before ≈16:00 CET (e.g. Mon 09:00) | latest doc = previous working day's observation | LIVE (no row is reusable: any candidate's T is on a working day or an earlier working day; [T, N] contains working days) | C2 |
| Working day, after ≈16:00 CET (e.g. Mon 17:00) | latest doc = today's observation | LIVE (proof T on today's working day is never reusable for any N ≥ T) | C2 — v1 makes NO day-long claim even when the publication has visibly happened; the document's `observation_date` shows the true date |
| Working day, delayed publication (Mon doc appears Mon 20:00) | previous doc until 20:00 | LIVE at every run; the 20:30 run proves the Mon doc | no timing assumption needed; delay is invisible to the policy |
| Working day = TARGET closing day (holiday Mon) | latest doc = previous working day's observation | LIVE at every run (indistinguishable from working day; no calendar consulted) | C2 (conservative superset) |
| Working day with a correction (Thu doc corrected Fri) | two contents for `observation_date`=Thu | each live run proves the content it gets; store keeps BOTH rows (different digests, same date); LATEST_KNOWN selection (date, then `last_proven_at`) serves the most recently proven revision to any future proof-eligible window | prior §3.3/§5.3 unchanged |

**Consequence (stated plainly, per "do not optimize away network calls at
the expense of false freshness"):** on working days v1 saves NO network
calls. The one live fetch per non-USD run is exactly today's behavior. v1's
acquisition reduction is confined to weekend stretches, where it is
provably safe (C1). This is Option A of the task ("conservative
acquisition reduction without claiming day-long freshness"), reinforced by
the single sound Option B window ("reuse only where no newer official
publication can exist under an explicit deterministic rule" — the ECB
weekend, by closure, not by timing). Option C is unnecessary.

---

## 5. Weekend / TARGET closing-day behavior

* **Weekend stretch (Sat 00:00 → Mon 00:00 ECB time):** first non-USD run
  (any instant in the stretch, Saturday or Sunday) → LIVE, proves document
  D (`observation_date` = last TARGET working day, possibly Thu or Fri).
  All subsequent non-USD runs in the stretch with `P(T, N)` true (same
  stretch, T ≤ N) → **CACHE_HIT**: zero network; the run's own
  `ResearchFxSnapshot` is published with the row's original
  `retrieved_at` (immutable) and `acquisition="CACHE_HIT"`; the report
  labels "ECB reference date: D" + "rates retrieved: <T₀>" + "reused from
  cache (served <N>)". D is genuinely the latest official observation for
  the whole stretch (C1) — the reuse makes a TRUE latest-ness claim.
* **Stretch edges (pinned in §13):** a proof at Fri 23:59 ECB covers
  nothing (Fri is in [T, N] for every N ≥ T); a proof at Sat 00:00:00.000001
  ECB covers up to Mon 00:00 ECB exclusive; N exactly at Mon 00:00 ECB is
  NOT covered (Monday's day is in [T, N]) — the Monday 00:00 run is LIVE.
* **TARGET closing days adjacent to the weekend:** irrelevant to the
  predicate (no calendar consulted); the served document's
  `observation_date` simply reflects the last working day the feed
  published, whatever it is. A long closure (e.g. holiday week) changes
  nothing: weekend stretches still reuse their own proofs; working days
  still live-fetch.
* **DST transitions (last Sunday of March / October):** the stretch
  boundaries move with the zone (23:00-UTC vs 22:00-UTC edges); the
  zone-aware date walk is correct across the transition — pinned by test
  P8 (§13). No special-casing.
* **Cross-weekend gap:** a Saturday proof does NOT cover the following
  Saturday (Mon–Fri working days in [T, N] → P false) → next weekend's
  first run is LIVE again.

## 6. Correction / republishation behavior (corrected)

* Corrections occur on ECB working days (the publisher's working days).
  v1 reuse intervals contain NO working days (§3.2) → **a correction can
  never fall inside a reuse interval.** The stale-content risk that the
  prior design accepted for same-day reuse (§5.2 residual (a)) is ELIMINATED
  in v1 by construction, not by detection.
* A correction observed by a live run (working day) creates a new row
  (same `observation_date`, different `content_sha256`); the superseded
  revision remains `VALID_HISTORICAL` (audit); LATEST_KNOWN selection
  (date, then `last_proven_at`) tracks the most recently proven revision.
  Unchanged from prior §3.3/§5.3.
* A correction that lands AFTER a weekend's last reuse (e.g. Monday
  correcting Friday's doc) affects Monday onward via live fetches only;
  the weekend's CACHE_HIT runs were serving the then-latest official
  document — a true statement at every moment of the stretch.

## 7. Fail-safe where publication status cannot be proven

The predicate is fail-safe by direction: `P(T, N)` is true ONLY when
closure is certain (every ECB day in [T, N] is Sat/Sun — C1, structural).
In every case where publication status cannot be proven, `P` is false and
the system falls to the live path:

* T on a working day (publication-completion unknown) → live.
* Any working day inside [T, N] (including N's own day) → live.
* T or N naive / zone unavailable / row undecodable / invariants violated /
  coverage gap → candidate excluded or predicate refused → live.
* Live then fails (`FxProviderError`) → **today's exact behavior**: run
  completes, NO `ResearchFxSnapshot`, USD Equivalent "Unavailable"; store
  untouched (artifacts retained). (Prior §9, unchanged.)
* Programming defect anywhere in the cache path → propagates to the
  post-claim catastrophic boundary (prior §9, unchanged; only
  `IntegrityError` and `FxCodecError` are caught by name, plus DB read
  errors at the SELECT site → treated as "no candidate").

There is NO path in which the system serves a cached document while a
publication event is possible, and NO path in which "cannot be proven"
degrades to "assume fine".

## 8. Explicit canonical-feed cache eligibility contract (BLOCKER 2)

### 8.1 Answers to the six required questions

1. **Is caching enabled ONLY for the canonical production default ECB
   feed?** YES. v1 has exactly one cache-eligible acquisition: the
   canonical default ECB feed acquisition (the lazy default
   `EcbFxProvider()` against the fixed `_ECB_STATISTICS_URL`).

2. **What exact signal establishes it?** The **canonical-default
   construction event at the existing construction site**
   (`orchestration.py` L1377-1380):

   ```
   fx_cache_eligible = fx_provider is None      # BEFORE construction
   if fx_provider is None:
       fx_provider = EcbFxProvider()            # canonical default (existing line)
   ```

   Eligibility is a local boolean SET AT THE SITE WHERE THE CANONICAL
   DEFAULT IS DEFINED — a policy-as-code declaration adjacent to the
   canonical feed, not a runtime inspection of the provider object. The
   declaration is justified in code comment by the feed's publication
   contract (C1/C2) — the same contract the freshness predicate encodes.
   Both store READ and store WRITE are gated on this boolean (the store is
   defined as "written only by the canonical live acquisition", prior §4).

   Explicitly REJECTED for v1, with reasons:
   * `isinstance(resolved, EcbFxProvider)` — class identity as business
     semantics; chosen in the prior design partly to avoid touching tests
     (the disapproved rationale); subclasses/wrappers of the canonical
     class would silently enter or leave cache behavior by inheritance
     accident.
   * Configuration/env feed identity — a new deployment surface for a
     one-feed world (PLAN §18: policy belongs in the core, not caller-
     configurable); settings drift would change cache eligibility
     invisibly.
   * Provider-declared capability (Protocol attribute) — modifies the
     frozen `FxProvider` boundary contract; a test fake that copies the
     capability attribute ACCIDENTALLY enters live cache behavior (the
     exact hazard the reviewer names); capability = another form of
     provider-specific fact in business semantics.

3. **Explicitly injected providers:** the cache is **unconditionally
   bypassed** — no store read, no store write, and the acquisition call is
   byte-for-byte today's (`fetch_rates(requested_currencies=
   required_currencies)`, prior caller-projection change does NOT apply).
   Rationale: injection is an explicit declaration that "the caller owns
   this run's acquisition semantics" — any object, whether a test fake, a
   future alternate feed, a wrapper, or even a hand-constructed
   `EcbFxProvider()`, is outside the canonical-default contract the
   freshness policy relies on. This is the fail-safe direction: the ONLY
   way into cache behavior is the production default path itself.

4. **`EcbFxProvider` subclasses / wrappers:** treated as injections →
   bypassed. There is no construction path by which a subclass or wrapper
   becomes canonical: the canonical site constructs exactly
   `EcbFxProvider()`. If production ever needs a different adapter
   (e.g. a retried transport), it must be injected (bypass) OR the new
   adapter must get its OWN reviewed eligibility declaration at its OWN
   canonical construction site — a future, explicit, code-review-visible
   event, never an implicit `isinstance` match.

5. **How tests inject deterministic providers without accidentally entering
   live cache behavior:** by construction — ANY non-None `fx_provider`
   bypasses the cache. Every existing orchestration-level FX test injects
   (`_FakeFxProvider`, `_TlsFailingFxProvider`, etc.) → zero cache
   involvement, zero behavior change, zero test modification. There is no
   capability flag to copy, no env var to leak, no class to
   subclass-match, no fixture to misconfigure: the accidental-entry
   surface is exactly the existing `fx_provider is None` production
   default, which tests do not use at the orchestration level. New cache
   tests exercise the canonical path deliberately (`fx_provider=None` +
   mocked `urllib.request.urlopen` per the repo precedent in
   `tests/providers/test_fx_transport.py` L97-105 + pinned `now` + seeded
   store), and §13 I6/I7 MECHANICALLY PROVE the bypass (including an
   injected REAL `EcbFxProvider` instance: zero store interaction).

6. **How provider class identity is kept out of business semantics:** the
   freshness rule is stated over the FEED's publication contract (C1/C2),
   not over a provider type; eligibility is a DECLARATION at the canonical
   construction site (reviewed code, adjacent to the feed definition), not
   a runtime identity check; no `isinstance`/`issubclass` on the provider
   appears anywhere in the cache path (a boundary guard test asserts the
   new modules contain no class-identity check of the provider object —
   §13 G1). The `EcbFxProvider` name appears in exactly one place in
   production logic: the pre-existing default-construction line it already
   occupies.

### 8.2 Force-refresh primitive (PLAN §18 "A user must be able to force a
refresh")

`execute_research_run(..., force_fresh: bool = False)` — additive keyword,
default False, threaded into `_try_fetch_fx_rates`. Effect: the reuse
lookup is skipped for that run (live path; the live success still
re-proves the store). Web wiring is OUT of v1 scope (no UI surface); the
mechanical primitive exists so the §18 obligation has a defined hook and so
cache tests can distinguish "eligible but forced" from "eligible and
reused". Reviewer decision D4 (§14) covers whether v1 ships the parameter
at all (recommended: yes, it is one boolean) and confirms the web surface
is deferred.

## 9. Injected-provider behavior (consolidated contract)

For `fx_provider is not None` (any object):

* `_get_required_fx_currencies` runs first (unchanged; USD-only → zero
  acquisition — preserved).
* Store: zero reads, zero writes.
* Acquisition: `fetch_rates(requested_currencies=required_currencies)` —
  today's exact call (provider-side filtering, as today).
* `FxProviderError` → nonfatal, `None` payload — today's exact boundary.
* Non-`FxProviderError` → propagates — today's exact discipline.
* Publication: run's own `ResearchFxSnapshot`, `schema_version=1`,
  `acquisition="LIVE"` (default) — byte-identical row to today.
* All existing test assertions (call counts, payload contents,
  `schema_version == 1`, absence of snapshot on failure, zero-call replay)
  remain valid **because the architecture preserves the injected-
  acquisition contract**, not because of any class check.

## 10. Concurrency implications of the corrected policy

The corrected predicate CHANGES re-proof traffic but NOT the race classes:

* `record_live_observation` now runs after EVERY canonical live fetch —
  i.e. on every working-day non-USD run (v1 reuses nothing on working
  days) plus the first run of each weekend stretch. The store row for the
  current document receives a convergent `last_proven_at` update daily.
  This is the same unique-key INSERT + conditional UPDATE pattern as prior
  §8 (no locks, `IntegrityError` → re-read → converge); no new race is
  introduced. SQLite single-writer serialization already applies.
* **Soundness under concurrent re-proof:** the predicate consumes the
  LATEST stored instant T; a shorter [T, N] interval is at least as safe
  as a longer one, and the latest proof is the true verification moment —
  so concurrent convergent updates cannot create a false-true predicate.
* **Weekend concurrency is a content-no-op:** inside a weekend stretch no
  publication is possible (C1), so any concurrent live fetch (e.g. a
  `force_fresh` run racing reuse runs) returns the SAME content; its
  re-proof changes `last_proven_at` only. A reuse run reading the row
  before or after the re-proof serves identical rates — no torn or
  inconsistent outcome. (Under the prior date-based rule this argument
  would need "same UTC day"; the closure rule is strictly stronger here.)
* Cross-day races (Sunday 23:50 reuse run vs Monday 00:05 live run): the
  predicate evaluates each run's own `now`; the Sunday run reuses (its N
  is in the stretch), the Monday run lives (its N is on Monday) — both
  correct, no coordination needed.
* Crash/recovery: unchanged from prior §8 (crash after fetch → no row yet
  → next eligible run live-fetches; cache write failure → run still
  publishes live evidence; run publication failure → store row retained,
  it is feed data, not run data).

## 11. `ResearchFxSnapshot.acquisition` — still recommended

YES, unchanged from prior §7.2. The two blockers do not touch the
provenance carrier:

* The corrected policy makes the label MORE necessary, not less: a v1
  CACHE_HIT can only occur on a weekend stretch, precisely when the
  served `observation_date` differs from "today" and the user most needs
  to see (a) the true reference date, (b) the original retrieval instant,
  (c) that this run reused rather than fetched. The `acquisition`
  column + display line is the honesty mechanism.
* The carrier decision logic stands: additive model column (one migration
  operation), default `"LIVE"` (historically true for every existing row),
  no frozen-codec change, no evidence-vocabulary change, no existing test
  breakage; REPLAY remains a read-path property (never stored).
* Immutability contract reaffirmed: on CACHE_HIT the V1 payload's
  `retrieved_at` is the ORIGINAL provider retrieval instant from the store
  row — never the serving time, never re-stamped. CACHE_HIT must not
  masquerade as LIVE: the column makes that mechanically impossible for
  any consumer that reads it, and the display renders it.

## 12. Final proposed smallest implementation slice (corrected)

`PRODUCT-INTEL.8A-FX` — "ECB FX observation store: closure-window reuse of
the full daily document" — same shape as prior §11 with exactly these
corrections:

1. **Store model** (`runs/`, prior §11.1): UNCHANGED — `FxObservationStore`
   with `last_proven_at` as a full aware-UTC **instant**; the documented
   meaning is now "last canonical live verification of this content at
   this instant (PROVEN_LATEST_AS_OF_T)" and the documented consumption
   rule is "never truncate to a date for freshness".
2. **Pure contracts** (`research/fx_cache_contract.py`): prior §11.2 with
   `is_same_utc_day` REPLACED by `no_publication_possible_between(t, n,
   zone)` (§3.3); digest + projection unchanged.
3. **Feed identity** (`providers/fx.py`): prior §11.3 unchanged (additive
   `FX_FEED_ID_ECB_DAILY` constant + mirror-lock test).
4. **Cache service** (`execution/fx_observation_cache.py`): prior §11.4
   plus `ECB_CALENDAR_ZONE = ZoneInfo("Europe/Brussels")`; both entry
   points take explicit `now` (§3.3).
5. **Orchestration** (`execution/orchestration.py::_try_fetch_fx_rates`):
   prior §11.5 with the gate REPLACED:
   ```
   required = _get_required_fx_currencies(...)        # UNCHANGED, first
   if not required: return None                        # UNCHANGED gate
   fx_cache_eligible = fx_provider is None             # NEW declaration
   if fx_provider is None: fx_provider = EcbFxProvider()  # EXISTING line
   if fx_cache_eligible and not force_fresh:
       hit = try_reuse_latest_observation(required, now=...)
       if hit: -> encode V1 (original retrieved_at) -> (payload, "CACHE_HIT")
   if fx_cache_eligible:
       full = fx_provider.fetch_rates(requested_currencies=None)
       binding check; record_live_observation(feed_id, full, now=...)
       projected = project_required_rates(full, required)
   else:
       projected-set = fx_provider.fetch_rates(
           requested_currencies=required)              # TODAY'S exact call
   encode V1 -> (payload, "LIVE")                       # UNCHANGED publish
   ```
   FxProviderError boundary and programming-defect propagation: UNCHANGED.
   `execute_research_run` gains `force_fresh: bool = False` (D4) and
   threads it; the publication call gains `acquisition=...` (D7).
6. **Model column + migration** (prior §11.6): UNCHANGED (one additive
   column, one new migration 0011 with two operations).
7. **Display** (prior §11.7): UNCHANGED (reference date + retrieved
   instant + acquisition label; both replay branches; zero-live GET
   preserved — the store is read only during execution of a claimed run).
8. **Exclusions** (prior §11.9): UNCHANGED, plus now explicit: **no
   business-day reuse in v1** (§4), no TARGET-calendar data, no
   publication-time assumption.

## 13. Exact test cases required for the temporal boundary cases

New nodes only; NO existing test modified. `zone` in unit tests = pinned
fixed offsets (`timezone(timedelta(hours=1))` for CET, `hours=2` for
CEST); integration tests pin `now` and seed `last_proven_at` explicitly.
Winter = CET, Summer = CEST. All predicate tests are pure and run on any
day of the week (deterministic by construction — no `skip`/conditional
logic).

**A. Pure predicate (`no_publication_possible_between`), pinned instants:**

* P1 same weekend day: T = Sat 2026-01-10 09:00+01, N = Sat 12:00+01 → True.
* P2 Saturday→Sunday: T = Sat 09:00+01, N = Sun 18:00+01 → True.
* P3 weekend→Monday edge: T = Sat 09:00+01, N = Mon 2026-01-12 00:00:00+01
  → False (N's ECB day is Monday); N = Sun 23:59:59.999999+01 → True.
* P4 Friday→Saturday edge: T = Fri 23:59+01, N = Sat 00:01+01 → False
  (T's ECB day is Friday — delayed-Friday-publication edge).
* P5 working-day proof never reuses (documents the v1 conservatism):
  T = Fri 16:30+01 (post-publication), N = Sat 09:00+01 → False;
  T = Mon 17:00+01 (post-publication, doc observation_date = Mon),
  N = Mon 23:00+01 → False.
* P6 Sunday within Sunday: T = Sun 23:00+01, N = Sun 23:59+01 → True.
* P7 Sunday→Monday: T = Sun 23:30+01, N = Mon 00:30+01 → False.
* P8 DST transition (summer, CEST): T = Sat 2026-03-28 09:00+02,
  N = Sun 2026-03-29 23:59+02 → True (UTC instants: 07:00Z → next-day
  21:59Z; the zone-date walk sees Sat+Sun only); and the winter analog
  with +01 → True. (Proves no UTC-day shortcut is used.)
* P9 gap of a working week: T = Sat 09:00+01, N = next Sat 09:00+01 →
  False (Mon–Fri in [T, N]).
* P10 proof instant == use instant: T = N = Sat 09:00+01 → True.
* P11 contract violations: T > N → ValueError; naive T or N → TypeError
  (both propagate as programming defects — a node asserting they RAISE,
  per frozen discipline).
* P12 TARGET-closing-day independence: T = Sat 2026-12-26 09:00+01,
  N = Sun 2026-12-27 18:00+01 (Mon 2026-12-28 is a known TARGET closing
  day) → True — identical evaluation to a non-holiday weekend; asserts the
  predicate references NO calendar data (same result with any Monday's
  status).
* P13 UTC-weekend vs ECB-weekend divergence (the §1 secondary flaw is
  closed): T = Fri 2026-01-09 23:30+00 (= Sat 00:30+01 ECB), N = Sat
  08:00+00 (= Sat 09:00+01) → **False** (T's ECB day is Friday) — a
  UTC-day rule would have said True.

**B. Integration (canonical path: `fx_provider=None` + mocked
`urllib.request.urlopen` + seeded store + pinned `now`; urlopen armed
fail-fast where zero-network is asserted):**

* I1 working day, empty store: one urlopen; row inserted
  (`original_retrieved_at == last_proven_at == fetch instant`); snapshot
  `acquisition="LIVE"`; payload byte-identical to today's filtered fetch
  (compare against `fetch_rates(required)` output for the same mocked
  document — projection equivalence).
* I2 weekend reuse: row proven Sat 09:00 (doc observation_date = Fri, the
  last working day); `now` = Sun 10:00; urlopen armed → **zero** urlopen;
  CACHE_HIT; snapshot payload `retrieved_at` == row's ORIGINAL (not the
  serving time); `acquisition="CACHE_HIT"`; USD equivalent equals the
  live-computed value for the same document.
* I3 working day after weekend proof: same row; `now` = Mon 09:00 →
  urlopen called once; row RE-PROVEN (`last_proven_at` = Mon instant,
  `original_retrieved_at` UNCHANGED, payload UNCHANGED); snapshot LIVE.
* I4 Friday proof, Saturday use: row proven Fri 17:00; `now` = Sat 09:00
  → live (documents P4/P5 conservatism end-to-end).
* I5 `force_fresh=True` on a reusable weekend state → live + re-proof +
  LIVE snapshot (reuse skipped).
* I6 **injected fake bypass (Blocker 2 core):** valid reusable weekend row
  exists; `fx_provider=_FakeFxProvider()` injected; `now` = Sunday →
  provider called with `requested_currencies` (today's exact call — assert
  the argument), ZERO store reads/writes (sentinel: store service patched
  to raise if touched), snapshot byte-identical to today's (payload +
  `schema_version == 1` + `acquisition="LIVE"`).
* I7 **injected real adapter bypass (class-identity is not semantics):**
  `fx_provider=EcbFxProvider()` constructed explicitly (urlopen mocked);
  valid reusable weekend row; `now` = Sunday → urlopen called (live),
  ZERO store interaction. (If `isinstance` gating had survived, this test
  would fail — it mechanically kills the prior design's gate.)
* I8 corrupted latest candidate (payload tampered) + otherwise reusable
  weekend state → candidate excluded (loud bounded log; row NOT deleted),
  live path taken, LIVE snapshot.
* I9 coverage gap: stored full set lacks a required currency + reusable
  state → live path.
* I10 weekend concurrent re-proof: seed row; two threads at the same
  pinned weekend `now` (one force_fresh, one normal) → one row;
  `original_retrieved_at` unchanged; both runs publish their own
  snapshots; no IntegrityError escapes.
* I11 REPLAY of a CACHE_HIT run: armed fail-fast Search/Page/Vendor/ECB/
  semantic/urlopen + store-service sentinel; replay renders the label;
  zero live, zero cache reads (prior `test_full_replay_entry_point_zero_
  live_boundaries` pattern, extended).
* I12 USD-only run on a reusable weekend state → zero urlopen AND zero
  store reads (the discovery gate precedes the lookup).

**C. Guard/authority (Blocker preservation proofs):**

* G1 AST boundary: `execution/fx_observation_cache.py`,
  `research/fx_cache_contract.py`, and the modified
  `orchestration.py` FX block contain NO `isinstance`/`issubclass` whose
  argument is a provider object (class identity is not business
  semantics); research module remains stdlib-only (existing guard suite
  auto-covers the new file).
* G2 authority invariance under cache: Machine Price snapshot bytes
  identical across LIVE / CACHE_HIT / FX-absent (non-USD fixture);
  compact-quote `usd_equivalent` identical LIVE vs CACHE_HIT (same
  document); vendor/semantic/human-review/HARD_CONFLICT fixtures
  re-proven (existing suites unmodified and green — the primary proof).
* G3 existing FX suites UNMODIFIED and green: `test_fx_codec`,
  `test_fx_math`, `test_fx_provider`, `test_fx_transport`,
  `test_fx_currency_discovery`, `test_fx_execution_integration`,
  `test_fx_tls_production_chain` (the TLS-failure node injects a failing
  provider → bypassed cache → "no snapshot on failure" holds exactly as
  frozen).

## 14. Remaining reviewer decisions

* **D1 — v1 closure-only policy:** confirm no business-day reuse in v1
  (working-day network behavior = today, byte-for-byte); acquisition
  reduction confined to ECB weekend stretches, where the served document
  is genuinely the latest official observation.
* **D2 — ECB calendar zone constant:** confirm `Europe/Brussels` as the
  publication-contract zone (CET/CEST; the zone of the stated ≈16:00 CET
  update), applied only inside the predicate; storage and comparison stay
  UTC.
* **D3 — business-day reuse (deferred):** record that v2 options are
  (i) deterministic TARGET-closing-day + publication-completion calendar
  contract (external data dependency, versioned, with its own
  provenance/retention design), (ii) 14:15-CET-fixing timing assumption +
  accepted same-day correction residual, (iii) remain closure-only.
  Recommendation: (iii) until a reviewer picks (i)/(ii) with the
  correction residual explicitly accepted.
* **D4 — `force_fresh` primitive:** confirm the additive
  `execute_research_run(force_fresh: bool = False)` parameter ships in v1
  (mechanical §18 hook; NOT wired to any web surface in v1); confirm the
  user-facing refresh surface is a separate later decision (8A-PRE §7.6
  candidate (b)).
* **D5 — explicit `now` parameter seam** on the cache service entries
  (default `timezone.now()`; tests pin it): confirm (no new dependency;
  no freezegun in `requirements.txt`).
* **D6 — eligibility declaration** at the canonical construction site
  (`fx_provider is None` → boolean set there; injection = unconditional
  bypass; no isinstance/config/capability): confirm; this REPLACES prior
  decision 5.
* **D7 — `ResearchFxSnapshot.acquisition` column:** reconfirm (still
  recommended; §11).
* **D8 — documentation governance drift (carried, still open):** STATUS.md
  (phase-ownership table) and PLAN roadmap still list 8A-PRE as "PLANNED
  (next delivery)" while 8A-PRE is complete (audit delivered) and this
  design lineage (8A-FX-DESIGN → FU1) exists uncommitted. Docs-only
  STATUS/PLAN update (8A-PRE complete; 8A-FX-DESIGN + FU1 state; AD entry)
  belongs to the approval/implementation step — flagged, not silently
  resolved in this read-only phase.
* **D9 — naming:** `FxObservationStore`, `no_publication_possible_between`,
  `FX_FEED_ID_ECB_DAILY`, `ECB_CALENDAR_ZONE`, `force_fresh` — confirm or
  rename.

---

## 15. Git governance evidence (this design phase)

Collected at completion (live command output in §15.1):

* `git rev-parse HEAD` → **`55d1879a03da3dc6163a28c9524b5ef0396b76b3`**
  (authoritative starting SHA — unchanged).
* `git status --short` → untracked ONLY: pre-existing evaluation
  artifacts (`b2_b3_full.txt`, `b2_b3_full_junit.xml`,
  `nemotron_full_evaluation.json`, `nemotron_full_manifest.json`,
  `nemotron_full_responses.jsonl`, `qwen38_run1_responses.jsonl`,
  `qwen38_run2_responses.jsonl`), the 8A-PRE audit, the prior
  8A-FX-DESIGN document, and THIS FU1 document (newly written, untracked,
  NOT committed). (`tmp_collection.txt` is a tracked, unmodified file —
  absent from `git status` and from both diffs; not part of this phase.)
* `git diff --stat` → **empty** (zero tracked-file changes).
* `git diff --name-status` → **empty**.

Explicit confirmations:

* No production changes: **CONFIRMED** (zero tracked-file edits).
* No test changes / deletions / renames: **CONFIRMED**.
* No skip / xfail / deselect changes: **CONFIRMED** (no test run
  performed or needed; frozen 5633-node baseline intact).
* No migration / model changes: **CONFIRMED**.
* No implementation: **CONFIRMED** (design only; §12 is proposed, not
  built).
* No commit / push / deploy: **CONFIRMED**.
* No arbitrary numeric TTL chosen: **CONFIRMED** — the v1 policy contains
  no duration constant; the only temporal boundary is the ECB
  publication contract's working-day/weekend structure (C1/C2), applied
  to proof instants.

**Corrected design delivered. STOP — no implementation performed, none
authorized.**

### 15.1 Live command output

```
$ git rev-parse HEAD
55d1879a03da3dc6163a28c9524b5ef0396b76b3
$ git status --short
?? b2_b3_full.txt
?? b2_b3_full_junit.xml
?? docs/PRODUCT_INTEL_8A_FX_DESIGN.md
?? docs/PRODUCT_INTEL_8A_FX_DESIGN_FU1.md
?? docs/PRODUCT_INTEL_8A_PRE_CACHING_FRESHNESS_AUDIT.md
?? nemotron_full_evaluation.json
?? nemotron_full_manifest.json
?? nemotron_full_responses.jsonl
?? qwen38_run1_responses.jsonl
?? qwen38_run2_responses.jsonl
$ git diff --stat
(empty)
$ git diff --name-status
(empty)
```
