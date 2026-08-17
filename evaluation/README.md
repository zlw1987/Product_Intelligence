# Evaluation corpus

The durable benchmark Product Intelligence answers are measured against.
Established by **PRODUCT-INTEL.0B**.

Tests and evaluation answer different questions:

* a **test** asks "does the code behave as implemented?"
* an **evaluation** asks "are the answers actually good?"

Everything under `tests/` answers the first question. This corpus exists to
answer the second one, later, without expectations quietly moving to flatter
whichever implementation is being measured.

**Nothing here evaluates anything yet.** There is no resolver, no search, and
no pricing to score — those are later phases. 0B delivers the corpus, its
contract, its validation, and a loader.

## What the corpus is for

The expensive failure is not "found nothing". It is:

```text
confident wrong identity
confident wrong product
confident wrong market conclusion
```

So the corpus treats **false confidence** and **correct abstention** as
first-class subjects. More than half of it is cases where the right answer is
some form of "not established", and several cases record identities that must
*not* be produced.

## Layout

```text
evaluation/
  README.md                     this file
  corpus/
    real_verified.json          real identities, each with an authoritative source
    synthetic.json              constructed cases, including adversarial ones

product_intelligence/evaluation/
  vocabulary.py                 evaluation-only controlled vocabularies
  cases.py                      read-only case objects
  validation.py                 deterministic corpus validation
  loader.py                     the one way to load the corpus

tests/evaluation/               tests for the corpus and its contract
```

The corpus is reference data, not runtime state: it is not a Django model, it
is not persisted, and it is never part of a research run. The loader code lives
inside the package so later phases can import it; the data lives outside it so
it reads as the reviewable document it is.

## REAL_VERIFIED vs SYNTHETIC

The distinction is load-bearing, and the validator enforces it in both
directions.

**`REAL_VERIFIED`** — the expected identity is backed by a recorded
manufacturer-controlled source. Provenance (source name, URL, verification
note, verification date) is mandatory. The five seed identities were checked
against manufacturer sources before the corpus was written.

**`SYNTHETIC`** — the case was constructed to exercise a behaviour. It carries
a construction note explaining what was built and why, and it **cannot** carry
source-shaped provenance: the validator rejects `source_url` and friends on a
synthetic case, because a fabricated citation is worse than none — a later
reviewer would trust it.

A case derived from a real part number is still `SYNTHETIC`. `SYN-0005` is a
mutation of a verified Samsung part number; the mutation is an evaluation
construction, and no claim is made that such a product exists. Wholly
fictitious part numbers use an `EVAL-` prefix so they can never be misread as
real.

Real and synthetic cases live in separate files, and each file declares which
kind it holds. A case whose `case_kind` disagrees with its file is a validation
error, so a synthetic case cannot drift into the real set.

## Case schema

One case, with every field:

```json
{
  "case_id": "SYN-0005",
  "case_kind": "REAL_VERIFIED | SYNTHETIC",

  "input": {
    "manufacturer_part_number": "MZ-QL23T8OO",
    "description": "3.84TB U.2 NVMe SSD"
  },

  "expectation": {
    "resolution": "EXACT_IDENTITY | AMBIGUOUS | CONFLICT | UNKNOWN",
    "manufacturer": "Samsung",
    "canonical_manufacturer_part_number": "MZ-QL23T800",
    "product_name": "PM9A3 NVMe U.2 3.84TB",
    "product_family": "PM9A3",
    "must_not_resolve_to": ["MZ-QL23T800"],
    "reason": "why abstention is correct"
  },

  "challenge_tags": ["NEAR_MISS_MPN"],

  "provenance": { "…see below…" },

  "notes": "free text for a human reviewer",
  "deliberately_shares_identity": false
}
```

`case_id`, `case_kind`, `input`, `expectation`, `challenge_tags`, and
`provenance` are required. `notes` and `deliberately_shares_identity` are
optional. Within `expectation`, only `resolution` is always required. Unknown
fields are rejected everywhere, so a typo cannot silently do nothing.

**`input`** is stored verbatim, whitespace included. Whitespace tolerance is
itself a challenge class, so the corpus must not pre-clean it. The loader
exposes `case.input.as_research_request()`, which applies the real domain
contract; validation constructs one for every case, so no case can ask for
something a caller could not submit.

**`expectation.resolution`** is the class of answer considered correct:

| Value | Meaning |
| --- | --- |
| `EXACT_IDENTITY` | Exactly one canonical identity is correct. |
| `AMBIGUOUS` | Several identities plausibly fit; no single one may be presented as settled. |
| `CONFLICT` | The supplied information points at incompatible identities; the disagreement is the finding. |
| `UNKNOWN` | Nothing supports an identity, including fictitious part numbers. |

