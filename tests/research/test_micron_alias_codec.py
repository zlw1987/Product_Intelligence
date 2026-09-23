"""Codec tests for the Micron alias snapshot (PRODUCT-INTEL.4D-D).

The codec is pure and versioned: it serializes the self-validating
``MicronAliasEligibilityResult`` (bounded provenance, never the catalog
body) and, on decode, reconstructs the contract so that ANY tampered or
corrupt persisted payload fails closed with ``MicronAliasCodecError``.
"""

from __future__ import annotations

import copy
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pytest

from product_intelligence.research.identity import compare_part_numbers
from product_intelligence.research.micron_alias_codec import (
    MicronAliasCodecError,
    decode_micron_alias_snapshot,
    encode_micron_alias_snapshot,
)
from product_intelligence.research.micron_packaging_alias import (
    MICRON_7500_APPROVED_ORIGIN,
    MICRON_7500_CATEGORY,
    MICRON_7500_MANUFACTURER,
    MICRON_7500_POLICY_ID,
    MICRON_7500_REQUESTED_CATALOG_URL,
    MICRON_7500_SOURCE_NAME,
    MicronAliasEligibilityResult,
    MicronAliasEligibilityStatus,
    MicronSsdCategoryEvidence,
    build_packaging_alias_relation,
    derive_lookup_base_candidate,
    extract_micron_7500_catalog_records,
    matched_ssd_category_evidence,
)
from product_intelligence.domain import ResearchRequest

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "pages"
CATALOG_FIXTURE = FIXTURES / "micron_7500_part_catalog.json"
BASE = "MTFDKCC3T8TGP-1BK1DABYY"
BASER = f"{BASE}R"
BASET = f"{BASE}T"
FIXTURE_SHA256 = (
    "160d4fe97a5df5249e8f6404f6b005c0515fab4def1b4668fdaf87c727600743"
)
UTC = timezone.utc
FIXED_AT = datetime(2026, 9, 22, 23, 20, 25, tzinfo=UTC)


def _body() -> str:
    return CATALOG_FIXTURE.read_bytes().decode("utf-8")


def _established_result(mpn: str = BASER) -> MicronAliasEligibilityResult:
    records = extract_micron_7500_catalog_records(_body())
    record = next(r for r in records if r.part_number == BASE)
    evidence = matched_ssd_category_evidence(record)
    return MicronAliasEligibilityResult(
        status=MicronAliasEligibilityStatus.ESTABLISHED,
        request=ResearchRequest(manufacturer_part_number=mpn, description="codec"),
        lookup_base_candidate=derive_lookup_base_candidate(mpn),
        policy_id=MICRON_7500_POLICY_ID,
        manufacturer=MICRON_7500_MANUFACTURER,
        category=MICRON_7500_CATEGORY,
        requested_source_url=MICRON_7500_REQUESTED_CATALOG_URL,
        fetched_final_url=MICRON_7500_REQUESTED_CATALOG_URL,
        retrieved_at=FIXED_AT,
        source_name=MICRON_7500_SOURCE_NAME,
        matched_base_mpn=BASE,
        part_number_match=compare_part_numbers(
            derive_lookup_base_candidate(mpn), BASE
        ),
        ssd_category_evidence=MicronSsdCategoryEvidence(
            attr_name=evidence.name, attr_id=evidence.attr_id, attr_value=True
        ),
        alias_relation=build_packaging_alias_relation(mpn, BASE),
        body_sha256=hashlib.sha256(_body().encode("utf-8")).hexdigest(),
    )


def _bounded_result(
    mpn: str = "NOT-IN-CATALOG",
) -> MicronAliasEligibilityResult:
    return MicronAliasEligibilityResult(
        status=MicronAliasEligibilityStatus.NO_AUTHORITY_MATCH,
        request=ResearchRequest(manufacturer_part_number=mpn, description="codec"),
        lookup_base_candidate=derive_lookup_base_candidate(mpn),
        policy_id=MICRON_7500_POLICY_ID,
        manufacturer=None,
        category=None,
        requested_source_url=MICRON_7500_REQUESTED_CATALOG_URL,
        fetched_final_url=MICRON_7500_REQUESTED_CATALOG_URL,
        retrieved_at=FIXED_AT,
        source_name=MICRON_7500_SOURCE_NAME,
        matched_base_mpn=None,
        part_number_match=None,
        ssd_category_evidence=None,
        alias_relation=None,
        body_sha256=FIXTURE_SHA256,
    )


