"""The offline Semantic V2 qualification evaluator (Q3-A).

Deterministic, zero-network, zero-AI: it evaluates PREVIOUSLY CAPTURED
model responses against the frozen, independently labeled corpus using
the REAL production V2 parser (``parse_semantic_response_v2`` +
``validate_semantic_response_v2``) and the REAL frozen V2 input
contract (case reconstruction through ``SemanticMatchCaseV2``). It
never calls a model, never manufactures a response for a missing case,
and never substitutes an expected answer for an invalid one: an invalid
captured response is a bounded failure state, not a guess.

Per-case outcome states (bounded):

* EVALUATED — an accepted attempt whose raw output re-parses through
  the production parser and scores against the independent label;
* NOT_CAPTURED — no capture record (coverage shortfall, never a pass);
* RUNTIME_FAILURE — the accepted attempt is an execution failure
  (bounded status; preserved separately from semantic decisions);
* CAPTURE_INTEGRITY_FAILURE — the capture claims OK but the raw output
  does not survive the production parser (tamper / bypass; fail
  closed, never re-scored);
* CONTRACT_REJECTED_OK — a contract-negative case rejected by the
  frozen input contract with its expected class;
* CONTRACT_VIOLATION — a case whose behavior disagrees with the frozen
  contract (a semantic payload that will not construct, or a
  contract-negative payload that does, or a wrong rejection class).

Scoring is decision-level against the independent label; severity is
computed from the label's conflict classes and flags — never from
model confidence.

This module imports the frozen research contract (authorized by the
Q3-A exact-allowlist exception in
``tests/research/test_research_identity_boundaries.py``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Final

from product_intelligence.research import (
    ALWAYS_HARD_CONFLICT_CLASSES,
    ConflictClass,
    V2SemanticDecision,
)
from product_intelligence.research.semantic_v2 import (
    SemanticMatchResponseV2,
    SemanticReasonCodeV2,
    SemanticV2ParseError,
    parse_semantic_response_v2,
    validate_semantic_response_v2,
)
from product_intelligence.evaluation.semantic_v2.capture import (
    CAPTURE_MODE,
    CaptureDocument,
    CaptureRecord,
    FALLBACK_ROUTE,
    PRIMARY_ROUTE,
)
from product_intelligence.evaluation.semantic_v2.direct_capture import (
    DIRECT_CAPTURE_MODE,
    DirectCaptureDocument,
    verify_direct_capture_against_corpus,
)
from product_intelligence.evaluation.semantic_v2.corpus import (
    AMBIGUOUS_CASE_CLASS,
    AUTHORITATIVE_CASE_CLASS,
    CONTRACT_NEGATIVE_CASE_CLASS,
    CorpusBundle,
    CorpusCase,
    CorpusInputRejectionError,
)

__all__ = [
    "OUTCOME_STATES",
    "SEVERITIES",
    "VERDICTS",
    "CaseOutcome",
    "EvaluationResult",
    "QualificationContractError",
    "classify_raw_response",
    "compute_metrics",
    "evaluate_direct_for_model",
    "evaluate_no_capture",
    "evaluate_offline",
]

OUTCOME_STATES: Final[frozenset[str]] = frozenset(
    {
        "EVALUATED",
        "NOT_CAPTURED",
        "NOT_INVOKED",
        "RUNTIME_FAILURE",
        "CAPTURE_INTEGRITY_FAILURE",
        "CONTRACT_REJECTED_OK",
        "CONTRACT_VIOLATION",
    }
)

VERDICTS: Final[frozenset[str]] = frozenset(
    {
        "CORRECT",
        "FALSE_MATCH",
        "FALSE_NO_MATCH",
        "ABSTAIN_ON_DEFINITE",
        "DEFENSIBLE",
        "OUTSIDE_DEFENSIBLE",
        "REJECTED_AS_EXPECTED",
        "REJECTED_VIOLATION",
        "NOT_EVALUATED",
        "RUNTIME_FAILED",
        "INTEGRITY_FAILED",
    }
)

SEVERITIES: Final[frozenset[str]] = frozenset(
    {"CRITICAL", "HIGH", "MEDIUM", "REVIEW"}
)

#: The frozen response-reason that claims reviewed manufacturer
#: relationship authority (harness cross-checks it against the input's
#: context provenance: the model may only claim what the input labeled).
_AUTHORIZED_RELATION_REASON: Final[str] = (
    SemanticReasonCodeV2.MATCH_AUTHORIZED_IDENTIFIER_RELATION.value
)

_PACKAGING_CLASSES: Final[frozenset[str]] = frozenset(
    {
        ConflictClass.PACKAGING_QUANTITY.value,
        ConflictClass.BUNDLE.value,
    }
)
_ACCESSORY_CLASSES: Final[frozenset[str]] = frozenset(
    {
        ConflictClass.ACCESSORY_RELATION.value,
        ConflictClass.PRODUCT_ROLE.value,
    }
)


class QualificationContractError(Exception):
    """The evaluation is VOID: the corpus or capture does not bind to
    the exact frozen contract / corpus identity. No metrics, no
    decision — fail closed."""


# ---------------------------------------------------------------------------
# Production parser fidelity (the real V2 parser, nothing recreated)
# ---------------------------------------------------------------------------


def classify_raw_response(
    raw_output: str,
) -> tuple[SemanticMatchResponseV2 | None, str | None]:
    """Classify one raw model output through the PRODUCTION V2 parser.

    Returns ``(validated_response, None)`` when the output is the exact
    strict structured V2 response; ``(None, "MALFORMED_JSON")`` when the
    production parser rejects the shape; ``(None, "SCHEMA_INVALID")``
    when the parsed output fails the frozen vocabulary / coherence
    rules. This is the same composition the production runtime's
    boundary uses (parse, then validate) — no approximation.
    """
    try:
        parsed = parse_semantic_response_v2(raw_output)
    except SemanticV2ParseError:
        return None, "MALFORMED_JSON"
    try:
        return validate_semantic_response_v2(parsed), None
    except (SemanticV2ParseError, ValueError, TypeError):
        return None, "SCHEMA_INVALID"


# ---------------------------------------------------------------------------
# Per-case outcomes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CaseOutcome:
    case_id: str
    case_class: str
    category: str
    substate: str
    primary_signal: str
    state: str
    verdict: str
    severity: str | None
    model_decision: str | None
    model_confidence: str | None
    model_reason_code: str | None
    model_conflict_classes: tuple[str, ...]
    expected_decision: str | None
    acceptable_decisions: tuple[str, ...] | None
    expected_conflict_classes: tuple[str, ...]
    runtime_failure_status: str | None
    provenance_role: str | None
    commercial_sales_unit_safety: bool
    notes: tuple[str, ...]

    def to_report_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "case_class": self.case_class,
            "category": self.category,
            "substate": self.substate,
            "primary_signal": self.primary_signal,
            "state": self.state,
            "verdict": self.verdict,
            "severity": self.severity,
            "model_decision": self.model_decision,
            "model_confidence": self.model_confidence,
            "model_reason_code": self.model_reason_code,
            "model_conflict_classes": list(self.model_conflict_classes),
            "expected_decision": self.expected_decision,
            "acceptable_decisions": (
                list(self.acceptable_decisions)
                if self.acceptable_decisions is not None
                else None
            ),
            "expected_conflict_classes": list(self.expected_conflict_classes),
            "runtime_failure_status": self.runtime_failure_status,
            "provenance_role": self.provenance_role,
            "commercial_sales_unit_safety": self.commercial_sales_unit_safety,
            "notes": list(self.notes),
        }


def _base_outcome(case: CorpusCase) -> CaseOutcome:
    return CaseOutcome(
        case_id=case.case_id,
        case_class=case.case_class,
        category=case.category,
        substate=case.substate,
        primary_signal=case.primary_signal,
        state="NOT_CAPTURED",
        verdict="NOT_EVALUATED",
        severity=None,
        model_decision=None,
        model_confidence=None,
        model_reason_code=None,
        model_conflict_classes=(),
        expected_decision=case.expected.get("decision"),
        acceptable_decisions=case.acceptable_decisions,
        expected_conflict_classes=tuple(
            sorted(case.expected_conflict_classes)
        ),
        runtime_failure_status=None,
        provenance_role=None,
        commercial_sales_unit_safety=case.expected.get(
            "commercial_sales_unit_safety", False
        ),
        notes=(),
    )


def _contract_negative_outcome(
    case: CorpusCase, rejection: str | None
) -> CaseOutcome:
    base = _base_outcome(case)
    expected_rejection = case.expected.get("rejection_class")
    if rejection is None:
        return CaseOutcome(
            **{
                **base.__dict__,
                "state": "CONTRACT_VIOLATION",
                "verdict": "REJECTED_VIOLATION",
                "severity": "CRITICAL",
                "notes": (
                    (
                        "the frozen V2 input contract accepted a "
                        "contract-negative payload; the semantic "
                        "execution path must fail closed here"
                    ),
                ),
            }
        )
    if rejection != expected_rejection:
        return CaseOutcome(
            **{
                **base.__dict__,
                "state": "CONTRACT_VIOLATION",
                "verdict": "REJECTED_VIOLATION",
                "severity": "CRITICAL",
                "notes": (
                    (
                        f"rejection class {rejection!r} disagrees with "
                        f"the expected {expected_rejection!r} (corpus "
                        "defect; fail closed)"
                    ),
                ),
            }
        )
    return CaseOutcome(
        **{
            **base.__dict__,
            "state": "CONTRACT_REJECTED_OK",
            "verdict": "REJECTED_AS_EXPECTED",
        }
    )


def _score_semantic(
    case: CorpusCase,
    case_obj: Any,
    response: SemanticMatchResponseV2,
    fallback_used: bool,
    provenance_role: str,
) -> CaseOutcome:
    base = _base_outcome(case)
    model_decision = response.decision.value
    notes: list[str] = []
    if fallback_used and provenance_role == "FALLBACK":
        notes.append("FALLBACK_ACCEPTED")

    # Harness coherence check the input-aware contract applies: the
    # model may only claim reviewed relationship authority when the
    # recorded input actually labeled it. (The production parser is
    # input-blind; the harness is not.)
    if response.reason_code.value == _AUTHORIZED_RELATION_REASON:
        provenances = {p.value for p in case_obj.context_provenances}
        if "MANUFACTURER_RELATION_AUTHORITY" not in provenances:
            notes.append("UNAUTHORIZED_AUTHORITY_CLAIM")
            if "CUSTOMER_RETRIEVAL_RELATION" in provenances:
                notes.append("CUSTOMER_ALIAS_PROMOTION")

    expected = case.expected
    if case.case_class == AUTHORITATIVE_CASE_CLASS:
        exp = expected["decision"]
        hard_expected = case.expected_hard_conflict_classes
        if model_decision == exp:
            verdict, severity = "CORRECT", None
        elif model_decision == V2SemanticDecision.MATCH.value:
            verdict = "FALSE_MATCH"
            if exp == V2SemanticDecision.NO_MATCH.value and hard_expected:
                severity = "CRITICAL"
            elif expected["commercial_sales_unit_safety"]:
                severity = "CRITICAL"
            elif exp == V2SemanticDecision.NO_MATCH.value:
                severity = "HIGH"
            else:  # expected UNCERTAIN
                severity = "HIGH"
        elif model_decision == V2SemanticDecision.NO_MATCH.value:
            verdict = "FALSE_NO_MATCH"
            severity = (
                "MEDIUM"
                if exp == V2SemanticDecision.MATCH.value
                else "REVIEW"
            )
        else:  # model UNCERTAIN, definite expectation
            verdict, severity = "ABSTAIN_ON_DEFINITE", "REVIEW"
    else:  # AMBIGUOUS: defensible set, never a hard error
        acceptable = tuple(expected["acceptable_decisions"])
        if model_decision in acceptable:
            verdict, severity = "DEFENSIBLE", None
        else:
            verdict = "OUTSIDE_DEFENSIBLE"
            severity = (
                "HIGH"
                if model_decision == V2SemanticDecision.MATCH.value
                else "REVIEW"
            )

    return CaseOutcome(
        **{
            **base.__dict__,
            "state": "EVALUATED",
            "verdict": verdict,
            "severity": severity,
            "model_decision": model_decision,
            "model_confidence": response.confidence.value,
            "model_reason_code": response.reason_code.value,
            "model_conflict_classes": tuple(
                sorted(c.value for c in response.conflict_classes)
            ),
            "provenance_role": provenance_role,
            "notes": tuple(notes),
        }
    )


# ---------------------------------------------------------------------------
# The offline evaluation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvaluationResult:
    """One model's offline evaluation against the exact corpus."""

    provider: str
    model: str
    route_role: str
    corpus_id: str
    corpus_version: str
    corpus_digest: str
    semantic_contract_binding: tuple[str, str, int, int, str]
    capture_run_id: str | None
    captured_at: str | None
    captured_by: str | None
    capture_notes: str | None
    outcomes: tuple[CaseOutcome, ...]
    metrics: dict[str, Any] = field(compare=True, default_factory=dict)
    #: The capture mode this result was produced from (production-route
    #: evaluation stays "PRODUCTION_ROUTE"; direct-model evaluation is
    #: "DIRECT_MODEL_QUALIFICATION"). Reports identify the mode
    #: explicitly and the two modes' coverage denominators are never
    #: mixed.
    capture_mode: str = CAPTURE_MODE


