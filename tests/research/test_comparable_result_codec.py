"""ComparableResultCodec tests (PRODUCT-INTEL.7C-A/FU2).

Tests for:
- Codec round-trip (encode then decode produces equivalent result)
- Codec strictness (rejects bad payloads)
- Codec purity (no Django/runs/providers imports)
- Schema version gate
- Decimal safety
- Enum stability
- BLOCKER 2: Decimal similarity encoding as strings
- BLOCKER 3: no candidate_enrichment_audits in encoded payload
- EvidenceSourceReference with source_authority + retrieved_at
- BLOCKER 4: new AuthorityAttemptResult shape (policy_id, requested_source_url,
  fetched_final_url, retrieved_at, matching_mpn)
"""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

from product_intelligence.research.comparable_research_results import (
    AuthorityAttemptResult,
    AuthorityAuditOutcomeKind,
    ComparableCandidateResult,
    ComparableResearchResult,
    ComparableResultKind,
    DatasheetAttemptResult,
    DatasheetAuditOutcomeKind,
    EvidenceLayer,
    EvidenceSourceReference,
    FieldAssessmentResult,
    ProductEnrichmentAudit,
)
from product_intelligence.research.comparable_result_codec import (
    COMPARABLE_RESULT_SCHEMA_VERSION,
    ComparableResultCodecError,
    decode_comparable_result,
    encode_comparable_result,
)
from product_intelligence.research.enterprise_ssd import (
    ENTERPRISE_SSD_SCHEMA,
)
from product_intelligence.research.enterprise_ssd_similarity import (
    ComparisonState,
)
from product_intelligence.research.specifications import (
    ResolutionState,
    SourceAuthority,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

POLICY_ID = "seagate-enterprise-ssd-nytro-support-catalog-v1"
SOURCE_URL = "https://www.seagate.com/support/enterprise-storage/solid-state-drives/nytro-5050/"
FINAL_URL = "https://www.seagate.com/support/enterprise-storage/solid-state-drives/nytro-5050/"
RETRIEVED_AT = "2025-01-01T00:00:00+00:00"


def _make_target_enrichment_audit() -> ProductEnrichmentAudit:
    return ProductEnrichmentAudit(
        product_mpn="XP15360SE70005",
        attempts=(DatasheetAttemptResult(
            outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
        ),),
    )


def _make_candidate_enrichment_audit(mpn: str = "XP15360SE70015") -> ProductEnrichmentAudit:
    return ProductEnrichmentAudit(
        product_mpn=mpn,
        attempts=(DatasheetAttemptResult(
            outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
        ),),
    )


def _make_evidence_ref() -> EvidenceSourceReference:
    return EvidenceSourceReference(
        source_name="Seagate Support",
        source_url="https://www.seagate.com/support/",
        evidence_layer=EvidenceLayer.SUPPORT_PAGE,
        source_authority=SourceAuthority.AUTHORITATIVE,
        retrieved_at="2025-01-01T00:00:00+00:00",
    )


def _make_matched_authority() -> AuthorityAttemptResult:
    return AuthorityAttemptResult(
        policy_id=POLICY_ID,
        outcome=AuthorityAuditOutcomeKind.MATCHED,
        requested_source_url=SOURCE_URL,
        fetched_final_url=FINAL_URL,
        retrieved_at=RETRIEVED_AT,
        matching_mpn="XP15360SE70005",
    )


def _make_all_12_assessments(
    scored_keys: tuple[str, ...] = (),
    scored_similarity: Decimal = Decimal("1"),
) -> tuple[FieldAssessmentResult, ...]:
    assessments: list[FieldAssessmentResult] = []
    ref = _make_evidence_ref()
    for key in ENTERPRISE_SSD_SCHEMA.definitions.keys():
        if key in scored_keys:
            assessments.append(FieldAssessmentResult(
                definition_key=key,
                comparison_state=ComparisonState.SCORED,
                target_resolution_state=ResolutionState.VERIFIED,
                candidate_resolution_state=ResolutionState.VERIFIED,
                field_similarity=scored_similarity,
                target_value="test",
                candidate_value="test",
                target_evidence=(ref,),
                candidate_evidence=(ref,),
            ))
        else:
            assessments.append(FieldAssessmentResult(
                definition_key=key,
                comparison_state=ComparisonState.BOTH_NOT_VERIFIED,
                target_resolution_state=ResolutionState.UNKNOWN,
                candidate_resolution_state=ResolutionState.UNKNOWN,
                field_similarity=None,
                target_value=None,
                candidate_value=None,
            ))
    return tuple(assessments)


def _make_no_requested_mpn_result() -> ComparableResearchResult:
    return ComparableResearchResult(
        kind=ComparableResultKind.NO_REQUESTED_MPN,
        target_mpn="",
        target_manufacturer=None,
        target_enrichment_audit=None,
        authority_audit=(AuthorityAttemptResult(
            policy_id=POLICY_ID,
            outcome=AuthorityAuditOutcomeKind.NO_REQUESTED_MPN,
            requested_source_url=SOURCE_URL,
        ),),
        candidates=(),
    )


def _make_no_authority_match_result() -> ComparableResearchResult:
    return ComparableResearchResult(
        kind=ComparableResultKind.NO_AUTHORITY_MATCH,
        target_mpn="UNKNOWN_MPN",
        target_manufacturer=None,
        target_enrichment_audit=None,
        authority_audit=(
            AuthorityAttemptResult(
                policy_id=POLICY_ID,
                outcome=AuthorityAuditOutcomeKind.NO_MPN_IN_SOURCE,
                requested_source_url=SOURCE_URL,
                fetched_final_url=FINAL_URL,
                retrieved_at=RETRIEVED_AT,
            ),
        ),
        candidates=(),
    )


def _make_full_result_with_candidates() -> ComparableResearchResult:
    ref = _make_evidence_ref()
    # 2 scored fields for a simpler round-trip test
    assessments = _make_all_12_assessments(
        scored_keys=("capacity", "physical_form_factor"),
    )
    return ComparableResearchResult(
        kind=ComparableResultKind.FULL,
        target_mpn="XP15360SE70005",
        target_manufacturer="Seagate",
        target_enrichment_audit=_make_target_enrichment_audit(),
        authority_audit=(_make_matched_authority(),),
        candidates=(
            ComparableCandidateResult(
                candidate_mpn="XP15360SE70015",
                candidate_normalized_mpn="XP15360SE70015",
                scored_field_count=2,
                evidence_coverage=Decimal("2") / Decimal("12"),
                observed_similarity=Decimal("1"),
                evidence_weighted_similarity=Decimal("2") / Decimal("12"),
                field_assessments=assessments,
                enrichment_audit=_make_candidate_enrichment_audit(),
            ),
        ),
    )


# ---------------------------------------------------------------------------
# Round-trip tests
# ---------------------------------------------------------------------------


class TestCodecRoundTrip:
    """Encoding then decoding produces an equivalent result."""

    def test_round_trip_no_requested_mpn(self) -> None:
        original = _make_no_requested_mpn_result()
        encoded = encode_comparable_result(original)
        decoded = decode_comparable_result(encoded, schema_version=1)
        assert decoded.kind is original.kind
        assert decoded.target_mpn == original.target_mpn
        assert decoded.target_manufacturer == original.target_manufacturer
        assert len(decoded.authority_audit) == len(original.authority_audit)
        assert decoded.authority_audit[0].outcome is original.authority_audit[0].outcome
        assert decoded.authority_audit[0].policy_id == original.authority_audit[0].policy_id

    def test_round_trip_no_authority_match(self) -> None:
        original = _make_no_authority_match_result()
        encoded = encode_comparable_result(original)
        decoded = decode_comparable_result(encoded, schema_version=1)
        assert decoded.kind is original.kind
        assert decoded.target_mpn == original.target_mpn
        assert (
            decoded.authority_audit[0].outcome
            is AuthorityAuditOutcomeKind.NO_MPN_IN_SOURCE
        )
        assert decoded.authority_audit[0].policy_id == POLICY_ID
        assert decoded.authority_audit[0].fetched_final_url == FINAL_URL

    def test_round_trip_full_with_candidates(self) -> None:
        """FULL result with candidates and field assessments round-trips."""
        original = _make_full_result_with_candidates()
        encoded = encode_comparable_result(original)
        decoded = decode_comparable_result(encoded, schema_version=1)

        assert decoded.kind is ComparableResultKind.FULL
        assert decoded.target_mpn == "XP15360SE70005"
        assert decoded.target_manufacturer == "Seagate"
        assert decoded.target_enrichment_audit is not None
        assert decoded.target_enrichment_audit.product_mpn == "XP15360SE70005"

        # Authority round-trip (new shape)
        auth = decoded.authority_audit[0]
        assert auth.policy_id == POLICY_ID
        assert auth.requested_source_url == SOURCE_URL
        assert auth.fetched_final_url == FINAL_URL
        assert auth.retrieved_at == RETRIEVED_AT
        assert auth.matching_mpn == "XP15360SE70005"

        # Candidate round-trip
        assert len(decoded.candidates) == 1
        candidate = decoded.candidates[0]
        assert candidate.candidate_mpn == "XP15360SE70015"
        assert candidate.scored_field_count == 2
        assert candidate.evidence_coverage == Decimal("2") / Decimal("12")
        assert candidate.observed_similarity == Decimal("1")
        assert candidate.enrichment_audit.product_mpn == "XP15360SE70015"

        # Field assessment round-trip
        assert len(candidate.field_assessments) == 12
        scored = [fa for fa in candidate.field_assessments
                  if fa.comparison_state is ComparisonState.SCORED]
        assert len(scored) == 2
        for s in scored:
            assert s.field_similarity == Decimal("1")
            assert len(s.target_evidence) == 1
            assert len(s.candidate_evidence) == 1

        not_scored = [fa for fa in candidate.field_assessments
                      if fa.comparison_state is not ComparisonState.SCORED]
        assert len(not_scored) == 10
        for ns in not_scored:
            assert ns.field_similarity is None

    def test_round_trip_produces_json_serializable(self) -> None:
        original = _make_full_result_with_candidates()
        encoded = encode_comparable_result(original)
        json.dumps(encoded)

    def test_round_trip_re_runs_post_init(self) -> None:
        original = _make_no_authority_match_result()
        encoded = encode_comparable_result(original)
        decoded = decode_comparable_result(encoded, schema_version=1)
        assert decoded is not None

    def test_encoded_payload_has_no_candidate_enrichment_audits(self) -> None:
        original = _make_full_result_with_candidates()
        encoded = encode_comparable_result(original)
        assert "candidate_enrichment_audits" not in encoded

    def test_encoded_payload_top_level_keys(self) -> None:
        original = _make_no_requested_mpn_result()
        encoded = encode_comparable_result(original)
        assert set(encoded.keys()) == {
            "kind", "target_mpn", "target_manufacturer",
            "target_enrichment_audit", "authority_audit", "candidates",
        }

    def test_authority_attempt_encoded_keys(self) -> None:
        """Encoded authority attempt has the new field keys."""
        original = _make_full_result_with_candidates()
        encoded = encode_comparable_result(original)
        auth = encoded["authority_audit"][0]
        assert set(auth.keys()) == {
            "policy_id", "outcome", "requested_source_url",
            "fetched_final_url", "retrieved_at", "matching_mpn",
        }


# ---------------------------------------------------------------------------
# Codec strictness
# ---------------------------------------------------------------------------


class TestCodecStrictness:
    """Codec rejects malformed payloads."""

    def test_rejects_unsupported_schema_version(self) -> None:
        with pytest.raises(ComparableResultCodecError, match="unsupported"):
            decode_comparable_result({}, schema_version=99)

    def test_rejects_bool_schema_version(self) -> None:
        with pytest.raises(ComparableResultCodecError, match="must be int"):
            decode_comparable_result({}, schema_version=True)

    def test_rejects_non_dict_payload(self) -> None:
        with pytest.raises(ComparableResultCodecError, match="mapping"):
            decode_comparable_result([], schema_version=1)

    def test_rejects_missing_keys(self) -> None:
        with pytest.raises(ComparableResultCodecError, match="missing required"):
            decode_comparable_result({"kind": "FULL"}, schema_version=1)

    def test_rejects_extra_top_level_keys(self) -> None:
        with pytest.raises(ComparableResultCodecError, match="unexpected keys"):
            decode_comparable_result(
                {
                    "kind": "NO_REQUESTED_MPN",
                    "target_mpn": "",
                    "target_manufacturer": None,
                    "target_enrichment_audit": None,
                    "authority_audit": [],
                    "candidates": [],
                    "candidate_enrichment_audits": [],
                },
                schema_version=1,
            )

    def test_rejects_wrong_type_for_kind(self) -> None:
        with pytest.raises(ComparableResultCodecError, match="expected string"):
            decode_comparable_result(
                {
                    "kind": 123,
                    "target_mpn": "",
                    "target_manufacturer": None,
                    "target_enrichment_audit": None,
                    "authority_audit": [],
                    "candidates": [],
                },
                schema_version=1,
            )

    def test_rejects_unknown_enum_value(self) -> None:
        with pytest.raises(ComparableResultCodecError, match="unknown ComparableResultKind"):
            decode_comparable_result(
                {
                    "kind": "NOT_A_KIND",
                    "target_mpn": "",
                    "target_manufacturer": None,
                    "target_enrichment_audit": None,
                    "authority_audit": [],
                    "candidates": [],
                },
                schema_version=1,
            )

    def test_rejects_non_list_authority_audit(self) -> None:
        with pytest.raises(ComparableResultCodecError, match="expected list"):
            decode_comparable_result(
                {
                    "kind": "NO_REQUESTED_MPN",
                    "target_mpn": "",
                    "target_manufacturer": None,
                    "target_enrichment_audit": None,
                    "authority_audit": "not a list",
                    "candidates": [],
                },
                schema_version=1,
            )

    def test_rejects_old_authority_attempt_keys(self) -> None:
        """Old V0 authority attempt keys (source_name, source_url, matched_mpn,
        raw_reference) are rejected in V1."""
        with pytest.raises(ComparableResultCodecError, match="unexpected keys"):
            decode_comparable_result(
                {
                    "kind": "NO_REQUESTED_MPN",
                    "target_mpn": "",
                    "target_manufacturer": None,
                    "target_enrichment_audit": None,
                    "authority_audit": [{
                        "outcome": "NO_REQUESTED_MPN",
                        "source_name": "Old",
                        "source_url": "https://old.com/",
                        "matched_mpn": None,
                        "raw_reference": None,
                    }],
                    "candidates": [],
                },
                schema_version=1,
            )


# ---------------------------------------------------------------------------
# Decimal safety
# ---------------------------------------------------------------------------


class TestDecimalSafety:
    """Decimal values are stored as strings, not floats."""

    def test_field_similarity_stored_as_string(self) -> None:
        result = _make_full_result_with_candidates()
        encoded = encode_comparable_result(result)
        fa = encoded["candidates"][0]["field_assessments"][0]
        # Find a scored one
        scored_fas = [f for f in encoded["candidates"][0]["field_assessments"]
                      if f["field_similarity"] is not None]
        assert len(scored_fas) == 2
        for fa in scored_fas:
            assert isinstance(fa["field_similarity"], str)
            assert fa["field_similarity"] == "1"

    def test_evidence_coverage_stored_as_string(self) -> None:
        result = _make_full_result_with_candidates()
        encoded = encode_comparable_result(result)
        cov = encoded["candidates"][0]["evidence_coverage"]
        assert isinstance(cov, str)

    def test_rejects_float_as_field_similarity(self) -> None:
        with pytest.raises(ComparableResultCodecError, match="Decimal must be stored as a string"):
            decode_comparable_result(
                {
                    "kind": "FULL",
                    "target_mpn": "XP",
                    "target_manufacturer": "Seagate",
                    "target_enrichment_audit": {
                        "product_mpn": "XP",
                        "attempts": [{
                            "outcome": "NO_DATASHEET_SOURCE",
                            "source_name": None,
                            "source_url": None,
                            "final_url": None,
                            "retrieved_at": None,
                            "observation_count": None,
                        }],
                    },
                    "authority_audit": [{
                        "policy_id": "test-policy",
                        "outcome": "MATCHED",
                        "requested_source_url": "https://example.com/",
                        "fetched_final_url": "https://example.com/",
                        "retrieved_at": "2025-01-01T00:00:00+00:00",
                        "matching_mpn": "XP",
                    }],
                    "candidates": [{
                        "candidate_mpn": "XP",
                        "candidate_normalized_mpn": "XP",
                        "scored_field_count": 1,
                        "evidence_coverage": "0.0833333333333333333333333333333333333333",
                        "observed_similarity": "1",
                        "evidence_weighted_similarity": "0.0833333333333333333333333333333333333333",
                        "field_assessments": [{
                            "definition_key": "capacity",
                            "comparison_state": "SCORED",
                            "target_resolution_state": "VERIFIED",
                            "candidate_resolution_state": "VERIFIED",
                            "field_similarity": 1.0,
                            "target_value": "x",
                            "candidate_value": "y",
                            "target_evidence": [{
                                "source_name": "S",
                                "source_url": "https://example.com/",
                                "evidence_layer": "SUPPORT_PAGE",
                                "source_authority": "AUTHORITATIVE",
                                "retrieved_at": "2025-01-01T00:00:00+00:00",
                            }],
                            "candidate_evidence": [{
                                "source_name": "S",
                                "source_url": "https://example.com/",
                                "evidence_layer": "SUPPORT_PAGE",
                                "source_authority": "AUTHORITATIVE",
                                "retrieved_at": "2025-01-01T00:00:00+00:00",
                            }],
                        }] + [{
                            "definition_key": k,
                            "comparison_state": "BOTH_NOT_VERIFIED",
                            "target_resolution_state": "UNKNOWN",
                            "candidate_resolution_state": "UNKNOWN",
                            "field_similarity": None,
                            "target_value": None,
                            "candidate_value": None,
                            "target_evidence": [],
                            "candidate_evidence": [],
                        } for k in ENTERPRISE_SSD_SCHEMA.definitions.keys()
                         if k != "capacity"],
                        "enrichment_audit": {
                            "product_mpn": "XP",
                            "attempts": [{
                                "outcome": "NO_DATASHEET_SOURCE",
                                "source_name": None,
                                "source_url": None,
                                "final_url": None,
                                "retrieved_at": None,
                                "observation_count": None,
                            }],
                        },
                    }],
                },
                schema_version=1,
            )


# ---------------------------------------------------------------------------
# Schema version gate
# ---------------------------------------------------------------------------


class TestSchemaVersion:
    """Schema version is exactly 1 and only 1 is supported."""

    def test_schema_version_is_1(self) -> None:
        assert COMPARABLE_RESULT_SCHEMA_VERSION == 1

    def test_version_zero_rejected(self) -> None:
        with pytest.raises(ComparableResultCodecError):
            decode_comparable_result({}, schema_version=0)

    def test_version_two_rejected(self) -> None:
        with pytest.raises(ComparableResultCodecError):
            decode_comparable_result({}, schema_version=2)


# ---------------------------------------------------------------------------
# Codec rejects constructor-invariant violations
# ---------------------------------------------------------------------------


class TestCodecWrapsInvariantViolations:
    """If decoded data violates a constructor invariant, codec wraps it."""

    def test_wraps_empty_authority_audit(self) -> None:
        with pytest.raises(ComparableResultCodecError):
            decode_comparable_result(
                {
                    "kind": "FULL",
                    "target_mpn": "XP",
                    "target_manufacturer": "Seagate",
                    "target_enrichment_audit": {
                        "product_mpn": "XP",
                        "attempts": [{
                            "outcome": "NO_DATASHEET_SOURCE",
                            "source_name": None,
                            "source_url": None,
                            "final_url": None,
                            "retrieved_at": None,
                            "observation_count": None,
                        }],
                    },
                    "authority_audit": [],
                    "candidates": [],
                },
                schema_version=1,
            )

    def test_wraps_fatal_outcome_in_result(self) -> None:
        with pytest.raises(ComparableResultCodecError):
            decode_comparable_result(
                {
                    "kind": "FULL",
                    "target_mpn": "XP",
                    "target_manufacturer": "Seagate",
                    "target_enrichment_audit": {
                        "product_mpn": "XP",
                        "attempts": [{
                            "outcome": "NO_DATASHEET_SOURCE",
                            "source_name": None,
                            "source_url": None,
                            "final_url": None,
                            "retrieved_at": None,
                            "observation_count": None,
                        }],
                    },
                    "authority_audit": [{
                        "policy_id": "test-policy",
                        "outcome": "AUTHORITY_FETCH_FAILED",
                        "requested_source_url": "https://example.com/",
                        "fetched_final_url": None,
                        "retrieved_at": None,
                        "matching_mpn": None,
                    }],
                    "candidates": [],
                },
                schema_version=1,
            )


# ---------------------------------------------------------------------------
# Type checks
# ---------------------------------------------------------------------------


class TestEncodeTypeCheck:
    """encode_comparable_result rejects non-ComparableResearchResult."""

    def test_rejects_wrong_type(self) -> None:
        with pytest.raises(TypeError, match="expected ComparableResearchResult"):
            encode_comparable_result("not a result")


# ---------------------------------------------------------------------------
# Enum stability
# ---------------------------------------------------------------------------


class TestEnumStability:
    """Enums are encoded through stable .value strings."""

    def test_kind_encoded_as_value(self) -> None:
        result = _make_no_requested_mpn_result()
        encoded = encode_comparable_result(result)
        assert encoded["kind"] == "NO_REQUESTED_MPN"

    def test_authority_outcome_encoded_as_value(self) -> None:
        result = _make_no_authority_match_result()
        encoded = encode_comparable_result(result)
        assert encoded["authority_audit"][0]["outcome"] == "NO_MPN_IN_SOURCE"

    def test_comparison_state_encoded_as_value(self) -> None:
        result = _make_full_result_with_candidates()
        encoded = encode_comparable_result(result)
        scored = [f for f in encoded["candidates"][0]["field_assessments"]
                  if f["comparison_state"] == "SCORED"]
        assert len(scored) == 2

    def test_evidence_layer_encoded_as_value(self) -> None:
        result = ComparableResearchResult(
            kind=ComparableResultKind.FULL,
            target_mpn="XP15360SE70005",
            target_manufacturer="Seagate",
            target_enrichment_audit=_make_target_enrichment_audit(),
            authority_audit=(_make_matched_authority(),),
            candidates=(ComparableCandidateResult(
                candidate_mpn="XP15360SE70015",
                candidate_normalized_mpn="XP15360SE70015",
                scored_field_count=1,
                evidence_coverage=Decimal("1") / Decimal("12"),
                observed_similarity=Decimal("1"),
                evidence_weighted_similarity=Decimal("1") / Decimal("12"),
                field_assessments=(
                    FieldAssessmentResult(
                        definition_key="capacity",
                        comparison_state=ComparisonState.SCORED,
                        target_resolution_state=ResolutionState.VERIFIED,
                        candidate_resolution_state=ResolutionState.VERIFIED,
                        field_similarity=Decimal("1"),
                        target_value="15.36 TB",
                        candidate_value="15.36 TB",
                        target_evidence=(_make_evidence_ref(),),
                        candidate_evidence=(_make_evidence_ref(),),
                    ),
                ) + tuple(
                    FieldAssessmentResult(
                        definition_key=k,
                        comparison_state=ComparisonState.BOTH_NOT_VERIFIED,
                        target_resolution_state=ResolutionState.UNKNOWN,
                        candidate_resolution_state=ResolutionState.UNKNOWN,
                        field_similarity=None,
                        target_value=None,
                        candidate_value=None,
                    )
                    for k in ENTERPRISE_SSD_SCHEMA.definitions.keys()
                    if k != "capacity"
                ),
                enrichment_audit=_make_candidate_enrichment_audit(),
            ),),
        )
        encoded = encode_comparable_result(result)
        fa = encoded["candidates"][0]["field_assessments"][0]
        assert fa["target_evidence"][0]["evidence_layer"] == "SUPPORT_PAGE"

    def test_source_authority_encoded_as_value(self) -> None:
        result = ComparableResearchResult(
            kind=ComparableResultKind.FULL,
            target_mpn="XP15360SE70005",
            target_manufacturer="Seagate",
            target_enrichment_audit=_make_target_enrichment_audit(),
            authority_audit=(_make_matched_authority(),),
            candidates=(ComparableCandidateResult(
                candidate_mpn="XP15360SE70015",
                candidate_normalized_mpn="XP15360SE70015",
                scored_field_count=1,
                evidence_coverage=Decimal("1") / Decimal("12"),
                observed_similarity=Decimal("1"),
                evidence_weighted_similarity=Decimal("1") / Decimal("12"),
                field_assessments=(
                    FieldAssessmentResult(
                        definition_key="capacity",
                        comparison_state=ComparisonState.SCORED,
                        target_resolution_state=ResolutionState.VERIFIED,
                        candidate_resolution_state=ResolutionState.VERIFIED,
                        field_similarity=Decimal("1"),
                        target_value="15.36 TB",
                        candidate_value="15.36 TB",
                        target_evidence=(_make_evidence_ref(),),
                        candidate_evidence=(_make_evidence_ref(),),
                    ),
                ) + tuple(
                    FieldAssessmentResult(
                        definition_key=k,
                        comparison_state=ComparisonState.BOTH_NOT_VERIFIED,
                        target_resolution_state=ResolutionState.UNKNOWN,
                        candidate_resolution_state=ResolutionState.UNKNOWN,
                        field_similarity=None,
                        target_value=None,
                        candidate_value=None,
                    )
                    for k in ENTERPRISE_SSD_SCHEMA.definitions.keys()
                    if k != "capacity"
                ),
                enrichment_audit=_make_candidate_enrichment_audit(),
            ),),
        )
        encoded = encode_comparable_result(result)
        ref = encoded["candidates"][0]["field_assessments"][0]["target_evidence"][0]
        assert ref["source_authority"] == "AUTHORITATIVE"
