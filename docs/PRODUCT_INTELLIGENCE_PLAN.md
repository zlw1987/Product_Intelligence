# Product Intelligence — Canonical Architecture and Roadmap

This is the canonical long-form design document for Product Intelligence.
Read it before implementing anything.

**Status labels used throughout this document**

| Label | Meaning |
| --- | --- |
| `IMPLEMENTED` | Exists in the repository today and is exercised by tests or checks. |
| `APPROVED / PLANNED` | Agreed direction, scheduled in the roadmap, not built yet. |
| `DEFERRED` | Explicitly not being built until a phase demonstrates a concrete need. |
| `UNDECIDED` | Open question. Do not silently pick an answer; raise it. |

Nothing in this document describes future functionality as if it already
works. If you find such a claim, it is a bug in the document — fix it.

---

## 1. Product mission

Given a manufacturer part number (MPN) and a product description, Product
Intelligence researches observable market pricing, identifies comparable
products, preserves the evidence behind both, and presents the result as a
browser-based report.

The value of the product is **defensible answers**, not fast answers. A price
range the user cannot trace back to real listings is worse than no answer.

Status: `APPROVED / PLANNED` — the mission is agreed; none of the research
capability is built.

## 2. Problem statement

Pricing and sourcing decisions are currently made by a person manually
searching the web for a part number, eyeballing a handful of listings, and
forming an unrecorded judgement. That process is slow, inconsistent between
people, impossible to audit afterwards, and produces no reusable record.

The specific difficulties the system must respect:

* **Part numbers are unforgiving.** `ABC1234-A` and `ABC1234-B` may be
  different products at different prices. Near-matches are a trap.
* **Listings are noisy.** Accessories, lots, refurbished units, wrong
  quantities, and unrelated products all surface for the same query.
* **Descriptions are ambiguous.** Free-text descriptions from an order line
  are abbreviated, inconsistent, and sometimes wrong.
* **Confident wrong answers are expensive.** A fabricated match that looks
  authoritative causes worse decisions than an explicit "unknown".

Status: `IMPLEMENTED` as a shared understanding recorded here.

## 3. Scope

Product Intelligence is an independent web application that:

1. Accepts an MPN plus a product description from any of several intake
   mechanisms.
2. Resolves, as far as the evidence allows, what product that identifies.
3. Researches observable market pricing from public listings.
4. Finds and assesses comparable products.
5. Preserves the evidence behind every conclusion, including rejected
   evidence and the reason for rejection.
6. Presents a durable report addressable by URL in a browser.

The application is a product in its own right. It is usable by a person with
a browser and no other system involved.

Status: `APPROVED / PLANNED`.

## 4. Non-goals

Product Intelligence is **not**:

* an ERP module, an extension of any order-entry system, or a component that
  requires one to function;
* a procurement, quoting, or purchasing system;
* a real-time price feed or a guarantee of current market price;
* an authoritative catalog or a system of record for product data;
* a general-purpose chat assistant;
* a system that guesses when it does not know.

Status: `IMPLEMENTED` as a binding constraint on all later phases.

## 5. System architecture

```text
Standalone Web UI ─────────┐
                           │
Legacy desktop launcher ───┤
                           │
Structured REST/API ───────┼──> Intake Layer
                           │
Future ERP launcher ───────┤
                           │
Other future clients ──────┘
                                  │
                                  v
                        Canonical Research Request
                                  │
                                  v
                       Product Intelligence Core
                                  │
              ┌───────────────────┼────────────────────┐
              │                   │                    │
              v                   v                    v
       Product Resolver     Price Intelligence    Comparable Research
              │                   │                    │
              └───────────────────┼────────────────────┘
                                  v
                             Evidence Store
                                  │
                                  v
                              Web Report
```

Layer responsibilities:

| Layer | Owns | Must not know about |
| --- | --- | --- |
| Intake | Transports, URL parameters, encodings, defensive parsing, caller metadata, redirects | Research logic |
| Core (`research/`) | Orchestration, resolution, pricing, comparables, evidence decisions | Callers, vendors, transports |
| Domain (`domain/`) | Contracts and controlled vocabularies | Callers, vendors, transports, frameworks, I/O |
| Providers (`providers/`) | Vendor adapters, credentials, vendor payload shapes | Business rules |
| Web report | Presentation of a completed or in-progress run | Which caller started the run |

The **caller is only an intake mechanism**. No business rule may branch on
which client produced a request.

Repository layout:

```text
/
├── CLAUDE.md                          durable operating instructions
├── README.md                          developer orientation
├── docs/PRODUCT_INTELLIGENCE_PLAN.md  this document
├── manage.py                          Django entry point
├── config/                            Django project configuration
├── evaluation/                        benchmark data + its README (0B)
│   └── corpus/                        real_verified.json, synthetic.json
├── product_intelligence/
│   ├── domain/                        contracts + vocabularies (0A)
│   ├── evaluation/                    corpus contracts, validation, loader (0B)
│   ├── runs/                          persisted run lifecycle + migration (1A)
│   ├── research/                      research core (not implemented)
│   ├── providers/                     provider boundaries (not implemented)
│   └── web/                           intake + presentation (not implemented)
└── tests/                             focused deterministic tests
```

The evaluation corpus sits outside the Python package deliberately: it is
reviewable reference data, not application code and not runtime state. Only its
loader and validation live in the package, so later phases can import them.

`runs/` is the persistence layer, and it is deliberately a fourth box rather
than a file inside an existing one (AD-025). It is the only package containing
a Django model:

| Layer | Owns | Must not know about |
| --- | --- | --- |
| `runs/` | The durable `ResearchRun` record, its lifecycle, its migration | Callers, vendors, transports, research results |

Status: `IMPLEMENTED` for the layout, the domain layer, the evaluation corpus
layer, the run-persistence layer, and the Django project skeleton.
`APPROVED / PLANNED` for every box below "Canonical Research Request" in the
diagram — a run records *that* research was requested and how it ended; nothing
performs any.

## 6. Multi-interface intake design

All intake mechanisms normalize into the same `ResearchRequest` before the
core sees anything. Planned mechanisms:

| Mechanism | Shape | Phase |
| --- | --- | --- |
| Standalone web form | HTML form POST | 1B |
| Structured API | `POST /api/v1/research` with a structured body | 5A |
| Constrained launcher | `GET /research/new?mpn=<encoded>&description=<encoded>` | 5B |
| Batch | not designed | `UNDECIDED` |

Capability levels are progressive: a capable client uses the structured API, a
constrained client percent-encodes its two values and opens the GET entry point
in a browser, and both end up at the same canonical request. Adding a client
means adding an adapter at the intake boundary — never a change to the core.

Encoding is the constrained client's own responsibility, and §7.2 explains why:
a query string cannot carry arbitrary unencoded text losslessly, so no intake
implementation may be specified as though it could.

