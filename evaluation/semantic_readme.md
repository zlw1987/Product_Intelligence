# Semantic Match Qualification Corpus

The offline benchmark for semantic product identity matching.

This corpus is **separate from the deterministic evaluation corpus** in `corpus/`.
It is designed to test semantic matching models that may assist with identity
decisions when deterministic evidence is insufficient.

**Important:** This corpus is for *offline qualification only*. No live model
integration is required for this phase.

## Purpose

The semantic qualification corpus evaluates LLM or other semantic models' ability
to determine whether a candidate listing matches a target product when the
deterministic 3C rules cannot establish identity.

**Important:** A false MATCH is materially worse than UNCERTAIN. One character
difference in an MPN can mean an entirely different product.

## Corpus Structure

```
evaluation/
  corpus/                         deterministic evaluation (0B)
  semantic_corpus/                semantic qualification (this file)
    cases.json                    human-readable JSON array of cases

product_intelligence/evaluation/
  semantic/                       offline evaluator package
    evaluator.py                  compute metrics, confusion matrix
    loader.py                     load cases for offline evaluation
    vocabulary.py                 semantic decision vocabulary
    prompt.py                     versioned prompt template
    prompt.py                     versioned prompt template

tests/evaluation/semantic/        tests for semantic corpus + evaluator
```

## Case Schema

```json
{
  "case_id": "SMQ-0001",
  "case_class": "title_exact_mpn",

  "target": {
    "manufacturer_part_number": "MZ1L2960HCJR-00A07",
    "description": "Samsung SSD PM9A3 960GB M.2 NVMe PCIe Gen4"
  },

  "candidate": {
    "product_title": "SSD disk Samsung PM9A3 960GB M.2 22110 NVMe PCIe Gen4 x4 | MZ1L2960HCJR-00A07",
    "manufacturer_part_number_text": null,
    "sku_text": null,
    "description_or_specs": null
  },

  "candidate_evidence_source": "TITLE_TEXT",
  "expected_decision": "MATCH",
  "critical_reason": "Exact MPN in title text with matching product description.",
  "provenance": "project_uat",
  "is_authority_safety_probe": false
}
```

### Evidence Sources

* `TITLE_TEXT` — MPN extracted from product title (not authoritative)
* `SKU_FIELD` — MPN from explicit SKU field (not authoritative)
* `EXPLICIT_MPN_FIELD` — MPN from authoritative explicit field (authoritative)
* `NONE` — No usable MPN evidence

**Authoritative evidence:** When `candidate_evidence_source` is `EXPLICIT_MPN_FIELD`,
the MPN in `manufacturer_part_number_text` is authoritative:
- Exact match → MATCH
- Conflict (different revision/suffix) → NO_MATCH

### Required Fields

* `case_id` — unique identifier (e.g., `SMQ-0001`)
* `case_class` — one of: `title_exact_mpn`, `base_mpn_only`, `different_capacity`,
  `different_form_factor`, `different_interface`, `suffix_missing`,
  `oem_revision_variant`, `accessory_trap`, `compatible_with_trap`,
  `replacement_trap`, `multipack_trap`, `brand_family_only`, `specification_rich`
* `target.manufacturer_part_number` — the MPN we're looking for
* `target.description` — the request description (optional, may be empty)
* `candidate.product_title` — the listing title (may be `null`)
* `candidate.manufacturer_part_number_text` — explicit MPN field (may be `null`)
* `candidate.sku_text` — explicit SKU field (may be `null`)
* `candidate.description_or_specs` — description or specs text (may be `null`)
* `candidate_evidence_source` — `EXPLICIT_MPN_FIELD | SKU_FIELD | TITLE_TEXT | NONE`
* `expected_decision` — `MATCH | NO_MATCH | UNCERTAIN`
* `critical_reason` — human-readable justification
* `provenance` — `synthetic` or `project_uat`
* `is_authority_safety_probe` — `true` for authority safety probe cases only

### Optional Fields

* `notes` — additional context
* `source_url` — URL where this listing was found (for UAT cases)
* `extraction_method` — how MPN was extracted (for UAT cases)

## Decision Vocabulary

### `MATCH`

The candidate listing is very likely the target product.

**Evidence that supports MATCH:**

* Exact MPN appears in title with matching product description
* Critical attributes (brand, family, capacity, form factor, interface) align
* No accessory/compatible-with/replacement wording
* No conflicting explicit MPN

### `NO_MATCH`

The candidate is definitely NOT the target product.

**Evidence that requires NO_MATCH:**

* Explicit conflicting MPN (different revision/suffix)
* Accessory wording: `compatible with`, `for`, `tray`, `caddy`, `kit`, `accessory`
* Different capacity
* Different form factor
* Different interface
* Drive vs enclosure
* Single unit vs multipack

### `UNCERTAIN`

Insufficient evidence to determine match or no-match with confidence.

**Evidence that supports UNCERTAIN:**

