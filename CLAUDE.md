# CLAUDE.md — Product Intelligence

Operating instructions for any Claude Code session in this repository. Assume
no chat history. This file plus `docs/PRODUCT_INTELLIGENCE_PLAN.md` is the
whole context.

## What this project is

Product Intelligence is an **independent web application**. Given a
manufacturer part number (MPN) and a product description, it researches
observable market pricing, finds comparable products, preserves the evidence
behind both, and presents a browser-based report.

It is not an ERP module and does not require one to function.

## Current phase

**PRODUCT-INTEL.0A is complete**, together with its corrective follow-up
**PRODUCT-INTEL.0A-FU1**; **PRODUCT-INTEL.0B is complete**;
**PRODUCT-INTEL.1A is complete**, together with its corrective follow-up
**PRODUCT-INTEL.1A-FU1**; **PRODUCT-INTEL.1B is complete**;
**PRODUCT-INTEL.2A is complete**, together with its corrective follow-up
**PRODUCT-INTEL.2A-FU1**; and **PRODUCT-INTEL.2B is complete**. The repository
contains architecture documentation, a minimal Django project, domain contracts,
the evaluation corpus and its loader, the persistent research-run lifecycle and
its migrations, the standalone browser shell, the deterministic part-number
comparison, the search-provider boundary, and their tests.

FU1 corrected two contract-level defects before 0A was frozen: an impossible
guarantee that arbitrary unencoded URL parameters arrive losslessly (see the
legacy client constraint below), and a `ProductIdentity` that could claim an
`EXACT` match with no part number.

0B added the evaluation corpus — benchmark data, contracts, validation, and a
loader. It added no research capability and evaluates nothing, because there is
nothing yet to evaluate.

1A added one persisted record, `ResearchRun` (see the persistence section
below). It stores *that* research was requested and how the attempt ended.

1A-FU1 closed two gaps before 1A was frozen: the stored state/timestamp
invariant was incomplete, so ordinary ORM calls could persist ten kinds of
impossible row (a `COMPLETED` run that never started, a `RUNNING` run with no
start time, a run created straight into a terminal state); and the Django floor
allowed an unsupported release. Both are corrected below.

1B added the first browser surface: a form at `/research/new`, a durable report
shell at `/research/<uuid>`, and the `ResearchRequest` translation between them
(see the web-shell section below). **It creates a `ResearchRun` and executes no
research.**

2A added one pure primitive: the deterministic part-number comparison in
`product_intelligence/research/identity.py` (see the identity section below).
**It compares two part numbers it is handed and resolves no product** — nothing
in the system supplies the second one.

2A-FU1 corrected one defect before 2A was frozen: normalization deleted every
approved separator wherever it appeared, so `AB-C123`, `ABC-123`, `ABC123`, and
`A-B-C-1-2-3` all collapsed onto the key `ABC123` and were reported as the same
part number. Separator *position* is now preserved — an internal whitespace run
is written as a hyphen rather than removed — and `_`, `/`, and `.` became data
rather than interchangeable formatting.

2B added the search-provider boundary in `product_intelligence/providers/`
(see the provider section below): three contracts, one protocol, one exception.
**No provider is integrated** — no adapter, no HTTP call, no credential, no
vendor dependency, and nothing calls `search()`.

**There is still no research capability.** No search, no candidate discovery, no
LLM, no pricing, no comparables, no resolver, and no background processing —
nothing moves a run out of `CREATED`, and the report page says exactly that
instead of showing progress.

Next planned phase: **PRODUCT-INTEL.2C — first real search provider.** Do not
start it unless asked. It is the priority after 2B: the remaining risk is no
longer architectural, and nothing here has yet met a real market page.

## Before you implement anything

1. Read `docs/PRODUCT_INTELLIGENCE_PLAN.md`. It is canonical.
2. Confirm which phase you were asked to do.
3. Do only that phase.

## Technology direction

Approved: Python 3.12 · Django · server-rendered HTML · minimal JavaScript ·
relational persistence · pluggable search providers · pluggable LLM
providers.

The supported baseline is **Python 3.12** (`pyproject.toml` declares
`requires-python = ">=3.12"`). The project virtual environment currently in use
is **Python 3.14.7**, which satisfies that baseline. The code avoids
version-specific syntax, so it runs across the supported range. Do not lower the
declared baseline to match whatever interpreter happens to be installed.

Django is pinned to **`>=5.2,<6.0`** — the current LTS line. A dependency floor
is a support commitment, not a note about which release first shipped an API
being used: do not lower it to the oldest version that merely compiles. Moving
above the 6.0 bound is its own decision, not a side effect of another change.

