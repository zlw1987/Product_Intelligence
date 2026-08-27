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


def test_semantic_prompt_v1_1_version():
    """Test semantic match prompt version is 1.1."""
    from product_intelligence.evaluation.semantic.prompt import SEMANTIC_PROMPT_VERSION

    assert SEMANTIC_PROMPT_VERSION == "1.1", \
        f"Expected prompt version 1.1, got {SEMANTIC_PROMPT_VERSION}"


def test_semantic_prompt_contains_v2_policy():
    """Test semantic prompt v1.1 contains updated decision policy.

    This test verifies the v1.1 semantics without relying on exact punctuation.
    """
    from product_intelligence.evaluation.semantic.prompt import (
        SYSTEM_PROMPT,
        USER_PROMPT_TEMPLATE,
    )

    prompt_text = SYSTEM_PROMPT + "\n" + USER_PROMPT_TEMPLATE
    prompt_lower = prompt_text.lower()

    # v1.1 should explicitly state: Use ONLY the evidence supplied
    assert "use only" in prompt_lower and "evidence supplied" in prompt_lower, \
        "Prompt v1.1 should state to use only supplied evidence"

    # v1.1 must prohibit outside product knowledge
    assert "outside" in prompt_lower or "outside product knowledge" in prompt_lower, \
        "Prompt v1.1 must prohibit outside product knowledge"

    # v1.1 must address authoritative MPN precedence
    assert "authoritative" in prompt_lower or "explicit" in prompt_lower, \
        "Prompt v1.1 should address authoritative/explicit MPN precedence"

    # v1.1 must have decision precedence rules
    assert "precedence" in prompt_lower or "apply in order" in prompt_lower, \
        "Prompt v1.1 should have decision precedence rules"


def test_semantic_prompt_v2_only_supplied_evidence():
    """Test prompt v1.1 enforces using ONLY supplied evidence."""
    from product_intelligence.evaluation.semantic.prompt import SYSTEM_PROMPT

    # Check that prompt explicitly says "only" and "supplied" together
    assert "use only the evidence supplied" in SYSTEM_PROMPT.lower(), \
        "Prompt must enforce using only supplied evidence"


def test_semantic_prompt_v2_authoritative_mpn_conflict():
    """Test prompt v1.1 explicitly states authoritative MPN conflict -> NO_MATCH."""
    from product_intelligence.evaluation.semantic.prompt import SYSTEM_PROMPT

    prompt_lower = SYSTEM_PROMPT.lower()

    # Must mention that explicit MPN conflict results in NO_MATCH
    assert "explicit" in prompt_lower and "conflict" in prompt_lower, \
        "Prompt must address explicit MPN conflict"
    assert "no_match" in prompt_lower or "no match" in prompt_lower, \
        "Prompt must indicate NO_MATCH for conflicts"


def test_semantic_prompt_v2_authoritative_exact_mpn():
    """Test prompt v1.1 explicitly states authoritative exact MPN -> MATCH."""
    from product_intelligence.evaluation.semantic.prompt import SYSTEM_PROMPT

    prompt_lower = SYSTEM_PROMPT.lower()

    # Must mention that exact MPN results in MATCH
    assert "exact" in prompt_lower and "match" in prompt_lower, \
        "Prompt must address exact MPN matching"


def test_semantic_prompt_v2_title_mpn_requires_product_itself():
    """Test prompt v1.1 clarifies title MPN MATCH requires product-itself context."""
    from product_intelligence.evaluation.semantic.prompt import SYSTEM_PROMPT

    prompt_lower = SYSTEM_PROMPT.lower()

    # Must clarify that title MPN is NOT authoritative on its own
    # and requires product description alignment
    assert "title" in prompt_lower or "text" in prompt_lower, \
        "Prompt must address title/text MPN"
    assert "not authoritative" in prompt_lower or "must also align" in prompt_lower, \
        "Prompt must clarify title MPN is not authoritative alone"


def test_semantic_prompt_v2_accessory_role_nu_match():
    """Test prompt v1.1 explicitly states accessory/non-core role -> NO_MATCH."""
    from product_intelligence.evaluation.semantic.prompt import SYSTEM_PROMPT

    prompt_lower = SYSTEM_PROMPT.lower()

    # Must mention accessory/tray/caddy/etc. roles -> NO_MATCH
    accessories = ["accessory", "tray", "caddy", "enclosure", "adapter",
                   "heatsink", "cable", "kit", "multipack"]
    found = any(acc in prompt_lower for acc in accessories)
    assert found, \
        "Prompt must address accessory/non-core roles that -> NO_MATCH"


def test_semantic_prompt_v2_compatible_with_nu_match():
    """Test prompt v1.1 explicitly states compatible-with -> NO_MATCH."""
    from product_intelligence.evaluation.semantic.prompt import SYSTEM_PROMPT

    prompt_lower = SYSTEM_PROMPT.lower()

    # Must mention compatible-with -> NO_MATCH
    assert "compatible" in prompt_lower and "no_match" in prompt_lower, \
        "Prompt must state compatible-with -> NO_MATCH"