Caller metadata (which client, which user, which order line) is an
**intake-boundary** concern. It may be recorded alongside a run for audit
purposes in a later phase, but it is never part of product identity and never
reaches resolution, pricing, or comparison logic.

Status: `APPROVED / PLANNED`. No intake mechanism is implemented.

## 7. Legacy desktop client compatibility strategy

The current production sales-order system runs on Microsoft Visual FoxPro 5.0
(1996). It is treated as a **highly constrained legacy client**, and it sets
the floor for what the intake boundary must tolerate.

Do **not** assume Visual FoxPro 5 has usable support for:

* modern REST clients
* JSON
* OAuth
* modern TLS libraries
* modern HTTP libraries
* sophisticated Unicode handling
* modern JavaScript or browser integration

**Its only required role is: build a URL and open the default browser.**

The minimum viable integration is conceptually:

```text
/research/new?mpn=ABC123&description=PRODUCT_DESCRIPTION
```

followed by the operating system opening that URL in the user's browser. The
server responds with the research page, or redirects to a report URL.

### 7.1 What the legacy client must be able to do

Exactly three things:

```text
string construction
    + a minimal percent-encoding helper we write
    + browser launch
```

A future phase (5B) may ship a small compatibility helper conceptually similar
to:

```text
UrlEncodeLegacy(value)
```

percent-encoding a query-parameter value sufficiently for a browser GET
launcher. It is a few dozen lines of FoxPro string work over a character
table — not an HTTP client. **It is not implemented in this phase.**

### 7.2 Arbitrary unencoded text is not a lossless transport

An earlier draft of this document promised that the web layer would tolerate
arbitrary plain, unencoded parameter values — including `&`, `#`, `%`, `?`,
`=`, `+`, quotes and non-ASCII bytes — without silent corruption. **That
promise was impossible and has been withdrawn.**

```text
/research/new?mpn=ABC&description=SSD & NVMe # New
```

* `&` begins another query parameter, so the description splits into fragments
  that were never distinguishable as one value;
* `#` begins a fragment identifier, which a browser normally does not send to
  the server at all — those bytes never arrive;
* `%`, `+`, `?` and `=` are reserved and may be reinterpreted before Django
  sees the request.

No server-side parsing can reconstruct information the browser or the URL
parser already discarded or reinterpreted. Claiming otherwise would be a
correctness bug in the architecture, not a robustness feature.

### 7.3 The capability hierarchy, in order of reliability

| Level | Mechanism | Guarantee |
| --- | --- | --- |
| Preferred | `POST /api/v1/research` with structured data (5A) | Lossless; for clients that can do it |
| **Reliable legacy** | Percent-encode with the minimal helper, then launch the browser (5B) | Lossless for the values the helper encodes |
| Last resort | Raw, unencoded query values | **Best-effort only**, for URL-safe characters; no guarantee |

The last-resort path exists so a hand-typed or crudely built URL still works
when it happens to contain nothing reserved. It is explicitly not a supported
contract for arbitrary text, and 5B must not be designed as though it were.

### 7.4 Remaining binding consequences

* **GET must be enough.** No POST body, no custom headers, no cookies, no
  content negotiation may be required.
* **No secrets in the client, ever.** Search API keys, LLM keys, tokens, and
  credentials live in the server environment. The launcher is not an AI
  client, and no key is ever embedded in a legacy application, a URL, or a
  desktop configuration file.
* **No result parsing in the client.** The launcher does not read, parse, or
  render results. The browser does. A client that cannot parse JSON is never
  asked to.
* **Long descriptions must degrade gracefully.** URL length limits are a real
  constraint; truncation policy is `UNDECIDED` and must be decided in 5B.
* **TLS is a deployment question, not a core question.** If the legacy client
  cannot negotiate modern TLS for the initial launch, that is solved at
  deployment (for example, an internally reachable endpoint), not by weakening
  the application.

None of this reaches the core. The core sees an MPN and a description.

Status: `APPROVED / PLANNED` as a constraint. No launcher code, no encoding
helper, and no FoxPro-side code of any kind exists in this repository. Phase 5B
implements the server-side GET entry point and may ship the encoding helper
described in §7.1.

## 8. Standalone web interface strategy

A person must be able to open Product Intelligence in a browser, type an MPN
and a description into a form, and start research — with no ERP, no legacy
client, and no integration of any kind present.

This standalone page is simultaneously:

* a real, supported, first-class user interface;
* the integration-independent fallback if any client is unavailable;
* the development and testing interface used throughout the roadmap.

Binding rule: **ERP integration must never be required for the core
application to function.** If a change would make the standalone path depend
on an integration, the change is wrong.

Planned flow:

```text
Open Product Intelligence
        ↓
Enter MPN + Description
        ↓
Start Research
        ↓
Browser report
```

Status: `APPROVED / PLANNED`, phase 1B. Not implemented.

## 9. Future ERP integration strategy

A future ERP (SAP is the expected successor to the current system) will
integrate the same way any other client does: as an intake mechanism.

```text
ERP
 ↓
same Product Intelligence intake boundary
 ↓
same core engine and browser report
```

Because the core accepts only an MPN and a description, replacing the legacy
launcher with an ERP launcher means writing one adapter at the intake
boundary. Resolution, pricing, comparison, evidence handling, and reporting
are untouched. The application must survive that replacement without a
redesign — that is the test of whether the boundary is real.

The same rule about secrets applies: an ERP client is a launcher, not an AI
client, and holds no provider credentials.

Status: `APPROVED / PLANNED` as an architectural constraint. No ERP-specific
code exists. Not scheduled before the phases marked "Future".

## 10. Core domain concepts

Defined in `product_intelligence/domain/`, standard library only.

**`ResearchRequest`** — the canonical input. Two fields:
`manufacturer_part_number` and `description`. Surrounding whitespace is
stripped; at least one field must be non-empty; the interior of a value is
never rewritten. It carries no caller, transport, or audit fields, and the
core cannot tell which intake produced it.

**`ProductIdentity`** — what the system believes the product is:
manufacturer, part number, normalized part number, product name, family,
category, plus `match_type` and `confidence`. Every descriptive field is
optional and defaults to absent. An unknown manufacturer stays unknown.

One structural invariant (AD-019): an identity may not claim a
part-number-level match it has no part number for. `EXACT` requires a
`manufacturer_part_number`; `NORMALIZED_EXACT` requires that plus the
`normalized_part_number` that distinguishes it from `EXACT`. Weaker match
types are unconstrained. This is a rule about what the type may *represent* —
no comparison, normalization, or match decision happens in the domain.

**`EvidenceReference`** — one attributable observation: source, source URL,
retrieval timestamp, raw content reference, normalized value, accept/reject
decision, reason, and confidence. Rejected evidence must carry a reason.
Timestamps must be timezone-aware and are always supplied by the caller, never
generated inside the domain.

