# Product Intelligence

An independent web application that takes a manufacturer part number (MPN)
and a product description, researches observable market pricing, finds
comparable products, preserves the supporting evidence, and presents the
result as a browser-based report.

It is a standalone product. It does not require an ERP, and it is not a
module of one.

## Current status

**Phase PRODUCT-INTEL.0A is complete: architecture and domain contracts.**
Its corrective follow-up **PRODUCT-INTEL.0A-FU1 is complete** as well: it
withdrew an impossible promise that arbitrary unencoded URL parameters would
arrive losslessly, and closed a domain contract that allowed an `EXACT` product
identity carrying no part number.

**Phase PRODUCT-INTEL.0B is complete: the evaluation corpus** — the benchmark
later phases will be measured against, established before there is anything to
measure so that expectations cannot be quietly rewritten to suit an
implementation.

**Phase PRODUCT-INTEL.1A is complete: the research-run lifecycle** — one
durable record per research request, with an opaque identifier, an explicit
state machine, and audit timestamps. Its corrective follow-up
**PRODUCT-INTEL.1A-FU1 is complete** as well: the stored state/timestamp
invariant is now complete rather than partial, a run can only be created in
`CREATED`, and the Django floor moved to the supported LTS line.

**Phase PRODUCT-INTEL.1B is complete: the standalone browser shell** — a form,
a durable report address, and the canonical request between them. **It creates
a research run; it does not execute research.**

**Phase PRODUCT-INTEL.2A is complete: the deterministic part-number
comparison** — given a requested part number and a candidate one, it answers
`EXACT`, `NORMALIZED_EXACT`, or `UNKNOWN`, and shows the normalized keys behind
the answer. **It compares two part numbers it is handed; it does not find
candidates and does not resolve a product.** Its corrective follow-up
**PRODUCT-INTEL.2A-FU1 is complete** as well: normalization was deleting
separators rather than canonicalizing them, which made `AB-C123` and `ABC-123`
the same part number. Separator position is now preserved.

What exists today:

* the canonical architecture and roadmap document
* durable project guidance for Claude Code sessions (`CLAUDE.md`)
* a minimal Django project with two applications and one model
* the domain contract layer: `ResearchRequest`, `ProductIdentity`,
  `EvidenceReference`, and their controlled vocabularies
* the evaluation corpus (`evaluation/`) — 19 cases: 5 real product identities
  with manufacturer provenance and 14 constructed cases covering near-miss part
  numbers, conflicts, partials, accessory confusion, ambiguity, and unknowns —
  with its schema, validation, and loader
* the persisted `ResearchRun` (`product_intelligence/runs/`) and its migrations
* the standalone web shell (`product_intelligence/web/`): the intake form, the
  report shell, and their routes
* the deterministic part-number comparison
  (`product_intelligence/research/identity.py`) and its normalization profile
* deterministic tests for those contracts, for the corpus, for the lifecycle,
  for the browser workflow, for the comparison, and for the architecture
  boundaries

**What does not exist:** market research of any kind. There is no web
search, no candidate discovery, no product lookup, no product resolver, no
description interpretation, no price calculation, no listing extraction, no
comparable-product discovery, no LLM integration, no structured API, and no ERP
integration. None of it is stubbed or partially present — those are later
phases. A run can be created through the browser and moved through its states by
code; nothing yet moves one, because nothing yet does research. The comparison
primitive can say whether two part numbers are the same part number, and nothing
supplies it with a second one. The corpus describes what good answers would look
like; nothing produces or scores an answer.

Next planned phase: **PRODUCT-INTEL.2B — search provider abstraction.**

## The browser workflow

```text
GET  /research/new       the form: manufacturer part number, description
POST /research/new       -> ResearchRequest -> ResearchRun (CREATED) -> redirect
GET  /research/<uuid>    the durable report shell
GET  /                   redirect to /research/new
```

A person with a browser and no integration of any kind can enter a part number,
a description, or both, and get a durable report address back. Either field may
be left blank — but not both, and that rule belongs to `ResearchRequest`: the
form constructs the contract and shows what it says, rather than keeping a
second copy of the policy. Nothing at this boundary normalizes a part number;
case, punctuation, and interior spacing are stored exactly as typed.

**The report shell executes no research and says so.** It shows the identifier,
the state, the part number, the description, and the creation time, states that
research execution is not connected yet, and shows no price, median, seller, or
comparable — real or placeholder. There is no spinner, no polling, and no
simulated progress: a submitted run is `CREATED` and stays there.

