"""Q3-A corpus integrity tests.

Mandated properties 1-5, 7, 8 of the Q3-A test list (corpus schema
validation; independent label provenance; synthetic vs real evidence
classification; corpus digest stability; label mutation changes the
digest; duplicate case id fails closed; unknown corpus version fails
closed) plus the sealed-corpus invariants (regeneration fidelity,
manifest reproducibility, mandated coverage, the motivating Micron
case).
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from tests.evaluation.semantic_v2._q3a_helpers import (
    CORPUS_PATH,
    MANIFEST_PATH,
    load_corpus_bundle,
)
from product_intelligence.evaluation.semantic_v2.corpus import (
    CorpusIntegrityError,
    CorpusSchemaError,
    build_manifest_document,
    load_corpus,
    verify_manifest,
)
from product_intelligence.evaluation.semantic_v2.fixtures import (
    FORBIDDEN_EVIDENCE_TOKENS,
    build_corpus_document,
)


@pytest.fixture(scope="module")
def corpus():
    return load_corpus_bundle()


def _write(tmp_path: Path, doc: dict, name: str = "corpus.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _reseal_case(case: dict) -> None:
    """Recompute one case's digest after a mutation, so that the schema
    checks (not the digest checks) surface for schema-level tests."""
    from product_intelligence.evaluation.semantic_v2.canonical import (
        canonical_sha256,
    )

    state_view = {k: v for k, v in case.items() if k != "case_digest"}
    case["case_digest"] = canonical_sha256(state_view)


# ===========================================================================
# 1. Corpus schema validation
# ===========================================================================


class TestCorpusSchemaValidation:
    def test_the_committed_corpus_loads(self, corpus) -> None:
        assert corpus.corpus_id == "PI-SEMANTIC-V2-QUALIFICATION"
        assert corpus.corpus_version == "1.0.0"
        assert len(corpus.cases) == 56
        assert len(corpus.semantic_cases) == 43
        assert len(corpus.contract_negative_cases) == 13

    def test_a_missing_case_key_is_rejected(self, corpus, tmp_path) -> None:
        doc = deepcopy(corpus.document)
        del doc["cases"][0]["challenge_tags"]
        _reseal_case(doc["cases"][0])
        with pytest.raises(CorpusSchemaError, match="missing required keys"):
            load_corpus(_write(tmp_path, doc))

    def test_an_unknown_case_key_is_rejected(self, corpus, tmp_path) -> None:
        doc = deepcopy(corpus.document)
        doc["cases"][0]["injected"] = "x"
        _reseal_case(doc["cases"][0])
        with pytest.raises(CorpusSchemaError, match="unknown keys"):
            load_corpus(_write(tmp_path, doc))

    def test_an_unknown_category_is_rejected(self, corpus, tmp_path) -> None:
        doc = deepcopy(corpus.document)
        doc["cases"][0]["category"] = "quantum_computer"
        _reseal_case(doc["cases"][0])
        with pytest.raises(CorpusSchemaError, match="category"):
            load_corpus(_write(tmp_path, doc))

    def test_an_unknown_decision_is_rejected(self, corpus, tmp_path) -> None:
        doc = deepcopy(corpus.document)
        target = next(
            c for c in doc["cases"]
            if c["expected"]["disposition"] == "SEMANTIC_EVALUATION"
        )
        target["expected"]["decision"] = "MAYBE"
        target["expected"]["acceptable_decisions"] = ["MAYBE"]
        _reseal_case(target)
        with pytest.raises(CorpusSchemaError, match="decision"):
            load_corpus(_write(tmp_path, doc))

    def test_an_unknown_rejection_class_is_rejected(
        self, corpus, tmp_path
    ) -> None:
        doc = deepcopy(corpus.document)
        target = next(
            c for c in doc["cases"]
            if c["expected"]["disposition"] == "INPUT_REJECTED"
        )
        target["expected"]["rejection_class"] = "WHATEVER"
        _reseal_case(target)
        with pytest.raises(CorpusSchemaError, match="rejection_class"):
            load_corpus(_write(tmp_path, doc))

    def test_a_bad_case_id_grammar_is_rejected(self, corpus, tmp_path) -> None:
        doc = deepcopy(corpus.document)
        doc["cases"][0]["case_id"] = "not-a-case-id"
        with pytest.raises(CorpusSchemaError, match="case_id"):
            load_corpus(_write(tmp_path, doc))

    def test_label_text_naming_model_output_is_rejected(
        self, corpus, tmp_path
    ) -> None:
        doc = deepcopy(corpus.document)
        target = next(
            c for c in doc["cases"]
            if c["expected"]["disposition"] == "SEMANTIC_EVALUATION"
        )
        target["label"]["evidence"] = "derived from the model output"
        _reseal_case(target)
        with pytest.raises(
            CorpusSchemaError, match="independent of any model output"
        ):
            load_corpus(_write(tmp_path, doc))

    def test_label_text_naming_a_candidate_model_is_rejected(
        self, corpus, tmp_path
    ) -> None:
        doc = deepcopy(corpus.document)
        target = next(
            c for c in doc["cases"]
            if c["expected"]["disposition"] == "SEMANTIC_EVALUATION"
        )
        target["label"]["source"] = "qwen said so"
        _reseal_case(target)
        with pytest.raises(
            CorpusSchemaError, match="independent of any model output"
        ):
            load_corpus(_write(tmp_path, doc))


# ===========================================================================
# 2. Independent label provenance
# ===========================================================================


class TestIndependentLabelProvenance:
    def test_every_case_carries_complete_label_provenance(self, corpus) -> None:
        for case in corpus.cases:
            label = case.label
            assert label["source_kind"] in {
                "CONTRACT_GROUNDED",
                "PRODUCT_KNOWLEDGE_GROUNDED",
                "REVIEWED_SOURCE_GROUNDED",
            }
            assert label["source"]
            assert label["evidence"]
            assert label["reviewer"]
            assert label["reviewer_status"] in {"REVIEWED", "UNREVIEWED"}
            assert label["ambiguity"] in {
                "UNAMBIGUOUS",
                "CONTESTABLE",
                "INSUFFICIENTLY_SUPPORTED",
            }
            # Mechanical independence: no candidate model / model-output
            # token anywhere in the label text.
            for field_name in ("source", "evidence"):
                text = label[field_name].lower()
                for token in FORBIDDEN_EVIDENCE_TOKENS:
                    assert token not in text, (case.case_id, field_name)

    def test_reviewed_source_labels_cite_recorded_sources(self, corpus) -> None:
        reviewed = [
            case
            for case in corpus.cases
            if case.label["source_kind"] == "REVIEWED_SOURCE_GROUNDED"
        ]
        assert reviewed, "the corpus must carry recorded-source cases"
        for case in reviewed:
            source = case.label["source"].lower()
            assert any(
                token in source
                for token in ("recorded", "uat", "fixture", "catalog")
            ), case.case_id

    def test_the_corpus_never_depends_on_a_capture(self, tmp_path) -> None:
        """Ground truth independence, behaviorally: building the corpus
        with a capture file present (and with different answers in it)
        must yield the identical corpus document (the generator never
        reads captures)."""
        baseline = build_corpus_document()
        capture_path = tmp_path / "capture.json"
        capture_path.write_text(
            json.dumps(
                {
                    "capture_schema_version": 1,
                    "corpus_id": "PI-SEMANTIC-V2-QUALIFICATION",
                    "corpus_version": "1.0.0",
                    "corpus_digest": baseline["corpus_digest"],
                    "semantic_contract": "V2",
                    "prompt_version": "2.0",
                    "provider": "amax",
                    "model": "qwen3.8-27b",
                    "capture_run_id": "SHOULD-NOT-MATTER",
                    "captured_at": "2026-10-08T12:00:00Z",
                    "captured_by": "probe",
                    "notes": "probe",
                    "records": [
                        {
                            "case_id": "V2Q-SSD-ATTR-CAPACITY-0024",
                            "attempts": [
                                {
                                    "role": "PRIMARY",
                                    "provider": "amax",
                                    "model": "qwen3.8-27b",
                                    "status": "OK",
                                    "raw_output": json.dumps(
                                        {
                                            "decision": "MATCH",
                                            "confidence": "HIGH",
                                            "reason_code":
                                                "MATCH_EXACT_PRODUCT_CONTEXT",
                                            "matched_attributes": [],
                                            "conflicting_attributes": [],
                                            "missing_critical_attributes": [],
                                            "conflict_classes": [],
                                        }
                                    ),
                                }
                            ],
                            "fallback_used": False,
                            "fallback_reason": None,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        regenerated = build_corpus_document()
        assert regenerated == baseline

    def test_fixtures_module_reads_no_capture_surface(self) -> None:
        """Static: the corpus source never imports the capture module or
        any runtime/transport surface."""
        import product_intelligence.evaluation.semantic_v2.fixtures as fx
        import product_intelligence.evaluation.semantic_v2.report as rep
        import product_intelligence.evaluation.semantic_v2.evaluator as ev

        for module in (fx, rep, ev):
            source = Path(module.__file__).read_text(encoding="utf-8")
            assert "semantic.transport" not in source
            assert "get_openai" not in source
        fx_source = Path(fx.__file__).read_text(encoding="utf-8")
        assert "capture" not in fx_source.lower()


# ===========================================================================
# 3. Synthetic vs real evidence classification
# ===========================================================================


class TestEvidenceClassification:
    def test_synthetic_cases_are_labeled_synthetic(self, corpus) -> None:
        for case in corpus.cases:
            if case.evidence_kind == "SYNTHETIC":
                assert case.label["source_kind"] in {
                    "CONTRACT_GROUNDED",
                    "REVIEWED_SOURCE_GROUNDED",
                }
            if case.case_id.startswith("V2Q-") and (
                case.input_payload["target"]["mpn"].startswith("SYN-")
            ):
                assert case.evidence_kind == "SYNTHETIC", case.case_id

    def test_recorded_fixture_cases_exist_and_cite_fixtures(
        self, corpus
    ) -> None:
        recorded = [
            c for c in corpus.cases if c.evidence_kind == "RECORDED_FIXTURE"
        ]
        assert len(recorded) >= 5
        micron = [
            c for c in recorded
            if "micron_7500_part_catalog" in c.label["source"]
        ]
        assert micron, "the recorded Micron catalog cases must exist"
        samsung = [
            c for c in recorded if "semantic_corpus" in c.label["source"]
        ]
        assert samsung, "the recorded project-UAT cases must exist"

    def test_no_real_market_cases_in_corpus_1_0_0(self, corpus) -> None:
        assert not [
            c for c in corpus.cases if c.evidence_kind == "REAL_MARKET"
        ]

    def test_real_market_cases_are_rejected_by_the_loader(
        self, corpus, tmp_path
    ) -> None:
        doc = deepcopy(corpus.document)
        target = next(
            c
            for c in doc["cases"]
            if c["evidence_kind"] == "SYNTHETIC"
            and c["case_class"] == "AUTHORITATIVE"
        )
        target["evidence_kind"] = "REAL_MARKET"
        _reseal_case(target)
        with pytest.raises(CorpusSchemaError, match="REAL_MARKET"):
            load_corpus(_write(tmp_path, doc))

    def test_synthetic_cases_are_not_real_market_evidence(
        self, corpus
    ) -> None:
        """Governance: synthetic labels are contract/construction
        evidence; none of them may claim recorded-market provenance."""
        for case in corpus.cases:
            if case.evidence_kind == "SYNTHETIC":
                assert (
                    "recorded 4D-D fixture" not in case.label["source"]
                    and "project_uat" not in case.label["source"]
                ), case.case_id


# ===========================================================================
# 4. Corpus digest stability
# ===========================================================================


class TestCorpusDigestStability:
    def test_reloading_yields_the_same_digest(self, corpus, tmp_path) -> None:
        path = _write(tmp_path, corpus.document)
        again = load_corpus(path)
        assert again.corpus_digest == corpus.corpus_digest
        assert [c.case_digest for c in again.cases] == [
            c.case_digest for c in corpus.cases
        ]

    def test_regeneration_from_the_source_is_byte_identical(
        self, corpus
    ) -> None:
        regenerated = build_corpus_document()
        assert json.dumps(regenerated, sort_keys=True) == json.dumps(
            corpus.document, sort_keys=True
        )
        assert regenerated["corpus_digest"] == corpus.corpus_digest

    def test_the_manifest_is_reproducible(self, corpus) -> None:
        committed = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        rebuilt = build_manifest_document(corpus.document)
        assert committed == rebuilt
        verify_manifest(corpus, committed)

    def test_a_mismatched_manifest_fails_closed(self, corpus, tmp_path) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        manifest["cases"][0]["case_digest"] = "0" * 64
        with pytest.raises(CorpusIntegrityError, match="manifest"):
            verify_manifest(corpus, manifest)


# ===========================================================================
# 5. Label mutation changes the digest
# ===========================================================================


class TestLabelMutation:
    def test_mutating_an_expected_decision_breaks_the_digest(
        self, corpus, tmp_path
    ) -> None:
        doc = deepcopy(corpus.document)
        target = next(
            c for c in doc["cases"]
            if c["case_class"] == "AUTHORITATIVE"
            and c["expected"]["decision"] == "MATCH"
        )
        target["expected"]["decision"] = "NO_MATCH"
        target["expected"]["acceptable_decisions"] = ["NO_MATCH"]
        with pytest.raises(CorpusIntegrityError):
            load_corpus(_write(tmp_path, doc))

    def test_mutating_the_label_evidence_breaks_the_case_digest(
        self, corpus, tmp_path
    ) -> None:
        doc = deepcopy(corpus.document)
        target = next(
            c for c in doc["cases"]
            if c["case_class"] == "AUTHORITATIVE"
        )
        target["label"]["evidence"] = target["label"]["evidence"] + " (revised)"
        with pytest.raises(CorpusIntegrityError, match="case_digest"):
            load_corpus(_write(tmp_path, doc))

    def test_a_proper_label_revision_changes_the_corpus_digest(
        self, corpus, tmp_path
    ) -> None:
        """Changing an expected label must change the corpus digest and
        create an auditable revision; the sealed document with the
        revision recomputes to a NEW digest (never silently the old
        one)."""
        from product_intelligence.evaluation.semantic_v2.canonical import (
            canonical_sha256,
        )

        doc = deepcopy(corpus.document)
        target = next(
            c for c in doc["cases"]
            if c["case_id"] == "V2Q-SSD-U1-THIN-0005"
        )
        old_digest = doc["corpus_digest"]
        target["expected"]["decision"] = "MATCH"
        target["expected"]["acceptable_decisions"] = ["MATCH", "UNCERTAIN"]
        target["label"]["ambiguity"] = "CONTESTABLE"
        target["label"]["evidence"] = (
            target["label"]["evidence"]
            + " (revision 1: label widened after review)"
        )
        state_view = {k: v for k, v in target.items() if k != "case_digest"}
        target["case_digest"] = canonical_sha256(state_view)
        doc["label_revisions"].append(
            {
                "revision": 1,
                "case_id": target["case_id"],
                "utc": "2026-10-09T00:00:00Z",
                "reason_class": "C",
                "statement": (
                    "the case definition was ambiguous; the acceptable "
                    "set is widened (test fixture revision)"
                ),
                "digest_before": old_digest,
                "digest_after": "",
            }
        )
        state = {
            k: v for k, v in doc.items()
            if k not in ("label_revisions", "corpus_digest")
        }
        new_digest = canonical_sha256(state)
        assert new_digest != old_digest, (
            "a label change must change the corpus digest"
        )
        doc["corpus_digest"] = new_digest
        doc["label_revisions"][0]["digest_after"] = new_digest
        revised = load_corpus(_write(tmp_path, doc))
        assert revised.corpus_digest != old_digest
        assert revised.case("V2Q-SSD-U1-THIN-0005").expected["decision"] == "MATCH"

    def test_a_revision_with_the_wrong_reason_class_is_rejected(
        self, corpus, tmp_path
    ) -> None:
        doc = deepcopy(corpus.document)
        doc["label_revisions"].append(
            {
                "revision": 1,
                "case_id": doc["cases"][0]["case_id"],
                "utc": "2026-10-09T00:00:00Z",
                "reason_class": "E",
                "statement": "the new implementation failed this case",
                "digest_before": "0" * 64,
                "digest_after": "0" * 64,
            }
        )
        with pytest.raises(CorpusSchemaError, match="reason_class"):
            load_corpus(_write(tmp_path, doc))

    def test_a_revision_for_a_unknown_case_is_rejected(
        self, corpus, tmp_path
    ) -> None:
        doc = deepcopy(corpus.document)
        doc["label_revisions"].append(
            {
                "revision": 1,
                "case_id": "V2Q-NO-SUCH-CASE",
                "utc": "2026-10-09T00:00:00Z",
                "reason_class": "A",
                "statement": "x",
                "digest_before": "0" * 64,
                "digest_after": "0" * 64,
            }
        )
        with pytest.raises(CorpusSchemaError, match="case_id"):
            load_corpus(_write(tmp_path, doc))


# ===========================================================================
# 7. Duplicate case id fails closed
# ===========================================================================


class TestDuplicateCaseId:
    def test_a_duplicate_case_id_is_rejected(self, corpus, tmp_path) -> None:
        doc = deepcopy(corpus.document)
        doc["cases"].append(deepcopy(doc["cases"][0]))
        with pytest.raises(CorpusSchemaError, match="duplicate case id"):
            load_corpus(_write(tmp_path, doc))


# ===========================================================================
# 8. Unknown corpus version fails closed
# ===========================================================================


class TestUnknownCorpusVersion:
    def test_an_unknown_corpus_schema_version_is_rejected(
        self, corpus, tmp_path
    ) -> None:
        doc = deepcopy(corpus.document)
        doc["corpus_schema_version"] = 2
        with pytest.raises(
            CorpusSchemaError, match="unknown corpus schema version"
        ):
            load_corpus(_write(tmp_path, doc))

    def test_a_future_corpus_schema_version_is_rejected(
        self, corpus, tmp_path
    ) -> None:
        doc = deepcopy(corpus.document)
        doc["corpus_schema_version"] = 99
        with pytest.raises(CorpusSchemaError):
            load_corpus(_write(tmp_path, doc))

    def test_an_unknown_corpus_id_is_rejected(self, corpus, tmp_path) -> None:
        doc = deepcopy(corpus.document)
        doc["corpus_id"] = "SOME-OTHER-CORPUS"
        with pytest.raises(CorpusSchemaError, match="corpus_id"):
            load_corpus(_write(tmp_path, doc))


# ===========================================================================
# Mandated corpus coverage (the Q3-A corpus spec)
# ===========================================================================


class TestMandatedCoverage:
    def test_all_seven_uncertain_substates_are_covered(self, corpus) -> None:
        pairs = {
            (c.substate, c.primary_signal)
            for c in corpus.semantic_cases
        }
        required = {
            ("U1_TITLE_MPN", "TITLE_MPN_TOKEN"),
            ("U2_SKU_ONLY", "SKU_EQUALS_TARGET"),
            ("U2_SKU_ONLY", "SKU_NOT_TARGET"),
            ("U3_PARTIAL_BOUNDARY", "PARTIAL_BOUNDARY"),
            ("U4_NO_MPN", "NO_RELATION"),
            ("U5_NEAR_MISS_MPN", "NEAR_MISS_TRUNCATION"),
            ("U5_NEAR_MISS_MPN", "NEAR_MISS_SUBSTITUTION"),
        }
        assert required <= pairs

    def test_several_product_categories_are_covered(self, corpus) -> None:
        categories = {c.category for c in corpus.semantic_cases}
        assert categories >= {
            "enterprise_ssd",
            "server_memory",
            "processor",
            "network_adapter",
            "workstation_gpu",
        }

    def test_the_motivating_micron_case_is_present_and_labeled(
        self, corpus
    ) -> None:
        case = corpus.case("V2Q-SSD-U5NM1-MICRON-0018")
        payload = case.input_payload
        assert payload["target"]["mpn"] == "MTFDKCC3T8TGP-1BK1DABYYR"
        assert payload["candidate"]["mpn_field"] == "MTFDKCC3T8TGP-1BK1DABYY"
        assert case.substate == "U5_NEAR_MISS_MPN"
        assert case.primary_signal == "NEAR_MISS_TRUNCATION"
        # Not labeled equivalent merely because of the shared base.
        assert case.expected["decision"] == "UNCERTAIN"
        assert case.expected["commercial_sales_unit_safety"] is True
        assert "PACKAGING_QUANTITY" in case.expected["missing_dimensions"]
        # The customer-retrieval relation is present and zero authority.
        assert "CUSTOMER_RETRIEVAL_RELATION" in (
            payload["context_provenance"]
        )
        reviewed = payload["target"]["reviewed_context"]
        assert reviewed["relation_kind"] == "CUSTOMER_RETRIEVAL_ALIAS"
        assert reviewed["evidence_body_sha256"] == (
            "160d4fe97a5df5249e8f6404f6b005c0515fab4def1b4668fdaf87c727600743"
        )

    def test_all_contract_negative_cases_are_rejected_by_the_contract(
        self, corpus
    ) -> None:
        for case in corpus.contract_negative_cases:
            rejection = None
            try:
                case.build_semantic_case()
            except Exception as exc:  # noqa: BLE001 - classified below
                from product_intelligence.evaluation.semantic_v2.corpus import (
                    CorpusInputRejectionError,
                )

                assert isinstance(
                    exc, CorpusInputRejectionError
                ), f"{case.case_id}: {exc!r}"
                rejection = exc.rejection_class
            assert rejection == case.expected["rejection_class"], case.case_id

    def test_case_ids_are_stable_and_unique(self, corpus) -> None:
        ids = [c.case_id for c in corpus.cases]
        assert len(ids) == len(set(ids))
        assert all(i.startswith("V2Q-") for i in ids)
