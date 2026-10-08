"""Q3-A-FU1 direct-model capture contract tests.

Mandated properties 1-3, 7-12, 14-15 of the FU1 test list as they
apply at the capture-artifact level: existing production-route
captures remain readable; the production-route fallback discipline is
untouched; direct-model primary and fallback captures work
independently; the direct-model fallback requires no fake primary
failure; cross-mode decoding fails closed; wrong / unknown
provider/model fails closed; duplicate / unknown case IDs fail
closed; corpus digest and prompt/contract mismatches fail closed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.evaluation.semantic_v2._q3a_helpers import (
    load_corpus_bundle,
    primary_route,
    fallback_route,
    write_capture,
)
from tests.evaluation.semantic_v2._q3a_fu1_helpers import (
    write_direct_capture,
)
from product_intelligence.evaluation.semantic_v2.capture import (
    CaptureError,
    load_capture,
    verify_capture_against_corpus,
)
from product_intelligence.evaluation.semantic_v2.direct_capture import (
    DirectCaptureError,
    DirectCaptureIntegrityError,
    load_direct_capture,
    verify_direct_capture_against_corpus,
)


@pytest.fixture(scope="module")
def corpus():
    return load_corpus_bundle()


def _mutate(path: Path, mutate) -> Path:
    """Load a written capture document, apply one mutation, re-write it,
    and return the path (tamper fixtures for the strict decoders)."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    mutate(doc)
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


# ===========================================================================
# 1. Existing production-route captures remain readable (unchanged)
# ===========================================================================


class TestProductionRouteCaptureUnchanged:
    def test_production_capture_still_loads(self, corpus, tmp_path) -> None:
        path = write_capture(tmp_path / "prod.json", corpus)
        doc = load_capture(path)
        verify_capture_against_corpus(doc, corpus)
        assert len(doc.records) == 43

    def test_production_fallback_still_never_after_primary_success(
        self, corpus, tmp_path
    ) -> None:
        """The frozen production-route discipline: a successful primary
        makes the answer final; a fallback attempt after it is outside
        the contract (unchanged by FU1)."""
        case_id = "V2Q-SSD-ATTR-CAPACITY-0024"
        path = write_capture(tmp_path / "prod.json", corpus)
        doc = json.loads(path.read_text(encoding="utf-8"))
        record = next(r for r in doc["records"] if r["case_id"] == case_id)
        record["attempts"].append(
            {
                "role": "FALLBACK",
                "provider": fallback_route()[0],
                "model": fallback_route()[1],
                "status": "OK",
                "raw_output": json.dumps({"decision": "MATCH"}),
            }
        )
        record["fallback_used"] = True
        record["fallback_reason"] = "TIMEOUT"
        path.write_text(json.dumps(doc), encoding="utf-8")
        with pytest.raises(CaptureError, match="primary attempt is OK"):
            load_capture(path)

    def test_production_fallback_still_execution_failure_only(
        self, corpus, tmp_path
    ) -> None:
        """A non-fallback-eligible primary failure still cannot have a
        second attempt (unchanged by FU1)."""
        case_id = "V2Q-SSD-ATTR-CAPACITY-0024"
        path = write_capture(tmp_path / "prod.json", corpus)
        doc = json.loads(path.read_text(encoding="utf-8"))
        record = next(r for r in doc["records"] if r["case_id"] == case_id)
        record["attempts"] = [
            {
                "role": "PRIMARY",
                "provider": primary_route()[0],
                "model": primary_route()[1],
                "status": "PROVIDER_NOT_CONFIGURED",
                "raw_output": None,
            },
            {
                "role": "FALLBACK",
                "provider": fallback_route()[0],
                "model": fallback_route()[1],
                "status": "OK",
                "raw_output": json.dumps({"decision": "MATCH"}),
            },
        ]
        record["fallback_used"] = True
        record["fallback_reason"] = "TIMEOUT"
        path.write_text(json.dumps(doc), encoding="utf-8")
        with pytest.raises(CaptureError, match="fallback-eligible"):
            load_capture(path)


# ===========================================================================
# 4-6. Direct-model primary / fallback captures work independently
# ===========================================================================


