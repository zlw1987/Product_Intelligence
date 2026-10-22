"""Q3-C-C2 - FU4 Bundle authority qualification: the label-governance
suite (the C2 endpoint of record, CORRECTED at the Q3-C-C1-FU3 + C2
corrective implementation: the 94-case DRAFT population of record, the
seal gate closed, the independent review PENDING).

This suite is the MECHANICAL audit surface of the labels (design
sections 4.6 / 8.2 / 9.4): the matrix coverage over the CORRECTED
(Q3-C-D1-FU1) row minimums (90 over the 48 rows), the population
minimums, the evidence-kind / category / vocabulary composition (the
section 5.6 floors over the 94-case corrected population), the
authoring discipline (the import prohibition, the anti-derivation
scan, the fixed independence attestation, the draft state), the
challenge-log + handoff completeness (the adjudication record), the
seal-gate closure (no sealed corpus over the unreviewed population;
the loader refuses the DRAFT state; the CLI fails closed), the review-
readiness dry-run (every corrected-population case loads under the
family loader with a test-local reviewer fill - a decoder fixture,
NEVER a committed review claim), the ADJUDICATED held-set state (the
W3 monotonic rule: the C2 endpoint's ten HELD cases are resolved -
the five released cases verified case-by-case over the exact
corrected behavior, the two removed cases pinned absent with their
recorded obligation destinations, the three C2-F6 cases carrying the
genuine recorded extraction results), the historical corpus / module
preservation (the C1-FU3 re-pins of record), and the adversarial gate
demonstrations (forged review metadata, missing review with the
PINNED W4 reason, missing matrix row, below-floor populations - the
W2 composition floors enforced over the actual seal population, stale
digests, modified expected labels cannot silently pass the
qualification gate).

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
#: this digest and fails the pin. RE-PIN of record (Q3-C-C2-R1-FU1
#: pre-seal label and provenance corrections - the pin's own stated
#: contract: a pin move is a recorded re-pin event, never a silent
#: one): the three corrected rows of record (CH-1 FA4-ADV-024
#: expected.tier -> HARD_CONFLICT; CH-2 FA4-UNPR-022 expected.
#: textual_relation -> T-DIFF-MATERIAL; F-R1 FA4-DELE-005 the
#: archive-recorded source URL at the three sealed locations) +
#: their label annotations, over the corrected 94-case DRAFT
#: population (the C1-FU3 + C2 corrected state of record otherwise
#: byte-unchanged). RE-PIN of record (Q3-C-C1-FU4 + C2-FU2 F-R6 /
#: F-R2 corrective implementation - the pin's own stated contract):
#: d1120de7d995e331a8b3cd4da0f4b071f5d5bacf94daf4f8d85aceffcf094dd5
#: -> 0cb7dfb1e9918d5c29fa51b0a189bdd2baf02cb0c500ba7981ce103ae00059d2 -
#: the two corrected rows of record (F-R6 FA4-ADV-012
#: expected.refusal.stage CONSTRUCTION -> CORPUS_INTEGRITY +
#: expected.refusal.error_type CONSTRUCTOR -> null, the Q3-C-D1-FU3
#: adjudication + its label annotations; F-R2 FA4-ADV-022 /
#: FA4-ADV-023 grounding citations + the verified Micron catalog
#: digest 160d4fe97a5df5249e8f6404f6b005c0515fab4def1b4668fdaf87c727600743
#: - a documentary annotation, no expected field moved) over the
#: otherwise byte-unchanged 94-case DRAFT population. The pin is
#: re-recorded again at the sealed endpoint under the seal's own
#: governance.
FIXTURES_PY_WORKTREE_SHA256 = (
    "0cb7dfb1e9918d5c29fa51b0a189bdd2baf02cb0c500ba7981ce103ae00059d2"
)

#: The C1 family package files are byte-frozen at the C1 endpoint
#: (the C2 phase touches NO family loader / CLI code).
#: RE-PIN of record for corpus.py (Q3-C-C1-FU3 + C2 corrective
#: implementation, design section 9.11 file (1)): the corrected
#: validator (the section 4.4 PROVEN coherence scoping, the identity-
#: context empty-part-number decode, the allowed NONE-basis recorded-
#: extraction-result state + the named CASEDOC_RECORDED_RESULT_CHANNEL_
#: MAPPING refusal, the W9 coherence-separation statement) is the C1-
#: FU3 endpoint of record - the pin's own stated contract (a pin move
#: is a recorded re-pin event, never a silent one). cli.py /
#: __init__.py are unchanged (byte-identical to the C1 / C2 pins).
#: RE-PIN of record for corpus.py (Q3-C-C1-FU4 + C2-FU2 corrective
#: implementation, design section 9.12 file (1) / (1b) - the pin's
#: own stated contract): aa09d2a58d6f71cc2a4b201155e6c859d1e34fc6552bde55e4131f95a40f157d
#: -> 7eee013bd246c81bc661eb54a4e4cd2dcb03de79232fd339474d9f9d46cbd56f
#: - the F-R6 loader observation re-classification (the D6-i
#: SOURCE_EXTRACTION_INPUT_DIGEST observation moves from the
#: CONSTRUCTOR layer to the CASE_DOCUMENT layer - the check logic +
#: the bounded reason unchanged; the existing stage-coherence rule
#: now accepts CORPUS_INTEGRITY / null and rejects the obsolete
#: CONSTRUCTION attribution over the D6-i shape) + the family-owned
#: read-only Contract B observation interface (observe_corpus_
#: case_integrity + observation_stages + the bounded record types -
#: the actual _run_family_checks() logic reused, the expected label
#: never read for behavior, no production bypass, no model / network
#: / pricing / derivation / replay invocation). cli.py /
#: __init__.py remain unchanged (byte-identical to the C1 / C2 pins).
C1_PACKAGE_PINS = {
    "product_intelligence/evaluation/bundle_authority/corpus.py": (
        "7eee013bd246c81bc661eb54a4e4cd2dcb03de79232fd339474d9f9d46cbd56f"
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
#: RE-PIN of record for the challenge log + the reviewer handoff
#: (Q3-C-C2-R1-FU1 pre-seal label and provenance corrections - the
#: pin's own stated contract): the pre-seal correction record under
#: the corrective implementer identity + correction instant (the
#: section 1 correction-of-record paragraph + the section 6 rows
#: 20 / 21 / 22 + the three per-case status cells) + the section
#: 4.1 re-verification worklist are the corrected governance state
#: of record; the CH-1 / CH-2 challenges + the F-R1 finding remain
#: OPEN for the independent reviewer's re-verification (not marked
#: resolved on the reviewer's behalf). The family README + the
#: DRAFT policy are unchanged (byte-identical to the C2 / C1-FU3
#: pins).
#: RE-PIN of record for the challenge log + the reviewer handoff
#: (Q3-C-C1-FU4 + C2-FU2 F-R6 / F-R2 corrective implementation - the
#: pin's own stated contract): the F-R6 + F-R2 correction-of-record
#: entry (the section 1 paragraph + the section 6 rows 23 / 24 + the
#: three per-case status cells - FA4-ADV-012 / FA4-ADV-022 /
#: FA4-ADV-023 flagged CORRECTED - reviewer re-verification
#: required) + the section 4.2 re-verification worklist + the
#: FA4-ADV-012 / FA4-ADV-022 [CORRECTED-VERIFY] worklist flags are
#: the corrected governance state of record; the F-R6 + F-R2
#: findings remain OPEN for the independent reviewer's re-
#: verification (not marked resolved on the reviewer's behalf);
#: F-R3 / F-R4 / F-R5 / F-R7 / F-R8 stand as recorded. The family
#: README + the DRAFT policy are unchanged (byte-identical to the
#: C2 / C1-FU3 pins).
FAMILY_ARTIFACT_PINS = {
    str(POLICY_DRAFT.relative_to(REPO_ROOT)): (
        "30da9e8f9234292cbd616d3438222dc5d8ad7fc7f001126f56a70e39992b814c"
    ),
    str(CHALLENGE_LOG.relative_to(REPO_ROOT)): (
        "52f6cc9bcf2ae111e8e5ab2d13a6c5e608a1cfd4812ab352549f2f70d491330c"
    ),
    str(REVIEWER_HANDOFF.relative_to(REPO_ROOT)): (
        "92f71e8f0358de972be4788cdd6abae64ac8eccec0cf3a6327eafe12e403636f"
    ),
    str(FAMILY_README.relative_to(REPO_ROOT)): (
        "4b3082a1c853550a59a90bd39e829ac2e39609970e59f082444e47477b0d952d"
    ),
}

#: The design section 5 matrix minimums (48 rows) - the CORRECTED
#: (Q3-C-D1-FU1) row minimums of record: A1 2 -> 1 (the recorded
#: variant deferred to C3 / the additive 1.1.0 obligation - the
#: explicit phase-boundary correction); D16 3 -> 2 (the execution-
#: level (iii) obligation preserved in the MANDATORY E1 adversarial-
#: execution assertion - the explicit phase-boundary correction);
#: the 90 Track A floor (16 (A) + 25 (B) + 13 (C) + 36 (D)).
ROW_MINIMUMS = {
    "A1": 1, "A2": 2, "A3": 1, "A4": 1, "A5": 2, "A6": 1, "A7": 2,
    "A8": 2, "A-DELE": 4,
    "B1": 2, "B2": 2, "B3": 1, "B4": 1, "B5": 3, "B6": 3, "B7": 2,
    "B8": 2, "B9": 2, "B10": 3, "B11": 1, "B12": 1, "B-DELE": 2,
    "C1": 2, "C2": 1, "C2b": 1, "C3": 2, "C4": 3, "C5": 1, "C6": 1,
    "C7": 2,
    "D1": 3, "D2": 1, "D3": 3, "D4": 2, "D5": 2, "D6": 2, "D7": 2,
    "D8": 2, "D9": 2, "D10": 2, "D11": 2, "D12": 1, "D13": 2,
    "D14": 3, "D15": 2, "D16": 2, "D17": 2, "D18": 1,
}
assert set(ROW_MINIMUMS) == set(fam.MATRIX_ROWS)
assert sum(ROW_MINIMUMS.values()) == 90, (
    "the corrected design minimum accounting (Q3-C-D1-FU1)"
)

#: The ADJUDICATED held-set state of record (the W3 monotonic held-set
#: rule, design section 8.2 item 6): the C2 endpoint's ten HELD cases
#: are resolved under the recorded Q3-C-D1-FU1 adjudication + the
#: verified C1-FU3 + C2 corrections - the held set is now EMPTY; the
#: release direction is the only one that moves population accounting,
#: and it moved under the revision's recorded destinations.
#: The five loader-held cases released IN THE POPULATION (the case IDs
#: stable - the corrected rows the reviewer verifies):
RELEASED_LOADER = {
    "FA4-DELE-001": "C2-F1",
    "FA4-DELE-002": "C2-F1",
    "FA4-DELE-003": "C2-F1",
    "FA4-ADV-006": "C2-F2a",
    "FA4-ADV-023": "C2-F5",
}
#: The two loader-held cases REMOVED from the v1.0.0 declared
#: population (case IDs retired; the obligations preserved with their
#: recorded destinations):
REMOVED_LOADER = {
    "FA4-ADV-034": "C2-F2b",  # the MANDATORY E1 adversarial-execution assertion (design section 9.6)
    "FA4-PROV-002": "C2-F3",  # the C3 / additive 1.1.0 obligation (design section 5.6)
}
#: The three C2-F6 evidence-gap cases released by the re-authoring
#: over the GENUINE recorded extraction results (the allowed NONE-
#: basis recorded-result state of design section 4.4):
RELEASED_EVIDENCE = {
    "FA4-UNPR-011": "C2-F6",
    "FA4-UNPR-012": "C2-F6",
    "FA4-CONTR-011": "C2-F6",
}
#: The full adjudicated set (all ten HELD cases of the C2 endpoint):
ADJUDICATED = {
    **RELEASED_LOADER,
    **REMOVED_LOADER,
    **RELEASED_EVIDENCE,
}
#: The corrected held set (of record): EMPTY - no case remains held
#: after the recorded adjudication + the verified corrections.
HELD: dict[str, str] = {}

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


def _frozen_p2_mapping(result_doc: dict) -> dict:
    """Re-run the FROZEN P2 mapping (a contract datum of the test)
    over a sealed extraction-result document: reconstruct the frozen
    ``SalesUnitExtractionResult`` from its sealed self-consistent
    document (the frozen constructor re-verifies the digests + cue
    spans) and return the frozen ``sales_unit_channel_from_extraction``
    mapping's canonical channel. Used only to VERIFY that a corrected
    case's presented channel is exactly the frozen mapping of its
    recorded result (design section 4.4 / C2-F6) - never as an
    expected-label source."""
    from product_intelligence.research import (
        SalesUnitCueDisposition,
        SalesUnitCueField,
        SalesUnitCueReason,
        SalesUnitCueV1,
        SalesUnitExtractionResult,
        SalesUnitExtractionState,
        SalesUnitIdentifierFieldNoteV1,
        sales_unit_channel_from_extraction,
    )
    from product_intelligence.research.semantic_v2 import (
        CandidateEvidenceSourceV2,
        SalesUnitKindV2,
    )

    def _cue(d):
        return SalesUnitCueV1(
            field=SalesUnitCueField(d["field"]),
            source=CandidateEvidenceSourceV2(d["source"]),
            raw_field_value=d["raw_field_value"],
            cue_text=d["cue_text"],
            cue_start=d["cue_start"],
            cue_end=d["cue_end"],
            kind=SalesUnitKindV2(d["kind"]) if d["kind"] else None,
            quantity=d["quantity"],
            disposition=SalesUnitCueDisposition(d["disposition"]),
            reason=SalesUnitCueReason(d["reason"]) if d["reason"] else None,
        )

    def _note(d):
        return SalesUnitIdentifierFieldNoteV1(
            field_name=d["field_name"], token_text=d["token_text"]
        )

    result = SalesUnitExtractionResult(
        result_doc["schema_version"],
        SalesUnitExtractionState(result_doc["state"]),
        tuple(_cue(c) for c in result_doc["cues"]),
        tuple(_note(n) for n in result_doc["identifier_field_notes"]),
        SalesUnitKindV2(result_doc["established_kind"])
        if result_doc["established_kind"] is not None
        else None,
        result_doc["established_quantity"],
        result_doc["input_digest"],
        result_doc["result_digest"],
    )
    return sales_unit_channel_from_extraction(result).canonical()


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
    record in the challenge log under that reviewer's identity - a
    missing review is rejected with the PINNED deterministic reason
    (the W4 adjudication of record: a gate that rejects for an un-
    pinned reason is a gate defect); (4) EVERY design section 5.6
    composition floor holds on the ACTUAL seal population (not the
    draft authoring population - the W2 adjudication of record): the
    corrected row minimums (90 over the 48 rows), the Track A / Track
    B floors (90 / 21 / 18 / 3), the evidence-kind composition
    (SYNTHETIC >= 80%, RECORDED_FIXTURE >= 5, REAL_MARKET = 0 at
    v1.0.0), the category floor (>= 4), and the bounded-vocabulary
    projection (every admitted member >= 1 time - the W6
    adjudication). A floor verified only over the draft population is
    NOT seal evidence.

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
                "under the case's reviewer identity"
            )
        if changelog_review_records[cid] != reviewer:
            return False, (
                f"case {cid}: the challenge log review record is under "
                "a different identity than the label's reviewer"
            )
    # (4) the design section 5.6 composition floors over the ACTUAL
    #     seal population (the W2 / W6 adjudications of record).
    from collections import Counter

    total = len(filled_cases)
    # the corrected row minimums (90 over the 48 rows).
    rows = Counter(c["matrix_row"] for c in filled_cases)
    for row, minimum in sorted(ROW_MINIMUMS.items()):
        if rows.get(row, 0) < minimum:
            return False, (
                f"matrix row {row}: {rows.get(row, 0)} < {minimum} "
                "in the sealed population"
            )
    # the Track A / Track B floors (90 / 21 / 18 / 3).
    track_a = sum(1 for c in filled_cases if c["track"] in ("A", "A_B"))
    if track_a < 90:
        return False, f"Track A population {track_a} < 90 in the sealed population"
    track_b = sum(1 for c in filled_cases if c["track"] in ("B", "A_B"))
    if track_b < 21:
        return False, f"Track B population {track_b} < 21 in the sealed population"
    shared = sum(1 for c in filled_cases if c["track"] == "A_B")
    if shared < 18:
        return False, f"A_B shared {shared} < 18 in the sealed population"
    b_only = sum(1 for c in filled_cases if c["track"] == "B")
    if b_only < 3:
        return False, f"B-only controls {b_only} < 3 in the sealed population"
    # the evidence-kind composition (SYNTHETIC >= 80%, RECORDED_
    # FIXTURE >= 5, REAL_MARKET = 0 at v1.0.0).
    kinds = Counter(c["evidence_kind"] for c in filled_cases)
    if kinds["SYNTHETIC"] / total < 0.80:
        return False, (
            f"SYNTHETIC share {kinds['SYNTHETIC']}/{total} < 80% in "
            "the sealed population"
        )
    if kinds["RECORDED_FIXTURE"] < 5:
        return False, (
            f"RECORDED_FIXTURE {kinds['RECORDED_FIXTURE']} < 5 in the "
            "sealed population"
        )
    if kinds.get("REAL_MARKET", 0) != 0:
        return False, (
            f"REAL_MARKET {kinds['REAL_MARKET']} != 0 in the v1.0.0 "
            "sealed population (C3's separately gated acquisition)"
        )
    # the category floor (>= 4).
    categories = {c["case_category"] for c in filled_cases}
    if len(categories) < 4:
        return False, (
            f"{len(categories)} product categories < 4 in the sealed "
            "population"
        )
    # the bounded-vocabulary projection (every admitted member >= 1
    # time - the W6 adjudication, over the ACTUAL seal population).
    states, axes, stages = set(), set(), set()
    bases, att_states = set(), set()
    for c in filled_cases:
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
    if states != {
        "ESTABLISHED", "SYNTACTICALLY_VALID", "PARTIAL", "ABSENT",
        "CONTRADICTED_PUBLISHED",
    }:
        return False, (
            f"composition-state projection incomplete in the sealed "
            f"population: {sorted(states)}"
        )
    if axes != {
        "CONSISTENT", "BOTH_UNPUBLISHED", "ATTESTED_NOT_MATERIAL",
        "CONTRADICTED", "UNDETERMINED",
    }:
        return False, (
            f"quantity-axis projection incomplete in the sealed "
            f"population: {sorted(axes)}"
        )
    if stages != {
        "CONSTRUCTION", "CODEC_DECODE", "PRESENTATION_GATE",
        "REPLAY_AGREEMENT", "CORPUS_INTEGRITY",
    }:
        return False, (
            f"refusal-stage projection incomplete in the sealed "
            f"population: {sorted(stages)}"
        )
    if not {"RECORDED_CHANNEL", "EXTRACTION_RESULT_V1", "NONE"} <= bases:
        return False, (
            f"candidate-basis projection incomplete in the sealed "
            f"population: {sorted(bases)}"
        )
    for att in (
        ("candidate", "PUBLISHED_STATEMENT"), ("candidate", "ABSENT"),
        ("target", "PUBLISHED_STATEMENT"), ("target", "REVIEWED_DETERMINATION"),
        ("target", "ABSENT"),
    ):
        if att not in att_states:
            return False, (
                f"attestation-side state {att!r} not projected in the "
                "sealed population"
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

    def test_track_a_population_meets_the_90_minimum(self):
        # Recorded in-place correction (Q3-C-C1-FU3 + C2 corrective
        # implementation): the Track A floor moves 92 -> 90 under the
        # adjudicated (Q3-C-D1-FU1) row minimums (A1 2->1; D16 3->2 -
        # the explicit phase-boundary corrections of record, each with
        # its destination). Intent preserved + strengthened: the floor
        # is the corrected 90 over the corrected population.
        track_a = [c for c in CASES if c["track"] in ("A", "A_B")]
        assert len(track_a) >= 90, f"Track A population {len(track_a)} < 90"

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
        # The corrected population of record (Q3-C-C1-FU3 + C2
        # corrective implementation): 94 cases = 88 SYNTHETIC + 6
        # RECORDED_FIXTURE + 0 REAL_MARKET (the D11-ii re-authoring
        # moves RECORDED_FIXTURE -> SYNTHETIC; the A1 recorded variant
        # is removed - C3 / 1.1.0).
        assert total == 94, f"the corrected population of record is 94 cases, got {total}"
        assert kinds["SYNTHETIC"] == 88, f"SYNTHETIC count {kinds['SYNTHETIC']} != 88"
        assert kinds["RECORDED_FIXTURE"] == 6, f"RECORDED_FIXTURE count {kinds['RECORDED_FIXTURE']} != 6"
        # the design section 5.6 floors stand over the record:
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
        # The corrected population of record carries five categories
        # (unchanged by the corrections - both removed cases were
        # workstation_gpu, and the D11-ii re-authoring stays in its
        # micron_ddr5 category).
        assert len(cats) == 5, f"the corrected population of record carries five categories, got {sorted(cats)}"
        assert set(cats) == {
            "memory_kit", "micron_ddr5", "nvme_ssd",
            "workstation_gpu", "networking_module",
        }, f"the category set of record moved: {sorted(cats)}"

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
        sorted(c["case_id"] for c in CASES),
        ids=lambda cid: cid,
    )
    def test_case_loads_with_the_review_fill(self, case_id, tmp_path):
        # The corrected review-readiness dry-run (design section 9.11
        # acceptance (1)): every one of the 94 corrected-population
        # cases loads under the REAL family loader with the two-
        # identity review fields filled (the fill is a test-local
        # decoder fixture, never a committed review claim). The C2
        # endpoint's seven loader-held cases load here for the first
        # time (the C1-FU3 corrections + the pre-seal case
        # corrections).
        case = next(c for c in CASES if c["case_id"] == case_id)
        _load_single(_filled(case), tmp_path)

    @pytest.mark.parametrize(
        "case_id, finding",
        sorted({**RELEASED_LOADER, **REMOVED_LOADER}.items()),
        ids=lambda cid: cid,
    )
    def test_released_held_case_behavior_is_pinned(self, case_id,
                                                    finding,
                                                    tmp_path):
        """The W3 monotonic held-set release, verified case-by-case
        over the EXACT corrected behavior (design section 9.11
        acceptance (2)): the seven C2 loader-held cases leave the
        held set ONLY under the recorded adjudication + the verified
        correction - the five released cases (the case IDs stable)
        load over the corrected documents; the two removed cases are
        absent from the declared population with their recorded
        obligation destinations (the challenge log section 6 rows
        18 / 19; the reviewer handoff section 4)."""
        in_population = case_id in {c["case_id"] for c in CASES}
        log = _changelog_text()
        if case_id in REMOVED_LOADER:
            assert not in_population, (
                f"{case_id}: the removed case is back in the declared "
                "population (the W3 monotonic release direction was "
                "violated)"
            )
            # the removal + the obligation destination are recorded:
            assert f"{case_id} | REMOVED" in log, (
                f"{case_id}: the recorded removal + obligation "
                "destination is missing from the challenge log"
            )
        else:
            assert in_population, (
                f"{case_id}: the released case is missing from the "
                "declared population (the case ID must stay stable)"
            )
            case = next(c for c in CASES if c["case_id"] == case_id)
            # the release is verified: the case LOADS under the
            # corrected loader (the exact corrected behavior).
            _load_single(_filled(case), tmp_path)
            # the HELD marker is gone (the release is recorded, not
            # silent):
            assert "HELD (" not in case["label"]["rationale"], (
                f"{case_id}: the released case still carries the HELD "
                "rationale marker"
            )

    @pytest.mark.parametrize(
        "case_id", sorted(RELEASED_EVIDENCE), ids=lambda cid: cid
    )
    def test_released_evidence_case_carries_the_genuine_recorded_result(
        self, case_id, tmp_path
    ):
        """The C2-F6 release verified case-by-case over the EXACT
        corrected behavior (design section 9.11 acceptance (2)): the
        three evidence-gap cases now carry the GENUINE frozen P2
        recorded extraction results over the allowed state (candidate
        composition record null, basis NONE, the presented channel
        EXACTLY the frozen P2 mapping of the recorded result) - the
        row's REQUIRED evidence is present, not a lighter shape.
        FA4-CONTR-011 additionally carries the W7 genuine
        CONTRADICTED_CUES instantiation."""
        case = next(c for c in CASES if c["case_id"] == case_id)
        _load_single(_filled(case), tmp_path)
        di = case["derivation_inputs"]
        # the allowed state (design section 4.4):
        assert di["candidate_composition"] is None
        assert di["candidate_basis"] == "NONE"
        assert di["extraction_evidence"] is not None
        result_doc = di["extraction_evidence"]["result_document"]
        assert result_doc is not None
        assert di["extraction_evidence"]["input_document"] is not None
        # the recorded result carries the row's genuine cue state:
        if case_id == "FA4-CONTR-011":
            assert result_doc["state"] == "CONTRADICTED_CUES", (
                f"{case_id}: the W7 cue-state accuracy - the recorded "
                "result must carry the genuine CONTRADICTED_CUES "
                f"state, got {result_doc['state']!r}"
            )
        else:
            assert result_doc["state"] == "AMBIGUOUS_CUE", (
                f"{case_id}: the recorded result must carry the row's "
                f"AMBIGUOUS_CUE state, got {result_doc['state']!r}"
            )
        # the presented channel is EXACTLY the frozen P2 mapping of
        # the recorded result (the frozen lossy map re-run as a
        # contract datum in this test - not an implementation
        # oracle):
        mapped = _frozen_p2_mapping(result_doc)
        assert mapped == di["channel"], (
            f"{case_id}: the presented channel is not the frozen P2 "
            "mapping of the recorded result"
        )
        # the released cases no longer carry the HELD marker (the
        # release is recorded, not silent):
        assert "HELD (" not in case["label"]["rationale"]

    def test_held_set_is_exactly_the_recorded_findings(self):
        # The corrected held set of record (the W3 monotonic
        # adjudication, design section 8.2 item 6): EMPTY - no case
        # rationale carries a HELD marker after the recorded release,
        # and every adjudicated case is named in the challenge log's
        # resolution record (the release direction only; no case is
        # un-holded silently).
        flagged = {
            c["case_id"]: re.search(r"HELD \((C2-F\w+)\)",
                                    c["label"]["rationale"]).group(1)
            for c in CASES if "HELD (C2-F" in c["label"]["rationale"]
        }
        assert flagged == HELD, (
            f"the held rationales disagree with the recorded held "
            f"set: {flagged}"
        )
        log = _changelog_text()
        for cid, finding in ADJUDICATED.items():
            assert finding in log, (
                f"the adjudicated finding {finding} ({cid}) is not "
                "recorded in the challenge log"
            )
            assert cid in log, (
                f"the adjudicated case {cid} is not named in the "
                "challenge log's resolution record"
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
        # Recorded in-place correction (strengthened): the challenge
        # log must name every adjudicated finding + case, and the
        # recorded resolution/removal record of the corrected
        # endpoint (the W3 monotonic adjudication - the release is
        # recorded, never silent).
        text = _changelog_text()
        for finding in ("C2-F1", "C2-F2a", "C2-F2b", "C2-F3", "C2-F5",
                        "C2-F6"):
            assert finding in text
        for cid in ADJUDICATED:
            assert cid in text
        # the recorded resolutions of record + the removals with
        # their obligation destinations:
        assert "Resolutions of record" in text
        for cid in REMOVED_LOADER:
            assert f"{cid} | REMOVED" in text, (
                f"{cid}: the recorded removal is missing from the "
                "challenge log"
            )
        # whitespace-normalized (the markdown wraps the statements):
        flat = re.sub(r"\s+", " ", text)
        assert "MANDATORY E1 adversarial-execution assertion" in flat
        assert "additive 1.1.0 obligation" in flat

    def test_changelog_records_the_adjudication_identity_and_instant(self):
        # The adjudication record of record names the adjudicator's
        # identity + instant (the W3 rule: a held-set change is
        # explicit - the endpoint SHAs + UTC instants of the
        # Q3-C-D1-FU1 revision + the Q3-C-D1-FU2 design gate), and
        # states that the independent review has still not occurred.
        text = _changelog_text()
        assert "34ca5edf056c68c1719ed470e832e9f956626c19" in text
        assert "4f53538f34c588c6f2b5e66a237f40acae2b5995" in text
        assert "2026-10-16T02:44:50Z" in text
        assert "2026-10-16T17:36:55Z" in text
        assert "INDEPENDENT REVIEW HAS STILL NOT OCCURRED" in text

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
        # Recorded in-place correction (strengthened): the D-row
        # population of the corrected endpoint is 36 (the C2
        # endpoint's 37 minus the removed FA4-ADV-034 - the D16-iii
        # third obligation is the MANDATORY E1 adversarial-execution
        # assertion, design section 9.6, named in the handoff).
        text = _handoff_text()
        d_ids = [
            c["case_id"] for c in CASES if c["matrix_row"].startswith("D")
        ]
        assert len(d_ids) == 36
        missing = [cid for cid in d_ids if cid not in text]
        assert not missing, f"D rows missing from the tester scope: {missing}"
        assert "FA4-ADV-034" in text, (
            "the removed case is not named in the handoff (the E1 "
            "mandatory assertion destination must be recorded)"
        )
        assert "MANDATORY E1 adversarial-execution assertion" in text


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

    # -- The W2 / W4 / W6 qualification-ready gate over the corrected
    #    seal population (design section 8.2 item 7) --------------

    def test_qualification_ready_gate_passes_over_the_corrected_seal_population(self):
        """W2 positive: EVERY section 5.6 composition floor is
        verified over the ACTUAL 94-case seal population (not the
        draft authoring population - a floor verified only over the
        draft population is NOT seal evidence): the corrected row
        minimums (90 over the 48 rows), the Track A / Track B floors
        (90 / 21 / 18 / 3), the evidence-kind composition (88
        SYNTHETIC >= 80% / 6 RECORDED_FIXTURE >= 5 / 0 REAL_MARKET),
        the category floor (5 >= 4), and the bounded-vocabulary
        projection (W6). The review fields are the test-local
        decoder fixture (the gate is mechanical - it never claims to
        verify a human review)."""
        filled = [_filled(c) for c in CASES]
        registry = frozenset({DRYRUN_REVIEWER})
        records = {c["case_id"]: DRYRUN_REVIEWER for c in filled}
        ok, reason = qualification_ready_gate(
            filled, reviewer_registry=registry,
            changelog_review_records=records,
        )
        assert ok, f"the corrected 94-case population is not " \
                   f"qualification-ready: {reason}"
        assert reason == "qualification-ready"

    def test_gate_refuses_a_missing_review_with_the_pinned_reason(self):
        """W4: a missing review record is rejected with the PINNED
        deterministic reason (a gate that rejects for an un-pinned
        reason is a gate defect) - the full corrected population
        with one case's review record dropped."""
        filled = [_filled(c) for c in CASES]
        registry = frozenset({DRYRUN_REVIEWER})
        records = {c["case_id"]: DRYRUN_REVIEWER for c in filled}
        victim = "FA4-UNPR-011"
        del records[victim]
        ok, reason = qualification_ready_gate(
            filled, reviewer_registry=registry,
            changelog_review_records=records,
        )
        assert not ok
        assert reason == (
            f"case {victim}: no review record in the challenge log "
            "under the case's reviewer identity"
        ), f"the pinned missing-review reason moved: {reason!r}"

    def test_gate_refuses_a_below_track_a_floor_population(self):
        """W2: dropping Track A cases below the corrected 90 floor
        (and their row minimums) fails the composition half of the
        gate - a floor violation over the seal population is never
        silently passed."""
        filled = [_filled(c) for c in CASES]
        # drop two Track A cases from a minimum row (A-DELE 4 -> 2):
        dropped = 0
        kept = []
        for c in filled:
            if dropped < 2 and c["matrix_row"] == "A-DELE":
                dropped += 1
                continue
            kept.append(c)
        registry = frozenset({DRYRUN_REVIEWER})
        records = {c["case_id"]: DRYRUN_REVIEWER for c in kept}
        ok, reason = qualification_ready_gate(
            kept, reviewer_registry=registry,
            changelog_review_records=records,
        )
        assert not ok
        assert "A-DELE" in reason or "Track A" in reason, (
            f"the floor refusal must name the violated floor, got: "
            f"{reason!r}"
        )

    def test_gate_refuses_a_below_evidence_kind_floor_population(self):
        """W2: a population below the RECORDED_FIXTURE >= 5 floor
        (the corrected record carries exactly 6) fails the
        composition half of the gate - the evidence-kind
        composition is verified over the seal population, never the
        draft authoring population."""
        filled = [_filled(c) for c in CASES]
        # drop the two RECORDED_FIXTURE cases from minimum rows:
        kept = []
        dropped = 0
        for c in filled:
            if (
                dropped < 2
                and c["evidence_kind"] == "RECORDED_FIXTURE"
                and c["matrix_row"] in ("D7", "B1")
            ):
                dropped += 1
                continue
            kept.append(c)
        assert dropped == 2
        registry = frozenset({DRYRUN_REVIEWER})
        records = {c["case_id"]: DRYRUN_REVIEWER for c in kept}
        ok, reason = qualification_ready_gate(
            kept, reviewer_registry=registry,
            changelog_review_records=records,
        )
        assert not ok
        assert "RECORDED_FIXTURE" in reason or "matrix row" in reason, (
            f"the floor refusal must name the violated floor, got: "
            f"{reason!r}"
        )


