"""Tests for the S2-C live V2 execution wiring (groups F live + H).

Covers ``product_intelligence.execution.semantic_decision_v2_execution``
and its integration into ``execution.orchestration``:

* ALL V2 outcomes persist through the S2-B service (MATCH / NO_MATCH /
  UNCERTAIN / RUNTIME_FAILURE / fallback success / fallback failure) for
  every V2-eligible candidate, and load back as V2 records;
* the exact V2 contract identity, the exact V2 input, the exact
  structured output, and the exact attempts are stored;
* the AUTHORITY FIREWALL: a V2 MATCH/HIGH does not enter the frozen 4A
  aggregation, does not alter Machine Price, does not alter Reviewed
  Price, does not create a HUMAN_CONFIRMED state, and creates NO V2
  human-review candidate (persist V2 result only);
* V1/V2 coexistence: the frozen V1 path is unchanged (V1-eligible
  candidates still get their V1 evaluation and their V1 review
  candidate on V1 MATCH); V2 additionally reaches U4 / U5 (candidates
  the V1 predicate never evaluates) with zero V1 calls for them;
* the 4D-D alias-expanded search batch carries
  CUSTOMER_RETRIEVAL_RELATION provenance in the recorded V2 input
  (retrieval hint only — derived relationship authority stays
  NOT_ESTABLISHED);
* the persisted V2 record replays through the S2-B service with the
  full binding verification.

Zero live AI / provider / network work: fake transports only.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import EvidenceDecision, ResearchRunState
from product_intelligence.research import (
    PRICE_RESULT_SCHEMA_VERSION,
    V2Confidence,
    V2SemanticDecision,
    ContextProvenance,
    ExtractionMethod,
    ListingObservation,
    RelationshipAuthority,
    aggregate_listing_prices,
    assess_listing_identity,
    decode_price_aggregation_result,
    derive_identity_state_v2,
    derive_authority_tier,
    derive_product_evidence_quality,
    derive_relationship_authority,
    encode_price_aggregation_result,
    normalize_listing_observation,
    is_v2_semantic_eligible,
)
from product_intelligence.research import (
    AuthorityRuleV2,
    AuthorityTier,
    CandidateProductEvidenceSource,
    ConflictClass,
    ProductEvidenceDimension,
    ProductEvidenceFactV2,
    ProductEvidenceProfileV2,
    RelationshipRequirement,
    SemanticEvaluationStateV2,
    SemanticEvaluationV2,
    substate_relationship_requirement,
)
from product_intelligence.research.semantic_decision_codec import (
    SemanticDecisionCodecError,
)
from product_intelligence.research.semantic_decision_v2 import (
    SemanticDecisionRecordV2,
    V2_CONTRACT_BINDING,
)
from product_intelligence.runs.models import (
    AiAssistedReviewCandidate,
    PriceIntelligenceSnapshot,
    ResearchRun,
    SemanticDecisionRecord as SemanticDecisionRecordRow,
)
from product_intelligence.execution.semantic_decision_persistence import (
    load_semantic_decision,
    replay_semantic_decision_record,
)
from product_intelligence.execution.semantic_decision_v2_execution import (
    SemanticDecisionV2Outcome,
    build_semantic_decision_records_v2,
    evaluate_semantic_matches_v2,
    persist_semantic_decision_records_v2,
)
from product_intelligence.semantic import SemanticDecision
from product_intelligence.semantic.runtime import SemanticRuntime
from product_intelligence.semantic.runtime_v2 import (
    PRIMARY_MODEL_V2,
    FALLBACK_MODEL_V2,
    SemanticRuntimeV2,
)
from product_intelligence.semantic.transport import FakeSemanticModelTransport


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


REQUEST = ResearchRequest("ABC-123", "A test product")


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    SemanticDecisionRecordRow.objects.all().delete()
    AiAssistedReviewCandidate.objects.all().delete()
    PriceIntelligenceSnapshot.objects.all().delete()
    ResearchRun.objects.all().delete()


def _v1_response(decision: str) -> str:
    return json.dumps(
        {
            "decision": decision,
            "confidence": "HIGH",
            "matched_attributes": ["mpn"],
            "conflicting_attributes": [],
            "missing_critical_attributes": [],
            "reason_code": "exact_mpn_match",
        }
    )


def _v2_response(
    decision: str = "MATCH",
    confidence: str = "HIGH",
    reason_code: str = "MATCH_DESCRIPTION_AND_ATTRIBUTES",
    conflicts=None,
    matched=None,
) -> str:
    return json.dumps(
        {
            "decision": decision,
            "confidence": confidence,
            "reason_code": reason_code,
            "matched_attributes": matched if matched is not None else [],
            "conflicting_attributes": [],
            "missing_critical_attributes": [],
            "conflict_classes": conflicts if conflicts is not None else [],
        }
    )


def _v1_runtime(response: str = _v1_response("MATCH")):
    return SemanticRuntime(
        primary_transport=FakeSemanticModelTransport(
            responses={"*": response},
            provider_reported_model="qwen3.8-27b",
        ),
        fallback_transport=FakeSemanticModelTransport(
            responses={"*": response},
            provider_reported_model="Qwen3.6-27B-262K",
        ),
    )


def _v2_runtime(
    response: str | None = _v2_response(),
    primary_error: str | None = None,
    fallback_response: str | None = None,
    fallback_error: str | None = None,
) -> SemanticRuntimeV2:
    def _t(error=None, raw=None, model=PRIMARY_MODEL_V2):
        return FakeSemanticModelTransport(
            responses={"UNKNOWN": raw} if raw is not None else None,
            failure_error_types={"UNKNOWN": error} if error else None,
            provider_reported_model=model,
            case_ids=("UNKNOWN",),
        )

    return SemanticRuntimeV2(
        primary_transport=_t(primary_error, response),
        fallback_transport=_t(
            fallback_error,
            fallback_response,
            model=FALLBACK_MODEL_V2,
        ),
    )


# -- Full orchestration helpers (fake providers, no live work) ------------


def _make_search_response(urls):
    from product_intelligence.providers.search import SearchQuery

    results = []
    for url in urls:
        result = MagicMock()
        result.source_url = url
        result.title = "Product"
        result.snippet = "Description"
        result.price_hint_text = None
        result.part_number_hint = None
        result.raw_reference = None
        results.append(result)
    response = MagicMock()
    response.provider_id = "test"
    response.query = MagicMock(spec=SearchQuery)
    response.retrieved_at = datetime.now(tz=timezone.utc)
    response.results = tuple(results)
    response.raw_response_reference = None
    return response


def _make_page_fetcher(url_to_body):
    from product_intelligence.providers.page import FetchedPage, PageFetchRequest

    fetcher = MagicMock()

    def _fetch(request: PageFetchRequest) -> FetchedPage:
        body = url_to_body.get(request.url, "<html></html>")
        return FetchedPage(
            requested_url=request.url,
            final_url=request.url,
            retrieved_at=datetime.now(tz=timezone.utc),
            status_code=200,
            body_text=body,
            content_type="text/html",
            body_byte_count=len(body),
            redirect_count=0,
            fetcher_id="test",
        )

    fetcher.fetch.side_effect = _fetch
    return fetcher


def _json_ld_page(payload):
    text = json.dumps(payload)
    return (
        f'<html><body><script type="application/ld+json">{text}'
        "</script></body></html>"
    )


def _accepted_page(price, mpn):
    return _json_ld_page(
        {
            "@type": "Product",
            "name": "Test Product",
            "mpn": mpn,
            "offers": {
                "@type": "Offer",
                "price": price,
                "priceCurrency": "USD",
                "itemCondition": "https://schema.org/NewCondition",
            },
        }
    )


def _u1_page(price):
    return _json_ld_page(
        {
            "@type": "Product",
            "name": "TEST-MPN Drive",
            "offers": {
                "@type": "Offer",
                "price": price,
                "priceCurrency": "USD",
                "itemCondition": "https://schema.org/NewCondition",
            },
        }
    )


def _u5_page(price, candidate_mpn):
    return _json_ld_page(
        {
            "@type": "Product",
            "name": f"Near miss product {candidate_mpn}",
            "mpn": candidate_mpn,
            "offers": {
                "@type": "Offer",
                "price": price,
                "priceCurrency": "USD",
                "itemCondition": "https://schema.org/NewCondition",
            },
        }
    )


def _execute(
    request, url_to_body, v1_get_default, v2_response_factory
):
    """One full execute_research_run with bounded fake runtimes.

    ``v1_get_default`` is the V1 default-runtime factory (a fake runtime
    factory, or a sentinel that fails the test if V1 is ever called).
    """
    from product_intelligence.execution import execute_research_run
    from product_intelligence.providers.search import SearchProvider

    urls = list(url_to_body)
    search_provider = MagicMock(spec=SearchProvider)
    search_provider.search.return_value = _make_search_response(urls)
    page_fetcher = _make_page_fetcher(url_to_body)

    run = ResearchRun.objects.create_from_request(request)
    with patch(
        "product_intelligence.execution.semantic_integration."
        "get_default_runtime",
        side_effect=v1_get_default,
    ), patch(
        "product_intelligence.execution.semantic_decision_v2_execution."
        "get_default_runtime_v2",
        side_effect=[v2_response_factory()],
    ):
        return execute_research_run(
            str(run.id),
            search_provider=search_provider,
            page_fetcher=page_fetcher,
        )


def _sentinel_v1_get_default():
    def _sentinel():
        raise AssertionError(
            "the V1 default runtime must not be constructed: this run "
            "carries no V1-eligible candidate"
        )

    return _sentinel


# ===========================================================================
# F. Persistence of ALL V2 outcomes (service round-trips)
# ===========================================================================


class TestV2OutcomesPersist:
    def _persist(self, run, assessment, runtime):
        outcomes = evaluate_semantic_matches_v2(
            REQUEST,
            (assessment,),
            context_provenances_by_assessment={},
            reviewed_target_context=None,
            runtime_v2=runtime,
        )
        published = aggregate_listing_prices(REQUEST, (assessment,)).assessments
        records = build_semantic_decision_records_v2(run, published, outcomes)
        persist_semantic_decision_records_v2(run, records)
        return records[0], outcomes[0]

    def _u1_run_and_assessment(self):
        observation = ListingObservation(
            source_url="https://example.com/u1",
            extraction_method=ExtractionMethod.JSON_LD,
            product_title="ABC-123 1TB NVMe Drive",
            price_text="100",
            currency_text="USD",
            availability_text="In stock",
            condition_text="New",
        )
        assessment = assess_listing_identity(
            REQUEST, normalize_listing_observation(observation)
        )
        run = ResearchRun.objects.create_from_request(REQUEST)
        return run, assessment

    def test_match_stored(self) -> None:
        run, assessment = self._u1_run_and_assessment()
        record, _ = self._persist(
            run, assessment, _v2_runtime(_v2_response("MATCH"))
        )
        assert record.decision is V2SemanticDecision.MATCH
        loaded = load_semantic_decision(run.id, 0)
        assert isinstance(loaded, SemanticDecisionRecordV2)
        assert loaded.decision is V2SemanticDecision.MATCH

    def test_no_match_stored(self) -> None:
        run, assessment = self._u1_run_and_assessment()
        record, _ = self._persist(
            run,
            assessment,
            _v2_runtime(
                _v2_response(
                    decision="NO_MATCH",
                    reason_code="NO_MATCH_PRODUCT_FAMILY",
                    conflicts=["PRODUCT_FAMILY"],
                )
            ),
        )
        assert record.decision is V2SemanticDecision.NO_MATCH
        loaded = load_semantic_decision(run.id, 0)
        assert loaded.decision is V2SemanticDecision.NO_MATCH

    def test_uncertain_stored(self) -> None:
        run, assessment = self._u1_run_and_assessment()
        record, _ = self._persist(
            run,
            assessment,
            _v2_runtime(
                _v2_response(
                    decision="UNCERTAIN",
                    confidence="MEDIUM",
                    reason_code="UNCERTAIN_IDENTIFIER_RELATION",
                )
            ),
        )
        assert record.decision is V2SemanticDecision.UNCERTAIN
        loaded = load_semantic_decision(run.id, 0)
        assert loaded.decision is V2SemanticDecision.UNCERTAIN

    def test_runtime_failure_stored(self) -> None:
        run, assessment = self._u1_run_and_assessment()
        record, _ = self._persist(
            run,
            assessment,
            _v2_runtime(primary_error="TIMEOUT", fallback_error="TIMEOUT"),
        )
        assert record.evaluation_state.value == "RUNTIME_FAILURE"
        assert record.decision is None
        loaded = load_semantic_decision(run.id, 0)
        assert loaded.evaluation_state.value == "RUNTIME_FAILURE"

    def test_fallback_success_stored(self) -> None:
        run, assessment = self._u1_run_and_assessment()
        record, _ = self._persist(
            run,
            assessment,
            _v2_runtime(
                primary_error="RATE_LIMITED", fallback_response=_v2_response()
            ),
        )
        assert record.fallback_used is True
        assert record.fallback_reason.value == "RATE_LIMITED"
        assert record.decision is V2SemanticDecision.MATCH
        assert record.actual_provider == "vllm-262k"
        loaded = load_semantic_decision(run.id, 0)
        assert loaded.fallback_used is True
        assert len(loaded.attempts) == 2

    def test_fallback_failure_stored(self) -> None:
        run, assessment = self._u1_run_and_assessment()
        record, _ = self._persist(
            run,
            assessment,
            _v2_runtime(
                primary_error="CONNECTION_ERROR",
                fallback_error="CONNECTION_ERROR",
            ),
        )
        assert record.evaluation_state.value == "RUNTIME_FAILURE"
        assert record.fallback_used is True
        assert record.error_type.value == "FALLBACK_CONNECTION_ERROR"
        loaded = load_semantic_decision(run.id, 0)
        assert loaded.error_type.value == "FALLBACK_CONNECTION_ERROR"

    def test_exact_v2_versions_stored(self) -> None:
        run, assessment = self._u1_run_and_assessment()
        record, _ = self._persist(run, assessment, _v2_runtime())
        assert (
            record.semantic_contract_version,
            record.prompt_version,
            record.input_schema_version,
            record.output_schema_version,
            record.authority_contract_version,
        ) == V2_CONTRACT_BINDING
        loaded = load_semantic_decision(run.id, 0)
        assert (
            loaded.semantic_contract_version,
            loaded.prompt_version,
            loaded.input_schema_version,
            loaded.output_schema_version,
            loaded.authority_contract_version,
        ) == V2_CONTRACT_BINDING

    def test_exact_v2_input_stored(self) -> None:
        run, assessment = self._u1_run_and_assessment()
        record, _ = self._persist(run, assessment, _v2_runtime())
        loaded = load_semantic_decision(run.id, 0)
        assert loaded.case == record.case
        assert loaded.case.target.mpn == "ABC-123"
        assert loaded.case.candidate_source_url == "https://example.com/u1"
        assert loaded.case.identity_state.value == "DETERMINISTIC_UNCERTAIN"
        assert loaded.case.substate.value == "U1_TITLE_MPN"
        assert loaded.case.product_evidence.matched_facts == frozenset()

    def test_exact_structured_output_stored(self) -> None:
        run, assessment = self._u1_run_and_assessment()
        record, _ = self._persist(
            run,
            assessment,
            _v2_runtime(
                _v2_response(
                    matched=[
                        {
                            "dimension": "CAPACITY",
                            "detail": "1TB",
                        }
                    ]
                )
            ),
        )
        loaded = load_semantic_decision(run.id, 0)
        assert loaded.matched_attributes == record.matched_attributes
        assert loaded.matched_attributes[0].dimension.value == "CAPACITY"
        assert loaded.matched_attributes[0].detail == "1TB"
        assert loaded.reason_code.value == "MATCH_DESCRIPTION_AND_ATTRIBUTES"

    def test_exact_attempts_stored(self) -> None:
        run, assessment = self._u1_run_and_assessment()
        record, _ = self._persist(
            run,
            assessment,
            _v2_runtime(primary_error="TIMEOUT", fallback_response=_v2_response()),
        )
        loaded = load_semantic_decision(run.id, 0)
        assert [a.canonical() for a in loaded.attempts] == [
            a.canonical() for a in record.attempts
        ]
        assert loaded.attempts[0].provider == "amax"
        assert loaded.attempts[1].provider == "vllm-262k"
        assert loaded.attempts[1].outcome.value == "OK"

    def test_every_eligible_candidate_gets_a_record(self) -> None:
        # All outcomes, every eligible candidate: two eligible candidates
        # (U1 + U5) -> two records.
        request = ResearchRequest("ABC-123", "A test product")
        from product_intelligence.research import (
            ExtractionMethod,
            ListingObservation,
        )

        u1_obs = ListingObservation(
            source_url="https://example.com/u1",
            extraction_method=ExtractionMethod.JSON_LD,
            product_title="ABC-123 Drive",
            price_text="100",
            currency_text="USD",
            availability_text="In stock",
            condition_text="New",
        )
        u5_obs = ListingObservation(
            source_url="https://example.com/u5",
            extraction_method=ExtractionMethod.JSON_LD,
            product_title="Near miss drive",
            manufacturer_part_number_text="ABC-124",
            price_text="200",
            currency_text="USD",
            availability_text="In stock",
            condition_text="New",
        )
        assessments = tuple(
            assess_listing_identity(request, normalize_listing_observation(o))
            for o in (u1_obs, u5_obs)
        )
        assert is_v2_semantic_eligible(assessments[0])
        assert is_v2_semantic_eligible(assessments[1])
        run = ResearchRun.objects.create_from_request(request)
        outcomes = evaluate_semantic_matches_v2(
            request,
            assessments,
            context_provenances_by_assessment={},
            reviewed_target_context=None,
            runtime_v2=_v2_runtime(),
        )
        assert len(outcomes) == 2
        published = aggregate_listing_prices(request, assessments).assessments
        records = build_semantic_decision_records_v2(run, published, outcomes)
        assert len(records) == 2
        assert records[0].assessment_index == 0
        assert records[1].assessment_index == 1
        count = persist_semantic_decision_records_v2(run, records)
        assert count == 2
        assert run.semantic_decision_records.count() == 2


# ===========================================================================
# H. Authority firewall
# ===========================================================================


REQUEST_4A = ResearchRequest("TEST-MPN", "Test product")


class TestAuthorityFirewall:
    def test_v2_match_high_does_not_enter_4a_and_no_review_candidate(
        self,
    ) -> None:
        """Full run: deterministic ACCEPTED (100) + U5 near-miss (9999)
        with a V2 MATCH/HIGH. The 4A bucket contains ONLY the
        deterministic price; NO review candidate exists (V1 never
        evaluates U5; V2 persists only)."""
        url_acc = "https://example.com/exact"
        url_u5 = "https://example.com/near-miss"
        result = _execute(
            REQUEST_4A,
            {
                url_acc: _accepted_page("100", "TEST-MPN"),
                url_u5: _u5_page("9999", "TEST-MPNA"),
            },
            lambda: _v1_runtime(_v1_response("NO_MATCH")),
            lambda: _v2_runtime(
                _v2_response(
                    decision="MATCH",
                    confidence="HIGH",
                )
            ),
        )
        assert result.run.current_state == ResearchRunState.COMPLETED

        # 4A: one bucket, the deterministic price only.
        assert result.snapshot is not None
        buckets = result.snapshot.payload.get("buckets", [])
        assert len(buckets) == 1
        assert str(buckets[0]["low"]) == "100"
        assert str(buckets[0]["median"]) == "100"
        all_prices = [
            str(b.get(k, "")) for b in buckets for k in ("low", "median", "high")
        ]
        assert "9999" not in all_prices

        # Machine Price is the deterministic 100 (the snapshot is the
        # machine surface).
        assert result.price_buckets == 1

        # NO review candidate: the V2 MATCH created none, and V1 never
        # evaluated the U5 candidate.
        assert AiAssistedReviewCandidate.objects.filter(
            run=result.run
        ).count() == 0

        # The V2 record persisted with the MATCH outcome...
        records = list(
            SemanticDecisionRecordRow.objects.filter(run=result.run)
        )
        assert len(records) == 1
        loaded = load_semantic_decision(result.run.id, records[0].assessment_index)
        assert isinstance(loaded, SemanticDecisionRecordV2)
        assert loaded.decision is V2SemanticDecision.MATCH
        assert loaded.confidence is V2Confidence.HIGH

    def test_v1_match_still_creates_its_v1_review_candidate(self) -> None:
        """V1 coexistence: a U1 candidate with a V1 MATCH still creates
        the review candidate — bound to V1 provenance (prompt 1.1), not
        to the V2 record. The V2 record for the same candidate coexists
        (persist only)."""
        url_u1 = "https://example.com/title-mpn"
        result = _execute(
            REQUEST_4A,
            {url_u1: _u1_page("500")},
            lambda: _v1_runtime(_v1_response("MATCH")),
            lambda: _v2_runtime(_v2_response("MATCH")),
        )
        assert result.run.current_state == ResearchRunState.COMPLETED
        assert len(result.ai_assisted_matches) == 1

        candidates = list(
            AiAssistedReviewCandidate.objects.filter(run=result.run)
        )
        assert len(candidates) == 1
        # The review candidate carries the V1 provenance (prompt 1.1) —
        # it was created by the V1 path, not by the V2 result.
        assert candidates[0].prompt_version == "1.1"

        # The V2 record for the same candidate coexists in the ledger.
        records = list(SemanticDecisionRecordRow.objects.filter(run=result.run))
        assert len(records) == 1
        loaded = load_semantic_decision(
            result.run.id, records[0].assessment_index
        )
        assert isinstance(loaded, SemanticDecisionRecordV2)
        assert loaded.decision is V2SemanticDecision.MATCH

    def test_u4_reaches_v2_without_any_v1_call(self) -> None:
        """U4 (no-MPN usable title): the V1 predicate never evaluates
        it; the V2 path evaluates it exactly once and persists the
        outcome."""
        url_u4 = "https://example.com/no-mpn"
        u4_page = _json_ld_page(
            {
                "@type": "Product",
                "name": "Usable title product",
                "offers": {
                    "@type": "Offer",
                    "price": "300",
                    "priceCurrency": "USD",
                    "itemCondition": "https://schema.org/NewCondition",
                },
            }
        )
        result = _execute(
            REQUEST_4A,
            {url_u4: u4_page},
            _sentinel_v1_get_default,
            lambda: _v2_runtime(_v2_response("UNCERTAIN", "MEDIUM", "UNCERTAIN_IDENTIFIER_RELATION")),
        )
        assert result.run.current_state == ResearchRunState.COMPLETED
        # The V1 default runtime was NEVER constructed: U4 is not V1-
        # eligible (the sentinel would have failed the run otherwise).
        records = list(SemanticDecisionRecordRow.objects.filter(run=result.run))
        assert len(records) == 1
        loaded = load_semantic_decision(result.run.id, records[0].assessment_index)
        assert loaded.decision is V2SemanticDecision.UNCERTAIN
        assert loaded.case.substate.value == "U4_NO_MPN"

    def test_v2_record_alone_creates_no_human_confirmed_state(self) -> None:
        # A V2 MATCH record by itself is a persistence artifact: no
        # review state exists for it (there is no review candidate to
        # confirm), so no HUMAN_CONFIRMED state can arise from it.
        url_u5 = "https://example.com/near-miss"
        result = _execute(
            REQUEST_4A,
            {url_u5: _u5_page("9999", "TEST-MPNA")},
            _sentinel_v1_get_default,
            lambda: _v2_runtime(_v2_response("MATCH", "HIGH")),
        )
        assert AiAssistedReviewCandidate.objects.filter(
            run=result.run
        ).count() == 0
        # The run completed with the candidate unresolved (no authority
        # tier exists for it beyond the deterministic state).
        assert result.run.current_state == ResearchRunState.COMPLETED

    def test_v2_outcome_does_not_alter_reviewed_price_inputs(self) -> None:
        # Reviewed Price is derived from deterministic ACCEPTED +
        # HUMAN_CONFIRMED evidence. A V2 MATCH creates no review
        # candidate and no human confirmation, so the reviewed
        # aggregation sees exactly the deterministic evidence.
        from product_intelligence.research.aggregation import (
            aggregate_reviewed_listing_prices,
        )

        url_acc = "https://example.com/exact"
        url_u5 = "https://example.com/near-miss"
        result = _execute(
            REQUEST_4A,
            {
                url_acc: _accepted_page("100", "TEST-MPN"),
                url_u5: _u5_page("9999", "TEST-MPNA"),
            },
            lambda: _v1_runtime(_v1_response("NO_MATCH")),
            lambda: _v2_runtime(_v2_response("MATCH", "HIGH")),
        )
        snapshot = result.snapshot
        price_result = decode_price_aggregation_result(
            snapshot.payload, schema_version=snapshot.schema_version
        )
        reviewed = aggregate_reviewed_listing_prices(
            REQUEST_4A,
            price_result.assessments,
            frozenset(),  # no human confirmations exist
        )
        # The reviewed aggregation is deterministic-only: zero human-
        # confirmed entries, and the V2-MATCH price (9999) is absent.
        assert all(
            bucket.human_confirmed_count == 0 for bucket in reviewed.buckets
        )
        for bucket in reviewed.buckets:
            for value in (bucket.low, bucket.median, bucket.high):
                assert str(value) != "9999"
            assert bucket.deterministic_count == bucket.count


# ===========================================================================
# Alias retrieval provenance (the 4D-D customer-retrieval relation)
# ===========================================================================


class TestAliasRetrievalProvenance:
    def test_v2_execution_records_the_customer_relation_provenance(
        self,
    ) -> None:
        # Unit level: a candidate provenance set carrying
        # CUSTOMER_RETRIEVAL_RELATION is recorded in the V2 input, and
        # the derived relationship authority stays NOT_ESTABLISHED
        # (customer retrieval confers zero identity authority).
        from product_intelligence.research import (
            ExtractionMethod,
            ListingObservation,
            derive_relationship_authority,
        )

        request = ResearchRequest("ABC-123", "A test product")
        observation = ListingObservation(
            source_url="https://example.com/u5",
            extraction_method=ExtractionMethod.JSON_LD,
            product_title="Near miss drive",
            manufacturer_part_number_text="ABC-124",
            price_text="200",
            currency_text="USD",
            availability_text="In stock",
            condition_text="New",
        )
        assessment = assess_listing_identity(
            request, normalize_listing_observation(observation)
        )
        provenances = frozenset({ContextProvenance.CUSTOMER_RETRIEVAL_RELATION})
        outcomes = evaluate_semantic_matches_v2(
            request,
            (assessment,),
            context_provenances_by_assessment={assessment: provenances},
            reviewed_target_context=None,
            runtime_v2=_v2_runtime(_v2_response("MATCH", "HIGH")),
        )
        assert len(outcomes) == 1
        assert outcomes[0].case.context_provenances == provenances
        # The recorded case says what it says: the class is the
        # retrieval-only class.
        assert outcomes[0].case.context_provenances == frozenset(
            {ContextProvenance.CUSTOMER_RETRIEVAL_RELATION}
        )
        # Derived: customer retrieval establishes no relationship.
        context = derive_identity_state_v2(assessment)
        assert derive_relationship_authority(context, provenances) is (
            RelationshipAuthority.NOT_ESTABLISHED
        )

        # And the persisted record carries the same derived snapshot.
        run = ResearchRun.objects.create_from_request(request)
        published = aggregate_listing_prices(request, (assessment,)).assessments
        records = build_semantic_decision_records_v2(run, published, outcomes)
        assert records[0].relationship_authority is (
            RelationshipAuthority.NOT_ESTABLISHED
        )
        persist_semantic_decision_records_v2(run, records)
        loaded = load_semantic_decision(run.id, 0)
        assert loaded.case.context_provenances == provenances
        assert loaded.relationship_authority is RelationshipAuthority.NOT_ESTABLISHED


# ===========================================================================
# Replay through the service (full binding verification)
# ===========================================================================


class TestV2ReplayThroughService:
    def test_replay_of_a_persisted_v2_record(self) -> None:
        request = ResearchRequest("ABC-123", "A test product")
        from product_intelligence.research import (
            ExtractionMethod,
            ListingObservation,
        )

        observation = ListingObservation(
            source_url="https://example.com/u1",
            extraction_method=ExtractionMethod.JSON_LD,
            product_title="ABC-123 1TB NVMe Drive",
            price_text="100",
            currency_text="USD",
            availability_text="In stock",
            condition_text="New",
        )
        assessment = assess_listing_identity(
            request, normalize_listing_observation(observation)
        )
        run = ResearchRun.objects.create_from_request(request)
        price_result = aggregate_listing_prices(request, (assessment,))
        PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=PRICE_RESULT_SCHEMA_VERSION,
            payload=encode_price_aggregation_result(price_result),
        )
        outcomes = evaluate_semantic_matches_v2(
            request,
            (assessment,),
            context_provenances_by_assessment={},
            reviewed_target_context=None,
            runtime_v2=_v2_runtime(_v2_response("MATCH", "HIGH")),
        )
        records = build_semantic_decision_records_v2(
            run, price_result.assessments, outcomes
        )
        persist_semantic_decision_records_v2(run, records)

        replay = replay_semantic_decision_record(run.id, 0)
        assert replay.record.decision is V2SemanticDecision.MATCH
        assert replay.contract_binding == V2_CONTRACT_BINDING
        # The exact historical V2 input is reconstructed.
        assert replay.case == records[0].case

    def test_replay_of_a_persisted_v1_record_is_unchanged(self) -> None:
        # The service replay still routes V1 records to the V1 adapter.
        from product_intelligence.research import (
            AttemptOutcome,
            AttemptRole,
        )
        from product_intelligence.research import (
            SemanticDecisionRecordV1,
        )
        from product_intelligence.research.semantic_decision_v1 import (
            SemanticDecisionAttempt,
        )

        request = ResearchRequest("ABC-123", "A test product")
        observation = ListingObservation(
            source_url="https://example.com/u1",
            extraction_method=ExtractionMethod.JSON_LD,
            product_title="ABC-123 1TB NVMe Drive",
            price_text="100",
            currency_text="USD",
            availability_text="In stock",
            condition_text="New",
        )
        assessment = assess_listing_identity(
            request, normalize_listing_observation(observation)
        )
        run = ResearchRun.objects.create_from_request(request)
        price_result = aggregate_listing_prices(request, (assessment,))
        PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=PRICE_RESULT_SCHEMA_VERSION,
            payload=encode_price_aggregation_result(price_result),
        )
        context = derive_identity_state_v2(assessment)
        profile = ProductEvidenceProfileV2(
            has_usable_product_title=True,
            matched_facts=frozenset(
                {
                    ProductEvidenceFactV2(
                        ProductEvidenceDimension.CAPACITY,
                        frozenset(
                            {CandidateProductEvidenceSource.LISTING_PRODUCT_TITLE}
                        ),
                    ),
                    ProductEvidenceFactV2(
                        ProductEvidenceDimension.INTERFACE,
                        frozenset(
                            {CandidateProductEvidenceSource.LISTING_PRODUCT_TITLE}
                        ),
                    ),
                }
            ),
        )
        evaluation = SemanticEvaluationV2.evaluated(
            V2SemanticDecision.MATCH, V2Confidence.HIGH, frozenset()
        )
        tier_decision = derive_authority_tier(
            context, evaluation, frozenset(), profile
        )
        record = SemanticDecisionRecordV1.build(
            run_id=str(run.id),
            assessment_index=0,
            source_url=observation.source_url,
            identity_state=context.state,
            substate=context.substate,
            relationship_signals=context.relationship_signals,
            normalized_requested_part_number=context.normalized_requested_part_number,
            normalized_candidate_part_number=context.normalized_candidate_part_number,
            relationship_requirement=substate_relationship_requirement(
                context.substate, context.primary_relationship_signal
            ),
            product_evidence=profile,
            product_evidence_quality=derive_product_evidence_quality(
                profile, frozenset()
            ),
            context_provenances=frozenset(),
            case_id="candidate-0",
            target_mpn=request.manufacturer_part_number,
            target_description=request.description,
            candidate_title=observation.product_title or "",
            candidate_mpn_field=None,
            candidate_sku=None,
            candidate_specs=None,
            evidence_source="TITLE_TEXT",
            evaluation_state=SemanticEvaluationStateV2.EVALUATED,
            decision=V2SemanticDecision.MATCH,
            confidence=V2Confidence.HIGH,
            conflict_classes=frozenset(),
            reason_code="exact_mpn_match",
            matched_attributes=("mpn",),
            conflicting_attributes=(),
            missing_critical_attributes=(),
            attempts=(
                SemanticDecisionAttempt(
                    AttemptRole.PRIMARY,
                    1,
                    "amax",
                    "qwen3.8-27b",
                    AttemptOutcome.OK,
                ),
            ),
            fallback_used=False,
            fallback_reason=None,
            error_type=None,
            actual_provider="amax",
            actual_model="qwen3.8-27b",
            evaluation_started_at="2026-02-10T12:00:00Z",
            evaluation_finished_at="2026-02-10T12:00:03Z",
            relationship_authority=tier_decision.relationship_authority,
            authority_tier=tier_decision.tier,
            fired_rules=tier_decision.fired_rules,
        )
        from product_intelligence.execution.semantic_decision_persistence import (
            persist_semantic_decision,
        )

        persist_semantic_decision(run, record)
        replay = replay_semantic_decision_record(run.id, 0)
        assert replay.contract_binding == (
            "V1",
            "1.1",
            1,
            1,
            "SEMANTIC_AUTHORITY_V2_S2A_FU2",
        )


# ===========================================================================
# The V1 no-wiring property survives (the V1 path still writes zero
# ledger records by itself)
# ===========================================================================


class TestV1NoWiringSurvives:
    def test_v1_evaluation_alone_writes_no_records(self) -> None:
        # The CURRENT V1 path (evaluate_semantic_matches) still creates
        # and reads ZERO ledger records: only the new V2 wiring writes.
        from product_intelligence.execution.evidence_writer import (
            ExecutionEvidenceWriter,
        )
        from product_intelligence.execution.semantic_integration import (
            evaluate_semantic_matches,
        )
        from product_intelligence.semantic import SemanticRuntime

        observation = ListingObservation(
            source_url="https://example.com/u1",
            extraction_method=ExtractionMethod.JSON_LD,
            product_title="ABC-123 1TB NVMe Drive",
            price_text="100",
            currency_text="USD",
            availability_text="In stock",
            condition_text="New",
        )
        assessment = assess_listing_identity(
            REQUEST, normalize_listing_observation(observation)
        )
        run = ResearchRun.objects.create_from_request(REQUEST)
        writer = ExecutionEvidenceWriter(run)
        runtime = SemanticRuntime(
            primary_transport=FakeSemanticModelTransport(
                responses={"*": _v1_response("MATCH")},
                case_ids=("*",),
                provider_reported_model="qwen3.8-27b",
            ),
            fallback_transport=FakeSemanticModelTransport(
                responses={"*": _v1_response("MATCH")},
                case_ids=("*",),
                provider_reported_model="Qwen3.6-27B-262K",
            ),
        )
        results = evaluate_semantic_matches(
            REQUEST, (assessment,), writer, runtime=runtime
        )
        assert len(results) == 1
        assert SemanticDecisionRecordRow.objects.count() == 0
        assert AiAssistedReviewCandidate.objects.count() == 0
