"""SEMANTIC-V2-A1 — RAW description evidence: the persisted replay chain.

End-to-end proof (zero live AI / provider / network work — fake
transports and recorded-page fakes only) that the page-published
description / specification text:

* is extracted by the bounded 3A rule (the JSON-LD
  ``Product.description`` position) and published as the named
  ``ListingObservation.description_text`` field;
* is persisted by the atomic final publication under the CURRENT
  frozen codec version (schema 2 — the V1 payload plus the additive
  per-observation ``description_text`` key, recorded in
  ``PriceIntelligenceSnapshot.schema_version``);
* is mapped onto the EXISTING V2 ``raw_specification_text`` channel
  (prompt 2.0, model-output enums, authority rules, and the semantic
  ledger codec all UNCHANGED), so the recorded V2 case carries the
  exact bounded RAW evidence supplied to the model;
* survives encoding -> snapshot persistence -> decoding -> V2 case
  construction -> semantic ledger persistence -> zero-live replay;
* changes NO deterministic decision, NO Machine Price, and NO
  historical V1 review / replay authority;
* is never parsed out of the opaque ``raw_reference`` by any business
  layer (AD-040).

Historical schema-1 snapshots remain replay-compatible through the
frozen V1 path; the frozen V1 codec suite passes unchanged.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import EvidenceDecision, ResearchRunState
from product_intelligence.research import (
    CURRENT_PRICE_RESULT_SCHEMA_VERSION,
    PRICE_RESULT_SCHEMA_VERSION,
    PRICE_RESULT_SCHEMA_VERSION_2,
    decode_price_aggregation_result,
    encode_price_aggregation_result,
    encode_price_aggregation_result_v2,
    is_v2_semantic_eligible,
)
from product_intelligence.research.semantic_decision_v2_perf import (
    V2_PERF_CONTRACT_BINDING,
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
from product_intelligence.semantic.runtime import SemanticRuntime
from product_intelligence.semantic.runtime_v2 import (
    FALLBACK_MODEL_V2,
    PRIMARY_MODEL_V2,
    SemanticRuntimeV2,
)
from product_intelligence.semantic.transport import (
    FakeSemanticModelTransport,
    TransportResult,
)

REQUEST = ResearchRequest("MZ-SV2A1-TARGET", "enterprise SSD for datacenters")

DESCRIPTION_TEXT = (
    "3.84TB enterprise NVMe SSD, U.2 15mm, PCIe Gen4 x4, "
    "6900/4100 MB/s sequential read/write, 1 DWPD, 256-bit AES."
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _v1_response(decision: str = "NO_MATCH") -> str:
    return json.dumps(
        {
            "decision": decision,
            "confidence": "HIGH",
            "matched_attributes": [],
            "conflicting_attributes": [],
            "missing_critical_attributes": [],
            "reason_code": "test_reason",
        }
    )


def _v2_response(decision: str = "MATCH", confidence: str = "HIGH") -> str:
    return json.dumps(
        {
            "decision": decision,
            "confidence": confidence,
            "reason_code": "MATCH_DESCRIPTION_AND_ATTRIBUTES",
            "matched_attributes": [],
            "conflicting_attributes": [],
            "missing_critical_attributes": [],
            "conflict_classes": [],
        }
    )


class _RecordingTransport:
    """A bounded in-memory V2 transport double that RECORDS the exact
    prompts the runtime supplies (no live work)."""

    def __init__(self, response: str, model: str = PRIMARY_MODEL_V2) -> None:
        self.response = response
        self.model = model
        self.calls: list[dict] = []

    def complete(self, **kwargs) -> TransportResult:
        self.calls.append(
            {
                "system_prompt": kwargs.get("system_prompt"),
                "user_prompt": kwargs.get("user_prompt"),
                "model": kwargs.get("model"),
            }
        )
        return TransportResult(
            raw_output=self.response,
            latency_ms=1.0,
            provider_status="200",
            provider_id="sv2a1-test",
            model_id=self.model,
            provider_reported_model=self.model,
        )


def _v2_runtime(response: str = _v2_response()) -> SemanticRuntimeV2:
    return SemanticRuntimeV2(
        primary_transport=FakeSemanticModelTransport(
            responses={"UNKNOWN": response},
            provider_reported_model=PRIMARY_MODEL_V2,
        ),
        fallback_transport=FakeSemanticModelTransport(
            responses=None,
            failure_error_types={"UNKNOWN": "CONNECTION_ERROR"},
            provider_reported_model=FALLBACK_MODEL_V2,
        ),
    )


def _v1_runtime(response: str = _v1_response()) -> SemanticRuntime:
    return SemanticRuntime(
        primary_transport=FakeSemanticModelTransport(
            responses={"UNKNOWN": response},
            provider_reported_model="qwen3.8-27b",
        ),
        fallback_transport=FakeSemanticModelTransport(
            responses={"UNKNOWN": response},
            provider_reported_model="Qwen3.6-27B-262K",
        ),
    )


def _json_ld_page(payload: dict) -> str:
    return (
        f'<html><body><script type="application/ld+json">{json.dumps(payload)}'
        "</script></body></html>"
    )


def _u4_page(description: str | None, *, title: str | None = None) -> str:
    """A V2-eligible U4 candidate page (missing MPN, usable title).

    The missing-MPN, description-grounded shape: the page publishes a
    title, a price, and — when ``description`` is not None — the
    page-published description in the JSON-LD ``Product.description``
    position. ``title`` overrides the default page title (the V1 test
    uses a title carrying the requested MPN as a token — the
    TITLE_TEXT evidence source that makes the candidate V1-eligible).
    """
    product = {
        "@type": "Product",
        "name": title or "Generic enterprise SSD 3.84TB U.2",
        "offers": {
            "@type": "Offer",
            "price": "1500.00",
            "priceCurrency": "USD",
            "itemCondition": "https://schema.org/NewCondition",
        },
    }
    if description is not None:
        product["description"] = description
    return _json_ld_page(product)


def _u5_page(description: str | None) -> str:
    """A V2-eligible U5 near-miss candidate page (explicit MPN)."""
    product = {
        "@type": "Product",
        "name": "Near miss drive",
        "mpn": "MZ-SV2A1-TARGETX",
        "offers": {
            "@type": "Offer",
            "price": "9999.00",
            "priceCurrency": "USD",
            "itemCondition": "https://schema.org/NewCondition",
        },
    }
    if description is not None:
        product["description"] = description
    return _json_ld_page(product)


def _exact_page(price: str) -> str:
    """A deterministic ACCEPTED page (the exact requested MPN)."""
    return _json_ld_page(
        {
            "@type": "Product",
            "name": "Exact target drive",
            "mpn": "MZ-SV2A1-TARGET",
            "offers": {
                "@type": "Offer",
                "price": price,
                "priceCurrency": "USD",
                "itemCondition": "https://schema.org/NewCondition",
            },
        }
    )


def _execute(
    url_to_body: dict[str, str],
    *,
    v1_response: str = _v1_response(),
    v2_response: str = _v2_response(),
    v2_recording_transport: _RecordingTransport | None = None,
):
    """One full execute_research_run with bounded fake runtimes."""
    from product_intelligence.execution import execute_research_run
    from product_intelligence.providers.search import SearchProvider

    urls = list(url_to_body)

    search_provider = MagicMock(spec=SearchProvider)
    search_response = MagicMock()
    search_response.provider_id = "test"
    search_results = []
    for url in urls:
        result = MagicMock()
        result.source_url = url
        result.title = "Product"
        result.snippet = "Description"
        result.price_hint_text = None
        result.part_number_hint = None
        result.raw_reference = None
        search_results.append(result)
    search_response.results = tuple(search_results)
    search_provider.search.return_value = search_response

    page_fetcher = MagicMock()

    def _fetch(request):
        body = url_to_body.get(request.url, "<html></html>")
        from product_intelligence.providers.page import FetchedPage

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

    page_fetcher.fetch.side_effect = _fetch

    if v2_recording_transport is None:
        v2_runtime_factory = _v2_runtime(v2_response)
    else:
        v2_runtime_factory = SemanticRuntimeV2(
            primary_transport=v2_recording_transport,
            fallback_transport=FakeSemanticModelTransport(
                responses=None,
                failure_error_types={"UNKNOWN": "CONNECTION_ERROR"},
                provider_reported_model=FALLBACK_MODEL_V2,
            ),
        )

    run = ResearchRun.objects.create_from_request(REQUEST)
    with patch(
        "product_intelligence.execution.semantic_integration."
        "get_default_runtime",
        side_effect=lambda: _v1_runtime(v1_response),
    ), patch(
        "product_intelligence.execution.semantic_decision_v2_execution."
        "get_default_runtime_v2",
        side_effect=[v2_runtime_factory],
    ):
        return execute_research_run(
            str(run.id),
            search_provider=search_provider,
            page_fetcher=page_fetcher,
        )


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Deterministic environment: no direct acquisition, no vendor
    lookup (USD-only runs perform zero FX calls)."""
    monkeypatch.delenv("PI_PREFERRED_SEARCH_DOMAINS", raising=False)
    monkeypatch.delenv("PI_VENDOR_LOOKUP_BASE_URL", raising=False)
    yield
    SemanticDecisionRecordRow.objects.all().delete()
    AiAssistedReviewCandidate.objects.all().delete()
    PriceIntelligenceSnapshot.objects.all().delete()
    ResearchRun.objects.all().delete()


