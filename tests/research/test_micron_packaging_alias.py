"""Research-core tests for the Micron 7500 packaging-alias contracts
(PRODUCT-INTEL.4D-D).

Covers: reviewed v1 policy constants, lookup-base derivation (including the
distinct degenerate-input handling), the fail-closed catalog parser against
the real 4D-D-PRE2 recorded fixture, SSD category evidence, the origin
boundary, the customer-defined alias relation invariants, reference
labeling, the eligibility-status vocabulary (including the distinct
INVALID_LOOKUP_BASE state), and the self-validating eligibility result
contract.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import (
    ESTABLISHED_MATCH_TYPES,
    IdentityMatchType,
)
from product_intelligence.research.identity import compare_part_numbers
from product_intelligence.research.micron_packaging_alias import (
    MICRON_7500_APPROVED_ORIGIN,
    MICRON_7500_CATEGORY,
    MICRON_7500_MANUFACTURER,
    MICRON_7500_POLICY_ID,
    MICRON_7500_REQUESTED_CATALOG_URL,
    MICRON_7500_SOURCE_NAME,
    PACKAGING_ALIAS_SUFFIXES,
    SSD_EVIDENCE_ATTR_ID,
    MicronAliasEligibilityResult,
    MicronAliasEligibilityStatus,
    MicronCatalogAttr,
    MicronCatalogParseError,
    MicronPackagingAliasRelation,
    MicronSsdCategoryEvidence,
    build_packaging_alias_relation,
    derive_lookup_base_candidate,
    extract_micron_7500_catalog_records,
    find_alias_reference,
    matched_ssd_category_evidence,
    packaging_alias_family,
    url_within_origin,
    verify_ssd_category_evidence,
)

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


# ---------------------------------------------------------------------------
# Reviewed v1 policy constants (pinned)
# ---------------------------------------------------------------------------


class TestPolicyConstants:
    def test_policy_id_is_pinned(self) -> None:
        assert MICRON_7500_POLICY_ID == "micron-7500-ssd-part-catalog-v1"

    def test_manufacturer_and_category_are_pinned(self) -> None:
        assert MICRON_7500_MANUFACTURER == "Micron"
        assert MICRON_7500_CATEGORY == "SSD"

    def test_requested_catalog_url_is_the_reviewed_pre2_endpoint(self) -> None:
        assert MICRON_7500_REQUESTED_CATALOG_URL == (
            "https://www.micron.com/content/micron/us/en/products/storage/ssd/"
            "data-center-ssd/7500-ssd/part-catalog/"
            "_jcr_content.products.json/getpartcatalog/storage/7500-ssd/-/en_US"
        )

    def test_approved_origin_is_pinned(self) -> None:
        assert MICRON_7500_APPROVED_ORIGIN == "https://www.micron.com"

    def test_source_name_is_pinned(self) -> None:
        assert MICRON_7500_SOURCE_NAME == "Micron 7500 SSD catalog"

    def test_suffix_set_is_exactly_uppercase_final_r_and_t(self) -> None:
        assert PACKAGING_ALIAS_SUFFIXES == frozenset({"R", "T"})
        assert SSD_EVIDENCE_ATTR_ID == "is-ssd"


# ---------------------------------------------------------------------------
# Lookup base candidate derivation
# ---------------------------------------------------------------------------


class TestDeriveLookupBaseCandidate:
    @pytest.mark.parametrize("mpn", [None, ""])
    def test_missing_or_empty_mpn_is_none(self, mpn: "str | None") -> None:
        assert derive_lookup_base_candidate(mpn) is None

    def test_base_request_is_its_own_candidate(self) -> None:
        assert derive_lookup_base_candidate(BASE) == BASE

    @pytest.mark.parametrize("mpn", [BASER, BASET])
    def test_final_uppercase_r_t_strips_to_base(self, mpn: str) -> None:
        assert derive_lookup_base_candidate(mpn) == BASE

    @pytest.mark.parametrize(
        ("mpn", "expected"),
        [
            ("ABR", "AB"),
            ("ABT", "AB"),
            ("ABC-R", "ABC-"),
            ("ABC-T", "ABC-"),
        ],
    )
    def test_generic_final_suffix_strips(self, mpn: str, expected: str) -> None:
        # Exactly one final character is stripped; the remainder is the
        # candidate verbatim (no further rewriting).
        assert derive_lookup_base_candidate(mpn) == expected

    @pytest.mark.parametrize("mpn", ["ABr", "ABt", "ABC-r", "ABC-t"])
    def test_lowercase_final_r_t_does_not_invoke_the_rule(self, mpn: str) -> None:
        # The full MPN is the candidate: lowercase r/t is content here,
        # not the customer suffix.
        assert derive_lookup_base_candidate(mpn) == mpn

    @pytest.mark.parametrize("mpn", ["R", "T", "-R", "-T", "----", "_"])
    def test_degenerate_inputs_have_no_usable_base(self, mpn: str) -> None:
        # Non-empty request whose suffix derivation (or content check)
        # leaves no usable lookup base: fail safe to None.
        assert derive_lookup_base_candidate(mpn) is None

    def test_non_string_raises_type_error(self) -> None:
        with pytest.raises(TypeError):
            derive_lookup_base_candidate(1234)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Catalog parser (real PRE2 fixture + fail-closed corruption)
# ---------------------------------------------------------------------------


def _load_fixture_body() -> str:
    return CATALOG_FIXTURE.read_bytes().decode("utf-8")


class TestCatalogParserRealFixture:
    def test_fixture_sha256_matches_pre2_evidence(self) -> None:
        import hashlib

        body = CATALOG_FIXTURE.read_bytes()
        assert hashlib.sha256(body).hexdigest() == FIXTURE_SHA256

    def test_all_24_rows_parse_in_published_order(self) -> None:
        records = extract_micron_7500_catalog_records(_load_fixture_body())
        assert len(records) == 24
        document = json.loads(_load_fixture_body())
        assert [r.part_number for r in records] == [
            row["part-number"] for row in document["details"]
        ]

    def test_target_row_carries_exact_base_and_ssd_evidence(self) -> None:
        records = extract_micron_7500_catalog_records(_load_fixture_body())
        target = next(r for r in records if r.part_number == BASE)
        assert target.part_name == "7500 4TB U.3 SSD"
        assert verify_ssd_category_evidence(target) is True
        evidence = matched_ssd_category_evidence(target)
        assert evidence.attr_id == "is-ssd"
        assert evidence.value is True
        assert evidence.name == "SSD"

    def test_no_r_or_t_row_exists_in_the_catalog(self) -> None:
        records = extract_micron_7500_catalog_records(_load_fixture_body())
        for record in records:
            assert record.part_number not in (BASER, BASET)

    def test_rows_preserve_all_published_attrs_verbatim(self) -> None:
        records = extract_micron_7500_catalog_records(_load_fixture_body())
        document = json.loads(_load_fixture_body())
        target = next(r for r in records if r.part_number == BASE)
        raw = next(row for row in document["details"] if row["part-number"] == BASE)
        assert [a.attr_id for a in target.attr] == [a["id"] for a in raw["attr"]]
        assert [a.value for a in target.attr] == [a["value"] for a in raw["attr"]]


class TestCatalogParserFailClosed:
    @pytest.mark.parametrize(
        "body",
        [
            "not json at all",
            "[1, 2, 3]",
            '"a string"',
            "null",
        ],
    )
    def test_non_json_or_non_mapping_body_raises(self, body: str) -> None:
        with pytest.raises(MicronCatalogParseError):
            extract_micron_7500_catalog_records(body)

    def test_missing_details_raises(self) -> None:
        with pytest.raises(MicronCatalogParseError):
            extract_micron_7500_catalog_records(json.dumps({"other": []}))

    def test_details_not_a_list_raises(self) -> None:
        with pytest.raises(MicronCatalogParseError):
            extract_micron_7500_catalog_records(
                json.dumps({"details": {"a": 1}})
            )

    def test_row_not_a_mapping_raises(self) -> None:
        with pytest.raises(MicronCatalogParseError):
            extract_micron_7500_catalog_records(
                json.dumps({"details": [{"part-number": "AB"}, 42]})
            )

    def test_rows_without_usable_part_number_are_skipped(self) -> None:
        body = json.dumps(
            {
                "details": [
                    {"part-number": "", "part-name": "empty"},
                    {"part-number": 1234, "part-name": "not a string"},
                    {"part-name": "no part number at all"},
                    {"part-number": "AB", "part-name": "AB product"},
                ]
            }
        )
        records = extract_micron_7500_catalog_records(body)
        assert [r.part_number for r in records] == ["AB"]

    def test_non_string_part_name_raises(self) -> None:
        with pytest.raises(MicronCatalogParseError):
            extract_micron_7500_catalog_records(
                json.dumps({"details": [{"part-number": "AB", "part-name": 7}]})
            )

    def test_attr_not_a_list_raises(self) -> None:
        with pytest.raises(MicronCatalogParseError):
            extract_micron_7500_catalog_records(
                json.dumps(
                    {"details": [{"part-number": "AB", "attr": "nope"}]}
                )
            )

    def test_attr_entry_not_a_mapping_raises(self) -> None:
        with pytest.raises(MicronCatalogParseError):
            extract_micron_7500_catalog_records(
                json.dumps(
                    {"details": [{"part-number": "AB", "attr": [42]}]}
                )
            )

    def test_attr_name_not_a_string_raises(self) -> None:
        with pytest.raises(MicronCatalogParseError):
            extract_micron_7500_catalog_records(
                json.dumps(
                    {
                        "details": [
                            {
                                "part-number": "AB",
                                "attr": [{"name": 1, "id": "x", "value": True}],
                            }
                        ]
                    }
                )
            )

    def test_attr_id_not_a_string_raises(self) -> None:
        with pytest.raises(MicronCatalogParseError):
            extract_micron_7500_catalog_records(
                json.dumps(
                    {
                        "details": [
                            {
                                "part-number": "AB",
                                "attr": [{"name": "n", "id": 5, "value": True}],
                            }
                        ]
                    }
                )
            )

    def test_attr_value_non_scalar_raises(self) -> None:
        for bad in ([True], {"nested": True}):
            with pytest.raises(MicronCatalogParseError):
                extract_micron_7500_catalog_records(
                    json.dumps(
                        {
                            "details": [
                                {
                                    "part-number": "AB",
                                    "attr": [
                                        {"name": "n", "id": "x", "value": bad}
                                    ],
                                }
                            ]
                        }
                    )
                )

    def test_attr_entries_may_omit_name_and_value(self) -> None:
        records = extract_micron_7500_catalog_records(
            json.dumps(
                {"details": [{"part-number": "AB", "attr": [{"id": "is-ssd"}]}]}
            )
        )
        entry = records[0].attr[0]
        assert entry.name is None
        assert entry.value is None

    def test_non_string_body_raises_type_error(self) -> None:
        with pytest.raises(TypeError):
            extract_micron_7500_catalog_records(b"bytes")  # type: ignore[arg-type]


class TestMicronCatalogRecordContract:
    def test_empty_part_number_rejected(self) -> None:
        from product_intelligence.research.micron_packaging_alias import (
            MicronCatalogRecord,
        )

        with pytest.raises(ValueError):
            MicronCatalogRecord(part_number="", part_name="x", attr=())

    def test_non_string_part_name_rejected(self) -> None:
        from product_intelligence.research.micron_packaging_alias import (
            MicronCatalogRecord,
        )

        with pytest.raises(TypeError):
            MicronCatalogRecord(  # type: ignore[arg-type]
                part_number="AB", part_name=7, attr=()
            )

    def test_non_tuple_attr_rejected(self) -> None:
        from product_intelligence.research.micron_packaging_alias import (
            MicronCatalogRecord,
        )

        with pytest.raises(TypeError):
            MicronCatalogRecord(  # type: ignore[arg-type]
                part_number="AB", part_name="x", attr=[MicronCatalogAttr("n", "i", 1)]
            )

    def test_attr_entry_wrong_value_type_rejected(self) -> None:
        with pytest.raises(TypeError):
            MicronCatalogAttr(name="n", attr_id="i", value=[1])  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# SSD category evidence
# ---------------------------------------------------------------------------


def _record_with_is_ssd(*values: object) -> "object":
    from product_intelligence.research.micron_packaging_alias import (
        MicronCatalogRecord,
    )

    attrs = tuple(
        MicronCatalogAttr(name="SSD" if v is True else None, attr_id="is-ssd", value=v)
        for v in values
    )
    return MicronCatalogRecord(part_number="AB", part_name="AB", attr=attrs)


class TestVerifySsdCategoryEvidence:
    def test_no_is_ssd_entries_is_false(self) -> None:
        from product_intelligence.research.micron_packaging_alias import (
            MicronCatalogRecord,
        )

        record = MicronCatalogRecord(
            part_number="AB",
            part_name="AB",
            attr=(MicronCatalogAttr(name="Capacity", attr_id="capacity", value="1GB"),),
        )
        assert verify_ssd_category_evidence(record) is False

    def test_single_true_is_true(self) -> None:
        assert verify_ssd_category_evidence(_record_with_is_ssd(True)) is True

    @pytest.mark.parametrize("value", [False, "true", 1, 0, None, "True"])
    def test_non_boolean_true_values_are_false(self, value: object) -> None:
        assert verify_ssd_category_evidence(_record_with_is_ssd(value)) is False

    def test_multiple_all_true_is_true(self) -> None:
        assert verify_ssd_category_evidence(_record_with_is_ssd(True, True)) is True

    def test_multiple_with_one_false_is_false(self) -> None:
        assert verify_ssd_category_evidence(_record_with_is_ssd(True, False)) is False

    def test_wrong_record_type_raises(self) -> None:
        with pytest.raises(TypeError):
            verify_ssd_category_evidence("not a record")  # type: ignore[arg-type]


class TestMatchedSsdCategoryEvidence:
    def test_returns_the_positive_entry(self) -> None:
        record = _record_with_is_ssd(True)
        evidence = matched_ssd_category_evidence(record)  # type: ignore[arg-type]
        assert evidence.attr_id == "is-ssd"
        assert evidence.value is True

    def test_raises_when_no_positive_entry_exists(self) -> None:
        from product_intelligence.research.micron_packaging_alias import (
            MicronCatalogRecord,
        )

        no_entries = MicronCatalogRecord(part_number="AB", part_name="AB", attr=())
        with pytest.raises(ValueError):
            matched_ssd_category_evidence(no_entries)
        # An all-negative record also carries no usable positive evidence.
        with pytest.raises(ValueError):
            matched_ssd_category_evidence(_record_with_is_ssd(False))  # type: ignore[arg-type]

    def test_returns_first_positive_entry_when_present(self) -> None:
        # The execution flow always verifies first (verify requires ALL
        # entries True); matched returns the first positive entry.
        evidence = matched_ssd_category_evidence(
            _record_with_is_ssd(True, False)  # type: ignore[arg-type]
        )
        assert evidence.value is True


# ---------------------------------------------------------------------------
# Origin boundary
# ---------------------------------------------------------------------------


class TestUrlWithinOrigin:
    def test_same_origin_different_path_is_inside(self) -> None:
        assert (
            url_within_origin(
                "https://www.micron.com/other/path?q=1", MICRON_7500_APPROVED_ORIGIN
            )
            is True
        )

    def test_scheme_downgrade_is_outside(self) -> None:
        assert (
            url_within_origin(
                "http://www.micron.com/path", MICRON_7500_APPROVED_ORIGIN
            )
            is False
        )

    def test_host_escape_is_outside(self) -> None:
        assert (
            url_within_origin(
                "https://www.micron.com.evil.com/path", MICRON_7500_APPROVED_ORIGIN
            )
            is False
        )
        assert (
            url_within_origin(
                "https://evil.micron.com/path", MICRON_7500_APPROVED_ORIGIN
            )
            is False
        )

    def test_non_default_port_is_outside(self) -> None:
        assert (
            url_within_origin(
                "https://www.micron.com:8443/path", MICRON_7500_APPROVED_ORIGIN
            )
            is False
        )

    def test_explicit_default_port_is_inside(self) -> None:
        assert (
            url_within_origin(
                "https://www.micron.com:443/path", MICRON_7500_APPROVED_ORIGIN
            )
            is True
        )

    def test_non_http_schemes_are_outside(self) -> None:
        for url in ("ftp://www.micron.com/x", "file:///tmp/x", "//www.micron.com/x"):
            assert url_within_origin(url, MICRON_7500_APPROVED_ORIGIN) is False

    def test_unparseable_or_non_string_fails_closed(self) -> None:
        assert url_within_origin("", MICRON_7500_APPROVED_ORIGIN) is False
        assert url_within_origin(None, MICRON_7500_APPROVED_ORIGIN) is False  # type: ignore[arg-type]
        assert url_within_origin("https://www.micron.com", 42) is False  # type: ignore[arg-type]

    def test_port_pinned_origin_matches_only_that_port(self) -> None:
        origin = "https://internal.example:8001"
        assert url_within_origin("https://internal.example:8001/x", origin) is True
        assert url_within_origin("https://internal.example/x", origin) is False


# ---------------------------------------------------------------------------
# Packaging alias family + relation
# ---------------------------------------------------------------------------


class TestPackagingAliasFamily:
    def test_family_shape(self) -> None:
        assert packaging_alias_family(BASE) == (BASE, BASER, BASET)

    @pytest.mark.parametrize("base", ["", None, 7])
    def test_invalid_base_rejected(self, base: object) -> None:
        with pytest.raises((ValueError, TypeError)):
            packaging_alias_family(base)  # type: ignore[arg-type]


class TestBuildPackagingAliasRelation:
    def test_request_base_excludes_itself(self) -> None:
        relation = build_packaging_alias_relation(BASE, BASE)
        assert relation.requested_mpn == BASE
        assert relation.base_mpn == BASE
        assert relation.aliases == (BASER, BASET)

    def test_request_r_variant(self) -> None:
        relation = build_packaging_alias_relation(BASER, BASE)
        assert relation.aliases == (BASE, BASET)

    def test_request_t_variant(self) -> None:
        relation = build_packaging_alias_relation(BASET, BASE)
        assert relation.aliases == (BASE, BASER)

    def test_case_variant_request_is_allowed_by_2a(self) -> None:
        # 2A NORMALIZED_EXACT: a case variant of the requested form still
        # establishes to exactly one family member.
        relation = build_packaging_alias_relation(BASE.lower(), BASE)
        assert relation.aliases == (BASER, BASET)

    def test_unrelated_request_rejected(self) -> None:
        with pytest.raises(ValueError):
            build_packaging_alias_relation("EVIL-MPN", BASE)

    def test_lower_r_request_rejected_by_derivation_consistency(self) -> None:
        # Establishes (NORMALIZED_EXACT) to the R family member, but the
        # customer rule (uppercase final only) does not derive the base from
        # it — mechanically inconsistent, rejected.
        with pytest.raises(ValueError):
            build_packaging_alias_relation("ABr", "AB")


class TestRelationInvariants:
    def _valid_relation(self) -> MicronPackagingAliasRelation:
        return build_packaging_alias_relation(BASER, BASE)

    def test_duplicate_aliases_rejected(self) -> None:
        with pytest.raises(ValueError):
            MicronPackagingAliasRelation(
                requested_mpn=BASER, base_mpn=BASE, aliases=(BASE, BASE)
            )

    def test_alias_outside_family_rejected(self) -> None:
        with pytest.raises(ValueError):
            MicronPackagingAliasRelation(
                requested_mpn=BASER, base_mpn=BASE, aliases=(BASE, "EVIL")
            )

    def test_swapped_alias_order_rejected(self) -> None:
        # Deterministic family order: base, base+R, base+T.
        with pytest.raises(ValueError):
            MicronPackagingAliasRelation(
                requested_mpn=BASE, base_mpn=BASE, aliases=(BASET, BASER)
            )

    def test_missing_alias_rejected(self) -> None:
        with pytest.raises(ValueError):
            MicronPackagingAliasRelation(
                requested_mpn=BASE, base_mpn=BASE, aliases=(BASER,)
            )

    def test_empty_requested_or_base_rejected(self) -> None:
        with pytest.raises(ValueError):
            MicronPackagingAliasRelation(
                requested_mpn="", base_mpn=BASE, aliases=(BASER, BASET)
            )
        with pytest.raises(ValueError):
            MicronPackagingAliasRelation(
                requested_mpn=BASE, base_mpn="", aliases=(BASER, BASET)
            )

    def test_non_tuple_aliases_rejected(self) -> None:
        with pytest.raises(TypeError):
            MicronPackagingAliasRelation(  # type: ignore[arg-type]
                requested_mpn=BASER, base_mpn=BASE, aliases=[BASE, BASET]
            )

    def test_reconstructed_relation_round_trips(self) -> None:
        relation = self._valid_relation()
        rebuilt = MicronPackagingAliasRelation(
            requested_mpn=relation.requested_mpn,
            base_mpn=relation.base_mpn,
            aliases=relation.aliases,
        )
        assert rebuilt == relation


# ---------------------------------------------------------------------------
# Reference labeling
# ---------------------------------------------------------------------------


class TestFindAliasReference:
    def test_exact_alias_is_found(self) -> None:
        assert find_alias_reference((BASE, BASET), BASE) == BASE
        assert find_alias_reference((BASE, BASET), BASER) is None

    def test_case_variant_alias_is_found_via_2a(self) -> None:
        assert find_alias_reference((BASE, BASET), BASE.lower()) == BASE
        assert find_alias_reference((BASE, BASET), BASET.lower()) == BASET

    def test_requested_mpn_is_not_a_target(self) -> None:
        # The identifiers are the ALIASES only; the requested form itself is
        # never among them (construction excludes it).
        assert find_alias_reference((BASE, BASET), "SOME-OTHER") is None

    def test_none_or_empty_published_value(self) -> None:
        assert find_alias_reference((BASE, BASET), None) is None
        assert find_alias_reference((BASE, BASET), "") is None

    def test_non_string_published_value_raises(self) -> None:
        with pytest.raises(TypeError):
            find_alias_reference((BASE, BASET), 42)  # type: ignore[arg-type]

    def test_string_passed_as_identifiers_raises(self) -> None:
        with pytest.raises(TypeError):
            find_alias_reference("NOT-ITERABLE-AS-ID", BASE)  # type: ignore[arg-type]

    def test_duplicate_identifiers_rejected(self) -> None:
        with pytest.raises(ValueError):
            find_alias_reference((BASE, BASE), BASE)

    def test_empty_identifier_rejected(self) -> None:
        with pytest.raises(ValueError):
            find_alias_reference((BASE, ""), BASE)

    def test_first_matching_identifier_wins(self) -> None:
        # Both identifiers cannot be 2A-equivalent to one published value,
        # so "first in order" is exercised with distinct matches.
        assert find_alias_reference((BASE, BASET), BASET) == BASET
        assert find_alias_reference((BASE, BASET), BASE) == BASE


# ---------------------------------------------------------------------------
# SSD evidence contract
# ---------------------------------------------------------------------------


class TestSsdCategoryEvidenceContract:
    def test_name_may_be_none_authority_is_id_plus_boolean(self) -> None:
        evidence = MicronSsdCategoryEvidence(
            attr_name=None, attr_id="is-ssd", attr_value=True
        )
        assert evidence.attr_name is None
        assert evidence.attr_id == "is-ssd"
        assert evidence.attr_value is True

    def test_name_may_be_the_published_display_label(self) -> None:
        evidence = MicronSsdCategoryEvidence(
            attr_name="SSD", attr_id="is-ssd", attr_value=True
        )
        assert evidence.attr_name == "SSD"

    @pytest.mark.parametrize("name", ["", 5, ["n"]])
    def test_bad_name_rejected(self, name: object) -> None:
        with pytest.raises(ValueError):
            MicronSsdCategoryEvidence(
                attr_name=name, attr_id="is-ssd", attr_value=True  # type: ignore[arg-type]
            )

    def test_wrong_attr_id_rejected(self) -> None:
        with pytest.raises(ValueError):
            MicronSsdCategoryEvidence(
                attr_name="SSD", attr_id="other-id", attr_value=True
            )

    @pytest.mark.parametrize("value", [False, 1, 0, "true", None])
    def test_attr_value_must_be_exactly_boolean_true(self, value: object) -> None:
        with pytest.raises(ValueError):
            MicronSsdCategoryEvidence(
                attr_name="SSD", attr_id="is-ssd", attr_value=value  # type: ignore[arg-type]
            )


# ---------------------------------------------------------------------------
# Eligibility result contract (self-validation)
# ---------------------------------------------------------------------------


def _established_result() -> MicronAliasEligibilityResult:
    """A valid ESTABLISHED result built from the real PRE2 fixture."""
    from product_intelligence.research.micron_packaging_alias import (
        MicronCatalogRecord,
    )
    import hashlib

    body = _load_fixture_body()
    records = extract_micron_7500_catalog_records(body)
    record = next(r for r in records if r.part_number == BASE)
    request = ResearchRequest(manufacturer_part_number=BASER, description="test")
    match = compare_part_numbers(BASE, BASE)
    relation = build_packaging_alias_relation(BASER, BASE)
    evidence = matched_ssd_category_evidence(record)
    return MicronAliasEligibilityResult(
        status=MicronAliasEligibilityStatus.ESTABLISHED,
        request=request,
        lookup_base_candidate=BASE,
        policy_id=MICRON_7500_POLICY_ID,
        manufacturer=MICRON_7500_MANUFACTURER,
        category=MICRON_7500_CATEGORY,
        requested_source_url=MICRON_7500_REQUESTED_CATALOG_URL,
        fetched_final_url=MICRON_7500_REQUESTED_CATALOG_URL,
        retrieved_at=FIXED_AT,
        source_name=MICRON_7500_SOURCE_NAME,
        matched_base_mpn=BASE,
        part_number_match=match,
        ssd_category_evidence=MicronSsdCategoryEvidence(
            attr_name=evidence.name, attr_id=evidence.attr_id, attr_value=True
        ),
        alias_relation=relation,
        body_sha256=hashlib.sha256(body.encode("utf-8")).hexdigest(),
    )


def _non_established_result(
    status: MicronAliasEligibilityStatus,
    mpn: str = BASE,
    **overrides: object,
) -> MicronAliasEligibilityResult:
    kwargs: dict = dict(
        status=status,
        request=ResearchRequest(manufacturer_part_number=mpn, description="test"),
        lookup_base_candidate=derive_lookup_base_candidate(mpn) or None,
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
    kwargs.update(overrides)
    return MicronAliasEligibilityResult(**kwargs)  # type: ignore[arg-type]


class TestEligibilityResultEstablished:
    def test_established_result_constructs_from_real_fixture(self) -> None:
        result = _established_result()
        assert result.status is MicronAliasEligibilityStatus.ESTABLISHED
        assert result.is_established is True
        assert result.can_supply_alias_relation is True
        assert result.can_supply_authority is True
        assert result.body_sha256 == FIXTURE_SHA256

    def test_tampered_policy_rejected(self) -> None:
        result = _established_result()
        with pytest.raises(ValueError):
            replace(result, policy_id="evil-policy")

    def test_tampered_manufacturer_rejected(self) -> None:
        result = _established_result()
        with pytest.raises(ValueError):
            replace(result, manufacturer="Seagate")

    def test_tampered_category_rejected(self) -> None:
        result = _established_result()
        with pytest.raises(ValueError):
            replace(result, category="Memory")

    def test_host_escaped_final_url_rejected(self) -> None:
        result = _established_result()
        with pytest.raises(ValueError):
            replace(
                result,
                fetched_final_url="https://evil.example/catalog.json",
            )

    def test_scheme_downgrade_final_url_rejected(self) -> None:
        result = _established_result()
        with pytest.raises(ValueError):
            replace(
                result,
                fetched_final_url=MICRON_7500_REQUESTED_CATALOG_URL.replace(
                    "https://", "http://"
                ),
            )

    def test_synthesized_base_mpn_rejected(self) -> None:
        # A base that is not the source-published row cannot be established:
        # the frozen-2A re-derivation and relation binding both fail.
        result = _established_result()
        with pytest.raises(ValueError):
            replace(result, matched_base_mpn=f"{BASE}SYNTH")

    def test_missing_authority_fields_rejected(self) -> None:
        result = _established_result()
        for field in (
            "fetched_final_url",
            "retrieved_at",
            "matched_base_mpn",
            "part_number_match",
            "ssd_category_evidence",
            "alias_relation",
            "source_name",
        ):
            with pytest.raises(ValueError):
                replace(result, **{field: None})

    def test_lookup_candidate_must_rederive(self) -> None:
        result = _established_result()
        with pytest.raises(ValueError):
            replace(result, lookup_base_candidate="WRONG")


class TestEligibilityResultNonEstablished:
    @pytest.mark.parametrize(
        "status",
        [s for s in MicronAliasEligibilityStatus if s is not
         MicronAliasEligibilityStatus.ESTABLISHED],
    )
    def test_every_non_established_status_cannot_carry_authority(
        self, status: MicronAliasEligibilityStatus
    ) -> None:
        mpn = "" if status is MicronAliasEligibilityStatus.NO_REQUESTED_MPN else BASE
        if status is MicronAliasEligibilityStatus.INVALID_LOOKUP_BASE:
            mpn = "-R"
        overrides: dict = {}
        if status in (
            MicronAliasEligibilityStatus.FETCH_FAILED,
            MicronAliasEligibilityStatus.SOURCE_REFUSED,
        ):
            overrides["requested_source_url"] = MICRON_7500_REQUESTED_CATALOG_URL
        if status in (
            MicronAliasEligibilityStatus.NO_AUTHORITY_MATCH,
            MicronAliasEligibilityStatus.AMBIGUOUS_AUTHORITY_MATCH,
            MicronAliasEligibilityStatus.CATEGORY_NOT_SSD,
            MicronAliasEligibilityStatus.PARSE_FAILED,
        ):
            overrides.update(
                requested_source_url=MICRON_7500_REQUESTED_CATALOG_URL,
                fetched_final_url=MICRON_7500_REQUESTED_CATALOG_URL,
                retrieved_at=FIXED_AT,
                source_name=MICRON_7500_SOURCE_NAME,
                body_sha256=FIXTURE_SHA256,
            )
        if status is MicronAliasEligibilityStatus.HOST_ESCAPED:
            overrides.update(
                requested_source_url=MICRON_7500_REQUESTED_CATALOG_URL,
                fetched_final_url="https://evil.example/catalog.json",
                retrieved_at=FIXED_AT,
            )
        result = _non_established_result(status, mpn=mpn, **overrides)
        assert result.is_established is False
        assert result.can_supply_alias_relation is False
        assert result.can_supply_authority is False
        assert result.manufacturer is None
        assert result.category is None
        assert result.matched_base_mpn is None
        assert result.part_number_match is None
        assert result.ssd_category_evidence is None
        assert result.alias_relation is None

    def test_non_established_with_manufacturer_rejected(self) -> None:
        with pytest.raises(ValueError):
            _non_established_result(
                MicronAliasEligibilityStatus.NO_AUTHORITY_MATCH,
                requested_source_url=MICRON_7500_REQUESTED_CATALOG_URL,
                fetched_final_url=MICRON_7500_REQUESTED_CATALOG_URL,
                retrieved_at=FIXED_AT,
                source_name=MICRON_7500_SOURCE_NAME,
                body_sha256=FIXTURE_SHA256,
                manufacturer="Micron",
            )

    def test_no_requested_mpn_requires_absent_mpn(self) -> None:
        with pytest.raises(ValueError):
            _non_established_result(
                MicronAliasEligibilityStatus.NO_REQUESTED_MPN, mpn=BASE
            )

    def test_no_requested_mpn_requires_empty_mpn(self) -> None:
        _non_established_result(
            MicronAliasEligibilityStatus.NO_REQUESTED_MPN, mpn=""
        )  # valid

    def test_invalid_lookup_base_requires_non_empty_mpn(self) -> None:
        with pytest.raises(ValueError):
            _non_established_result(
                MicronAliasEligibilityStatus.INVALID_LOOKUP_BASE, mpn=""
            )

    def test_invalid_lookup_base_for_degenerate_mpn_is_valid(self) -> None:
        result = _non_established_result(
            MicronAliasEligibilityStatus.INVALID_LOOKUP_BASE, mpn="-R"
        )
        assert result.status is MicronAliasEligibilityStatus.INVALID_LOOKUP_BASE
        assert result.lookup_base_candidate is None
        assert result.requested_source_url is None

    def test_fetch_failed_carries_reviewed_url_but_nothing_fetched(self) -> None:
        result = _non_established_result(
            MicronAliasEligibilityStatus.FETCH_FAILED,
            requested_source_url=MICRON_7500_REQUESTED_CATALOG_URL,
        )
        assert result.fetched_final_url is None
        assert result.body_sha256 is None

    def test_fetch_failed_requires_reviewed_url(self) -> None:
        with pytest.raises(ValueError):
            _non_established_result(
                MicronAliasEligibilityStatus.FETCH_FAILED,
                requested_source_url="https://elsewhere.example/x",
            )

    def test_host_escaped_requires_outside_origin(self) -> None:
        with pytest.raises(ValueError):
            _non_established_result(
                MicronAliasEligibilityStatus.HOST_ESCAPED,
                requested_source_url=MICRON_7500_REQUESTED_CATALOG_URL,
                fetched_final_url=MICRON_7500_REQUESTED_CATALOG_URL,
                retrieved_at=FIXED_AT,
            )

    def test_host_escaped_carries_no_source_name_or_body_sha(self) -> None:
        with pytest.raises(ValueError):
            _non_established_result(
                MicronAliasEligibilityStatus.HOST_ESCAPED,
                requested_source_url=MICRON_7500_REQUESTED_CATALOG_URL,
                fetched_final_url="https://evil.example/x",
                retrieved_at=FIXED_AT,
                source_name=MICRON_7500_SOURCE_NAME,
            )

    def test_fetched_states_require_body_sha(self) -> None:
        for status in (
            MicronAliasEligibilityStatus.NO_AUTHORITY_MATCH,
            MicronAliasEligibilityStatus.AMBIGUOUS_AUTHORITY_MATCH,
            MicronAliasEligibilityStatus.CATEGORY_NOT_SSD,
            MicronAliasEligibilityStatus.PARSE_FAILED,
        ):
            with pytest.raises(ValueError):
                _non_established_result(
                    status,
                    requested_source_url=MICRON_7500_REQUESTED_CATALOG_URL,
                    fetched_final_url=MICRON_7500_REQUESTED_CATALOG_URL,
                    retrieved_at=FIXED_AT,
                    source_name=MICRON_7500_SOURCE_NAME,
                    body_sha256=None,
                )

    def test_bad_body_sha_rejected(self) -> None:
        with pytest.raises(ValueError):
            _non_established_result(
                MicronAliasEligibilityStatus.NO_AUTHORITY_MATCH,
                requested_source_url=MICRON_7500_REQUESTED_CATALOG_URL,
                fetched_final_url=MICRON_7500_REQUESTED_CATALOG_URL,
                retrieved_at=FIXED_AT,
                source_name=MICRON_7500_SOURCE_NAME,
                body_sha256="NOT-A-SHA",
            )

    def test_uppercase_body_sha_rejected(self) -> None:
        with pytest.raises(ValueError):
            _non_established_result(
                MicronAliasEligibilityStatus.NO_AUTHORITY_MATCH,
                requested_source_url=MICRON_7500_REQUESTED_CATALOG_URL,
                fetched_final_url=MICRON_7500_REQUESTED_CATALOG_URL,
                retrieved_at=FIXED_AT,
                source_name=MICRON_7500_SOURCE_NAME,
                body_sha256=FIXTURE_SHA256.upper(),
            )

    def test_naive_retrieved_at_rejected(self) -> None:
        with pytest.raises(ValueError):
            _non_established_result(
                MicronAliasEligibilityStatus.NO_AUTHORITY_MATCH,
                requested_source_url=MICRON_7500_REQUESTED_CATALOG_URL,
                fetched_final_url=MICRON_7500_REQUESTED_CATALOG_URL,
                retrieved_at=FIXED_AT.replace(tzinfo=None),
                source_name=MICRON_7500_SOURCE_NAME,
                body_sha256=FIXTURE_SHA256,
            )


# ---------------------------------------------------------------------------
# Frozen 2A regression invariant (the alias relation never changes 2A)
# ---------------------------------------------------------------------------


class TestTwoARegressionInvariant:
    @pytest.mark.parametrize(
        ("a", "b"),
        [(BASE, BASER), (BASE, BASET), (BASER, BASET)],
    )
    def test_family_forms_are_never_established_under_2a(self, a: str, b: str) -> None:
        comparison = compare_part_numbers(a, b)
        assert comparison.match_type is IdentityMatchType.UNKNOWN
        assert comparison.match_type not in ESTABLISHED_MATCH_TYPES
