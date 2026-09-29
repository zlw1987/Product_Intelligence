"""Promotion-regression authority invariants (PRODUCT-INTEL.SEMANTIC.PROMOTION-REGRESSION).

These tests prove the A1 harness protects the frozen production authority
contracts:

1. the production SemanticRuntime route is byte-for-byte unchanged and
   rejects the challenger model (no caller-configurable override exists or
   was added);
2. the harness reuses the shared contract objects and the frozen status
   mapping (no forked parser, no forked prompt, no forked eligibility);
3. the harness's eligibility, specs-building, and single-attempt
   interpretation are locked against the frozen execution/runtime
   originals over full outcome matrices;
4. a semantic MATCH stays AI_ASSISTED_MATCH: the original deterministic
   assessment is never mutated, the frozen 4A aggregation still excludes
   it, a real production AiAssistedMatchResult can be built from the
   harness's provenance, HARD_CONFLICT is not bypassed, and no human
   confirmation or Reviewed Price authority is fabricated.

All tests are offline (fake transports). Importing the harness module must
not pull in Django, execution, or any network client.
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import (
    EvidenceDecision,
    IdentityMatchType,
)
from product_intelligence.evaluation.semantic.promotion_regression import (
    _build_case_specs,
    build_case_inputs,
    get_authorized_model_spec,
    interpret_transport_outcome,
    load_promotion_regression_corpus,
    map_semantic_disposition,
    run_promotion_regression,
    semantic_call_is_expected,
)
from product_intelligence.research.aggregation import (
    PriceAggregationExclusionReason,
    aggregate_listing_prices,
)
from product_intelligence.research.listings import (
    ExtractionMethod,
    ListingObservation,
)
from product_intelligence.research.matching import (
    assess_listing_identity,
    is_human_review_eligible_assessment,
)
from product_intelligence.research.normalization import (
    NormalizedAvailability,
    NormalizedCondition,
    NormalizedListingObservation,
)
from product_intelligence.semantic.contract import (
    SEMANTIC_PROMPT_VERSION,
    SYSTEM_PROMPT,
    RawOutputParseError,
    SemanticDecision,
    build_prompt,
    parse_raw_output,
    validate_response,
)
from product_intelligence.semantic.runtime import (
    _TRANSPORT_ERROR_TO_STATUS,
    FALLBACK_MODEL,
    FALLBACK_PROVIDER,
    PRIMARY_FALLBACK_ELIGIBLE_ERRORS,
    PRIMARY_MODEL,
    PRIMARY_PROVIDER,
    SEMANTIC_MAX_TOKENS,
    SEMANTIC_TEMPERATURE,
    SemanticAttempt,
    SemanticAttemptStatus,
    SemanticRuntime,
    SemanticRuntimeConfig,
    SemanticRuntimeConfigError,
    SemanticRuntimeResult,
    validate_runtime_config,
)
from product_intelligence.semantic.transport import (
    TransportFailure,
    TransportResult,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
NEOTRON_SPEC = get_authorized_model_spec("amax", "nemotron-3-super")
QWEN_SPEC = get_authorized_model_spec("amax", "qwen3.8-27b")
CORPUS = load_promotion_regression_corpus()
CALLED_IDS = tuple(c.case_id for c in CORPUS.cases if c.expected_semantic_call)

_VALID_MATCH = json.dumps(
    {
        "decision": "MATCH",
        "confidence": "HIGH",
        "matched_attributes": ["mpn"],
        "conflicting_attributes": [],
        "missing_critical_attributes": [],
        "reason_code": "ideal",
    }
)


def _ideal_run(spec):
    def resp(decision: str) -> str:
        payload = {
            "decision": decision,
            "confidence": "HIGH",
            "matched_attributes": [],
            "conflicting_attributes": [],
            "missing_critical_attributes": [],
            "reason_code": "ideal",
        }
        return json.dumps(payload)

    from product_intelligence.semantic.transport import FakeSemanticModelTransport

    responses = {
        c.case_id: resp(c.expected_semantic_decision)
        for c in CORPUS.cases
        if c.expected_semantic_call
    }
    transport = FakeSemanticModelTransport(
        case_ids=CALLED_IDS,
        responses=responses,
        provider_reported_model=spec.model,
    )
    return run_promotion_regression(spec, transport), transport


# ---------------------------------------------------------------------------
# 1. The production route is unchanged and rejects the challenger
# ---------------------------------------------------------------------------


class TestProductionRouteUnchanged:
    def test_primary_route_constants_are_frozen(self):
        assert PRIMARY_PROVIDER == "amax"
        assert PRIMARY_MODEL == "nemotron-3-super"

    def test_fallback_route_constants_are_frozen(self):
        assert FALLBACK_PROVIDER == "vllm-262k"
        assert FALLBACK_MODEL == "Qwen3.6-27B-262K"

    def test_generation_constants_are_frozen(self):
        assert SEMANTIC_TEMPERATURE == 0.0
        assert type(SEMANTIC_TEMPERATURE) is float
        assert SEMANTIC_MAX_TOKENS == 32768
        assert type(SEMANTIC_MAX_TOKENS) is int

    def test_production_runtime_rejects_challenger_as_primary(self):
        """No caller-configurable model override: the frozen runtime
        refuses to run qwen3.8-27b in the PRIMARY seat."""
        config = SemanticRuntimeConfig(primary_model="qwen3.8-27b")
        with pytest.raises(SemanticRuntimeConfigError):
            validate_runtime_config(config)

    def test_production_runtime_rejects_challenger_as_fallback(self):
        config = SemanticRuntimeConfig(fallback_model="qwen3.8-27b")
        with pytest.raises(SemanticRuntimeConfigError):
            validate_runtime_config(config)

    def test_production_result_cannot_carry_challenger_route(self):
        """SemanticRuntimeResult self-validates the pinned requested
        primary; a challenger-named result cannot even be constructed."""
        with pytest.raises(ValueError, match="pinned primary model"):
            SemanticRuntimeResult(
                case_id="SPR-0001",
                target_mpn="X",
                target_description="d",
                candidate_title="t",
                candidate_mpn_field=None,
                candidate_sku=None,
                candidate_specs=None,
                evidence_source="UNKNOWN",
                requested_primary_provider="amax",
                requested_primary_model="qwen3.8-27b",
                attempts=(
                    SemanticAttempt(
                        provider="amax",
                        model="qwen3.8-27b",
                        status=SemanticAttemptStatus.OK,
                        latency_ms=1.0,
                    ),
                ),
                fallback_used=False,
                fallback_reason=None,
                actual_provider="amax",
                actual_model="qwen3.8-27b",
                decision=SemanticDecision.MATCH,
                confidence=None,
                matched_attributes=(),
                conflicting_attributes=(),
                missing_critical_attributes=(),
                reason_code="x",
                error_type=None,
            )

    def test_fallback_allowlist_stays_execution_failures_only(self):
        """The frozen fallback trigger set contains only execution-failure
        codes - content rejection and any semantic disagreement have no
        member, by construction."""
        from product_intelligence.semantic.runtime import (
            PRIMARY_NON_FALLBACK_ERRORS,
        )

        assert "CASE_REJECTED" not in PRIMARY_FALLBACK_ELIGIBLE_ERRORS
        assert not (PRIMARY_FALLBACK_ELIGIBLE_ERRORS & PRIMARY_NON_FALLBACK_ERRORS)
        for code in PRIMARY_FALLBACK_ELIGIBLE_ERRORS:
            assert code in {s.value for s in SemanticAttemptStatus}


# ---------------------------------------------------------------------------
# 2. Shared objects: no forked contract
# ---------------------------------------------------------------------------


class TestSharedContractObjects:
    def test_harness_uses_the_contract_prompt_builder(self):
        from product_intelligence.evaluation.semantic.promotion_regression import (
            build_prompt as harness_build_prompt,
        )

        assert harness_build_prompt is build_prompt

    def test_harness_uses_the_strict_contract_parser(self):
        from product_intelligence.evaluation.semantic.promotion_regression import (
            parse_raw_output as harness_parse,
            validate_response as harness_validate,
            RawOutputParseError as harness_parse_error,
            SemanticDecision as harness_decision,
        )

        assert harness_parse is parse_raw_output
        assert harness_validate is validate_response
        assert harness_parse_error is RawOutputParseError
        assert harness_decision is SemanticDecision
        assert SEMANTIC_PROMPT_VERSION == "1.1"

    def test_harness_reuses_frozen_transport_status_mapping(self):
        from product_intelligence.evaluation.semantic.promotion_regression import (
            _TRANSPORT_ERROR_TO_STATUS as harness_mapping,
            SemanticAttemptStatus as harness_status,
        )
        import product_intelligence.semantic.runtime as runtime_module

        assert harness_mapping is runtime_module._TRANSPORT_ERROR_TO_STATUS
        assert harness_status is runtime_module.SemanticAttemptStatus

    def test_harness_prompt_text_is_frozen(self):
        """The harness defines no prompt text of its own: the module source
        assigns no SYSTEM_PROMPT / USER_PROMPT_TEMPLATE / prompt version,
        and its prompt version constant IS the frozen contract object."""
        import ast as _ast
        from pathlib import Path as _Path

        import product_intelligence.evaluation.semantic.promotion_regression as harness

        source = _Path(harness.__file__).read_text(encoding="utf-8")
        assigned: list[str] = []
        for node in _ast.parse(source).body:
            if isinstance(node, _ast.Assign):
                assigned.extend(
                    t.id for t in node.targets if isinstance(t, _ast.Name)
                )
            elif isinstance(node, (_ast.FunctionDef, _ast.ClassDef)):
                assigned.append(node.name)
        assert "SYSTEM_PROMPT" not in assigned
        assert "USER_PROMPT_TEMPLATE" not in assigned
        assert "SEMANTIC_PROMPT_VERSION" not in assigned
        assert harness.SEMANTIC_PROMPT_VERSION is SEMANTIC_PROMPT_VERSION


# ---------------------------------------------------------------------------
# 3. Mirror locks: harness behavior == frozen production behavior
# ---------------------------------------------------------------------------


def _make_observation(
    *,
    title: str | None = "Test Product",
    mpn: str | None = None,
    sku: str | None = None,
    brand: str | None = None,
    price: str | None = None,
    currency: str | None = None,
) -> ListingObservation:
    return ListingObservation(
        source_url="https://example.com/promotion-regression/mirror",
        extraction_method=ExtractionMethod.JSON_LD,
        product_title=title,
        manufacturer_part_number_text=mpn,
        sku_text=sku,
        brand_text=brand,
        price_text=price,
        currency_text=currency,
    )


def _make_normalized(
    observation: ListingObservation,
    *,
    condition: NormalizedCondition = NormalizedCondition.UNKNOWN,
) -> NormalizedListingObservation:
    price_amount = None
    if observation.price_text:
        try:
            price_amount = Decimal(observation.price_text)
        except Exception:
            pass
    return NormalizedListingObservation(
        observation=observation,
        price_amount=price_amount,
        currency_code=observation.currency_text,
        availability=NormalizedAvailability.UNKNOWN,
        condition=condition,
        seller_name=None,
        normalization_issues=(),
    )


class TestEligibilityMirrorLockedToExecution:
    """The harness's eligibility predicate must equal the frozen FU3B
    execution predicate + usable-evidence gate, for every deterministic
    state - and the public research predicate it relies on must keep
    mirroring the execution predicate."""

    @pytest.fixture
    def execution_predicates(self):
        from product_intelligence.execution.semantic_integration import (
            _has_usable_evidence,
            _is_semantic_eligible,
        )

        return _is_semantic_eligible, _has_usable_evidence

    def _battery(self):
        """Build real assessments for every deterministic state."""
        cases = []
        request = ResearchRequest("TEST-MPN-001", "Test product description")

        def add(obs: ListingObservation):
            norm = _make_normalized(obs)
            cases.append(assess_listing_identity(request, norm))

        # ACCEPTED / EXACT
        add(_make_observation(title="P", mpn="TEST-MPN-001"))
        # ACCEPTED / NORMALIZED_EXACT
        add(_make_observation(title="P", mpn="test mpn 001"))
        # REJECTED / MPN_MISMATCH
        add(_make_observation(title="P", mpn="TEST-MPN-002"))
        # REJECTED / PARTIAL_MPN_ONLY (shorter prefix at boundary)
        add(_make_observation(title="P", mpn="TEST-MPN"))
        # REJECTED / PARTIAL_MPN_ONLY (longer extension at boundary)
        add(_make_observation(title="P", mpn="TEST-MPN-001-REV"))
        # REJECTED / NO_EXPLICIT_MPN_EVIDENCE / TITLE_TEXT
        add(_make_observation(title="TEST-MPN-001 is here"))
        # REJECTED / NO_EXPLICIT_MPN_EVIDENCE / SKU_FIELD (with title)
        add(_make_observation(title="A product", sku="RETAILER-SKU"))
        # REJECTED / NO_EXPLICIT_MPN_EVIDENCE / NONE
        add(_make_observation(title="A product"))
        # REJECTED / NO_EXPLICIT_MPN_EVIDENCE / SKU_FIELD (NO title)
        add(_make_observation(title=None, sku="RETAILER-SKU"))
        # UNDECIDED / NO_REQUESTED_MPN (description-only request)
        desc_request = ResearchRequest("", "Description only")
        norm = _make_normalized(_make_observation(title="P", sku="S"))
        cases.append(assess_listing_identity(desc_request, norm))
        return cases

    def test_research_predicate_mirrors_execution_predicate(self, execution_predicates):
        is_exec_eligible, _ = execution_predicates
        for assessment in self._battery():
            assert is_human_review_eligible_assessment(assessment) is is_exec_eligible(
                assessment
            ), f"mirror drift on {assessment.decision.value}/{assessment.rejection_reason}"

    def test_harness_eligibility_equals_execution_rules(self, execution_predicates):
        is_exec_eligible, has_usable = execution_predicates
        for assessment in self._battery():
            expected = is_exec_eligible(assessment) and has_usable(assessment)
            assert semantic_call_is_expected(assessment) is expected, (
                f"harness eligibility drifted from the frozen execution "
                f"rules on {assessment.decision.value}/"
                f"{assessment.rejection_reason.value if assessment.rejection_reason else None}"
            )

    def test_harness_eligibility_matches_corpus_declarations(self, execution_predicates):
        is_exec_eligible, has_usable = execution_predicates
        for case in CORPUS.cases:
            assessment = assess_case_for_mirror(case)
            expected = is_exec_eligible(assessment) and has_usable(assessment)
            assert semantic_call_is_expected(assessment) is expected
            assert expected is case.expected_semantic_call


def assess_case_for_mirror(case):
    from product_intelligence.evaluation.semantic.promotion_regression import (
        assess_case,
    )

    return assess_case(case)


@pytest.mark.parametrize(
    "brand,mpn,sku,condition",
    [
        (None, None, None, None),
        ("Acme", None, None, None),
        (None, "MPN-1", None, None),
        (None, None, "SKU-1", None),
        (None, None, None, "new"),
        ("Acme", "MPN-1", "SKU-1", "new"),
        ("Acme", None, "SKU-1", "open box"),
    ],
)
def test_specs_builder_mirror_locked_to_execution(brand, mpn, sku, condition):
    """The harness's candidate-specs builder must produce byte-identical
    strings to the frozen execution integration's builder."""
    from product_intelligence.execution.semantic_integration import (
        _build_candidate_specs,
    )

    observation = _make_observation(
        title="P", brand=brand, mpn=mpn, sku=sku
    )
    if condition is not None:
        observation = ListingObservation(
            source_url=observation.source_url,
            extraction_method=ExtractionMethod.JSON_LD,
            product_title="P",
            manufacturer_part_number_text=mpn,
            sku_text=sku,
            brand_text=brand,
            condition_text=condition,
        )
    assert _build_case_specs(observation) == _build_candidate_specs(observation)


