"""Mutation tests proving the corpus validator actually rejects bad records.

A validator that only ever sees valid data is indistinguishable from one that
returns ``True``. Each test here takes a known-good record, breaks exactly one
thing, and asserts the break is caught — so the invariants documented in
``evaluation/README.md`` are enforced rather than merely described.

These operate on dictionaries, not files: the validator is pure, so no
temporary corpus files, no I/O, and no network are involved.
"""

from __future__ import annotations

import copy
import json
from typing import Any, Callable

import pytest

from product_intelligence.evaluation import (
    SUPPORTED_CORPUS_VERSION,
    CaseKind,
    CorpusValidationError,
    build_case,
    build_corpus_file,
    load_corpus_file,
    validate_corpus,
)

WHERE = "test"


def valid_real_case() -> dict:
    return {
        "case_id": "REAL-9001",
        "case_kind": "REAL_VERIFIED",
        "input": {
            "manufacturer_part_number": "TEST-PART-1",
            "description": "a test part",
        },
        "expectation": {
            "resolution": "EXACT_IDENTITY",
            "manufacturer": "TestCo",
            "canonical_manufacturer_part_number": "TEST-PART-1",
            "product_name": "Test Part One",
            "product_family": "Test Family",
        },
        "challenge_tags": ["EXACT_INPUT"],
        "provenance": {
            "kind": "MANUFACTURER",
            "source_name": "TestCo",
            "source_url": "https://example.invalid/test-part-1",
            "verification_note": "TestCo's page identifies this part.",
            "verified_on": "2026-08-17",
        },
    }


def valid_synthetic_case() -> dict:
    return {
        "case_id": "SYN-9001",
        "case_kind": "SYNTHETIC",
        "input": {
            "manufacturer_part_number": "TEST-PART-2",
            "description": "a constructed part",
        },
        "expectation": {
            "resolution": "UNKNOWN",
            "must_not_resolve_to": ["TEST-PART-1"],
            "reason": "the part number is fictitious",
        },
        "challenge_tags": ["UNKNOWN_PRODUCT"],
        "provenance": {
            "kind": "SYNTHETIC_CONSTRUCTION",
            "construction": "wholly constructed for this test",
        },
    }


def build_real(raw: dict):
    return build_case(raw, declared_case_kind=CaseKind.REAL_VERIFIED, where=WHERE)


def build_synthetic(raw: dict):
    return build_case(raw, declared_case_kind=CaseKind.SYNTHETIC, where=WHERE)


def test_the_known_good_records_validate() -> None:
    """Otherwise every rejection test below could be passing for the wrong reason."""
    assert build_real(valid_real_case()).case_id == "REAL-9001"
    assert build_synthetic(valid_synthetic_case()).case_id == "SYN-9001"


def _mutate(base: dict, mutation: Callable[[dict], Any]) -> dict:
    broken = copy.deepcopy(base)
    mutation(broken)
    return broken


def _set_expectation(**fields: Any) -> Callable[[dict], Any]:
    def mutation(case: dict) -> None:
        case["expectation"].update(fields)

    return mutation


