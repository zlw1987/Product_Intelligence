# CLAUDE.md — Product Intelligence

Operating instructions for any AI coding session in this repository.
Assume no chat history.

## Reading order

1. Read this file completely.
2. Read `docs/PRODUCT_INTELLIGENCE_STATUS.md` completely — it carries the
   current completed phase, next planned phase, and implementation snapshot.
3. Read the relevant canonical sections of
   `docs/PRODUCT_INTELLIGENCE_PLAN.md` before implementing anything. That
   document is the authoritative source for architecture decisions, phase
   specifications, the decision log, and historical rationale.
4. Inspect the actual repository and tests.

**If any of these sources — the repository, tests, STATUS, CLAUDE, or PLAN —
materially disagree about architecture, phase state, or capability, STOP and
report the conflict before changing anything. Do not silently resolve it.**

## Document ownership

| Document | Role | Update frequency |
| --- | --- | --- |
| `CLAUDE.md` (this file) | Durable AI operating contract. Cross-phase rules, boundaries, safety constraints. | Rarely. Only when a durable operating rule, architectural invariant, workflow rule, or safety constraint changes. |
| `docs/PRODUCT_INTELLIGENCE_STATUS.md` | Volatile current-state: completed phase, next phase, implementation snapshot, what is not yet connected, validation baseline. | Every phase completion. |
| `docs/PRODUCT_INTELLIGENCE_PLAN.md` | Canonical long-form architecture, phase specifications, roadmap, decision log, historical rationale. | When roadmap status, architecture, durable decisions, or canonical phase specifications change. |
| `README.md` | Human/developer orientation: setup, commands, concise overview, links. | When developer-facing setup or capability information materially changes. |

**Do NOT update CLAUDE.md merely because a phase completed.** Ordinary phase
completion updates STATUS.md.

## What this project is

Product Intelligence is an **independent web application**. Given a
manufacturer part number (MPN) and a product description, it researches
observable market pricing, finds comparable products, preserves the evidence
behind both, and presents a browser-based report.

It is **not** an ERP module and does not require one to function.

## Technology direction

Approved: Python 3.12 · Django · server-rendered HTML · minimal JavaScript ·
relational persistence · pluggable search providers · pluggable LLM providers.

The supported baseline is **Python 3.12** (`pyproject.toml` declares
`requires-python = ">=3.12"`). Do not lower the declared baseline to match
whatever interpreter happens to be installed.

Django is pinned to **`>=5.2,<6.0`** — the current LTS line. A dependency floor
is a support commitment, not a note about which release first shipped an API.
Moving above 6.0 is its own decision.

Do **not** introduce, merely because this is an AI project: React, Next.js, a
separate SPA frontend, LangChain, agent frameworks, Celery, Redis, vector
databases, Kubernetes, message brokers, multi-model orchestration, or
multiple search providers. Each requires a phase that demonstrates a concrete
need.

## Architecture rules (binding)

### Caller-independent core

Every intake mechanism — standalone web form, structured API, legacy desktop
launcher, future ERP, batch — normalizes into the same `ResearchRequest`
(MPN + description). No business logic may branch on which client called.
Caller metadata belongs at the intake boundary, never in product identity.

### Layer boundaries

- `domain/` — contracts and vocabularies (stdlib only, no Django, no I/O).
- `research/` — core engine, stays free of persistence.
- `runs/` — persisted research-run lifecycle, the **only** package with a
  Django model.
- `providers/` — vendor adapters.
- `web/` — Django intake and presentation, the only layer allowed to know
  about transports and callers.

Dependency direction: outer layers import inner ones, never the reverse.
Architecture guard tests enforce this.

### Frozen-phase semantics

**Frozen implemented-phase semantics must not be changed unless the user's
task explicitly requires changing that contract.** The canonical plan
(`docs/PRODUCT_INTELLIGENCE_PLAN.md`, sections below) records the binding
rules for each implemented phase:

| Phase | Canonical plan section |
| --- | --- |
| 0A domain contracts | §10 |
| 0B evaluation corpus | §21 (full rules in `evaluation/README.md`) |
| 1A/1A-FU1 run persistence | §15 |
| 1B web shell | §8.1 |
| 2A/2A-FU1 part-number identity | §12.1 |
| 2B search-provider boundary | §13.1 |
| 2C Serper adapter | §13.5 |
| 3A page fetch + extraction | §13.6, §16.1 |
| 3B listing normalization | §16.2 |
| 3C MPN matching + rejection | §16.3 |
| 4A price aggregation | §16.4 |

Do not violate these rules. If a phase seems to require something that
contradicts a frozen contract, say so and ask — do not just change it.

## Evidence-first behavior