def _model_view(
    record: CaptureRecord, target_route: tuple[str, str]
) -> tuple[str, Any, str | None]:
    """Project one record onto one model's qualification view.

    Returns ``(kind, accepted_attempt, runtime_status)`` where kind is
    EVALUATE / NOT_INVOKED / RUNTIME_FAILURE:

    * target PRIMARY: the primary attempt is the primary's answer when
      OK; otherwise the primary failed (the fallback answer, if any,
      belongs to the fallback model - never to the primary's
      qualification);
    * target FALLBACK: a successful primary finalizes the case BEFORE
      the fallback is invoked (not invoked - no data, not a failure);
      otherwise the fallback attempt, if OK, is the fallback's answer.
    """
    if target_route == PRIMARY_ROUTE:
        if record.attempts[0].status == "OK":
            return "EVALUATE", record.attempts[0], None
        return "RUNTIME_FAILURE", None, record.attempts[0].status
    if record.attempts[0].status == "OK":
        return "NOT_INVOKED", None, None
    if len(record.attempts) == 2 and record.attempts[1].status == "OK":
        return "EVALUATE", record.attempts[1], None
    return "RUNTIME_FAILURE", None, record.attempts[-1].status


def evaluate_for_model(
    corpus: CorpusBundle,
    capture: CaptureDocument,
    provider: str,
    model: str,
) -> EvaluationResult:
    """Evaluate one capture against one corpus for ONE pinned model
    (offline, deterministic).

    The primary and the fallback are qualified INDEPENDENTLY from the
    same run: each model's view counts only the answers that model
    itself produced (see ``_model_view``).

    Raises ``QualificationContractError`` when the capture does not
    bind to the exact corpus / frozen contract (the evaluation is void;
    never best-effort) - including the cross-mode presentation of a
    direct-model capture document (refused, never reinterpreted).
    """
    from product_intelligence.evaluation.semantic_v2.capture import (
        verify_capture_against_corpus,
    )

    if not isinstance(capture, CaptureDocument):
        raise QualificationContractError(
            "a direct-model capture document was presented to the "
            "production-route evaluator; the two capture modes are "
            "separate typed schemas and are never reinterpreted across "
            "modes"
        )

    if (provider, model) not in (PRIMARY_ROUTE, FALLBACK_ROUTE):
        raise QualificationContractError(
            f"model {provider!r}/{model!r} is not one of the frozen V2 "
            f"pinned routes {PRIMARY_ROUTE!r} / {FALLBACK_ROUTE!r}; no "
            "qualification view is produced for an unpinned identity"
        )
    role = "PRIMARY" if (provider, model) == PRIMARY_ROUTE else "FALLBACK"

    try:
        verify_capture_against_corpus(capture, corpus)
    except Exception as exc:
        raise QualificationContractError(str(exc)) from exc

    records_by_case = {record.case_id: record for record in capture.records}
    outcomes: list[CaseOutcome] = []
    for case in sorted(corpus.cases, key=lambda c: c.case_id):
        if case.case_class == CONTRACT_NEGATIVE_CASE_CLASS:
            try:
                case.build_semantic_case()
            except CorpusInputRejectionError as exc:
                outcomes.append(_contract_negative_outcome(case, exc.rejection_class))
            else:
                outcomes.append(_contract_negative_outcome(case, None))
            continue

        # A semantic corpus case must reconstruct (corpus defect
        # otherwise - fail closed, never evaluated as a model answer).
        try:
            case_obj = case.build_semantic_case()
        except CorpusInputRejectionError as exc:
            base = _base_outcome(case)
            outcomes.append(
                CaseOutcome(
                    **{
                        **base.__dict__,
                        "state": "CONTRACT_VIOLATION",
                        "verdict": "REJECTED_VIOLATION",
                        "severity": "CRITICAL",
                        "notes": (
                            (
                                f"a semantic corpus case failed the "
                                f"frozen input contract "
                                f"[{exc.rejection_class}]: {exc.detail} "
                                "(corpus defect; fail closed)"
                            ),
                        ),
                    }
                )
            )
            continue

        record = records_by_case.get(case.case_id)
        if record is None:
            outcomes.append(_base_outcome(case))
            continue

        kind, accepted, failure_status = _model_view(record, (provider, model))
        base = _base_outcome(case)
        if kind == "NOT_INVOKED":
            outcomes.append(
                CaseOutcome(
                    **{
                        **base.__dict__,
                        "state": "NOT_INVOKED",
                        "verdict": "NOT_EVALUATED",
                        "notes": (
                            (
                                "the primary answer was final before the "
                                "fallback was invoked; this model has no "
                                "data for the case (not a failure, not "
                                "a pass)"
                            ),
                        ),
                    }
                )
            )
            continue
        if kind == "RUNTIME_FAILURE":
            outcomes.append(
                CaseOutcome(
                    **{
                        **base.__dict__,
                        "state": "RUNTIME_FAILURE",
                        "verdict": "RUNTIME_FAILED",
                        "runtime_failure_status": failure_status,
                        "provenance_role": role,
                        "notes": (
                            (
                                "the model's attempt is an execution "
                                "failure; preserved separately from any "
                                "semantic decision (never NO_MATCH, "
                                "never a pass)"
                            ),
                        ),
                    }
                )
            )
            continue

        response, failure = classify_raw_response(accepted.raw_output or "")
        if response is None:
            outcomes.append(
                CaseOutcome(
                    **{
                        **base.__dict__,
                        "state": "CAPTURE_INTEGRITY_FAILURE",
                        "verdict": "INTEGRITY_FAILED",
                        "severity": "CRITICAL",
                        "runtime_failure_status": failure,
                        "notes": (
                            (
                                f"the capture claims an OK attempt for "
                                f"this model but its raw output does "
                                f"not survive the production V2 parser "
                                f"({failure}); the response is NOT "
                                "accepted and NOT substituted with the "
                                "expected answer"
                            ),
                        ),
                    }
                )
            )
            continue

        outcomes.append(
            _score_semantic(
                case, case_obj, response, record.fallback_used, provenance_role=role
            )
        )

    outcomes = tuple(outcomes)
    return EvaluationResult(
        provider=provider,
        model=model,
        route_role=role,
        corpus_id=corpus.corpus_id,
        corpus_version=corpus.corpus_version,
        corpus_digest=corpus.corpus_digest,
        semantic_contract_binding=corpus.semantic_contract_binding,
        capture_run_id=capture.capture_run_id or None,
        captured_at=capture.captured_at,
        captured_by=capture.captured_by or None,
        capture_notes=capture.notes or None,
        outcomes=outcomes,
        metrics=compute_metrics(outcomes),
    )


