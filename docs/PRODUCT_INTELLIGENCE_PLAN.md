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
├── product_intelligence/
│   ├── domain/                        contracts + vocabularies (0A)
│   ├── research/                      research core (not implemented)
│   ├── providers/                     provider boundaries (not implemented)
│   └── web/                           intake + presentation (not implemented)
└── tests/                             focused deterministic tests
```

Status: `IMPLEMENTED` for the layout, the domain layer, and the Django
project skeleton. `APPROVED / PLANNED` for every box below "Canonical
Research Request" in the diagram.

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

Status: `IMPLEMENTED` — as contracts with contract-level validation only. No
logic consumes them yet.

Deliberately **not** modelled yet: `ResearchRun` as an entity, listings,
price aggregates, comparable products, specifications. Building the full
schema before the behaviour exists would guess wrong.

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

## 15. Research-run lifecycle direction

A research attempt is a first-class record with its own identity, so that a
report is durable, addressable, and re-openable.

Planned states (vocabulary `IMPLEMENTED` as `ResearchRunState`, machinery
`APPROVED / PLANNED` for 1A):

```text
created → running → completed
                  → partially_completed
                  → failed
```

`partially_completed` is deliberate: a run that found pricing but no
comparables is a useful, honest result and must be representable.

A completed run is addressable at:

```text
/research/<research-id>
```

The identifier scheme (UUID vs. opaque slug) and whether report URLs are
guessable are `UNDECIDED` and must be settled in 1A alongside §19.

Status: `APPROVED / PLANNED`. No run entity, persistence, or state machine
exists.

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
* **Report URLs are not an access-control mechanism.** Whether reports need
  authentication, and what visibility they have, is `UNDECIDED` and must be
  settled before any deployment beyond a trusted internal network.
* **`DEBUG` off and a real `SECRET_KEY`** are required for any deployment.
  The repository default is explicitly development-only.

Authentication and authorization are `DEFERRED`; no phase before 8C assumes
them.

Status: `APPROVED / PLANNED`. `IMPLEMENTED` today only as: no secrets in the
repository, and environment-sourced Django settings.

## 20. Testing strategy

Principles:

* **Deterministic by default.** No test depends on the network, on a live
  vendor, or on model output.
* **Contracts are tested at the contract level.** Validation rules that the
  whole system relies on get direct tests.
* **Architecture invariants are tested mechanically, not just documented.**
  `tests/domain/test_domain_boundaries.py` fails if the domain gains a
  non-stdlib import, a calling-system concept, or a vendor name.
* **No placeholder tests for unbuilt behaviour.** A test for search
  behaviour that does not exist is noise.
* **Provider interactions will use recorded fixtures**, never live calls, so
  the suite stays deterministic (`APPROVED / PLANNED` from 2B).

Status: `IMPLEMENTED` for the domain contracts and the architecture guards.

## 21. Evaluation strategy

Testing proves the code does what it says. Evaluation proves the *answers*
are good — these are different problems, and research quality needs the
second one.

Planned (0B, the next phase):

* A curated corpus of real part numbers and descriptions with known-correct
  expectations, including deliberately hard cases: near-miss part numbers,
  accessory-vs-product confusion, ambiguous descriptions, discontinued parts,
  and parts with no observable market.
* Measures that matter more than accuracy alone: **false-confidence rate**
  (confidently wrong), **abstention correctness** (said unknown when it
  should have), and price-range plausibility.
* The corpus is the basis for the `UNDECIDED` thresholds in §16.

Status: `APPROVED / PLANNED` — phase 0B. Not started.

## 22. Approved phased roadmap

```text
PRODUCT-INTEL.0A   Architecture + domain contracts              IMPLEMENTED
PRODUCT-INTEL.0B   Evaluation corpus                            NEXT
PRODUCT-INTEL.1A   ResearchRun lifecycle
PRODUCT-INTEL.1B   Basic standalone web research/report shell
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

Every phase after 0A is `APPROVED / PLANNED` and unimplemented. Do not
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

Also deferred as capability, per the roadmap rather than per this list: real
web search, real product lookup, LLM calls, prompt engineering, price
calculation, listing extraction, comparable discovery, similarity scoring,
launcher code of any kind, and the research API.

Open questions currently `UNDECIDED`: search vendor · LLM vendor · research
identifier scheme · report access control · which aggregate represents
"market price" · outlier handling · description truncation policy for URL
length limits · first product category · cache storage mechanism · batch
intake design.

## 24. CURRENT STATUS

```text
CURRENT STATUS

Completed:
- PRODUCT-INTEL.0A
- PRODUCT-INTEL.0A-FU1 (corrective follow-up attached to 0A)

Current approved implementation state:
- Project architecture established
- Durable Claude guidance established
- Initial domain contracts established
- Focused contract tests established

Not yet implemented:
- Evaluation corpus
- ResearchRun lifecycle
- Web research UI
- Search providers
- LLM providers
- Market pricing
- Comparable products
- FoxPro integration
- SAP integration

Next planned phase:
- PRODUCT-INTEL.0B — Evaluation corpus
```

Concretely, the repository contains: this document, `CLAUDE.md`, `README.md`, a
minimal Django project skeleton with no applications and no models, the domain
contract layer, empty boundary packages carrying their rules as documentation,
and 65 passing tests. There is no research capability of any kind.

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
| AD-017 | Target runtime is Python 3.12; code avoids version-specific syntax. Approved target: **Python 3.12**. Interpreter available during 0A development: **Python 3.10.1**. | 3.12 is the approved direction, but the development machine has 3.10.1 (with Django and pytest), and the domain layer should not be gratuitously incompatible. The distinction is recorded rather than resolved: this is an environment gap, not an architecture change. | Accepted |
| AD-019 | An established `ProductIdentity` must carry the part-number evidence its match type claims: `EXACT` requires a part number, `NORMALIZED_EXACT` requires both a part number and the normalized form. | The type could otherwise represent a state that cannot exist — a character-for-character match against no part number, reporting itself established at high confidence. That is precisely the fabricated certainty AD-009 forbids, expressed as a data structure. Enforcing it at construction keeps `is_established` a report rather than a compensation, and the rule uses only fields already in the contract, so it adds no matching or normalization logic. Weaker match types stay unconstrained: `DESCRIPTION_ONLY` *means* no part-number evidence. | Accepted (0A-FU1) |