def _decoded_v2_record(run: ResearchRun, index: int = 0):
    """Strictly decode the run's persisted V2 ledger record (the
    recorded case = the exact input the model saw)."""
    record = load_semantic_decision(run.id, index)
    assert (
        record.semantic_contract_version,
        record.prompt_version,
        record.input_schema_version,
        record.output_schema_version,
        record.authority_contract_version,
    ) == V2_PERF_CONTRACT_BINDING
    return record


# ---------------------------------------------------------------------------
# A1-2/A1-4: schema-2 publication + the persisted description
# ---------------------------------------------------------------------------


class TestSchema2Publication:
    def test_a_published_run_persists_schema2_with_the_description(self) -> None:
        url = "https://example.com/u4"
        result = _execute({url: _u4_page(DESCRIPTION_TEXT)})

        assert result.run.current_state is ResearchRunState.COMPLETED
        snapshot = PriceIntelligenceSnapshot.objects.get(run=result.run)
        # Publication selects the encoder + recorded version from the
        # frozen constant (advanced to 2 under the gated A1 approval).
        assert snapshot.schema_version == CURRENT_PRICE_RESULT_SCHEMA_VERSION
        assert snapshot.schema_version == PRICE_RESULT_SCHEMA_VERSION_2

        observation = (
            snapshot.payload["assessments"][0]["normalized_listing"]["observation"]
        )
        # The additive key is present with the exact published text.
        assert observation["description_text"] == DESCRIPTION_TEXT

        # The dispatcher decodes the run's OWN payload back to the
        # in-memory result (lossless).
        decoded = decode_price_aggregation_result(
            snapshot.payload, schema_version=snapshot.schema_version
        )
        assert decoded.request == result.run.to_research_request()
        assert (
            decoded.assessments[0].normalized_listing.observation.description_text
            == DESCRIPTION_TEXT
        )

    def test_a_run_without_description_persists_schema2_with_explicit_null(
        self,
    ) -> None:
        url = "https://example.com/u4"
        result = _execute({url: _u4_page(None)})

        snapshot = PriceIntelligenceSnapshot.objects.get(run=result.run)
        assert snapshot.schema_version == PRICE_RESULT_SCHEMA_VERSION_2
        observation = (
            snapshot.payload["assessments"][0]["normalized_listing"]["observation"]
        )
        # The key is ALWAYS present; null when absent (no omission, no
        # defaulting).
        assert "description_text" in observation
        assert observation["description_text"] is None