#: Backward-compatible name for the primary model's view.
def evaluate_offline(
    corpus: CorpusBundle,
    capture: CaptureDocument,
    provider: str,
    model: str,
) -> EvaluationResult:
    return evaluate_for_model(corpus, capture, provider, model)


def evaluate_no_capture(
    corpus: CorpusBundle, provider: str, model: str
) -> EvaluationResult:
    """The explicit no-capture baseline: every eligible semantic case is
    NOT_CAPTURED (never a pass, never a fabricated response); contract-
    negative cases are still evaluated for rejection correctness. The
    capture identity fields are None in the resulting report."""
    from product_intelligence.evaluation.semantic_v2.capture import (
        FALLBACK_ROUTE,
        PRIMARY_ROUTE,
    )

    route = (provider, model)
    if route not in (PRIMARY_ROUTE, FALLBACK_ROUTE):
        raise QualificationContractError(
            f"model {provider!r}/{model!r} is not one of the frozen V2 "
            f"pinned routes; no qualification baseline is produced for "
            "an unqualified identity"
        )
    role = "PRIMARY" if route == PRIMARY_ROUTE else "FALLBACK"
    outcomes: list[CaseOutcome] = []
    for case in sorted(corpus.cases, key=lambda c: c.case_id):
        if case.case_class == CONTRACT_NEGATIVE_CASE_CLASS:
            try:
                case.build_semantic_case()
            except CorpusInputRejectionError as exc:
                outcomes.append(_contract_negative_outcome(case, exc.rejection_class))
            else:
                outcomes.append(_contract_negative_outcome(case, None))
        else:
            outcomes.append(_base_outcome(case))
    outcomes = tuple(outcomes)
    return EvaluationResult(
        provider=provider,
        model=model,
        route_role=role,
        corpus_id=corpus.corpus_id,
        corpus_version=corpus.corpus_version,
        corpus_digest=corpus.corpus_digest,
        semantic_contract_binding=corpus.semantic_contract_binding,
        capture_run_id=None,
        captured_at=None,
        captured_by=None,
        capture_notes=None,
        outcomes=outcomes,
        metrics=compute_metrics(outcomes),
    )