class TestDirectCaptureIndependence:
    def test_primary_direct_capture_works_independently(
        self, corpus, tmp_path
    ) -> None:
        path = write_direct_capture(tmp_path / "p.json", corpus)
        doc = load_direct_capture(path)
        verify_direct_capture_against_corpus(doc, corpus)
        assert doc.target_route == primary_route()
        assert len(doc.records) == 43
        assert all(r.execution_status == "OK" for r in doc.records)
        # One bounded execution per case: no attempts, no roles.
        raw = json.loads(path.read_text(encoding="utf-8"))
        for record in raw["records"]:
            assert set(record.keys()) == {
                "case_id",
                "execution_status",
                "raw_output",
            }

    def test_fallback_direct_capture_works_independently(
        self, corpus, tmp_path
    ) -> None:
        path = write_direct_capture(
            tmp_path / "f.json", corpus, target=fallback_route()
        )
        doc = load_direct_capture(path)
        verify_direct_capture_against_corpus(doc, corpus)
        assert doc.target_route == fallback_route()
        assert len(doc.records) == 43

    def test_fallback_direct_capture_requires_no_primary_failure(
        self, corpus, tmp_path
    ) -> None:
        """The fallback model is captured DIRECTLY: its capture carries
        no primary attempt at all, succeeded or failed - qualifying the
        fallback never requires manufacturing a primary failure."""
        path = write_direct_capture(
            tmp_path / "f.json", corpus, target=fallback_route()
        )
        raw = json.loads(path.read_text(encoding="utf-8"))
        assert "attempts" not in raw
        for record in raw["records"]:
            assert "role" not in record
            assert "attempts" not in record
        doc = load_direct_capture(path)
        assert all(
            record.raw_output is not None for record in doc.records
        )

    def test_direct_capture_failure_records_are_bounded(
        self, corpus, tmp_path
    ) -> None:
        case_a = "V2Q-SSD-ATTR-CAPACITY-0024"
        case_b = "V2Q-SSD-U4-THIN-0015"
        path = write_direct_capture(
            tmp_path / "c.json",
            corpus,
            failures={case_a: "TIMEOUT", case_b: "CONNECTION_ERROR"},
        )
        doc = load_direct_capture(path)
        verify_direct_capture_against_corpus(doc, corpus)
        by_id = {r.case_id: r for r in doc.records}
        assert by_id[case_a].execution_status == "TIMEOUT"
        assert by_id[case_a].raw_output is None
        assert by_id[case_b].execution_status == "CONNECTION_ERROR"
        assert by_id[case_b].raw_output is None

    def test_distinct_run_ids_and_provenance_are_preserved(
        self, corpus, tmp_path
    ) -> None:
        p1 = write_direct_capture(
            tmp_path / "a.json", corpus, capture_run_id="RUN-A"
        )
        p2 = write_direct_capture(
            tmp_path / "b.json",
            corpus,
            target=fallback_route(),
            capture_run_id="RUN-B",
            captured_at="2026-10-09T00:00:00Z",
        )
        d1, d2 = load_direct_capture(p1), load_direct_capture(p2)
        assert d1.capture_run_id == "RUN-A"
        assert d2.capture_run_id == "RUN-B"
        assert d1.captured_at == "2026-10-08T12:00:00Z"
        assert d2.captured_at == "2026-10-09T00:00:00Z"
        # Two runs, two models, two distinct documents: nothing is
        # shared or combined.
        assert d1.target_route != d2.target_route


# ===========================================================================
# 7. Cross-mode decoding fails closed (both directions)
# ===========================================================================


class TestCrossModeDecodingFailsClosed:
    def test_production_document_is_rejected_by_the_direct_loader(
        self, corpus, tmp_path
    ) -> None:
        path = write_capture(tmp_path / "prod.json", corpus)
        with pytest.raises(DirectCaptureIntegrityError, match="cross-mode"):
            load_direct_capture(path)

    def test_direct_document_is_rejected_by_the_production_loader(
        self, corpus, tmp_path
    ) -> None:
        path = write_direct_capture(tmp_path / "direct.json", corpus)
        with pytest.raises(CaptureError, match="missing required keys"):
            load_capture(path)

    def test_a_production_mode_label_on_a_direct_shape_is_rejected(
        self, corpus, tmp_path
    ) -> None:
        path = write_direct_capture(tmp_path / "direct.json", corpus)
        path = _mutate(
            path, lambda doc: doc.__setitem__("capture_mode", "PRODUCTION_ROUTE")
        )
        with pytest.raises(
            DirectCaptureIntegrityError, match="PRODUCTION_ROUTE"
        ):
            load_direct_capture(path)

    def test_an_unknown_capture_mode_is_rejected(
        self, corpus, tmp_path
    ) -> None:
        path = write_direct_capture(tmp_path / "direct.json", corpus)
        path = _mutate(
            path, lambda doc: doc.__setitem__("capture_mode", "HYBRID")
        )
        with pytest.raises(DirectCaptureError, match="unknown capture mode"):
            load_direct_capture(path)

    def test_a_hybrid_document_with_both_key_sets_is_rejected_everywhere(
        self, corpus, tmp_path
    ) -> None:
        path = write_direct_capture(tmp_path / "hybrid.json", corpus)
        path = _mutate(
            path, lambda doc: doc.__setitem__("capture_schema_version", 1)
        )
        with pytest.raises(CaptureError, match="unknown keys"):
            load_capture(path)
        with pytest.raises(DirectCaptureError, match="unknown keys"):
            load_direct_capture(path)


