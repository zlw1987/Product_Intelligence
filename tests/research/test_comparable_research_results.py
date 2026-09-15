"""Pure ComparableResearchResult construction invariant tests (7C-A/FU1).

Tests for:
- AuthorityAuditOutcomeKind and AUTHORITY_FATAL_OUTCOMES
- DatasheetAuditOutcomeKind
- ComparableResultKind
- AuthorityAttemptResult state-dependent field shape (BLOCKER 4)
- DatasheetAttemptResult state-dependent field shape
- ProductEnrichmentAudit (BLOCKER 3 - simplified shape)
- EvidenceSourceReference (with source_authority + retrieved_at)
- FieldAssessmentResult (BLOCKER 2 - comparison_state, field_similarity)
- ComparableCandidateResult (BLOCKER 2 - scalar projection)
- ComparableResearchResult kind-specific invariants
- Impossible-state rejection
- NO_MPN_IN_SOURCE + NO_REQUESTED_MPN contradiction
- ComparisonState enum import
"""

from __future__ import annotations

from decimal import Decimal

import pytest

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


def _make_evidence_ref() -> EvidenceSourceReference:
    return EvidenceSourceReference(
        source_name="Seagate Support",
        source_url="https://www.seagate.com/support/",
        evidence_layer=EvidenceLayer.SUPPORT_PAGE,
        source_authority=SourceAuthority.AUTHORITATIVE,
        retrieved_at="2025-01-01T00:00:00+00:00",
    )