# ---------------------------------------------------------------------------
# The independent DIRECT_MODEL_QUALIFICATION evaluation (Q3-A-FU1)
# ---------------------------------------------------------------------------


def evaluate_direct_for_model(
    corpus: CorpusBundle,
    direct_capture: DirectCaptureDocument,
    provider: str,
    model: str,
) -> EvaluationResult:
    """Evaluate one DIRECT_MODEL_QUALIFICATION capture for ONE pinned
    model (offline, deterministic).

    This is a separate evaluator path from the production-route
    evaluator: it never imports or invokes the production
    orchestration, there is no primary-before-fallback requirement and
    no fallback projection, and no NOT_INVOKED state exists. The
    capture is bound to exactly one provider/model and each eligible
    semantic case is judged on that model's own execution:

    * record with status OK whose raw output re-parses through the
      frozen production parser -> EVALUATED;
    * record with a bounded execution failure status -> RUNTIME_
      FAILURE (preserved separately, never a semantic decision);
    * no record for the case -> NOT_CAPTURED (a missing response is
      never a pass and never a fabricated answer);
    * record with status OK whose raw output does not survive the
      production parser -> CAPTURE_INTEGRITY_FAILURE (fail closed,
      never substituted with the expected answer).

    The frozen production V2 parser is REUSED unchanged
    (``classify_raw_response`` = ``parse_semantic_response_v2`` +
    ``validate_semantic_response_v2``); scoring, metrics, and gates are
    the same label-driven surface, with the capture mode recorded on
    the result so the two modes' coverage denominators are never
    mixed.

    Raises ``QualificationContractError`` on any cross-mode, model-
    identity, corpus, or contract mismatch (the evaluation is void;
    fail closed).
    """
    if not isinstance(direct_capture, DirectCaptureDocument):
        raise QualificationContractError(
            "a production-route capture document was presented to the "
            "direct-model evaluator; the two capture modes are separate "
            "typed schemas and are never reinterpreted across modes"
        )
    if (provider, model) not in (PRIMARY_ROUTE, FALLBACK_ROUTE):
        raise QualificationContractError(
            f"model {provider!r}/{model!r} is not one of the frozen V2 "
            f"pinned routes {PRIMARY_ROUTE!r} / {FALLBACK_ROUTE!r}; no "
            "direct-model qualification is produced for an unpinned "
            "identity"
        )
    if (provider, model) != (
        direct_capture.target_provider,
        direct_capture.target_model,
    ):
        raise QualificationContractError(
            f"the capture is bound to "
            f"{direct_capture.target_provider!r}/"
            f"{direct_capture.target_model!r}; direct-model responses "
            "are never transferred to a different model identity"
        )
    role = "PRIMARY" if (provider, model) == PRIMARY_ROUTE else "FALLBACK"

    try:
        verify_direct_capture_against_corpus(direct_capture, corpus)
    except Exception as exc:
        raise QualificationContractError(str(exc)) from exc

    records_by_case = {
        record.case_id: record for record in direct_capture.records
    }
    outcomes: list[CaseOutcome] = []
    for case in sorted(corpus.cases, key=lambda c: c.case_id):
        if case.case_class == CONTRACT_NEGATIVE_CASE_CLASS:
            try:
                case.build_semantic_case()
            except CorpusInputRejectionError as exc:
                outcomes.append(
                    _contract_negative_outcome(case, exc.rejection_class)
                )
            else:
                outcomes.append(_contract_negative_outcome(case, None))
            continue

        # A semantic corpus case must reconstruct (corpus defect
        # otherwise - fail closed, never evaluated as a model answer).
        try:
            case_obj = case.build_semantic_case()
        except CorpusInputRejectionError as exc:
            base = _base_outcome(case)
            outcomes.append(
                CaseOutcome(
                    **{
                        **base.__dict__,
                        "state": "CONTRACT_VIOLATION",
                        "verdict": "REJECTED_VIOLATION",
                        "severity": "CRITICAL",
                        "notes": (
                            (
                                f"a semantic corpus case failed the "
                                f"frozen input contract "
                                f"[{exc.rejection_class}]: {exc.detail} "
                                "(corpus defect; fail closed)"
                            ),
                        ),
                    }
                )
            )
            continue

        record = records_by_case.get(case.case_id)
        base = _base_outcome(case)
        if record is None:
            outcomes.append(
                CaseOutcome(
                    **{
                        **base.__dict__,
                        "state": "NOT_CAPTURED",
                        "verdict": "NOT_EVALUATED",
                        "notes": (
                            (
                                "the direct capture carries no record "
                                "for this case; a missing response is "
                                "never a pass and never a fabricated "
                                "answer"
                            ),
                        ),
                    }
                )
            )
            continue
        if record.execution_status != "OK":
            outcomes.append(
                CaseOutcome(
                    **{
                        **base.__dict__,
                        "state": "RUNTIME_FAILURE",
                        "verdict": "RUNTIME_FAILED",
                        "runtime_failure_status": record.execution_status,
                        "provenance_role": "DIRECT",
                        "notes": (
                            (
                                "the direct execution failed; preserved "
                                "separately from any semantic decision "
                                "(never NO_MATCH, never a pass)"
                            ),
                        ),
                    }
                )
            )
            continue

        response, failure = classify_raw_response(record.raw_output or "")
        if response is None:
            outcomes.append(
                CaseOutcome(
                    **{
                        **base.__dict__,
                        "state": "CAPTURE_INTEGRITY_FAILURE",
                        "verdict": "INTEGRITY_FAILED",
                        "severity": "CRITICAL",
                        "runtime_failure_status": failure,
                        "notes": (
                            (
                                "the direct capture carries an OK record "
                                "whose raw output does not survive the "
                                f"production V2 parser ({failure}); the "
                                "response is NOT accepted and NOT "
                                "substituted with the expected answer"
                            ),
                        ),
                    }
                )
            )
            continue

        outcomes.append(
            _score_semantic(
                case,
                case_obj,
                response,
                fallback_used=False,
                provenance_role="DIRECT",
            )
        )

    outcomes = tuple(outcomes)
    return EvaluationResult(
        provider=provider,
        model=model,
        route_role=role,
        corpus_id=corpus.corpus_id,
        corpus_version=corpus.corpus_version,
        corpus_digest=corpus.corpus_digest,
        semantic_contract_binding=corpus.semantic_contract_binding,
        capture_run_id=direct_capture.capture_run_id or None,
        captured_at=direct_capture.captured_at,
        captured_by=direct_capture.captured_by or None,
        capture_notes=direct_capture.notes or None,
        outcomes=outcomes,
        metrics=compute_metrics(outcomes),
        capture_mode=DIRECT_CAPTURE_MODE,
    )


