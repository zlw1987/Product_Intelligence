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
│   ├── research/                      part-number comparison (2A) +
│   │                                  raw listing extraction (3A)
│   ├── providers/                     search boundary (2B) + Serper (2C) +
│   │                                  page-fetch boundary and fetcher (3A)
│   └── web/                           standalone form + report shell (1B)
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

`web/` became a Django application in 1B, holding the intake form, two views,
the routes, and the templates. It contains no model: a run outlives the request
that created it and belongs to no caller, so the lifecycle stays in `runs/`
(AD-025, AD-032). The dependency arrow points one way — `web` imports `domain`
and `runs`, and a guard test fails if any inner layer imports `web`.

Status: `IMPLEMENTED` for the layout, the domain layer, the evaluation corpus
layer, the run-persistence layer, the Django project, the standalone web intake
and report shell, the deterministic part-number comparison primitive inside the
core (§12.1), the search-provider boundary (§13.1), its first real adapter
(§13.5), the page-fetch boundary and its standard-library fetcher (§13.6),
deterministic raw listing extraction (§16.1), and deterministic listing
normalization (§16.2). `APPROVED / PLANNED` for every box below "Canonical
Research Request" in the diagram: a run records *that* research was requested
and how it ended, and the web shell starts nothing. The core can now compare
two part numbers it is handed, fetch a public page safely, extract raw listing
observations from what that page publishes, and turn one raw observation's
commercial attributes into a deterministic value or a recorded reason it could
not — but nothing orchestrates that sequence, and nothing in the run lifecycle
or the web shell invokes any of it, so no box in the diagram from "Product
Resolver" onward does anything yet.

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

Status: `IMPLEMENTED` for the standalone web form (1B), which normalizes its two
submitted strings into a `ResearchRequest` and creates one run.
`APPROVED / PLANNED` for every other mechanism. Nothing downstream of the
canonical request exists, so an intake produces a recorded request, not
research.

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

**The shell executes no research, and says so.** A submitted run is `CREATED`
and stays there: the web layer never calls `transition_to`, because there is
nothing to run. The report states that research execution is not connected yet
rather than showing a spinner, a progress bar, or a poll — a fake progress
indicator is fabricated certainty with an animation (AD-009, AD-034). It shows
the identifier, state, MPN, description, and `created_at`, with `started_at` and
`finished_at` displayed only if a run ever carries them. There is no placeholder
price, median, seller table, or example comparable, and no evaluation-corpus
case is displayed as though it were a result.

A GET creates nothing whatever query parameters it carries. The launcher entry
point that turns `?mpn=…&description=…` into a run belongs to 5B (AD-033); a GET
that created records would let a prefetch, a crawler, or a refresh start
research.

MPN and description are untrusted input from every intake, so they are rendered
through ordinary Django auto-escaping and never marked safe. CSRF protection is
enabled on the POST. The identifier in a report URL is still not access control
(§19): report visibility remains `UNDECIDED`, so this shell is for local
development and trusted internal use, not public deployment.

Status: `IMPLEMENTED` (1B) for the form, the report shell, the routes, and the
run creation between them. `APPROVED / PLANNED` for everything the report would
display once research exists.

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

Status: `IMPLEMENTED` — as contracts with contract-level validation only. Two
things consume them: the persistence layer (§15), which stores a
`ResearchRequest` and rebuilds one, and the part-number comparison primitive
(§12.1), which reads the part number a request carries. Nothing researches
anything, and nothing in the domain compares or normalizes a part number.

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

**Nothing is wired to it.** The primitive supplies a comparison; no phase yet
supplies a candidate. The web shell, the run lifecycle, and the corpus are
unchanged, and a guard test asserts that `runs/`, `web/`, and `evaluation/` do
not import the research core (AD-036).

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
split. No LLM is integrated. No prompts exist.

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

A future **internal or distributor price source** enters through this same
boundary, as one more provider. It must not become conditional logic in the core
for one company's systems. Internal commercial pricing and public market pricing
are distinct classes of evidence and must not automatically share one aggregate
(§16); exposing internal pricing through a report also makes report access
control a blocker rather than a deferred question (§19).

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

