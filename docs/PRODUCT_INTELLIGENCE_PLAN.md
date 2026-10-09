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

Status: `PARTIALLY IMPLEMENTED` — isolated research primitives through 4A
exist, the 4B price intelligence report is implemented, 4C-A/B/B-FU/C
implement execution ownership, backend orchestration, deduplication, and
web execution/retry integration, FU3A/FU3B implement semantic qualification
and semantic execution integration, and HUMAN-REVIEW implements human review
for AI-assisted semantic matches. The web form creates a run, triggers
execution synchronously, and redirects to the report with the full result.
PRODUCT-INTEL.4D (Customer Quote Research Expansion) is
IMPLEMENTED / APPROVED / FROZEN / COMPLETE: 4D-B is APPROVED/FROZEN,
4D-C-A is APPROVED/FROZEN, 4D-C-SEC is APPROVED/FROZEN, 4D-C is
APPROVED/FROZEN, 4D-D-PRE1 is APPROVED/FROZEN and 4D-D-PRE2 is
APPROVED/FROZEN (evidence SHA 1cb65a3d6002006af9e1c77906a6de6b5a3fd42c),
and 4D-D (including 4D-D-FU1) is APPROVED/FROZEN (v1 scope: Micron 7500
SSD only; frozen SHA 065320180c17b89c7460164326a0c9f49e01fe3b; frozen
baseline 5097 collected; final acceptance 5097 passed, 0 failed, 0
skipped, 0 xfailed, 0 deselected, +39 subtests passed).
PRODUCT-INTEL.PILOT-RELEASE-2 (4D Customer Requirement Deployment &
UAT) is DEPLOYED / ACCEPTED: the frozen 4D customer requirements are
deployed on the internal production/pilot Windows server (deployed
runtime SHA 065320180c17b89c7460164326a0c9f49e01fe3b — the
independently reviewed and frozen PRODUCT-INTEL.4D-D-FU1 runtime SHA;
deployment is Git-managed and exact-approved-SHA based), migrations
through 0010_research_micron_alias_snapshot are deployed, and the
production smoke test passed on 2026-09-23. The later commits c6ad6ae
and 7ff0ab7 are docs-only project-state closures; production does not
need to move merely to obtain those documentation edits, and 7ff0ab7
is not the production runtime SHA. The 8A (Caching & Freshness) series
is in progress: PRODUCT-INTEL.8A-PRE (Caching & Freshness Architecture
Audit) is APPROVED / COMPLETE (read-only / design-first audit
delivered; no TTL values approved there), the 8A-FX design lineage
(8A-FX-DESIGN, 8A-FX-DESIGN-FU1) is APPROVED / FROZEN as design, and
PRODUCT-INTEL.8A-FX-A1 (Canonical ECB Observation Cache) is
IMPLEMENTED / PENDING FINAL REVIEW (canonical spec §26.18; AD-064):
the first safe caching slice — cross-run reuse of the canonical
production ECB daily FX observation set, acquisition-only, with a
proof-instant + Europe/Brussels weekend-closure freshness policy (no
numeric TTL). Later planned work
includes 5A (Structured external API, PLANNED / NON-BLOCKING), 8B
(Research history), and 8C (Production hardening); none of them is
NEXT, and authentication/session remains outside the current priority.

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
| Execution (`execution/`) | Orchestration, pipeline coordination, run lifecycle transitions | Callers, vendors, transports, presentation, evidence decisions |
| Core (`research/`) | Deterministic research primitives: resolution, pricing, comparables, evidence decisions | Callers, vendors, transports, persistence, providers, network |
| Domain (`domain/`) | Contracts and controlled vocabularies | Callers, vendors, transports, frameworks, I/O |
| Providers (`providers/`) | Vendor adapters, credentials, vendor payload shapes | Business rules |
| Web report | Presentation of a completed or in-progress run | Which caller started the run, execution logic |

The **caller is only an intake mechanism**. No business rule may branch on
which client produced a request.

Repository layout:

```text
/
├── CLAUDE.md                               durable operating instructions
├── README.md                               developer orientation
├── docs/PRODUCT_INTELLIGENCE_PLAN.md       this document
├── docs/PRODUCT_INTELLIGENCE_STATUS.md     volatile current-state
├── manage.py                               Django entry point
├── config/                            Django project configuration
├── evaluation/                        benchmark data + its README (0B)
│   └── corpus/                        real_verified.json, synthetic.json
├── product_intelligence/
│   ├── domain/                        contracts + vocabularies (0A)
│   ├── evaluation/                    corpus contracts, validation, loader (0B)
│   ├── runs/                          persisted run lifecycle + migration (1A) +
│   │                                  price intelligence snapshot (4B)
│   ├── research/                      part-number comparison (2A) +
│   │                                  raw listing extraction (3A) +
│   │                                  listing normalization (3B) +
│   │                                  MPN matching + rejection (3C) +
│   │                                  price aggregation (4A) +
│   │                                  versioned codec (4B)
│   ├── providers/                     search boundary (2B) + Serper (2C) +
│   │                                  page-fetch boundary and fetcher (3A)
│   ├── execution/                     research orchestration (4C-B implemented)
│   └── web/                           standalone form + price report (1B, 4B)
└── tests/                             focused deterministic tests
```

Repository documents, by ownership:

| Document | Role |
| --- | --- |
| `CLAUDE.md` | Durable repository-level agent operating contract |
| `docs/PRODUCT_INTELLIGENCE_STATUS.md` | Volatile current-state snapshot |
| `docs/PRODUCT_INTELLIGENCE_PLAN.md` | Canonical long-form architecture, roadmap, phase specifications, and decisions |
| `README.md` | Human/developer orientation |

The evaluation corpus sits outside the Python package deliberately: it is
reviewable reference data, not application code and not runtime state. Only its
loader and validation live in the package, so later phases can import them.

`runs/` is the persistence layer, and it is deliberately a fourth box rather
than a file inside an existing one (AD-025). It is the only package containing
a Django model:

| Layer | Owns | Must not know about |
| --- | --- | --- |
| `runs/` | The durable `ResearchRun` record, its lifecycle, its migration, `PriceIntelligenceSnapshot` (4B), `ExecutionEvidenceRecord` (4C-A), `AiAssistedReviewCandidate` (HUMAN-REVIEW) | Callers, vendors, transports, research semantics |

`web/` became a Django application in 1B, holding the intake form, report view, retry endpoint, review endpoints, routes, and templates. It contains no model: a run outlives the request that created it and belongs to no caller, so the lifecycle stays in `runs/` (AD-025, AD-032). `web` imports `domain` and `runs`, and a guard test fails if any inner layer imports `web`. 4C-C wired the web form to the execution layer, and HUMAN-REVIEW permits narrow read-side research imports through a symbol-level allowlist enforced by `tests/web/test_web_boundaries.py`.

`execution/` is the research orchestration layer (4C-B implemented). Real research
orchestration must coordinate provider I/O, the deterministic research primitives
in `research/`, and the `runs/` lifecycle — and `research/` is intentionally
pure and forbidden from depending on providers, persistence, or network. Neither
`research/` nor `web/` can own orchestration: `research/` cannot import the
dependencies it would need, and `web/` must not carry research semantics. The
execution layer sits between them, allowed to import `domain`, `research`,
`providers`, and `runs`, but forbidden from importing `web`. `web/` invokes
execution via the public API (`execute_research_run`), and execution must not
know which transport or client requested the run. This preserves the caller-independence boundary
(AD-001) without weakening the pure-research boundary (AD-013). See AD-051.

Status: `IMPLEMENTED` for the layout, the domain layer, the evaluation corpus
layer, the run-persistence layer, the Django project, the standalone web intake
and report shell, the deterministic part-number comparison primitive inside the
core (§12.1), the search-provider boundary (§13.1), its first real adapter
(§13.5), the page-fetch boundary and its standard-library fetcher (§13.6),
deterministic raw listing extraction (§16.1), deterministic listing
normalization (§16.2), deterministic MPN matching + rejection (§16.3),
isolated deterministic price aggregation (§16.4), and the 4B persisted
read-only price intelligence report. The listed isolated research primitives
and the 4B report are implemented; and (4C-B) end-to-end execution/
orchestration is implemented; web execution/retry integration (4C-C) is
implemented and frozen; semantic integration (FU3B) is implemented and frozen;
human review (HUMAN-REVIEW) is implemented and frozen. Still-not-implemented:
structured API (5A). 6A/6B/6C are implemented and frozen (product specification
framework, Enterprise SSD category schema, specification evidence extraction
and resolution). 7A/7B/7C are implemented and frozen (comparable-product
candidate discovery, similarity scoring, comparison presentation). 4D
(Customer Quote Research Expansion) is IMPLEMENTED / APPROVED / FROZEN /
COMPLETE. PILOT-RELEASE-2 (4D Customer Requirement Deployment & UAT;
deployment/UAT phase, not a feature-development phase) is DEPLOYED /
ACCEPTED (deployed runtime SHA
065320180c17b89c7460164326a0c9f49e01fe3b; production smoke passed
2026-09-23). The 8A (Caching & Freshness) series is in progress: 8A-PRE
(Caching & Freshness Architecture Audit) is APPROVED / COMPLETE (read-only
/ design-first audit delivered; no TTL values approved there), the 8A-FX
design lineage is APPROVED / FROZEN as design, and 8A-FX-A1 (Canonical
ECB Observation Cache) is IMPLEMENTED / PENDING FINAL REVIEW (the first
safe caching slice; canonical spec §26.18; AD-064). 5A remains PLANNED /
NOT IMPLEMENTED / NON-BLOCKING
for the current FoxPro/browser workflow, and 8B/8C remain later
planned; none of them is NEXT.

## 6. Multi-interface intake design

All intake mechanisms normalize into the same `ResearchRequest` before the
core sees anything. Planned mechanisms:

| Mechanism | Shape | Phase |
| --- | --- | --- |
| Standalone web form | HTML form POST | 1B — `IMPLEMENTED` |
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

Status: `IMPLEMENTED` for the standalone web form (1B) and the constrained FoxPro launcher GET contract (5B). `APPROVED / PLANNED` for the structured API (5A). Downstream research primitives exist through 4A, and 4C-C wired the web form so that submission triggers full execution rather than leaving the run as CREATED.

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

A small compatibility helper was shipped in 5B, conceptually similar to:

```text
UrlEncodeLegacy(value)
```

percent-encoding a query-parameter value sufficiently for a browser GET
launcher. It is a few dozen lines of FoxPro string work over a character
table — not an HTTP client. 5B delivered the server-side GET prefill contract
and the FoxPro client integration (outside this repository); localhost UAT
passed.

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
  constraint; description truncation / URL-length policy remains UNDECIDED; 5B did not establish a general truncation policy.
* **TLS is a deployment question, not a core question.** If the legacy client
  cannot negotiate modern TLS for the initial launch, that is solved at
  deployment (for example, an internally reachable endpoint), not by weakening
  the application.

None of this reaches the core. The core sees an MPN and a description.

Status: `APPROVED / PLANNED` as a constraint. No launcher code, no encoding
helper, and no FoxPro-side code of any kind exists in this repository — the
FoxPro client is maintained in the existing Visual FoxPro sales-order
application. 5B implemented the server-side GET prefill contract; the client
integration was delivered outside this repository and localhost UAT passed.

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

### 8.1 What 1B implemented

```text
GET  /research/new       the form (a GET never creates anything)
POST /research/new       ResearchRequest -> ResearchRun (CREATED) -> redirect
GET  /research/<uuid>    the durable report shell
GET  /                   redirect to /research/new
```

The routes are named `research-new` and `research-detail`, and they live in
`product_intelligence/web/`. Post/Redirect/Get is the shape: a valid submission
creates exactly one run through
`ResearchRun.objects.create_from_request(...)` and answers with a redirect, so
reloading the report cannot submit anything twice. An invalid submission
re-renders the form with the reason and creates nothing.

The form does not validate intake itself. Both fields are individually optional
and keep their submitted text (`strip=False`); the "at least one of them" rule
and all whitespace handling come from constructing a `ResearchRequest` and
reporting what it says, so there is one validation policy rather than two that
can drift (AD-032). No part-number normalization happens at the boundary —
that is 2A/3C work, and inventing a version of it in a form would put a
matching decision in the one layer forbidden to make one.

**The shell executes research and presents the result (4C-C implemented).**
A submitted run transitions from `CREATED` to `RUNNING` to `COMPLETED`
(or `PARTIALLY_COMPLETED` / `FAILED`) through the backend executor. The report
shows the full result: state, MPN, description, timestamps, and — if a
`PriceIntelligenceSnapshot` exists — the complete price intelligence evidence.
Human review candidates are presented for completed runs with semantic matches.
Research retry is available for failed runs.

A GET creates nothing whatever query parameters it carries. The launcher entry
point that turns `?mpn=…&description=…` into a prefilled form (no side effect) belongs to 5B; 1B reserved the launcher concern for 5B; 5B resolved it as prefill-only GET, preserving no-side-effect GET semantics (AD-033); a GET
that created records would let a prefetch, a crawler, or a refresh start
research.

MPN and description are untrusted input from every intake, so they are rendered
through ordinary Django auto-escaping and never marked safe. CSRF protection is
enabled on all POST write endpoints (submission, retry, review). The identifier
in a report URL is still not access control
(§19): report visibility remains `UNDECIDED`, so this shell is for local
development and trusted internal use, not public deployment.

Status: `IMPLEMENTED` (1B) for the form, the report shell, the routes, and the
run creation between them. `IMPLEMENTED` (4B) for the report shell extended
with persisted price-result presentation: the report reads an optional
`PriceIntelligenceSnapshot`, decodes it through the versioned codec, validates
request provenance, and renders buckets, contributing evidence, and excluded
listings. Corrupt payload or provenance mismatch fails closed with zero
aggregate numbers. **As of 4C-B, backend research EXECUTION exists:** the
`execution/` package implements the full orchestration pipeline from
`claim_execution` through search, fetch, extraction, normalization, matching,
and aggregation to snapshot persistence. **4C-C is implemented (frozen):** the
web form creates a `CREATED` run, triggers execution via
`execute_research_run()`, and redirects to the report with the full result.
On execution failure, the run transitions to `FAILED` and the report shows
the failure state. Research retry is available for failed runs.

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

Status: `IMPLEMENTED` — as contracts with contract-level validation only.
The persistence layer (§15) stores and rebuilds a `ResearchRequest`.
The research core (§12–§16) consumes `ResearchRequest`, `IdentityMatchType`,
and `EvidenceDecision`: 2A reads the part number a request carries;
3C uses `EvidenceDecision` and `IdentityMatchType` for accept/reject/undecided
outcomes. Nothing in the domain compares, normalizes, or aggregates.

Listings, normalized listings, and identity assessments are research-layer
contracts (`product_intelligence.research`), not domain-layer contracts. The
domain owns the request and the vocabulary enums; the research core owns the
observation and assessment types.

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
`EvidenceReference` contract. There is no complete standalone evidence store.
Price-result evidence *is* persisted inside `PriceIntelligenceSnapshot` (4B):
nested `ListingObservation`, `NormalizedListingObservation`, and
`ListingIdentityAssessment` values are serialized as opaque JSON. However,
no standalone Django model exists for those contracts — they live only as
nested values inside the snapshot payload, and are not independently
queryable.

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

**An LLM may assist with** semantic work only: existing FU3A/FU3B production semantic runtime assists with narrowly eligible semantic identity cases; future work includes:

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

### 12.1 The deterministic part-number comparison (2A, corrected in 2A-FU1)

Phase 2A implemented the first two items on the deterministic list — exact and
normalized part-number matching — as one small primitive in
`product_intelligence/research/identity.py`. It is a pure function of two
strings: no I/O, no database, no provider, no model, no benchmark data. 2A-FU1
corrected its normalization, which was too permissive; §12.3 records what was
withdrawn and why.

**The public surface.**

```text
normalize_part_number(value)                     -> the comparison key
compare_part_numbers(requested, candidate)       -> PartNumberMatchAssessment
compare_request_to_candidate(request, candidate) -> PartNumberMatchAssessment
```

**The normalization profile, in full.**

1. Surrounding whitespace is removed — `str.strip()`, the same Unicode-aware
   operation `ResearchRequest` already applies, so a request that arrived
   through the canonical contract is unchanged.
2. A value carrying nothing but structural characters keys to the empty string:
   there is no part number in it.
3. ASCII `a-z` folds to `A-Z`. Nothing else is case-mapped.
4. Each run of **internal ASCII whitespace** becomes one canonical separator,
   written `-`.
5. Every other character is kept, in place.

The key therefore **preserves the identifier's structure**. `ABC-123` keys to
`ABC-123`, `abc 123` keys to `ABC-123`, and `ABC123` keys to `ABC123` — the
first two are the same identifier written two ways, and the third is a different
identifier that happens to share its alphanumerics.

The characters that count as structure rather than content are:

```text
whitespace   space, tab, newline, carriage return, form feed, vertical tab
separators   -   _   /   .
```

"Structure" here means only that a value built purely from them contains no part
number. It does **not** mean they are interchangeable. **The one approved
formatting equivalence is: an internal ASCII-whitespace run and a hyphen at the
same boundary are the same boundary.** `_`, `/`, and `.` are preserved verbatim
and are never rewritten as a hyphen or as each other.

Nothing else is rewritten. No separator is deleted, repeated punctuation is not
collapsed (`ABC--123` keeps both hyphens), characters and tokens are not
reordered, letters and digits are never dropped, `O`/`0` and `I`/`l`/`1` are
never interchanged, nothing is truncated, no prefix or suffix is guessed, and
there is no fuzzy matching, edit distance, similarity score, embedding, or model
call anywhere in it. A one-character alphanumeric difference stays a difference.

Two exclusions are deliberate rather than accidental:

* **"Remove every non-alphanumeric character" was rejected.** It is the obvious
  one-liner and it silently erases characters that distinguish real products —
  and it widens by itself every time an unfamiliar character appears. `+`, `#`,
  `@`, `:`, parentheses, and arbitrary punctuation are therefore *data*, and
  `ABC+123` does not match `ABC123`.
* **No broad Unicode compatibility transform runs.** A part number is an
  identifier, and NFKC-style folding merges code points whose identity
  equivalence no phase has approved. Non-ASCII characters *inside* the
  identifier are preserved exactly — surrounding whitespace is the one
  exception, and it follows `ResearchRequest` / `str.strip()` semantics, which
  are Unicode-aware. This is also why case folding is an explicit ASCII table
  rather than `str.upper()`: that method expands and rewrites characters in ways
  that are correct for prose and wrong for an identifier. The cost is stated in
  §12.2.

**The outcomes.** Only three, drawn from the existing `IdentityMatchType`:

| Result | Meaning |
| --- | --- |
| `EXACT` | Both sides carry part-number content and are character-for-character equal after surrounding whitespace is removed. |
| `NORMALIZED_EXACT` | Both sides carry part-number content and their normalized keys are equal — they describe the same identifier structure and differ only by ASCII case and by how a boundary was written. |
| `UNKNOWN` | Part-number identity was not established. |

Worked examples:

```text
abc-123          vs  ABC-123          NORMALIZED_EXACT   ABC-123  / ABC-123
ABC 123          vs  ABC-123          NORMALIZED_EXACT   ABC-123  / ABC-123
bcm957504 n425g  vs  BCM957504-N425G  NORMALIZED_EXACT   BCM957504-N425G (both)
ABC123           vs  ABC-123          UNKNOWN            ABC123   / ABC-123
AB-C123          vs  ABC-123          UNKNOWN            AB-C123  / ABC-123
ABC123           vs  A-B-C-1-2-3      UNKNOWN            ABC123   / A-B-C-1-2-3
ABC_123          vs  ABC-123          UNKNOWN            ABC_123  / ABC-123
ABC--123         vs  ABC-123          UNKNOWN            ABC--123 / ABC-123
```

`UNKNOWN` covers everything else, including a missing part number on either
side, which returns a result rather than raising: "identity could not be
established" is a research outcome, and only a structurally invalid argument
type is a caller defect. Two values consisting purely of structural characters
can never match — their keys are both empty, and an established identity
requires part-number content on both sides, so normalization cannot manufacture
a match out of nothing.

`CONFLICT` is never returned: it means evidence is incompatible, and two
different strings do not support that wider claim. `PARTIAL` is never returned
either — containment is not identity, `MTFDKCC3T8TFR` does not establish
`MTFDKCC3T8TFR-1BC1ZABYY`, and classifying partial overlap belongs to 3C.
Widening identity to raise recall is the trade this design refuses.

**A comparison is not a resolution.** An `EXACT` part-number comparison says the
two supplied strings are the same part number and *nothing else*: not that the
manufacturer is right, that the description agrees, that a listing belongs to
the product, or that the source is trustworthy. When a request's part number
matches while its description names a different product, this primitive still
truthfully reports `EXACT` — detecting that cross-evidence disagreement needs
evidence it does not have, and the corpus case for it (SYN-0006) expects the
*system* to report a conflict, which is a conclusion drawn from both sides.

**It holds no catalog and invents no facts.** No part number is mapped to a
manufacturer, product, family, or category. Those mappings exist in the
evaluation corpus as benchmark truth, and moving them into runtime resolution
would be test leakage. The result carries no `ConfidenceLevel` and no numeric
score either: `EXACT` is not a synonym for `HIGH`, because confidence is a
judgement about evidence quality and a string comparison is not one.

**The result is auditable.** `PartNumberMatchAssessment` is a frozen dataclass
exposing both values as compared, both normalized keys, and the match type, so a
reviewer can re-derive the decision from the result alone. Because the keys keep
the identifier's structure, the audit trail distinguishes the two cases that
matter: `bcm957504 n425g` and `BCM957504-N425G` both key to `BCM957504-N425G`
and matched, while `AB-C123` keys to `AB-C123` against `ABC-123` and did not.
It is not persisted, is not a model, and no logging infrastructure was added
for it.

**Historical note:** At the end of phase 3C, the primitive was not yet wired into execution. As of 4C-B, the matching primitive is fully wired into the orchestration pipeline; 4C-C wired web execution; and HUMAN-REVIEW later added narrow approved read-side research imports. The primitive supplies a comparison; it discovers
no candidates itself. 3C consumes it with explicit listing MPN candidates
extracted from pages. A guard test asserts that `runs/` and `evaluation/` do not import the research core, while `web/` may import only the explicitly approved Human Review read-side research symbols (enforced by `tests/web/test_web_boundaries.py`) (AD-036).

### 12.2 Known limits of the profile

Stated rather than left to be discovered:

* **`_`, `/`, and `.` are data.** A part number written `ABC_123` does not match
  `ABC-123`. If a real manufacturer writes one part number both ways, that is
  evidence for a further equivalence — recorded and approved per separator, not
  assumed for the class (§12.3).
* **Non-ASCII separators are data.** A part number written with a non-breaking
  space or an en dash does not normalize onto its ASCII-hyphen equivalent.
* **Padded and repeated punctuation does not collapse.** `ABC - 123` and
  `ABC--123` each keep every boundary they were written with, so neither matches
  `ABC-123`. A whitespace *run* collapses because it is one boundary a typist
  spaced out; extending that to punctuation would be a new equivalence.
* **The profile is one fixed set, not per-manufacturer.** Some manufacturers
  treat a separator as meaningful. Nothing here knows which, because nothing here
  knows the manufacturer.
* **Comparison is symmetric and unranked.** There is no notion of a better or
  worse candidate, and no ordering over several candidates. Selecting among
  candidates needs evidence, which is 3A-3C.

Every one of these fails toward abstention. That is the intended direction: a
missed normalized match costs a re-query, and a false exact costs a wrong price
on a real order.

### 12.3 What 2A-FU1 withdrew, and why

2A's first implementation removed every structural character wherever it
appeared. That deleted separator *position*, not just separator spelling, and
the consequences were reproduced before the fix:

```text
AB-C123  vs  ABC-123      -> NORMALIZED_EXACT   (both keyed to ABC123)
ABC123   vs  ABC-123      -> NORMALIZED_EXACT   (both keyed to ABC123)
ABC123   vs  A-B-C-1-2-3  -> NORMALIZED_EXACT   (both keyed to ABC123)
ABC_123  vs  ABC-123      -> NORMALIZED_EXACT   (both keyed to ABC123)
ABC--123 vs  ABC-123      -> NORMALIZED_EXACT   (both keyed to ABC123)
```

Each of those is a false exact — the failure mode this system exists to avoid —
and the first is the worst of them: the same characters with the boundary in a
different place are not the same identifier by any reading.

Two equivalences were withdrawn:

* **Deleting separators.** Replaced by canonicalizing them: an internal
  whitespace run is written as a hyphen, and nothing is removed. Whether a
  boundary exists, and where, is now preserved.
* **Treating `-`, `_`, `/`, and `.` as one interchangeable class.** The corpus
  evidences exactly one substitution — SYN-0008's `bcm957504 n425g` for
  `BCM957504-N425G`, whitespace against a hyphen — and five verified part numbers
  cannot show that every manufacturer treats every separator as decorative. The
  evidence supported one equivalence; the implementation had generalized it to
  four.

Nothing was withdrawn from `EXACT`, which was already character-for-character
after boundary handling. No corpus expectation was changed: SYN-0008 still
resolves as `NORMALIZED_EXACT`, and it is the case that justifies the one rule
that survived.

Status: `IMPLEMENTED` (2A, corrected in 2A-FU1) for the comparison primitive
described in §12.1. `APPROVED / PLANNED` for the rest of the responsibility
split. The 2A comparator itself uses no LLM and no prompt. FU3A/FU3B later introduced a separate frozen semantic runtime.

## 13. Search-provider boundary

A `SearchProvider` abstraction sits between the research core and any external
search or listing source.

* Business logic depends on the boundary, never on a vendor.
* Vendor names, payload shapes, rate limits, retries, and credentials stay
  inside the adapter.
* Provider results are converted into internal types at the adapter edge; no
  vendor-shaped data reaches the domain or the core.
* Credentials come from the server environment only.

The first search-provider selection is settled as of 2C: Serper, ordinary
Google Search only (§13.5). Additional providers — a second search vendor, or
Google Shopping as a distinct mode of this one — remain `DEFERRED` until a
phase demonstrates a concrete need; multiple *simultaneous* providers are
`DEFERRED` under the same rule.

### 13.1 What 2B implemented

`product_intelligence/providers/search.py` — one synchronous operation and
three immutable provider-neutral contracts:

```text
SearchQuery  ->  SearchProvider.search(query)  ->  SearchResponse
                                                     |- SearchResult, ...
```

```python
class SearchProvider(Protocol):
    def search(self, query: SearchQuery) -> SearchResponse: ...
```

| Contract | Fields |
| --- | --- |
| `SearchQuery` | `text` |
| `SearchResult` | `source_url`, `title`, `snippet`, `price_hint_text`, `part_number_hint`, `raw_reference` |
| `SearchResponse` | `provider_id`, `query`, `retrieved_at`, `results`, `raw_response_reference` |

`SearchQuery` is deliberately **not** a `ResearchRequest` (AD-038). A research
request is a person's input, MPN plus description; a query is one string sent to
one external service. One request may later produce several queries, and
deciding which is query *generation* — research-core work that does not exist.
A provider handed a `ResearchRequest` would have to make that decision itself,
which is how a transport adapter acquires research semantics. Query text is
stripped of surrounding whitespace and must be non-empty. There is no category,
locale, result limit, search mode, pagination cursor, or shopping flag: each is
a policy no phase has taken, and 2C needs none of them.

`SearchResult` records one observation and interprets nothing. `source_url` is
the only required field, because an observation nobody can re-open is not
evidence; it must be an absolute `http`/`https` URL with a host, so
`javascript:`, `data:`, `file:`, other schemes, and relative or scheme-relative
values are refused at the boundary rather than stored and later rendered. The
URL is then kept exactly as observed. That is one narrow rule, not a URL-security
subsystem — it judges no host, no redirect, and no content.

`price_hint_text` is **not a price** (AD-039). It is whatever price-shaped text
the provider displayed — `"$399.99"`, `"$399.99 - $449.99"`, `"from $399"`,
`"EUR 320"`, `"$33/mo"` — and it stays a string: never a `Decimal`, never
assigned a currency, never resolved between a sale price, a shipping charge and
a monthly payment, and never used in arithmetic. The contract has **no numeric
price field at all**, and a test asserts the exact field list, because a numeric
price on a search result would present a snippet as a verified market
observation. Extraction (3A), normalization (3B), and aggregation (4A) exist
precisely because that conversion is a decision with rules rather than a cast.

`part_number_hint` is an **unverified** candidate part number, present only when
a provider explicitly publishes such a field. It is stored exactly as published:
not normalized, not compared, not called a match. A part number *inferred* from
a title, a snippet, or a URL is not this field — that is extraction from noisy
text (3A/3C), and blurring the two would let a guess enter the system under the
name of a published value.

`SearchResponse` carries provenance. `provider_id` is a non-empty string an
adapter supplies for attribution; it is runtime data, never an enumeration, and
no business rule may branch on it — the generic boundary contains no list of
vendors. `retrieved_at` must be timezone-aware and is always supplied by the
adapter, never generated inside the contracts (AD-015). `results` is an
immutable tuple, and **zero results is a valid answer**: a provider finding
nothing is information, and raising instead would push a legitimate outcome into
the failure path.

`SearchProviderError` is the boundary's single failure concept. A taxonomy of
timeout / quota / auth / rate-limit / parse errors would be designed against
imagined failures before a real provider has produced one; 2C sees the real
error surface and may justify a small hierarchy then. Invalid construction of a
contract is a caller defect and raises `TypeError` or `ValueError` instead.

Deliberately absent: provider registry, factory, plugin discovery, dependency
injection, provider manager, fallback chain, multi-provider fan-out, retries,
rate-limit scheduling, circuit breakers, and async. One provider arrives in 2C;
the boundary is designed for replaceability, not simultaneity.

### 13.2 Raw provider material

Real providers return more than these contracts carry, and some of it will
matter. The rule is neither "widen the contract until it holds everything" nor
"pass the payload through so the core can look inside" (AD-040):

```text
provider adapter  ->  normalized SearchResult / SearchResponse fields
                  +   an opaque raw reference
```

Business logic reads the normalized fields. `SearchResult.raw_reference` and
`SearchResponse.raw_response_reference` preserve what the provider actually
returned so a human or a test can re-inspect it. They are opaque strings, kept
verbatim, and nothing in this project parses them. A provider-shaped `dict` is
deliberately not the type: it would invite a research rule to read a
vendor-specific key, and the vendor would be in the business logic from that
moment on.

### 13.3 Recorded fixtures

From 2C onward, provider adapters are regression-tested against **sanitized
recorded responses** — real provider output with credentials, tokens, request
secrets, and personal or customer information removed (AD-041). A recording
should preserve enough of the real response to reproduce an adapter mapping
failure, and nothing more.

* Live calls: only in an explicit, manually run integration or smoke check.
* The normal automated suite: no network, no credentials.
* Regression tests: recorded fixtures.

No such fixture exists yet, and 2B deliberately did not invent one. A fabricated
"real response" would be a guess about a provider that has not been chosen, and
it would pass regardless of what the real one does. Synthetic fakes are
sufficient for testing the interface itself, and that is all 2B's tests use.

### 13.4 What the first real provider (2C) must do

Recorded here so the phase begins with its obligations rather than deriving
them:

* integrate **exactly one** real provider behind this boundary;
* make real search calls only in an explicit or manual integration path;
* capture sanitized real responses as recorded fixtures, and map them to these
  contracts in tests;
* expose traceable search evidence — provider, URL, retrieval time, preserved
  raw material;
* use the deterministic 2A comparison early, whenever a result carries an
  explicit candidate part number;
* **not** accept a result as a listing merely because it contains a price.

If the selected provider is metered or paid per request, basic duplicate
external-call protection must be addressed before it is used as normal
application behaviour — see §18, which distinguishes that narrow concern from
general caching.

A future **internal or distributor price source** does not automatically enter
through this same boundary. The earlier 2B-era direction anticipated it generically
as another provider; 4D-B refines that direction based on the now-known real
structured Vendor API: a structured internal/distributor commercial source does
NOT have to use `SearchProvider` when the `SearchProvider` contract
(`SearchQuery` → URLs/search results) is semantically wrong. 4D-B uses a
provider-neutral commercial-source boundary for structured commercial
observations, with vendor-specific payload/transport logic in adapters and
core/business rules remaining vendor-neutral. Internal commercial pricing and
public market pricing are distinct classes of evidence and MUST NOT automatically
share an aggregate (§16); exposing internal pricing through a report also makes
report access control a blocker rather than a deferred question (§19, §26.3).

Status: `IMPLEMENTED` (2B) for the boundary — the contracts, the protocol, the
one exception, and their guards; `IMPLEMENTED` (2C) for the first real
provider. §13.5 records what 2C added; vendor selection is settled as Serper
(ordinary Google Search), and the boundary itself is unchanged.

### 13.5 What 2C implemented

One adapter, `product_intelligence/providers/serper.py`: `SerperSearchProvider`,
constructible directly (`SerperSearchProvider(api_key=...)`, for tests) or from
the server environment (`SerperSearchProvider.from_environment()`, reading
`SERPER_API_KEY` — the only place in the adapter that touches `os.environ`).
`search()` sends one bounded-timeout HTTPS POST to Serper's ordinary Google
Search endpoint (`https://google.serper.dev/search`), with the credential in
the `X-API-KEY` header Serper documents — never the URL. Google Shopping is a
different endpoint and was deliberately not implemented.

Mapping is direct and narrow: an `organic` item's `link` becomes `source_url`,
`title` becomes `title`, `snippet` becomes `snippet`. `price_hint_text` and
`part_number_hint` are always `None` — ordinary Google Search publishes
neither field, and the real recorded fixture confirms it: several snippets
contain price-shaped text (`"$2,135.00 $2,700.00"`), and none of it is
extracted, because that conversion is 3A/3B's decision with rules, not this
adapter's guess. An item with no usable absolute `http`/`https` link is
discarded rather than fabricated; the surrounding raw response text still
preserves it. The adapter never calls `product_intelligence.research.identity`
— a provider observes, and 2A's exact/normalized comparison is unchanged.

Real provider material stays opaque exactly as AD-040 requires: each mapped
`SearchResult.raw_reference` is that one `organic` item's JSON, and
`SearchResponse.raw_response_reference` is the full response body text.
Neither is parsed anywhere outside the adapter.

Errors are translated to the single `SearchProviderError` the 2B boundary
already defines: HTTP failure status, transport/network failure, timeout,
invalid JSON, and a structurally unusable top-level response are all covered,
and no credential-bearing material ever enters an exception message.

One real, sanitized fixture was recorded —
`tests/fixtures/providers/serper/real_verified_mz_ql23t800_organic_search.json`,
Serper's ordinary-search response for the public MPN `MZ-QL23T800` (evaluation
corpus case `REAL-0001`) — and is the only thing
`tests/providers/test_serper_provider.py` exercises the real mapping code
against; the rest of that file's tests use small synthetic payloads for
malformed-item and error-path coverage, with `urllib.request.urlopen`
monkeypatched so the automated suite makes zero network calls. A separate,
explicitly manual script, `scripts/serper_live_smoke.py`, makes one real call
on request and prints a safe summary only — provider id, query, result count,
public titles and URLs, never the credential. Two live calls were made during
2C's development: one to record the fixture, one to validate the shipped
smoke script.

**Historical note:** At the end of phase 2C, nothing was wired to the Serper
adapter. `runs/` and `web/` imported no part of `product_intelligence.providers`,
and the guard test that checks this also covered `providers/serper.py`. A
submitted run remained `CREATED`, and research execution was not connected.
Duplicate-call protection (§18.1) was identified as a live exposure for the
future phase that would wire the adapter into execution.

**As of 4C-B:** The Serper adapter IS wired into the execution pipeline.
Duplicate paid-call protection IS implemented via atomic `claim_execution`
which ensures at most one paid search call per ResearchRun. A new ResearchRun
created for retry cannot share evidence or snapshot with any prior run.

**Real-response observations**, classified for what they mean to later phases:

* Organic results consistently carried a usable `link` — all ten results in
  the recorded fixture mapped cleanly. *Relevant now*: confirms the
  discard-don't-fabricate policy has a real fixture behind it, not just a
  synthetic one.
* Snippets routinely contain price-shaped text, star ratings
  (`rating`, `ratingCount`), and tracking query parameters
  (`srsltid=...`) inside otherwise-valid URLs. *3A/3B concern*: extraction
  and normalization will have to decide what, if anything, to do with a price
  seen in a snippet, and whether to canonicalize or ignore tracking
  parameters — this adapter does neither.
* No `organic` item published a structured part-number field, only free text
  containing the queried MPN. *Confirms an existing decision*: `part_number_hint`
  staying `None` for ordinary search is not a gap, it is what real ordinary
  search results actually look like.
* Serper additionally returned `relatedSearches` and per-response `credits`.
  *Irrelevant now*: neither maps to any 2B contract field, and both are simply
  part of the preserved `raw_response_reference`.
* The 2B contracts fit the real payload without needing a change — every field
   `SerperSearchProvider` populates already existed, and the adapter never
  needed to store anything the opaque references could not hold.

### 13.6 The page-fetch boundary and what real pages taught us (3A)

2C ended with real candidate URLs and no way to read what was on the other end
of one. 3A opened them.

Three observations are now kept strictly apart, and the layering is the point:

```text
SearchResult        what a search provider said about a URL
FetchedPage         what that URL actually returned
ListingObservation  what the returned document publishes about one offer
```

A snippet is a third party's description of a page; the page is the page; and
neither is a market listing. Collapsing any two of them would let a search
summary be reported as page evidence, or let a page's text be reported as a
price.

**`product_intelligence/providers/page.py`** holds the generic boundary:
`PageFetchRequest` (one field, `url`), `FetchedPage`, the `PageFetcher`
protocol, `PageFetchError`, and one subclass, `UnsafeFetchTargetError`. It is
stdlib contracts only — no network, no vendor, no credential, no configuration
— and it is scanned by the same guards as `search.py`.

The one subclass earns its place, and it is the only taxonomy this boundary
gets. Every other failure is something the outside world did — a timeout, a
403, a malformed response. `UnsafeFetchTargetError` is a decision *this code*
made: the destination was refused before, or instead of, being contacted. A
caller that cannot tell "we declined to go there" from "the site was down"
cannot report either honestly, and the two have opposite implications for
whether a retry could ever succeed.

`FetchedPage` keeps `requested_url` and `final_url` separately and requires
both, because a redirect is evidence: a listing reached at a different address
than the one a search result advertised is a fact a reviewer needs.

**`product_intelligence/providers/http_page.py`** holds the one concrete
fetcher, `HttpPageFetcher`, built on `urllib.request`. It is self-hosted and
free: no crawler service, no browser, no browser farm, no proxy pool, and no
per-page fee. That was deliberate method rather than thrift — part of what 3A
existed to establish is whether any of that is *needed*, and buying it in
advance would have answered the question by assumption.

Bounds, all defaults and all documented next to the code that enforces them:

| Bound | Default | Why |
| --- | --- | --- |
| Timeout | 10.0 s per hop | One unresponsive host cannot hold a caller open. |
| Redirects | 3 | Enough for `http`→`https`, apex→`www`, and canonical-slug hops; short enough that a loop ends quickly. |
| Response size | 5 MiB | Real retail pages run well past 1 MiB of markup. The limit **refuses rather than truncates**: a document cut mid-element would be parsed as though it were whole, and a parser silently reporting fewer listings because bytes went missing is worse than a fetch that failed loudly. |
| Content type | `text/html`, `application/xhtml+xml` | This fetcher retrieves a document for HTML extraction. Sniffing past a server's own declaration would be guessing. |

Destination safety, because a URL reaching this fetcher may have come from an
external search provider and is therefore untrusted:

* scheme, host presence, and absence of embedded credentials are enforced by
  the `PageFetchRequest` contract itself. A request that *cannot hold* a
  credential is a stronger guarantee than a fetcher that promises to strip one;
* the host is resolved with `socket.getaddrinfo`, and **every** address it
  resolves to must be publicly routable. One private address among several
  refuses the whole host — which address a later connection picks is not this
  code's decision to make;
* loopback, private, link-local (including the cloud metadata address
  `169.254.169.254`), unspecified, multicast, and reserved destinations are
  refused, as are IPv4-mapped and 6to4-embedded forms of them;
* **redirects are not followed by `urllib`.** The fetcher follows them itself
  and puts every hop through the identical URL and address checks. A public host
  redirecting to `http://127.0.0.1/` is the ordinary shape of this attack, and a
  library quietly following it would defeat the checks on the only hop that
  matters — the last;
* the opener is assembled by hand from HTTP and HTTPS handlers only. `urllib`'s
  `build_opener()` installs a `FileHandler`, an `FTPHandler`, an
  `UnknownHandler`, and a `ProxyHandler`; each is a way for a URL — or an
  ambient environment variable — to send this code somewhere other than the
  public page it was asked for;
* no cookie processor, no `Authorization` header, and no application or
  provider credential exists in this module to send. Three request headers are
  sent: `User-Agent`, `Accept`, `Accept-Encoding`;
* the method is GET, no form is submitted, and no JavaScript is executed.

**What this does not amount to, stated rather than implied.** These are
application-level checks and they are not network isolation. Two gaps are real:

1. **DNS time-of-check/time-of-use.** The name is resolved once for validation
   and `urllib` resolves it again when it connects. A DNS answer that changes
   between those moments — classic rebinding — is not prevented. Closing it
   means owning the socket: resolving once, connecting to the pinned address,
   and carrying the original hostname through TLS verification and the `Host`
   header. That is a change to how the connection is made, and it belongs to a
   phase hardening deployment (8C), not one learning what pages contain.
2. **Egress is otherwise unrestricted.** Anything this process can reach, it can
   still reach if a name resolves to a public address fronting something
   internal.

The durable answer to both is network-level — an egress allowlist or an
outbound proxy in the deployment. 3A makes the ordinary mistakes hard and says
plainly what it does not solve.

**Politeness.** The User-Agent identifies this application honestly, does not
impersonate a browser, and is never rotated. No bot-detection measure is worked
around. A 403 or a 429 is recorded as what the site said and is not retried
against — respecting it is both correct and the cheapest way to learn which
sources need a different approach.

#### What the real sample found

Seven public URLs were fetched, once each, on 2026-08-17. They were selected
from the ten organic results already recorded in
`tests/fixtures/providers/serper/real_verified_mz_ql23t800_organic_search.json`
— **no new search call was made in 3A**. One further live fetch was made to
validate the shipped smoke script: **eight live page requests in total, and
zero search-provider calls.**

| Source | Role | Outcome |
| --- | --- | --- |
| `www.samsung.com` | Manufacturer | `STATIC_FETCH_OK` — JSON-LD `Product` |
| `oempcworld.com` | Retailer | `STATIC_FETCH_OK` — JSON-LD `Product` + `Offer` |
| `www.exxactcorp.com` | Retailer | `STATIC_FETCH_OK` — no JSON-LD; full record in flat meta |
| `www.newegg.com` | Marketplace | `STATIC_FETCH_OK`, then `JS_SHELL_OR_NO_USEFUL_STATIC_DATA` |
| `www.fusionww.com` | Distributor | `OTHER` — soft block: HTTP 200 access-restricted interstitial |
| `www.serversupply.com` | Retailer | `BLOCKED_403` |
| `www.ebay.com` | Marketplace | `BLOCKED_403` |

Five of seven returned a document; three of seven yielded usable structured
product data. Both hard blocks were marketplaces or high-traffic retail, and
both were respected rather than worked around.

Five findings, classified by what they mean:

* **A published price can be broken and still be published.** The manufacturer
  page serves `"price": "undefined"` inside a well-formed `schema.org` `Offer` —
  a template that failed. *Relevant now, and decisive*: an extractor converting
  to `Decimal` at this layer would raise on a live page or silently drop the
  offer, and neither outcome is visible to a reviewer. This single observation
  is the strongest evidence for the phase's central rule that values stay text.
* **Structured data is not the same as complete data.** The manufacturer puts
  the MPN in `sku` and publishes no `mpn`. One retailer publishes `sku` as its
  own internal number (`501489`) and no `mpn` at all, with the part number
  present only inside the product title. Another publishes `mpn` as
  `"mpn:MZ-QL23T800"`, prefix included, and no currency anywhere on the page.
  *3B/3C concern*: reconciling those is normalization and matching, with
  recorded reasons — and 3A's job is to make sure the raw strings survive
  intact to be reconciled.
* **Flat meta tags are not a legacy curiosity.** One retailer page carries **no
  JSON-LD at all** and publishes its entire product record — `mpn`, `sku`,
  `brand`, `price`, `availability` — in `<meta name=...>` tags. *Relevant now*:
  this is the evidence that justified implementing the META path. Without it, a
  page plainly stating its part number and its price would have produced
  nothing.
* **One page can publish one offer twice.** A storefront carries `"1055.85"` in
  a JSON-LD `Offer` and `"1,055.85"` in `og:price:amount`. *Relevant now*: this
  is why meta extraction runs only when JSON-LD produced nothing. Running both
  would turn one offer into two observations, and 4A counts observations.
* **A block can arrive as a success.** One distributor returned **HTTP 200**
  with an "Access Restricted" interstitial whose JSON-LD is a `WebAPI` node
  telling an automated reader to call a different service instead of crawling.
  *Two consequences*: a classifier reading only status codes would have called
  this a successful fetch of a product page; and the content is **data, not
  instruction** (§19) — it was read, classified, recorded as a fixture, and the
  advertised API was not called.

#### Static-HTTP sufficiency: recommendation A

**Static HTTP is sufficient for initial 3A coverage. A browser fallback is not
yet justified**, and specifically must not be bought on the strength of one
blocked marketplace.

The evidence: three independent sources — one manufacturer and two retailers —
yielded complete raw observations through a plain, free, standard-library GET.
That is enough distinct sources to build 3B and 3C against. The two hard blocks
were `www.serversupply.com` and `www.ebay.com`; browser rendering would not
obviously help with either, because a 403 at the HTTP layer is an access
decision rather than a rendering problem, and defeating it means the
bot-evasion this project does not do. `www.newegg.com` is the one case a
headless browser plausibly *would* fix — it returned 200 and renders its product
data client-side — and one fixable source is not a reason to acquire browser
infrastructure, a dependency, and a deployment surface.

Recorded so a later phase does not have to rediscover it: if browser rendering
is ever justified, the evidence to look for is *client-rendered pages*
(`JS_SHELL_OR_NO_USEFUL_STATIC_DATA`) accumulating across sources, not blocks.
A free self-hosted headless browser would be the first thing to try, behind the
existing `PageFetcher` protocol, which is designed to accept one without
changing anything above it. There is no evidence at all yet for a paid managed
scraping provider.

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

Vendor selection for *generic* LLM provider integration is `UNDECIDED`. Model
orchestration across several models is `DEFERRED`.

**A. Existing frozen semantic runtime (FU3A/FU3B).** A production semantic
runtime already exists under `product_intelligence/semantic/`. FU3A defined
the contract, transport, and runtime with a pinned qualified model route
(amax/nemotron-3-super primary, vllm-262k/Qwen3.6-27B-262K fallback,
temperature=0.0, max_tokens=32768). FU3B wired that runtime into the research
execution pipeline for narrowly eligible identity candidates. This is not a
generic `LLMProvider` abstraction — it is a specific, frozen, production
semantic qualification runtime.

**B. Future generic LLM provider abstraction.** The `LLMProvider` boundary
abstraction described above — a generic, replaceable LLM provider interface
analogous to `SearchProvider` — is not yet implemented. It is the planned
boundary for future specification evidence extraction (6C), comparable-product
semantics (7A-7C), and any other LLM-assisted capability beyond the existing
frozen semantic runtime.

Status: `APPROVED / PLANNED` for the generic `LLMProvider` abstraction (B).
generic LLMProvider is not part of 6A or 6B. Earliest specification-extraction
evaluation is 6C, and even there only if recorded evidence demonstrates
deterministic extraction is insufficient. `IMPLEMENTED (FROZEN)` for the
specific semantic runtime (A) under FU3A/FU3B.

## 15. Research-run lifecycle

A research attempt is a first-class record with its own identity, so that a
report is durable, addressable, and re-openable. Phase 1A built exactly that
record and nothing more: it persists *that* research was requested and how the
attempt ended. It performs no research.

### 15.1 Where it lives

`product_intelligence/runs/` — a small Django application whose 1A model was
`ResearchRun` (AD-025). 4B added a second model, `PriceIntelligenceSnapshot`,
which persists the price intelligence result as opaque versioned JSON
(AD-050). Later phases added `ExecutionEvidenceRecord` (4C-A) and `AiAssistedReviewCandidate` (HUMAN-REVIEW). All four models live in `runs/` — the persistence package — so that no other layer carries a Django model. The reasoning is the layer table in §5:

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
invent a rule the contract has not agreed to. The description truncation / URL-length policy remains UNDECIDED; 5B did not establish a general truncation policy, where URL length limits actually bite.

A run is always first stored in `CREATED`; the state/timestamp shape of every
stored row is a database constraint (§15.5, AD-030).

There are **no caller fields**: no calling application, no order number, no
customer, no user, no transport metadata, and no provider. A persisted record is
precisely where caller-independence would quietly stop being true — one
"just for audit" column at a time — so a guard test asserts the complete field
list.

A run is created from a `ResearchRequest` and can rebuild one, so later phases
consume the contract rather than the database row.

### 15.2b The 4B snapshot model (PriceIntelligenceSnapshot)

4B added `PriceIntelligenceSnapshot` as the second model in `runs/`. It is a
run one-to-one primary key (AD-050):

| Field | Type | Meaning |
| --- | --- | --- |
| `run` | one-to-one to `ResearchRun` | The owning run (PK = FK; the ResearchRun UUID serves as snapshot identity) |
| `schema_version` | small int, >= 1 | Codec version for the payload |
| `payload` | JSONField | Opaque versioned `PriceAggregationResult` dict |
| `created_at` | timestamp | When the snapshot was persisted |

The `payload` is opaque: `runs/` stores it but does not interpret its
structure. The codec in `research/price_result_codec.py` transforms the
research-layer contract to and from JSON. `runs/` imports no part of
`research/`.

`PriceIntelligenceSnapshot.created_at` is persistence time — it records
when the price result was stored, not when any source was fetched.
4B does NOT establish or persist source retrieval time through
`ListingObservation`. Execution/fetch provenance and any execution-level
retrieval timestamps remain part of 4C's evidence-persistence design.

Cascade delete: deleting the `ResearchRun` deletes its snapshot.

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
as of 4C-B, execution orchestration exists but there is no background processing,
no queue, and no worker, so no second writer exists for a single run. The honest
fix — a conditional update, row locking, or both — belongs to the phase that
first introduces a concurrent writer and can test it. Adding locking now would
guard against a scenario the system cannot yet produce.

Status: `IMPLEMENTED` (1A) for the record, its identity, its state machine, its
timestamps, and its migration; (1B) for the report at `/research/<id>`, which
reads a run and renders it; (4C-B) for the execution orchestration layer
that moves a run from CREATED through the full pipeline to COMPLETED or FAILED;
and (4C-C) for web execution wiring so the web form triggers execution
synchronously. The report view is read-only (GET only): it starts nothing,
transitions nothing, and writes no timestamp. Review actions (confirm/reject/undo)
are POST endpoints handled by the runs-owned review service. The web form
creates a `CREATED` run, calls `execute_research_run()`, and redirects to the
report.

## 16. Price-intelligence direction

Planned pipeline, all deterministic:

1. **Listing extraction** (3A) — fetch a candidate URL safely and extract raw
   listing observations from what it publishes (§13.6, §16.1). `IMPLEMENTED`.
2. **Normalization** (3B) — price, currency, condition, availability, seller
   (§16.2). `IMPLEMENTED`. Quantity, pack size, and unit price remain
   unimplemented: no recorded fixture publishes raw evidence for them (§16.2).
3. **Match and reject** (3C) — classify each listing with an
   `IdentityMatchType`, using the deterministic part-number comparison from
   §12.1 for the exact and normalized cases; record every rejection with a
   reason. Partial-overlap classification is 3C's own work — 2A does not
   attempt it.
4. **Aggregation** (4A) — count, low, median, high, and an observed
   low/high market range (when count >= 3), computed from accepted
   listings only.
5. **Orchestration** (4C) — coordinate one `ResearchRun` end-to-end: query
   generation, candidate selection, search invocation, page fetching,
   extraction, normalization, matching, aggregation, result persistence,
   lifecycle transitions, failure semantics, and duplicate paid-call
   protection. `IMPLEMENTED` (4C-B). Web form wiring `IMPLEMENTED` (4C-C).
6. **Report** (4B) — persist the `PriceAggregationResult` as a
   `PriceIntelligenceSnapshot` and present the numbers together with the
   listings and the rejections that produced them. `IMPLEMENTED`.

Rules:

* Only accepted, part-number-level matches contribute to a price conclusion
  unless a documented rule says otherwise.
* A small sample yields a low confidence and says so; it does not yield a
  narrow-looking range.
* Zero accepted listings yields `UNKNOWN`, never an estimate.
* Every displayed number is reproducible from the retained evidence.

Which aggregate constitutes "market price" remains `UNDECIDED` — no global
market-price selection or cross-bucket policy exists. Outlier handling is
settled: 4A has no automatic outlier removal; extreme but accepted prices
expand the observed low/high. A more advanced outlier policy remains deferred.

Isolated deterministic primitives through 4A are implemented and answer
steps 1 through 4. Aggregation computes bucket-level observed statistics:
count, low, median, high, and (when count >= 3) market range, per
exact currency and known condition. No automatic outlier removal exists,
and no global market-price is selected. The execution orchestration that
connects these steps, persists the result, and transitions the run lifecycle
is 4C (AD-051). The read-only web report that presents a persisted result
is 4B (AD-050) and is now implemented.

Binding constraints on the phases above, recorded in 2B so each phase starts
with them rather than rediscovering them:

**3A — extraction may be source-specific, business rules may not.** Generic
extraction over search results will not be enough for every source. Once real
recorded fixtures (§13.3) *show* that, 3A may add narrowly scoped
source-specific extraction strategies alongside the generic path. They stay
outside the domain and outside business rules: a strategy knows how one site
writes a price, and nothing else. None of it may be written before fixtures
justify it. A price hint from a provider (§13.1) is an observation and not an
extraction result — the two must not be conflated.

*Outcome (3A):* **no source-specific strategy was written.** No recorded fixture
justified one — the page that defeated generic JSON-LD was covered by adding a
generic *meta* path, which serves any page using that convention rather than one
site, and the pages that yielded nothing publish no static product data that any
per-source selector could reach. The permission stands unused and the bar is
unchanged: a real fixture first, then a strategy (§16.1).

**3B — normalization is not conversion.** 3B explicitly normalizes price,
currency representation, condition, availability, and seller. "Normalize
currency" means recording that an observation is in EUR in a consistent form;
it is **not** converting EUR to USD. No implicit FX conversion happens
anywhere, in 3B or later: a rate is a market observation of its own, with its
own source and its own retrieval time, and silently applying one would
manufacture a number no evidence supports.

*Outcome (3B):* implemented as described (§16.2), with one narrowing found
during the phase rather than assumed going in. Quantity, pack size, and unit
price were **not** normalized: no recorded 3A fixture publishes raw evidence
whose semantics mean "this offer sells N units for this price" — inventory
counts, minimum-order quantities, and capacity figures are not pack size, and
none of the five fixtures publishes anything else in that shape either.
`ListingObservation` was not speculatively extended to carry fields nothing
produces, and no quantity is guessed from a title. The absence is recorded as
a finding, not hidden as an oversight (§16.2).

**4A — aggregation requires demonstrable comparability.** An aggregate over
observations that are not comparable is a wrong number with a confident
presentation. At minimum:

* mixed currencies may not silently share one aggregate;
* a multi-pack total price may not be compared with a single-unit price without
  unit normalization;
* new, used, refurbished, and unknown-condition offers may not be blindly mixed
  into one market band.

The same rule governs classes of evidence: internal or distributor pricing and
public market pricing are different observations of different things and do not
automatically belong in one aggregate (§13.4).

4A is IMPLEMENTED; §16.4 records the implementation.

### 16.1 What 3A implemented

The first step of the pipeline, and only the first step: **a real public URL
becomes raw listing observations**, with the page preserved in between.

```text
recorded search fixture  ->  HttpPageFetcher  ->  FetchedPage
                                                     |
                                                     v
                                        extract_listing_observations()
                                                     |
                                                     v
                                        ListingObservation, ...
```

The fetch half is §13.6. This section is the extraction half, which lives in the
research core: `product_intelligence/research/listings.py` (the contract) and
`product_intelligence/research/extraction.py` (the extractor).

**The two halves do not import each other.** `extract_listing_observations`
takes a document *string* and a `source_url`, not a `FetchedPage`. The research
core therefore stays free of the provider layer exactly as the 2A guards
require, opens no socket, and can be exercised with a string literal; the
fetcher knows nothing about listings. They meet only in code that holds both —
today, one manual script.

#### The raw contract

`ListingObservation` is frozen, and every field except `source_url` and
`extraction_method` is optional **raw text**:

| Field | What it is |
| --- | --- |
| `source_url` | Where the observation came from — required |
| `extraction_method` | `JSON_LD` or `META`, provenance only |
| `product_title` | As published |
| `manufacturer_part_number_text` | The MPN *field* a page published, verbatim |
| `sku_text` | The SKU field, verbatim |
| `brand_text` | Brand name, from a string or a nested `name` |
| `price_text` | Characters a page published in a price position |
| `currency_text` | As published — never inferred |
| `availability_text` | As published — no vocabulary |
| `condition_text` | As published — no vocabulary |
| `seller_text` | As published |
| `offer_url_text` | A URL the offer itself published, if any |
| `raw_reference` | The structured node, preserved opaquely (AD-040) |

A test asserts the exact field list. There is **no numeric price field**, and
that absence is the safeguard — the same argument that kept one off
`SearchResult` in 2B (AD-039). There is also no accepted/rejected flag, no
rejection reason, no score, and no confidence: 3C decides, with a reason.

`offer_url_text` is present because a page can price several variants at
several addresses; without it, two observations from one page are
indistinguishable in their traceability. Fields the contract deliberately does
*not* carry — a GTIN, a category, a description, a price-valid-until date — all
survive inside `raw_reference`, which is how the contract stays small without
discarding evidence.

`ExtractionMethod` has exactly two members because two mechanisms exist. A
third, for a narrowly scoped per-source strategy, is described below and is
deliberately **not declared**: a vocabulary member nothing produces is a
placeholder for unbuilt behaviour. Provenance is also not trustworthiness — a
JSON-LD price is still one page's claim, and the manufacturer fixture proves it
by publishing `undefined` in exactly that position.

#### What the extractor reads

**JSON-LD first.** `application/ld+json` blocks are located with an
`HTMLParser` rather than a regular expression — a regular expression over HTML
gets the easy cases right and then mis-slices a page with a `</script>` inside a
string literal. `schema.org` `Product` nodes are found through the three real
shapes (a bare object, a top-level list, an `@graph` wrapper), and their
`Offer` / `AggregateOffer` children are mapped.

**Flat meta second, and only when JSON-LD produced nothing.** The
`name="price"` / `mpn` / `sku` / `brand` / `availability` family and the
OpenGraph `og:price:amount` / `og:price:currency` pair. Both were added against
real pages that publish them, not in anticipation.

**Never arbitrary rendered text, and never may be.** There is no scan of
visible HTML for currency-shaped substrings. The recorded storefront fixture
contains fourteen distinct dollar amounts: a free-shipping threshold, financing
plan bounds, a per-instalment amount (`price_per_term: $527.92`), four
recommended products in *markup identical* to the product's own price element,
and — somewhere among them — the real price. A first-match rule, a
lowest-match rule, and a largest-match rule each return a wrong number from that
page with complete confidence. The same reasoning already excluded snippet
prices in 2C: the recorded search response carries
`"$2,135.00 $2,700.00 You Save: $565.00"` and `"$2,145.00 As low as $102.98/mo"`,
where a current price, a struck-through list price, a saving, and a monthly
instalment are four different numbers and nothing in the text says which is
which.

**Never a number.** JSON is parsed with `parse_float=str` and `parse_int=str`,
so a price written as the JSON number `1055.85` arrives as the text `"1055.85"`
rather than as a float that has already discarded its representation. A guard
test forbids the extraction module from importing `decimal`, `statistics`, or
`math` at all.

**Never a decision.** No listing is accepted or rejected, no observation is
deduplicated or ranked, and the 2A comparator is **not called** — an extractor
that decided identity would be judging its own evidence. That the raw published
MPN *could* later be handed to the comparator is demonstrated in a test, and
nowhere in the extraction code.

#### Deliberate refusals, each with a real reason

* **An `AggregateOffer` yields no `price_text`.** A low and a high across
  sellers is a range, not this product's price; picking either end would be the
  lowest-wins rule wearing a schema name. The node survives in `raw_reference`.
  If it publishes its own concrete offers, those are read — that is reading, not
  inference.
* **Several offers do not collapse into one.** A page publishing three offers is
  publishing three; collapsing them would silently reduce a count 4A depends on.
* **A `Product` with no offer still yields an observation.** A manufacturer page
  publishing a part number and no price is exactly what a manufacturer page
  should contribute, and dropping it would leave only retailers.
* **Mixed currencies are recorded side by side and never combined.** No rate, no
  conversion, no blending — in this phase or any later one (§16).
* **A malformed JSON-LD block is skipped and its siblings are unaffected.**
  Losing a page's data to someone else's typo would be an outage.
* **A non-`Product` node is ignored rather than guessed at.** The sampled pages
  carry `Organization`, `BreadcrumbList`, `ImageObject`, and `WebAPI` nodes.
* **Traversal is depth- and count-bounded.** Untrusted JSON nests as deeply as
  its author likes.
* **Zero observations is a valid answer**, and it is the right one for the two
  sampled pages that publish nothing readable. A page this extractor cannot read
  is recorded as unreadable, never filled in from a search snippet.

#### No source-specific extractor was added

§16 permits a narrowly scoped per-source strategy *once a real fixture shows the
generic path is insufficient*. No fixture showed that. The one page that
defeated generic JSON-LD (`www.exxactcorp.com`) was fully covered by adding the
generic **meta** path, which serves any page using that convention rather than
one site. The two pages that yielded nothing publish no static product data at
all, which no per-source selector can fix. Writing one anyway would have been
line count without evidence, so the permission stands unused and the option
stays open.

#### Recorded fixtures

Five, under `tests/fixtures/pages/`, each derived from one live fetch and
documented in that directory's README with its source, date, outcome, what was
retained, and what was removed. Four are **reduced**: the live documents run
from 198 KB to 850 KB and are almost entirely navigation, styling, scripts, and
marketing copy. Each reduction was verified by running the extractor over the
full document and over the reduced fixture and confirming the observations are
identical — 1.85 MB of real pages became 14 KB of test evidence with no change
in behaviour. The fifth is kept in full because it is 1.9 KB and reducing it
would remove the point.

Synthetic edge cases live in a separate file, written inline and labelled, so a
recording and a fake can never be confused (AD-041).

#### What 3A explicitly did not do

* **No normalization (3B).** No `Decimal`, no currency vocabulary, no quantity
  or pack-size parsing, no unit price, no condition or availability taxonomy, no
  shipping arithmetic, no seller normalization, and no FX of any kind.
* **No matching or rejection (3C).** No listing is compared to a request,
  accepted, or rejected, and no rejection reason is recorded.
* **No aggregation (4A).** No count, low, median, high, or range. **No market
  price is computed anywhere.**
* **No integration (at 3A).** `runs/` and `web/` imported no part of `providers/` or of
  the extraction core. A submitted run was `CREATED` and the report page
  stated research execution was not connected. *(4C-B later implemented backend
  orchestration; 4C-C later connected the web form to the executor.)*
* **No caching, no LLM, no Google Shopping, and no search call.**

Status: `IMPLEMENTED` (3A) for safe static page fetching, deterministic raw
listing extraction, and the recorded real-page fixtures. `IMPLEMENTED` (3B) for
deterministic listing normalization, described in full below. **No market
price works, and none is claimed.**

### 16.2 What 3B implemented

The second step of the pipeline, and only the second: **one raw
`ListingObservation`'s commercial attributes become a deterministic,
comparable representation — or a recorded reason they could not.**

```text
ListingObservation  ->  normalize_listing_observation()  ->  NormalizedListingObservation
```

The contract and the function both live in the research core:
`product_intelligence/research/normalization.py`. Like extraction (3A), it
takes the 3A contract directly rather than a `FetchedPage`, imports nothing
from `providers/`, and performs no I/O — the same guard tests that scan every
file under `research/` for stdlib-only imports, no network or filesystem
access, and no persistence/provider/benchmark import cover this module by
construction, and were extended with 3B-specific guards proving `decimal` is
used here and nowhere else in the core (`tests/research/
test_listing_normalization_boundaries.py`).

#### The normalized contract

`NormalizedListingObservation` is frozen and carries:

| Field | What it is |
| --- | --- |
| `observation` | The exact raw `ListingObservation` this was built from — a reference, never a copy |
| `price_amount` | `Decimal \| None` |
| `currency_code` | `str \| None` — an ISO-style three-letter code, never converted |
| `availability` | `NormalizedAvailability` — a small controlled vocabulary, `UNKNOWN` included |
| `condition` | `NormalizedCondition` — a small controlled vocabulary, `UNKNOWN` included |
| `seller_name` | `str \| None` — whitespace-normalized only |
| `normalization_issues` | `tuple[NormalizationIssue, ...]` |

A reviewer can always get from a normalized field back to the raw text that
produced it, including when that raw text produced nothing:
`normalized.price_amount` may be `None` while `normalized.observation
.price_text` is `"undefined"`, and `normalization_issues` explains the gap.
There is no `accepted`, `rejected`, `valid_listing`, `identity_match`,
`confidence`, `should_use_for_price`, or `aggregate_eligible` field, and no
`min`/`max`/`median`/`average`/`estimate` — a test asserts the exact field
list is free of every one of them. 3B decides nothing about whether an
observation belongs to the requested product, and computes no statistic over
more than one. The constructor carries one narrow invariant beyond type
checks: a non-`None` `currency_code` must be one of the codes this module's
own currency logic can produce — a value this module could not itself have
normalized to (a lowercase code, an unmapped symbol) is a caller defect, not
a state the type should be able to represent silently.

`NormalizationIssue` (`field`, `code`, `raw_value`, `reason`) explains one
field's failure to normalize, never the listing's. Its vocabulary,
`NormalizationIssueCode`, has exactly six members —
`INVALID_PRICE`, `AMBIGUOUS_PRICE`, `UNRECOGNIZED_CURRENCY`,
`CONFLICTING_CURRENCY`, `UNRECOGNIZED_AVAILABILITY`,
`UNRECOGNIZED_CONDITION` — because those are the six kinds of abstention this
module actually produces. `CONFLICTING_CURRENCY` covers the one case where two
*present* pieces of evidence — a currency embedded in `price_text` and a
separately published `currency_text` — disagree, distinct from
`UNRECOGNIZED_CURRENCY`'s single unmapped value. `INVALID_QUANTITY`,
`INVALID_PACK_SIZE`, and `UNIT_PRICE_NOT_COMPUTABLE` are deliberately absent:
nothing in this module computes a quantity, a pack size, or a unit price
(below), and a vocabulary member nothing produces is a placeholder for
unbuilt behaviour — the same rule `ExtractionMethod` (3A) already established
for its own vocabulary.

#### Price: a conservative, single-amount grammar

Raw `price_text` becomes a `Decimal` only when it names one unambiguous
amount, optionally wrapped by a currency symbol (`$ € £ ¥`) or a known
three-letter code (`EUR 1055.85`), with comma-grouping accepted **only** in
exact groups of three digits:

```text
1055.85       valid  ->  Decimal("1055.85")
1300.53       valid  ->  Decimal("1300.53")
1,055.85      valid  ->  Decimal("1055.85")
10,055.85     valid  ->  Decimal("10055.85")
$1,055.85     valid  ->  Decimal("1055.85")   (symbol stripped to locate the amount)
EUR 1055.85   valid  ->  Decimal("1055.85"), embedded currency EUR
1055.85 EUR   valid  ->  Decimal("1055.85"), embedded currency EUR
```

Everything else abstains rather than guessing, classified into one of two
issue codes: `AMBIGUOUS_PRICE` when the text names a range, a discount, or a
recurring payment (`"from $399"`, `"$399 - $449"`, `"$33/mo"`, `"You save
$565"`, `"20% OFF"`) — checked by a small set of marker phrases and by
counting how many amount-shaped tokens the text contains — and
`INVALID_PRICE` otherwise (`"undefined"`, `"N/A"`, `"Call for price"`,
`"1.055,85"`, `"1,00,055"`). Neither a US-style nor a European-style reading
is ever guessed at: a period used as a thousands separator and a grouping
that is not exactly three digits both fail to parse rather than being
silently reinterpreted, and `"undefined"` becomes `None` plus a recorded
issue, never `Decimal("0")`. Money is `Decimal` throughout; a guard test
parses the module's own AST and asserts it never calls `float(...)`.

A currency decoration may appear on **one side only**. Text decorated on both
sides (`"EUR 100 USD"`, `"$100 EUR"`) also classifies `AMBIGUOUS_PRICE` —
`price_amount` stays `None` — whether or not the two decorations happen to
agree, because accepting it would mean either picking a side or inferring an
agreement the text does not structurally establish.

#### Currency: conservative mapping, reconciled evidence, explicitly no FX

A small fixed set of ISO-style codes (`USD`, `EUR`, `GBP`, and sixteen
others actually exercised by tests) normalizes case-insensitively to its
uppercase form; `€` and `£` map to `EUR`/`GBP` because each names one
currency unambiguously. **`$` and `¥` are never mapped** — both are shared by
several live currencies, and mapping either would be exactly the inference
the phase instructions forbid, embedded in `price_text` or published
separately. A price and its currency normalize independently: `price_amount`
can be set with `currency_code` absent (a real 3A fixture case — no currency
published anywhere on the page), and either can be `None` while the other is
not.

Independent does not mean **contradictory evidence is silently ignored**. A
single-sided currency decoration inside `price_text` is real evidence and is
reconciled against `currency_text`: if only one source names a currency, it is
used; if both name the same one, it is used; if they name *different*
currencies (`price_text="EUR 100"`, `currency_text="USD"`), neither is chosen
— `currency_code` stays `None` and a `CONFLICTING_CURRENCY` issue records the
disagreement, and `price_amount` still normalizes, because the amount and its
comparability are separate questions. No conversion rate, live or hardcoded,
exists anywhere in this module; two observations in different currencies stay
two observations in different currencies; nothing compares, sorts, or picks a
minimum or maximum between them.

#### Availability and condition: small vocabularies, `UNKNOWN` on anything unmapped

`NormalizedAvailability` (`IN_STOCK`, `OUT_OF_STOCK`, `PREORDER`,
`BACKORDER`, `LIMITED`, `DISCONTINUED`, `UNKNOWN`) and `NormalizedCondition`
(`NEW`, `USED`, `REFURBISHED`, `DAMAGED`, `UNKNOWN`) map the `schema.org`
enumeration values (with or without the `http(s)://schema.org/` prefix) and a
small set of conservative plain-text spellings. Both maps deliberately
**exclude** `"true"` / `"false"` and prose like `"open box"` or `"like new"`:
a real 3A fixture publishes `availability_text="false"`, which is no
`schema.org` term and is not evidence of any particular stock state, and
guessing it into `OUT_OF_STOCK` would be exactly the fabricated certainty
this phase exists to avoid. Unmapped text produces `UNKNOWN` plus a recorded
`UNRECOGNIZED_AVAILABILITY` / `UNRECOGNIZED_CONDITION` issue; text absent
from the raw observation produces `UNKNOWN` with **no** issue, because
nothing was published to fail to normalize.

#### Seller: representation cleanup only, never entity resolution

Surrounding whitespace is removed and an internal whitespace run collapses to
one space. Nothing else changes — no case folding, no punctuation removal,
and no decision that `"Amazon.com"` and `"Amazon"` name one seller. Deciding
that is entity resolution, which this phase does not attempt.

#### Quantity, pack size, and unit price: an evidence gap, not an oversight

The roadmap describes 3B eventually normalizing quantity, pack size, and unit
price. An audit of every field in every one of the five recorded 3A fixtures
(`tests/fixtures/pages/`) found no structured field on any of them whose
semantics mean "this offer sells N units for this price" — no inventory
count, minimum-order quantity, or capacity figure (`"3.84TB"`) is pack size,
and `ListingObservation` itself carries no raw `quantity_text` or
`pack_size_text` field for a normalizer to read. Per the phase instructions,
that absence is not solved by guessing: `ListingObservation` was **not**
speculatively extended, no quantity is inferred from a product title, and
`NormalizedListingObservation` carries no `quantity`, `pack_size`, or
`unit_price` field. The finding — not the guess — is what 3B contributes on
this point, and it is 3C or a later phase's to revisit if a fixture ever
shows the evidence.

#### What 3B explicitly did not do

* **No identity comparison.** The published MPN and SKU fields are untouched
  — not normalized, not stripped of a prefix, not compared. `identity.py` is
  not imported (§24 of the phase instructions; a guard test asserts it).
* **No listing acceptance or rejection (3C).** No `accepted` field, no
  rejection reason, no match type, no score. A normalized price does not
  imply a valid listing.
* **No aggregation (4A).** No count, low, median, high, range, or estimate,
  and no cross-currency comparison of any kind.
* **No integration (at the end of 3B).** `runs/` and `web/` imported no part of
  `research`'s new module — the existing guard that checks the whole
  `product_intelligence.research` namespace already covered it. At the end of
  3B, a submitted run was still `CREATED`. *(4C-B later implemented backend
  orchestration; 4C-C later connected the web form to the executor.)*
* **No quantity, pack size, or unit price** — see above.
* **No live call of any kind.** Every test runs against the same recorded 3A
  fixtures or inline synthetic text; the normal `pytest` run makes zero
  network requests, exactly as before.

Status: `IMPLEMENTED` (3B) for deterministic price, currency, availability,
condition, and seller normalization, and for the quantity/pack-size evidence
audit. 3C (next) accepts or rejects listing identity. No aggregation or
market price exists yet.

### 16.3 What 3C implemented

The third step of the pipeline, and only the third: **each normalised listing
is classified against the requested part number, and a decision is recorded**.

```text
ResearchRequest  +  NormalizedListingObservation
        ↓
  evidence detection + deterministic MPN comparison
        ↓
  ACCEPTED / REJECTED / UNDECIDED  +  match type  +  reason
```

The contract and the function live in the research core:
`product_intelligence/research/matching.py`.

#### `ListingIdentityAssessment`

Frozen, auditable dataclass carrying:

* `normalized_listing` — the exact `NormalizedListingObservation` (which itself
  carries the raw `ListingObservation`).
* `requested_part_number` — the MPN the request was looking for.
* `candidate_part_number_raw` — the raw candidate identifier from the listing.
* `candidate_part_number_compared` — the candidate text after any wrapper
  cleanup (may differ from raw).
* `candidate_evidence_source` — `EXPLICIT_MPN_FIELD`, `SKU_FIELD`,
  `TITLE_TEXT`, or `NONE`.
* `match_type` — `EXACT`, `NORMALIZED_EXACT`, `PARTIAL`, or `UNKNOWN`.
* `decision` — `ACCEPTED`, `REJECTED`, or `UNDECIDED`.
* `rejection_reason` — `NO_REQUESTED_MPN`, `NO_EXPLICIT_MPN_EVIDENCE`,
  `MPN_MISMATCH`, or `PARTIAL_MPN_ONLY` (always present for `REJECTED` /
  `UNDECIDED`; always `None` for `ACCEPTED`).

#### Constructor invariants

The dataclass carries a `__post_init__` that enforces the 3C state invariants
on *any* construction, not just the builder:

* `ACCEPTED` requires `EXPLICIT_MPN_FIELD` evidence, `EXACT` or
  `NORMALIZED_EXACT` match type, and no rejection reason.
* `REJECTED` requires a non-`None` rejection reason.
* `UNDECIDED` requires `UNKNOWN` match type and `NO_REQUESTED_MPN` reason.
* `PARTIAL` match type must always pair with `REJECTED` decision and
  `PARTIAL_MPN_ONLY` reason.

Impossible combinations raise `ValueError` at construction. No override
framework exists.

#### Acceptance policy

A listing is `ACCEPTED` **only** when:

1. An explicit manufacturer-part-number field exists on the listing.
2. After narrow `mpn:` wrapper cleanup, the existing 2A comparator returns
   `EXACT` or `NORMALIZED_EXACT`.

No other evidence source — SKU, title text, URL — automatically establishes
identity. Unknown beats fabricated certainty.

#### Narrow `mpn:` wrapper cleanup

One recorded fixture (`exxactcorp_pm9a3_mz_ql23t800.html`) publishes its MPN as
`"mpn:MZ-QL23T800"`. The literal `mpn:` prefix is a field-label wrapper, not
part of the identifier. A narrow cleanup strips this prefix (case-insensitively)
from an explicit MPN field only — never from a SKU, never from title text, never
generalized to arbitrary `key:` stripping. The 2A normalizer is unchanged.

#### Empty / structure-only explicit MPN

When the explicit MPN field carries no part-number content after cleanup
(e.g. `"mpn:"` yielding `""`, or a structure-only value like `"---"`), the
candidate is classified as `UNKNOWN` with `REJECTED` /
`NO_EXPLICIT_MPN_EVIDENCE` — not `MPN_MISMATCH`, because there is no
different candidate MPN to mismatch against.

#### SKU and title text

SKU field (`REJECTED` with `NO_EXPLICIT_MPN_EVIDENCE`) and title text
(`REJECTED` with `NO_EXPLICIT_MPN_EVIDENCE`) are recorded for auditability but
never produce `ACCEPTED`. Even if a SKU equals the requested MPN
character-for-character, it stays rejected — the two are semantically distinct
fields.

#### PARTIAL boundary rule

When the requested MPN and the candidate MPN are not `EXACT` or
`NORMALIZED_EXACT` but one is a strict prefix of the other at a preserved
identifier boundary (`-`, `_`, `/`, `.`) — e.g. `MTFDKCC3T8TFR` vs
`MTFDKCC3T8TFR-1BC1ZABYY` — the match type is `PARTIAL` and the decision is
`REJECTED` with `PARTIAL_MPN_ONLY`. A mid-alphanumeric-token prefix
(`ABC123` vs `ABC1234`) is not classified as partial; it stays `UNKNOWN`.
PARTIAL is explicitly rejected — it is not price-eligible identity evidence.

#### Description-only request

When the request carries no MPN, the decision is `UNDECIDED` with
`NO_REQUESTED_MPN` — not `REJECTED`, because there is nothing to reject
against.

#### Rejected evidence remains reachable

Every assessment holds the full `NormalizedListingObservation`, which holds the
raw `ListingObservation`. A reviewer can trace the raw MPN text, the compared
text, the evidence source, the match type, the decision, and the rejection
reason back through the full chain to the raw page HTML.

#### Commercial normalization issues do not decide identity

Price, currency, availability, condition, and seller issues are not identity
reasons. `IdentityRejectionReason` carries no `BAD_PRICE`, `WRONG_CURRENCY`,
or `UNRECOGNIZED_CONDITION` member.

#### What 3C did not do

* **No LLM call.** All decisions are deterministic string comparisons against
  the existing 2A comparator. No model, no prompt, no embedding.
* **No persistence.** No model, no migration. The assessment is a pure function
  result.
* **No orchestration (at the end of 3C).** No search, no fetch, no extraction,
  no normalization, no run transition. It takes values it is handed. *(4C-B
  later implemented backend orchestration wiring 3C into the pipeline;
  4C-C later connected the web form to the executor.)*
* **No aggregation (4A).** No count, low, median, high, or range.
* **No integration (at the end of 3C).** `runs/` and `web/` import no part of
  `providers/` or of the matching core. A submitted run was still `CREATED`.
* **No description semantics.** The description field is carried but never
  read. 6A itself does not interpret request descriptions. Any future
description/category/comparable semantic interpretation belongs to a later
explicitly approved phase.
* **No manufacturer trust rules.** No per-manufacturer normalization profiles.
* **No fuzzy matching, edit distance, or character-confusion tables.**
  `O`/`0` and `I`/`l`/`1` are never interchanged.

Status: `IMPLEMENTED` (3C) for deterministic MPN matching and listing rejection
against the five recorded real-page fixtures plus synthetic and adversarial edge
cases. `IMPLEMENTED` (4A) for isolated deterministic price aggregation.
`IMPLEMENTED` (4B) for price-result persistence via `PriceIntelligenceSnapshot`
and the read-only web report that presents the full result: buckets, contributing
evidence, and excluded listings. `IMPLEMENTED` (4C-B) for backend orchestration:
the `execution/` package connects search through extraction, normalization,
matching, and aggregation with atomic final publication. **4C-C is IMPLEMENTED
(frozen):** the web form creates a `CREATED` run, triggers execution via
`execute_research_run()`, and redirects to the report with the full result.

### 16.4 What 4A implemented

4A added `product_intelligence/research/aggregation.py`: the deterministic
price aggregation over identity-accepted listings, together with its canonical
contracts and regression test suite.

**Input**: a `ResearchRequest` and a tuple of `ListingIdentityAssessment`
objects produced by 3C.

**Output**: a single `PriceAggregationResult` containing zero or more
`PriceAggregateBucket` objects, zero or more `PriceAggregationExclusion`
objects, and a `VerificationStatus`.

**What aggregation is**: Given N assessed listings, determine which ones
belong to the same comparable price pool and compute statistics over that pool.
Not price intelligence, not market analysis, not recommendation — just
deterministic arithmetic over a validated, auditable, frozen input.

**What aggregation is not**: market intelligence, price recommendation, buyer
advice, competitive analysis, price monitoring, or vendor comparison.

*Outcome (4A):* implemented as described below. 4A computes arithmetic over
supplied normalized offer prices — bucket-level count, low, median, high, and
market range — but performs no research, orchestrates no pipeline, and chooses
no global market price. No run transitions — a submitted run is still `CREATED`.
The aggregation function is pure, deterministic, and auditable; every input
appears in exactly one bucket or exclusion.

#### 4A Contracts

`aggregate_listing_prices(request, assessments)` — takes a `ResearchRequest` and
a tuple of `ListingIdentityAssessment` objects. Returns a
`PriceAggregationResult`. Input must be a `tuple` (not a list); a
`ResearchRequest` (not a plain tuple).

`PriceAggregationResult` — immutable container holding:
* `request` — the `ResearchRequest` this aggregation was performed for.
* `assessments` — the input tuple, echoed verbatim.
* `buckets` — zero or more `PriceAggregateBucket` objects, one per distinct
  `(currency_code, condition)` group.
* `exclusions` — zero or more `PriceAggregationExclusion` objects, each
  explaining why one input assessment is not in a bucket.
* `verification_status` — `UNKNOWN` (zero buckets), `VERIFIED` (exactly one
  bucket), `AMBIGUOUS` (more than one bucket).

Every input assessment appears in exactly one bucket or exclusion, enforced
at construction with `Counter` (not `set`) so that multiplicity errors —
the same object appearing twice in output — are caught.

**Request provenance**: every assessment's `requested_part_number` must equal
the result's `request.manufacturer_part_number` exactly.

**Unique bucket keys**: at most one bucket per exact
`(currency_code, condition)` in a result.

`PriceAggregateBucket` — one comparable price group. Fields:
* `currency_code` — non-empty string (e.g. `"USD"`, `"EUR"`).
* `condition` — `NormalizedCondition` (never `UNKNOWN` — unknown condition is
  excluded, not grouped).
* `assessments` — tuple of accepted `ListingIdentityAssessment` objects.
* `count` — `int` (not `bool`) equal to `len(assessments)`.
* `low`, `median`, `high` — `Decimal`, recomputed from assessment prices.
* `market_range_low`, `market_range_high` — both `None` (count < 3) or both
  `Decimal` (count >= 3). Never one-sided.
* `confidence` — `ConfidenceLevel`: `LOW` (count 1-2), `MEDIUM` (count >= 3).

**Type enforcement**: `count` must be `int` (not `bool`); `low`, `median`,
`high` must be `Decimal`; `market_range_low`, `market_range_high` must be
`Decimal` or `None` (paired); `confidence` must be `ConfidenceLevel`.

Statistics are recomputed from `assessments` in `__post_init__` and compared
against supplied values. Mismatch raises `ValueError`.

`PriceAggregationExclusion` — one explanation for a missing assessment.
Fields: `assessment`, `reason` (`PriceAggregationExclusionReason`).

`PriceAggregationExclusionReason` — ordered enum:
1. `IDENTITY_NOT_ACCEPTED` — decision was `REJECTED` or `UNDECIDED`.
2. `NO_NUMERIC_PRICE` — accepted but no parseable `Decimal` price.
3. `NO_COMPARABLE_CURRENCY` — accepted, has price, but no currency.
4. `UNKNOWN_CONDITION` — accepted, has price and currency, but condition is
   `UNKNOWN` (not confidently mapped).

A listing with multiple ineligibilities is excluded for the first matching
reason (precedence order).

* **`DUPLICATE_SUSPECT` is not implemented.** Exact duplicate INPUT VALUES
  (two `ListingIdentityAssessment` objects equal by value) are refused at the
  input boundary with `ValueError`. No broad market-listing deduplication
  exists — genuinely different assessments with the same price, currency, and
  condition are not duplicates because their evidence (source, seller,
  observation) differs.

#### 4A Decision Rules

Eligibility for a bucket (fixed precedence):
1. `IDENTITY_NOT_ACCEPTED` if decision is not `ACCEPTED`.
2. `NO_NUMERIC_PRICE` if accepted but `price_amount` is `None`.
3. `NO_COMPARABLE_CURRENCY` if accepted, has price, but no currency.
4. `UNKNOWN_CONDITION` if accepted, has price and currency, but condition is
   `UNKNOWN`.
5. Eligible — enters the `(currency_code, condition)` bucket.

Exact duplicate input values: two `ListingIdentityAssessment` objects that
compare equal by value (frozen dataclass `__eq__`) raise `ValueError`.
The check is **value-based**, not identity-based. A dataclass with identical
fields from two separate constructor calls is still a duplicate.

No other deduplication exists — genuinely different assessments with the same
price, currency, and condition are both valid evidence.

Median: custom exact Decimal midpoint. For even count N, takes the two middle
values and computes `(v1 + v2) / 2` using Decimal arithmetic. No
`statistics.median` dependency.

Market range: present only when bucket count >= 3, where
`market_range_low == low` and `market_range_high == high`.

Confidence: `LOW` for count 1-2, `MEDIUM` for count >= 3. 4A never produces
`HIGH` or `VERY_HIGH`.

Verification status from bucket count: `UNKNOWN` (0 buckets), `VERIFIED`
(1 bucket), `AMBIGUOUS` (>1 buckets).

#### 4A What stays out

**No FX conversion** — prices in different currencies stay in different
buckets. No currency lookup, no historical rates, no cross-bucket aggregation.

**No outlier removal** — an extreme price (5000 when others are 100, 110) is
retained in its bucket and counted in statistics. It is not trimmed, winsorized,
or flagged.

**No global "market price"** — aggregation produces bucket-level statistics,
never a single number summarizing all comparable prices.

**No unit-price inference** — quantity / pack-size normalization and
unit-price calculation remain deferred pending actual listing evidence and
a separately approved responsibility; they are NOT part of the 6A
product-specification framework. Aggregation operates on the published
price as-is.

**No LLM confidence** — confidence is derived from count, not guessed. No
model, no prompt, no embedding.

**No persistence** — no model, no migration. Aggregation is a pure function.

**No orchestration (at the end of 4A).** No search, no fetch, no extraction,
no normalization, no matching, no run transition. It takes values it is
handed. *(4C-B later implemented backend orchestration; 4C-C later connected
the web form to the executor.)*

**No integration (at the end of 4A).** `runs/` and `web/` import no part
of the aggregation module. A submitted run was still `CREATED`.

**No availability eligibility rule** — 4A does not check normalized
availability or normalization issues. An `UNKNOWN` availability is irrelevant
for price aggregation.

Status: `IMPLEMENTED` (4A) for deterministic price aggregation over
identity-accepted listings.

### 16.5 What 4B implemented

4B implemented price-result persistence and the read-only web report.
No orchestration was added.

**Snapshot model.** `PriceIntelligenceSnapshot` in `runs/`: one-to-one to
`ResearchRun`, storing `schema_version`, opaque versioned JSON `payload`,
and `created_at`. The payload holds the full `PriceAggregationResult` as
versioned JSON. Cascade delete on run deletion.

**V1 codec.** `research/price_result_codec.py`: pure module (stdlib + domain
+ research contracts only, no Django, no I/O). `encode_price_aggregation_result`
produces a JSON-serialisable dict with canonical assessment-index references
(assessments stored once, referenced by index in buckets and exclusions).
`decode_price_aggregation_result` reconstructs all nested contracts through
normal constructors. Schema-version gate rejects unknown versions. Decimal
preserved as strings, enums as explicit strings, strict schema (no extra keys,
no missing keys, no type coercion). Fail-closed decode: all nested constructor
failures — `ResearchRequest`, `ListingObservation`, `NormalizationIssue`,
`NormalizedListingObservation`, `ListingIdentityAssessment`,
`PriceAggregateBucket`, `PriceAggregationExclusion`, and
`PriceAggregationResult` — are wrapped as `PriceResultCodecError`.

**Canonical assessment-index references.** The encoder maps each distinct
assessment VALUE to a canonical integer index. Bucket and exclusion membership
references assessments by index. The decoder resolves indexes back to the
assessment objects. Hash collisions are handled correctly: the mapping uses
assessment objects as dict keys (hash + equality), not `hash(assessment)`.

**Request provenance.** The decoded result's `ResearchRequest` is compared
to the run's request. A mismatch shows the snapshot as unavailable — zero
numbers rendered.

**Read-only GET.** `/research/<uuid>` reads the snapshot, decodes it,
validates provenance, and renders. Multiple GET requests change no state.
No run transitions, no timestamp writes.

**UNKNOWN / VERIFIED / AMBIGUOUS presentation.** The report renders all three
verification statuses. UNKNOWN shows no buckets but shows excluded listings
with their 3C rejection evidence. VERIFIED shows buckets with contributing
evidence and any excluded listings. AMBIGUOUS shows multiple non-comparable
price groups.

**Contributing + excluded evidence.** Each contributing listing shows:
source URL (hyperlinked when safe), product title, seller, normalized price,
condition, evidence source, raw MPN, compared MPN, match type, raw price text.
Each excluded listing shows the same plus: 3C rejection reason, exclusion
reason, identity decision, and match type.

**URL hyperlink validation.** External page URLs are validated before
hyperlinking: absolute `http`/`https` with non-empty hostname, no embedded
credentials, no HTML-breaking characters. Malformed URLs (e.g. bad IPv6)
return False rather than raising. No network request, no URL rewriting.

**Snapshot timestamp is persistence time.** The `created_at` on the snapshot
model records when the price result was stored, not when any source was
fetched. 4B does not persist source retrieval time; execution/fetch
provenance and retrieval timestamps are part of 4C's evidence-persistence design.

**No orchestration (at the end of 4B).** A submitted run stayed `CREATED`.
Nothing ran automatically. No pipeline connected search through extraction,
normalization, matching, and aggregation. *(4C-B later implemented backend
orchestration; 4C-C later connected the web form to the executor.)*

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

The product specification framework (6A), the first category-specific
schema (6B), and specification evidence extraction and resolution (6C)
precede this work. Enterprise SSD is finalized and implemented as the
first 6B category.

Status:
    7A — IMPLEMENTED / APPROVED / FROZEN
    7B — IMPLEMENTED / APPROVED / FROZEN
    7C-A — IMPLEMENTED / APPROVED / FROZEN
    7C-B — IMPLEMENTED / APPROVED / FROZEN
    7C-C — IMPLEMENTED / APPROVED / FROZEN

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

### 18.1 Paid-call protection is a different problem from caching

8A is not moved and no new caching phase is invented. What is clarified here is
that two distinct concerns have been getting one name (AD-041's sibling concern,
recorded in 2B):

| Concern | What it is | When |
| --- | --- | --- |
| Duplicate paid-call protection | Not paying twice for effectively the same immediate research operation | With the metered provider that creates the exposure (2C, if the selected provider is paid per request) |
| General caching (8A) | Price / specification / comparable freshness windows, explicit refresh, invalidation policy across information classes | 8A |

The first is narrow and operational: one research operation should not issue the
same external request twice because a page was reloaded or a step retried. It is
**not** permission to introduce Redis, Celery, a cache platform, or a freshness
policy — all of which remain `DEFERRED` per §23. The second is a design problem
about how long an answer stays true, and it needs the answers to exist first.

**Historical note:** At the end of 2C, neither caching nor paid-call protection
was implemented. 2C integrated Serper, which is metered and paid
per request, but wired it into nothing at that time: `search()` was only
ever called from an explicit manual script or from tests, so no call happened
as a side effect of ordinary application use.

Status: **As of 4C-B, duplicate paid-call protection IS IMPLEMENTED.**
Atomic `claim_execution` ensures at most one paid search call per ResearchRun.
A new ResearchRun created for retry cannot share evidence or snapshot with any
prior run. General caching/freshness remains `DEFERRED` to 8A.

8A-PRE (Caching & Freshness Architecture Audit) — the selected next
delivery as of the PILOT-RELEASE-2 closure — is APPROVED / COMPLETE
(read-only / design-first audit delivered; it authorized no
implementation and no TTL values, and it changed no production code).
The 8A-FX design lineage (8A-FX-DESIGN, 8A-FX-DESIGN-FU1) is APPROVED /
FROZEN as design. The first bounded caching slice, 8A-FX-A1 (Canonical
ECB Observation Cache), is IMPLEMENTED / PENDING FINAL REVIEW: cross-run
reuse of the canonical production ECB daily FX observation set,
acquisition-only, under a proof-instant + Europe/Brussels
weekend-closure freshness policy (no numeric TTL; §26.18, AD-064).
General caching beyond the 8A-FX slice (page/vendor/semantic/search,
negative caching, retention) remains DEFERRED to later 8A decisions.

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
  authenticates nobody and authorizes nothing. For the current restricted
  internal pilot deployment, the project-lead decision is that people who can
  reach the internal pilot server are currently considered authorized for this
  pilot; PILOT-RELEASE-2 introduces no application authentication, no
  login/session identity, no OAuth, and no per-user authorization. Whether
  reports need authentication, and what visibility they have, remains to be
  settled before any deployment beyond a trusted internal network (8C
  production hardening). Choosing the identifier scheme in 1A did not answer
  that question and must not be read as having answered it.
* **`DEBUG` off and a real `SECRET_KEY`** are required for any deployment.
  The repository default is explicitly development-only.

Authentication and authorization are `DEFERRED`; no phase before 8C assumes
them. **They stop being deferrable at a specific, foreseeable point**, recorded
in 2B so it is not discovered at deployment: the moment a report can expose
internal commercial or vendor pricing (§13.4), report access control becomes a
blocker rather than an open question. Public market pricing shown to an internal
audience is a different exposure from a distributor's negotiated price shown to
whoever holds a URL. Launcher URLs remain URL builders throughout and never
carry provider or authentication secrets (AD-005).

The current security posture has three distinct layers, kept separate in this
documentation so they are not conflated: (1) the current restricted internal
deployment assumption — the pilot server itself has restricted access, and
people who can reach this internal server are currently considered authorized
for this pilot; (2) the existing frozen vendor-price network gate — 4D-C-SEC
`REMOTE_ADDR` / `PI_VENDOR_PRICE_ALLOWED_CIDRS` (unchanged by
PILOT-RELEASE-2); and (3) future broader production-hardening concerns —
full application authentication, login/session identity, OAuth, and
per-user authorization, which remain `DEFERRED` to 8C and are NOT part of
PILOT-RELEASE-2. The report UUID is never access control, and no
session-based authorization is introduced.

**4D-B is the phase that triggers this gate.** Before 4D-B vendor/customer
commercial prices are exposed in the report, deployment MUST verify or
establish trusted-corporate-network / VPN / approved-subnet access restriction.
Full application authentication is NOT required for this documentation — 8C
remains the formal production-hardening/authentication phase. Report UUID is
never access control.

Consequence for the 1B web shell, stated plainly rather than discovered at
deployment time: **anyone who can reach the server can open any report whose
identifier they hold, and can submit a request.** That is acceptable for local
development and a trusted internal network, and it is not acceptable on a public
address. The open question is access control, not the identifier scheme — a
longer UUID would change nothing. CSRF protection is enabled on all POST write endpoints (submission, retry,
human review confirm/reject/undo) and ordinary output escaping is applied to
untrusted intake text.

Status: `APPROVED / PLANNED` for §19 security practices. 4D-C-SEC is
`APPROVED / FROZEN` (SHA 75bfbe3d1b4a8abc12d655cc903298f08e06a8f0,
frozen baseline 4693 collected).

### 4D-C-SEC — Vendor Commercial Price Access Gate (PRODUCT-INTEL.4D-C-SEC)

**APPROVED / FROZEN.** Frozen SHA: 75bfbe3d1b4a8abc12d655cc903298f08e06a8f0.
Frozen test baseline: 4693 collected.

**Intent:** Establish a server-side network access gate before vendor
commercial prices may be rendered in the browser. This protects internal
commercial vendor price visibility. It does not grant identity authority,
pricing authority, or modify any research logic.

**Configuration:**

```
PI_VENDOR_PRICE_ALLOWED_CIDRS
```

Example deployment value (never hardcoded):

```
10.0.0.0/8,192.168.50.0/24,172.16.8.0/21
```

The deployment value belongs in the server environment, not source code.
Absence or blank means **DENY** (fail-closed default).

**Accepted client-address source:**

```
request.META["REMOTE_ADDR"]
```

The following are explicitly NOT trusted:

```
X-Forwarded-For
HTTP_X_FORWARDED_FOR
X-Real-IP
HTTP_X_REAL_IP
Forwarded
query parameters
cookies
Host header
report UUID
arbitrary request headers
```

No proxy-aware client IP handling is implemented. A future deployment that
introduces a reverse proxy and needs forwarded-client-IP processing requires
a separately reviewed trusted-proxy contract (§26.6).

**CIDR semantics:**

- IPv4 and IPv6 supported
- Comma-separated, whitespace tolerated around entries
- Empty entries between commas are ignored safely
- One malformed entry -> entire configuration fails-closed (deny all)

**Decision table:**

| Condition | Result |
|---|---|
| No configured CIDRs | DENY |
| Malformed CIDR config | DENY |
| Missing REMOTE_ADDR | DENY |
| Invalid REMOTE_ADDR | DENY |
| IP outside all networks | DENY |
| IP inside at least one network | ALLOW |

**4D-C browser rendering is gated on this approval.** 4D-C-SEC is now
approved and frozen; PRODUCT-INTEL.4D-C implements the browser rendering
behind this gate. The security branch is server-side and occurs before any
vendor supplemental artifact access: ALLOWED requests use the frozen 4D-C-A
historical replay (complete projection); DENIED requests use a public-only
replay that never reads ResearchSupplementSnapshot. The authorization boolean
may remain in the template context for neutral messaging, but denied context
contains no vendor rows — the boolean is never the row-hiding mechanism.

**Implementation location:** `product_intelligence/web/commercial_access.py`.
Not in `research/`, `providers/`, or `domain/` — this is HTTP request
authorization at the presentation boundary, not research semantics.

Full application authentication is deferred to 8C.

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
  a Django import, or if Django models appear outside `runs/` (the approved
  models are `ResearchRun`, `PriceIntelligenceSnapshot`, `ExecutionEvidenceRecord`,
  and `AiAssistedReviewCandidate`).
  `tests/web/test_web_boundaries.py` fails if an inner layer imports the web
  layer, if the web layer gains a model, a vendor name, a provider import, a
  network client, or a call to `transition_to`. It enforces an explicit
  symbol-level allowlist for research imports (price_result_codec, aggregation,
  matching — specific symbols only) and rejects bare execution package imports,
  execution submodules, and research/identity. `research/identity` is banned
  (research decision logic, not display).
  `tests/research/test_research_identity_boundaries.py` fails if the research
  core gains a non-stdlib import, a persistence / provider / benchmark / web
  import, a network or filesystem module, or a vendor name; if the domain
  imports the research core; or if `runs`, `web`, or `evaluation` wires itself
  to the identity primitive before a phase supplies candidates.
  `tests/providers/test_provider_boundaries.py` fails if a generic boundary
  module (`providers/__init__.py`, `providers/search.py`, and — from 3A —
  `providers/page.py`) gains a non-stdlib import, a vendor name, a
  calling-system concept, a network or configuration module, a model, or a
  third-party dependency; if the provider layer imports persistence, the
  research core, the web layer, or the benchmark; if any inner layer wires
  itself to either boundary; or if the project declares a crawler,
  browser-automation, or managed-scraping dependency — 3A established with a
  plain HTTP client that none is needed, and acquiring one later would answer
  that question by assumption. The vendor-name scan is scoped to the *generic*
  boundary modules, because an adapter is the one place a vendor name belongs.
  Two further 3A guards assert the permitted direction so the network scans
  cannot pass vacuously: `http_page.py` *must* reach the network, and `page.py`
  must not.
  `tests/research/test_research_identity_boundaries.py` additionally fails if
  the 3A extractor imports `decimal`, `statistics`, or `math` — 3A observes text
  and converts nothing — or if `identity.py` acquires a parser it has no reason
  to hold.
* **The browser workflow is tested through the Django test client**, which
  exercises the real URLs, views, forms, templates, and database — no browser
  automation dependency, and nothing mocked between the form and the row. Tests
  cover: web execution (POST creates a run, triggers execution via
  `execute_research_run()`, redirects to report); retry (POST on a failed run
  creates a new run and executes it); Human Review GET/POST behaviour (review
  candidates presented, confirm/reject/undo actions with binding validation);
  Machine Price (deterministic-only buckets) vs Reviewed Price (deterministic
  + human-confirmed); fail-closed snapshot binding (corrupt payload or
  provenance mismatch shows snapshot as unavailable); CSRF protection on all
  POST write endpoints; and the cross-layer authority regression of
  REJECTED -> semantic MATCH -> human CONFIRM. The honest-reporting rules are
  tested as behaviour: that opening a report via GET transitions nothing, and
  that script-like input arrives escaped rather than interpreted.
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
* **Provider interactions use recorded fixtures, never live calls**, so the
  suite stays offline and deterministic. 2B established the policy (§13.3) with
  synthetic fakes only; 2C added the first real, sanitized recording
  (`tests/fixtures/providers/serper/`) and tests the actual adapter mapping
  against it, offline; 3A added five recorded real pages
  (`tests/fixtures/pages/`) under the same rule. A live call belongs only to an
  explicit, manually run check — `scripts/serper_live_smoke.py` and
  `scripts/page_extract_smoke.py` — never to `pytest`. **The normal suite makes
  zero network requests and consumes zero search credits**, and a guard test
  fails if anything under `tests/` so much as references the manual fetch
  script.
* **The evaluation corpus is validated as data.** Its invariants have direct
  tests, and mutation-style tests break one field at a time to prove the
  validator rejects what it claims to. A validator that only ever sees valid
  data is indistinguishable from one that returns `True`.
* **The corpus is also test input, never a runtime dependency.** From 2A, the
  part-number comparison is exercised against real corpus cases — every verified
  part number against itself, the punctuation variant, the near miss, the
  truncation, the description-only requests, and every identity a case forbids
  as an answer. The loader is imported by those tests, and a guard test asserts
  the research core does not import it.
* **A fetcher is judged by what it declines to open.** The 3A fetcher tests
  run offline — `socket.getaddrinfo` and the opener are both replaced, so the
  suite makes no DNS query and opens no connection — and most of them are
  refusals: loopback, private, link-local, metadata, multicast, reserved, and
  IPv4-mapped destinations; a host resolving to one public *and* one private
  address; a redirect to a private address, to a non-web scheme, or carrying
  credentials; an oversized response; a non-HTML content type; and a redirect
  loop. A safety rule exercised only along its happy path is indistinguishable
  from no rule at all.
* **Extraction is regression-tested against real recorded pages** in
  `tests/fixtures/pages/`, through the real extractor, with synthetic edge cases
  kept in a separate file and labelled (§16.1, AD-041). The negative half is the
  important half: that a page's visible dollar amounts never become a price,
  that a part number in a title or a URL never becomes a published part number,
  that an `AggregateOffer` yields no price, and that a page publishing nothing
  readable yields zero observations rather than a guess.
* **A deterministic primitive is tested hardest on what it must refuse.** Most
  of the 2A suite is negative: near misses, truncations, containment,
  punctuation outside the profile, and — after 2A-FU1 — moved and missing
  structural boundaries. A comparator is only as good as the matches it
  declines, and a widened normalization profile fails those tests first. The
  2A-FU1 defect is covered by tests asserting what a normalized *key* looks
  like, not only which pairs collide: a key assertion fails the moment structure
  starts being discarded again, whereas a collision assertion can pass for the
  wrong reason.

Status: `IMPLEMENTED` for the domain contracts, the evaluation corpus, the run
lifecycle, the web shell, the part-number comparison, the search-provider
boundary, the Serper adapter's offline fixture-based regression tests, the
page-fetch boundary and its fetcher, raw listing extraction against recorded
real pages, deterministic listing normalization, deterministic MPN matching
and listing rejection, and the architecture guards.

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
computes a metric, and no threshold is chosen. 2A used the corpus as *test
input* for the part-number comparison and changed no expected answer; that is
not evaluation, because a comparison primitive with no candidate source resolves
nothing to score.

## 22. Approved phased roadmap

```text
PRODUCT-INTEL.0A   Architecture + domain contracts              IMPLEMENTED
                   0A-FU1 contract correctness cleanup          IMPLEMENTED
PRODUCT-INTEL.0B   Evaluation corpus                            IMPLEMENTED
PRODUCT-INTEL.1A   ResearchRun lifecycle                        IMPLEMENTED
                   1A-FU1 persistence invariant hardening       IMPLEMENTED
PRODUCT-INTEL.1B   Basic standalone web research/report shell   IMPLEMENTED
PRODUCT-INTEL.2A   Deterministic product identity model         IMPLEMENTED
                   2A-FU1 structure-preserving normalization    IMPLEMENTED
PRODUCT-INTEL.2B   Search provider abstraction                  IMPLEMENTED
PRODUCT-INTEL.2C   First real search provider (Serper)          IMPLEMENTED
PRODUCT-INTEL.3A   Market listing extraction                    IMPLEMENTED
PRODUCT-INTEL.3B   Listing normalization                        IMPLEMENTED
PRODUCT-INTEL.3C   MPN matching + rejection                     IMPLEMENTED
PRODUCT-INTEL.4A   Price aggregation                            IMPLEMENTED
PRODUCT-INTEL.4B   Price Intelligence result persistence +
                   read-only web report                         IMPLEMENTED
PRODUCT-INTEL.4C   Research execution orchestration
                   FU3A  Production semantic runtime contract  IMPLEMENTED
                   FU3B  Semantic execution integration       IMPLEMENTED

----- PRICE MVP + SEMANTIC + HUMAN REVIEW -----

PRODUCT-INTEL.5A   Structured external intake API             PLANNED
PRODUCT-INTEL.5B   Visual FoxPro 5 launcher integration       IMPLEMENTED
PRODUCT-INTEL.HUMAN-REVIEW  Human review for AI-assisted matches  IMPLEMENTED
PRODUCT-INTEL.PILOT-RELEASE-1  Internal pilot deployment          DEPLOYED / ACCEPTED

----- PILOT-RELEASE-2 DEPLOYED / ACCEPTED — 8A SERIES IN PROGRESS -----

PRODUCT-INTEL.4D-PRE  Preferred Source Feasibility Audit         APPROVED / FROZEN
PRODUCT-INTEL.4D-A    Source Acquisition Optimization            APPROVED / FROZEN
PRODUCT-INTEL.4D-B    Internal Vendor Commercial Evidence        APPROVED / FROZEN
PRODUCT-INTEL.4D-C-A  ECB FX + Compact Quote Projection          APPROVED / FROZEN
PRODUCT-INTEL.4D-C-SEC Vendor Commercial Price Access Gate        APPROVED / FROZEN
PRODUCT-INTEL.4D-C    Compact Quote Summary (browser rendering)  APPROVED / FROZEN
PRODUCT-INTEL.4D-D-PRE1 Early 4D-D authority feasibility review  APPROVED / FROZEN
PRODUCT-INTEL.4D-D-PRE2 Micron official authority evidence capture
                                                                APPROVED / FROZEN
PRODUCT-INTEL.4D-D    Micron Packaging Alias Retrieval (incl. 4D-D-FU1)
                                                                APPROVED / FROZEN

----- PRODUCT-INTEL.4D — Customer Quote Research Expansion: COMPLETE -----

PRODUCT-INTEL.PILOT-RELEASE-2  4D Customer Requirement Deployment
                   & UAT                                        DEPLOYED / ACCEPTED
PRODUCT-INTEL.8A-PRE  Caching & Freshness Architecture Audit
                   (READ-ONLY / DESIGN-FIRST)                   APPROVED / COMPLETE
PRODUCT-INTEL.8A-FX-DESIGN  FX lookup identity & freshness
                   design                                       APPROVED / COMPLETE
PRODUCT-INTEL.8A-FX-DESIGN-FU1  Freshness proof & canonical-feed
                   eligibility closure                         APPROVED / FROZEN
PRODUCT-INTEL.8A-FX-A1  Canonical ECB Observation Cache
                   (first safe caching slice)                   IMPLEMENTED / PENDING FINAL REVIEW

----- PRODUCTION-PRIORITY PUBLIC RESEARCH RECALL -----

PRODUCT-INTEL.PUBLIC-RESEARCH-RECALL-FU1  Exact-MPN recall defect
                   + Micron 7500 SSD policy applicability        IMPLEMENTED / PENDING FINAL REVIEW

----- FOXPRO MVP + HUMAN REVIEW -----

PRODUCT-INTEL.6A   Product specification framework            IMPLEMENTED
PRODUCT-INTEL.6B   First category-specific schema (Enterprise SSD v1)  IMPLEMENTED
PRODUCT-INTEL.6C   Specification evidence extraction and
                   resolution                                 IMPLEMENTED
PRODUCT-INTEL.6D   Authoritative datasheet specification      
                   enrichment                                 IMPLEMENTED / APPROVED / FROZEN
PRODUCT-INTEL.7A   Comparable-product candidate discovery     IMPLEMENTED / APPROVED / FROZEN
PRODUCT-INTEL.7B   Similarity scoring                         IMPLEMENTED / APPROVED / FROZEN
PRODUCT-INTEL.7C-A  Comparable research results + codec      IMPLEMENTED / APPROVED / FROZEN
PRODUCT-INTEL.7C-B  Comparable research orchestration         IMPLEMENTED / APPROVED / FROZEN
PRODUCT-INTEL.7C-C  Comparable web trigger + presentation     IMPLEMENTED / APPROVED / FROZEN

----- COMPARABLE MVP -----

PRODUCT-INTEL.8A   Caching / refresh strategy                   IN PROGRESS (8A-PRE complete; 8A-FX-A1 pending final review)
PRODUCT-INTEL.8B   Research history
PRODUCT-INTEL.8C   Production hardening

Future:
  SAP launcher integration
  additional clients
  additional product-category schemas
  additional search providers
  additional LLM providers
```

**Roadmap (current state):**

```
DEPLOYED / ACCEPTED:
  PILOT-RELEASE-1  Internal pilot deployment (pilot_check PASS, Waitress,
                   remote browser, real Serper, AMAX/nemotron-3-super primary
                   semantic, human review, comparable research, persistent
                   SQLite, Windows service)

COMPLETE — PRODUCT-INTEL.4D (Customer Quote Research Expansion):
  IMPLEMENTED / APPROVED / FROZEN / COMPLETE
  4D-PRE  Preferred Source Feasibility Audit (approved / frozen)
  4D-A    Source Acquisition Optimization (approved / frozen)
  4D-B    Internal Vendor Commercial Evidence (approved / frozen)
  4D-C    Compact Quote Summary (4D-C-A + 4D-C-SEC + 4D-C, approved / frozen)
  4D-D    Micron Packaging Alias Retrieval (incl. 4D-D-FU1; approved /
          frozen at SHA 065320180c17b89c7460164326a0c9f49e01fe3b,
          baseline 5097 collected, final acceptance 5097 passed)

DEPLOYED / ACCEPTED — PRODUCT-INTEL.PILOT-RELEASE-2 (4D Customer
Requirement Deployment & UAT)
  Deployed runtime SHA: 065320180c17b89c7460164326a0c9f49e01fe3b (the
  independently reviewed and frozen PRODUCT-INTEL.4D-D-FU1 runtime
  SHA; deployment is Git-managed and exact-approved-SHA based).
  Production smoke test passed: 2026-09-23. 4D is deployed; migrations
  through 0010_research_micron_alias_snapshot are deployed (4D
  migrations 0008 / 0009 / 0010). Production environment details
  (application path, persistent SQLite, service ID / WinSW wrapper,
  Waitress, port, health endpoint, 4D preferred-source configuration,
  Vendor API configuration) are recorded in the operational Confluence
  references and are not duplicated here. The recorded representative
  4D production smoke validation covered: a normal customer quote flow
  exercising current Price Intelligence / Compact Quote behavior;
  Micron 7500 R/T packaging-alias behavior. The previously planned
  broader UAT matrix (direct-source acquisition via a viable
  preferred-source case; normal Serper fallback; real Vendor API
  commercial evidence; compact quote rendering; non-USD vendor evidence
  + persisted ECB USD equivalent; Micron 7500 packaging-alias BASE/R/T
  behavior; a non-eligible MPN proving alias abstention; Visual FoxPro
  launcher -> browser prefill against the deployed server; historical
  report reload causing zero new Search/Vendor/ECB/Micron/Semantic live
  work; vendor-price access behavior under the existing frozen network
  gate (4D-C-SEC, unchanged)) remains a validation reference; the
  production records do not claim that every matrix case was separately
  executed and evidenced during the 2026-09-23 cutover.
  Authentication: current restricted internal pilot deployment assumption
  (reachability = authorized for this pilot); full application
  authentication remains a deferred 8C production-hardening concern; the
  frozen 4D-C-SEC REMOTE_ADDR / PI_VENDOR_PRICE_ALLOWED_CIDRS gate is
  unchanged; report UUID is not access control.
  Runtime-vs-docs: the later commits c6ad6ae and 7ff0ab7 are docs-only
  project-state closures; production does not need to move merely to
  obtain those documentation edits; 7ff0ab7 is not the production
  runtime SHA.

8A SERIES — IN PROGRESS (Caching & Freshness):
  8A-PRE  Caching & Freshness Architecture Audit
        APPROVED / COMPLETE (read-only / design-first audit delivered;
        authorized no implementation and no TTL values; it distinguished
        at minimum: market/public prices (short freshness); Vendor
        commercial observations (short freshness); ECB FX rates (tied to
        persisted official observation date); product specifications
        (longer freshness); comparable research (medium freshness);
        deterministic identity/authority evidence (not automatically
        equivalent to market-price freshness); user/operator forced
        refresh; historical reports (immutable replay, NEVER refreshed
        merely by GET)).
  8A-FX-DESIGN / 8A-FX-DESIGN-FU1  FX lookup identity, content identity,
        and freshness design (incl. the corrected proof-instant +
        Europe/Brussels weekend-closure predicate and the canonical-
        default eligibility declaration)
        APPROVED / FROZEN as design
  8A-FX-A1  Canonical ECB Observation Cache (first safe caching slice;
        acquisition-only; FX remains DISPLAY-SUPPLEMENTAL; no numeric
        TTL; §26.18; AD-064)
        IMPLEMENTED / PENDING FINAL REVIEW

IMPLEMENTED (frozen):
  4C-A  Execution ownership/lifecycle/evidence primitives
  4C-B  Backend research execution (orchestration pipeline)
  4C-B-FU  Exact duplicate observation deduplication
  4C-C  Web execution/retry integration
  FU3A  Production semantic runtime contract
  FU3B  Semantic execution integration
  HUMAN-REVIEW  Human review for AI-assisted semantic matches
  SEMANTIC-QWEN38-PRODUCTION-PROMOTION-B1  Production semantic PRIMARY
        route promotion (amax/qwen3.8-27b primary; frozen fallback
        vllm-262k/Qwen3.6-27B-262K unchanged; PLAN §26.17)
        IMPLEMENTED / PENDING FINAL REVIEW

PLANNED:
  5A    Structured external API (not a blocker for current workflow)
  8B    Research history
  8C    Production hardening

DELIVERED:
  5B    Visual FoxPro 5 launcher (server-side + client integrated outside repo)
  6A    Product specification framework (implemented / approved / frozen)
  6B    Enterprise SSD category schema (12-field v1 / approved / frozen)
  6C    Specification evidence extraction and resolution (implemented / approved / frozen)

DELIVERED (frozen):
  7A    Comparable-product candidate discovery (implemented / approved / frozen)

DELIVERED (approved / frozen):
  7B    Enterprise SSD similarity scoring (implemented / approved / frozen)

IMPLEMENTED (frozen):
  6D    Authoritative datasheet specification enrichment
        (6D IS the candidate-specification enrichment; implemented / approved / frozen)

DELIVERED (frozen):
  7C-A  Comparable research results + codec (implemented / approved / frozen)
  7C-B  Comparable research orchestration
        (frozen primitives composed into one bounded execution pipeline;
         implemented / approved / frozen)
  7C-C  Comparable web trigger + presentation
        (web trigger route, pure presentation, CSRF, boundary guards;
         implemented / approved / frozen)

FUTURE:
  SAP   SAP launcher integration
```

**6C IMPLEMENTED AND FROZEN.**
**7A IMPLEMENTED AND FROZEN.**
**7B IMPLEMENTED / APPROVED / FROZEN.**
**7C-A IMPLEMENTED AND FROZEN.**
**7C-B IMPLEMENTED / APPROVED / FROZEN.**
**7C-C IMPLEMENTED / APPROVED / FROZEN (web trigger + presentation).**

6A is IMPLEMENTED AND FROZEN. 6B is IMPLEMENTED AND FROZEN (with
approved evidence-backed corrective addition: "2.5in" -> "2.5-inch").
6C is IMPLEMENTED AND FROZEN.

6A defines the product specification framework: specification definition,
specification value, specification observation (raw evidence), normalized
specification observation, specification resolution, category schema,
and product specification set. It is a pure, deterministic,
caller-independent framework: no Django model, no persistence, no network
access, no extraction, no LLM call, no category-specific fields, and no
reuse of the frozen FU3A/FU3B semantic runtime.

6A distinguishes source authority (AUTHORITATIVE vs SECONDARY) from
extraction authority. Source authority is supplied explicitly by the
evidence-acquisition policy, not auto-classified by hostname or URL.
An authoritative source does not make an LLM interpretation authoritative.

6A defines the binding deterministic resolution policy:
- UNKNOWN — zero usable canonical values
- VERIFIED — exactly one unique canonical value supported by at least one
  AUTHORITATIVE observation
- UNVERIFIED — exactly one unique canonical value with SECONDARY-only
  support
- CONFLICT — more than one unique canonical value

No majority voting: evidence multiplicity does not vote truth into
existence.

Enterprise SSD is finalized and implemented as the first 6B category.
6C is implemented with specification evidence extraction and resolution.
6C acquires specification evidence from approved sources, extracts raw
specification observations, preserves source provenance, normalizes using
the 6B category schema, and feeds normalized evidence into the 6A
deterministic resolver to produce ProductSpecificationSet results.
6C uses only the demonstrated structural mechanism:
`var supportSpecsData = JSON.parse('...')` embedded in `<script>` tags.
Samsung PM9A3 remains a source-specific static-HTML evidence gap.
Seagate Nytro 5050 demonstrates that deterministic static structured
extraction is sufficient for the minimum real 6C vertical slice.
Current evidence therefore does not justify an LLM extractor.

7B is IMPLEMENTED / APPROVED / FROZEN. 7C (Comparable-Product Presentation) is IMPLEMENTED / APPROVED / FROZEN.
6D (authoritative datasheet specification enrichment) is IMPLEMENTED / APPROVED / FROZEN and IS the candidate-specification enrichment that was the subject
of the prior delivery-decision question. 7C (web presentation) is frozen: all
three sub-phases (7C-A, 7C-B, 7C-C) are implemented and approved.

7B (similarity scoring) computes deterministic field-level similarity evidence
between target and candidate specifications. VERIFIED-only scoring, 12-field
equal weight, DECIMAL min/max ratio, TEXT/ENUM/BOOLEAN exact equality.
Execution-owned EnterpriseSsdSimilarityResult with 7A source binding,
retained source outcomes, and provenance audit. Evidence sparsity (1/12
coverage per candidate under current 6C extraction) means candidate
specification enrichment is needed before useful 7C presentation.

7C (comparison web report) depends on 7B freeze and candidate specification
enrichment.

### 22.0 Product Specification Framework — 6A Phase Contract

The following is the binding canonical contract for 6A implementation.
Planned implementation lives in:

    product_intelligence/research/specifications.py

6A is:

- **pure** — no side effects, no state beyond its inputs
- **deterministic** — same inputs always produce the same outputs
- **caller-independent** — no knowledge of which client or transport produced the data
- **Django-independent** — no model, no migration, no ORM, no framework
- **persistence-free** — no database, no file I/O, no storage
- **provider-free** — no provider interface, no vendor adapter
- **network-free** — no HTTP, no DNS, no socket, no external call
- **category-neutral** — no SSD-specific, CPU-specific, or any category-specific fields

It defines seven canonical contracts and one deterministic resolver concept.
No unnecessary Python syntax or constructor signatures are frozen here;
semantics are frozen, not incidental implementation style.

#### 22.0.1 SpecificationDefinition

Answers: *"What specification is this?"*

It is a definition/schema concept, NOT a product's actual value.

A SpecificationDefinition semantically includes:

- a stable machine key
- a human-readable label
- a value kind
- an optional canonical unit (where applicable)
- allowed values (where applicable for ENUM)

Initial supported value kinds are EXACTLY:

| Value kind | Meaning |
| --- | --- |
| `TEXT` | Free-text canonical value (e.g. interface connector name) |
| `DECIMAL` | Numeric canonical value using `Decimal` — never `float` |
| `BOOLEAN` | True/false canonical value |
| `ENUM` | One value from a defined allowed set |

Do NOT add `RANGE`, `LIST`, `SET`, `OBJECT`, or `FORMULA` unless a later
real category demonstrates need.

No SSD-specific definition keys belong in 6A. Those enter through 6B.

**Definition/value compatibility.** A canonical SpecificationValue is
usable ONLY when it is valid for the SpecificationDefinition it belongs to:

- `TEXT` -> any canonical text value
- `DECIMAL` -> `Decimal`, never `float`
- `BOOLEAN` -> boolean value
- `ENUM` -> value must be a member of the definition's allowed values

A DECIMAL definition may declare a canonical unit. A normalized DECIMAL value
for that definition is interpreted in that canonical unit. 6A performs NO unit
conversion — conversion of raw source units into the definition's canonical unit
belongs to category normalization downstream (6B semantics + 6C execution).

A value of the wrong kind, wrong ENUM member, or otherwise incompatible with
the definition is NOT usable canonical evidence.

#### 22.0.2 SpecificationValue

A SpecificationValue is a CANONICAL value. It is not raw external text.

Example:

- Source text: `"3,840 GB"`
- Canonical representation: `Decimal("3.84")` with canonical unit `"TB"`

Or simply:

- `"U.3"`
- `True`

6A defines what canonical values can represent.
6A does NOT define how a web page, PDF, LLM, or source string is converted
into that value. That belongs downstream (6C).

A SpecificationValue is only usable when it is valid for its associated
SpecificationDefinition (see §22.0.1 definition/value compatibility rules).

#### 22.0.3 SpecificationObservation — Raw Evidence

A SpecificationObservation means:

    "A source published this raw information about this specification."

It does NOT mean:

    "Therefore this value is true."

**Product identity binding.** A SpecificationObservation must semantically bind
to:

- one established `ProductIdentity`
- one `SpecificationDefinition`

An identity is established exactly according to the existing
`ProductIdentity.is_established` semantics. 6A reuses that authority; it does
NOT invent a new semantic identity tier for specifications. Specifications do
NOT establish identity.

An observation bound to an unestablished `ProductIdentity` is invalid.

This binding is the mechanism that makes cross-product evidence
(Product A identity + Product B evidence) mechanically rejectable.

Product identity is not inferred from source URL, hostname, raw text, or LLM
output. 6C must supply evidence already associated with the established
identity it is researching.

The observation contract preserves semantic provenance sufficient to
audit the statement, including:

- product identity binding
- specification key / definition binding
- source name
- source URL
- retrieval timestamp
- raw value
- raw reference / locator (when available)
- source authority

Raw evidence remains raw.

A raw reference/locator is for audit provenance and is not parsed by generic
business logic merely because it exists.

#### 22.0.4 Source Authority

Initial source-authority vocabulary:

| Authority | Meaning |
| --- | --- |
| `AUTHORITATIVE` | Manufacturer-controlled or otherwise explicitly authoritative product source |
| `SECONDARY` | Retailer / distributor / marketplace / other supporting source |

6A does NOT infer this tier from hostname or URL.
A later evidence-acquisition policy supplies the authority classification.

**Binding orthogonality rule: source authority != extraction authority.**

An authoritative source does not make an extraction mechanism authoritative.
Example: a manufacturer datasheet is an AUTHORITATIVE source, but an LLM's
interpretation of that datasheet is not thereby an authoritative interpretation.
An extraction mechanism never inherits truth authority merely from the
document it reads.

#### 22.0.5 NormalizedSpecificationObservation

Mirrors the project's existing evidence-first 3A → 3B pattern:

    SpecificationObservation
        ->
    NormalizedSpecificationObservation

The normalized contract preserves the ORIGINAL observation, including:

- product identity binding
- specification definition binding
- source provenance
- source authority

It carries either:

- a valid canonical SpecificationValue (which MUST be valid for the original
  SpecificationDefinition per §22.0.1 compatibility rules)

or:

- no canonical value + explicit normalization issue/reason

An ambiguous or unparseable raw value does NOT silently become a fact.
Issue-only observations are preserved as evidence; they are never silently
discarded, and no canonical value is guessed.

Example:

- `"3.84 TB"` -> canonical `Decimal("3.84")` TB
- `"up to 7.68 TB depending on model"` -> no canonical value,
  explicit ambiguous normalization issue

6A defines this generic contract.
6B owns category-specific definitions and normalization meaning.
6C performs real extraction and normalization.

#### 22.0.6 SpecificationResolution — Four-State Deterministic Resolver

**Usable canonical observation.** A usable canonical observation is a
`NormalizedSpecificationObservation` that:

1. preserves an original `SpecificationObservation`;
2. therefore remains bound to one established `ProductIdentity`;
3. remains bound to one `SpecificationDefinition`;
4. contains a canonical `SpecificationValue` valid for that definition.

An issue-only normalized observation is preserved as evidence but is NOT a
usable canonical observation for value resolution.

The deterministic resolver operates on usable canonical observations.

**Self-auditing invariants.** A SpecificationResolution represents resolution
of exactly one established `ProductIdentity` plus exactly one
`SpecificationDefinition` from an exact collection of
`NormalizedSpecificationObservation` evidence.

- Every input normalized observation belongs to the SAME established
  `ProductIdentity` as the resolution.
- Every input normalized observation belongs to the SAME
  `SpecificationDefinition` as the resolution.
- Cross-product evidence is invalid.
- Cross-specification evidence is invalid.
- The resolution preserves the evidence collection from which it was derived.
- Issue-only observations remain preserved even though they do not vote on the
  canonical value.
- No evidence is silently dropped merely because it conflicts or failed
  normalization.

The exact Python field names/signature remain implementation work.

**Resolution states and value consistency.** Exactly four resolution states.
All usable values must already be valid for the same `SpecificationDefinition`.

| State | Condition |
| --- | --- |
| `UNKNOWN` | Zero usable canonical values. Resolved value = none. May still preserve issue-only normalized observations. |
| `VERIFIED` | Exactly one unique usable canonical value AND >= 1 AUTHORITATIVE usable observation supports it. Resolved value = that value. |
| `UNVERIFIED` | Exactly one unique usable canonical value AND all usable support is SECONDARY. Resolved value = that value. |
| `CONFLICT` | More than one unique usable canonical value. Resolved value = none. |

**No majority voting.** Evidence multiplicity does not vote truth into
existence. No source-count weighting. No "authoritative source automatically
wins conflict."

Worked examples:

```
AUTHORITATIVE  3.84 TB
SECONDARY      3.84 TB
    -> VERIFIED 3.84 TB

SECONDARY      U.3
SECONDARY      U.3
    -> UNVERIFIED U.3

AUTHORITATIVE  3.84 TB
SECONDARY      7.68 TB
    -> CONFLICT

9 SECONDARY     3.84 TB
1 AUTHORITATIVE 7.68 TB
    -> CONFLICT   (not 9-to-1 voting)
```

#### 22.0.7 CategorySchema

A CategorySchema is a versioned grouping of definitions for one product
category. Semantic identity includes:

- stable schema id
- schema version
- human-readable label
- specification definitions

6A defines only the category-neutral mechanism.
6B creates the first real category schema.
No enterprise-SSD fields belong in 6A.

**Unique definition keys.** A CategorySchema's SpecificationDefinition keys
must be unique within that schema. No two definitions in one schema may claim
the same stable machine key.

The framework must allow a later second category without redesigning the
fundamental contract.

#### 22.0.8 ProductSpecificationSet — Identity First

A ProductSpecificationSet represents the COMPLETE resolved state for:

    one established ProductIdentity
        under
    one CategorySchema

**Identity comes FIRST.** Specifications do not establish product identity.

A ProductSpecificationSet must bind fail-closed to an ESTABLISHED
`ProductIdentity` (using existing established-identity semantics; do NOT
redefine `IdentityMatchType`) rather than to an arbitrary free-form product
label.

**Completeness invariants:**

A. Exactly ONE `SpecificationResolution` exists for EVERY
   `SpecificationDefinition` in the `CategorySchema`. Specifications with no
   usable evidence appear explicitly as `UNKNOWN` resolutions.

B. No resolution may exist for a definition outside the `CategorySchema`.

C. No duplicate resolution for the same definition key.

D. Every resolution's `ProductIdentity` must equal the `ProductSpecificationSet`'s
   `ProductIdentity`.

E. Every resolution's `SpecificationDefinition` must correspond to the exact
   definition represented by that `CategorySchema` key.

An omitted resolution does NOT silently mean `UNKNOWN`. `UNKNOWN` must be
explicit.

**Cross-product/specification failure modes.** All of the following fail
closed:

- Product A identity + Product B resolution/evidence
- a `capacity` resolution placed under the `form_factor` definition
- duplicate resolutions for the same specification key
- a schema definition missing its resolution entirely
- a resolution for a specification not in the schema

This is the mechanical meaning of:

    Product A identity + Product B specification evidence must be rejected.

6A does not solve persistence or acquisition of that identity.
6C must consume/provide evidence consistently with this identity binding;
it must not weaken the identity-first invariant.

#### 22.0.9 Evidence-First Audit Chain

Every `SpecificationResolution` remains auditable back through:

    SpecificationResolution
        ->
    NormalizedSpecificationObservation(s)
        ->
    SpecificationObservation(s)
        ->
    source/raw provenance

and every link in that chain remains bound to the same established
`ProductIdentity` and `SpecificationDefinition`.

A `ProductSpecificationSet` must never contain a resolved fact whose evidence
chain cannot be traced. This extends the evidence-first principles of §11
to specification resolution.

#### 22.0.10 6A Explicit Non-Scope

The following are NOT part of 6A and must not appear in its implementation:

- Django model, migration, or persistence
- snapshot codec
- web view, template, or URL
- execution wiring
- SearchProvider change
- provider call
- network access
- page fetching
- HTML extraction
- PDF extraction
- specification extraction
- LLM call
- FU3A/FU3B semantic-runtime reuse
- LLM/model qualification
- product-category classifier
- SSD-specific specification fields
- comparable candidate discovery
- similarity weights
- compatibility rules
- similarity score
- comparison report

Do not add placeholder production types for 6B/6C/7A-7C behaviour.

Do not
execute a later phase while working on an earlier one.

**The next phase is the priority.** 4A turned 3C's accepted listings into
deterministic bucket-level price statistics: eligibility with ordered exclusion
reasons, currency+condition grouping, exact Decimal median, derived confidence
(LOW/MEDIUM), exact-duplicate input refusal by value, multiplicity preservation
with Counter, request provenance validation, and canonical bucket keys. No FX
conversion, no outlier removal, no global market-price selection, no LLM call,
no persistence, no orchestration. 4B — persisting the `PriceAggregationResult`
as a `PriceIntelligenceSnapshot` and presenting it at `/research/<uuid>` as a
read-only price intelligence report — is what makes the result durable and
reviewable by URL. 4C — orchestrating the full research pipeline from
`ResearchRequest` through search, fetch, extraction, normalization, matching,
and aggregation, then persisting the result — is what connects the isolated
primitives into an end-to-end research run. 4B does not execute research: it
renders what already exists and says honestly when nothing is there.

### 22.1 Enterprise SSD Category Schema — 6B Phase Contract

The following is the binding canonical contract for 6B implementation.
Implementation lives in:

    product_intelligence/research/enterprise_ssd.py

6B is:

- **pure** — no side effects, no state beyond its inputs
- **deterministic** — same inputs always produce the same outputs
- **caller-independent** — no knowledge of which client or transport produced the data
- **Django-independent** — no model, no migration, no ORM, no framework
- **persistence-free** — no database, no file I/O, no storage
- **provider-free** — no provider interface, no vendor adapter
- **network-free** — no HTTP, no DNS, no socket, no external call
- **representation-only** — normalizes raw values to canonical form;
  does not extract, resolve, or infer authority
- **category-generic** — Enterprise SSD generic rules, no manufacturer-specific
  normalizers (SamsungNormalizer, MicronNormalizer, etc. forbidden)

6B imports only:

    standard library
    product_intelligence.research.specifications (frozen 6A contracts)

It does not import any other research submodule, domain, or framework module.

#### 22.1.1 Enterprise SSD Schema V1

Schema identifiers:

| Attribute | Value |
| --- | --- |
| `schema_id` | `enterprise-ssd` |
| `schema_version` | `1.0` |
| `label` | `Enterprise SSD` |
| `definitions` | exactly 12 SpecificationDefinitions |

The 12-field set (ordered by definition):

| # | Key | Label | Kind | Canonical Unit |
| --- | --- | --- | --- | --- |
| 1 | `capacity` | Capacity | DECIMAL | TB |
| 2 | `storage_protocol` | Storage Protocol | ENUM | — |
| 3 | `pcie_generation` | PCIe Generation | ENUM | — |
| 4 | `pcie_lane_count` | PCIe Lane Count | DECIMAL | — |
| 5 | `physical_form_factor` | Physical Form Factor | ENUM | — |
| 6 | `interface_connector` | Interface / Connector | TEXT | — |
| 7 | `sequential_read` | Sequential Read | DECIMAL | MB/s |
| 8 | `sequential_write` | Sequential Write | DECIMAL | MB/s |
| 9 | `random_read_iops` | Random Read IOPS | DECIMAL | IOPS |
| 10 | `random_write_iops` | Random Write IOPS | DECIMAL | IOPS |
| 11 | `endurance_dwpd` | Endurance | DECIMAL | DWPD |
| 12 | `power_loss_protection` | Power Loss Protection | BOOLEAN | — |

#### 22.1.2 Enum Vocabularies

**storage_protocol**: NVMe, SATA, SAS

**pcie_generation**: PCIe 3.0, PCIe 4.0, PCIe 5.0

**physical_form_factor**: 2.5-inch, M.2, E1.S, E3.S

U.2 and U.3 are NOT valid physical_form_factor values (they are connectors).

#### 22.1.3 Normalization Contract

6B normalization is representation-only:

- Input: SpecificationObservation already bound to an established
  ProductIdentity and one SpecificationDefinition from this schema.
- Output: NormalizedSpecificationObservation with exactly one of:
    canonical SpecificationValue, or normalization issue.
- The original observation is preserved with full provenance.
- Source authority is never changed or inferred.
- No resolution (VERIFIED/UNVERIFIED/CONFLICT/UNKNOWN) is performed.
- No ProductIdentity is created or modified.
- No resolve_specification() is called.

Normalization issue vocabulary:

| Issue code | Meaning |
| --- | --- |
| MISSING_OR_EMPTY_VALUE | No parseable content |
| UNRECOGNIZED_FORMAT | Value does not match expected pattern |
| UNSUPPORTED_UNIT | Unit is explicitly unsupported (e.g. TiB for capacity) |
| OUT_OF_RANGE_OR_NON_POSITIVE | Value is zero, negative, or non-finite |
| AMBIGUOUS_VALUE | Multiple possible readings (ranges, "up to", etc.) |

#### 22.1.4 Key Normalization Rules

**capacity**: decimal-SI only (TB, GB). 1000 GB = 1 TB. TiB/GiB rejected.
Unitless rejected.

**storage_protocol**: case-insensitive exact match. Composite values
rejected (e.g. "PCIe 4.0 x4 NVMe").

**pcie_generation**: narrow exact equivalents (PCIe 4.0, Gen4, PCI Express
4.0, etc.). Bare "PCIe" rejected.

**pcie_lane_count**: positive whole number. "x4", "4", "4 lanes". Fractions
and zero rejected.

**physical_form_factor**: narrow spellings only. U.2/U.3 explicitly
rejected (connector types, not form factors).

**interface_connector**: TEXT — narrow canonical spellings for U.2/U.3/M.2.
Other non-empty values abstain rather than invent a taxonomy.

**sequential_read/write**: decimal-SI throughput (MB/s, GB/s × 1000).
MiB/s/GiB/s rejected.

**random_read/write_iops**: explicit IOPS token required; optional K
(×1000) or M (×1,000,000) SI multipliers; unitless numeric/K/M forms
abstain.

**endurance_dwpd**: plain numeric or explicit DWPD. TBW/PBW not derived.

**power_loss_protection**: explicit boolean tokens only. Prose rejected.

**Numeric values with comma grouping**: strict thousands-grouping semantics
enforced. Comma-separated integer portions must use exact three-digit groups
after the first group (e.g. 1,000 accepted; 1,000,00 rejected; 3,84 rejected).
Malformed comma grouping abstains. Punctuation is never blindly stripped.

#### 22.1.5 Schema Versioning Rule

Incompatible field meaning changes or enum semantic changes require a
schema version bump. Adding a field is a version bump. Removing a field
is a version bump. Renaming a field is a version bump.

#### 22.1.6 Relationship to 6A and 6C

6A (frozen) defines the specification framework: definitions, values,
observations, normalized observations, resolutions, category schemas,
and the resolver. 6B uses only CategorySchema and the normalization
primitive — it does not call resolve_specification().

6C (now IMPLEMENTED / APPROVED / FROZEN) owns evidence acquisition and extraction:
it acquires specification evidence from approved sources, extracts raw
specification observations, preserves source provenance, normalizes
using the 6B category schema, and feeds normalized evidence into the
6A deterministic resolver. 6B does not do any of this.

No LLM model or provider is selected in 6B.

#### 22.1.7 Evidence-Backed Corrective Addition (APPROVED / FROZEN)

Real Seagate Nytro 5050 manufacturer evidence demonstrated "2.5in" (no space
between number and unit) as an exact formatting equivalent of the existing
2.5-inch canonical form for `physical_form_factor`.

Correction applied to `_FORM_FACTOR_MAP`:
    "2.5in" -> "2.5-inch"

No schema version bump because:
- field meaning unchanged
- canonical value unchanged ("2.5-inch")
- enum allowed_values unchanged
- only accepted lexical representation expanded by real evidence

This is a narrow, evidence-backed, corrective modification of frozen 6B.
Approved by project lead and re-frozen.


### 22.2 Specification Evidence Extraction & Resolution — 6C Phase Contract

**IMPLEMENTED / APPROVED / FROZEN**

Implementation lives in:

    product_intelligence/research/enterprise_ssd_extraction.py
    product_intelligence/execution/specification_evidence.py

6C is:

- **explicit approved sources** — no source discovery or search
- **deterministic structured extraction** — embedded JavaScript JSON product data arrays
- **no arbitrary text mining** — TB, NVMe, GB/s in prose is not extracted
- **pure research extraction** — receives document text, produces observations
- **provenance preservation** — raw values, locators, source URLs, timestamps
- **frozen 6B normalization** — reuse of normalize_enterprise_ssd_observation()
- **frozen 6A resolution** — reuse of resolve_specification()
- **complete ProductSpecificationSet** — all 12 definitions present, UNKNOWN explicit
- **source outcomes auditable** — EXTRACTED, NO_OBSERVATIONS, FETCH_FAILED, SOURCE_REFUSED
- **requested_url removed** — always source.source_url (one source of truth)
- **provenance trace** — every normalized obs traces to an EXTRACTED outcome
- **evidence consistency** — resolution.evidence equals normalized obs per definition
- **no LLM** — deterministic-first; LLM extraction may be evaluated later
- **no persistence/web** — in-memory auditable result only
- **no identity leakage** — extraction module imports no evaluation module

#### 22.2.1 Source Acquisition Model

6C does NOT discover sources. It receives EXPLICITLY APPROVED source descriptors
via the `SpecificationEvidenceSource` contract:

- `product_identity` — must be established (existing `is_established` semantics)
- `source_name` — human-readable source name
- `source_url` — absolute http(s) URL (validated by `require_fetchable_url`)
- `source_authority` — `SourceAuthority.AUTHORITATIVE` or `SourceAuthority.SECONDARY`

Authority is SUPPLIED EXPLICITLY. It is NEVER inferred from hostname, URL,
manufacturer name, or document content.

Cross-product source input (source's product_identity ≠ target identity)
fails closed BEFORE acquisition. The page is never fetched.

#### 22.2.2 Existing PageFetcher Reuse

6C reuses the existing PageFetcher protocol, PageFetchRequest, FetchedPage,
PageFetchError, and UnsafeFetchTargetError. No new HTTP client is created.

Observation source_url is set to `FetchedPage.final_url` (where evidence
came from). Observation `retrieved_at` comes from `FetchedPage.retrieved_at`.
Source outcomes preserve the source descriptor; the requested URL is always
`outcome.source.source_url` (no duplicate field).

#### 22.2.3 Deterministic Structured Extraction

`extract_enterprise_ssd_specification_observations()` is a PURE function:
receives document text + provenance parameters, produces raw
`SpecificationObservation` values only.

It searches for specification data in one structured format:

1. **Embedded JavaScript JSON product data arrays** — The demonstrated
   structural marker is `var supportSpecsData = JSON.parse('...')` in
   `<script>` tags. Only this exact variable name is accepted (real
   manufacturer evidence: Seagate Nytro 5050). Contains arrays of product
   records with `skuNumber` and `features[]`. Exact `skuNumber` match to
   target MPN. Each feature's `title` is resolved to an ENTERPRISE_SSD_SCHEMA
   definition key via the `_RAW_LABEL_TO_SCHEMA_KEY` mapping.
   Unrelated JSON.parse targets (e.g. `var unrelatedData = JSON.parse(...)`)
   produce zero observations.

REMOVED mechanisms (no real manufacturer evidence ever demonstrated):
- JSON-LD Product additionalProperty/PropertyValue pairs
- HTML specification tables (label + value rows)
- HTML definition lists (dt + dd pairs)

Arbitrary visible text is NOT mined. Composite values are NOT split.
Unknown field labels are ignored, not guessed. A malformed JSON block
does not poison sibling blocks.

Only labels demonstrated by real manufacturer fixtures are mapped:
- "Form Factor" -> physical_form_factor (Seagate Nytro 5050)

#### 22.2.4 Real Manufacturer Evidence

Seagate Nytro 5050 NVMe SSD (XP15360SE70005):
- **Source**: https://www.seagate.com/support/enterprise-storage/solid-state-drives/nytro-5050/
- **Accessible via static HTTP**: YES (200 OK, 796 KB)
- **Structure**: Embedded JavaScript JSON variable (`var supportSpecsData = JSON.parse('...')`)
  in a `<script>` tag. Contains an array of 81 product records.
  Each record has `skuNumber`, `title`, `features[]`.
  Features are title/value/order triples.
- **Target record (XP15360SE70005)**:
  - Form Factor: "2.5in"
  - Interface: "PCIe<sup>®</sup> Gen4 x4 NVMe "
  - Encryption: "Standard Model"
- **Extraction result**: 1 observation (Form Factor -> physical_form_factor)
- **Normalization**: "2.5in" (no space) normalizes to "2.5-inch" via
  evidence-backed 6B correction. Resolution state: VERIFIED.
- **Composite Interface value**: "PCIe Gen4 x4 NVMe" is preserved as-is.
  It is NOT split into storage_protocol, pcie_generation, pcie_lane_count
  per 6B rules.

Samsung PM9A3 (MZ-QL23T800) product page:
- **Source**: https://www.samsung.com/us/business/memory-storage/nvme-ssd/pm9a3-nvme-u-2-ssd-3-8tb-sku-mz-ql23t800/
- **Accessible via static HTTP**: YES (200 OK, retrieved 2026-09-04)
- **JSON-LD Product data**: YES (name, sku, brand, offers, color)
- **Specification data in structured format**: NO
  - No embedded JSON product data arrays
  - No JSON-LD additionalProperty
  - No HTML specification tables (0 tables in body)
  - No definition lists (0 dl in body)
  - `__NEXT_DATA__` payload inspected (2026-09-04): valid JSON but contains
    only product variant metadata (model codes, titles, images) and UI
    rendering configuration. NO specification label/value records exist.
  - Spec table is rendered by Next.js React components — not accessible via
    static HTTP extraction
- **Extraction result**: NO_OBSERVATIONS

**EVIDENCE STATUS**: The real Seagate Nytro 5050 page produces one raw
specification observation (Form Factor = "2.5in") through embedded JSON
extraction. After the evidence-backed 6B correction ("2.5in" -> "2.5-inch"),
the full pipeline produces VERIFIED resolution for physical_form_factor.

Samsung PM9A3 remains a source-specific static-HTML evidence gap.
Seagate Nytro 5050 demonstrates that deterministic static structured
extraction is sufficient for the minimum real 6C vertical slice.
Current evidence therefore does not justify an LLM extractor.

#### 22.2.5 Resolution Completeness

Every ENTERPRISE_SSD_SCHEMA definition receives a `SpecificationResolution`:
- UNKNOWN when no usable evidence
- VERIFIED when one value with AUTHORITATIVE support
- UNVERIFIED when one value with SECONDARY-only support
- CONFLICT when >1 distinct usable values

No majority voting. No authoritative-wins-conflict. All 12 resolutions
always exist in the `ProductSpecificationSet`.

#### 22.2.6 Source Outcome Vocabulary

| State | Meaning |
| --- | --- |
| EXTRACTED | Fetch succeeded, ≥1 observation extracted |
| NO_OBSERVATIONS | Fetch succeeded, no structured spec data found |
| FETCH_FAILED | PageFetchError prevented acquisition |
| SOURCE_REFUSED | UnsafeFetchTargetError refused acquisition |

Normal PageFetchError: bounded external failure — preserve outcome,
continue with other approved sources.

#### 22.2.7 Architecture Boundaries

**Research extraction module** (`enterprise_ssd_extraction.py`):
- MAY import: stdlib, `product_intelligence.domain`, `product_intelligence.research.*`
- MUST NOT import: providers, execution, web, django, semantic, evaluation, network

**Execution module** (`specification_evidence.py`):
- MAY import: domain, providers.page, research.*
- MUST NOT import: web, django, semantic/FU3 runtime, evaluation, provider concrete adapters
- Depends on PageFetcher protocol, NOT HttpPageFetcher concrete implementation


### 22.3 Comparable-Product Candidate Discovery — 7A Phase Contract

7A implements candidate discovery from approved manufacturer-catalog sources.

**7A answers**: "What evidence-backed products are candidates for later comparison?"
**7A does NOT answer**: "Which candidate is most similar/compatible/better?"

A CANDIDATE means only: a distinct product identity discovered from accepted
source evidence and eligible to proceed to later similarity research (7B+).
Candidate != comparable. 7B owns all similarity/compatibility scoring.

**Production modules:**
    research/comparable_candidates.py (Observation, Source, Assessment, Candidate)
    research/enterprise_ssd_candidate_extraction.py (pure extraction)
    execution/comparable_discovery.py (execution + result audit)

**Key contracts:**
- ComparableCandidateObservation: raw catalog record (exact MPN preserved verbatim, optional title preserved verbatim)
- ComparableCandidateSource: approved source descriptor (AUTHORITATIVE in v1)
- ComparableCandidateAssessment: observation assessed vs target (2A-derived disposition; stores exact ProductIdentity type target_identity; __post_init__ re-derives disposition; rejects subclasses of ProductIdentity)
- ComparableCandidate: deduplicated candidate (normalized-key grouping, all evidence preserved; all evidence inside one candidate must bind to the exact same target_identity object; cross-target evidence is rejected)
- ComparableCandidateDiscoveryResult: self-validating; enforces exact observation->assessment binding, exact target_identity binding, AUTHORITATIVE-only result invariant; foreign assessments in candidate evidence are rejected

**Why ProductIdentity was NOT reused:**
Frozen ProductIdentity represents the requested product's identity.
7A must not manufacture ProductIdentity(match_type=EXACT) for catalog rows.

**Source strategy (v1):**
- Explicitly approved manufacturer catalog sources only.
- No SearchProvider, Serper, search snippets, LLM, embeddings, fuzzy identity.
- AUTHORITATIVE required; SECONDARY rejected before fetch.

**Mechanism:**
- var supportSpecsData = JSON.parse('...') (same structural anchor as 6C)
- Extracts skuNumber + title; ignores features/capacity/performance (that is 7B)
- Bounded JS string decoder (handles JS escapes without corrupting literal non-ASCII Unicode)

**Target-self exclusion:** frozen 2A compare_part_numbers()
**Deduplication:** frozen 2A normalize_part_number() semantics only

**Result audit:** ComparableCandidateDiscoveryResult self-validates all invariants.

**Real vertical slice:** Seagate 81 records -> 81 observations -> 1 TARGET_SELF -> 80 candidates.

### 22.4 Enterprise SSD Similarity Scoring — 7B Phase Contract

**Status: IMPLEMENTED / APPROVED / FROZEN**

7B answers:
    "Given verified specification evidence for the target and candidate,
     how similar are their observable specifications?"

7B does NOT answer:
    "Is this drive guaranteed compatible?"
    "Can this drive replace the target?"
    "Which one should the user buy?"
    "Which candidate is best?"

Similarity != compatibility certification.

No score, rank, recommendation, or compatibility label is produced.
Only auditable field-level similarity evidence.

#### 22.4.1 Input Authority

Uses ONLY frozen contracts:
    ProductSpecificationSet
    ENTERPRISE_SSD_SCHEMA
    ComparableCandidate
    ComparableCandidateDiscoveryResult

A field may contribute to similarity ONLY when:
    target resolution.state == VERIFIED
    AND
    candidate resolution.state == VERIFIED

Do NOT score:
    UNKNOWN
    UNVERIFIED
    CONFLICT

These mean evidence is unavailable/non-authoritative/conflicting.
They are NOT mismatches.

#### 22.4.2 Candidate ProductIdentity Bridge

7A deliberately did NOT reuse ProductIdentity for discovered candidates.
7B requires candidate ProductIdentity because frozen 6C specification
extraction/resolution requires ProductIdentity.

`establish_candidate_product_identity(candidate: ComparableCandidate) -> ProductIdentity`:
    - manufacturer_part_number = candidate.manufacturer_part_number
    - normalized_part_number = candidate.normalized_part_number
    - match_type = IdentityMatchType.EXACT
    - manufacturer = None (NOT guessed)
    - product_name = None (NOT inferred from titles)

The EXACT match_type means "the candidate's own MPN is established by
authoritative evidence." It does NOT mean the candidate equals the target.

The bridge requires EXACT ComparableCandidate type (not isinstance).
Subclasses of ComparableCandidate are rejected. This is an exact-type
contract: `type(candidate) is not ComparableCandidate` raises TypeError.

The bridge rejects non-AUTHORITATIVE evidence. ComparableCandidate itself
enforces AUTHORITATIVE-only, and the bridge re-checks explicitly.

#### 22.4.3 ComparableCandidateSpecificationProfile

Immutable contract binding:
    - candidate (ComparableCandidate, exact type)
    - candidate_identity (ProductIdentity, exact type, from bridge)
    - specification_set (ProductSpecificationSet)

Self-validating:
    - candidate_identity must be the EXACT output of
      establish_candidate_product_identity(candidate)
    - caller may not enrich the identity with manufacturer/product_name/
      category metadata
    - spec set must use the candidate identity (object identity)
    - schema must be ENTERPRISE_SSD_SCHEMA

#### 22.4.4 Field Comparison Contract

`SpecificationSimilarityFieldAssessment` binds:
    definition
    target_resolution
    candidate_resolution
    comparison_state
    field_similarity (Decimal in [0, 1], only when SCORED)

`comparison_state` vocabulary:
    SCORED — both sides VERIFIED, similarity computed
    TARGET_NOT_VERIFIED — target not VERIFIED
    CANDIDATE_NOT_VERIFIED — candidate not VERIFIED
    BOTH_NOT_VERIFIED — neither side VERIFIED

No "mismatch" state for missing evidence.

**Field score self-validation:** When SCORED, the constructor recomputes
the actual field similarity from the raw target and candidate resolutions
using `_compute_field_similarity()`. The supplied `field_similarity` value
is never trusted — it must equal the re-derived score. A caller cannot
supply a wrong-but-in-range value (e.g. 0.73 instead of 0.5 for
3.84 vs 7.68) because the constructor detects the mismatch.

#### 22.4.5 Field Similarity Rules

Uses frozen `SpecificationDefinition.value_kind`:

TEXT:
    canonical exact equality -> 1 if equal, 0 if not

ENUM:
    exact canonical enum equality -> 1 if equal, 0 if not

BOOLEAN:
    exact equality -> 1 if equal, 0 if not

DECIMAL:
    For positive values: min(target, candidate) / max(target, candidate)
    Examples: 3.84 vs 3.84 -> 1, 3.84 vs 7.68 -> 0.5, 7000 vs 6300 -> 0.9

No arbitrary tolerance, no rounding into match buckets, no field-specific
weighting. Invalid/non-positive DECIMAL values propagate as contract errors.

#### 22.4.6 Equal Field Weights

7B v1 has NO domain-business weights.
Every definition in ENTERPRISE_SSD_SCHEMA contributes one possible unit.
No field may be omitted merely because it is currently UNKNOWN in real data.

#### 22.4.7 Aggregate Contract

`EnterpriseSsdCandidateSimilarity`:
    candidate_profile
    target_specification_set
    field_assessments (exactly 12)
    scored_field_count (int, exact type — bool/float rejected)
    evidence_coverage (Decimal, exact type — int rejected)
    observed_similarity (Decimal or None, exact type — float rejected)
    evidence_weighted_similarity (Decimal or None, exact type — bool rejected)

evidence_coverage = scored_field_count / 12
observed_similarity = sum(scored similarities) / scored_field_count (None if 0)
evidence_weighted_similarity = sum(scored similarities) / 12 (None if 0)

Mechanically: evidence_weighted_similarity == observed_similarity * evidence_coverage
(subject only to exact Decimal arithmetic).

No quantization/rounding in the research layer.
No ranking field. No ordinal bucket. No recommendation.

Self-validating: constructor re-derives all computed fields from raw resolutions.
Exact scalar types enforced (bool/int/float substitutes rejected even when
numerically equal). A caller cannot fabricate a higher score, fake coverage,
drop a mismatch field, or substitute resolutions.

#### 22.4.8 Batch Result

`EnterpriseSsdSimilarityResult` is OWNED BY THE EXECUTION LAYER
(`execution/comparable_similarity.py`). It is NOT in the research layer.

Fields:
    discovery_result (frozen ComparableCandidateDiscoveryResult, exact type)
    source_outcomes (tuple of ComparableSimilaritySourceOutcome)
    candidate_profiles (one per candidate)
    similarities (one per profile)

Self-validating:
    - discovery_result must be EXACTLY a ComparableCandidateDiscoveryResult
      (no duck typing, no subclasses)
    - source_outcomes retained in result (not discarded)
    - **7A source binding:** canonical EXTRACTED source descriptors are
      derived from the frozen 7A result (same dedup semantics as the
      pipeline: ComparableCandidateSource value equality, first-seen wins).
      Each 7B source outcome.source must be the exact same object
      (object identity: `outcome.source is canonical_7a_source`).
      Copied/value-equal substitutes are rejected.
      Count and order must match exactly.
    - final_url is structurally validated by `require_fetchable_url()`
    - Exact candidate object identity binding
    - Order exactly matches discovery_result.candidates order
    - Every similarity targets discovery_result.target_specification_set
    - No missing candidate, no foreign candidate, no duplicate candidate
    - No ranking/top-N field

**Candidate spec provenance audit:** For every candidate profile,
for every SpecificationResolution, for every observation in resolution.evidence,
the provenance audit verifies:
    - observation.product_identity is profile.candidate_identity
    - A FETCHED 7B source outcome exists where:
        observation.source_name == outcome.source.source_name
        observation.source_authority is outcome.source.source_authority
        observation.source_url == outcome.final_url
        observation.retrieved_at == outcome.retrieved_at
    - Evidence from FETCH_FAILED, SOURCE_REFUSED, foreign URL, wrong timestamp,
      wrong source, wrong authority, another candidate, or unaccounted source
      fails closed.
    - Zero evidence is legal (UNKNOWN resolution with empty evidence).

#### 22.4.9 Execution

`research_and_score_enterprise_ssd_candidates(discovery_result, page_fetcher)`:
    1. Validate discovery_result is EXACTLY ComparableCandidateDiscoveryResult
       (TypeError BEFORE any fetch)
    2. Identify EXTRACTED source outcomes from frozen 7A result
    3. Fetch each unique EXTRACTED source exactly ONCE
       (deduplicated by source descriptor, not by outcome identity)
    4. For each candidate:
       a. establish_candidate_product_identity (7B bridge)
       b. extract_enterprise_ssd_specification_observations (frozen 6C)
          from each fetched document (reuse in memory, no refetch per candidate)
       c. normalize_enterprise_ssd_observation (frozen 6B)
       d. resolve_specification (frozen 6A)
       e. Build ComparableCandidateSpecificationProfile
    5. Score each candidate via score_enterprise_ssd_candidate_similarity
    6. Return self-validating EnterpriseSsdSimilarityResult with:
       - retained source_outcomes
       - one FETCHED/FAILED outcome per unique source
       - provenance-audited candidate profiles

Does NOT rediscover candidates. Does NOT use SearchProvider.
One fetch per unique source (not one fetch per candidate).

7B source outcome states:
    FETCHED — page fetched, final_url + retrieved_at present
    FETCH_FAILED — PageFetchError caught, final_url=None, retrieved_at=None
    SOURCE_REFUSED — UnsafeFetchTargetError caught, final_url=None, retrieved_at=None

7B source outcomes are RETAINED in the result, not discarded.

#### 22.4.10 Architecture Boundaries

`research/enterprise_ssd_similarity.py` may import:
    stdlib, domain, research specifications, research enterprise_ssd,
    research comparable_candidates, Decimal

Must NOT import:
    providers, execution, runs, web, django, SearchProvider, semantic,
    evaluation, filesystem, environment

`execution/comparable_similarity.py` may import:
    domain, providers.page (including require_fetchable_url), frozen research
    contracts, frozen 6C extractor/normalizer/resolver, frozen 7A contracts,
    7B similarity research contracts

Must NOT import:
    providers.search, providers.serper, HttpPageFetcher concrete,
    semantic, evaluation, web, Django, persistence/runs

**EnterpriseSsdSimilarityResult is execution-owned.** The research layer
contains only the pure scoring logic and candidate identity bridge.

#### 22.4.11 Real Seagate Coverage Result

Under current frozen 6C extraction capability (only "Form Factor" label
mapped), real Seagate Nytro 5050 fixture produces:
    - 81 observations -> 1 TARGET_SELF -> 80 candidates
    - Each candidate: 1 scoreable field (physical_form_factor)
    - evidence_coverage = 1/12 for all candidates
    - observed_similarity = 1 (same form factor across siblings)
    - evidence_weighted_similarity = 1/12 for all candidates
    - 1 fetch per source (not 80)
    - source_outcomes retained with exact 7A source descriptor binding
    - candidate spec evidence provenance traced to FETCHED 7B outcomes

Current candidate specification evidence is too sparse for useful
differentiation. This is a limitation of frozen 6C extraction capability,
not a 7B failure. Candidate specification enrichment is required before
useful 7C presentation.

### 22.5 Corrective follow-up phases

Three follow-ups (0A-FU1, 1A-FU1, 2A-FU1) each corrected a real contract- or
data-integrity defect before its phase was frozen, and each was worth its cost.
From 2B onward, a *standalone* follow-up phase carries a higher bar and should
normally be reserved for a defect that materially threatens one of:

* false confidence or a false exact match,
* data integrity,
* security,
* provider cost,
* a hard architectural boundary.

Everything else — minor cleanup, wording, speculative future-proofing, and
theoretical edge cases — should be folded into the next phase, recorded as known
debt, or deferred until real provider evidence shows whether it matters at all.

This is not a severity framework and not a process to administer. It exists for
one reason: the cost of architecture latency is now higher than the cost of a
small imperfection carried forward for one phase.

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
not read their absence as an oversight: reopen / resume semantics on an
existing run · a per-transition event or history table · persisted failure
diagnostics · distributed locking · a server database in place of development
SQLite. *(Note: 4C-C implements `retry_run` which creates a NEW run from a
failed run's request and executes it. This is not the same as reopening the
existing run — the old run remains in FAILED state.)*

**4C-A implements atomic execution claim and terminal transition using a
database-level compare-and-set pattern (conditional UPDATE) instead of
`SELECT FOR UPDATE`.** The atomicity is portable across SQLite, PostgreSQL,
and MySQL. The decision to persist evidence relationally in `runs/` was
recorded in 4C-A and is stable for the MVP.

Also deferred as capability, per the roadmap rather than per this list: real
product lookup, generic LLM provider abstraction (the `LLMProvider` boundary
interface — not the existing FU3A/FU3B semantic runtime), prompt engineering
for future generic LLM phases, global market-price selection and reporting,
similarity scoring (7B), and the research API. FoxPro launcher
server-side GET contract is implemented (5B); FoxPro-side client is maintained
outside this repository. Real web search exists as of 2C, real page
fetching plus raw listing extraction as of 3A, deterministic listing
normalization as of 3B, deterministic MPN matching and listing rejection as
of 3C, and deterministic price aggregation (bucket-level statistics) as of 4A
— all five can be called directly. *As of 4C-B, backend orchestration is
implemented:* the `execution/` package calls `search()`, `fetch()`,
`normalize_listing_observation()`, and `aggregate_listing_prices()` as part of
the ordinary backend research pipeline. *As of 4C-C (frozen), the web form
calls these through the backend executor.* *No API calls these* — that is 5A.
*As of 7A, comparable-product candidate discovery is implemented*
(evidence-backed, from approved manufacturer catalog sources only).
Similarity scoring and comparison reporting remain deferred to 7B/7C.

Deferred specifically around page fetching and extraction (3A), so that a later
phase does not read their absence as an oversight: browser-rendered fetching of
any kind (headless browser, browser farm, managed scraping service) ·
bot-detection evasion, user-agent rotation, and proxies · retry policy and
backoff · robots/politeness scheduling · crawling, link traversal, and sitemap
discovery · asset fetching · page or response caching · a standalone Django model for
`FetchedPage` or a `ListingObservation` · a source-specific extraction strategy
(permitted by §16 once a fixture justifies one; none did) · microdata and RDFa
parsing · visible-text price extraction of any kind (permanently excluded, not
deferred) · MPN inference from a title, snippet, or URL · DNS pinning and
connection-level SSRF hardening (§13.6, deployment-level, 8C).

Deferred specifically around listing normalization (3B), so that a later phase
does not read their absence as an oversight: quantity and pack-size
normalization and unit-price calculation (no recorded fixture publishes raw
evidence for any of the three — §16.2) · currency conversion of any kind, live
or hardcoded · seller entity resolution · condition or availability inference
from marketing prose (`"like new"`, `"open box"`) · a standalone Django model
for `NormalizedListingObservation` · any acceptance, rejection, confidence, or
aggregate field on the normalized contract.

Deferred specifically around MPN matching and listing rejection (3C), so that
a later phase does not read their absence as an oversight: fuzzy or
edit-distance matching over part numbers · character-confusion tables
(`O`/`0`, `I`/`l`/`1`) · semantic matching from description text ·
per-manufacturer normalization profiles or trust rules · SKU-as-MPN inference
rules · listing acceptance on description-only matches · confidence scoring on
the assessment · a standalone Django model for `ListingIdentityAssessment` · any aggregation
over accepted listings. `PARTIAL` classification exists and is explicitly
rejected — it is informative but not price-eligible identity evidence.

Deferred specifically around part-number identity (2A), so that a later phase
does not read their absence as an oversight: partial or fuzzy part-number
matching of any kind · edit distance and similarity scoring over part numbers ·
character-confusion tables (`O`/`0`, `I`/`l`/`1`) · Unicode compatibility
normalization · per-manufacturer normalization profiles · candidate ranking ·
a runtime product catalog · persistence of a comparison result.

Deferred specifically around the search-provider boundary (2B), so that a later
phase does not read their absence as an oversight: provider registry · provider
factory · plugin discovery · dependency-injection container · provider manager ·
fallback chain · multi-provider orchestration or fan-out · retry policy ·
rate-limit scheduling · circuit breakers · async provider interface · a provider
error taxonomy beyond one base exception · pagination and result-limit policy ·
locale and category query parameters · query generation · persistence of search
results · a numeric price field on a search result.

Deferred specifically around the Serper adapter (2C), so that a later phase
does not read their absence as an oversight: Google Shopping · a second search
provider · duplicate-paid-call protection (required before, not at, the phase
that first calls it from ordinary execution — §18.1; *deferred at the end of
2C, later resolved by 4C-A via atomic `claim_execution`*) · query generation
from a `ResearchRequest` · automatic invocation from `runs/` or `web/` (*deferred
at the end of 2C; later resolved by 4C-B/4C-C backend orchestration and web
execution wiring*) · page fetching or crawling of any kind · MPN inference from
a title, snippet, or URL · price extraction from snippet text · a provider
error taxonomy beyond the existing single `SearchProviderError`.

Open questions currently `UNDECIDED`: LLM vendor · report
access control (the identifier scheme was settled in 1A as a random UUID, which
is explicitly not access control) · which aggregate represents
"market price" · advanced outlier policy (4A has settled: no automatic
outlier removal; extreme but accepted prices expand the observed low/high) ·
description truncation policy for URL
length limits · first product category · cache storage mechanism · batch
intake design · every evaluation pass/fail threshold (§21.3) · the recorded
listing-snapshot format for price evaluation (§21.4). Search vendor is settled
as of 2C: Serper, ordinary Google Search only.

## 24. Current repository status

The volatile current implementation snapshot is maintained in:

    docs/PRODUCT_INTELLIGENCE_STATUS.md

STATUS.md owns:
- latest completed phase
- next planned phase
- concise implemented-capability snapshot
- current blockers/debt
- latest validation baseline

This canonical plan does not duplicate that operational snapshot.

§22 remains the canonical phased roadmap and implementation-history record.

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
| AD-025 | Persistence lives in its own Django application, `product_intelligence/runs/`, holding the project's models. The domain and the research core stay database-free, and the web layer does not own the lifecycle. 4B added `PriceIntelligenceSnapshot` as a second model (see AD-050); both live in `runs/` so no other layer carries a Django model. | Each of the three alternatives breaks something specific. A model in `domain/` would make the contracts require Django to import, contradicting AD-013 and failing the guard that enforces it. A model in `research/` would tie the engine to a database, so no part of it could be reasoned about or tested without one — and the engine is the piece most likely to be exercised in isolation. Ownership in `web/` would make a run's existence a property of the transport that created it, which is exactly the caller-coupling AD-001 exists to prevent; a run outlives its request and belongs to no client. A fourth package costs one directory and keeps the dependency arrow pointing one way: `runs` imports `domain`, never the reverse. | Accepted (1A) |
| AD-026 | A run's primary key is an application-generated random UUID, serving as both the database key and the public report identifier. Opacity is explicitly **not** access control. | The report URL `/research/<id>` has to be durable and non-enumerable, and a UUID primary key gives both without a second identifier to keep in sync — a separate public id alongside a sequential key would add a consistency obligation for no capability. Generating it in the application rather than the database means the identity exists before the first write, so nothing has to round-trip to learn it. The second half of the decision matters more than the first: unguessability is not authorization, and writing it down here is what stops a later phase from treating "the URL is hard to guess" as a security answer. Report visibility stays `UNDECIDED` per §19. | Accepted (1A) |
| AD-027 | Transitions go through one method against an explicit table; terminal states are terminal; an illegal move raises and changes nothing; assigning `state` on a saved run and calling `save()` is refused. | Two failure modes are worth engineering against. The first is silent coercion — clamping an illegal move to the nearest legal state would tell a caller a run progressed when it did not, which is AD-009's fabricated certainty wearing a state machine's clothes. The second is the bypass: a convention that says "use `transition_to`" is obeyed until the first hurried caller, and then the lifecycle rules are advisory forever. AD-014 says invariants are enforced by tests rather than documents; the same logic applies to the API itself, and the guard costs a handful of lines. Retry and reopen stay out because no phase has asked for them and a re-run is honestly a new run. | Accepted (1A) |
| AD-028 | A run records three timestamps and nothing else about its history. No event table, and no persisted failure diagnostics. | `created_at` / `started_at` / `finished_at` fully audit a lifecycle with four edges — a history table would record the same three facts in a shape justified only by transitions that do not exist. `FAILED` is a state, not a stack trace: nothing currently executes a run, so any diagnostics schema would be designed against imagined failures and would be wrong in the specific ways that matter. Research history is 8B, and the phase that first produces real failures is the one that can see what is worth keeping. | Accepted (1A) |
| AD-029 | Cross-process transition atomicity is not guaranteed. The limitation is documented in §15.7 rather than solved. | `transition_to` checks the in-memory state and writes; two concurrent writers could both pass the check and the last write would win. The honest options were to fix it, to hide it, or to state it. Fixing it means conditional updates or row locking built against a concurrency scenario the system cannot yet produce — there is no worker, no queue, and nothing that executes a run, so the fix would ship untested by anything real. Hiding it would leave a later phase trusting a guarantee that was never made. Stating it costs nothing and hands the phase that introduces a second writer both the problem and the reason it was left. | Accepted (1A) |
| AD-030 | One check constraint states the complete state/timestamp shape of a stored row, replacing the narrower "finished implies started" rule; and a run may only be *created* in `CREATED`. The database judges the row; the application judges the path. | 1A relied on application code for a rule the database was only half-checking, and the gap was not theoretical: an audit found ten invalid shapes that ordinary ORM calls persisted, including a `COMPLETED` run that never started. A guarantee that holds only when callers use the intended method is a convention, and this one is cheap to make real. One expression rather than several overlapping rules means a single place to read what a valid row is, no gap between rules to fall through, and — because every branch names a state — storage-level confinement of `state` to the vocabulary, which `choices` alone does not give. The creation rule closes the other half: without it, a run could be inserted directly into a terminal state, structurally valid and a complete fiction about what happened. What the constraint deliberately does **not** do is prove provenance: a check sees one row, never the sequence that produced it, so `QuerySet.update()` and raw SQL can still skip the transition path. That residue is documented (§15.6) rather than chased with triggers or a history table, both of which AD-028 rules out. | Accepted (1A-FU1) |
| AD-031 | The Django floor is the supported 5.2 LTS line (`>=5.2,<6.0`), not the oldest release whose API happens to compile. | 1A set the floor at 5.1 because `CheckConstraint(condition=…)` arrived there. That is a statement about syntax availability, not about whether the release is safe to run: 5.1 is out of security support, so the declaration invited an installation receiving no fixes. A dependency floor is a support commitment. The upper bound stays below 6.0 — moving to a new major line is its own decision with its own testing, not a side effect of a correction. `requires-python = ">=3.12"` is unchanged; the development environment runs Python 3.14.7, which satisfies both. | Accepted (1A-FU1) |
| AD-032 | The web layer is a Django application with no model, and its form validates by *constructing* `ResearchRequest` rather than by restating the rules. Both fields are individually optional and keep their submitted text (`strip=False`); no part-number normalization happens at the boundary. | Two policies for what valid intake is would drift, and nothing would fail when they did — a form that grew its own "at least one field" rule, or its own trimming, would silently decide what the canonical contract is supposed to decide. Constructing the contract and translating `DomainValidationError` into a visible error keeps one authority and makes the persisted values identical to what any other intake would produce. `strip=False` matters even though Django's stripping agrees with the contract today: leaving it on would mean the form quietly co-owns a normalization rule, and a later change on either side would be invisible until stored values disagreed. Normalizing a part number here would be worse still — it is a matching decision (2A/3C) taken in the one layer forbidden to make one, where one character can mean a different product. The application holds no model because a run outlives the request that created it and belongs to no caller (AD-025). | Accepted (1B) |
| AD-033 | A GET creates nothing. The browser workflow is Post/Redirect/Get, and the launcher entry point that turns `?mpn=…&description=…` into a prefilled form (no side effect) stays in 5B; 1B reserved the launcher concern for 5B; 5B resolved it as prefill-only GET, preserving no-side-effect GET semantics. | The 1B route shape is deliberately the one 5B will adapt, which makes "it would be two lines to honour the parameters now" the obvious mistake to prevent. A GET that creates records is a side effect on a method defined not to have one: a prefetch, a crawler, a bookmark, or a refresh would each start research, and the run table would fill with requests nobody made. Post/Redirect/Get is the other half — without the redirect, the page a user lands on is the submission itself, and reloading a report would silently create duplicates of it. The launcher also needs decisions 1B has not made (URL length limits, truncation policy, encoding), so implementing it early would guess at them. | Accepted (1B) |
| AD-034 | The report shell states that research execution is not connected. No spinner, no polling, no simulated delay, no placeholder price, median, seller table, or example comparable. | A progress indicator over nothing is fabricated certainty with an animation (AD-009): it tells the user work is under way, and the only honest fact is that no execution engine exists. The same reasoning rules out placeholder values — a `$0` or an `N/A median` on a page titled with a real part number is a claim the system has no evidence for, and the evidence-first rule (AD-007) means a number appears only with the listings behind it. A blank "no results exist" section is not a gap in the phase; it is the accurate report, and it is the durable place later phases fill. Displaying an evaluation-corpus case here would be worse again: benchmark truth is reference data, never a result (AD-020). | Accepted (1B) |
| AD-035 | **Amended by AD-037.** Originally: part-number normalization removes one closed, explicitly enumerated formatting allowlist — ASCII whitespace plus `-`, `_`, `/`, `.` — with ASCII-only case folding, everything else being data. | The *exclusions* stand and are the durable half of this entry: "remove every non-alphanumeric character" is rejected because it erases characters that distinguish real products and widens itself every time an unfamiliar character appears; an enumerated set makes each addition an edit someone has to defend; and broad Unicode compatibility folding is excluded because it merges code points whose identity equivalence no phase has approved, which is also why case folding is an explicit ASCII table rather than `str.upper()`. What did not stand was *removal*: deleting the enumerated characters discarded where a boundary was, not merely how it was written. See AD-037. | Amended (2A-FU1) |
| AD-036 | The 2A comparator returns only `EXACT`, `NORMALIZED_EXACT`, or `UNKNOWN`; it carries no confidence, invents no product facts, does no partial or fuzzy matching, and is wired into nothing. | Each exclusion closes a specific way a narrow primitive turns into a false conclusion. `CONFLICT` would be the comparator claiming evidence is incompatible when all it saw was two different strings. `PARTIAL` — or any containment, edit-distance, or similarity rule — would raise recall by weakening identity, which is the one trade this product cannot make: `MTFDKCC3T8TFR` is a family prefix, not an orderable part. A confidence band would equate mechanism with trustworthiness, and `EXACT` is not `HIGH`: the string matched, which says nothing about whether the source, the description, or the listing is sound. A catalog inside the comparator would take benchmark answers from the evaluation corpus and make them production resolution logic, which is test leakage with the corpus's own truth. And wiring it into the web shell or the run lifecycle would connect a comparator to a system that supplies no candidates, so anything displayed would be invented — integration belongs to the phase with real candidate evidence. A guard test asserts `runs` and `evaluation` do not import the research core. `web` has a narrow read-only research dependency (codec + display contracts, approved by AD-050); the guard test enforces an explicit symbol-level allowlist. | Accepted (2A) |
| AD-037 | Normalization canonicalizes how a structural boundary was written and never whether one exists. An internal ASCII-whitespace run is *written as* a hyphen; no separator is deleted; and `_`, `/`, `.` are data rather than spellings of a hyphen. | AD-035's implementation deleted every enumerated separator wherever it appeared, which collapsed `AB-C123`, `ABC-123`, `ABC123`, and `A-B-C-1-2-3` onto one key and reported them as the same part number. Those are false exacts, and a false exact is the failure this product is built to avoid — the first pair is the clearest: the same characters with the boundary in a different place are not the same identifier by any reading. The error was evidential, not clerical. The corpus supports exactly one substitution — SYN-0008's `bcm957504 n425g` for `BCM957504-N425G`, whitespace against a hyphen — and the implementation had generalized one case about one separator into a rule about four, then gone further and thrown position away as well. Five verified part numbers cannot establish that separator position is globally irrelevant across manufacturers, and the burden runs the other way: an equivalence is approved per separator, with evidence, or it is not approved. Preserving structure also repairs auditability, because a normalized key that keeps its boundaries shows a reviewer *why* two values matched rather than only that they did. The cost is abstention on `ABC_123` against `ABC-123` (§12.2), which is the cheap direction: a missed normalized match costs a re-query, a false exact costs a wrong price on a real order. | Accepted (2A-FU1) |
| AD-038 | The provider boundary returns provider-neutral observations. `SearchQuery` is one external search operation and is deliberately not `ResearchRequest`; a provider is a `Protocol` with one synchronous `search` method and no registry, factory, fallback chain, retry policy, or async variant. | Two different mistakes are being avoided at once. Passing `ResearchRequest` into a provider would make the adapter decide what to search for — query generation is a research decision, and one request may legitimately produce several queries, so the provider would end up owning research semantics inside a transport layer. Building a provider *framework* would be the opposite error: registries, factories, and fallback chains are machinery for a problem the project does not have, since exactly one provider arrives in 2C and nothing has shown a need for a second. A protocol with one method costs nothing to replace and nothing to carry, and the boundary's whole job is to be the thing business logic depends on instead of a vendor (AD-011). The one exception type follows the same logic: a taxonomy of timeout / quota / auth / parse failures designed before any provider has failed would be wrong in the places that matter, and 2C can subdivide it against real behaviour. | Accepted (2B) |
| AD-039 | A search result carries a price *hint* as text and a part-number *hint* as unverified published text. The contract has no numeric price field, no currency, and no match or confidence field; result URLs must be absolute `http`/`https`. | A search snippet saying `$399.99` is not a price: it may be a sale price, a monthly payment, a shipping charge, a range, a price for a multi-pack, or a different currency's symbol, and choosing among those is exactly what 3A/3B exist to do with recorded rules and rejection reasons. A `Decimal` field on this contract would let a snippet enter arithmetic as though it were a verified market observation, which is fabricated certainty (AD-009) arriving through the cheapest possible door — so the absence of the field, asserted by a test on the exact field list, is the safeguard. The part-number hint is the same argument for identity: a value a provider publishes is an observation, and calling it verified would make a vendor the authority on product identity, which AD-008 forbids. Keeping it unnormalized also keeps the two paths distinct — a *published* field is a hint, a part number *inferred* from title or snippet text is extraction (3A/3C) and must carry its own rejection reasoning. The URL rule is narrow and separate: a result is evidence only if someone can re-open it, and `javascript:`, `data:`, and `file:` values are not addresses of that kind and must not reach a report. | Accepted (2B) |
| AD-040 | Provider-native payload material is preserved as an **opaque string reference**, never as a structure business logic reads. Normalized contract fields are what the core consumes. | Real providers return more than any contract will hold, and the useful residue has to be kept — evidence-first (AD-007) means what was actually returned stays inspectable. The tempting shortcut is to attach the vendor's parsed payload as a `dict` and let callers reach into it "just for now". That is how a vendor gets into business logic permanently: one research rule reads one vendor-specific key, and the boundary that exists to make providers replaceable has been bypassed while still appearing to be in place. An opaque string cannot be read that way without a deliberate parse that no rule may perform, so the material is preserved for humans, fixtures, and later phases without becoming an interface. It is also kept verbatim rather than trimmed, because it is the artifact a recorded fixture is compared against. | Accepted (2B) |
| AD-041 | Real recorded provider fixtures begin with the first real provider (2C). 2B tests its boundary with synthetic fakes only, and no fixture is invented in advance. | A recorded fixture's whole value is that it is what a real service actually returned, so an adapter's mapping can be regression-tested offline without credentials or network. A fixture written before a provider is chosen would be a guess wearing that authority: it would pass whatever the adapter did, and it would quietly encode an imagined payload shape as the expected one — the same failure mode AD-024 forbids in the evaluation corpus. Fakes are honest about being fakes and are sufficient to prove the interface is satisfiable. Sanitization (credentials, tokens, request secrets, personal and customer data removed) is part of the policy rather than an afterthought, because the first recording will otherwise be made from a real authenticated call. | Accepted (2B) |
| AD-042 | Serper is the first real `SearchProvider`, integrated as one adapter (`providers/serper.py`) calling ordinary Google Search only; the credential is read from `SERPER_API_KEY` in the server environment inside one constructor (`from_environment`) and sent in Serper's documented header; `price_hint_text` and `part_number_hint` stay `None` for every mapped result. | A vendor had to be chosen to prove the 2B boundary against reality, and Serper's ordinary-search endpoint is the narrowest real surface that does so without also deciding a pricing-extraction question (Shopping) or an orchestration question (query generation) the roadmap has not reached yet. Reading the credential only inside one environment-backed constructor keeps the adapter testable by direct construction (`SerperSearchProvider(api_key=...)`) without the real environment, mirrors AD-005's "no secrets in the client" rule at the server edge, and matches the phase brief's instruction to keep configuration reading at the adapter/config edge rather than build an application-wide settings framework. `price_hint_text` and `part_number_hint` staying `None` is not caution for its own sake: ordinary Google Search organic results do not publish either field, confirmed against the real recorded fixture, and inventing either by regexing a snippet or a URL would be extraction (3A/3C) performed inside a transport adapter — the exact layering violation AD-039 exists to prevent. | Accepted (2C) |
| AD-043 | Page fetching enters through a second provider boundary (`providers/page.py`) with one standard-library implementation (`providers/http_page.py`). A `SearchResult`, a `FetchedPage`, and a `ListingObservation` are three distinct observations and are never collapsed. Extraction lives in the research core and takes a document *string*, so neither half imports the other. | The layering is the decision. A search snippet is a third party's description of a page; the page is what that URL returned; and a listing observation is what the document publishes. Collapsing the first two would let a snippet be reported as page evidence — precisely the conversion AD-039 refused when it kept a numeric price off `SearchResult`. Collapsing the last two would put document parsing in a transport adapter and page retrieval in the engine, which is how the research core acquires a network stack and stops being testable without one. Passing a string rather than a `FetchedPage` is what makes the separation structural rather than stylistic: the research guards already forbid `providers` imports, and a shared type would have forced either a relaxation or a domain-level contract that both layers depend on — a third thing to keep in sync for no capability. The two halves meet in a caller that holds both, which today is one manual script and tomorrow is whichever phase orchestrates research. | Accepted (3A) |
| AD-044 | The fetcher is bounded (timeout, redirects, response size, HTML-only content types), sends no credential or cookie, issues GET only, follows redirects itself, and refuses any destination resolving to a non-public address — while the documentation states plainly that this is not network isolation, and that DNS rebinding and general egress remain open at the application layer. | A fetcher consuming URLs that originated from an external search provider is an SSRF primitive unless it is built as one that is not, and the ordinary attack is not exotic: a public host that 302s to `http://169.254.169.254/`. Two implementation choices carry most of the weight and both were deliberate. Following redirects manually was necessary because `urllib` would otherwise follow them transparently and the address checks would apply to every hop except the only one that matters — the last. Assembling the opener by hand was necessary because `build_opener()` installs `FileHandler`, `FTPHandler`, and `ProxyHandler`, each of which lets a URL or an ambient environment variable send the fetch somewhere other than the public page requested. Refusing an oversized response rather than truncating it follows AD-009: a truncated document parses as though it were whole, so the failure would surface as *fewer listings*, which is a wrong answer delivered quietly rather than an error delivered loudly. The honesty clause is the other half of the decision. Closing the DNS time-of-check/time-of-use gap means owning the socket — resolving once, connecting to the pinned address, and carrying the hostname through TLS verification — which is a change to how connections are made and belongs to deployment hardening (8C), not to a phase learning what pages contain. Stating the residue costs nothing and stops a later phase from trusting a guarantee that was never made, exactly as AD-029 did for transition atomicity. | Accepted (3A) |
| AD-045 | Extraction reads only structured data a page deliberately published — `schema.org` JSON-LD first, flat product meta second and only when JSON-LD yielded nothing — and every extracted value stays raw text. No visible-text price scan exists, and none may be added. An `AggregateOffer` yields no price at all. | Three real pages sampled in this phase settle this better than argument could. One publishes `"price": "undefined"` inside a well-formed `Offer`: a converting extractor raises on it or silently drops the offer, and a reviewer sees neither. One publishes `"1055.85"` in JSON-LD and `"1,055.85"` in OpenGraph — the same money, twice, on one page, which is why the second mechanism is a fallback rather than an addition; running both would turn one offer into two observations and 4A counts observations. One publishes a price with no currency anywhere and an `availability` of `"false"`, which no vocabulary contains. Converting at this layer would mean each of those either fails or is guessed at inside a parser with nowhere to record which, whereas raw text moves the decision to 3B where "unparseable price" and "no currency" are outcomes with reasons attached. The prohibition on visible-text scanning is stronger than a preference and is recorded as permanent: the sampled storefront carries fourteen distinct dollar amounts — a shipping threshold, financing bounds, a per-instalment figure, four recommended products in markup identical to the real price element — so first-match, lowest-match, and largest-match rules each return a wrong number with total confidence. The `AggregateOffer` refusal is the same rule in miniature: a low and a high across sellers is a range, and picking an end is lowest-wins wearing a schema name. Parsing with `parse_float=str` is what makes "raw" true rather than aspirational — a float has already discarded how the page wrote the number. | Accepted (3A) |
| AD-046 | A raw price becomes `Decimal` only when it names one unambiguous amount; anything naming a range, a discount, or a recurring payment abstains with `AMBIGUOUS_PRICE`, and anything else unparseable abstains with `INVALID_PRICE` — never a chosen amount, never `Decimal("0")`. Currency normalizes to a small conservative code set with no symbol treated as globally unique (`$` and `¥` are never mapped, embedded in a price or not), and no exchange-rate conversion exists anywhere, in this phase or any later one. **An unambiguous currency embedded directly in `price_text` (`"EUR 100"`, `"100 EUR"`, `"€100"`) is real currency evidence and is reconciled with `currency_text` rather than discarded**: agreement (or one source alone) yields that currency; disagreement between the two yields `currency_code=None` plus a recorded `CONFLICTING_CURRENCY` issue, without discarding an otherwise-valid `price_amount`. A price decorated with a currency marker on both sides (`"EUR 100 USD"`, `"$100 EUR"`) never normalizes cleanly, agreeing or not. | `"from $399"`, `"$399 - $449"`, `"$33/mo"`, and `"You save $565"` each contain a syntactically valid-looking number, and picking any of them — first, lowest, largest, or "the one after the word 'from'" — would be the identical mistake 3A already refused for visible-text scanning (AD-045), moved one layer later where it would be easier to excuse as "just normalization". `"undefined"` becoming `Decimal("0")` would be worse than raising: a template failure would silently enter arithmetic as a real, cheap price. On currency, `$` prices four different national currencies and `¥` prices two; mapping either to one guess is the fabricated certainty AD-009 already forbids, so both stay unmapped even though doing so leaves some real prices with `currency_code=None`. FX conversion is excluded on the same evidentiary standard as everything else in this system: a rate is itself a market observation with its own source and retrieval time, and applying one silently would manufacture a number no evidence supports — §16 already committed to this for 4A, and 3B is the first phase in a position to violate it by convenience. The reconciliation rule closes a gap found before the phase was frozen: an earlier draft derived `currency_code` from `currency_text` alone, so `price_text="EUR 100"` beside `currency_text="USD"` silently normalized to `currency_code="USD"` — contradictory evidence producing a clean, confident, wrong answer, which is exactly the false confidence AD-009 forbids. Discarding the embedded evidence instead (keeping `currency_text` as the sole source) would have been equally wrong in the other direction: a page that plainly writes `"EUR 100"` and nothing else is not thereby evidence-free about its own currency. Refusing doubly-decorated text is the same abstention discipline applied to the decoration itself, not just the digits: a regex with two independently optional decoration slots can match `"EUR 100 USD"` structurally, and treating that as one clean price/currency pair — by picking a side or by inferring agreement — would be a guess wearing a successful parse. | Accepted (3B) |
| AD-047 | Quantity, pack size, and unit-price normalization were not implemented in 3B, and `ListingObservation` was not extended to carry raw fields for them. | The phase instructions required checking real evidence before building: an audit of every field in all five recorded 3A fixtures found no structured field on any of them meaning "this offer sells N units for this price" — an inventory count, a minimum-order quantity, and a capacity figure are each a different fact, and none is pack size. Building the normalization logic anyway would mean inventing a raw input to feed it, most plausibly by parsing a product title (`"3.84TB"`, `"MZ-QL23T800"`) — exactly the guess 3A's own MPN-in-title exclusion already rejected for identity, applied here to commercial quantity instead. Extending `ListingObservation` speculatively would also break 3A's own precedent: `ExtractionMethod` deliberately carries no member for an unbuilt mechanism, on the stated principle that a vocabulary entry nothing produces is a placeholder for behaviour that does not exist. The absence is recorded here, in §16.2, and in the completion report specifically so 3C is not the phase that discovers it by surprise. | Accepted (3B) |
| AD-048 | Only an explicit MPN field carrying `EXACT` or `NORMALIZED_EXACT` (2A) is automatically accepted; SKU and title evidence alone never establish MPN identity; `PARTIAL` is informative but never price-eligible identity evidence. | Three concrete risks are being closed. First: a SKU is a retailer's internal identifier and may equal an MPN by coincidence, by convention, or never — treating it as MPN evidence would let a false match through every time a retailer happens to reuse the manufacturer's format. Second: title text is free-form marketing prose where the MPN may appear as a contained token (`"Samsung MZ-QL23T800 Ultra"`) and accepting it would be matching a substring, which is precisely the partial-identity trap that costs a wrong price on a real order. Third: partial overlap (`MTFDKCC3T8TFR` vs `MTFDKCC3T8TFR-1BC1ZABYY`) looks like evidence but is exactly the family-prefix confusion the system must avoid — PARTIAL does not establish requested-product identity and therefore is not price-eligible evidence. The acceptance rule is therefore narrow: one explicit structured MPN field, one deterministic comparator (2A), and nothing weaker crosses the line. When no explicit MPN is published, the listing is `REJECTED` with `NO_EXPLICIT_MPN_EVIDENCE`, not `UNKNOWN` — the absence of evidence is recorded, not left silent. A narrow `mpn:` wrapper cleanup is permitted because one recorded page (`exxactcorp_pm9a3_mz_ql23t800.html`) publishes its MPN as `"mpn:MZ-QL23T800"`, and the `mpn:` prefix is a field-label wrapper, not the identifier itself. It applies to the explicit MPN field only, is not generalized to arbitrary `key:` stripping, and leaves the 2A normalizer unchanged. | Accepted (3C) |
| AD-049 | Aggregation groups identity-accepted listings by exact currency + known condition, computes count/low/median/high from each bucket, derives confidence LOW/MEDIUM from observation count, and excludes every non-accepted or ineligible listing with a recorded reason. Exact duplicate input values refused at the boundary. No FX conversion, no outlier removal, no broad market-listing deduplication, no LLM confidence, no invented evidence, no availability eligibility rule. | Grouping by exact currency (never cross-currency) and known condition (UNKNOWN excluded, not grouped) keeps comparable pools real: a $100 USD price and a $100 EUR price are not the same price, and a NEW listing and a REFURBISHED listing serve different market expectations. Median uses custom exact Decimal midpoint for even counts — no `statistics.median` dependency. Confidence derived from count (`LOW` for 1-2, `MEDIUM` for >=3) tells the user how many independent observations support the number. 4A never produces `HIGH` or `VERY_HIGH`. Exact duplicate INPUT VALUES (two ListingIdentityAssessment objects equal by value) are refused at the input boundary with `ValueError` — the check is value-based, not identity-based, so separately constructed equal objects are caught. No broad market-listing deduplication exists: genuinely different assessments with the same price, currency, and condition are not duplicates because their evidence (source, seller, observation) differs. The exclusion discipline follows AD-007: evidence-first means the user can see not only what was accepted but why each rejected or ineligible listing was excluded. No FX conversion, no outlier removal, no unit-price inference, no manual override — those would each add a decision the system has no evidence to make and no mechanism to audit. | Accepted (4A) |
| AD-050 | One versioned `PriceIntelligenceSnapshot` per `ResearchRun`, persisted in `runs/`, using the `ResearchRun` UUID as the snapshot identity. The snapshot preserves a `PriceAggregationResult` as opaque versioned JSON (`schema_version` + `payload`) with a `created_at` timestamp. A separate codec module in `research/price_result_codec.py` encodes and decodes the result: pure, no Django, no I/O, Decimal preserved as strings, enums explicit, nested contracts reconstructed through normal constructors. 4B reads and presents the snapshot at `/research/<uuid>` as a read-only report. It does not execute research. Request-provenance mismatch or corrupt payload fails closed with no price numbers rendered. | `PriceAggregationResult` is the durable price intelligence answer for one run. The report URL `/research/<uuid>` must survive across requests and deployments, so the result it renders must be persisted. The `ResearchRun` UUID already identifies the result uniquely — a second identifier would add a consistency obligation for no capability. Naming it `PriceIntelligenceSnapshot` rather than `ResearchResult` is deliberate: it preserves the price pipeline evidence (listing observations through identity assessments through aggregation) but is not the complete execution evidence store (it cannot represent search candidates never fetched, page-fetch failures, or pages producing zero observations — that is 4C's question). Versioned opaque JSON with a decoder that fails closed on unknown versions means the report stays interpretable and never renders partially-corrupt data as verified. The codec lives in `research/` as a pure module because it transforms research-layer contracts to and from JSON — it is serialization discipline, not persistence logic, and must not touch Django. | Accepted (4B architecture checkpoint) · IMPLEMENTED (4B) |
| AD-051 | Research orchestration is a separate application layer (`execution/`) and phase (4C), rather than living in `research/` or `web/`. `execution/` coordinates one `ResearchRun` through provider I/O and deterministic research primitives. Deterministic research and evidence decisions — identity resolution, listing acceptance/rejection, price eligibility, aggregation semantics — remain owned by `research/`. `execution/` invokes those decision primitives but must not reimplement or override them. `execution/` may import `domain`, `research`, `providers`, and `runs`, but must not import `web/`. `research/` remains pure and must not import `execution`, `providers`, `runs`, or Django. `web/` may invoke execution but must not carry research semantics. | The previous PLAN stated that `research/` owns orchestration. But `research/` is intentionally pure — its guard tests enforce stdlib-only imports and forbid persistence, provider, network, and Django dependencies. Real orchestration must coordinate all of those. Putting orchestration in `web/` would make research semantics a property of the transport layer, violating caller-independence (AD-001): the core would then be structured around how the browser submits a request rather than around the canonical `ResearchRequest`. The execution layer sits between them: it imports what it needs to run a pipeline, but stays independent of which client triggered the run. This preserves both boundaries — `research/` stays testable without a database or network, and `web/` stays a presentation and intake layer. Coordination is not authority: `execution/` orchestrates the pipeline steps but does not make evidence decisions — listing acceptance, price eligibility, and identity resolution remain `research/` primitives that `execution/` calls, not reimplements. *Note: `execution/` was created in 4C-B alongside the backend orchestration implementation.* | Accepted (4B architecture checkpoint) |
| AD-052 | `PriceIntelligenceSnapshot` is not the complete research-execution evidence store. It preserves evidence reachable through `ListingObservation` → `NormalizedListingObservation` → `ListingIdentityAssessment` → `PriceAggregationResult`. It cannot represent search candidates never fetched, page-fetch failures, blocked pages, or fetched pages producing zero observations. 4C must decide how those execution attempts and outcomes are preserved before claiming end-to-end evidence completeness. | The snapshot is a price result, not an execution log. A search that returns 10 candidates, of which 3 were fetched, 2 were blocked, and 1 produced zero observations — the snapshot can only represent the three that yielded observations and their downstream assessments. The other seven execution events are silently lost. That is acceptable for 4B's read-only report: it renders what the aggregation produced, and says honestly when nothing exists. But 4C, which owns the full orchestration pipeline, must decide whether to preserve execution evidence beyond what the aggregation carries. That decision depends on whether a partial run's diagnostic value justifies additional persistence surface — a question 4C can answer with real failure data rather than speculation. | Accepted (4B architecture checkpoint) |
| AD-053 | Human review for AI-assisted semantic matches uses a separate authority overlay. The deterministic `ListingIdentityAssessment` snapshot is never mutated. `AI_ASSISTED_MATCH` is a disposition on `AiAssistedMatchResult`, not a decision on the snapshot assessment. Human confirmation creates a run-scoped `AiAssistedReviewCandidate` with states UNREVIEWED/CONFIRMED/REJECTED. Machine Price (4A aggregation) remains deterministic-only. Reviewed Price is a distinct aggregation contract that includes deterministic ACCEPTED + human-CONFIRMED listings, with per-listing origin (`DETERMINISTIC`/`HUMAN_CONFIRMED`). Human confirmation changes identity authority only — price eligibility still follows deterministic non-identity rules (numeric Decimal, comparable currency, known condition). Candidate binding fails closed. No reviewer identity or authentication was introduced. | Semantic matching (FU3B) produces `AI_ASSISTED_MATCH` dispositions that are intentionally excluded from 4A aggregation. These matches have valid evidence but the system has no way to verify semantic correctness automatically. Human review lets a person confirm or reject these candidates on the report page. The authority model preserves the invariant that deterministic identity is the only automatic authority: the snapshot assessment stays REJECTED for human-confirmed listings. A separate aggregation contract (`aggregate_reviewed_listing_prices`) reads human confirmation state and produces `ReviewedPriceAggregationResult` with origin tracking. This avoids polluting the frozen 4A contract while providing a usable reviewed price view. The candidate model (`AiAssistedReviewCandidate`) is run-scoped with immutable semantic provenance fields, and the review service uses conditional database updates for concurrency safety. Web performs binding validation before any mutation. | Accepted (HUMAN-REVIEW) |
| AD-054 | 6A/6B/6C responsibility split: 6A is a pure specification framework; 6B supplies the first category-specific schema; 6C acquires, extracts, and normalizes real specification evidence and invokes 6A resolution. | Evidence/authority contracts must precede extraction. Full 6A semantic contract: §22.0. §22.0 also defines the identity/specification provenance-binding chain: every observation binds to an established ProductIdentity and SpecificationDefinition, every resolution is self-auditing over a single identity/spec pair, and ProductSpecificationSet completeness invariants make cross-product evidence mechanically rejectable. 6A defines SpecificationDefinition, SpecificationValue, SpecificationObservation, NormalizedSpecificationObservation, SpecificationResolution, CategorySchema, and ProductSpecificationSet as a deterministic, caller-independent, Django-free, persistence-free, network-free framework. 6A performs no extraction, no LLM call, and no reuse of the frozen FU3A/FU3B semantic runtime. Source authority (AUTHORITATIVE/SECONDARY) is distinguished from extraction authority: an authoritative source does not make an LLM interpretation authoritative. 6B supplies the first category-specific specification schema (Enterprise SSD preferred). 6C acquires specification evidence from approved sources, extracts raw specification observations, preserves source provenance, normalizes using the 6B category schema, and feeds normalized evidence into the 6A deterministic resolver to produce ProductSpecificationSet results. Resolution states: UNKNOWN (zero usable canonical values), VERIFIED (one canonical value with AUTHORITATIVE support), UNVERIFIED (one canonical value with SECONDARY-only support), CONFLICT (more than one canonical value). No majority voting — evidence multiplicity does not vote truth into existence. 7A-7C depend on 6A/6B/6C (framework + category schema + real specification evidence), not merely on schema definitions. | Accepted (architecture documentation) |
| AD-055 | Enterprise SSD finalized as first 6B category; 12-field schema v1; strict abstaining deterministic normalization; no extraction, no resolution, no authority inference; 6C remains evidence acquisition/extraction boundary. | 6A framework provides the generic contracts; 6B instantiates the first real category using them. The 12-field v1 schema is narrow enough that each field has a clear deterministic normalization meaning, yet broad enough to support later comparable-product research across enterprise SSD products. Normalization is representation-only: it changes how a raw value is represented, not whether it is true or authoritative. Composite/ambiguous values abstain with explicit issue codes rather than guessing. 6C is responsible for turning real source material into specification observations that this schema can normalize. | Accepted (6B implementation) |
| AD-056 | 6C uses explicit approved sources and existing PageFetcher; deterministic structured extraction via supportSpecsData embedded JSON (var supportSpecsData = JSON.parse('...')); source authority remains explicit (never hostname-inferred); normalization uses frozen 6B (with evidence-backed corrective addition: "2.5in" -> "2.5-inch"); resolution uses frozen 6A; fetch/no-evidence outcomes remain auditable; no LLM implemented; Samsung PM9A3 page accessible but NO_OBSERVATIONS (spec table JS-rendered); exact MPN record selection; only "Form Factor" label mapping currently evidenced; provenance/source-outcome audits (multiplicity-aware); final_url validation; raw value exact preservation. | 6C owns the complete evidence acquisition pipeline: explicit approved-source descriptors (source_url validated through require_fetchable_url at construction), existing PageFetcher acquisition (PageFetcher protocol imported from providers.page, not HttpPageFetcher concrete), deterministic structured extraction (var supportSpecsData = JSON.parse('...') demonstrated by Seagate Nytro 5050), exact MPN record selection (skuNumber match), raw provenance preservation (exact source value), frozen 6B normalization (with evidence-backed "2.5in" correction), frozen 6A resolution, complete ProductSpecificationSet with explicit UNKNOWN, and auditable source outcomes (EXTRACTED/NO_OBSERVATIONS/FETCH_FAILED/SOURCE_REFUSED) with self-consistency validation and final_url validation. Source outcomes preserve complete source descriptor including authority. Result audit enforces sum(EXTRACTED observation_count) == len(normalized_observations). Provenance trace is multiplicity-aware: each EXTRACTED outcome contributes capacity equal to observation_count. No source discovery or search. No LLM extractor — deterministic-first. Research extraction module is pure (receives text, produces observations). No persistence/web. The Samsung PM9A3 manufacturer page is accessible via static HTTP but produces NO_OBSERVATIONS (spec table rendered by Next.js React components). No real manufacturer fixture has demonstrated JSON-LD, HTML tables, or definition lists as extraction mechanisms. Only the supportSpecsData embedded JSON structure is accepted. | Accepted (6C implementation) |
| AD-057 | 7A candidate discovery is evidence-first and distinct from similarity: explicit AUTHORITATIVE manufacturer catalog sources produce raw candidate observations; frozen 2A excludes the target and groups only exact/normalized-exact candidate identities; no SearchProvider, LLM, spec filtering, scoring, ranking, or persistence is introduced. | Candidate != comparable. 7A discovers product identities from approved catalog sources; 7B scores similarity. ProductIdentity is NOT reused for discovered candidates (it represents the requested product, not catalog rows). supportSpecsData is the first mechanism. Target-self exclusion uses frozen 2A compare_part_numbers(). Deduplication uses frozen 2A normalize_part_number() semantics. No spec-based pre-filtering (that is 7B). No score/rank fields on candidates. Result is self-auditing. | Accepted (7A implementation) |
| AD-058 | 7B deterministic similarity scoring: VERIFIED-only field comparison, 12-field equal weight, Decimal min/max ratio for numeric fields, candidate ProductIdentity bridge (EXACT, no manufacturer guessed), evidence_coverage and evidence_weighted_similarity, one-fetch-per-source execution reusing frozen 6C extraction per candidate identity, self-validating contracts, field score self-validation, exact scalar types, execution-owned EnterpriseSsdSimilarityResult with 7A source binding, retained source outcomes and provenance audit. | 7B computes auditable similarity evidence between target and candidate specifications. Similarity != compatibility certification. VERIFIED-only scoring: UNKNOWN/UNVERIFIED/CONFLICT states are not mismatches. 12 fields have equal weight (no domain-business weights). DECIMAL fields use min/max ratio (positive values), TEXT/ENUM/BOOLEAN use exact canonical equality. Field score self-validation: SpecificationSimilarityFieldAssessment recomputes actual score from raw resolutions, rejecting wrong-but-in-range supplied values. Exact scalar types: scored_field_count must be int (not bool/float), evidence_coverage/observed_similarity/evidence_weighted_similarity must be Decimal (not int/float/bool). evidence_coverage = scored/12, evidence_weighted_similarity = sum/12. Candidate ProductIdentity bridge uses EXACT match type, rejects non-AUTHORITATIVE evidence, and ComparableCandidateSpecificationProfile enforces exact bridge output identity (no enriched metadata). Execution fetches each unique source ONCE, calls frozen 6C extraction per candidate identity. EnterpriseSsdSimilarityResult is execution-owned: exact ComparableCandidateDiscoveryResult type (no duck typing, TypeError BEFORE fetch), 7A source binding (canonical EXTRACTED source descriptors derived from frozen 7A result, exact object identity enforced — copied/value-equal substitutes rejected, count and order audited), retained source outcomes, final_url structurally validated, candidate spec evidence traced to FETCHED 7B outcomes (provenance audit). Real Seagate fixture: 80 candidates, each with 1 scoreable field (Form Factor), coverage = 1/12. Evidence too sparse for useful differentiation. | Accepted (7B implementation) |
| AD-059 | 6D Authoritative Datasheet Specification Enrichment: manufacturer PDF datasheet acquisition through provider-neutral DocumentFetcher boundary; concrete HttpPdfFetcher (stdlib urllib); pure research table interpretation (MPN -> table -> column -> row binding, unit incorporation); frozen 6B normalization + frozen 6A resolution; 7A-grounded authority chain (derive_datasheet_source_from_discovery); public API requires frozen ComparableCandidateDiscoveryResult + exact EXTRACTED outcome (identity-verified member) — arbitrary DatasheetSource objects rejected; batch shared PDF fetch; bounded parser exception taxonomy (pdfminer only, RuntimeError propagates); fully self-auditing SpecificationEnrichmentResult (raw->outcome->normalized->resolution provenance); 6C+6D evidence composition (normalize + re-resolve); abstention paths return valid empty result (zero source_outcomes, all UNKNOWN). | 6D extends specification evidence capability beyond frozen 6C extraction. Added after 7B freeze because frozen 7B revealed only 1/12 candidate evidence coverage. Provider-neutral document boundary. Concrete PDF fetcher (stdlib urllib, no browser). Pure research layer table interpretation (no PDF parser in research/). Six-field allowlist: capacity, sequential_read, sequential_write, random_read_iops, random_write_iops, endurance_dwpd. Support-record datasheet-link extraction from var supportSpecsData JSON. AUTHORITATIVE-only enforcement. Bounded model-row grammar (3 exact forms). Whole-PDF MPN uniqueness. Raw MPN exactness. Bounded parser exception handling (pdfminer/pdfplumber only, programming errors propagate). Self-auditing result. 6C+6D evidence composition. Real Seagate fixture: Nytro 5550/5350 datasheet PDF (8 pages, 15 tables). XP15360SE70005: 6 VERIFIED observations. Candidate composition: scored_field_count=7, evidence_coverage=7/12. | Accepted (6D implementation) |
| AD-060 | PROD-FIX1 production corrections (canonical spec §26.10): (1) the Internal Vendor adapter supports BOTH the canonical JSON wrapper and the production section-oriented response, parsed by a strict bounded recursive-descent literal parser (no eval/literal_eval, three exact section labels only, exact `{Not Found}` bounded marker, Decimal-exact numbers); the allowlist mappers remain the sole sensitive-data boundary. (2) Compact Quote price formatting renders no-symbol currencies once (`ZAR 30,999.0`), never code-as-prefix plus code-suffix. (3) AI-assisted semantic matches render immediately after Compact quote summary (presentation order only). (4) A valid run-scoped human-CONFIRMED semantic candidate contributes ONE Compact Quote row for the SAME run via a projection-layer extension: identity authority only; price/currency/condition exactly the persisted normalized values (UNKNOWN condition stays Unknown); explicit "Human Confirmed" provenance; persisted FX evidence only; the frozen PriceIntelligenceSnapshot and Machine Price are never mutated; UNREVIEWED/REJECTED/invalid-binding/cross-run candidates never enter; Undo removes the row on the next GET; historical GET stays zero-live-I/O. (5) The new-research form carries a front-end-only duplicate-click guard (disable + `Researching…`) — explicitly NOT a backend dedupe guarantee. (6) NO insecure TLS bypass, unverified context, or HTTP fallback was added for the ECB trust-chain failure, and regression tests mechanically guard against future bypasses. **Amended by AD-061 (FU1):** items (1) and (4) had production-fidelity / authority-ownership defects corrected by the bounded follow-up; item (6) no longer records an operational CA-store repair as an outstanding action (see AD-061). | Defects were discovered in real production use of the deployed PILOT-RELEASE-2 runtime. Each correction is the minimal bounded change to the identified defect: the Vendor parser adds a second supported upstream contract without weakening the allowlist privacy boundary; the currency fix changes display formatting only; the section move is template ordering only; the confirm->quote path reuses the existing fail-closed binding validation and adds a display projection (the frozen 4A/Reviewed Price authority contracts are untouched); the submit guard is client UX only; the TLS item preserves secure verification. No 8A caching, no new providers, no new models, no migrations. | SUPERSEDED IN PART BY AD-061 (PILOT-RELEASE-2-PROD-FIX1-FU1) |
| AD-061 | PROD-FIX1-FU1 production review-blocker closure (canonical spec §26.11): (1) VENDOR WIRE FIDELITY — the adapter now supports the ACTUAL hybrid production Ingram placement (explicit `vendorPartNumber` + nested `pricing` customerPrice/retailPrice/currencyCode + TOP-LEVEL boolean availability + TOP-LEVEL `Avl_Quantity`) through the same bounded availability truth table (contradiction => UNKNOWN fail-closed; false+0 => OUT_OF_STOCK/0; true+positive => IN_STOCK), with the canonical nested form and flat compatibility form retained and separately tested (the flat form is NOT described as the only/exact production wire shape); the integration path proves the faithful hybrid Ingram + REAL nested Synnex EU (`OnlineCheck.Header.CurrencyCode`, `OnlineCheck.Item.ManufacturerItemIdentifier/UnitPriceAmount/AvailabilityTotal`) with fake/redacted SessionId/BuyerAccountId/SystemId at their realistic structural locations, stripped by the allowlist; section-scanner documentation and behavior are reconciled — only the three exact line-anchored labels establish sections, a COMPLETE bounded literal is authoritative, and unknown/interstitial text after it is never parsed into data nor allowed to poison the section, while malformed content INSIDE a literal still fails that source closed (no generic HTML scraping). (2) HUMAN-CONFIRMED AUTHORITY OWNERSHIP — the single pure candidate-to-assessment binding primitive (`research.matching.is_review_candidate_binding_valid`) is shared by the web GET/POST paths and both historical replay boundaries (no divergent rule copies; the 8-step POST validation is unchanged in strength); both replay entry points DERIVE the effective human-confirmed selection from persisted state (`derive_human_confirmed_assessment_indices`: CONFIRMED + this run + in-range index + full binding + human-review eligibility + persisted price/currency) and no longer accept ANY caller-supplied index — a bare integer can never mint HUMAN_CONFIRMED authority; the lowest-level pure projection helper is retained as an already-authorized-selection consumer with that contract stated; Machine Price untouched; human review run-scoped; historical GET zero-live-I/O. (3) ECB EVIDENCE CORRECTION — a later SECURE retry from the same production Python runtime (no certifi install, no manual certificate, no fx.py change, no TLS-verification bypass; observation date 2026-09-24, USD 1.1367, ZAR 18.6836) succeeded, so the documentation no longer states an unproven root cause or an outstanding CA-trust-store installation action as fact; the transient failure, its correct FxNetworkError classification, the run completing without ResearchFxSnapshot, and the retained failure-path regression tests are preserved as recorded evidence; NO TLS workaround was added or is required. (4) REVIEWED PRICE WORDING — the Reviewed Price summary now derives the truthful price-contributing counts from the reviewed buckets themselves (per-bucket `human_confirmed_count` / `deterministic_count` sums) instead of overstating them with the validated-CONFIRMED-candidate count; reviewed-price eligibility is NOT changed to make the count match. | Bounded append-only corrective follow-up to the independently reviewed PROD-FIX1 commit (8811104): correct ONLY the review blockers and any directly necessary tests/docs; retain the previous implementation. | IMPLEMENTED / PENDING FINAL REVIEW (PILOT-RELEASE-2-PROD-FIX1-FU1) |
| AD-062 | PROD-FIX1-FU2 final review-blocker closure (canonical spec §26.12): the PUBLIC (denied-branch) historical compact quote replay now OWNS its price/currency/condition evidence authority exactly like the authorized replay. `replay_public_compact_quote_projection` no longer accepts ANY caller-supplied `PriceAggregationResult` (the `price_result` parameter is removed; the only parameter is `run`). It verifies the run is a real ResearchRun, loads `PriceIntelligenceSnapshot.objects.get(run=run)`, decodes it through the canonical price-result codec, verifies `decoded.request == run.to_research_request()`, and uses THAT decoded persisted result for the frozen public bucket projection, the shared human-confirmed binding derivation, and the human-confirmed price/currency/condition evidence. A same-request cross-run result — identical source URL / product title / MPN field / SKU / evidence source, different persisted price — can no longer substitute for the persisted snapshot, so a CONFIRMED candidate's identity authority can never be exercised over another run's price evidence (historical report immutability; run-scoped evidence authority; confirmation establishes identity authority only over the persisted evidence belonging to that same run). Fail-closed: missing snapshot (DoesNotExist, the existing persisted-artifact behavior), malformed payload / unsupported schema version (PriceResultCodecError), request-provenance-corrupt snapshot (CompactQuoteProjectionError). The denied branch remains vendor-free: NO ResearchSupplementSnapshot read, NO commercial supplement codec import, NO Vendor/Search/Page/ECB- live/Semantic/network work; persisted ResearchFxSnapshot remains allowed; zero live I/O. The authorized replay (`replay_compact_quote_projection`), Machine Price, and Human Review state semantics are UNCHANGED. | Final independent review of FU1 blocked on the public replay trusting caller-supplied price evidence: request equality alone does not prove the evidence is THIS run's persisted snapshot, and the shared binding primitive legitimately matches across same-request runs with identical identity fields. The correction is the minimal bounded change: the denied replay loads its own authority source, removing the caller-owned input rather than comparing against it. | IMPLEMENTED / PENDING FINAL REVIEW (PILOT-RELEASE-2-PROD-FIX1-FU2) |
| AD-063 | B1 production semantic PRIMARY route promotion (canonical spec §26.17): the code-pinned production semantic route moves from `amax/nemotron-3-super` to `amax/qwen3.8-27b` as PRIMARY; the FALLBACK stays byte-for-byte `vllm-262k/Qwen3.6-27B-262K`. The only production change is `PRIMARY_MODEL` in `product_intelligence/semantic/runtime.py` (plus its pinned-route docstring block). Everything else is frozen: fallback on execution failure only (explicit allowlist; a valid primary decision is FINAL; semantic disagreement never triggers fallback); temperature 0.0 exact float / max_tokens 32768 / request-timeout behavior; prompt v1.1, parser, response schema, enums, validation, reason codes; deterministic identity matching, semantic eligibility, `_map_semantic_decision`, AI_ASSISTED_MATCH (MATCH only) authority and its 4A exclusion, HARD_CONFLICT, Working Quote, Reviewed Price, human confirmation, commercial/vendor authority, execution evidence; the frozen A1 promotion-regression facility and its evaluation-only model catalog; the qualification corpus. Nemotron remains a qualified/reference model but is NOT the production fallback (Nemotron and Qwen 3.8 share provider `amax`; the fallback exists for provider-level execution redundancy). | Reviewer decision based on frozen, independently reviewed evidence: the 64-case FULL qualification of `amax/qwen3.8-27b` (100% valid, 96.88% accuracy, 100% MATCH precision, 85.71% MATCH recall, 0 false MATCH, safety cost 2, all hard gates PASS — matching the historical qualified Nemotron headline metrics and wrong-case IDs), the A1 production-shaped live promotion regression (22 processed / 16 semantic-called cases, both models passing all six objective promotion gates), and human review closing the two surfaced disagreements (SPR-0009: no authority expansion; SPR-0020: candidate SKU provides exact target identity, supporting the AI_ASSISTED_MATCH authority). No caller-configurable routing, no model override surface, no third provider. | IMPLEMENTED / PENDING FINAL REVIEW (SEMANTIC-QWEN38-PRODUCTION-PROMOTION-B1) |
| AD-064 | 8A-FX-A1 canonical ECB observation cache (canonical spec §26.18; design lineage 8A-PRE audit + 8A-FX-DESIGN + 8A-FX-DESIGN-FU1, all reviewed): the first safe caching slice — cross-run reuse of the canonical production ECB daily FX observation set. (1) ELIGIBILITY: cache active ONLY on the canonical default path, declared at the canonical-default construction site (`fx_cache_eligible = fx_provider is None`, before `EcbFxProvider()` construction); ANY explicitly injected provider (fake, EcbFxProvider instance, subclass, wrapper, any FxProvider-compatible object) unconditionally bypasses the cache (zero store reads/writes) and executes the existing live acquisition contract byte-for-byte; no isinstance/issubclass/provider-class-identity eligibility logic exists (mechanically guarded). (2) USD-ONLY: currency discovery precedes any cache work; USD-only runs perform zero provider calls AND zero cache/store work. (3) FEED IDENTITY: one stable canonical identifier `FX_FEED_ID_ECB_DAILY = "ecb:eurofxref-daily"` in providers/fx.py, bound to the eurofxref-daily.xml endpoint + provider_id "ECB" + base_currency "EUR" (mirror-locked); not a class name; not user-configurable. (4) STORE: new `runs.FxObservationStore` (migration 0011) — cross-run ACQUISITION CONTENT (not run evidence; no ResearchRun relation; no cascade; not ResearchFxSnapshot/PriceIntelligenceSnapshot/ExecutionEvidenceRecord/ResearchSupplementSnapshot/Django CACHES): feed_id, provider_id, base_currency, observation_date, content_sha256, full-document payload through the reused fail-closed FX codec V1, original_retrieved_at (IMMUTABLE provider instant), last_proven_at (timezone-aware proof instant, never truncated to a date), created_at; UniqueConstraint (feed_id, observation_date, content_sha256); latest-selection index. (5) CONTENT IDENTITY: pure research contract `research/fx_cache_contract.py` (stdlib only, no Django/provider/I/O): canonical SHA-256 over byte-stable JSON of the FULL PARSED rate observation (provider + base + observation_date + rates sorted by code, exact str(Decimal) text; raw XML never hashed/persisted; no dict-order/locale/float dependence); same observation_date + changed rates (correction) => distinct digest => distinct row (superseded revision retained as VALID_HISTORICAL, never overwritten). (6) PROJECTION: `project_required_rates` — full set -> required currencies, document order preserved, mirrors the provider's own filter (mirror-locked) so LIVE and CACHE_HIT run payloads are byte-identical for the same document; required_currencies is a projection input, never cache identity. (7) FRESHNESS: pure predicate `no_publication_possible_between(T, N, zone)` over ACTUAL aware instants (naive => TypeError; T > N => ValueError; zone = Europe/Brussels via zoneinfo; DST-aware; system-local timezone never consulted): reuse possible only while EVERY Europe/Brussels calendar day overlapping the CLOSED interval [T, N] is Saturday/Sunday (weekend stretch [Sat 00:00, Mon 00:00 CET/CEST)); working days: NO reuse ever (a working-day proof covers no N >= T); TARGET closing days treated conservatively as working days (no calendar data, no invented holidays); no numeric TTL; explicit conservative policy, NOT a claim of physical ECB incapability. (8) LIVE PATH: one full-set fetch (requested_currencies=None) -> feed-binding validation (contract defect propagates) -> digest -> persist/reconcile in the store's OWN transaction (before the run's atomic final publication) -> last_proven_at set only on successful live observation -> project -> existing per-run FX codec V1 -> run's ResearchFxSnapshot acquisition="LIVE"; original provider retrieved_at preserved. (9) CACHE_HIT PATH: latest stored observation -> fail-closed decode + integrity validation (digest binding, feed invariants, cross-field consistency, impossible stored timestamps) -> freshness predicate on the row's ACTUAL last_proven_at -> if reusable: ZERO ECB calls, original retrieved_at preserved, projection from the full cached set, run's own snapshot acquisition="CACHE_HIT"; never masquerades as LIVE. (10) FAILURES: malformed/unsupported/corrupt EXISTING cache payload is NOT a cache miss — it PROPAGATES (fail closed; never caught into a silent live fallback; row never deleted); only "no row" is an ordinary miss; live FxProviderError remains NONFATAL (no snapshot, store untouched); uniqueness race reconciled ONLY for the specifically understood race (competing row for the exact content identity; exact semantic/content identity validated; convergent conditional last_proven_at re-proof; otherwise fail closed); unrelated IntegrityError/other storage errors propagate; cache persistence failure after live success propagates; no distributed locking, no select_for_update. (11) PROVENANCE: additive `ResearchFxSnapshot.acquisition` (LIVE/CACHE_HIT, default LIVE; migration preserves all existing rows as LIVE); REPLAY is a read behavior (compact_quote_replay reads the run's own snapshot with zero live provider calls and zero cache acquisition), never a stored value, never mutates the persisted value. (12) PUBLICATION ATOMICITY: the per-run ResearchFxSnapshot remains part of the run's atomic final publication; the store row has different ownership/lifetime (a successfully persisted store row survives a later failed run publication and must not imply the run completed; it carries no run authority). (13) PRESENTATION: one additive bounded report line (ECB reference date + original provider retrieval instant + LIVE/CACHE_HIT label) on both replay branches; no DB IDs, raw cache keys, exception text, provider raw body, or implementation details exposed; GET remains zero-live and never reads the store. (14) AUTHORITY INVARIANTS UNCHANGED (re-proven): frozen 4A public market authority (Machine Price snapshot bytes identical across LIVE/CACHE_HIT/FX-absent), Machine Price, Reviewed Price, deterministic/semantic identity, AI_ASSISTED_MATCH authority, vendor supplemental authority, human-confirmed authority, HARD_CONFLICT, semantic production route (PRIMARY amax/qwen3.8-27b; FALLBACK vllm-262k/Qwen3.6-27B-262K; Nemotron qualified/reference only), fallback semantics, review semantics; FX remains DISPLAY-SUPPLEMENTAL only (USD equivalent identical LIVE vs CACHE_HIT for the same document). Explicitly NOT cached: public pages, search/Serper, vendor observations, semantic responses, identity decisions, Machine/Reviewed Price, human-review state, comparable research, rendered reports, negative/failure results. No `force_fresh` primitive ships in A1 (a later 8A decision); no retention/cleanup policy (store naturally bounded at ~1 row per working day + corrections). | The 8A-PRE audit established the ECB FX observation layer as the safest first cache candidate (display-supplemental authority, content identity = observation date, non-sensitive, single call site, full provenance already persisted); the 8A-FX-DESIGN + FU1 lineage resolved the exact miss/hit boundary (pre-fetch feed-identity lookup vs post-fetch content identity), the unsound same-UTC-day proof window (replaced by the proof-instant + Europe/Brussels weekend-closure predicate), and the isinstance feed gate (replaced by canonical-default eligibility declaration). A1 implements that frozen design as the bounded first slice: acquisition-only substitution with fail-closed cache integrity, conservative weekend-only reuse, and zero authority change. | IMPLEMENTED / PENDING FINAL REVIEW (PRODUCT-INTEL.8A-FX-A1) |
| AD-065 | SEMANTIC-AUTHORITY-V2-S2-A contract freeze (canonical spec §26.21): the approved Semantic Authority V2 design is frozen IN CODE as a pure contract, with NOTHING wired into production. (1) MODULE: new `research/semantic_authority_v2.py` (stdlib + frozen research/domain imports only; no Django, no I/O, no network, no LLM, no mutable global state; exported through `research/__init__.py`; no other research module, execution, semantic, runs, web, or providers module references it — mechanically guarded). (2) STATES: the V2 deterministic overlay over the frozen `ListingIdentityAssessment` — DETERMINISTIC_VERIFIED (V_EXACT, V_NORMALIZED_EXACT), DETERMINISTIC_UNCERTAIN (U1_TITLE_MPN, U2_SKU_ONLY, U3_PARTIAL_BOUNDARY, U4_NO_MPN, U5_NEAR_MISS_MPN), DETERMINISTIC_CONFLICT (C1_INCOMPATIBLE_EXPLICIT_MPN), DETERMINISTIC_UNEVALUABLE (E1_NO_TARGET_MPN, E2_NO_CANDIDATE_EVIDENCE — the E2 addition is permitted by the "at minimum" contract) — derived by the pure `derive_identity_state_v2`; out-of-contract assessment combinations fail closed. (3) NEAR-MISS: bounded signals EXACT / NORMALIZED_EXACT / TITLE_MPN_TOKEN / SKU_EQUALS_TARGET / SKU_NOT_TARGET / PARTIAL_BOUNDARY / NEAR_MISS_TRUNCATION / NEAR_MISS_SUBSTITUTION / COMPATIBILITY_WORDING (4-token overlay vocabulary, title-only, word-boundary) / EMPTY_MPN_FIELD / NO_RELATION. NM-1 = strict prefix/truncation on the EXISTING frozen normalized MPN keys (either direction); NM-2 = same-length exactly-one-character substitution; Levenshtein, arbitrary substring matching, containment authority, suffix stripping, manufacturer-specific acceptance, and normalization changes are explicitly OUT. Membership is never identity authority; outside NM-1/NM-2, explicit MPN_MISMATCH stays deterministic conflict. (4) AMENDMENT 1 — NM-2 CEILING: NM-2 without reviewed authoritative relationship context (a provenance carrying ESTABLISH_IDENTIFIER_RELATIONSHIP) caps the maximum future AUTOMATIC tier at NEEDS_REVIEW, frozen as explicit matrix data (NEAR_MISS_SUBSTITUTION_WITHOUT_RELATION_AUTHORITY + the ceiling rule), never a prompt convention; generic safety rule, not a manufacturer special case; AI may still return MATCH/HIGH and a human may confirm later — it cannot auto-price. (5) AMENDMENT 2 — CONTEXT PROVENANCE: three DISTINCT bounded classes with disjoint capability sets — MANUFACTURER_PRODUCT_CONTEXT (GROUND_PRODUCT_FACTS only; does NOT establish the identifier relationship), MANUFACTURER_RELATION_AUTHORITY (GROUND_PRODUCT_FACTS + ESTABLISH_IDENTIFIER_RELATIONSHIP; the class that may raise relationship authority / STRONG), CUSTOMER_RETRIEVAL_RELATION (RETRIEVAL_RECALL_ONLY; never identity, never Machine Verified, never NM-2 auto-comparable, never STRONG, never overrides conflict, never enters 4A, never described as manufacturer equivalence). Context quality STRONG/LIMITED/WEAK is computed only from provenance classes — never from model confidence or AI matched_attributes (RELATION -> STRONG; else PRODUCT -> LIMITED; else WEAK). (6) CONFLICT TAXONOMY: 14-value ConflictClass with exact frozen severity sets — ALWAYS_HARD (MPN_IDENTITY, PRODUCT_FAMILY, GENERATION, CAPACITY, INTERFACE, FORM_FACTOR, PRODUCT_ROLE, ACCESSORY_RELATION, PACKAGING_QUANTITY, BUNDLE), REVIEWABLE (REVISION_OR_SUFFIX, BRAND, OTHER_MATERIAL_CONFLICT — BRAND is reviewable, not hard), PRICE_DIMENSION_ONLY (CONDITION — a price dimension, never identity); disjoint, exhaustive, import-self-checked; tray-vs-retail wording alone is not hard, single-vs-multipack is hard, drive-tray accessory is hard. (7) AUTHORITY MATRIX AS DATA: bounded tiers MACHINE_VERIFIED / AI_ASSISTED_COMPARABLE / NEEDS_REVIEW / HUMAN_CONFIRMED / HUMAN_REJECTED / HARD_CONFLICT / EXCLUDED_LOW_CONFIDENCE / SEMANTIC_UNAVAILABLE; DETERMINISTIC_STATE_POLICIES (VERIFIED -> MACHINE_VERIFIED no AI; CONFLICT -> HARD_CONFLICT AI-ineligible human-cannot-confirm; UNEVALUABLE -> EXCLUDED_LOW_CONFIDENCE no AI authority; UNCERTAIN -> NEEDS_REVIEW, the only semantic entry point); SEMANTIC_OUTCOME_TIER_MATRIX with all 27 (decision x confidence x context quality) combinations defined — MATCH+HIGH requires STRONG for AI_ASSISTED_COMPARABLE, MATCH+MEDIUM and MATCH+HIGH+incomplete-context and MATCH+HIGH+reviewable-conflict -> NEEDS_REVIEW, MATCH+LOW / NO_MATCH / UNCERTAIN+non-actionable / UNCERTAIN+LOW -> EXCLUDED_LOW_CONFIDENCE, UNCERTAIN+actionable -> NEEDS_REVIEW; restrict-only ceilings; ALWAYS_HARD supersession; runtime failure -> SEMANTIC_UNAVAILABLE and is NEVER interpreted as NO_MATCH; precedence HARD_CONFLICT > HUMAN_CONFIRMED > AI authority; ineligible states ignore supplied semantic/human inputs (fail closed). (8) U4 RECALL: no-MPN usable-title (and empty-MPN usable-title) listings are DETERMINISTIC_UNCERTAIN / U4_NO_MPN and future semantic entry points — an intentional recall feature, NOT re-conservatized; eligibility is not authority (weak outcomes stay excluded through the frozen gates); the CURRENT V1 runtime gate is unchanged and does not call the AI on U4. (9) UI VOCABULARY (no UI built): frozen badges (Machine Verified; AI-Assisted Comparable — not machine verified; Needs Review — not verified; Human Confirmed; Human Rejected; Hard Conflict — excluded; Low Confidence; AI Evidence Unavailable); attention order NEEDS_REVIEW, AI_ASSISTED_COMPARABLE, HUMAN_CONFIRMED, MACHINE_VERIFIED, HUMAN_REJECTED, HARD_CONFLICT, EXCLUDED_LOW_CONFIDENCE, SEMANTIC_UNAVAILABLE (attention, not authority). (10) AMENDMENT 3 — SUMMARY WORDING: "Comparable evidence: N listings" is forbidden when the count contains NEEDS_REVIEW (frozen FORBIDDEN_MARKET_EVIDENCE_HEADLINE); the future headline is "Market evidence found: N listings" (NEEDS_REVIEW MAY count) with a separate "Pricing-eligible comparable listings: N" line (NEEDS_REVIEW MUST NOT count; no price statistic may include Needs Review before confirmation); the legacy "N comparable NEW listings (machine-verified)" line may remain; counting is a pure function over frozen tier sets (import-self-checked). (11) FROZEN V1 PROOF: the 2A comparator, 3C assessment/decisions/rejection reasons, PriceIntelligenceSnapshot V1, 4A aggregation, Reviewed Price, prompt v1.1, parser, production route (amax/qwen3.8-27b PRIMARY, vllm-262k/Qwen3.6-27B-262K FALLBACK, temperature 0.0, max_tokens 32768), FU3B eligibility, human-review eligibility, replay, and vendor authority are all unchanged (byte-level no-wiring scans + behavior pins + the preserved frozen regression suite). **Amended by AD-066 (S2-A-FU1):** item (5)'s global context-quality rule (RELATION -> STRONG; else PRODUCT -> LIMITED; else WEAK) and item (7)'s context-quality matrix key were the identified U4 re-conservatization defect — replaced by two orthogonal authority prerequisites (bounded product evidence quality + state-specific identifier relationship authority, with U4 NOT_APPLICABLE so MANUFACTURER_RELATION_AUTHORITY is never required for U4); ContextQuality / derive_context_quality are removed. All frozen contract tables are now runtime-immutable tuples of immutable entries with pure lookup functions (Blocker 2). See AD-066 and §26.22. | The Product Lead approved the V2 deterministic state overlay design with three amendments (NM-2 auto-authority ceiling; distinct context provenance classes; "Market evidence found" summary wording). S2-A freezes that approved design as independently testable, completeness-checkable pure contract data so that later phases (V2 wiring, V3 qualification, future semantic entry) build against frozen vocabulary instead of prose — and so the three amendments cannot drift into prompt conventions. Contract-only on purpose: a phase that both defines and wires the V2 authority would change production behavior, which the frozen V1 invariants (deterministic identity, AI_ASSISTED_MATCH exclusion from 4A, human-review run scoping, HARD_CONFLICT precedence) forbid until the V2 workflow has its own reviewed phase. | IMPLEMENTED / PENDING FINAL REVIEW (PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-S2-A); AMENDED IN PART BY AD-066 (PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-S2-A-FU1) |
| AD-066 | SEMANTIC-AUTHORITY-V2-S2-A-FU1 review-blocker corrections (canonical spec §26.22): the pending S2-A contract (AD-065) is corrected in code on the authoritative starting SHA `46869f9a3ee6fad638b87b71cd14ed848224c057` (baseline collection 5972). CONTRACT ONLY — nothing is wired, no migrations, no V1 behavior change, no deployment. **Amended in part by AD-067 (S2-A-FU2):** the FU1 general state-specific gate (reaching AI_ASSISTED_COMPARABLE required RelationshipAuthority ESTABLISHED for U1/U2/U3/U5) was itself over-broad — the relationship requirement is now the frozen state/sub-state-specific SUBSTATE_RELATIONSHIP_REQUIREMENTS table (U1_TITLE_MPN NOT_REQUIRED; U2 + SKU_EQUALS_TARGET NOT_APPLICABLE; U2 + SKU_NOT_TARGET / U3 / U5 + NM-1 / U5 + NM-2 REVIEWED_RELATION_AUTHORITY_REQUIRED; U4 unchanged NOT_APPLICABLE). The orthogonal dimension derivations (A: product evidence quality; B: relationship authority), the NM-2 ceiling, customer-retrieval zero authority, and the immutable-table protections stand as recorded. (1) BLOCKER 1 — U4 WAS RE-CONSERVATIZED: S2-A made `ContextQuality.STRONG` globally equivalent to the presence of `MANUFACTURER_RELATION_AUTHORITY`, and the matrix's only `AI_ASSISTED_COMPARABLE` row (MATCH+HIGH+STRONG) locked U4_NO_MPN out of auto-authority — a no-MPN candidate has no identifier relationship for any source to establish. The authority prerequisites are now TWO ORTHOGONAL, STATE-SPECIFIC dimensions, each derived independently: A. PRODUCT EVIDENCE QUALITY (`ProductEvidenceQuality` STRONG/LIMITED/WEAK) — computed ONLY from the bounded `ProductEvidenceProfileV2` (usable product title + bounded matched-attribute facts; each fact = `ProductEvidenceDimension` x grounded candidate-side source, source vocabulary exactly {LISTING_PRODUCT_TITLE, REVIEWED_PRODUCT_CONTEXT} — no model-claim source exists, so the model cannot self-promote by asserting matched attributes) and reviewed product-grounding provenance classes; the frozen STRONG bar is bounded and testable: usable title AND >= `STRONG_PRODUCT_EVIDENCE_MIN_MATCHED_FACTS` (2) matched facts spanning >= `STRONG_PRODUCT_EVIDENCE_MIN_MATCHED_DIMENSIONS` (2) distinct hard product dimensions (the six-dimension `ProductEvidenceDimension` vocabulary mirroring the same-named ALWAYS_HARD conflict classes); a title alone is NOT strong; CUSTOMER_RETRIEVAL_RELATION grounds nothing; MANUFACTURER_PRODUCT_CONTEXT strengthens product grounding only; unsupported or state-contradicting profiles fail closed (ValueError). B. IDENTIFIER RELATIONSHIP AUTHORITY (`RelationshipAuthority` ESTABLISHED/NOT_ESTABLISHED/NOT_APPLICABLE) — via `derive_relationship_authority`: U4_NO_MPN is NOT_APPLICABLE (the question does not exist; relation provenance cannot change it), U1/U2/U3/U5 are ESTABLISHED only with reviewed relation provenance (customer retrieval confers ZERO), verified states are ESTABLISHED by the frozen deterministic comparator, C1 is NOT_ESTABLISHED, E1/E2 are NOT_APPLICABLE. The 27-row matrix is re-keyed on (decision x confidence x PRODUCT evidence quality) with the SAME tier values; reaching AI_ASSISTED_COMPARABLE additionally requires the state-specific relationship question to be NOT_APPLICABLE (U4) or ESTABLISHED (U1/U2/U3/U5) — the new general state-specific gate (fired rule CEILING_IDENTIFIER_RELATIONSHIP_NOT_ESTABLISHED) preserves S2-A's effective requirement for U1/U2/U3 and U5-NM-1 (no authority expansion there). REQUIRED BEHAVIOR NOW CONTRACTED: U4 + MATCH + HIGH + strong approved product evidence + no HARD conflict + no REVIEWABLE conflict => AI_ASSISTED_COMPARABLE is PERMITTED without MANUFACTURER_RELATION_AUTHORITY. The NM-2 CEILING REMAINS FROZEN (amendment 1): U5 + NEAR_MISS_SUBSTITUTION without reviewed authoritative relationship authority caps the maximum automatic tier at NEEDS_REVIEW — even for MATCH + HIGH + STRONG product evidence; CUSTOMER_RETRIEVAL_RELATION cannot satisfy that gate. `ContextQuality` / `derive_context_quality` are removed; `derive_authority_tier` gains a bounded `product_evidence` profile parameter (default = conservative state-derived profile that can never reach STRONG by itself). (2) BLOCKER 2 — FROZEN CONTRACT TABLES WERE MUTABLE DICTS: `Final[dict[...]]` is not runtime immutability. Every frozen contract mapping (`SEMANTIC_OUTCOME_TIER_MATRIX` 27 entries, `DETERMINISTIC_STATE_POLICIES` 4, `CONTEXT_PROVENANCE_CAPABILITIES` 3, `AUTHORITY_TIER_BADGES` 8, and the private `_PRIMARY_SIGNALS_BY_SUBSTATE` / `_STATE_OF_SUBSTATE` derivation tables) is now a runtime-immutable tuple of immutable entries (tuples / enums / frozen dataclasses / frozensets / str) with a pure lookup function (`semantic_outcome_tier`, `deterministic_state_policy`, `context_provenance_capabilities`, `authority_tier_badge`) — deterministically iterable, equality-testable, completeness-checkable (import self-checks), consumable without copying into a mutable authority table. The severity frozensets and the attention-order tuple remain immutable. The module's global namespace is import-self-checked to contain NO dict/list/set at all, and the boundary test `test_v2_contract_tables_are_immutable_data` now actually proves immutability with real mutation attempts (TypeError / AttributeError / FrozenInstanceError) covering every frozen authority/context/display mapping. | Independent review of pending S2-A identified two blockers: (a) the approved product goal of U4 (no-MPN description-match recall) was contradicted in the frozen contract — identifier-relationship authority had been globalized as the definition of "strong evidence", re-conservatizing exactly the state the approved design intended to open to qualified AI under strong description/product evidence; (b) an authority/safety contract that later runtime code will consume must not be stored as mutable dicts while claiming immutability. Both corrections stay inside the approved V2 design: (a) splits the single coupled context-quality dimension into the two orthogonal state-specific prerequisites the amendments were written for (the NM-2 ceiling, customer-retrieval zero authority, hard/reviewable conflict rules, and all 27 matrix tier values are unchanged); (b) is a representation correction with no semantic change. The evidence bar is deliberately bounded and testable so V3 can qualify against it, and the source vocabulary has no model-claim member so the model can never self-qualify. | IMPLEMENTED / PENDING FINAL REVIEW (PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-S2-A-FU1); AMENDED IN PART BY AD-067 (PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-S2-A-FU2) |
| AD-067 | SEMANTIC-AUTHORITY-V2-S2-A-FU2 review-blocker correction (canonical spec §26.23): the pending S2-A-FU1 contract (AD-066) is corrected in code on the authoritative starting SHA `f54489dbd4ea8375ba6924e21f3bce161caac9e1` (baseline collection 5989). CONTRACT ONLY — nothing is wired, no migrations, no V1 behavior change, no deployment. BLOCKER — the relationship gate was global, not state-specific: FU1 required RelationshipAuthority.ESTABLISHED for EVERY U1/U2/U3/U5 candidate before AI_ASSISTED_COMPARABLE was allowed. The relationship requirement must itself be STATE-SPECIFIC bounded contract data (the purpose of semantic AI is to resolve deterministic uncertainty; absence of manufacturer relationship proof must not force every uncertain identifier-shaped listing into human review). DELIVERED: (1) RelationshipRequirement (NOT_APPLICABLE / NOT_REQUIRED / REVIEWED_RELATION_AUTHORITY_REQUIRED); (2) SUBSTATE_RELATIONSHIP_REQUIREMENTS — runtime-immutable tuple of 14 (sub-state, primary signal, requirement) entries covering exactly the combinations the frozen derivation permits (import-self-checked against _PRIMARY_SIGNALS_BY_SUBSTATE; pure fail-closed lookup substate_relationship_requirement — unknown combinations never gain authority): V_EXACT / V_NORMALIZED_EXACT / U4 (NO_RELATION, EMPTY_MPN_FIELD) / C1 / E1 / E2 (NO_RELATION, EMPTY_MPN_FIELD) / U2 + SKU_EQUALS_TARGET -> NOT_APPLICABLE; U1_TITLE_MPN -> NOT_REQUIRED; U2 + SKU_NOT_TARGET / U3_PARTIAL_BOUNDARY / U5 + NEAR_MISS_TRUNCATION / U5 + NEAR_MISS_SUBSTITUTION -> REVIEWED_RELATION_AUTHORITY_REQUIRED; (3) derive_authority_tier gate re-keyed on the table — the automatic tier is capped at NEEDS_REVIEW (fired rule CEILING_IDENTIFIER_RELATIONSHIP_NOT_ESTABLISHED, name unchanged) when and only when the entry requires REVIEWED_RELATION_AUTHORITY and dimension B is not ESTABLISHED; for U5 + NM-2 the frozen NM-2-specific ceiling rule caps first (explicit audit form; subsumes the general gate). REQUIRED BEHAVIOR NOW CONTRACTED: U1 + exact title MPN + MATCH/HIGH + STRONG bounded product evidence + no HARD/REVIEWABLE conflict => AI_ASSISTED_COMPARABLE WITHOUT MANUFACTURER_RELATION_AUTHORITY (COMPATIBILITY_WORDING / accessory / product-role conflicts remain safety inputs through the taxonomy — no recall expansion bypasses safety); U2 + SKU_EQUALS_TARGET + MATCH/HIGH + STRONG + clean => AI_ASSISTED without the requirement; U2 + SKU_NOT_TARGET and U3 follow explicit conservative policies (capped at NEEDS_REVIEW without reviewed relationship authority, including customer retrieval); U5/NM-1 follows its own explicit bounded policy (the NM-2-specific rule does not fire for NM-1); U4 FU1 behavior unchanged (NOT_APPLICABLE, auto-tier capable); U5/NM-2 ceiling, customer-retrieval zero authority, HARD_CONFLICT taxonomy, BRAND=REVIEWABLE, CONDITION=PRICE_DIMENSION_ONLY, U4 recall, and precedence HARD_CONFLICT > HUMAN_CONFIRMED > AI unchanged. Dimensions A/B derivations unchanged from FU1; all FU1 immutable-table protections retained + the new table added to the immutability proof. Three FU1 test nodes that encoded the blanket gate were corrected in place (exact old/new expectations in STATUS); 14 new test nodes; no test deleted/renamed/skipped/xfail/deselected/ignored/weakened; collection 5989 -> 6003 (no decrease). | Independent review of pending S2-A-FU1 identified that the U4 correction had been implemented by carving U4 out of a BLANKET U1/U2/U3/U5 relationship gate, when the approved contract requires the relationship requirement to be state-specific: U1_TITLE_MPN exists precisely because deterministic 3C refuses to treat title text as manufacturer identity authority — the semantic evaluation is the designated resolver of the title-MPN question, and MATCH + HIGH + STRONG bounded product evidence + clean conflicts must be capable of AI_ASSISTED_COMPARABLE without MANUFACTURER_RELATION_AUTHORITY; U2 + SKU_EQUALS_TARGET carries a frozen-2A-established relationship; U2 + SKU_NOT_TARGET / U3 / U5 (both shapes) keep explicit conservative REVIEWED_RELATION_AUTHORITY_REQUIRED policies so no authority expands where the identifier is genuinely not the target. The correction is bounded contract data (one entry per permitted (sub-state, primary signal) combination, completeness-checked, fail-closed, V3-consumable) — not another ad hoc gate — and it preserves every FU1 safety contract (NM-2 ceiling, customer retrieval zero authority, conflict taxonomy, precedence, immutable tables, U4 behavior). | IMPLEMENTED / PENDING FINAL REVIEW (PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-S2-A-FU2) |
| AD-068 | SEMANTIC-AUTHORITY-V2-S2-B persistence / codec phase (canonical spec §26.24): on the authoritative starting SHA `9206126d4fb13300028256964c98f477c5d17969` (baseline collection 6003), the complete Semantic Authority V2 evaluation/provenance artifact is persisted as a first-class versioned record covering ALL semantic outcomes (MATCH / NO_MATCH / UNCERTAIN / RUNTIME_FAILURE / NOT_EVALUATED, with or without fallback). BOUNDED PERSISTENCE/CODEC ONLY: no V2 semantic eligibility is enabled in production, no live semantic execution is modified, no AI is called for U4/U5, no authority changes, no UI, no deployment. DELIVERED: (1) PURE ARTIFACT — new `research/semantic_decision_record.py` (stdlib + research package exports only; no Django, no I/O, no clock, no float): the immutable `SemanticDecisionRecord` value object with binding (run UUID, assessment_index, source_url), the exact contract-version binding (semantic contract V1, prompt v1.1, input/output schema v1, authority contract `SEMANTIC_AUTHORITY_V2_S2A_FU2`), the deterministic V2 context (state/sub-state/relationship signals/normalized keys + the derived relationship-requirement snapshot), the bounded `ProductEvidenceProfileV2` (encoded versioned; derived quality snapshot), the context provenances as present at evaluation time, the exact recorded prompt input, the recorded semantic output (evaluation state, decision, confidence, structured `ConflictClass` set, bounded reason code, recorded attribute lists — the V1 output contract admits no prose), the bounded runtime provenance (pinned primary/fallback attempts with role/number/provider/model/outcome, fallback reason, bounded failure class, actual provider/model, ISO-8601 UTC evaluation instants), the derived audit snapshots (relationship authority, authority tier, fired rules under the exact bound contract), and self-verifying canonical SHA-256 input/output section digests (floats refused at canonical encoding). Only DETERMINISTIC_UNCERTAIN contexts are ledgered (entry-point-only; anything else fails closed). The runtime-provenance vocabularies are MIRRORS of the frozen FU3A runtime (AttemptOutcome/SemanticFailureClass/SemanticFallbackReason + route constants), drift-pinned by tests — the pure research layer imports no semantic runtime surface (the established V2SemanticDecision-mirrors-SemanticDecision precedent). (2) STRICT VERSIONED CODEC — new `research/semantic_decision_codec.py`: schema v1; exact field set at every level (missing AND extra keys rejected); strict enums (unknown values rejected); no float authority data (floats anywhere in a payload rejected); no lossy serialization (sets encoded sorted-unique; order-significant lists kept); no silent defaulting (nullable = present key with null); decode wraps every constructor/validation failure in the bounded `SemanticDecisionCodecError`; `canonical_payload_digest` = SHA-256 of the canonical (sorted-keys, compact, ASCII) payload encoding. (3) PURE REPLAY — new `research/semantic_decision_replay.py`: zero-live reconstruction from the artifact: the contract-binding gate knows EXACTLY one safe envelope `SUPPORTED_CONTRACT_BINDINGS = (("V1", "1.1", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU2"),)` and REFUSES explicitly any other (unknown or future) binding — an old persisted decision is never silently reinterpreted under a newer contract, and the historical binding is never substituted by current module constants; it reconstructs the historical `SemanticEvaluationV2`, the `IdentityStateAssessmentV2`, the product-evidence profile, and the context provenances; it re-derives under the frozen S2-A module (relationship requirement, product evidence quality, relationship authority, `derive_authority_tier` with no human overlay) and PROVES the stored derived audit snapshots agree exactly (tamper/version-drift => `SemanticDecisionReplayError`). (4) PERSISTENCE — additive `runs.SemanticDecisionRecord` model (migration 0012, single CreateModel, no backfill, no rewrite of any existing structure): UUID pk, run FK (CASCADE, related_name `semantic_decision_records`), assessment_index, schema_version, opaque `payload` JSONField, and a SEPARATE `payload_digest` column — the whole-artifact tamper anchor computed at write time by the service and verified on every read (a QuerySet.update()/raw-SQL bypass is caught on read; fail closed). Storage, not interpretation: no ad hoc semantic columns; the schema is owned by the codec. One record per (run, assessment_index) (unique constraint). Immutability: artifact columns editable=False + a single service-owned write path that never overwrites (`SemanticDecisionAlreadyRecordedError`). NEW service `execution/semantic_decision_persistence.py` (the API future S2-C will call): `persist_semantic_decision` (encode + digest + transactional create; run_id binding check), `load_semantic_decision` (digest verification + strict decode; ABSENCE returns None — legacy semantic provenance unavailable under V2, never NO_MATCH / NOT_EVALUATED / AI failure, never fabricated), `replay_semantic_decision_record` (load + full binding verification against the run's persisted evidence — canonical request identity + snapshot assessment source-URL at the recorded index — + the pure replay). The service owns no authority derivation logic (it composes the research-layer replay; mechanically guarded). (5) SEPARATION PRESERVED — `AiAssistedReviewCandidate` remains the human-review workflow artifact (MATCH outcomes only, mutable review state, forged-confirmation protections, HARD_CONFLICT supersession, Reviewed Price behavior); the two share the narrow explicit (run, assessment_index) stable binding and reference neither other's rows. S2-B does NOT wire live semantic execution: the current V1 path creates and reads ZERO records (proved by a fake-transport execution test + source scans); live wiring is S2-C together with the final V2 input/output contract, so S2-B does not persist a temporary contract. (6) TESTS — new nodes across `tests/research/test_semantic_decision_record.py`, `test_semantic_decision_codec.py`, `test_semantic_decision_replay.py`, `test_semantic_decision_boundaries.py`, `tests/runs/test_semantic_decision_record.py`, `tests/execution/test_semantic_decision_persistence.py` (all outcomes persist/round-trip/replay; provenance exactness; structured safety round-trips; codec strictness incl. extra/missing/unknown-schema/unknown-enum/malformed/tamper; zero-live sentinels; contract-version refusal; human-review preservation; architecture boundaries). Six existing model-registry / ResearchRun field pins extended in place to include the new additive model (the mandated "made twice" model-addition decision): `tests/research/test_research_identity_boundaries.py`, `tests/runs/test_research_run_boundaries.py` (model set + EXPECTED_FIELDS), `tests/web/test_web_boundaries.py`, `tests/providers/test_provider_boundaries.py`, `tests/runs/test_comparable_research_execution.py`. No test deleted/renamed/skipped/xfail/deselected/ignored/weakened; the known Windows/Python-3.14 subprocess flake allowlist NOT expanded. | The S2-A audit found full semantic provenance exists mainly for MATCH / AiAssistedReviewCandidate paths; NO_MATCH / UNCERTAIN / runtime failures preserve no structured decision history for future V2 authority/replay. A first-class persisted semantic-decision artifact (rather than overloading AiAssistedReviewCandidate, which carries human-review responsibilities and must not become an ambiguous all-outcome container) provides the zero-live historical replay foundation: the artifact binds to the exact semantic/authority contract versions under which it was produced, stores source inputs plus a small set of derived audit snapshots whose agreement replay must prove, and fails closed on unknown versions, tamper, and corruption. The separate payload-digest column is the whole-artifact tamper anchor that in-payload section digests alone cannot provide. Persistence/codec now, live wiring in S2-C, avoids persisting a temporary contract that the final V2 input/output contract would immediately obsolete. | IMPLEMENTED / PENDING FINAL REVIEW (PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-S2-B); AMENDED IN PART BY AD-069 (PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-S2-B-FU1) |
| AD-069 | SEMANTIC-AUTHORITY-V2-S2-B-FU1 persistence-envelope / semantic-V1 decoupling (canonical spec §26.25): bounded architecture correction on the pending S2-B candidate (AD-068), starting SHA `95d9fd903cf941996d63dcd9b7f48265daf7c2a4` (baseline collection 6227). BLOCKER corrected: the durable record/codec/replay infrastructure was hard-bound to the OLD semantic V1 contract (semantic contract "V1", prompt "1.1", exact V1 prompt-input/output shape, exact current primary/fallback provider/model route), which would have forced S2-C's final V2 contract into the obsolete V1 persistence contract or required a new persistence schema before schema v1 was used live. CORRECTION: the persistence ENVELOPE is now versionable INDEPENDENTLY from the semantic contract it contains (envelope schema version != semantic contract version != prompt version != input/output schema versions != runtime route version). (1) UNIVERSAL ENVELOPE FOUNDATION — `research/semantic_decision_record.py` rewritten: canonical encoding discipline (no floats), strict decode helpers, the universal persistence binding (run UUID canonical, assessment_index non-negative int, source_url non-empty), the bounded error vocabulary (SemanticDecisionCodecError, SemanticDecisionReplayError), and the `SemanticDecisionContractAdapter` extension point (frozen dataclass: envelope_schema_version, semantic_contract_version, supported_bindings, record_type, + encode/decode/replay/run_binding_violation) — it owns no semantic contract value. (2) UNIVERSAL ENVELOPE CODEC — `research/semantic_decision_codec.py` rewritten: `SEMANTIC_DECISION_SCHEMA_VERSION` (1) is the PAYLOAD FORMAT version (the row's schema_version column), independent of the recorded semantic contract version; the explicit adapter REGISTRY (frozen tuple, currently exactly the Semantic V1 adapter) is the version-adapter extension point; decode = row version registered -> mapping + no floats -> declared envelope version agrees with the row's -> universal binding exact/valid -> contract section names a semantic contract version (dispatch key) -> dispatch on the RECORDED (envelope schema version, semantic contract version) pair to the registered adapter (no adapter -> explicit fail-closed refusal, never best-effort decoded, never reinterpreted); encode = dispatch on the record's registered adapter type + universal framing self-check; `canonical_payload_digest` unchanged. The universal modules name no V1 route token and no quoted V1 contract/prompt literal (mechanically guarded). (3) UNIVERSAL REPLAY DISPATCH — `research/semantic_decision_replay.py` rewritten: `SUPPORTED_CONTRACT_BINDINGS` is exactly the union of the registered adapters' supported bindings (no gate/registry drift); `replay_semantic_decision` reads the RECORD's recorded identity (never current module constants), refuses unsupported bindings explicitly, then selects the exact registered adapter and delegates the version-owned replay. (4) SEMANTIC V1 ADAPTER (FIRST REGISTERED) — NEW `research/semantic_decision_v1.py` owns, and ONLY it owns: the V1 contract identity (V1 / prompt 1.1 / input+output schema v1 / authority contract SEMANTIC_AUTHORITY_V2_S2A_FU2 = `V1_CONTRACT_BINDING`), the V1 pinned route (amax/qwen3.8-27b primary, vllm-262k/Qwen3.6-27B-262K fallback — a V1 contract rule, not an envelope invariant; drift-pinned to FU3A), the V1 runtime-provenance mirrors (drift-pinned), the V1 prompt-input shape, the V1 typed record `SemanticDecisionRecordV1` (RENAMED from SemanticDecisionRecord so the V1 payload is no longer conflated with the universal schema; the V1 exact-binding check, the V1 route pin, the S2-A context validation, the evaluation/execution coherence, and the self-verifying section digests all remain as V1-adapter rules), the strict V1 payload codec, the V1 pure zero-live replay (reconstruction + S2-A re-derivation + derived-agreement proof), the V1 run-binding check (recorded prompt-input target MPN/description == run's canonical request), and the registered instance `SEMANTIC_V1_ADAPTER`. The V1 payload's PERSISTED BYTES are byte-identical to the S2-B schema-v1 payload: no data migration. (5) UNIVERSAL SERVICE — `execution/semantic_decision_persistence.py` now contract-agnostic: persist dispatches through the registry (unregistered artifact type -> TypeError; the service names no V1 literal), replay adds the adapter-specific recorded request-identity check (`adapter.run_binding_violation`) alongside the universal binding verification, and the immutability wording is corrected (editable=False is NOT DB enforcement; the APPLICATION contract = service-owned append-only write path + (run, assessment_index) uniqueness + digest anchor verified on every read; out-of-band mutation detected/fails closed where the digest differs). (6) MODEL/MIGRATION UNCHANGED — `runs.SemanticDecisionRecord` fields, help text, constraints, index, and migration 0012 (single additive CreateModel) are untouched; only the model docstring is corrected (universal envelope; schema_version = envelope format axis; future contracts reuse the row by registering an adapter — no model change, no new migration, no data rewrite; corrected immutability wording). NO live execution wiring, NO V2 contract definition (S2-C freezes the final V2 input/output/prompt/eligibility contract and registers a V2 adapter at that time), NO authority expansion, NO deployment. (7) TESTS — no test deleted/renamed/skipped/xfail/deselected/ignored/weakened merely to obtain green; the nodes whose pins encoded the now-rejected coupling (artifact schema v1 == semantic V1 forever at the universal layer) were corrected ONLY in that expectation while preserving the safety property (interpretation requires an explicitly supported exact semantic contract): class references move to SemanticDecisionRecordV1 (mechanical rename), the encode non-record TypeError pin moves to the registry-dispatch message, the V1 contract/prompt/authority-binding rejection nodes now test the V1 adapter pin, the private section-encoder imports move to the V1 module, the boundaries MODULES guard set gains the fourth research module (strengthened), the package export pin updates to the new surface; new nodes prove the 19 mandated properties (envelope/contract version independence; the V1 adapter validates V1 exactly; the V1 route pin stays V1-adapter-owned; the universal storage layer owns no V1 provider/model assumptions; replay dispatches through explicit version-specific support; unknown semantic contract / unknown artifact schema fail closed; historical V1 replay + MATCH/NO_MATCH/UNCERTAIN/runtime-failure/fallback provenance unchanged; digest/tamper unchanged; legacy absence distinct; human review unchanged; S2-A frozen; no live wiring; zero AI/network replay). Collection 6227 -> 6270 (no decrease; +43 = 35 new nodes [5 record + 8 codec + 3 replay + 11 boundaries (3 new decoupling guards + 8 auto-expanded) + 4 runs + 4 persistence] + 8 auto-expanded existing parametrized directory-scan nodes for the fourth research module [domain caller-token +1, providers +1, runs +1, web +1, research-core per-file scans +4]). | Independent review of the pending S2-B found the persistence envelope hard-bound to the obsolete V1 contract, which would have forced S2-C's final V2 contract into the V1 persistence contract (or a new persistence schema before schema v1 was used live) — neither acceptable. The correction preserves every S2-B safety property (strict fail-closed codec, tamper anchor, anti-reinterpretation replay gate, zero-live, human-review separation, additive migration) while moving ALL V1 assumptions into the first registered version-specific adapter and making the envelope, the row, the migration, and the service contract-agnostic: storage can durably identify any registered semantic contract; interpretation requires an explicitly registered adapter. | IMPLEMENTED / PENDING FINAL REVIEW (PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-S2-B-FU1) |
| AD-070 | SEMANTIC-AUTHORITY-V2-S2-C final Semantic V2 contract + eligibility + execution wiring (canonical spec §26.26): on the authoritative starting SHA `c6caa23c024e48962191a0c856230b684fb21c3c` (S2-B-FU1 endpoint, PENDING FINAL REVIEW; baseline collection 6270), the FIRST FINAL Semantic V2 contract is frozen in code and V2 semantic execution is wired into the comparable-research execution flow for V2-eligible candidates. S2-C does NOT declare the V2 route QUALIFIED for the new contract (explicit marker ``V2_AUTHORITY_QUALIFIED = False``; Qualification V3 comes after S2-C review/freeze) and gives V2 outputs ZERO production authority: no Machine Price, no 4A bucket, no Reviewed Price, no headline market statistics, no AI-Assisted Comparable pricing output, no UI authority presentation, no vendor authority, no V2 human-review candidate. (1) FINAL V2 INPUT CONTRACT — NEW `research/semantic_v2.py`: the versioned immutable `SemanticMatchCaseV2` (23 required fields, no silent defaults; absent candidate facts are explicit None): A. TARGET (case_id, requested MPN, requested description); B. CANDIDATE LISTING (source URL, title, published MPN field, published SKU, brand and condition when separately observed, reserved structured-listing-evidence section, commercial price/package context labeled NEVER identity evidence, frozen 3C evidence source); C. DETERMINISTIC IDENTITY CONTEXT (IdentityStateV2, substate, primary signal, all bounded signals, frozen normalized keys, the frozen state/sub-state-specific relationship-requirement snapshot — contract-derived, not caller input); D. CONTEXT PROVENANCE (the bounded ContextProvenance classes as present; CUSTOMER_RETRIEVAL_RELATION is retrieval-only, zero identity authority, never described as manufacturer equivalence); E. PRODUCT EVIDENCE (the authority-side ProductEvidenceProfileV2 — deterministic/reviewed only). Construction fails closed on foreign state (UNCERTAIN only), foreign context (re-derivation must agree), wrong requirement, or unsupported profile. (2) ELIGIBILITY V2 — `is_v2_semantic_eligible(assessment)`: based on the frozen S2-A derived state — DETERMINISTIC_UNCERTAIN only (U1 / U2 both signals / U3 / U4 / U5 both near-miss shapes); VERIFIED / CONFLICT / UNEVALUABLE never eligible; no Levenshtein, no arbitrary substring matching; no manufacturer special case; the V1 predicate (execution.semantic_integration) is unchanged and remains the only V1 gate. (3) SAFE PRODUCT-EVIDENCE BUILDER — `build_v2_product_evidence_profile(observation, context_provenances, matched_facts)`: STRONG is reachable only from bounded facts grounded in LISTING_PRODUCT_TITLE / REVIEWED_PRODUCT_CONTEXT (the frozen source vocabulary has no model-claim member; the builder signature accepts no model output); fail-closed on ungrounded/unsupported facts. DOCUMENTED LIMITATION: the current main-flow deterministic extraction proves no exact bounded identity-dimension equality for listing candidates, so the live path passes matched_facts=frozenset() — candidates remain at most LIMITED/WEAK under the frozen S2-A bar (NEEDS_REVIEW until future evidence infrastructure); no fact is fabricated, no heuristic invented, the S2-A evidence bar is not weakened. (4) FINAL V2 OUTPUT CONTRACT — strict structured response: decision (MATCH/NO_MATCH/UNCERTAIN), confidence (HIGH/MEDIUM/LOW), bounded reason code (17 generic codes; no manufacturer-specific codes), bounded structured attributes (12 observation dimensions incl. PACKAGING_QUANTITY / BUNDLE / ACCESSORY_RELATION / BRAND / REVISION_OR_SUFFIX / CONDITION, each dimension+detail), bounded missing-critical dimensions, structured ConflictClass set validated against the frozen S2-A vocabulary; REASON_CODE_RULES frozen data keeps reason/conflict coherence (NO_MATCH_CAPACITY requires ConflictClass.CAPACITY; MATCH/UNCERTAIN may never carry an ALWAYS_HARD class; NO_MATCH is always conflict-grounded); unknown decision/confidence/reason/enum, missing fields, extra fields (no chain-of-thought surface), malformed lists, and incoherent combinations all fail closed. CONDITION stays PRICE_DIMENSION_ONLY; BRAND stays REVIEWABLE; PACKAGING_QUANTITY stays ALWAYS_HARD (physical-product equivalence is never sales-unit equivalence). (5) FINAL PROMPT V2 — NEW `semantic/contract_v2.py`: SEMANTIC_PROMPT_VERSION_V2 = "2.0" (used unchanged by Qualification V3 unless an actual defect is found first); the system prompt states the commercial-semantic-equivalence task, the explicit NOT-asked-to rules (no price estimation; no Machine Verified decisions; no overriding deterministic HARD_CONFLICT; no inferring manufacturer authority; no turning customer aliases into manufacturer equivalence; no market-aggregation decisions), the identifier rules (exact MPN strong but not only; missing candidate MPN not automatically NO_MATCH; title MPN may be compatibility/reference wording; careful SKU interpretation; near-miss not automatically equivalent), the provenance rules (customer retrieval = retrieval hint only; labeled manufacturer relation authority = stronger evidence; manufacturer product context = grounding only), the sales-unit rules (same physical product with different pack quantity/bundle is not pricing-comparable as the same sales unit; accessory/tray/caddy/enclosure is a material conflict), the strict six-key JSON response schema, and "insufficient evidence -> UNCERTAIN, never a guess; a false MATCH is materially worse than UNCERTAIN"; the user prompt deterministically renders the exact recorded V2 input's five sections (the historical prompt is reconstructable from the persisted input without any live call). (6) V2 RUNTIME — NEW `semantic/runtime_v2.py`: the V2 pinned route (amax/qwen3.8-27b primary, vllm-262k/Qwen3.6-27B-262K fallback — the currently frozen qualified route identities, carried as V2 contract data, drift-pinned to the frozen FU3A route), temperature 0.0 / max_tokens 32768, fallback on EXECUTION FAILURE ONLY (the frozen allowlist; MATCH/NO_MATCH/UNCERTAIN at any confidence is final), model identity verification, strict V2 output at the boundary (malformed -> MALFORMED_JSON, unknown/incoherent -> SCHEMA_INVALID), bounded per-attempt provenance + evaluation instants, and the explicit `V2_AUTHORITY_QUALIFIED = False` qualification-boundary marker. The V1 runtime is byte-untouched. (7) V2 PERSISTENCE ADAPTER (SECOND REGISTERED) — NEW `research/semantic_decision_v2.py` registered at the S2-B extension point: SemanticDecisionRecordV2 (exact V2 binding ("V2", "2.0", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU2"), the exact recorded V2 input as the case section, the strict structured output, the V2 route pin, the derived audit snapshots incl. product evidence quality, self-verifying digests), the strict V2 payload codec (envelope schema 1 reused — no model change, no migration), the V2 zero-live replay (reconstruction + S2-A re-derivation + derived-agreement proof; exact-binding gate; a future V2-lineage binding refused), the V2 run-binding check (recorded case target MPN/description == the run's canonical request), and SEMANTIC_V2_ADAPTER. Cross-adapter reinterpretation fails closed in both directions. (8) EXECUTION WIRING — NEW `execution/semantic_decision_v2_execution.py` + orchestration: every V2-eligible candidate (the frozen S2-A DETERMINISTIC_UNCERTAIN states, including the U4/U5 states V1 never reaches — the motivating Micron-shape near miss) gets exactly one V2 evaluation on the V2 pinned route; ALL outcomes persist as SemanticDecisionRecordV2 in the atomic final publication block through the unchanged S2-B service (MATCH / NO_MATCH / UNCERTAIN / RUNTIME_FAILURE / fallback success / fallback failure); the 4D-D alias-expanded search batch carries CUSTOMER_RETRIEVAL_RELATION provenance in the recorded V2 input (the 4D-D firewall restricts the V1 authority path only — V2 is persist-only, so the motivating alias-retrieved near misses reach the V2 semantic layer); V1 behavior is unchanged (the V1 predicate, the V1 evidence writes, and the V1 review-candidate creation all stand; V1-eligible candidates run BOTH the unchanged V1 evaluation and the new V2 evaluation — the explicit V1->V2 switch decision belongs to Qualification V3); no V2 ExecutionDetailCode vocabulary, no V2 execution-evidence rows (the ledger is the S2-B audit surface), no V2 review candidate. (9) TESTS — new files: `tests/research/test_semantic_v2_contract.py` (60: eligibility truth table over real 3C assessments; input exactness/immutability/no-defaults/provenance separation/requirement snapshot/foreign-context and foreign-request fail-closed; the evidence-builder safety incl. the proof a V2 MATCH/HIGH with rich matched_attributes cannot raise ProductEvidenceQuality; output strictness incl. reason/conflict coherence and the condition price-only distinction; the bounded reason vocabulary), `tests/semantic/test_contract_v2.py` (33: prompt version pin; the task framing; every explicit behavioral rule; no chain-of-thought surface; the five-section rendering incl. the customer-relation retrieval-only label and the never-identity commercial context), `tests/semantic/test_runtime_v2.py` (29: exact V2 route pins; fallback-on-execution-failure-only; MATCH/NO_MATCH/UNCERTAIN/low-confidence never fallback; exact failure/fallback provenance; strict output at the boundary; defect propagation; V2_AUTHORITY_QUALIFIED False), `tests/research/test_semantic_decision_v2.py` (50: V2 record contract identity + route pin + all outcomes + incoherent-output refusal; codec round-trips + exact versions/input/output/attempts stored + cross-adapter refusal + tamper; zero-live replay + derived-agreement + unknown-binding refusal + V1 replay unchanged), `tests/research/test_semantic_v2_boundaries.py` (32: universal envelope owns no V1/V2 route assumption; V1 assumptions in the V1 adapter; V2 assumptions in the V2 adapter/contract; new research modules pure; S2-A frozen; mirror drift pins incl. V2_AUTHORITY_QUALIFIED; persistence owns no authority logic; aggregation owns no semantic output interpretation; the model output cannot self-promote — architecture scans), `tests/execution/test_semantic_decision_v2_execution.py` (20: all outcomes persist through the service; exact stored identity; the authority firewall — V2 MATCH/HIGH absent from 4A, no review candidate, Machine Price and Reviewed Price unchanged, no HUMAN_CONFIRMED; V1 coexistence incl. the V1 review candidate bound to prompt 1.1; U4 with zero V1 calls; alias provenance NOT_ESTABLISHED; service replay of V2 and V1; the V1 path alone still writes zero records), `tests/execution/test_semantic_v2_motivating_case.py` (9: the motivating Micron shape — not machine-verified; U5/NM-1 bounded classification; V2 entry point; rich structured V2 input; customer relation alone establishes no identity; the frozen U5/NM-1 ceiling caps MATCH/HIGH+STRONG at NEEDS_REVIEW without reviewed relationship authority (and MANUFACTURER_RELATION_AUTHORITY is the class that clears it, subject to all gates); full-orchestration no-Machine-Price-contamination proof with the ESTABLISHED 4D-D alias relation recorded as CUSTOMER_RETRIEVAL_RELATION). Corrected existing nodes (requirement corrections — the registry is the mandated S2-C extension point; the safety property in each is preserved and where possible strengthened): `test_supported_bindings_are_exactly_the_frozen_v1_tuple` (now exactly the V1+V2 bindings, in registration order), `test_supported_bindings_are_the_registry_union` (len 2), `test_envelope_schema_version_and_semantic_contract_are_distinct_axes` / `test_unknown_semantic_contract_fails_closed_at_dispatch` / `test_unknown_semantic_contract_error_is_not_a_v1_shape_error` (the unknown-contract axis is proven with actually unregistered keys — "V2" is now registered), `test_registry_lookup_is_explicit_and_fail_closed` (1xV2 registered; 2xV1/V2 and 1xV9 unregistered), `test_v1_record_is_the_registered_v1_adapter_record` (unregistered pairs use 1xV9 / 2xV1 / 2xV2), `test_registry_is_the_explicit_version_adapter_extension_point` (registry len 2; both adapters' envelope version == SEMANTIC_DECISION_SCHEMA_VERSION; fail-closed pairs minus 1xV2) + its MODULES guard set gains the fifth research module (the same eight guards apply — strengthened) and the package-export pin gains the V2 surface (strengthened), `test_storage_carries_unknown_semantic_contract_but_interpretation_fails_closed` (unknown-contract storage/interpretation property proven with "V9"; new adjacent node proves cross-CONTRACT reinterpretation — a V1-shaped body under the registered V2 name — is refused at the V2 adapter), `test_only_the_service_module_references_the_ledger_in_execution` (the exact ledger-reference allowlist gains the S2-C V2 wiring module; the V1 path's zero-touch property is proven by the adjacent unchanged nodes). No test deleted/renamed/skipped/xfail/deselected/ignored; no file decreased; the known Windows/Python-3.14 subprocess flake allowlist NOT expanded. Collection 6270 -> 6528 (+258 = 233 new-file nodes + 16 auto-expanded directory scans for the two new research modules [domain +2, providers +2, runs +2, web +2, research-core per-file +8] + 8 auto-expanded S2-B boundary MODULES guards for the fifth module + 1 new cross-contract persistence node). | The customer complaint: the system finds too few usable market-comparison sources because semantic AI mostly annotates candidates deterministic matching already understands — it must actually resolve DETERMINISTIC_UNCERTAIN listings (U4 no-MPN usable title, U5 bounded near-miss MPN — e.g. the Motivating Micron-shape explicit near miss — which the frozen V1 predicate never reaches). S2-A froze the authority contract, S2-B/S2-B-FU1 froze the contract-agnostic persistence envelope with an explicit adapter extension point; S2-C is the phase that defines the FINAL V2 input/output/prompt/eligibility/runtime contract (used unchanged by Qualification V3), registers the first V2 adapter, and wires V2 execution — while keeping every V2 output at zero production authority until the route is formally qualified. Persisting ALL outcomes of every V2-eligible candidate (evidence/provenance only) gives Qualification V3 the corpus, the zero-live replay gives audit, and the explicit qualification marker makes the authority boundary mechanical. | IMPLEMENTED / PENDING FINAL REVIEW (PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-S2-C) |
| AD-071 | SEMANTIC-AUTHORITY-V2-S2-C-FU1 input evidence fidelity (canonical spec §26.27): bounded INPUT-EVIDENCE correction on the pending S2-C candidate (AD-070), on the authoritative starting SHA `a3127bca4bc4177b447ece8b20c33d83ec4ed415` (baseline collection 6528). S2-C is REVIEWED but NOT APPROVED / NOT FROZEN and MUST NOT deploy, and NO historical production V2 record exists anywhere (verified: the `runs_semanticdecisionrecord` table is absent from the development database; V2 is persist-only and unqualified), so FU1 amends the PRE-FREEZE candidate in place: the contract binding stays exactly `("V2", "2.0", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU2")` and the prompt version stays `2.0` (2.0 never shipped — the frozen 2.0 that Qualification V3 will qualify against is the corrected text; bumping would create a phantom version of an unshipped artifact). BLOCKER corrected: the S2-C "FINAL" V2 input did not provide the structured product/commercial evidence the product goal requires — `candidate_specs` was a misleading free-text slot always None, the commercial context was a composed price/availability/seller/offer string, no packaging/sales-unit channel existed, and the motivating test claimed family/capacity/interface/form factor were "structured" merely because the tokens occur in the candidate TITLE. DELIVERED: (1) EXTRACTION-CAPABILITY AUDIT documented in `research/semantic_v2.py` and the report: 3A `ListingObservation` carries page-published structured fields (title, MPN field, SKU, brand, price, currency, availability, condition, seller, offer URL; the remaining JSON-LD material stays in the OPAQUE raw_reference, unparsable per AD-040); 3B normalizes commercial only; 3C compares explicit MPN fields only; the 6A/6B/6C/7A/7B specification infrastructure exists ONLY in the comparable-research flow and requires an ESTABLISHED identity; the 4D-D alias acquisition is the ONLY reviewed manufacturer target context the main flow carries. Consequences: candidate-side structured product facts are filled ONLY from published fields the extractor actually carries (brand); every other product dimension stays explicit None; the published title is RAW observation text (no token is parsed into a fact); the commercial section is typed with the explicit sales-unit channel. (2) CORRECTED INPUT CONTRACT — `SemanticMatchCaseV2` (17 required top-level fields; no silent defaults): A. TARGET = `TargetEvidenceV2` (structured caller-published MPN; the requested description as RAW observation text, explicit None when absent; `ReviewedTargetContextV2 | None` — structured/reviewed target-side context, present only when the main flow carries one, relation kind bounded to `CUSTOMER_RETRIEVAL_ALIAS` = zero identity authority, full fetch provenance incl. ISO-8601 UTC instant and 64-hex body digest, fail-closed); B. CANDIDATE LISTING = published identifier fields (MPN field / SKU), the frozen 3C evidence source, `CandidateProductEvidenceV2` (nine bounded product dimensions — each a `CandidateObservationFactV2` (value + explicit `CandidateEvidenceSourceV2` provenance: PUBLISHED_STRUCTURED_FIELD / LISTING_TITLE / SPECIFICATION_TEXT / REVIEWED_PRODUCT_CONTEXT — no model-claim member) or explicit None; plus raw_title_text / raw_specification_text labeled RAW observation text) and `CandidateCommercialEvidenceV2` (condition / price / currency / availability / seller as bounded facts, offer URL, and the REQUIRED `CandidateSalesUnitEvidenceV2` channel — ALWAYS explicit: UNAVAILABLE (all value fields None) or OBSERVED (bounded `SalesUnitKindV2` SINGLE_UNIT / PACK_QUANTITY / TRAY_OR_FACTORY_PACK / BUNDLE + published raw detail + provenance + bounded positive int quantity where the kind carries one; PACK_QUANTITY requires it, SINGLE_UNIT forbids it); the live main-flow builder always records UNAVAILABLE — the extractor publishes no packaging field and nothing is inferred from price); C. DETERMINISTIC IDENTITY CONTEXT, D. CONTEXT PROVENANCE, E. authority-side PRODUCT EVIDENCE — all unchanged from S2-C. (3) LIVE BUILDERS — `build_candidate_product_evidence_v2` / `build_candidate_commercial_evidence_v2` (pure over `ListingObservation`; published fields only; title as raw text; explicit UNAVAILABLE packaging) and `build_semantic_match_case_v2` gains the EXPLICIT `reviewed_target_context` keyword (no silent default); the SAFE authority-side builder `build_v2_product_evidence_profile` is UNCHANGED (frozen S2-A signature; the live path still passes matched_facts=frozenset() — the audit proves the main flow grounds no bounded identity-dimension equality; observation evidence can never become authority). (4) 4D-D TARGET CONTEXT WIRING — NEW `reviewed_target_context_from_alias_result` in the V2 execution wiring (deterministic over the ESTABLISHED result's own re-verified fields; non-ESTABLISHED -> explicit None; an ESTABLISHED result missing a reviewed field fails closed; a corrupted ESTABLISHED result cannot exist through the result's own self-validation, the check is defense in depth); the orchestration carries it into `evaluate_semantic_matches_v2` (new EXPLICIT keyword) for every V2-eligible candidate of the run. (5) PROMPT V2 CORRECTED (version stays 2.0 — pre-freeze, per (1)) — the system prompt gains the EVIDENCE CLASSES rules (STRUCTURED FACT vs RAW OBSERVATION TEXT vs COMMERCIAL/PACKAGING EVIDENCE vs REVIEWED TARGET CONTEXT vs AUTHORITY-SIDE PRODUCT EVIDENCE; absence of packaging evidence is NOT proof of equal sales unit and never read as "single unit"; no packaging value inferred from price; a raw-text token is not a structured fact and raw text never becomes manufacturer authority; absence of a structured fact does not erase raw observation evidence; never manufacture a missing fact; UNPROVEN sales unit + otherwise-matching evidence -> missing_critical_attributes + UNCERTAIN_MISSING_CRITICAL_ATTRIBUTES); the user prompt renders the corrected sections (structured facts with source labels or explicit absence; raw title / specification text under the raw label; commercial facts + the explicit sales-unit state; the reviewed target context labeled STRUCTURED/REVIEWED / target-side only / zero identity authority). (6) PERSISTENCE/REPLAY — the V2 codec's case section is corrected to the exact new shape (strict key sets; unknown enums / invented evidence sources / invalid sales-unit cross-states / tampered reviewed context all fail closed; a pre-FU1-shaped payload is never silently reinterpreted); the V2 run-binding check reads the corrected target section; the V1 adapter / V1 payload bytes / V1 replay are byte-untouched; no migration. (7) TESTS — the flawed motivating node `test_the_input_carries_the_structured_evaluation_context` is CORRECTED IN PLACE as `test_the_input_carries_the_corrected_evidence_contract` (it no longer claims title tokens are structured evidence; it proves: raw title reaches the model labeled raw; structured product dimensions are explicit absences; packaging is explicitly UNAVAILABLE (the fixture's only commercial fact is a price); the absence renders with the never-infer rule — customer-relation retrieval-only, the U5/NM-1 ceiling, and the no-Machine-Price-contamination proofs are the unchanged adjacent nodes); NEW `tests/research/test_semantic_v2_input_evidence.py` (27: the 20 mandated input-evidence properties + the reviewed-target-context contract incl. the 4D-D helper over the real recorded catalog fixture); +8 prompt evidence-class nodes, +11 codec nodes (packaging single-unit / pack-quantity / bundle / tray round-trips if observed; UNAVAILABLE default; reviewed-context round-trip + zero-live replay; pre-FU1-shape refusal; legacy 'specs' key refusal; invalid cross-state / unknown-source / unknown-relation-kind refusal), +1 full-orchestration motivating node (the ESTABLISHED 4D-D context reaches the recorded V2 input; candidate packaging stays UNAVAILABLE; derived snapshots unchanged); mechanical shape corrections in the S2-C test helpers (the corrected builder signature / case shape) preserving every safety assertion; the package-export pins gain the FU1 surface (strengthened). No test deleted/renamed/skipped/xfail/deselected/ignored; no file decreased; the known Windows/Python-3.14 subprocess flake allowlist NOT expanded. Collection 6528 -> 6575 (+47; no decrease). | The S2-C review blocker: richer MODEL-OBSERVATION input is required before the Semantic V2 contract can be declared FINAL — the model must receive the best SAFE product and commercial evidence already in the system, with explicit structure and provenance, while the AUTHORITY-side ProductEvidenceProfileV2 stays independently grounded (the model must never bootstrap authority from its own output). The correction is an input-contract fix on the unshipped pre-freeze candidate: no authority rule moves (S2-A frozen; the live path still grounds zero matched facts — the audit proves why), no packaging value is ever inferred, and the motivating case is documented honestly (raw title evidence; explicit packaging absence; reviewed target context from the ESTABLISHED 4D-D acquisition, zero identity authority). | IMPLEMENTED / PENDING FINAL REVIEW (PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-S2-C-FU1); AMENDS IN PART AD-070 (the pre-freeze S2-C candidate) |
| AD-072 | SEMANTIC-AUTHORITY-V2-Q3-A qualification V3: independent corpus, harness, and offline qualification (canonical spec §26.28): on the authoritative starting SHA `cf51a23e31d175cc9e6759d12f97171769db87e5` (S2-C-FU1 endpoint, now APPROVED / FROZEN per the Q3-A operator briefing; baseline collection 6575), the independent, deterministic, OFFLINE qualification system for the exact frozen Semantic V2 contract is built. NO live model qualification is executed in Q3-A and NO frozen production artifact changes (the S2-C / S2-C-FU1 prompt 2.0, input contract, output contract, reason codes, eligibility, S2-A authority matrix, persistence adapter, and runtime route are byte-untouched; `V2_AUTHORITY_QUALIFIED` stays False; no deployment). (1) CORPUS - NEW `evaluation/semantic_v2_qualification/` (data outside the Python package, the 0B precedent): `corpus_v1.json` (version 1.0.0, schema v1, 56 cases; digest `2c37ba088c317d8cefc6ad0dd7e0d73cfd085f6474ef43eb6953e3cf0170b549`): 43 semantic (36 AUTHORITATIVE + 7 AMBIGUOUS) + 13 CONTRACT_NEGATIVE across 5 categories, covering all seven frozen uncertain state/substate combinations and every mandated adversarial shape; the motivating Micron case (target MTFDKCC3T8TGP-1BK1DABYYR vs candidate MTFDKCC3T8TGP-1BK1DABYY, U5/NM-1, recorded 4D-D reviewed target context + customer-retrieval relation) is RECORDED_FIXTURE and expected UNCERTAIN with PACKAGING_QUANTITY missing and commercial_sales_unit_safety=true (the truncated form is the exact recorded-catalog part; the R/T relation is customer-defined - no manufacturer document states what R denotes; the pair is NOT labeled equivalent for sharing a base identifier). Every case: stable id, category, the EXACT frozen V2 input payload (SemanticMatchCaseV2.canonical()), derived substate/primary signal, expected decision (+ acceptable set for ambiguous), expected conflict classes, expected missing-critical dimensions, advisory reason code, the sales-unit-safety flag, bounded label source kind + citation + independent evidence, reviewer identity/status, ambiguity class, case digest. SYNTHETIC vs RECORDED_FIXTURE labeled; REAL_MARKET reserved (loader rejects it). (2) INTEGRITY - canonical serialization (sorted keys, compact, ASCII, no floats) + SHA-256 per case and over the state view; a label change MUST change the digest and create a label_revisions entry with the bounded reason class (A/B/C/D - "the new implementation failed this case" is not a class); the auditable source is `product_intelligence/evaluation/semantic_v2/fixtures.py` (declarative cases over the EXACT frozen chain with a substate self-check; regeneration must reproduce the corpus byte-for-byte); the strict loader mechanically rejects label text naming model output or a candidate model (ground truth is never derived from the system under test; the generator never reads captures); reproducible `manifest_v1.json`. (3) HARNESS - NEW `product_intelligence/evaluation/semantic_v2/`: `corpus.py` (strict loading + typed reconstruction through the REAL constructor + bounded rejection classes NON_UNCERTAIN_STATE / INVALID_INPUT_SCHEMA / FOREIGN_DETERMINISTIC_CONTEXT / UNSUPPORTED_EVIDENCE), `capture.py` (the captured-response artifact for the later live phase: schema v1, bound to the exact corpus digest + frozen prompt 2.0 + contract V2; attempts mirror the frozen runtime discipline with drift-pinned mirrors; a record for a contract-negative case is a schema-bypass attack; one RUN projected per model), `evaluator.py` (deterministic zero-network zero-AI evaluation through the PRODUCTION parser - parse_semantic_response_v2 + validate_semantic_response_v2, no recreation; per-case states EVALUATED / NOT_CAPTURED / NOT_INVOKED / RUNTIME_FAILURE / CAPTURE_INTEGRITY_FAILURE / CONTRACT_REJECTED_OK / CONTRACT_VIOLATION; never substitutes an expected answer for an invalid response; never manufactures a response), `gates.py` (the eight mandatory hard safety gates + fail-closed decision), `policy.py` + the DRAFT policy artifact (proposed thresholds: match precision >= 0.99, recall >= 0.90, valid response rate >= 0.99, eligible coverage >= 1.00 - DRAFT, NOT finalized production acceptance thresholds), `report.py` (the reproducible report bound to corpus digest / contract binding / REAL system-prompt digest / runtime configuration identity / capture provenance; grants no authority; verify_report fails closed against a mutated corpus), `cli.py` (offline commands; no research import). (4) PRIMARY/FALLBACK INDEPENDENCE - a capture records one run; the primary view counts a fallback-answered case as its own execution failure; the fallback view counts a primary-answered case as NOT_INVOKED; metrics/gates/coverage/decision are computed separately per provider/model; a primary PASS never qualifies the fallback. (5) METRICS/SEVERITY - separate per model (all mandated metrics including false-MATCH examples with case ids, performance by substate and category, runtime failures by bounded status, provenance per case); ambiguous cases visible but excluded from hard accuracy; contract-negative scored on rejection correctness; zero-denominator metrics reported unavailable (never 0/100%); severity deterministic and label-driven (CRITICAL = false MATCH on independently established ALWAYS_HARD conflict or sales-unit safety; HIGH = other false MATCH; MEDIUM = false NO_MATCH on expected MATCH; REVIEW = abstention on definite / outside an ambiguous defensible set; model confidence never overrides the label). (6) DECISION - precedence NOT_QUALIFIED (safety, even with high accuracy, even while the policy is pending) > POLICY_PENDING (no approved policy - the Q3-A final state) > INCOMPLETE_COVERAGE > BELOW_THRESHOLD / THRESHOLD_INDETERMINATE > QUALIFIED (unreachable in Q3-A); a void evaluation is FAIL_CLOSED with an explicit fail-closed report. (7) BASELINE - committed no-capture reports for both pinned route candidates (43/43 NOT_CAPTURED, 13/13 contract-negative rejected as expected, all gates pass, POLICY_PENDING; reproducible by test). (8) BOUNDARY - the A1-FU2 evaluation->research exact-allowlist mechanism extended by EXACTLY SIX named harness files (corpus / fixtures / capture / evaluator / gates / report); canonical / policy / cli / __init__ stay research-independent; the A1-FU2 entry remains exactly one file; no execution / runs / web / providers / Django / aggregation / review / price surface imported; the live transport is never imported during offline replay (socket-blocked test). (9) TESTS - 132 new nodes in `tests/evaluation/semantic_v2/` covering all 36 mandated properties plus the anti-manipulation proofs (changing expectations to fit model output changes the digest, stops the historical report from verifying, and leaves the capture unable to follow the revision; an unsealed label edit is rejected on load; the corpus generator never reads captures); `test_only_promotion_regression_may_wire_research` corrected in place for the second exact allowlist (safety property preserved and strengthened; the A1-FU2 one-file pin unchanged); new `test_qualification_v2_exception_is_an_exact_allowlist` locks the Q3-A set. No test deleted/renamed/skipped/xfail/deselected/ignored; no file decreased; the Windows subprocess flake allowlist NOT expanded. Collection 6575 -> 6748 (+173 = 132 new + 40 auto-expanded parameterized scans for the 10 new evaluation files + 1 new mechanism node). | Q3-A is the first Qualification V3 sub-phase: it must make the frozen Semantic V2 contract MEASURABLE before any model is measured - an independent digest-sealed corpus with provenance-governed labels, a reproducible offline harness that uses the real frozen prompt/parser (never a recreation), fail-closed safety gates that high aggregate accuracy cannot mask, and an explicit POLICY_PENDING boundary so no qualification claim can be made without an approved policy and captured responses. Live capture (Q3-B) and the qualification decision (Q3-C) are explicitly OUT of scope. | IMPLEMENTED / PENDING FINAL REVIEW (PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-A); RECORDS THE S2-C / S2-C-FU1 APPROVAL (the frozen contract under qualification is the corrected S2-C-FU1 candidate: binding ("V2", "2.0", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU2"), prompt 2.0) |
| AD-073 | SEMANTIC-AUTHORITY-V2-Q3-A-FU1 independent model qualification capture (canonical spec §26.29): bounded CAPTURE-ARCHITECTURE corrective follow-up on the reviewed Q3-A candidate (AD-072), on the authoritative starting SHA `8435864e7517c17843a7406a79de4c819a6ef2fa` (Q3-A endpoint; baseline collection 6748). Q3-A is recorded as REVIEWED / NOT APPROVED / NOT FROZEN; the review blocker is corrected here. BLOCKER: the Q3-A capture contract is one production run of the frozen pinned route (primary attempt; fallback only after an eligible primary EXECUTION failure), so a normal run finalizes every case on the primary's success and the fallback view of that run is all NOT_INVOKED - a single production-route capture structurally cannot provide full qualification coverage for BOTH models independently. The fix does NOT manufacture primary failures and does NOT change production fallback behavior. DELIVERED (offline infrastructure only - NO live model calls; the controlled capture runner is Q3-B): (1) TWO EXPLICITLY DISTINCT, VERSIONED CAPTURE MODES as SEPARATE typed documents (never one ambiguous structure): Mode A PRODUCTION_ROUTE = the existing `capture.py` schema v1, unchanged and still readable (primary first; fallback on eligible primary execution failure only with the frozen reason mapping; a successful primary finalizes the route; NOT_INVOKED semantics retained; the report's capture section now explicitly identifies `capture_mode: PRODUCTION_ROUTE` + schema version - additive identity fields, no committed artifact affected); Mode B DIRECT_MODEL_QUALIFICATION = NEW `product_intelligence/evaluation/semantic_v2/direct_capture.py` (`direct_capture_schema_version: 1`): each capture targets EXACTLY ONE pinned provider/model (amax/qwen3.8-27b or vllm-262k/Qwen3.6-27B-262K - wrong/unknown/mixed identities fail closed; no other model may enter the frozen V2 qualification), every eligible semantic case is that model's own single bounded execution (one execution_status from OK + the frozen runtime execution-failure vocabulary; raw_output iff OK), NO primary-before-fallback requirement, NO artificial primary failures, NO production routing, NO production execution or pricing authority; model identity bound to the document and each record's interpretation; exact frozen corpus id/version/digest + semantic contract V2 + prompt 2.0 preserved; distinct run id + provenance per capture; duplicate case IDs / unknown case IDs / contract-negative records (schema-bypass attack) / corpus / prompt / contract mismatches all fail closed; missing eligible cases are NOT a load error (they surface as NOT_CAPTURED - a coverage shortfall, never a pass). (2) BACKWARD COMPATIBILITY: cross-mode decoding fails closed in both directions (the production loader refuses direct documents on the exact key sets; the direct loader refuses production documents with an explicit cross-mode error; hybrids are refused by both); old captures are never reinterpreted or migrated; historical production-route report identity is preserved. (3) INDEPENDENT DIRECT-MODEL EVALUATOR (NEW `evaluate_direct_for_model` in `evaluator.py`; never imports or invokes the production orchestration path - mechanically verified): verifies exact provider/model identity, corpus id/version/digest, semantic contract V2 + prompt 2.0, every case id (duplicates rejected at load, unknown / contract-negative rejected at corpus verification), fails closed (QualificationContractError) on any mismatch including cross-mode artifact presentation (typed guards in BOTH evaluators); per-case states EVALUATED (OK + parser-valid) / RUNTIME_FAILURE (bounded status preserved separately) / NOT_CAPTURED (no record) / CAPTURE_INTEGRITY_FAILURE (OK but the raw output does not survive the parser - never substituted with the expected answer); reuses the FROZEN production V2 parser composition UNCHANGED (parse_semantic_response_v2 + validate_semantic_response_v2 via classify_raw_response) and the same label-driven scoring / severity / metric surface; NO NOT_INVOKED state; complete direct-model qualification requires all 43 eligible semantic cases to have an accepted parser-valid response, satisfied independently by primary and fallback; the two modes' coverage denominators are never mixed (a full direct fallback capture is 43 evaluated / 0 NOT_INVOKED while the same model's production-route view of a primary-answered run stays 0 evaluated / 43 NOT_INVOKED). (4) SAFETY AND DECISIONS: the eight MANDATORY hard safety gates and the fail-closed decision vocabulary (FAIL_CLOSED / NOT_QUALIFIED / POLICY_PENDING / INCOMPLETE_COVERAGE / THRESHOLD_INDETERMINATE / BELOW_THRESHOLD / QUALIFIED) are unchanged and work identically in both modes (gate-for-gate equality proven, incl. the input-aware authority-promotion cross-check); the qualification policy remains DRAFT, so no QUALIFIED result is produced under it (full correct direct captures stay POLICY_PENDING); V2_AUTHORITY_QUALIFIED remains False; no Machine Price / Reviewed Price / human-review authority change. (5) REPORTING: NEW `build_direct_report` / `verify_direct_report` (report kind SEMANTIC_V2_DIRECT_MODEL_QUALIFICATION_OFFLINE) explicitly identifying capture mode, capture schema version, provider/model (bound target), corpus identity + digest, frozen contract/prompt identity (real system-prompt digest), capture run id + provenance, evaluation timestamp, and the direct coverage facts (eligible/evaluated/not-captured/runtime-failure/invalid-response counts WITH case ids + completeness flag), per-substate / per-category performance, false-MATCH case IDs, the eight gate results, the policy status (DRAFT), and the decision; each mode's verifier REFUSES the other mode's reports (cross-mode kind check, fail closed); production-route build_report content is unchanged and the committed no-capture baseline reports (both pinned candidates) remain BYTE-IDENTICAL to what the unchanged pipeline reproduces (JSON + Markdown, proven by test); the two modes' reports are never silently combined. (6) CLI: NEW `evaluate-direct` command (one report per pinned model per direct capture; void evaluations emit an explicit FAIL_CLOSED direct-kind report); the existing `evaluate` command (production-route mode + no-capture baseline) is unchanged in behavior. (7) BOUNDARY (preserved, strengthened): the new `direct_capture.py` is RESEARCH-INDEPENDENT (it re-imports the frozen route/contract pins from the allowlisted `capture.py` - the house least-privilege pattern), so the Q3-A evaluation->research exact allowlist remains EXACTLY THE SAME SIX FILES (no new exception; no prefix/glob/regex); the Q3-A mechanism test `test_qualification_v2_exception_is_an_exact_allowlist` is STRENGTHENED in place (strictly additive: `direct_capture.py` pinned as a non-allowlisted module that must exist and remain research-independent). (8) TESTS: 76 NEW nodes in `tests/evaluation/semantic_v2/` (test_q3a_fu1_direct_capture.py 35; test_q3a_fu1_direct_evaluation.py 19; test_q3a_fu1_qualification.py 12; test_q3a_fu1_reports.py 10; + shared _q3a_fu1_helpers.py fixture writer - declared test fixtures, not model output) covering all 32 mandated properties: production-route captures still readable / fallback never after primary success / fallback execution-failure-only; independent direct primary + fallback captures with no fake primary failure; cross-mode decode + evaluation fail closed; wrong / unknown / mixed provider-model fail closed; duplicate / unknown case IDs; contract-negative responses; corpus digest / prompt / contract mismatches; missing / runtime-failure / invalid responses cannot PASS; primary qualification does not qualify the fallback (and vice versa); independent denominators (NOT_INVOKED production-only); production parser reused without approximation (case-for-case outcome equality across modes); false-MATCH gates identical in both modes; synthetic labels stay synthetic; the Micron case unchanged (UNCERTAIN expected; a direct MATCH is CRITICAL in both modes); no production execution imports (AST + module-state proof); no network / model calls (socket-blocked); historical baseline reports byte-identical; policy remains DRAFT; V2_AUTHORITY_QUALIFIED remains False; no pricing / review authority tokens. No test deleted/renamed/skipped/xfail/deselected/ignored/weakened; no file decreased; the Windows subprocess flake allowlist NOT expanded. Collection 6748 -> 6828 (+80 = 76 new-file nodes + 4 auto-expanded parameterized scans for direct_capture.py [vendor-token +1, stdlib-imports +1, no-outer-layer +1, providers INNER_ROOTS +1]). | Q3-A review found the qualification harness attempts to qualify both models independently from the SAME production-route capture, but a normal run cannot contain full fallback coverage: the successful primary finalizes each case before the fallback is invoked, so the fallback view is NOT_INVOKED for those cases. Qualifying the fallback (or the primary, from a fallback-answered run) therefore required either waiting for real primary failures in production or manufacturing them - both unacceptable (the harness must not simulate production failures to manufacture qualification data, and production fallback behavior must not change). Independent per-model direct captures are the honest benchmark shape: each pinned model is measured on its own execution of every eligible case against the exact frozen prompt/input/contract, with the same fail-closed gates and the same corpus ground truth; production-route captures keep their meaning as production evidence. Separate typed schemas (not optional fields on one document) keep the two modes unambiguous and preserve historical capture / report identity. | IMPLEMENTED / PENDING FINAL REVIEW (PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-A-FU1); RECORDS THE Q3-A REVIEW STATE (REVIEWED / NOT APPROVED / NOT FROZEN; the independent-qualification-coverage blocker is corrected in part by FU1 - the frozen Semantic V2 production contract, the corpus, the DRAFT policy, and V2_AUTHORITY_QUALIFIED = False are all unchanged) |
| AD-074 | SEMANTIC-AUTHORITY-V2-Q3-B controlled live direct-model capture (canonical spec §26.30): bounded LIVE-QUALIFICATION-EVIDENCE phase on the authoritative starting SHA `517ef25c7ce83bba364234dda46270b147c0c053` (Q3-A-FU1 endpoint; baseline collection 6828). Q3-A and Q3-A-FU1 are recorded as APPROVED / FROZEN per the Q3-B operator briefing, so the frozen DIRECT_MODEL_QUALIFICATION capture schema (AD-073) and its independent offline evaluator / report path are the contract this phase executes against. THIS PHASE COLLECTS EVIDENCE ONLY: it grants no qualification, no pricing authority, and no human-review authority; the qualification policy stays DRAFT; V2_AUTHORITY_QUALIFIED stays False; the decision stays POLICY_PENDING (at best). NO frozen production artifact changed (prompt 2.0, input / output schema, reason codes, eligibility, authority matrix, persistence adapter, runtime route, corpus labels, DRAFT policy byte-untouched; corpus digest unchanged `2c37ba08...0b549`; no migration; no deployment). DELIVERED: (1) SEPARATE BENCHMARK-ONLY LIVE CAPTURE RUNNER - NEW `product_intelligence/evaluation/semantic_v2/live_capture.py` (research-independent: the frozen route / contract pins are re-imported from the allowlisted capture.py / direct_capture.py; the Q3-A evaluation->research exact-allowlist remains EXACTLY THE SAME SIX FILES): one run targets EXACTLY ONE frozen pinned identity (amax/qwen3.8-27b or vllm-262k/Qwen3.6-27B-262K - unknown / mixed / whitespace identities fail closed), executes ALL 43 eligible semantic cases (the 13 CONTRACT_NEGATIVE cases are never rendered into a prompt, never sent, never recorded), and writes the approved Q3-A-FU1 DIRECT_MODEL_QUALIFICATION capture document (unchanged schema v1 - self-verified through load_direct_capture / verify_direct_capture_against_corpus after writing) + a runner manifest sidecar (run identity, fixed retry policy, bounded per-case attempt evidence, per-case prompt digests, REAL system-prompt digest, git HEAD, key presence as a bare bool; evidence only - the evaluator never reads it). It reuses, never recreates: the frozen production V2 prompt builder (semantic.contract_v2.build_semantic_prompt_v2 over the REAL typed corpus case), the frozen production V2 parser composition (evaluator.classify_raw_response = parse_semantic_response_v2 + validate_semantic_response_v2, identity-first then parse then validate - the production runtime boundary discipline), and the approved provider transport / configuration mechanism (semantic.transport.get_openai_transport_for_provider, imported LAZILY inside transport construction only - module import loads no network client; no os.environ read outside the transport adapter). No production orchestration is imported or invoked (no execution / runs / web / providers / framework surface; AST + module-state proven); no general-purpose autonomous agent. (2) BOUNDED ENVELOPE - request timeout bounded (default 300.0 s, hard bound 3600.0 s - mirrors of the frozen runtime bounds, drift-pinned; non-finite / non-positive / out-of-bounds fail closed) and reaches the transport; concurrency bounded (default 1, hard bound 4, recorded; records stay in corpus order under concurrency); generation parameters are the frozen pins (temperature exact float 0.0, max_tokens 32768 - NOT caller-configurable, drift-pinned to production); the transport classification table is a drift-pinned mirror of the frozen V2 runtime's. (3) FIXED RETRY POLICY (documented in the module + every manifest; no retry decision ever reads the label) - retryable (no model output, transient transport condition, identical request, at most max_attempts=3 total): TIMEOUT / DNS_ERROR / TLS_ERROR / CONNECTION_ERROR / RATE_LIMITED / PROVIDER_UNAVAILABLE; final after exactly one call (never retried, never cherry-picked): OK / HTTP_ERROR / EMPTY_RESPONSE / MALFORMED_JSON / SCHEMA_INVALID / INVALID_RESPONSE / MODEL_IDENTITY_MISMATCH; run-level abort after recording the attempted case: AUTHENTICATION_FAILED / MODEL_NOT_FOUND / INVALID_REQUEST_CONFIGURATION / UNSUPPORTED_PARAMETER / unrecognized transport code (no document for out-of-vocabulary evidence - manifest only); CASE_REJECTED stays CASE-LOCAL (run continues; manifest-documented; no document record; replays NOT_CAPTURED - never a pass). (4) CREDENTIALS / SAFETY - no key, base URL, Authorization header, or credential value is hardcoded, printed, or written to any artifact (proven by sentinel-value tests); an unconfigured provider fails closed BEFORE any network call (bounded error, no artifact); the frozen Semantic V2 runtime is unmodified. (5) OFFLINE REPLAY - each model's document replays through the UNCHANGED evaluate_direct_for_model + gates + policy + decide + build_direct_report / verify_direct_report path (`evaluate-direct` CLI): separate reports per model with coverage / valid-response rate / MATCH precision-recall / false-MATCH case ids / HARD_CONFLICT + packaging + accessory + near-miss errors / ambiguous behavior / runtime failures / per-category + per-substate metrics / the eight safety gates / DRAFT policy / decision (POLICY_PENDING at best). (6) EVIDENCE INTEGRITY - artifacts stored separately from the corpus labels (runner-managed directory, gitignore-protected, never committed alongside labels); expected labels never modified from model responses; reports bound to corpus digest + REAL system-prompt digest + contract version + provider/model + capture run id + evaluation timestamp; append-only artifacts (existing paths are never overwritten); a missing or incomplete capture never becomes PASS. (7) CLI - `python -m product_intelligence.evaluation.semantic_v2.live_capture capture` (--provider/--model validated against the frozen pins; --dry-run = full offline preflight, no transport, no call, no artifact); the offline `cli.py` is unchanged. (8) TESTS - 80 NEW nodes in NEW `tests/evaluation/semantic_v2/test_q3b_live_capture.py` (every model call is a scripted, recording test double; the full pipeline re-proven under a blocked socket): exact model pinning; frozen prompt fidelity; transport boundary (lazy import + approved mechanism + unconfigured fail-closed + no own env read); no credential leakage; timeout handling; bounded retry; no semantic-error retries; no best-of-N; no contract-negative model calls; complete eligible-case traversal; failure preservation; independent model capture; capture schema validation; offline replay fidelity; no production execution imports; no authority promotion; no pricing contamination; no network calls during ordinary unit tests; bounded concurrency. The Q3-A / Q3-A-FU1 guards are STRENGTHENED in place (strictly additive): the offline names-no-AI-surface guard now pins live_capture.py as the ONE module that may reference the live transport surface; the direct-model AST guard pins its transport reference as exactly ONE lazy function-level import of the approved factory (module-level transport import impossible; the production runtime module still forbidden). No test deleted/renamed/skipped/xfailed/deselected/ignored/weakened; no file decreased; the Windows subprocess flake allowlist NOT expanded. Collection 6828 -> 6912 (+84 = 80 new-file nodes + 4 auto-expanded parameterized scans for live_capture.py [vendor-token +1, stdlib-imports +1, web inner-layer +1, providers INNER_ROOTS +1]). (9) LIVE EXECUTION (this session, per the operator briefing) - the primary (amax/qwen3.8-27b) live capture was executed on the configured endpoint under the fixed policy; the fallback (vllm-262k/Qwen3.6-27B-262K) endpoint is NOT configured in this environment and the runner failed closed at preflight with the bounded PROVIDER_NOT_CONFIGURED classification (no network call, no artifact) - its live capture is deferred to the session where the endpoint is available; the session evidence (coverage, retries, replay reports) is recorded in the STATUS Q3-B section. | Q3-A-FU1 (AD-073) built the capture schema + offline evaluator and explicitly deferred the controlled live runner to Q3-B. Q3-B is that deferred runner: it must collect REAL per-model evidence on the exact frozen prompt / corpus / contract with a FIXED, documented, bounded retry policy and a lazy reuse of the approved transport - while provably touching no production orchestration, no authority, no pricing, no labels, and no secrets. The runner is benchmark-only by construction (one pinned model per run, no routing, no manufactured failures), and the evidence stays fail-closed: an incomplete capture or a DRAFT policy can never become a qualification. | IMPLEMENTED / PENDING FINAL REVIEW (PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-B); RECORDS THE Q3-A + Q3-A-FU1 APPROVAL (APPROVED / FROZEN per the Q3-B operator briefing; the frozen Semantic V2 production contract, the corpus, the DRAFT policy, and V2_AUTHORITY_QUALIFIED = False are all unchanged) |

## 26. Customer Quote Research Expansion — 4D Phase Architecture

**Status: IMPLEMENTED / APPROVED / FROZEN / COMPLETE**

4D-PRE — APPROVED / FROZEN (Preferred Source Feasibility Audit, evidence only)
4D-A — APPROVED / FROZEN (Source Acquisition Optimization)
4D-B — APPROVED / FROZEN (Internal Vendor Commercial Evidence)
     Frozen SHA: c74c90b0590d1c393419d94a1c107bfe93f7143c
     Frozen baseline: 4299 collected
4D-C-A — APPROVED / FROZEN (ECB FX + Compact Quote Projection Foundation)
     Frozen SHA: 059ade96ff2141684b973e576adcc91a10094707
     Frozen baseline: 4582 collected
4D-C-SEC — APPROVED / FROZEN (Vendor Commercial Price Access Gate)
     Frozen SHA: 75bfbe3d1b4a8abc12d655cc903298f08e06a8f0
     Frozen baseline: 4693 collected
4D-C — APPROVED / FROZEN (Compact Quote Summary — browser rendering)
     Frozen SHA: 4592b8966b703dfd6a72c3067d7b191314ff2968
     Frozen baseline: 4766 collected
4D-D-PRE1 — APPROVED / FROZEN (early feasibility review; binding conclusion
     at the time: NO CURRENT 4D-D ELIGIBILITY AUTHORITY EXISTS)
4D-D-PRE2 — APPROVED / FROZEN (Micron official authority evidence capture;
     evidence SHA 1cb65a3d6002006af9e1c77906a6de6b5a3fd42c)
4D-D — APPROVED / FROZEN (Micron Packaging Alias Retrieval, incl. 4D-D-FU1;
     v1 scope: Micron 7500 SSD ONLY)
     Frozen SHA: 065320180c17b89c7460164326a0c9f49e01fe3b
     Frozen baseline: 5097 collected
     Final acceptance: 5097 passed, 0 failed, 0 skipped, 0 xfailed,
     0 deselected (+ 39 subtests passed)

Note: 4D-C security gate (trusted network/VPN access control) is resolved by
the frozen 4D-C-SEC REMOTE_ADDR-only access policy. Report UUID is not access
control.

The complete 4D phase is closed. PRODUCT-INTEL.PILOT-RELEASE-2 — 4D
Customer Requirement Deployment & UAT — is DEPLOYED / ACCEPTED: the
already-frozen 4D customer requirements are deployed to the internal
production/pilot Windows server (deployed runtime SHA
065320180c17b89c7460164326a0c9f49e01fe3b — the independently reviewed
and frozen PRODUCT-INTEL.4D-D-FU1 runtime SHA; deployment is Git-managed
and exact-approved-SHA based), migrations through
0010_research_micron_alias_snapshot are deployed, and the production
smoke test passed on 2026-09-23. It was a deployment/UAT phase, not a
feature-development phase. The later commits c6ad6ae and 7ff0ab7 are
docs-only project-state closures; production does not need to move
merely to obtain those documentation edits, and 7ff0ab7 is not the
production runtime SHA. The 8A (Caching & Freshness) series then
proceeded: PRODUCT-INTEL.8A-PRE — Caching & Freshness Architecture
Audit (READ-ONLY / DESIGN-FIRST) is APPROVED / COMPLETE — it recorded
the caching/freshness architecture before any caching implementation and
itself authorized NO implementation and NO TTL values; the 8A-FX design
lineage (8A-FX-DESIGN, 8A-FX-DESIGN-FU1) is APPROVED / FROZEN as
design; and PRODUCT-INTEL.8A-FX-A1 — Canonical ECB Observation Cache
(the first safe caching slice; §26.18; AD-064) is IMPLEMENTED /
PENDING FINAL REVIEW. 5A remains PLANNED / NOT IMPLEMENTED /
NON-BLOCKING, and 8B/8C remain later planned (directional; not an
approved implementation order); none of them is NEXT.

### 26.0 Overview

PRODUCT-INTEL.4D extends the deployed pilot to incorporate customer-pilot
requirements around quote research, vendor commercial pricing, compact
presentation, currency conversion display, and Micron packaging alias
retrieval.

It is structured as five sub-phases, each with a specific purpose, boundary,
and non-goal. None of them reopens frozen phases. No frozen phase boundary is
weakened.

```
4D-PRE  Preferred Source Feasibility Audit  (evidence only, no production change)
4D-A    Source Acquisition Optimization
4D-B    Internal Vendor Commercial Evidence
4D-C    Compact Quote Summary
4D-D    Micron Packaging Alias Retrieval
```

### 26.1 4D-PRE — Preferred Source Feasibility Audit

**Purpose:** Audit the customer's 12 preferred public websites to determine
per-site acquisition viability, data quality, and whether direct lookup can
reduce Serper credit usage.

**Scope:** Evidence collection only. No production code, no tests, no
architecture change.

**The 12 preferred sites:**

cdw.com, newegg.com, serversupply.com, harddiskdirect.com, esaitech.com,
serverorbit.com, directmacro.com, dihuni.com, centralcomputer.com,
memory4less.com, fs.com, naddod.com


**Configuration:**

```
Planned server-side environment variable:
    PI_PREFERRED_SEARCH_DOMAINS

Current customer value:
    cdw.com,newegg.com,serversupply.com,harddiskdirect.com,esaitech.com,serverorbit.com,directmacro.com,dihuni.com,centralcomputer.com,memory4less.com,fs.com,naddod.com
```

This affects acquisition preference only. It grants no source or identity
authority.

**Per-site audit fields:**

| Field | What it records |
| --- | --- |
| source / domain | The hostname being audited |
| direct lookup mechanism | Stable URL pattern or search entry point |
| tested search shape | Query form used to find a known MPN |
| stable product URL? | Does the same MPN resolve to the same URL? |
| static HTML? | Returns structured product data via plain HTTP? |
| JS required? | Requires client-side rendering for product data? |
| bot / blocking behavior | 403, CAPTCHA, interstitial, rate limit? |
| explicit MPN evidence? | MPN published as a structured field? |
| price? | Price visible and structured? |
| currency? | Currency published? |
| availability? | Stock status visible and structured? |
| condition? | NEW / USED / REFURBISHED published? |
| source-specific extraction needed? | Does the generic 3A path produce usable observations? |
| recommendation | DIRECT / SERPER_FALLBACK / UNSUITABLE |
| evidence / notes | Free-text findings |

**Non-goals:**
- No production code
- No scraping infrastructure
- No headless browser or scraping infrastructure acquired, installed, or
  implemented. 4D-PRE may *record* that a site requires JavaScript rendering.
  Whether browser support is justified is a later 4D-A design decision based on
  the completed audit evidence.
- No per-site adapter written in 4D-PRE

### 26.2 4D-A — Source Acquisition Optimization

**Intent:** Use direct source lookup where 4D-PRE evidence proves it reliable.
Serper becomes fallback rather than unconditional discovery dependency.

**Architecture decisions:**

- Direct-source results flow through the **existing** fetch/extract/normalize/
  deterministic-identity/semantic-assist authority boundaries. They do not
  bypass any frozen step.
- Preferred source status affects acquisition **priority only**.
- Preferred source status **NEVER grants identity authority.**
- No headless-browser or scraping infrastructure unless later evidence justifies it.
- Provider-cost reduction is an explicit goal.
- No arbitrary fallback trigger (e.g. "3 results means skip Serper") is frozen
  at this stage; the exact trigger is a 4D-A design decision after 4D-PRE
  evidence exists.

**Non-goals:**
- 4D-A does not by itself authorize another generic metered web-search provider.
  Evidence-backed direct-source/site adapters may be introduced behind the
  provider boundary when 4D-PRE demonstrates a stable mechanism.
- Not a bypass of frozen identity or authority contracts
- Vendor/site-specific transport logic must not leak into research core or web
  presentation

### 26.3 4D-B — Internal Vendor Commercial Evidence

**Intent:** Integrate the customer's internal vendor lookup API as a
structured commercial evidence source.

**Vendor API:**

```
configured via environment:
    PI_VENDOR_LOOKUP_BASE_URL

current deployment example:
    http://157.22.244.39:8808/vendor

request form:
    ?partno=<URL-ENCODED-MPN>
```

Known upstream sources: Ingram, CDW, Synnex EU.

This is **structured internal commercial evidence**, not public web search.

**Boundary decision:**

- Introduce a **provider-neutral commercial-source boundary** appropriate to
  structured vendor observations. This does NOT force structured commercial
  data into `SearchProvider` if that contract is semantically wrong.
- Vendor-shaped payloads remain in adapters.
- Core / business logic consumes provider-neutral normalized observations.
- One vendor section failure must not destroy usable other vendor results.
- Whole vendor API failure is supplemental / nonfatal.

**Authority constraints (binding):**

Vendor commercial data **MUST NOT** automatically enter:
- frozen 4A Machine Price
- frozen Reviewed Price
- 2A identity authority
- semantic authority
- comparable scoring

It is **supplemental commercial evidence** unless a later explicit phase
changes that authority contract.

**Condition policy:**

Customer policy: if a vendor API result successfully identifies the requested
product, that vendor API inventory is BRAND NEW.

Represent this as explicit policy provenance:
```
brand_new = true
brand_new_basis = VENDOR_API_POLICY
```

Do NOT fabricate a source-published NEW condition field.

**Known successful payload fields:**

| Source | Fields |
| --- | --- |
| Ingram | `vendorPartNumber`, `pricing.customerPrice`, `pricing.retailPrice`, `pricing.currencyCode`, `availability.available`, `availability.Avl_Quantity` |
| CDW | `manufacturerPartNumber`, `price`, `currencyCode`, `inventoryStatus.stockStatus`, `inventoryStatus.Avl_Quantity` |
| Synnex EU | `OnlineCheck.Header.CurrencyCode`, `OnlineCheck.Item.ManufacturerItemIdentifier`, `UnitPriceAmount`, `AvailabilityTotal`, `Note`; "not maintained in our catalogue" means no usable product |

**Vendor identity binding (binding validation):**

A successful vendor commercial observation requires the vendor's explicit
manufacturer-part-number field to compare against the requested MPN through
the frozen 2A comparator as `EXACT` or `NORMALIZED_EXACT`:

| Source | MPN field |
| --- | --- |
| Ingram | `vendorPartNumber` |
| CDW | `manufacturerPartNumber` |
| Synnex EU | `OnlineCheck.Item.ManufacturerItemIdentifier` |

Mismatch or absent explicit vendor MPN: do not create a normal commercial
product row. This is a binding validation for a supplemental vendor
observation. It MUST NOT promote vendor data into frozen 4A identity authority.

**Vendor price / not-found / inventory contract:**

*Ingram:*
- Primary displayed commercial price: `pricing.customerPrice`
- Fallback only if `customerPrice` absent: `pricing.retailPrice`
- If `customerPrice` used and `retailPrice` present, `retailPrice` may be
  summarized in Note
- Currency: `pricing.currencyCode`
- `available=true` or `Avl_Quantity > 0`, when non-conflicting => `In Stock`
- `available=false` with `Avl_Quantity=0` => `Out of Stock`
- Contradiction or insufficient evidence => `Unknown`
- Not-found response (`{Not Found}`): no row

*CDW:*
- Price: `price`
- Currency: `currencyCode`
- `stockStatus InStock` => `In Stock`
- `stockStatus OutOfStock` => `Out of Stock`
- Contradictory or unknown => `Unknown`
- `Avl_Quantity` may appear in Note
- Not-found response (`{Not Found}`): no row

*Synnex EU:*
- Price: `UnitPriceAmount`
- Currency: `OnlineCheck.Header.CurrencyCode`
- Numeric `AvailabilityTotal > 0` => `In Stock`
- Numeric `0` => `Out of Stock`
- Missing or unparseable => `Unknown`
- Useful bounded note such as "No Returns" may be displayed
- Response containing "not maintained in our catalogue": no row

Vendor API successful identity-bound row:
- `Brand New = Yes`
- `basis = VENDOR_API_POLICY`
- Do NOT fabricate source-published NEW condition evidence.

**Vendor sensitive metadata (binding rule):**

Do NOT persist, render, log into report payloads, or expose through Note/raw
references internal transport/account/session metadata such as:

- `SessionId`
- `BuyerAccountId`
- `SystemId`
- or equivalent credentials/session/account identifiers

Recorded test fixtures in 4D-B must be sanitized.

**Security gate:**

§19 already states that report access control stops being deferrable when
internal commercial pricing enters reports. **4D-B is the phase that triggers
this gate.**

Before 4D-B vendor/customer commercial prices are exposed in the report,
deployment MUST verify or establish trusted-corporate-network / VPN /
approved-subnet access restriction. Current pilot security state is not
claimed to satisfy this gate.

Full application authentication is NOT required for this documentation — 8C
remains the formal production-hardening / authentication phase. Report UUID is
never access control.

### 26.4 4D-C — Compact Quote Summary

**Status: APPROVED / FROZEN (PRODUCT-INTEL.4D-C; frozen SHA
4592b8966b703dfd6a72c3067d7b191314ff2968, frozen baseline 4766 collected).**
Implemented behind the frozen 4D-C-SEC gate: server-side security branch in
`research_detail` selects the frozen 4D-C-A authorized replay (ALLOWED) or
the new public-only replay (DENIED — never reads ResearchSupplementSnapshot)
before any vendor supplemental artifact access; display-only presentation in
`web/compact_quote_presentation.py` renders the table below near the top of
the report, reusing `presentation._is_safe_href_url` for public source links.

**Intent:** Add a compact customer-facing table near the top of Price
Intelligence.

**Table columns:**

| Column | Meaning |
| --- | --- |
| Source | Hostname (web) or vendor name (vendor API) |
| Price | Original price in published currency |
| USD Equivalent | Supplemental display via FX evidence |
| Inventory | Normalized availability |
| Brand New | Condition: Yes / No / Unknown |
| Note | Bounded human-facing note (web and vendor rows) |

**Public web rows:**
- Source displays main hostname, stripping leading `www.`.
- Full safe URL remains link target.
- Existing full evidence / audit sections MUST remain.

**Vendor API rows:**
- Display human names: `Ingram (Vendor API)`, `CDW (Vendor API)`,
  `Synnex EU (Vendor API)`.

**Inventory display:**
- `IN_STOCK` => `In Stock`
- `LIMITED` => `In Stock`, retain `Limited` in Note
- `OUT_OF_STOCK` => `Out of Stock`
- `PREORDER` / `BACKORDER` / `DISCONTINUED` => `Out of Stock`, retain
  specific state in Note
- `UNKNOWN` => `Unknown`
- Do not fabricate a binary result from `UNKNOWN`.
- Web evidence uses existing deterministic normalized availability.
- Vendor API uses explicit provider mapping.

**Brand New:**
- Web evidence: uses existing normalized condition.
  - `NEW` => `Yes`
  - `USED` / `REFURBISHED` / `DAMAGED` => `No`
  - `UNKNOWN` => `Unknown`
- Vendor API successful identity match => `Yes` by explicit `VENDOR_API_POLICY`.

**Note (web and vendor rows):**

Bounded human-facing note. Examples:
- Verified
- AI-assisted HIGH - review required
- Human confirmed
- Excluded - MPN evidence insufficient
- Preferred source
- Vendor API - customer price
- Qty 48
- No Returns

No raw payload or secret/session/account data in Note.

### 26.5 4D-C FX (Currency Conversion Display)

**USD Equivalent is a supplemental display value.**

**Binding constraints:**

- Currency conversion **MUST NOT** be moved into frozen 3B normalization or
  frozen 4A aggregation.
- FX rate is itself **evidence**, carrying: source, retrieved/rate date, rate.
- Historical report reload must use **persisted** FX evidence.
- `GET /research/<uuid>` must **not** make live Vendor API or FX calls.
  Historical report GET renders persisted evidence only.
- If FX is unavailable, original price remains valid and USD Equivalent
  displays unavailable.
- Use `Decimal` semantics in future implementation.
- Official ECB daily / working-day reference data is the intended source unless
  design evidence later requires otherwise.

**USD source rows:** USD Equivalent = same USD amount without needing an FX
conversion lookup.

**Non-USD source rows:** use only persisted FX evidence. Zero live FX network
calls on historical report GET.

**Note:** Future deployments that introduce a reverse proxy and need
forwarded-client-IP processing (e.g., X-Forwarded-For or X-Real-IP) must
design and document a trusted-proxy contract. This is a separate security
design beyond the current REMOTE_ADDR-only policy. Until such a contract is
approved and implemented, only `REMOTE_ADDR` is the authoritative client
address source.

### 26.6 4D-C-SEC — Vendor Commercial Price Access Gate

**APPROVED / FROZEN** (PRODUCT-INTEL.4D-C-SEC; SHA
75bfbe3d1b4a8abc12d655cc903298f08e06a8f0, frozen baseline 4693 collected).

A server-side network access gate prevents vendor commercial price visibility
until a trusted-corporate-network / VPN / approved-subnet access condition is
satisfied. See §19 for the binding security contract.

**Security contract:**
- `PI_VENDOR_PRICE_ALLOWED_CIDRS` — comma-separated CIDR notation (IPv4/IPv6)
- Absent or blank → DENY (fail-closed)
- Only `request.META["REMOTE_ADDR"]` is the accepted client-address source
- X-Forwarded-For, X-Real-IP, Forwarded, query params, cookies, Host header,
  report UUID are all explicitly rejected
- Malformed CIDR → entire configuration fails closed (deny all)
- No authentication or session system introduced
- No identity authority or pricing authority change
- `product_intelligence/web/commercial_access.py` — HTTP request authorization
  at the presentation boundary; not in `research/`, `providers/`, or `domain/`
- Full application authentication deferred to 8C
- 4D-C browser rendering implemented behind this gate (§26.4): server-side
  security branch before vendor supplemental artifact access

### 26.7 4D-D — Micron Packaging Alias Retrieval

**Customer requirement:**

Manufacturer: Micron only. For Micron Memory / SSD, a final `R` or `T` may
identify packaging variants:

```
MTFDKCC3T8TGP-1BK1DABYYR
MTFDKCC3T8TGP-1BK1DABYYT
MTFDKCC3T8TGP-1BK1DABYY
```

**The rule:**
- Manufacturer must be Micron.
- Only the **final** character may be `R` or `T`.
- Removing that final character must leave the exact same base.

**Safety gate:**

Packaging alias expansion is allowed only when manufacturer is established as
Micron AND product category is evidence-backed as Memory or SSD.

Do NOT enable the rule merely because unverified request-description text says
"SSD" or "Memory".

If manufacturer/category eligibility is not established, abstain and generate
no packaging alias.

**Architecture decision:**

**DO NOT** modify frozen 2A part-number identity normalization.
**DO NOT** classify these as `EXACT` or `NORMALIZED_EXACT` merely by dropping
`R`/`T`.

Use a **distinct retrieval/reference relation**, conceptually:
`MICRON_PACKAGING_ALIAS`.

It may generate retrieval aliases:
- requested base+`R`
- base+`T`
- base

**Purpose:**
- Improve search / discovery recall.
- Allow clearly labeled reference rows.

**It must NOT automatically:**
- Enter Machine Price authority.
- Become deterministic exact identity.
- Become Reviewed Price authority.
- Alter frozen 2A normalization.

If a later phase wants these variants to enter authoritative pricing, that
requires independent evidence-backed validation.

**4D-D implementation record (original candidate pass — historical; final
state APPROVED / FROZEN via the 4D-D FU1 record below):**

Implemented against the frozen 4D-D-PRE2 evidence (SHA
1cb65a3d6002006af9e1c77906a6de6b5a3fd42c). v1 scope is binding: Micron 7500
SSD ONLY (not generic Micron memory, not DRAM, not any other family or
suffix set; extension requires additional reviewed authority policies and
recorded manufacturer evidence).

Authority split as implemented:

```
Micron catalog (reviewed 4D-D-PRE2 family-catalog endpoint):
    manufacturer / category / source-published BASE authority
    (policy id micron-7500-ssd-part-catalog-v1, module-private,
    no environment/DB/caller injection; category from the matched row's
    own structured is-ssd == True attribute, never inferred)

customer rule (final uppercase R/T strip; base re-derivation):
    R/T retrieval relation only (MICRON_PACKAGING_ALIAS)
    — retrieval recall + clearly labeled reference rows;
    never identity, never Machine/Reviewed/Compact/Comparable authority;
    frozen 2A/3C unchanged (family forms are NEVER established under 2A)
```

Runtime behavior as implemented:

* direct-sufficient runs: zero Micron authority fetch, zero paid search,
  no alias snapshot;
* one direct-insufficient run with a non-empty MPN: at most ONE reviewed
  family-catalog fetch (bounded audit statuses: ESTABLISHED, NO_REQUESTED_MPN,
  INVALID_LOOKUP_BASE, NO_AUTHORITY_MATCH, AMBIGUOUS_AUTHORITY_MATCH,
  CATEGORY_NOT_SSD, FETCH_FAILED, SOURCE_REFUSED, HOST_ESCAPED, PARSE_FAILED);
  the bounded audit is persisted as `ResearchMicronAliasSnapshot` (V1 codec,
  body SHA-256, never the catalog body) BEFORE the paid search;
* only ESTABLISHED changes the paid query, and only to the FROZEN OR shape
  `("REQUESTED" OR "ALIAS1" OR "ALIAS2") description` (the group alone when
  the request has no description): requested MPN first, established aliases
  in deterministic relation order, one parenthesized OR group — an AND
  grouping would require every quoted identifier simultaneously and defeat
  the recall purpose of alias expansion; at most ONE paid search per run;
  every other status keeps the ordinary frozen query;
  `build_search_query` is unchanged;
* semantic firewall: with an ESTABLISHED alias-expanded search, non-ACCEPTED
  assessments from that search batch are excluded from semantic evaluation
  (no AI_ASSISTED_MATCH / review candidate / Reviewed Price path membership)
  while remaining in frozen 4A input and exclusions; direct and ordinary
  non-alias assessments retain frozen semantic behavior; deterministic exact
  requested-MPN listings keep normal frozen 4A behavior;
* historical GET renders the separate "Micron packaging alias evidence"
  section ONLY from the persisted snapshot (zero live provider / network /
  semantic work; fail closed on codec error or request-provenance mismatch);
  alias reference rows are persisted EXCLUDED assessments only;
* R/T per-part detail endpoints are never fetched (PRE2: Invalid
  Partnumber / template echo — not authority).

Collection accounting (frozen 4D-C baseline 4766 -> 5052):

| Component | Nodes |
| --- | --- |
| Frozen 4D-C baseline | 4766 |
| Explicit new focused 4D-D test nodes (7 files) | 258 |
| New explicit 4D-D model-field inventory test (test_research_run_boundaries.py) | 1 |
| Automatic parameterized expansion (domain +2, providers +4, research identity +8, runs +4, web +9) | 27 |
| **4D-D collection** | **5052** |

State at the time of this record: the candidate was IMPLEMENTED / PENDING
FINAL REVIEW and was not approved; independent review identified
source-level defects, corrected by the 4D-D-FU1 pass below. Final state:
APPROVED / FROZEN (see the 4D-D FU1 record).

**4D-D FU1 implementation record (APPROVED / FROZEN):**

Append-only correction pass on the 4D-D implementation commit; fixes three
independently verified source-level acceptance blockers without changing any
4D-D scope, policy, status vocabulary, persistence, codec, web, or firewall
semantics.

* BLOCKER 1 — runtime reachability. The production authority endpoint
  returns `Content-Type: application/json;charset=utf-8` (PRE2) but the real
  default `HttpPageFetcher` accepted exactly `text/html` /
  `application/xhtml+xml`, so MICRON_PACKAGING_ALIAS was unreachable in the
  real default runtime. Fix: additive immutable `accepted_media_types` /
  `accept_header` constructor configuration on the existing `HttpPageFetcher`
  (no second HTTP/provider abstraction, no browser, no requests/httpx, no
  cookie/proxy/auth). The default configuration is exactly the frozen 3A
  behavior (default `application/json` refusal and its regression unchanged);
  a JSON-configured fetcher accepts exactly `application/json` (parameters
  and casing ignored), sends `Accept: application/json`, and keeps every
  SSRF / redirect / credential / timeout / size bound. Default orchestration
  wiring: with no injected page fetcher, the ordinary candidate fetcher is
  the HTML-only default and the ONE Micron authority fetch uses a lazily
  created JSON-configured `HttpPageFetcher` — instantiated only when fallback
  search is required AND the request MPN is non-empty (direct-sufficient runs
  never instantiate or fetch it). An explicitly injected fetcher governs the
  authority fetch as well, preserving the deterministic fake-provider tests.
  Mandatory real-adapter integration (offline via public DNS fixture +
  controlled opener + PRE2-recorded catalog bytes): the REAL JSON-configured
  `HttpPageFetcher` reaches ESTABLISHED for
  `MTFDKCC3T8TGP-1BK1DABYYR` (matched base `MTFDKCC3T8TGP-1BK1DABYY`,
  manufacturer Micron, category SSD); the REAL default HTML-only fetcher
  refuses the same recorded bytes (`PageFetchError` / bounded FETCH_FAILED);
  the default production wiring end-to-end sends `Accept: application/json`
  for the catalog, persists ESTABLISHED, and issues exactly ONE paid search.
* BLOCKER 2 — query semantics. `build_alias_expanded_search_query` emits the
  frozen OR shape (requested MPN first, aliases in deterministic relation
  order, ordinary description appended; group alone without a description).
  `build_search_query` is unchanged; exactly ONE `SearchProvider.search()`
  call remains.
* BLOCKER 3 — broad exception catch removed. The authority module contains
  no `except Exception` (in any form): only `PageFetchError` (-> FETCH_FAILED)
  and `UnsafeFetchTargetError` (-> SOURCE_REFUSED) are downgraded; a bare
  `Exception` and a `RuntimeError` propagate to the catastrophic boundary.
  Dependency-contract defects (non-callable `fetch`; non-`FetchedPage` /
  contract-invalid return) propagate `TypeError` and are never given a
  bounded authority status.
* HTTP_PAGE opener-OSError change (14981e3) kept and separately
  regression-tested as a transport-classification fix (`_build_opener`
  OSError -> bounded `PageFetchError`; non-OSError programming errors still
  propagate). It does not solve, and is not claimed to solve, the Micron
  JSON reachability issue (that is BLOCKER 1).
* Production files changed (FU1): `providers/http_page.py` (additive
  media-type capability, defaults unchanged), `execution/orchestration.py`
  (default JSON authority fetcher wiring, additive),
  `execution/micron_alias_authority.py` (broad catch removed; dependency
  contract defects propagate), `execution/search_query.py` (OR shape in
  `build_alias_expanded_search_query` only).

Independent review of the pushed FU1 commit (ChatGPT, acting as project lead
/ independent architecture reviewer) is complete and approved
PRODUCT-INTEL.4D-D-FU1. PRODUCT-INTEL.4D-D (including 4D-D-FU1) is
APPROVED / FROZEN:

Frozen SHA: 065320180c17b89c7460164326a0c9f49e01fe3b
Frozen collection baseline: 5097 collected
Final acceptance execution: 5097 passed, 0 failed, 0 skipped, 0 xfailed,
0 deselected (+ 39 subtests passed)

### 26.8 Deferred items for 4D

The following are NOT pulled into 4D unless already documented as future:

- Redis
- Celery
- Background jobs
- Generic scraping platform
- React / SPA rewrite
- Full auth implementation
- PostgreSQL migration
- Caching implementation (8A)
- SAP work

8A caching / refresh remains later.
8B research history remains later.
8C production hardening remains later.

### 26.9 PILOT-RELEASE-2: 4D Customer Requirement Deployment & UAT

**Status: DEPLOYED / ACCEPTED** (deployment/UAT phase, not a
feature-development phase).

Purpose: deploy the already-frozen 4D customer requirements to the restricted
internal Windows pilot server and validate the complete real business
workflow before starting another architecture feature phase.

Deployment record (PILOT-RELEASE-2 closure):
- Deployed runtime SHA: 065320180c17b89c7460164326a0c9f49e01fe3b — the
  independently reviewed and frozen PRODUCT-INTEL.4D-D-FU1 runtime SHA.
  Deployment is Git-managed and exact-approved-SHA based (local
  `production` branch pinned to independently approved SHAs).
- Production smoke test passed: 2026-09-23. The recorded representative
  4D production smoke validation covered: a normal customer quote flow
  exercising current Price Intelligence / Compact Quote behavior;
  Micron 7500 R/T packaging-alias behavior. The previously planned
  broader UAT matrix (listed below) remains a validation reference; the
  production records do not claim that every matrix case was separately
  executed and evidenced during the 2026-09-23 cutover.
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

Runtime-vs-docs distinction (binding for this closure):
- Runtime freeze / deployed SHA = 065320180c17b89c7460164326a0c9f49e01fe3b.
- The later commits c6ad6ae (PRODUCT-INTEL.4D-CLOSE) and 7ff0ab7
  (PRODUCT-INTEL.4D-CLOSE-FU1) are docs-only project-state closures;
  production does not need to move merely to obtain those
  documentation edits.
- 7ff0ab7 is NOT the production runtime SHA; the deployed production
  runtime at 0653201 is intentional and correct.

Previously planned broader UAT matrix (high level; historical planning
reference):
- direct-source acquisition using a viable preferred-source case
- normal Serper fallback
- real Vendor API commercial evidence
- compact quote rendering
- non-USD vendor evidence + persisted ECB USD equivalent
- Micron 7500 packaging-alias BASE/R/T behavior
- a non-eligible MPN proving alias abstention
- Visual FoxPro launcher -> browser prefill against the deployed server
- historical report reload causing zero new Search/Vendor/ECB/Micron/Semantic
  live work
- vendor-price access behavior under the existing frozen network gate
  (4D-C-SEC `REMOTE_ADDR` / `PI_VENDOR_PRICE_ALLOWED_CIDRS`, unchanged)

Authentication/session decision for the current pilot:
- The current pilot server itself has restricted access; people who can reach
  this internal server are currently considered authorized for this pilot.
- Full application authentication, login/session identity, OAuth, and
  per-user authorization are NOT part of PILOT-RELEASE-2; they remain
  deferred future production-hardening concerns (8C). No authentication or
  session design is introduced by this phase.
- The report UUID is never access control.
- The frozen 4D-C-SEC vendor-commercial-price network gate is unchanged.

Next delivery (post-PILOT-RELEASE-2): PRODUCT-INTEL.8A-PRE (Caching &
Freshness Architecture Audit) — PLANNED. [State update: 8A-PRE has
COMPLETED (APPROVED / COMPLETE); the 8A series advanced through the
approved 8A-FX design lineage to 8A-FX-A1 (IMPLEMENTED / PENDING FINAL
REVIEW; §26.18). The planning text below is preserved as the historical
closure decision.] READ-ONLY / DESIGN-FIRST:
investigate and record a caching and freshness architecture before any
caching implementation; it is NOT authorization to implement caching,
and no actual TTL values are approved in this closure. Chosen because
Product Intelligence is now in production and evidence classes have
materially different freshness requirements: the design must prevent
stale evidence from being presented as current while avoiding
unnecessary paid/live calls. The future 8A design must distinguish at
minimum: market/public prices (short freshness); Vendor commercial
observations (short freshness); ECB FX rates (tied to persisted official
observation date); product specifications (longer freshness); comparable
research (medium freshness); deterministic identity/authority evidence
(not automatically equivalent to market-price freshness); user/operator
forced refresh; historical reports (immutable replay, NEVER refreshed
merely by GET).

Later planned (directional; not an approved implementation order):
5A (structured external API — PLANNED / NOT IMPLEMENTED / NON-BLOCKING for
the current FoxPro/browser workflow), 8A (caching / refresh strategy —
the future implementation phase that 8A-PRE precedes), 8B (research
history), 8C (production hardening). None of them is NEXT;
authentication/session remains outside the current priority.

### 26.10 PILOT-RELEASE-2-PROD-FIX1: Production Quote-Workflow Corrections

**Status: IMPLEMENTED / PENDING FINAL REVIEW.** Bounded production
corrective phase against defects discovered during real production use of
the deployed PILOT-RELEASE-2 runtime (frozen deployed runtime SHA
065320180c17b89c7460164326a0c9f49e01fe3b). Corrective scope only: no new
feature phases, no 8A caching, no new models/migrations, no deployment in
this commit.

**26.10.1 Vendor real-response contract (4D-B adapter correction)**

The production Vendor API (`PI_VENDOR_LOOKUP_BASE_URL`) answers HTTP 200
with `Content-Type: text/html; charset=utf-8` and a body that is NOT one
JSON document — a plain-text, section-oriented body with exactly three
bounded section labels:

```
Ingram Product: { ... }
CDW Product: {Not Found}
Synnex EU Product: { ... }
```

**FU3 correction (see §26.13):** the "plain-text" wording above is
incomplete for the OBSERVED production body. A bounded production
structure probe (no values printed) established that the real endpoint
answers HTTP 200 / `Content-Type: text/html; charset=utf-8` (approximately
5485 bytes for the observed Micron lookup, 5 lines) and that each
recognized section line carries an exact literal `<p>` immediately before
the known label — structurally `<p>Ingram Product: { ... }</p>` /
`<p>CDW Product: {Not Found}</p>` /
`<p>Synnex EU Product: { ... }</p>` (each label exactly once). The adapter
now recognizes each of the three exact known labels in exactly two outer
forms: the existing plain line-anchored form (unchanged) and the observed
exact paragraph-prefix form. The contract is exactly
`optional whitespace + optional exact "<p>" + exact bounded known label` —
the support is the observed literal only, NOT a generic HTML parser (no
other tags, no attributes, no nesting, no tag stripping, no HTML
unescaping, no DOM search). The source payload after the label remains
bounded literal data parsed by the unchanged strict grammar; a trailing
observed `</p>` after a COMPLETE bounded literal is the already-supported
post-literal interstitial material (never data).

Frozen correction rules:

* The adapter supports BOTH upstream contracts: the canonical JSON wrapper
  (retained, unchanged behavior) and the production section-oriented body
  (new). When the body is not one JSON document, the strict section parser
  is attempted before the lookup is failed.
* Section parsing is strict and bounded: only the three exact labels are
  recognized (case-sensitive, line-anchored); arbitrary section labels are
  never trusted, parsed, or persisted; the section value must be either the
  exact bounded `{Not Found}` marker or a bounded literal mapping parsed by
  a dedicated recursive-descent parser (no eval, no literal_eval, no code
  execution; duplicate keys, non-string keys, expressions, and code-looking
  tokens are refused; depth/entry bounds enforced). Numbers are parsed from
  text directly into Decimal — no binary float ever touches a value.
* Section content is mapped through the SAME allowlist mappers, extended
  with the flat production field forms (Ingram: `vendorPartNumber`,
  `customerPrice`/`retailPrice`, `currency`, `quantity`/`available`;
  CDW: `manufacturerPartNumber`, `price`, `currency`/`currencyCode`,
  `stockStatus`/`quantity`/`Avl_Quantity`; Synnex EU:
  `ManufacturerItemIdentifier`, `UnitPriceAmount`,
  `currency`/`CurrencyCode`, `AvailabilityTotal`, bounded `Note`
  meanings). The canonical nested forms remain supported unchanged.
  **FU1 correction (see §26.11.1):** the ACTUAL production Ingram wire
  placement is the hybrid form (nested `pricing` + top-level boolean
  `availability` + top-level `Avl_Quantity`); the flat forms are retained
  compatibility forms, not the only/exact production wire shape.
* Exactly one Vendor network call per lookup; transport/timeout/size/
  redirect/no-proxy behavior unchanged; malformed one-source content does
  not destroy independently valid sources; the raw body is never logged or
  persisted.
* PRIVACY INVARIANT (unchanged and re-proven): the real Synnex payload's
  sensitive metadata (`SessionId`, `BuyerAccountId`, `SystemId`, and any
  other non-allowlisted field) never enters CommercialSourceCandidate,
  ResearchSupplementSnapshot, logs, or error detail. The allowlist mappers
  remain the security boundary; test fixtures use fake/redacted sentinels.

**26.10.2 Currency formatting (Compact Quote display correction)**

The Compact Quote price formatter rendered no-symbol currencies as
`ZAR30,999.0 ZAR` (code used as fallback prefix, then appended). Corrected:
known-symbol currencies keep `$1,515.72 USD` / `€962.86 EUR`; currencies
without a configured symbol render the code exactly once as a leading
prefix: `ZAR 30,999.0`. A bare currency code is not a symbol (the former
`CHF -> "CHF"` mapping entry was removed). Decimal values and FX math are
not altered.

**26.10.3 AI-assisted semantic matches placement (presentation only)**

`research_detail.html` renders the "AI-assisted semantic matches" section
immediately after "Compact quote summary" and before the detailed
lower-level audit/research sections (Micron alias evidence, Price
intelligence, Reviewed price, Comparable products). Template ordering only:
no semantic eligibility, model, or review-state behavior changes.

**26.10.4 Confirm Match -> Compact Quote (projection-layer extension)**

A valid run-scoped, human-CONFIRMED semantic candidate MAY contribute to
the Compact Quote for that SAME ResearchRun. Authority rules (binding):

* Human confirmation establishes IDENTITY authority only. It must NOT
  invent or upgrade other facts: price and currency come from the
  persisted PriceIntelligenceSnapshot assessment (exactly the frozen
  normalized values); condition is EXACTLY the persisted normalized
  condition (UNKNOWN renders "Unknown" — never upgraded to Yes; NEW may
  truthfully render Yes); a confirmed candidate without persisted
  price/currency evidence produces no row.
* Machine Price (frozen 4A artifact) is never mutated; the original
  PriceIntelligenceSnapshot is byte-identical before and after
  confirmation.
* The semantic MATCH itself still does NOT enter the Compact Quote before
  human confirmation; REJECTED and UNREVIEWED candidates do not enter;
  Undo removes the row on the next GET; cross-run candidates cannot enter
  another run; invalid/stale bindings fail closed (the same fail-closed
  candidate-to-assessment binding validation that feeds the Reviewed
  Price, plus projection-side re-validation of range, semantic
  eligibility, and persisted price/currency).
* Every projected row carries the explicit "Human Confirmed" provenance
  note; USD Equivalent uses persisted FX evidence only.
* Vendor authority remains separate and supplemental; Micron alias
  remains retrieval/reference only.
* Historical GET `/research/<uuid>` remains ZERO LIVE I/O: the effective
  Compact Quote is recomputed only from already-persisted
  PriceIntelligenceSnapshot + AiAssistedReviewCandidate review state +
  ResearchSupplementSnapshot + ResearchFxSnapshot.
* Implementation is a projection-layer extension (`research/
  compact_quote.project_human_confirmed_rows` + additive replay
  parameters), not a rewrite of frozen 4A artifacts. The frozen Reviewed
  Price behavior is unchanged. **FU1 supersession (see §26.11.2):** the
  additive replay index parameters were removed — the replay boundary
  itself derives the effective human-confirmed selection from persisted
  state; a caller-supplied bare index can never mint HUMAN_CONFIRMED
  authority.

**26.10.5 Research submit duplicate-click guard (UX only)**

The new-research form carries a small front-end-only inline JavaScript
guard: on a valid submit the button is immediately disabled and relabeled
`Researching…`; the normal POST continues. If client-side validation
prevents submission the button stays enabled. This is NOT a backend
dedupe guarantee: no in-progress run is shared across users, no MPN-level
locking, no caching, no server-side whole-run reuse, no ResearchRun
lifecycle change.

**26.10.6 ECB / USD Equivalent TLS trust-chain issue (no bypass)**

Production observed `ssl.SSLCertVerificationError` /
`CERTIFICATE_VERIFY_FAILED` / `unable to get local issuer certificate`
when the ECB FX provider ran on the production server. Binding conclusion
and locked behavior:

* Secure HTTPS verification is preserved; NO `verify=False`, no unverified
  SSL context, no disabled hostname check, no certificate suppression, no
  hard-coded downloaded certificates, and no fallback to an untrusted HTTP
  endpoint were added. The provider's transport is unchanged.
* The failure was correctly classified as bounded `FxNetworkError`
  (regression-tested against the exact production error class via the real
  stdlib wrapping path), and orchestration keeps FX failure nonfatal:
  the affected run completed without a ResearchFxSnapshot, the original
  non-USD price survived, and USD Equivalent displayed "Unavailable"
  (regression-tested end-to-end; the failure-path regression tests remain
  valuable and are retained by FU1).
* FU1 production evidence (recorded in §26.11): a later secure retry from
  the SAME production Python runtime — without installing certifi,
  without manually installing any certificate, without changing fx.py,
  and without disabling TLS verification — succeeded and returned
  official rates (observation date 2026-09-24; USD 1.1367; ZAR 18.6836).
  The exact reason for the transient trust-chain failure has NOT been
  proven; there is currently no evidence-backed requirement to
  install/update a CA trust store, and no such action is recorded as an
  outstanding fact. If the failure reoccurs persistently, the CA trust
  state of the production Python runtime is the first place to inspect —
  as an investigation step, not as a pre-declared repair.
* If a future phase requires supporting an explicitly configured trusted
  CA bundle, that is a NEW configuration contract to be designed, reviewed,
  and approved separately — no such pattern exists in the repository
today, and none was invented by this phase.
* Caching must not hide this failure (8A-PRE remains design-first and is
  not implemented here).

### 26.11 PILOT-RELEASE-2-PROD-FIX1-FU1: Production Review-Blocker Closure

**Status: IMPLEMENTED / PENDING FINAL REVIEW.** Bounded append-only
corrective follow-up on the independently reviewed PROD-FIX1 commit (SHA
8811104e14103c41346c05471b3170c55c97386a). Corrects the three review
blockers plus one presentation-accuracy defect. No deployment, no 8A
caching, no new models/migrations. The PROD-FIX1 implementation is
retained except where a blocker required correction.

**26.11.1 Vendor production-wire fidelity (BLOCKER 1)**

The PROD-FIX1 "production-equivalent" test fixture simplified the real
production Ingram section into a flat form. The ACTUAL production wire
shape is a HYBRID placement, now supported and fixture-mirrored:

* Ingram: explicit `vendorPartNumber`; nested `pricing` block
  (`customerPrice` / `retailPrice` / `currencyCode`); TOP-LEVEL boolean
  availability signal; TOP-LEVEL `Avl_Quantity`. The nested-pricing branch
  keeps its pricing authority (customerPrice present => authoritative;
  retailPrice fallback only when the customerPrice key is absent), keeps
  the canonical nested availability dict, and additionally recognizes the
  hybrid top-level placement through the SAME bounded availability truth
  table: contradiction or uncheckable lone signal => UNKNOWN (fail
closed); `false` + `Avl_Quantity 0` => OUT_OF_STOCK / 0; `true` +
  positive => IN_STOCK. Stock is never inferred from vendor reputation or
  unrelated fields; unknown fields (e.g. `vendorName`) remain ignored by
  the allowlist. The canonical nested form and the flat compatibility form
  are both retained and separately tested; the flat form is a
  COMPATIBILITY form, not the only/exact production wire shape.
* Synnex EU: the integration path now uses the REAL nested form
  (`OnlineCheck.Header.CurrencyCode`,
  `OnlineCheck.Item.ManufacturerItemIdentifier`,
  `OnlineCheck.Item.UnitPriceAmount`, `OnlineCheck.Item.AvailabilityTotal`)
  with fake/redacted `SessionId` / `BuyerAccountId` / `SystemId` at their
  realistic structural locations (the `OnlineCheck.Header` block); the
  allowlist strips them and they never enter candidates, snapshots, logs,
  or error detail.
* Section scanner/strict-parser consistency (the documented contract was
  "unrecognized/interstitial text is ignored" but the parser rejected a
  known section as trailing garbage when such text followed a complete
  literal). Resolved: only the three exact line-anchored labels establish
  sections; once a section's COMPLETE bounded literal has parsed, unknown
  text up to the next recognized header is interstitial — never parsed
  into data, never persisted, never able to poison the complete mapping.
  Malformed content INSIDE a section literal still fails that source
  closed. No generic HTML scraping was introduced; the strict bounded
  recursive-descent grammar is unchanged.
* Integration proof: the full `execute_research_run` test now uses the
  faithful hybrid Ingram section + nested Synnex section for the exact
  requested MPN `MTFDKBA480TFR-1BC1ZABYYR`: one Ingram observation
  (1515.72 USD, customer price, OUT_OF_STOCK, quantity 0), one Synnex EU
  observation (962.86 EUR, OUT_OF_STOCK, quantity 0), CDW NOT_FOUND,
  sensitive metadata absent from the persisted snapshot.

**26.11.2 Human-confirmation authority ownership (BLOCKER 2)**

PROD-FIX1 let the replay/service boundary accept
`confirmed_assessment_indices` from the caller. `project_human_confirmed_rows`
proves index/type/range/eligibility but cannot prove CONFIRMED persisted
review state or the full candidate-to-assessment binding, so a direct
internal caller could have presented an UNREVIEWED or REJECTED
semantic-eligible assessment as `HUMAN_CONFIRMED`. Corrected:

* The single pure candidate-to-assessment binding primitive
  (`research.matching.is_review_candidate_binding_valid`) is now the ONE
  place the binding rule exists: eligibility + source_url + target_mpn +
  candidate_title + candidate_mpn_field (raw observation field) +
  candidate_sku + evidence_source. The web GET presentation, the 8-step
  review-POST validation, and both historical replay boundaries all apply
  this same primitive (no divergent copies). The web 8-step POST
  fail-closed validation is unchanged in strength.
* `execution.compact_quote_replay.derive_human_confirmed_assessment_indices`
  proves from PERSISTED STATE (zero live I/O) that each human row is: (1)
  an AiAssistedReviewCandidate for THIS run; (2) review_state CONFIRMED;
  (3) mapped to an in-range assessment index; (4) fully bound to that
  assessment via the shared primitive; (5) the assessment is still
  human-review eligible; (6) persisted price/currency exist (enforced by
  the projection — no row without them). UNREVIEWED / REJECTED / undone /
  tampered / stale / cross-run candidates never enter.
* BOTH replay entry points (`replay_compact_quote_projection`,
  `replay_public_compact_quote_projection`) no longer accept any
  caller-supplied index parameter: a bare integer can never mint
  `HUMAN_CONFIRMED` authority at the boundary that owns the effective
  historical Compact Quote. The lowest-level pure projection helper
  (`project_human_confirmed_rows`) is retained as an
  already-authorized-selection consumer with that contract stated
  explicitly, and keeps its defense-in-depth fail-closed checks.
* Machine Price remains untouched; human review remains run-scoped;
  historical GET remains zero-live-I/O (DB reads of persisted state only).

### 26.12 PILOT-RELEASE-2-PROD-FIX1-FU2: Public Replay Persisted-Snapshot Authority

**Status: IMPLEMENTED / PENDING FINAL REVIEW.** Bounded append-only
corrective follow-up on the FU1 commit (SHA
681a4a8b67895e510eb277c850c0e83318af17b9). Closes the final independent
review blocker for PROD-FIX1. No deployment, no 8A caching, no new
models/migrations. FU1 (Vendor hybrid wire, shared binding primitive,
authorized replay authority, ECB evidence, Reviewed Price wording) is
retained unchanged.

**The blocker (final FU1 review):** FU1 removed the caller-supplied
`confirmed_assessment_indices` from both replay boundaries, but the
PUBLIC (denied-branch) replay
`replay_public_compact_quote_projection(run=..., price_result=...)`
still accepted a CALLER-SUPPLIED `PriceAggregationResult` and verified
only `price_result.request == run.to_research_request()`. Request
equality is NOT proof that the price/currency/condition evidence is
the persisted `PriceIntelligenceSnapshot` belonging to THIS run. A
same-request cross-run scenario could borrow evidence: Run A (request
R, CONFIRMED semantic candidate, source URL/title/MPN-field/SKU/
evidence-source binding X, persisted price 1890 USD) and Run B (same
request R, same binding X, later/different persisted price 999 USD).
If an internal caller supplied Run B's decoded result with Run A, the
shared binding primitive (`is_review_candidate_binding_valid`) would
legitimately match Run A's CONFIRMED candidate against Run B's
assessment — all identity/provenance fields are equal — and the public
replay could present Run B's 999 USD as a HUMAN_CONFIRMED row for
Run A. That violates historical report immutability, run-scoped
evidence authority, and the rule that confirmation establishes
identity authority only over the persisted evidence belonging to that
same run.

**The correction:** the public/denied replay boundary now OWNS its
`PriceIntelligenceSnapshot` authority exactly like the authorized
replay. The `price_result` parameter is REMOVED; the entry point is
`replay_public_compact_quote_projection(run=run)`. It:

1. verifies `run` is a real `ResearchRun` (TypeError otherwise);
2. loads `PriceIntelligenceSnapshot.objects.get(run=run)` — missing
   artifact fails closed (DoesNotExist propagates, the existing
   persisted-artifact behavior shared with the authorized replay; the
   web view maps it to "summary unavailable");
3. decodes it through the canonical price-result codec
   (`decode_price_aggregation_result`; malformed payload / unsupported
   schema version fails closed with `PriceResultCodecError`);
4. verifies `decoded.request == run.to_research_request()` (a
   request-provenance-corrupt snapshot fails closed with
   `CompactQuoteProjectionError`);
5. uses THAT decoded persisted result for the frozen public bucket
   projection, the shared human-confirmed binding derivation
   (`derive_human_confirmed_assessment_indices`), and the
   human-confirmed price/currency/condition evidence;
6. reads persisted `ResearchFxSnapshot` only (never live);
7. NEVER reads `ResearchSupplementSnapshot` and never imports/calls the
   commercial supplement codec (4D-C-SEC denied branch unchanged);
8. performs ZERO live Search/Page/Vendor/ECB/Semantic/network work.

**Authority statement (exact):** BOTH the authorized and the denied
historical Compact Quote replay paths derive public and
human-confirmed price evidence from the ResearchRun's OWN persisted
`PriceIntelligenceSnapshot`. NO caller-supplied
`PriceAggregationResult` (and no caller-supplied index) is an authority
source at either boundary.

**Regression proof (same-request cross-run, direct service level):**
Run A (1890 USD, CONFIRMED candidate) and Run B (999 USD, SAME request,
SAME source URL / product title / MPN field / SKU / evidence source,
CONFIRMED candidate) — (a) the exploit premise is proven non-vacuous:
the shared binding primitive legitimately matches Run A's candidate
against Run B's assessment and the derivation would mint index 0 over
Run B's evidence; (b) the public replay for Run A shows Run A's
persisted 1890 USD and no 999 anywhere in Run A's projection; (c)
Run B's public replay independently shows its own 999 USD and no 1890;
(d) `inspect.signature` proves the only parameter is `run`, and
supplying Run B's decoded result raises TypeError; (e) the authorized
replay for Run A still shows 1890 (unchanged); (f) every
`PriceIntelligenceSnapshot` is byte-identical (schema_version +
payload) before/after both replays on both runs (Machine Price
untouched).

**Boundary preservation (re-proven):** the denied/public replay remains
vendor-free — no `ResearchSupplementSnapshot` read (armed fail-fast,
including a real persisted supplement with a sentinel vendor price), no
commercial supplement codec import (mechanical AST guard, runs.models
allowlist extended with exactly `PriceIntelligenceSnapshot`), no
InternalVendorAdapter, no SearchProvider, no PageFetcher, no ECB live
call, no SemanticRuntime, no generic network call (armed fail-fast).
Persisted `ResearchFxSnapshot` remains allowed; persisted
`PriceIntelligenceSnapshot` is now REQUIRED because it is the authority
source. FU1's human-confirmed authority semantics are preserved:
UNREVIEWED / REJECTED / tampered / stale / cross-run candidates never
enter; Undo removes the row on the next GET; the 8-step review-POST
validation is unchanged in strength.

**26.11.3 ECB trust-chain evidence correction (BLOCKER 3)**

PLAN §26.10.6 is corrected as recorded there: the transient trust-chain
failure is retained as history and its failure-path regression tests are
retained (not removed, not weakened); NO insecure TLS workaround exists or
was added; `providers/fx.py` is unchanged in this phase; and the
documentation no longer states an unproven root cause or an outstanding
CA-store installation action as fact, given the successful secure retry
from the same production runtime (2026-09-24 rates).

**26.11.4 Reviewed Price wording accuracy (presentation defect)**

The Reviewed Price summary sentence previously stated "includes N
human-confirmed AI-assisted listings" using the count of validated
CONFIRMED candidates (N), even when fewer of them were actually
price-eligible for the reviewed buckets (e.g. UNKNOWN condition). The
template now derives the truthful PRICE-CONTRIBUTING counts from the
reviewed buckets themselves (sum of per-bucket `human_confirmed_count` /
`deterministic_count`) and renders conditionally truthful wording. Review
eligibility is NOT changed to make the count match: a confirmed
UNKNOWN-condition listing still renders in the Compact Quote (display)
while staying out of the Reviewed Price arithmetic (frozen contract).

### 26.13 PILOT-RELEASE-2-PROD-FIX1-FU3: Vendor Paragraph Envelope

**Status: IMPLEMENTED / PENDING FINAL REVIEW.** Bounded append-only
corrective follow-up on the FU2 commit (SHA
ec67f0f2f8f357fb77dd3cc1a5947e50a1b80af2). Closes the exact remaining
production defect: on the approved SHA, the production Vendor response
for `MTFDKBA480TFR-1BC1ZABYYR` (run
f3a82fda-f708-4974-806e-d13a18482f96) was persisted as FAILED /
`retrieved_at=None` / zero observations / zero issues because the section
scanner did not recognize the real OUTER response envelope — the defect
was inside Vendor response contract recognition, before source mapping,
2A binding, persistence, and Compact Quote projection. A bounded
production structure probe (no response values or sensitive fields
printed) established the observed exact structure. No deployment; no 8A
caching; no Vendor adapter redesign; the hybrid Ingram, nested Synnex EU,
Human Confirmed, FX, Compact Quote authority, and replay contracts are
unchanged except where directly necessary to support the observed
envelope.

**The observed production envelope (structure only; no real values):**

* HTTP 200
* `Content-Type: text/html; charset=utf-8`
* approximately 5485 bytes for the observed Micron lookup (5 lines)
* each known section label appears exactly once
* each recognized section line carries an exact literal `<p>`
  immediately before the known label (the observed three-character line
  prefix is the HTML paragraph opener), structurally:

  ```
  <p>Ingram Product: { ... }</p>
  <p>CDW Product: {Not Found}</p>
  <p>Synnex EU Product: { ... }</p>
  ```

* the source payload after the label remains bounded literal data

**The correction (narrowest possible bounded support):** the section
scanner now recognizes each of the three exact known labels in exactly
two outer forms:

1. the existing plain line-anchored form (`Ingram Product: ...`,
   leading whitespace tolerated) — unchanged;
2. the observed exact paragraph-prefix form (`<p>Ingram Product: ...`,
   leading whitespace before `<p>` tolerated) — equivalently for
   `CDW Product:` and `Synnex EU Product:`.

The contract is exactly `optional whitespace + optional exact "<p>" +
exact bounded known label`. The HTML support is deliberately narrow:

* the exact literal `<p>` only — no other tag (`<div>`, `<span>`,
  `<script>`, ...), no attributes (`<p class=...>`), no nesting
  (`<p><span>...`), no case variants, no text before `<p>` on the line
* NO BeautifulSoup, NO HTMLParser as a generic document parser, NO
  arbitrary tag stripping, NO generic HTML unescaping of the body
  (**FU4 correction, exact literals corrected by FU4-FU1, see
  §26.14 / §26.15:** the three exact observed paragraph-envelope
  entity literals — `&quot;` / the exact hexadecimal numeric LF entity
  (`"&" + "#xA;"`) / the exact hexadecimal numeric CR entity
  (`"&" + "#xD;"`) — are now decoded ONLY on the paragraph path;
  still no html.unescape, no other named entity (the unsupported
  `&nbsp;` / `&cr;` spellings are NOT decoded), no other numeric
  entity, no case/format variant, and the retained plain-text form is
  never decoded), NO arbitrary DOM text
  search, NO regex scraping of generic HTML
* the existing three-label allowlist remains the authority; unknown
  labels (with or without `<p>`) remain untrusted and ignored
* the existing strict bounded literal parser remains responsible for the
  section value; malformed content INSIDE a literal still fails that
  source closed; one malformed source does not destroy valid siblings;
  duplicate-label first-wins, max body size, exactly-one-network-call,
  no-redirect, no-proxy, and no-eval/no-literal_eval behavior all remain
* a trailing observed `</p>` after a COMPLETE bounded literal is the
  already-supported post-literal interstitial material (never parsed
  into data), provided it does not weaken malformed-in-literal rejection
* the raw body is never logged or persisted

The already-implemented source mapping (hybrid Ingram — vendorPartNumber
+ nested pricing.customerPrice / retailPrice / currencyCode + top-level
boolean availability + top-level Avl_Quantity; nested Synnex EU —
OnlineCheck.Header.CurrencyCode + OnlineCheck.Item.
ManufacturerItemIdentifier / UnitPriceAmount / AvailabilityTotal; CDW
`{Not Found}`; flat compatibility forms), the exact-MPN 2A binding, the
allowlist sensitive-metadata stripping (SessionId / BuyerAccountId /
SystemId and every other non-allowlisted field), persistence, and
Compact Quote projection are UNCHANGED. Expected normalized result for
the requested MPN (synthetic fixtures in tests): Ingram 1515.72 USD /
CUSTOMER_PRICE / OUT_OF_STOCK / quantity 0; Synnex EU 962.86 EUR /
OUT_OF_STOCK / quantity 0; CDW NOT_FOUND.

**Preserved production evidence (unchanged):** the Human Confirmed
semantic listings → Compact Quote architecture proven by run
f3a82fda-f708-4974-806e-d13a18482f96 remains accepted. That run's absence
of a ResearchFxSnapshot is explained by its inputs: frozen 4A had no
reportable non-USD bucket; Vendor returned zero usable observations due
to this parser failure; human-confirmed EUR evidence was added only
later through review. Historical replay must NOT perform a live ECB call
merely because a later human confirmation introduces EUR — that
zero-live historical contract remains frozen. A NEW run after this
repair obtains FX during execution because the Synnex EUR observation is
then a usable Vendor observation: the existing 4D-C execution-time
currency discovery requests EUR + USD from the FX provider, persists a
ResearchFxSnapshot when the provider succeeds, and the Synnex EUR
Compact Quote row receives its USD Equivalent from the persisted
snapshot (no FX production code altered by this phase).

**Proof levels (new tests):**

1. Scanner: exact `<p>Ingram Product:`, `<p>CDW Product:`,
   `<p>Synnex EU Product:` recognized (plus leading-whitespace
   tolerance, duplicate-label policy, unknown-label refusal, and the
   adversarial boundary set — `<div>` / `<span>` / `<script>` /
   `<p class="x">` / nested `<p><span>` / `prefix<p>` — all NOT
   recognized).
2. Full adapter: the paragraph-wrapped production-shaped body (single
   line per section; faithful hybrid Ingram + nested Synnex with fake
   sentinels) maps Ingram (exact MPN, 1515.72 USD CUSTOMER_PRICE,
   OUT_OF_STOCK, quantity 0) and Synnex EU (exact MPN, 962.86 EUR,
   OUT_OF_STOCK, quantity 0); CDW `{Not Found}`; bounded PARTIAL status;
   `retrieved_at` present; exactly one network call; sensitive sentinels
   absent from the normalized response; malformed-in-literal fails that
   source closed without destroying siblings.
3. Full `execute_research_run`: the paragraph-wrapped fixture travels
   through the actual Vendor adapter; both observations persist in the
   ResearchSupplementSnapshot; sensitive sentinel metadata absent from
   the persisted payload; Machine Price unchanged; Vendor supplemental
   only (paid search not suppressed; no semantic input).
4. Compact Quote historical replay (armed fail-fast live boundaries):
   Ingram Vendor row + Synnex EU Vendor row present, CDW row absent,
   USD Equivalent from the persisted FX snapshot, zero live replay I/O.
5. FX integration (existing 4D-C behavior, no FX production code
   altered): the usable Synnex EUR observation triggers execution-time
currency discovery requesting EUR + USD; the injected deterministic
provider's success persists a ResearchFxSnapshot; the Synnex EUR
Compact Quote row receives the persisted USD Equivalent.

### 26.14 PILOT-RELEASE-2-PROD-FIX1-FU4: Vendor Paragraph Entity
Decoding + Synnex Availability Wire Type

**Status: IMPLEMENTED / BLOCKED IN INDEPENDENT REVIEW (EXACT ENTITY
LITERAL DEFECT) / ENTITY LITERAL CONTRACT CORRECTED BY FU4-FU1
(§26.15) / PENDING FINAL REVIEW.** Bounded append-only
corrective follow-up on the FU3 commit (SHA
2f8c693bd428527d17fb7268eee1b0fba5c014e6). FU3 was independently
source-reviewed, deployed, and production-smoked; the smoke run
`a05a0aec-6f83-43d9-a3be-f9b41797f610` for
`MTFDKBA480TFR-1BC1ZABYYR` (Micron 7450 PRO 480GB NVMe M.2 Non-SED)
completed with `ResearchRunState.COMPLETED` but persisted the Vendor
result as `lookup_status=PARTIAL` / `observations=[]` / Ingram ->
MALFORMED_SECTION / CDW -> NOT_FOUND / Synnex EU -> MALFORMED_SECTION:
the FU3 outer-envelope fix worked (the scanner now recognizes exactly
`<p>Ingram Product:` / `<p>CDW Product:` / `<p>Synnex EU Product:`),
and the remaining defect was INSIDE the section literal
representation. Two exact production-wire differences, both corrected
with the narrowest bounded support; the FU3 implementation is retained
and no FU3 decision is redesigned. No deployment; no 8A caching; no
Vendor adapter redesign; final approval remains with the project lead
after independent GitHub review and a later production smoke.

**FU4-FU1 correction record (see §26.15):** the FU4 commit (SHA
1c8b96934c58fc567514bdc68b87da08b2cdcbe5) was BLOCKED in independent
review for one concrete production-fidelity defect: its
implementation, tests, and docs substituted the unsupported
named-entity spellings `&nbsp;` / `&cr;` for the two EXACT
production-observed hexadecimal numeric entities (the LF entity formed
by `"&" + "#xA;"` and the CR entity formed by `"&" + "#xD;"`) in
items 1 / 2 / 4 / 5 below. The entity-vocabulary statements in those
items are corrected in place; the Synnex availability wire-type
support (item 3) was independently reviewed and is acceptable — it is
preserved unchanged by FU4-FU1.

**1. Observed paragraph-envelope entity encoding (production-safe
probe; structure/vocabulary only).** A read-only production probe
established the exact entity vocabulary inside the section values of
the observed response (HTTP 200; `Content-Type: text/html;
charset=utf-8`; approximately 5485 bytes; 5 lines): Ingram — `&quot;`
(166 occurrences), the exact hexadecimal numeric LF entity formed by
`"&" + "#xA;"` (ampersand, hash, lowercase x, uppercase A, semicolon),
and the exact hexadecimal numeric CR entity formed by `"&" + "#xD;"`
(ampersand, hash, lowercase x, uppercase D, semicolon); CDW — none;
Synnex EU — `&quot;` (154 occurrences). No other named entity
(`&apos;` / `&lsquo;` / `&rsquo;` / `&amp;` / `&lt;` / `&gt;` /
`&nbsp;` / `&cr;` / ...) and no OTHER numeric entity (decimal, or any
other hex case/format spelling) was observed. (FU4-FU1 correction:
the FU4 text's statement "no numeric entity was observed" was FALSE —
two exact hexadecimal numeric entities WERE observed and are the
approved decodings; the `&nbsp;` / `&cr;` spellings were the
unsupported FU4 substitution.) Replacing EXACTLY `&quot;` -> `"`
(U+0022), the exact hex numeric LF entity -> LF (U+000A), the exact
hex numeric CR entity -> CR (U+000D) left no recognized HTML entity in
any section, and the UNCHANGED strict bounded literal parser then
succeeded: Ingram ->
mapping (27 top-level keys), CDW -> not_found, Synnex EU -> mapping
(2 top-level keys). The mapped production values are mutable upstream
commercial data (at probe time: Ingram 1515.72 USD CUSTOMER_PRICE
OUT_OF_STOCK quantity 0; Synnex 966.58 EUR LIST_PRICE — the old
962.86 EUR observation is historical and is NOT an acceptance
invariant; the production contract is exact requested MPN + valid
finite non-negative price + EUR + LIST_PRICE + correct documented
AvailabilityTotal semantics).

**2. Correction A (exact paragraph entity decoding, narrowest
possible; exact literals corrected by FU4-FU1).** On the FU3 exact
paragraph-envelope path only, the
section value text is normalized by EXACTLY three bounded literal
replacements — `&quot;` -> U+0022, the exact hexadecimal numeric LF
entity (`"&" + "#xA;"`) -> U+000A (LF), the exact hexadecimal numeric
CR entity (`"&" + "#xD;"`) -> U+000D (CR) — before the unchanged
strict recursive-descent parser runs. This is NOT html.unescape, NOT a
generic entity table, and NOT a regex over arbitrary entities: no
other named entity (`&apos;` / `&lsquo;` / `&rsquo;` / `&amp;` /
`&lt;` / `&gt;` / `&nbsp;` / `&cr;` / ...), no OTHER numeric entity
(decimal, or any other hex case/format spelling such as `&#10;` /
`&#13;` / `&#x0a;` / `&#x0d;` / `&#X0A;` / `&#X0D;` / `&#x000A;` /
`&#x000D;`), no case/format variant of the two approved hex numeric
entities is decoded (adversarially tested). The retained plain-text
section form is NEVER decoded (a literal `&quot;` / hex-LF-entity /
hex-CR-entity spelling in the legacy plain contract remains plain
text, unchanged). Unknown/unapproved entity forms inside an
authoritative literal remain fail-closed: a bare entity token outside
a string fails the strict grammar (MALFORMED_SECTION); inside a string
it is inert raw text, never interpreted. The DECODED values (`"` /
LF / CR) contain no `&` or `;` characters, so the decodings cannot
cascade into or create new entity-like sequences. The strict bounded
literal parser, the exact
`{Not Found}` marker, the three-label allowlist, duplicate-label
first-wins, max body size, exactly-one-network-call, no-redirect /
no-proxy / no-eval / no-literal_eval, and the trailing-`</p>`
interstitial contract (a trailing `</p>` after a COMPLETE parsed value
remains non-data interstitial material, exactly as FU3 defined) are
all UNCHANGED (re-proven). The raw Vendor body is still never logged,
persisted, put into exception detail, or exposed to user output.

**3. Correction B (Synnex nested string availability).** The current
real nested Synnex wire represents `OnlineCheck.Item.AvailabilityTotal`
as a non-negative integer, observed as the ASCII decimal digit STRING
`"0"` (with `UnitPriceAmount` observed as a numeric string — already
supported by the existing `_safe_decimal`, so no new generic price
behavior). A narrow Synnex-specific reading (`
_synnex_availability_total`) is applied to the REAL nested path only:
it accepts the existing `_safe_int` readings (non-negative int /
finite integral Decimal) plus exactly the production-observed string
form — ASCII decimal digits only, non-negative, no sign, no decimal
point, no exponent, no whitespace coercion, bounded digit length
(`"0"` -> 0, `"1"` -> 1, `"12"` -> 12). The GLOBAL `_safe_int`
contract is UNCHANGED: it still rejects strings everywhere else
(Ingram / CDW / flat Synnex compatibility form / all other code
paths). Rejected string forms (`"-1"` / `"+1"` / `"1.0"` / `"1e2"` /
`" 0 "` / `""` / `"abc"` / bool / float / list / dict / over-bounded
digit strings) fail to UNKNOWN with quantity None — no stock state is
fabricated.

**4. Expected normalized result (synthetic production-shaped
fixtures).** The new full-adapter and full-execution fixtures mirror
the CURRENT observed representation: exact `<p>` wrapper, `&quot;`-
encoded quoted strings, the exact hex numeric LF/CR entities
(`"&" + "#xA;"` / `"&" + "#xD;"`) in a non-authoritative
synthetic Ingram field, CDW `{Not Found}`, nested Synnex OnlineCheck
with fake SessionId / BuyerAccountId / SystemId sentinels, Synnex
`UnitPriceAmount` as a numeric string, Synnex `AvailabilityTotal` as
the digit string `"0"`. Deterministic synthetic values: Ingram
1515.72 USD CUSTOMER_PRICE OUT_OF_STOCK quantity 0; Synnex 962.86 EUR
LIST_PRICE OUT_OF_STOCK quantity 0 (explicitly synthetic — the live
production price is mutable commercial data and is NOT a permanent
expected production price); CDW NOT_FOUND. Sensitive fake sentinel
values and field names, and the entity spellings, remain absent from
the normalized output and the persisted supplement where the existing
contract requires absence.

**5. Proof levels (new tests; corrected by FU4-FU1).** (1) Exact
observed entity decoding on the paragraph path (Ingram `&quot;` /
exact hex numeric LF entity / exact hex numeric CR entity; Synnex
`&quot;`; CDW `{Not Found}` unchanged) through the unchanged bounded
grammar and source mappers. (2) Adversarial non-decoding: `&apos;` /
`&lsquo;` / `&rsquo;` / `&amp;` / `&lt;` / `&gt;` / `&nbsp;` /
`&cr;`, arbitrary decimal numeric entities, equivalent numeric
representations of the approved code points (`&#10;` / `&#13;` /
`&#x0a;` / `&#x0d;` / `&#X0A;` / `&#X0D;` / `&#x000A;` / `&#x000D;`),
and case variants (`&Quot;` / `&#xa;` / `&#XA;` / `&#xd;` / `&#XD;`)
remain raw and fail-closed; the
plain-text form is never decoded; FU4 did NOT become generic HTML
handling. (3) The full FU3 HTML boundary set (`<div>` / `<span>` /
`<script>` / `<p class="x">` / `<p><span>` / `prefix<p>` / `<p> `
/ `<P>` / `<p >` / `<p/>` / unknown labels / wrong case) is retained
and re-proven unchanged. (4) Faithful production-shaped full adapter
mapping (entity-encoded wire). (5) Synnex availability string grammar
(accept `"0"` / positive digit string; reject signed / decimal /
exponent / whitespace / empty / text / non-string / over-bounded;
flat form unchanged; global `_safe_int` still rejects strings).
(6) Full `execute_research_run` integration on the encoded fixture:
one Vendor call, COMPLETED, PARTIAL, both observations, CDW NOT_FOUND,
sensitive metadata absent from the persisted supplement, Machine
Price immutable (deterministic zero-public-search fixture; zero
buckets; no vendor value in the artifact), supplemental-only vendor
(paid search not suppressed; no semantic input; no public-search
authority; no human-confirmed authority). (7) FX: the usable Synnex
EUR observation triggers the EXISTING 4D-C execution-time currency
discovery (EUR + USD requested; deterministic injected provider;
ResearchFxSnapshot persisted) — no FX production code modified.
(8) Compact Quote historical replay (armed fail-fast zero-live
boundaries exactly as FU3): Ingram + Synnex Vendor rows, CDW row
absent, USD Equivalent from the persisted ResearchFxSnapshot.

**6. Unchanged.** Machine Price authority; Reviewed Price authority;
human-confirmed authority; public-search authority; semantic matching
authority; 2A exact / normalized-exact binding semantics;
orchestration; Compact Quote authority/projection semantics; replay
semantics; FX production implementation; historical replay
zero-live behavior; Search/Page/Vendor/FX/Semantic replay
boundaries; migrations/models; dependencies; no 8A caching.

### 26.15 PILOT-RELEASE-2-PROD-FIX1-FU4-FU1: Exact Observed Vendor
Entity Correction

**Status: IMPLEMENTED / PENDING FINAL REVIEW.** Bounded append-only
corrective follow-up on the FU4 commit (SHA
1c8b96934c58fc567514bdc68b87da08b2cdcbe5), which was BLOCKED in
independent review for one concrete production-fidelity defect: the
FU4 implementation, tests, and docs substituted the unsupported
named-entity spellings `&nbsp;` / `&cr;` for the two EXACT
production-observed hexadecimal numeric entities inside the
paragraph-envelope section values. The FU4 implementation is retained;
ONLY the two wrong entity literals (plus the directly necessary
tests/docs) are corrected. No deployment; no 8A caching; no Vendor
adapter redesign; no Synnex change; final approval remains with the
project lead after independent GitHub review and a later production
smoke. (Canonical spec: this section.)

**1. The exact observed entity vocabulary (production evidence).**
The production-safe read-only probe observed EXACTLY: Ingram —
`&quot;` (166 occurrences), the exact hexadecimal numeric LF entity
formed by `"&" + "#xA;"` (ampersand, hash, lowercase x, uppercase A,
semicolon), and the exact hexadecimal numeric CR entity formed by
`"&" + "#xD;"` (ampersand, hash, lowercase x, uppercase D,
semicolon); CDW — none; Synnex EU — `&quot;` (154 occurrences). The
FU4 spellings `&nbsp;` and `&cr;` are NOT supported by production
evidence; they were the FU4 defect. The FU4 statement "no numeric
entity was observed" is false and is corrected here: two exact
hexadecimal numeric entities WERE observed and are approved; no OTHER
numeric entity is approved.

Correct security boundary:

* APPROVED (decoded ONLY on the FU3 exact paragraph-envelope path):
  * `&quot;` -> U+0022 (literal double quote)
  * the exact 5-character hex numeric LF entity
    (0x26 0x23 0x78 0x41 0x3B) -> U+000A (LF)
  * the exact 5-character hex numeric CR entity
    (0x26 0x23 0x78 0x44 0x3B) -> U+000D (CR)
* UNAPPROVED (never decoded; adversarially tested): every other named
  entity (including `&nbsp;` / `&cr;` / `&Quot;`), every other
  decimal numeric entity (e.g. `&#10;` / `&#13;` / `&#65;` / `&#39;`
  / `&#38;` / `&#60;` / `&#62;` / `&#123;` / `&#125;`), every other
  hexadecimal numeric entity / equivalent representation (e.g.
  `&#x0a;` / `&#x0d;` / `&#X0A;` / `&#X0D;` / `&#x000A;` /
  `&#x000D;`), and every case/format variant of the two approved hex
  numeric entities (e.g. `&#xa;` / `&#XA;` / `&#xd;` / `&#XD;`).

**2. The corrected production decode table.**
`product_intelligence/providers/internal_vendor.py`
`_PARAGRAPH_ENTITY_LITERALS` now contains EXACTLY:

```
("&quot;", '"'),
(exact 5-character hex numeric LF literal formed by "&" + "#xA;", "\n"),
(exact 5-character hex numeric CR literal formed by "&" + "#xD;", "\r"),
```

i.e. `&quot;` -> U+0022, the exact hex numeric LF entity -> U+000A
(LF), the exact hex numeric CR entity -> U+000D (CR). The two hex
numeric literals are verified character-by-character in the production
module (import-time self-check: `assert "&#xA;" == "&" + "#xA;"`,
`assert "&#xD;" == "&" + "#xD;"`, plus exact 5-codepoint sequences
0x26/0x23/0x78/0x41/0x3B and 0x26/0x23/0x78/0x44/0x3B) and in a
dedicated test. NO `&nbsp;` decoding, NO `&cr;` decoding, no
html.unescape, no `html` import, no HTMLParser, no BeautifulSoup, no
arbitrary numeric-entity regex. Decoding remains ONLY on the exact FU3
paragraph-envelope path; the retained plain-text section contract
remains undecoded. All other FU4 behavior (scanner, strict bounded
literal grammar, `{Not Found}` marker, three-label allowlist,
duplicate-label first-wins, max body size, one network call,
no-redirect / no-proxy / no-eval / no-literal_eval) is unchanged.

**3. Test corrections (test preservation maintained).** No pre-FU4
(and no FU4) test node is deleted or renamed. The FU4 node
`test_nbsp_and_cr_entities_decoded_to_lf_and_cr` is RETAINED but its
assertion purpose is corrected: it now proves `&nbsp;` and `&cr;` are
NOT decoded (the node's name records the rejected FU4 contract). New
FU4-FU1 nodes prove: exact `&quot;` decoding on the paragraph path
(retained), the exact hex numeric LF entity -> LF, the exact hex
numeric CR entity -> CR, the decode table's exact composition with
character-by-character literal verification, non-decoding of
`&nbsp;` / `&cr;` (retained node), non-decoding of arbitrary decimal
numeric entities (retained, fail-closed), non-decoding of equivalent
numeric representations, non-decoding of case variants of the
approved hex entities, and plain-form non-decoding of all approved
spellings (strengthened). The faithful production-shaped
synthetic fixtures (provider + execution) use the corrected exact
entity encoding (`&quot;` + exact hex numeric LF/CR entities) and
still produce: Ingram exact MPN / 1515.72 USD / CUSTOMER_PRICE /
OUT_OF_STOCK / quantity 0; CDW NOT_FOUND; Synnex EU exact MPN /
deterministic synthetic EUR price / LIST_PRICE / OUT_OF_STOCK /
quantity 0. The full `execute_research_run` integration fixture uses
the same corrected exact entity encoding.

**4. Synnex preserved (not redesigned).** The FU4 Synnex
implementation was independently reviewed and is acceptable:
`_synnex_availability_total()` and its narrow nested-path behavior
are preserved unchanged. `OnlineCheck.Item.AvailabilityTotal` real
production value (type str, value `"0"`) continues to be accepted
only as narrow ASCII digits-only strings on the REAL nested Synnex
path; the GLOBAL `_safe_int` remains unchanged and continues to
reject strings; the flat Synnex compatibility form continues to
reject string quantities.

**5. Unchanged.** Machine Price authority; Reviewed Price authority;
human-confirmed authority; public-search authority; semantic matching
authority; 2A exact / normalized-exact binding semantics;
orchestration; Compact Quote authority/projection semantics; replay
semantics; FX production implementation; historical replay
zero-live behavior; Search/Page/Vendor/FX/Semantic replay
boundaries; migrations/models; dependencies; no 8A caching; no
deployment.


### 26.16 SEMANTIC-QWEN38-PROMOTION-REGRESSION-A1: Semantic PRIMARY
Promotion-Regression Harness

**Status: IMPLEMENTED / APPROVED / FROZEN** (independent review;
frozen HEAD `b26b50e4a5ea1ae6be7fae4e8d680a6d3a880331`). Bounded
evaluation-only phase. It builds a SEPARATE promotion-regression
facility for semantic PRIMARY candidates and changes NOTHING in the
production semantic route, prompt, parser, eligibility rules,
aggregation, or review authority. It is not authorization to promote
`amax/qwen3.8-27b`; promotion remains a human-reviewed decision.
The frozen A1 evidence was the input to the separately reviewed B1
promotion (§26.17). (Operator documentation:
`docs/SEMANTIC_PROMOTION_REGRESSION.md`.)

**1. Two questions, two facilities.** Semantic QUALIFICATION
(frozen; `evaluation/semantic_corpus/cases.json`, 64 cases, prompt v1.1
FULL SHA256 `f50e5584659f953ce73a97ccc8bc1ff487fbeeb37e2e0a72e52210613aeab1ff`,
corpus SHA256 `3c21d6fcd4eefa5cc383792abfd9308bd5c03315834c8ffdffd0f6a2b3619ca1`)
asks whether a model passes the frozen benchmark. PROMOTION REGRESSION
(this phase) asks whether a formally qualified challenger, considered for
the production PRIMARY seat, respects the production-shaped
semantic/execution authority boundaries. The two corpora, runners,
artifacts, and verdict concepts are separate and must remain separate in
source and documentation. `amax/qwen3.8-27b` passing FULL qualification
does not itself change production.

**2. Frozen production authority is NOT owned by the LLM and the harness
must test the architecture, not bypass it.** The harness replays the real
production chain per case:

```
deterministic matching      real research.matching.assess_listing_identity
        |
        v
semantic eligibility        frozen FU3B states via the public pure
                            research predicate
                            is_human_review_eligible_assessment + the
                            usable-evidence title gate
        |
        v
semantic model              ONE harness-owned transport attempt per
                            eligible case; prompt v1.1 built by the
                            shared contract; strict contract parser /
                            validator; exact provider-reported model
                            identity; frozen transport status mapping
                            (reused object, not forked)
        |
        v
semantic decision           MATCH / NO_MATCH / UNCERTAIN or bounded
                            failure status
        |
        v
execution disposition       MATCH -> EvidenceDecision.AI_ASSISTED_MATCH
                            (AI-assisted evidence only); NO_MATCH /
                            UNCERTAIN -> UNDECIDED (no authority). The
                            original ListingIdentityAssessment is never
                            mutated; frozen 4A still excludes the
                            underlying REJECTED assessment as
                            IDENTITY_NOT_ACCEPTED.
```

A case whose declared deterministic state is not realized by the real
frozen chain fails the run closed (a defective case measures nothing).

**3. Evaluation-only model authorization.** The harness authorizes
EXACTLY `amax/nemotron-3-super` (role `production_primary`, baseline)
and `amax/qwen3.8-27b` (role `challenger`) for PRIMARY-seat regression
runs; any other provider/model fails closed. This is NOT production
configuration: the frozen `SemanticRuntime` is untouched —
`validate_runtime_config` still rejects the challenger, and a
`SemanticRuntimeResult` still cannot carry a challenger-named requested
primary (self-validation). (Present-tense note, superseded by §26.17:
after the B1 promotion the pinned production primary is
`amax/qwen3.8-27b` and the non-pinned rejected model in either seat is
the demoted former primary `amax/nemotron-3-super`; the harness
authorization list above is frozen A1 evidence tooling and did not
itself change.) The fallback model
(`vllm-262k/Qwen3.6-27B-262K`) is not a PRIMARY promotion candidate and
is not authorized by this harness. No environment variable, CLI flag, or
code path selects a production model outside the frozen route.

**4. No fallback chain in the harness.** Each model is tested in the
PRIMARY seat with exactly one transport attempt per eligible case: no
retry, no second model, no reinterpretation of an invalid first
response. Production fallback semantics (execution failure only, never
semantic disagreement) remain the frozen runtime's contract and are
covered by the runtime's own tests; the harness mirror-locks its
single-attempt interpretation against the real runtime's primary
attempt over the full outcome matrix (every transport error code,
identity drift, empty, malformed, schema-invalid, valid decisions).
Run-fatal transport errors (frozen transport vocabulary) abort the run
after recording the failed case, mirroring the qualification runner.

**5. Corpus (v1, 22 cases, synthetic).** Categories A..J are each
enforced present by the loader: A deterministic ACCEPTED (exact +
normalized-exact; no semantic call); B explicit MPN_MISMATCH (no
semantic call; cannot become AI_ASSISTED_MATCH); C TITLE_TEXT eligible;
D SKU_FIELD eligible; E PARTIAL_MPN_ONLY eligible (AI-assisted only);
F no usable evidence (source NONE, or eligible state without a product
title; no semantic call); G accessory/compatible-with/replacement/
multipack traps; H capacity/form-factor/interface conflicts; I
normalized exact identity + trailing description — GENERAL contracts
deliberately NOT copying SMQ-0053 / SMQ-0062 (loader-locked: the
frozen cases' distinctive literals must not appear in category I);
J decision mapping (the corpus must contain called cases expecting
MATCH, NO_MATCH, and UNCERTAIN). Each case carries a
corpus-declared `match_is_unsafe` fact (a model MATCH on that case is
an unsafe positive-authority expansion); the harness contains no
per-case-ID logic and no model-specific exceptions. Case changes
follow the evaluation-truth rules (A/B/C/D reasons only; "the
challenger failed this case" is not a valid reason).

**6. Comparison and promotion gates.** The two-run comparison is
machine-readable with per-case rows: case ID, category, expected
authority outcome, both models' decisions/confidences/validity, model
disagreement, safety-sensitive disagreement, positive authority
expansion (challenger MATCH while primary NO_MATCH/UNCERTAIN — a
MANDATORY human-review condition because the challenger expands
positive authority relative to production), conservative challenger
regression (primary MATCH while challenger NO_MATCH/UNCERTAIN — recall
loss), unsafe/false MATCH per model, reason codes, bounded provenance
(no raw model bodies in the comparison artifact). Provenance
compatibility (corpus version + SHA256, prompt version + SHA256,
case order, generation parameters, timeout, completed status) fails
closed. The harness computes objective gate facts and NEVER declares a
winner: no scores, ranks, or latency/token/accuracy weighting. A run's
promotion gate fails on: invalid output violating the response
contract; any transport call on a no-call case (semantic override of
deterministic authority); false MATCH on a `match_is_unsafe` case;
disposition/authority-boundary violation (MATCH anything other than
AI_ASSISTED_MATCH; non-MATCH producing authority; deterministic state
changed); or provenance incompatibility/corruption.

**7. Reviewer-authorized boundary exception (exact allowlist; A1-FU2
least privilege).** The 2A-era guard
`tests/research/test_research_identity_boundaries.py::test_no_outer_layer_is_wired_to_the_identity_primitive_yet`
forbade any `product_intelligence/evaluation` file from importing
`product_intelligence.research`. The promotion-regression harness must
replay the real deterministic identity chain, so the original
evaluation->research boundary was deliberately narrowed by an
architecture-reviewer authorized exception (recorded during A1,
authorized and exacted as a two-file allowlist in A1-FU1, and
tightened to one file in A1-FU2) for EXACTLY ONE file:
`product_intelligence/evaluation/semantic/promotion_regression.py` —
the one module that actually imports research.
`promotion_regression_cli.py` receives NO exception because it does
not directly depend on research (it consumes the harness module); if
the CLI or any other evaluation module later needs a direct research
dependency, that requires a NEW explicit architecture-review
decision. The exception is an explicit, reviewer-authorized governance
decision — not an implementer-authorized redesign, and not a
prefix/glob/regex match: no other `promotion_regression_*` module, in
any location, is covered without a new reviewer decision. The guard
carries the immutable allowlist
`PROMOTION_REGRESSION_RESEARCH_EXCEPTION`, and mechanical tests
(`test_only_promotion_regression_may_wire_research`,
`test_promotion_regression_exception_is_an_exact_allowlist`) lock that
the allowlist holds exactly one entry, that every OTHER evaluation
file remains research-independent, that the excepted file imports
research but never execution/runs/web/providers/Django, and that
arbitrary future `promotion_regression_*` names are NOT automatically
exempt. Dependency direction is preserved and locked both ways: the
harness imports research contracts; no production module references
`promotion_regression` (source-scanned).

**8. Unchanged.** Production semantic route constants (PRIMARY
`amax/nemotron-3-super`; FALLBACK `vllm-262k/Qwen3.6-27B-262K`;
temperature 0.0 exact float; max_tokens 32768); the frozen
qualification corpus and prompt v1.1 (SHA256 re-locked by new tests);
the strict parser/validator; the fallback allowlist; FU3B eligibility
and disposition semantics; 4A aggregation; Reviewed Price; human
review; HARD_CONFLICT working-quote policy; migrations/models;
dependencies; no deployment.

**9. Live execution is human-authorized.** Implementation and tests
use fake/recorded transports only. The live Nemotron-vs-Qwen run and
comparison are executed by the human reviewer with the exact commands
documented in `docs/SEMANTIC_PROMOTION_REGRESSION.md`; the resulting
artifacts (gitignored) plus the pushed diff are the input to the
human promotion decision.

### 26.17 SEMANTIC-QWEN38-PRODUCTION-PROMOTION-B1: Production PRIMARY
Route Promotion (qwen3.8-27b)

**Status: IMPLEMENTED / PENDING FINAL REVIEW.** Bounded production-route
phase implementing the reviewer-authorized promotion of
`amax/qwen3.8-27b` to the production semantic PRIMARY seat, on the
frozen A1 HEAD `b26b50e4a5ea1ae6be7fae4e8d680a6d3a880331`. It is a
route-identity change ONLY.

**1. Promotion basis (frozen evidence).** (a) Frozen 64-case FULL
qualification of `amax/qwen3.8-27b`: 100% valid output, 96.88% decision
accuracy, 100% MATCH precision, 85.71% MATCH recall, 0 false MATCH,
safety cost 2, all hard gates PASS — exactly matching the historical
qualified Nemotron FULL-run headline metrics and wrong-case IDs
(SMQ-0053, SMQ-0062) under the same frozen corpus/prompt/settings. (b)
A1 production-shaped live promotion regression (22 processed cases, 16
semantic-called cases): both `amax/nemotron-3-super` and
`amax/qwen3.8-27b` passed ALL six objective promotion gates. (c) Human
review of the two surfaced disagreements: SPR-0009 (expected UNCERTAIN;
Nemotron NO_MATCH/HIGH, Qwen 3.8 UNCERTAIN/LOW; no authority expansion)
and SPR-0020 (expected MATCH; Nemotron UNCERTAIN/LOW, Qwen 3.8
MATCH/MEDIUM; the candidate SKU provides the exact target identity and
the normalized title is aligned and non-conflicting, so the
AI_ASSISTED_MATCH authority is supported). Both CLOSED: no promotion
blocker.

**2. Route after B1 (the ONLY route change).**

| Setting | Value |
| --- | --- |
| PRIMARY | `amax` / `qwen3.8-27b` |
| FALLBACK | `vllm-262k` / `Qwen3.6-27B-262K` |
| temperature | `0.0` (exact float) |
| max_tokens | `32768` |

Only the PRIMARY model changed. The fallback topology is FROZEN:
Nemotron is deliberately NOT made the production fallback because
Nemotron and Qwen 3.8 share provider `amax`. The production fallback
exists for EXECUTION FAILURE (provider-level redundancy), not semantic
disagreement; keeping `amax -> vllm-262k` preserves that redundancy.

**3. Invariants (unchanged).** Fallback on execution failure only, via
the existing explicit allowlist; a valid primary decision (MATCH /
NO_MATCH / UNCERTAIN) is FINAL; no disagreement fallback, no
low-confidence fallback, no reason-code fallback, no secondary-model
voting, no consensus evaluation, no retry-to-Nemotron, no
caller-selectable models, no model override parameters, no production
model tournament logic, no third provider. Generation contract
(temperature 0.0 exact float, max_tokens 32768, request-timeout
behavior, prompt v1.1, parser, response schema, enums, validation,
reason-code handling) unchanged. Authority/execution contract
(deterministic identity matching, semantic eligibility —
`_is_semantic_eligible`, `_has_usable_evidence` — `_map_semantic_decision`,
AI_ASSISTED_MATCH = MATCH only, NO_MATCH/UNCERTAIN produce no semantic
authority, HARD_CONFLICT handling, Working Quote policy, Reviewed Price
policy, human confirmation semantics, public 4A aggregation with
AI_ASSISTED_MATCH excluded, commercial/vendor authority, execution
evidence semantics) unchanged.

**4. Implementation scope.** Exactly one production file:
`product_intelligence/semantic/runtime.py` (`PRIMARY_MODEL` constant +
the module docstring's pinned-route block). No refactor, no renamed
constants, no generalized model routing system, no
environment-configurable PRIMARY/FALLBACK models. The route remains
code-pinned and non-caller-configurable: `validate_runtime_config`
rejects every other model in both seats — including the demoted
`amax/nemotron-3-super` — and `SemanticRuntimeResult` self-validates
the pinned requested primary and attempt provenance.

**5. Frozen A1 artifacts untouched.** Qualification corpus, prompt v1.1,
strict parser/validator, `evaluation/semantic_promotion_regression/
cases.json`, the promotion-regression harness behavior, and the
harness's evaluation-only authorized-model catalog (nemotron role
`production_primary` / qwen3.8-27b role `challenger` — frozen A1
evidence tooling, not production routing). No special-casing of
SPR-0009 / SPR-0020 / SMQ-0053 / SMQ-0062: promotion is a route
change, not corpus tuning.

**6. Model status after B1.** `amax/nemotron-3-super` remains a
qualified/reference model (full-qualification catalog entry and
promotion-regression baseline) but is neither the production primary
nor the production fallback. `vllm-262k/Qwen3.6-27B-262K` remains the
sole production fallback.

**7. Test updates.** Route-identity freeze assertions only, moved from
Nemotron to the reviewer-approved Qwen 3.8 primary:
`tests/semantic/test_runtime.py`,
`tests/execution/test_semantic_integration.py`,
`tests/execution/test_4d_a_direct_acquisition.py`,
`tests/execution/test_review_candidate_persistence.py`,
`tests/web/test_cross_layer_regression.py`,
`tests/evaluation/semantic/test_promotion_regression_authority.py`,
`tests/evaluation/semantic/test_benchmark_runner.py`. All other
safety/authority/fallback tests unchanged in strength. Two route pins
strengthened (additive): the demoted former primary is rejected in the
PRIMARY seat, and it is ALSO rejected in the FALLBACK seat (provider
redundancy). No test deleted, renamed, skipped, xfail'd, deselected,
or weakened.

**8. Unchanged.** Production FALLBACK identity; fallback eligibility
allowlist; generation settings; prompt/parser/corpus; authority
mapping; migrations/models; dependencies; no deployment; no live model
calls in the implementation phase (promotion evidence is the already
frozen, independently reviewed A1 record).

### 26.18 PRODUCT-INTEL.8A-FX-A1: Canonical ECB Observation Cache

**Status: IMPLEMENTED / PENDING FINAL REVIEW.** First safe caching slice
of the 8A series: cross-run reuse of the canonical production ECB daily
FX observation set. Canonical spec authority for this phase; decision
record AD-064; design lineage: 8A-PRE audit (APPROVED / COMPLETE),
8A-FX-DESIGN (APPROVED / COMPLETE), 8A-FX-DESIGN-FU1 (APPROVED / FROZEN
as design). Starting SHA 55d1879a03da3dc6163a28c9524b5ef0396b76b3.

**1. Purpose and boundary.** Replaces ONLY external acquisition of ECB
FX evidence under the approved freshness contract. It MUST NOT cache or
reuse: public product pages; search/Serper results; vendor observations;
semantic model responses; identity decisions; Machine Price; Reviewed
Price; human-review state; comparable research; rendered reports;
negative/failure results. FX remains DISPLAY-SUPPLEMENTAL only. No
numeric TTL is introduced; the policy is proof-instant +
Europe/Brussels weekend-closure.

**2. Eligibility (canonical default only).** Cache is active ONLY on the
canonical production default ECB acquisition. The decision is made from
the existing orchestration API semantics
(`execute_research_run(..., fx_provider=None)`) at the canonical-default
construction site in `execution/orchestration.py::_try_fetch_fx_rates`:

    fx_cache_eligible = fx_provider is None      # BEFORE construction
    if fx_provider is None:
        fx_provider = EcbFxProvider()            # existing line

ANY explicitly injected provider (a fake, an `EcbFxProvider` instance,
a subclass, a wrapper, any FxProvider-compatible object) unconditionally
bypasses the cache (zero store reads, zero store writes) and executes
the existing live acquisition contract byte-for-byte. Provider class
identity is NOT business/cache semantics: no `isinstance` /
`issubclass` / class-identity check exists anywhere in the cache path
(mechanically guarded by test). Existing injected-provider tests remain
on the existing live contract by construction.

**3. USD-only contract (preserved).** Currency discovery
(`_get_required_fx_currencies`) precedes any cache work. USD-only
reports -> zero FX provider acquisition -> zero FX cache lookup -> no
`ResearchFxSnapshot`. The cache is not a reason to touch the store for
USD-only runs.

**4. Feed identity.** One explicit stable canonical feed identifier for
the production ECB daily reference-rate feed:
`providers/fx.py::FX_FEED_ID_ECB_DAILY = "ecb:eurofxref-daily"`. It is
the semantic external feed, not a provider class name, and is not
user-configurable. Endpoint ownership stays in `providers/fx.py`
(`https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml`); the
binding (endpoint + `provider_id="ECB"` + `base_currency="EUR"`) is
mirror-locked by test.

**5. Store (new cross-run content model).** `runs.FxObservationStore`
(migration 0011). Represents cross-run ACQUISITION CONTENT, not run
evidence. It does NOT overload `ResearchFxSnapshot`,
`PriceIntelligenceSnapshot`, `ExecutionEvidenceRecord`,
`ResearchSupplementSnapshot`, or Django's `CACHES` framework. Fields:
`id` (UUID pk), `feed_id`, `provider_id`, `base_currency`,
`observation_date`, `content_sha256`, `payload` (JSONField, FULL
document through the reused fail-closed FX codec V1),
`original_retrieved_at` (IMMUTABLE provider instant), `last_proven_at`
(timezone-aware proof instant, never truncated to a date), `created_at`.
`UniqueConstraint(feed_id, observation_date, content_sha256)`;
latest-selection index `(feed_id, -observation_date, -last_proven_at)`;
non-empty check constraints. NO `ResearchRun` relation (not run-scoped;
no cascade; a failed run publication leaves a successfully persisted row
intact — it must not imply the run completed).

**6. Content identity (pure research contract).**
`research/fx_cache_contract.py` (stdlib only; no Django, no provider,
no I/O). `fx_document_content_sha256` computes a deterministic canonical
SHA-256 from a byte-stable JSON representation of the FULL PARSED rate
observation: provider_id + base_currency + observation_date + rates
sorted by currency code with exact `str(Decimal)` textual
representation (no raw ECB XML hashed or persisted; no Python
dict-order dependence; no locale dependence; no float conversion). A
correction/republication for the same `observation_date` with changed
rates yields a different digest and therefore a distinct content
identity (distinct row; the superseded revision remains
VALID_HISTORICAL and is never overwritten).

**7. Projection (not cache identity).** `project_required_rates`
projects the FULL stored/fetched set to `required_currencies` (document
order preserved; mirrors the provider's own post-parse filter,
mirror-locked). `required_currencies` is a projection input, not cache
identity — no per-requested-currency-set cache entries. On both LIVE and
CACHE_HIT: full observation -> project/filter -> existing per-run FX
codec -> `ResearchFxSnapshot`. The run payload is byte-identical across
the two paths for the same document.

**8. Freshness contract (pure).**
`no_publication_possible_between(proof_instant T, use_instant N, zone)`
— no I/O; no Django; no provider; tz-aware inputs only (naive/malformed
-> fail closed with `TypeError`); `T > N` -> `ValueError`; handles
CET/CEST via `zoneinfo`; correct across DST boundaries; never uses the
system-local timezone implicitly. Uses the ACTUAL proof instant T and
current instant N; never reduces `last_proven_at` to a date before
evaluating. Reuse is possible only while EVERY Europe/Brussels calendar
day overlapping the CLOSED interval [T, N] is Saturday/Sunday (the
weekend stretch [Saturday 00:00, Monday 00:00 CET/CEST)). Working days:
NO reuse ever (a proof on a working day covers no N >= T; do not reuse
merely because a live proof occurred earlier that day — perform live
acquisition). TARGET closing days: no authoritative calendar contract,
so treated conservatively like working days (no invented holiday
calendar). This is an explicit conservative A1 product freshness policy
based on ECB's documented regular publication schedule (reference rates
normally updated on working days around 16:00 CET, except TARGET closing
days); it does NOT describe or encode the stronger external claim that
ECB is physically incapable of an exceptional weekend correction.

**9. LIVE path (canonical, reuse not allowed).** (1) determine required
currencies; (2) ONE full-set ECB fetch (`requested_currencies=None`);
(3) validate the returned observation (feed binding `provider_id="ECB"`
/ `base_currency="EUR"` — contract defect propagates); (4) calculate the
canonical digest; (5) persist/reconcile the cross-run content entry in
the store's OWN transaction (before the run's atomic final
publication); (6) set/update `last_proven_at` only for a successful
live observation; (7) project requested currencies; (8) write the
current run's `ResearchFxSnapshot`; (9) acquisition = LIVE. The original
provider `retrieved_at` is preserved (never replaced by cache insertion
time or run-publication time).

**10. CACHE_HIT path (canonical, approved reuse).** (1) load the latest
valid cached observation for the canonical feed; (2) decode and validate
it (fail closed); (3) apply the pure freshness predicate using its
ACTUAL `last_proven_at`; (4) if reuse allowed: ZERO ECB calls, preserve
the original provider `retrieved_at`, project the current required
currencies from the full cached set, write this run's own
`ResearchFxSnapshot`, acquisition = CACHE_HIT. The cache-served instant
is never claimed as provider retrieval time. CACHE_HIT must never
masquerade as LIVE.

**11. Failure semantics (fail closed).** Preserved: live
`FxProviderError` is nonfatal (no FX snapshot if no valid evidence
obtained; run can complete). Programming/contract defects propagate.
IMPORTANT correction: a MALFORMED OR UNSUPPORTED EXISTING CACHE PAYLOAD
IS NOT A CACHE MISS. If an `FxObservationStore` row exists and its
codec/integrity validation fails (malformed rate payload, unsupported
schema version, invalid digest, provider/base mismatch, impossible
stored timestamps), the error PROPAGATES / fails closed — it is NOT
catched into a silent live fallback, and the corrupted row is not
deleted. Cache lookup with NO ROW is an ordinary miss -> live
acquisition. Uniqueness race on insert: bounded reconciliation is
permitted — fetch the competing row, validate EXACT semantic/content
identity, converge (convergent conditional `last_proven_at` re-proof) if
identical, otherwise fail closed. Arbitrary `IntegrityError` is NOT
treated as automatically benign; only the specifically understood
uniqueness race is reconciled. Other database/storage errors propagate.
Cache persistence failure after a successful live provider fetch
propagates (the cache is not silently pretended to have succeeded). No
distributed locking; no `select_for_update` as a fake cross-process
guarantee.

**12. Concurrency / idempotency.** Two concurrent runs may both
live-fetch the same observation (acceptable; the store converges on ONE
canonical content identity via the deterministic uniqueness constraint).
If ECB content differs (a correction), distinct content hashes
represent distinct observations/content revisions — never overwrite a
different correction merely because `observation_date` matches.

**13. Per-run provenance (additive).** `ResearchFxSnapshot.acquisition`
(CharField, choices LIVE/CACHE_HIT, default LIVE, editable=False).
Describes how THIS run obtained its FX evidence; does not change the FX
payload or authority. REPLAY is NOT a stored acquisition value — it is a
read behavior: `compact_quote_replay` reads the existing run snapshot
with zero live provider calls and zero cache acquisition, and never
mutates the persisted LIVE/CACHE_HIT value. The migration preserves all
existing `ResearchFxSnapshot` rows as LIVE.

**14. Run publication atomicity.** The per-run `ResearchFxSnapshot`
remains part of the run's final atomic publication. The cross-run store
has different ownership/lifetime from the run. If the live ECB fetch
succeeds, the cache content is persisted, and a later current-run
publication fails, the cache content remains legitimate external
evidence (its persistence transaction completed) and must not falsely
imply the `ResearchRun` completed. No run authority is attached to the
cache row.

**15. Web presentation (smallest additive change).** The report shows,
in clear bounded form, where this run's FX evidence exists (both ALLOWED
and DENIED replay branches): the ECB observation date, the original
provider retrieval time, and whether the current run used LIVE or
CACHE_HIT acquisition. It does NOT redesign the report and does NOT
expose internal DB IDs, raw cache keys, internal exception information,
the provider raw body, or implementation details. The GET path remains
zero-live and never reads the cross-run store.

**16. Explicitly out of scope for A1.** Caching of public pages,
search/Serper, vendor, semantic responses, market listings, or any
second feed; negative caching; a `force_fresh` primitive (a later 8A
decision); store retention/cleanup policy (the store is naturally
bounded at ~1 row per working day + corrections); any numeric TTL; any
TARGET-calendar data dependency; any publication-time assumption.

**17. Authority invariants (unchanged, re-proven).** Frozen 4A public
market authority; Machine Price; Reviewed Price; deterministic identity;
semantic identity; AI_ASSISTED_MATCH authority; vendor supplemental
authority; human-confirmed authority; HARD_CONFLICT behavior; semantic
production route (PRIMARY amax/qwen3.8-27b; FALLBACK
vllm-262k/Qwen3.6-27B-262K; Nemotron-3-Super qualified/reference only);
fallback semantics; review semantics. Regression: Machine Price snapshot
bytes identical across LIVE / CACHE_HIT / FX-absent; compact-quote USD
equivalent identical LIVE vs CACHE_HIT for the same document.

**18. Files.** Production: NEW `research/fx_cache_contract.py`,
`execution/fx_observation_cache.py`; `runs/models.py` (ADD
`FxObservationStore`; ADD `ResearchFxSnapshot.acquisition`);
`providers/fx.py` (ADD `FX_FEED_ID_ECB_DAILY` constant, no behavior
change); `execution/orchestration.py` (`_try_fetch_fx_rates` gains the
canonical cache branch + full-document fetch + acquisition threading;
no other orchestration logic touched); `runs/__init__.py` (export
`FxObservationStore`); `web/views.py` + `web/templates/web/
research_detail.html` (additive FX evidence line). Migration: NEW 0011
(CreateModel `FxObservationStore`, AddField `ResearchFxSnapshot.
acquisition` with LIVE default); no historical migration rewritten or
squashed. Tests: NEW `tests/research/test_fx_cache_contract.py`,
`tests/runs/test_fx_observation_store.py`,
`tests/execution/test_fx_observation_cache.py`,
`tests/execution/test_fx_cache_orchestration.py`,
`tests/execution/test_fx_cache_authority.py`,
`tests/web/test_fx_evidence_presentation.py`; ADD nodes to
`tests/providers/test_fx_provider.py` (feed-identity mirror-lock); model
inventories in `test_provider_boundaries.py`,
`test_research_identity_boundaries.py`, `test_research_run_boundaries.py`,
`test_web_boundaries.py` updated to the exact supersets. All existing FX
/ replay / boundary / authority suites unmodified and green.

### 26.19 PUBLIC-RESEARCH-RECALL-FU1: Production-priority exact-MPN recall
defect + Micron 7500 SSD policy applicability (IMPLEMENTED / APPROVED /
DEPLOYED; Serper wire contract corrected by §26.20)

Production-priority corrective follow-up on the approved / frozen /
deployed starting SHA `2b66ac65fbce86adcd4218dfefe1a5c7349128e4`. Two
independent retrieval defects surfaced on one high-frequency AMAX request
(MPN `MTC20F2085S1RC64BH1T`, description `Micron 32GB DDR5-6400 ECC 2Rx8
RDIMM CL52 Tray`): (1) the exact-MPN public comparable pipeline received
zero exact-MPN candidates, and (2) the request was routed to — and the
report presented as evaluated against — the `micron-7500-ssd-part-catalog-
v1` policy even though the requested product is DDR5 RDIMM memory, not a
Micron 7500 SSD. This section records the binding design of the fix.
Retrieval recall and identity authority are separate concerns: this phase
only changes WHICH candidates reach the pipeline and WHEN the SSD catalog
policy is consulted; it changes no identity, pricing, vendor, semantic,
human-review, comparable, FX, cache, or replay authority.

**1. Root cause of the exact-MPN recall defect.** The one paid search
issued the blended query `"<MPN>" <description>` (`build_search_query`),
and the Serper adapter sent `{"q": ...}` with no result-count parameter,
relying on the provider's default page (the recorded 2C fixture is exactly
10 organic results). Search engines treat a quoted phrase as a strong but
SOFT ranking signal, and a query can only degenerate toward terms present
in the query. With the description's high-document-frequency terms
co-ranked against a rare exact MPN, the engine returned broad description
matches (generic `Micron 32GB DDR5` aggregator pages) and the few exact-
MPN pages never entered the response; any exact-MPN pages ranked past the
default page were truncated at the wire. The downstream pipeline is
correct: every returned result is fetched, extracted, normalized, and
gated by frozen 3C; an exact-MPN page that publishes the requested MPN in
an explicit field is ACCEPTED, and a generic page fails closed with
NO_EXPLICIT_MPN_EVIDENCE. The defect was entirely at the retrieval
boundary.

**2. Exact-MPN retrieval is a first-class path.** For an explicit-MPN
request (MPN + description), the paid query is now the exact-MPN phrase
alone: `"<MPN>"`. The description is removed from the PAID QUERY and
remains pipeline context (frozen 3C identity reads the request's MPN;
semantic eligibility, presentation, and review all read the request's
description directly, never the search query). MPN-only and description-
only forms are unchanged. Rationale (binding): a page the frozen 3C gate
can ACCEPT contains the exact requested MPN in an explicit field, is
therefore indexed under that phrase, and is reachable by the exact-MPN
phrase query; a page without the MPN can only ever be REJECTED, so
description terms add cost and noise, not recall, and their presence in
the query is precisely the displacement channel. A phrase-only query's
degraded fallbacks still stay inside the MPN's token space. The frozen 4D-
D alias-expanded query shape is unchanged.

**3. Provider page size is an adapter-internal policy.** The provider-
neutral `SearchQuery` contract carries no result limit (frozen 2B); how
many organic results one paid call requests is a vendor payload-shape
decision owned by the adapter. `SerperSearchProvider` now requests
`num = 50` (the larger documented organic page for one ordinary-search
request; constant `DEFAULT_ORGANIC_RESULT_COUNT`, value locked by test).
This adds NO second paid call: one request per run (frozen 4C claim
contract unchanged; `claim_execution` still ensures at most one paid
search per ResearchRun). Because the paid query is MPN-first, results
beyond the provider default are further exact-MPN candidates, not
description noise. The adapter maps every returned organic item (no
client-side truncation), and orchestration processes every result (no
candidate cap). CORRECTED BY FU2 (§26.20): the explicit `num = 50`
parameter was rejected by the production Serper account (HTTP 400, "Query
pattern not allowed for free accounts") while the identical exact-quoted-
MPN query without it succeeds (HTTP 200); the wire body again carries
only `q`, the provider's default organic count applies, and the adapter
still maps every returned organic item. The exact-MPN phrase query (item
2) and the NOT_APPLICABLE applicability gate (item 4) remain deployed and
unchanged.

**4. Micron 7500 SSD policy applicability (NOT_APPLICABLE).** The 4D-D v1
policy is Micron 7500 SSD ONLY, but acquisition previously ran for EVERY
non-empty-MPN request — triggered by the MPN suffix shape alone, with no
evidence that the requested product belongs to the SSD catalog. A DDR5
RDIMM request therefore fetched the SSD catalog and the report presented
the `micron-7500-ssd-part-catalog-v1` policy / `Micron 7500 SSD catalog`
source as though applicable. A new bounded pre-fetch abstention
`NOT_APPLICABLE` (no fetches, no provenance, no authority) is returned
when the request description explicitly establishes the product as a
memory module under a bounded, recorded, NEGATIVE vocabulary of unambiguous
memory-class terms (`DIMM`, `RDIMM`, `UDIMM`, `SODIMM`, `LPCAMM`,
`LPCAMM2`, `DRAM`, `DDR2`–`DDR5`; standalone ASCII tokens, case-
insensitive). This is a negative applicability filter: it confers no
manufacturer/category/identity/pricing authority and never blocks a
request whose description carries no such evidence (the catalog remains
the only POSITIVE authority; SSD evidence still comes only from the
matched row's own `is-ssd` attribute). Priority: NO_REQUESTED_MPN <
NOT_APPLICABLE < INVALID_LOOKUP_BASE < fetch. The T-strip lookup-base
derivation is unchanged and remains a retrieval pointer ONLY: the apparent
`MTC20F2085S1RC64BH1T -> MTC20F2085S1RC64BH1` relationship is NOT
established as authoritative by this phase (no new manufacturer-source
authority for memory packaging exists in the architecture); a page
publishing the stripped base form is still an explicit MPN CONFLICT
(MPN_MISMATCH) under frozen 2A/3C.

**5. Authority invariants (unchanged, re-proven).** Frozen 3C identity
acceptance (explicit MPN field EXACT/NORMALIZED_EXACT only);
NO_EXPLICIT_MPN_EVIDENCE remains a valid rejection and generic
`Micron 32GB DDR5` evidence can never become exact-MPN authority;
semantic MATCH remains advisory; AI_ASSISTED_MATCH, Working Quote,
Reviewed Price, Machine Price, 4A public market authority, B2/B3
presentation, vendor supplemental authority, human-review authority,
comparable research (7C), FX/cache (8A-FX-A1), replay, and the count<3
median presentation contract are all untouched. No model or migration
change.

**6. Files.** Production: `execution/search_query.py` (exact-MPN phrase
query for explicit-MPN requests; MPN-only/description-only unchanged),
`providers/serper.py` (adapter-internal `num=50` organic page at the
time; corrected by §26.20 to a query-text-only wire body),
`research/micron_packaging_alias.py` (bounded non-SSD vocabulary +
`find_non_ssd_category_evidence`; `NOT_APPLICABLE` status + contract
invariants), `execution/micron_alias_authority.py` (pre-fetch
applicability gate), `web/micron_alias_presentation.py` +
`web/templates/web/research_detail.html` (truthful NOT_APPLICABLE
applicability wording; zero fetch provenance). Tests: NEW
`tests/execution/test_public_research_recall.py`; NEW nodes in
`tests/research/test_micron_packaging_alias.py`,
`tests/research/test_micron_alias_codec.py`,
`tests/execution/test_micron_alias_authority.py` (via the recall file's
gate class), `tests/web/test_micron_alias_report.py`,
`tests/providers/test_serper_provider.py`; corrected in place (contract
preserved/strengthened, none deleted/renamed/skipped): the 4C-B
`test_mpn_plus_description_query` and the three 4D-D bounded-authority
ordinary-query assertions (now the exact-MPN phrase form; the 4D-D
authority/snapshot/single-search/firewall contracts unchanged) and the
Serper wire-body assertion (pinned `num=50` alongside the credential
contract at the time; corrected by §26.20).

**7. Explicit non-fixes.** No second paid search per run. No identity-
threshold change. No semantic-override of explicit identity conflicts.
No UNKNOWN->MATCH conversion. No vendor-authority expansion. No FX/cache/
replay change. No comparable-research change. No hard-coded Micron MPN,
manufacturer, or reseller domain in the retrieval fix (the regression
fixture uses the production MPN only as data; the rules are general
exact-MPN / memory-class rules). No memory-catalog alias mechanism is
invented: if a Micron RDIMM packaging relationship ever requires authority
it needs its own reviewed manufacturer-source evidence and policy, out of
scope here.

### 26.20 PUBLIC-RESEARCH-RECALL-FU2: Serper wire-contract compatibility
correction (IMPLEMENTED / PENDING FINAL REVIEW)

Production-runtime compatibility correction to the approved / deployed
§26.19 (FU1), on the authoritative starting SHA `2326d1d62738801598f8b52143d59b0bcdc86819`
(baseline collection 5838). Transport/retrieval compatibility ONLY: the
correction touches the Serper request wire body. Nothing in this section
changes identity, pricing, vendor, semantic, human-review, comparable,
FX, cache, replay, or authority behavior.

**1. Production evidence and root cause.** After FU1 deployment,
production request `f123617a-f467-4b0c-8302-4272a108dd9f` (MPN
`MTC20F2085S1RC64BH1T`, description `Micron 32GB DDR5-6400 ECC 2Rx8 RDIMM
CL52 Tray`) failed at the search step (`PROVIDER_ERROR`). Persisted
execution evidence shows FU1 working as designed up to the provider call:
the exact requested MPN was issued as a first-class exact-phrase search
query, and the Micron 7500 SSD alias policy was classified
NOT_APPLICABLE ("request description explicitly establishes a
memory-module product; Micron 7500 SSD catalog policy does not apply")
with zero catalog fetches. Controlled production probes of
`POST https://google.serper.dev/search` on the current production account
then established the root cause:

* Probe A — `{"q": "\"MTC20F2085S1RC64BH1T\"", "num": 50}` => HTTP 400
  `{"message": "Query pattern not allowed for free accounts.",
  "statusCode": 400}`.
* Probe B — `{"q": "\"MTC20F2085S1RC64BH1T\""}` (same exact quoted MPN,
  WITHOUT `num`) => HTTP 200, with exact-MPN evidence in the organic
  results (first result: CDW, snippet including `Mfg #
  MTC20F2085S1RC64BH1T`).

The exact quoted MPN query is therefore supported and useful; the
explicit `num` result-count parameter introduced by FU1 is the sole
incompatibility with the current production Serper account.

**2. Correction (binding, narrowest possible).** The ordinary Serper
request body carries ONLY the query text: `{"q": query.text}`. The
provider's default organic result count applies. NO replacement value
(e.g. 10), NO other explicit result-count parameter, NO pagination, NO
second Serper call, NO retry behavior, NO account-tier detection, and NO
catch-and-silent-retry of the HTTP 400: the request contract itself
stops sending the incompatible parameter. `DEFAULT_ORGANIC_RESULT_COUNT`
is removed; no dead constant and no documentation claiming an explicit
50-result request remains in the adapter.

**3. Unchanged (re-proven by the preserved §26.19 regression suite).** The
exact-MPN phrase paid query for explicit-MPN requests (§26.19 item 2;
MPN-only and description-only forms byte-identical); the frozen 4D-D
alias-expanded query shape; the adapter's mapping of EVERY returned
organic item (response contract, independent of any request parameter);
frozen 3C identity gates (generic no-MPN evidence rejected
NO_EXPLICIT_MPN_EVIDENCE; explicit conflicting MPN rejected MPN_MISMATCH;
the T-stripped base form remains ONLY whatever bounded retrieval /
diagnostic pointer §26.19 already permits, never identity authority);
the NOT_APPLICABLE applicability gate with zero Micron 7500 catalog
fetches for established memory-module requests; legitimate 7500 SSD
ESTABLISHED and non-Micron SSD NO_AUTHORITY_MATCH behavior; and every
§26.19 item 5 authority invariant.

**4. Files.** Production: `providers/serper.py` ONLY (constant removed;
wire body `{"q": query.text}`; docstrings corrected to record the
production-account compatibility constraint). Tests:
`tests/providers/test_serper_provider.py` (the credential wire-body node
corrected in place — FU1's `num` pin replaced by the complete-payload
`{"q": ...}` pin plus an explicit `"num"`-absence pin; the credential
contract — header, never URL, never body — preserved; import of the
removed constant dropped) and `tests/execution/test_public_research_
recall.py` (the FU1 wire-body `num=50` node replaced in place with the
corrected contract — exact query text, complete payload, explicit
`"num"` absence — same class, same position, still collected; the
companion 50-item response-mapping node preserved unchanged). Docs: this
section + STATUS.

**5. Explicit non-fixes.** No Serper account upgrade as part of this
correction; no retry/fallback on HTTP 400; no result-count negotiation;
no change to any identity, pricing, vendor, semantic, human-review,
comparable, FX, cache, or replay authority; no model or migration
change.

### 26.21 SEMANTIC-AUTHORITY-V2-S2-A: Semantic Authority Contract V2
(contract freeze — IMPLEMENTED / PENDING FINAL REVIEW)

Bounded CONTRACT-ONLY phase on the authoritative starting SHA
`1a3c4a91bfbc6acda32025fa5145805f572185ff` (baseline collection 5838).
S2-A establishes the approved Semantic Authority V2 design in code as a
frozen pure contract. It wires nothing: production behavior after S2-A is
identical to the starting SHA. V2 is NOT wired into execution, semantic,
runs, web, or providers; V3 qualification has NOT happened; AI authority
has NOT expanded; no deployment may occur from this phase.

**1. Scope and non-scope.** S2-A defines, in the new pure module
`product_intelligence/research/semantic_authority_v2.py` (stdlib + frozen
research/domain imports only; no Django, no I/O, no network, no LLM, no
mutable global state) and exports it through `research/__init__.py`:

* the V2 top-level states and bounded sub-states;
* the bounded near-miss relationship signals (NM-1 / NM-2 only);
* the pure deterministic derivation `derive_identity_state_v2` over the
  frozen `ListingIdentityAssessment`;
* the structured conflict taxonomy with exact severity sets;
* the distinct context provenance classes and capability table;
* the authority-tier vocabulary and the authority matrix as pure data;
* the future UI display vocabulary (badges, attention order, summary
  wording) as frozen contract data.

MUST NOT (re-proven by no-wiring tests): wire V2 into production
execution; change current semantic eligibility (the frozen FU3B
predicate remains the only live gate); change current runtime/prompt
(prompt v1.1, parser, route, temperature, max_tokens); create DB
migrations; change AI calls; change 4A; change Reviewed Price; change UI
behavior; change replay behavior; change production authority; change
vendor authority; deploy anything. The frozen 2A comparator, 3C
assessment, decisions, rejection reasons, PriceIntelligenceSnapshot V1,
4A aggregation, and the current semantic V1 contract are unchanged.

**2. V2 states.** The V2 deterministic state overlay is derived over the
frozen `ListingIdentityAssessment`:

| V2 state | Sub-states (bounded) |
| --- | --- |
| `DETERMINISTIC_VERIFIED` | `V_EXACT`, `V_NORMALIZED_EXACT` |
| `DETERMINISTIC_UNCERTAIN` | `U1_TITLE_MPN`, `U2_SKU_ONLY`, `U3_PARTIAL_BOUNDARY`, `U4_NO_MPN`, `U5_NEAR_MISS_MPN` |
| `DETERMINISTIC_CONFLICT` | `C1_INCOMPATIBLE_EXPLICIT_MPN` |
| `DETERMINISTIC_UNEVALUABLE` | `E1_NO_TARGET_MPN`, `E2_NO_CANDIDATE_EVIDENCE` |

Mapping rules (frozen 3C -> V2): UNDECIDED + NO_REQUESTED_MPN -> E1;
ACCEPTED + EXACT -> V_EXACT; ACCEPTED + NORMALIZED_EXACT ->
V_NORMALIZED_EXACT; REJECTED + NO_EXPLICIT_MPN_EVIDENCE + TITLE_TEXT ->
U1; + SKU_FIELD -> U2 (SKU_EQUALS_TARGET when the frozen 2A comparator
establishes identity with the SKU, else SKU_NOT_TARGET); + NONE or an
explicit MPN field with no part-number content -> U4 when the listing
carries a usable product title (the frozen V1 usability gate: non-empty
title), else E2; REJECTED + PARTIAL_MPN_ONLY -> U3; REJECTED +
MPN_MISMATCH + explicit MPN source -> U5 for bounded near-miss shapes
(NM-1 / NM-2) else C1. Any assessment combination outside the frozen 3C
contract fails closed (`ValueError`). `E2_NO_CANDIDATE_EVIDENCE` is an
S2-A addition (the contract requires the enumerated sub-states "at
minimum").

**3. Near-miss relationship signals.** Bounded signals: EXACT,
NORMALIZED_EXACT, TITLE_MPN_TOKEN, SKU_EQUALS_TARGET, SKU_NOT_TARGET,
PARTIAL_BOUNDARY, NEAR_MISS_TRUNCATION, NEAR_MISS_SUBSTITUTION,
COMPATIBILITY_WORDING (overlay only, from the frozen 4-token vocabulary
{compatible, replacement, interchangeable, drop-in}, word-boundary
matched against the listing title), EMPTY_MPN_FIELD, NO_RELATION.
Near-miss membership is NEVER identity authority. NM-1 = strict
prefix/truncation relationship using the EXISTING frozen normalized MPN
keys (either direction). NM-2 = same length, exactly one-character
substitution. NOT implemented: Levenshtein fuzzy matching, arbitrary
substring matching, generic containment authority, suffix stripping,
manufacturer-specific acceptance, normalization changes. Anything outside
the bounded NM-1/NM-2 shapes remains deterministic conflict where the
frozen assessment is explicit MPN_MISMATCH.

**4. Product-lead amendment 1 — NM-2 authority ceiling.** NM-2 MAY be
classified U5_NEAR_MISS_MPN and MAY be evaluated by future semantic AI,
but NM-2 WITHOUT reviewed authoritative relationship context (a
provenance carrying `ESTABLISH_IDENTIFIER_RELATIONSHIP` — today
`MANUFACTURER_RELATION_AUTHORITY`, or another future explicitly reviewed
authoritative relationship source) has maximum future AUTOMATIC tier =
`NEEDS_REVIEW`. The ceiling is explicit matrix data
(`NEAR_MISS_SUBSTITUTION_WITHOUT_RELATION_AUTHORITY`), not a prompt
convention. Purpose: recall via AI/human inspection without letting a
one-character revision/model difference silently enter automatic
pricing. This is a generic safety rule, not a manufacturer special case.
AI may still return MATCH/HIGH; a human may confirm later; it simply
cannot auto-price as AI-assisted comparable.

**5. Product-lead amendment 2 — context provenance classes.** Three
DISTINCT bounded classes (not one ambiguous boolean), with disjoint
capability sets:

* `MANUFACTURER_PRODUCT_CONTEXT` — reviewed manufacturer source
  establishing base product facts (base MPN/category/family). Capability:
  GROUND_PRODUCT_FACTS only. Does NOT establish the identifier
  relationship.
* `MANUFACTURER_RELATION_AUTHORITY` — reviewed manufacturer or
  equivalent approved authoritative source explicitly establishing the
  relevant relationship/equivalence between identifiers. Capabilities:
  GROUND_PRODUCT_FACTS + ESTABLISH_IDENTIFIER_RELATIONSHIP. The only
  class that can raise relationship authority / authoritative STRONG
  context quality for matrix purposes.
* `CUSTOMER_RETRIEVAL_RELATION` — customer/project-defined relationship
  existing solely for retrieval recall. Capability: RETRIEVAL_RECALL_ONLY.
  MUST NEVER, by itself: establish identity; produce Machine Verified;
  raise NM-2 to automatic AI comparable; raise U5 context quality to
  authoritative STRONG; override conflict; enter 4A; be described to the
  model as manufacturer-established equivalence.

Context quality (STRONG / LIMITED / WEAK) is computed ONLY from
provenance classes — never from model confidence or AI
`matched_attributes`: RELATION capability present -> STRONG; else GROUND
capability present -> LIMITED; else WEAK (customer retrieval alone is
WEAK).

**6. Conflict taxonomy.** Bounded `ConflictClass` (14 values: MPN_IDENTITY,
REVISION_OR_SUFFIX, BRAND, PRODUCT_FAMILY, GENERATION, CAPACITY,
INTERFACE, FORM_FACTOR, PRODUCT_ROLE, ACCESSORY_RELATION,
PACKAGING_QUANTITY, BUNDLE, CONDITION, OTHER_MATERIAL_CONFLICT) with
exact frozen severity sets:

* ALWAYS_HARD: MPN_IDENTITY, PRODUCT_FAMILY, GENERATION, CAPACITY,
  INTERFACE, FORM_FACTOR, PRODUCT_ROLE, ACCESSORY_RELATION,
  PACKAGING_QUANTITY, BUNDLE.
* REVIEWABLE: REVISION_OR_SUFFIX, BRAND, OTHER_MATERIAL_CONFLICT.
* PRICE_DIMENSION_ONLY: CONDITION.

BRAND is REVIEWABLE, not hard. CONDITION is a price/condition dimension,
never an identity conflict. Tray-vs-retail wording alone is not hard;
single-vs-multipack is hard (PACKAGING_QUANTITY); drive-tray accessory vs
drive is hard (PRODUCT_ROLE / ACCESSORY_RELATION). The sets are disjoint
and cover the whole vocabulary (mechanically self-checked at import).

**7. Authority tiers and matrix.** Bounded derived workflow vocabulary:
MACHINE_VERIFIED, AI_ASSISTED_COMPARABLE, NEEDS_REVIEW, HUMAN_CONFIRMED,
HUMAN_REJECTED, HARD_CONFLICT, EXCLUDED_LOW_CONFIDENCE,
SEMANTIC_UNAVAILABLE. The matrix is pure contract data:

* `DETERMINISTIC_STATE_POLICIES` — per-state: deterministic tier
  (VERIFIED -> MACHINE_VERIFIED; CONFLICT -> HARD_CONFLICT; UNEVALUABLE ->
  EXCLUDED_LOW_CONFIDENCE; UNCERTAIN -> NEEDS_REVIEW), semantic
  eligibility, AI-authority permission, human-confirmation permission
  (UNCERTAIN is the only state with all three True).
* `SEMANTIC_OUTCOME_TIER_MATRIX` — all 27 (decision x confidence x
  context-quality) combinations defined as data: MATCH + HIGH requires
  STRONG context to reach AI_ASSISTED_COMPARABLE (LIMITED/WEAK ->
  NEEDS_REVIEW); MATCH + MEDIUM -> NEEDS_REVIEW; MATCH + LOW -> EXCLUDED;
  NO_MATCH (any confidence) -> EXCLUDED; UNCERTAIN + actionable context
  (LIMITED/STRONG) -> NEEDS_REVIEW, without it -> EXCLUDED; UNCERTAIN +
  LOW -> EXCLUDED.
* Ceilings (restrict only, never lift): reviewable conflict on a MATCH ->
  NEEDS_REVIEW; NM-2 without relationship authority (amendment 1) ->
  NEEDS_REVIEW.
* Supersession: any ALWAYS_HARD conflict -> HARD_CONFLICT.
* Runtime failure -> SEMANTIC_UNAVAILABLE, never interpreted as NO_MATCH.
* Precedence: HARD_CONFLICT > HUMAN_CONFIRMED > AI authority. A semantic
  outcome supplied for a non-eligible state is ignored (fail closed); a
  human outcome on a state that admits no overlay does not change the
  deterministic tier.

**8. U4 description-match contract.** U4_NO_MPN is an intentional recall
feature and must NOT be re-conservatized: a public listing with no usable
manufacturer MPN evidence but usable product title evidence is
DETERMINISTIC_UNCERTAIN / U4_NO_MPN and a future semantic AI entry point.
S2-A defines the state/policy only — no calls are wired. Weak/generic
descriptions stay distinguishable through the future context-quality and
confidence gates; eligibility does not mean authority.

**9. UI vocabulary contract (no UI implemented).** Frozen future display
terminology: mandatory badges — "Machine Verified", "AI-Assisted
Comparable — not machine verified", "Needs Review — not verified",
"Human Confirmed", "Human Rejected", "Hard Conflict — excluded", "Low
Confidence", "AI Evidence Unavailable". Attention order (ATTENTION, not
authority): 1. NEEDS REVIEW; 2. AI-ASSISTED COMPARABLE; 3. RESOLVED
(HUMAN CONFIRMED, MACHINE VERIFIED); 4. HUMAN REJECTED / HARD / LOW /
UNAVAILABLE.

**10. Product-lead amendment 3 — summary wording.** The misleading
headline "Comparable evidence: N listings" is FORBIDDEN when the count
contains NEEDS_REVIEW items (frozen as
`FORBIDDEN_MARKET_EVIDENCE_HEADLINE`). The future wording is "Market
evidence found: N listings" with tier breakdown, where NEEDS_REVIEW MAY
count under market evidence, plus a separate "Pricing-eligible comparable
listings: N" line, where NEEDS_REVIEW MUST NOT count; no price statistic
may include Needs Review before confirmation. The legacy machine line
"N comparable NEW listings (machine-verified)" may remain. Counting is a
pure function over the frozen tier sets (MARKET_EVIDENCE_TIERS =
pricing-eligible tiers + NEEDS_REVIEW; PRICING_ELIGIBLE_TIERS =
MACHINE_VERIFIED + AI_ASSISTED_COMPARABLE + HUMAN_CONFIRMED),
self-checked at import.

**11. Files.** Production: `research/semantic_authority_v2.py` (new pure
contract module) and `research/__init__.py` (public export + phase status
note only; no behavior change). Tests:
`tests/research/test_semantic_authority_v2.py` (mapping, near-miss,
provenance, taxonomy, matrix completeness/precedence, U4 invariant, UI
vocabulary, no-wiring) and
`tests/research/test_semantic_authority_v2_boundaries.py` (import purity,
no I/O/arithmetic, immutable contract data, export surface). Docs: this
section, STATUS, and AD-065.

**12. Explicit non-fixes / non-goals.** No V2 wiring; no V1 behavior
change; no prompt, parser, route, or transport change; no model or
migration; no UI; no deployment; no vendor authority change. V3
qualification (whatever that process becomes) is a separate future phase
and has NOT happened.

### 26.22 SEMANTIC-AUTHORITY-V2-S2-A-FU1: Corrective Follow-Up —
Orthogonal Evidence Gates + Frozen Mappings
(corrective follow-up to §26.21 — IMPLEMENTED / PENDING FINAL REVIEW)

Bounded CONTRACT-ONLY corrective follow-up on the pending S2-A
(§26.21, AD-065), on the authoritative starting SHA
`46869f9a3ee6fad638b87b71cd14ed848224c057` (baseline collection 5972).
S2-A-FU1 corrects the two independent-review blockers in S2-A. S2-B is
NOT started and nothing is wired: production behavior after S2-A-FU1 is
identical to the starting SHA; V3 qualification has NOT happened; AI
authority in production has NOT expanded; no deployment may occur from
this phase.

**1. Blocker 1 — U4 description-match was re-conservatized.** S2-A made
`ContextQuality.STRONG` globally equivalent to the presence of
`MANUFACTURER_RELATION_AUTHORITY`, and the matrix's only
`AI_ASSISTED_COMPARABLE` row was MATCH + HIGH + STRONG: a U4_NO_MPN
candidate — which by definition has no candidate identifier for any
manufacturer source to establish a relationship for — was locked out of
the automatic tier, contradicting the approved product goal. The
authority prerequisites are now TWO ORTHOGONAL, state-specific
dimensions, each derived independently:

* **A. Product evidence quality** — `ProductEvidenceQuality`
  (STRONG / LIMITED / WEAK), computed ONLY from the bounded
  `ProductEvidenceProfileV2` (usable product title + bounded
  matched-attribute facts) and reviewed product-grounding provenance
  classes — never from model confidence, decisions, or model-claimed
  attributes. A matched-attribute fact is a (`ProductEvidenceDimension`,
  grounded candidate-side source) pair: the dimension vocabulary is the
  six hard product dimensions (PRODUCT_FAMILY, GENERATION, CAPACITY,
  INTERFACE, FORM_FACTOR, PRODUCT_ROLE — mirroring the same-named
  ALWAYS_HARD conflict classes), and the source vocabulary is EXACTLY
  {LISTING_PRODUCT_TITLE, REVIEWED_PRODUCT_CONTEXT}. No model-claim
  source exists in the vocabulary: the future semantic runtime cannot
  self-promote its authority by asserting arbitrary matched attributes.
  The frozen STRONG bar is bounded and testable (future-qualifiable by
  V3): a usable title AND at least
  `STRONG_PRODUCT_EVIDENCE_MIN_MATCHED_FACTS` (2) matched facts
  spanning at least
  `STRONG_PRODUCT_EVIDENCE_MIN_MATCHED_DIMENSIONS` (2) distinct hard
  product dimensions. A title alone is NOT strong. LIMITED = some
  product grounding (usable title, reviewed product grounding, or at
  least one matched fact) without the full bar; WEAK = none of those.
  `CUSTOMER_RETRIEVAL_RELATION` grounds nothing. `MANUFACTURER_PRODUCT_
  CONTEXT` strengthens product grounding but does not establish the
  identifier relationship. `MANUFACTURER_RELATION_AUTHORITY` establishes
  the identifier relationship where that question exists (and also
  grounds reviewed product facts). Fail closed: a reviewed-grounded
  fact requires a reviewed product provenance (ValueError otherwise);
  a title-grounded fact requires a usable title; a profile
  contradicting the derived state (U4 without a usable title; E2 with
  one) is rejected.
* **B. Identifier relationship authority** — `RelationshipAuthority`
  (ESTABLISHED / NOT_ESTABLISHED / NOT_APPLICABLE), derived by
  `derive_relationship_authority` per candidate state: U4_NO_MPN ->
  NOT_APPLICABLE (no candidate identifier exists; relation provenance
  cannot change that); U1 / U2 / U3 / U5 -> ESTABLISHED only with
  reviewed relation provenance (`MANUFACTURER_RELATION_AUTHORITY`;
  `CUSTOMER_RETRIEVAL_RELATION` confers ZERO relationship authority);
  verified states -> ESTABLISHED by the frozen deterministic
  comparator; C1 -> NOT_ESTABLISHED; E1 / E2 -> NOT_APPLICABLE.

The 27-row matrix is re-keyed on (decision x confidence x product
evidence quality) with the SAME tier values as S2-A. Reaching
`AI_ASSISTED_COMPARABLE` additionally requires the state-specific
relationship question to be NOT_APPLICABLE (U4) or ESTABLISHED
(U1/U2/U3/U5): a general state-specific gate (fired rule
`CEILING_IDENTIFIER_RELATIONSHIP_NOT_ESTABLISHED`) that preserves
S2-A's effective requirement for U1/U2/U3 and U5-NM-1 (no authority
expansion for those states). The NM-2 ceiling (amendment 1) REMAINS
frozen as its own audit rule: U5 + NEAR_MISS_SUBSTITUTION without
reviewed relationship authority caps the maximum automatic tier at
NEEDS_REVIEW — even for MATCH + HIGH + STRONG product evidence.
`ContextQuality` / `derive_context_quality` are REMOVED. `derive_
authority_tier` accepts a bounded `product_evidence` profile (default:
the conservative state-derived profile, which can never reach STRONG by
itself — explicit evidence is required for automatic authority).

Required behavior (contracted + tested): U4_NO_MPN + semantic MATCH +
HIGH confidence + strong approved product evidence + no HARD conflict
+ no REVIEWABLE conflict => AI_ASSISTED_COMPARABLE is PERMITTED; U4
does NOT require MANUFACTURER_RELATION_AUTHORITY; U4 weak/incomplete
evidence remains NEEDS_REVIEW or EXCLUDED_LOW_CONFIDENCE per the frozen
matrix; U5 NM-2 without relationship authority remains NEEDS_REVIEW;
U5 NM-2 with valid MANUFACTURER_RELATION_AUTHORITY may pass that
specific ceiling, subject to the rest of the authority gates; customer
retrieval cannot satisfy the NM-2 relationship gate.

**2. Blocker 2 — frozen contract tables were mutable dicts.** Python
`Final` does not make a dict runtime-immutable. Every frozen contract
mapping is now a runtime-immutable tuple of immutable entries with a
pure lookup function: `SEMANTIC_OUTCOME_TIER_MATRIX` (27 entries; `semantic_outcome_tier`), `DETERMINISTIC_STATE_POLICIES` (4; `deterministic_state_policy`), `CONTEXT_PROVENANCE_CAPABILITIES` (3; `context_provenance_capabilities`), `AUTHORITY_TIER_BADGES` (8; `authority_tier_badge`), and the private `_PRIMARY_SIGNALS_BY_SUBSTATE` / `_STATE_OF_SUBSTATE` derivation tables. The severity frozensets and the attention-order tuple remain immutable as before. The module's global namespace is import-self-checked to contain NO dict / list / set at all, and `test_v2_contract_tables_are_immutable_data` now actually proves immutability with real mutation attempts (TypeError / AttributeError / FrozenInstanceError) over every frozen authority / context / display mapping — no `.copy()` of mutable globals; the authoritative stored contract itself is immutable.

**3. Files.** Production: `research/semantic_authority_v2.py` (contract
correction) and `research/__init__.py` (public export surface).
Tests: `tests/research/test_semantic_authority_v2.py` (16 new orthogonal-
dimension nodes; existing nodes corrected in place ONLY where they
encoded the flawed U4 / global-STRONG contract — the exact corrected
nodes are enumerated in STATUS) and
`tests/research/test_semantic_authority_v2_boundaries.py` (immutability
proof rewritten + no-mutable-global-state guard). Docs: this section,
STATUS, AD-065 (amended in part), AD-066 (new).

**4. Explicit non-fixes / non-goals.** No S2-B; no V2 wiring; no V1
behavior change; no prompt, parser, route, or transport change; no
model or migration; no UI; no deployment; no vendor authority change.
V3 qualification is a separate future phase and has NOT happened.

### 26.23 SEMANTIC-AUTHORITY-V2-S2-A-FU2: Corrective Follow-Up —
State-Specific Relationship Requirements
(corrective follow-up to §26.22 — IMPLEMENTED / PENDING FINAL REVIEW)

Bounded CONTRACT-ONLY corrective follow-up on the pending S2-A-FU1
(§26.22, AD-066), on the authoritative starting SHA
`f54489dbd4ea8375ba6924e21f3bce161caac9e1` (baseline collection 5989).
S2-A-FU2 corrects the third independent-review blocker in the S2-A
line: FU1's identifier-relationship gate was over-broad. S2-B is NOT
started and nothing is wired: production behavior after S2-A-FU2 is
identical to the starting SHA; V3 qualification has NOT happened; AI
authority in production has NOT expanded; no deployment may occur from
this phase.

**1. Blocker — the relationship gate was global, not state-specific.**
FU1 correctly restored U4_NO_MPN (relationship authority NOT_APPLICABLE)
but then introduced an over-broad general gate: U1 / U2 / U3 / U5
required `RelationshipAuthority.ESTABLISHED` before
AI_ASSISTED_COMPARABLE was allowed. That is NOT the approved contract:
the relationship-authority requirement must itself be STATE-SPECIFIC
bounded contract data. The purpose of semantic AI is to resolve
deterministic uncertainty; absence of deterministic / manufacturer
relationship proof must not automatically force every uncertain
identifier-shaped listing into human review.

**2. The frozen state/sub-state-specific requirement table.** New
bounded immutable data contract in `research/semantic_authority_v2.py`:

* `RelationshipRequirement` (3 members):
  * `NOT_APPLICABLE` — no reviewed-relationship requirement gates the
    automatic tier: the state admits no AI authority at all (verified,
    C1, E1, E2 — never consulted), no identifier-relationship question
    exists (U4_NO_MPN: no candidate identifier), or the relationship is
    already established by the frozen deterministic comparator (U2 +
    SKU_EQUALS_TARGET: the published SKU is frozen-2A identical to the
    target — nothing for a reviewed source to establish).
  * `NOT_REQUIRED` — the question exists but the automatic tier does
    not require reviewed relationship authority; the state-specific
    policy delegates the question to the semantic evaluation itself,
    gated by the product-evidence bar and the structured conflict
    taxonomy (U1_TITLE_MPN: whether the exact requested MPN in the
    title denotes the product or is merely compatibility/reference/SEO
    text is precisely the question the semantic evaluation resolves;
    COMPATIBILITY_WORDING / accessory / product-role conflicts remain
    safety inputs through the taxonomy).
  * `REVIEWED_RELATION_AUTHORITY_REQUIRED` — reaching
    AI_ASSISTED_COMPARABLE requires `RelationshipAuthority.ESTABLISHED`
    (reviewed authoritative relationship provenance —
    MANUFACTURER_RELATION_AUTHORITY or a future reviewed
    relationship-authority class); CUSTOMER_RETRIEVAL_RELATION confers
    zero relationship authority and never satisfies it (U2 +
    SKU_NOT_TARGET, U3, U5 + NM-1, U5 + NM-2).
* `SUBSTATE_RELATIONSHIP_REQUIREMENTS` — runtime-immutable tuple of
  14 (sub-state, primary signal, requirement) entries covering EXACTLY
  the combinations the frozen derivation permits (import-self-checked
  against `_PRIMARY_SIGNALS_BY_SUBSTATE`); explicit per-entry policies:
  V_EXACT / V_NORMALIZED_EXACT / U4 (both signals) / C1 / E1 / E2 (both
  signals) / U2 + SKU_EQUALS_TARGET -> NOT_APPLICABLE; U1 -> NOT_
  REQUIRED; U2 + SKU_NOT_TARGET / U3 / U5 + NEAR_MISS_TRUNCATION / U5 +
  NEAR_MISS_SUBSTITUTION -> REVIEWED_RELATION_AUTHORITY_REQUIRED.
* `substate_relationship_requirement(substate, primary_signal)` — pure
  fail-closed lookup (TypeError on non-V2 inputs; ValueError on any
  combination the table does not define — unknown combinations never
  gain authority); independently testable and future V3-harness
  consumable.

**3. The gate.** `derive_authority_tier` caps a would-be
AI_ASSISTED_COMPARABLE at NEEDS_REVIEW (fired rule
CEILING_IDENTIFIER_RELATIONSHIP_NOT_ESTABLISHED, name unchanged) when —
and only when — the candidate's table entry requires
REVIEWED_RELATION_AUTHORITY and dimension B is not ESTABLISHED. For
U5 + NM-2 the frozen NM-2-specific ceiling rule (amendment 1) caps
first and is the explicit audit form of the same requirement (it
subsumes the general gate, which is conditioned on the tier still being
AI_ASSISTED). The NM-2 safety ceiling, customer-retrieval zero-
authority, HARD_CONFLICT taxonomy, BRAND=REVIEWABLE,
CONDITION=PRICE_DIMENSION_ONLY, U4 recall, and the precedence
HARD_CONFLICT > HUMAN_CONFIRMED > AI authority are ALL unchanged.
Dimensions A (`derive_product_evidence_quality`) and B
(`derive_relationship_authority`) are unchanged from FU1; all FU1
immutable-table protections are retained and the new table is added to
the immutability proof (`test_v2_contract_tables_are_immutable_data` +
the no-mutable-globals import self-check).

**4. Required behavior (contracted + tested).**

1. U1 + exact target MPN in title + MATCH/HIGH + STRONG product
   evidence + clean conflicts => AI_ASSISTED_COMPARABLE WITHOUT
   MANUFACTURER_RELATION_AUTHORITY (with no provenance, customer
   retrieval only, and product grounding only).
2. U1 compatibility/accessory conflicts remain HARD/NEEDS_REVIEW per
   the structured conflict taxonomy (COMPATIBILITY_WORDING overlay +
   ACCESSORY_RELATION / PRODUCT_ROLE => HARD_CONFLICT; reviewable =>
   NEEDS_REVIEW) — no recall expansion bypasses safety.
3. U2 + SKU_EQUALS_TARGET + MATCH/HIGH + STRONG + clean conflicts =>
   AI_ASSISTED_COMPARABLE without MANUFACTURER_RELATION_AUTHORITY.
4. U2 + SKU_NOT_TARGET follows the explicit conservative policy
   (REVIEWED_RELATION_AUTHORITY_REQUIRED; customer retrieval never
   satisfies it).
5. U3 follows its explicit state-specific conservative policy; the U3
   choice does not silently determine U1/U2/U5 behavior (identical
   inputs are uncapped for U1 — pinned).
6. U4 FU1 behavior unchanged (NOT_APPLICABLE; auto-tier capable).
7. U5 + NM-1 follows its own explicit bounded policy (REVIEWED_RELATION_AUTHORITY_REQUIRED; the NM-2-specific rule does not fire for
   NM-1).
8. U5 + NM-2 without relationship authority remains NEEDS_REVIEW even
   with MATCH/HIGH/STRONG evidence (ceiling unchanged).
9. U5 + NM-2 with MANUFACTURER_RELATION_AUTHORITY may clear that
   specific ceiling (unchanged).
10. CUSTOMER_RETRIEVAL_RELATION never clears NM-2 (unchanged).
11. Precedence HARD_CONFLICT > HUMAN_CONFIRMED > AI unchanged.
12. All frozen contract tables (including the new requirement table)
    remain genuinely immutable.
13. V1 production wiring / eligibility / runtime unchanged (no-wiring
    scans pass unmodified).

**5. Files.** Production: `research/semantic_authority_v2.py` (state/
sub-state-specific requirement contract) and `research/__init__.py`
(public export surface: `RelationshipRequirement`, `SUBSTATE_RELATIONSHIP_REQUIREMENTS`, `substate_relationship_requirement`).
Tests: `tests/research/test_semantic_authority_v2.py` (14 new nodes;
3 FU1 nodes corrected in place — exactly the ones that encoded the
blanket gate: `TestContextProvenance::test_customer_retrieval_cannot_grant_auto_authority`, `TestContextProvenance::test_manufacturer_product_
context_alone_cannot_reach_auto_tier`, `TestRelationshipAuthorityStates::
test_question_bearing_states_without_relation_authority_are_capped` —
each correction preserves or redirects the surrounding safety contract,
exact old/new expectations recorded in STATUS) and
`tests/research/test_semantic_authority_v2_boundaries.py` (immutability
proof extended to the new table; export-surface pins extended). Docs:
this section, STATUS, AD-066 (amended in part), AD-067 (new).

**6. Explicit non-fixes / non-goals.** No S2-B; no V2 wiring; no V1
behavior change; no prompt, parser, route, or transport change; no
model or migration; no UI; no deployment; no vendor authority change;
no expansion of the known Windows subprocess allowlist. V3
qualification is a separate future phase and has NOT happened.

### 26.24 SEMANTIC-AUTHORITY-V2-S2-B: Persistence / Codec Phase
(IMPLEMENTED / AMENDED IN PART BY S2-B-FU1 — PENDING FINAL REVIEW —
decision record: AD-068)

CORRECTED IN PART BY S2-B-FU1 (section §26.25, AD-069): the durable
persistence ENVELOPE was hard-bound to the old Semantic V1 contract — the
record constructor, the codec, and the replay gate all required semantic
contract == V1, prompt == 1.1, input/output schema == 1, authority
contract == S2-A-FU2, and the V1 pinned provider/model route. That
coupling would have forced S2-C's final V2 contract into the obsolete V1
persistence contract (or a new persistence schema before schema v1 was
used live). FU1 split the envelope from the V1 contract: the universal
envelope (foundation + codec framing + replay dispatch + service) is
now contract-agnostic and dispatches on the RECORDED (envelope schema
version, semantic contract version) pair to explicitly REGISTERED
version-specific adapters; the first registered adapter (the Semantic V1
adapter) keeps every V1 pin. All other S2-B content (storage, digests,
replay safety, migration, human-review separation, zero-live, backward
compatibility, no-wiring) stands as recorded below. AD-068 stands
amended in part.

Bounded PERSISTENCE/CODEC phase on the authoritative starting SHA
`9206126d4fb13300028256964c98f477c5d17969` (S2-A-FU2, APPROVED / FROZEN;
baseline collection 6003). S2-B persists the complete Semantic Authority
V2 evaluation/provenance artifact needed for future execution and zero-
live historical replay. It is about RECORDING semantics, not granting
new production authority: after S2-B, production behavior is identical to
the starting SHA. S2-C (live execution wiring under the final V2
input/output contract) is NOT started.

**1. Scope (frozen).** S2-B delivers: the persisted artifact contract, the
strict versioned codec, the pure replay/reconstruction path, the additive
runs model + migration, and the execution-layer persistence service that
future S2-C will call. S2-B does NOT: enable V2 semantic eligibility in
production, change the live semantic prompt or AI route, call AI for
U4/U5, enable AI_ASSISTED_COMPARABLE pricing, change Machine Price /
frozen 4A / Reviewed Price, change UI ordering/presentation, change
vendor authority, or deploy. Current V1 production behavior is unchanged
(no-wiring proved by test).

**2. Architecture decision.** `SemanticDecisionRecord` is a first-class
persisted semantic-decision artifact — the semantic EXECUTION/PROVENANCE
LEDGER (one record per assessed entry-point candidate; ALL outcomes:
MATCH / NO_MATCH / UNCERTAIN / RUNTIME_FAILURE / NOT_EVALUATED, with or
without fallback). `AiAssistedReviewCandidate` remains the human-review
WORKFLOW artifact (MATCH outcomes only; mutable review state; forged-
confirmation protections; HARD_CONFLICT supersession; Reviewed Price
behavior). It is NOT overloaded into the universal ledger. The two share
the narrow explicit (run, assessment_index) stable binding and reference
neither other's rows.

Storage design (the established versioned-JSON-box pattern of
PriceIntelligenceSnapshot / ResearchSupplementSnapshot / ResearchFxSnapshot
/ ResearchMicronAliasSnapshot): the runs model carries id (UUID4), run
(FK CASCADE, related_name `semantic_decision_records`), assessment_index,
schema_version (codec version; only 1 supported), `payload` (opaque
codec-encoded artifact JSON — all semantic authority fields live inside;
the schema is owned by the codec, not the model), `payload_digest`
(canonical SHA-256 of the payload, stored in a SEPARATE column computed at
write time — the whole-artifact tamper anchor: a payload altered outside
the service, even with in-payload section digests recomputed, is detected
on every read), and created_at (persistence time, distinct from the
evaluation instants inside the payload). No ad hoc semantic columns:
scattering the versioned artifact's 20+ fields across columns would turn
every contract version into a migration and give the runs layer
interpretation rights it does not have (runs stores, it does not
interpret). No indexed-query requirement exists yet (lookups are by
(run, assessment_index), covered by the unique constraint); S2-B adds no
UI.

Layering: the artifact + codec + replay are PURE research-layer modules
(Django-free; no network/file I/O; no clock; no float; no semantic-runtime
imports — its runtime-provenance vocabularies are mirrors of the frozen
FU3A runtime, drift-pinned by tests, following the
V2SemanticDecision-mirrors-SemanticDecision precedent; they consume the
frozen S2-A contract through the research package's public export
surface, keeping the S2-A no-wiring lexical guards intact). The
persistence SERVICE is an execution-layer module
(`execution/semantic_decision_persistence.py` — the runs layer cannot
import research under the frozen boundary) that composes the research
codec + replay with the runs model; it owns the only write path and the
read/replay paths with integrity verification, and it owns no authority
derivation logic (guarded).

**3. The persisted artifact (schema v1) — minimum complete.**

* **Identity / binding** — run UUID (canonical string),
  assessment_index (stable position in the run's ordered assessment
  tuple), source_url (the listing's stable identity).
* **Contract binding** — semantic contract version `V1` (the frozen FU3A
  production semantic contract), prompt version `1.1`, input schema
  version 1, output schema version 1, authority contract version
  `SEMANTIC_AUTHORITY_V2_S2A_FU2` (the S2-A contract as frozen through
  S2-A-FU2). The artifact binds to the exact versions under which it was
  produced; anything else fails closed at construction/decode.
* **Deterministic V2 context** — IdentityStateV2, V2 sub-state,
  relationship signals (primary + bounded overlay; the context is
  constructor-validated as a legitimate S2-A context), normalized
  requested/candidate keys, and the derived relationship-requirement
  snapshot (stored; replay proves it).
* **Product evidence** — `ProductEvidenceProfileV2` (usable-title fact +
  bounded matched facts, each = dimension x grounded candidate-side
  sources) in versioned encoded form; the derived
  `ProductEvidenceQuality` snapshot (stored; replay proves it); the
  context provenances (MANUFACTURER_PRODUCT_CONTEXT /
  MANUFACTURER_RELATION_AUTHORITY / CUSTOMER_RETRIEVAL_RELATION) as
  actually present at evaluation time.
* **Recorded prompt input** — the exact V1 case fields (case_id, target
  MPN/description, candidate title/MPN field/SKU/specs, evidence source):
  from them the historical prompt is deterministically reconstructable
  without any live call.
* **Recorded semantic output** — evaluation state
  (NOT_EVALUATED / EVALUATED / RUNTIME_FAILURE), decision
  (MATCH / NO_MATCH / UNCERTAIN), confidence (HIGH / MEDIUM / LOW),
  structured conflict classes (the V2 `ConflictClass` set), the bounded
  reason code, and the recorded attribute lists. The V1 output contract
  admits no explanatory prose; none is stored. A RUNTIME_FAILURE never
  carries a decision (it is never interpreted as NO_MATCH).
* **Runtime provenance** — attempts in call order (role PRIMARY/
  FALLBACK, attempt number, provider, model, bounded outcome — the V1
  pinned route is enforced), fallback_used, fallback reason, bounded
  final failure class (family-consistent with attempt count), actual
  provider/model (the OK attempt's; None on any failure), and the
  ISO-8601 UTC evaluation instants (absent, never defaulted, for
  NOT_EVALUATED). No latency, no raw body, no exception text.
* **Derived audit snapshots** — relationship authority, authority tier,
  fired rules under the exact bound contract version.
* **Integrity** — self-verifying canonical SHA-256 digests: input digest
  over binding + contract + context + product evidence + prompt input;
  output digest over evaluation + execution + derived. The record
  constructor refuses a record whose stored digests do not agree with
  its own sections.

Persisted vs strictly re-derived: the artifact stores the source inputs
plus the small derived set above (tamper/audit purpose); everything else
(the state policy, the matrix base tier, the primary signal, the prompt
rendering) is strictly re-derived and never stored. Where both source
inputs and derived results are stored, the replay path MUST prove they
agree (step 5).

**4. The strict versioned codec.** Schema v1. Exact field set at every
level (missing AND extra keys rejected). Strict enums (unknown values
rejected; set encodings must be sorted and unique). No float authority
data (a float anywhere in a payload is rejected). No lossy serialization.
No silent defaulting of missing safety fields (nullable means present
key with null; an absent key is an error). Decode wraps every
constructor/validation failure (including the record's digest
self-verification) in the bounded `SemanticDecisionCodecError`.
Unsupported schema versions fail closed — no best-effort migration, no
permissive unknown-field acceptance.

**5. The replay contract (pure, zero-live).** `replay_semantic_decision`
reconstructs, from the persisted artifact alone, with ZERO live AI calls
and ZERO provider/network calls: (a) the contract-binding gate — the
known safe-replay envelope is exactly
`("V1", "1.1", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU2")`; any other
binding (unknown OR future) is refused explicitly, so an old persisted
decision is never silently reinterpreted under a newer contract and the
historical binding is never substituted by current module constants;
(b) the historical `SemanticEvaluationV2` (the exact evaluation used at
the time, incl. RUNTIME_FAILURE as SEMANTIC_UNAVAILABLE-shaped, never
NO_MATCH, and NOT_EVALUATED as the deterministic-policy state, never an
AI failure); (c) the S2-A authority inputs (`IdentityStateAssessmentV2`,
product-evidence profile, context provenances, recorded prompt input);
(d) the re-derivation under the frozen S2-A module (relationship
requirement, product evidence quality, relationship authority,
`derive_authority_tier` with no human overlay — the overlay is a later
workflow concern); and (e) the derived-agreement proof: every stored
derived audit snapshot must EXACTLY agree with the re-derivation —
disagreement (or a derivation that fails closed on the recorded inputs)
is a `SemanticDecisionReplayError`. The service-level replay adds full
binding verification against the run's persisted evidence: the recorded
request identity must equal the run's canonical request, and the recorded
source URL must bind to the run's snapshot assessment at the recorded
index (a same-request cross-run or out-of-range artifact cannot replay
over this run's evidence).

**6. Backward compatibility.** Existing historical runs created before
V2/S2-B remain readable exactly as before. No SemanticDecisionRecord is
ever fabricated for a legacy run: absence of a V2 semantic artifact means
"legacy semantic provenance unavailable under V2" — NOT NO_MATCH, NOT
NOT_EVALUATED, NOT an AI failure. `load_semantic_decision` returns None
for absence; an explicit replay request for an absent record fails
closed. Historical V1 behavior is exactly what it was (the frozen V1
regression suites pass unchanged).

**7. Migration safety.** One additive migration (0012): a single
CreateModel for `runs.SemanticDecisionRecord`. No backfill, no data
rewrite, no PriceIntelligenceSnapshot mutation, no existing review-state
change. `python manage.py makemigrations --check`: "No changes
detected"; `python manage.py migrate --plan`: includes 0012 (Create
model SemanticDecisionRecord). No deployment/migration of production.

**8. Human-review preservation.** `AiAssistedReviewCandidate` and its
service are unchanged (model field inventory re-pinned by test): the
UNREVIEWED/CONFIRMED/REJECTED state machine, binding validation, forged-
confirmation protections, HARD_CONFLICT supersession, stale confirmed
hard-conflict exclusion, Remove/Restore, and Reviewed Price behavior all
pass unchanged. A persisted ledger record creates no review candidate;
a review candidate's state machine is untouched by the ledger.

**9. S2-A contract preservation.** The frozen S2-A module and its export
surface are unmodified. The record module consumes the V2 vocabulary
through the research package's public exports (the S2-A no-wiring lexical
guards are intact and pass unmodified). The recorded derived snapshots
are produced under `SEMANTIC_AUTHORITY_V2_S2A_FU2` — U1 NOT_REQUIRED, U2
SKU_EQUALS_TARGET NOT_APPLICABLE, U2 SKU_NOT_TARGET / U3 / U5-NM-1 /
U5-NM-2 REVIEWED_RELATION_AUTHORITY_REQUIRED, U4 NOT_APPLICABLE, NM-2
independent ceiling, customer retrieval zero authority, HARD_CONFLICT
precedence, the ProductEvidenceQuality bar, immutable contract tables,
"Market evidence found" terminology, and the pricing-eligible
separation — all encoded, not redefined (the mirror tests + the S2-A
suite + the no-wiring scans pass unchanged).

**10. Files.** Production: NEW `research/semantic_decision_record.py`,
`research/semantic_decision_codec.py`, `research/semantic_decision_replay.py`;
`research/__init__.py` (public export surface + phase note);
`runs/models.py` (additive `SemanticDecisionRecord` model); NEW
`runs/migrations/0012_semantic_decision_record.py`; `runs/__init__.py`
(model export); NEW `execution/semantic_decision_persistence.py`.
Tests: NEW `tests/research/test_semantic_decision_record.py`,
`test_semantic_decision_codec.py`, `test_semantic_decision_replay.py`,
`test_semantic_decision_boundaries.py`; NEW
`tests/runs/test_semantic_decision_record.py`; NEW
`tests/execution/test_semantic_decision_persistence.py`; six existing
model-registry / ResearchRun field pins extended in place (the additive
model is the "made twice" decision: research-identity, runs-boundaries
[model set + EXPECTED_FIELDS], web-boundaries, providers-boundaries,
comparable-research-execution). Docs: this section, STATUS, AD-068.

**11. Explicit non-goals.** No S2-C (live semantic execution wiring,
final V2 input/output contract); no V3 qualification; no UI; no prompt /
parser / route / transport change; no vendor authority change; no
deployment; no expansion of the known Windows subprocess flake allowlist.

### 26.25 SEMANTIC-AUTHORITY-V2-S2-B-FU1: Decouple the Persistence
Envelope from Semantic V1 (PENDING FINAL REVIEW — decision record: AD-069)

Bounded architecture correction on the pending S2-B candidate (canonical
spec: §26.24; starting SHA `95d9fd903cf941996d63dcd9b7f48265daf7c2a4`,
baseline collection 6227). S2-B is NOT approved: independent review found
one architecture blocker — the durable record/codec/replay infrastructure
was hard-bound to the OLD semantic V1 contract (semantic contract "V1",
prompt "1.1", the exact V1 prompt-input/output shape, and the exact
current primary/fallback provider/model route), so S2-C's final V2
contract would either be forced into the obsolete V1 persistence contract
or require a new persistence schema before schema v1 was ever used live.
FU1 makes the persistence ENVELOPE versionable independently from the
semantic contract it contains, WITHOUT inventing the final V2 contract,
WITHOUT wiring live execution, WITHOUT enabling V2 authority, and WITHOUT
deploying. After FU1, production behavior is identical to the starting
SHA; no V2 contract fields are guessed.

**1. Scope (frozen).** FU1 delivers: the universal contract-agnostic
envelope (foundation + codec + replay dispatch + service), the Semantic
V1 adapter as the FIRST registered version-specific interpretation layer,
the corrected immutability wording, and the tests proving the decoupling.
FU1 does NOT: define any Semantic V2 input/output/prompt contract, wire
live execution, enable V2 authority, change the V1 record's persisted
bytes, change migration 0012, change the runs model fields, or deploy.

**2. Required architecture.** The durable DB storage envelope (run,
assessment_index, payload ENVELOPE schema version, opaque payload,
payload digest, created_at) is preserved exactly. The opaque payload
explicitly identifies its semantic contract version in its `contract`
section. The universal envelope does NOT require semantic contract ==
V1, prompt == 1.1, or provider/model == today's V1 route: those are rules
of the VERSION-SPECIFIC semantic contract adapter. Conceptually:

    SemanticDecisionEnvelope / persisted row
        +-- contract identity/version (dispatch key: the recorded
            semantic contract version)
        +-- version-owned semantic artifact payload (adapter-owned shape)
        +-- execution provenance (persisted exactly; route VALIDATION is
            adapter-owned)
        +-- integrity information (envelope digest anchor + adapter
            section digests)

The version axes are independent: persistence envelope version !=
semantic contract version != prompt version != semantic input schema
version != semantic output schema version != runtime route version.

**3. The important distinction (anti-reinterpretation preserved).** The
correction is NOT "allow arbitrary version strings while decoding
everything as V1":

* STORAGE/TRANSPORT: the universal codec durably identifies/versions an
  artifact without assuming all future semantic contracts are V1 (a row
  whose payload names an unregistered semantic contract with a consistent
  digest anchor stores fine and is durably identifiable).
* INTERPRETATION/REPLAY: requires a REGISTERED / explicitly supported
  version-specific adapter; unknown or future semantic contracts fail
  closed with an explicit "no registered adapter" refusal — never
  best-effort decoded, never reinterpreted under the current contract.

**4. The universal layer (contract-agnostic).**

* `research/semantic_decision_record.py` — the envelope FOUNDATION:
  canonical encoding discipline (sorted keys, compact, ASCII, no floats),
  strict decode helpers (exact key sets, strict enums, explicit
  nullability, sorted-unique set encodings, float refusal), the universal
  persistence binding (run UUID canonical, assessment_index non-negative
  int, source_url non-empty) with its section encoding/validation, the
  bounded error vocabulary (`SemanticDecisionCodecError`,
  `SemanticDecisionReplayError`), and the `SemanticDecisionContractAdapter`
  extension point (frozen dataclass: envelope_schema_version,
  semantic_contract_version, supported_bindings, record_type, +
  encode/decode/replay/run_binding_violation). It owns no semantic
  contract value.
* `research/semantic_decision_codec.py` — the universal ENVELOPE CODEC:
  `SEMANTIC_DECISION_SCHEMA_VERSION` (1) is the PAYLOAD FORMAT version
  (the row's `schema_version` column), independent of the recorded
  semantic contract version; the adapter REGISTRY
  (`_REGISTERED_SEMANTIC_CONTRACT_ADAPTERS`, a frozen tuple — currently
  exactly `SEMANTIC_V1_ADAPTER`) is the explicit extension point;
  decode: row version registered -> payload is a mapping with no floats ->
  the payload's declared envelope version agrees with the row's -> the
  universal binding is exact and valid -> the `contract` section names a
  semantic contract version -> dispatch on the RECORDED (envelope schema
  version, semantic contract version) pair to the registered adapter (no
  adapter -> explicit fail-closed refusal); encode: dispatch on the
  record's registered adapter type + universal framing self-check;
  `canonical_payload_digest` (the whole-artifact tamper anchor value).
  The universal layer names no V1 route token and no quoted V1
  contract/prompt literal (mechanically guarded).
* `research/semantic_decision_replay.py` — the universal REPLAY
  DISPATCH: `SUPPORTED_CONTRACT_BINDINGS` is exactly the union of the
  registered adapters' `supported_bindings` (no drift between the gate
  and the registry); `replay_semantic_decision` reads the RECORD's
  recorded contract identity (never current module constants), refuses
  any unsupported binding explicitly, then selects the exact registered
  adapter and delegates the version-owned replay to it.
* `execution/semantic_decision_persistence.py` — the universal SERVICE:
  persist dispatches the artifact to its registered adapter (unregistered
  artifact type -> TypeError; the service names no V1 literal); load =
  digest verification + universal decode; replay = digest + universal
  decode + the universal binding verification (row exists, index in
  range, recorded source URL matches the run's persisted assessment at
  that index) + the ADAPTER-SPECIFIC recorded request-identity check
  (`adapter.run_binding_violation`) + the universal replay dispatch. The
  service owns no authority derivation logic (mechanically guarded) and
  no contract-specific assumption.
* `runs/models.py` + migration 0012 — UNCHANGED (fields, help text,
  constraints, index, single CreateModel). The model DOCSTRING is
  corrected: the row is the universal envelope (a future semantic
  contract reuses the row by registering a new adapter — no model
  change, no new migration, no data rewrite); `schema_version` is the
  envelope format version, independent of the recorded semantic contract
  version.

**5. The Semantic V1 adapter (first registered; version-specific).**
New `research/semantic_decision_v1.py` owns, and ONLY it owns: the V1
contract identity (semantic contract `V1`, prompt `1.1`, input/output
schema version 1, authority contract `SEMANTIC_AUTHORITY_V2_S2A_FU2`,
the exact tuple `V1_CONTRACT_BINDING`); the V1 pinned route
(`amax`/`qwen3.8-27b` primary, `vllm-262k`/`Qwen3.6-27B-262K` fallback —
a V1 contract rule, not an envelope invariant; drift-pinned to the
frozen FU3A route); the V1 runtime-provenance vocabulary (AttemptRole /
AttemptOutcome / SemanticFailureClass / SemanticFallbackReason — mirrors
of the frozen FU3A runtime, drift-pinned); the V1 recorded prompt-input
shape (`SemanticPromptInput`); the V1 typed record
(`SemanticDecisionRecordV1` — renamed from `SemanticDecisionRecord`, so
the V1 payload is no longer conflated with the universal schema; the
V1 exact-binding check, the V1 route pin, the S2-A context validation,
the evaluation/execution coherence rules, and the self-verifying
section digests all remain, now as V1-adapter rules); the V1 payload
codec (the exact V1 section shapes; strict; fail closed); the V1 pure
zero-live replay (reconstruction + re-derivation under the frozen S2-A
module + the derived-agreement proof); the V1 run-binding check (the
recorded prompt-input target MPN/description must equal the run's
canonical request); and the registered adapter instance
`SEMANTIC_V1_ADAPTER` (envelope schema 1, semantic contract `V1`,
supported bindings = (V1_CONTRACT_BINDING,), record type =
`SemanticDecisionRecordV1`). The V1 payload's PERSISTED BYTES are
byte-identical to the S2-B schema-v1 payload (the same sections, the
same canonical encoding, the same digests): no data migration, no
re-encoding of existing artifacts.

**6. Replay (dispatch by explicit recorded contract/version).**
replay(record): identify the recorded semantic contract/version -> gate
on the exact supported bindings (the registry union) -> choose the exact
registered adapter -> the adapter validates, reconstructs, re-derives,
and verifies the stored snapshots. Unknown/future semantic contract:
explicit failure at the codec dispatch AND at the replay gate. NEVER:
silently use the current contract, reinterpret an old record under a new
contract, or best-effort decode an unknown semantic version. ZERO live
AI/network behavior is preserved (the dispatched V1 replay is the same
pure reconstruction as S2-B; sentinels unchanged).

**7. No premature V2.** FU1 defines no Semantic Input V2, no Semantic
Output V2, no Prompt V2, no eligibility wiring. The extension point is
the adapter registry: S2-C registers a V2 adapter (new module, new
record type, new payload shapes, its own route pin — possibly a new
envelope format version) without redesigning the envelope, the row, the
migration, or the service.

**8. Migration.** NO migration change: the existing DB row is already a
generic opaque payload box; 0012 remains the single additive
CreateModel; no replacement migration, no data rewrite, no
delete/recreate of the model.

**9. Immutability wording (audit correction).** `editable=False` is NOT
DB immutability enforcement — it only keeps fields out of Django
auto-generated forms. The corrected documentation (model docstring +
service docstring) states: the ledger's immutability is the APPLICATION
contract — the single service-owned append-only write path that never
overwrites, the (run, assessment_index) uniqueness constraint, and the
whole-artifact digest anchor verified on every read; out-of-band
mutation (QuerySet.update() / raw SQL) bypasses the service and is
detected where the digest anchor differs — every read of the mutated row
then fails closed. No DB triggers are added.

**10. Test preservation.** No test deleted/renamed/skipped/xfail/
deselected/ignored/weakened merely to obtain green. Existing nodes whose
pins encoded the now-rejected coupling (artifact schema v1 == semantic
V1 forever, at the UNIVERSAL layer) were corrected ONLY in that
expectation while preserving the safety property (interpretation
requires an explicitly supported exact semantic contract): the record
class references move to `SemanticDecisionRecordV1` (mechanical rename
following the concept rename); the encode non-record TypeError message
pin moves from "expected SemanticDecisionRecord" to "expected a
registered semantic-decision record artifact"; the V1 contract/prompt/
authority-binding rejection nodes now test the V1 adapter's pin (the
same rejections, the same safety); the private section-encoder imports
move to the V1 module; the boundaries MODULES guard set gains the fourth
research module (strengthened, same guards); the package export pin is
updated to the new surface. New nodes: 35 proving: (1) the persistence
envelope version is independent of the semantic contract version (the
two axes fail closed with distinct errors; a row durably identifies an
unknown contract with a consistent digest anchor while interpretation
fails closed at the explicit dispatch); (2) the V1 adapter still
validates V1 exactly; (3) the V1 route pin remains enforced by the V1
adapter; (4) the universal storage layer (foundation/codec/replay/
service modules) owns no V1 provider/model or quoted V1 contract/prompt
assumptions; (5) replay dispatches through explicit version-specific
support (the registry; a spy proves the universal gate routes to the
registered V1 adapter; the gate table is the registry union);
(6) unknown semantic contract fails closed; (7) unknown artifact
(envelope) schema fails closed; (8)-(14) historical V1 replay, MATCH /
NO_MATCH / UNCERTAIN / runtime-failure / fallback-provenance replay,
and payload digest/tamper behavior remain exact and unchanged;
(15) legacy absence remains distinct; (16) human-review behavior
unchanged; (17) S2-A frozen authority contract unchanged; (18) no live
semantic wiring exists; (19) zero AI/network replay remains enforced.
In addition, the fourth research file auto-enters the existing
parametrized directory scans (domain caller-token, provider, runs-
persistence, web research, and the four research-core per-file scans in
`test_research_identity_boundaries.py`): +8 expanded nodes, no test
file decreased. Collection: 6227 -> 6270 (+43 = 35 new + 8 auto-
expanded).

**11. Files.** Production: REWRITTEN (universal) `research/
semantic_decision_record.py` (envelope foundation), `research/
semantic_decision_codec.py` (universal envelope codec + registry),
`research/semantic_decision_replay.py` (universal replay dispatch);
NEW `research/semantic_decision_v1.py` (the first registered adapter);
`research/__init__.py` (export surface: `SemanticDecisionRecord` ->
`SemanticDecisionRecordV1` + the universal/V1 symbols + the registry
functions); `execution/semantic_decision_persistence.py` (universal
service: registry dispatch + adapter run-binding hook + corrected
immutability wording); `runs/models.py` (docstring corrections only —
fields and help text untouched, so migration 0012 stays exact). No
migration. Tests: the six S2-B test files updated as item 10 records
(new nodes added in `test_semantic_decision_record.py`,
`test_semantic_decision_codec.py`, `test_semantic_decision_replay.py`,
`test_semantic_decision_boundaries.py`, `tests/runs/
test_semantic_decision_record.py`, `tests/execution/
test_semantic_decision_persistence.py`). Docs: this section, STATUS,
AD-069; §26.24 header amended.

**12. Explicit non-goals.** No Semantic V2 contract definition; no
S2-C live wiring; no V3 qualification; no UI; no prompt / parser /
transport change; no vendor authority change; no migration change; no
deployment; no expansion of the known Windows subprocess flake
allowlist.

### 26.26 SEMANTIC-AUTHORITY-V2-S2-C: Final Semantic V2 Contract +
Eligibility + Execution Wiring (PENDING FINAL REVIEW — decision record:
AD-070)

The first FINAL Semantic V2 contract, frozen in code and wired into the
comparable-research execution flow for V2-eligible candidates. Starting
SHA `c6caa23c024e48962191a0c856230b684fb21c3c` (S2-B-FU1 endpoint,
PENDING FINAL REVIEW; baseline collection 6270). S2-C does NOT declare
the V2 route qualified for the new contract and gives V2 outputs ZERO
production authority: Qualification V3 comes after S2-C review/freeze.

**1. Scope (frozen).** S2-C delivers: (a) the final Semantic V2 input
contract; (b) the final Semantic V2 output contract; (c) the final
Prompt V2; (d) the explicit V2 eligibility predicate; (e) the V2 runtime
route on the currently frozen qualified route identities; (f) execution
integration for V2-eligible deterministic uncertainty; (g)
`SemanticDecisionRecordV2` + the registered V2 persistence adapter; (h)
persistence of ALL V2 semantic outcomes; (i) zero-live V2 replay; (j)
strong architecture/safety tests. It does NOT deliver: AI-Assisted
Comparable price aggregation, new UI presentation, Needs Review UI
ordering, V2 human-review actions, automatic Reviewed Price
contribution, Machine Price changes, vendor changes, deployment,
Qualification V3 corpus/results, or model promotion based on V2
performance.

**2. The final V2 input contract (`research/semantic_v2.py`).**
`SemanticMatchCaseV2`: a versioned immutable value object, 23 required
fields, no silent defaults (absent candidate facts are explicit None),
five clearly separated sections — TARGET (case_id, requested MPN,
requested description); CANDIDATE LISTING (source URL, title, published
MPN field, published SKU, brand and condition when separately observed,
the reserved structured-listing-evidence section, the commercial
price/package context — NEVER identity evidence — and the frozen 3C
evidence source); DETERMINISTIC IDENTITY CONTEXT (IdentityStateV2,
substate, primary signal, all bounded signals, the frozen normalized
keys, the frozen relationship-requirement snapshot — contract-derived,
not caller input); CONTEXT PROVENANCE (the bounded
ContextProvenance classes as present — the three classes remain
distinct: MANUFACTURER_PRODUCT_CONTEXT != MANUFACTURER_RELATION_
AUTHORITY, and CUSTOMER_RETRIEVAL_RELATION is retrieval-only with zero
identity authority); PRODUCT EVIDENCE (the authority-side
ProductEvidenceProfileV2 — deterministic/reviewed only; the model may
observe it and report conclusions, but the authority-side profile must
originate from deterministic or reviewed evidence inputs, never from the
model). Construction fails closed on a non-UNCERTAIN state, a context
that disagrees with the frozen re-derivation of the assessment, a
requirement that disagrees with the frozen table, or an unsupported
profile.

**3. Eligibility V2.** `is_v2_semantic_eligible(assessment)`: the frozen
S2-A derived state only — DETERMINISTIC_UNCERTAIN -> eligible (U1
TITLE_MPN, U2 SKU_ONLY both signals, U3 PARTIAL_BOUNDARY, U4 NO_MPN
usable title, U5 bounded near-miss MPN both shapes); VERIFIED /
CONFLICT / UNEVALUABLE -> never eligible. No special-casing of any
manufacturer; no Levenshtein; no arbitrary substring fuzzy matching —
the only near-miss states are the frozen S2-A bounded states. The
current V1 predicate (`execution.semantic_integration`) is unchanged and
remains the only V1 gate.

**4. The safe product-evidence builder.**
`build_v2_product_evidence_profile(observation, context_provenances,
matched_facts)`: the bounded STRONG evidence bar is reachable only from
facts whose candidate-side grounding is independently present in
LISTING_PRODUCT_TITLE or REVIEWED_PRODUCT_CONTEXT (the frozen source
vocabulary has no model-claim member; the builder's signature accepts no
model output — the V2 model's matched_attributes can never directly
become ProductEvidenceFactV2 authority facts). Fail-closed on a
title-grounded fact without a usable title and on a reviewed-grounded
fact without a GROUND_PRODUCT_FACTS provenance. DOCUMENTED
LIMITATION: the current main-flow deterministic extraction proves no
exact bounded identity-dimension equality for listing candidates (that
infrastructure exists only in the comparable-research specification
flow), so the live path passes matched_facts=frozenset(): candidates
remain at most LIMITED (usable title) or WEAK, and the frozen S2-A bar
keeps them at NEEDS_REVIEW until future evidence infrastructure safely
proves facts. No fact is fabricated; no unsafe heuristic is invented;
the S2-A evidence bar is not weakened to increase recall.

**5. The final V2 output contract.** Strict structured response:
decision (MATCH/NO_MATCH/UNCERTAIN), confidence (HIGH/MEDIUM/LOW), a
bounded 17-member reason-code vocabulary (generic semantic classes; no
manufacturer-specific codes), bounded structured matched/conflicting
attributes (12 observation dimensions: product family, generation,
capacity, interface, form factor, product role, accessory relation,
packaging quantity / sales unit, bundle, brand, revision / suffix,
condition — each dimension + short observed detail), bounded
missing-critical dimensions, and a structured ConflictClass set
validated against the frozen S2-A ConflictClass vocabulary. The frozen
REASON_CODE_RULES keep the decision/conflict combination internally
coherent: a NO_MATCH caused by a CAPACITY conflict carries
ConflictClass.CAPACITY; NO_MATCH_MULTIPLE_CONFLICTS requires two or
more ALWAYS_HARD classes; MATCH and UNCERTAIN may never carry an
ALWAYS_HARD class (a hard conflict is a structured NO_MATCH, never
overridden); NO_MATCH is always conflict-grounded. Unknown
decision/confidence/reason code, unknown conflict class, missing
required fields, extra fields (there is no chain-of-thought field and
no free-form hidden reasoning surface), malformed lists, and incoherent
combinations all fail closed. No prose-only semantic authority.
CONDITION remains PRICE_DIMENSION_ONLY (never identity); BRAND remains
REVIEWABLE; PACKAGING_QUANTITY remains ALWAYS_HARD: physical-product
equivalence is never sales-unit equivalence ("same underlying physical
drive" does not imply "same comparable price unit").

**6. The final Prompt V2 (`semantic/contract_v2.py`).**
SEMANTIC_PROMPT_VERSION_V2 = "2.0" — used unchanged by Qualification V3
unless an actual defect is discovered before qualification. The system
prompt states: the task is commercial semantic equivalence of the
TARGET product and the CANDIDATE listing (not string matching); it is
NOT asked to estimate a price, decide Machine Verified status, override
deterministic HARD_CONFLICT, infer manufacturer authority, turn customer
aliases into manufacturer equivalence, or decide final market
aggregation; it SHOULD determine whether the candidate represents the
same commercially comparable product, which attributes match, whether
material conflicts exist, whether important facts are missing, and
whether uncertainty remains. Explicit rules: exact MPN equality is
strong evidence but not the only evidence; missing candidate MPN is not
automatically NO_MATCH; a target MPN in the title may be identity OR
compatibility/reference wording (inspect context); SKU evidence is
interpreted carefully; near-miss identifiers are not automatically
equivalent; customer retrieval relationships are retrieval hints only;
labeled manufacturer relationship authority is stronger evidence; same
physical product with different pack quantity / bundle is not
pricing-comparable as the same sales unit; accessory/tray/caddy/
enclosure versus the requested product is a material conflict;
insufficient evidence -> UNCERTAIN rather than guessing; a false MATCH
is materially worse than UNCERTAIN. The response format is the exact
strict six-key JSON schema (no prose, no Markdown, no chain-of-thought
field). The user prompt deterministically renders the recorded V2
input's five sections — the customer relation is labeled retrieval-
only/never-manufacturer-equivalence, the commercial context is labeled
NEVER identity evidence, and the product evidence section is labeled
authority-side (observe, do not create/upgrade/assert). The historical
prompt is reconstructable from the persisted V2 input alone (zero live
calls).

**7. The V2 runtime (`semantic/runtime_v2.py`).** The V2 pinned route:
amax/qwen3.8-27b PRIMARY, vllm-262k/Qwen3.6-27B-262K FALLBACK — the
currently frozen qualified route identities, carried as V2 CONTRACT
data (NOT the universal persistence envelope; drift-pinned to the
frozen FU3A route), temperature 0.0, max_tokens 32768. Fallback policy:
EXECUTION FAILURE ONLY (the frozen allowlist) — a valid primary
response (MATCH/NO_MATCH/UNCERTAIN at any confidence) is final; no
voting, no consensus, no semantic-disagreement fallback, no
low-confidence fallback, no NO_MATCH fallback. Model identity
verification, bounded per-attempt provenance, bounded evaluation
instants, strict V2 output at the boundary (malformed -> MALFORMED_
JSON; unknown/incoherent -> SCHEMA_INVALID; identity mismatch ->
MODEL_IDENTITY_MISMATCH). The explicit qualification-boundary marker
`V2_AUTHORITY_QUALIFIED = False` lives here (mirrored, drift-pinned in
the V2 adapter): the V2 route is NOT qualified for the new contract.
The V1 runtime is untouched.

**8. The V2 persistence adapter (`research/semantic_decision_v2.py`).**
Registered at the S2-B extension point as the SECOND adapter (the
envelope, the row, the migration, and the service do not change; no
migration). `SemanticDecisionRecordV2` binds the exact contract
identity ("V2", "2.0", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU2"), carries
the exact recorded V2 input (the case section — which IS the
deterministic S2-A context, the provenance, and the authority-side
product evidence), the strict structured output, the V2 route-pinned
attempts, the derived audit snapshots (product evidence quality,
relationship authority, authority tier, fired rules under the bound
authority contract), and self-verifying canonical digests. The version-
neutral transport-provenance value objects are reused from the first
registered adapter module; the V2 route pin and family-consistency
rules are V2-adapter-owned. Cross-adapter reinterpretation fails closed
in both directions (a V1-shaped body under the V2 name and vice versa).
The V2 zero-live replay reconstructs the evaluation and the S2-A
authority inputs from the exact recorded input, re-derives under the
frozen S2-A module, and proves the stored derived snapshots agree
(tamper/version-drift -> SemanticDecisionReplayError); a future
V2-lineage binding (e.g. prompt 2.1) is refused explicitly — never
reinterpreted under the current contract. The V1 adapter, V1 replay,
V1 historical records, and V1 codec compatibility are unchanged.

**9. Execution wiring.** `execution/semantic_decision_v2_execution.py`
+ orchestration: after the unchanged V1 semantic integration and the
unchanged 4A aggregation, every V2-eligible candidate (the frozen S2-A
DETERMINISTIC_UNCERTAIN states — including the U4/U5 states V1 never
reaches) receives exactly one V2 evaluation on the V2 pinned route; one
`SemanticDecisionRecordV2` is built per outcome and ALL outcomes
(MATCH / NO_MATCH / UNCERTAIN / RUNTIME_FAILURE / fallback success /
fallback failure) persist in the atomic final publication block through
the unchanged S2-B service. The 4D-D alias-expanded paid-search batch
carries CUSTOMER_RETRIEVAL_RELATION provenance in the recorded V2 input
(the only wired customer-retrieval-relation source; the 4D-D firewall
restricts the V1 authority path only — V2 is persist-only, so the
motivating alias-retrieved near misses reach the V2 semantic layer).
V1 coexists unchanged: V1-eligible candidates run BOTH the unchanged V1
evaluation (which may create its V1 review candidate on V1 MATCH —
bound to prompt 1.1) and the new V2 evaluation; the explicit V1->V2
switch decision belongs to Qualification V3. No V2 ExecutionDetailCode
vocabulary, no V2 execution-evidence rows (the ledger is the S2-B audit
surface), no V2 human-review candidate (persist V2 result only).

**10. The authority firewall (binding until Qualification V3).** No
production code path treats a V2 MATCH/HIGH as pricing-authoritative:
V2 outcomes are not in the 4A input, not in the review-candidate input,
not in the snapshot payload, and not in any public summary; the
aggregation layer owns no semantic output interpretation; the
persistence layer owns no authority logic; the V2 execution module
imports no aggregation / review / price codec surface (mechanically
guarded); `V2_AUTHORITY_QUALIFIED is False` (drift-pinned in the
adapter); the motivating-case test proves a full run with a V2
MATCH/HIGH near-miss leaves Machine Price, Reviewed Price, the price
summary, and the review queue exactly the deterministic-only values.

**11. Test preservation and collection.** No test deleted, renamed,
skipped, xfailed, deselected, ignored, or weakened merely to get green.
Eleven existing nodes whose pins encoded the now-registered V2
extension (the registry held "exactly one adapter" at the S2-B
endpoint) were corrected ONLY in that expectation while preserving the
safety property (explicit, fail-closed version-adapter dispatch): the
exact-binding union is now V1+V2; the unknown-contract axis is proven
with actually unregistered keys; the registry allowlist gains the V2
wiring module for the ledger-reference scan; the package-export pin
gains the V2 surface; the boundary MODULES guard set gains the fifth
research module. New nodes: 233 across seven new test files (contract
60, prompt 33, runtime 29, adapter 50, boundaries 32, execution 20,
motivating case 9) + 16 auto-expanded directory scans for the two new
research modules + 8 auto-expanded S2-B boundary guards + 1 new
cross-contract persistence node. Collection: 6270 -> 6528 (+258; no
file decreased).

**12. Explicit non-goals.** No qualification claim (V2_AUTHORITY_
QUALIFIED stays False; no fake qualification data); no V2 review/UI
wiring; no V2 price aggregation; no V1 behavior change (the V1
predicate, prompt, parser, route, and runtime are untouched); no S2-A
change; no migration; no deployment; no expansion of the known Windows
subprocess flake allowlist.

### 26.27 SEMANTIC-AUTHORITY-V2-S2-C-FU1: Input Evidence Fidelity
(PENDING FINAL REVIEW - decision record: AD-071; amends in part the
pre-freeze S2-C candidate, AD-070 / section 26.26)

Bounded INPUT-EVIDENCE correction on the pending S2-C candidate, on the
authoritative starting SHA `a3127bca4bc4177b447ece8b20c33d83ec4ed415`
(baseline collection 6528). S2-C is REVIEWED but NOT APPROVED / NOT
FROZEN and MUST NOT deploy; NO historical production V2 record exists
anywhere (the `runs_semanticdecisionrecord` table is absent from the
development database; V2 is persist-only and unqualified). FU1 therefore
amends the PRE-FREEZE candidate in place: the contract binding stays
exactly `("V2", "2.0", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU2")` and the
prompt version stays `2.0` (2.0 never shipped; the frozen 2.0 that
Qualification V3 will qualify against is the corrected text).

**1. The blocker (corrected).** The S2-C "FINAL" V2 input did not provide
the structured product/commercial evidence the product goal requires:
`candidate_specs` was a misleading free-text slot always `None`; the
commercial context was a composed price/availability/seller/offer
string; no packaging/sales-unit channel existed; and the motivating test
claimed family/capacity/interface/form factor were "structured evidence"
merely because the tokens occur in the candidate TITLE. Richer MODEL
OBSERVATION input is required before the contract can be declared FINAL -
while the AUTHORITY-side `ProductEvidenceProfileV2` stays independently
grounded (the model must never bootstrap authority from its own output;
S2-A is unchanged and frozen).

**2. Extraction-capability audit (documented in `research/semantic_v2.py`).**
(1) 3A `ListingObservation` carries the page-published STRUCTURED fields
(product title, MPN field, SKU, brand, price, currency, availability,
condition, seller, offer URL; JSON-LD / product meta are the only offer
mechanisms); the remaining JSON-LD material (description, GTIN,
category, ...) stays in the OPAQUE `raw_reference`, which no business
rule may parse (AD-040). (2) 3B normalizes COMMERCIAL attributes only;
it extracts no product attributes. (3) 3C compares EXPLICIT MPN fields
only (frozen 2A comparator); title and SKU text never establish
identity. (4) The 6A/6B/6C specification framework and the 7A/7B
comparable-research extraction exist ONLY in the comparable-research
flow and require an ESTABLISHED product identity plus manufacturer
support pages with the reviewed embedded structure - not available to
main-flow listing candidates. (5) 4D-D (Micron 7500 packaging-alias
acquisition) is the ONLY reviewed manufacturer TARGET context the main
execution flow carries: when ESTABLISHED it proves the requested part's
family-catalog membership (manufacturer, verified SSD category, exact
source-published base MPN) through a fail-closed deterministic parser
over a reviewed origin; its R/T relation is CUSTOMER-DEFINED (retrieval
only, zero identity authority); the result carries no other catalog
attributes (e.g. the box quantity is NOT carried into the main flow -
and must not be claimed as candidate packaging evidence).

**3. The corrected input contract (`research/semantic_v2.py`).**
`SemanticMatchCaseV2` (17 required top-level fields; no silent
defaults; construction fails closed exactly as S2-C):
A. TARGET - `TargetEvidenceV2`: the structured caller-published MPN (the
run's identity anchor); the requested description as RAW OBSERVATION
TEXT (explicit None when absent - never an empty sentinel); and
`ReviewedTargetContextV2 | None` (structured/reviewed target-side
context: manufacturer, verified category, matched base part number,
bounded relation kind - today only `CUSTOMER_RETRIEVAL_ALIAS`, zero
identity authority, never manufacturer-stated - with the relation's
family part numbers other than the requested form, source name/URL,
ISO-8601 UTC retrieval instant, and 64-hex evidence body digest;
fail-closed on any bad value). B. CANDIDATE LISTING - published
identifier fields (MPN field / SKU), the frozen 3C evidence source,
`CandidateProductEvidenceV2` (nine bounded product dimensions - product
family, generation, capacity, interface, form factor, product role,
accessory relation, brand, revision/suffix - each a
`CandidateObservationFactV2` (observed value + explicit
`CandidateEvidenceSourceV2` provenance: PUBLISHED_STRUCTURED_FIELD /
LISTING_TITLE / SPECIFICATION_TEXT / REVIEWED_PRODUCT_CONTEXT; NO
model-claim member) or explicit None; plus `raw_title_text` /
`raw_specification_text` RAW observation text) and
`CandidateCommercialEvidenceV2` (condition / price / currency /
availability / seller as bounded facts, the published offer URL, and
the REQUIRED `CandidateSalesUnitEvidenceV2` channel - ALWAYS explicit:
`UNAVAILABLE` (all value fields None) or `OBSERVED` (bounded
`SalesUnitKindV2` SINGLE_UNIT / PACK_QUANTITY / TRAY_OR_FACTORY_PACK /
BUNDLE + published raw detail + provenance + bounded positive int
quantity where the kind carries one; PACK_QUANTITY requires it,
SINGLE_UNIT forbids it)). C. DETERMINISTIC IDENTITY CONTEXT,
D. CONTEXT PROVENANCE, E. authority-side PRODUCT EVIDENCE - unchanged
from S2-C.

**4. Safe live builders (observation side).**
`build_candidate_product_evidence_v2` fills ONLY published
structured-field facts the extractor actually carries (brand); every
other dimension stays explicit None; NO title token is parsed into a
structured fact; the title is carried as raw observation text; no
specification text is carried (it stays in the opaque raw reference).
`build_candidate_commercial_evidence_v2` carries the published
commercial fields as bounded facts and ALWAYS the explicit UNAVAILABLE
sales-unit state (the extractor publishes no packaging field; nothing
is inferred from price). `build_semantic_match_case_v2` gains the
EXPLICIT `reviewed_target_context` keyword (no silent default). The
SAFE authority-side builder `build_v2_product_evidence_profile` is
UNCHANGED (frozen S2-A signature; the live path still passes
matched_facts=frozenset() - the audit proves the main flow grounds no
bounded identity-dimension equality; observation evidence - structured
or raw - can never become authority).

**5. 4D-D target-context wiring.** NEW
`reviewed_target_context_from_alias_result` in the V2 execution wiring:
deterministic over the ESTABLISHED result's own re-verified fields;
non-ESTABLISHED -> explicit None; an ESTABLISHED result missing a
reviewed field fails closed (defense in depth - the result's own
self-validation already makes such a state unconstructible). The
orchestration carries it into `evaluate_semantic_matches_v2` (new
EXPLICIT keyword) for every V2-eligible candidate of the run. No 4D-D
contract, codec, snapshot, or fetch behavior changes.

**6. Prompt V2 corrected (version stays 2.0).** The system prompt gains
the EVIDENCE CLASSES rules: STRUCTURED FACT (bounded value + source
label; an observation about one side, not a proof of agreement), RAW
OBSERVATION TEXT (may support reasoning; a token is not a structured
fact; never manufacturer authority; absence of a structured fact does
not erase the raw evidence), COMMERCIAL / PACKAGING EVIDENCE (never
identity; the sales-unit channel is explicit; UNAVAILABLE is not proof
of equal sales unit and never "single unit"; nothing inferred from
price), REVIEWED TARGET CONTEXT (target-side only; the customer-retrieval
relation is zero identity authority), AUTHORITY-SIDE PRODUCT EVIDENCE
(observe, never create/upgrade/assert), and NEVER MANUFACTURE A MISSING
FACT (absent from all evidence -> missing_critical_attributes). The
sales-unit rule gains: UNPROVEN sales unit + otherwise-matching evidence
-> PACKAGING_QUANTITY / BUNDLE in missing_critical_attributes +
UNCERTAIN. The user prompt renders the corrected sections (structured
facts with source labels or explicit absence; raw text under the raw
label; commercial facts + explicit sales-unit state; the reviewed
target context labeled STRUCTURED/REVIEWED / target-side only / zero
identity authority).

**7. Persistence / replay.** The V2 codec's case section is corrected to
the exact new shape (strict key sets; unknown enums, invented evidence
sources, invalid sales-unit cross-states, and a tampered reviewed
context all fail closed; a pre-FU1-shaped payload is never silently
reinterpreted - strict decode fails closed). The V2 run-binding check
reads the corrected target section. The V1 adapter, V1 payload bytes,
V1 replay, the envelope, the row, the service, and migration 0012 are
byte-untouched. NO migration.

**8. Tests.** The flawed motivating node
`test_the_input_carries_the_structured_evaluation_context` is corrected
IN PLACE as `test_the_input_carries_the_corrected_evidence_contract`:
it no longer claims title tokens are structured evidence; it proves (A)
raw candidate title evidence reaches the model labeled raw, (B) truly
structured product facts are present only where the extraction layer
produced them (all four dimensions explicit absences), (C) packaging /
sales-unit evidence is explicitly ABSENT (the fixture's only commercial
fact is a price), and (D) the absence renders with the never-infer rule
(not silently interpreted as equivalence); (E) customer-relation
retrieval-only, (F) the U5/NM-1 ceiling, and (G) no Machine Price
contamination are the unchanged adjacent nodes. New:
`tests/research/test_semantic_v2_input_evidence.py` (27 nodes: the 20
mandated input-evidence properties + the reviewed-target-context
contract incl. the 4D-D helper over the real recorded catalog fixture);
+8 prompt evidence-class nodes; +11 codec nodes (packaging
single-unit / pack-quantity / tray / bundle round-trips if observed;
UNAVAILABLE default; reviewed-context round-trip + zero-live replay;
pre-FU1-shape refusal; legacy `specs` key refusal; invalid
cross-state / unknown-source / unknown-relation-kind refusal); +1
full-orchestration motivating node (the ESTABLISHED 4D-D context
reaches the recorded V2 input; candidate packaging stays UNAVAILABLE;
derived snapshots unchanged). Mechanical shape corrections in the
S2-C test helpers (corrected builder signature / case shape) preserve
every safety assertion. No test deleted/renamed/skipped/xfail/deselected/
ignored; no file decreased; the known Windows/Python-3.14 subprocess
flake allowlist NOT expanded. Collection 6528 -> 6575 (+47).

**9. Explicit non-goals.** No S2-A change (the authority matrix, the
STRONG bar, the relationship requirements, the NM-2 ceiling,
customer-retrieval zero authority, and the conflict taxonomy are
frozen); no V1 behavior change (predicate, prompt, parser, route,
runtime, adapter, and payload bytes untouched); no qualification claim
(`V2_AUTHORITY_QUALIFIED` stays False); no packaging inference from
price or any other commercial fact; no title-token parsing into
structured facts; no 3A/3B/3C/4A/4D-D contract, codec, snapshot, or
fetch change; no new specification engine; no migration; no deployment.


### 26.28 SEMANTIC-AUTHORITY-V2-Q3-A: Qualification V3 — Independent

Corpus, Harness and Offline Qualification

(PENDING FINAL REVIEW — decision record: AD-072; S2-C / S2-C-FU1 now

APPROVED / FROZEN per the Q3-A operator briefing)



Bounded QUALIFICATION-INFRASTRUCTURE phase on the authoritative

starting SHA `cf51a23e31d175cc9e6759d12f97171769db87e5` (S2-C-FU1

endpoint, now APPROVED / FROZEN; baseline collection 6575). Q3-A

builds the independent, deterministic, OFFLINE qualification system

for the exact frozen Semantic V2 contract

(`("V2", "2.0", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU2")`). NO live

model qualification is executed in Q3-A; NO frozen production

artifact changes (prompt, input schema, output schema, reason codes,

eligibility, authority matrix, persistence adapter, runtime route all

byte-untouched); `V2_AUTHORITY_QUALIFIED` stays False; no deployment.

The phase delivers: (1) a versioned, independently labeled

qualification corpus; (2) a reproducible offline evaluation harness

using the REAL frozen V2 input / prompt / parser; (3) separate

semantic-accuracy and safety metrics; (4) explicit false-MATCH

detection with deterministic severity; (5) contract / version /

provenance verification; (6) a fail-closed qualification decision;

(7) a reproducible offline report bound to the exact corpus digest;

(8) tests proving qualification cannot be manipulated by changing

expectations to fit model output.



**1. The corpus.** NEW `evaluation/semantic_v2_qualification/` (data,

outside the Python package, following the 0B precedent):

`corpus_v1.json` (version `1.0.0`, schema v1, 56 cases; corpus digest

`2c37ba088c317d8cefc6ad0dd7e0d73cfd085f6474ef43eb6953e3cf0170b549`),

`manifest_v1.json` (reproducible per-case digest manifest),

`policy/qualification_policy_draft_1.json` (the DRAFT threshold

proposal), `reports/q3a_baseline/` (the committed no-capture baseline

reports), `README.md` (governance). 43 semantic cases (36

AUTHORITATIVE + 7 AMBIGUOUS) + 13 CONTRACT_NEGATIVE, across 5

product categories (enterprise_ssd / server_memory / processor /

network_adapter / workstation_gpu), covering all seven frozen

uncertain state/substate combinations (U1 / U2 both signals / U3 / U4

/ U5 NM-1 / U5 NM-2) and every mandated adversarial shape. Each case

carries: stable id, category, the EXACT frozen V2 input payload

(`SemanticMatchCaseV2.canonical()`), the derived substate / primary

signal, the expected decision (+ the acceptable set for ambiguous

cases), expected conflict classes, expected missing-critical

dimensions, an advisory expected reason code, the commercial-

sales-unit-safety flag, the label source kind (CONTRACT_GROUNDED /

PRODUCT_KNOWLEDGE_GROUNDED / REVIEWED_SOURCE_GROUNDED), the source

citation, the independent evidence, reviewer identity + status, the

ambiguity class, and the case digest. Evidence kinds: SYNTHETIC

(by-construction scenarios with clearly synthetic MPNs — never

real-market accuracy evidence) and RECORDED_FIXTURE (the recorded 4D-D

Micron 7500 part-catalog fixture, body digest

`160d4fe97a5df5249e8f6404f6b005c0515fab4def1b4668fdaf87c727600743`;

the recorded project-UAT V1 semantic corpus

`evaluation/semantic_corpus/cases.json`); REAL_MARKET is RESERVED

(corpus 1.0.0 ships none; the loader rejects it — a real-market label

requires an independently retrieved market source, which Q3-A does not

fabricate). The motivating Micron case (target

`MTFDKCC3T8TGP-1BK1DABYYR` vs candidate `MTFDKCC3T8TGP-1BK1DABYY`,

U5 / NEAR_MISS_TRUNCATION, with the reviewed 4D-D target context and

CUSTOMER_RETRIEVAL_RELATION provenance) is RECORDED_FIXTURE and

expected UNCERTAIN with PACKAGING_QUANTITY missing and

commercial_sales_unit_safety = true: the truncated form is the exact

recorded-catalog part ("7500 4TB U.3 SSD"); the R/T family relation is

a CUSTOMER-DEFINED 4D-D rule (no manufacturer document states what the

final R denotes — the frozen module records this explicitly);

physical-product family membership is grounded while commercial

sales-unit comparability is UNPROVEN; the pair is NOT labeled

equivalent merely because it shares a base identifier.

Contract-negative cases: non-UNCERTAIN states (VERIFIED / CONFLICT /

UNEVALUABLE cannot enter the V2 input), tampered requirement, foreign

signal, state/substate mismatch, unknown enums, invented evidence

sources (candidate-side and authority-side MODEL_CLAIM — authority-

boundary attacks), extra keys, sales-unit cross-state, U4 without a

usable title, and an invented reviewed-relation kind.



**2. Corpus integrity (frozen, digest-bound).** Canonical

serialization (sorted keys, compact, ASCII, NO floats) + SHA-256 per

case and over the whole state view. Changing an expected label MUST

change the corpus digest and create a `label_revisions` entry with the

bounded reason class (A: old expectation factually wrong; B:

authoritative source changed; C: case definition was ambiguous; D:

product behaviour requirement intentionally changed — "the new

implementation failed this case" is not a valid class). The auditable

SOURCE is `product_intelligence/evaluation/semantic_v2/fixtures.py`

(declarative cases over the EXACT frozen chain: request -> observation

-> 3B normalization -> 3C assessment -> S2-A derivation -> S2-C input

builder / the real `SemanticMatchCaseV2` constructor); a generator

self-check fails loudly if a fixture lands in a different deterministic

state/substate than declared, or if the mandated coverage is missing;

regeneration must reproduce the committed corpus byte-for-byte (proven

by test). The loader is strict (exact key sets, bounded vocabularies,

per-case digest verification, corpus digest verification, duplicate-id

rejection, unknown-version rejection, and a MECHANICAL rejection of

label text naming model output or a candidate model — ground truth is

never derived from the system under test, and the corpus generator

never reads a capture file). The reproducible manifest binds

case_id -> case digest; a mismatched manifest fails closed.



**3. The offline harness.** NEW `product_intelligence/evaluation/

semantic_v2/`: `canonical.py` (digest discipline), `fixtures.py`

(corpus source — runs the frozen chain), `corpus.py` (strict loader +

typed case reconstruction through the REAL constructor + bounded

rejection classes NON_UNCERTAIN_STATE / INVALID_INPUT_SCHEMA /

FOREIGN_DETERMINISTIC_CONTEXT / UNSUPPORTED_EVIDENCE + digest /

manifest verification), `capture.py` (the captured-response artifact

contract for the later LIVE phase: schema v1; binds to the exact

corpus digest + frozen prompt `2.0` + semantic contract `V2`;

attempts mirror the frozen runtime discipline — PRIMARY (frozen

primary route) first, at most one FALLBACK (frozen fallback route)

second, fallback on execution failure only with the frozen reason

mapping (drift-pinned mirrors), raw output only for OK attempts; a

record for a contract-negative case is a schema-bypass attack; a

capture is one RUN, projected per model), `evaluator.py`

(deterministic, zero-network, zero-AI evaluation using the PRODUCTION

V2 parser — `parse_semantic_response_v2` +

`validate_semantic_response_v2`, no recreation — and the real case

constructor; per-case states EVALUATED / NOT_CAPTURED / NOT_INVOKED /

RUNTIME_FAILURE / CAPTURE_INTEGRITY_FAILURE / CONTRACT_REJECTED_OK /

CONTRACT_VIOLATION; the offline evaluator never substitutes an

expected answer for an invalid model response and never manufactures

a response for a missing case), `gates.py` (the mandatory hard safety

gates + the fail-closed decision), `policy.py` (the policy artifact

contract), `report.py` (the reproducible report + verification),

`cli.py` (offline commands; no research import).



**4. Primary/fallback independence.** Both frozen runtime identities

are the qualification candidates (PRIMARY amax/qwen3.8-27b; FALLBACK

vllm-262k/Qwen3.6-27B-262K) and require INDEPENDENT qualification: a

capture records one run of the pinned route; the PRIMARY view counts

a fallback-answered case as the primary's own execution failure; the

FALLBACK view counts a primary-answered case as NOT_INVOKED (no data

— not a failure, not a pass). Metrics, safety gates, coverage, and

the decision are computed separately per provider/model; a

primary-model PASS never automatically qualifies the fallback; the

fallback remains execution-failure-only.



**5. Metrics and severity.** Reported separately per model: total /

eligible / authoritative / ambiguous / contract-negative counts;

valid structured response rate; MATCH precision; MATCH recall;

NO_MATCH accuracy; UNCERTAIN rate; false-MATCH count; false-NO_MATCH

count; HARD_CONFLICT false-MATCH count; packaging/bundle false-MATCH

count; accessory false-MATCH count; near-miss false-MATCH count;

sales-unit-safety false-MATCH count; false-MATCH examples WITH CASE

IDS; performance by U1/U2/U3/U4/U5 substate; performance by product

category; runtime failure count by bounded status; primary/fallback

provenance per case. Semantic errors are separate surfaces from

parser failures and execution failures — errors are never hidden

inside aggregate accuracy. Ambiguous cases remain VISIBLE in reports

(defensible / outside-defensible, with examples) but are excluded

from hard accuracy; contract-negative cases are scored on rejection

correctness only. A metric with an insufficient denominator is

reported `unavailable` (never 0%, never 100%). Severity is

deterministic and label-driven (model confidence NEVER overrides the

independent ground truth): CRITICAL = false MATCH violating an

independently established ALWAYS_HARD conflict or commercial sales-

unit safety; HIGH = false MATCH on a materially different product

without an established hard-conflict label; MEDIUM = false NO_MATCH

that reduces recall (expected MATCH); REVIEW = UNCERTAIN where a

definite answer is expected, or an ambiguous case outside its

defensible set (an outside-defensible MATCH is HIGH — a false MATCH

is materially worse than UNCERTAIN — but can never be CRITICAL: an

ambiguous label does not independently establish a hard conflict).



**6. Safety gates and decision.** MANDATORY hard safety conditions

(not configurable): zero false MATCH on independently established

ALWAYS_HARD conflicts; zero false MATCH on known packaging-quantity

conflicts; zero false MATCH on known accessory/product-role

conflicts; zero schema-bypass acceptance; zero unauthorized authority

promotion — including the input-aware cross-check the production

parser cannot see (MATCH_AUTHORIZED_IDENTIFIER_RELATION is lawful

only when the recorded input labeled MANUFACTURER_RELATION_AUTHORITY;

a CUSTOMER_RETRIEVAL_RELATION input never qualifies the claim); zero

contract-version mismatch accepted; zero missing required evaluation

silently treated as PASS. Configurable thresholds live in a SEPARATE

reviewable policy artifact, DRAFT until approval: the proposed values

(match precision >= 0.99; MATCH recall >= 0.90; valid structured

response rate >= 0.99; eligible coverage >= 1.00) are PROPOSALS, NOT

finalized production acceptance thresholds. Without an APPROVED

qualification policy the final status is POLICY_PENDING, not PASS.

Decision precedence keeps the most severe finding visible:

NOT_QUALIFIED (any hard safety gate failure — even with high

aggregate accuracy and even while the policy is pending) >

POLICY_PENDING > INCOMPLETE_COVERAGE (any eligible case without an

accepted parser-valid response from that model) > BELOW_THRESHOLD /

THRESHOLD_INDETERMINATE > QUALIFIED (PASS — unreachable in Q3-A). A

void evaluation (corpus/capture binding mismatch) is FAIL_CLOSED with

an explicit fail-closed report; a safety failure and coverage facts

stay visible in the rationale regardless of the decision.



**7. The committed baseline.** `reports/q3a_baseline/` — the explicit

no-capture reports for BOTH pinned route candidates: 43/43 eligible

cases NOT_CAPTURED, 13/13 contract-negative cases rejected as

expected, all eight gates pass, decision POLICY_PENDING (coverage +

DRAFT-policy facts in the rationale), reproducible byte-for-byte by

test. This is the honest Q3-A state: no live V2 responses exist yet

(V2 is persist-only and unqualified; no historical production V2

record exists), so the harness ships ready for the later live-capture

phase and the qualification decision is explicitly NOT made.



**8. Report identity binding.** Every report records: semantic

contract version (V2), prompt version (2.0), input schema version (1),

output schema version (1), authority contract version

(SEMANTIC_AUTHORITY_V2_S2A_FU2), provider, model, corpus digest,

system-prompt digest (of the REAL frozen prompt text — the harness

renders with `build_semantic_prompt_v2` and carries no prompt copy),

corpus input digest, runtime configuration identity (pinned primary /

fallback routes, temperature 0.0, max_tokens 32768, the

V2_AUTHORITY_QUALIFIED marker as-is), capture provenance (run id,

instant, captured-by), and the evaluation timestamp; the report

digest is computed over everything except the generation instant (the

offline report is reproducible). `verify_report` fails closed against

a mutated corpus (corpus digest + per-case expected-label snapshot) —

historical results remain associated with their original versions,

and a capture bound to the original corpus digest cannot be evaluated

against a revised corpus (it fails closed instead of silently

re-scoring).



**9. Architecture boundary.** The harness must use the real frozen

research/semantic surface (no recreated prompt or parser), so the

A1-FU2 evaluation->research EXACT-ALLOWLIST mechanism is extended by

EXACTLY SIX named files (`corpus.py`, `fixtures.py`, `capture.py`,

`evaluator.py`, `gates.py`, `report.py`); `canonical.py`, `policy.py`,

`cli.py`, and `__init__.py` remain research-independent. The A1-FU2

entry remains exactly one file (that decision is unchanged). Least

privilege, exact paths, no prefix/glob/regex match; locked by

`test_qualification_v2_exception_is_an_exact_allowlist` plus the

preserved A1-FU2 mechanism test. The harness imports no execution /

runs / web / providers / Django / aggregation / human-review / price-

codec surface (mechanically guarded); the live transport is never

imported during offline replay (tested with the socket layer blocked).



**10. Authority firewall (binding).** Q3-A is evaluation

infrastructure only: 4A Machine Price, Reviewed Price, AI-Assisted

Comparable pricing, human-review authority, the V2 qualification

marker, the S2-A relationship requirements, the S2-A

ProductEvidenceQuality rules, and the existing V1 runtime behavior

are all unchanged. The report grants no authority; no decision token

grants one; `V2_AUTHORITY_QUALIFIED` remains False.



**11. Explicit non-goals.** No live model qualification; no captured

V2 responses shipped; no approved policy (the policy artifact stays

DRAFT); no V1 -> V2 switch decision (that belongs to the later

qualification completion); no new production code path; no migration;

no deployment.
### 26.29 SEMANTIC-AUTHORITY-V2-Q3-A-FU1: Independent Model
Qualification Capture

(PENDING FINAL REVIEW — decision record: AD-073; Q3-A recorded as
REVIEWED / NOT APPROVED / NOT FROZEN per the FU1 operator briefing)

Bounded CAPTURE-ARCHITECTURE corrective follow-up on the reviewed Q3-A
candidate (AD-072), on the authoritative starting SHA
`8435864e7517c17843a7406a79de4c819a6ef2fa` (baseline collection 6748).
FU1 corrects the one blocking architecture defect found in Q3-A
review: the Q3-A capture contract is ONE production run of the frozen
pinned route (primary attempt; fallback only after an eligible primary
EXECUTION failure), so a normal run finalizes every case on the
primary's success and the fallback view of that run is all NOT_INVOKED
— a single production-route capture structurally cannot provide full
qualification coverage for BOTH models independently. The correction
does NOT manufacture primary failures and does NOT change production
fallback behavior: it introduces two explicitly distinct, versioned
capture modes and a dedicated independent evaluator/report path for
the benchmark-only mode. OFFLINE INFRASTRUCTURE ONLY: no live model
calls in FU1 (the controlled capture runner is Q3-B); no frozen
production artifact changes (prompt 2.0, input/output schemas, reason
codes, eligibility, authority matrix, persistence adapter, runtime
route byte-untouched; corpus digest unchanged; DRAFT policy unchanged;
`V2_AUTHORITY_QUALIFIED = False`; no migration; no deployment).

**1. The two capture modes (separate typed documents).** Mode A
PRODUCTION_ROUTE: the existing `capture.py` schema v1, unchanged and
still readable (primary first; fallback on eligible primary execution
failure only, frozen reason mapping; a successful primary finalizes
the route; a fallback response never qualifies the primary and vice
versa; NOT_INVOKED retained); the production-route report now
explicitly identifies the mode (capture section carries
`capture_mode: PRODUCTION_ROUTE` + `capture_schema_version: 1` —
additive identity fields; the committed no-capture baselines are
unaffected). Mode B DIRECT_MODEL_QUALIFICATION: NEW
`product_intelligence/evaluation/semantic_v2/direct_capture.py`
(`direct_capture_schema_version: 1`): each capture targets EXACTLY
ONE pinned provider/model (amax/qwen3.8-27b or
vllm-262k/Qwen3.6-27B-262K — wrong/unknown/mixed identities fail
closed; no other model may enter the frozen V2 qualification); every
eligible semantic case is that model's own single bounded execution
(one `execution_status` from OK + the frozen runtime execution-
failure vocabulary; `raw_output` iff OK); NO primary-before-fallback
requirement, NO artificial primary failures, NO production routing,
NO production execution or pricing authority; the model identity is
bound to the document and to each record's interpretation; the exact
frozen corpus id/version/digest + semantic contract V2 + prompt 2.0
are preserved; each capture carries a distinct run id + provenance;
duplicate case IDs, unknown case IDs, contract-negative records
(schema-bypass attack), and corpus/prompt/contract mismatches all
fail closed; missing eligible cases are NOT a load error — they
surface as NOT_CAPTURED at evaluation (coverage shortfall, never a
pass).

**2. Backward compatibility.** Cross-mode decoding fails closed in
both directions (production loader refuses direct documents on the
exact key sets; direct loader refuses production documents with an
explicit cross-mode error; hybrids refused by both); old captures are
never reinterpreted or silently migrated; historical production-route
report identity is preserved (committed baselines remain byte-
identical, proven by test).

**3. The independent direct-model evaluator.** NEW
`evaluate_direct_for_model` (in `evaluator.py`; never imports or
invokes the production orchestration path — mechanically verified):
verifies (a) exact provider/model identity against the frozen pinned
routes, (b) the capture's bound target == the requested model
(responses never transfer between identities), (c) corpus id/version/
digest, (d) semantic contract V2 + prompt 2.0, (e) every case id —
and fails closed (`QualificationContractError`) on any mismatch,
including cross-mode artifact presentation (typed guards in BOTH
evaluators). Per-case states: EVALUATED (OK + parser-valid) /
RUNTIME_FAILURE (bounded status, preserved separately) / NOT_CAPTURED
(no record) / CAPTURE_INTEGRITY_FAILURE (OK but the raw output does
not survive the parser — never substituted with the expected answer).
It reuses the FROZEN production V2 parser composition UNCHANGED
(`parse_semantic_response_v2` + `validate_semantic_response_v2` via
`classify_raw_response`) and the same label-driven scoring / severity
/ metric surface — no approximation; NO NOT_INVOKED state exists in
this mode. A complete direct-model qualification requires all 43
eligible semantic cases to have an accepted, parser-valid response;
primary and fallback must each satisfy this independently. The two
modes' coverage denominators are never mixed (a full direct fallback
capture is 43 evaluated / 0 NOT_INVOKED while the same model's
production-route view of a primary-answered run stays 0 evaluated /
43 NOT_INVOKED).

**4. Safety and decisions.** The eight MANDATORY hard safety gates
and the fail-closed decision vocabulary (FAIL_CLOSED / NOT_QUALIFIED
/ POLICY_PENDING / INCOMPLETE_COVERAGE / THRESHOLD_INDETERMINATE /
BELOW_THRESHOLD / QUALIFIED) are unchanged and work identically in
both modes (gate-for-gate equality proven, including the input-aware
authority-promotion cross-check). The policy remains DRAFT, so no
QUALIFIED result is produced under it (full correct direct captures
stay POLICY_PENDING); `V2_AUTHORITY_QUALIFIED` remains False; no
Machine Price / Reviewed Price / human-review authority change.

**5. Reporting.** NEW `build_direct_report` / `verify_direct_report`
(report kind SEMANTIC_V2_DIRECT_MODEL_QUALIFICATION_OFFLINE)
explicitly identifying: capture mode, capture schema version,
provider/model (bound target), corpus identity + digest, frozen
contract/prompt identity (real system-prompt digest), capture run id
+ provenance, evaluation timestamp, eligible/evaluated/not-captured/
runtime-failure/invalid-response counts WITH case ids + completeness
flag, per-substate / per-category performance, false-MATCH case IDs,
the eight gate results, the policy status (DRAFT), and the decision.
Each mode's verifier REFUSES the other mode's reports (cross-mode
kind check, fail closed); the two modes' reports are never silently
combined. Production-route `build_report` content is unchanged.

**6. CLI.** NEW `evaluate-direct` command (one report per pinned
model per direct capture; void evaluations emit an explicit
FAIL_CLOSED direct-kind report); the existing `evaluate` command is
unchanged in behavior.

**7. Architecture boundary (preserved, strengthened).**
`direct_capture.py` is RESEARCH-INDEPENDENT (it re-imports the frozen
route/contract pins from the allowlisted `capture.py`), so the Q3-A
evaluation->research exact allowlist remains EXACTLY THE SAME SIX
FILES — no new exception, no prefix/glob/regex. The Q3-A mechanism
test `test_qualification_v2_exception_is_an_exact_allowlist` is
strengthened in place (strictly additive: `direct_capture.py` pinned
as a non-allowlisted module that must exist and remain research-
independent).

**8. Ground truth and safety (unchanged).** Corpus untouched: 56
cases (43 semantic: 36 AUTHORITATIVE + 7 AMBIGUOUS; 13
CONTRACT_NEGATIVE); the motivating Micron case
(`MTFDKCC3T8TGP-1BK1DABYYR` vs `MTFDKCC3T8TGP-1BK1DABYY`,
`V2Q-SSD-U5NM1-MICRON-0018`) still expects UNCERTAIN with
PACKAGING_QUANTITY missing and the commercial sales-unit-safety flag
(a MATCH on it is CRITICAL in both modes — proven); synthetic /
recorded-fixture / real-market provenance stays separate (REAL_MARKET
still loader-rejected).

**9. Tests.** 76 NEW nodes in `tests/evaluation/semantic_v2/`
(test_q3a_fu1_direct_capture.py 35; test_q3a_fu1_direct_evaluation.py
19; test_q3a_fu1_qualification.py 12; test_q3a_fu1_reports.py 10; +
shared _q3a_fu1_helpers.py) covering all 32 mandated properties. No
test deleted/renamed/skipped/xfail/deselected/ignored/weakened; no
file decreased; the Windows subprocess flake allowlist NOT expanded.
Collection 6748 -> 6828 (+80 = 76 new-file nodes + 4 auto-expanded
parameterized scans for direct_capture.py).

**10. Explicit non-goals.** No live model qualification (Q3-B
implements the controlled capture runner after independent FU1
approval); no approved policy; no V1 -> V2 switch decision; no
production execution or pricing authority; no migration; no
deployment.


### 26.30 SEMANTIC-AUTHORITY-V2-Q3-B: Controlled Live
Direct-Model Capture

(IMPLEMENTED / PENDING FINAL REVIEW — decision record: AD-074; Q3-A
and Q3-A-FU1 recorded as APPROVED / FROZEN per the Q3-B operator
briefing)

Bounded LIVE-QUALIFICATION-EVIDENCE phase on the authoritative
starting SHA `517ef25c7ce83bba364234dda46270b147c0c053` (Q3-A-FU1
endpoint; baseline collection 6828). Q3-A and Q3-A-FU1 are recorded
as APPROVED / FROZEN per the Q3-B operator briefing, so the frozen
DIRECT_MODEL_QUALIFICATION capture schema (AD-073) and the
independent offline evaluator / report path it defined are the
contract this phase executes against. Q3-B implements the bounded,
controlled LIVE capture runner that Q3-A-FU1 explicitly deferred: it
runs the frozen Semantic V2 qualification corpus INDEPENDENTLY
against each of the two pinned models, captures their real responses
as a strict DIRECT_MODEL_QUALIFICATION document, and replays that
document through the approved offline evaluator. **This phase
collects evidence only.** It grants no qualification, no pricing
authority, and no human-review authority; the qualification policy
stays DRAFT; `V2_AUTHORITY_QUALIFIED` stays False; the decision
stays POLICY_PENDING (at best) under the shipped DRAFT policy.

**1. Frozen models (both captured independently).** Primary
`amax / qwen3.8-27b`; fallback `vllm-262k / Qwen3.6-27B-262K`. Each
model is run as its OWN single-model DIRECT_MODEL_QUALIFICATION
capture - the runner targets exactly one pinned provider/model per
run, and the two identities must each be captured independently.
The runner NEVER simulates a primary failure to reach the fallback,
never performs production primary-before-fallback routing, and never
transfers a response between the two model identities. No other
provider/model may enter the frozen V2 qualification (wrong / unknown
/ mixed identities fail closed).

**2. Separate benchmark-only live capture runner (NEW
`product_intelligence/evaluation/semantic_v2/live_capture.py`).**
The runner is a BENCHMARK-ONLY live entry point, deliberately
separate from production orchestration. It reuses, never recreates:
(a) the FROZEN production V2 prompt builder
(`semantic.contract_v2.build_semantic_prompt_v2`) over the REAL typed
corpus case (`CorpusCase.build_semantic_case`) - every sent prompt is
byte-exact output of the frozen builder; (b) the approved Q3-A-FU1
direct-capture schema (`direct_capture.py`) - the written document
loads and verifies through the UNCHANGED `load_direct_capture` /
`verify_direct_capture_against_corpus`; (c) the frozen production V2
parser composition (`evaluator.classify_raw_response` =
`parse_semantic_response_v2` + `validate_semantic_response_v2`) for
per-attempt classification, exactly as the production runtime
boundary classifies; (d) the approved provider transport /
configuration mechanism
(`semantic.transport.get_openai_transport_for_provider`), read from
the server environment. The runner preserves the exact corpus
digest + semantic contract + prompt identity, and pins the
provider/model identity. It imports NO production orchestration
(no execution / runs / web / providers / framework surface), does
NO pricing or human-review work, and enables NO authority
(`V2_AUTHORITY_QUALIFIED` stays False). It introduces no
general-purpose autonomous agent: it is a bounded, operator-invoked
capture loop over the fixed 43-case corpus.

**3. Live transport boundary (lazy, approved mechanism only).** The
live transport module is imported LAZILY - only inside transport
construction (`build_live_transport`), never at module import time -
so importing the runner loads no network client and no live call
happens until the operator explicitly runs it. All environment
access stays inside the approved transport adapter: the runner names
no `os.environ` read of its own. An unconfigured provider fails
closed (bounded `LiveCaptureConfigError`, no credential value, no
network call, no artifact written) BEFORE any case is sent. If the
approved transport cannot be safely reused, the phase stops and
reports the exact integration boundary rather than opening an
undocumented network path.

**4. Bounded timeouts, concurrency, and the FIXED retry policy.**
The request timeout is bounded (default 300.0 s, hard bound 3600.0
s - mirrors of the frozen runtime bounds, drift-pinned); a
non-finite / non-positive / out-of-bounds timeout fails closed.
Concurrency is bounded (default 1 sequential, hard bound 4) and
recorded in the manifest. The retry policy is FIXED before
collection and documented in the module + every manifest:

* a transient transport failure that produced NO model output
  (TIMEOUT, DNS_ERROR, TLS_ERROR, CONNECTION_ERROR, RATE_LIMITED,
  PROVIDER_UNAVAILABLE) may be retried with the IDENTICAL request,
  at most `max_attempts` times total (1..3, bounded);
* a definitive per-case outcome - a provider response body or an
  output/identity-contract failure (OK, HTTP_ERROR, EMPTY_RESPONSE,
  MALFORMED_JSON, SCHEMA_INVALID, INVALID_RESPONSE,
  MODEL_IDENTITY_MISMATCH) - is FINAL after exactly one call: it is
  never retried, and a response is never cherry-picked between
  attempts;
* a semantic disagreement with the ground truth is NEVER a retry
  reason (the runner has no access to the label and no semantic
  decision may re-trigger a call);
* a run-level identity / configuration break (AUTHENTICATION_FAILED,
  MODEL_NOT_FOUND, INVALID_REQUEST_CONFIGURATION,
  UNSUPPORTED_PARAMETER) or an unrecognized transport code aborts the
  run after recording the attempted case (bounded, in-vocabulary
  evidence only);
* CASE_REJECTED (a content-policy rejection of the case's own
  content) is CASE-LOCAL per the frozen transport vocabulary: the run
  continues, the case is documented in the manifest only (its status
  is outside the direct-capture vocabulary, so it has no document
  record and replays as NOT_CAPTURED - a coverage shortfall, never a
  pass).

**5. Capture discipline (no fabrication, no silent skips).** For the
target model, ALL 43 eligible semantic cases are attempted (in corpus
order); the 13 CONTRACT_NEGATIVE cases are NEVER rendered into a
prompt, NEVER sent, and NEVER recorded. Every attempted case
preserves: its case id, the exact model identity (bound to the
document and each record's interpretation), the frozen
prompt/input identity (per-case prompt digest + the REAL
system-prompt digest), its bounded execution status, the raw model
response when (and only when) the status is OK, and the run id +
timestamps. A missing or incomplete capture is NOT a pass: it
replays as NOT_CAPTURED / RUNTIME_FAILURE / CAPTURE_INTEGRITY_
FAILURE and the decision stays fail-closed. The runner never
substitutes an expected answer for a failure and never manufactures a
response.

**6. Offline replay (approved evaluator, separate reports).** After
live capture, each model's document is replayed through the
UNCHANGED `evaluate_direct_for_model` + `gates` + `policy` +
`decide` + `build_direct_report` / `verify_direct_report` path (the
`evaluate-direct` CLI), producing a SEPARATE report for
`amax/qwen3.8-27b` and for `vllm-262k/Qwen3.6-27B-262K`. Each report
covers: coverage (eligible / evaluated / not-captured /
runtime-failure / invalid-response, WITH case ids + completeness
flag), valid-response rate, MATCH precision / recall, false-MATCH
case ids, HARD_CONFLICT errors, packaging / bundle errors, accessory
/ product-role errors, near-miss errors, ambiguous-case behavior,
runtime failures, per-category and per-substate metrics, the eight
mandatory safety gates, the DRAFT policy status, and the decision.
The qualification policy stays DRAFT; the decision stays
POLICY_PENDING (at best) and no report grants authority.

**7. Evidence integrity.** Capture artifacts are stored separately
from the corpus labels (runner-managed directory, not the corpus
tree)
as (a) the strict DIRECT_MODEL_QUALIFICATION capture document
(the frozen schema) and (b) a runner manifest sidecar (run identity,
fixed retry policy, bounded per-case attempt evidence, prompt
digests; evidence only - the evaluator never reads it). Expected
labels are never modified based on model responses. Every report
binds the corpus digest, the prompt (REAL system prompt) digest, the
semantic contract version, the provider/model, the capture run id,
and the evaluation timestamp. A missing or incomplete capture never
becomes a PASS.

**8. Credentials and safety.** No API key, base URL, Authorization
header, or other credential value is ever hardcoded, printed, or
written to an artifact: the transport adapter reads the server
environment; the manifest records key PRESENCE as a bare bool; error
messages are bounded and name no secret. The frozen Semantic V2
runtime is NOT modified to accommodate the benchmark.

**9. Tests (NEW
`tests/evaluation/semantic_v2/test_q3b_live_capture.py`, 80 nodes;
every model call is a scripted, recording test double - no live
network call anywhere in the file, and the full pipeline is re-proven
under a blocked socket).** Exact model pinning (pinned primary +
fallback accepted; unknown / mixed / whitespace identities fail
closed; generation parameters are the frozen pins and drift-pinned
against production; the classification mirror matches the frozen
runtime table). Frozen prompt fidelity (every sent prompt is
byte-exact frozen-builder output; the manifest binds the REAL system
prompt by digest, equal to the report's construction; the artifact
carries the frozen contract identity + per-case prompt digests).
Transport boundary (no module-level transport import; construction
uses the approved environment mechanism; an unconfigured provider
fails closed before any call; an injected transport needs no
environment; the runner reads no environment of its own). No
credential leakage (no key / endpoint value in any artifact; the
transport section carries only the bounded fields; the summary is
secret-free). Timeout handling (invalid / out-of-bounds timeouts fail
closed; the configured timeout reaches the transport; a timeout is
classified and preserved). Bounded retry (retryable-then-success
records the single real output; retries are hard-bounded; every
retryable status is retried then recorded; the max-attempts bound is
enforced; the policy buckets are complete and disjoint). No
semantic-error retries / no best-of-N (every output / identity
failure is final after one call; an unfavorable semantic decision is
never retried and is scored as-is; a successful first attempt never
gets a second call; exactly one record per case; an invalid output is
never replaced by a later one). No contract-negative model calls (the
13 are never rendered / sent / recorded). Complete traversal (all 43
attempted in corpus order; a completed run leaves no case unaccounted
for). Failure preservation (bounded statuses verbatim; a run abort
preserves attempted evidence and names the unattempted cases; an
out-of-vocabulary abort writes manifest only; CASE_REJECTED stays
case-local and replays NOT_CAPTURED). Independent model capture (two
separate documents; a document never transfers to the other
identity). Capture schema validation (the written document round-
trips the frozen loader; a tampered corpus digest or record status
fails closed). Offline replay fidelity (a full correct capture
replays to 43 EVALUATED and stays POLICY_PENDING under the DRAFT
policy; the direct report builds, verifies, and binds the run). No
production execution imports (no execution / runs / web / providers /
framework surface enters the process; the module names no forbidden
surface). No authority promotion (the marker stays False; artifacts
grant no authority token). No pricing contamination (artifacts name
no pricing / review surface). No network calls during ordinary unit
tests (full fake pipeline + dry-run + CLI dry-run + CLI
unpinned-route refusal under a blocked socket). Bounded concurrency
(the bound is enforced; concurrent execution never exceeds it and
records stay in corpus order; a concurrent run matches a sequential
run).

The Q3-A / Q3-A-FU1 architecture guards are PRESERVED and STRENGTHENED
in place (strictly additive): the offline-harness
"names-no-AI-surface" guard pins `live_capture.py` as the ONE module
that may reference the live transport surface (exempted from the
substring scan, load-bearing asserted); the direct-model AST guard
pins that the runner's transport reference is exactly ONE lazy
function-level import of the approved factory (no module-level
transport import, the production runtime module still forbidden).
The Q3-A evaluation->research exact-allowlist remains EXACTLY THE SAME
SIX FILES (the live runner is research-independent: it re-imports the
frozen route / contract pins from the allowlisted `capture.py` /
`direct_capture.py` and the corpus / prompt surfaces from their
allowlisted / semantic owners - no new research exception). No test
deleted / renamed / skipped / xfailed / deselected / ignored /
weakened; no file decreased; the Windows subprocess flake allowlist
NOT expanded. Collection 6828 -> 6912 (+84 = 80 new-file nodes + 4
auto-expanded parameterized scans for `live_capture.py` [vendor-token
+1, stdlib-imports +1, web inner-layer +1, providers INNER_ROOTS
+1]).

**10. Explicit non-goals.** No qualification decision (the decision
stays POLICY_PENDING under the DRAFT policy - granting qualification
is a later, separately approved phase); no approved policy; no
`V2_AUTHORITY_QUALIFIED = True`; no V1 -> V2 switch decision; no
production execution / routing / pricing / human-review authority; no
general-purpose autonomous agent; no modification of the frozen
Semantic V2 runtime, prompt, corpus labels, or DRAFT policy; no
simulation of primary failure to reach the fallback; no deployment.
If live credentials or an endpoint are unavailable, the bounded
runner + tests are still delivered and the phase stops before
claiming live qualification results for that model.