def _degenerate_result(mpn: str = "-R") -> MicronAliasEligibilityResult:
    return MicronAliasEligibilityResult(
        status=MicronAliasEligibilityStatus.INVALID_LOOKUP_BASE,
        request=ResearchRequest(manufacturer_part_number=mpn, description="codec"),
        lookup_base_candidate=None,
        policy_id=MICRON_7500_POLICY_ID,
        manufacturer=None,
        category=None,
        requested_source_url=None,
        fetched_final_url=None,
        retrieved_at=None,
        source_name=None,
        matched_base_mpn=None,
        part_number_match=None,
        ssd_category_evidence=None,
        alias_relation=None,
        body_sha256=None,
    )


class TestRoundTrip:
    @pytest.mark.parametrize("mpn", [BASE, BASER, BASET])
    def test_established_round_trip_all_request_forms(self, mpn: str) -> None:
        result = _established_result(mpn)
        payload = encode_micron_alias_snapshot(result)
        decoded = decode_micron_alias_snapshot(payload, schema_version=1)
        assert decoded == result

    def test_established_round_trip_preserves_every_field(self) -> None:
        result = _established_result()
        payload = encode_micron_alias_snapshot(result)
        decoded = decode_micron_alias_snapshot(payload)
        assert decoded.status is MicronAliasEligibilityStatus.ESTABLISHED
        assert decoded.request == result.request
        assert decoded.lookup_base_candidate == BASE
        assert decoded.manufacturer == MICRON_7500_MANUFACTURER
        assert decoded.category == MICRON_7500_CATEGORY
        assert decoded.matched_base_mpn == BASE
        assert decoded.body_sha256 == FIXTURE_SHA256
        assert decoded.alias_relation is not None
        assert decoded.alias_relation.base_mpn == BASE
        assert decoded.alias_relation.aliases == (BASE, BASET)
        assert decoded.part_number_match is not None
        assert decoded.part_number_match.match_type.value == "EXACT"
        assert decoded.ssd_category_evidence is not None
        assert decoded.ssd_category_evidence.attr_id == "is-ssd"
        assert decoded.ssd_category_evidence.attr_value is True
        assert decoded.retrieved_at == FIXED_AT

    def test_bounded_non_established_round_trip(self) -> None:
        result = _bounded_result()
        payload = encode_micron_alias_snapshot(result)
        assert decode_micron_alias_snapshot(payload, schema_version=1) == result

    def test_invalid_lookup_base_round_trip(self) -> None:
        result = _degenerate_result()
        payload = encode_micron_alias_snapshot(result)
        decoded = decode_micron_alias_snapshot(payload, schema_version=1)
        assert decoded == result
        assert decoded.status is MicronAliasEligibilityStatus.INVALID_LOOKUP_BASE

    def test_payload_is_json_serializable_and_bounded(self) -> None:
        import json

        payload = encode_micron_alias_snapshot(_established_result())
        # Bounded provenance: the catalog body itself never appears.
        text = json.dumps(payload)
        assert "7500 4TB U.3 SSD" not in text
        assert "sequential_read" not in text
        assert payload["body_sha256"] == FIXTURE_SHA256
        assert "details" not in payload

    def test_retrieved_at_persisted_at_second_precision(self) -> None:
        # Repository codec convention (4D-B/fx): datetimes persist in
        # deterministic second-precision UTC form.
        micros = datetime(2026, 9, 22, 23, 20, 25, 123456, tzinfo=UTC)
        result = _established_result()
        from dataclasses import replace

        result = replace(result, retrieved_at=micros)
        payload = encode_micron_alias_snapshot(result)
        assert payload["retrieved_at"] == "2026-09-22T23:20:25+00:00"
        decoded = decode_micron_alias_snapshot(payload, schema_version=1)
        assert decoded.retrieved_at == datetime(2026, 9, 22, 23, 20, 25, tzinfo=UTC)


class TestEncodeContract:
    def test_rejects_non_result_input(self) -> None:
        with pytest.raises(MicronAliasCodecError):
            encode_micron_alias_snapshot({"not": "a result"})  # type: ignore[arg-type]