Do **not** introduce, merely because this is an AI project: React, Next.js, a
separate SPA frontend, LangChain, agent frameworks, Celery, Redis, vector
databases, Kubernetes, message brokers, multi-model orchestration, or
multiple search providers. Each requires a phase that demonstrates a concrete
need.

## Architecture rules (binding)

**Caller-independent core.** Every intake mechanism — standalone web form,
structured API, legacy desktop launcher, future ERP, batch — normalizes into
the same `ResearchRequest` (MPN + description). No business logic may branch
on which client called. Caller metadata belongs at the intake boundary, never
in product identity.

**Layers.** `domain/` holds contracts and vocabularies (stdlib only, no
Django, no I/O). `research/` holds the core engine and stays free of
persistence. `runs/` holds the persisted research-run lifecycle and is the only
package with a Django model. `providers/` holds vendor adapters. `web/` holds
Django intake and presentation, and is the only layer allowed to know about
transports and callers.

**Run persistence (1A).** `product_intelligence/runs/` owns `ResearchRun`: a
UUID primary key, the canonical MPN and description from a `ResearchRequest`,
a `state` generated from the existing `ResearchRunState` vocabulary, and
`created_at` / `started_at` / `finished_at`. Binding rules:

* **No caller or provider columns**, ever — no calling application, order
  number, customer, user, transport metadata, search provider, or model
  provider. A guard test asserts the exact field list.
* **Create through `ResearchRun.objects.create_from_request(request)`.** The
  `ResearchRequest` contract is the single authority on valid input; do not
  restate its rules here.
* **A run is always created in `CREATED`.** Persisting one directly in
  `RUNNING` or a terminal state raises `InvalidInitialResearchRunState`, and an
  unsaved run cannot transition.
* **Transition through `run.transition_to(state, at=...)`.** Allowed:
  `CREATED → RUNNING`, and `RUNNING →` `COMPLETED` / `PARTIALLY_COMPLETED` /
  `FAILED`. Terminal is terminal — no retry, reopen, or resume. An illegal move
  raises `InvalidResearchRunTransition` and changes nothing; assigning `state`
  and saving raises `UnsupportedResearchRunStateChange`.
* **Every stored row satisfies one state/timestamp shape**, enforced by the
  check constraint `research_run_state_matches_timestamps`: `CREATED` with
  neither timestamp, `RUNNING` with a start and no finish, terminal with both.
  Keep it a single constraint — do not add overlapping partial rules, triggers,
  or a history table.
* **The database judges the row; the application judges the path.** A check
  constraint sees one row, never the sequence before it, so `QuerySet.update()`
  and raw SQL can still skip the transition path. That residue is accepted and
  documented (§15.6 of the plan); do not build machinery to close every ORM
  bypass.
* **The UUID is not access control.** It resists enumeration and does nothing
  else. Report authentication and visibility remain undecided.
* **Transitions are not atomic across processes** (§15.7 of the plan). Do not
  add locking or queues to fix it before a phase introduces a real second
  writer. No concurrency mechanism exists.

**Web shell (1B).** `product_intelligence/web/` is a Django application holding
the form, the two views, the routes, and the templates. Binding rules:

* **It owns no model, and never will.** Persistence stays in `runs/` (AD-025);
  a guard test asserts `runs.ResearchRun` is still the only model and that no
  inner layer imports `web`.
* **`ResearchRequest` remains the single validation authority.** The form's two
  fields are individually optional and set `strip=False`; the "at least one of
  them" rule and all whitespace handling come from *constructing the contract*
  and reporting what it says. Do not restate those rules in a form.
* **No part-number normalization at the boundary** — not case, punctuation,
  hyphens, or interior whitespace. That is 2A/3C work.
* **Post/Redirect/Get.** A successful POST calls
  `ResearchRun.objects.create_from_request(...)` exactly once and redirects to
  `/research/<uuid>`. Never `objects.create(state=…)`, `bulk_create()`,
  `QuerySet.update()`, or raw SQL.
* **A GET creates nothing**, whatever query parameters it carries. The launcher
  entry point that turns `?mpn=…&description=…` into a run is 5B; a GET that
  created records would let a prefetch or a refresh start research.
* **The shell tells the truth.** A new run is `CREATED` and stays there — this
  layer never transitions a run. The page says research execution is not
  connected yet. No spinner, no polling, no fake progress, no placeholder
  price, median, seller, or comparable.
* **CSRF protection stays on**; the report page is escaped ordinary Django
  output, and no user value is ever marked safe.