# ===========================================================================
# 9-10. Wrong / unknown provider-model fails closed
# ===========================================================================


class TestModelIdentityBinding:
    @pytest.mark.parametrize(
        "target",
        [
            (fallback_route()[0], primary_route()[1]),  # mixed
            (primary_route()[0], fallback_route()[1]),  # mixed
            ("not-a-pinned-provider", "not-a-pinned-model"),  # unknown
            (primary_route()[0], "qwen3.9-99b"),  # unknown model
        ],
        ids=["fb-provider-p-model", "p-provider-f-model", "unknown",
             "unknown-model"],
    )
    def test_non_pinned_targets_fail_closed(
        self, corpus, tmp_path, target
    ) -> None:
        path = write_direct_capture(
            tmp_path / "c.json", corpus, target=target
        )
        with pytest.raises(
            DirectCaptureIntegrityError, match="pinned route"
        ):
            load_direct_capture(path)

    def test_pinned_targets_round_trip(self, corpus, tmp_path) -> None:
        for route in (primary_route(), fallback_route()):
            path = write_direct_capture(
                tmp_path / f"{route[0]}.json", corpus, target=route
            )
            doc = load_direct_capture(path)
            assert doc.target_provider == route[0]
            assert doc.target_model == route[1]


# ===========================================================================
# 11-12, 14-15. Duplicate / unknown case ids, digest, prompt/contract
# ===========================================================================


class TestCaseIdentityBinding:
    def test_duplicate_case_id_fails_closed(self, corpus, tmp_path) -> None:
        path = write_direct_capture(tmp_path / "c.json", corpus)
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["records"].append(dict(doc["records"][0]))
        path.write_text(json.dumps(doc), encoding="utf-8")
        with pytest.raises(DirectCaptureError, match="duplicate"):
            load_direct_capture(path)

    def test_unknown_case_id_fails_closed(self, corpus, tmp_path) -> None:
        path = write_direct_capture(tmp_path / "c.json", corpus)
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["records"].append(
            {
                "case_id": "V2Q-SSD-NO-SUCH-CASE-9999",
                "execution_status": "OK",
                "raw_output": json.dumps({"decision": "UNCERTAIN"}),
            }
        )
        path.write_text(json.dumps(doc), encoding="utf-8")
        loaded = load_direct_capture(path)
        with pytest.raises(
            DirectCaptureIntegrityError, match="not in the bound corpus"
        ):
            verify_direct_capture_against_corpus(loaded, corpus)

    def test_contract_negative_case_record_fails_closed(
        self, corpus, tmp_path
    ) -> None:
        cn_id = next(
            c.case_id
            for c in corpus.cases
            if c.case_class == "CONTRACT_NEGATIVE"
        )
        path = write_direct_capture(tmp_path / "c.json", corpus)
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["records"].append(
            {
                "case_id": cn_id,
                "execution_status": "OK",
                "raw_output": json.dumps({"decision": "MATCH"}),
            }
        )
        path.write_text(json.dumps(doc), encoding="utf-8")
        loaded = load_direct_capture(path)
        with pytest.raises(
            DirectCaptureIntegrityError, match="schema-bypass"
        ):
            verify_direct_capture_against_corpus(loaded, corpus)

    def test_corpus_digest_mismatch_fails_closed(self, corpus, tmp_path) -> None:
        path = write_direct_capture(tmp_path / "c.json", corpus)
        path = _mutate(
            path,
            lambda doc: doc.__setitem__(
                "corpus_digest", "0" * 64
            ),
        )
        loaded = load_direct_capture(path)
        with pytest.raises(
            DirectCaptureIntegrityError, match="different corpus"
        ):
            verify_direct_capture_against_corpus(loaded, corpus)

    def test_corpus_version_mismatch_fails_closed(self, corpus, tmp_path) -> None:
        path = write_direct_capture(tmp_path / "c.json", corpus)
        path = _mutate(
            path, lambda doc: doc.__setitem__("corpus_version", "9.9.9")
        )
        loaded = load_direct_capture(path)
        with pytest.raises(
            DirectCaptureIntegrityError, match="different corpus"
        ):
            verify_direct_capture_against_corpus(loaded, corpus)

    def test_prompt_version_mismatch_fails_closed(self, corpus, tmp_path) -> None:
        path = write_direct_capture(tmp_path / "c.json", corpus)
        path = _mutate(
            path, lambda doc: doc.__setitem__("prompt_version", "1.1")
        )
        with pytest.raises(
            DirectCaptureIntegrityError, match="prompt_version"
        ):
            load_direct_capture(path)

    def test_semantic_contract_mismatch_fails_closed(
        self, corpus, tmp_path
    ) -> None:
        path = write_direct_capture(tmp_path / "c.json", corpus)
        path = _mutate(
            path, lambda doc: doc.__setitem__("semantic_contract", "V1")
        )
        with pytest.raises(
            DirectCaptureIntegrityError, match="semantic_contract"
        ):
            load_direct_capture(path)

    def test_missing_semantic_cases_are_allowed_and_surface_later(
        self, corpus, tmp_path
    ) -> None:
        """A direct capture that omits eligible cases is NOT a load
        error: the cases surface as NOT_CAPTURED at evaluation (a
        coverage shortfall, never a pass)."""
        omitted = [
            c.case_id
            for c in corpus.semantic_cases[:2]
        ]
        path = write_direct_capture(
            tmp_path / "c.json", corpus, missing=tuple(omitted)
        )
        doc = load_direct_capture(path)
        verify_direct_capture_against_corpus(doc, corpus)  # must not raise
        assert len(doc.records) == 43 - 2