`manufacturer` and `canonical_manufacturer_part_number` are required for
`EXACT_IDENTITY` and **forbidden** for the other three — expecting abstention
and naming the answer at the same time is a contradiction. Those three require
`reason` instead.

**`expectation.must_not_resolve_to`** lists part numbers that must not be
reported as *this request's resolved identity*. It does not forbid surfacing
them: a near-miss part number that a report shows and explicitly rejects is the
desired behaviour, while the same part number presented as the answer is the
failure. Most cases do not need the field; where it appears it is the point of
the case.

**`provenance`** takes one of two shapes, chosen by `case_kind`:

```json
"provenance": {
  "kind": "MANUFACTURER",
  "source_name": "Samsung Business",
  "source_url": "https://…",
  "verification_note": "what the source actually says",
  "verified_on": "2026-08-17"
}
```

```json
"provenance": {
  "kind": "SYNTHETIC_CONSTRUCTION",
  "construction": "what was built from what, and why",
  "derived_from_case_ids": ["REAL-0001"]
}
```

`source_url` is **data**. Nothing in this repository fetches it — not the
loader, not the validator, not the tests. A source that has changed must be
re-reviewed by a person; it is never silently re-read.

## What expectations deliberately do not contain

The corpus records truth, not instructions. There is no field for a required
search query, a search provider, an LLM or a prompt, a numeric confidence
score, a ranking algorithm, or a similarity threshold. Those are later phases'
design decisions, and a benchmark that pre-decided them would measure obedience
instead of correctness.

`product_family` is a broad label for human understanding, taken from the
manufacturer source. It is not a category taxonomy — category-specific schemas
are phase 6 work and must not start here.

## Challenge tags

Tags describe the shape of the request, not the product. Every one of these is
exercised by at least one synthetic case, and the tests fail if coverage is
lost.

| Tag | What it exercises |
| --- | --- |
| `EXACT_INPUT` | Correct part number, compatible description. The baseline. |
| `MPN_ONLY_INPUT` | Correct part number, no description. |
| `DESCRIPTION_ONLY_INPUT` | No part number. A strong description is still not part-number evidence. |
| `SURROUNDING_WHITESPACE` | Padding around either value, as copy-paste produces. |
| `NEAR_MISS_MPN` | One-character mutation of a verified part number. |
| `DESCRIPTION_MPN_CONFLICT` | Part number and description name different products. |
| `PARTIAL_MPN` | Truncated or incomplete part number. |
| `PUNCTUATION_VARIANT` | Case and separator differences only. |
| `ACCESSORY_CONFUSION` | An accessory that must not become the product it fits. |
| `AMBIGUOUS_DESCRIPTION` | A description fitting several products. |
| `UNKNOWN_PRODUCT` | A fictitious or unverifiable identity. |
| `CONFLICTING_BRAND` | Brand information pointing in incompatible directions. |

## Validation rules

`product_intelligence/evaluation/validation.py` enforces all of the following
deterministically, with no I/O beyond reading the corpus files:

*Structure* — the file declares a supported `corpus_version` and a
`declared_case_kind`, and holds at least one case; every case carries the
required fields, no unknown fields, and correctly typed values.

*Identity of a case* — `case_id` is unique across the whole corpus and uses
only uppercase letters, digits, and hyphens; `case_kind` is from the controlled
vocabulary and matches the file it is in.

*Input* — exactly the two canonical fields, both strings, together forming a
valid `ResearchRequest`.

*Expectation* — `resolution` is from the controlled vocabulary;
`EXACT_IDENTITY` carries a manufacturer and a canonical part number; the
abstaining resolutions carry neither, and carry a `reason`;
`must_not_resolve_to` holds unique non-empty strings and never contains the
case's own expected canonical identity.

*Challenge tags* — at least one, all from the controlled vocabulary, no
duplicates.

*Provenance* — a real case has an authoritative `kind`, a non-empty
`source_name`, an `https://` `source_url`, a `verification_note`, and an ISO
`verified_on` date; a synthetic case has `SYNTHETIC_CONSTRUCTION` provenance
with a construction note, may not carry source fields at all, and any
`derived_from_case_ids` must reference cases that exist and never itself.

*Across cases* — two real cases may not expect the same canonical identity
unless both set `deliberately_shares_identity`, so a seed recorded twice by
accident cannot inflate the benchmark.

The URL rule is a string check on a recorded citation. Reachability is
explicitly **not** validated: a benchmark that needed the network to load would
be neither deterministic nor durable.