# ---------------------------------------------------------------------------
# AuthorityAttemptResult invariants (BLOCKER 4)
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

    # --- BLOCKER 4: Non-MATCHED outcomes must NOT have matched_mpn ---

    def test_non_matched_no_mpn_in_source_rejects_faked_matched_mpn(self) -> None:
        """NO_MPN_IN_SOURCE + matched_mpn='FAKE' must fail."""
        with pytest.raises(ValueError, match="non-MATCHED"):
            AuthorityAttemptResult(
                outcome=AuthorityAuditOutcomeKind.NO_MPN_IN_SOURCE,
                source_name="S",
                source_url="https://example.com/",
                matched_mpn="FAKE",
            )

    def test_non_matched_ambiguous_rejects_faked_matched_mpn(self) -> None:
        """AMBIGUOUS_MPN_MATCH + matched_mpn='FAKE' must fail."""
        with pytest.raises(ValueError, match="non-MATCHED"):
            AuthorityAttemptResult(
                outcome=AuthorityAuditOutcomeKind.AMBIGUOUS_MPN_MATCH,
                source_name="S",
                source_url="https://example.com/",
                matched_mpn="FAKE",
            )

    def test_non_matched_fetch_failed_rejects_faked_matched_mpn(self) -> None:
        """AUTHORITY_FETCH_FAILED + matched_mpn='FAKE' must fail."""
        with pytest.raises(ValueError, match="non-MATCHED"):
            AuthorityAttemptResult(
                outcome=AuthorityAuditOutcomeKind.AUTHORITY_FETCH_FAILED,
                source_name="S",
                source_url="https://example.com/",
                matched_mpn="FAKE",
            )

    def test_non_matched_source_refused_rejects_faked_matched_mpn(self) -> None:
        """AUTHORITY_SOURCE_REFUSED + matched_mpn='FAKE' must fail."""
        with pytest.raises(ValueError, match="non-MATCHED"):
            AuthorityAttemptResult(
                outcome=AuthorityAuditOutcomeKind.AUTHORITY_SOURCE_REFUSED,
                source_name="S",
                source_url="https://example.com/",
                matched_mpn="FAKE",
            )

    def test_non_matched_host_escaped_rejects_faked_matched_mpn(self) -> None:
        """AUTHORITY_HOST_ESCAPED + matched_mpn='FAKE' must fail."""
        with pytest.raises(ValueError, match="non-MATCHED"):
            AuthorityAttemptResult(
                outcome=AuthorityAuditOutcomeKind.AUTHORITY_HOST_ESCAPED,
                source_name="S",
                source_url="https://example.com/",
                matched_mpn="FAKE",
            )

    def test_non_matched_no_structural_obs_rejects_faked_matched_mpn(self) -> None:
        """NO_STRUCTURAL_OBSERVATIONS + matched_mpn='FAKE' must fail."""
        with pytest.raises(ValueError, match="non-MATCHED"):
            AuthorityAttemptResult(
                outcome=AuthorityAuditOutcomeKind.NO_STRUCTURAL_OBSERVATIONS,
                source_name="S",
                source_url="https://example.com/",
                matched_mpn="FAKE",
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
            assert result.matched_mpn is None


# ---------------------------------------------------------------------------
# DatasheetAttemptResult invariants
# ---------------------------------------------------------------------------


class TestDatasheetAttemptResult:
    """DatasheetAttemptResult enforces state-dependent field shape."""

    def test_no_datasheet_source_rejects_fabricated_provenance(self) -> None:
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
# ProductEnrichmentAudit (BLOCKER 3 - simplified shape)
# ---------------------------------------------------------------------------


class TestProductEnrichmentAudit:
    """ProductEnrichmentAudit represents only per-product 6D enrichment."""

    def test_valid(self) -> None:
        audit = ProductEnrichmentAudit(
            product_mpn="XP15360SE70005",
            attempts=(DatasheetAttemptResult(
                outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
            ),),
        )
        assert audit.product_mpn == "XP15360SE70005"
        assert len(audit.attempts) == 1

    def test_empty_attempts_allowed(self) -> None:
        audit = ProductEnrichmentAudit(product_mpn="XP15360SE70005")
        assert audit.attempts == ()

    def test_rejects_empty_product_mpn(self) -> None:
        with pytest.raises(ValueError, match="product_mpn"):
            ProductEnrichmentAudit(product_mpn="")

    def test_rejects_non_string_product_mpn(self) -> None:
        with pytest.raises(TypeError, match="product_mpn"):
            ProductEnrichmentAudit(product_mpn=123)  # type: ignore[arg-type]

    def test_rejects_non_tuple_attempts(self) -> None:
        with pytest.raises(TypeError, match="attempts"):
            ProductEnrichmentAudit(
                product_mpn="XP",
                attempts=[DatasheetAttemptResult(  # type: ignore[arg-type]
                    outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
                )],
            )

    def test_rejects_bad_attempt_type(self) -> None:
        with pytest.raises(TypeError, match="attempts\\[0\\]"):
            ProductEnrichmentAudit(
                product_mpn="XP",
                attempts=("not_an_attempt",),  # type: ignore[arg-type]
            )

    def test_no_authority_audit_field(self) -> None:
        """ProductEnrichmentAudit must NOT have authority_audit."""
        audit = ProductEnrichmentAudit(product_mpn="XP")
        assert not hasattr(audit, "authority_audit")

    def test_no_target_identity_field(self) -> None:
        """ProductEnrichmentAudit must NOT have target_identity."""
        audit = ProductEnrichmentAudit(product_mpn="XP")
        assert not hasattr(audit, "target_identity")

    def test_no_specification_set_field(self) -> None:
        """ProductEnrichmentAudit must NOT have specification_set."""
        audit = ProductEnrichmentAudit(product_mpn="XP")
        assert not hasattr(audit, "specification_set")


# ---------------------------------------------------------------------------
# EvidenceSourceReference (with source_authority + retrieved_at)
# ---------------------------------------------------------------------------


class TestEvidenceSourceReference:
    """EvidenceSourceReference preserves frozen PRE2 provenance contract."""

    def test_valid(self) -> None:
        ref = EvidenceSourceReference(
            source_name="Seagate Support",
            source_url="https://www.seagate.com/support/",
            evidence_layer=EvidenceLayer.SUPPORT_PAGE,
            source_authority=SourceAuthority.AUTHORITATIVE,
            retrieved_at="2025-01-01T00:00:00+00:00",
        )
        assert ref.evidence_layer is EvidenceLayer.SUPPORT_PAGE
        assert ref.source_authority is SourceAuthority.AUTHORITATIVE
        assert ref.retrieved_at == "2025-01-01T00:00:00+00:00"

    def test_rejects_empty_source_name(self) -> None:
        with pytest.raises(ValueError, match="source_name"):
            EvidenceSourceReference(
                source_name="",
                source_url="https://example.com/",
                evidence_layer=EvidenceLayer.SUPPORT_PAGE,
                source_authority=SourceAuthority.AUTHORITATIVE,
                retrieved_at="2025-01-01",
            )

    def test_requires_source_authority(self) -> None:
        """source_authority is required (frozen PRE2 provenance contract)."""
        assert EvidenceSourceReference(
            source_name="S",
            source_url="https://example.com/",
            evidence_layer=EvidenceLayer.DATASHEET_PDF,
            source_authority=SourceAuthority.AUTHORITATIVE,
            retrieved_at="2025-01-01",
        )

    def test_requires_retrieved_at(self) -> None:
        """retrieved_at is required (frozen PRE2 provenance contract)."""
        ref = EvidenceSourceReference(
            source_name="S",
            source_url="https://example.com/",
            evidence_layer=EvidenceLayer.SUPPORT_PAGE,
            source_authority=SourceAuthority.SECONDARY,
            retrieved_at="2025-06-01T12:00:00+00:00",
        )
        assert ref.retrieved_at == "2025-06-01T12:00:00+00:00"


# ---------------------------------------------------------------------------
# FieldAssessmentResult (BLOCKER 2 - comparison_state, field_similarity)
# ---------------------------------------------------------------------------


class TestFieldAssessmentResult:
    """FieldAssessmentResult carries frozen 7B comparison semantics."""

    def test_scored_valid(self) -> None:
        fa = FieldAssessmentResult(
            definition_key="capacity",
            comparison_state=ComparisonState.SCORED,
            target_resolution_state=ResolutionState.VERIFIED,
            candidate_resolution_state=ResolutionState.VERIFIED,
            field_similarity=Decimal("1"),
            target_value="15.36 TB",
            candidate_value="15.36 TB",
        )
        assert fa.comparison_state is ComparisonState.SCORED
        assert fa.field_similarity == Decimal("1")

    def test_scored_requires_decimal_similarity(self) -> None:
        with pytest.raises(ValueError, match="SCORED comparison requires"):
            FieldAssessmentResult(
                definition_key="capacity",
                comparison_state=ComparisonState.SCORED,
                target_resolution_state=ResolutionState.VERIFIED,
                candidate_resolution_state=ResolutionState.VERIFIED,
                field_similarity=None,
                target_value="x",
                candidate_value="y",
            )

    def test_scored_rejects_non_decimal_similarity(self) -> None:
        with pytest.raises(TypeError, match="field_similarity must be Decimal"):
            FieldAssessmentResult(
                definition_key="capacity",
                comparison_state=ComparisonState.SCORED,
                target_resolution_state=ResolutionState.VERIFIED,
                candidate_resolution_state=ResolutionState.VERIFIED,
                field_similarity=1.0,  # float, not Decimal
                target_value="x",
                candidate_value="y",
            )

    def test_scored_rejects_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="not in range"):
            FieldAssessmentResult(
                definition_key="capacity",
                comparison_state=ComparisonState.SCORED,
                target_resolution_state=ResolutionState.VERIFIED,
                candidate_resolution_state=ResolutionState.VERIFIED,
                field_similarity=Decimal("2"),
                target_value="x",
                candidate_value="y",
            )

    def test_both_not_verified_requires_none_similarity(self) -> None:
        with pytest.raises(ValueError, match="must have field_similarity=None"):
            FieldAssessmentResult(
                definition_key="capacity",
                comparison_state=ComparisonState.BOTH_NOT_VERIFIED,
                target_resolution_state=ResolutionState.UNKNOWN,
                candidate_resolution_state=ResolutionState.UNKNOWN,
                field_similarity=Decimal("0.5"),
                target_value=None,
                candidate_value=None,
            )

    def test_both_not_verified_valid(self) -> None:
        fa = FieldAssessmentResult(
            definition_key="capacity",
            comparison_state=ComparisonState.BOTH_NOT_VERIFIED,
            target_resolution_state=ResolutionState.UNKNOWN,
            candidate_resolution_state=ResolutionState.UNKNOWN,
            field_similarity=None,
            target_value=None,
            candidate_value=None,
        )
        assert fa.field_similarity is None

    def test_target_not_verified_valid(self) -> None:
        fa = FieldAssessmentResult(
            definition_key="capacity",
            comparison_state=ComparisonState.TARGET_NOT_VERIFIED,
            target_resolution_state=ResolutionState.UNKNOWN,
            candidate_resolution_state=ResolutionState.VERIFIED,
            field_similarity=None,
            target_value=None,
            candidate_value="15.36 TB",
        )
        assert fa.field_similarity is None

    def test_candidate_not_verified_valid(self) -> None:
        fa = FieldAssessmentResult(
            definition_key="capacity",
            comparison_state=ComparisonState.CANDIDATE_NOT_VERIFIED,
            target_resolution_state=ResolutionState.VERIFIED,
            candidate_resolution_state=ResolutionState.UNKNOWN,
            field_similarity=None,
            target_value="15.36 TB",
            candidate_value=None,
        )
        assert fa.field_similarity is None

    def test_rejects_empty_definition_key(self) -> None:
        with pytest.raises(ValueError, match="definition_key"):
            FieldAssessmentResult(
                definition_key="",
                comparison_state=ComparisonState.BOTH_NOT_VERIFIED,
                target_resolution_state=ResolutionState.UNKNOWN,
                candidate_resolution_state=ResolutionState.UNKNOWN,
                field_similarity=None,
                target_value=None,
                candidate_value=None,
            )

    def test_with_evidence(self) -> None:
        ref = _make_evidence_ref()
        fa = FieldAssessmentResult(
            definition_key="capacity",
            comparison_state=ComparisonState.SCORED,
            target_resolution_state=ResolutionState.VERIFIED,
            candidate_resolution_state=ResolutionState.VERIFIED,
            field_similarity=Decimal("1"),
            target_value="15.36 TB",
            candidate_value="15.36 TB",
            target_evidence=(ref,),
            candidate_evidence=(ref,),
        )
        assert len(fa.target_evidence) == 1
        assert len(fa.candidate_evidence) == 1


