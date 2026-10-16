"""Q3-C-C2 - FU4 Bundle authority qualification: the label-governance
suite (the C2 endpoint of record: the DRAFT population, the seal gate
closed, the independent review PENDING).

This suite is the MECHANICAL audit surface of the labels (design
sections 4.6 / 8.2 / 9.4): the matrix coverage, the population
minimums, the evidence-kind / category / vocabulary composition, the
authoring discipline (the import prohibition, the anti-derivation
scan, the fixed independence attestation, the draft state), the
challenge-log + handoff completeness, the seal-gate closure (no sealed
corpus over the unreviewed population; the loader refuses the DRAFT
state; the CLI fails closed), the review-readiness dry-run (every
non-held case loads under the family loader with a test-local reviewer
fill - a decoder fixture, NEVER a committed review claim), the held
case set (the C2-F findings, pinned exactly), the historical corpus /
module preservation, and the adversarial gate demonstrations (forged
review metadata, missing review, missing matrix rows, stale digests,
modified expected labels cannot silently pass the qualification gate).

RECORDED CAVEAT (task discipline, of record): a matching digest
authenticates the BYTES of a record, not the humanity or independence
of its authorship. The qualification gate below is mechanical; the
trust it protects (the genuine two-identity review) is the reviewer
handoff's job, and the gate never claims to verify it.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

from product_intelligence.evaluation.bundle_authority import corpus as fam  # noqa: E402
from product_intelligence.evaluation.bundle_authority import (  # noqa: E402
    cli as fam_cli,
)
from product_intelligence.evaluation.bundle_authority import (  # noqa: E402
    fixtures as fam_fixtures,
)

# The C1 suite's historical-preservation pin tables (single source of
# truth - if the C1 pins move, they move under the C1 suite's own
# governance, and this suite follows).
from tests.evaluation.bundle_authority.test_q3c_c1_corpus_integrity import (  # noqa: E402
    TestHistoricalPreservation as _C1_HISTORICAL,
)

# ---------------------------------------------------------------------------
# The C2 endpoint constants of record
# ---------------------------------------------------------------------------

FAMILY_DIR = REPO_ROOT / "evaluation" / "fu4_bundle_authority_qualification"
FIXTURES_PY = (
    REPO_ROOT
    / "product_intelligence"
    / "evaluation"
    / "bundle_authority"
    / "fixtures.py"
)
CHALLENGE_LOG = FAMILY_DIR / "challenge_log.md"
REVIEWER_HANDOFF = FAMILY_DIR / "reviewer_handoff.md"
FAMILY_README = FAMILY_DIR / "README.md"
POLICY_DRAFT = FAMILY_DIR / "policy" / "qualification_policy_draft_1.json"

AUTHOR_IDENTITY = "PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR"
AUTHOR_UTC = "2026-10-15T23:22:50Z"

#: The working-tree digest of the committed DRAFT authoring source (the
#: stale-digest / modified-label gate: ANY byte change to the draft
#: population - a label, an expected axis, a reviewer field - moves
#: this digest and fails the pin. The pin is re-recorded at the sealed
#: endpoint under the seal's own governance.)
FIXTURES_PY_WORKTREE_SHA256 = (
    "77e6610bc4a88a02fa92050ed3d655966e803ffd6f45d6b1f247efee81a0d815"
)

#: The C1 family package files are byte-frozen at the C1 endpoint
#: (the C2 phase touches NO family loader / CLI code).
C1_PACKAGE_PINS = {
    "product_intelligence/evaluation/bundle_authority/corpus.py": (
        "f4eac0fc40a76179632e8a37f46ebf0c814f897f2941d8ca2d43556c1a7d1a9b"
    ),
    "product_intelligence/evaluation/bundle_authority/cli.py": (
        "19fdb751af5a85c36ada81039b7df8ff76982d3697cf1b2ffa3a09360b851156"
    ),
    "product_intelligence/evaluation/bundle_authority/__init__.py": (
        "47dde174a8b81d415f12d95684784273f079b5ee68a7446778698fb0537e0728"
    ),
}

#: The C2 governance artifacts of record (the non-seal family
#: directory contents at the draft endpoint).
FAMILY_ARTIFACT_PINS = {
    str(POLICY_DRAFT.relative_to(REPO_ROOT)): (
        "30da9e8f9234292cbd616d3438222dc5d8ad7fc7f001126f56a70e39992b814c"
    ),
    str(CHALLENGE_LOG.relative_to(REPO_ROOT)): (
        "04c65a86bcafc760d51c0d3b0aa19b2270eb2b7adfacb3e27bc10a4fbb8f4b6e"
    ),
    str(REVIEWER_HANDOFF.relative_to(REPO_ROOT)): (
        "1dedcdb9cf320513c61d6d0c064f4bdd43c1b533972c601b4c5c06f1b9747294"
    ),
    str(FAMILY_README.relative_to(REPO_ROOT)): (
        "4b3082a1c853550a59a90bd39e829ac2e39609970e59f082444e47477b0d952d"
    ),
}

#: The design section 5 matrix minimums (48 rows).
ROW_MINIMUMS = {
    "A1": 2, "A2": 2, "A3": 1, "A4": 1, "A5": 2, "A6": 1, "A7": 2,
    "A8": 2, "A-DELE": 4,
    "B1": 2, "B2": 2, "B3": 1, "B4": 1, "B5": 3, "B6": 3, "B7": 2,
    "B8": 2, "B9": 2, "B10": 3, "B11": 1, "B12": 1, "B-DELE": 2,
    "C1": 2, "C2": 1, "C2b": 1, "C3": 2, "C4": 3, "C5": 1, "C6": 1,
    "C7": 2,
    "D1": 3, "D2": 1, "D3": 3, "D4": 2, "D5": 2, "D6": 2, "D7": 2,
    "D8": 2, "D9": 2, "D10": 2, "D11": 2, "D12": 1, "D13": 2,
    "D14": 3, "D15": 2, "D16": 3, "D17": 2, "D18": 1,
}
assert set(ROW_MINIMUMS) == set(fam.MATRIX_ROWS)
assert sum(ROW_MINIMUMS.values()) == 92, "the design minimum accounting"

#: The HELD set (the C2-F findings - challenge log section 4).
HELD_LOADER = {
    "FA4-PROV-002": "C2-F3",
    "FA4-DELE-001": "C2-F1",
    "FA4-DELE-002": "C2-F1",
    "FA4-DELE-003": "C2-F1",
    "FA4-ADV-006": "C2-F2a",
    "FA4-ADV-023": "C2-F5",
    "FA4-ADV-034": "C2-F2b",
}
HELD_EVIDENCE = {
    "FA4-UNPR-011": "C2-F6",
    "FA4-UNPR-012": "C2-F6",
    "FA4-CONTR-011": "C2-F6",
}
HELD = {**HELD_LOADER, **HELD_EVIDENCE}

#: The test-local reviewer fill (a DECODER FIXTURE for the dry-run -
#: the same discipline as the C1 suite's c1-fixture-author / c1-
#: fixture-reviewer identities. It is NEVER a claim that an
#: independent review occurred; the committed population carries
#: null reviewer fields.)
DRYRUN_REVIEWER = "c2-dryrun-reviewer"
DRYRUN_REVIEWER_UTC = "2026-10-16T00:00:00Z"
DRYRUN_CREATED_UTC = "2026-10-16T00:00:00Z"

FORBIDDEN_AUTHORING_MODULES = frozenset(
    {
        "product_intelligence.research.semantic_authority_fu4",
        "product_intelligence.research.semantic_decision_v2_fu4",
        "product_intelligence.research.semantic_authority_v2",
        "product_intelligence.research.semantic_authority_fu3",
    }
)

CASES = fam_fixtures.CASES


def _sha256_file(rel: str) -> str:
    return hashlib.sha256((REPO_ROOT / rel).read_bytes()).hexdigest()


def _filled(case: dict) -> dict:
    """The dry-run reviewer fill (test-local; a decoder fixture)."""
    doc = copy.deepcopy(case)
    doc["label"]["reviewer"] = DRYRUN_REVIEWER
    doc["label"]["reviewer_utc"] = DRYRUN_REVIEWER_UTC
    doc["label"]["review_status"] = "REVIEWED"
    return doc


def _stage_case(case: dict, tmp: Path) -> None:
    """Stage every cited archive at its relative path under the temp
    repo root (the real committed bytes)."""
    for side in ("candidate", "target"):
        block = case["source"][side]
        if block["archive"] is not None:
            dest = tmp / block["archive"]
            if not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(REPO_ROOT / block["archive"], dest)


def _load_single(case: dict, tmp: Path) -> None:
    _stage_case(case, tmp)
    document = fam_fixtures.build_corpus_document(DRYRUN_CREATED_UTC, (case,))
    base = tmp / "evaluation" / "fu4_bundle_authority_qualification"
    base.mkdir(parents=True, exist_ok=True)
    corpus_file = base / "corpus_v1.json"
    corpus_file.write_bytes(fam_fixtures.corpus_bytes(document))
    manifest_file = base / "manifest_v1.json"
    manifest_file.write_bytes(
        fam.canonically_serialize(fam.build_manifest_document(document))
    )
    fam.load_bundle(corpus_file, manifest_file)


def _changelog_text() -> str:
    return CHALLENGE_LOG.read_text(encoding="utf-8")


def _handoff_text() -> str:
    return REVIEWER_HANDOFF.read_text(encoding="utf-8")


def qualification_ready_gate(
    filled_cases: list[dict],
    *,
    reviewer_registry: frozenset[str],
    changelog_review_records: dict[str, str],
) -> tuple[bool, str]:
    """The C2 qualification gate (the mechanical half of the seal).

    A population is QUALIFICATION-READY iff: (1) the family loader
    accepts it (the REVIEWED two-identity label state, every document
    coherent); (2) every case's reviewer identity is in the RECORDED
    reviewer registry (the identities the review section of the
    challenge log records as having genuinely reviewed - at this
    endpoint the registry is EMPTY); (3) every case has a review
    record in the challenge log under that reviewer's identity; (4)
    the full design matrix is instantiated at its minimums over the
    sealed population.

    RECORDED LIMIT: the gate is mechanical. It catches forgeries of
    the RECORD (a reviewer identity without a recorded review, a
    missing row, a stale digest, a modified label) - it does NOT
    verify that a human / distinct agent actually performed the
    re-derivation. That is the review's own trust, never the
    digest's.
    """
    # (2) + (3) first - the cheap mechanical identity checks.
    for case in filled_cases:
        cid = case["case_id"]
        reviewer = case["label"].get("reviewer")
        if reviewer not in reviewer_registry:
            return False, (
                f"case {cid}: reviewer {reviewer!r} is not in the "
                "recorded reviewer registry (no recorded review)"
            )
        if cid not in changelog_review_records:
            return False, (
                f"case {cid}: no review record in the challenge log "
                f"under reviewer {reviewer!r}"
            )
        if changelog_review_records[cid] != reviewer:
            return False, (
                f"case {cid}: the challenge log review record is under "
                "a different identity than the label's reviewer"
            )
    # (4) the matrix coverage over the sealed population.
    from collections import Counter

    rows = Counter(c["matrix_row"] for c in filled_cases)
    for row, minimum in sorted(ROW_MINIMUMS.items()):
        if rows.get(row, 0) < minimum:
            return False, (
                f"matrix row {row}: {rows.get(row, 0)} < {minimum} "
                "in the sealed population"
            )
    # (1) the loader.
    document = fam_fixtures.build_corpus_document(
        DRYRUN_CREATED_UTC, tuple(filled_cases)
    )
    try:
        fam.verify_corpus_document(document)
    except fam.BundleAuthorityCorpusError as exc:
        return False, f"the family loader refused the population: {exc}"
    return True, "qualification-ready"


# ---------------------------------------------------------------------------
# Matrix coverage + population composition (the design section 5 / 5.6
# floors over the declared DRAFT population)
# ---------------------------------------------------------------------------


class TestMatrixCoverage:
    def test_all_48_rows_instantiated_at_their_minimums(self):
        from collections import Counter

        rows = Counter(c["matrix_row"] for c in CASES)
        assert set(rows) == set(fam.MATRIX_ROWS), (
            f"rows missing: {sorted(set(fam.MATRIX_ROWS) - set(rows))}; "
            f"unknown rows: {sorted(set(rows) - set(fam.MATRIX_ROWS))}"
        )
        short = {
            r: (rows[r], n) for r, n in ROW_MINIMUMS.items() if rows[r] < n
        }
        assert not short, f"rows below their design minimums: {short}"

    @pytest.mark.parametrize(
        "row, minimum", sorted(ROW_MINIMUMS.items()), ids=lambda r: r
    )
    def test_row_minimum(self, row, minimum):
        from collections import Counter

        rows = Counter(c["matrix_row"] for c in CASES)
        assert rows[row] >= minimum

    def test_track_a_population_meets_the_92_minimum(self):
        track_a = [c for c in CASES if c["track"] in ("A", "A_B")]
        assert len(track_a) >= 92, f"Track A population {len(track_a)} < 92"

    def test_track_b_population_meets_the_21_minimum_with_18_shared(self):
        track_b = [c for c in CASES if c["track"] in ("B", "A_B")]
        shared = [c for c in CASES if c["track"] == "A_B"]
        b_only = [c for c in CASES if c["track"] == "B"]
        assert len(track_b) >= 21, f"Track B population {len(track_b)} < 21"
        assert len(shared) >= 18, f"A_B shared {len(shared)} < 18"
        assert len(b_only) >= 3, f"B-only controls {len(b_only)} < 3"

    def test_b_only_cases_carry_no_track_a_surface(self):
        for c in CASES:
            if c["track"] == "B":
                assert c["surface"] is None

    def test_evidence_kind_composition(self):
        from collections import Counter

        kinds = Counter(c["evidence_kind"] for c in CASES)
        total = len(CASES)
        assert kinds["SYNTHETIC"] / total >= 0.80, (
            f"SYNTHETIC share {kinds['SYNTHETIC']}/{total} < 80%"
        )
        assert kinds["RECORDED_FIXTURE"] >= 5
        assert kinds.get("REAL_MARKET", 0) == 0, (
            "v1.0.0 carries ZERO REAL_MARKET cases (C3's gated "
            "acquisition)"
        )

    def test_product_category_diversity(self):
        from collections import Counter

        cats = Counter(c["case_category"] for c in CASES)
        assert len(cats) >= 4, f"only {len(cats)} product categories"

    def test_bounded_vocabulary_projection(self):
        """Every bounded member the contract admits for a bundle
        comparison appears in >= 1 case (design section 5.6 floor)."""
        states, axes, stages = set(), set(), set()
        bases, att_states = set(), set()
        for c in CASES:
            e = c["expected"]
            for k in ("candidate_composition_state", "target_composition_state"):
                if e[k]:
                    states.add(e[k])
            if e["quantity_axis"]:
                axes.add(e["quantity_axis"])
            if e["refusal"]:
                stages.add(e["refusal"]["stage"])
            bases.add(c["derivation_inputs"]["candidate_basis"])
            for side in ("candidate", "target"):
                att_states.add(
                    (side, c["completeness_attestation_source"][side]["state"])
                )
        assert states == {
            "ESTABLISHED", "SYNTACTICALLY_VALID", "PARTIAL", "ABSENT",
            "CONTRADICTED_PUBLISHED",
        }, f"composition-state projection incomplete: {sorted(states)}"
        assert axes == {
            "CONSISTENT", "BOTH_UNPUBLISHED", "ATTESTED_NOT_MATERIAL",
            "CONTRADICTED", "UNDETERMINED",
        }, f"quantity-axis projection incomplete: {sorted(axes)}"
        assert stages == {
            "CONSTRUCTION", "CODEC_DECODE", "PRESENTATION_GATE",
            "REPLAY_AGREEMENT", "CORPUS_INTEGRITY",
        }, f"refusal-stage projection incomplete: {sorted(stages)}"
        assert {"RECORDED_CHANNEL", "EXTRACTION_RESULT_V1", "NONE"} <= bases
        assert ("candidate", "PUBLISHED_STATEMENT") in att_states
        assert ("candidate", "ABSENT") in att_states
        assert ("target", "PUBLISHED_STATEMENT") in att_states
        assert ("target", "REVIEWED_DETERMINATION") in att_states
        assert ("target", "ABSENT") in att_states

    def test_gate_denominator_tags_present(self):
        from collections import Counter

        tagged = Counter(tag for c in CASES for tag in c["challenge_tags"])
        for tag in (
            "cross_listing_substitution",  # M9
            "attestation_missing",  # M10
            "historical_binding_confusion",  # M13
            "semantic_match_unproven_bundle",  # I-1 rows
            "forged_attestation",  # the D1 / C7 / D5 family
        ):
            assert tagged[tag] >= 1, f"no case carries {tag!r}"
        assert set(tagged) <= set(fam.CHALLENGE_TAGS)


# ---------------------------------------------------------------------------
# The draft state + the closed seal gate
# ---------------------------------------------------------------------------


class TestDraftStateAndSealGate:
    def test_every_label_is_the_explicit_draft_state(self):
        for c in CASES:
            lab = c["label"]
            assert lab["review_status"] == "DRAFT", c["case_id"]
            assert lab["reviewer"] is None, (
                f"{c['case_id']}: a reviewer identity exists in the "
                "DRAFT population (no fabricated review)"
            )
            assert lab["reviewer_utc"] is None, c["case_id"]
            assert lab["author"] == AUTHOR_IDENTITY, c["case_id"]
            assert lab["author_utc"] == AUTHOR_UTC, c["case_id"]

    def test_no_seal_artifact_is_committed(self):
        assert not (FAMILY_DIR / "corpus_v1.json").exists(), (
            "a sealed corpus is committed before the independent "
            "review completes (a false seal)"
        )
        assert not (FAMILY_DIR / "manifest_v1.json").exists(), (
            "a sealed manifest is committed before the independent "
            "review completes (a false seal)"
        )

    def test_family_directory_carries_exactly_the_nonseal_artifacts(self):
        expected = {
            "README.md", "challenge_log.md", "reviewer_handoff.md",
            "policy",
        }
        actual = {p.name for p in FAMILY_DIR.iterdir()}
        assert actual == expected, (
            f"family directory contents moved: {sorted(actual)}"
        )
        policy_files = {p.name for p in (FAMILY_DIR / "policy").iterdir()}
        assert policy_files == {"qualification_policy_draft_1.json"}

    def test_loader_refuses_the_draft_population(self):
        document = fam_fixtures.build_corpus_document(
            DRYRUN_CREATED_UTC, tuple(CASES)
        )
        with pytest.raises(fam.BundleAuthorityCorpusError) as exc:
            fam.verify_corpus_document(document)
        assert "review" in exc.value.reason.lower() or "DRAFT" in (
            exc.value.reason
        )

    def test_cli_corpus_build_fails_closed_over_the_draft(self, tmp_path):
        out_dir = tmp_path / "out"
        exit_code = fam_cli.main(
            [
                "corpus-build",
                "--out-dir",
                str(out_dir),
                "--created-utc",
                DRYRUN_CREATED_UTC,
            ]
        )
        assert exit_code == 1, (
            "the CLI sealed the unreviewed population (a false seal)"
        )
        assert not (out_dir / "corpus_v1.json").exists()
        assert not (out_dir / "manifest_v1.json").exists()


# ---------------------------------------------------------------------------
# The review-readiness dry-run (the seal is mechanically achievable:
# every non-held case loads under the REAL family loader with the
# two-identity review fields filled - the fill is a test-local decoder
# fixture, never a committed review claim)
# ---------------------------------------------------------------------------


class TestReviewReadiness:
    @pytest.mark.parametrize(
        "case_id",
        sorted(
            c["case_id"] for c in CASES if c["case_id"] not in HELD_LOADER
        ),
        ids=lambda cid: cid,
    )
    def test_case_loads_with_the_review_fill(self, case_id, tmp_path):
        case = next(c for c in CASES if c["case_id"] == case_id)
        _load_single(_filled(case), tmp_path)

    @pytest.mark.parametrize(
        "case_id, finding", sorted(HELD_LOADER.items()),
        ids=lambda cid: cid,
    )
    def test_held_case_fails_the_loader(self, case_id, finding, tmp_path):
        case = next(c for c in CASES if c["case_id"] == case_id)
        with pytest.raises(fam.BundleAuthorityCorpusError):
            _load_single(_filled(case), tmp_path)

    @pytest.mark.parametrize(
        "case_id", sorted(HELD_EVIDENCE), ids=lambda cid: cid
    )
    def test_held_evidence_case_loads_with_the_gap_recorded(self,
                                                             case_id,
                                                             tmp_path):
        """The C2-F6 lighter shapes load (the U0 expectation is
        re-derivable over them); they are HELD on the row's required
        recorded extraction evidence, which the family's basis-
        coherence rule cannot carry with a DERIVED outcome."""
        case = next(c for c in CASES if c["case_id"] == case_id)
        _load_single(_filled(case), tmp_path)
        assert "HELD (C2-F6)" in case["label"]["rationale"]

    def test_held_set_is_exactly_the_recorded_findings(self):
        flagged = {
            c["case_id"]: re.search(r"HELD \((C2-F\w+)\)",
                                    c["label"]["rationale"]).group(1)
            for c in CASES if "HELD (C2-F" in c["label"]["rationale"]
        }
        assert flagged == HELD, (
            f"the held rationales disagree with the recorded held "
            f"set: {flagged}"
        )


# ---------------------------------------------------------------------------
# Label governance (design section 4.6 - the mechanical half)
# ---------------------------------------------------------------------------


class TestLabelGovernance:
    def test_independence_attestation_is_the_fixed_statement(self):
        for c in CASES:
            assert c["label"]["independence_attestation"] == (
                fam.INDEPENDENCE_ATTESTATION
            ), c["case_id"]

    def test_anti_derivation_scan_over_every_label(self):
        for c in CASES:
            for field in ("grounding_citation", "rationale"):
                text = c["label"][field].lower()
                hits = [t for t in fam.FORBIDDEN_LABEL_TOKENS if t in text]
                assert not hits, (
                    f"{c['case_id']}.label.{field} names {hits}; the "
                    "expected outcome must be independent of any model "
                    "or implementation output"
                )

    def test_grounding_citations_name_approved_sources(self):
        approved = re.compile(
            r"P3|Q3-B4|Q3-C-D1|R1|P5|Revision record|P4-FU|S2-A|O-\d",
            re.I,
        )
        for c in CASES:
            assert approved.search(c["label"]["grounding_citation"]), (
                f"{c['case_id']}: the grounding citation names no "
                "approved design source"
            )

    def test_labeling_provenance_is_bounded_and_row_coherent(self):
        for c in CASES:
            assert c["label"]["labeling_provenance"] in (
                fam.LABELING_PROVENANCE_VALUES
            ), c["case_id"]
        for c in CASES:
            if c["matrix_row"].startswith("D") and c["expected"][
                "outcome"
            ] in ("REFUSED", "NON_CONSTRUCTIBLE"):
                assert c["label"]["labeling_provenance"] == (
                    "ADVERSARIAL_CONSTRUCTION"
                ), (
                    f"{c['case_id']}: the adversarial REFUSED / "
                    f"NON_CONSTRUCTIBLE rows are ADVERSARIAL_CONSTRUCTI"
                    f"ON (the recorded defect shape), got "
                    f"{c['label']['labeling_provenance']}"
                )

    def test_author_and_reviewer_distinctness_gate(self, tmp_path):
        """A forged self-review (reviewer == author) must be refused
        by the loader even with a REVIEWED flip."""
        case = next(c for c in CASES if c["case_id"] == "FA4-PROV-001")
        forged = _filled(case)
        forged["label"]["reviewer"] = forged["label"]["author"]
        with pytest.raises(fam.BundleAuthorityLabelError) as exc:
            _load_single(forged, tmp_path)
        assert "distinct" in exc.value.reason

    def test_missing_review_is_refused_by_the_loader(self, tmp_path):
        """The DRAFT state (no review) is refused - a self-reviewed
        corpus is not a qualification corpus."""
        case = next(c for c in CASES if c["case_id"] == "FA4-PROV-001")
        with pytest.raises(fam.BundleAuthorityCorpusError):
            _load_single(case, tmp_path)  # the DRAFT case, unmodified

    def test_a_b_cases_carry_the_semantic_identity_note(self):
        for c in CASES:
            if c["track"] == "A_B":
                assert c["expected"]["semantic_identity_note"], c["case_id"]
            elif c["track"] == "A":
                assert c["expected"]["semantic_identity_note"] is None, (
                    c["case_id"]
                )


# ---------------------------------------------------------------------------
# The challenge log + the reviewer handoff (the audit surface)
# ---------------------------------------------------------------------------


class TestChallengeLogAndHandoff:
    def test_changelog_exists_and_records_every_case(self):
        text = _changelog_text()
        for c in CASES:
            assert c["case_id"] in text, (
                f"{c['case_id']} is missing from the challenge log"
            )

    def test_changelog_records_the_held_findings(self):
        text = _changelog_text()
        for finding in ("C2-F1", "C2-F2a", "C2-F2b", "C2-F3", "C2-F5",
                        "C2-F6"):
            assert finding in text
        for cid in HELD:
            assert cid in text

    def test_changelog_reviewer_column_is_pending(self):
        """No reviewer identity is recorded anywhere in the log's
        per-case table - the review has not occurred."""
        text = _changelog_text()
        table_rows = [
            line for line in text.splitlines()
            if line.startswith("| FA4-")
        ]
        assert len(table_rows) == len(CASES)
        for line in table_rows:
            cells = [c.strip() for c in line.split("|")]
            # the reviewer column is the 7th cell (index 7 with the
            # leading empty cell)
            assert cells[7] == "PENDING", (
                f"a reviewer identity is recorded in the challenge log "
                f"table: {line[:80]}..."
            )

    def test_handoff_exists_and_lists_every_case(self):
        text = _handoff_text()
        for c in CASES:
            assert c["case_id"] in text, (
                f"{c['case_id']} is missing from the reviewer handoff"
            )

    def test_handoff_records_the_seal_procedure_and_the_gate_status(self):
        text = re.sub(r"\s+", " ", _handoff_text())
        low = text.lower()
        assert "seal procedure" in low
        assert "not independently reviewed" in low or (
            "has not occurred" in low
        )
        assert "20%" in text  # the tester minimum
        assert "ALL" in text

    def test_handoff_tester_scope_includes_all_d_rows(self):
        text = _handoff_text()
        d_ids = [
            c["case_id"] for c in CASES if c["matrix_row"].startswith("D")
        ]
        assert len(d_ids) == 37
        missing = [cid for cid in d_ids if cid not in text]
        assert not missing, f"D rows missing from the tester scope: {missing}"


# ---------------------------------------------------------------------------
# Case + corpus integrity (the stale-digest / modified-label gates)
# ---------------------------------------------------------------------------


class TestIntegrity:
    def test_fixtures_source_digest_pin(self):
        """The committed DRAFT authoring source is byte-pinned: a
        modified expected label, a forged reviewer field, or a stale
        case digest moves the file's digest and fails this pin."""
        actual = _sha256_file(
            str(FIXTURES_PY.relative_to(REPO_ROOT))
        )
        assert actual == FIXTURES_PY_WORKTREE_SHA256, (
            f"fixtures.py moved (working-tree digest {actual}); the "
            "DRAFT population is sealed-by-digest at this endpoint - "
            "any label / expected-axis / review-field change requires "
            "the re-recorded pin under the label-governance rule"
        )

    def test_modified_expected_label_moves_the_case_digest(self):
        case = copy.deepcopy(
            next(c for c in CASES if c["case_id"] == "FA4-PROV-001")
        )
        original = fam.case_state_digest(case)
        case["expected"]["unit"] = "UNPROVEN"
        assert fam.case_state_digest(case) != original, (
            "a modified expected label does not move the case digest "
            "(the stale-digest gate is broken)"
        )

    def test_tampered_sealed_case_fails_the_loader(self, tmp_path):
        case = _filled(
            next(c for c in CASES if c["case_id"] == "FA4-PROV-001")
        )
        _stage_case(case, tmp_path)
        document = fam_fixtures.build_corpus_document(
            DRYRUN_CREATED_UTC, (case,)
        )
        sealed = fam_fixtures.corpus_bytes(document)
        # tamper INSIDE the sealed bytes (no digest recomputation)
        tampered = json.loads(sealed.decode("ascii"))
        tampered["cases"][0]["expected"]["textual_relation"] = (
            "T-DIFF-MATERIAL"
        )
        base = tmp_path / "evaluation" / "fu4_bundle_authority_qualification"
        base.mkdir(parents=True, exist_ok=True)
        corpus_file = base / "corpus_v1.json"
        corpus_file.write_bytes(fam.canonically_serialize(tampered))
        with pytest.raises(fam.BundleAuthorityDigestError) as exc:
            fam.load_corpus(corpus_file)
        assert "case_digest does not verify" in exc.value.reason

    def test_corpus_build_is_byte_stable(self):
        """The draft population serializes deterministically (the
        byte-for-byte regeneration property at the draft level - the
        seal's regeneration target)."""
        a = fam_fixtures.corpus_document_bytes(DRYRUN_CREATED_UTC)
        b = fam_fixtures.corpus_document_bytes(DRYRUN_CREATED_UTC)
        assert a == b
        document = json.loads(a.decode("ascii"))
        assert document["corpus_digest"] == fam.corpus_state_digest(document)
        for case_doc in document["cases"]:
            state = {
                k: v for k, v in case_doc.items() if k != "case_digest"
            }
            assert case_doc["case_digest"] == fam.case_state_digest(state)

    def test_missing_matrix_row_cannot_pass_the_gate(self):
        """Adversarial: a population missing a required row fails the
        coverage half of the gate (even with a full forged review)."""
        dropped = [c for c in CASES if c["matrix_row"] != "D14"]
        forged = [_filled(c) for c in dropped]
        registry = frozenset({DRYRUN_REVIEWER})
        records = {c["case_id"]: DRYRUN_REVIEWER for c in forged}
        ok, reason = qualification_ready_gate(
            forged, reviewer_registry=registry,
            changelog_review_records=records,
        )
        assert not ok
        assert "D14" in reason

    def test_forged_review_metadata_cannot_pass_the_gate(self):
        """Adversarial: a forged REVIEWED flip with an invented
        reviewer identity passes the LOADER (the mechanical truth -
        the digest does not authenticate a human review) but fails the
        qualification gate (the reviewer is not in the recorded
        registry; there is no review record)."""
        case = _filled(
            next(c for c in CASES if c["case_id"] == "FA4-PROV-001")
        )
        # the loader accepts the forged two-identity state (recorded
        # mechanical truth)
        with tempfile.TemporaryDirectory() as td:
            _load_single(case, Path(td))
        # but the gate refuses it: no recorded review exists
        ok, reason = qualification_ready_gate(
            [case], reviewer_registry=frozenset(),
            changelog_review_records={},
        )
        assert not ok
        assert "not in the recorded reviewer registry" in reason
        # and with a registry that does not name the forger
        ok2, reason2 = qualification_ready_gate(
            [case], reviewer_registry=frozenset({"someone-else"}),
            changelog_review_records={"FA4-PROV-001": "someone-else"},
        )
        assert not ok2
        assert reason2.startswith("case FA4-PROV-001")