**Still nothing is wired to it.** `runs/` and `web/` import no part of
`product_intelligence.providers`, and the guard test that checks this now also
covers `providers/serper.py` by construction (it scans every file under
`providers/`). A submitted run is still `CREATED`, and research execution is
still not connected. Serper is a metered, paid-per-request API; because
nothing in ordinary application execution calls it yet, duplicate-call
protection (§18.1) is not yet a live exposure — but it becomes one the moment
a later phase wires this adapter into research execution, and must be
addressed no later than that phase.

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
timestamps, and its migration; and (1B) for the report at `/research/<id>`,
which reads a run and renders it. The report is read-only: it starts nothing,
transitions nothing, and writes no timestamp. Nothing in the system moves a run
out of `CREATED`, because nothing executes one.

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

3A and 3B are implemented and answer only steps 1 and 2. **No market price is
computed anywhere**, and nothing matches, rejects, or aggregates an
observation — a normalized price does not imply a valid listing, and 3B decides
nothing about whether an observation belongs to the requested product. §16.1
and §16.2 record exactly what was built and what was deliberately left to 3C
and 4A.

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

Status: `APPROVED / PLANNED`. Nothing implemented.

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
* **No integration.** `runs/` and `web/` import no part of `providers/` or of
  the extraction core. A submitted run is still `CREATED`, and the report page
  still says research execution is not connected.
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
* **No integration.** `runs/` and `web/` import no part of `research`'s new
  module — the existing guard that checks the whole `product_intelligence.
  research` namespace already covers it. A submitted run is still `CREATED`.
* **No quantity, pack size, or unit price** — see above.
* **No live call of any kind.** Every test runs against the same recorded 3A
  fixtures or inline synthetic text; the normal `pytest` run makes zero
  network requests, exactly as before.

Status: `IMPLEMENTED` (3B) for deterministic price, currency, availability,
condition, and seller normalization, and for the quantity/pack-size evidence
audit. `APPROVED / PLANNED` for 3C onward. **No listing is accepted, rejected,
or priced anywhere.**

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

Neither is implemented. 2C integrated Serper, which is metered and paid
per request, but wired it into nothing: `search()` is only ever called from an
explicit manual script or from tests against a recorded fixture, so no call
happens as a side effect of ordinary application use and nothing is paid for
twice yet.

Status: `DEFERRED` to 8A for general caching. Storage mechanism is `UNDECIDED`.
Duplicate paid-call protection remains `APPROVED / PLANNED` — required before
Serper is called from ordinary research execution (a later phase), not before
2C, which introduces no such call site. No caching or call-deduplication of any
kind exists.

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
them. **They stop being deferrable at a specific, foreseeable point**, recorded
in 2B so it is not discovered at deployment: the moment a report can expose
internal commercial or vendor pricing (§13.4), report access control becomes a
blocker rather than an open question. Public market pricing shown to an internal
audience is a different exposure from a distributor's negotiated price shown to
whoever holds a URL. Launcher URLs remain URL builders throughout and never
carry provider or authentication secrets (AD-005).

Consequence for the 1B web shell, stated plainly rather than discovered at
deployment time: **anyone who can reach the server can open any report whose
identifier they hold, and can submit a request.** That is acceptable for local
development and a trusted internal network, and it is not acceptable on a public
address. The open question is access control, not the identifier scheme — a
longer UUID would change nothing. 1B added CSRF protection on the form POST and
ordinary output escaping of MPN and description, which are defences against
different problems and are not a substitute.

Status: `APPROVED / PLANNED`. `IMPLEMENTED` today as: no secrets in the
repository, environment-sourced Django settings, an unguessable run identifier
that is explicitly not a permission check, CSRF protection on the one POST, and
untrusted intake text rendered escaped and never marked safe.

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
  `tests/web/test_web_boundaries.py` fails if an inner layer imports the web
  layer, if the web layer gains a model, a vendor name, a provider import, a
  network client, or a call to `transition_to`.
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
  automation dependency, and nothing mocked between the form and the row. The
  honest-reporting rules are tested as behaviour: that a submitted run is
  `CREATED` with no timestamps, that opening a report transitions nothing, and
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
real pages, and the architecture guards.

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
PRODUCT-INTEL.3C   MPN matching + rejection                     NEXT
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

