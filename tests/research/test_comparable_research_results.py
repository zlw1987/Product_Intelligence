"""Pure ComparableResearchResult construction invariant tests (7C-A/FU2).

Tests for:
- AuthorityAuditOutcomeKind and AUTHORITY_FATAL_OUTCOMES
- DatasheetAuditOutcomeKind
- ComparableResultKind
- AuthorityAttemptResult state-dependent field shape (BLOCKER 4 - PRE1 audit)
- DatasheetAttemptResult state-dependent field shape
- ProductEnrichmentAudit (non-empty attempts, MPN binding)
- EvidenceSourceReference (with source_authority + retrieved_at)
- FieldAssessmentResult (BLOCKER 3 - comparison state re-derivation)
- ComparableCandidateResult (BLOCKER 2 - aggregate self-audit)
- ComparableResearchResult kind-specific invariants
- Impossible-state rejection
- NO_MPN_IN_SOURCE + NO_REQUESTED_MPN contradiction
- ComparisonState enum import
- Enrichment audit MPN binding
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


def _make_all_12_assessments(
    scored_keys: tuple[str, ...] = (),
    scored_similarity: Decimal = Decimal("1"),
) -> tuple[FieldAssessmentResult, ...]:
    """Build 12 internally-consistent FieldAssessmentResults for all
    ENTERPRISE_SSD_SCHEMA definitions.

    Fields in `scored_keys` get SCORED state with given similarity.
    All other fields get BOTH_NOT_VERIFIED.
    """
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


def _make_matched_authority() -> AuthorityAttemptResult:
    """Build a valid MATCHED AuthorityAttemptResult."""
    return AuthorityAttemptResult(
        policy_id=POLICY_ID,
        outcome=AuthorityAuditOutcomeKind.MATCHED,
        requested_source_url=SOURCE_URL,
        fetched_final_url=FINAL_URL,
        retrieved_at=RETRIEVED_AT,
        matching_mpn="XP15360SE70005",
    )


# ---------------------------------------------------------------------------
# AuthorityAttemptResult invariants (BLOCKER 4 - PRE1 audit shape)
# ---------------------------------------------------------------------------


class TestAuthorityAttemptResult:
    """AuthorityAttemptResult mirrors frozen PRE1 _AuthoritySourceOutcome."""

    def test_matched_requires_complete_provenance(self) -> None:
        result = AuthorityAttemptResult(
            policy_id=POLICY_ID,
            outcome=AuthorityAuditOutcomeKind.MATCHED,
            requested_source_url=SOURCE_URL,
            fetched_final_url=FINAL_URL,
            retrieved_at=RETRIEVED_AT,
            matching_mpn="XP15360SE70005",
        )
        assert result.outcome is AuthorityAuditOutcomeKind.MATCHED
        assert result.matching_mpn == "XP15360SE70005"

    def test_matched_rejects_missing_policy_id(self) -> None:
        with pytest.raises(ValueError, match="policy_id"):
            AuthorityAttemptResult(
                policy_id="",
                outcome=AuthorityAuditOutcomeKind.MATCHED,
                requested_source_url=SOURCE_URL,
                fetched_final_url=FINAL_URL,
                retrieved_at=RETRIEVED_AT,
                matching_mpn="XP",
            )

    def test_matched_rejects_missing_requested_source_url(self) -> None:
        with pytest.raises(ValueError, match="requested_source_url"):
            AuthorityAttemptResult(
                policy_id=POLICY_ID,
                outcome=AuthorityAuditOutcomeKind.MATCHED,
                requested_source_url=None,
                fetched_final_url=FINAL_URL,
                retrieved_at=RETRIEVED_AT,
                matching_mpn="XP",
            )

    def test_matched_rejects_missing_fetched_final_url(self) -> None:
        with pytest.raises(ValueError, match="fetched_final_url"):
            AuthorityAttemptResult(
                policy_id=POLICY_ID,
                outcome=AuthorityAuditOutcomeKind.MATCHED,
                requested_source_url=SOURCE_URL,
                fetched_final_url=None,
                retrieved_at=RETRIEVED_AT,
                matching_mpn="XP",
            )

    def test_matched_rejects_missing_retrieved_at(self) -> None:
        with pytest.raises(ValueError, match="retrieved_at"):
            AuthorityAttemptResult(
                policy_id=POLICY_ID,
                outcome=AuthorityAuditOutcomeKind.MATCHED,
                requested_source_url=SOURCE_URL,
                fetched_final_url=FINAL_URL,
                retrieved_at=None,
                matching_mpn="XP",
            )

    def test_matched_rejects_missing_matching_mpn(self) -> None:
        with pytest.raises(ValueError, match="matching_mpn"):
            AuthorityAttemptResult(
                policy_id=POLICY_ID,
                outcome=AuthorityAuditOutcomeKind.MATCHED,
                requested_source_url=SOURCE_URL,
                fetched_final_url=FINAL_URL,
                retrieved_at=RETRIEVED_AT,
                matching_mpn=None,
            )

    def test_no_requested_mpn_valid_shape(self) -> None:
        result = AuthorityAttemptResult(
            policy_id=POLICY_ID,
            outcome=AuthorityAuditOutcomeKind.NO_REQUESTED_MPN,
            requested_source_url=SOURCE_URL,
        )
        assert result.fetched_final_url is None
        assert result.retrieved_at is None
        assert result.matching_mpn is None

    def test_no_requested_mpn_rejects_matching_mpn(self) -> None:
        with pytest.raises(ValueError, match="NO_REQUESTED_MPN"):
            AuthorityAttemptResult(
                policy_id=POLICY_ID,
                outcome=AuthorityAuditOutcomeKind.NO_REQUESTED_MPN,
                requested_source_url=SOURCE_URL,
                matching_mpn="XP",
            )

    def test_no_requested_mpn_rejects_fetched_final_url(self) -> None:
        with pytest.raises(ValueError, match="NO_REQUESTED_MPN"):
            AuthorityAttemptResult(
                policy_id=POLICY_ID,
                outcome=AuthorityAuditOutcomeKind.NO_REQUESTED_MPN,
                requested_source_url=SOURCE_URL,
                fetched_final_url=FINAL_URL,
            )

    def test_no_requested_mpn_requires_policy_id(self) -> None:
        with pytest.raises(ValueError, match="policy_id"):
            AuthorityAttemptResult(
                policy_id="",
                outcome=AuthorityAuditOutcomeKind.NO_REQUESTED_MPN,
            )

    def test_no_requested_mpn_requires_requested_source_url(self) -> None:
        with pytest.raises(ValueError, match="requested_source_url"):
            AuthorityAttemptResult(
                policy_id=POLICY_ID,
                outcome=AuthorityAuditOutcomeKind.NO_REQUESTED_MPN,
                requested_source_url=None,
            )

    # --- Non-MATCHED outcomes must NOT have matching_mpn ---

    def test_non_matched_no_mpn_in_source_rejects_faked_mpn(self) -> None:
        with pytest.raises(ValueError, match="must not have matching_mpn"):
            AuthorityAttemptResult(
                policy_id=POLICY_ID,
                outcome=AuthorityAuditOutcomeKind.NO_MPN_IN_SOURCE,
                requested_source_url=SOURCE_URL,
                fetched_final_url=FINAL_URL,
                retrieved_at=RETRIEVED_AT,
                matching_mpn="FAKE",
            )

    def test_non_matched_ambiguous_rejects_faked_mpn(self) -> None:
        with pytest.raises(ValueError, match="must not have matching_mpn"):
            AuthorityAttemptResult(
                policy_id=POLICY_ID,
                outcome=AuthorityAuditOutcomeKind.AMBIGUOUS_MPN_MATCH,
                requested_source_url=SOURCE_URL,
                fetched_final_url=FINAL_URL,
                retrieved_at=RETRIEVED_AT,
                matching_mpn="FAKE",
            )

    def test_non_matched_fetch_failed_rejects_faked_mpn(self) -> None:
        with pytest.raises(ValueError, match="must not have matching_mpn"):
            AuthorityAttemptResult(
                policy_id=POLICY_ID,
                outcome=AuthorityAuditOutcomeKind.AUTHORITY_FETCH_FAILED,
                requested_source_url=SOURCE_URL,
                matching_mpn="FAKE",
            )

    def test_non_matched_source_refused_rejects_faked_mpn(self) -> None:
        with pytest.raises(ValueError, match="must not have matching_mpn"):
            AuthorityAttemptResult(
                policy_id=POLICY_ID,
                outcome=AuthorityAuditOutcomeKind.AUTHORITY_SOURCE_REFUSED,
                requested_source_url=SOURCE_URL,
                matching_mpn="FAKE",
            )

    def test_non_matched_host_escaped_rejects_faked_mpn(self) -> None:
        with pytest.raises(ValueError, match="must not have matching_mpn"):
            AuthorityAttemptResult(
                policy_id=POLICY_ID,
                outcome=AuthorityAuditOutcomeKind.AUTHORITY_HOST_ESCAPED,
                requested_source_url=SOURCE_URL,
                fetched_final_url=FINAL_URL,
                matching_mpn="FAKE",
            )

    def test_non_matched_no_structural_obs_rejects_faked_mpn(self) -> None:
        with pytest.raises(ValueError, match="must not have matching_mpn"):
            AuthorityAttemptResult(
                policy_id=POLICY_ID,
                outcome=AuthorityAuditOutcomeKind.NO_STRUCTURAL_OBSERVATIONS,
                requested_source_url=SOURCE_URL,
                fetched_final_url=FINAL_URL,
                retrieved_at=RETRIEVED_AT,
                matching_mpn="FAKE",
            )

    # --- Fetched-but-no-match outcomes require full provenance ---

    def test_no_mpn_in_source_valid(self) -> None:
        result = AuthorityAttemptResult(
            policy_id=POLICY_ID,
            outcome=AuthorityAuditOutcomeKind.NO_MPN_IN_SOURCE,
            requested_source_url=SOURCE_URL,
            fetched_final_url=FINAL_URL,
            retrieved_at=RETRIEVED_AT,
        )
        assert result.matching_mpn is None

    def test_no_mpn_in_source_rejects_missing_fetched_final_url(self) -> None:
        with pytest.raises(ValueError, match="fetched_final_url"):
            AuthorityAttemptResult(
                policy_id=POLICY_ID,
                outcome=AuthorityAuditOutcomeKind.NO_MPN_IN_SOURCE,
                requested_source_url=SOURCE_URL,
                fetched_final_url=None,
                retrieved_at=RETRIEVED_AT,
            )

    def test_no_structural_obs_valid(self) -> None:
        result = AuthorityAttemptResult(
            policy_id=POLICY_ID,
            outcome=AuthorityAuditOutcomeKind.NO_STRUCTURAL_OBSERVATIONS,
            requested_source_url=SOURCE_URL,
            fetched_final_url=FINAL_URL,
            retrieved_at=RETRIEVED_AT,
        )
        assert result.matching_mpn is None

    # --- Fetch failure outcomes: no fetched evidence ---

    def test_fetch_failed_valid(self) -> None:
        result = AuthorityAttemptResult(
            policy_id=POLICY_ID,
            outcome=AuthorityAuditOutcomeKind.AUTHORITY_FETCH_FAILED,
            requested_source_url=SOURCE_URL,
        )
        assert result.fetched_final_url is None
        assert result.retrieved_at is None

    def test_fetch_failed_rejects_fetched_final_url(self) -> None:
        with pytest.raises(ValueError, match="must not have fetched_final_url"):
            AuthorityAttemptResult(
                policy_id=POLICY_ID,
                outcome=AuthorityAuditOutcomeKind.AUTHORITY_FETCH_FAILED,
                requested_source_url=SOURCE_URL,
                fetched_final_url=FINAL_URL,
            )

    def test_source_refused_valid(self) -> None:
        result = AuthorityAttemptResult(
            policy_id=POLICY_ID,
            outcome=AuthorityAuditOutcomeKind.AUTHORITY_SOURCE_REFUSED,
            requested_source_url=SOURCE_URL,
        )
        assert result.fetched_final_url is None

    # --- Host escaped: URL present, no MPN ---

    def test_host_escaped_valid(self) -> None:
        result = AuthorityAttemptResult(
            policy_id=POLICY_ID,
            outcome=AuthorityAuditOutcomeKind.AUTHORITY_HOST_ESCAPED,
            requested_source_url=SOURCE_URL,
            fetched_final_url="https://other.example.com/",
        )
        assert result.matching_mpn is None

    def test_host_escaped_rejects_missing_fetched_final_url(self) -> None:
        with pytest.raises(ValueError, match="fetched_final_url"):
            AuthorityAttemptResult(
                policy_id=POLICY_ID,
                outcome=AuthorityAuditOutcomeKind.AUTHORITY_HOST_ESCAPED,
                requested_source_url=SOURCE_URL,
                fetched_final_url=None,
            )

    # --- Ambiguous MPN: fetched, but multiple records ---

    def test_ambiguous_valid(self) -> None:
        result = AuthorityAttemptResult(
            policy_id=POLICY_ID,
            outcome=AuthorityAuditOutcomeKind.AMBIGUOUS_MPN_MATCH,
            requested_source_url=SOURCE_URL,
            fetched_final_url=FINAL_URL,
            retrieved_at=RETRIEVED_AT,
        )
        assert result.matching_mpn is None

    def test_ambiguous_rejects_missing_retrieved_at(self) -> None:
        with pytest.raises(ValueError, match="retrieved_at"):
            AuthorityAttemptResult(
                policy_id=POLICY_ID,
                outcome=AuthorityAuditOutcomeKind.AMBIGUOUS_MPN_MATCH,
                requested_source_url=SOURCE_URL,
                fetched_final_url=FINAL_URL,
                retrieved_at=None,
            )

    # --- Old fields no longer exist ---

    def test_no_source_name_field(self) -> None:
        """AuthorityAttemptResult must NOT have source_name."""
        result = _make_matched_authority()
        assert not hasattr(result, "source_name")

    def test_no_source_url_field(self) -> None:
        """AuthorityAttemptResult must NOT have source_url."""
        result = _make_matched_authority()
        assert not hasattr(result, "source_url")

    def test_no_matched_mpn_field(self) -> None:
        """AuthorityAttemptResult must NOT have matched_mpn (old name)."""
        result = _make_matched_authority()
        assert not hasattr(result, "matched_mpn")

    def test_no_raw_reference_field(self) -> None:
        """AuthorityAttemptResult must NOT have raw_reference."""
        result = _make_matched_authority()
        assert not hasattr(result, "raw_reference")


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
                retrieved_at="2025-01-01T00:00:00+00:00",
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
                final_url="https://example.com/ds.pdf",
                retrieved_at="2025-01-01T00:00:00+00:00",
                observation_count=None,
            )

    def test_enriched_valid(self) -> None:
        result = DatasheetAttemptResult(
            outcome=DatasheetAuditOutcomeKind.ENRICHED,
            source_name="Seagate Datasheet",
            source_url="https://example.com/ds.pdf",
            final_url="https://example.com/ds.pdf",
            retrieved_at="2025-01-01T00:00:00+00:00",
            observation_count=6,
        )
        assert result.observation_count == 6


# ---------------------------------------------------------------------------
# ProductEnrichmentAudit (non-empty attempts)
# ---------------------------------------------------------------------------


class TestProductEnrichmentAudit:
    """ProductEnrichmentAudit: non-empty attempts, no authority_audit."""

    def test_valid(self) -> None:
        audit = ProductEnrichmentAudit(
            product_mpn="XP15360SE70005",
            attempts=(DatasheetAttemptResult(
                outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
            ),),
        )
        assert audit.product_mpn == "XP15360SE70005"
        assert len(audit.attempts) == 1

    def test_rejects_empty_attempts(self) -> None:
        """Empty attempts tuple is rejected: every product must have
        at least one enrichment attempt (including NO_DATASHEET_SOURCE)."""
        with pytest.raises(ValueError, match="non-empty"):
            ProductEnrichmentAudit(product_mpn="XP15360SE70005")

    def test_rejects_empty_product_mpn(self) -> None:
        with pytest.raises(ValueError, match="product_mpn"):
            ProductEnrichmentAudit(
                product_mpn="",
                attempts=(DatasheetAttemptResult(
                    outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
                ),),
            )

    def test_rejects_non_string_product_mpn(self) -> None:
        with pytest.raises(TypeError, match="product_mpn"):
            ProductEnrichmentAudit(
                product_mpn=123,  # type: ignore[arg-type]
                attempts=(DatasheetAttemptResult(
                    outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
                ),),
            )

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
        audit = ProductEnrichmentAudit(
            product_mpn="XP",
            attempts=(DatasheetAttemptResult(
                outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
            ),),
        )
        assert not hasattr(audit, "authority_audit")

    def test_no_target_identity_field(self) -> None:
        """ProductEnrichmentAudit must NOT have target_identity."""
        audit = ProductEnrichmentAudit(
            product_mpn="XP",
            attempts=(DatasheetAttemptResult(
                outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
            ),),
        )
        assert not hasattr(audit, "target_identity")

    def test_no_specification_set_field(self) -> None:
        """ProductEnrichmentAudit must NOT have specification_set."""
        audit = ProductEnrichmentAudit(
            product_mpn="XP",
            attempts=(DatasheetAttemptResult(
                outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
            ),),
        )
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
                retrieved_at="2025-01-01T00:00:00+00:00",
            )

    def test_requires_source_authority(self) -> None:
        """source_authority is required (frozen PRE2 provenance contract)."""
        assert EvidenceSourceReference(
            source_name="S",
            source_url="https://example.com/",
            evidence_layer=EvidenceLayer.DATASHEET_PDF,
            source_authority=SourceAuthority.AUTHORITATIVE,
            retrieved_at="2025-01-01T00:00:00+00:00",
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
# FieldAssessmentResult (BLOCKER 3 - comparison state re-derivation)
# ---------------------------------------------------------------------------


class TestFieldAssessmentResult:
    """FieldAssessmentResult mechanically validates comparison_state."""

    # --- Valid states ---

    def test_scored_valid(self) -> None:
        fa = FieldAssessmentResult(
            definition_key="capacity",
            comparison_state=ComparisonState.SCORED,
            target_resolution_state=ResolutionState.VERIFIED,
            candidate_resolution_state=ResolutionState.VERIFIED,
            field_similarity=Decimal("1"),
            target_value="15.36 TB",
            candidate_value="15.36 TB",
            target_evidence=(_make_evidence_ref(),),
            candidate_evidence=(_make_evidence_ref(),),
        )
        assert fa.comparison_state is ComparisonState.SCORED
        assert fa.field_similarity == Decimal("1")

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
            candidate_evidence=(_make_evidence_ref(),),
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
            target_evidence=(_make_evidence_ref(),),
        )
        assert fa.field_similarity is None

    # --- BLOCKER 3: Scored requires decimal similarity ---

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
                target_evidence=(_make_evidence_ref(),),
                candidate_evidence=(_make_evidence_ref(),),
            )

    def test_scored_rejects_non_decimal_similarity(self) -> None:
        with pytest.raises(TypeError, match="field_similarity must be Decimal"):
            FieldAssessmentResult(
                definition_key="capacity",
                comparison_state=ComparisonState.SCORED,
                target_resolution_state=ResolutionState.VERIFIED,
                candidate_resolution_state=ResolutionState.VERIFIED,
                field_similarity=1.0,
                target_value="x",
                candidate_value="y",
                target_evidence=(_make_evidence_ref(),),
                candidate_evidence=(_make_evidence_ref(),),
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
                target_evidence=(_make_evidence_ref(),),
                candidate_evidence=(_make_evidence_ref(),),
            )

    # --- BLOCKER 3: Non-SCORED requires None similarity ---

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

    # --- BLOCKER 3: Comparison state must match resolution states ---

    def test_rejects_scored_with_unverified_target(self) -> None:
        """SCORED requires both sides VERIFIED."""
        with pytest.raises(ValueError, match="does not match"):
            FieldAssessmentResult(
                definition_key="capacity",
                comparison_state=ComparisonState.SCORED,
                target_resolution_state=ResolutionState.UNKNOWN,
                candidate_resolution_state=ResolutionState.VERIFIED,
                field_similarity=Decimal("1"),
                target_value=None,
                candidate_value="x",
                candidate_evidence=(_make_evidence_ref(),),
            )

    def test_rejects_scored_with_unverified_candidate(self) -> None:
        with pytest.raises(ValueError, match="does not match"):
            FieldAssessmentResult(
                definition_key="capacity",
                comparison_state=ComparisonState.SCORED,
                target_resolution_state=ResolutionState.VERIFIED,
                candidate_resolution_state=ResolutionState.UNKNOWN,
                field_similarity=Decimal("1"),
                target_value="x",
                candidate_value=None,
                target_evidence=(_make_evidence_ref(),),
            )

    def test_rejects_scored_with_both_unverified(self) -> None:
        with pytest.raises(ValueError, match="does not match"):
            FieldAssessmentResult(
                definition_key="capacity",
                comparison_state=ComparisonState.SCORED,
                target_resolution_state=ResolutionState.UNKNOWN,
                candidate_resolution_state=ResolutionState.UNKNOWN,
                field_similarity=Decimal("1"),
                target_value=None,
                candidate_value=None,
            )

    def test_rejects_both_not_verified_with_verified_target(self) -> None:
        with pytest.raises(ValueError, match="does not match"):
            FieldAssessmentResult(
                definition_key="capacity",
                comparison_state=ComparisonState.BOTH_NOT_VERIFIED,
                target_resolution_state=ResolutionState.VERIFIED,
                candidate_resolution_state=ResolutionState.UNKNOWN,
                field_similarity=None,
                target_value="x",
                candidate_value=None,
                target_evidence=(_make_evidence_ref(),),
            )

    def test_rejects_both_not_verified_with_both_verified(self) -> None:
        with pytest.raises(ValueError, match="does not match"):
            FieldAssessmentResult(
                definition_key="capacity",
                comparison_state=ComparisonState.BOTH_NOT_VERIFIED,
                target_resolution_state=ResolutionState.VERIFIED,
                candidate_resolution_state=ResolutionState.VERIFIED,
                field_similarity=None,
                target_value="x",
                candidate_value="y",
                target_evidence=(_make_evidence_ref(),),
                candidate_evidence=(_make_evidence_ref(),),
            )

    def test_rejects_candidate_not_verified_with_target_not_verified(self) -> None:
        """CANDIDATE_NOT_VERIFIED requires target VERIFIED."""
        with pytest.raises(ValueError, match="does not match"):
            FieldAssessmentResult(
                definition_key="capacity",
                comparison_state=ComparisonState.CANDIDATE_NOT_VERIFIED,
                target_resolution_state=ResolutionState.UNKNOWN,
                candidate_resolution_state=ResolutionState.UNKNOWN,
                field_similarity=None,
                target_value=None,
                candidate_value=None,
            )

    def test_rejects_target_not_verified_with_candidate_not_verified(self) -> None:
        """TARGET_NOT_VERIFIED requires candidate VERIFIED."""
        with pytest.raises(ValueError, match="does not match"):
            FieldAssessmentResult(
                definition_key="capacity",
                comparison_state=ComparisonState.TARGET_NOT_VERIFIED,
                target_resolution_state=ResolutionState.UNKNOWN,
                candidate_resolution_state=ResolutionState.UNKNOWN,
                field_similarity=None,
                target_value=None,
                candidate_value=None,
            )

    # --- Additional resolution state combos ---

    def test_rejects_scored_with_conflict_target(self) -> None:
        with pytest.raises(ValueError, match="does not match"):
            FieldAssessmentResult(
                definition_key="capacity",
                comparison_state=ComparisonState.SCORED,
                target_resolution_state=ResolutionState.CONFLICT,
                candidate_resolution_state=ResolutionState.VERIFIED,
                field_similarity=Decimal("1"),
                target_value=None,
                candidate_value="x",
                candidate_evidence=(_make_evidence_ref(),),
            )

    def test_rejects_scored_with_unverified_candidate(self) -> None:
        with pytest.raises(ValueError, match="does not match"):
            FieldAssessmentResult(
                definition_key="capacity",
                comparison_state=ComparisonState.SCORED,
                target_resolution_state=ResolutionState.VERIFIED,
                candidate_resolution_state=ResolutionState.UNVERIFIED,
                field_similarity=Decimal("1"),
                target_value="x",
                candidate_value="y",
                target_evidence=(_make_evidence_ref(),),
                candidate_evidence=(_make_evidence_ref(),),
            )

    def test_valid_with_evidence(self) -> None:
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


# ---------------------------------------------------------------------------
# ComparableCandidateResult (BLOCKER 2 - aggregate self-audit)
# ---------------------------------------------------------------------------


class TestComparableCandidateResult:
    """ComparableCandidateResult re-derives aggregate scalars from field_assessments."""

    def test_valid_all_scored(self) -> None:
        """All 12 fields SCORED with similarity=1."""
        assessments = _make_all_12_assessments(
            scored_keys=tuple(ENTERPRISE_SSD_SCHEMA.definitions.keys()),
            scored_similarity=Decimal("1"),
        )
        total = Decimal(len(ENTERPRISE_SSD_SCHEMA.definitions))
        result = ComparableCandidateResult(
            candidate_mpn="XP15360SE70015",
            candidate_normalized_mpn="XP15360SE70015",
            scored_field_count=12,
            evidence_coverage=total / total,
            observed_similarity=Decimal("1"),
            evidence_weighted_similarity=Decimal("1"),
            field_assessments=assessments,
            enrichment_audit=_make_candidate_enrichment_audit(),
        )
        assert result.candidate_mpn == "XP15360SE70015"
        assert result.scored_field_count == 12

    def test_valid_partial_scored(self) -> None:
        """7 fields scored (typical 6C+6D composition)."""
        assessments = _make_all_12_assessments(
            scored_keys=(
                "capacity", "sequential_read", "sequential_write",
                "random_read_iops", "random_write_iops", "endurance_dwpd",
                "physical_form_factor",
            ),
        )
        result = ComparableCandidateResult(
            candidate_mpn="XP15360SE70015",
            candidate_normalized_mpn="XP15360SE70015",
            scored_field_count=7,
            evidence_coverage=Decimal("7") / Decimal("12"),
            observed_similarity=Decimal("1"),
            evidence_weighted_similarity=Decimal("7") / Decimal("12"),
            field_assessments=assessments,
            enrichment_audit=_make_candidate_enrichment_audit(),
        )
        assert result.scored_field_count == 7

    def test_valid_no_scored(self) -> None:
        """All 12 fields BOTH_NOT_VERIFIED."""
        assessments = _make_all_12_assessments(scored_keys=())
        result = ComparableCandidateResult(
            candidate_mpn="XP15360SE70015",
            candidate_normalized_mpn="XP15360SE70015",
            scored_field_count=0,
            evidence_coverage=Decimal("0"),
            observed_similarity=None,
            evidence_weighted_similarity=None,
            field_assessments=assessments,
            enrichment_audit=_make_candidate_enrichment_audit(),
        )
        assert result.scored_field_count == 0
        assert result.observed_similarity is None

    # --- BLOCKER 2: Aggregate mismatch rejections ---

    def test_rejects_wrong_scored_field_count(self) -> None:
        """scored_field_count must match actual scored assessments."""
        assessments = _make_all_12_assessments(scored_keys=("capacity",))
        with pytest.raises(ValueError, match="scored_field_count"):
            ComparableCandidateResult(
                candidate_mpn="XP",
                candidate_normalized_mpn="XP",
                scored_field_count=5,  # Wrong — only 1 is scored
                evidence_coverage=Decimal("5") / Decimal("12"),
                observed_similarity=Decimal("1"),
                evidence_weighted_similarity=Decimal("5") / Decimal("12"),
                field_assessments=assessments,
                enrichment_audit=ProductEnrichmentAudit(
                    product_mpn="XP",
                    attempts=(DatasheetAttemptResult(
                        outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
                    ),),
                ),
            )

    def test_rejects_wrong_evidence_coverage(self) -> None:
        assessments = _make_all_12_assessments(scored_keys=("capacity",))
        with pytest.raises(ValueError, match="evidence_coverage"):
            ComparableCandidateResult(
                candidate_mpn="XP",
                candidate_normalized_mpn="XP",
                scored_field_count=1,
                evidence_coverage=Decimal("5") / Decimal("12"),  # Wrong
                observed_similarity=Decimal("1"),
                evidence_weighted_similarity=Decimal("1") / Decimal("12"),
                field_assessments=assessments,
                enrichment_audit=ProductEnrichmentAudit(
                    product_mpn="XP",
                    attempts=(DatasheetAttemptResult(
                        outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
                    ),),
                ),
            )

    def test_rejects_wrong_observed_similarity(self) -> None:
        """observed_similarity must be mean of scored similarities."""
        # One scored field with similarity=0.5
        assessments = _make_all_12_assessments(
            scored_keys=("capacity",),
            scored_similarity=Decimal("0.5"),
        )
        with pytest.raises(ValueError, match="observed_similarity"):
            ComparableCandidateResult(
                candidate_mpn="XP",
                candidate_normalized_mpn="XP",
                scored_field_count=1,
                evidence_coverage=Decimal("1") / Decimal("12"),
                observed_similarity=Decimal("1"),  # Wrong — should be 0.5
                evidence_weighted_similarity=Decimal("0.5") / Decimal("12"),
                field_assessments=assessments,
                enrichment_audit=ProductEnrichmentAudit(
                    product_mpn="XP",
                    attempts=(DatasheetAttemptResult(
                        outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
                    ),),
                ),
            )

    def test_rejects_wrong_evidence_weighted_similarity(self) -> None:
        assessments = _make_all_12_assessments(
            scored_keys=("capacity",),
            scored_similarity=Decimal("0.5"),
        )
        with pytest.raises(ValueError, match="evidence_weighted_similarity"):
            ComparableCandidateResult(
                candidate_mpn="XP",
                candidate_normalized_mpn="XP",
                scored_field_count=1,
                evidence_coverage=Decimal("1") / Decimal("12"),
                observed_similarity=Decimal("0.5"),
                evidence_weighted_similarity=Decimal("1") / Decimal("12"),  # Wrong
                field_assessments=assessments,
                enrichment_audit=ProductEnrichmentAudit(
                    product_mpn="XP",
                    attempts=(DatasheetAttemptResult(
                        outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
                    ),),
                ),
            )

    # --- BLOCKER 2: Field set validation ---

    def test_rejects_missing_field(self) -> None:
        """Missing one definition key."""
        assessments = _make_all_12_assessments(scored_keys=())
        # Drop one assessment (11 instead of 12)
        truncated = assessments[:-1]
        with pytest.raises(ValueError, match="has 11 items"):
            ComparableCandidateResult(
                candidate_mpn="XP",
                candidate_normalized_mpn="XP",
                scored_field_count=0,
                evidence_coverage=Decimal("0"),
                observed_similarity=None,
                evidence_weighted_similarity=None,
                field_assessments=truncated,
                enrichment_audit=ProductEnrichmentAudit(
                    product_mpn="XP",
                    attempts=(DatasheetAttemptResult(
                        outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
                    ),),
                ),
            )

    def test_rejects_duplicate_definition_key(self) -> None:
        assessments = _make_all_12_assessments(scored_keys=())
        # Add a duplicate first field (13 total — caught by count check first)
        duplicated = assessments + (assessments[0],)
        with pytest.raises(ValueError, match="has 13 items"):
            ComparableCandidateResult(
                candidate_mpn="XP",
                candidate_normalized_mpn="XP",
                scored_field_count=0,
                evidence_coverage=Decimal("0"),
                observed_similarity=None,
                evidence_weighted_similarity=None,
                field_assessments=duplicated,
                enrichment_audit=ProductEnrichmentAudit(
                    product_mpn="XP",
                    attempts=(DatasheetAttemptResult(
                        outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
                    ),),
                ),
            )

    def test_rejects_unknown_definition_key(self) -> None:
        """A definition_key not in ENTERPRISE_SSD_SCHEMA is rejected."""
        unknown_fa = FieldAssessmentResult(
            definition_key="not_a_real_field",
            comparison_state=ComparisonState.BOTH_NOT_VERIFIED,
            target_resolution_state=ResolutionState.UNKNOWN,
            candidate_resolution_state=ResolutionState.UNKNOWN,
            field_similarity=None,
            target_value=None,
            candidate_value=None,
        )
        base = _make_all_12_assessments(scored_keys=())
        # Replace last with unknown
        modified = base[:-1] + (unknown_fa,)
        with pytest.raises(ValueError, match="do not match"):
            ComparableCandidateResult(
                candidate_mpn="XP",
                candidate_normalized_mpn="XP",
                scored_field_count=0,
                evidence_coverage=Decimal("0"),
                observed_similarity=None,
                evidence_weighted_similarity=None,
                field_assessments=modified,
                enrichment_audit=ProductEnrichmentAudit(
                    product_mpn="XP",
                    attempts=(DatasheetAttemptResult(
                        outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
                    ),),
                ),
            )

    # --- Enrichment MPN binding ---

    def test_rejects_enrichment_audit_mpn_mismatch(self) -> None:
        """enrichment_audit.product_mpn must equal candidate_mpn."""
        assessments = _make_all_12_assessments(scored_keys=())
        with pytest.raises(ValueError, match="product_mpn"):
            ComparableCandidateResult(
                candidate_mpn="XP15360SE70015",
                candidate_normalized_mpn="XP15360SE70015",
                scored_field_count=0,
                evidence_coverage=Decimal("0"),
                observed_similarity=None,
                evidence_weighted_similarity=None,
                field_assessments=assessments,
                enrichment_audit=ProductEnrichmentAudit(
                    product_mpn="WRONG_MPN",
                    attempts=(DatasheetAttemptResult(
                        outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
                    ),),
                ),
            )

    # --- Type invariants ---

    def test_rejects_empty_candidate_mpn(self) -> None:
        assessments = _make_all_12_assessments(scored_keys=())
        with pytest.raises(ValueError, match="candidate_mpn"):
            ComparableCandidateResult(
                candidate_mpn="",
                candidate_normalized_mpn="X",
                scored_field_count=0,
                evidence_coverage=Decimal("0"),
                observed_similarity=None,
                evidence_weighted_similarity=None,
                field_assessments=assessments,
                enrichment_audit=_make_candidate_enrichment_audit(),
            )

    def test_rejects_non_int_scored_field_count(self) -> None:
        assessments = _make_all_12_assessments(scored_keys=())
        with pytest.raises(TypeError, match="scored_field_count"):
            ComparableCandidateResult(
                candidate_mpn="XP",
                candidate_normalized_mpn="XP",
                scored_field_count=True,
                evidence_coverage=Decimal("0"),
                observed_similarity=None,
                evidence_weighted_similarity=None,
                field_assessments=assessments,
                enrichment_audit=ProductEnrichmentAudit(
                    product_mpn="XP",
                    attempts=(DatasheetAttemptResult(
                        outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
                    ),),
                ),
            )

    def test_rejects_non_decimal_evidence_coverage(self) -> None:
        assessments = _make_all_12_assessments(scored_keys=())
        with pytest.raises(TypeError, match="evidence_coverage"):
            ComparableCandidateResult(
                candidate_mpn="XP",
                candidate_normalized_mpn="XP",
                scored_field_count=0,
                evidence_coverage=0.0,
                observed_similarity=None,
                evidence_weighted_similarity=None,
                field_assessments=assessments,
                enrichment_audit=ProductEnrichmentAudit(
                    product_mpn="XP",
                    attempts=(DatasheetAttemptResult(
                        outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
                    ),),
                ),
            )

    def test_no_candidate_object_field(self) -> None:
        """ComparableCandidateResult must NOT have a candidate object field."""
        assessments = _make_all_12_assessments(scored_keys=())
        result = ComparableCandidateResult(
            candidate_mpn="XP",
            candidate_normalized_mpn="XP",
            scored_field_count=0,
            evidence_coverage=Decimal("0"),
            observed_similarity=None,
            evidence_weighted_similarity=None,
            field_assessments=assessments,
            enrichment_audit=ProductEnrichmentAudit(
                    product_mpn="XP",
                    attempts=(DatasheetAttemptResult(
                        outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
                    ),),
                ),
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
            authority_audit=(_make_matched_authority(),),
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
                authority_audit=(_make_matched_authority(),),
                candidates=(),
            )

    def test_full_rejects_empty_target_manufacturer(self) -> None:
        with pytest.raises(ValueError, match="target_manufacturer"):
            ComparableResearchResult(
                kind=ComparableResultKind.FULL,
                target_mpn="XP15360SE70005",
                target_manufacturer="",
                target_enrichment_audit=_make_target_enrichment_audit(),
                authority_audit=(_make_matched_authority(),),
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
                    policy_id=POLICY_ID,
                    outcome=AuthorityAuditOutcomeKind.NO_MPN_IN_SOURCE,
                    requested_source_url=SOURCE_URL,
                    fetched_final_url=FINAL_URL,
                    retrieved_at=RETRIEVED_AT,
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
                    _make_matched_authority(),
                    AuthorityAttemptResult(
                        policy_id="other-policy",
                        outcome=AuthorityAuditOutcomeKind.AMBIGUOUS_MPN_MATCH,
                        requested_source_url=SOURCE_URL,
                        fetched_final_url=FINAL_URL,
                        retrieved_at=RETRIEVED_AT,
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
                    _make_matched_authority(),
                    AuthorityAttemptResult(
                        policy_id="other-policy",
                        outcome=AuthorityAuditOutcomeKind.NO_REQUESTED_MPN,
                        requested_source_url=SOURCE_URL,
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
                        policy_id=POLICY_ID,
                        outcome=fatal,
                        requested_source_url=SOURCE_URL,
                        fetched_final_url=FINAL_URL
                            if fatal not in (
                                AuthorityAuditOutcomeKind.AUTHORITY_FETCH_FAILED,
                                AuthorityAuditOutcomeKind.AUTHORITY_SOURCE_REFUSED,
                            )
                            else None,
                        retrieved_at=RETRIEVED_AT
                            if fatal in (
                                AuthorityAuditOutcomeKind.NO_STRUCTURAL_OBSERVATIONS,
                            )
                            else None,
                    ),),
                    candidates=(),
                )

    def test_full_requires_target_enrichment_audit(self) -> None:
        with pytest.raises(ValueError, match="target_enrichment_audit"):
            ComparableResearchResult(
                kind=ComparableResultKind.FULL,
                target_mpn="XP15360SE70005",
                target_manufacturer="Seagate",
                target_enrichment_audit=None,
                authority_audit=(_make_matched_authority(),),
                candidates=(),
            )

    def test_full_rejects_target_enrichment_mpn_mismatch(self) -> None:
        """target_enrichment_audit.product_mpn must equal target_mpn."""
        with pytest.raises(ValueError, match="product_mpn"):
            ComparableResearchResult(
                kind=ComparableResultKind.FULL,
                target_mpn="XP15360SE70005",
                target_manufacturer="Seagate",
                target_enrichment_audit=ProductEnrichmentAudit(
                    product_mpn="WRONG_MPN",
                    attempts=(DatasheetAttemptResult(
                        outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
                    ),),
                ),
                authority_audit=(_make_matched_authority(),),
                candidates=(),
            )

    def test_full_with_candidates(self) -> None:
        """FULL kind with candidates works; each carries its own audit."""
        assessments = _make_all_12_assessments(scored_keys=())
        result = ComparableResearchResult(
            kind=ComparableResultKind.FULL,
            target_mpn="XP15360SE70005",
            target_manufacturer="Seagate",
            target_enrichment_audit=_make_target_enrichment_audit(),
            authority_audit=(_make_matched_authority(),),
            candidates=(
                ComparableCandidateResult(
                    candidate_mpn="XP15360SE70015",
                    candidate_normalized_mpn="XP15360SE70015",
                    scored_field_count=0,
                    evidence_coverage=Decimal("0"),
                    observed_similarity=None,
                    evidence_weighted_similarity=None,
                    field_assessments=assessments,
                    enrichment_audit=_make_candidate_enrichment_audit(),
                ),
            ),
        )
        assert len(result.candidates) == 1
        assert result.candidates[0].enrichment_audit.product_mpn == "XP15360SE70015"

    def test_no_candidate_enrichment_audits_field(self) -> None:
        """ComparableResearchResult must NOT have candidate_enrichment_audits."""
        result = ComparableResearchResult(
            kind=ComparableResultKind.NO_AUTHORITY_MATCH,
            target_mpn="UNKNOWN",
            target_manufacturer=None,
            target_enrichment_audit=None,
            authority_audit=(AuthorityAttemptResult(
                policy_id=POLICY_ID,
                outcome=AuthorityAuditOutcomeKind.NO_MPN_IN_SOURCE,
                requested_source_url=SOURCE_URL,
                fetched_final_url=FINAL_URL,
                retrieved_at=RETRIEVED_AT,
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
                    policy_id=POLICY_ID,
                    outcome=AuthorityAuditOutcomeKind.NO_MPN_IN_SOURCE,
                    requested_source_url=SOURCE_URL,
                    fetched_final_url=FINAL_URL,
                    retrieved_at=RETRIEVED_AT,
                ),
            ),
            candidates=(),
        )
        assert result.kind is ComparableResultKind.NO_AUTHORITY_MATCH

    def test_no_authority_match_rejects_fabricated_manufacturer(self) -> None:
        with pytest.raises(ValueError, match="target_manufacturer=None"):
            ComparableResearchResult(
                kind=ComparableResultKind.NO_AUTHORITY_MATCH,
                target_mpn="UNKNOWN",
                target_manufacturer="Guessed Manufacturer",
                target_enrichment_audit=None,
                authority_audit=(AuthorityAttemptResult(
                    policy_id=POLICY_ID,
                    outcome=AuthorityAuditOutcomeKind.NO_MPN_IN_SOURCE,
                    requested_source_url=SOURCE_URL,
                    fetched_final_url=FINAL_URL,
                    retrieved_at=RETRIEVED_AT,
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
                policy_id=POLICY_ID,
                outcome=AuthorityAuditOutcomeKind.NO_REQUESTED_MPN,
                requested_source_url=SOURCE_URL,
            ),),
            candidates=(),
        )
        assert result.kind is ComparableResultKind.NO_REQUESTED_MPN

    def test_no_requested_mpn_rejects_fabricated_manufacturer(self) -> None:
        with pytest.raises(ValueError, match="target_manufacturer=None"):
            ComparableResearchResult(
                kind=ComparableResultKind.NO_REQUESTED_MPN,
                target_mpn="",
                target_manufacturer="Guessed",
                target_enrichment_audit=None,
                authority_audit=(AuthorityAttemptResult(
                    policy_id=POLICY_ID,
                    outcome=AuthorityAuditOutcomeKind.NO_REQUESTED_MPN,
                    requested_source_url=SOURCE_URL,
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
                    policy_id=POLICY_ID,
                    outcome=AuthorityAuditOutcomeKind.AMBIGUOUS_MPN_MATCH,
                    requested_source_url=SOURCE_URL,
                    fetched_final_url=FINAL_URL,
                    retrieved_at=RETRIEVED_AT,
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
                    policy_id=POLICY_ID,
                    outcome=AuthorityAuditOutcomeKind.MATCHED,
                    requested_source_url=SOURCE_URL,
                    fetched_final_url=FINAL_URL,
                    retrieved_at=RETRIEVED_AT,
                    matching_mpn="AMBIGUOUS",
                ),
                AuthorityAttemptResult(
                    policy_id="other-policy",
                    outcome=AuthorityAuditOutcomeKind.MATCHED,
                    requested_source_url=SOURCE_URL,
                    fetched_final_url=FINAL_URL,
                    retrieved_at=RETRIEVED_AT,
                    matching_mpn="AMBIGUOUS",
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
                    policy_id=POLICY_ID,
                    outcome=AuthorityAuditOutcomeKind.MATCHED,
                    requested_source_url=SOURCE_URL,
                    fetched_final_url=FINAL_URL,
                    retrieved_at=RETRIEVED_AT,
                    matching_mpn="X",
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
                        policy_id=POLICY_ID,
                        outcome=AuthorityAuditOutcomeKind.NO_MPN_IN_SOURCE,
                        requested_source_url=SOURCE_URL,
                        fetched_final_url=FINAL_URL,
                        retrieved_at=RETRIEVED_AT,
                    ),
                    AuthorityAttemptResult(
                        policy_id=POLICY_ID,
                        outcome=AuthorityAuditOutcomeKind.NO_REQUESTED_MPN,
                        requested_source_url=SOURCE_URL,
                    ),
                ),
                candidates=(),
            )


# ---------------------------------------------------------------------------
# BLOCKER 1: DatasheetAttemptResult adversarial matrix
# ---------------------------------------------------------------------------


class TestDatasheetAttemptResultAdversarial:
    """BLOCKER 1: Every DatasheetAttemptResult outcome shape enforced."""

    def test_enriched_rejects_zero_observation_count(self) -> None:
        with pytest.raises(ValueError, match="observation_count > 0"):
            DatasheetAttemptResult(
                outcome=DatasheetAuditOutcomeKind.ENRICHED,
                source_name="S",
                source_url="https://example.com/",
                final_url="https://example.com/",
                retrieved_at=RETRIEVED_AT,
                observation_count=0,
            )

    def test_enriched_rejects_bool_observation_count(self) -> None:
        with pytest.raises(TypeError, match="observation_count must be int"):
            DatasheetAttemptResult(
                outcome=DatasheetAuditOutcomeKind.ENRICHED,
                source_name="S",
                source_url="https://example.com/",
                final_url="https://example.com/",
                retrieved_at=RETRIEVED_AT,
                observation_count=True,
            )

    def test_enriched_rejects_missing_final_url(self) -> None:
        with pytest.raises(ValueError, match="final_url"):
            DatasheetAttemptResult(
                outcome=DatasheetAuditOutcomeKind.ENRICHED,
                source_name="S",
                source_url="https://example.com/",
                final_url=None,
                retrieved_at=RETRIEVED_AT,
                observation_count=5,
            )

    def test_enriched_rejects_missing_retrieved_at(self) -> None:
        with pytest.raises(ValueError, match="retrieved_at"):
            DatasheetAttemptResult(
                outcome=DatasheetAuditOutcomeKind.ENRICHED,
                source_name="S",
                source_url="https://example.com/",
                final_url="https://example.com/",
                retrieved_at=None,
                observation_count=5,
            )

    def test_enriched_valid_full_shape(self) -> None:
        result = DatasheetAttemptResult(
            outcome=DatasheetAuditOutcomeKind.ENRICHED,
            source_name="Seagate Datasheet",
            source_url="https://example.com/ds.pdf",
            final_url="https://example.com/ds.pdf",
            retrieved_at=RETRIEVED_AT,
            observation_count=6,
        )
        assert result.observation_count == 6

    def test_no_observations_requires_zero_count(self) -> None:
        result = DatasheetAttemptResult(
            outcome=DatasheetAuditOutcomeKind.NO_OBSERVATIONS,
            source_name="S",
            source_url="https://example.com/",
            final_url="https://example.com/",
            retrieved_at=RETRIEVED_AT,
            observation_count=0,
        )
        assert result.observation_count == 0

    def test_no_observations_rejects_nonzero_count(self) -> None:
        with pytest.raises(ValueError, match="observation_count == 0"):
            DatasheetAttemptResult(
                outcome=DatasheetAuditOutcomeKind.NO_OBSERVATIONS,
                source_name="S",
                source_url="https://example.com/",
                final_url="https://example.com/",
                retrieved_at=RETRIEVED_AT,
                observation_count=5,
            )

    def test_no_observations_requires_final_url(self) -> None:
        with pytest.raises(ValueError, match="final_url"):
            DatasheetAttemptResult(
                outcome=DatasheetAuditOutcomeKind.NO_OBSERVATIONS,
                source_name="S",
                source_url="https://example.com/",
                final_url=None,
                retrieved_at=RETRIEVED_AT,
                observation_count=0,
            )

    def test_parse_failed_requires_zero_count(self) -> None:
        with pytest.raises(ValueError, match="observation_count"):
            DatasheetAttemptResult(
                outcome=DatasheetAuditOutcomeKind.PARSE_FAILED,
                source_name="S",
                source_url="https://example.com/",
                final_url="https://example.com/",
                retrieved_at=RETRIEVED_AT,
                observation_count=None,
            )

    def test_parse_failed_valid_shape(self) -> None:
        result = DatasheetAttemptResult(
            outcome=DatasheetAuditOutcomeKind.PARSE_FAILED,
            source_name="S",
            source_url="https://example.com/",
            final_url="https://example.com/",
            retrieved_at=RETRIEVED_AT,
            observation_count=0,
        )
        assert result.observation_count == 0

    def test_fetch_failed_rejects_final_url(self) -> None:
        with pytest.raises(ValueError, match="must not have final_url"):
            DatasheetAttemptResult(
                outcome=DatasheetAuditOutcomeKind.FETCH_FAILED,
                source_name="S",
                source_url="https://example.com/",
                final_url="https://example.com/",
                retrieved_at=None,
                observation_count=0,
            )

    def test_fetch_failed_rejects_retrieved_at(self) -> None:
        with pytest.raises(ValueError, match="must not have retrieved_at"):
            DatasheetAttemptResult(
                outcome=DatasheetAuditOutcomeKind.FETCH_FAILED,
                source_name="S",
                source_url="https://example.com/",
                final_url=None,
                retrieved_at=RETRIEVED_AT,
                observation_count=0,
            )

    def test_fetch_failed_valid_shape(self) -> None:
        result = DatasheetAttemptResult(
            outcome=DatasheetAuditOutcomeKind.FETCH_FAILED,
            source_name="S",
            source_url="https://example.com/",
            final_url=None,
            retrieved_at=None,
            observation_count=0,
        )
        assert result.observation_count == 0

    def test_source_refused_valid_shape(self) -> None:
        result = DatasheetAttemptResult(
            outcome=DatasheetAuditOutcomeKind.SOURCE_REFUSED,
            source_name="S",
            source_url="https://example.com/",
            final_url=None,
            retrieved_at=None,
            observation_count=0,
        )
        assert result.observation_count == 0

    def test_source_refused_rejects_nonzero_observation_count(self) -> None:
        with pytest.raises(ValueError, match="observation_count == 0"):
            DatasheetAttemptResult(
                outcome=DatasheetAuditOutcomeKind.SOURCE_REFUSED,
                source_name="S",
                source_url="https://example.com/",
                final_url=None,
                retrieved_at=None,
                observation_count=5,
            )

    def test_no_datasheet_source_all_none(self) -> None:
        result = DatasheetAttemptResult(
            outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
        )
        assert result.source_name is None
        assert result.source_url is None
        assert result.final_url is None
        assert result.retrieved_at is None
        assert result.observation_count is None

    def test_enriched_rejects_non_tz_timestamp(self) -> None:
        with pytest.raises(ValueError, match="timezone-aware"):
            DatasheetAttemptResult(
                outcome=DatasheetAuditOutcomeKind.ENRICHED,
                source_name="S",
                source_url="https://example.com/",
                final_url="https://example.com/",
                retrieved_at="2025-01-01T00:00:00",
                observation_count=5,
            )


# ---------------------------------------------------------------------------
# BLOCKER 1: ProductEnrichmentAudit NO_DATASHEET_SOURCE must be sole attempt
# ---------------------------------------------------------------------------


class TestProductEnrichmentAuditNoDatasheetSourceConstraint:
    """BLOCKER 1: NO_DATASHEET_SOURCE must be the ONLY attempt."""

    def test_no_datasheet_source_with_other_attempt_rejected(self) -> None:
        with pytest.raises(ValueError, match="NO_DATASHEET_SOURCE must be the only attempt"):
            ProductEnrichmentAudit(
                product_mpn="XP",
                attempts=(
                    DatasheetAttemptResult(
                        outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
                    ),
                    DatasheetAttemptResult(
                        outcome=DatasheetAuditOutcomeKind.FETCH_FAILED,
                        source_name="S",
                        source_url="https://example.com/",
                        final_url=None,
                        retrieved_at=None,
                        observation_count=0,
                    ),
                ),
            )

    def test_multiple_no_datasheet_source_rejected(self) -> None:
        with pytest.raises(ValueError, match="NO_DATASHEET_SOURCE must be the only attempt"):
            ProductEnrichmentAudit(
                product_mpn="XP",
                attempts=(
                    DatasheetAttemptResult(
                        outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
                    ),
                    DatasheetAttemptResult(
                        outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
                    ),
                ),
            )


# ---------------------------------------------------------------------------
# BLOCKER 2: AMBIGUOUS_AUTHORITY legal mixes with NO_MPN_IN_SOURCE
# ---------------------------------------------------------------------------


class TestAmbiguousAuthorityLegalMixes:
    """BLOCKER 2: AMBIGUOUS_AUTHORITY permits NO_MPN_IN_SOURCE alongside
    AMBIGUOUS_MPN_MATCH."""

    def test_ambiguous_plus_no_mpn_in_source(self) -> None:
        """AMBIGUOUS_MPN_MATCH + NO_MPN_IN_SOURCE -> AMBIGUOUS_AUTHORITY."""
        result = ComparableResearchResult(
            kind=ComparableResultKind.AMBIGUOUS_AUTHORITY,
            target_mpn="AMBIGUOUS",
            target_manufacturer=None,
            target_enrichment_audit=None,
            authority_audit=(
                AuthorityAttemptResult(
                    policy_id=POLICY_ID,
                    outcome=AuthorityAuditOutcomeKind.AMBIGUOUS_MPN_MATCH,
                    requested_source_url=SOURCE_URL,
                    fetched_final_url=FINAL_URL,
                    retrieved_at=RETRIEVED_AT,
                ),
                AuthorityAttemptResult(
                    policy_id="other-policy",
                    outcome=AuthorityAuditOutcomeKind.NO_MPN_IN_SOURCE,
                    requested_source_url=SOURCE_URL,
                    fetched_final_url=FINAL_URL,
                    retrieved_at=RETRIEVED_AT,
                ),
            ),
            candidates=(),
        )
        assert result.kind is ComparableResultKind.AMBIGUOUS_AUTHORITY

    def test_matched_plus_matched_plus_no_mpn_in_source(self) -> None:
        """MATCHED + MATCHED + NO_MPN_IN_SOURCE -> AMBIGUOUS_AUTHORITY."""
        result = ComparableResearchResult(
            kind=ComparableResultKind.AMBIGUOUS_AUTHORITY,
            target_mpn="AMBIGUOUS",
            target_manufacturer=None,
            target_enrichment_audit=None,
            authority_audit=(
                AuthorityAttemptResult(
                    policy_id=POLICY_ID,
                    outcome=AuthorityAuditOutcomeKind.MATCHED,
                    requested_source_url=SOURCE_URL,
                    fetched_final_url=FINAL_URL,
                    retrieved_at=RETRIEVED_AT,
                    matching_mpn="AMBIGUOUS",
                ),
                AuthorityAttemptResult(
                    policy_id="other-policy",
                    outcome=AuthorityAuditOutcomeKind.MATCHED,
                    requested_source_url=SOURCE_URL,
                    fetched_final_url=FINAL_URL,
                    retrieved_at=RETRIEVED_AT,
                    matching_mpn="AMBIGUOUS",
                ),
                AuthorityAttemptResult(
                    policy_id="third-policy",
                    outcome=AuthorityAuditOutcomeKind.NO_MPN_IN_SOURCE,
                    requested_source_url=SOURCE_URL,
                    fetched_final_url=FINAL_URL,
                    retrieved_at=RETRIEVED_AT,
                ),
            ),
            candidates=(),
        )
        assert result.kind is ComparableResultKind.AMBIGUOUS_AUTHORITY


# ---------------------------------------------------------------------------
# BLOCKER 3: FULL kind authority evidence binding
# ---------------------------------------------------------------------------


class TestFullAuthorityEvidenceBinding:
    """BLOCKER 3: FULL kind binds matching_mpn to target_mpn."""

    def test_full_requires_matching_mpn_equals_target_mpn(self) -> None:
        with pytest.raises(ValueError, match="matching_mpn"):
            ComparableResearchResult(
                kind=ComparableResultKind.FULL,
                target_mpn="XP15360SE70005",
                target_manufacturer="Seagate",
                target_enrichment_audit=_make_target_enrichment_audit(),
                authority_audit=(AuthorityAttemptResult(
                    policy_id=POLICY_ID,
                    outcome=AuthorityAuditOutcomeKind.MATCHED,
                    requested_source_url=SOURCE_URL,
                    fetched_final_url=FINAL_URL,
                    retrieved_at=RETRIEVED_AT,
                    matching_mpn="WRONG_MPN",
                ),),
                candidates=(),
            )

    def test_full_duplicate_policy_ids_rejected(self) -> None:
        with pytest.raises(ValueError, match="duplicate policy_ids"):
            ComparableResearchResult(
                kind=ComparableResultKind.FULL,
                target_mpn="XP15360SE70005",
                target_manufacturer="Seagate",
                target_enrichment_audit=_make_target_enrichment_audit(),
                authority_audit=(
                    _make_matched_authority(),
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

    def test_ambiguous_duplicate_policy_ids_rejected(self) -> None:
        """Duplicate policy_ids rejected for ALL kinds, not just FULL."""
        with pytest.raises(ValueError, match="duplicate policy_ids"):
            ComparableResearchResult(
                kind=ComparableResultKind.AMBIGUOUS_AUTHORITY,
                target_mpn="AMBIGUOUS",
                target_manufacturer=None,
                target_enrichment_audit=None,
                authority_audit=(
                    AuthorityAttemptResult(
                        policy_id=POLICY_ID,
                        outcome=AuthorityAuditOutcomeKind.AMBIGUOUS_MPN_MATCH,
                        requested_source_url=SOURCE_URL,
                        fetched_final_url=FINAL_URL,
                        retrieved_at=RETRIEVED_AT,
                    ),
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


# ---------------------------------------------------------------------------
# Non-FULL target shape constraints
# ---------------------------------------------------------------------------


class TestNonFullTargetShape:
    """Non-FULL results must not leak authority-established target data."""

    def test_no_authority_match_requires_none_enrichment(self) -> None:
        with pytest.raises(ValueError, match="target_enrichment_audit=None"):
            ComparableResearchResult(
                kind=ComparableResultKind.NO_AUTHORITY_MATCH,
                target_mpn="UNKNOWN",
                target_manufacturer=None,
                target_enrichment_audit=_make_target_enrichment_audit(),
                authority_audit=(AuthorityAttemptResult(
                    policy_id=POLICY_ID,
                    outcome=AuthorityAuditOutcomeKind.NO_MPN_IN_SOURCE,
                    requested_source_url=SOURCE_URL,
                    fetched_final_url=FINAL_URL,
                    retrieved_at=RETRIEVED_AT,
                ),),
                candidates=(),
            )

    def test_ambiguous_requires_none_enrichment(self) -> None:
        with pytest.raises(ValueError, match="target_enrichment_audit=None"):
            ComparableResearchResult(
                kind=ComparableResultKind.AMBIGUOUS_AUTHORITY,
                target_mpn="AMBIGUOUS",
                target_manufacturer=None,
                target_enrichment_audit=_make_target_enrichment_audit(),
                authority_audit=(AuthorityAttemptResult(
                    policy_id=POLICY_ID,
                    outcome=AuthorityAuditOutcomeKind.AMBIGUOUS_MPN_MATCH,
                    requested_source_url=SOURCE_URL,
                    fetched_final_url=FINAL_URL,
                    retrieved_at=RETRIEVED_AT,
                ),),
                candidates=(),
            )

    def test_no_requested_mpn_requires_none_enrichment(self) -> None:
        with pytest.raises(ValueError, match="target_enrichment_audit=None"):
            ComparableResearchResult(
                kind=ComparableResultKind.NO_REQUESTED_MPN,
                target_mpn="",
                target_manufacturer=None,
                target_enrichment_audit=_make_target_enrichment_audit(),
                authority_audit=(AuthorityAttemptResult(
                    policy_id=POLICY_ID,
                    outcome=AuthorityAuditOutcomeKind.NO_REQUESTED_MPN,
                    requested_source_url=SOURCE_URL,
                ),),
                candidates=(),
            )

    def test_no_authority_match_requires_none_manufacturer(self) -> None:
        with pytest.raises(ValueError, match="target_manufacturer=None"):
            ComparableResearchResult(
                kind=ComparableResultKind.NO_AUTHORITY_MATCH,
                target_mpn="UNKNOWN",
                target_manufacturer="Leaked Manufacturer",
                target_enrichment_audit=None,
                authority_audit=(AuthorityAttemptResult(
                    policy_id=POLICY_ID,
                    outcome=AuthorityAuditOutcomeKind.NO_MPN_IN_SOURCE,
                    requested_source_url=SOURCE_URL,
                    fetched_final_url=FINAL_URL,
                    retrieved_at=RETRIEVED_AT,
                ),),
                candidates=(),
            )

    def test_ambiguous_requires_none_manufacturer(self) -> None:
        with pytest.raises(ValueError, match="target_manufacturer=None"):
            ComparableResearchResult(
                kind=ComparableResultKind.AMBIGUOUS_AUTHORITY,
                target_mpn="AMBIGUOUS",
                target_manufacturer="Leaked Manufacturer",
                target_enrichment_audit=None,
                authority_audit=(AuthorityAttemptResult(
                    policy_id=POLICY_ID,
                    outcome=AuthorityAuditOutcomeKind.AMBIGUOUS_MPN_MATCH,
                    requested_source_url=SOURCE_URL,
                    fetched_final_url=FINAL_URL,
                    retrieved_at=RETRIEVED_AT,
                ),),
                candidates=(),
            )

    def test_no_authority_match_requires_nonempty_target_mpn(self) -> None:
        with pytest.raises(ValueError, match="non-empty target_mpn"):
            ComparableResearchResult(
                kind=ComparableResultKind.NO_AUTHORITY_MATCH,
                target_mpn="",
                target_manufacturer=None,
                target_enrichment_audit=None,
                authority_audit=(AuthorityAttemptResult(
                    policy_id=POLICY_ID,
                    outcome=AuthorityAuditOutcomeKind.NO_MPN_IN_SOURCE,
                    requested_source_url=SOURCE_URL,
                    fetched_final_url=FINAL_URL,
                    retrieved_at=RETRIEVED_AT,
                ),),
                candidates=(),
            )

    def test_no_requested_mpn_requires_empty_target_mpn(self) -> None:
        with pytest.raises(ValueError, match="empty target_mpn"):
            ComparableResearchResult(
                kind=ComparableResultKind.NO_REQUESTED_MPN,
                target_mpn="LEAKED_MPN",
                target_manufacturer=None,
                target_enrichment_audit=None,
                authority_audit=(AuthorityAttemptResult(
                    policy_id=POLICY_ID,
                    outcome=AuthorityAuditOutcomeKind.NO_REQUESTED_MPN,
                    requested_source_url=SOURCE_URL,
                ),),
                candidates=(),
            )

    def test_ambiguous_requires_nonempty_target_mpn(self) -> None:
        with pytest.raises(ValueError, match="non-empty target_mpn"):
            ComparableResearchResult(
                kind=ComparableResultKind.AMBIGUOUS_AUTHORITY,
                target_mpn="",
                target_manufacturer=None,
                target_enrichment_audit=None,
                authority_audit=(AuthorityAttemptResult(
                    policy_id=POLICY_ID,
                    outcome=AuthorityAuditOutcomeKind.AMBIGUOUS_MPN_MATCH,
                    requested_source_url=SOURCE_URL,
                    fetched_final_url=FINAL_URL,
                    retrieved_at=RETRIEVED_AT,
                ),),
                candidates=(),
            )


# ---------------------------------------------------------------------------
# BLOCKER 4: FieldAssessmentResult resolution state value/evidence invariants
# ---------------------------------------------------------------------------


class TestFieldAssessmentResolutionStateInvariants:
    """BLOCKER 4: ResolutionState -> value/evidence contracts."""

    def test_verified_rejects_none_value(self) -> None:
        with pytest.raises(ValueError, match="VERIFIED.*non-None"):
            FieldAssessmentResult(
                definition_key="capacity",
                comparison_state=ComparisonState.CANDIDATE_NOT_VERIFIED,
                target_resolution_state=ResolutionState.VERIFIED,
                candidate_resolution_state=ResolutionState.UNKNOWN,
                field_similarity=None,
                target_value=None,
                candidate_value=None,
                target_evidence=(_make_evidence_ref(),),
            )

    def test_verified_rejects_empty_evidence(self) -> None:
        with pytest.raises(ValueError, match="VERIFIED.*non-empty evidence"):
            FieldAssessmentResult(
                definition_key="capacity",
                comparison_state=ComparisonState.CANDIDATE_NOT_VERIFIED,
                target_resolution_state=ResolutionState.VERIFIED,
                candidate_resolution_state=ResolutionState.UNKNOWN,
                field_similarity=None,
                target_value="value",
                candidate_value=None,
                target_evidence=(),
            )

    def test_verified_rejects_no_authoritative_evidence(self) -> None:
        secondary_ref = EvidenceSourceReference(
            source_name="S",
            source_url="https://example.com/",
            evidence_layer=EvidenceLayer.SUPPORT_PAGE,
            source_authority=SourceAuthority.SECONDARY,
            retrieved_at=RETRIEVED_AT,
        )
        with pytest.raises(ValueError, match="AUTHORITATIVE"):
            FieldAssessmentResult(
                definition_key="capacity",
                comparison_state=ComparisonState.CANDIDATE_NOT_VERIFIED,
                target_resolution_state=ResolutionState.VERIFIED,
                candidate_resolution_state=ResolutionState.UNKNOWN,
                field_similarity=None,
                target_value="value",
                candidate_value=None,
                target_evidence=(secondary_ref,),
            )

    def test_unverified_rejects_none_value(self) -> None:
        with pytest.raises(ValueError, match="UNVERIFIED.*non-None"):
            FieldAssessmentResult(
                definition_key="capacity",
                comparison_state=ComparisonState.BOTH_NOT_VERIFIED,
                target_resolution_state=ResolutionState.UNVERIFIED,
                candidate_resolution_state=ResolutionState.UNKNOWN,
                field_similarity=None,
                target_value=None,
                candidate_value=None,
                target_evidence=(_make_evidence_ref(),),
            )

    def test_unverified_rejects_empty_evidence(self) -> None:
        with pytest.raises(ValueError, match="UNVERIFIED.*non-empty"):
            FieldAssessmentResult(
                definition_key="capacity",
                comparison_state=ComparisonState.BOTH_NOT_VERIFIED,
                target_resolution_state=ResolutionState.UNVERIFIED,
                candidate_resolution_state=ResolutionState.UNKNOWN,
                field_similarity=None,
                target_value="value",
                candidate_value=None,
                target_evidence=(),
            )

    def test_conflict_rejects_present_value(self) -> None:
        with pytest.raises(ValueError, match="CONFLICT.*None"):
            FieldAssessmentResult(
                definition_key="capacity",
                comparison_state=ComparisonState.BOTH_NOT_VERIFIED,
                target_resolution_state=ResolutionState.CONFLICT,
                candidate_resolution_state=ResolutionState.UNKNOWN,
                field_similarity=None,
                target_value="should_be_none",
                candidate_value=None,
                target_evidence=(_make_evidence_ref(),),
            )

    def test_conflict_rejects_empty_evidence(self) -> None:
        with pytest.raises(ValueError, match="CONFLICT.*non-empty"):
            FieldAssessmentResult(
                definition_key="capacity",
                comparison_state=ComparisonState.BOTH_NOT_VERIFIED,
                target_resolution_state=ResolutionState.CONFLICT,
                candidate_resolution_state=ResolutionState.UNKNOWN,
                field_similarity=None,
                target_value=None,
                candidate_value=None,
                target_evidence=(),
            )

    def test_unknown_rejects_present_value(self) -> None:
        with pytest.raises(ValueError, match="UNKNOWN.*None"):
            FieldAssessmentResult(
                definition_key="capacity",
                comparison_state=ComparisonState.BOTH_NOT_VERIFIED,
                target_resolution_state=ResolutionState.UNKNOWN,
                candidate_resolution_state=ResolutionState.UNKNOWN,
                field_similarity=None,
                target_value="should_be_none",
                candidate_value=None,
            )

    def test_unknown_permits_empty_evidence(self) -> None:
        """UNKNOWN may have empty evidence (issue-only evidence may exist)."""
        fa = FieldAssessmentResult(
            definition_key="capacity",
            comparison_state=ComparisonState.BOTH_NOT_VERIFIED,
            target_resolution_state=ResolutionState.UNKNOWN,
            candidate_resolution_state=ResolutionState.UNKNOWN,
            field_similarity=None,
            target_value=None,
            candidate_value=None,
        )
        assert fa.target_value is None

    def test_unknown_permits_nonempty_evidence(self) -> None:
        """UNKNOWN may have non-empty evidence."""
        fa = FieldAssessmentResult(
            definition_key="capacity",
            comparison_state=ComparisonState.BOTH_NOT_VERIFIED,
            target_resolution_state=ResolutionState.UNKNOWN,
            candidate_resolution_state=ResolutionState.UNKNOWN,
            field_similarity=None,
            target_value=None,
            candidate_value=None,
            target_evidence=(_make_evidence_ref(),),
        )
        assert fa.target_value is None


# ---------------------------------------------------------------------------
# Field order enforcement (frozen 7B)
# ---------------------------------------------------------------------------


class TestFieldOrderEnforcement:
    """ComparableCandidateResult requires exact canonical field order."""

    def test_rejects_permuted_field_order(self) -> None:
        """Same 12 keys in wrong order are rejected."""
        assessments = _make_all_12_assessments(scored_keys=())
        # Swap first two
        permuted = (assessments[1], assessments[0]) + assessments[2:]
        with pytest.raises(ValueError, match="canonical schema definition order"):
            ComparableCandidateResult(
                candidate_mpn="XP",
                candidate_normalized_mpn="XP",
                scored_field_count=0,
                evidence_coverage=Decimal("0"),
                observed_similarity=None,
                evidence_weighted_similarity=None,
                field_assessments=permuted,
                enrichment_audit=ProductEnrichmentAudit(
                    product_mpn="XP",
                    attempts=(DatasheetAttemptResult(
                        outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
                    ),),
                ),
            )