* **The UUID in the URL is not authorization.** Report access control is still
  undecided, so this shell is for local development and trusted internal use
  only — not public deployment.

**Part-number identity (2A, corrected in 2A-FU1).**
`product_intelligence/research/identity.py` owns the deterministic comparison:
`normalize_part_number`, `compare_part_numbers`, `compare_request_to_candidate`,
and the frozen `PartNumberMatchAssessment`. Binding rules:

* **It is a pure function of two strings.** No I/O, no Django, no provider, no
  model call, and no import of `product_intelligence.evaluation`. The corpus is
  test input only.
* **Normalization canonicalizes how a boundary was written, never whether one
  exists.** Surrounding whitespace is removed (`str.strip()`, as
  `ResearchRequest` does); ASCII `a-z` folds to `A-Z`; each run of internal ASCII
  whitespace becomes one hyphen; **every other character is kept, in place**. So
  `abc 123` and `ABC-123` both key to `ABC-123`, and `ABC123` keys to `ABC123`
  and matches neither.
* **No separator is ever deleted.** 2A deleted them and thereby made `AB-C123`,
  `ABC-123`, and `ABC123` one key — a false exact (AD-037). Never restore
  separator deletion.
* **`_`, `/`, and `.` are data**, not spellings of a hyphen: `ABC_123` does not
  match `ABC-123`. The corpus evidences one substitution (whitespace against a
  hyphen, SYN-0008) and that is the only one approved. Adding another needs its
  own evidence, per separator.
* **Repeated and padded punctuation does not collapse.** `ABC--123` and
  `ABC - 123` keep every boundary written; only a *whitespace run* collapses.
* **Everything else is data** — `+`, `#`, `@`, `:`, parentheses, other
  punctuation, and every non-ASCII code point *inside* the identifier. Never
  "strip all non-alphanumeric", never NFKC or another broad compatibility
  transform, never `str.upper()`. A test asserts the exact character sets.
* **Nothing is reordered, truncated, guessed, or corrected.** No edit distance,
  similarity, embedding, or `O`/`0`-style confusion table. A one-character
  alphanumeric difference stays a difference.
* **Three outcomes only**: `EXACT` (character-for-character after boundary
  whitespace), `NORMALIZED_EXACT` (equal normalized keys, meaning the same
  identifier structure written differently), `UNKNOWN`. Both sides must carry
  part-number content — a value that is only structure keys to `""`, and two
  empty keys never match. Missing input returns `UNKNOWN` rather than raising;
  only a wrong argument *type* raises.
* **Never `CONFLICT` and never `PARTIAL`.** Two different strings do not
  establish incompatible evidence, and containment is not identity. Partial
  classification is 3C.
* **No confidence, no catalog, no product facts.** `EXACT` is not `HIGH`, and no
  part number is mapped to a manufacturer, product, family, or category
  anywhere in runtime code — those mappings are benchmark truth and using them
  would be test leakage.
* **A comparison is not a resolution.** A matching part number says nothing
  about the manufacturer, the description, the listing, or the source. When the
  description disagrees, the comparator still reports what it compared; the
  cross-evidence conclusion belongs to a later phase.
* **Nothing is wired to it.** `runs/`, `web/`, and `evaluation/` do not import
  the research core, and a guard test enforces that. Integration waits for a
  phase with a real candidate source.

**Search-provider boundary (2B).** `product_intelligence/providers/search.py`
owns `SearchQuery`, `SearchResult`, `SearchResponse`, the `SearchProvider`
protocol, and `SearchProviderError`. Binding rules:

* **The generic boundary is stdlib-only contracts.** No vendor package, no
  credential, no environment reading, no HTTP client, no Django, no model, no
  persistence. A vendor name may appear in an adapter (2C), never here — a guard
  test scopes the vendor scan to `providers/__init__.py` and `providers/search.py`.
* **`SearchQuery` is one external search operation, not a `ResearchRequest`.**
  It has one field, `text`, stripped and non-empty. Query generation — turning
  one request into one or more queries — is research-core work and does not
  exist. Do not add category, locale, result limit, search mode, pagination, or
  shopping flags without a phase that needs them.
* **`price_hint_text` is text, never a price.** No `Decimal`, no currency, no
  arithmetic, no choosing between sale price, shipping, and monthly payment.
  **Never add a numeric price field** — a test asserts the exact field list.
  Extraction is 3A, normalization 3B, aggregation 4A.
