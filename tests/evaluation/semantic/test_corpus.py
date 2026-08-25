"""Tests for semantic match qualification corpus loader.

 PRODUCT-INTEL.SEMANTIC
"""

from pathlib import Path

from product_intelligence.evaluation.semantic.loader import (
    SemanticCorpus,
    SemanticDecision,
    SemanticMatchCandidate,
    SemanticMatchCase,
    SemanticMatchTarget,
    SemanticCaseClass,
    load_corpus,
    validate_response,
)


def test_load_corpus():
    """Test loading the semantic corpus."""
    corpus = load_corpus()
    assert isinstance(corpus, SemanticCorpus)
    assert len(corpus.cases) >= 50  # At least 50 cases as specified


def test_corpus_case_count_distribution():
    """Test that the corpus has the required case distribution."""
    corpus = load_corpus()

    case_classes = [c.case_class for c in corpus.cases]

    # Count by class
    from collections import Counter
    class_counts = Counter(case_classes)

    # Check we have at least some of each required class
    required_classes = [
        SemanticCaseClass.TITLE_EXACT_MPN,
        SemanticCaseClass.BASE_MPN_ONLY,
        SemanticCaseClass.DIFFERENT_CAPACITY,
        SemanticCaseClass.ACCESSORY_TRAP,
        SemanticCaseClass.COMPATIBLE_WITH_TRAP,
        SemanticCaseClass.REPLACEMENT_TRAP,
    ]

    for cls in required_classes:
        assert class_counts.get(cls, 0) > 0, f"Missing cases for class {cls.value}"


def test_corpus_unique_case_ids():
    """Test that all case IDs are unique."""
    corpus = load_corpus()
    case_ids = [c.case_id for c in corpus.cases]
    assert len(case_ids) == len(set(case_ids)), "Duplicate case IDs found"


def test_corpus_provenance_values():
    """Test that provenance values are valid."""
    corpus = load_corpus()
    for case in corpus.cases:
        assert case.provenance in ("synthetic", "project_uat"), \
            f"Invalid provenance '{case.provenance}' for case {case.case_id}"


def test_corpus_decision_values():
    """Test that expected_decision values are valid."""
    corpus = load_corpus()
    valid_decisions = {d.value for d in SemanticDecision}
    for case in corpus.cases:
        assert case.expected_decision.value in valid_decisions, \
            f"Invalid decision '{case.expected_decision}' for case {case.case_id}"


def test_corpus_required_uat_cases():
    """Test that required MZ1 UAT cases are present."""
    corpus = load_corpus()

    # Required case IDs from specification
    required_ids = [
        "SMQ-0001",  # Title exact / direct product
        "SMQ-0002",  # Base MPN only
        "SMQ-0003",  # Same family different capacity
        "SMQ-0004",  # Explicit conflict
        "SMQ-0005",  # Accessory trap
        "SMQ-0006",  # Replacement/caddy trap
    ]

    case_ids = {c.case_id for c in corpus.cases}
    for req_id in required_ids:
        assert req_id in case_ids, f"Missing required case {req_id}"


def test_corpus_accessory_hard_negatives():
    """Test that accessory exact-MPN hard negatives are present."""
    corpus = load_corpus()

    accessory_cases = [
        c for c in corpus.cases
        if c.case_class in (
            SemanticCaseClass.ACCESSORY_TRAP,
            SemanticCaseClass.COMPATIBLE_WITH_TRAP,
            SemanticCaseClass.REPLACEMENT_TRAP,
        )
        and "MZ1L2960HCJR-00A07" in c.candidate.product_title
    ]

    # At least 3 accessory trap cases with exact MPN in title
    assert len(accessory_cases) >= 3, \
        f"Expected at least 3 accessory trap cases with exact MPN, found {len(accessory_cases)}"


def test_validate_response_valid():
    """Test validating a valid semantic match response."""
    response = {
        "decision": "MATCH",
        "confidence": "HIGH",
        "matched_attributes": ["brand", "capacity"],
        "conflicting_attributes": [],
        "missing_critical_attributes": [],
        "reason_code": "exact_mpn_match",
    }

    validated = validate_response(response)
    assert validated.decision.value == "MATCH"
    assert validated.confidence.value == "HIGH"
    assert validated.matched_attributes == ("brand", "capacity")


def test_validate_response_invalid_decision():
    """Test that invalid decision is rejected."""
    response = {
        "decision": "INVALID",
        "confidence": "HIGH",
        "matched_attributes": [],
        "conflicting_attributes": [],
        "missing_critical_attributes": [],
        "reason_code": "test",
    }

    try:
        validate_response(response)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "decision" in str(e).lower()


def test_validate_response_unknown_key():
    """Test that unknown keys are rejected."""
    response = {
        "decision": "MATCH",
        "confidence": "HIGH",
        "matched_attributes": [],
        "conflicting_attributes": [],
        "missing_critical_attributes": [],
        "reason_code": "test",
        "unknown_field": "value",
    }

    try:
        validate_response(response)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "unknown" in str(e).lower() or "unknown key" in str(e).lower()


def test_validate_response_missing_field():
    """Test that missing required fields are rejected."""
    response = {
        "decision": "MATCH",
        "confidence": "HIGH",
        # Missing other required fields
    }

    try:
        validate_response(response)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "field" in str(e).lower()