**Vocabularies** — `IdentityMatchType`, `ConfidenceLevel`,
`VerificationStatus`, `EvidenceDecision`, `ResearchRunState`.

Status: `IMPLEMENTED` — as contracts with contract-level validation only. The
only consumer is the persistence layer (§15), which stores a `ResearchRequest`
and rebuilds one; nothing researches anything.

Deliberately **not** modelled yet: listings, price aggregates, comparable
products, specifications. Building the full schema before the behaviour exists
would guess wrong. `ResearchRun` is now modelled — as a lifecycle record only
(§15), not as a container of results that do not exist.

## 11. Evidence model principles

1. **Every reported fact is attributable.** A market price or product fact
   the report shows must trace to preserved evidence.
2. **Rejected evidence is retained, with its reason.** What was excluded and
   why is part of the answer. "We found 40 listings and used 6" is only
   credible if the other 34 are inspectable.
3. **Raw and normalized values are both kept.** Normalization must be
   reviewable against what was actually observed.
4. **Retrieval time is recorded.** Prices are observations at a moment, not
   standing truths.
5. **No conclusion without support.** The system must not present a precise
   market price derived from nothing. Insufficient evidence produces
   `UNVERIFIED` or `UNKNOWN`, not a number.

Status: `APPROVED / PLANNED` as principles; `IMPLEMENTED` only as the
`EvidenceReference` contract. There is no evidence store.

## 12. Deterministic vs LLM responsibilities

**Deterministic application code owns**, and remains solely authoritative
for:

* exact part-number matching
* normalized part-number matching
* all arithmetic
* price aggregation, median / min / max
* unit-price calculation
* currency handling
* deduplication mechanics
* thresholds
* validation
* timestamps
* database persistence

**An LLM may later assist with** semantic work only:

* interpreting ambiguous product descriptions
* product-category classification
* specification extraction
* search-query generation
* explaining differences between compared products
* summarizing already-verified results

**The binding rule:** an LLM is never the sole authority for exact product
identity, and never produces a number that the report presents as fact. LLM
output that affects a conclusion must be checkable against deterministic
rules or evidence.

Status: `APPROVED / PLANNED` as the responsibility split. No LLM is
integrated. No prompts exist.

## 13. Search-provider boundary

A `SearchProvider` abstraction will sit between the research core and any
external search or listing source.

* Business logic depends on the boundary, never on a vendor.
* Vendor names, payload shapes, rate limits, retries, and credentials stay
  inside the adapter.
* Provider results are converted into internal types at the adapter edge; no
  vendor-shaped data reaches the domain or the core.
* Credentials come from the server environment only.

Vendor selection is `UNDECIDED`. One provider will be integrated first
(phase 2C); multiple simultaneous providers are `DEFERRED` until a phase
shows a concrete need.

Status: `APPROVED / PLANNED` (2B), with `IMPLEMENTED` boundary rules recorded
in `product_intelligence/providers/__init__.py`. No provider exists.

## 14. LLM-provider boundary

An `LLMProvider` abstraction will sit between the research core and any model
vendor, with the same rules as the search boundary: no vendor names in
business logic, credentials from the server environment, and adapter-edge
conversion into internal types.

Additional constraints specific to LLM use:

* Every LLM-assisted step declares which of the semantic responsibilities in
  §12 it is performing.
* LLM output is treated as a *proposal* subject to deterministic checking,
  not as a result.
* An LLM failure or timeout degrades the run to a partial result. It never
  fabricates one.

Vendor selection is `UNDECIDED`. Model orchestration across several models is
`DEFERRED`.

Status: `APPROVED / PLANNED`. Not scheduled before the specification and
comparable phases (6A onward). No LLM code exists.

## 15. Research-run lifecycle

A research attempt is a first-class record with its own identity, so that a
report is durable, addressable, and re-openable. Phase 1A built exactly that
record and nothing more: it persists *that* research was requested and how the
attempt ended. It performs no research.

### 15.1 Where it lives

`product_intelligence/runs/` — a small Django application whose only model is
`ResearchRun` (AD-025). The reasoning is the layer table in §5:

* `domain/` is stdlib-only contracts, and a model there would break both the
  rule and the guard test that enforces it;
* `research/` is the caller-independent engine and stays free of persistence,
  so it can be reasoned about and tested without a database;
* `web/` is transport and presentation. A run outlives the request that created
  it and belongs to no caller, so the lifecycle is not the web layer's to own.

The dependency runs one way: `runs` imports `domain`, never the reverse.

### 15.2 What is persisted

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | UUID, primary key | Opaque durable identifier |
| `manufacturer_part_number` | text, may be empty | Canonical MPN from the request |
| `description` | text, may be empty | Canonical description from the request |
| `state` | text, from `ResearchRunState` | Lifecycle state |
| `created_at` | timestamp | When the run was recorded |
| `started_at` | timestamp or absent | When it began |
| `finished_at` | timestamp or absent | When it reached a terminal state |

Both text fields hold exactly what `ResearchRequest` produced — surrounding
whitespace already stripped, interior untouched — and neither carries a length
limit, because the canonical contract imposes none and persistence must not
invent a rule the contract has not agreed to. A truncation policy remains a 5B
question, where URL length limits actually bite.

A run is always first stored in `CREATED`; the state/timestamp shape of every
stored row is a database constraint (§15.5, AD-030).

There are **no caller fields**: no calling application, no order number, no
customer, no user, no transport metadata, and no provider. A persisted record is
precisely where caller-independence would quietly stop being true — one
"just for audit" column at a time — so a guard test asserts the complete field
list.

A run is created from a `ResearchRequest` and can rebuild one, so later phases
consume the contract rather than the database row.

### 15.3 Identity

The primary key is a random (version 4) UUID generated by the application. One
identifier serves both the database and the planned report URL: a second
"public id" alongside a sequential key would buy nothing the UUID does not
already provide, and two identifiers means keeping two things consistent. It is
assigned at construction and never rewritten, so `/research/<id>` stays valid
for the life of the record.

**UUID opacity is not access control.** An unguessable identifier resists
casual enumeration; it authenticates nobody, authorizes nothing, and does not
stop a leaked or shared URL from working for whoever holds it. Report
visibility and authentication remain `UNDECIDED` (§19). Nothing in 1A settled
them.

### 15.4 States and transitions

The vocabulary is the existing `ResearchRunState`; the persisted choices are
*generated* from it, so a second, drifting list of states cannot come into
existence.

| From | May become |
| --- | --- |
| `CREATED` | `RUNNING` |
| `RUNNING` | `COMPLETED`, `PARTIALLY_COMPLETED`, `FAILED` |
| `COMPLETED` | — |
| `PARTIALLY_COMPLETED` | — |
| `FAILED` | — |