class TestDecodeStructure:
    def test_non_dict_payload_rejected(self) -> None:
        for bad in ([], "text", None, 42):
            with pytest.raises(MicronAliasCodecError):
                decode_micron_alias_snapshot(bad)  # type: ignore[arg-type]

    def test_extra_top_level_key_rejected(self) -> None:
        payload = encode_micron_alias_snapshot(_established_result())
        payload["injected"] = True
        with pytest.raises(MicronAliasCodecError):
            decode_micron_alias_snapshot(payload, schema_version=1)

    def test_missing_top_level_key_rejected(self) -> None:
        payload = encode_micron_alias_snapshot(_established_result())
        del payload["body_sha256"]
        with pytest.raises(MicronAliasCodecError):
            decode_micron_alias_snapshot(payload, schema_version=1)

    def test_unsupported_schema_version_rejected(self) -> None:
        payload = encode_micron_alias_snapshot(_established_result())
        payload["schema_version"] = 2
        with pytest.raises(MicronAliasCodecError):
            decode_micron_alias_snapshot(payload, schema_version=2)

    def test_model_and_payload_version_disagreement_rejected(self) -> None:
        payload = encode_micron_alias_snapshot(_established_result())
        with pytest.raises(MicronAliasCodecError):
            decode_micron_alias_snapshot(payload, schema_version=2)

    def test_unknown_status_rejected(self) -> None:
        payload = encode_micron_alias_snapshot(_established_result())
        payload["status"] = "TOTALLY_NEW_STATUS"
        with pytest.raises(MicronAliasCodecError):
            decode_micron_alias_snapshot(payload, schema_version=1)

    @pytest.mark.parametrize("field", ["policy_id", "manufacturer", "status"])
    def test_non_string_required_fields_rejected(self, field: str) -> None:
        payload = encode_micron_alias_snapshot(_established_result())
        payload[field] = 12345
        with pytest.raises(MicronAliasCodecError):
            decode_micron_alias_snapshot(payload, schema_version=1)

    def test_bad_datetime_rejected(self) -> None:
        payload = encode_micron_alias_snapshot(_bounded_result())
        payload["retrieved_at"] = "22/09/2026 12:00"
        with pytest.raises(MicronAliasCodecError):
            decode_micron_alias_snapshot(payload, schema_version=1)

    def test_non_utc_datetime_rejected(self) -> None:
        payload = encode_micron_alias_snapshot(_bounded_result())
        payload["retrieved_at"] = "2026-09-22T23:20:25+02:00"
        with pytest.raises(MicronAliasCodecError):
            decode_micron_alias_snapshot(payload, schema_version=1)