REAL_MUTATIONS = {
    "unknown top-level field": lambda case: case.update({"challenge_tag": ["EXACT_INPUT"]}),
    "missing case_id": lambda case: case.pop("case_id"),
    "missing input": lambda case: case.pop("input"),
    "missing expectation": lambda case: case.pop("expectation"),
    "missing provenance": lambda case: case.pop("provenance"),
    "empty case_id": lambda case: case.update({"case_id": "  "}),
    "lowercase case_id": lambda case: case.update({"case_id": "real-9001"}),
    "non-string case_id": lambda case: case.update({"case_id": 9001}),
    "case_kind outside the vocabulary": lambda case: case.update({"case_kind": "REAL"}),
    "synthetic case in a real file": lambda case: case.update({"case_kind": "SYNTHETIC"}),
    "unknown input field": lambda case: case["input"].update({"quantity": "1"}),
    "missing description": lambda case: case["input"].pop("description"),
    "non-string input value": lambda case: case["input"].update(
        {"manufacturer_part_number": 12345}
    ),
    "input that is not a valid research request": lambda case: case["input"].update(
        {"manufacturer_part_number": "  ", "description": ""}
    ),
    "resolution outside the vocabulary": _set_expectation(resolution="PROBABLY"),
    "exact identity with no canonical part number": lambda case: case[
        "expectation"
    ].pop("canonical_manufacturer_part_number"),
    "exact identity with no manufacturer": lambda case: case["expectation"].pop(
        "manufacturer"
    ),
    "empty manufacturer": _set_expectation(manufacturer="   "),
    "unknown expectation field": _set_expectation(expected_price="430.00"),
    "forbidding the expected identity": _set_expectation(
        must_not_resolve_to=["TEST-PART-1"]
    ),
    "duplicate forbidden identity": _set_expectation(
        must_not_resolve_to=["OTHER-PART", "OTHER-PART"]
    ),
    "forbidden identity that is not a string": _set_expectation(
        must_not_resolve_to=[None]
    ),
    "must_not_resolve_to that is not a list": _set_expectation(
        must_not_resolve_to="OTHER-PART"
    ),
    "no challenge tags": lambda case: case.update({"challenge_tags": []}),
    "challenge tag outside the vocabulary": lambda case: case.update(
        {"challenge_tags": ["HARD_ONE"]}
    ),
    "duplicate challenge tags": lambda case: case.update(
        {"challenge_tags": ["EXACT_INPUT", "EXACT_INPUT"]}
    ),
    "challenge tags that are not a list": lambda case: case.update(
        {"challenge_tags": "EXACT_INPUT"}
    ),
    "real case with synthetic provenance": lambda case: case.update(
        {
            "provenance": {
                "kind": "SYNTHETIC_CONSTRUCTION",
                "construction": "made up",
            }
        }
    ),
    "real case with no source url": lambda case: case["provenance"].pop("source_url"),
    "real case with no verification note": lambda case: case["provenance"].pop(
        "verification_note"
    ),
    "real case with no verification date": lambda case: case["provenance"].pop(
        "verified_on"
    ),
    "real case with an empty source url": lambda case: case["provenance"].update(
        {"source_url": ""}
    ),
    "real case with a non-https source url": lambda case: case["provenance"].update(
        {"source_url": "http://example.invalid/test-part-1"}
    ),
    "real case with an unparseable verification date": lambda case: case[
        "provenance"
    ].update({"verified_on": "August 2026"}),
    "provenance kind outside the vocabulary": lambda case: case["provenance"].update(
        {"kind": "A_GUY_TOLD_ME"}
    ),
    "non-boolean identity sharing flag": lambda case: case.update(
        {"deliberately_shares_identity": "yes"}
    ),
}

SYNTHETIC_MUTATIONS = {
    "real case kind in a synthetic file": lambda case: case.update(
        {"case_kind": "REAL_VERIFIED"}
    ),
    "fabricated source provenance": lambda case: case["provenance"].update(
        {"source_url": "https://example.invalid/not-a-real-source"}
    ),
    "fabricated verification note": lambda case: case["provenance"].update(
        {"verification_note": "the manufacturer says so"}
    ),
    "manufacturer provenance on a constructed case": lambda case: case[
        "provenance"
    ].update({"kind": "MANUFACTURER"}),
    "no construction note": lambda case: case["provenance"].pop("construction"),
    "empty construction note": lambda case: case["provenance"].update(
        {"construction": ""}
    ),
    "abstention that also names the answer": _set_expectation(
        canonical_manufacturer_part_number="TEST-PART-1"
    ),
    "abstention with no reason": lambda case: case["expectation"].pop("reason"),
    "derivation that is not a list": lambda case: case["provenance"].update(
        {"derived_from_case_ids": "REAL-9001"}
    ),
}


@pytest.mark.parametrize("description", sorted(REAL_MUTATIONS))
def test_broken_real_case_is_rejected(description: str) -> None:
    broken = _mutate(valid_real_case(), REAL_MUTATIONS[description])

    with pytest.raises(CorpusValidationError):
        build_real(broken)


@pytest.mark.parametrize("description", sorted(SYNTHETIC_MUTATIONS))
def test_broken_synthetic_case_is_rejected(description: str) -> None:
    broken = _mutate(valid_synthetic_case(), SYNTHETIC_MUTATIONS[description])

    with pytest.raises(CorpusValidationError):
        build_synthetic(broken)


def test_optional_fields_are_accepted() -> None:
    raw = valid_real_case()
    raw["notes"] = "a note for a reviewer"
    raw["deliberately_shares_identity"] = False

    case = build_real(raw)

    assert case.notes == "a note for a reviewer"
    assert case.deliberately_shares_identity is False


def test_case_input_whitespace_is_preserved_not_rejected() -> None:
    """Padded input is a challenge class, so validation must keep it intact."""
    raw = valid_real_case()
    raw["input"]["manufacturer_part_number"] = "  TEST-PART-1  "

    case = build_real(raw)

    assert case.input.manufacturer_part_number == "  TEST-PART-1  "
    assert case.input.as_research_request().manufacturer_part_number == "TEST-PART-1"


def _corpus_file(*cases: dict, case_kind: str = "REAL_VERIFIED") -> dict:
    return {
        "corpus_version": SUPPORTED_CORPUS_VERSION,
        "declared_case_kind": case_kind,
        "cases": list(cases),
    }


def test_valid_corpus_file_payload_is_accepted() -> None:
    built = build_corpus_file(_corpus_file(valid_real_case()), where=WHERE)

    assert [case.case_id for case in built] == ["REAL-9001"]