* **`part_number_hint` is unverified**, and only for a part number a provider
  *explicitly publishes*. It is stored exactly as published: not normalized, not
  compared, not a match. A part number inferred from a title, snippet, or URL is
  extraction (3A/3C), not this field.
* **A provider observes; it never decides.** No identity comparison, no price
  parsing, no acceptance, no "verified results". The provider layer does not
  import `research`, `runs`, `web`, or `evaluation`, and a guard test enforces it.
* **Provider-native payload stays opaque.** `raw_reference` and
  `raw_response_reference` are strings kept verbatim, never parsed, never a
  `dict` for business logic to read a vendor key out of.
* **`source_url` must be an absolute `http`/`https` URL with a host.**
  `javascript:`, `data:`, `file:`, other schemes, and relative values are
  rejected. That is the whole rule — do not grow a URL-security subsystem.
* **`retrieved_at` is timezone-aware and supplied by the adapter.** Contracts
  never generate time. **Zero results is a valid response**, not an error.
* **One exception, one method, synchronous.** No registry, factory, plugin
  discovery, DI container, manager, fallback chain, fan-out, retries, rate-limit
  scheduler, circuit breaker, async variant, or error taxonomy. One provider
  arrives in 2C; design for replaceability, not simultaneity.
* **Nothing is wired to it.** No inner layer imports `providers`, and a guard
  test enforces that. Tests use synthetic fakes only — **sanitized recorded
  fixtures of real responses begin in 2C**, and inventing one now would produce
  a fixture that passes whatever the real provider does.

**Legacy client constraint.** The production sales-order system is Microsoft
Visual FoxPro 5.0. Assume it has *no* usable REST client, JSON, OAuth, modern
TLS, modern HTTP library, Unicode sophistication, or browser integration. Its
only role is to build a URL and open the default browser. GET alone must be
enough — no POST body, no custom headers, no cookies, no response parsing, and
no credentials in the client.

What FoxPro must be able to do is exactly: **string construction + a minimal
percent-encoding helper we write + browser launch.**

```text
/research/new?mpn=<percent-encoded>&description=<percent-encoded>
```

**Do not promise lossless transport of arbitrary unencoded text.** A URL query
string is not a transparent channel: `&` starts another parameter, `#` starts a
fragment a browser normally never sends, and `%`, `+`, `?` and `=` are
similarly reserved. Bytes reinterpreted or dropped before the request reaches
Django cannot be recovered by any amount of server-side parsing. Raw
unencoded values are accepted **best-effort, for URL-safe characters only** —
never as a guarantee. The encoding helper is what makes the legacy path
reliable, and it belongs to phase 5B; do not write it now.

**Standalone web UI is first-class.** A person with a browser and no
integration at all must be able to enter an MPN and description and get a
report. Never make the standalone path depend on an integration.

**Future SAP compatibility.** SAP will replace FoxPro as a launcher via one
adapter at the intake boundary. If a change would force the research core to
be rewritten when that happens, the change is wrong.

**Evidence-first.** Every reported price or product fact traces to preserved
evidence: source, URL, retrieval time, raw reference, normalized value,
accept/reject decision, reason, confidence. Rejected evidence is kept with
its reason. Never present a precise conclusion without traceable listings.

**Deterministic before LLM.** Application code owns and stays solely
authoritative for: exact and normalized MPN matching, all arithmetic, price
aggregation, median/min/max, unit price, currency, deduplication, thresholds,
validation, timestamps, persistence. An LLM may later assist only with
semantics: ambiguous descriptions, category classification, specification
extraction, query generation, explaining differences, summarizing verified
results. **An LLM is never the sole authority for exact product identity.**

**Unknown beats fabricated certainty.** `UNKNOWN`, `UNVERIFIED`, `AMBIGUOUS`,
and `CONFLICT` are correct answers. Never silently convert uncertainty into a
confident match.

**Exact identity matters.** One character can mean a different product.
Distinguish `EXACT`, `NORMALIZED_EXACT`, `PARTIAL`, `DESCRIPTION_ONLY`,
`CONFLICT`, `UNKNOWN`. Semantic similarity is not identity. An identity may
not claim a match it holds no evidence for: `EXACT` requires a part number and
`NORMALIZED_EXACT` requires the normalized form too, enforced at construction
in `domain/models.py`.

**Provider abstraction.** External vendors sit behind `SearchProvider` and
`LLMProvider`. No vendor name (Tavily, SerpAPI, Google, Bing, OpenAI,
Anthropic, …) may appear in domain models or business logic.

**No secrets in clients.** API keys, LLM keys, and credentials live in the
server environment only — never in the repository, never in a URL, never in
FoxPro or SAP. Launchers are URL builders, not AI clients.