`PARTIALLY_COMPLETED` is deliberate: a run that found pricing but no
comparables is a useful, honest result and must be representable.

Terminal means terminal. There is no retry, reopen, or resume — a re-run is a
new run, and inventing reopen semantics now would answer a question no phase
has asked.

One method, `transition_to(target_state, at=None)`, is the supported way to
move. An illegal move raises `InvalidResearchRunTransition` and changes
nothing — not the state, not a timestamp, not the row. Nothing is coerced to a
"closest legal" state, because a caller that believes a run progressed when it
did not is the same fabricated certainty the rest of the system forbids
(AD-009). Assigning `state` on a saved run and calling `save()` raises
`UnsupportedResearchRunStateChange`, so the rule is enforced rather than merely
documented (AD-014).

A run is also created only in `CREATED`: persisting one directly in `RUNNING`
or a terminal state raises `InvalidInitialResearchRunState`, and a run that has
never been stored cannot transition at all. A lifecycle that can be entered
halfway is not a lifecycle (AD-030).

### 15.5 Timestamps

| State | `created_at` | `started_at` | `finished_at` |
| --- | --- | --- | --- |
| `CREATED` | present | absent | absent |
| `RUNNING` | present | present | absent |
| terminal | present | present | present |

`started_at` is written at most once — structurally, because `RUNNING` is
reachable only from `CREATED` and `CREATED` is reachable from nowhere, not
because a guard compensates.

That table is not merely a description of what the application does; it is the
stored shape of every row, enforced by one check constraint,
`research_run_state_matches_timestamps`:

```sql
(finished_at IS NULL     AND started_at IS NULL     AND state = 'CREATED')
OR (finished_at IS NULL     AND started_at IS NOT NULL AND state = 'RUNNING')
OR (finished_at IS NOT NULL AND started_at IS NOT NULL AND state IN
        ('COMPLETED', 'FAILED', 'PARTIALLY_COMPLETED'))
```

One rule rather than several overlapping ones, so there is a single place to
read what a valid row is and no gap between rules to fall through. Because
every branch names a state, it also confines `state` to the five values in the
vocabulary — `choices` is validation, not storage. It replaced the narrower
1A rule "finished implies started", which admitted most invalid shapes; the
two are not kept side by side (AD-030, migration `0002`).

### 15.6 Who guarantees what

The database and the application answer different questions, and neither is
asked to answer the other's:

| | Guarantees | Cannot guarantee |
| --- | --- | --- |
| **Database** | A stored row is structurally self-consistent, for every write that reaches the table | That the row arrived by a legal route |
| **Application** (`transition_to`, `save`) | An allowed transition path was followed, and a run begins in `CREATED` | Anything about writes that never call it |

A check constraint sees one row, not the sequence of rows that preceded it, so
no constraint can prove a `COMPLETED` row was ever `RUNNING`. Proving that
needs triggers or a history table, and both are deliberately out of scope
(AD-028).

The consequence is stated rather than left to be discovered: **`QuerySet.update()`
and raw SQL bypass the application entirely**, so a direct write can move a run
along a route the transition table forbids. What such a write cannot do is
leave a structurally impossible row behind. Closing the provenance gap
completely is not 1A work; knowing exactly where it sits is, and a test asserts
both halves.

Time enters at the application layer, from Django's timezone utilities, and
never inside the domain (AD-015). `transition_to` accepts the moment
explicitly, which is what keeps the tests deterministic without freezing a
global clock.

No event or history table exists. Three timestamps audit the only lifecycle
there is, and a per-transition log is not built on speculation (8B is where
research history belongs). `FAILED` likewise carries no failure detail: it is a
state, not a stack trace, and exception persistence waits for a phase that
actually produces failures worth recording.

### 15.7 Known limitation: transitions are not atomic across processes

`transition_to` reads the state on the in-memory instance, checks it against the
table, and writes. Two processes holding the same run could both observe
`RUNNING`, both consider a terminal move legal, and both write — last write
wins, silently.

This is recorded rather than papered over, and it is not a live risk today:
nothing executes a run, and there is no background processing, no queue, and no
worker, so no second writer exists. The honest fix — a conditional update, row
locking, or both — belongs to the phase that first introduces a concurrent
writer and can test it. Adding locking now would guard against a scenario the
system cannot produce.

Status: `IMPLEMENTED` (1A) for the record, its identity, its state machine, its
timestamps, and its migration. The report at `/research/<id>` is `APPROVED /
PLANNED` for 1B — no view, URL, or template exists.

## 16. Price-intelligence direction

Planned pipeline, all deterministic:

1. **Listing extraction** (3A) — obtain candidate listings via the search
   boundary.
2. **Normalization** (3B) — currency, quantity, pack size, unit price,
   condition, availability, seller.
3. **Match and reject** (3C) — classify each listing with an
   `IdentityMatchType`; record every rejection with a reason.
4. **Aggregation** (4A) — count, low, median, high, and an estimated market
   range computed from accepted listings only.
5. **Report** (4B) — present the numbers together with the listings and the
   rejections that produced them.

Rules:

* Only accepted, part-number-level matches contribute to a price conclusion
  unless a documented rule says otherwise.
* A small sample yields a low confidence and says so; it does not yield a
  narrow-looking range.
* Zero accepted listings yields `UNKNOWN`, never an estimate.
* Every displayed number is reproducible from the retained evidence.

Which aggregate constitutes "market price", and how outliers are handled, are
`UNDECIDED` — to be settled in 4A with the evaluation corpus from 0B.

Status: `APPROVED / PLANNED`. Nothing implemented.

## 17. Comparable-product direction

Planned after pricing, because comparison depends on identity and
specifications being trustworthy first:

1. **Candidate discovery** (7A) — find plausible alternatives.
2. **Similarity scoring** (7B) — score against extracted specifications.
3. **Comparison report** (7C) — present candidates with compatibility notes
   and, critically, the important *differences*.

Rules:

* A comparable is never presented as equivalent. Differences are shown as
  prominently as similarities.
* Similarity is explicitly *not* identity — see §10 and `IdentityMatchType`.
* A comparison must state what it could not verify.

Specification extraction (6A) and the first category-specific schema (6B)
precede this work. Which category comes first is `UNDECIDED`.

Status: `APPROVED / PLANNED`. Nothing implemented.

## 18. Caching / freshness direction

Different classes of information decay at different rates:

| Information | Freshness window |
| --- | --- |
| Market prices | short-lived |
| Comparable products | medium-lived |
| Product specifications | longer-lived |

Rules for whenever this is built (8A):

* Cache policy belongs to the core, keyed on the canonical request. It is
  never coupled to a calling system, and no client dictates freshness.
* A user must be able to force a refresh.
* A report must show how old its evidence is; stale data presented as current
  is a correctness bug.