Post/Redirect/Get means reloading a report never creates a second run, and a GET
of the form creates nothing at all — the launcher entry point that turns
`?mpn=…&description=…` into a run is phase 5B, deliberately not built here.

Submitted text is untrusted and is rendered through ordinary Django escaping;
CSRF protection is enabled on the form. **The report URL is still not access
control** — whether reports need authentication is undecided — so this shell is
for local development and trusted internal use, not a public deployment.

## The research run

One `ResearchRun` records one canonical `ResearchRequest` — the MPN and
description, exactly as the contract validated them — plus a lifecycle:

```text
CREATED ──> RUNNING ──> COMPLETED
                    ──> PARTIALLY_COMPLETED
                    ──> FAILED
```

Every run begins in `CREATED` — one cannot be created part-way through its own
lifecycle. Terminal states are terminal: there is no retry, reopen, or resume,
and a re-run is a new run. `transition_to()` is the one supported way to move;
an illegal move raises and changes nothing, and assigning the state field on a
saved run is refused rather than silently allowed. `created_at`, `started_at`,
and `finished_at` record the progression, and a run holds no caller data — no
calling application, order number, customer, user, or provider.

Each state pairs with exactly one timestamp arrangement — `CREATED` with
neither, `RUNNING` with a start and no finish, terminal with both — and that
shape is a database check constraint, not just an application rule. The split of
responsibility is deliberate: **the database guarantees a stored row is
structurally self-consistent; the application guarantees an allowed path was
followed.** A check constraint sees one row and not the sequence before it, so
`QuerySet.update()` and raw SQL can still move a run along a route the
transition table forbids — they simply cannot leave an impossible row behind.
That gap is documented rather than chased with triggers or a history table.

The identifier is a random UUID, so a future report URL is durable and not
enumerable. **That is not access control:** it authenticates nobody and
authorizes nothing, and whether reports require authentication is an open
question for a later phase. Transitions are also not atomic across processes —
harmless today, since nothing executes a run, and documented in §15.7 of the
plan rather than papered over. No concurrency mechanism of any kind was
introduced.

## Part-number identity

One deterministic primitive answers one narrow question:

```text
requested part number + candidate part number
        -> EXACT | NORMALIZED_EXACT | UNKNOWN
```

`EXACT` means the two values are character-for-character equal once surrounding
whitespace is removed.

`NORMALIZED_EXACT` means they are **the same identifier written two ways**. The
normalization is deliberately narrow: ASCII `a-z` folds to `A-Z`, each run of
internal ASCII whitespace is written as a hyphen, and **every other character is
kept exactly where it is**.

```text
abc-123          vs  ABC-123          NORMALIZED_EXACT   ABC-123 / ABC-123
ABC 123          vs  ABC-123          NORMALIZED_EXACT   ABC-123 / ABC-123
bcm957504 n425g  vs  BCM957504-N425G  NORMALIZED_EXACT   BCM957504-N425G (both)

ABC123           vs  ABC-123          UNKNOWN            ABC123   / ABC-123
AB-C123          vs  ABC-123          UNKNOWN            AB-C123  / ABC-123
ABC_123          vs  ABC-123          UNKNOWN            ABC_123  / ABC-123
ABC--123         vs  ABC-123          UNKNOWN            ABC--123 / ABC-123
```

**Separator position is part of the identifier.** A normalization that deleted
separators would make `AB-C123`, `ABC-123`, and `ABC123` one key and call them
the same part number — which is what the first implementation did, and why it
was corrected before the phase was frozen. `_`, `/`, and `.` are data too: one
corpus case evidences that whitespace and a hyphen can spell the same boundary,
and that is not evidence that every manufacturer treats every separator as
decoration.

**Everything else is data.** `+`, `#`, `@`, `:`, parentheses, any other
punctuation, and every non-ASCII character inside the identifier are kept, so
`ABC+123` is not `ABC123`. There is no "strip all non-alphanumeric" rule, no
Unicode compatibility folding, no reordering, no truncation, no guessed prefix
or suffix, no `O`/`0` correction, and no fuzzy, edit-distance, or similarity
comparison. A one-character alphanumeric difference stays a difference, which is
the whole point: `MZ-QL23T800` and `MZ-QL23T8OO` are not the same product.

