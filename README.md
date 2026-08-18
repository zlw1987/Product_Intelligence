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

**Phase PRODUCT-INTEL.2B is complete: the search-provider boundary** — the
provider-neutral shape the research core will depend on instead of a vendor.
**It defines contracts and integrates no provider:** there is no adapter, no
HTTP call, no credential, no vendor dependency, and nothing in the system calls
it.

**Phase PRODUCT-INTEL.2C is complete: the first real search provider,
Serper** — one adapter, `product_intelligence/providers/serper.py`, behind the
2B boundary, calling Serper's ordinary Google Search endpoint. It maps
`organic` results to `SearchResult`/`SearchResponse` and fabricates neither a
price (`price_hint_text` stays `None`) nor a part number
(`part_number_hint` stays `None`) — ordinary search publishes neither. The
credential is read from `SERPER_API_KEY` in the server environment only.
Regression tests run entirely offline against a sanitized recorded fixture in
`tests/fixtures/providers/serper/`; the normal test suite makes zero calls to
Serper. **Nothing is wired to it:** the run lifecycle and the web shell are
unchanged, and a submitted run is still `CREATED` and stays there.

**Phase PRODUCT-INTEL.3A is complete: market listing extraction** — the first
vertical slice from a real public URL to a raw observation. A page-fetch
boundary (`product_intelligence/providers/page.py`) with one standard-library
fetcher (`http_page.py`): bounded timeout, redirects and response size,
HTML-only, GET-only, no credential, and refusal of any destination resolving to
a non-public address, revalidated on every redirect hop. Then deterministic
extraction in the research core (`research/listings.py`, `research/extraction.py`)
reading `schema.org` JSON-LD and flat product meta into raw
`ListingObservation`s. **Every value stays text** — no `Decimal`, no currency,
no vocabulary, no arithmetic — and **no price is ever read out of visible page
text**. Seven real public pages were fetched once each; five returned a document
and three yielded usable structured data, all five recorded as sanitized
fixtures in `tests/fixtures/pages/`. **No browser, crawler, or paid scraping
dependency was added, and none is justified yet. Nothing is wired to it:** a
submitted run is still `CREATED`.

**Phase PRODUCT-INTEL.3B is complete: deterministic listing normalization** —
turning one raw `ListingObservation`'s commercial attributes into a
comparable value, or a recorded reason it could not
(`product_intelligence/research/normalization.py`). A valid, unambiguous price
becomes `Decimal`; `"undefined"`, a range (`"$399 - $449"`), a financing
payment (`"$33/mo"`), and a discount (`"20% OFF"`) all abstain with a recorded
`NormalizationIssue` instead of being guessed at, and `"1,00,055"` /
`"1.055,85"` are refused rather than reinterpreted as one locale or the other.
Currency, availability, and condition each normalize through a small
conservative vocabulary — `availability_text="false"` stays `UNKNOWN`, never a
guessed `OUT_OF_STOCK` — and **no exchange-rate conversion exists anywhere**.
Quantity, pack size, and unit price were **not** implemented: no recorded 3A
fixture publishes raw evidence for any of the three, so none was invented.
**It decides no identity and computes no aggregate** — the published MPN/SKU
text is untouched, `identity.py` is never imported, and the normalized
contract carries no accepted/rejected field, no confidence, and no
min/max/median. Proven against the same five recorded 3A fixtures plus a wide
set of synthetic edge cases, entirely offline. **Nothing is wired to it:** a
submitted run is still `CREATED`.

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
* the search-provider boundary (`product_intelligence/providers/search.py`):
  `SearchQuery`, `SearchResult`, `SearchResponse`, the `SearchProvider`
  protocol, and one boundary exception
* the Serper adapter (`product_intelligence/providers/serper.py`): the first
  real `SearchProvider`, calling Serper's ordinary Google Search endpoint, plus
  a sanitized recorded fixture (`tests/fixtures/providers/serper/`) and a
  manual live-smoke script (`scripts/serper_live_smoke.py`)
* the page-fetch boundary (`product_intelligence/providers/page.py`) and its
  standard-library fetcher (`http_page.py`)
* deterministic raw listing extraction (`product_intelligence/research/
  listings.py`, `extraction.py`), five sanitized recorded real-page fixtures
  (`tests/fixtures/pages/`), and a manual smoke script
  (`scripts/page_extract_smoke.py`)
* deterministic listing normalization
  (`product_intelligence/research/normalization.py`): price, currency,
  availability, condition, and seller, each converted or abstained with a
  recorded reason — no identity decision, no aggregate, no FX