**Evaluation truth does not move to suit an implementation.** The corpus in
`evaluation/` is the benchmark later phases are measured against. Changing an
expected answer requires stating which of these it is: (A) the old expectation
was factually wrong, (B) the authoritative source changed, (C) the case
definition was ambiguous, or (D) the product behaviour requirement intentionally
changed. **"The new implementation failed this case" is not a valid reason** —
that is the benchmark working. Adding cases is ordinary work; a new
`REAL_VERIFIED` case needs provenance as strong as the existing seeds. Corpus
data is reference material, never runtime state: it is not persisted, not a
Django model, and never part of a research run. Full rules in
`evaluation/README.md`.

## Approved roadmap (abbreviated)

```text
0A Architecture + domain contracts            <- complete
   0A-FU1 contract correctness cleanup        <- complete
0B Evaluation corpus                          <- complete
1A ResearchRun lifecycle                      <- complete
   1A-FU1 persistence invariant hardening     <- complete
1B Standalone web research/report shell       <- complete
2A Deterministic product identity model       <- complete
   2A-FU1 structure-preserving normalization  <- complete
2B Search provider abstraction                <- complete
2C First real search provider                 <- next
3A Market listing extraction
3B Listing normalization
3C MPN matching + rejection
4A Price aggregation
4B Price Intelligence web report      ----- PRICE MVP -----
5A Structured external intake API
5B Visual FoxPro 5 launcher integration  ----- FOXPRO MVP -----
6A Product specification framework
6B First category-specific schema
7A Comparable-product candidate discovery
7B Similarity scoring
7C Comparison web report              ----- COMPARABLE MVP -----
8A Caching / refresh strategy
8B Research history
8C Production hardening

Future: SAP launcher, additional clients, additional category schemas,
additional search and LLM providers.
```

## Working rules

* **Do not silently expand phase scope.** If a phase seems to require
  something from a later phase, say so and ask — do not just build it.
* **Do not describe planned work as implemented.** In code, docs, or reports.
* **Update status documentation after completing an approved phase**: the
  CURRENT STATUS section and the decision log in
  `docs/PRODUCT_INTELLIGENCE_PLAN.md`, plus the phase markers here and in
  `README.md`.
* **Do not commit or push unless explicitly asked.** Also do not deploy or
  configure external infrastructure.
* **Keep the architecture guard tests passing.**
  `tests/domain/test_domain_boundaries.py` fails if the domain gains a
  non-stdlib import, a calling-system concept, or a vendor name.
  `tests/evaluation/test_evaluation_boundaries.py` fails if the evaluation
  layer gains a framework import, a provider import, a vendor name, or a
  network call. `tests/runs/test_research_run_boundaries.py` fails if a run
  gains a caller-shaped or provider-shaped column, if the domain or research
  core gains a Django import, or if a second model appears.
  `tests/web/test_web_boundaries.py` fails if an inner layer imports the web
  layer, if the web layer gains a model, a vendor name, a provider import, a
  network client, or a call to `transition_to`.
  `tests/research/test_research_identity_boundaries.py` fails if the research
  core gains a non-stdlib import, a persistence/provider/benchmark/web import, a
  network or filesystem module, or a vendor name; if the domain imports the
  research core; or if `runs`, `web`, or `evaluation` wires itself to the
  identity primitive.
  `tests/providers/test_provider_boundaries.py` fails if the generic search
  boundary gains a non-stdlib import, a vendor name, a calling-system concept, a
  network or configuration module, a model, or a third-party dependency; if the
  provider layer imports persistence, the research core, the web layer, or the
  benchmark; or if any inner layer wires itself to the boundary while no
  provider exists. If a guard fails, fix the design, not the test.
* **A corrective follow-up phase has a higher bar from 2B onward.** Reserve a
  standalone FU for a defect that materially threatens false confidence or a
  false exact, data integrity, security, provider cost, or a hard architectural
  boundary. Fold minor cleanup, wording, speculative future-proofing, and
  theoretical edge cases into the next phase, record them as known debt, or
  defer them until real provider evidence shows they matter. This is not a
  severity framework — it exists because architecture latency now costs more
  than a small imperfection carried for one phase (§22.1 of the plan).

## Commands

```bash
python -m pytest
```

```bash
python manage.py check
```

Confirms every model change has a migration (it must report "No changes
detected"):

```bash
python manage.py makemigrations --check --dry-run
```

The browser shell, for local development only (`/research/new` is the form):

```bash
python manage.py migrate
```

```bash
python manage.py runserver
```