# ---------------------------------------------------------------------------
# A1-3: the recorded V2 case carries the exact bounded RAW evidence
# ---------------------------------------------------------------------------


class TestV2RawInputPropagation:
    def test_the_model_receives_the_published_description_as_raw_text(self) -> None:
        url = "https://example.com/u4"
        recorder = _RecordingTransport(_v2_response())
        result = _execute(
            {url: _u4_page(DESCRIPTION_TEXT)}, v2_recording_transport=recorder
        )

        assert result.run.current_state is ResearchRunState.COMPLETED
        assert len(recorder.calls) == 1
        user_prompt = recorder.calls[0]["user_prompt"]
        # The EXACT bounded RAW evidence supplied to the model, rendered
        # under the frozen 2.0 raw-observation label (prompt text
        # unchanged).
        assert f'- Specification text: "{DESCRIPTION_TEXT}"' in user_prompt
        assert "Raw observation text" in user_prompt
        # Prompt 2.0 identity: the frozen system prompt is what the
        # runtime supplies (no prompt change in this phase).
        assert recorder.calls[0]["system_prompt"]

    def test_the_recorded_v2_case_carries_the_published_description(self) -> None:
        url = "https://example.com/u4"
        result = _execute({url: _u4_page(DESCRIPTION_TEXT)})

        record = _decoded_v2_record(result.run)
        assert (
            record.case.candidate_product.raw_specification_text
            == DESCRIPTION_TEXT
        )
        # The raw title channel is unchanged and distinct.
        assert (
            record.case.candidate_product.raw_title_text
            == "Generic enterprise SSD 3.84TB U.2"
        )
        # The description is RAW: NO structured product dimension was
        # derived from its tokens (capacity / interface / form factor
        # all stay explicit absences).
        product = record.case.candidate_product
        assert product.capacity is None
        assert product.interface is None
        assert product.form_factor is None
        assert product.product_family is None
        assert product.generation is None

    def test_the_recorded_v2_case_carries_explicit_null_when_absent(self) -> None:
        url = "https://example.com/u4"
        result = _execute({url: _u4_page(None)})

        record = _decoded_v2_record(result.run)
        assert record.case.candidate_product.raw_specification_text is None