Every phase after 3B is `APPROVED / PLANNED` and unimplemented. Do not
execute a later phase while working on an earlier one.

**The next phase is the priority.** 3B turned raw listing text into
deterministic, comparable values — `"1055.85"` into `Decimal("1055.85")`,
`"undefined"` into `None` plus a recorded `INVALID_PRICE` issue,
`"false"` into `UNKNOWN` availability rather than a guessed `OUT_OF_STOCK` —
without deciding anything about which product a listing describes. That is
exactly what is still missing: nothing yet says whether a normalized listing's
published part number is the one that was requested. 3C — classifying each
normalized observation against `research.identity`'s `EXACT` /
`NORMALIZED_EXACT` / `UNKNOWN` comparison (2A), with every rejection recorded
and its reason kept — is what turns a pile of normalized observations into
evidence a price conclusion could actually cite.

### 22.1 Corrective follow-up phases

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
not read their absence as an oversight: retry / reopen / resume semantics · a
per-transition event or history table · persisted failure diagnostics ·
cross-process transition atomicity · distributed locking · a server database
in place of development SQLite.

Also deferred as capability, per the roadmap rather than per this list: real
product lookup, LLM calls, prompt engineering, price calculation, listing
*matching and rejection*, comparable discovery, similarity scoring, launcher
code of any kind, and the research API. Real web search exists as of 2C, real
page fetching plus raw listing extraction as of 3A, and deterministic listing
normalization as of 3B — all three can be called directly — but
*orchestration* (query generation from a `ResearchRequest`, deciding which
candidate URLs to open, automatic invocation from a research run) remains
deferred: nothing calls `search()`, `fetch()`, or
`normalize_listing_observation()` except an explicit manual script and offline
tests.

Deferred specifically around page fetching and extraction (3A), so that a later
phase does not read their absence as an oversight: browser-rendered fetching of
any kind (headless browser, browser farm, managed scraping service) ·
bot-detection evasion, user-agent rotation, and proxies · retry policy and
backoff · robots/politeness scheduling · crawling, link traversal, and sitemap
discovery · asset fetching · page or response caching · persistence of a
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
from marketing prose (`"like new"`, `"open box"`) · persistence of a
`NormalizedListingObservation` · any acceptance, rejection, confidence, or
aggregate field on the normalized contract.

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
that first calls it from ordinary execution — §18.1) · query generation from a
`ResearchRequest` · automatic invocation from `runs/` or `web/` · page
fetching or crawling of any kind · MPN inference from a title, snippet, or URL
· price extraction from snippet text · a provider error taxonomy beyond the
existing single `SearchProviderError`.

Open questions currently `UNDECIDED`: LLM vendor · report
access control (the identifier scheme was settled in 1A as a random UUID, which
is explicitly not access control) · which aggregate represents
"market price" · outlier handling · description truncation policy for URL
length limits · first product category · cache storage mechanism · batch
intake design · every evaluation pass/fail threshold (§21.3) · the recorded
listing-snapshot format for price evaluation (§21.4). Search vendor is settled
as of 2C: Serper, ordinary Google Search only.

## 24. CURRENT STATUS