class _ScriptedTransport:
    """Returns one scripted outcome for every call."""

    def __init__(self, outcome):
        self._outcome = outcome
        self.call_count = 0

    def complete(self, *, system_prompt, user_prompt, model, temperature, max_tokens):
        self.call_count += 1
        return self._outcome


class _SentinelFallback:
    """Records any call; returns a bounded failure so the runtime can
    finish a two-attempt history."""

    def __init__(self):
        self.call_count = 0

    def complete(self, *, system_prompt, user_prompt, model, temperature, max_tokens):
        self.call_count += 1
        return TransportFailure(error_type="MODEL_NOT_FOUND", transport_status="404")


class TestInterpretationMirrorLockedToRuntime:
    """The harness's single-attempt interpretation must classify every
    outcome exactly the way the production primary attempt does."""

    @pytest.mark.parametrize(
        "label,outcome",
        [
            (
                "valid_match",
                TransportResult(
                    raw_output=_VALID_MATCH,
                    latency_ms=10.0,
                    provider_status="200",
                    provider_id="amax",
                    model_id="nemotron-3-super",
                    provider_reported_model="nemotron-3-super",
                    finish_reason="stop",
                ),
            ),
            (
                "valid_no_match",
                TransportResult(
                    raw_output=_VALID_MATCH.replace(
                        '"decision": "MATCH"', '"decision": "NO_MATCH"'
                    ).replace('"matched_attributes": ["mpn"]', '"matched_attributes": []'),
                    latency_ms=10.0,
                    provider_status="200",
                    provider_id="amax",
                    model_id="nemotron-3-super",
                    provider_reported_model="nemotron-3-super",
                    finish_reason="stop",
                ),
            ),
            (
                "prose_around_json",
                TransportResult(
                    raw_output="Here is the JSON:\n" + _VALID_MATCH,
                    latency_ms=10.0,
                    provider_status="200",
                    provider_reported_model="nemotron-3-super",
                ),
            ),
            (
                "empty_response",
                TransportResult(
                    raw_output="   ",
                    latency_ms=10.0,
                    provider_status="200",
                    provider_reported_model="nemotron-3-super",
                ),
            ),
            (
                "identity_none",
                TransportResult(
                    raw_output=_VALID_MATCH,
                    latency_ms=10.0,
                    provider_status="200",
                    provider_reported_model=None,
                ),
            ),
            (
                "identity_mismatch",
                TransportResult(
                    raw_output=_VALID_MATCH,
                    latency_ms=10.0,
                    provider_status="200",
                    provider_reported_model="another-model",
                ),
            ),
        ],
    )
    def test_success_path_outcomes(self, label, outcome):
        primary = _ScriptedTransport(outcome)
        sentinel = _SentinelFallback()
        runtime = SemanticRuntime(
            config=SemanticRuntimeConfig(),
            primary_transport=primary,
            fallback_transport=sentinel,
        )
        result = runtime.evaluate(
            case_id="MIRROR",
            target_mpn="T",
            target_description="d",
            candidate_title="c",
        )
        harness = interpret_transport_outcome(outcome, "nemotron-3-super")
        assert harness.status is result.attempts[0].status, label
        if harness.status is SemanticAttemptStatus.OK:
            assert result.decision is harness.response.decision
            # A valid primary decision is FINAL: zero fallback calls.
            assert sentinel.call_count == 0
            assert primary.call_count == 1
        elif harness.status.value in PRIMARY_FALLBACK_ELIGIBLE_ERRORS:
            assert sentinel.call_count == 1
        else:
            assert sentinel.call_count == 0

    @pytest.mark.parametrize(
        "error_code",
        sorted(_TRANSPORT_ERROR_TO_STATUS.keys()),
    )
    def test_transport_failure_codes(self, error_code):
        outcome = TransportFailure(error_type=error_code, transport_status="500")
        primary = _ScriptedTransport(outcome)
        sentinel = _SentinelFallback()
        runtime = SemanticRuntime(
            config=SemanticRuntimeConfig(),
            primary_transport=primary,
            fallback_transport=sentinel,
        )
        result = runtime.evaluate(
            case_id="MIRROR",
            target_mpn="T",
            target_description="d",
            candidate_title="c",
        )
        harness = interpret_transport_outcome(outcome, "nemotron-3-super")
        assert harness.status is result.attempts[0].status, error_code
        assert harness.transport_error_type == error_code
        # Fallback eligibility is decided by the mapped STATUS, exactly as in
        # production (the frozen allowlist names statuses, not raw codes).
        if harness.status.value in PRIMARY_FALLBACK_ELIGIBLE_ERRORS:
            assert sentinel.call_count == 1  # execution failure -> fallback
        else:
            assert sentinel.call_count == 0  # fail closed, no fallback

    def test_unknown_error_code_fails_closed_both_sides(self):
        outcome = TransportFailure(error_type="NOT_A_REAL_CODE")
        primary = _ScriptedTransport(outcome)
        sentinel = _SentinelFallback()
        runtime = SemanticRuntime(
            config=SemanticRuntimeConfig(),
            primary_transport=primary,
            fallback_transport=sentinel,
        )
        result = runtime.evaluate(
            case_id="MIRROR",
            target_mpn="T",
            target_description="d",
            candidate_title="c",
        )
        harness = interpret_transport_outcome(outcome, "nemotron-3-super")
        assert harness.status is SemanticAttemptStatus.UNKNOWN_ERROR
        assert result.attempts[0].status is SemanticAttemptStatus.UNKNOWN_ERROR
        assert sentinel.call_count == 0  # unknown code never buys a fallback


