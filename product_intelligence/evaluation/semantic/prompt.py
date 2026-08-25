"""Versioned semantic match prompt template (PRODUCT-INTEL.SEMANTIC).

This module provides a shared, model-independent prompt for semantic matching.
It is used for offline qualification without any live model integration.

The same prompt is used for every model in first qualification.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# Prompt version
# ---------------------------------------------------------------------------

SEMANTIC_PROMPT_VERSION = "1.0"


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a product identity matching assistant.

Your task is to determine whether a candidate product listing matches a target
product based on manufacturer part number (MPN) and product description evidence.

CRITICAL SAFETY RULES:
- A false MATCH (incorrectly claiming a product matches) is materially worse
  than returning UNCERTAIN when evidence is insufficient.
- One character difference in an MPN can mean an entirely different product.
- Primary semantic cases normally lack authoritative explicit MPN fields.
- If an EXPLICIT_MPN_FIELD is supplied, it IS authoritative:
  * Exact match -> MATCH
  * Conflicting MPN (different revision/suffix) -> NO_MATCH
- Semantic reasoning cannot override an explicit MPN conflict.
- Exact MPN appearing in TITLE_TEXT is strong evidence but is NOT authoritative
  on its own - product description must also align.
- Clear accessory roles (tray, caddy, enclosure, heatsink, adapter,
  standalone kit/bundle, or multipack) are not the target product.
- WARNING SIGNALS - do not automatically label, investigate further:
  * "replacement", "compatible with", and "for" are warning signals
  * Determine whether the listing is the target product itself, an alternative,
    or an accessory. If product role remains ambiguous, return UNCERTAIN.
- Capacity differences (e.g., 960GB vs 1.92TB), form factor differences (e.g.,
  M.2 vs U.2), and interface differences (e.g., NVMe vs SATA) indicate NO_MATCH.
- If critical identity evidence is missing or ambiguous, return UNCERTAIN.
- Do NOT reason about prices or infer seller quality.

Decision vocabulary:
- MATCH: The candidate is very likely the target product based on evidence.
- NO_MATCH: The candidate is definitely NOT the target product.
- UNCERTAIN: Insufficient evidence to determine match or no-match.

Response format: JSON object only, no prose."""


# ---------------------------------------------------------------------------
# User prompt template
# ---------------------------------------------------------------------------

USER_PROMPT_TEMPLATE = """Evaluate whether the candidate product matches the target product.

TARGET PRODUCT:
- Manufacturer Part Number (MPN): {target_mpn}
- Description: {target_description}

CANDIDATE PRODUCT:
- Product Title: {candidate_title}
- Candidate MPN text: {candidate_mpn_field}
- SKU: {candidate_sku}
- Description/Specs: {candidate_specs}
- Evidence Source: {evidence_source}

Based on the evidence above, determine if the candidate is the same product
as the target.

Consider:
1. Does the MPN match exactly (watch for revision/suffix differences)?
2. Does the product description align with the target?
3. Are there capacity, form factor, or interface differences?
4. Is there accessory, compatible-with, replacement, or multipack wording?
5. Is critical identity evidence missing or ambiguous?

Respond with a JSON object:
{{
  "decision": "MATCH" or "NO_MATCH" or "UNCERTAIN",
  "confidence": "HIGH" or "MEDIUM" or "LOW",
  "matched_attributes": ["list of matching attributes"],
  "conflicting_attributes": ["list of conflicting attributes"],
  "missing_critical_attributes": ["list of missing critical evidence"],
  "reason_code": "short code like 'exact_mpn_match' or 'capacity_mismatch'"
}}

JSON object only, no prose."""


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SemanticPrompt:
    """A constructed semantic match prompt with version tracking."""

    version: str
    system_prompt: str
    user_prompt: str
    case_id: str
    target_mpn: str
    target_description: str
    candidate_title: str
    candidate_mpn_field: str | None
    candidate_sku: str | None
    candidate_specs: str | None
    evidence_source: str


def build_prompt(
    case_id: str,
    target_mpn: str,
    target_description: str,
    candidate_title: str,
    candidate_mpn_field: str | None,
    candidate_sku: str | None,
    candidate_specs: str | None,
    evidence_source: str,
) -> SemanticPrompt:
    """Build a versioned semantic match prompt for one case.

    Args:
        case_id: The case identifier
        target_mpn: The target product's MPN
        target_description: The target product's description
        candidate_title: The candidate product's title
        candidate_mpn_field: The MPN from an explicit field (or None)
        candidate_sku: The candidate's SKU (or None)
        candidate_specs: The candidate's description/specs (or None)
        evidence_source: Where the candidate evidence came from

    Returns:
        A SemanticPrompt with versioned prompts ready for model input
    """
    user_prompt = USER_PROMPT_TEMPLATE.format(
        target_mpn=target_mpn or "(not provided)",
        target_description=target_description or "(not provided)",
        candidate_title=candidate_title or "(not provided)",
        candidate_mpn_field=candidate_mpn_field or "(not in explicit field)",
        candidate_sku=candidate_sku or "(not provided)",
        candidate_specs=candidate_specs or "(not provided)",
        evidence_source=evidence_source,
    )

    return SemanticPrompt(
        version=SEMANTIC_PROMPT_VERSION,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        case_id=case_id,
        target_mpn=target_mpn,
        target_description=target_description,
        candidate_title=candidate_title,
        candidate_mpn_field=candidate_mpn_field,
        candidate_sku=candidate_sku,
        candidate_specs=candidate_specs,
        evidence_source=evidence_source,
    )


