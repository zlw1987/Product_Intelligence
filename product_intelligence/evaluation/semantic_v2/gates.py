"""The fail-closed qualification decision (Q3-A).

Hard safety gates are MANDATORY and not configurable: a failure of any
one is NOT_QUALIFIED no matter how high the aggregate accuracy is, and
it stays visible in the report. Configurable semantic thresholds come
from the (DRAFT, unapproved) policy artifact; without an APPROVED
policy the decision is POLICY_PENDING, never QUALIFIED (PASS).

Bounded decision vocabulary (per provider/model):

* FAIL_CLOSED — the evaluation is void (contract / corpus / capture
  binding mismatch; nothing is scored);
* NOT_QUALIFIED — a hard safety gate failed (visible even when the
  policy is pending and even with high aggregate accuracy);
* POLICY_PENDING — no APPROVED applicable qualification policy exists
  (the DRAFT policy's thresholds are reported, never acted upon);
* INCOMPLETE_COVERAGE — not every eligible semantic case produced an
  accepted, parser-valid response (missing captures, runtime
  failures, integrity failures, contract violations);
* THRESHOLD_INDETERMINATE — an approved policy's threshold has an
  insufficient denominator (reported unavailable, never satisfied by
  default);
* BELOW_THRESHOLD — an approved policy's threshold is missed;
* QUALIFIED — (PASS) an approved policy's thresholds all met and every
  safety gate passed. Unreachable in Q3-A (the policy is DRAFT).

Decision precedence keeps the most severe finding visible first:
safety > policy approval > coverage > thresholds. Coverage and policy
facts are always carried in the rationale regardless of the decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from product_intelligence.research import (
    AUTHORITY_CONTRACT_VERSION_V2_FU3,
    V2_CONTRACT_BINDING,
)
from product_intelligence.evaluation.semantic_v2.corpus import (
    KNOWN_PRODUCTION_BINDINGS,
)
from product_intelligence.evaluation.semantic_v2.evaluator import (
    EvaluationResult,
)
from product_intelligence.evaluation.semantic_v2.policy import (
    PolicyDocument,
    policy_applies_to,
)

__all__ = [
    "DECISIONS",
    "HARD_SAFETY_GATES",
    "GateResult",
    "evaluate_safety_gates",
    "decide",
]

DECISIONS: Final[frozenset[str]] = frozenset(
    {
        "FAIL_CLOSED",
        "NOT_QUALIFIED",
        "INCOMPLETE_COVERAGE",
        "THRESHOLD_INDETERMINATE",
        "BELOW_THRESHOLD",
        "POLICY_PENDING",
        "QUALIFIED",
    }
)

HARD_SAFETY_GATES: Final[tuple[str, ...]] = (
    "zero_false_match_on_always_hard_conflicts",
    "zero_false_match_on_packaging_quantity_conflicts",
    "zero_false_match_on_accessory_product_role_conflicts",
    "zero_schema_bypass_acceptance",
    "zero_unauthorized_authority_promotion",
    "zero_customer_alias_authority_promotion",
    "zero_contract_version_mismatch",
    "zero_missing_required_evaluation_silent_pass",
)

#: The conflict-class sets the packaging / accessory gates watch.
_PACKAGING = frozenset({"PACKAGING_QUANTITY", "BUNDLE"})
_ACCESSORY = frozenset({"ACCESSORY_RELATION", "PRODUCT_ROLE"})
_ALWAYS_HARD = frozenset(
    {
        "MPN_IDENTITY",
        "PRODUCT_FAMILY",
        "GENERATION",
        "CAPACITY",
        "INTERFACE",
        "FORM_FACTOR",
        "PRODUCT_ROLE",
        "ACCESSORY_RELATION",
        "PACKAGING_QUANTITY",
        "BUNDLE",
    }
)


@dataclass(frozen=True)
class GateResult:
    name: str
    passed: bool
    detail: str
    failing_case_ids: tuple[str, ...] = ()

    def to_report_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "detail": self.detail,
            "failing_case_ids": list(self.failing_case_ids),
        }


def _false_matches(result: EvaluationResult) -> list:
    return [
        o for o in result.outcomes if o.verdict == "FALSE_MATCH"
    ]


def evaluate_safety_gates(result: EvaluationResult) -> dict[str, GateResult]:
    """The mandatory hard safety conditions, computed deterministically
    from the per-case outcomes (never from aggregate accuracy)."""
    false_match = _false_matches(result)

    hard = [
        o
        for o in false_match
        if set(o.expected_conflict_classes) & _ALWAYS_HARD
    ]
    packaging = [
        o
        for o in false_match
        if set(o.expected_conflict_classes) & _PACKAGING
    ]
    accessory = [
        o
        for o in false_match
        if set(o.expected_conflict_classes) & _ACCESSORY
    ]
    bypass = [
        o
        for o in result.outcomes
        if o.state in ("CONTRACT_VIOLATION", "CAPTURE_INTEGRITY_FAILURE")
    ]
    authority = [
        o
        for o in result.outcomes
        if "UNAUTHORIZED_AUTHORITY_CLAIM" in o.notes
    ]
    alias = [
        o
        for o in result.outcomes
        if "CUSTOMER_ALIAS_PROMOTION" in o.notes
    ]

    # Contract-version mismatch: structurally verified at load/verify
    # time (the evaluation would be void before scoring); the gate
    # re-states the binding agreement against the known production
    # bindings (no literal copy: drift-pinned to the research export
    # and the semantic layer's 2.1 owner). Q3-B5-P1: in the 2.0
    # context the gate pins the frozen 2.0 production binding (the
    # detail text is byte-identical to the pre-2.1 gate); in the 2.1
    # context it pins the separately versioned 2.1 production binding
    # (the separately versioned FU3 authority token) - the only
    # allowed delta. The eight gate names and their fail-closed
    # semantics are unchanged.
    binding_key = tuple(result.semantic_contract_binding)
    binding_ok = binding_key in KNOWN_PRODUCTION_BINDINGS
    if binding_key == tuple(V2_CONTRACT_BINDING):
        binding_detail = "corpus binds to the exact frozen production contract"
    elif binding_key in KNOWN_PRODUCTION_BINDINGS:
        binding_detail = (
            f"corpus binds to the exact 2.1 production contract "
            f"(prompt {result.semantic_contract_binding[1]}, "
            f"authority {AUTHORITY_CONTRACT_VERSION_V2_FU3})"
        )
    else:
        binding_detail = (
            f"corpus binding {list(binding_key)!r} is not one of the "
            f"known production bindings"
        )

    # Every corpus case has exactly one outcome with an explicit
    # state; nothing is silently dropped.
    states = {o.state for o in result.outcomes}
    explicit = all(
        o.verdict is not None and o.case_id for o in result.outcomes
    )
    completeness_ok = explicit and not (states - {
        "EVALUATED",
        "NOT_CAPTURED",
        "NOT_INVOKED",
        "RUNTIME_FAILURE",
        "CAPTURE_INTEGRITY_FAILURE",
        "CONTRACT_REJECTED_OK",
        "CONTRACT_VIOLATION",
    })

    gates: dict[str, GateResult] = {}
    gates[HARD_SAFETY_GATES[0]] = GateResult(
        name=HARD_SAFETY_GATES[0],
        passed=not hard,
        detail=(
            "zero false MATCH on independently established "
            "ALWAYS_HARD conflict cases"
        ),
        failing_case_ids=tuple(o.case_id for o in hard),
    )
    gates[HARD_SAFETY_GATES[1]] = GateResult(
        name=HARD_SAFETY_GATES[1],
        passed=not packaging,
        detail=(
            "zero false MATCH on known packaging-quantity / bundle "
            "conflict cases"
        ),
        failing_case_ids=tuple(o.case_id for o in packaging),
    )
    gates[HARD_SAFETY_GATES[2]] = GateResult(
        name=HARD_SAFETY_GATES[2],
        passed=not accessory,
        detail=(
            "zero false MATCH on known accessory / product-role "
            "conflict cases"
        ),
        failing_case_ids=tuple(o.case_id for o in accessory),
    )
    gates[HARD_SAFETY_GATES[3]] = GateResult(
        name=HARD_SAFETY_GATES[3],
        passed=not bypass,
        detail=(
            "zero schema-bypass acceptance (no ineligible payload "
            "evaluated, no tampered capture accepted)"
        ),
        failing_case_ids=tuple(o.case_id for o in bypass),
    )
    gates[HARD_SAFETY_GATES[4]] = GateResult(
        name=HARD_SAFETY_GATES[4],
        passed=not authority,
        detail=(
            "zero unauthorized authority promotion (no response "
            "claims reviewed manufacturer relationship authority the "
            "input did not label)"
        ),
        failing_case_ids=tuple(o.case_id for o in authority),
    )
    gates[HARD_SAFETY_GATES[5]] = GateResult(
        name=HARD_SAFETY_GATES[5],
        passed=not alias,
        detail=(
            "zero customer-retrieval-alias promotion to manufacturer "
            "relationship authority"
        ),
        failing_case_ids=tuple(o.case_id for o in alias),
    )
    gates[HARD_SAFETY_GATES[6]] = GateResult(
        name=HARD_SAFETY_GATES[6],
        passed=binding_ok,
        detail=binding_detail,
    )
    gates[HARD_SAFETY_GATES[7]] = GateResult(
        name=HARD_SAFETY_GATES[7],
        passed=completeness_ok,
        detail=(
            "every corpus case carries exactly one explicit outcome "
            "(no missing required evaluation silently treated as PASS)"
        ),
    )
    return gates


def decide(
    result: EvaluationResult,
    gates: dict[str, GateResult],
    policy: PolicyDocument | None,
    threshold_evaluation: dict[str, Any] | None,
) -> tuple[str, tuple[str, ...]]:
    """The fail-closed qualification decision for one model."""
    rationale: list[str] = []

    failed = [name for name, g in gates.items() if not g.passed]
    if failed:
        rationale.extend(f"SAFETY_GATE_FAILED:{name}" for name in failed)
        # The coverage / policy facts stay visible either way.
        _append_coverage_rationale(result, rationale)
        _append_policy_rationale(result, policy, rationale)
        return "NOT_QUALIFIED", tuple(rationale)

    _append_coverage_rationale(result, rationale)

    if policy is None or not policy_applies_to(
        policy, result.corpus_id, result.corpus_version
    ):
        rationale.append("POLICY_PENDING:no approved applicable policy")
        return "POLICY_PENDING", tuple(rationale)
    if not policy.approved:
        rationale.append(
            f"POLICY_PENDING:policy {policy.policy_version} is "
            f"{policy.status}, not approved"
        )
        return "POLICY_PENDING", tuple(rationale)

    counts = result.metrics["counts"]
    if (
        counts["not_captured"]
        or counts["not_invoked"]
        or counts["runtime_failure_count"]
        or counts["capture_integrity_failures"]
        or counts["contract_violations"]
    ):
        return "INCOMPLETE_COVERAGE", tuple(rationale)

    assert threshold_evaluation is not None
    unmet = [
        name
        for name, entry in threshold_evaluation.items()
        if entry["met"] is False
    ]
    if unmet:
        rationale.extend(f"THRESHOLD_MISSED:{name}" for name in unmet)
        return "BELOW_THRESHOLD", tuple(rationale)
    indeterminate = [
        name
        for name, entry in threshold_evaluation.items()
        if entry["met"] is None
    ]
    if indeterminate:
        rationale.extend(
            f"THRESHOLD_INDETERMINATE:{name}" for name in indeterminate
        )
        return "THRESHOLD_INDETERMINATE", tuple(rationale)

    return "QUALIFIED", tuple(["ALL_SAFETY_GATES_PASSED", "ALL_THRESHOLDS_MET"])


def _append_coverage_rationale(
    result: EvaluationResult, rationale: list[str]
) -> None:
    counts = result.metrics["counts"]
    rationale.append(
        "COVERAGE:"
        f"not_captured={counts['not_captured']},"
        f"not_invoked={counts['not_invoked']},"
        f"runtime_failures={counts['runtime_failure_count']},"
        f"capture_integrity_failures={counts['capture_integrity_failures']},"
        f"contract_violations={counts['contract_violations']}"
    )


def _append_policy_rationale(
    result: EvaluationResult,
    policy: PolicyDocument | None,
    rationale: list[str],
) -> None:
    if policy is None or not policy_applies_to(
        policy, result.corpus_id, result.corpus_version
    ) or not policy.approved:
        status = (
            policy.status if policy is not None else "ABSENT"
        )
        rationale.append(f"POLICY:{status}")
