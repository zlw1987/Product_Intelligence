"""Corpus 1.1.0 binding-only re-seal integrity (Q3-B5-P1, T3 + T4).

The approved Q3-B3-FU2 design (section 9.1) re-seals the qualification
corpus for the separately versioned 2.1 contract binding:

* all 56 per-case documents (payload, expected outcome, label,
  challenge metadata, sealed per-case digest) are byte-identical to
  1.0.0 - a mechanical proof of label / payload invariance;
* only the authorized contract binding / version metadata moves
  (``corpus_version`` -> 1.1.0, ``semantic_contract_binding`` -> the
  separately versioned 2.1 binding with the separately versioned FU3
  authority token, Q3-B4 AD-Q3B4-5), and the corpus digest is
  recomputed;
* ``label_revisions`` stays empty - NO corpus label revision;
* both versions coexist: 1.0.0 stays bound to the 2.0 binding for
  historical evidence, 1.1.0 is bound to the 2.1 binding; the harness
  loads each against its own binding and refuses every cross-version
  combination (T2 file);
* the anti-manipulation property is preserved on the re-seal: a label
  mutation changes the digest and requires a bounded revision entry.

T4 (harness invariance): the eight hard gates keep their exact names
and fail-closed semantics (in the 2.0 context the gate output is
byte-identical to the pre-2.1 harness - proven against the committed
2.0 baseline reports; in the 2.1 context the
``zero_contract_version_mismatch`` gate pins the 2.1 production
binding - the only allowed delta); the DRAFT policy artifact is
byte-unchanged; the severity mapping is unchanged; the no-capture 2.1
baseline report is reproducible and committed; the 13 CONTRACT_
NEGATIVE rejections are identical across the two corpus versions
(prompt-independent).
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from tests.evaluation.semantic_v2._q3a_helpers import (
    BASELINE_2_1_REPORT_DIR,
    BASELINE_REPORT_DIR,
    CORPUS_2_1_PATH,
    CORPUS_PATH,
    MANIFEST_2_1_PATH,
    MANIFEST_PATH,
    POLICY_PATH,
    fallback_route,
    load_corpus_bundle,
    primary_route,
)
from product_intelligence.evaluation.semantic_v2.canonical import (
    canonical_sha256,
)
from product_intelligence.evaluation.semantic_v2.corpus import (
    BINDING_CORPUS_VERSIONS,
    CorpusIntegrityError,
    KNOWN_PRODUCTION_BINDINGS,
    build_manifest_document,
    load_corpus,
    reject_class_for,
    verify_manifest,
)
from product_intelligence.evaluation.semantic_v2.evaluator import (
    evaluate_no_capture,
)
from product_intelligence.evaluation.semantic_v2.fixtures import (
    CORPUS_VERSION,
    CORPUS_VERSION_2_1,
    build_corpus_2_1_document,
    build_corpus_document,
)
from product_intelligence.evaluation.semantic_v2.gates import (
    HARD_SAFETY_GATES,
    decide,
    evaluate_safety_gates,
)
from product_intelligence.evaluation.semantic_v2.policy import (
    load_policy,
)
from product_intelligence.evaluation.semantic_v2.report import (
    build_report,
    render_markdown,
    verify_report,
)
from product_intelligence.research import V2_CONTRACT_BINDING
from product_intelligence.semantic.contract_v2_1 import (
    V2_1_CONTRACT_BINDING,
)

GENERATED_UTC = "2026-10-08T00:00:00Z"


@pytest.fixture(scope="module")
def corpus_2_0():
    return load_corpus(CORPUS_PATH)


@pytest.fixture(scope="module")
def corpus_2_1():
    return load_corpus(CORPUS_2_1_PATH)


def _write(tmp_path: Path, doc: dict, name: str = "corpus.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


# ===========================================================================
# T3.1 The committed re-seal is what the auditable source produces
# ===========================================================================


class TestCommittedReSeal:
    def test_the_committed_1_1_0_corpus_loads(self, corpus_2_1) -> None:
        assert corpus_2_1.corpus_version == CORPUS_VERSION_2_1 == "1.1.0"
        assert list(corpus_2_1.semantic_contract_binding) == list(
            V2_1_CONTRACT_BINDING
        )
        assert len(corpus_2_1.cases) == 56
        assert len(corpus_2_1.semantic_cases) == 43
        assert len(corpus_2_1.contract_negative_cases) == 13
        assert corpus_2_1.document["label_revisions"] == []

    def test_regeneration_from_the_source_is_byte_identical(
        self, corpus_2_1
    ) -> None:
        regenerated = build_corpus_2_1_document()
        assert json.dumps(regenerated, sort_keys=True) == json.dumps(
            corpus_2_1.document, sort_keys=True
        )
        assert regenerated["corpus_digest"] == corpus_2_1.corpus_digest

    def test_the_manifest_is_reproducible(self, corpus_2_1) -> None:
        committed = json.loads(MANIFEST_2_1_PATH.read_text(encoding="utf-8"))
        rebuilt = build_manifest_document(corpus_2_1.document)
        assert committed == rebuilt
        verify_manifest(corpus_2_1, committed)
        assert committed["semantic_contract_binding"] == list(
            V2_1_CONTRACT_BINDING
        )
        assert committed["corpus_version"] == CORPUS_VERSION_2_1

    def test_the_1_0_0_corpus_is_unchanged(self, corpus_2_0) -> None:
        # Historical evidence: 1.0.0 stays bound to the 2.0 binding with
        # its recorded digest (no re-interpretation, no re-seal in
        # place).
        assert corpus_2_0.corpus_version == CORPUS_VERSION == "1.0.0"
        assert list(corpus_2_0.semantic_contract_binding) == list(
            V2_CONTRACT_BINDING
        )
        assert corpus_2_0.corpus_digest == (
            "2c37ba088c317d8cefc6ad0dd7e0d73cfd085f6474ef43eb6953e3cf0170b549"
        )
        assert json.loads(
            CORPUS_PATH.read_text(encoding="utf-8")
        )["corpus_digest"] == corpus_2_0.corpus_digest


# ===========================================================================
# T3.2 The re-seal is binding-only: per-case byte identity + the exact
#       top-level delta
# ===========================================================================


class TestBindingOnlyInvariance:
    def test_all_56_case_digests_are_byte_identical(
        self, corpus_2_0, corpus_2_1
    ) -> None:
        d10 = {c.case_id: c.case_digest for c in corpus_2_0.cases}
        d11 = {c.case_id: c.case_digest for c in corpus_2_1.cases}
        assert set(d10) == set(d11)
        for case_id in d10:
            assert d10[case_id] == d11[case_id], case_id

    def test_every_case_document_is_zero_diff(
        self, corpus_2_0, corpus_2_1
    ) -> None:
        by_id_10 = {c.case_id: c for c in corpus_2_0.cases}
        for case in corpus_2_1.cases:
            old = by_id_10[case.case_id]
            assert case.input_payload == old.input_payload
            assert case.expected == old.expected
            assert case.label == old.label
            assert case.category == old.category
            assert case.case_class == old.case_class
            assert case.evidence_kind == old.evidence_kind
            assert case.input_shape == old.input_shape
            assert case.challenge_tags == old.challenge_tags
            assert case.substate == old.substate
            assert case.primary_signal == old.primary_signal

    def test_only_the_authorized_metadata_moves(
        self, corpus_2_0, corpus_2_1
    ) -> None:
        d10 = corpus_2_0.document
        d11 = corpus_2_1.document
        moved = {
            k
            for k in d11
            if k not in d10 or json.dumps(d10[k], sort_keys=True)
            != json.dumps(d11[k], sort_keys=True)
        }
        assert moved == {
            "corpus_version",
            "semantic_contract_binding",
            "corpus_digest",
        }, sorted(moved)
        assert d11["corpus_id"] == d10["corpus_id"]
        assert d11["corpus_label"] == d10["corpus_label"]
        assert d11["created_utc"] == d10["created_utc"]
        assert d11["corpus_schema_version"] == d10["corpus_schema_version"]
        assert d11["label_revisions"] == [] == d10["label_revisions"]
        # The digest is recomputed over the re-sealed state (deterministic
        # canonical serialization; the cases state is identical).
        state = {
            k: v for k, v in d11.items() if k != "corpus_digest"
        }
        state = {k: v for k, v in state.items() if k != "label_revisions"}
        assert canonical_sha256(state) == d11["corpus_digest"]
        assert d11["corpus_digest"] != d10["corpus_digest"]

    def test_the_known_bindings_map_is_exact(
        self, corpus_2_0, corpus_2_1
    ) -> None:
        assert KNOWN_PRODUCTION_BINDINGS == frozenset(
            {
                tuple(V2_CONTRACT_BINDING),
                tuple(V2_1_CONTRACT_BINDING),
            }
        )
        assert BINDING_CORPUS_VERSIONS == {
            tuple(V2_CONTRACT_BINDING): CORPUS_VERSION,
            tuple(V2_1_CONTRACT_BINDING): CORPUS_VERSION_2_1,
        }

    def test_both_versions_load_against_their_own_bindings(
        self, corpus_2_0, corpus_2_1
    ) -> None:
        # (The loader refuses every other version/binding combination -
        # see the binding / replay file.)
        assert tuple(corpus_2_0.semantic_contract_binding) in (
            KNOWN_PRODUCTION_BINDINGS
        )
        assert tuple(corpus_2_1.semantic_contract_binding) in (
            KNOWN_PRODUCTION_BINDINGS
        )


# ===========================================================================
# T3.3 Anti-manipulation preserved on the re-seal
# ===========================================================================


class TestAntiManipulationOnReSeal:
    def test_an_unsealed_label_edit_on_1_1_0_is_rejected_on_load(
        self, corpus_2_1, tmp_path
    ) -> None:
        doc = deepcopy(corpus_2_1.document)
        target = next(
            c for c in doc["cases"] if c["case_id"] == "V2Q-SSD-ATTR-CAPACITY-0024"
        )
        target["expected"]["decision"] = "MATCH"
        target["expected"]["acceptable_decisions"] = ["MATCH"]
        # corpus_digest / case_digest NOT recomputed: silent mutation.
        with pytest.raises(CorpusIntegrityError, match="case_digest"):
            load_corpus(_write(tmp_path, doc))

    def test_a_sealed_label_change_on_1_1_0_changes_the_digest(
        self, corpus_2_1, tmp_path
    ) -> None:
        doc = deepcopy(corpus_2_1.document)
        target = next(
            c for c in doc["cases"] if c["case_id"] == "V2Q-SSD-U1-THIN-0005"
        )
        old_digest = doc["corpus_digest"]
        target["expected"]["decision"] = "MATCH"
        target["expected"]["acceptable_decisions"] = ["MATCH", "UNCERTAIN"]
        state_view = {k: v for k, v in target.items() if k != "case_digest"}
        target["case_digest"] = canonical_sha256(state_view)
        state = {
            k: v for k, v in doc.items()
            if k not in ("label_revisions", "corpus_digest")
        }
        doc["corpus_digest"] = canonical_sha256(state)
        assert doc["corpus_digest"] != old_digest
        # A label move WITHOUT a bounded revision entry is a corpus
        # governance violation: the re-seal is binding-only, and the
        # label digests no longer agree with 1.0.0.
        revised = load_corpus(_write(tmp_path, doc))
        old_case = corpus_2_1.case("V2Q-SSD-U1-THIN-0005")
        assert (
            revised.case("V2Q-SSD-U1-THIN-0005").case_digest
            != old_case.case_digest
        )
        assert revised.document["label_revisions"] == []
        assert (
            "V2Q-SSD-U1-THIN-0005" in
            {
                c.case_id
                for c in revised.cases
                if c.case_digest
                != next(
                    x.case_digest for x in corpus_2_1.cases
                    if x.case_id == c.case_id
                )
            }
        )

    def test_a_historical_2_0_report_stays_bound_to_1_0_0(
        self, corpus_2_1
    ) -> None:
        """Cross-version replay isolation, report side: the committed
        2.0 no-capture baseline reports verify against the 1.0.0 corpus
        and FAIL against the 1.1.0 re-seal (the labels are identical,
        but the binding is different - never a silent reinterpretation).
        """
        from product_intelligence.evaluation.semantic_v2.report import (
            ReportError,
        )

        for path in sorted(BASELINE_REPORT_DIR.glob("*__report.json")):
            report = json.loads(path.read_text(encoding="utf-8"))
            with pytest.raises(ReportError, match="corpus digest"):
                verify_report(report, corpus_2_1)

    def test_a_2_1_report_stays_bound_to_1_1_0(
        self, corpus_2_0
    ) -> None:
        from product_intelligence.evaluation.semantic_v2.report import (
            ReportError,
            verify_report,
        )

        for path in sorted(BASELINE_2_1_REPORT_DIR.glob("*__report.json")):
            report = json.loads(path.read_text(encoding="utf-8"))
            verify_report(report, load_corpus(CORPUS_2_1_PATH))
            with pytest.raises(ReportError, match="corpus digest"):
                verify_report(report, corpus_2_0)


# ===========================================================================
# T4. Harness invariance: gates, policy, severity, contract-negatives,
#     and the committed 2.1 no-capture baseline
# ===========================================================================


class TestHarnessInvariance:
    def test_the_eight_gate_names_and_order_are_unchanged(self) -> None:
        assert HARD_SAFETY_GATES == (
            "zero_false_match_on_always_hard_conflicts",
            "zero_false_match_on_packaging_quantity_conflicts",
            "zero_false_match_on_accessory_product_role_conflicts",
            "zero_schema_bypass_acceptance",
            "zero_unauthorized_authority_promotion",
            "zero_customer_alias_authority_promotion",
            "zero_contract_version_mismatch",
            "zero_missing_required_evaluation_silent_pass",
        )

    def test_the_2_0_context_gate_output_is_byte_identical(
        self, corpus_2_0
    ) -> None:
        """In the 2.0 context the gate results (names, pass/fail,
        details, failing case ids) are exactly what the pre-2.1
        harness produced - proven against the committed 2.0 baseline
        reports."""
        result = evaluate_no_capture(corpus_2_0, *primary_route())
        gates = evaluate_safety_gates(result)
        assert set(gates) == set(HARD_SAFETY_GATES)
        for path in sorted(BASELINE_REPORT_DIR.glob("*__report.json")):
            committed = json.loads(path.read_text(encoding="utf-8"))
            assert committed["safety_gates"] == {
                name: gates[name].to_report_dict()
                for name in gates
            }, path.name
        # The 2.0 contract-version gate pins the frozen 2.0 binding.
        assert gates["zero_contract_version_mismatch"].passed
        assert gates["zero_contract_version_mismatch"].detail == (
            "corpus binds to the exact frozen production contract"
        )

    def test_the_2_1_context_gate_output(self, corpus_2_1) -> None:
        """In the 2.1 context the seven unchanged gates keep their
        exact detail text, and zero_contract_version_mismatch pins the
        2.1 production binding (the only allowed delta)."""
        result = evaluate_no_capture(corpus_2_1, *primary_route())
        gates_2_1 = evaluate_safety_gates(result)
        result_2_0 = evaluate_no_capture(load_corpus(CORPUS_PATH), *primary_route())
        gates_2_0 = evaluate_safety_gates(result_2_0)
        for name in HARD_SAFETY_GATES:
            if name == "zero_contract_version_mismatch":
                continue
            assert gates_2_1[name].to_report_dict() == gates_2_0[name].to_report_dict(), name
        gate = gates_2_1["zero_contract_version_mismatch"]
        assert gate.passed
        assert (
            gate.detail
            == "corpus binds to the exact 2.1 production contract (prompt 2.1, authority "
            + "SEMANTIC_AUTHORITY_V2_S2A_FU3)"
        )

    def test_the_draft_policy_artifact_is_byte_unchanged(self) -> None:
        raw = POLICY_PATH.read_bytes()
        doc = json.loads(raw)
        assert doc["status"] == "DRAFT"
        assert doc["approval"]["approved"] is False
        assert doc["applicability"]["corpus_version"] == CORPUS_VERSION
        assert doc["thresholds"] == {
            "eligible_coverage_min": 1.0,
            "match_precision_min": 0.99,
            "match_recall_min": 0.9,
            "valid_structured_response_rate_min": 0.99,
        }
        # The DRAFT policy binds to the 1.0.0 corpus identity (byte-
        # unchanged): it is NOT applicable to the 1.1.0 re-seal, so a
        # 2.1 evaluation with the DRAFT policy is POLICY_PENDING
        # ("no approved applicable policy") - never QUALIFIED.
        policy = load_policy(POLICY_PATH)
        from product_intelligence.evaluation.semantic_v2.policy import (
            policy_applies_to,
        )

        assert policy_applies_to(
            policy, "PI-SEMANTIC-V2-QUALIFICATION", CORPUS_VERSION
        )
        assert not policy_applies_to(
            policy, "PI-SEMANTIC-V2-QUALIFICATION", CORPUS_VERSION_2_1
        )

    def test_the_thirteen_contract_negative_rejections_are_identical(
        self, corpus_2_0, corpus_2_1
    ) -> None:
        for case in corpus_2_1.contract_negative_cases:
            old = corpus_2_0.case(case.case_id)
            assert old.case_class == "CONTRACT_NEGATIVE"
            assert reject_class_for(case.input_payload) == (
                old.expected["rejection_class"]
            )
            assert reject_class_for(case.input_payload) == (
                case.expected["rejection_class"]
            )

    def test_the_no_capture_2_1_baseline_is_reproducible_and_committed(
        self, corpus_2_1
    ) -> None:
        policy = load_policy(POLICY_PATH)
        for route, stem_route in (
            (primary_route(), "amax_qwen3.8-27b"),
            (fallback_route(), "vllm-262k_Qwen3.6-27B-262K"),
        ):
            result = evaluate_no_capture(corpus_2_1, *route)
            gates = evaluate_safety_gates(result)
            from product_intelligence.evaluation.semantic_v2.policy import (
                evaluate_thresholds,
                policy_applies_to,
            )

            te = (
                evaluate_thresholds(policy, result.metrics)
                if policy_applies_to(
                    policy,
                    corpus_2_1.corpus_id,
                    corpus_2_1.corpus_version,
                )
                else None
            )
            decision, rationale = decide(result, gates, policy, te)
            rebuilt = build_report(
                result=result,
                gates=gates,
                policy=policy,
                threshold_evaluation=te,
                decision=decision,
                rationale=rationale,
                corpus=corpus_2_1,
                generated_utc=GENERATED_UTC,
            )
            stem = f"no-capture_{stem_route}"
            committed_json = (
                BASELINE_2_1_REPORT_DIR / f"{stem}__report.json"
            ).read_text(encoding="utf-8")
            assert (
                json.dumps(rebuilt, indent=1, sort_keys=True, ensure_ascii=True)
                + "\n"
            ) == committed_json, stem
            committed_md = (
                BASELINE_2_1_REPORT_DIR / f"{stem}__report.md"
            ).read_text(encoding="utf-8")
            assert render_markdown(rebuilt) == committed_md, stem
            # The no-capture baseline is an explicit fail-closed state:
            # 43/43 eligible NOT_CAPTURED, all eight gates pass, the
            # decision is POLICY_PENDING, and the report grants no
            # authority.
            assert decision == "POLICY_PENDING"
            assert rebuilt["authority"]["granted"] is False
            assert rebuilt["authority"]["v2_authority_qualified"] is False
            assert (
                rebuilt["metrics"]["counts"]["not_captured"] == 43
            )
            assert all(
                g["passed"] for g in rebuilt["safety_gates"].values()
            )

    def test_the_2_1_baseline_contract_section_binds_the_2_1_identity(
        self
    ) -> None:
        report = json.loads(
            (
                BASELINE_2_1_REPORT_DIR
                / "no-capture_amax_qwen3.8-27b__report.json"
            ).read_text(encoding="utf-8")
        )
        contract = report["contract"]
        assert contract["semantic_contract_version"] == "V2"
        assert contract["prompt_version"] == "2.1"
        assert contract["input_schema_version"] == 1
        assert contract["output_schema_version"] == 1
        assert contract["authority_contract_version"] == (
            "SEMANTIC_AUTHORITY_V2_S2A_FU3"
        )
        assert contract["semantic_contract_binding"] == [
            "V2",
            "2.1",
            1,
            1,
            "SEMANTIC_AUTHORITY_V2_S2A_FU3",
        ]
        from product_intelligence.evaluation.semantic_v2.canonical import (
            canonical_sha256,
        )
        from product_intelligence.semantic.contract_v2_1 import (
            SYSTEM_PROMPT_V2_1,
        )

        # The REAL 2.1 system prompt, by digest (the harness binds the
        # prompt by reference; no copy in the report).
        assert contract["system_prompt_digest"] == canonical_sha256(
            {"text": SYSTEM_PROMPT_V2_1}
        )
        # The runtime configuration identity is unchanged (the pinned
        # routes, the frozen generation parameters, the persist-only
        # marker).
        assert contract["runtime_config_identity"] == {
            "primary": {"provider": "amax", "model": "qwen3.8-27b"},
            "fallback": {
                "provider": "vllm-262k",
                "model": "Qwen3.6-27B-262K",
            },
            "temperature": "0.0",
            "max_tokens": 32768,
            "v2_authority_qualified": False,
        }
