"""FU4 offline qualification harness integration tests
(PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-B5-P5-R2).

Mandated integration matrix (design section 9.2, rows 17-24, plus the
task's 28-item adversarial / regression list) over the REAL public
harness interfaces (``load_corpus`` / ``verify_manifest`` /
``evaluate_no_capture`` / ``evaluate_direct_for_model`` / ``decide`` /
``build_report`` / ``verify_report`` / the CLI regeneration path —
never only internal helper functions) and over the REAL R1 record /
replay entry points (``encode_semantic_decision_record`` /
``decode_semantic_decision_record`` / ``replay_semantic_decision``).

The R2 registration state pinned here:

* the harness knows EXACTLY the three production bindings
  (2.0/FU2 -> 1.0.0, 2.1/FU3 -> 1.1.0, 2.1/FU4 -> 1.2.0); the four
  known bindings of the system (V1, 2.0/FU2, 2.1/FU3, 2.1/FU4) are
  each distinguished exactly — V1 is codec / replay only, 2.1/FU3 is
  harness-only (codec-refused), unknown / mixed-axis bindings fail
  closed with no fallback to a nearby binding;
* corpus 1.2.0 is the binding-only re-seal of the sealed 1.1.0
  document (56/56 per-case documents byte-identical; ``label_revisions``
  empty; exactly ``{corpus_version, semantic_contract_binding,
  corpus_digest}`` moved), sealed under the exact FU4 binding
  (``("V2", "2.1", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU4")`` — composed
  from the frozen exports; the semantic layer's 2.1 owner constant is
  the drift-pinned source), with the required manifest statement and
  the explicit 1.1.0 lineage inside the manifest digest;
* the committed 1.2.0 no-capture baselines (both pinned route
  candidates) are POLICY_PENDING with ``granted: false`` — the FU4
  binding is a registration, NOT a qualification and NOT a new model
  capability;
* the FU4 bundle states (PROVEN / UNPROVEN / CONTRADICTED) remain
  governed by the R1 deterministic derivation + zero-live replay, never
  by the corpus 1.2.0 semantic labels;
* the historical 1.0.0 / 1.1.0 artifacts, baselines, and reports are
  byte-identical and remain interpretable (and refuse the 1.2.0
  lineage in both directions);
* the six R2-amended modules themselves (contract_v2_1.py /
  corpus.py / fixtures.py / gates.py / report.py / cli.py) are
  content-pinned at the R2 endpoint by literal SHA-256 (the
  TestR2EndpointModulePins class - the R2-FU1 restoration of the six
  file-content integrity contracts the FU4 A1 frozen-module table
  re-pinned around at R2).

Every case is an OFFLINE recorded-input / recorded-payload
construction — NO live call, NO model capture, NO network.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import socket
from pathlib import Path

import pytest

from tests.evaluation.semantic_v2._q3a_helpers import (
    BASELINE_2_1_REPORT_DIR,
    BASELINE_REPORT_DIR,
    CORPUS_2_1_PATH,
    CORPUS_PATH,
    POLICY_PATH,
    fallback_route,
    primary_route,
)
from tests.evaluation.semantic_v2._q3a_fu1_helpers import (
    write_direct_capture,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
CORPUS_DIR = REPO_ROOT / "evaluation" / "semantic_v2_qualification"
CORPUS_2_1_FU4_PATH = CORPUS_DIR / "corpus_2_1_fu4.json"
MANIFEST_2_1_FU4_PATH = CORPUS_DIR / "manifest_2_1_fu4.json"
BASELINE_1_2_0_REPORT_DIR = CORPUS_DIR / "reports" / "q3b5_p5_baseline_1_2_0"

#: The deterministic baseline instant (the corpus creation date - the
#: same convention the committed 1.0.0 / 1.1.0 baselines use).
GENERATED_UTC = "2026-10-08T00:00:00Z"

#: The sealed corpus digests of record (RECORDED literals, never
#: computed from the artifacts at run time).
CORPUS_1_0_0_DIGEST = (
    "2c37ba088c317d8cefc6ad0dd7e0d73cfd085f6474ef43eb6953e3cf0170b549"
)
CORPUS_1_1_0_DIGEST = (
    "14396eae884841e20063cb4da0d4424ce8f05ff8745f2c787fc395d250ea8dcd"
)
CORPUS_1_2_0_DIGEST = (
    "582b35bbee93959eaa5a598fa579cd99229e550e37f3c6cd970f7774ed9d1b91"
)
MANIFEST_1_2_0_DIGEST = (
    "972ba35428d1dfc0a4b07d2027d9186577cf398a3ba4dc96dc61865b9843d8d7"
)

#: The file digests of the historical committed artifacts (RECORDED -
#: the same literals the FU4 suite's A1 CORPUS_ARTIFACT_PINS table
#: pins; 1.0.0 / 1.1.0 / the DRAFT policy are byte-frozen by R2).
HISTORICAL_ARTIFACT_FILE_DIGESTS = {
    "corpus_v1.json": (
        "ffb407b3e440f08ae5e92f8fe4444d23d46744753dee8088fc8e6fea79a8430b"
    ),
    "manifest_v1.json": (
        "caa5d76ffdce92a4de1b7f9e04dfef640518b3d0ec1580ec916cedf27f607c44"
    ),
    "corpus_2_1.json": (
        "6f5254c8772ea34547ef8a8315ce4f2352df48d8c2121ed431248d047777bff9"
    ),
    "manifest_2_1.json": (
        "f37956e45b3d873e583d6f2f42ac7e6f5393110b8ea64e95a9a98e1c02d36ac7"
    ),
    "policy/qualification_policy_draft_1.json": (
        "6bc30d3781b7cac27e8dd767849ca53e6d4141095ca972d528ffbee2e4cdc111"
    ),
}

#: The six modules R2 explicitly amended to register the FU4 offline
#: binding (design section 10.2): the semantic layer's 2.1 FU4 binding
#: constant (contract_v2_1.py) and the harness extension targets
#: (corpus.py / fixtures.py / gates.py / report.py / cli.py). They
#: left the FU4 suite's A1 FROZEN_MODULE_PINS table at R2 (17 -> 11
#: rows - they are no longer BYTE-FROZEN inputs), and this suite is
#: their recorded R2-endpoint content pin (the R2-FU1 restoration of
#: the six file-content integrity contracts; the same category as the
#: R1-FU1 codec pin in the R1 suite). The digests are the SHA-256 of
#: the exact committed content at the R2 endpoint (starting SHA
#: 202a3efa386c45b137b2f407510fe91a594f5e55) - RECORDED literals,
#: never computed from the files at run time.
#: Why these digests differ from the pre-R2 A1 pins: R2 amended these
#: six modules on purpose - contract_v2_1.py gained the
#: V2_1_FU4_CONTRACT_BINDING constant + import self-checks (the FU3
#: binding byte-unchanged); fixtures.py gained
#: CORPUS_VERSION_2_1_FU4 = "1.2.0" + build_corpus_2_1_fu4_document()
#: + the manifest statement / lineage keys; corpus.py gained the third
#: BINDING_CORPUS_VERSIONS entry (KNOWN_PRODUCTION_BINDINGS = exactly
#: three) + the mirrored manifest builder; gates.py gained the
#: zero_contract_version_mismatch third-binding detail branch (the
#: eight gate names / order / fail-closed semantics unchanged); the
#: report.py _contract_section gained the third-binding branch (the
#: report schema unchanged); cli.py gained the corpus-build 1.2.0
#: generation. The pre-R2 literals (contract_v2_1.py
#: dc86899f..., fixtures.py cdb60166..., corpus.py 876edbe8...,
#: gates.py 113c7b53..., report.py cad62e42..., cli.py 0102c4cc... -
#: the ac75f47 content) are OBSOLETE and must not be restored as
#: current expectations.
R2_ENDPOINT_MODULE_PINS: dict[str, str] = {
    "product_intelligence/semantic/contract_v2_1.py": (
        "d9e564ef1824b55e31a2096082feff2e5d7d7df42154b4845785f4d846617ea4"
    ),
    "product_intelligence/evaluation/semantic_v2/corpus.py": (
        "4c0851a82b2f0863a16938c419e49938c86c1494aefbbde03684e496ee4fb4e4"
    ),
    "product_intelligence/evaluation/semantic_v2/cli.py": (
        "e4853546e879eaf1b1edb69002b7f07aece15f5199e7d4979ae662eb84d9c645"
    ),
    "product_intelligence/evaluation/semantic_v2/fixtures.py": (
        "ac8777dc27cdf879415645a04468690366d5d92f515c67fe7f794482cb0c783f"
    ),
    "product_intelligence/evaluation/semantic_v2/gates.py": (
        "a441ada2a275983f15ddb39f770c4163a42c4f95255c99f7565ea6d83c582e3f"
    ),
    "product_intelligence/evaluation/semantic_v2/report.py": (
        "45626ae166cf6ba0e4818357dc65363bf837503153a78764b518a7294f6a8619"
    ),
}

#: The required manifest statement (the task's exact wording).
REQUIRED_MANIFEST_STATEMENT = (
    "Corpus 1.2.0 is a binding-registration and "
    "semantic-compatibility corpus. It does not independently "
    "qualify FU4 Bundle composition authority."
)


def _file_digest(relative_path: str) -> str:
    return hashlib.sha256((REPO_ROOT / relative_path).read_bytes()).hexdigest()


def _write_corpus(tmp_path: Path, doc: dict) -> Path:
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


# The R1 record / replay surface + its test construction helpers (the
# house cross-test-helper pattern - the R1 suite's helpers are the
# offline recorded-input builders for the registered FU4 record).
from tests.research.test_semantic_decision_v2_fu4 import (  # noqa: E402
    CLAUSE,
    COUNT_ONLY_RAW_DETAIL,
    EST_RAW_DETAIL,
    _bundle_channel,
    _case_with_channel,
    _context,
    _extract,
    _fu4_record,
    _make_target_attestation,
    _make_target_fu4,
    _recompute_output_digest,
    _roundtrip,
)

from product_intelligence.evaluation.semantic_v2.canonical import (  # noqa: E402
    canonical_sha256,
)
from product_intelligence.evaluation.semantic_v2.capture import (  # noqa: E402
    PRIMARY_ROUTE,
)
from product_intelligence.evaluation.semantic_v2.corpus import (  # noqa: E402
    BINDING_CORPUS_VERSIONS,
    CorpusIntegrityError,
    KNOWN_PRODUCTION_BINDINGS,
    build_manifest_document,
    load_corpus,
    verify_manifest,
)
from product_intelligence.evaluation.semantic_v2.direct_capture import (  # noqa: E402
    DirectCaptureIntegrityError,
    load_direct_capture,
    verify_direct_capture_against_corpus,
)
from product_intelligence.evaluation.semantic_v2.evaluator import (  # noqa: E402
    QualificationContractError,
    evaluate_direct_for_model,
    evaluate_no_capture,
)
from product_intelligence.evaluation.semantic_v2.fixtures import (  # noqa: E402
    CORPUS_VERSION_2_1_FU4,
    build_corpus_2_1_document,
    build_corpus_2_1_fu4_document,
    build_corpus_document,
)
from product_intelligence.evaluation.semantic_v2.gates import (  # noqa: E402
    HARD_SAFETY_GATES,
    decide,
    evaluate_safety_gates,
)
from product_intelligence.evaluation.semantic_v2.policy import (  # noqa: E402
    load_policy,
    policy_applies_to,
)
from product_intelligence.evaluation.semantic_v2.report import (  # noqa: E402
    ReportError,
    build_report,
    render_markdown,
    verify_direct_report,
    verify_report,
)
from product_intelligence.research import (  # noqa: E402
    AUTHORITY_CONTRACT_VERSION_V2_FU4,
    AuthorityTier,
    PRICING_ELIGIBLE_TIERS,
    SalesUnitAuthorityV2,
    V1_CONTRACT_BINDING,
    V2_AUTHORITY_QUALIFIED,
    V2_CONTRACT_BINDING,
)
from product_intelligence.research import semantic_authority_fu4 as fu4  # noqa: E402
from product_intelligence.research import semantic_authority_fu3 as fu3  # noqa: E402
from product_intelligence.research import (  # noqa: E402
    semantic_decision_v2 as sdv2,
)
from product_intelligence.research import (  # noqa: E402
    semantic_decision_v2_fu4 as sdv4,
)
from product_intelligence.research.sales_unit_extraction import (  # noqa: E402
    SalesUnitExtractionState,
)
from product_intelligence.research.semantic_authority_fu4 import (  # noqa: E402
    BundleCompositionStateV2FU4,
    candidate_composition_from_extraction,
    derive_sales_unit_authority_fu4_case,
)
from product_intelligence.research.semantic_authority_fu3 import (  # noqa: E402
    TargetSalesUnitEvidenceSourceV2,
    TargetSalesUnitFormV2,
)
from product_intelligence.research.semantic_decision_codec import (  # noqa: E402
    SemanticDecisionCodecError,
    decode_semantic_decision_record,
    encode_semantic_decision_record,
    supported_contract_bindings,
)
from product_intelligence.research.semantic_decision_replay import (  # noqa: E402
    SUPPORTED_CONTRACT_BINDINGS,
    replay_semantic_decision,
)
from product_intelligence.semantic.contract_v2_1 import (  # noqa: E402
    SEMANTIC_PROMPT_VERSION_V2_1,
    V2_1_CONTRACT_BINDING,
    V2_1_FU4_CONTRACT_BINDING,
)


@pytest.fixture(scope="module")
def corpus_1_0_0():
    return load_corpus(CORPUS_PATH)


@pytest.fixture(scope="module")
def corpus_1_1_0():
    return load_corpus(CORPUS_2_1_PATH)


@pytest.fixture(scope="module")
def corpus_1_2_0():
    return load_corpus(CORPUS_2_1_FU4_PATH)


@pytest.fixture(scope="module")
def policy():
    return load_policy(POLICY_PATH)


# ===========================================================================
# T1. The registry and the seal (the four known bindings, distinguished
#     exactly; unknown / mixed-axis bindings fail closed)
# ===========================================================================


class TestRegistryAndSeal:
    def test_the_four_known_bindings_are_distinguished_exactly(self) -> None:
        # Item 1: the system knows EXACTLY four bindings, and each is
        # distinguished exactly on every surface: V1 (codec / replay
        # only - never a harness seal), 2.0/FU2 (codec + replay +
        # harness 1.0.0), 2.1/FU3 (harness 1.1.0 only - codec /
        # replay-refused), 2.1/FU4 (codec + replay + harness 1.2.0).
        # Unknown or mixed-axis bindings fail closed - no fallback to
        # a nearby binding.
        assert V2_1_FU4_CONTRACT_BINDING == (
            "V2", "2.1", 1, 1, AUTHORITY_CONTRACT_VERSION_V2_FU4
        )
        # The research record adapter's mirror is drift-pinned against
        # the semantic layer's 2.1 owner (the P1 discipline).
        assert sdv4.V2_FU4_CONTRACT_BINDING == tuple(V2_1_FU4_CONTRACT_BINDING)
        assert sdv4.V2_FU4_CONTRACT_BINDING == (
            "V2", "2.1", 1, 1, AUTHORITY_CONTRACT_VERSION_V2_FU4
        )
        # Codec / replay union: exactly (V1, 2.0/FU2, 2.1/FU4); the
        # harness-only 2.1/FU3 binding is NOT registered (unchanged by
        # R2); no fourth production binding exists.
        assert supported_contract_bindings() == (
            V1_CONTRACT_BINDING,
            V2_CONTRACT_BINDING,
            tuple(V2_1_FU4_CONTRACT_BINDING),
        )
        assert SUPPORTED_CONTRACT_BINDINGS == supported_contract_bindings()
        assert tuple(V2_1_CONTRACT_BINDING) not in {
            tuple(b) for b in SUPPORTED_CONTRACT_BINDINGS
        }
        # Harness seal registry: exactly the three production bindings,
        # each to its own corpus version.
        assert BINDING_CORPUS_VERSIONS == {
            tuple(V2_CONTRACT_BINDING): "1.0.0",
            tuple(V2_1_CONTRACT_BINDING): "1.1.0",
            tuple(V2_1_FU4_CONTRACT_BINDING): "1.2.0",
        }
        assert KNOWN_PRODUCTION_BINDINGS == frozenset(BINDING_CORPUS_VERSIONS)
        # V1 is never a harness seal (historical V1, codec / replay
        # only - unchanged).
        assert tuple(V1_CONTRACT_BINDING) not in BINDING_CORPUS_VERSIONS
        # Unknown / mixed-axis bindings fail closed at the seal level
        # (no fallback to a nearby binding).
        for forged in (
            ("V2", "2.0", 1, 1, AUTHORITY_CONTRACT_VERSION_V2_FU4),
            ("V2", "2.1", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU9"),
            ("V2", "2.2", 1, 1, AUTHORITY_CONTRACT_VERSION_V2_FU4),
            ("V1", "2.1", 1, 1, AUTHORITY_CONTRACT_VERSION_V2_FU4),
            ("V2", "2.1", 2, 1, AUTHORITY_CONTRACT_VERSION_V2_FU4),
        ):
            assert forged not in BINDING_CORPUS_VERSIONS
            assert forged not in KNOWN_PRODUCTION_BINDINGS
            assert forged not in {
                tuple(b) for b in SUPPORTED_CONTRACT_BINDINGS
            }

    def test_fu4_maps_only_to_corpus_1_2_0(self) -> None:
        # Item 2: the FU4 binding seals EXACTLY corpus 1.2.0 - no other
        # version, and the 1.2.0 version is sealed under no other
        # binding.
        assert (
            BINDING_CORPUS_VERSIONS[tuple(V2_1_FU4_CONTRACT_BINDING)]
            == "1.2.0"
            == CORPUS_VERSION_2_1_FU4
        )
        assert set(BINDING_CORPUS_VERSIONS.values()) == {"1.0.0", "1.1.0", "1.2.0"}
        assert "1.2.0" not in (
            v for k, v in BINDING_CORPUS_VERSIONS.items() if k != tuple(V2_1_FU4_CONTRACT_BINDING)
        )

    def test_historical_binding_to_corpus_mappings_unchanged(self) -> None:
        # Item 3: the two historical seal entries are byte-unchanged
        # (2.0/FU2 -> 1.0.0, 2.1/FU3 -> 1.1.0); the existing V1,
        # 2.0/FU2, and 2.1/FU3 bindings are all unchanged (their
        # owner constants, their registry positions, their seals).
        assert tuple(V2_CONTRACT_BINDING) == (
            "V2", "2.0", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU2"
        )
        assert tuple(V2_1_CONTRACT_BINDING) == (
            "V2", "2.1", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU3"
        )
        assert V2_1_CONTRACT_BINDING[4] == fu3.AUTHORITY_CONTRACT_VERSION_V2_FU3
        assert (
            BINDING_CORPUS_VERSIONS[tuple(V2_CONTRACT_BINDING)] == "1.0.0"
        )
        assert (
            BINDING_CORPUS_VERSIONS[tuple(V2_1_CONTRACT_BINDING)] == "1.1.0"
        )
        # The live record type still pins the frozen 2.0 / FU2 binding
        # (the registration wires no live path).
        assert sdv2.V2_CONTRACT_BINDING == V2_CONTRACT_BINDING
        assert sdv2.SEMANTIC_V2_ADAPTER.supported_bindings == (V2_CONTRACT_BINDING,)


# ===========================================================================
# T2. The corpus 1.2.0 binding-only re-seal (design row 17 + items
#     4-10, 26)
# ===========================================================================


class TestCorpus120ReSeal:
    def test_all_56_historical_case_ids_preserved(self) -> None:
        # Item 4: every historical case id survives the re-seal.
        d10 = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
        d11 = json.loads(CORPUS_2_1_PATH.read_text(encoding="utf-8"))
        d12 = json.loads(CORPUS_2_1_FU4_PATH.read_text(encoding="utf-8"))
        ids10 = [c["case_id"] for c in d10["cases"]]
        ids11 = [c["case_id"] for c in d11["cases"]]
        ids12 = [c["case_id"] for c in d12["cases"]]
        assert len(ids12) == 56
        assert ids12 == ids11 == ids10
        assert len(set(ids12)) == 56

    def test_all_56_expected_semantic_labels_unchanged(self) -> None:
        # Item 5: every per-case document (payload, expected outcome -
        # decision / acceptable decisions / conflict classes /
        # ambiguity classification / negative controls - and the
        # sealed per-case digest) is byte-identical to 1.1.0 (and to
        # 1.0.0); no label moved.
        d10 = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
        d11 = json.loads(CORPUS_2_1_PATH.read_text(encoding="utf-8"))
        d12 = json.loads(CORPUS_2_1_FU4_PATH.read_text(encoding="utf-8"))
        c10 = {c["case_id"]: c for c in d10["cases"]}
        c11 = {c["case_id"]: c for c in d11["cases"]}
        c12 = {c["case_id"]: c for c in d12["cases"]}
        for case_id in c11:
            assert (
                json.dumps(c12[case_id], sort_keys=True)
                == json.dumps(c11[case_id], sort_keys=True)
                == json.dumps(c10[case_id], sort_keys=True)
            ), case_id
        assert d12["label_revisions"] == [] == d11["label_revisions"]
        # The three sales-unit safety cases keep their exact labels.
        for case_id, decision, classes in (
            ("V2Q-SSD-SU-TRAY-0032", "NO_MATCH", ("PACKAGING_QUANTITY",)),
            ("V2Q-SSD-SU-MULTI-0033", "NO_MATCH", ("PACKAGING_QUANTITY",)),
            ("V2Q-GPU-SU-BUNDLE-0034", "NO_MATCH", ("BUNDLE",)),
        ):
            expected = c12[case_id]["expected"]
            assert expected["decision"] == decision
            assert tuple(sorted(expected["conflict_classes"])) == classes

    def test_only_the_authorized_metadata_moved(self) -> None:
        # Design row 17: EXACTLY {corpus_version, semantic_contract_
        # binding, corpus_digest} moved; corpus_id / schema / label /
        # created_utc unchanged; the digest is the canonical
        # recomputation over the re-sealed state.
        d11 = json.loads(CORPUS_2_1_PATH.read_text(encoding="utf-8"))
        d12 = json.loads(CORPUS_2_1_FU4_PATH.read_text(encoding="utf-8"))
        moved = {
            k
            for k in d12
            if k not in d11 or json.dumps(d11[k], sort_keys=True)
            != json.dumps(d12[k], sort_keys=True)
        }
        assert moved == {"corpus_version", "semantic_contract_binding", "corpus_digest"}
        assert d12["corpus_version"] == "1.2.0"
        assert d12["semantic_contract_binding"] == list(V2_1_FU4_CONTRACT_BINDING)
        assert d12["corpus_id"] == d11["corpus_id"]
        assert d12["corpus_label"] == d11["corpus_label"]
        assert d12["created_utc"] == d11["created_utc"]
        assert d12["corpus_schema_version"] == d11["corpus_schema_version"]
        state = {
            k: v
            for k, v in d12.items()
            if k not in ("label_revisions", "corpus_digest")
        }
        assert canonical_sha256(state) == d12["corpus_digest"]

    def test_corpus_1_2_0_canonical_digest_and_manifest_integrity(
        self, corpus_1_2_0
    ) -> None:
        # Item 6: the committed 1.2.0 corpus loads (the loader
        # re-verifies every per-case digest + the whole-corpus digest +
        # the seal), matches the recorded canonical digest, and its
        # committed manifest verifies with the required statement +
        # the explicit 1.1.0 lineage inside the manifest digest;
        # regenerating from the auditable source reproduces BOTH
        # artifacts byte-for-byte (the P1 property).
        assert corpus_1_2_0.corpus_version == "1.2.0"
        assert tuple(corpus_1_2_0.semantic_contract_binding) == (
            "V2", "2.1", 1, 1, AUTHORITY_CONTRACT_VERSION_V2_FU4
        )
        assert corpus_1_2_0.corpus_digest == CORPUS_1_2_0_DIGEST
        committed_manifest = json.loads(
            MANIFEST_2_1_FU4_PATH.read_text(encoding="utf-8")
        )
        verify_manifest(corpus_1_2_0, committed_manifest)
        assert committed_manifest["manifest_digest"] == MANIFEST_1_2_0_DIGEST
        assert committed_manifest["corpus_version"] == "1.2.0"
        assert committed_manifest["case_count"] == 56
        # The required statement (the task's exact wording) - inside
        # the manifest digest (a tamper is an integrity error).
        assert committed_manifest["statement"] == REQUIRED_MANIFEST_STATEMENT
        # The explicit lineage from corpus 1.1.0.
        assert committed_manifest["lineage"] == {
            "derived_from_corpus_version": "1.1.0",
            "derived_from_corpus_digest": CORPUS_1_1_0_DIGEST,
        }
        # Regeneration from the auditable source is byte-for-byte.
        rebuilt_corpus = build_corpus_2_1_fu4_document()
        assert (
            json.dumps(rebuilt_corpus, indent=1, sort_keys=True, ensure_ascii=True)
            + "\n"
        ) == CORPUS_2_1_FU4_PATH.read_text(encoding="utf-8")
        rebuilt_manifest = build_manifest_document(rebuilt_corpus)
        assert (
            json.dumps(rebuilt_manifest, indent=1, sort_keys=True, ensure_ascii=True)
            + "\n"
        ) == MANIFEST_2_1_FU4_PATH.read_text(encoding="utf-8")
        # The historical manifests do NOT gain the additive keys.
        for name in ("manifest_v1.json", "manifest_2_1.json"):
            historical = json.loads(
                (CORPUS_DIR / name).read_text(encoding="utf-8")
            )
            assert "statement" not in historical
            assert "lineage" not in historical

    def test_wrong_corpus_digest_rejected(self, tmp_path) -> None:
        # Item 7: a tampered 1.2.0 document is refused by the loader -
        # any per-case field edit (the case digest), any corpus-level
        # edit (the whole-corpus digest), or a stale corpus_digest.
        doc = json.loads(CORPUS_2_1_FU4_PATH.read_text(encoding="utf-8"))
        tampered = copy.deepcopy(doc)
        target = next(c for c in tampered["cases"] if c["case_id"] == "V2Q-GPU-SU-BUNDLE-0034")
        target["expected"]["decision"] = "MATCH"
        target["expected"]["acceptable_decisions"] = ["MATCH"]
        with pytest.raises(CorpusIntegrityError, match="case_digest"):
            load_corpus(_write_corpus(tmp_path, tampered))
        tampered = copy.deepcopy(doc)
        tampered["corpus_label"] = "mutated-after-seal"
        with pytest.raises(CorpusIntegrityError, match="corpus_digest"):
            load_corpus(_write_corpus(tmp_path, tampered))
        tampered = copy.deepcopy(doc)
        tampered["corpus_version"] = "1.2.1"
        with pytest.raises(CorpusIntegrityError, match="sealed under"):
            load_corpus(_write_corpus(tmp_path, tampered))
        tampered = copy.deepcopy(doc)
        tampered["corpus_digest"] = "0" * 64
        with pytest.raises(CorpusIntegrityError, match="corpus_digest"):
            load_corpus(_write_corpus(tmp_path, tampered))

    def test_wrong_binding_rejected(self, tmp_path) -> None:
        # Item 8: the 1.2.0 version under a WRONG binding (2.1/FU3 or
        # 2.0/FU2) is refused - a corpus version is only interpretable
        # under the production binding it was sealed with.
        doc = json.loads(CORPUS_2_1_FU4_PATH.read_text(encoding="utf-8"))
        for wrong_binding in (
            ["V2", "2.1", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU3"],
            ["V2", "2.0", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU2"],
        ):
            tampered = copy.deepcopy(doc)
            tampered["semantic_contract_binding"] = wrong_binding
            with pytest.raises(CorpusIntegrityError, match="sealed under"):
                load_corpus(_write_corpus(tmp_path, tampered))

    def test_unknown_authority_token_rejected(self, tmp_path) -> None:
        # Item 9: an unknown authority token in the corpus binding is
        # refused (no fallback to a nearby binding).
        doc = json.loads(CORPUS_2_1_FU4_PATH.read_text(encoding="utf-8"))
        tampered = copy.deepcopy(doc)
        tampered["semantic_contract_binding"] = [
            "V2", "2.1", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU9",
        ]
        with pytest.raises(CorpusIntegrityError, match="known production"):
            load_corpus(_write_corpus(tmp_path, tampered))
        # Whitespace / case variants of the FU4 token are not the
        # token (the loader's exact-tuple comparison fails closed).
        tampered = copy.deepcopy(doc)
        tampered["semantic_contract_binding"] = [
            "V2", "2.1", 1, 1, AUTHORITY_CONTRACT_VERSION_V2_FU4 + " ",
        ]
        with pytest.raises(CorpusIntegrityError, match="known production"):
            load_corpus(_write_corpus(tmp_path, tampered))

    def test_cross_version_corpus_substitution_rejected(self, tmp_path) -> None:
        # Item 10: no corpus version may be substituted for another -
        # in either direction, across the whole lineage.
        doc_11 = json.loads(CORPUS_2_1_PATH.read_text(encoding="utf-8"))
        doc_10 = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
        doc_12 = json.loads(CORPUS_2_1_FU4_PATH.read_text(encoding="utf-8"))
        # 1.1.0 / 1.0.0 sealed under the FU4 binding: refused.
        for historical in (doc_11, doc_10):
            tampered = copy.deepcopy(historical)
            tampered["semantic_contract_binding"] = list(V2_1_FU4_CONTRACT_BINDING)
            with pytest.raises(CorpusIntegrityError, match="sealed under"):
                load_corpus(_write_corpus(tmp_path, tampered))
        # 1.2.0 sealed under the historical bindings: refused.
        for wrong_binding in (
            list(V2_1_CONTRACT_BINDING),
            list(V2_CONTRACT_BINDING),
        ):
            tampered = copy.deepcopy(doc_12)
            tampered["semantic_contract_binding"] = wrong_binding
            with pytest.raises(CorpusIntegrityError, match="sealed under"):
                load_corpus(_write_corpus(tmp_path, tampered))
        # A 1.2.0 document with a 1.1.0 version (or vice versa) under
        # the matching binding: refused.
        tampered = copy.deepcopy(doc_12)
        tampered["corpus_version"] = "1.1.0"
        tampered["semantic_contract_binding"] = list(V2_1_FU4_CONTRACT_BINDING)
        with pytest.raises(CorpusIntegrityError, match="sealed under"):
            load_corpus(_write_corpus(tmp_path, tampered))

    def test_historical_corpus_artifacts_byte_identical(self) -> None:
        # Item 26: the committed 1.0.0 / 1.1.0 artifacts + the DRAFT
        # policy are byte-identical to the recorded digests (no change
        # to any historical corpus version).
        for name, expected in HISTORICAL_ARTIFACT_FILE_DIGESTS.items():
            assert _file_digest(f"evaluation/semantic_v2_qualification/{name}") == (
                expected
            ), name
        # And their inner corpus digests stand.
        for path, digest in (
            (CORPUS_PATH, CORPUS_1_0_0_DIGEST),
            (CORPUS_2_1_PATH, CORPUS_1_1_0_DIGEST),
        ):
            assert json.loads(path.read_text(encoding="utf-8"))["corpus_digest"] == (
                digest
            )


# ===========================================================================
# T3. The no-capture baseline + the capture / report surface (design
#     rows 17/20-24 + items 11-17)
# ===========================================================================


class TestNoCaptureAndCapture:
    def test_fu4_no_capture_evaluation_succeeds_on_the_sealed_corpus(
        self, corpus_1_2_0, policy
    ) -> None:
        # Item 11: the FU4 no-capture evaluation runs to completion on
        # the valid sealed 1.2.0 corpus for BOTH pinned routes:
        # 43/43 eligible NOT_CAPTURED, the 13 contract-negative cases
        # evaluated for rejection correctness, all eight gates pass,
        # the decision POLICY_PENDING (never a pass), and the committed
        # baseline reproduces byte-for-byte (JSON + Markdown).
        for route, stem_route in (
            (primary_route(), "amax_qwen3.8-27b"),
            (fallback_route(), "vllm-262k_Qwen3.6-27B-262K"),
        ):
            result = evaluate_no_capture(corpus_1_2_0, *route)
            assert (result.provider, result.model) == route
            assert result.route_role == (
                "PRIMARY" if route == PRIMARY_ROUTE else "FALLBACK"
            )
            assert tuple(result.semantic_contract_binding) == (
                "V2", "2.1", 1, 1, AUTHORITY_CONTRACT_VERSION_V2_FU4
            )
            gates = evaluate_safety_gates(result)
            assert all(g.passed for g in gates.values())
            assert result.metrics["counts"]["not_captured"] == 43
            assert result.metrics["counts"]["not_invoked"] == 0
            assert result.metrics["counts"]["contract_violations"] == 0
            te = (
                evaluate_thresholds_for(policy, result, corpus_1_2_0)
            )
            decision, rationale = decide(result, gates, policy, te)
            assert decision == "POLICY_PENDING"
            assert any(r.startswith("POLICY_PENDING:") for r in rationale)
            report = build_report(
                result=result,
                gates=gates,
                policy=policy,
                threshold_evaluation=te,
                decision=decision,
                rationale=rationale,
                corpus=corpus_1_2_0,
                generated_utc=GENERATED_UTC,
            )
            committed_json = (
                BASELINE_1_2_0_REPORT_DIR
                / f"no-capture_{stem_route}__report.json"
            ).read_text(encoding="utf-8")
            assert (
                json.dumps(report, indent=1, sort_keys=True, ensure_ascii=True)
                + "\n"
            ) == committed_json
            committed_md = (
                BASELINE_1_2_0_REPORT_DIR
                / f"no-capture_{stem_route}__report.md"
            ).read_text(encoding="utf-8")
            assert render_markdown(report) == committed_md

    def test_invalid_prompt_2_1_output_fails_closed(
        self, tmp_path, corpus_1_2_0, policy
    ) -> None:
        # Item 12: an invalid Prompt 2.1 output (one that does not
        # survive the frozen production parser) is a bounded
        # CAPTURE_INTEGRITY_FAILURE - never substituted with the
        # expected answer, never a semantic decision; the evaluation
        # is INCOMPLETE_COVERAGE, never QUALIFIED.
        case = corpus_1_2_0.semantic_cases[0]
        path = write_direct_capture(
            tmp_path / "d.json",
            corpus_1_2_0,
            invalid={case.case_id: "{not a valid response"},
        )
        capture = load_direct_capture(path)
        verify_direct_capture_against_corpus(capture, corpus_1_2_0)
        result = evaluate_direct_for_model(corpus_1_2_0, capture, *primary_route())
        outcome = next(o for o in result.outcomes if o.case_id == case.case_id)
        assert outcome.state == "CAPTURE_INTEGRITY_FAILURE"
        assert outcome.verdict == "INTEGRITY_FAILED"
        gates = evaluate_safety_gates(result)
        te = evaluate_thresholds_for(policy, result, corpus_1_2_0)
        decision, rationale = decide(result, gates, policy, te)
        # The invalid response fails the zero-schema-bypass gate: an
        # invalid captured output is a bounded safety failure (never
        # silently accepted, never substituted) - NOT_QUALIFIED, never
        # QUALIFIED, and the integrity failure stays visible.
        assert decision == "NOT_QUALIFIED"
        assert "SAFETY_GATE_FAILED:zero_schema_bypass_acceptance" in rationale
        assert not gates["zero_schema_bypass_acceptance"].passed
        assert case.case_id in gates[
            "zero_schema_bypass_acceptance"
        ].failing_case_ids
        # The other 42 label-consistent responses evaluate normally -
        # the failure is bounded to its own case.
        assert result.metrics["counts"]["capture_integrity_failures"] == 1
        assert sum(1 for o in result.outcomes if o.state == "EVALUATED") == 42

    def test_primary_fallback_provenance_independently_recorded(
        self, tmp_path, corpus_1_2_0
    ) -> None:
        # Item 13: the two 1.2.0 baselines are separate per-model
        # artifacts (the no-capture discipline), and a capture bound to
        # one pinned model is never evaluated as the other (no
        # response transfer between identities).
        primary_report = json.loads(
            (
                BASELINE_1_2_0_REPORT_DIR
                / "no-capture_amax_qwen3.8-27b__report.json"
            ).read_text(encoding="utf-8")
        )
        fallback_report = json.loads(
            (
                BASELINE_1_2_0_REPORT_DIR
                / "no-capture_vllm-262k_Qwen3.6-27B-262K__report.json"
            ).read_text(encoding="utf-8")
        )
        assert primary_report["model"] == {
            "provider": "amax",
            "model": "qwen3.8-27b",
            "route_role": "PRIMARY",
        }
        assert fallback_report["model"] == {
            "provider": "vllm-262k",
            "model": "Qwen3.6-27B-262K",
            "route_role": "FALLBACK",
        }
        # A primary-bound capture is refused for the fallback model.
        path = write_direct_capture(tmp_path / "d.json", corpus_1_2_0)
        capture = load_direct_capture(path)
        assert (capture.target_provider, capture.target_model) == primary_route()
        with pytest.raises(QualificationContractError):
            evaluate_direct_for_model(corpus_1_2_0, capture, *fallback_route())

    def test_wrong_provider_model_provenance_rejected(
        self, tmp_path, corpus_1_2_0
    ) -> None:
        # Item 14: no qualification surface accepts a non-pinned
        # provider / model identity - the no-capture route check and
        # the direct-capture load check both fail closed.
        with pytest.raises(QualificationContractError, match="pinned routes"):
            evaluate_no_capture(corpus_1_2_0, "amax", "nemotron-3-super")
        with pytest.raises(QualificationContractError, match="pinned routes"):
            evaluate_no_capture(corpus_1_2_0, "other", "model")
        path = write_direct_capture(
            tmp_path / "d.json",
            corpus_1_2_0,
            target=("other-provider", "other-model"),
        )
        with pytest.raises(DirectCaptureIntegrityError):
            load_direct_capture(path)

    def test_historical_1_0_0_1_1_0_baselines_remain_interpretable(
        self, corpus_1_0_0, corpus_1_1_0, corpus_1_2_0
    ) -> None:
        # Item 15 (+ 27): the committed 1.0.0 / 1.1.0 no-capture
        # baselines verify against their own corpora (historical
        # reports remain interpretable), and the cross-lineage
        # combination is refused in BOTH directions (a 1.2.0 report on
        # a historical corpus; a historical report on 1.2.0).
        for report_dir, corpus in (
            (BASELINE_REPORT_DIR, corpus_1_0_0),
            (BASELINE_2_1_REPORT_DIR, corpus_1_1_0),
        ):
            paths = sorted(report_dir.glob("*__report.json"))
            assert len(paths) == 2
            for path in paths:
                report = json.loads(path.read_text(encoding="utf-8"))
                verify_report(report, corpus)
        for path in sorted(BASELINE_1_2_0_REPORT_DIR.glob("*__report.json")):
            report = json.loads(path.read_text(encoding="utf-8"))
            verify_report(report, corpus_1_2_0)
        # Cross-lineage refusal (both directions).
        for historical_dir in (BASELINE_REPORT_DIR, BASELINE_2_1_REPORT_DIR):
            for path in sorted(historical_dir.glob("*__report.json")):
                report = json.loads(path.read_text(encoding="utf-8"))
                with pytest.raises(ReportError):
                    verify_report(report, corpus_1_2_0)
        for path in sorted(BASELINE_1_2_0_REPORT_DIR.glob("*__report.json")):
            report = json.loads(path.read_text(encoding="utf-8"))
            for historical in (corpus_1_0_0, corpus_1_1_0):
                with pytest.raises(ReportError):
                    verify_report(report, historical)
                with pytest.raises(ReportError):
                    verify_direct_report(report, historical)

    def test_no_live_model_call_during_no_capture_or_replay(
        self, corpus_1_2_0, monkeypatch
    ) -> None:
        # Item 16: no live model call (or ANY network call) occurs
        # during the no-capture evaluation, the report build / verify,
        # or the FU4 record replay - armed fail-fast socket sentinels.
        def refuse(*_a, **_k):
            raise AssertionError("a network call was attempted")

        monkeypatch.setattr(socket, "socket", refuse)
        monkeypatch.setattr(socket, "create_connection", refuse)
        monkeypatch.setattr(socket, "getaddrinfo", refuse)
        result = evaluate_no_capture(corpus_1_2_0, *primary_route())
        gates = evaluate_safety_gates(result)
        assert all(g.passed for g in gates.values())
        report = build_report(
            result=result,
            gates=gates,
            policy=None,
            threshold_evaluation=None,
            decision="POLICY_PENDING",
            rationale=("POLICY_PENDING:no approved applicable policy",),
            corpus=corpus_1_2_0,
            generated_utc=GENERATED_UTC,
        )
        verify_report(report, corpus_1_2_0)
        # The R1 record / replay round trip over the FU4 binding is
        # zero-live as well (the replay re-runs the frozen derivation
        # + presentation gate; no provider / model / network surface).
        ctx = _context()
        chan = _bundle_channel(None, COUNT_ONLY_RAW_DETAIL)
        case = _case_with_channel(chan)
        record = _fu4_record(case=case, ctx=ctx, channel=chan)
        _roundtrip(record)
        # A historical V2 record replays zero-live under the same
        # sentinels (the R1 byte-compatibility property).
        from tests.research.test_semantic_decision_v2 import _build_record

        from product_intelligence.research import (
            V2Confidence,
            V2SemanticDecision,
        )
        from product_intelligence.research.semantic_decision_codec import (
            decode_semantic_decision_record,
            encode_semantic_decision_record,
        )

        v2_record = _build_record(
            decision=V2SemanticDecision.MATCH, confidence=V2Confidence.HIGH
        )
        payload = encode_semantic_decision_record(v2_record)
        decoded = decode_semantic_decision_record(payload, schema_version=1)
        replay_semantic_decision(decoded)

    def test_fu4_semantic_qualification_cannot_set_production_authority_flags(
        self, tmp_path, corpus_1_2_0, policy
    ) -> None:
        # Item 17 (+ design row 21): every committed 1.2.0 baseline
        # carries granted: false + v2_authority_qualified: false + the
        # evaluation-evidence-only note, and the decision is
        # POLICY_PENDING; a HYPOTHETICAL full-pass evaluation over
        # 1.2.0 (every eligible case answering its label) with the
        # DRAFT policy is STILL POLICY_PENDING - the DRAFT is 1.0.0-
        # scoped and unapproved, so 1.2.0 qualification can never set
        # a production authority flag. The live record type still pins
        # the FU2 token.
        for path in sorted(BASELINE_1_2_0_REPORT_DIR.glob("*__report.json")):
            report = json.loads(path.read_text(encoding="utf-8"))
            assert report["authority"]["granted"] is False
            assert report["authority"]["v2_authority_qualified"] is False
            assert (
                report["authority"]["note"]
                == "this report is evaluation evidence only; it grants "
                "no pricing authority, no tier promotion, and no "
                "human-review behavior change"
            )
            assert report["decision"] == "POLICY_PENDING"
            assert report["policy"] is None
        assert not policy_applies_to(
            policy, corpus_1_2_0.corpus_id, corpus_1_2_0.corpus_version
        )
        # The hypothetical full pass (label-consistent responses for
        # every eligible case; zero failures; complete coverage).
        path = write_direct_capture(tmp_path / "full.json", corpus_1_2_0)
        capture = load_direct_capture(path)
        result = evaluate_direct_for_model(corpus_1_2_0, capture, *primary_route())
        assert result.metrics["counts"]["not_captured"] == 0
        assert result.metrics["counts"]["runtime_failure_count"] == 0
        assert result.metrics["counts"]["capture_integrity_failures"] == 0
        gates = evaluate_safety_gates(result)
        assert all(g.passed for g in gates.values())
        te = evaluate_thresholds_for(policy, result, corpus_1_2_0)
        assert te is None  # the DRAFT is not applicable to 1.2.0
        decision, rationale = decide(result, gates, policy, te)
        assert decision == "POLICY_PENDING"
        assert any(r.startswith("POLICY_PENDING:") for r in rationale)
        # Even with the DRAFT thresholds artificially evaluated, the
        # unapproved status keeps the decision POLICY_PENDING (the
        # ladder: policy approval > thresholds).
        from product_intelligence.evaluation.semantic_v2.policy import (
            evaluate_thresholds,
        )

        te_forced = evaluate_thresholds(policy, result.metrics)
        decision_forced, _ = decide(result, gates, policy, te_forced)
        assert decision_forced == "POLICY_PENDING"
        # The live record type still pins the frozen 2.0 / FU2 binding.
        assert sdv2.V2_AUTHORITY_QUALIFIED is False
        assert sdv2.V2_CONTRACT_BINDING == V2_CONTRACT_BINDING


def evaluate_thresholds_for(policy, result, corpus) -> dict | None:
    """The CLI's threshold-evaluation rule (applicability-gated)."""
    from product_intelligence.evaluation.semantic_v2.policy import (
        evaluate_thresholds,
    )

    if policy is not None and policy_applies_to(
        policy, corpus.corpus_id, corpus.corpus_version
    ):
        return evaluate_thresholds(policy, result.metrics)
    return None