# ---------------------------------------------------------------------------
# A1-4: zero-live replay over the schema-2 chain
# ---------------------------------------------------------------------------


class TestZeroLiveReplay:
    def test_schema2_description_survives_zero_live_replay(self) -> None:
        url = "https://example.com/u4"
        result = _execute({url: _u4_page(DESCRIPTION_TEXT)})

        # The zero-live replay re-verifies the record's digest, the
        # request identity, and the snapshot assessment binding —
        # decoding the run's OWN persisted schema-2 payload through the
        # dispatcher, with no network, no re-fetch, and no raw_reference
        # parse.
        replay = replay_semantic_decision_record(result.run.id, 0)
        assert replay.case == _decoded_v2_record(result.run).case
        assert (
            replay.case.candidate_product.raw_specification_text
            == DESCRIPTION_TEXT
        )

    def test_historical_schema1_snapshot_still_replays(self) -> None:
        """A schema-1 (V1) snapshot row with a V2 record replays exactly
        as before the phase — the dispatcher routes it through the
        frozen V1 path (historical behavior preserved)."""
        from product_intelligence.research import (
            ExtractionMethod,
            ListingObservation,
            aggregate_listing_prices,
            assess_listing_identity,
            normalize_listing_observation,
        )
        from product_intelligence.execution.semantic_decision_v2_execution import (
            build_semantic_decision_records_v2,
            evaluate_semantic_matches_v2,
            persist_semantic_decision_records_v2,
        )

        run = ResearchRun.objects.create_from_request(REQUEST)
        observation = ListingObservation(
            source_url="https://example.com/hist",
            extraction_method=ExtractionMethod.JSON_LD,
            product_title="Historical drive",
            price_text="100",
            currency_text="USD",
            availability_text="In stock",
            condition_text="New",
        )
        assessment = assess_listing_identity(
            REQUEST, normalize_listing_observation(observation)
        )
        assert is_v2_semantic_eligible(assessment)
        # The HISTORICAL publication shape: schema 1, the frozen V1
        # encoder, no description_text key anywhere.
        price_result = aggregate_listing_prices(REQUEST, (assessment,))
        payload = encode_price_aggregation_result(price_result)
        PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=PRICE_RESULT_SCHEMA_VERSION,
            payload=payload,
        )
        outcomes = evaluate_semantic_matches_v2(
            REQUEST,
            (assessment,),
            context_provenances_by_assessment={},
            reviewed_target_context=None,
            runtime_v2=_v2_runtime(),
        )
        records = build_semantic_decision_records_v2(
            run, price_result.assessments, outcomes
        )
        persist_semantic_decision_records_v2(run, records)

        # The zero-live replay works over the schema-1 snapshot ...
        replay = replay_semantic_decision_record(run.id, 0)
        # ... and the recorded case carries the historical channel state.
        assert (
            replay.case.candidate_product.raw_specification_text is None
        )


# ---------------------------------------------------------------------------
# A1-1 (test 9): no automatic change in deterministic matching / pricing
# ---------------------------------------------------------------------------


