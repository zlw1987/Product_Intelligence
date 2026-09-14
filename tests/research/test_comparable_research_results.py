"""Pure ComparableResearchResult construction invariant tests (7C-A).

Tests for:
- AuthorityAuditOutcomeKind and AUTHORITY_FATAL_OUTCOMES
- DatasheetAuditOutcomeKind
- ComparableResultKind
- AuthorityAttemptResult state-dependent field shape
- DatasheetAttemptResult state-dependent field shape
- ProductEnrichmentAudit
- ComparableResearchResult kind-specific invariants
- Impossible-state rejection
- NO_MPN_IN_SOURCE + NO_REQUESTED_MPN contradiction
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from product_intelligence.domain.enums import IdentityMatchType
from product_intelligence.domain.models import ProductIdentity
from product_intelligence.research.comparable_candidates import (
    ComparableCandidate,
    ComparableCandidateAssessment,
    ComparableCandidateObservation,
)
from product_intelligence.research.comparable_research_results import (
    AUTHORITY_FATAL_OUTCOMES,
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
from product_intelligence.research.specifications import SourceAuthority


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_identity() -> ProductIdentity:
    return ProductIdentity(
        manufacturer_part_number="XP15360SE70005",
        normalized_part_number="15360SE70005",
        match_type=IdentityMatchType.EXACT,
        manufacturer="Seagate",
        product_name="Nytro 5050",
    )


# ---------------------------------------------------------------------------
# AuthorityAttemptResult invariants
# ---------------------------------------------------------------------------


class TestAuthorityAttemptResult:
    """AuthorityAttemptResult enforces state-dependent field shape."""

    def test_matched_requires_source_and_mpn(self) -> None:
        result = AuthorityAttemptResult(
            outcome=AuthorityAuditOutcomeKind.MATCHED,
            source_name="Seagate Support",
            source_url="https://www.seagate.com/support/",
            matched_mpn="XP15360SE70005",
        )
        assert result.outcome is AuthorityAuditOutcomeKind.MATCHED

    def test_matched_rejects_missing_source_name(self) -> None:
        with pytest.raises(ValueError, match="source_name"):
            AuthorityAttemptResult(
                outcome=AuthorityAuditOutcomeKind.MATCHED,
                source_name=None,
                source_url="https://example.com/",
                matched_mpn="XP",
            )

    def test_matched_rejects_missing_source_url(self) -> None:
        with pytest.raises(ValueError, match="source_url"):
            AuthorityAttemptResult(
                outcome=AuthorityAuditOutcomeKind.MATCHED,
                source_name="Source",
                source_url=None,
                matched_mpn="XP",
            )

    def test_matched_rejects_missing_mpn(self) -> None:
        with pytest.raises(ValueError, match="matched_mpn"):
            AuthorityAttemptResult(
                outcome=AuthorityAuditOutcomeKind.MATCHED,
                source_name="Source",
                source_url="https://example.com/",
                matched_mpn=None,
            )

    def test_no_requested_mpn_allows_none_sources(self) -> None:
        result = AuthorityAttemptResult(
            outcome=AuthorityAuditOutcomeKind.NO_REQUESTED_MPN,
        )
        assert result.source_name is None
        assert result.source_url is None
        assert result.matched_mpn is None

    def test_no_requested_mpn_rejects_matched_mpn(self) -> None:
        with pytest.raises(ValueError, match="NO_REQUESTED_MPN"):
            AuthorityAttemptResult(
                outcome=AuthorityAuditOutcomeKind.NO_REQUESTED_MPN,
                matched_mpn="XP",
            )

    def test_source_backed_requires_source_fields(self) -> None:
        """All source-backed outcomes require source_name and source_url."""
        for outcome in [
            AuthorityAuditOutcomeKind.NO_MPN_IN_SOURCE,
            AuthorityAuditOutcomeKind.AMBIGUOUS_MPN_MATCH,
            AuthorityAuditOutcomeKind.AUTHORITY_FETCH_FAILED,
            AuthorityAuditOutcomeKind.AUTHORITY_SOURCE_REFUSED,
            AuthorityAuditOutcomeKind.AUTHORITY_HOST_ESCAPED,
            AuthorityAuditOutcomeKind.NO_STRUCTURAL_OBSERVATIONS,
        ]:
            result = AuthorityAttemptResult(
                outcome=outcome,
                source_name="Source",
                source_url="https://example.com/",
            )
            assert result.source_name == "Source"


# ---------------------------------------------------------------------------
# DatasheetAttemptResult invariants
# ---------------------------------------------------------------------------


class TestDatasheetAttemptResult:
    """DatasheetAttemptResult enforces state-dependent field shape."""

    def test_no_datasheet_source_rejects_fabricated_provenance(self) -> None:
        """NO_DATASHEET_SOURCE must have all provenance None."""
        with pytest.raises(ValueError, match="source_name"):
            DatasheetAttemptResult(
                outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
                source_name="Fabricated",
            )

        with pytest.raises(ValueError, match="source_url"):
            DatasheetAttemptResult(
                outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
                source_url="https://fabricated.com/",
            )

        with pytest.raises(ValueError, match="final_url"):
            DatasheetAttemptResult(
                outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
                final_url="https://fabricated.com/",
            )

        with pytest.raises(ValueError, match="retrieved_at"):
            DatasheetAttemptResult(
                outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
                retrieved_at="2025-01-01",
            )

    def test_no_datasheet_source_clean(self) -> None:
        """NO_DATASHEET_SOURCE with no provenance is valid."""
        result = DatasheetAttemptResult(
            outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
        )
        assert result.source_name is None
        assert result.source_url is None

    def test_enriched_requires_observation_count(self) -> None:
        with pytest.raises(ValueError, match="observation_count"):
            DatasheetAttemptResult(
                outcome=DatasheetAuditOutcomeKind.ENRICHED,
                source_name="Source",
                source_url="https://example.com/",
                observation_count=None,
            )

    def test_enriched_valid(self) -> None:
        result = DatasheetAttemptResult(
            outcome=DatasheetAuditOutcomeKind.ENRICHED,
            source_name="Seagate Datasheet",
            source_url="https://example.com/ds.pdf",
            observation_count=6,
        )
        assert result.observation_count == 6


# ---------------------------------------------------------------------------
# ComparableResearchResult FULL kind
# ---------------------------------------------------------------------------


class TestComparableResearchResultFull:
    """FULL kind invariants."""

    def test_full_valid(self) -> None:
        """A valid FULL result."""
        identity = _make_identity()
        result = ComparableResearchResult(
            kind=ComparableResultKind.FULL,
            target_mpn="XP15360SE70005",
            target_manufacturer="Seagate",
            target_enrichment_audit=ProductEnrichmentAudit(
                target_identity=identity,
                authority_audit=(AuthorityAttemptResult(
                    outcome=AuthorityAuditOutcomeKind.MATCHED,
                    source_name="Seagate Support",
                    source_url="https://www.seagate.com/support/",
                    matched_mpn="XP15360SE70005",
                ),),
                datasheet_audit=(DatasheetAttemptResult(
                    outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
                ),),
            ),
            authority_audit=(
                AuthorityAttemptResult(
                    outcome=AuthorityAuditOutcomeKind.MATCHED,
                    source_name="Seagate Support",
                    source_url="https://www.seagate.com/support/",
                    matched_mpn="XP15360SE70005",
                ),
            ),
            candidates=(),
            candidate_enrichment_audits=(),
        )
        assert result.kind is ComparableResultKind.FULL

    def test_full_rejects_empty_target_mpn(self) -> None:
        identity = _make_identity()
        with pytest.raises(ValueError, match="target_mpn"):
            ComparableResearchResult(
                kind=ComparableResultKind.FULL,
                target_mpn="",
                target_manufacturer="Seagate",
                target_enrichment_audit=ProductEnrichmentAudit(
                    target_identity=identity,
                    authority_audit=(AuthorityAttemptResult(
                        outcome=AuthorityAuditOutcomeKind.MATCHED,
                        source_name="S",
                        source_url="https://example.com/",
                        matched_mpn="XP",
                    ),),
                ),
                authority_audit=(AuthorityAttemptResult(
                    outcome=AuthorityAuditOutcomeKind.MATCHED,
                    source_name="S",
                    source_url="https://example.com/",
                    matched_mpn="XP",
                ),),
                candidates=(),
                candidate_enrichment_audits=(),
            )

    def test_full_rejects_empty_target_manufacturer(self) -> None:
        identity = _make_identity()
        with pytest.raises(ValueError, match="target_manufacturer"):
            ComparableResearchResult(
                kind=ComparableResultKind.FULL,
                target_mpn="XP15360SE70005",
                target_manufacturer="",
                target_enrichment_audit=ProductEnrichmentAudit(
                    target_identity=identity,
                    authority_audit=(AuthorityAttemptResult(
                        outcome=AuthorityAuditOutcomeKind.MATCHED,
                        source_name="S",
                        source_url="https://example.com/",
                        matched_mpn="XP",
                    ),),
                ),
                authority_audit=(AuthorityAttemptResult(
                    outcome=AuthorityAuditOutcomeKind.MATCHED,
                    source_name="S",
                    source_url="https://example.com/",
                    matched_mpn="XP",
                ),),
                candidates=(),
                candidate_enrichment_audits=(),
            )

    def test_full_requires_exactly_one_matched(self) -> None:
        identity = _make_identity()
        with pytest.raises(ValueError, match="exactly one MATCHED"):
            ComparableResearchResult(
                kind=ComparableResultKind.FULL,
                target_mpn="XP15360SE70005",
                target_manufacturer="Seagate",
                target_enrichment_audit=ProductEnrichmentAudit(
                    target_identity=identity,
                    authority_audit=(AuthorityAttemptResult(
                        outcome=AuthorityAuditOutcomeKind.NO_MPN_IN_SOURCE,
                        source_name="S1",
                        source_url="https://s1.com/",
                    ),),
                ),
                authority_audit=(AuthorityAttemptResult(
                    outcome=AuthorityAuditOutcomeKind.NO_MPN_IN_SOURCE,
                    source_name="S1",
                    source_url="https://s1.com/",
                ),),
                candidates=(),
                candidate_enrichment_audits=(),
            )

    def test_full_rejects_ambiguous_in_audit(self) -> None:
        identity = _make_identity()
        with pytest.raises(ValueError, match="AMBIGUOUS_MPN_MATCH"):
            ComparableResearchResult(
                kind=ComparableResultKind.FULL,
                target_mpn="XP15360SE70005",
                target_manufacturer="Seagate",
                target_enrichment_audit=ProductEnrichmentAudit(
                    target_identity=identity,
                    authority_audit=(AuthorityAttemptResult(
                        outcome=AuthorityAuditOutcomeKind.AMBIGUOUS_MPN_MATCH,
                        source_name="S",
                        source_url="https://example.com/",
                    ),),
                ),
                authority_audit=(
                    AuthorityAttemptResult(
                        outcome=AuthorityAuditOutcomeKind.MATCHED,
                        source_name="S",
                        source_url="https://example.com/",
                        matched_mpn="XP",
                    ),
                    AuthorityAttemptResult(
                        outcome=AuthorityAuditOutcomeKind.AMBIGUOUS_MPN_MATCH,
                        source_name="S2",
                        source_url="https://s2.com/",
                    ),
                ),
                candidates=(),
                candidate_enrichment_audits=(),
            )

    def test_full_requires_non_matched_is_no_mpn_in_source(self) -> None:
        identity = _make_identity()
        with pytest.raises(ValueError, match="NO_MPN_IN_SOURCE"):
            ComparableResearchResult(
                kind=ComparableResultKind.FULL,
                target_mpn="XP15360SE70005",
                target_manufacturer="Seagate",
                target_enrichment_audit=ProductEnrichmentAudit(
                    target_identity=identity,
                    authority_audit=(AuthorityAttemptResult(
                        outcome=AuthorityAuditOutcomeKind.MATCHED,
                        source_name="S",
                        source_url="https://example.com/",
                        matched_mpn="XP",
                    ),),
                ),
                authority_audit=(
                    AuthorityAttemptResult(
                        outcome=AuthorityAuditOutcomeKind.MATCHED,
                        source_name="S",
                        source_url="https://example.com/",
                        matched_mpn="XP",
                    ),
                    AuthorityAttemptResult(
                        outcome=AuthorityAuditOutcomeKind.NO_REQUESTED_MPN,
                    ),
                ),
                candidates=(),
                candidate_enrichment_audits=(),
            )

    def test_full_rejects_fatal_authority_outcome(self) -> None:
        """Any fatal outcome in authority_audit rejects COMPLETED."""
        identity = _make_identity()
        for fatal in AUTHORITY_FATAL_OUTCOMES:
            with pytest.raises(ValueError, match=fatal.value):
                ComparableResearchResult(
                    kind=ComparableResultKind.FULL,
                    target_mpn="XP15360SE70005",
                    target_manufacturer="Seagate",
                    target_enrichment_audit=ProductEnrichmentAudit(
                        target_identity=identity,
                        authority_audit=(AuthorityAttemptResult(
                            outcome=AuthorityAuditOutcomeKind.MATCHED,
                            source_name="S",
                            source_url="https://example.com/",
                            matched_mpn="XP",
                        ),),
                    ),
                    authority_audit=(AuthorityAttemptResult(
                        outcome=fatal,
                        source_name="S",
                        source_url="https://example.com/",
                    ),),
                    candidates=(),
                    candidate_enrichment_audits=(),
                )


# ---------------------------------------------------------------------------
# ComparableResearchResult NO_AUTHORITY_MATCH kind
# ---------------------------------------------------------------------------


class TestComparableResearchResultNoAuthorityMatch:
    """NO_AUTHORITY_MATCH kind invariants."""

    def test_no_authority_match_valid(self) -> None:
        result = ComparableResearchResult(
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
        assert result.kind is ComparableResultKind.NO_AUTHORITY_MATCH

    def test_no_authority_match_rejects_candidates(self) -> None:
        identity = _make_identity()
        # Build a minimal candidate for the test
        with pytest.raises(ValueError, match="empty candidates"):
            ComparableResearchResult(
                kind=ComparableResultKind.NO_AUTHORITY_MATCH,
                target_mpn="UNKNOWN",
                target_manufacturer=None,
                target_enrichment_audit=None,
                authority_audit=(AuthorityAttemptResult(
                    outcome=AuthorityAuditOutcomeKind.NO_MPN_IN_SOURCE,
                    source_name="S",
                    source_url="https://example.com/",
                ),),
                candidates=(ComparableCandidateResult(  # type: ignore[call-arg]
                    candidate=_make_candidate(),
                    enrichment_audit=ProductEnrichmentAudit(
                        target_identity=identity,
                        authority_audit=(AuthorityAttemptResult(
                            outcome=AuthorityAuditOutcomeKind.NO_MPN_IN_SOURCE,
                            source_name="S",
                            source_url="https://example.com/",
                        ),),
                    ),
                ),),
                candidate_enrichment_audits=(ProductEnrichmentAudit(
                    target_identity=identity,
                    authority_audit=(AuthorityAttemptResult(
                        outcome=AuthorityAuditOutcomeKind.NO_MPN_IN_SOURCE,
                        source_name="S",
                        source_url="https://example.com/",
                    ),),
                ),),
            )

    def test_no_authority_match_rejects_fabricated_manufacturer(self) -> None:
        with pytest.raises(ValueError, match="fabricated"):
            ComparableResearchResult(
                kind=ComparableResultKind.NO_AUTHORITY_MATCH,
                target_mpn="UNKNOWN",
                target_manufacturer="Guessed Manufacturer",
                target_enrichment_audit=None,
                authority_audit=(AuthorityAttemptResult(
                    outcome=AuthorityAuditOutcomeKind.NO_MPN_IN_SOURCE,
                    source_name="S",
                    source_url="https://example.com/",
                ),),
                candidates=(),
                candidate_enrichment_audits=(),
            )


# ---------------------------------------------------------------------------
# ComparableResearchResult NO_REQUESTED_MPN kind
# ---------------------------------------------------------------------------


class TestComparableResearchResultNoRequestedMpn:
    """NO_REQUESTED_MPN kind invariants."""

    def test_no_requested_mpn_valid(self) -> None:
        result = ComparableResearchResult(
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
        assert result.kind is ComparableResultKind.NO_REQUESTED_MPN

    def test_no_requested_mpn_rejects_fabricated_manufacturer(self) -> None:
        with pytest.raises(ValueError, match="fabricated"):
            ComparableResearchResult(
                kind=ComparableResultKind.NO_REQUESTED_MPN,
                target_mpn="",
                target_manufacturer="Guessed",
                target_enrichment_audit=None,
                authority_audit=(AuthorityAttemptResult(
                    outcome=AuthorityAuditOutcomeKind.NO_REQUESTED_MPN,
                ),),
                candidates=(),
                candidate_enrichment_audits=(),
            )


# ---------------------------------------------------------------------------
# ComparableResearchResult AMBIGUOUS_AUTHORITY kind
# ---------------------------------------------------------------------------


class TestComparableResearchResultAmbiguousAuthority:
    """AMBIGUOUS_AUTHORITY kind invariants."""

    def test_ambiguous_via_ambiguous_mpn(self) -> None:
        result = ComparableResearchResult(
            kind=ComparableResultKind.AMBIGUOUS_AUTHORITY,
            target_mpn="AMBIGUOUS",
            target_manufacturer=None,
            target_enrichment_audit=None,
            authority_audit=(
                AuthorityAttemptResult(
                    outcome=AuthorityAuditOutcomeKind.AMBIGUOUS_MPN_MATCH,
                    source_name="S",
                    source_url="https://example.com/",
                ),
            ),
            candidates=(),
            candidate_enrichment_audits=(),
        )
        assert result.kind is ComparableResultKind.AMBIGUOUS_AUTHORITY

    def test_ambiguous_via_multiple_matched(self) -> None:
        result = ComparableResearchResult(
            kind=ComparableResultKind.AMBIGUOUS_AUTHORITY,
            target_mpn="AMBIGUOUS",
            target_manufacturer=None,
            target_enrichment_audit=None,
            authority_audit=(
                AuthorityAttemptResult(
                    outcome=AuthorityAuditOutcomeKind.MATCHED,
                    source_name="S1",
                    source_url="https://s1.com/",
                    matched_mpn="AMBIGUOUS",
                ),
                AuthorityAttemptResult(
                    outcome=AuthorityAuditOutcomeKind.MATCHED,
                    source_name="S2",
                    source_url="https://s2.com/",
                    matched_mpn="AMBIGUOUS",
                ),
            ),
            candidates=(),
            candidate_enrichment_audits=(),
        )
        assert result.kind is ComparableResultKind.AMBIGUOUS_AUTHORITY

    def test_ambiguous_rejects_no_ambiguous_or_multi(self) -> None:
        with pytest.raises(ValueError, match="AMBIGUOUS_MPN_MATCH"):
            ComparableResearchResult(
                kind=ComparableResultKind.AMBIGUOUS_AUTHORITY,
                target_mpn="X",
                target_manufacturer=None,
                target_enrichment_audit=None,
                authority_audit=(AuthorityAttemptResult(
                    outcome=AuthorityAuditOutcomeKind.MATCHED,
                    source_name="S",
                    source_url="https://example.com/",
                    matched_mpn="X",
                ),),
                candidates=(),
                candidate_enrichment_audits=(),
            )


# ---------------------------------------------------------------------------
# Cross-kind contradiction check
# ---------------------------------------------------------------------------


class TestContradictoryAuthorityMix:
    """NO_MPN_IN_SOURCE + NO_REQUESTED_MPN mix is rejected."""

    def test_rejects_mixed_outcomes(self) -> None:
        """Mixed NO_MPN_IN_SOURCE + NO_REQUESTED_MPN is caught either by
        kind-specific validation or the cross-kind contradiction check."""
        with pytest.raises(ValueError):
            ComparableResearchResult(
                kind=ComparableResultKind.NO_AUTHORITY_MATCH,
                target_mpn="UNKNOWN",
                target_manufacturer=None,
                target_enrichment_audit=None,
                authority_audit=(
                    AuthorityAttemptResult(
                        outcome=AuthorityAuditOutcomeKind.NO_MPN_IN_SOURCE,
                        source_name="S1",
                        source_url="https://s1.com/",
                    ),
                    AuthorityAttemptResult(
                        outcome=AuthorityAuditOutcomeKind.NO_REQUESTED_MPN,
                    ),
                ),
                candidates=(),
                candidate_enrichment_audits=(),
            )


# ---------------------------------------------------------------------------
# Helper for candidate tests
# ---------------------------------------------------------------------------


def _make_candidate() -> ComparableCandidate:
    """Build a minimal ComparableCandidate for testing."""
    identity = _make_identity()
    observation = ComparableCandidateObservation(
        manufacturer_part_number_raw="XP15360SE70015",
        product_name_raw="Nytro 5050 15.36TB",
        source_name="Seagate Support",
        source_url="https://www.seagate.com/support/",
        retrieved_at=datetime.now(timezone.utc),
        source_authority=SourceAuthority.AUTHORITATIVE,
    )
    assessment = ComparableCandidateAssessment.build(identity, observation)
    return ComparableCandidate(
        manufacturer_part_number="XP15360SE70015",
        normalized_part_number="XP15360SE70015",
        evidence=(assessment,),
    )


# ---------------------------------------------------------------------------
# EvidenceSourceReference and FieldAssessmentResult
# ---------------------------------------------------------------------------


class TestEvidenceSourceReference:
    """EvidenceSourceReference contract."""

    def test_valid(self) -> None:
        ref = EvidenceSourceReference(
            source_name="Seagate Support",
            source_url="https://www.seagate.com/support/",
            layer=EvidenceLayer.SUPPORT_PAGE,
        )
        assert ref.layer is EvidenceLayer.SUPPORT_PAGE

    def test_rejects_empty_source_name(self) -> None:
        with pytest.raises(ValueError, match="source_name"):
            EvidenceSourceReference(
                source_name="",
                source_url="https://example.com/",
                layer=EvidenceLayer.SUPPORT_PAGE,
            )


class TestFieldAssessmentResult:
    """FieldAssessmentResult contract."""

    def test_valid(self) -> None:
        fa = FieldAssessmentResult(
            field_name="capacity",
            target_value="15.36 TB",
            candidate_value="3.84 TB",
        )
        assert fa.field_name == "capacity"

    def test_rejects_empty_field_name(self) -> None:
        with pytest.raises(ValueError, match="field_name"):
            FieldAssessmentResult(
                field_name="",
                target_value="x",
                candidate_value="y",
            )
