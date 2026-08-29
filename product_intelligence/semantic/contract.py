"""Neutral semantic contract (PRODUCT-INTEL.SEMANTIC.CONTRACT).

This module contains the shared production semantic contract elements
that are used by both the production runtime and the evaluation harness.

It is intentionally free of:
- Runner/harness code
- Evaluation corpus loading
- Django imports
- Network client imports

The contract provides:
- Prompt v1.1 construction
- Semantic decision/response schema
- Strict raw-response parsing/validation
- Shared vocabulary

This module may be imported by production code without pulling in
evaluation infrastructure.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Prompt version (frozen)
# ---------------------------------------------------------------------------

SEMANTIC_PROMPT_VERSION = "1.1"


# ---------------------------------------------------------------------------
# System prompt (frozen)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a product identity matching assistant.

Your task is to determine whether a candidate product listing matches a target
product based on manufacturer part number (MPN) and product description evidence.

CRITICAL SAFETY RULES:
- Use ONLY the evidence supplied in the target and candidate.
- Do not rely on unstated product specifications or outside product knowledge.
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
- When uncertain between MATCH and UNCERTAIN, prefer UNCERTAIN.

DECISION PRECEDENCE (apply in order):

A. AUTHORITATIVE EXPLICIT MPN

1. Explicit authoritative MPN conflict (different revision/suffix):
       -> NO_MATCH
   Semantic similarity never overrides it.

2. Explicit authoritative exact target MPN:
       -> MATCH
   Do not downgrade merely because non-conflicting descriptive fields
   are missing.

B. CLEAR DIFFERENT PRODUCT ROLE / HARD NEGATIVES

Before allowing title/spec similarity to produce MATCH:

3. Clear accessory / tray / caddy / enclosure / adapter / heatsink /
   cable / kit / multipack / different product role:
       -> NO_MATCH

4. "compatible with TARGET" or "compatible replacement for TARGET":
       -> NO_MATCH

5. "replacement for TARGET" alone, without sufficient identity evidence:
       -> UNCERTAIN

C. TITLE MPN

6. Exact target MPN clearly present in title/text:
       -> MATCH
   ONLY if the listing clearly represents the target product itself
   and no supplied evidence conflicts.

   An accessory, kit, compatible product, replacement product, or
   conflicting critical attribute must NOT be rescued by exact-MPN text
   appearing somewhere in the title.

D. SUFFIX

7. Target ABC-XYZ vs candidate ABC:
       suffix MISSING
       -> UNCERTAIN
       unless other supplied evidence proves identity or mismatch.

8. Target ABC-XYZ vs candidate ABC-XYQ:
       suffix explicitly DIFFERENT
       -> NO_MATCH

E. NO USABLE MPN / SPEC-ONLY

9. If target lacks usable MPN, or identity is supported only by aligned
   manufacturer/family/capacity/form-factor/interface/specs:

       spec similarity alone can NEVER produce MATCH.

   If a supplied critical attribute explicitly conflicts:
       -> NO_MATCH

   Otherwise:
       -> UNCERTAIN

F. OTHER CRITICAL CONFLICT

10. Explicit material supplied-evidence conflict in capacity, form factor,
    interface, revision, suffix, quantity, or product role:
        -> NO_MATCH

11. Otherwise insufficient identity evidence:
        -> UNCERTAIN

Decision vocabulary:
- MATCH: The candidate is very likely the target product based on evidence.
- NO_MATCH: The candidate is definitely NOT the target product.
- UNCERTAIN: Insufficient evidence to determine match or no-match.

Response format: Return the JSON object directly.
Do not wrap it in Markdown or code fences.
Do not include prose before or after the JSON object."""


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
# Vocabulary
# ---------------------------------------------------------------------------


class SemanticDecision(str, Enum):
    """Semantic match decision.

    The three decisions are mutually exclusive:

    * `MATCH` — the candidate is very likely the target product
    * `NO_MATCH` — the candidate is definitely not the target product
    * `UNCERTAIN` — insufficient evidence to determine match or no-match
    """

    MATCH = "MATCH"
    NO_MATCH = "NO_MATCH"
    UNCERTAIN = "UNCERTAIN"