class TestDeterministicInvariance:
    def test_the_description_changes_no_deterministic_decision(self) -> None:
        """The 3B/3C decisions over the same page are identical with and
        without the published description: the field is evidence for the
        RAW semantic channel only, never a deterministic input."""
        url_with = "https://example.com/u4"
        result_with = _execute({url_with: _u4_page(DESCRIPTION_TEXT)})
        url_without = "https://example.com/u4"
        result_without = _execute({url_without: _u4_page(None)})

        with_decoded = decode_price_aggregation_result(
            result_with.snapshot.payload,
            schema_version=result_with.snapshot.schema_version,
        )
        without_decoded = decode_price_aggregation_result(
            result_without.snapshot.payload,
            schema_version=result_without.snapshot.schema_version,
        )
        a_with = with_decoded.assessments[0]
        a_without = without_decoded.assessments[0]
        assert a_with.decision is a_without.decision
        assert a_with.match_type is a_without.match_type
        assert a_with.candidate_evidence_source is a_without.candidate_evidence_source
        assert a_with.rejection_reason is a_without.rejection_reason
        # The only observation difference is the additive field itself.
        obs_with = a_with.normalized_listing.observation
        obs_without = a_without.normalized_listing.observation
        assert obs_with.description_text == DESCRIPTION_TEXT
        assert obs_without.description_text is None
        for name in (
            "source_url",
            "extraction_method",
            "product_title",
            "manufacturer_part_number_text",
            "sku_text",
            "brand_text",
            "price_text",
            "currency_text",
            "availability_text",
            "condition_text",
            "seller_text",
            "offer_url_text",
        ):
            assert getattr(obs_with, name) == getattr(obs_without, name), name

    def test_the_description_changes_no_machine_price(self) -> None:
        """With a deterministic ACCEPTED candidate (exact MPN) on the page
        set, the 4A bucket is the exact price in BOTH runs; the U4
        candidate's published description never adds, moves, or alters
        any Machine Price figure."""
        urls = {
            "https://example.com/exact": _exact_page("800.00"),
            "https://example.com/u4": None,  # filled per run below
        }

        def _run(description: str | None):
            return _execute(
                {
                    "https://example.com/exact": urls["https://example.com/exact"],
                    "https://example.com/u4": _u4_page(description),
                }
            )

        result_with = _run(DESCRIPTION_TEXT)
        result_without = _run(None)

        for result in (result_with, result_without):
            decoded = decode_price_aggregation_result(
                result.snapshot.payload, schema_version=result.snapshot.schema_version
            )
            buckets = [
                (
                    b.currency_code,
                    str(b.low),
                    str(b.median),
                    str(b.high),
                    b.count,
                )
                for b in decoded.buckets
            ]
            # Exactly the deterministic exact-MPN price; the U4 1500.00
            # (with or without description) is never a Machine Price.
            assert buckets == [("USD", "800.00", "800.00", "800.00", 1)], buckets

    def test_a_v2_match_stays_out_of_machine_price_with_description(self) -> None:
        """Authority firewall preserved over the new evidence shape: the
        U5 near miss (with published description) gets a V2 MATCH, yet
        its 9999 price never enters a 4A bucket."""
        url_u5 = "https://example.com/u5"
        result = _execute({url_u5: _u5_page(DESCRIPTION_TEXT)})

        record = _decoded_v2_record(result.run)
        assert record.evaluation_state.value == "EVALUATED"
        assert record.decision.value == "MATCH"
        decoded = decode_price_aggregation_result(
            result.snapshot.payload, schema_version=result.snapshot.schema_version
        )
        prices = [
            str(value)
            for bucket in decoded.buckets
            for value in (bucket.low, bucket.median, bucket.high)
        ]
        assert prices == []
        # No V2 human-review candidate exists (SV2-B scope, not A1).
        assert AiAssistedReviewCandidate.objects.filter(run=result.run).count() == 0


# ---------------------------------------------------------------------------
# A1-1 (test 10): no modification to historical V1 review / replay authority
# ---------------------------------------------------------------------------