Status: `DEFERRED` to 8A. Storage mechanism is `UNDECIDED`. No caching of any
kind exists, and none should be added before 8A.

## 19. Security boundaries

* **Secrets live in the server environment only.** Never in the repository,
  never in a URL, never in a client, never in a desktop configuration file.
* **Clients hold no credentials.** Every launcher is a URL builder.
* **All input from any intake is untrusted**, including input from an
  internal ERP. It is validated and normalized at the boundary before use.
* **Untrusted external content stays data.** Text retrieved from search
  results or web pages is evidence to be analysed, never instructions to be
  followed — this is a live risk once an LLM is involved.
* **Report URLs are not an access-control mechanism.** A run's identifier is a
  random UUID (§15.3), which resists enumeration and does nothing else: it
  authenticates nobody and authorizes nothing. Whether reports need
  authentication, and what visibility they have, is still `UNDECIDED` and must
  be settled before any deployment beyond a trusted internal network. Choosing
  the identifier scheme in 1A did not answer that question and must not be read
  as having answered it.
* **`DEBUG` off and a real `SECRET_KEY`** are required for any deployment.
  The repository default is explicitly development-only.

Authentication and authorization are `DEFERRED`; no phase before 8C assumes
them.

Status: `APPROVED / PLANNED`. `IMPLEMENTED` today only as: no secrets in the
repository, environment-sourced Django settings, and an unguessable run
identifier that is explicitly not a permission check.

## 20. Testing strategy

Principles:

* **Deterministic by default.** No test depends on the network, on a live
  vendor, or on model output.
* **Contracts are tested at the contract level.** Validation rules that the
  whole system relies on get direct tests.
* **Architecture invariants are tested mechanically, not just documented.**
  `tests/domain/test_domain_boundaries.py` fails if the domain gains a
  non-stdlib import, a calling-system concept, or a vendor name.
  `tests/runs/test_research_run_boundaries.py` fails if a research run gains a
  caller-shaped or provider-shaped column, if the domain or research core gains
  a Django import, or if a second model appears.
* **The database is set up without a plugin.** `tests/conftest.py` configures
  Django and creates an in-memory SQLite test database for the session. The
  suite therefore exercises the real migration, stays offline and
  deterministic, and leaves no file behind — and the project keeps its rule
  that a dependency arrives with the phase that needs it.
* **Refusals are tested as hard as happy paths.** For a state machine that is
  most of the value: a lifecycle exercised only along its legal route is
  indistinguishable from an attribute assignment.
* **No placeholder tests for unbuilt behaviour.** A test for search
  behaviour that does not exist is noise.
* **Provider interactions will use recorded fixtures**, never live calls, so
  the suite stays deterministic (`APPROVED / PLANNED` from 2B).
* **The evaluation corpus is validated as data.** Its invariants have direct
  tests, and mutation-style tests break one field at a time to prove the
  validator rejects what it claims to. A validator that only ever sees valid
  data is indistinguishable from one that returns `True`.

Status: `IMPLEMENTED` for the domain contracts, the evaluation corpus, the run
lifecycle, and the architecture guards.

## 21. Evaluation strategy

Testing proves the code does what it says. Evaluation proves the *answers*
are good — these are different problems, and research quality needs the
second one.

The corpus lives in `evaluation/`, with its contracts, validation, and loader
in `product_intelligence/evaluation/`. `evaluation/README.md` is the detailed
reference; this section records what binds the rest of the roadmap.

### 21.1 Real versus synthetic

Every case is `REAL_VERIFIED` or `SYNTHETIC`, and the two are kept in separate
files with the distinction enforced by validation.

`REAL_VERIFIED` means the expected identity is backed by a recorded
manufacturer-controlled source: source name, URL, verification note, and
verification date. `SYNTHETIC` means the case was constructed to exercise a
behaviour, and it carries a construction note **instead of** source-shaped
provenance — a fabricated citation is worse than none, because a later reviewer
would trust it.

A case derived from a real part number is still synthetic: a one-character
mutation of a verified part number is an evaluation construction, not a claim
that such a product exists. Wholly fictitious part numbers carry an `EVAL-`
prefix so they cannot be misread as real.

### 21.2 What the corpus records

Truth, never implementation. Expectations may record the expected
manufacturer, canonical part number, product and family text, whether an exact
identity should be resolvable at all, and identities that must **not** be
accepted. They may not record a required search query, provider, prompt,
ranking, similarity threshold, or numeric confidence — those are later phases'
decisions, and a benchmark that pre-decided them would measure obedience rather
than correctness. The broad family label is for human understanding; it is not
a category taxonomy, which remains phase 6 work.

Expected answers use a four-value evaluation vocabulary — `EXACT_IDENTITY`,
`AMBIGUOUS`, `CONFLICT`, `UNKNOWN` — deliberately separate from
`IdentityMatchType`. The runtime enum answers "by what mechanism was this
matched?"; an expectation answers "what class of answer is correct?" Reusing
the runtime enum would smuggle a matching design into the benchmark.

### 21.3 Metrics

Defined now, computed by nothing yet, because no resolver exists to score:

* **identity accuracy** — of the cases where an identity should be resolvable,
  how many resolved to the expected one;
* **false-confidence rate** — how often the system confidently resolves to an
  identity the corpus says is wrong or forbidden. This is the metric that
  matters most; scoring well on accuracy and badly here is worse than answering
  less often;
* **abstention correctness** — whether `AMBIGUOUS` / `CONFLICT` / `UNKNOWN`
  cases are correctly *not* forced into an exact identity;
* **false-exact rate** — how often exactness is claimed where the corpus does
  not support it, independent of whether the chosen product happened to be
  right.

**No pass/fail threshold is set.** Thresholds must be earned empirically once
there is something to measure, and they remain `UNDECIDED` — including the ones
§16 defers to this corpus.

### 21.4 Price evaluation is a snapshot problem

The corpus contains no price, and no expected price will be added to it. A
market price is an observation at a moment, not a property of a product;
freezing one into the benchmark would make it stale within weeks and would fail
a correct implementation for running later.

Price evaluation must instead work against preserved, timestamped listing
snapshots:

```text
recorded listings at time T  ->  deterministic aggregation  ->  expected
aggregate for that snapshot
```

The expectation is then about the arithmetic and the accept/reject decisions
over a fixed set of observations, which stays true, rather than about the
market, which does not. Those snapshots belong with 3A–4A. The same reasoning
is why real cases record no stock status and no lifecycle state.

### 21.5 Change discipline

Evaluation truth must not move when an implementation changes. A change to an
expected answer must state whether (A) the old expectation was factually wrong,
(B) authoritative source information changed, (C) the case definition was
ambiguous, or (D) the product behaviour requirement intentionally changed.