Every reported price or product fact traces to preserved evidence: source, URL,
retrieval time, raw reference, normalized value, accept/reject decision, reason,
confidence. Rejected evidence is kept with its reason. Never present a precise
conclusion without traceable listings.

## Unknown beats fabricated certainty

`UNKNOWN`, `UNVERIFIED`, `AMBIGUOUS`, and `CONFLICT` are correct answers.
Never silently convert uncertainty into a confident match. A fabricated match
that looks authoritative causes worse decisions than an explicit "unknown".

## Exact identity safety

One character can mean a different product. Distinguish `EXACT`,
`NORMALIZED_EXACT`, `PARTIAL`, `DESCRIPTION_ONLY`, `CONFLICT`, `UNKNOWN`.
Semantic similarity is not identity. An identity may not claim a match it
holds no evidence for: `EXACT` requires a part number and `NORMALIZED_EXACT`
requires the normalized form too, enforced at construction in
`domain/models.py`.

## Deterministic code owns identity and arithmetic

Application code owns and stays solely authoritative for: exact and normalized
MPN matching, all arithmetic, price aggregation, median/min/max, unit price,
currency, deduplication, thresholds, validation, timestamps, persistence.

## LLM is never sole authority for exact identity

An LLM may later assist only with semantics: ambiguous descriptions, category
classification, specification extraction, query generation, explaining
differences, summarizing verified results. **An LLM is never the sole
authority for exact product identity**, and never produces a number that the
report presents as fact.

## Evaluation truth does not move to suit an implementation

The corpus in `evaluation/` is the benchmark later phases are measured against.
Changing an expected answer requires stating which of these it is: (A) the old
expectation was factually wrong, (B) the authoritative source changed, (C) the
case definition was ambiguous, or (D) the product behaviour requirement
intentionally changed.

**"The new implementation failed this case" is not a valid reason** — that is
the benchmark working. Full rules in `evaluation/README.md`.

## Provider abstraction

External vendors sit behind `SearchProvider` and `LLMProvider`. No vendor name
(Tavily, SerpAPI, Google, Bing, OpenAI, Anthropic, ...) may appear in domain
models or business logic. Vendor names belong only in adapter modules.

## No secrets in clients

API keys, LLM keys, and credentials live in the server environment only —
never in the repository, never in a URL, never in FoxPro or SAP. Launchers are
URL builders, not AI clients.

## Legacy client: Visual FoxPro 5.0

The production sales-order system is Microsoft Visual FoxPro 5.0. Assume it has
*no* usable REST client, JSON, OAuth, modern TLS, modern HTTP library, Unicode
sophistication, or browser integration. Its only role is to build a URL and open
the default browser. GET alone must be enough — no POST body, no custom headers,
no cookies, no response parsing, and no credentials in the client.

What FoxPro must be able to do is exactly: **string construction + a minimal
percent-encoding helper we write + browser launch.**

**Do not promise lossless transport of arbitrary unencoded text.** A URL query
string is not a transparent channel. Raw unencoded values are accepted
**best-effort, for URL-safe characters only** — never as a guarantee.

See canonical plan §7 for the full constraint.

## Standalone web UI is first-class

A person with a browser and no integration at all must be able to enter an MPN
and description and get a report. Never make the standalone path depend on an
integration.

## Future SAP compatibility

SAP will replace FoxPro as a launcher via one adapter at the intake boundary.
If a change would force the research core to be rewritten when that happens,
the change is wrong.

See canonical plan §9.

## Working rules

* **Do not silently expand phase scope.** If a phase seems to require something
  from a later phase, say so and ask — do not just build it.
* **Do not describe planned work as implemented.** In code, docs, or reports.
* **Do not commit or push unless explicitly asked.** Also do not deploy or
  configure external infrastructure.
* **Keep the architecture guard tests passing.** They enforce layer boundaries,
  stdlib-only domain contracts, no vendor names in business logic, no Django in
  the core, single-model persistence, and no crawler/browser dependency. If a
  guard fails, fix the design, not the test.
* **A corrective follow-up phase has a higher bar from 2B onward.** Reserve a
  standalone FU for a defect that materially threatens false confidence or a
  false exact, data integrity, security, provider cost, or a hard architectural
  boundary. Fold minor cleanup into the next phase, record as known debt, or
  defer. (§22.1 of the plan).

## Commands

```bash
python -m pytest
```

```bash
python manage.py check
```

Confirm every model change has a migration (must report "No changes detected"):

```bash
python manage.py makemigrations --check --dry-run
```

Manual live page fetch plus extraction (developer-only, never part of `pytest`):

```bash
python scripts/page_extract_smoke.py https://example.com/some-product
```

Local development server:

```bash
python manage.py migrate
python manage.py runserver
```