class ConfidenceLevel(str, Enum):
    """Confidence in the semantic match decision."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass(frozen=True)
class SemanticMatchResponse:
    """Structured response from a semantic match model.

    This is the contract that semantic matchers must produce. The evaluator
    validates responses against this schema.
    """

    decision: SemanticDecision
    confidence: ConfidenceLevel
    matched_attributes: tuple[str, ...]
    conflicting_attributes: tuple[str, ...]
    missing_critical_attributes: tuple[str, ...]
    reason_code: str

    def __post_init__(self) -> None:
        """Validate the response structure."""
        if not isinstance(self.decision, SemanticDecision):
            raise TypeError(
                f"decision must be SemanticDecision, got {type(self.decision).__name__}"
            )
        if not isinstance(self.confidence, ConfidenceLevel):
            raise TypeError(
                f"confidence must be ConfidenceLevel, got {type(self.confidence).__name__}"
            )
        if not isinstance(self.matched_attributes, tuple):
            raise TypeError(
                f"matched_attributes must be tuple, got {type(self.matched_attributes).__name__}"
            )
        if not isinstance(self.conflicting_attributes, tuple):
            raise TypeError(
                f"conflicting_attributes must be tuple, got {type(self.conflicting_attributes).__name__}"
            )
        if not isinstance(self.missing_critical_attributes, tuple):
            raise TypeError(
                f"missing_critical_attributes must be tuple, got {type(self.missing_critical_attributes).__name__}"
            )
        if not isinstance(self.reason_code, str):
            raise TypeError(
                f"reason_code must be str, got {type(self.reason_code).__name__}"
            )
        if not self.reason_code:
            raise ValueError("reason_code must be non-empty")


# ---------------------------------------------------------------------------
# Raw output parser (strict)
# ---------------------------------------------------------------------------


class RawOutputParseError(ValueError):
    """Raised when raw model output cannot be parsed."""

    pass


def parse_raw_output(raw_output: str) -> dict[str, Any]:
    """Parse raw model output into a response dict.

    Strict parsing rules:
    - Entire trimmed output must be exactly one JSON object
    - No prose before/after JSON
    - No markdown code fences
    - Malformed JSON rejected
    - JSON arrays rejected
    - Unknown keys rejected (prose, explanation, notes NOT allowed)
    - Missing required keys rejected
    - Invalid enum values rejected

    Args:
        raw_output: Raw string output from model

    Returns:
        Parsed response dict

    Raises:
        RawOutputParseError: If parsing fails
    """
    if not isinstance(raw_output, str):
        raise RawOutputParseError(f"Raw output must be string, got {type(raw_output).__name__}")

    trimmed = raw_output.strip()

    if not trimmed:
        raise RawOutputParseError("Empty output")

    if trimmed.startswith("```"):
        raise RawOutputParseError("Markdown code fences not allowed")

    if not trimmed.startswith("{"):
        raise RawOutputParseError("Output must be a JSON object starting with '{'")

    if not trimmed.endswith("}"):
        raise RawOutputParseError("Output must end with '}'")

    try:
        parsed = json.loads(trimmed)
    except json.JSONDecodeError as e:
        raise RawOutputParseError(f"Invalid JSON: {e}")

    if not isinstance(parsed, dict):
        raise RawOutputParseError(f"Output must be JSON object, got {type(parsed).__name__}")

    required_keys = {
        "decision",
        "confidence",
        "matched_attributes",
        "conflicting_attributes",
        "missing_critical_attributes",
        "reason_code",
    }
    missing = required_keys - set(parsed.keys())
    if missing:
        raise RawOutputParseError(f"Missing required keys: {missing}")

    # Unknown keys - only required keys are allowed (prose/explanation/notes NOT permitted)
    unknown = set(parsed.keys()) - required_keys
    if unknown:
        raise RawOutputParseError(f"Unknown keys: {unknown}")

    valid_decisions = {"MATCH", "NO_MATCH", "UNCERTAIN"}
    if parsed["decision"] not in valid_decisions:
        raise RawOutputParseError(f"Invalid decision: {parsed['decision']}")

    valid_confidences = {"HIGH", "MEDIUM", "LOW"}
    if parsed["confidence"] not in valid_confidences:
        raise RawOutputParseError(f"Invalid confidence: {parsed['confidence']}")

    for key in ["matched_attributes", "conflicting_attributes", "missing_critical_attributes"]:
        if not isinstance(parsed[key], list):
            raise RawOutputParseError(f"{key} must be array")

    if not isinstance(parsed["reason_code"], str) or not parsed["reason_code"].strip():
        raise RawOutputParseError("reason_code must be non-empty string")

    return parsed


def validate_response(response: dict[str, Any] | SemanticMatchResponse) -> SemanticMatchResponse:
    """Validate and normalize a semantic match model response.

    Args:
        response: The raw response dict or already-constructed SemanticMatchResponse.

    Returns:
        A validated SemanticMatchResponse.

    Raises:
        ValueError: If the response is invalid.
    """
    if isinstance(response, SemanticMatchResponse):
        return response

    if not isinstance(response, dict):
        raise TypeError(f"Response must be dict or SemanticMatchResponse, got {type(response).__name__}")

    required = [
        "decision",
        "confidence",
        "matched_attributes",
        "conflicting_attributes",
        "missing_critical_attributes",
        "reason_code",
    ]
    for field_name in required:
        if field_name not in response:
            raise ValueError(f"Missing required field: {field_name}")

    decision_value = response["decision"]
    if not isinstance(decision_value, str):
        raise TypeError(f"decision must be string, got {type(decision_value).__name__}")
    try:
        decision = SemanticDecision(decision_value)
    except ValueError:
        raise ValueError(
            f"Invalid decision '{decision_value}'. "
            f"Must be one of: {[d.value for d in SemanticDecision]}"
        )

    confidence_value = response["confidence"]
    if not isinstance(confidence_value, str):
        raise TypeError(f"confidence must be string, got {type(confidence_value).__name__}")
    try:
        confidence = ConfidenceLevel(confidence_value)
    except ValueError:
        raise ValueError(
            f"Invalid confidence '{confidence_value}'. "
            f"Must be one of: {[c.value for c in ConfidenceLevel]}"
        )

    for key in ["matched_attributes", "conflicting_attributes", "missing_critical_attributes"]:
        arr = response[key]
        if not isinstance(arr, list):
            raise TypeError(f"{key} must be array, got {type(arr).__name__}")
        for item in arr:
            if not isinstance(item, str):
                raise TypeError(f"{key} items must be string, got {type(item).__name__}")

    reason_code = response["reason_code"]
    if not isinstance(reason_code, str):
        raise TypeError(f"reason_code must be string, got {type(reason_code).__name__}")
    if not reason_code:
        raise ValueError("reason_code must be non-empty")

    # Unknown keys check
    allowed_keys = set(required)
    for key in response.keys():
        if key not in allowed_keys:
            raise ValueError(f"Unknown key in response: {key}")

    return SemanticMatchResponse(
        decision=decision,
        confidence=confidence,
        matched_attributes=tuple(response["matched_attributes"]),
        conflicting_attributes=tuple(response["conflicting_attributes"]),
        missing_critical_attributes=tuple(response["missing_critical_attributes"]),
        reason_code=reason_code,
    )


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