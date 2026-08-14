# Product Intelligence

An independent web application that takes a manufacturer part number (MPN)
and a product description, researches observable market pricing, finds
comparable products, preserves the supporting evidence, and presents the
result as a browser-based report.

It is a standalone product. It does not require an ERP, and it is not a
module of one.

## Current status

**Phase PRODUCT-INTEL.0A is complete: architecture and domain contracts.**

What exists today:

* the canonical architecture and roadmap document
* durable project guidance for Claude Code sessions (`CLAUDE.md`)
* a minimal Django project skeleton — no apps, no models, no migrations, no
  views, no routes
* the domain contract layer: `ResearchRequest`, `ProductIdentity`,
  `EvidenceReference`, and their controlled vocabularies
* deterministic tests for those contracts and for the architecture boundaries

**What does not exist:** market research of any kind. There is no web
search, no product lookup, no price calculation, no listing extraction, no
comparable-product discovery, no LLM integration, no persistence, no user
interface, and no ERP integration. None of it is stubbed or partially
present — those are later phases.

Next planned phase: **PRODUCT-INTEL.0B — Evaluation corpus.**

## Requirements

* Python 3.12 (the approved target)
* Django 5.x

Note: the code is written to run on Python 3.10 as well, because that is the
interpreter currently installed on the development machine. No 3.12-only
syntax is used. `pyproject.toml` declares `requires-python = ">=3.12"` to
record the approved target, so installing the project as a package on 3.10
will be refused — running the tests directly, as below, works on either.

## Setup

```bash
python -m venv .venv
```

Activate it — PowerShell:

```bash
.venv\Scripts\Activate.ps1
```

Or bash / Git Bash:

```bash
source .venv/Scripts/activate
```

Then install dependencies:

```bash
pip install -r requirements.txt
```

## Running the checks

The test suite (deterministic, no network, no credentials required):

```bash
python -m pytest
```

Django system check:

```bash
python manage.py check
```

There is nothing useful to serve yet — the project has no routes — so
`runserver` is not part of the workflow at this phase.

## Layout

```text
CLAUDE.md                          operating rules for Claude Code sessions
docs/PRODUCT_INTELLIGENCE_PLAN.md  canonical architecture and roadmap
config/                            Django project configuration
product_intelligence/
  domain/                          contracts + vocabularies (implemented)
  research/                        research core (not implemented)
  providers/                       search/LLM boundaries (not implemented)
  web/                             intake + presentation (not implemented)
tests/                             focused deterministic tests
```

The empty packages under `product_intelligence/` are not placeholders for
symmetry: each carries the boundary rules that apply to it as documentation,
so a later phase implements into a defined space rather than inventing one.

## Architecture in one paragraph

Every way of starting research — a web form, a structured API, a legacy
desktop launcher, a future ERP — is only an *intake mechanism*. All of them
normalize into the same `ResearchRequest` of MPN plus description, and the
research core cannot tell which one produced it. Conclusions must trace to
preserved evidence. Deterministic code owns identity matching and all
arithmetic; an LLM may later assist with semantics only. Unknown is a valid
answer and is always preferred to a confident guess.

## Where to read next

`docs/PRODUCT_INTELLIGENCE_PLAN.md` is canonical: mission, scope, non-goals,
architecture, the Visual FoxPro 5 compatibility constraint, provider
boundaries, the phased roadmap, current status, and the decision log. It
labels every item `IMPLEMENTED`, `APPROVED / PLANNED`, `DEFERRED`, or
`UNDECIDED`.