```text
CURRENT STATUS

Completed:
- PRODUCT-INTEL.0A
- PRODUCT-INTEL.0A-FU1 (corrective follow-up attached to 0A)
- PRODUCT-INTEL.0B
- PRODUCT-INTEL.1A
- PRODUCT-INTEL.1A-FU1 (corrective follow-up attached to 1A)
- PRODUCT-INTEL.1B
- PRODUCT-INTEL.2A
- PRODUCT-INTEL.2A-FU1 (corrective follow-up attached to 2A)
- PRODUCT-INTEL.2B
- PRODUCT-INTEL.2C
- PRODUCT-INTEL.3A
- PRODUCT-INTEL.3B

Current approved implementation state:
- Project architecture established
- Durable Claude guidance established
- Initial domain contracts established
- Evaluation corpus, its contracts, validation, and loader established
- Persistent ResearchRun lifecycle established
- Standalone web intake form and durable report shell established
- Deterministic part-number comparison primitive established
- Provider-neutral search boundary established (contracts + protocol)
- Serper adapter established: the first real SearchProvider, ordinary Google
  Search, offline fixture-based regression tests, one sanitized recorded
  response, one manual live-smoke script — wired into nothing
- Page-fetch boundary established (PageFetchRequest, FetchedPage, PageFetcher,
  PageFetchError, UnsafeFetchTargetError) with one standard-library fetcher:
  bounded timeout, redirects and response size, HTML-only content types,
  GET-only, no credential, and refusal of non-public destinations revalidated
  on every redirect hop — wired into nothing
- Deterministic raw listing extraction established (ListingObservation +
  schema.org JSON-LD and flat product meta extraction), converting nothing and
  deciding nothing
- Five sanitized recorded real-page fixtures and one manual page-extract smoke
  script established
- Deterministic listing normalization established (NormalizedListingObservation
  + price/currency/availability/condition/seller normalization), deciding no
  identity and computing no aggregate
- Focused contract, lifecycle, web, identity, provider, Serper-adapter,
  page-fetch, extraction, normalization, and boundary tests established

Not yet implemented:
- Research execution of any kind
- Candidate discovery beyond one raw, unorchestrated search call
- Query generation from a ResearchRequest
- Any orchestration from a search result to a page fetch to an extraction to
  a normalization
- Listing matching, rejection, or price aggregation
- Quantity, pack-size, or unit-price normalization (no fixture evidence yet —
  §16.2)
- Browser-rendered fetching (not justified by the 3A sample - see 13.6)
- Crawling or link traversal
- LLM providers
- Product resolver
- Description interpretation
- Market pricing
- Comparable products
- Structured intake API
- FoxPro integration
- SAP integration
- Report access control
- Duplicate paid-call protection (not yet needed: nothing calls Serper from
  ordinary execution)

Next planned phase:
- PRODUCT-INTEL.3C — MPN matching + rejection
```

Concretely, the repository contains: this document, `CLAUDE.md`, `README.md`, a
minimal Django project with two applications (one of which holds the only
model), the domain contract layer, the evaluation corpus layer, the
run-persistence layer and its two migrations, the standalone web shell, the
deterministic part-number comparison primitive, the search-provider boundary,
the Serper adapter with its recorded fixture and manual smoke script, the
page-fetch boundary and its fetcher, deterministic raw listing extraction and
its five recorded real-page fixtures, deterministic listing normalization, and
over a thousand passing tests, all offline. There is still no research
capability: nothing orchestrates a search, fetches a page, extracts a listing,
normalizes it as part of any automatic flow, resolves a product, or prices
anything — each phase through 3B proved that one more step of the pipeline
works correctly in isolation, and that is the whole of what any of them claim.

**What 3B added.** One module, `product_intelligence/research/normalization.py`,
described in full in §16.2: `NormalizedListingObservation`,
`NormalizationIssue`, `NormalizationIssueCode`, `NormalizedAvailability`,
`NormalizedCondition`, and `normalize_listing_observation`. A raw
`ListingObservation`'s price, currency, availability, condition, and seller
become deterministic values — `Decimal`, an ISO-style currency code, a small
controlled vocabulary — or abstain with a recorded reason when the raw text
cannot be converted without guessing, proven against the same five recorded
3A fixtures plus synthetic tests for the ambiguous and malformed shapes the
phase instructions specified. **It decides no identity and computes no
aggregate**: the published MPN and SKU fields are untouched, `identity.py` is
never imported, and there is no accepted/rejected field, no min/max/median,
and no currency conversion anywhere. Quantity, pack size, and unit price were
not implemented — no recorded fixture publishes raw evidence for any of the
three, and `ListingObservation` was not speculatively extended to invent a
field nothing produces. `runs/` and `web/` are unchanged, and a submitted run
is still `CREATED`.