# ---------------------------------------------------------------------------
# The authoring import prohibition (design section 4.6 item 2(a))
# ---------------------------------------------------------------------------


class TestImportProhibition:
    def _imported_modules(self, path: Path) -> set[str]:
        modules: set[str] = set()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    modules.add(node.module)
        return modules

    def test_fixtures_imports_no_research_module(self):
        modules = self._imported_modules(FIXTURES_PY)
        research = {
            m for m in modules if m.startswith("product_intelligence.research")
        }
        assert not research, (
            f"fixtures.py imports the research surface (the section "
            f"4.6(a) prohibition): {sorted(research)}"
        )

    def test_fixtures_import_set_is_exactly_the_allowlist(self):
        modules = self._imported_modules(FIXTURES_PY)
        external = {
            m for m in modules
            if m and not m.startswith("product_intelligence.evaluation.bundle_authority")
            and m not in ("__future__", "typing")
        }
        assert not external, (
            f"fixtures.py imports outside the family + stdlib "
            f"allowlist: {sorted(external)}"
        )

    def test_no_forbidden_module_name_in_fixtures_source(self):
        src = FIXTURES_PY.read_text(encoding="utf-8")
        for mod in FORBIDDEN_AUTHORING_MODULES:
            short = mod.rsplit(".", 1)[-1]
            assert short not in src, (
                f"fixtures.py names the forbidden module {short!r} "
                "(the label-determining derivations)"
            )

    def test_family_package_has_no_evaluator_surface(self):
        """The seal precedes the evaluator (section 4.6 item 2(c)):
        at the C2 endpoint no evaluator / gates / report / policy-
        loader module exists in the family package."""
        pkg = REPO_ROOT / "product_intelligence" / "evaluation" / "bundle_authority"
        names = {p.name for p in pkg.iterdir() if p.name.endswith(".py")}
        assert names == {"__init__.py", "corpus.py", "fixtures.py",
                         "cli.py"}, (
            f"the family package surface moved: {sorted(names)}"
        )


