"""ComparableResultCodec tests (PRODUCT-INTEL.7C-A/FU1).

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


def _make_no_requested_mpn_result() -> ComparableResearchResult:
    """Build a minimal NO_REQUESTED_MPN result for round-trip tests."""
    return ComparableResearchResult(
        kind=ComparableResultKind.NO_REQUESTED_MPN,
        target_mpn="",
        target_manufacturer=None,
        target_enrichment_audit=None,
        authority_audit=(AuthorityAttemptResult(
            outcome=AuthorityAuditOutcomeKind.NO_REQUESTED_MPN,
        ),),
        candidates=(),
    )


def _make_no_authority_match_result() -> ComparableResearchResult:
    """Build a minimal NO_AUTHORITY_MATCH result."""
    return ComparableResearchResult(
        kind=ComparableResultKind.NO_AUTHORITY_MATCH,
        target_mpn="UNKNOWN_MPN",
        target_manufacturer=None,
        target_enrichment_audit=None,
        authority_audit=(
            AuthorityAttemptResult(
                outcome=AuthorityAuditOutcomeKind.NO_MPN_IN_SOURCE,
                source_name="Seagate Support",
                source_url="https://www.seagate.com/support/",
            ),
        ),
        candidates=(),
    )


def _make_full_result_with_candidates() -> ComparableResearchResult:
    """Build a FULL result with candidates for round-trip tests."""
    ref = EvidenceSourceReference(
        source_name="Seagate Support",
        source_url="https://www.seagate.com/support/",
        evidence_layer=EvidenceLayer.SUPPORT_PAGE,
        source_authority=SourceAuthority.AUTHORITATIVE,
        retrieved_at="2025-01-01T00:00:00+00:00",
    )
    return ComparableResearchResult(
        kind=ComparableResultKind.FULL,
        target_mpn="XP15360SE70005",
        target_manufacturer="Seagate",
        target_enrichment_audit=_make_target_enrichment_audit(),
        authority_audit=(AuthorityAttemptResult(
            outcome=AuthorityAuditOutcomeKind.MATCHED,
            source_name="Seagate Support",
            source_url="https://www.seagate.com/support/",
            matched_mpn="XP15360SE70005",
        ),),
        candidates=(
            ComparableCandidateResult(
                candidate_mpn="XP15360SE70015",
                candidate_normalized_mpn="XP15360SE70015",
                scored_field_count=7,
                evidence_coverage=Decimal("7") / Decimal("12"),
                observed_similarity=Decimal("1"),
                evidence_weighted_similarity=Decimal("7") / Decimal("12"),
                field_assessments=(
                    FieldAssessmentResult(
                        definition_key="capacity",
                        comparison_state=ComparisonState.SCORED,
                        target_resolution_state=ResolutionState.VERIFIED,
                        candidate_resolution_state=ResolutionState.VERIFIED,
                        field_similarity=Decimal("1"),
                        target_value="15.36 TB",
                        candidate_value="15.36 TB",
                        target_evidence=(ref,),
                        candidate_evidence=(ref,),
                    ),
                    FieldAssessmentResult(
                        definition_key="interface",
                        comparison_state=ComparisonState.BOTH_NOT_VERIFIED,
                        target_resolution_state=ResolutionState.UNKNOWN,
                        candidate_resolution_state=ResolutionState.UNKNOWN,
                        field_similarity=None,
                        target_value=None,
                        candidate_value=None,
                    ),
                ),
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
        assert decoded.authority_audit[0].source_name == "Seagate Support"

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

        # Candidate round-trip
        assert len(decoded.candidates) == 1
        candidate = decoded.candidates[0]
        assert candidate.candidate_mpn == "XP15360SE70015"
        assert candidate.candidate_normalized_mpn == "XP15360SE70015"
        assert candidate.scored_field_count == 7
        assert candidate.evidence_coverage == Decimal("7") / Decimal("12")
        assert candidate.observed_similarity == Decimal("1")
        assert candidate.evidence_weighted_similarity == Decimal("7") / Decimal("12")
        assert candidate.enrichment_audit.product_mpn == "XP15360SE70015"

        # Field assessment round-trip
        assert len(candidate.field_assessments) == 2
        scored = candidate.field_assessments[0]
        assert scored.definition_key == "capacity"
        assert scored.comparison_state is ComparisonState.SCORED
        assert scored.field_similarity == Decimal("1")
        assert len(scored.target_evidence) == 1
        assert scored.target_evidence[0].source_authority is SourceAuthority.AUTHORITATIVE
        assert scored.target_evidence[0].retrieved_at == "2025-01-01T00:00:00+00:00"

        not_scored = candidate.field_assessments[1]
        assert not_scored.definition_key == "interface"
        assert not_scored.comparison_state is ComparisonState.BOTH_NOT_VERIFIED
        assert not_scored.field_similarity is None

    def test_round_trip_produces_json_serializable(self) -> None:
        """Encoded payload must be JSON-serialisable."""
        original = _make_full_result_with_candidates()
        encoded = encode_comparable_result(original)
        json.dumps(encoded)

    def test_round_trip_re_runs_post_init(self) -> None:
        """Decoded result must pass __post_init__ invariants."""
        original = _make_no_authority_match_result()
        encoded = encode_comparable_result(original)
        decoded = decode_comparable_result(encoded, schema_version=1)
        assert decoded is not None

    # BLOCKER 3: no candidate_enrichment_audits in encoded payload
    def test_encoded_payload_has_no_candidate_enrichment_audits(self) -> None:
        """Encoded V1 payload must NOT contain candidate_enrichment_audits."""
        original = _make_full_result_with_candidates()
        encoded = encode_comparable_result(original)
        assert "candidate_enrichment_audits" not in encoded

    def test_encoded_payload_top_level_keys(self) -> None:
        """Encoded V1 payload has exactly the approved keys."""
        original = _make_no_requested_mpn_result()
        encoded = encode_comparable_result(original)
        assert set(encoded.keys()) == {
            "kind", "target_mpn", "target_manufacturer",
            "target_enrichment_audit", "authority_audit", "candidates",
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
            decode_comparable_result({}, schema_version=True)  # type: ignore[arg-type]

    def test_rejects_non_dict_payload(self) -> None:
        with pytest.raises(ComparableResultCodecError, match="mapping"):
            decode_comparable_result([], schema_version=1)

    def test_rejects_missing_keys(self) -> None:
        with pytest.raises(ComparableResultCodecError, match="missing required"):
            decode_comparable_result({"kind": "FULL"}, schema_version=1)

    def test_rejects_extra_top_level_keys(self) -> None:
        """V1 rejects extra top-level keys (no candidate_enrichment_audits)."""
        with pytest.raises(ComparableResultCodecError, match="unexpected keys"):
            decode_comparable_result(
                {
                    "kind": "NO_REQUESTED_MPN",
                    "target_mpn": "",
                    "target_manufacturer": None,
                    "target_enrichment_audit": None,
                    "authority_audit": [],
                    "candidates": [],
                    "candidate_enrichment_audits": [],  # Not in V1 corrected projection
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


# ---------------------------------------------------------------------------
# Decimal safety
# ---------------------------------------------------------------------------


class TestDecimalSafety:
    """Decimal values are stored as strings, not floats."""

    def test_field_similarity_stored_as_string(self) -> None:
        """field_similarity must be a Decimal string in the encoded payload."""
        result = _make_full_result_with_candidates()
        encoded = encode_comparable_result(result)
        fa = encoded["candidates"][0]["field_assessments"][0]
        assert isinstance(fa["field_similarity"], str)
        assert fa["field_similarity"] == "1"

    def test_evidence_coverage_stored_as_string(self) -> None:
        result = _make_full_result_with_candidates()
        encoded = encode_comparable_result(result)
        cov = encoded["candidates"][0]["evidence_coverage"]
        assert isinstance(cov, str)

    def test_rejects_float_as_field_similarity(self) -> None:
        """Codec rejects float where Decimal string is expected."""
        with pytest.raises(ComparableResultCodecError, match="Decimal must be stored as a string"):
            decode_comparable_result(
                {
                    "kind": "FULL",
                    "target_mpn": "XP",
                    "target_manufacturer": "Seagate",
                    "target_enrichment_audit": {
                        "product_mpn": "XP15360SE70005",
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
                        "outcome": "MATCHED",
                        "source_name": "S",
                        "source_url": "https://example.com/",
                        "matched_mpn": "XP",
                        "raw_reference": None,
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
                            "field_similarity": 1.0,  # float!
                            "target_value": "x",
                            "candidate_value": "y",
                            "target_evidence": [],
                            "candidate_evidence": [],
                        }],
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
                        "product_mpn": "XP15360SE70005",
                        "attempts": [],
                    },
                    "authority_audit": [],  # Empty — violates non-empty invariant
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
                        "product_mpn": "XP15360SE70005",
                        "attempts": [],
                    },
                    "authority_audit": [{
                        "outcome": "AUTHORITY_FETCH_FAILED",
                        "source_name": "S",
                        "source_url": "https://example.com/",
                        "matched_mpn": None,
                        "raw_reference": None,
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
            encode_comparable_result("not a result")  # type: ignore[arg-type]


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
        fa = encoded["candidates"][0]["field_assessments"][0]
        assert fa["comparison_state"] == "SCORED"

    def test_evidence_layer_encoded_as_value(self) -> None:
        result = _make_full_result_with_candidates()
        encoded = encode_comparable_result(result)
        ref = encoded["candidates"][0]["field_assessments"][0]["target_evidence"][0]
        assert ref["evidence_layer"] == "SUPPORT_PAGE"

    def test_source_authority_encoded_as_value(self) -> None:
        result = _make_full_result_with_candidates()
        encoded = encode_comparable_result(result)
        ref = encoded["candidates"][0]["field_assessments"][0]["target_evidence"][0]
        assert ref["source_authority"] == "AUTHORITATIVE"