Challenge-tag coverage is *not* a validator rule, because the validator must be
able to validate any subset of the corpus. The tests own coverage.

## Loading it

```python
from product_intelligence.evaluation import load_corpus

corpus = load_corpus()

corpus.real_verified                    # the seed identities
corpus.synthetic                        # the constructed cases
corpus.case("SYN-0005")                 # one case by id
corpus.with_challenge_tag(tag)          # cases exercising one condition
corpus.case("SYN-0005").input.as_research_request()
```

Cases are frozen dataclasses holding tuples, and the corpus index is read-only,
so nothing being measured can edit the thing measuring it. `load_corpus` either
returns a fully valid corpus or raises `CorpusValidationError` — it never
returns a partial one, because a benchmark that silently dropped its hardest
cases would still look like it passed.

## Evaluation metrics

Defined now so later phases measure the same things. **None of them is
computed yet**, and no pass/fail threshold is set: thresholds have to be earned
empirically once there is something to measure, and a number invented today
would be a guess dressed as a standard.

**Identity accuracy** — among cases whose expected resolution is
`EXACT_IDENTITY`, the fraction resolved to the expected canonical identity.

**False-confidence rate** — the count and fraction of cases where the system
confidently resolves to an identity the corpus says is wrong: anything listed
in `must_not_resolve_to`, or a canonical identity other than the expected one.
This is the metric that matters most. A system scoring well on identity
accuracy and badly here is worse than one that answers less often.

**Abstention correctness** — among cases expecting `AMBIGUOUS`, `CONFLICT`, or
`UNKNOWN`, the fraction where the system correctly declines to present a single
settled identity. Reporting candidates, or reporting the conflict, counts as
correct; picking one counts as failure.

**False-exact rate** — the fraction of cases reported as an exact identity
where the corpus does not support one. It overlaps the two above deliberately:
it isolates the specific act of claiming exactness, independent of whether the
product chosen happened to be right.

Price metrics are not defined here. See below.

## Price evaluation is kept time-safe

A market price is an observation at a moment, not a property of a product. So
this corpus contains **no price of any kind**, and no expected price will ever
be added to it. `"this SSD should cost $430"` would be stale within weeks and
would make the benchmark actively dishonest — it would fail a correct
implementation for the crime of running later.

Price evaluation, when the pricing phases arrive, must instead work against
recorded snapshots:

```text
recorded listings at time T   (preserved, timestamped evidence)
        ->
deterministic aggregation
        ->
expected aggregate for that snapshot
```

The expectation is then about the arithmetic and the accept/reject decisions
over a fixed set of observations, which stays true forever, rather than about
the market, which does not. Those snapshots belong with the listing and pricing
phases (3A–4A); nothing about them is built now, and no listing is fetched.

The same reasoning is why real cases record no stock status and no lifecycle
state: neither is in the preserved evidence, and both change.

## Changing the corpus

Evaluation truth must not move when an implementation changes.

If you change an expected answer, the change must state which of these it is:

* **A** — the old expectation was factually wrong;
* **B** — the authoritative source information changed;
* **C** — the case definition was ambiguous;
* **D** — the product behaviour requirement intentionally changed.

**"the new implementation failed this case" is not a valid reason.** That is
the benchmark working. A corpus edited to match whatever the code now does
measures nothing at all.

Adding cases is ordinary work and needs no justification beyond the coverage it
adds. Adding a `REAL_VERIFIED` case requires authoritative provenance as strong
as the existing seeds.

## Growing the corpus

Five real identities is a deliberate floor, not an ambition: every one is
individually verified, and a corpus of carelessly gathered part numbers would
be worse than a small careful one.

The intended expansion is real, representative MPN and description pairs drawn
from the company's sales-order workflow — the actual product lines and the
actual abbreviated, inconsistent descriptions people type. Those inputs are the
real distribution, and no invented case reproduces them.

That expansion has conditions:

* cases are curated and verified before becoming benchmark truth, exactly like
  the seeds — production data is *input*, not automatically *truth*;
* no customer names, sales-order numbers, prices, quantities, or other
  sensitive business data enters this corpus. It holds part numbers,
  descriptions, and expected identities;
* the result is a sanitized representative set, not production records copied
  across.

No such case exists yet, and none is invented here.

## Current contents

```text
REAL_VERIFIED   5
SYNTHETIC      14
total          19
```

Real seed identities: Samsung `MZ-QL23T800`, Micron `MTFDKCC3T8TFR-1BC1ZABYY`,
Intel `PK8071305072902`, Kingston `KSM48R40BS4TMM-32HMR`, Broadcom
`BCM957504-N425G`.