* Base MPN only, suffix missing (e.g., `MZ1L2960HCJR` vs `MZ1L2960HCJR-00A07`)
* Capacity matches but form factor unknown
* Description-rich without usable MPN
* Partial overlap without clear exclusion

## Primary Semantic vs Authority Probes

The corpus has two conceptually separate sets:

### Primary Semantic Cases

Evidence sources: `TITLE_TEXT`, `SKU_FIELD`, or `NONE`

These produce the headline semantic metrics:
- Semantic decision accuracy
- Semantic MATCH precision
- Semantic MATCH recall
- False MATCH count and rate
- Safety cost

### Authority Safety Probes

Cases where `is_authority_safety_probe: true`

Small set used only to verify:
- Explicit conflict → NO_MATCH
- Explicit exact → MATCH (if retained as capability probe)

**Authority probes must NOT inflate primary semantic MATCH precision/recall.**

## Accessory Safety Gates

Mandatory hard gates that pass independently of overall metrics:

* **zero_false_match_on_authority_conflicts** — No false MATCH on authority probe cases
* **zero_false_match_on_accessory_safety_set** — No false MATCH on accessory hard-negative set

The accessory safety set includes cases from:
- `accessory_trap`
- `compatible_with_trap`
- `replacement_trap`
- `multipack_trap`
- `drive_vs_enclosure`

One false MATCH in that safety set fails qualification regardless of overall
precision.

## Confusion Matrix Metrics

The evaluator derives all metrics from a 3x3 confusion matrix:

```
Actual MATCH:      M->M, M->N, M->U
Actual NO_MATCH:   N->M, N->N, N->U
Actual UNCERTAIN:  U->M, U->N, U->U
```

### Derived Metrics

* **decision_accuracy** = (M->M + N->N + U->U) / all valid predictions
* **MATCH precision** = M->M / (M->M + N->M + U->M)
* **MATCH recall** = M->M / (M->M + M->N + M->U)
* **NO_MATCH precision** = N->N / (M->N + N->N + U->N)
* **NO_MATCH recall** = N->N / (N->M + N->N + N->U)
* **UNCERTAIN precision** = U->U / (M->U + N->U + U->U)
* **UNCERTAIN recall** = U->U / (U->M + U->N + U->U)
* **false_match_count** = N->M + U->M

## Safety Cost (Lower is Better)

```
safety_cost = 10 * (N->M + U->M)          # false MATCH: expensive
            + 1 * (M->N + M->U + N->U + U->N)  # other errors: cheap
```

* A correct decision costs 0
* A false MATCH (predicting MATCH when expected is NO_MATCH or UNCERTAIN) costs 10
* Any other wrong decision costs 1

## Qualification Gates

| Gate | Threshold | Description |
|------|-----------|-------------|
| `zero_false_match_on_safety_probes` | true | No false MATCH on authority probes |
| `valid_output_rate_sufficient` | >= 0.99 | At least 99% of cases have valid output |
| `match_precision_sufficient` | >= 0.98 | MATCH precision >= 98% |
| `overall_accuracy_target` | >= 0.90 | Decision accuracy >= 90% |

All gates must pass for qualification.

## Strict Parser

The evaluator parses model output with strict rules:

* Output must be exactly one JSON object
* No prose before or after JSON
* No markdown code fences
* Unknown keys rejected (`prose`, `explanation`, `notes` not allowed)
* Missing required keys rejected
* Invalid enum values rejected

**Allowed keys only:**
```json
{
  "decision": "MATCH | NO_MATCH | UNCERTAIN",
  "confidence": "HIGH | MEDIUM | LOW",
  "matched_attributes": [],
  "conflicting_attributes": [],
  "missing_critical_attributes": [],
  "reason_code": "..."
}
```

## Export/Import Workflow

### Export Corpus

```python
from product_intelligence.evaluation.semantic.prompt import export_corpus_to_jsonl

count = export_corpus_to_jsonl(corpus, "prompts.jsonl")
```

Each line contains: `case_id`, `prompt_version`, `system_prompt`, `user_prompt`

### Import Results

```python
from product_intelligence.evaluation.semantic.prompt import import_results_from_jsonl

responses = import_results_from_jsonl("model_outputs.jsonl")
```

Each line should contain: `case_id`, `raw_output` (the raw model response string)

### Evaluate

```python
from product_intelligence.evaluation.semantic.evaluator import evaluate_responses

result = evaluate_responses(corpus, responses)
print(result.gates_passed)  # All gates must be True
```

## Output Contract

A semantic matcher's response must be:

```json
{
  "decision": "MATCH | NO_MATCH | UNCERTAIN",
  "confidence": "HIGH | MEDIUM | LOW",
  "matched_attributes": ["...", "..."],
  "conflicting_attributes": ["...", "..."],
  "missing_critical_attributes": ["...", "..."],
  "reason_code": "..."
}
```

**Invalid responses:**

* Malformed JSON
* Unknown key
* Missing required key
* Invalid enum value
* Prose outside JSON

Invalid responses reduce `valid_output_rate` but do NOT affect confusion matrix
or safety cost calculations.