* deterministic tests for those contracts, for the corpus, for the lifecycle,
  for the browser workflow, for the comparison, for the provider boundary, for
  the Serper adapter's mapping, for page-fetch safety, for extraction and
  normalization against the recorded real pages (all offline), and for the
  architecture boundaries

**What does not exist:** market research of any kind. There is no candidate
discovery beyond one raw search call, no product lookup, no product resolver,
no description interpretation, no listing matching or rejection, no price
calculation, no comparable-product discovery, no LLM integration, no
structured API, and no integration with any calling system. None of it is
stubbed or partially present — those are later phases. A run can be created
through the browser and moved through its states by code; nothing yet moves
one, because nothing yet does research. The comparison primitive can say
whether two part numbers are the same part number, and nothing supplies it with
a second one. Search can return real results, a page can be fetched and read,
and a raw observation can be normalized into comparable values — but nothing
calls any of them from the run lifecycle or the web shell, nothing decides
which URL to open, nothing says whether a normalized observation belongs to
the requested product, and **no price is computed anywhere**. The corpus
describes what good answers would look like; nothing produces or scores an
answer.

Next planned phase: **PRODUCT-INTEL.3C — MPN matching + rejection.**

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

## The search-provider boundary

One synchronous operation, three provider-neutral contracts:

```text
SearchQuery  ->  SearchProvider.search(query)  ->  SearchResponse
                                                     |- SearchResult, ...
```

```text
SearchQuery      text
SearchResult     source_url, title, snippet,
                 price_hint_text, part_number_hint, raw_reference
SearchResponse   provider_id, query, retrieved_at, results,
                 raw_response_reference
```

A `SearchQuery` is deliberately **not** a `ResearchRequest`. A research request
is a person's input — part number plus description; a query is one string sent
to one external service. Turning the first into one or more of the second is
query generation, which belongs to the research core and does not exist. A
provider handed a research request would have to make that decision itself.

**A price hint is not a price.** `price_hint_text` is whatever price-shaped text
the provider displayed — `$399.99`, `$399.99 - $449.99`, `from $399`, `EUR 320`,
`$33/mo` — and it stays a string. It is never converted to a `Decimal`, given a
currency, resolved between a sale price and a monthly payment, or used in
arithmetic, and the contract has **no numeric price field at all**. Extraction,
normalization, and aggregation are later phases precisely because that
conversion is a decision with rules rather than a cast.

**A part-number hint is unverified.** It exists only when a provider explicitly
publishes such a field, and it is stored exactly as published — not normalized,
not compared, not a match. A part number *inferred* from a title or a snippet is
not this field; that is extraction from noisy text, and it belongs to a phase
that also records why a candidate was rejected. A provider observes; the
research core decides what an observation establishes, by handing the hint to
the deterministic comparison above.

**Provider-native payload stays opaque.** Whatever else a provider returned is
preserved as an opaque string — `raw_reference` on a result,
`raw_response_reference` on a response — so it can be re-inspected by a person
or a test. It is never parsed, and never a dictionary for business logic to read
a vendor-specific key out of, because that is how a vendor ends up inside the
rules the boundary exists to keep it out of.

A result URL must be an absolute `http`/`https` address with a host, so a
`javascript:`, `data:`, or `file:` value never reaches a report; the URL is
otherwise kept exactly as observed. `retrieved_at` must be timezone-aware and is
supplied by the adapter, never generated in the contracts. **Zero results is a
valid answer** — a provider finding nothing is information, not a failure.

There is one exception type, one method, and no async variant — and no registry,
factory, plugin discovery, fallback chain, fan-out, retry policy, rate limiter,
or circuit breaker. One provider arrives next; the boundary is built for
replaceability, not simultaneity.

**No provider existed until 2C.** 2B's own tests used only synthetic fakes;
sanitized recordings of real provider responses begin with the first real
provider, because a fixture invented before a provider is chosen would pass no
matter what the real one does.

## The Serper adapter

`product_intelligence/providers/serper.py` is the first real `SearchProvider`,
calling Serper's ordinary Google Search endpoint
(`https://google.serper.dev/search`) — **not** Google Shopping, which is a
distinct future decision. Vendor naming is correct in this one module; it does
not leak into the generic boundary, the domain, the research core, `runs/`, or
`web/`.

```text
SerperSearchProvider.from_environment()   reads SERPER_API_KEY from the
                                           server environment; never a file,
                                           never a URL, never a client
SerperSearchProvider(api_key=...)         explicit construction for tests
provider.search(SearchQuery(text=...))    one POST, X-API-KEY header,
                                           bounded timeout, stdlib urllib only
```