class TestV1AuthorityUnchanged:
    def _v1_candidate_rows(self, result) -> list[tuple]:
        rows = AiAssistedReviewCandidate.objects.filter(run=result.run)
        return sorted(
            (
                r.assessment_index,
                r.source_url,
                r.target_mpn,
                r.target_description,
                r.candidate_title,
                r.candidate_mpn_field,
                r.candidate_sku,
                r.candidate_specs,
                r.evidence_source,
                r.semantic_confidence,
                r.semantic_reason_code,
                r.review_state,
            )
            for r in rows
        )

    def test_the_v1_review_candidate_is_identical_with_and_without_description(
        self,
    ) -> None:
        """The V1 review path is byte-identical in its persisted
        authority surface: a U4 candidate (V1-eligible via the
        TITLE_TEXT source — the requested MPN as a title token) with and
        without the published description produces the same V1 candidate
        rows — the description never enters the V1 evidence or the V1
        decision."""
        url = "https://example.com/u4"
        title = "MZ-SV2A1-TARGET enterprise SSD 3.84TB U.2"
        v1_match = _v1_response("MATCH")
        result_with = _execute(
            {url: _u4_page(DESCRIPTION_TEXT, title=title)}, v1_response=v1_match
        )
        result_without = _execute(
            {url: _u4_page(None, title=title)}, v1_response=v1_match
        )

        rows_with = self._v1_candidate_rows(result_with)
        rows_without = self._v1_candidate_rows(result_without)
        assert rows_with == rows_without
        # The V1 path actually ran (one V1-eligible candidate, MATCH):
        # the surface is identical, non-empty, and carries no
        # description material.
        assert len(rows_with) == 1
        for row in rows_with:
            assert DESCRIPTION_TEXT not in repr(row)


# ---------------------------------------------------------------------------
# A1-1 (test 8): no raw_reference authority parsing
# ---------------------------------------------------------------------------


class TestNoRawReferenceAuthority:
    def test_business_layers_never_parse_raw_reference_for_the_description(self) -> None:
        """An observation whose opaque raw_reference contains
        description-shaped material but whose NAMED field is absent
        yields an absent V2 channel: no business layer re-parses the
        reference (AD-040)."""
        from product_intelligence.research import (
            ExtractionMethod,
            ListingObservation,
            assess_listing_identity,
            build_candidate_product_evidence_v2,
            derive_identity_state_v2,
            build_semantic_match_case_v2,
            build_v2_product_evidence_profile,
            normalize_listing_observation,
        )

        observation = ListingObservation(
            source_url="https://example.com/opaque",
            extraction_method=ExtractionMethod.JSON_LD,
            product_title="Opaque drive",
            price_text="100",
            currency_text="USD",
            availability_text="In stock",
            condition_text="New",
            # The reference publishes description-shaped material ...
            raw_reference=(
                '{"@type": "Product", "description": '
                '"a description only the opaque reference carries"}'
            ),
            # ... but the extractor's bounded rule published none.
            description_text=None,
        )
        assessment = assess_listing_identity(
            REQUEST, normalize_listing_observation(observation)
        )
        context = derive_identity_state_v2(assessment)
        profile = build_v2_product_evidence_profile(
            observation=observation,
            context_provenances=frozenset(),
            matched_facts=frozenset(),
        )
        case = build_semantic_match_case_v2(
            case_id="opaque-0",
            request=REQUEST,
            assessment=assessment,
            context=context,
            product_evidence=profile,
            context_provenances=frozenset(),
            reviewed_target_context=None,
        )
        assert case.candidate_product.raw_specification_text is None

    def test_normalization_and_matching_ignore_the_description_field(self) -> None:
        """3B normalization and 3C matching are pure functions of the
        pre-existing fields: the description changes no normalization
        issue, no normalized commercial value, and no assessment."""
        from product_intelligence.research import (
            ExtractionMethod,
            ListingObservation,
            assess_listing_identity,
            normalize_listing_observation,
        )

        def _observation(description: str | None) -> ListingObservation:
            return ListingObservation(
                source_url="https://example.com/inv",
                extraction_method=ExtractionMethod.JSON_LD,
                product_title="Invariant drive",
                manufacturer_part_number_text="MZ-SV2A1-TARGETX",
                price_text="100.00",
                currency_text="USD",
                availability_text="In stock",
                condition_text="New",
                description_text=description,
            )

        with_desc = _observation(DESCRIPTION_TEXT)
        without_desc = _observation(None)
        norm_with = normalize_listing_observation(with_desc)
        norm_without = normalize_listing_observation(without_desc)
        assert norm_with.price_amount == norm_without.price_amount
        assert norm_with.currency_code == norm_without.currency_code
        assert norm_with.availability == norm_without.availability
        assert norm_with.condition == norm_without.condition
        assert norm_with.seller_name == norm_without.seller_name
        assert norm_with.normalization_issues == norm_without.normalization_issues

        assess_with = assess_listing_identity(REQUEST, norm_with)
        assess_without = assess_listing_identity(REQUEST, norm_without)
        assert assess_with.decision is assess_without.decision
        assert assess_with.match_type is assess_without.match_type
        assert assess_with.rejection_reason is assess_without.rejection_reason