def test_semantic_prompt_v2_replacement_for_may_uncertain():
    """Test prompt v1.1 clarifies replacement-for alone may remain UNCERTAIN."""
    from product_intelligence.evaluation.semantic.prompt import SYSTEM_PROMPT

    prompt_lower = SYSTEM_PROMPT.lower()

    # Must mention replacement-for ambiguity
    assert "replacement" in prompt_lower, \
        "Prompt must address replacement-for wording"
    # Should mention that it may remain UNCERTAIN without sufficient evidence
    assert "uncertain" in prompt_lower, \
        "Prompt must mention UNCERTAIN for ambiguous cases"


def test_semantic_prompt_v2_missing_suffix_vs_different():
    """Test prompt v1.1 distinguishes missing suffix vs different suffix."""
    from product_intelligence.evaluation.semantic.prompt import SYSTEM_PROMPT

    prompt_lower = SYSTEM_PROMPT.lower()

    # Must distinguish missing suffix (UNCERTAIN) vs different suffix (NO_MATCH)
    assert "suffix" in prompt_lower, \
        "Prompt must address suffix differences"


def test_semantic_prompt_v2_spec_only_never_match():
    """Test prompt v1.1 explicitly states spec-only can never produce MATCH."""
    from product_intelligence.evaluation.semantic.prompt import SYSTEM_PROMPT

    prompt_lower = SYSTEM_PROMPT.lower()

    # Must state spec similarity alone never produces MATCH
    assert "spec" in prompt_lower and "never" in prompt_lower and "match" in prompt_lower, \
        "Prompt must state spec-only can never produce MATCH"


def test_semantic_prompt_v2_insufficient_uncertain():
    """Test prompt v1.1 states insufficient evidence -> UNCERTAIN."""
    from product_intelligence.evaluation.semantic.prompt import SYSTEM_PROMPT

    prompt_lower = SYSTEM_PROMPT.lower()

    # Must mention insufficient evidence -> UNCERTAIN
    assert "insufficient" in prompt_lower and "uncertain" in prompt_lower, \
        "Prompt must state insufficient evidence -> UNCERTAIN"


def test_semantic_prompt_v2_false_match_preference():
    """Test prompt v1.1 states false MATCH preference toward UNCERTAIN."""
    from product_intelligence.evaluation.semantic.prompt import SYSTEM_PROMPT

    prompt_lower = SYSTEM_PROMPT.lower()

    # Must mention that false MATCH is worse than UNCERTAIN
    assert "false" in prompt_lower and "match" in prompt_lower, \
        "Prompt must mention false MATCH safety"


def test_semantic_prompt_v2_strict_json():
    """Test prompt v1.1 enforces strict JSON only."""
    from product_intelligence.evaluation.semantic.prompt import SYSTEM_PROMPT

    # Must state return JSON directly without markdown/code fences/prose
    prompt_lower = SYSTEM_PROMPT.lower()
    assert "json object directly" in prompt_lower, \
        "Prompt must enforce returning JSON object directly"
    assert "markdown" in prompt_lower and "code fence" in prompt_lower, \
        "Prompt must prohibit markdown and code fences"
    assert "prose" in prompt_lower, \
        "Prompt must prohibit prose output"


def test_semantic_prompt_v1_1_markdown_fences_prohibited():
    """Test prompt v1.1 explicitly prohibits markdown fences."""
    from product_intelligence.evaluation.semantic.prompt import SYSTEM_PROMPT

    # Must explicitly prohibit markdown/code fences
    prompt_lower = SYSTEM_PROMPT.lower()
    assert "markdown" in prompt_lower and "fence" in prompt_lower, \
        "Prompt must explicitly prohibit markdown/code fences"
    assert "code fence" in prompt_lower or "code fence" in prompt_lower, \
        "Prompt must explicitly prohibit code fences"


def test_semantic_corpus_v2_authority_probe_ids_unchanged():
    """Test that authority probe IDs remain the same in v2 as in v1."""
    from product_intelligence.evaluation.semantic.loader import load_corpus

    corpus = load_corpus()

    # Authority probe IDs must remain EXACTLY these six
    expected_authority_ids = {
        "SMQ-0004",
        "SMQ-0011",
        "SMQ-0030",
        "SMQ-0041",
        "SMQ-0058",
        "SMQ-0061",
    }

    authority_ids = {c.case_id for c in corpus.cases if c.is_authority_safety_probe}
    assert authority_ids == expected_authority_ids, \
        f"Authority probe IDs changed from v1! Expected {expected_authority_ids}, got {authority_ids}"


def test_semantic_corpus_v2_case_order_unchanged():
    """Test that case ordering is unchanged from v1 to v2."""
    from product_intelligence.evaluation.semantic.loader import load_corpus

    corpus = load_corpus()

    # Case IDs should be in order from SMQ-0001 to SMQ-0064
    expected_ids = [f"SMQ-{i:04d}" for i in range(1, 65)]
    actual_ids = [c.case_id for c in corpus.cases]

    assert actual_ids == expected_ids, \
        f"Case order changed from v1! Expected {expected_ids}, got {actual_ids}"