# ---------------------------------------------------------------------------
# ComparableCandidateResult (BLOCKER 2 - scalar projection)
# ---------------------------------------------------------------------------


class TestComparableCandidateResult:
    """ComparableCandidateResult uses pure scalar projection."""

    def test_valid(self) -> None:
        result = ComparableCandidateResult(
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
                ),
            ),
            enrichment_audit=_make_candidate_enrichment_audit(),
        )
        assert result.candidate_mpn == "XP15360SE70015"
        assert result.scored_field_count == 7

    def test_rejects_empty_candidate_mpn(self) -> None:
        with pytest.raises(ValueError, match="candidate_mpn"):
            ComparableCandidateResult(
                candidate_mpn="",
                candidate_normalized_mpn="X",
                scored_field_count=0,
                evidence_coverage=Decimal("0"),
                observed_similarity=None,
                evidence_weighted_similarity=None,
                field_assessments=(),
                enrichment_audit=_make_candidate_enrichment_audit(),
            )

    def test_zero_scored_requires_none_similarities(self) -> None:
        with pytest.raises(ValueError, match="observed_similarity=None"):
            ComparableCandidateResult(
                candidate_mpn="XP",
                candidate_normalized_mpn="XP",
                scored_field_count=0,
                evidence_coverage=Decimal("0"),
                observed_similarity=Decimal("0"),
                evidence_weighted_similarity=None,
                field_assessments=(),
                enrichment_audit=_make_candidate_enrichment_audit(),
            )

    def test_rejects_non_int_scored_field_count(self) -> None:
        with pytest.raises(TypeError, match="scored_field_count"):
            ComparableCandidateResult(
                candidate_mpn="XP",
                candidate_normalized_mpn="XP",
                scored_field_count=True,  # bool, not int
                evidence_coverage=Decimal("0"),
                observed_similarity=None,
                evidence_weighted_similarity=None,
                field_assessments=(),
                enrichment_audit=_make_candidate_enrichment_audit(),
            )

    def test_rejects_non_decimal_evidence_coverage(self) -> None:
        with pytest.raises(TypeError, match="evidence_coverage"):
            ComparableCandidateResult(
                candidate_mpn="XP",
                candidate_normalized_mpn="XP",
                scored_field_count=0,
                evidence_coverage=0.0,  # float, not Decimal
                observed_similarity=None,
                evidence_weighted_similarity=None,
                field_assessments=(),
                enrichment_audit=_make_candidate_enrichment_audit(),
            )

    def test_no_candidate_object_field(self) -> None:
        """ComparableCandidateResult must NOT have a candidate object field."""
        result = ComparableCandidateResult(
            candidate_mpn="XP",
            candidate_normalized_mpn="XP",
            scored_field_count=0,
            evidence_coverage=Decimal("0"),
            observed_similarity=None,
            evidence_weighted_similarity=None,
            field_assessments=(),
            enrichment_audit=_make_candidate_enrichment_audit(),
        )
        assert not hasattr(result, "candidate")