Mapping from a Serper `organic` entry to `SearchResult` is direct: `link` ->
`source_url`, `title` -> `title`, `snippet` -> `snippet`. Ordinary Google
Search publishes neither a price field nor a part-number field, so
`price_hint_text` and `part_number_hint` are always `None` here — including
when a snippet contains price-shaped text, which real results do. An item
with no usable absolute `http`/`https` link is discarded, never fabricated.
The adapter never calls the part-number comparator; a provider observes, and
2A's identity decision stays where it belongs.

Regression tests (`tests/providers/test_serper_provider.py`) run entirely
offline: they parse a real, sanitized recorded response
(`tests/fixtures/providers/serper/`) and exercise the actual mapping code, plus
synthetic edge cases for malformed items and translated errors with
`urllib.request.urlopen` monkeypatched. The normal `pytest` run makes zero
calls to Serper. A separate, explicitly manual script,
`scripts/serper_live_smoke.py`, makes one real call on request and prints only
a safe summary — provider id, query, result count, public titles and URLs —
never the credential.

**Nothing is wired to this adapter.** The run lifecycle and the web shell do
not import `product_intelligence.providers`, so a submitted run is still
`CREATED` and stays there. Serper becoming part of ordinary application
execution needs basic duplicate-call protection first, since it is a metered,
paid API — that is future work, not settled by 2C.

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
  research/                        part-number comparison (implemented) +
                                    raw listing extraction (implemented) +
                                    listing normalization (implemented)
  providers/                       search boundary + serper.py (implemented) +
                                    page-fetch boundary + http_page.py
                                    (implemented)
  web/                             standalone form + report shell (implemented)
scripts/
  serper_live_smoke.py             manual, explicit live-call check (2C)
  page_extract_smoke.py            manual, explicit live-fetch check (3A)
tests/                             focused deterministic tests
  fixtures/providers/serper/       sanitized recorded Serper response
  fixtures/pages/                  five sanitized recorded real product pages