# ===========================================================================
# T4. Authority isolation (the FU4 bundle states are governed by the
#     R1 deterministic derivation + zero-live replay, never by the
#     corpus 1.2.0 semantic labels; items 18-24)
# ===========================================================================


class TestAuthorityIsolation:
    def test_fu4_bundle_states_governed_by_r1_replay_not_corpus_labels(
        self, corpus_1_2_0
    ) -> None:
        # Item 18: over the committed 1.2.0 sales-unit cases, the FU4
        # unit state is derived from the RECORDED CHANNEL (the R1
        # deterministic derivation + zero-live replay) - the corpus
        # semantic label (a model-side NO_MATCH) is never an input.
        # All three derive CONTRADICTED (the form axis over the
        # default single-unit target) and the recorded FU4 tier is
        # NEEDS_REVIEW (the ceiling fires) - never the automatic
        # comparable.
        for case_id in (
            "V2Q-SSD-SU-TRAY-0032",
            "V2Q-SSD-SU-MULTI-0033",
            "V2Q-GPU-SU-BUNDLE-0034",
        ):
            corpus_case = corpus_1_2_0.case(case_id)
            recorded = corpus_case.build_semantic_case()
            channel = recorded.candidate_commercial.sales_unit
            # The case-level FU4 derivation over the recorded channel
            # (no derivation-side records presented - the corpus
            # carries none).
            unit = derive_sales_unit_authority_fu4_case(
                recorded, None, None, None
            )
            assert unit is SalesUnitAuthorityV2.CONTRADICTED, case_id
            # The R1 record / replay governance: the SAME recorded
            # channel in an FU4 record replays to the SAME unit state
            # + the capped tier through the universal dispatch.
            ctx = _context()
            r1_case = _case_with_channel(channel)
            record = _fu4_record(case=r1_case, ctx=ctx, channel=channel)
            payload, decoded, replay = _roundtrip(record)
            assert decoded == record
            assert (
                replay.authority_decision.sales_unit_authority
                is SalesUnitAuthorityV2.CONTRADICTED
            )
            assert replay.authority_decision.tier is AuthorityTier.NEEDS_REVIEW
            assert (
                fu4.AuthorityRuleV2FU4.CEILING_SALES_UNIT_CONTRADICTED
                in replay.authority_decision.fired_rules
            )
            # The semantic label is recorded on the corpus (NO_MATCH +
            # the sales-unit conflict classes) and is NOT the unit
            # state: a MATCH evaluation over the identical channel
            # derives the identical unit (the label / decision never
            # enter the derivation).
            assert corpus_case.expected["decision"] == "NO_MATCH"
            from tests.research.test_semantic_decision_v2_fu4 import (
                _match_evaluation,
            )

            match_record = _fu4_record(
                case=r1_case, ctx=ctx, channel=channel,
                evaluation=_match_evaluation(),
            )
            _, _, match_replay = _roundtrip(match_record)
            assert (
                match_replay.authority_decision.sales_unit_authority
                is SalesUnitAuthorityV2.CONTRADICTED
            )

    def test_count_only_bundle_cannot_gain_automatic_comparable(self) -> None:
        # Item 19: a count-only bundle (the published count alone -
        # the P2-FU1 shape) cannot gain automatic comparable authority
        # under the FU4 binding: UNPROVEN unit, the cap tier
        # NEEDS_REVIEW, never pricing-eligible - even over a
        # same-count attested target record the count cannot
        # substitute for.
        ctx = _context()
        chan = _bundle_channel(3, COUNT_ONLY_RAW_DETAIL)
        case = _case_with_channel(chan)
        from product_intelligence.research.semantic_authority_fu3 import (
            TargetSalesUnitEvidenceV2,
        )

        same_count_target = TargetSalesUnitEvidenceV2(
            TargetSalesUnitFormV2.BUNDLE, 3,
            TargetSalesUnitEvidenceSourceV2.REVIEWED_TARGET_CONTEXT,
        )
        record = _fu4_record(
            case=case,
            ctx=ctx,
            channel=chan,
            target_evidence=same_count_target,
            candidate_composition=None,
            quantity_attestation=None,
        )
        _, _, replay = _roundtrip(record)
        decision = replay.authority_decision
        assert decision.sales_unit_authority is SalesUnitAuthorityV2.UNPROVEN
        assert decision.tier is AuthorityTier.NEEDS_REVIEW
        assert (
            fu4.AuthorityRuleV2FU4.CEILING_SALES_UNIT_NOT_PROVEN
            in decision.fired_rules
        )
        assert decision.tier not in PRICING_ELIGIBLE_TIERS
        # The same input preserves the historical FU3 behavior
        # (PROVEN over equal counts) - documented per-binding
        # behavior, never drift (the three-token coexistence).
        from tests.research.test_semantic_decision_v2_fu4 import (
            _match_evaluation,
        )

        from product_intelligence.research.semantic_authority_fu4 import (
            derive_authority_tier_for_contract_fu4,
        )

        fu3_decision = derive_authority_tier_for_contract_fu4(
            fu3.AUTHORITY_CONTRACT_VERSION_V2_FU3,
            ctx,
            _match_evaluation(),
            frozenset(),
            case.product_evidence,
            None,
            sales_unit_channel=chan,
            target_unit_evidence=same_count_target,
        )
        assert fu3_decision.sales_unit_authority is (
            SalesUnitAuthorityV2.PROVEN_EQUIVALENT
        )

    def test_missing_completeness_attestation_cannot_become_proven(self) -> None:
        # Item 20: a fully parseable published composition WITHOUT a
        # completeness attestation (the corpus 0034 shape -
        # SYNTACTICALLY_VALID, completeness-unknown) can never become
        # PROVEN under FU4, even over an independently attested-equal
        # target: the derivation holds the cap (UNPROVEN), and a
        # record claiming PROVEN + the automatic tier over that
        # evidence is un-constructible (the constructor invariants) -
        # hence undecodable.
        ctx = _context()
        chan = _bundle_channel(None, "bundle: 2x RAM + 1x CPU")
        case = _case_with_channel(chan)
        # The recorded channel's composition record (no marker - no
        # attestation).
        candidate = fu4.candidate_composition_from_channel(chan)
        assert candidate is not None
        assert candidate.state is BundleCompositionStateV2FU4.SYNTACTICALLY_VALID
        assert candidate.completeness_attestation is None
        target = _make_target_fu4(
            CLAUSE,
            BundleCompositionStateV2FU4.ESTABLISHED,
            None,
            _make_target_attestation(CLAUSE),
        )
        unit = derive_sales_unit_authority_fu4_case(
            case, candidate, target, None
        )
        assert unit is SalesUnitAuthorityV2.UNPROVEN
        record = _fu4_record(
            case=case,
            ctx=ctx,
            channel=chan,
            target_evidence=target,
            candidate_composition=candidate,
        )
        _, _, replay = _roundtrip(record)
        assert (
            replay.authority_decision.sales_unit_authority
            is SalesUnitAuthorityV2.UNPROVEN
        )
        assert replay.authority_decision.tier is AuthorityTier.NEEDS_REVIEW
        # The PROVEN direction stands only over the FULL corrected D6
        # conjunction (independently attested complete compositions on
        # BOTH sides) - the label-agnostic safe direction.
        est_chan = _bundle_channel(None, EST_RAW_DETAIL)
        est_case = _case_with_channel(est_chan)
        est_candidate = fu4.candidate_composition_from_channel(est_chan)
        assert est_candidate is not None
        assert est_candidate.state is BundleCompositionStateV2FU4.ESTABLISHED
        est_record = _fu4_record(
            case=est_case,
            ctx=ctx,
            channel=est_chan,
            target_evidence=_make_target_fu4(
                CLAUSE,
                BundleCompositionStateV2FU4.ESTABLISHED,
                None,
                _make_target_attestation(CLAUSE),
            ),
            candidate_composition=est_candidate,
        )
        _, _, est_replay = _roundtrip(est_record)
        assert est_replay.authority_decision.sales_unit_authority is (
            SalesUnitAuthorityV2.PROVEN_EQUIVALENT
        )
        assert est_replay.authority_decision.tier is (
            AuthorityTier.AI_ASSISTED_COMPARABLE
        )

    def test_tampered_extraction_evidence_cannot_pass_fu4_replay(self) -> None:
        # Item 21: a genuine EXTRACTION_RESULT_V1 candidate record
        # (the complete embedded original result inside the payload)
        # is tampered at the embedded evidence (a cue field) with the
        # section digest RECOMPUTED (the self-consistent forgery) -
        # the strict decode refuses it (the round-trip document
        # identity / the embedded original's own integrity), no unit
        # is derived from it, and no replay passes.
        result, chan = _extract(f"bundle: {CLAUSE}, complete list")
        assert result.state is SalesUnitExtractionState.OBSERVED_UNAMBIGUOUS
        case = _case_with_channel(chan)
        ctx = _context()
        candidate = candidate_composition_from_extraction(result)
        target = _make_target_fu4(
            CLAUSE,
            BundleCompositionStateV2FU4.ESTABLISHED,
            None,
            _make_target_attestation(CLAUSE),
        )
        record = _fu4_record(
            case=case,
            ctx=ctx,
            channel=chan,
            target_evidence=target,
            candidate_composition=candidate,
            quantity_attestation=None,
        )
        payload, decoded, replay = _roundtrip(record)
        assert (
            replay.authority_decision.sales_unit_authority
            is SalesUnitAuthorityV2.PROVEN_EQUIVALENT
        )
        # Tamper the embedded original's cue field (beyond any
        # recomputable digest of the candidate record alone).
        tampered = copy.deepcopy(payload)
        embedded = tampered["authority"]["candidate_composition"][
            "extraction_result"
        ]
        embedded["cues"][0]["cue_text"] = "tampered cue text"
        # A self-consistent forgery recomputes the section digest.
        tampered["integrity"]["output_digest"] = _recompute_output_digest(
            tampered
        )
        with pytest.raises(SemanticDecisionCodecError):
            decode_semantic_decision_record(tampered, schema_version=1)
        # An out-of-band field tamper (no digest recomputation) is
        # refused by the section digest check itself.
        tampered = copy.deepcopy(payload)
        tampered["authority"]["candidate_composition"]["extraction_result"][
            "cues"
        ][0]["quantity"] = 99
        with pytest.raises(SemanticDecisionCodecError):
            decode_semantic_decision_record(tampered, schema_version=1)
        # Neither shape yields a replay (no unit derived from a
        # tampered embedding; the genuine record's replay stands).
        assert (
            replay.authority_decision.sales_unit_authority
            is SalesUnitAuthorityV2.PROVEN_EQUIVALENT
        )

    def test_needs_review_remains_non_pricing_eligible(self) -> None:
        # Item 22: over EVERY committed 1.2.0 case, the FU4 no-capture
        # arithmetic (the derivation of the recorded channel) never
        # yields a unit state that lifts a ceiling: the three
        # sales-unit cases derive CONTRADICTED (the form axis), every
        # remaining case's UNAVAILABLE channel derives UNPROVEN per
        # the frozen delegation - and the cap tier is never
        # pricing-eligible.
        corpus_1_2_0 = load_corpus(CORPUS_2_1_FU4_PATH)
        units = {}
        for case in corpus_1_2_0.semantic_cases:
            recorded = case.build_semantic_case()
            unit = derive_sales_unit_authority_fu4_case(
                recorded, None, None, None
            )
            units[case.case_id] = unit
        assert len(units) == 43
        for case_id in (
            "V2Q-SSD-SU-TRAY-0032",
            "V2Q-SSD-SU-MULTI-0033",
            "V2Q-GPU-SU-BUNDLE-0034",
        ):
            assert units[case_id] is SalesUnitAuthorityV2.CONTRADICTED
        for case_id, unit in units.items():
            if case_id not in (
                "V2Q-SSD-SU-TRAY-0032",
                "V2Q-SSD-SU-MULTI-0033",
                "V2Q-GPU-SU-BUNDLE-0034",
            ):
                assert unit is SalesUnitAuthorityV2.UNPROVEN, case_id
            # No case derives PROVEN (the corpus carries no
            # attested-composition evidence - the binding-only
            # re-seal adds none).
            assert unit is not SalesUnitAuthorityV2.PROVEN_EQUIVALENT
        # The cap tier is never pricing-eligible (the frozen constant
        # + its import self-check).
        assert AuthorityTier.NEEDS_REVIEW not in PRICING_ELIGIBLE_TIERS

    def test_v2_authority_qualified_remains_false(self) -> None:
        # Item 23: the qualification marker stays False in BOTH pinned
        # locations + the FU4 adapter's mirror; the live runtime stays
        # on the frozen 2.0 prompt axis; the committed 1.2.0
        # baselines record it False.
        import product_intelligence.semantic.runtime_v2 as runtime_v2

        assert V2_AUTHORITY_QUALIFIED is False
        assert runtime_v2.V2_AUTHORITY_QUALIFIED is False
        assert runtime_v2.SEMANTIC_PROMPT_VERSION_V2 == "2.0"
        assert sdv4.V2_FU4_AUTHORITY_QUALIFIED is False
        for path in sorted(BASELINE_1_2_0_REPORT_DIR.glob("*__report.json")):
            report = json.loads(path.read_text(encoding="utf-8"))
            assert (
                report["contract"]["runtime_config_identity"][
                    "v2_authority_qualified"
                ]
                is False
            )
            assert report["authority"]["v2_authority_qualified"] is False

    def test_no_live_runtime_references_the_fu4_qualification_harness(self) -> None:
        # Item 24: no live runtime module (research / semantic /
        # execution / runs / web / providers) references the FU4
        # qualification harness (the evaluation harness package, the
        # 1.2.0 corpus artifacts, or the harness seal registry) - the
        # registration is evaluation infrastructure only.
        package_root = REPO_ROOT / "product_intelligence"
        lexical_markers = (
            "semantic_v2_qualification",
            "corpus_2_1_fu4",
            "BINDING_CORPUS_VERSIONS",
            "q3b5_p5_baseline_1_2_0",
        )
        for layer in ("research", "semantic", "execution", "runs", "web", "providers"):
            root = package_root / layer
            assert root.is_dir()
            for path in sorted(root.rglob("*.py")):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            assert not alias.name.startswith(
                                "product_intelligence.evaluation"
                            ), f"{path.name} imports the evaluation harness"
                    elif (
                        isinstance(node, ast.ImportFrom)
                        and node.module
                        and not node.level
                    ):
                        assert not node.module.startswith(
                            "product_intelligence.evaluation"
                        ), f"{path.name} imports the evaluation harness"
                source = path.read_text(encoding="utf-8")
                for marker in lexical_markers:
                    assert marker not in source, (
                        f"{path.name} references the FU4 qualification "
                        f"harness ({marker!r})"
                    )