# ---------------------------------------------------------------------------
# 4. Authority boundaries: MATCH stays AI-assisted, never leaks
# ---------------------------------------------------------------------------


class TestAuthorityBoundaries:
    def test_semantic_match_stays_outside_frozen_4a(self):
        """A harness-observed MATCH on an eligible candidate still leaves
        the original assessment REJECTED, and the frozen 4A aggregation
        still excludes it as IDENTITY_NOT_ACCEPTED."""
        run, _ = _ideal_run(NEOTRON_SPEC)
        case = CORPUS.get_case("SPR-0005")
        record = next(r for r in run.records if r.case_id == case.case_id)
        assert record.decision == "MATCH"
        assert record.disposition == "AI_ASSISTED_MATCH"

        # Rebuild a priced assessment for the same case (identity does not
        # depend on price) and run the frozen 4A aggregation on it.
        inputs = build_case_inputs(case)
        priced_observation = ListingObservation(
            source_url=inputs.observation.source_url,
            extraction_method=ExtractionMethod.JSON_LD,
            product_title=inputs.observation.product_title,
            manufacturer_part_number_text=inputs.observation.manufacturer_part_number_text,
            sku_text=inputs.observation.sku_text,
            brand_text=inputs.observation.brand_text,
            price_text="100.00",
            currency_text="USD",
            condition_text="new",
        )
        priced = NormalizedListingObservation(
            observation=priced_observation,
            price_amount=Decimal("100.00"),
            currency_code="USD",
            availability=NormalizedAvailability.UNKNOWN,
            condition=NormalizedCondition.NEW,
            seller_name=None,
            normalization_issues=(),
        )
        assessment = assess_listing_identity(inputs.request, priced)
        assert assessment.decision is EvidenceDecision.REJECTED

        result = aggregate_listing_prices(inputs.request, (assessment,))
        assert result.buckets == ()
        assert len(result.exclusions) == 1
        assert (
            result.exclusions[0].reason
            is PriceAggregationExclusionReason.IDENTITY_NOT_ACCEPTED
        )
        # The assessment is a frozen dataclass: nothing the harness (or a
        # semantic result) did may have mutated it.
        assert assessment.decision is EvidenceDecision.REJECTED

    def test_ai_assisted_match_result_constructible_from_harness_provenance(self):
        """The provenance the harness records for a MATCH is exactly what
        the frozen production AiAssistedMatchResult validates: a real
        SemanticRuntimeResult (pinned primary) + real assessment must
        construct without error."""
        from product_intelligence.execution.semantic_integration import (
            AiAssistedMatchResult,
        )

        run, _ = _ideal_run(NEOTRON_SPEC)
        case = CORPUS.get_case("SPR-0005")
        record = next(r for r in run.records if r.case_id == case.case_id)
        assert record.decision == "MATCH"
        assert run.spec.model == PRIMARY_MODEL  # pinned-primary run

        inputs = build_case_inputs(case)
        assessment = assess_listing_identity(inputs.request, inputs.normalized)

        semantic_result = SemanticRuntimeResult(
            case_id=case.case_id,
            target_mpn=record.target_mpn,
            target_description=record.target_description,
            candidate_title=record.candidate_title or "",
            candidate_mpn_field=record.candidate_mpn_field,
            candidate_sku=record.candidate_sku,
            candidate_specs=None,
            evidence_source=record.deterministic_evidence_source,
            requested_primary_provider=PRIMARY_PROVIDER,
            requested_primary_model=PRIMARY_MODEL,
            attempts=(
                SemanticAttempt(
                    provider=PRIMARY_PROVIDER,
                    model=PRIMARY_MODEL,
                    status=SemanticAttemptStatus.OK,
                    latency_ms=record.latency_ms or 0.0,
                ),
            ),
            fallback_used=False,
            fallback_reason=None,
            actual_provider=PRIMARY_PROVIDER,
            actual_model=PRIMARY_MODEL,
            decision=SemanticDecision(record.decision),
            confidence=None if record.confidence is None else _confidence(record.confidence),
            matched_attributes=record.matched_attributes,
            conflicting_attributes=record.conflicting_attributes,
            missing_critical_attributes=record.missing_critical_attributes,
            reason_code=record.reason_code,
            error_type=None,
        )
        wrapped = AiAssistedMatchResult(
            original_assessment=assessment,
            semantic_result=semantic_result,
            disposition=EvidenceDecision.AI_ASSISTED_MATCH,
        )
        assert wrapped.disposition is EvidenceDecision.AI_ASSISTED_MATCH
        assert wrapped.original_assessment.decision is EvidenceDecision.REJECTED

    def test_hard_conflict_not_bypassed_by_semantic_attributes(self):
        """A challenger MATCH that reports identity-critical conflicting
        attributes still classifies as HARD_CONFLICT under the frozen
        domain working-quote policy - semantic output cannot bypass it."""
        from product_intelligence.domain.working_quote_policy import (
            WorkingQuoteDisposition,
            classify_working_quote_policy,
        )

        for conflicts in (
            ["capacity"],
            ["form factor"],
            ["interface"],
            ["compatible with"],
            ["multipack"],
            ["product type"],
        ):
            disposition = classify_working_quote_policy(
                review_state="UNREVIEWED",
                semantic_confidence="HIGH",
                strong_sku_identity=False,
                conflicting_attributes=conflicts,
            )
            assert disposition is WorkingQuoteDisposition.HARD_CONFLICT, conflicts

    def test_no_human_confirmation_or_reviewed_price_fabricated(self):
        """Harness artifacts carry no review state and no
        HUMAN_CONFIRMED / Reviewed Price authority - only the
        AI_ASSISTED_MATCH / UNDECIDED disposition vocabulary."""
        for spec in (NEOTRON_SPEC, QWEN_SPEC):
            run, _ = _ideal_run(spec)
            blob = json.dumps(
                [r.to_dict() for r in run.records]
                + [run.manifest]
                + [g.to_dict() for g in run.gates],
                ensure_ascii=False,
            )
            assert "HUMAN_CONFIRMED" not in blob
            assert "review_state" not in blob
            dispositions = {r.disposition for r in run.records}
            assert dispositions <= {
                "AI_ASSISTED_MATCH",
                "UNDECIDED",
                None,
            }

    def test_disposition_mapping_vocabulary(self):
        assert map_semantic_disposition(SemanticDecision.MATCH) is (
            EvidenceDecision.AI_ASSISTED_MATCH
        )
        assert map_semantic_disposition(SemanticDecision.NO_MATCH) is (
            EvidenceDecision.UNDECIDED
        )
        assert map_semantic_disposition(SemanticDecision.UNCERTAIN) is (
            EvidenceDecision.UNDECIDED
        )
        assert map_semantic_disposition(None) is None