**What 2C added.** One adapter, `product_intelligence/providers/serper.py`,
described in full in §13.5: `SerperSearchProvider`, calling Serper's ordinary
Google Search endpoint and mapping `organic` results onto the unchanged 2B
contracts. `price_hint_text` and `part_number_hint` stay `None` for every
result — confirmed against a real recorded response, not merely asserted —
because ordinary search publishes neither, and the adapter never calls
`research.identity`. The credential is read from `SERPER_API_KEY` in the
server environment only, sent in Serper's documented header, and never appears
in a log, exception, fixture, or raw reference. One real response was
recorded, sanitized (nothing needed redacting — Serper's JSON does not echo
the credential), and committed to `tests/fixtures/providers/serper/`; the
offline suite exercises the adapter's actual mapping code against it, so
`pytest` still makes zero network calls. Two live calls were made total during
development. **It resolves no product and prices nothing**: `runs/` and
`web/` import no part of `providers`, a submitted run is still `CREATED`, and
Serper being metered has no operational consequence yet because nothing calls
it outside a manual script and tests. The generic 2B boundary required no
change to accommodate the real payload.

**What 2B added.** One module, `product_intelligence/providers/search.py`,
described in full in §13.1: `SearchQuery`, `SearchResult`, `SearchResponse`, the
`SearchProvider` protocol, and one `SearchProviderError`. It is a shape, and
deliberately nothing more — **no provider is integrated**. There is no adapter,
no HTTP call, no credential, no environment variable, no vendor dependency, no
registry or factory, and nothing in the system calls `search()`: a run submitted
through the browser is still `CREATED`, and the report still says research
execution is not connected. A search result carries a price *hint* that stays
text and a part-number *hint* that stays unverified, provider-native material
stays opaque, and result URLs are constrained to absolute `http`/`https`. No
model, no migration, no dependency, and no UI change arrived with it; the 2A
comparator and the evaluation corpus are untouched. 2B also recorded the
operational constraints later phases inherit — source-specific extraction (§16,
3A), currency normalization without conversion (§16, 3B), aggregation
comparability (§16, 4A), paid-call protection as distinct from caching (§18.1),
the access-control blocker for internal pricing (§19), and the recorded-fixture
policy (§13.3).

**What 2A-FU1 corrected.** One defect found in review, before 2A was frozen:
**normalization discarded separator position.** Removing every structural
character wherever it appeared meant `AB-C123`, `ABC-123`, `ABC123`, and
`A-B-C-1-2-3` all keyed to `ABC123` and were reported as the same part number —
a false exact, which is the most expensive answer this system can produce. The
key now preserves structure: an internal whitespace run is *written as* a hyphen
rather than deleted, and `_`, `/`, and `.` are data. The single equivalence the
corpus evidences survives, and the three it does not were withdrawn (§12.3,
AD-037). FU1 changed the normalization, its docstrings, the tests that had
encoded the old behaviour, and this documentation. It added no capability, moved
no corpus expectation, and started no later phase; the roadmap numbering is
unchanged.

**What 2A added.** One pure primitive,
`product_intelligence/research/identity.py`, described in full in §12.1: a
documented conservative normalization profile (as corrected by FU1), a
comparison returning `EXACT`,
`NORMALIZED_EXACT`, or `UNKNOWN`, and an auditable frozen result carrying both
values and both normalized keys. **It resolves no product**: it compares two
part numbers it is handed, and nothing in the system hands it a second one —
there is no search, no candidate source, and no resolver. It reads no
description, holds no catalog, computes no confidence, and does no partial or
fuzzy matching. No model, no migration, no dependency, and no UI change arrived
with it, the web shell and the run lifecycle are untouched, and no corpus
expectation was altered — the corpus was used as test input and it still loads
unchanged.