# ---------------------------------------------------------------------------
# Export / Import workflow
# ---------------------------------------------------------------------------

import json
from pathlib import Path


def export_corpus_to_jsonl(
    corpus,  # SemanticCorpus
    output_path: str | Path,
) -> int:
    """Export semantic corpus + prompts to JSONL for model input.

    Each line in the JSONL file contains:
    - case_id
    - prompt_version
    - system_prompt
    - user_prompt

    Args:
        corpus: The SemanticCorpus to export
        output_path: Path to write the JSONL file

    Returns:
        Number of cases exported

    Raises:
        IOError: If the file cannot be written
    """
    output_path = Path(output_path)
    count = 0

    with open(output_path, "w", encoding="utf-8") as f:
        for case in corpus.cases:
            # Build prompt for this case
            prompt = build_prompt(
                case_id=case.case_id,
                target_mpn=case.target.manufacturer_part_number,
                target_description=case.target.description,
                candidate_title=case.candidate.product_title or "",
                candidate_mpn_field=case.candidate.manufacturer_part_number_text,
                candidate_sku=case.candidate.sku_text,
                candidate_specs=case.candidate.description_or_specs,
                evidence_source=case.candidate_evidence_source,
            )

            record = {
                "case_id": prompt.case_id,
                "prompt_version": prompt.version,
                "system_prompt": prompt.system_prompt,
                "user_prompt": prompt.user_prompt,
            }

            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1

    return count


def import_results_from_jsonl(
    input_path: str | Path,
    corpus_case_ids: set[str],
) -> dict[str, dict[str, Any]]:
    """Import recorded model outputs from JSONL for evaluation.

    Each line should contain:
    - case_id
    - raw_output (the raw model response string)

    Args:
        input_path: Path to read the JSONL file
        corpus_case_ids: REQUIRED set of valid case IDs. Unknown IDs raise ValueError.

    Returns:
        Dict mapping case_id to parsed response dicts

    Raises:
        IOError: If the file cannot be read
        ValueError: If a case_id is not in corpus_case_ids, or if a duplicate
                    case_id is found (regardless of whether earlier entry was valid)
    """
    from product_intelligence.evaluation.semantic.evaluator import parse_raw_output, RawOutputParseError

    input_path = Path(input_path)
    results: dict[str, dict[str, Any]] = {}
    seen_case_ids: set[str] = set()  # Track ALL case IDs, valid or not
    errors: list[str] = []

    with open(input_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(f"Line {line_num}: Invalid JSON - {e}")
                continue

            if "case_id" not in record:
                errors.append(f"Line {line_num}: Missing case_id")
                continue

            case_id = record["case_id"]

            # Validate case_id is a string
            if not isinstance(case_id, str):
                errors.append(f"Line {line_num}: case_id must be string, got {type(case_id).__name__}")
                continue

            # Check for duplicate case_id BEFORE validating raw_output presence.
            # Once a case_id is seen, it is consumed regardless of later validation.
            if case_id in seen_case_ids:
                raise ValueError(f"Line {line_num}: Duplicate case_id '{case_id}'")

            # Mark this case_id as seen BEFORE validating raw_output.
            # Now any subsequent line with the same case_id will be rejected.
            seen_case_ids.add(case_id)

            # Check for unknown case ID (after recording to detect duplicates across
            # valid lines vs unknown lines too)
            if case_id not in corpus_case_ids:
                raise ValueError(f"Line {line_num}: Unknown case_id '{case_id}' not in corpus")

            if "raw_output" not in record:
                errors.append(f"Line {line_num}: Missing raw_output")
                continue

            raw_output = record["raw_output"]

            # Parse raw output
            try:
                parsed = parse_raw_output(raw_output)
                results[case_id] = parsed
            except RawOutputParseError as e:
                errors.append(f"Line {line_num} (case {case_id}): Parse error - {e}")
                continue

    if errors:
        # Log errors but return what we could parse
        import sys
        print(f"Warning: {len(errors)} errors during import:", file=sys.stderr)
        for err in errors[:10]:  # Show first 10
            print(f"  {err}", file=sys.stderr)
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more", file=sys.stderr)

    return results