# ---------------------------------------------------------------------------
# Historical corpus + module preservation
# ---------------------------------------------------------------------------


class TestHistoricalPreservation:
    @pytest.mark.parametrize(
        "rel", sorted(_C1_HISTORICAL.SEMANTIC_ARTIFACT_FILE_PINS),
        ids=lambda r: r.rsplit("/", 1)[-1],
    )
    def test_semantic_family_artifact_is_byte_identical(self, rel):
        assert _sha256_file(rel) == (
            _C1_HISTORICAL.SEMANTIC_ARTIFACT_FILE_PINS[rel]
        ), f"{rel} moved; the family leaves the semantic corpus " \
          "byte-identical"

    @pytest.mark.parametrize(
        "rel", sorted(_C1_HISTORICAL.SEMANTIC_1_2_0_INNER_DIGESTS),
        ids=lambda r: r.rsplit("/", 1)[-1],
    )
    def test_semantic_1_2_0_seal_stands(self, rel):
        document = json.loads((REPO_ROOT / rel).read_text(encoding="utf-8"))
        field, expected = _C1_HISTORICAL.SEMANTIC_1_2_0_INNER_DIGESTS[rel]
        assert document[field] == expected

    @pytest.mark.parametrize(
        "rel", sorted(C1_PACKAGE_PINS), ids=lambda r: r.rsplit("/", 1)[-1]
    )
    def test_c1_family_package_is_byte_frozen(self, rel):
        assert _sha256_file(rel) == C1_PACKAGE_PINS[rel], (
            f"{rel} moved; the C2 phase touches NO family loader / "
            "CLI code (the validator is the C1 endpoint of record)"
        )

    def test_c0_pinned_implementation_modules_stand(self):
        """The C0 content pins (the qualified surface's identity) are
        re-asserted at the C2 endpoint (single source of truth: the
        C0 pin table - the bounded CRLF->LF normalization policy +
        the committed size / SHA-256 literals)."""
        from tests.research import test_q3c_c0_fu4_implementation_pins as c0

        for module in c0.PINNED_MODULES:
            raw = (REPO_ROOT / module["path"]).read_bytes()
            content = raw.replace(b"\r\n", b"\n")
            assert len(content) == module["committed_size"], (
                f"{module['path']} moved (the C0 content pin)"
            )
            assert hashlib.sha256(content).hexdigest() == (
                module["committed_sha256"]
            ), f"{module['path']} moved (the C0 content pin)"

    def test_family_governance_artifacts_are_byte_pinned(self):
        for rel, expected in sorted(FAMILY_ARTIFACT_PINS.items()):
            assert _sha256_file(rel) == expected, (
                f"{rel} moved; the C2 governance record is sealed-by-"
                "digest at this endpoint"
            )