**What 1B added.** The first browser surface: `GET /research/new` (the form),
`POST /research/new` (creates exactly one run through
`create_from_request` and redirects), `GET /research/<uuid>` (the durable report
shell), and `/` redirecting to the form. The form's only job is translation —
raw strings in, a canonical `ResearchRequest` out, or the contract's own error
shown on the page. **It executes no research**: a submitted run is `CREATED` and
stays there, nothing calls `transition_to`, and the report says research
execution is not connected yet instead of showing progress. No model was added,
no migration was needed, and no search, provider, LLM, launcher, queue, or
authentication arrived with it.

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
| AD-032 | The web layer is a Django application with no model, and its form validates by *constructing* `ResearchRequest` rather than by restating the rules. Both fields are individually optional and keep their submitted text (`strip=False`); no part-number normalization happens at the boundary. | Two policies for what valid intake is would drift, and nothing would fail when they did — a form that grew its own "at least one field" rule, or its own trimming, would silently decide what the canonical contract is supposed to decide. Constructing the contract and translating `DomainValidationError` into a visible error keeps one authority and makes the persisted values identical to what any other intake would produce. `strip=False` matters even though Django's stripping agrees with the contract today: leaving it on would mean the form quietly co-owns a normalization rule, and a later change on either side would be invisible until stored values disagreed. Normalizing a part number here would be worse still — it is a matching decision (2A/3C) taken in the one layer forbidden to make one, where one character can mean a different product. The application holds no model because a run outlives the request that created it and belongs to no caller (AD-025). | Accepted (1B) |
| AD-033 | A GET creates nothing. The browser workflow is Post/Redirect/Get, and the launcher entry point that turns `?mpn=…&description=…` into a run stays in 5B. | The 1B route shape is deliberately the one 5B will adapt, which makes "it would be two lines to honour the parameters now" the obvious mistake to prevent. A GET that creates records is a side effect on a method defined not to have one: a prefetch, a crawler, a bookmark, or a refresh would each start research, and the run table would fill with requests nobody made. Post/Redirect/Get is the other half — without the redirect, the page a user lands on is the submission itself, and reloading a report would silently create duplicates of it. The launcher also needs decisions 1B has not made (URL length limits, truncation policy, encoding), so implementing it early would guess at them. | Accepted (1B) |
| AD-034 | The report shell states that research execution is not connected. No spinner, no polling, no simulated delay, no placeholder price, median, seller table, or example comparable. | A progress indicator over nothing is fabricated certainty with an animation (AD-009): it tells the user work is under way, and the only honest fact is that no execution engine exists. The same reasoning rules out placeholder values — a `$0` or an `N/A median` on a page titled with a real part number is a claim the system has no evidence for, and the evidence-first rule (AD-007) means a number appears only with the listings behind it. A blank "no results exist" section is not a gap in the phase; it is the accurate report, and it is the durable place later phases fill. Displaying an evaluation-corpus case here would be worse again: benchmark truth is reference data, never a result (AD-020). | Accepted (1B) |
| AD-035 | **Amended by AD-037.** Originally: part-number normalization removes one closed, explicitly enumerated formatting allowlist — ASCII whitespace plus `-`, `_`, `/`, `.` — with ASCII-only case folding, everything else being data. | The *exclusions* stand and are the durable half of this entry: "remove every non-alphanumeric character" is rejected because it erases characters that distinguish real products and widens itself every time an unfamiliar character appears; an enumerated set makes each addition an edit someone has to defend; and broad Unicode compatibility folding is excluded because it merges code points whose identity equivalence no phase has approved, which is also why case folding is an explicit ASCII table rather than `str.upper()`. What did not stand was *removal*: deleting the enumerated characters discarded where a boundary was, not merely how it was written. See AD-037. | Amended (2A-FU1) |
| AD-036 | The 2A comparator returns only `EXACT`, `NORMALIZED_EXACT`, or `UNKNOWN`; it carries no confidence, invents no product facts, does no partial or fuzzy matching, and is wired into nothing. | Each exclusion closes a specific way a narrow primitive turns into a false conclusion. `CONFLICT` would be the comparator claiming evidence is incompatible when all it saw was two different strings. `PARTIAL` — or any containment, edit-distance, or similarity rule — would raise recall by weakening identity, which is the one trade this product cannot make: `MTFDKCC3T8TFR` is a family prefix, not an orderable part. A confidence band would equate mechanism with trustworthiness, and `EXACT` is not `HIGH`: the string matched, which says nothing about whether the source, the description, or the listing is sound. A catalog inside the comparator would take benchmark answers from the evaluation corpus and make them production resolution logic, which is test leakage with the corpus's own truth. And wiring it into the web shell or the run lifecycle would connect a comparator to a system that supplies no candidates, so anything displayed would be invented — integration belongs to the phase with real candidate evidence. A guard test asserts `runs`, `web`, and `evaluation` do not import the research core. | Accepted (2A) |
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
