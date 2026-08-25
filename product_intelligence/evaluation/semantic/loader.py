"""Semantic match qualification corpus loader (PRODUCT-INTEL.SEMANTIC).

This module loads and validates the semantic match qualification corpus
from the JSON file.

No live model integration is required for this phase.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from product_intelligence.evaluation.semantic.vocabulary import (
    ConfidenceLevel,
    SemanticCaseClass,
    SemanticDecision,
    SemanticMatchResponse,
)


@dataclass(frozen=True)
class SemanticMatchTarget:
    """The target product we're looking for."""

    manufacturer_part_number: str
    description: str


@dataclass(frozen=True)
class SemanticMatchCandidate:
    """The candidate listing we're evaluating."""

    product_title: str | None
    manufacturer_part_number_text: str | None
    sku_text: str | None
    description_or_specs: str | None


@dataclass(frozen=True)
class SemanticMatchCase:
    """One semantic match qualification case."""

    case_id: str
    case_class: SemanticCaseClass
    target: SemanticMatchTarget
    candidate: SemanticMatchCandidate
    candidate_evidence_source: str
    expected_decision: SemanticDecision
    critical_reason: str
    provenance: str
    notes: str | None = None
    source_url: str | None = None
    extraction_method: str | None = None
    is_authority_safety_probe: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation for JSON serialization."""
        return {
            "case_id": self.case_id,
            "case_class": self.case_class.value,
            "target": {
                "manufacturer_part_number": self.target.manufacturer_part_number,
                "description": self.target.description,
            },
            "candidate": {
                "product_title": self.candidate.product_title,
                "manufacturer_part_number_text": self.candidate.manufacturer_part_number_text,
                "sku_text": self.candidate.sku_text,
                "description_or_specs": self.candidate.description_or_specs,
            },
            "candidate_evidence_source": self.candidate_evidence_source,
            "expected_decision": self.expected_decision.value,
            "critical_reason": self.critical_reason,
            "provenance": self.provenance,
            "notes": self.notes,
            "source_url": self.source_url,
            "extraction_method": self.extraction_method,
        }


@dataclass(frozen=True)
class SemanticCorpus:
    """The complete semantic match qualification corpus."""

    corpus_version: int
    cases: tuple[SemanticMatchCase, ...]

    def __len__(self) -> int:
        """Return the number of cases in the corpus."""
        return len(self.cases)

    def get_case(self, case_id: str) -> SemanticMatchCase:
        """Get a case by its ID.

        Raises:
            KeyError: If the case is not found.
        """
        for case in self.cases:
            if case.case_id == case_id:
                return case
        raise KeyError(f"Case not found: {case_id}")

    def filter_by_class(self, case_class: SemanticCaseClass) -> tuple[SemanticMatchCase, ...]:
        """Filter cases by class."""
        return tuple(c for c in self.cases if c.case_class is case_class)

    def filter_by_provenance(self, provenance: str) -> tuple[SemanticMatchCase, ...]:
        """Filter cases by provenance (synthetic or project_uat)."""
        return tuple(c for c in self.cases if c.provenance == provenance)


def load_corpus(path: str | Path | None = None) -> SemanticCorpus:
    """Load the semantic match qualification corpus from JSON.

    Args:
        path: Path to the cases.json file. If None, uses the default location.

    Returns:
        A SemanticCorpus instance with all cases loaded and validated.

    Raises:
        FileNotFoundError: If the file is not found.
        ValueError: If the file is invalid or contains validation errors.
    """
    if path is None:
        # Use absolute path based on project root
        path = Path(__file__).parent / ".." / ".." / "evaluation" / "semantic_corpus" / "cases.json"
        # Resolve to absolute path
        path = path.resolve()
        # If not found, try from tests directory
        if not path.exists():
            path = Path("evaluation") / "semantic_corpus" / "cases.json"
    elif isinstance(path, str):
        path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Semantic corpus file not found: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in semantic corpus: {e}")

    # Validate top-level structure
    if not isinstance(data, dict):
        raise ValueError("Semantic corpus must be a JSON object")

    if "corpus_version" not in data:
        raise ValueError("Semantic corpus must have corpus_version")
    if "cases" not in data:
        raise ValueError("Semantic corpus must have cases")

    corpus_version = data["corpus_version"]
    if not isinstance(corpus_version, int) or corpus_version < 1:
        raise ValueError(f"Invalid corpus_version: {corpus_version}")

    cases_data = data["cases"]
    if not isinstance(cases_data, list):
        raise ValueError("cases must be a JSON array")

    cases: list[SemanticMatchCase] = []
    seen_ids: set[str] = set()

    for idx, case_data in enumerate(cases_data):
        case_id = _validate_case(case_data, idx, seen_ids)
        case = _build_case(case_data, case_id)
        cases.append(case)
        seen_ids.add(case_id)

    return SemanticCorpus(
        corpus_version=corpus_version,
        cases=tuple(cases),
    )


def _validate_case(case_data: dict[str, Any], index: int, seen_ids: set[str]) -> str:
    """Validate one case and return its ID.

    Raises:
        ValueError: If the case is invalid.
    """
    if not isinstance(case_data, dict):
        raise ValueError(f"Case at index {index} must be a JSON object")

    # Required fields
    required = [
        "case_id", "case_class", "target", "candidate",
        "candidate_evidence_source", "expected_decision",
        "critical_reason", "provenance",
    ]
    for field in required:
        if field not in case_data:
            raise ValueError(f"Case at index {index} missing required field: {field}")

    case_id = case_data["case_id"]
    if not isinstance(case_id, str):
        raise ValueError(f"Case at index {index}: case_id must be string")
    if not case_id:
        raise ValueError(f"Case at index {index}: case_id must be non-empty")
    if case_id in seen_ids:
        raise ValueError(f"Duplicate case_id: {case_id}")
    seen_ids.add(case_id)

    # Validate case_class
    case_class_value = case_data["case_class"]
    if not isinstance(case_class_value, str):
        raise ValueError(f"Case {case_id}: case_class must be string")
    try:
        case_class = SemanticCaseClass(case_class_value)
    except ValueError:
        raise ValueError(
            f"Case {case_id}: invalid case_class '{case_class_value}'. "
            f"Must be one of: {[c.value for c in SemanticCaseClass]}"
        )
    case_data["_validated_case_class"] = case_class

    # Validate expected_decision
    expected_decision_value = case_data["expected_decision"]
    if not isinstance(expected_decision_value, str):
        raise ValueError(f"Case {case_id}: expected_decision must be string")
    try:
        expected_decision = SemanticDecision(expected_decision_value)
    except ValueError:
        raise ValueError(
            f"Case {case_id}: invalid expected_decision '{expected_decision_value}'. "
            f"Must be one of: {[d.value for d in SemanticDecision]}"
        )
    case_data["_validated_expected_decision"] = expected_decision

    # Validate provenance
    provenance = case_data["provenance"]
    if not isinstance(provenance, str):
        raise ValueError(f"Case {case_id}: provenance must be string")
    if provenance not in ("synthetic", "project_uat"):
        raise ValueError(
            f"Case {case_id}: provenance must be 'synthetic' or 'project_uat', "
            f"got '{provenance}'"
        )

    # Validate target
    target = case_data["target"]
    if not isinstance(target, dict):
        raise ValueError(f"Case {case_id}: target must be object")
    if "manufacturer_part_number" not in target:
        raise ValueError(f"Case {case_id}: target must have manufacturer_part_number")
    if "description" not in target:
        raise ValueError(f"Case {case_id}: target must have description")
    case_data["_validated_target"] = SemanticMatchTarget(
        manufacturer_part_number=target["manufacturer_part_number"],
        description=target["description"],
    )

    # Validate candidate
    candidate = case_data["candidate"]
    if not isinstance(candidate, dict):
        raise ValueError(f"Case {case_id}: candidate must be object")
    case_data["_validated_candidate"] = SemanticMatchCandidate(
        product_title=candidate.get("product_title"),
        manufacturer_part_number_text=candidate.get("manufacturer_part_number_text"),
        sku_text=candidate.get("sku_text"),
        description_or_specs=candidate.get("description_or_specs"),
    )

    # Validate optional fields
    if "notes" in case_data and case_data["notes"] is not None:
        if not isinstance(case_data["notes"], str):
            raise ValueError(f"Case {case_id}: notes must be string or null")
    if "source_url" in case_data and case_data["source_url"] is not None:
        if not isinstance(case_data["source_url"], str):
            raise ValueError(f"Case {case_id}: source_url must be string or null")
    if "extraction_method" in case_data and case_data["extraction_method"] is not None:
        if not isinstance(case_data["extraction_method"], str):
            raise ValueError(f"Case {case_id}: extraction_method must be string or null")
    if "is_authority_safety_probe" in case_data:
        if not isinstance(case_data["is_authority_safety_probe"], bool):
            raise ValueError(f"Case {case_id}: is_authority_safety_probe must be boolean")

    return case_id


def _build_case(case_data: dict[str, Any], case_id: str) -> SemanticMatchCase:
    """Build a SemanticMatchCase from validated data."""
    return SemanticMatchCase(
        case_id=case_id,
        case_class=case_data["_validated_case_class"],
        target=case_data["_validated_target"],
        candidate=case_data["_validated_candidate"],
        candidate_evidence_source=case_data["candidate_evidence_source"],
        expected_decision=case_data["_validated_expected_decision"],
        critical_reason=case_data["critical_reason"],
        provenance=case_data["provenance"],
        notes=case_data.get("notes"),
        source_url=case_data.get("source_url"),
        extraction_method=case_data.get("extraction_method"),
        is_authority_safety_probe=case_data.get("is_authority_safety_probe", False),
    )


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

    # Required fields
    required = ["decision", "confidence", "matched_attributes",
                "conflicting_attributes", "missing_critical_attributes", "reason_code"]
    for field in required:
        if field not in response:
            raise ValueError(f"Missing required field: {field}")

    # Validate decision
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

    # Validate confidence
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

    # Validate arrays
    matched_attributes = response["matched_attributes"]
    if not isinstance(matched_attributes, list):
        raise TypeError(f"matched_attributes must be array, got {type(matched_attributes).__name__}")
    for item in matched_attributes:
        if not isinstance(item, str):
            raise TypeError(f"matched_attributes items must be string, got {type(item).__name__}")

    conflicting_attributes = response["conflicting_attributes"]
    if not isinstance(conflicting_attributes, list):
        raise TypeError(f"conflicting_attributes must be array, got {type(conflicting_attributes).__name__}")
    for item in conflicting_attributes:
        if not isinstance(item, str):
            raise TypeError(f"conflicting_attributes items must be string, got {type(item).__name__}")

    missing_critical_attributes = response["missing_critical_attributes"]
    if not isinstance(missing_critical_attributes, list):
        raise TypeError(f"missing_critical_attributes must be array, got {type(missing_critical_attributes).__name__}")
    for item in missing_critical_attributes:
        if not isinstance(item, str):
            raise TypeError(f"missing_critical_attributes items must be string, got {type(item).__name__}")

    # Validate reason_code
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
        matched_attributes=tuple(matched_attributes),
        conflicting_attributes=tuple(conflicting_attributes),
        missing_critical_attributes=tuple(missing_critical_attributes),
        reason_code=reason_code,
    )