# ---------------------------------------------------------------------------
# ComparableResearchResult FULL kind
# ---------------------------------------------------------------------------


class TestComparableResearchResultFull:
    """FULL kind invariants."""

    def test_full_valid(self) -> None:
        result = ComparableResearchResult(
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
            candidates=(),
        )
        assert result.kind is ComparableResultKind.FULL

    def test_full_rejects_empty_target_mpn(self) -> None:
        with pytest.raises(ValueError, match="target_mpn"):
            ComparableResearchResult(
                kind=ComparableResultKind.FULL,
                target_mpn="",
                target_manufacturer="Seagate",
                target_enrichment_audit=_make_target_enrichment_audit(),
                authority_audit=(AuthorityAttemptResult(
                    outcome=AuthorityAuditOutcomeKind.MATCHED,
                    source_name="S",
                    source_url="https://example.com/",
                    matched_mpn="XP",
                ),),
                candidates=(),
            )

    def test_full_rejects_empty_target_manufacturer(self) -> None:
        with pytest.raises(ValueError, match="target_manufacturer"):
            ComparableResearchResult(
                kind=ComparableResultKind.FULL,
                target_mpn="XP15360SE70005",
                target_manufacturer="",
                target_enrichment_audit=_make_target_enrichment_audit(),
                authority_audit=(AuthorityAttemptResult(
                    outcome=AuthorityAuditOutcomeKind.MATCHED,
                    source_name="S",
                    source_url="https://example.com/",
                    matched_mpn="XP",
                ),),
                candidates=(),
            )

    def test_full_requires_exactly_one_matched(self) -> None:
        with pytest.raises(ValueError, match="exactly one MATCHED"):
            ComparableResearchResult(
                kind=ComparableResultKind.FULL,
                target_mpn="XP15360SE70005",
                target_manufacturer="Seagate",
                target_enrichment_audit=_make_target_enrichment_audit(),
                authority_audit=(AuthorityAttemptResult(
                    outcome=AuthorityAuditOutcomeKind.NO_MPN_IN_SOURCE,
                    source_name="S1",
                    source_url="https://s1.com/",
                ),),
                candidates=(),
            )

    def test_full_rejects_ambiguous_in_audit(self) -> None:
        with pytest.raises(ValueError, match="AMBIGUOUS_MPN_MATCH"):
            ComparableResearchResult(
                kind=ComparableResultKind.FULL,
                target_mpn="XP15360SE70005",
                target_manufacturer="Seagate",
                target_enrichment_audit=_make_target_enrichment_audit(),
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
            )

    def test_full_requires_non_matched_is_no_mpn_in_source(self) -> None:
        with pytest.raises(ValueError, match="NO_MPN_IN_SOURCE"):
            ComparableResearchResult(
                kind=ComparableResultKind.FULL,
                target_mpn="XP15360SE70005",
                target_manufacturer="Seagate",
                target_enrichment_audit=_make_target_enrichment_audit(),
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
            )

    def test_full_rejects_fatal_authority_outcome(self) -> None:
        for fatal in AUTHORITY_FATAL_OUTCOMES:
            with pytest.raises(ValueError, match=fatal.value):
                ComparableResearchResult(
                    kind=ComparableResultKind.FULL,
                    target_mpn="XP15360SE70005",
                    target_manufacturer="Seagate",
                    target_enrichment_audit=_make_target_enrichment_audit(),
                    authority_audit=(AuthorityAttemptResult(
                        outcome=fatal,
                        source_name="S",
                        source_url="https://example.com/",
                    ),),
                    candidates=(),
                )

    def test_full_with_candidates(self) -> None:
        """FULL kind with candidates works; each carries its own audit."""
        result = ComparableResearchResult(
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
                    scored_field_count=0,
                    evidence_coverage=Decimal("0"),
                    observed_similarity=None,
                    evidence_weighted_similarity=None,
                    field_assessments=(),
                    enrichment_audit=_make_candidate_enrichment_audit(),
                ),
            ),
        )
        assert len(result.candidates) == 1
        assert result.candidates[0].enrichment_audit.product_mpn == "XP15360SE70015"

    # BLOCKER 3: no candidate_enrichment_audits at top level
    def test_no_candidate_enrichment_audits_field(self) -> None:
        """ComparableResearchResult must NOT have candidate_enrichment_audits."""
        result = ComparableResearchResult(
            kind=ComparableResultKind.NO_AUTHORITY_MATCH,
            target_mpn="UNKNOWN",
            target_manufacturer=None,
            target_enrichment_audit=None,
            authority_audit=(AuthorityAttemptResult(
                outcome=AuthorityAuditOutcomeKind.NO_MPN_IN_SOURCE,
                source_name="S",
                source_url="https://example.com/",
            ),),
            candidates=(),
        )
        assert not hasattr(result, "candidate_enrichment_audits")


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
        )
        assert result.kind is ComparableResultKind.NO_AUTHORITY_MATCH

    def test_no_authority_match_rejects_candidates(self) -> None:
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
                candidates=(ComparableCandidateResult(
                    candidate_mpn="XP",
                    candidate_normalized_mpn="XP",
                    scored_field_count=0,
                    evidence_coverage=Decimal("0"),
                    observed_similarity=None,
                    evidence_weighted_similarity=None,
                    field_assessments=(),
                    enrichment_audit=_make_candidate_enrichment_audit(),
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
            )


# ---------------------------------------------------------------------------
# Cross-kind contradiction check
# ---------------------------------------------------------------------------


class TestContradictoryAuthorityMix:
    """NO_MPN_IN_SOURCE + NO_REQUESTED_MPN mix is rejected."""

    def test_rejects_mixed_outcomes(self) -> None:
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
            )