# ---------------------------------------------------------------------------
# Metrics (separate per model; unavailable denominators are explicit)
# ---------------------------------------------------------------------------


def _metric(numerator: int | None, denominator: int) -> dict[str, Any]:
    """One ratio metric. The value is an exact 6-decimal string (the
    float-free identity discipline: numerators/denominators are the
    integers; the string is the canonical decimal rendering). A zero
    denominator is reported unavailable, never 0 or 1."""
    if denominator <= 0 or numerator is None:
        return {
            "numerator": None,
            "denominator": denominator,
            "value": None,
            "status": "unavailable",
        }
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": f"{numerator / denominator:.6f}",
        "status": "computed",
    }


def _sliced(
    outcomes: tuple[CaseOutcome, ...],
    predicate,
) -> list[CaseOutcome]:
    return [o for o in outcomes if predicate(o)]


def compute_metrics(
    outcomes: tuple[CaseOutcome, ...],
) -> dict[str, Any]:
    """The separate semantic-accuracy / safety metric surface.

    Hard accuracy metrics run over AUTHORITATIVE evaluated cases only;
    ambiguous cases are reported separately (visible, never forced);
    contract-negative cases are reported separately (rejection
    correctness, never semantic accuracy). Runtime / parser failures
    are never hidden inside aggregate accuracy.
    """
    auth = _sliced(outcomes, lambda o: o.case_class == AUTHORITATIVE_CASE_CLASS)
    auth_eval = _sliced(auth, lambda o: o.state == "EVALUATED")
    amb = _sliced(outcomes, lambda o: o.case_class == AMBIGUOUS_CASE_CLASS)
    amb_eval = _sliced(amb, lambda o: o.state == "EVALUATED")
    cn = _sliced(
        outcomes, lambda o: o.case_class == CONTRACT_NEGATIVE_CASE_CLASS
    )

    def model_is(o: CaseOutcome, d: str) -> bool:
        return o.model_decision == d

    def expected_is(o: CaseOutcome, d: str) -> bool:
        return o.expected_decision == d

    tp_match = _sliced(
        auth_eval, lambda o: model_is(o, "MATCH") and expected_is(o, "MATCH")
    )
    model_match = _sliced(auth_eval, lambda o: model_is(o, "MATCH"))
    expected_match = _sliced(auth_eval, lambda o: expected_is(o, "MATCH"))
    false_match = _sliced(
        auth_eval, lambda o: o.verdict == "FALSE_MATCH"
    )
    false_no_match = _sliced(
        auth_eval, lambda o: o.verdict == "FALSE_NO_MATCH"
    )
    model_no_match_expected = _sliced(
        auth_eval, lambda o: model_is(o, "NO_MATCH") and expected_is(o, "NO_MATCH")
    )
    expected_no_match = _sliced(auth_eval, lambda o: expected_is(o, "NO_MATCH"))
    model_uncertain = _sliced(auth_eval, lambda o: model_is(o, "UNCERTAIN"))

    hard_false_match = [
        o
        for o in false_match
        if expected_is(o, "NO_MATCH") and o.expected_conflict_classes
        and _expected_hard(o)
    ]
    packaging_false_match = [
        o
        for o in false_match
        if set(o.expected_conflict_classes) & _PACKAGING_CLASSES
    ]
    accessory_false_match = [
        o
        for o in false_match
        if set(o.expected_conflict_classes) & _ACCESSORY_CLASSES
    ]
    near_miss_false_match = [
        o for o in false_match if o.substate == "U5_NEAR_MISS_MPN"
    ]
    sales_unit_false_match = [
        o for o in false_match if o.commercial_sales_unit_safety
    ]

    captured = _sliced(outcomes, lambda o: o.case_class != CONTRACT_NEGATIVE_CASE_CLASS)
    evaluated_all = _sliced(captured, lambda o: o.state == "EVALUATED")
    not_invoked = _sliced(captured, lambda o: o.state == "NOT_INVOKED")
    answered_or_failed = _sliced(
        captured,
        lambda o: o.state
        in (
            "EVALUATED",
            "RUNTIME_FAILURE",
            "CAPTURE_INTEGRITY_FAILURE",
            "NOT_INVOKED",
        ),
    )

    def by(key) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for o in captured:
            group = key(o)
            slot = out.setdefault(
                group,
                {
                    "total": 0,
                    "evaluated": 0,
                    "correct": 0,
                    "false_match": 0,
                    "false_no_match": 0,
                    "runtime_failure": 0,
                    "not_captured": 0,
                    "not_invoked": 0,
                },
            )
            slot["total"] += 1
            if o.state == "EVALUATED":
                slot["evaluated"] += 1
                if o.verdict in ("CORRECT", "DEFENSIBLE"):
                    slot["correct"] += 1
            if o.verdict == "FALSE_MATCH":
                slot["false_match"] += 1
            if o.verdict == "FALSE_NO_MATCH":
                slot["false_no_match"] += 1
            if o.state == "RUNTIME_FAILURE":
                slot["runtime_failure"] += 1
            if o.state == "NOT_CAPTURED":
                slot["not_captured"] += 1
            if o.state == "NOT_INVOKED":
                slot["not_invoked"] += 1
        return out

    amb_defensible = _sliced(amb_eval, lambda o: o.verdict == "DEFENSIBLE")
    amb_outside = _sliced(amb_eval, lambda o: o.verdict == "OUTSIDE_DEFENSIBLE")

    runtime_failures = _sliced(outcomes, lambda o: o.state == "RUNTIME_FAILURE")
    by_status: dict[str, int] = {}
    for o in runtime_failures:
        status = o.runtime_failure_status or "UNKNOWN"
        by_status[status] = by_status.get(status, 0) + 1

    integrity_failures = _sliced(
        outcomes, lambda o: o.state == "CAPTURE_INTEGRITY_FAILURE"
    )
    contract_violations = _sliced(
        outcomes, lambda o: o.state == "CONTRACT_VIOLATION"
    )
    cn_ok = _sliced(cn, lambda o: o.state == "CONTRACT_REJECTED_OK")
    cn_bad = _sliced(cn, lambda o: o.state == "CONTRACT_VIOLATION")

    severity_counts: dict[str, int] = {}
    for o in outcomes:
        if o.severity:
            severity_counts[o.severity] = severity_counts.get(o.severity, 0) + 1

    fallback_accepted = _sliced(
        auth_eval + amb_eval, lambda o: o.provenance_role == "FALLBACK"
    )

    return {
        "counts": {
            "total_cases": len(outcomes),
            "eligible_semantic_cases": len(captured),
            "authoritative_cases": len(auth),
            "ambiguous_cases": len(amb),
            "contract_negative_cases": len(cn),
            "captured_cases": len(answered_or_failed),
            "evaluated_cases": len(evaluated_all),
            "authoritative_evaluated": len(auth_eval),
            "ambiguous_evaluated": len(amb_eval),
            "not_captured": len(_sliced(captured, lambda o: o.state == "NOT_CAPTURED")),
            "not_invoked": len(not_invoked),
            "runtime_failure_count": len(runtime_failures),
            "runtime_failures_by_status": dict(sorted(by_status.items())),
            "capture_integrity_failures": len(integrity_failures),
            "contract_rejected_as_expected": len(cn_ok),
            "contract_violations": len(contract_violations),
            "fallback_accepted_count": len(fallback_accepted),
        },
        "valid_structured_response_rate": _metric(
            len(evaluated_all),
            len(answered_or_failed),
        ),
        "match_precision": _metric(len(tp_match), len(model_match)),
        "match_recall": _metric(len(tp_match), len(expected_match)),
        "no_match_accuracy": _metric(
            len(model_no_match_expected), len(expected_no_match)
        ),
        "uncertain_rate": _metric(len(model_uncertain), len(auth_eval)),
        "false_match_count": len(false_match),
        "false_no_match_count": len(false_no_match),
        "hard_conflict_false_match_count": len(hard_false_match),
        "packaging_false_match_count": len(packaging_false_match),
        "accessory_false_match_count": len(accessory_false_match),
        "near_miss_false_match_count": len(near_miss_false_match),
        "sales_unit_safety_false_match_count": len(sales_unit_false_match),
        "false_match_examples": [
            {
                "case_id": o.case_id,
                "category": o.category,
                "substate": o.substate,
                "expected": o.expected_decision,
                "model": o.model_decision,
                "severity": o.severity,
                "expected_conflict_classes": list(o.expected_conflict_classes),
            }
            for o in false_match
        ],
        "false_no_match_examples": [
            {
                "case_id": o.case_id,
                "expected": o.expected_decision,
                "model": o.model_decision,
                "severity": o.severity,
            }
            for o in false_no_match
        ],
        "severity_counts": {
            s: severity_counts.get(s, 0) for s in ("CRITICAL", "HIGH", "MEDIUM", "REVIEW")
        },
        "by_substate": by(lambda o: o.substate),
        "by_category": by(lambda o: o.category),
        "ambiguous": {
            "evaluated": len(amb_eval),
            "defensible": len(amb_defensible),
            "outside_defensible": len(amb_outside),
            "outside_examples": [
                {
                    "case_id": o.case_id,
                    "acceptable": list(o.acceptable_decisions or ()),
                    "model": o.model_decision,
                    "severity": o.severity,
                }
                for o in amb_outside
            ],
        },
        "contract_negative": {
            "rejected_as_expected": len(cn_ok),
            "violations": len(cn_bad),
            "violation_examples": [
                {"case_id": o.case_id, "notes": list(o.notes)} for o in cn_bad
            ],
        },
    }


def _expected_hard(o: CaseOutcome) -> bool:
    hard = {c.value for c in ALWAYS_HARD_CONFLICT_CLASSES}
    return bool(set(o.expected_conflict_classes) & hard)
