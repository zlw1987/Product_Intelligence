"""Versioned semantic match prompt template (PRODUCT-INTEL.SEMANTIC).

This module provides a shared, model-independent prompt for semantic matching.
It is used for offline qualification without any live model integration.

The same prompt is used for every model in first qualification.

Single source of truth (FU3A2)
------------------------------
Prompt v1.1 is NOT defined here. ``SEMANTIC_PROMPT_VERSION``, ``SYSTEM_PROMPT``,
``USER_PROMPT_TEMPLATE``, ``SemanticPrompt`` and ``build_prompt`` are
re-exported from the neutral production contract
``product_intelligence.semantic.contract``. Evaluation and production build
byte-identical prompts because they call the *same function object*.

Only the evaluation-specific JSONL export/import workflow is defined locally.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Canonical contract objects - re-exported, never re-implemented.
from product_intelligence.semantic.contract import (
    SEMANTIC_PROMPT_VERSION,
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
    SemanticPrompt,
    build_prompt,
)


# ---------------------------------------------------------------------------
# Export / Import workflow
# ---------------------------------------------------------------------------


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