Everything else is `UNKNOWN` — including a truncated part number, a contained
one, and a missing one. `MTFDKCC3T8TFR` does not establish
`MTFDKCC3T8TFR-1BC1ZABYY`: containment is not identity, and partial matching is
deliberately not implemented. A missing part number returns a result rather than
raising, because "identity could not be established" is a legitimate research
outcome. Two values made only of separators can never match each other, since
neither carries any part-number content.

The result is a frozen `PartNumberMatchAssessment` carrying both values as
compared, both normalized keys, and the match type, so a reviewer can re-derive
the decision from the result alone — the keys above are exactly what it exposes.
It carries no confidence score — `EXACT` is not a synonym for `HIGH`, because a
matching string says nothing about whether the source is trustworthy.

**A comparison is not a product resolution.** It says the two strings are the
same part number and nothing more: not that the manufacturer is right, that the
description agrees, or that a listing belongs to the product. If a request's part
number matches while its description names a different product, this primitive
still reports `EXACT` and a later phase reports the conflict. It holds no
catalog — no part number is mapped to a manufacturer or product anywhere in
runtime code — reads no description, and **is wired into nothing**: no search
exists, so nothing supplies a candidate to compare against.

## Requirements

* Django `>=5.2,<6.0` — the current LTS line. The floor is a support
  commitment, not the oldest release whose API happens to compile.
* Python:

```text
supported baseline:            Python 3.12   (pyproject requires-python = ">=3.12")
project .venv currently in use: Python 3.14.7
```

The declared baseline is the contract; the installed interpreter simply has to
satisfy it, and today's does. No version-specific syntax is used, so the code
runs across the supported range. Do not lower `requires-python` to accommodate
an older interpreter — provisioning a supported one is an environment task, not
an architecture change.

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

Confirm the model and its migration are in step — this must report "No changes
detected":

```bash
python manage.py makemigrations --check --dry-run
```

The test suite creates its own in-memory SQLite database, so no local database
setup is required to run it. To create a development database file instead:

```bash
python manage.py migrate
```

Then serve the browser shell locally and open <http://127.0.0.1:8000/research/new>:

```bash
python manage.py runserver
```

That is a development configuration: `DEBUG` defaults on, the `SECRET_KEY`
default is explicitly insecure, and report access control is undecided. Do not
expose it beyond a trusted network.

## Layout

```text
CLAUDE.md                          operating rules for Claude Code sessions
docs/PRODUCT_INTELLIGENCE_PLAN.md  canonical architecture and roadmap
config/                            Django project configuration
evaluation/                        evaluation corpus + its README (implemented)
  corpus/                          real_verified.json, synthetic.json
product_intelligence/
  domain/                          contracts + vocabularies (implemented)
  evaluation/                      corpus validation + loader (implemented)
  runs/                            persisted run lifecycle (implemented)
  research/                        part-number comparison (implemented)
  providers/                       search/LLM boundaries (not implemented)
  web/                             standalone form + report shell (implemented)
tests/                             focused deterministic tests
```

`evaluation/README.md` explains the corpus: its schema, the real-versus-
synthetic rule, the challenge classes, the metric definitions, why no price is
recorded in it, and the discipline governing changes to an expected answer.

The still-empty `providers/` package is not a placeholder for symmetry: it
carries the boundary rules that apply to it as documentation, so the phase that
implements it does so into a defined space rather than inventing one.

## Architecture in one paragraph

Every way of starting research — a web form, a structured API, a legacy
desktop launcher, a future ERP — is only an *intake mechanism*. All of them
normalize into the same `ResearchRequest` of MPN plus description, and the
research core cannot tell which one produced it. Conclusions must trace to
preserved evidence. Deterministic code owns identity matching and all
arithmetic; an LLM may later assist with semantics only. Unknown is a valid
answer and is always preferred to a confident guess — and the evaluation corpus
exists to measure exactly that, since a confidently wrong identity is the most
expensive failure this system can produce.

## Where to read next

`docs/PRODUCT_INTELLIGENCE_PLAN.md` is canonical: mission, scope, non-goals,
architecture, the Visual FoxPro 5 compatibility constraint, provider
boundaries, the phased roadmap, current status, and the decision log. It
labels every item `IMPLEMENTED`, `APPROVED / PLANNED`, `DEFERRED`, or
`UNDECIDED`.