# ===========================================================================
# T5. Historical preservation (items 25-28)
# ===========================================================================


class TestHistoricalPreservation:
    def test_frozen_fu2_fu3_replay_behavior_unchanged(self) -> None:
        # Item 25: the frozen FU2 / FU3 replay behavior is unchanged -
        # the historical V2 (2.0/FU2) record decodes / replays /
        # re-encodes byte-identically through the universal entry
        # points, and the 2.1/FU3 binding is still codec / replay-
        # refused (harness-only - the R2 change is additive).
        from tests.research.test_semantic_decision_v2 import _build_record

        from product_intelligence.research import (
            V2Confidence,
            V2SemanticDecision,
        )
        from product_intelligence.research.semantic_decision_codec import (
            decode_semantic_decision_record,
            encode_semantic_decision_record,
        )

        record = _build_record(
            decision=V2SemanticDecision.MATCH, confidence=V2Confidence.HIGH
        )
        payload = encode_semantic_decision_record(record)
        decoded = decode_semantic_decision_record(payload, schema_version=1)
        assert decoded == record
        assert encode_semantic_decision_record(decoded) == payload
        replay_semantic_decision(decoded)
        # The 2.1/FU3 harness-only binding is still refused at the
        # codec's claim gate (zero claims) - unchanged by R2.
        forged = copy.deepcopy(payload)
        forged["contract"]["authority_contract_version"] = (
            fu3.AUTHORITY_CONTRACT_VERSION_V2_FU3
        )
        forged["contract"]["prompt_version"] = "2.1"
        with pytest.raises(SemanticDecisionCodecError, match="no registered"):
            decode_semantic_decision_record(forged, schema_version=1)

    def test_historical_qualification_reports_remain_interpretable(
        self, corpus_1_0_0, corpus_1_1_0
    ) -> None:
        # Item 27 (with T3): the committed historical baselines carry
        # their original contract identity (the 2.0 / 2.1-FU3 binding
        # + the REAL system-prompt digests) and verify against their
        # corpora - the R2 extension changes no historical report
        # semantics.
        for report_dir, expected_binding, expected_digest in (
            (
                BASELINE_REPORT_DIR,
                ("V2", "2.0", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU2"),
                "c0cc98bdd6d357e81d4692218f18d354351fc2833267b3062b7cd74b18445a84",
            ),
            (
                BASELINE_2_1_REPORT_DIR,
                ("V2", "2.1", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU3"),
                "e2949e7544d26228ac6f5555ae8ebd28019076e1de88ace25e79a5d942d818fc",
            ),
        ):
            for path in sorted(report_dir.glob("*__report.json")):
                report = json.loads(path.read_text(encoding="utf-8"))
                assert tuple(report["contract"]["semantic_contract_binding"]) == (
                    expected_binding
                )
                assert report["contract"]["system_prompt_digest"] == (
                    expected_digest
                )
                assert report["authority"]["granted"] is False
            if report_dir == BASELINE_REPORT_DIR:
                verify_report(
                    json.loads(
                        sorted(report_dir.glob("*__report.json"))[0]
                        .read_text(encoding="utf-8")
                    ),
                    corpus_1_0_0,
                )
            else:
                verify_report(
                    json.loads(
                        sorted(report_dir.glob("*__report.json"))[0]
                        .read_text(encoding="utf-8")
                    ),
                    corpus_1_1_0,
                )

    def test_the_eight_gate_names_and_semantics_unchanged(self) -> None:
        # Item 28: the eight mandatory hard safety gates keep their
        # exact names / order, pass over the 1.2.0 no-capture state,
        # and the 2.0-context gate detail stays byte-identical to the
        # committed historical baseline (the R2 delta is the one
        # recorded third-binding detail branch).
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
        corpus_1_2_0 = load_corpus(CORPUS_2_1_FU4_PATH)
        gates = evaluate_safety_gates(
            evaluate_no_capture(corpus_1_2_0, *primary_route())
        )
        assert set(gates) == set(HARD_SAFETY_GATES)
        assert all(g.passed for g in gates.values())
        assert gates["zero_contract_version_mismatch"].detail == (
            "corpus binds to the exact 2.1 production contract "
            f"(prompt {SEMANTIC_PROMPT_VERSION_V2_1}, "
            f"authority {AUTHORITY_CONTRACT_VERSION_V2_FU4})"
        )
        # The 2.0 context gate output is byte-identical to the
        # committed historical baseline (the R2 change adds a branch,
        # it moves nothing).
        corpus_1_0_0 = load_corpus(CORPUS_PATH)
        gates_2_0 = evaluate_safety_gates(
            evaluate_no_capture(corpus_1_0_0, *primary_route())
        )
        committed = json.loads(
            sorted(BASELINE_REPORT_DIR.glob("*__report.json"))[0]
            .read_text(encoding="utf-8")
        )
        for name in HARD_SAFETY_GATES:
            assert committed["safety_gates"][name] == gates_2_0[name].to_report_dict()


class TestR2EndpointModulePins:
    """The six R2-owned modules' file-content integrity (R2-FU1).

    R2's recorded claim that "the six R2-owned files' post-R2 state is
    pinned by the new R2 suite" was NOT implemented as file-content
    pins: no node in this suite - or anywhere else in the tree - read
    the six modules' bytes and compared their SHA-256 against a
    literal, so any post-R2 edit to any of the six passed the full
    7568-node suite silently. This class restores the six contracts
    the FU4 A1 frozen-module table dropped at R2, at the correct
    endpoint: the same safety property as the removed rows (any edit
    fails the suite; a change requires an explicit, recorded re-pin),
    pinned at the R2-endpoint content rather than the obsolete pre-R2
    literals. The expected digests are RECORDED literals computed from
    the committed content at the starting SHA 202a3efa - never
    derived from the files under test at run time.
    """

    @pytest.mark.parametrize(
        "relative_path,expected_digest",
        sorted(R2_ENDPOINT_MODULE_PINS.items()),
        ids=lambda v: v if isinstance(v, str) else str(v),
    )
    def test_r2_amended_module_is_content_pinned_at_the_r2_endpoint(
        self, relative_path: str, expected_digest: str
    ) -> None:
        assert _file_digest(relative_path) == expected_digest, (
            f"{relative_path} differs from its R2-endpoint content "
            f"(commit 202a3efa, digest {expected_digest}); the module "
            "was explicitly amended by R2 to register the FU4 offline "
            "binding - a further change requires an explicit, recorded "
            "re-pin"
        )