**"The new implementation failed this case" is not a valid reason.** A corpus
edited to match whatever the code now does measures nothing.

### 21.6 Growing the corpus

Five verified identities is a deliberate floor. The intended expansion is real,
representative MPN and description pairs from the company's sales-order
workflow — the actual product lines and the actual abbreviated, inconsistent
descriptions people type, which no invented case reproduces. Those cases must
be curated and verified before becoming benchmark truth, and must carry no
customer names, order numbers, prices, quantities, or other sensitive business
data. None exists yet, and none is invented.

Status: `IMPLEMENTED` for the corpus, its contracts, validation, and loader
(0B). `APPROVED / PLANNED` for every measurement described above: nothing
computes a metric, and no threshold is chosen.

## 22. Approved phased roadmap

```text
PRODUCT-INTEL.0A   Architecture + domain contracts              IMPLEMENTED
                   0A-FU1 contract correctness cleanup          IMPLEMENTED
PRODUCT-INTEL.0B   Evaluation corpus                            IMPLEMENTED
PRODUCT-INTEL.1A   ResearchRun lifecycle                        IMPLEMENTED
                   1A-FU1 persistence invariant hardening       IMPLEMENTED
PRODUCT-INTEL.1B   Basic standalone web research/report shell   NEXT
PRODUCT-INTEL.2A   Deterministic product identity model
PRODUCT-INTEL.2B   Search provider abstraction
PRODUCT-INTEL.2C   First real search provider
PRODUCT-INTEL.3A   Market listing extraction
PRODUCT-INTEL.3B   Listing normalization
PRODUCT-INTEL.3C   MPN matching + rejection
PRODUCT-INTEL.4A   Price aggregation
PRODUCT-INTEL.4B   Price Intelligence web report

----- PRICE MVP -----

PRODUCT-INTEL.5A   Structured external intake API
PRODUCT-INTEL.5B   Visual FoxPro 5 launcher integration

----- FOXPRO MVP -----

PRODUCT-INTEL.6A   Product specification framework
PRODUCT-INTEL.6B   First category-specific schema
PRODUCT-INTEL.7A   Comparable-product candidate discovery
PRODUCT-INTEL.7B   Similarity scoring
PRODUCT-INTEL.7C   Comparison web report

----- COMPARABLE MVP -----

PRODUCT-INTEL.8A   Caching / refresh strategy
PRODUCT-INTEL.8B   Research history
PRODUCT-INTEL.8C   Production hardening

Future:
  SAP launcher integration
  additional clients
  additional product-category schemas
  additional search providers
  additional LLM providers
```

Every phase after 1A is `APPROVED / PLANNED` and unimplemented. Do not
execute a later phase while working on an earlier one.

## 23. Explicit deferred items

Not to be introduced until a specific phase demonstrates a concrete
requirement. "It is an AI project" is not a requirement.

`DEFERRED`: React · Next.js · any separate SPA frontend · LangChain · agent
frameworks · Celery · Redis · vector databases · Kubernetes · message brokers
· multi-model orchestration · multiple simultaneous search providers ·
background job processing · authentication · caching · scraping
infrastructure · dashboards · polished UI work · production deployment
tooling.

Deferred specifically around the run lifecycle (1A), so that later phases do
not read their absence as an oversight: retry / reopen / resume semantics · a
per-transition event or history table · persisted failure diagnostics ·
cross-process transition atomicity · distributed locking · a server database
in place of development SQLite.

Also deferred as capability, per the roadmap rather than per this list: real
web search, real product lookup, LLM calls, prompt engineering, price
calculation, listing extraction, comparable discovery, similarity scoring,
launcher code of any kind, and the research API.

Open questions currently `UNDECIDED`: search vendor · LLM vendor · report
access control (the identifier scheme was settled in 1A as a random UUID, which
is explicitly not access control) · which aggregate represents
"market price" · outlier handling · description truncation policy for URL
length limits · first product category · cache storage mechanism · batch
intake design · every evaluation pass/fail threshold (§21.3) · the recorded
listing-snapshot format for price evaluation (§21.4).

## 24. CURRENT STATUS

```text
CURRENT STATUS

Completed:
- PRODUCT-INTEL.0A
- PRODUCT-INTEL.0A-FU1 (corrective follow-up attached to 0A)
- PRODUCT-INTEL.0B
- PRODUCT-INTEL.1A
- PRODUCT-INTEL.1A-FU1 (corrective follow-up attached to 1A)

Current approved implementation state:
- Project architecture established
- Durable Claude guidance established
- Initial domain contracts established
- Evaluation corpus, its contracts, validation, and loader established
- Persistent ResearchRun lifecycle established
- Focused contract, lifecycle, and boundary tests established

Not yet implemented:
- Web research UI
- Web report page
- Search providers
- LLM providers
- Product resolver
- Market pricing
- Comparable products
- FoxPro integration
- SAP integration

Next planned phase:
- PRODUCT-INTEL.1B — Basic standalone web research/report shell
```

Concretely, the repository contains: this document, `CLAUDE.md`, `README.md`, a
minimal Django project with one application, the domain contract layer, the
evaluation corpus layer, the run-persistence layer and its two migrations, empty
boundary packages carrying their rules as documentation, and 250 passing tests.
There is no research capability of any kind.

**What 1A added.** One persisted record: `ResearchRun`, in
`product_intelligence/runs/`, with a UUID identity, the canonical MPN and
description from a `ResearchRequest`, a state drawn from the existing
`ResearchRunState` vocabulary, three lifecycle timestamps, one supported
transition method, and one migration. It stores that research was asked for and
how the attempt ended. **It runs no research**: there is still no search, no
model call, no resolver, no pricing, no comparables, no view, no URL, and no
background processing — nothing yet moves a run out of `CREATED`. 1A also
corrected stale documentation that described Python 3.10.1 as the development
interpreter (AD-017).

**What 1A-FU1 corrected.** Two defects found in review, before 1A was frozen:

1. **An incomplete stored invariant.** 1A enforced the lifecycle in application
   code and backed it with one narrow database rule ("finished implies
   started"). An audit of what an ordinary `objects.create(...)` could persist
   found ten invalid shapes getting through — `RUNNING` with no start time,
   `COMPLETED` that never finished, `CREATED` carrying both timestamps, and runs
   created directly in a terminal state. One constraint now describes the whole
   shape, and a run must be created in `CREATED` (§15.5, §15.6, AD-030).
2. **An unsupported dependency floor.** `requirements.txt` allowed Django 5.1
   because that is where `CheckConstraint(condition=…)` appeared — a reason
   about API availability, not about support. 5.1 no longer receives security
   fixes; the floor is now the 5.2 LTS line (AD-031).

FU1 changed the model's constraints and save path, added migration `0002`,
corrected the dependency range and documentation, and added regression tests.
It added no capability and started no later phase; the roadmap numbering is
unchanged.

**What 0B added.** The evaluation corpus: 19 cases (5 `REAL_VERIFIED` seed
identities with manufacturer provenance, 14 `SYNTHETIC` cases covering twelve
adversarial classes), a strict JSON case schema, deterministic validation with
mutation tests, and one loader so later phases do not each invent their own
parsing. It measures nothing yet — there is no resolver — and it added no
research capability, no persistence, and no runtime state.

**What 0A-FU1 corrected.** Two contract-level defects found in independent
review, before 0A was frozen:

1. **An impossible transport guarantee.** The FoxPro compatibility contract
   promised that arbitrary unencoded URL parameter values would survive
   without silent corruption. Reserved characters make that unachievable — see
   §7.2 and AD-018. The approved legacy path is now minimal percent-encoding
   plus browser launch, with raw values accepted best-effort only.
2. **An impossible `ProductIdentity` state.** The type could represent an
   `EXACT`, high-confidence, established identity with no part number at all —
   see §10 and AD-019. Construction now rejects it.

FU1 changed documentation, one domain invariant, and tests. It added no
capability and started no later phase; the roadmap numbering is unchanged.

## 25. Architecture decision log

| # | Decision | Rationale | Status |
| --- | --- | --- | --- |
| AD-001 | The core is caller-independent; all intake normalizes to one `ResearchRequest`. | The calling system will be replaced. The research engine should not notice. | Accepted |
| AD-002 | The canonical request is MPN + description only. | Anything more lets callers diverge and leaks caller concepts into product identity. | Accepted |
| AD-003 | The legacy desktop client is a URL-building launcher and nothing more. | Visual FoxPro 5 predates modern HTTP, JSON, and TLS tooling. Assuming otherwise would make the integration undeliverable. | Accepted |
| AD-004 | **Superseded by AD-018.** Originally: the intake layer tolerates plain, unencoded URL parameters. | The intent — worst-case legacy behaviour must degrade rather than crash — stands. The guarantee did not: it promised recovery of bytes that never reach the server. | Superseded |
| AD-018 | Arbitrary raw query-string values are **not a lossless transport**. The approved Visual FoxPro 5 fallback is **minimal percent-encoding plus browser launch**, not REST/JSON client functionality. | A query string reserves characters: `&` starts the next parameter, so one description becomes several values with no record that they were ever one; `#` starts a fragment identifier that a browser normally does not transmit, so those bytes never arrive at all; `%`, `+`, `?` and `=` may be reinterpreted in transit. Defensive server-side parsing cannot reconstruct information discarded before the request existed, so tolerance is the only honest promise and encoding is where correctness actually comes from. Percent-encoding two values is a character table and string concatenation — within reach of a 1996 desktop client, unlike an HTTP/JSON/TLS stack — so the legacy path stays reliable without weakening the launcher-only boundary. Raw values remain accepted best-effort for URL-safe characters. | Accepted (0A-FU1) |
| AD-005 | No client ever holds secrets. | Keys in a 1996 desktop application cannot be rotated or protected. | Accepted |
| AD-006 | Standalone web use is a first-class interface, not a fallback. | Guarantees the product works with zero integration, and gives development a real UI. | Accepted |
| AD-007 | Evidence-first: conclusions trace to preserved evidence, rejections included. | An untraceable price is not a defensible answer. | Accepted |
| AD-008 | Deterministic code owns identity and arithmetic; LLMs assist with semantics only. | Exact part-number identity and money must be reproducible and auditable. | Accepted |
| AD-009 | Uncertainty is representable and preferred over fabricated certainty. | A confident wrong match is the most expensive failure mode. | Accepted |
| AD-010 | Semantic similarity is never treated as exact identity. | One character can mean a different product. | Accepted |
| AD-011 | External vendors sit behind `SearchProvider` / `LLMProvider` boundaries. | Vendors will change; business logic should not. | Accepted |
| AD-012 | Django with server-rendered HTML; no SPA. | The UI is a form and a report. An SPA would add infrastructure without a requirement. | Accepted |
| AD-013 | Domain contracts are plain stdlib dataclasses; no modelling framework. | Keeps the domain importable without a framework and testable without infrastructure. Revisit only if serialization needs justify it. | Accepted |
| AD-014 | Architecture invariants are enforced by tests, not documentation alone. | Documents drift; tests fail. | Accepted |
| AD-015 | The domain never generates timestamps. | Caller-supplied time keeps behaviour deterministic and testable. | Accepted |
| AD-016 | No `ResearchRun` entity or database schema in 0A. | Modelling persistence before the behaviour exists guesses wrong. | Accepted |
| AD-017 | The supported baseline is **Python 3.12**, declared as `requires-python = ">=3.12"`; code avoids version-specific syntax. The project virtual environment in use is **Python 3.14.7**, which satisfies the baseline. | The declared baseline is the contract, and an installed interpreter only has to satisfy it. An earlier revision of this entry recorded a development machine running 3.10.1 — that environment gap no longer exists and the wording was corrected in 1A. The baseline itself is unchanged: it is not lowered to match whichever interpreter is installed, and provisioning a supported one is an environment task rather than an architecture change. | Accepted (wording corrected 1A) |
| AD-019 | An established `ProductIdentity` must carry the part-number evidence its match type claims: `EXACT` requires a part number, `NORMALIZED_EXACT` requires both a part number and the normalized form. | The type could otherwise represent a state that cannot exist — a character-for-character match against no part number, reporting itself established at high confidence. That is precisely the fabricated certainty AD-009 forbids, expressed as a data structure. Enforcing it at construction keeps `is_established` a report rather than a compensation, and the rule uses only fields already in the contract, so it adds no matching or normalization logic. Weaker match types stay unconstrained: `DESCRIPTION_ONLY` *means* no part-number evidence. | Accepted (0A-FU1) |
| AD-020 | The evaluation corpus is reference data outside the runtime domain: JSON under `evaluation/`, loader and validation under `product_intelligence/evaluation/`, never a Django model and never persisted. | Evaluation asks whether answers are *good*; the domain describes what the system *is*. Mixing them would put benchmark concepts into runtime contracts and make expected answers part of application state — where a migration, a fixture load, or a research run could change them. Keeping the data outside the package also keeps it reading as the reviewable document it is. The dependency runs one way only: evaluation imports the domain to prove every case input is a valid `ResearchRequest`, so the corpus and the intake boundary cannot drift apart. | Accepted (0B) |
| AD-021 | Every case is `REAL_VERIFIED` with authoritative provenance, or `SYNTHETIC` with a construction note — enforced, separately filed, and never blended. A synthetic case may not carry source-shaped provenance. | A benchmark is only as trustworthy as its weakest citation. An invented part number presented as a real product would silently teach later phases to expect a thing that does not exist, and a fabricated source is worse than no source because a reviewer would trust it. Cases derived from real part numbers stay synthetic: the mutated request is an evaluation construction, not a claim about a product. | Accepted (0B) |
| AD-022 | Expected answers use an evaluation-only vocabulary (`EXACT_IDENTITY`, `AMBIGUOUS`, `CONFLICT`, `UNKNOWN`) rather than reusing `IdentityMatchType`, and record no query, provider, prompt, ranking, threshold, or numeric score. | The two vocabularies answer different questions: `IdentityMatchType` says by what mechanism something matched, an expectation says what class of answer is correct. A case asserting that a formatting variant resolves to a known part number is deliberately silent about whether a resolver gets there by exact comparison or by normalization — that is 2A/3C's design decision, and encoding it now would make the benchmark measure obedience to a guess instead of correctness. | Accepted (0B) |
| AD-023 | No price, stock, or lifecycle claim enters the corpus. Price evaluation will operate against preserved timestamped listing snapshots: recorded listings at time T → deterministic aggregation → expected aggregate for that snapshot. | A market price is an observation at a moment, not a property of a product. "This SSD should cost $430" would be stale within weeks and would then fail a *correct* implementation for the crime of running later — a benchmark that punishes correctness is worse than none. An expectation about arithmetic over a fixed set of recorded observations stays true permanently, and it tests what the system actually owns: the aggregation and the accept/reject decisions. | Accepted (0B) |
| AD-024 | An expected answer may be changed only with a stated reason of kind A (factually wrong), B (source changed), C (ambiguous case definition), or D (requirement changed). A failing implementation is explicitly not a valid reason. | Without this rule the corpus decays into a record of what the code already does, which measures nothing. The failure mode is quiet and rational-looking at each step — one case adjusted per phase, each time to unblock work — so the prohibition has to be written down rather than assumed. | Accepted (0B) |
| AD-025 | Persistence lives in its own Django application, `product_intelligence/runs/`, holding the project's only model. The domain and the research core stay database-free, and the web layer does not own the lifecycle. | Each of the three alternatives breaks something specific. A model in `domain/` would make the contracts require Django to import, contradicting AD-013 and failing the guard that enforces it. A model in `research/` would tie the engine to a database, so no part of it could be reasoned about or tested without one — and the engine is the piece most likely to be exercised in isolation. Ownership in `web/` would make a run's existence a property of the transport that created it, which is exactly the caller-coupling AD-001 exists to prevent; a run outlives its request and belongs to no client. A fourth package costs one directory and keeps the dependency arrow pointing one way: `runs` imports `domain`, never the reverse. | Accepted (1A) |
| AD-026 | A run's primary key is an application-generated random UUID, serving as both the database key and the public report identifier. Opacity is explicitly **not** access control. | The report URL `/research/<id>` has to be durable and non-enumerable, and a UUID primary key gives both without a second identifier to keep in sync — a separate public id alongside a sequential key would add a consistency obligation for no capability. Generating it in the application rather than the database means the identity exists before the first write, so nothing has to round-trip to learn it. The second half of the decision matters more than the first: unguessability is not authorization, and writing it down here is what stops a later phase from treating "the URL is hard to guess" as a security answer. Report visibility stays `UNDECIDED` per §19. | Accepted (1A) |
| AD-027 | Transitions go through one method against an explicit table; terminal states are terminal; an illegal move raises and changes nothing; assigning `state` on a saved run and calling `save()` is refused. | Two failure modes are worth engineering against. The first is silent coercion — clamping an illegal move to the nearest legal state would tell a caller a run progressed when it did not, which is AD-009's fabricated certainty wearing a state machine's clothes. The second is the bypass: a convention that says "use `transition_to`" is obeyed until the first hurried caller, and then the lifecycle rules are advisory forever. AD-014 says invariants are enforced by tests rather than documents; the same logic applies to the API itself, and the guard costs a handful of lines. Retry and reopen stay out because no phase has asked for them and a re-run is honestly a new run. | Accepted (1A) |
| AD-028 | A run records three timestamps and nothing else about its history. No event table, and no persisted failure diagnostics. | `created_at` / `started_at` / `finished_at` fully audit a lifecycle with four edges — a history table would record the same three facts in a shape justified only by transitions that do not exist. `FAILED` is a state, not a stack trace: nothing currently executes a run, so any diagnostics schema would be designed against imagined failures and would be wrong in the specific ways that matter. Research history is 8B, and the phase that first produces real failures is the one that can see what is worth keeping. | Accepted (1A) |
| AD-029 | Cross-process transition atomicity is not guaranteed. The limitation is documented in §15.7 rather than solved. | `transition_to` checks the in-memory state and writes; two concurrent writers could both pass the check and the last write would win. The honest options were to fix it, to hide it, or to state it. Fixing it means conditional updates or row locking built against a concurrency scenario the system cannot yet produce — there is no worker, no queue, and nothing that executes a run, so the fix would ship untested by anything real. Hiding it would leave a later phase trusting a guarantee that was never made. Stating it costs nothing and hands the phase that introduces a second writer both the problem and the reason it was left. | Accepted (1A) |
| AD-030 | One check constraint states the complete state/timestamp shape of a stored row, replacing the narrower "finished implies started" rule; and a run may only be *created* in `CREATED`. The database judges the row; the application judges the path. | 1A relied on application code for a rule the database was only half-checking, and the gap was not theoretical: an audit found ten invalid shapes that ordinary ORM calls persisted, including a `COMPLETED` run that never started. A guarantee that holds only when callers use the intended method is a convention, and this one is cheap to make real. One expression rather than several overlapping rules means a single place to read what a valid row is, no gap between rules to fall through, and — because every branch names a state — storage-level confinement of `state` to the vocabulary, which `choices` alone does not give. The creation rule closes the other half: without it, a run could be inserted directly into a terminal state, structurally valid and a complete fiction about what happened. What the constraint deliberately does **not** do is prove provenance: a check sees one row, never the sequence that produced it, so `QuerySet.update()` and raw SQL can still skip the transition path. That residue is documented (§15.6) rather than chased with triggers or a history table, both of which AD-028 rules out. | Accepted (1A-FU1) |
| AD-031 | The Django floor is the supported 5.2 LTS line (`>=5.2,<6.0`), not the oldest release whose API happens to compile. | 1A set the floor at 5.1 because `CheckConstraint(condition=…)` arrived there. That is a statement about syntax availability, not about whether the release is safe to run: 5.1 is out of security support, so the declaration invited an installation receiving no fixes. A dependency floor is a support commitment. The upper bound stays below 6.0 — moving to a new major line is its own decision with its own testing, not a side effect of a correction. `requires-python = ">=3.12"` is unchanged; the development environment runs Python 3.14.7, which satisfies both. | Accepted (1A-FU1) |
