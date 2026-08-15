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
**PRODUCT-INTEL.0A-FU1**. The repository contains architecture documentation, a
minimal Django skeleton, domain contracts, and their tests.

FU1 corrected two contract-level defects before 0A was frozen: an impossible
guarantee that arbitrary unencoded URL parameters arrive losslessly (see the
legacy client constraint below), and a `ProductIdentity` that could claim an
`EXACT` match with no part number.

**There is no research capability of any kind.** No search, no LLM, no
pricing, no comparables, no persistence, no views.

Next planned phase: **PRODUCT-INTEL.0B — Evaluation corpus.** Do not start it
unless asked.

## Before you implement anything

1. Read `docs/PRODUCT_INTELLIGENCE_PLAN.md`. It is canonical.
2. Confirm which phase you were asked to do.
3. Do only that phase.

## Technology direction

Approved: Python 3.12 · Django · server-rendered HTML · minimal JavaScript ·
relational persistence · pluggable search providers · pluggable LLM
providers.

Approved target runtime is **Python 3.12**; the interpreter available during
initial development was **Python 3.10.1**. The code avoids version-specific
syntax so it runs on both. Do not lower the approved baseline to match a local
machine — that gap is an environment task.

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
Django, no I/O). `research/` holds the core engine. `providers/` holds vendor
adapters. `web/` holds Django intake and presentation, and is the only layer
allowed to know about transports and callers.

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

## Approved roadmap (abbreviated)

```text
0A Architecture + domain contracts            <- complete
   0A-FU1 contract correctness cleanup        <- complete
0B Evaluation corpus                          <- next
1A ResearchRun lifecycle
1B Standalone web research/report shell
2A Deterministic product identity model
2B Search provider abstraction
2C First real search provider
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
  non-stdlib import, a calling-system concept, or a vendor name. If a guard
  fails, fix the design, not the test.

## Commands

```bash
python -m pytest
```

```bash
python manage.py check
```