# ---------------------------------------------------------------------------
# The pre-seal label / provenance corrections of record (Q3-C-C2-R1-FU1)
# the independent C2-R1 review's CH-1 / CH-2 challenges + the F-R1
# provenance finding, corrected under the section 4.6 item 5
# governance (class A - the expectation was factually wrong over the
# frozen contract; the F-R1 correction is a provenance annotation, no
# label field moved). Each regression below FAILS if the pre-
# correction value returns.
# ---------------------------------------------------------------------------


class TestPreSealCorrections:
    def test_fa4_adv_024_expected_tier_is_the_hard_conflict_supersession(self):
        """CH-1 regression (FA4-ADV-024 / D12, MAJOR): the expected
        tier is the frozen S2-A hard-conflict SUPERSESSION result, never
        the pre-supersession matrix base. Independently re-derived
        here from the sealed scripted context + the frozen contract
        DATA (the module is the byte-pinned contract of record - the
        frozen `SEMANTIC_OUTCOME_TIER_MATRIX` base, the frozen
        `ALWAYS_HARD_CONFLICT_CLASSES` set, and the frozen supersession
        precedence "always last inside the AI path" documented in the
        contract's `derive_authority_tier` docstring): NO_MATCH + HIGH
        + STRONG -> base EXCLUDED_LOW_CONFIDENCE; the scripted conflict
        class CAPACITY is ALWAYS_HARD -> supersession ->
        HARD_CONFLICT. The case's OWN sealed payload derived section
        records exactly that (tier + fired rule). Fails if the
        pre-correction tier (EXCLUDED_LOW_CONFIDENCE) returns."""
        from product_intelligence.research import semantic_authority_v2 as s2a

        case = next(c for c in CASES if c["case_id"] == "FA4-ADV-024")
        expected = case["expected"]
        # The sealed scripted context (the case's own payload evaluation
        # section - the frozen contract data the derivation consumes).
        payload = case["recorded_case"]["payload_document"]
        evaluation = payload["evaluation"]
        assert evaluation["decision"] == "NO_MATCH"
        assert evaluation["confidence"] == "HIGH"
        assert evaluation["conflict_classes"] == ["CAPACITY"]
        quality = payload["derived"]["product_evidence_quality"]
        assert quality == "STRONG"
        # The frozen derivation re-derived over the contract data:
        base = s2a.semantic_outcome_tier(
            s2a.V2SemanticDecision.NO_MATCH,
            s2a.V2Confidence.HIGH,
            s2a.ProductEvidenceQuality[quality],
        )
        assert base is s2a.AuthorityTier.EXCLUDED_LOW_CONFIDENCE
        hard = {s2a.ConflictClass(c) for c in evaluation["conflict_classes"]}
        assert hard & s2a.ALWAYS_HARD_CONFLICT_CLASSES, (
            "the scripted conflict class must be a frozen ALWAYS_HARD "
            "member (the supersession precondition)"
        )
        final = (
            s2a.AuthorityTier.HARD_CONFLICT
            if (hard & s2a.ALWAYS_HARD_CONFLICT_CLASSES)
            else base
        )
        assert final is s2a.AuthorityTier.HARD_CONFLICT
        # The authored expectation: the superseded result ...
        assert expected["tier"] == final.value
        # ... never the pre-supersession base (the exact CH-1
        # regression).
        assert expected["tier"] != base.value
        # The case's own sealed payload snapshot agrees (the recorded
        # snapshot contradicted the pre-correction expected block).
        assert payload["derived"]["authority_tier"] == expected["tier"]
        assert "HARD_CONFLICT_SUPERSEDES" in payload["derived"]["fired_rules"]
        assert "SEMANTIC_OUTCOME_MATRIX" in payload["derived"]["fired_rules"]
        # The preserved axes (the correction moves ONLY the tier):
        assert expected["outcome"] == "DERIVED"
        assert expected["unit"] == "PROVEN_EQUIVALENT"
        assert expected["quantity_axis"] == "BOTH_UNPUBLISHED"
        assert expected["candidate_composition_state"] == "ESTABLISHED"
        assert expected["target_composition_state"] == "ESTABLISHED"
        assert expected["textual_relation"] == "T-AGREE"
        assert expected["expected_ceiling"] is None
        assert expected["pricing_eligible"] is False
        assert expected["refusal"] is None
        assert expected["replay"] == "REPLAY_PASS"
        # The frozen pricing-eligibility consequence stands: HARD_
        # CONFLICT is outside the frozen PRICING_ELIGIBLE_TIERS set.
        assert s2a.AuthorityTier.HARD_CONFLICT not in s2a.PRICING_ELIGIBLE_TIERS

    def test_fa4_unpr_022_textual_relation_is_the_frozen_grammar_multiset_difference(self):
        """CH-2 regression (FA4-UNPR-022 / B11, LOW): the sealed
        candidate clause '2x RAM + 1x CPU, as listed' and the sealed
        target clause '2x RAM + 1x CPU' BOTH fully parse under the
        frozen P3 versioned materiality grammar - 'as listed' is a
        valid item token (alphanumerics with an internal single
        space, the same class as the worked-example 'power cables') -
        and their canonical multisets DIFFER, so the frozen textual
        axis over two fully-parsed clauses is T-DIFF-MATERIAL (never
        T-DIFF-UNESTABLISHED, which the grammar reserves for a side
        that does not fully parse). Re-derived here by re-running the
        frozen grammar over the sealed clause bytes (the contract
        datum - never an expected-label source); the target clause
        digest cross-checks the sealed attestation binding. Fails if
        the pre-correction T-DIFF-UNESTABLISHED returns. The UNPROVEN
        unit + its governing missing-completeness rationale (U15 - the
        candidate is completeness-unknown) are preserved: a material
        difference over a completeness-unknown clause never derives a
        contradiction (the D7 safe direction)."""
        import hashlib

        from product_intelligence.research import semantic_authority_fu4 as fu4

        case = next(c for c in CASES if c["case_id"] == "FA4-UNPR-022")
        expected = case["expected"]
        cand_clause = case["derivation_inputs"]["candidate_composition"]["composition_clause"]
        tgt_clause = case["derivation_inputs"]["target_evidence"]["document"]["composition_clause"]
        assert cand_clause == "2x RAM + 1x CPU, as listed"
        assert tgt_clause == "2x RAM + 1x CPU"
        # The frozen grammar over the sealed clause bytes:
        parsed_cand = fu4._full_parse_clause(cand_clause)
        parsed_tgt = fu4._full_parse_clause(tgt_clause)
        assert parsed_cand is not None, (
            "the sealed candidate clause does not fully parse under "
            "the frozen grammar - the T-DIFF-MATERIAL correction would "
            "misstate the frozen contract (STOP condition of record)"
        )
        assert parsed_tgt is not None, (
            "the sealed target clause does not fully parse under the "
            "frozen grammar - the T-DIFF-MATERIAL correction would "
            "misstate the frozen contract (STOP condition of record)"
        )
        # The trailing 'as listed' is a valid item token (quantity 1)
        # of the frozen grammar - the same class as the worked-example
        # 'power cables':
        assert (1, "as listed") in parsed_cand
        assert fu4._ITEM_TOKEN_RE.match("as listed")
        # ... and the canonical multisets DIFFER:
        assert parsed_cand != parsed_tgt
        # The frozen axis over two fully-parsed differing clauses:
        assert fu4._textual_relation(cand_clause, tgt_clause) == "T-DIFF-MATERIAL"
        # The authored expectation: the corrected relationship ...
        assert expected["textual_relation"] == "T-DIFF-MATERIAL"
        # ... never the pre-correction value (the exact CH-2
        # regression):
        assert expected["textual_relation"] != "T-DIFF-UNESTABLISHED"
        # The preserved UNPROVEN outcome + its governing missing-
        # completeness rationale (U15):
        assert expected["outcome"] == "DERIVED"
        assert expected["unit"] == "UNPROVEN"
        assert expected["candidate_composition_state"] == "SYNTACTICALLY_VALID"
        assert expected["target_composition_state"] == "ESTABLISHED"
        assert expected["quantity_axis"] == "BOTH_UNPUBLISHED"
        assert expected["tier"] == "NEEDS_REVIEW"
        assert expected["expected_ceiling"] == "CEILING_SALES_UNIT_NOT_PROVEN"
        assert expected["pricing_eligible"] is False
        assert expected["refusal"] is None
        assert expected["replay"] == "NOT_APPLICABLE"
        # The sealed target attestation binds exactly the sealed
        # target clause (the clause-digest cross-check over the
        # corrected parse ground):
        att = case["derivation_inputs"]["target_evidence"]["document"]["completeness_attestation"]
        assert att["clause_digest"] == hashlib.sha256(
            tgt_clause.encode("utf-8")
        ).hexdigest()

    def test_fa4_dele_005_source_url_is_the_archive_recorded_url(self):
        """F-R1 regression (FA4-DELE-005 / B-DELE, MEDIUM provenance):
        the sealed source blocks + the recorded V2 case carry the URL
        the committed recording evidence supports - the cited
        archive's own 4D-PRE evidence line (the DirectMacro search-
        results page for the recorded MPN), which is exactly the
        original 4D-A acquisition target for that MPN (the 4D-A
        record pins the locator URL and forbids a fabricated product
        slug). Fails if the unsupported pre-correction URL
        (www.directd.com) returns anywhere in the case. The expected
        label is unaffected (the URL is not a channel / derivation
        field); the C1 provenance-binding invariant (the recorded V2
        case's candidate source URL exactly equal to the sealed
        candidate block's) stands."""
        case = next(c for c in CASES if c["case_id"] == "FA4-DELE-005")
        archive_rel = case["source"]["candidate"]["archive"]
        assert archive_rel == (
            "tests/fixtures/pages/"
            "directmacro_bcm957608_p2200gqf00_search.html"
        )
        archive = (REPO_ROOT / archive_rel).read_bytes()
        # The declared archive digests verify over the committed file
        # (both sealed blocks cite the same archive):
        for side in ("candidate", "target"):
            assert hashlib.sha256(archive).hexdigest() == (
                case["source"][side]["archive_digest"]
            ), f"the {side} block's declared archive digest no longer " \
               "verifies over the committed file"
        # The archive's own 4D-PRE evidence records the retrieval URL:
        text = archive.decode("utf-8")
        m = re.search(r"^\s+source: (\S+)$", text, re.MULTILINE)
        assert m, "the archive's recorded 4D-PRE source line is missing"
        recorded_url = m.group(1)
        assert recorded_url == (
            "https://directmacro.com/catalogsearch/result/?q=BCM957608-P2200GQF00"
        )
        # Every sealed location carries exactly the archive-recorded
        # URL (the C1 provenance binding keeps the recorded V2 case
        # equal to the sealed candidate block; the target block cites
        # the same archive):
        assert case["source"]["candidate"]["source_url"] == recorded_url
        assert case["source"]["target"]["source_url"] == recorded_url
        assert case["recorded_case"]["v2_case_document"]["candidate"]["source_url"] == recorded_url
        # The unsupported pre-correction URL is gone (the exact F-R1
        # regression):
        assert "www.directd.com" not in json.dumps(case)