class TestDecodeTamperResistant:
    """A tampered persisted payload must never construct authority."""

    def test_established_claim_with_foreign_policy_rejected(self) -> None:
        payload = encode_micron_alias_snapshot(_established_result())
        payload["policy_id"] = "seagate-nytro-v1"
        with pytest.raises(MicronAliasCodecError):
            decode_micron_alias_snapshot(payload, schema_version=1)

    def test_established_claim_with_foreign_manufacturer_rejected(self) -> None:
        payload = encode_micron_alias_snapshot(_established_result())
        payload["manufacturer"] = "Seagate"
        with pytest.raises(MicronAliasCodecError):
            decode_micron_alias_snapshot(payload, schema_version=1)

    def test_established_claim_with_foreign_category_rejected(self) -> None:
        payload = encode_micron_alias_snapshot(_established_result())
        payload["category"] = "Memory"
        with pytest.raises(MicronAliasCodecError):
            decode_micron_alias_snapshot(payload, schema_version=1)

    def test_established_claim_with_escaped_final_url_rejected(self) -> None:
        payload = encode_micron_alias_snapshot(_established_result())
        payload["fetched_final_url"] = "https://evil.example/catalog.json"
        with pytest.raises(MicronAliasCodecError):
            decode_micron_alias_snapshot(payload, schema_version=1)

    def test_established_claim_with_scheme_downgrade_rejected(self) -> None:
        payload = encode_micron_alias_snapshot(_established_result())
        payload["fetched_final_url"] = (
            "http://" + MICRON_7500_REQUESTED_CATALOG_URL[len("https://"):]
        )
        with pytest.raises(MicronAliasCodecError):
            decode_micron_alias_snapshot(payload, schema_version=1)

    def test_established_claim_with_synthesized_base_rejected(self) -> None:
        payload = encode_micron_alias_snapshot(_established_result())
        payload["matched_base_mpn"] = f"{BASE}X"
        with pytest.raises(MicronAliasCodecError):
            decode_micron_alias_snapshot(payload, schema_version=1)

    def test_established_claim_with_foreign_alias_rejected(self) -> None:
        payload = encode_micron_alias_snapshot(_established_result())
        payload["alias_relation"]["aliases"] = ["EVIL-1", "EVIL-2"]
        with pytest.raises(MicronAliasCodecError):
            decode_micron_alias_snapshot(payload, schema_version=1)

    def test_established_claim_with_wrong_requested_binding_rejected(self) -> None:
        payload = encode_micron_alias_snapshot(_established_result())
        payload["requested_mpn"] = BASET  # relation binds BASER
        with pytest.raises(MicronAliasCodecError):
            decode_micron_alias_snapshot(payload, schema_version=1)

    def test_bounded_status_upgraded_to_established_rejected(self) -> None:
        payload = encode_micron_alias_snapshot(_bounded_result())
        payload["status"] = "ESTABLISHED"
        with pytest.raises(MicronAliasCodecError):
            decode_micron_alias_snapshot(payload, schema_version=1)

    def test_established_downgraded_keeps_authority_rejected(self) -> None:
        # ESTABLISHED provenance with a non-established status still carries
        # the authority fields -> the contract refuses it.
        payload = encode_micron_alias_snapshot(_established_result())
        payload["status"] = "NO_AUTHORITY_MATCH"
        with pytest.raises(MicronAliasCodecError):
            decode_micron_alias_snapshot(payload, schema_version=1)

    def test_authority_injected_into_bounded_status_rejected(self) -> None:
        payload = encode_micron_alias_snapshot(_bounded_result())
        payload["manufacturer"] = "Micron"
        payload["category"] = "SSD"
        with pytest.raises(MicronAliasCodecError):
            decode_micron_alias_snapshot(payload, schema_version=1)

    def test_no_requested_mpn_with_present_mpn_rejected(self) -> None:
        # NO_REQUESTED_MPN means the MPN is truly absent.
        result = MicronAliasEligibilityResult(
            status=MicronAliasEligibilityStatus.NO_REQUESTED_MPN,
            request=ResearchRequest(manufacturer_part_number="", description="x"),
            lookup_base_candidate=None,
            policy_id=MICRON_7500_POLICY_ID,
            manufacturer=None,
            category=None,
            requested_source_url=None,
            fetched_final_url=None,
            retrieved_at=None,
            source_name=None,
            matched_base_mpn=None,
            part_number_match=None,
            ssd_category_evidence=None,
            alias_relation=None,
            body_sha256=None,
        )
        payload = encode_micron_alias_snapshot(result)
        payload["requested_mpn"] = "AB"
        with pytest.raises(MicronAliasCodecError):
            decode_micron_alias_snapshot(payload, schema_version=1)

    def test_invalid_lookup_base_with_absent_mpn_rejected(self) -> None:
        # INVALID_LOOKUP_BASE means the MPN was present but unusable.
        payload = encode_micron_alias_snapshot(_degenerate_result())
        payload["requested_mpn"] = ""
        payload["description"] = "codec"
        with pytest.raises(MicronAliasCodecError):
            decode_micron_alias_snapshot(payload, schema_version=1)

    def test_body_sha_tamper_rejected(self) -> None:
        payload = encode_micron_alias_snapshot(_established_result())
        payload["body_sha256"] = "0" * 64
        # The contract does not re-hash the body (it is not persisted); a
        # syntactically valid but foreign SHA is accepted by the contract
        # itself. A malformed SHA must still be rejected.
        decoded = decode_micron_alias_snapshot(payload, schema_version=1)
        assert decoded.body_sha256 == "0" * 64
        payload["body_sha256"] = "zz" * 32
        with pytest.raises(MicronAliasCodecError):
            decode_micron_alias_snapshot(payload, schema_version=1)

    def test_match_nested_extra_key_rejected(self) -> None:
        payload = encode_micron_alias_snapshot(_established_result())
        payload["part_number_match"]["injected"] = True
        with pytest.raises(MicronAliasCodecError):
            decode_micron_alias_snapshot(payload, schema_version=1)

    def test_match_missing_key_rejected(self) -> None:
        payload = encode_micron_alias_snapshot(_established_result())
        del payload["part_number_match"]["match_type"]
        with pytest.raises(MicronAliasCodecError):
            decode_micron_alias_snapshot(payload, schema_version=1)

    def test_unknown_match_type_rejected(self) -> None:
        payload = encode_micron_alias_snapshot(_established_result())
        payload["part_number_match"]["match_type"] = "PARTIAL"
        with pytest.raises(MicronAliasCodecError):
            decode_micron_alias_snapshot(payload, schema_version=1)

    def test_relation_aliases_not_a_list_rejected(self) -> None:
        payload = encode_micron_alias_snapshot(_established_result())
        payload["alias_relation"]["aliases"] = "NOT-A-LIST"
        with pytest.raises(MicronAliasCodecError):
            decode_micron_alias_snapshot(payload, schema_version=1)

    def test_ssd_evidence_value_not_boolean_rejected(self) -> None:
        payload = encode_micron_alias_snapshot(_established_result())
        payload["ssd_category_evidence"]["attr_value"] = "true"
        with pytest.raises(MicronAliasCodecError):
            decode_micron_alias_snapshot(payload, schema_version=1)

    def test_ssd_evidence_wrong_id_rejected(self) -> None:
        payload = encode_micron_alias_snapshot(_established_result())
        payload["ssd_category_evidence"]["attr_id"] = "is-memory"
        with pytest.raises(MicronAliasCodecError):
            decode_micron_alias_snapshot(payload, schema_version=1)

    def test_request_binding_mismatch_rejected(self) -> None:
        # A payload whose request does not re-derive its candidate fails.
        payload = encode_micron_alias_snapshot(_established_result())
        payload["lookup_base_candidate"] = "WRONG-CANDIDATE"
        with pytest.raises(MicronAliasCodecError):
            decode_micron_alias_snapshot(payload, schema_version=1)