# ---------------------------------------------------------------------------
# The DRAFT-only policy state (design section 7.1 / 7.2)
# ---------------------------------------------------------------------------


class TestPolicyDraft:
    @pytest.fixture(scope="class")
    def policy(self):
        return json.loads(POLICY_DRAFT.read_text(encoding="utf-8"))

    def test_policy_is_draft_only(self, policy):
        assert policy["status"] == "DRAFT"
        assert policy["approval"]["approved"] is False
        assert policy["approval"]["approved_by"] is None
        assert policy["approval"]["approved_utc"] is None

    def test_policy_applies_to_the_family_corpus_identity(self, policy):
        assert policy["applicability"] == {
            "corpus_id": fam.CORPUS_ID,
            "corpus_version": fam.FIRST_CORPUS_VERSION,
        }

    def test_policy_carrying_the_design_7_2_threshold_vocabulary(self,
                                                                 policy):
        track_a = {
            "false_proven_count_max", "false_contradicted_rate_max",
            "unproven_abstention_min", "integrity_rejection_min",
            "replay_agreement_min", "substitution_rejection_min",
            "missing_attestation_fail_closed_min",
            "quantity_conflict_detection_min",
            "pricing_leakage_count_max",
            "historical_confusion_rejection_min",
            "model_independence_invariance_min", "tier_axis_min",
            "axis_audit_min", "integrity_stage_accuracy_min",
        }
        track_b = {
            "hallucination_rate_max", "constituent_precision_min",
            "constituent_recall_min", "attestation_grounding_min",
            "ambiguous_abstention_min", "valid_schema_min",
            "coverage_min",
        }
        assert set(policy["thresholds"]["track_a"]) == track_a
        assert set(policy["thresholds"]["track_b"]) == track_b
        # the zero-tolerance invariants of the draft vocabulary
        assert policy["thresholds"]["track_a"]["false_proven_count_max"] == 0
        assert (
            policy["thresholds"]["track_a"]["pricing_leakage_count_max"]
            == 0
        )
        assert (
            policy["thresholds"]["track_b"]["hallucination_rate_max"] == 0.0
        )

    def test_semantic_family_policy_is_unchanged(self):
        """The existing semantic-family DRAFT policy (corpus 1.0.0-
        scoped) is UNCHANGED, UNCOPIED, UNEXTENDED (the F-4 lineage)."""
        rel = (
            "evaluation/semantic_v2_qualification/policy/"
            "qualification_policy_draft_1.json"
        )
        assert _sha256_file(rel) == (
            _C1_HISTORICAL.SEMANTIC_ARTIFACT_FILE_PINS[rel]
        )