# ===========================================================================
# Schema strictness (fail closed, no optional-field ambiguity)
# ===========================================================================


class TestSchemaStrictness:
    def test_unknown_document_key_is_rejected(self, corpus, tmp_path) -> None:
        path = write_direct_capture(tmp_path / "c.json", corpus)
        path = _mutate(path, lambda doc: doc.__setitem__("extra", 1))
        with pytest.raises(DirectCaptureError, match="unknown keys"):
            load_direct_capture(path)

    def test_missing_document_key_is_rejected(self, corpus, tmp_path) -> None:
        path = write_direct_capture(tmp_path / "c.json", corpus)
        doc = json.loads(path.read_text(encoding="utf-8"))
        del doc["notes"]
        path.write_text(json.dumps(doc), encoding="utf-8")
        with pytest.raises(DirectCaptureError, match="missing required keys"):
            load_direct_capture(path)

    def test_unknown_schema_version_is_rejected(self, corpus, tmp_path) -> None:
        path = write_direct_capture(tmp_path / "c.json", corpus)
        path = _mutate(
            path,
            lambda doc: doc.__setitem__("direct_capture_schema_version", 2),
        )
        with pytest.raises(DirectCaptureError, match="schema version"):
            load_direct_capture(path)

    def test_unknown_execution_status_is_rejected(self, corpus, tmp_path) -> None:
        path = write_direct_capture(tmp_path / "c.json", corpus)
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["records"][0]["execution_status"] = "PARTLY_OK"
        path.write_text(json.dumps(doc), encoding="utf-8")
        with pytest.raises(DirectCaptureError, match="unknown bounded status"):
            load_direct_capture(path)

    def test_a_configuration_status_is_not_a_model_execution_status(
        self, corpus, tmp_path
    ) -> None:
        path = write_direct_capture(tmp_path / "c.json", corpus)
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["records"][0]["execution_status"] = "PROVIDER_NOT_CONFIGURED"
        doc["records"][0]["raw_output"] = None
        path.write_text(json.dumps(doc), encoding="utf-8")
        with pytest.raises(DirectCaptureError, match="unknown bounded status"):
            load_direct_capture(path)

    def test_a_failed_status_with_raw_output_is_rejected(
        self, corpus, tmp_path
    ) -> None:
        path = write_direct_capture(tmp_path / "c.json", corpus)
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["records"][0]["execution_status"] = "TIMEOUT"
        doc["records"][0]["raw_output"] = json.dumps({"decision": "MATCH"})
        path.write_text(json.dumps(doc), encoding="utf-8")
        with pytest.raises(DirectCaptureError, match="carries no raw output"):
            load_direct_capture(path)

    def test_an_ok_status_without_raw_output_is_rejected(
        self, corpus, tmp_path
    ) -> None:
        path = write_direct_capture(tmp_path / "c.json", corpus)
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["records"][0]["raw_output"] = None
        path.write_text(json.dumps(doc), encoding="utf-8")
        with pytest.raises(
            DirectCaptureError, match="must carry the raw model output"
        ):
            load_direct_capture(path)

    def test_an_empty_run_id_is_rejected(self, corpus, tmp_path) -> None:
        path = write_direct_capture(tmp_path / "c.json", corpus)
        path = _mutate(path, lambda doc: doc.__setitem__("capture_run_id", ""))
        with pytest.raises(DirectCaptureError, match="capture_run_id"):
            load_direct_capture(path)

    def test_an_invalid_instant_is_rejected(self, corpus, tmp_path) -> None:
        path = write_direct_capture(tmp_path / "c.json", corpus)
        path = _mutate(
            path, lambda doc: doc.__setitem__("captured_at", "yesterday")
        )
        with pytest.raises(DirectCaptureError, match="ISO-8601"):
            load_direct_capture(path)
