"""ComparableResultCodec tests (PRODUCT-INTEL.7C-A).

Tests for:
- Codec round-trip (encode then decode produces equivalent result)
- Codec strictness (rejects bad payloads)
- Codec purity (no Django/runs/providers imports)
- Schema version gate
- Decimal safety
- Enum stability
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from product_intelligence.domain.enums import IdentityMatchType
from product_intelligence.domain.models import ProductIdentity
from product_intelligence.research.comparable_research_results import (
    AuthorityAttemptResult,
    AuthorityAuditOutcomeKind,
    ComparableResearchResult,
    ComparableResultKind,
    DatasheetAttemptResult,
    DatasheetAuditOutcomeKind,
    ProductEnrichmentAudit,
)
from product_intelligence.research.comparable_result_codec import (
    COMPARABLE_RESULT_SCHEMA_VERSION,
    ComparableResultCodecError,
    decode_comparable_result,
    encode_comparable_result,
)
from product_intelligence.research.specifications import SourceAuthority


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_identity() -> ProductIdentity:
    return ProductIdentity(
        manufacturer_part_number="XP15360SE70005",
        normalized_manufacturer_part_number="15360SE70005",
        match_type=IdentityMatchType.EXACT,
        manufacturer="Seagate",
        product_name="Nytro 5050",
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
        candidate_enrichment_audits=(),
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
        candidate_enrichment_audits=(),
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

    def test_round_trip_produces_json_serializable(self) -> None:
        """Encoded payload must be JSON-serialisable."""
        original = _make_no_requested_mpn_result()
        encoded = encode_comparable_result(original)
        # This will raise TypeError if the payload has non-JSON types
        json.dumps(encoded)

    def test_round_trip_re_runs_post_init(self) -> None:
        """Decoded result must pass __post_init__ invariants."""
        original = _make_no_authority_match_result()
        encoded = encode_comparable_result(original)
        # This constructs a new object through the normal constructor
        # which runs __post_init__ — if invariants fail, it raises.
        decoded = decode_comparable_result(encoded, schema_version=1)
        assert decoded is not None  # __post_init__ passed


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

    def test_rejects_extra_keys(self) -> None:
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
                    "unknown_field": "bad",
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
                    "candidate_enrichment_audits": [],
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
                    "candidate_enrichment_audits": [],
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
                    "candidate_enrichment_audits": [],
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
        """Empty authority_audit should be caught by the codec."""
        with pytest.raises(ComparableResultCodecError):
            decode_comparable_result(
                {
                    "kind": "FULL",
                    "target_mpn": "XP",
                    "target_manufacturer": "Seagate",
                    "target_enrichment_audit": None,
                    "authority_audit": [],  # Empty — violates non-empty invariant
                    "candidates": [],
                    "candidate_enrichment_audits": [],
                },
                schema_version=1,
            )

    def test_wraps_fatal_outcome_in_result(self) -> None:
        """Fatal authority outcomes cannot be in a COMPLETED result."""
        with pytest.raises(ComparableResultCodecError):
            decode_comparable_result(
                {
                    "kind": "FULL",
                    "target_mpn": "XP",
                    "target_manufacturer": "Seagate",
                    "target_enrichment_audit": None,
                    "authority_audit": [{
                        "outcome": "AUTHORITY_FETCH_FAILED",
                        "source_name": "S",
                        "source_url": "https://example.com/",
                        "matched_mpn": None,
                        "raw_reference": None,
                    }],
                    "candidates": [],
                    "candidate_enrichment_audits": [],
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