def _confidence(value: str):
    from product_intelligence.semantic.contract import ConfidenceLevel

    return ConfidenceLevel(value)


# ---------------------------------------------------------------------------
# 5. Import boundaries: evaluation-only, production untouched
# ---------------------------------------------------------------------------


HARNESS_FILES = (
    REPO_ROOT
    / "product_intelligence"
    / "evaluation"
    / "semantic"
    / "promotion_regression.py",
    REPO_ROOT
    / "product_intelligence"
    / "evaluation"
    / "semantic"
    / "promotion_regression_cli.py",
)

_ALLOWED_TOP_LEVEL_IMPORTS = (
    set(sys.stdlib_module_names) | {"product_intelligence"}
)


class TestImportBoundaries:
    @pytest.mark.parametrize("path", HARNESS_FILES, ids=lambda p: p.name)
    def test_harness_imports_only_stdlib_and_project(self, path: Path):
        modules: set[str] = set()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    modules.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
                modules.add(node.module.split(".")[0])
        disallowed = modules - _ALLOWED_TOP_LEVEL_IMPORTS
        assert not disallowed, f"{path.name} imports {sorted(disallowed)}"

    @pytest.mark.parametrize("path", HARNESS_FILES, ids=lambda p: p.name)
    def test_harness_never_imports_execution_runs_web_or_django(self, path: Path):
        """AST import scan (module-level AND lazy, anywhere in the file):
        the harness must never import the Django-dependent execution layer,
        persistence, web, or provider layers."""
        tree = ast.parse(path.read_text(encoding="utf-8"))
        forbidden_prefixes = (
            "product_intelligence.execution",
            "product_intelligence.runs",
            "product_intelligence.web",
            "product_intelligence.providers",
            "django",
        )
        offenders: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for prefix in forbidden_prefixes:
                        if (
                            alias.name == prefix
                            or alias.name.startswith(prefix + ".")
                        ):
                            offenders.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.level:  # relative import: stays inside the package
                    continue
                module = node.module or ""
                for prefix in forbidden_prefixes:
                    if module == prefix or module.startswith(prefix + "."):
                        offenders.append(module)
        assert not offenders, (
            f"{path.name} imports {sorted(set(offenders))}; the harness must "
            "stay evaluation-only and must not drag in Django-dependent "
            "layers"
        )

    def test_no_production_module_references_the_harness(self):
        """Production must never import evaluation code. Specifically, no
        production module may reference promotion_regression at all."""
        production_roots = (
            "domain",
            "research",
            "providers",
            "runs",
            "execution",
            "semantic",
            "web",
        )
        for root in production_roots:
            package_dir = REPO_ROOT / "product_intelligence" / root
            for py in package_dir.rglob("*.py"):
                if "__pycache__" in py.parts:
                    continue
                source = py.read_text(encoding="utf-8")
                assert "promotion_regression" not in source, (
                    f"production module {py} references the evaluation "
                    "promotion-regression harness; production must never "
                    "depend on evaluation code"
                )

    def test_clean_state_import_loads_no_django_or_execution(self):
        """Freshly import the harness from an evicted module state and
        inspect what actually loaded: the harness's full import closure must
        contain no Django, no execution, no runs, no web, and no providers.

        Uses the same evict-and-restore discipline as
        ``tests/semantic/test_runtime_boundaries.py`` (including the
        parent-package attribute restore) so the session state is left
        exactly as found.
        """
        from contextlib import contextmanager

        class _Unset:
            pass

        _UNSET = _Unset()

        @contextmanager
        def _clean_harness_state():
            saved_modules = dict(sys.modules)
            to_evict = [
                name
                for name in sys.modules
                if name == "product_intelligence" or name.startswith("product_intelligence.")
                or name.split(".")[0]
                in ("django", "requests", "urllib", "urllib3", "httpx", "aiohttp")
            ]
            snapshots = []
            for name in to_evict:
                parent_name, sep, attr = name.rpartition(".")
                if not sep:
                    continue
                parent = sys.modules.get(parent_name)
                if parent is None:
                    continue
                snapshots.append((parent, attr, getattr(parent, attr, _UNSET)))
            for name in to_evict:
                del sys.modules[name]
            try:
                yield
            finally:
                sys.modules.clear()
                sys.modules.update(saved_modules)
                for parent, attr, old_value in snapshots:
                    if old_value is _UNSET:
                        if hasattr(parent, attr):
                            delattr(parent, attr)
                    else:
                        setattr(parent, attr, old_value)

        with _clean_harness_state():
            import product_intelligence.evaluation.semantic.promotion_regression  # noqa: F401

            loaded = set(sys.modules)

        assert (
            "product_intelligence.evaluation.semantic.promotion_regression"
            in loaded
        )
        offenders = sorted(
            name
            for name in loaded
            if name.split(".")[0] == "django"
            or name.startswith("product_intelligence.execution")
            or name.startswith("product_intelligence.runs")
            or name.startswith("product_intelligence.web")
            or name.startswith("product_intelligence.providers")
        )
        assert offenders == [], (
            f"fresh import of the promotion-regression harness pulled in "
            f"{offenders}; the harness must stay evaluation-only"
        )