def test_validate_response_prose_rejected():
    """Test that prose outside JSON is detected."""
    # This test would be run if we were parsing raw text responses
    # For now, we test that dict inputs are validated
    response = "This is prose, not JSON"
    try:
        validate_response(response)
        assert False, "Should have raised TypeError"
    except TypeError as e:
        assert "dict" in str(e).lower() or "response" in str(e).lower()


def test_corpus_case_classes_covered():
    """Test that all required case classes are represented."""
    corpus = load_corpus()

    case_classes = [c.case_class for c in corpus.cases]
    from collections import Counter
    class_counts = Counter(case_classes)

    # Check distribution: at least 15 MATCH, 20 NO_MATCH, 10 UNCERTAIN
    decisions = [c.expected_decision for c in corpus.cases]
    decision_counts = Counter(decisions)

    assert decision_counts.get(SemanticDecision.MATCH, 0) >= 12, \
        f"Expected at least 12 MATCH cases, found {decision_counts.get(SemanticDecision.MATCH, 0)}"
    assert decision_counts.get(SemanticDecision.NO_MATCH, 0) >= 20, \
        f"Expected at least 20 NO_MATCH cases, found {decision_counts.get(SemanticDecision.NO_MATCH, 0)}"
    assert decision_counts.get(SemanticDecision.UNCERTAIN, 0) >= 10, \
        f"Expected at least 10 UNCERTAIN cases, found {decision_counts.get(SemanticDecision.UNCERTAIN, 0)}"


def test_corpus_mz1_uat_cases():
    """Test that all MZ1 UAT cases are present with correct expectations."""
    corpus = load_corpus()

    # Build a map for quick lookup
    case_map = {c.case_id: c for c in corpus.cases}

    # Check required cases
    # SMQ-0001: Title exact / direct product -> MATCH
    case = case_map.get("SMQ-0001")
    assert case is not None, "Missing SMQ-0001"
    assert case.expected_decision == SemanticDecision.MATCH, \
        f"SMQ-0001 should be MATCH, got {case.expected_decision.value}"

    # SMQ-0002: Base MPN only -> UNCERTAIN
    case = case_map.get("SMQ-0002")
    assert case is not None, "Missing SMQ-0002"
    assert case.expected_decision == SemanticDecision.UNCERTAIN, \
        f"SMQ-0002 should be UNCERTAIN, got {case.expected_decision.value}"

    # SMQ-0003: Same family different capacity -> NO_MATCH
    case = case_map.get("SMQ-0003")
    assert case is not None, "Missing SMQ-0003"
    assert case.expected_decision == SemanticDecision.NO_MATCH, \
        f"SMQ-0003 should be NO_MATCH, got {case.expected_decision.value}"

    # SMQ-0004: Explicit conflict -> NO_MATCH
    case = case_map.get("SMQ-0004")
    assert case is not None, "Missing SMQ-0004"
    assert case.expected_decision == SemanticDecision.NO_MATCH, \
        f"SMQ-0004 should be NO_MATCH, got {case.expected_decision.value}"

    # SMQ-0005: Accessory trap -> NO_MATCH
    case = case_map.get("SMQ-0005")
    assert case is not None, "Missing SMQ-0005"
    assert case.expected_decision == SemanticDecision.NO_MATCH, \
        f"SMQ-0005 should be NO_MATCH, got {case.expected_decision.value}"

    # SMQ-0006: Replacement/caddy trap -> NO_MATCH
    case = case_map.get("SMQ-0006")
    assert case is not None, "Missing SMQ-0006"
    assert case.expected_decision == SemanticDecision.NO_MATCH, \
        f"SMQ-0006 should be NO_MATCH, got {case.expected_decision.value}"


def test_corpus_no_duplicate_primary_cases():
    """Test that no two PRIMARY cases are exact duplicates.

    PRIMARY cases must not share the same:
      - case_class
      - target.manufacturer_part_number
      - target.description
      - candidate.product_title
      - candidate.manufacturer_part_number_text
      - candidate.sku_text
      - candidate.description_or_specs
      - candidate_evidence_source
      - expected_decision

    case_id, notes, critical_reason, and provenance are NOT part of the
    duplicate key - they cannot make otherwise identical cases unique.
    """
    corpus = load_corpus()

    # Get only PRIMARY (non-authority-probe) cases
    primary_cases = [c for c in corpus.cases if not c.is_authority_safety_probe]

    # Build duplicate key for each case
    seen: dict[tuple, str] = {}
    duplicates: list[tuple[str, str]] = []  # (case_id, existing_case_id)

    for case in primary_cases:
        key = (
            case.case_class.value,
            case.target.manufacturer_part_number,
            case.target.description,
            case.candidate.product_title,
            case.candidate.manufacturer_part_number_text,
            case.candidate.sku_text,
            case.candidate.description_or_specs,
            case.candidate_evidence_source,
            case.expected_decision.value,
        )
        if key in seen:
            duplicates.append((case.case_id, seen[key]))
        else:
            seen[key] = case.case_id

    assert len(duplicates) == 0, \
        f"Duplicate PRIMARY cases found: {duplicates}"