```

`evaluation/README.md` explains the corpus: its schema, the real-versus-
synthetic rule, the challenge classes, the metric definitions, why no price is
recorded in it, and the discipline governing changes to an expected answer.

`providers/` holds two boundaries and one adapter each: the search boundary
with the Serper adapter behind it (see "The Serper adapter" above), and the
page-fetch boundary with the standard-library `HttpPageFetcher` behind it (see
"Fetching a page" below). The LLM boundary is still documentation only: the
package carries the rules that apply to it, so the phase that implements it does
so into a defined space rather than inventing one.

## Fetching a page, and reading one

3A added the first vertical slice from a public URL to a raw observation, and
the layering is deliberate:

```text
SearchResult        what a search provider said about a URL      (2B / 2C)
FetchedPage         what that URL actually returned              (3A)
ListingObservation  what the returned document publishes         (3A)
```

None of the three is collapsed into another. A snippet is a third party's
description of a page; the page is the page; and neither is a market listing.

**`HttpPageFetcher`** is standard library only — no crawler service, no browser,
no proxy, no per-page fee. Every fetch is bounded (10 s, 3 redirects, 5 MiB,
`text/html` or `application/xhtml+xml`), sends no credential or cookie, issues
GET only, executes no JavaScript, and retrieves the document alone — no images,
scripts, stylesheets, or link traversal. Because a URL may have come from an
external search result, every destination is resolved first and refused unless
*every* address it resolves to is publicly routable; loopback, private,
link-local (including `169.254.169.254`), multicast, and reserved destinations
are refused, and **every redirect hop is revalidated** rather than followed by
`urllib`. An oversized response is refused rather than truncated, because a
document cut mid-element parses as though it were whole.

These are application-level checks and **not** network isolation. DNS
time-of-check/time-of-use and general egress remain open at this layer; the
durable fix is an egress allowlist or outbound proxy in the deployment. That
limitation is documented rather than papered over (§13.6 of the plan).

**`extract_listing_observations`** reads only structured data a page
deliberately published: `schema.org` JSON-LD first, and flat product meta tags
only when JSON-LD produced nothing — one recorded page publishes the same offer
in both places, and running both would turn one offer into two observations.

Every extracted value stays **raw text**. No `Decimal`, no currency, no
condition or availability vocabulary, no arithmetic. That is not caution for its
own sake: one recorded manufacturer page publishes `"price": "undefined"` inside
a well-formed `Offer`, one retailer publishes `"mpn:MZ-QL23T800"` prefix and
all, and one publishes a price with no currency anywhere on the page. A
converting extractor would crash or silently drop each of them; keeping them as
text moved the decision to 3B, where "unparseable price" is now an outcome with
a recorded reason instead of a crash or a silent drop.

**No price is ever read out of visible page text**, and none ever may be. One
recorded page carries fourteen distinct dollar amounts — a shipping threshold,
financing plan bounds, a per-instalment figure, and four recommended products in
markup identical to the real price element. A first-match, lowest-match, or
largest-match rule returns a wrong number from that page with complete
confidence.

Extraction lives in the research core and takes a document *string*, so it
imports nothing from `providers/` and opens no socket; the fetcher knows nothing
about listings. The two halves meet only in a caller that holds both — today,
one manual script:

```bash
python scripts/page_extract_smoke.py https://example.com/some-product
```

The normal test suite makes **zero** network requests: extraction is
regression-tested against the recorded pages in `tests/fixtures/pages/`, and the
fetcher's tests replace both DNS resolution and the opener.

## Normalizing a listing

3B adds one more step, still offline and still deterministic:

```text
ListingObservation  ->  normalize_listing_observation()  ->  NormalizedListingObservation
```

**Price** becomes `Decimal` only when the raw text names exactly one
unambiguous amount — `"1055.85"`, `"1,055.85"`, `"$1,055.85"`, `"EUR 1055.85"`
all parse; `"undefined"`, `"N/A"`, `"from $399"`, `"$399 - $449"`, `"$33/mo"`,
`"20% OFF"`, `"1.055,85"`, and `"1,00,055"` all abstain, each with a recorded
`NormalizationIssue` naming the field, a code (`INVALID_PRICE` or
`AMBIGUOUS_PRICE`), the raw value, and a reason. No first/lowest/largest-amount
rule exists here either, for the same reason none exists in extraction:
`"1.055,85"` is never silently reinterpreted as `1055.85`, and `"undefined"`
never becomes `Decimal("0")`.

**Currency** normalizes to a small set of ISO-style codes, case-insensitively.
`$` and `¥` are **never** treated as establishing a currency — both price
several live currencies — while `€` and `£` may map, because each is
unambiguous. A price and its currency are independent: either can be present
while the other is absent, and **no exchange-rate conversion exists anywhere**.
An unambiguous currency embedded directly in `price_text` (`"EUR 100"`,
`"100 EUR"`, `"€100"`) is real currency evidence, not discarded once the
number is found: it is reconciled with the separately published
`currency_text`, so agreeing evidence from both places reinforces one result
and *disagreeing* evidence (`price_text="EUR 100"` beside
`currency_text="USD"`) abstains to `currency_code=None` with a recorded
`CONFLICTING_CURRENCY` issue rather than either source silently winning. A
price decorated with a currency marker on both sides (`"EUR 100 USD"`) never
normalizes cleanly either way.

**Availability** and **condition** each normalize through a small controlled
vocabulary (`IN_STOCK` / `OUT_OF_STOCK` / `PREORDER` / `BACKORDER` / `LIMITED`
/ `DISCONTINUED` / `UNKNOWN`, and `NEW` / `USED` / `REFURBISHED` / `DAMAGED` /
`UNKNOWN`), recognizing `schema.org` values and a handful of conservative
plain-text spellings. `availability_text="false"` — real evidence off a
recorded fixture — normalizes to `UNKNOWN` with a recorded issue, **never** a
guessed `OUT_OF_STOCK`.

**Seller** gets whitespace cleanup only: no entity resolution, so
`"Amazon.com"` and `"Amazon"` stay two different strings.

**Quantity, pack size, and unit price are not implemented.** An audit of all
five recorded 3A fixtures found no structured field on any of them meaning
"this offer sells N units for this price" — an inventory count and a capacity
figure are not pack size — so none was guessed, and `ListingObservation` was
not extended to invent a field nothing produces.

**It decides no identity and computes no aggregate.** The published MPN/SKU
text is untouched, `research.identity` is never imported, and
`NormalizedListingObservation` carries no accepted/rejected field, no match
type, no confidence, and no min/max/median — a normalized price does not imply
a valid listing. `runs/` and `web/` are unchanged, and a submitted run is
still `CREATED`.

Every `NormalizedListingObservation` holds the exact `ListingObservation` it
was built from, so a reviewer can always trace a normalized value — or an
abstention — back to the raw text that produced it. The normal test suite
still makes **zero** network requests: normalization is regression-tested
against the same five recorded 3A fixtures, plus a wide set of inline
synthetic edge cases for the ambiguous and malformed shapes above.

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