FILE_MUTATIONS = {
    "unknown file field": lambda payload: payload.update({"cases_v2": []}),
    "missing version": lambda payload: payload.pop("corpus_version"),
    "unsupported version": lambda payload: payload.update({"corpus_version": 2}),
    "version that is a boolean": lambda payload: payload.update(
        {"corpus_version": True}
    ),
    "declared kind outside the vocabulary": lambda payload: payload.update(
        {"declared_case_kind": "MOSTLY_REAL"}
    ),
    "no cases at all": lambda payload: payload.update({"cases": []}),
    "cases that are not a list": lambda payload: payload.update({"cases": {}}),
}


@pytest.mark.parametrize("description", sorted(FILE_MUTATIONS))
def test_broken_corpus_file_is_rejected(description: str) -> None:
    broken = _mutate(_corpus_file(valid_real_case()), FILE_MUTATIONS[description])

    with pytest.raises(CorpusValidationError):
        build_corpus_file(broken, where=WHERE)


def test_payload_that_is_not_an_object_is_rejected() -> None:
    with pytest.raises(CorpusValidationError):
        build_corpus_file([valid_real_case()], where=WHERE)


def test_duplicate_case_ids_are_rejected() -> None:
    cases = build_corpus_file(
        _corpus_file(valid_real_case(), valid_real_case()), where=WHERE
    )

    with pytest.raises(CorpusValidationError, match="duplicate case_id"):
        validate_corpus(cases)


def test_accidentally_repeated_real_identity_is_rejected() -> None:
    """A seed recorded twice would inflate the benchmark silently."""
    second = valid_real_case()
    second["case_id"] = "REAL-9002"
    cases = build_corpus_file(_corpus_file(valid_real_case(), second), where=WHERE)

    with pytest.raises(CorpusValidationError, match="repeat the identity"):
        validate_corpus(cases)


def test_deliberately_shared_real_identity_is_accepted() -> None:
    first = valid_real_case()
    first["deliberately_shares_identity"] = True
    second = valid_real_case()
    second["case_id"] = "REAL-9002"
    second["deliberately_shares_identity"] = True

    corpus = validate_corpus(build_corpus_file(_corpus_file(first, second), where=WHERE))

    assert len(corpus) == 2


def test_real_case_without_an_expected_identity_is_rejected() -> None:
    """A verified source is what a real case is for; abstaining wastes it.

    A request that should legitimately go unresolved is a constructed
    situation, and belongs in the synthetic set.
    """
    raw = valid_real_case()
    raw["expectation"] = {
        "resolution": "UNKNOWN",
        "reason": "not established",
    }
    cases = build_corpus_file(_corpus_file(raw), where=WHERE)

    with pytest.raises(CorpusValidationError, match="canonical identity"):
        validate_corpus(cases)


def test_derivation_referencing_an_unknown_case_is_rejected() -> None:
    synthetic = valid_synthetic_case()
    synthetic["provenance"]["derived_from_case_ids"] = ["REAL-0000"]
    cases = build_corpus_file(
        _corpus_file(synthetic, case_kind="SYNTHETIC"), where=WHERE
    )

    with pytest.raises(CorpusValidationError, match="unknown case"):
        validate_corpus(cases)


def test_self_referential_derivation_is_rejected() -> None:
    synthetic = valid_synthetic_case()
    synthetic["provenance"]["derived_from_case_ids"] = ["SYN-9001"]
    cases = build_corpus_file(
        _corpus_file(synthetic, case_kind="SYNTHETIC"), where=WHERE
    )

    with pytest.raises(CorpusValidationError, match="references the case itself"):
        validate_corpus(cases)


def test_validation_errors_name_the_offending_case() -> None:
    """A benchmark is reviewed by people; the error has to point at the record."""
    broken = valid_real_case()
    broken["expectation"]["resolution"] = "PROBABLY"

    with pytest.raises(CorpusValidationError) as raised:
        build_real(broken)

    assert "REAL-9001" in str(raised.value)
    assert "resolution" in str(raised.value)


def test_unreadable_corpus_file_is_reported_as_a_corpus_error(tmp_path) -> None:
    missing = tmp_path / "not_here.json"

    with pytest.raises(CorpusValidationError, match="cannot be read"):
        load_corpus_file(missing)


def test_malformed_json_is_reported_as_a_corpus_error(tmp_path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{not json", encoding="utf-8")

    with pytest.raises(CorpusValidationError, match="not valid JSON"):
        load_corpus_file(path)


def test_a_corpus_file_round_trips_through_json(tmp_path) -> None:
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps(_corpus_file(valid_real_case())), encoding="utf-8")

    assert [case.case_id for case in load_corpus_file(path)] == ["REAL-9001"]