# ---------------------------------------------------------------------------
# The authoring import prohibition (design section 4.6 item 2(a))
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# The F-R6 + F-R2 pre-seal corrections of record (Q3-C-C1-FU4 +
# C2-FU2): the D6-i stage re-attribution (the approved Q3-C-D1-FU3
# adjudication - Option B, the C2-F2a precedent; the Q3-C-D1-FU3-
# FU1 two-contract correction) + the D11 documentary citation
# digest completion (the verified Micron catalog digest; no expected
# field moves). Each regression below FAILS if the pre-correction
# value returns.
# ---------------------------------------------------------------------------

#: The verified Micron catalog digest (F-R2): recomputed from the
#: current source bytes at test time (the catalog file itself is
#: UNCHANGED - a catalog move fails the pin, as does a path-only
#: citation).
MICRON_CATALOG_REL = "tests/fixtures/pages/micron_7500_part_catalog.json"
MICRON_CATALOG_SHA256 = (
    "160d4fe97a5df5249e8f6404f6b005c0515fab4def1b4668fdaf87c727600743"
)


class TestC2Fu2Corrections:
    def test_fa4_adv_012_refusal_is_the_f_r6_adjudicated_corpus_integrity(self):
        """F-R6 regression (FA4-ADV-012 / D6-i): the expected refusal
        is the ADJUDICATED stage re-attribution of the approved Q3-C-
        D1-FU3 revision record (Option B - the C2-F2a precedent):
        CORPUS_INTEGRITY with error_type null (the stage-error
        vocabulary: the loader's own stage names no implementation
        error class) + the exact named observation
        SOURCE_EXTRACTION_INPUT_DIGEST at the CASE_DOCUMENT layer
        (the family loader's cross-document integrity check - the
        frozen constructor / codec / derivation are silent over the
        sealed shape). The pre-correction CONSTRUCTION / CONSTRUCTOR
        attribution trips this pin. Every unrelated expected axis +
        the case identity / governance / sealed evidence remains
        byte-unchanged (the correction moves ONLY the two refusal
        fields + the label annotation)."""
        case = next(c for c in CASES if c["case_id"] == "FA4-ADV-012")
        refusal = case["expected"]["refusal"]
        assert refusal == {"stage": "CORPUS_INTEGRITY", "error_type": None}, (
            f"FA4-ADV-012: the F-R6 adjudicated refusal moved: {refusal!r}"
        )
        # the obsolete pre-correction attribution trips the pin:
        assert refusal != {"stage": "CONSTRUCTION", "error_type": "CONSTRUCTOR"}
        # the governing design adjudication is named in the label
        # annotation (the exact observation point, not the correction's
        # prose alone):
        citation = case["label"]["grounding_citation"]
        rationale = case["label"]["rationale"]
        assert "Q3-C-D1-FU3" in citation
        assert "SOURCE_EXTRACTION_INPUT_DIGEST" in citation
        assert "CASE_DOCUMENT" in rationale
        assert "CORPUS_INTEGRITY" in rationale
        # PRESERVED (byte-unchanged by the correction):
        e = case["expected"]
        assert e["outcome"] == "REFUSED"
        assert e["replay"] == "NOT_APPLICABLE"
        for axis in (
            "unit", "quantity_axis", "candidate_composition_state",
            "target_composition_state", "textual_relation", "tier",
            "expected_ceiling", "pricing_eligible", "semantic_identity_note",
        ):
            assert e[axis] is None, (
                f"FA4-ADV-012: the unrelated expected axis {axis!r} "
                f"moved: {e[axis]!r}"
            )
        assert case["matrix_row"] == "D6"
        assert case["track"] == "A"
        assert case["surface"] == "DERIVATION"
        assert case["evidence_kind"] == "SYNTHETIC"
        assert case["challenge_tags"] == ["cross_listing_substitution"]
        assert case["label"]["author"] == AUTHOR_IDENTITY
        assert case["label"]["author_utc"] == AUTHOR_UTC
        assert case["label"]["reviewer"] is None
        assert case["label"]["reviewer_utc"] is None
        assert case["label"]["review_status"] == "DRAFT"
        assert case["label"]["labeling_provenance"] == "ADVERSARIAL_CONSTRUCTION"
        # every sealed evidence document is byte-unchanged (the
        # recorded cross-document defect is plain-verifiable over the
        # sealed bytes - the test re-derives it itself, it does not
        # trust the label):
        ext = case["derivation_inputs"]["extraction_evidence"]
        assert ext["input_document"]["fields"]["product_title"] == (
            "ABC-123 1TB NVMe Drive: bundle: 2x RAM + 1x SSD"
        )
        assert ext["result_document"]["input_digest"] == (
            "660fdb477109d2bbabc4c6adf5b8fa1b1c1d7e442fbfdf5a45efa40200a52599"
        )
        assert fam.canonical_sha256(ext["input_document"]) != (
            ext["result_document"]["input_digest"]
        ), "the sealed D6-i cross-document defect is missing (the " \
           "evidence documents moved under the correction)"
        assert case["source"]["candidate"]["title_text"] == (
            "ABC-123 1TB NVMe Drive: bundle: 2x RAM + 1x SSD"
        )
        # the corrected case LOADS under the real family loader with
        # the test-local reviewer fill (Contract A - the acceptance
        # after the stage-coherence verification):
        with tempfile.TemporaryDirectory() as td:
            _load_single(_filled(case), Path(td))

    def test_fa4_adv_012_obsolete_construction_attribution_is_refused_by_the_corrected_loader(
        self, tmp_path
    ):
        """F-R6 regression (the loader half): the pre-correction
        CONSTRUCTION / CONSTRUCTOR attribution is REFUSED by the
        corrected stage-coherence rule over the sealed FA4-ADV-012
        documents (the case-document observation fired; no
        constructor-layer observation exists over the shape) - a
        mutation of the label back to the obsolete attribution trips
        this pin, and the refusal is the bounded deterministic
        reason, never a silent acceptance."""
        case = next(c for c in CASES if c["case_id"] == "FA4-ADV-012")
        reverted = _filled(case)
        reverted["expected"]["refusal"] = {
            "stage": "CONSTRUCTION",
            "error_type": "CONSTRUCTOR",
        }
        # the Contract B interface is independent of the label: the
        # reverted attribution still observes the genuine defect:
        reverted["case_digest"] = fam.case_state_digest(reverted)
        record = fam.observe_corpus_case_integrity(reverted)
        assert "SOURCE_EXTRACTION_INPUT_DIGEST" in record.check_names
        assert fam.observation_stages(record, "DERIVATION") == frozenset(
            {"CORPUS_INTEGRITY"}
        )
        # and Contract A refuses the obsolete attribution:
        document = fam_fixtures.build_corpus_document(
            DRYRUN_CREATED_UTC, (reverted,)
        )
        with pytest.raises(fam.BundleAuthorityLabelError) as exc:
            fam.verify_corpus_document(document)
        assert (
            "case FA4-ADV-012: the labeled CONSTRUCTION defect is not "
            "observable"
        ) in exc.value.reason

    def test_fa4_adv_022_and_023_citations_carry_the_verified_catalog_digest(self):
        """F-R2 regression (FA4-ADV-022 / FA4-ADV-023 / D11): the two
        grounding citations carry the VERIFIED catalog digest (the
        pre-correction path-only citation trips the pin). The digest
        is recomputed from the catalog's CURRENT source bytes at test
        time (a catalog move or a path-only citation fails the node);
        the cases' expected labels + evidence classification are
        UNAFFECTED (the F-R2 correction is a documentary annotation -
        no expected field moved)."""
        catalog = REPO_ROOT / MICRON_CATALOG_REL
        actual = hashlib.sha256(catalog.read_bytes()).hexdigest()
        assert actual == MICRON_CATALOG_SHA256, (
            f"the Micron catalog moved (working-tree digest {actual}); "
            "the cited digest is the verified value of record - a "
            "catalog change is a STOP condition, not a silent "
            "re-pin"
        )
        for cid in ("FA4-ADV-022", "FA4-ADV-023"):
            case = next(c for c in CASES if c["case_id"] == cid)
            citation = case["label"]["grounding_citation"]
            path_idx = citation.index(MICRON_CATALOG_REL)
            assert MICRON_CATALOG_SHA256 in citation[path_idx:], (
                f"{cid}: the D11 grounding citation names the Micron "
                "catalog by path only - the F-R2 verified digest "
                "returns (the pre-correction value)"
            )
            # the expected label + evidence classification are
            # unaffected by the documentary correction:
            e = case["expected"]
            assert e["outcome"] == "DERIVED"
            assert e["unit"] == "CONTRADICTED"
            assert e["tier"] == "NEEDS_REVIEW"
            assert e["expected_ceiling"] == "CEILING_SALES_UNIT_CONTRADICTED"
            assert e["pricing_eligible"] is False
            assert case["evidence_kind"] == "SYNTHETIC"
            assert case["matrix_row"] == "D11"
            assert case["label"]["review_status"] == "DRAFT"
            assert case["label"]["reviewer"] is None


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
        # Recorded in-place correction (pin re-recorded under the
        # C1-FU3 endpoint's own governance): corpus.py is the C1-FU3
        # CORRECTED validator of record (design section 9.11 file
        # (1) - the adjudicated corrections, not a silent move); cli.
        # py / __init__.py remain the C1 / C2 byte-frozen files (the
        # corrective phase touches NO CLI / package-surface code).
        assert _sha256_file(rel) == C1_PACKAGE_PINS[rel], (
            f"{rel} moved; the family package is sealed-by-digest at "
            "the C1-FU3 endpoint of record (the C1-FU3 corrections "
            "are the re-pinned state of corpus.py)"
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
        # Recorded in-place correction (pins re-recorded under the
        # governance rule): the challenge log + the reviewer handoff
        # are the CORRECTED governance state of record - at the
        # Q3-C-C2-R1-FU1 endpoint the pre-seal correction record +
        # the section 4.1 re-verification worklist (the earlier
        # re-pin: the adjudication record + the corrected rows'
        # worklist - design section 9.11 file (5)); the family README
        # + the DRAFT policy remain the C2 byte-frozen artifacts.
        for rel, expected in sorted(FAMILY_ARTIFACT_PINS.items()):
            assert _sha256_file(rel) == expected, (
                f"{rel} moved; the family governance record is "
                "sealed-by-digest at the Q3-C-C2-R1-FU1 pre-seal "
                "correction endpoint of record"
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
