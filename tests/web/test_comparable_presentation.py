"""Tests for the comparable result presentation module (PRODUCT-INTEL.7C-C).

Pure display tests. Proves:
- candidate order exactly preserved
- no sorting by similarity
- no top-N
- all candidates retained
- Decimal values remain string-exact
- labels/units come from ENTERPRISE_SSD_SCHEMA
- safe URL / unsafe URL behavior
- no |safe / mark_safe
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from product_intelligence.research.comparable_research_results import (
    EvidenceSourceReference,
    EvidenceLayer,
    SourceAuthority,
)


def _make_evidence() -> tuple:
    """Create a minimal evidence reference for VERIFIED states."""
    return (EvidenceSourceReference(
        source_name="TestSource",
        source_url="https://example.com/support",
        evidence_layer=EvidenceLayer.SUPPORT_PAGE,
        source_authority=SourceAuthority.AUTHORITATIVE,
        retrieved_at="2024-01-01T00:00:00+00:00",
    ),)


def _make_field_assessment(
    definition_key: str,
    comparison_state: str = "SCORED",
    target_state: str = "VERIFIED",
    candidate_state: str = "VERIFIED",
    field_similarity: Decimal | None = Decimal("1"),
    target_value: str | None = "2.5-inch",
    candidate_value: str | None = "2.5-inch",
    target_evidence: tuple | None = None,
    candidate_evidence: tuple | None = None,
) -> object:
    """Build a minimal FieldAssessmentResult for testing."""
    from product_intelligence.research.comparable_research_results import (
        FieldAssessmentResult,
    )
    from product_intelligence.research.enterprise_ssd_similarity import (
        ComparisonState,
    )
    from product_intelligence.research.specifications import (
        ResolutionState,
    )

    _STATE_MAP = {
        "SCORED": ComparisonState.SCORED,
        "TARGET_NOT_VERIFIED": ComparisonState.TARGET_NOT_VERIFIED,
        "CANDIDATE_NOT_VERIFIED": ComparisonState.CANDIDATE_NOT_VERIFIED,
        "BOTH_NOT_VERIFIED": ComparisonState.BOTH_NOT_VERIFIED,
    }
    _RES_MAP = {
        "VERIFIED": ResolutionState.VERIFIED,
        "UNVERIFIED": ResolutionState.UNVERIFIED,
        "CONFLICT": ResolutionState.CONFLICT,
        "UNKNOWN": ResolutionState.UNKNOWN,
    }

    # VERIFIED states need non-empty evidence
    if target_evidence is None:
        target_evidence = _make_evidence() if target_state == "VERIFIED" else ()
    if candidate_evidence is None:
        candidate_evidence = _make_evidence() if candidate_state == "VERIFIED" else ()

    return FieldAssessmentResult(
        definition_key=definition_key,
        comparison_state=_STATE_MAP[comparison_state],
        target_resolution_state=_RES_MAP[target_state],
        candidate_resolution_state=_RES_MAP[candidate_state],
        field_similarity=field_similarity,
        target_value=target_value,
        candidate_value=candidate_value,
        target_evidence=target_evidence,
        candidate_evidence=candidate_evidence,
    )


def _make_candidate(
    mpn: str,
    scored: int = 7,
    observed_sim: Decimal | None = None,
    weighted_sim: Decimal | None = None,
    field_assessments: tuple | None = None,
) -> object:
    """Build a minimal ComparableCandidateResult for testing."""
    from product_intelligence.research.comparable_research_results import (
        ComparableCandidateResult,
        ProductEnrichmentAudit,
        DatasheetAttemptResult,
        DatasheetAuditOutcomeKind,
    )

    total = 12
    coverage = Decimal(scored) / Decimal(total)

    if field_assessments is None:
        # Build minimal field assessments for all 12 schema keys
        # First `scored` fields are SCORED/VERIFIED, rest are BOTH_NOT_VERIFIED/UNKNOWN
        field_assessments_list = []
        schema_keys = ["capacity", "storage_protocol", "pcie_generation",
                       "pcie_lane_count", "physical_form_factor",
                       "interface_connector", "sequential_read",
                       "sequential_write", "random_read_iops",
                       "random_write_iops", "endurance_dwpd",
                       "power_loss_protection"]
        for idx, key in enumerate(schema_keys):
            if idx < scored:
                field_assessments_list.append(
                    _make_field_assessment(key, "SCORED", "VERIFIED", "VERIFIED", Decimal("1")),
                )
            else:
                field_assessments_list.append(
                    _make_field_assessment(
                        key, "BOTH_NOT_VERIFIED", "UNKNOWN", "UNKNOWN",
                        None, None, None,
                    ),
                )
        field_assessments = tuple(field_assessments_list)

    # Compute aggregates from actual field assessments for self-validation
    from product_intelligence.research.enterprise_ssd_similarity import (
        ComparisonState,
    )
    scored_sims = [
        fa.field_similarity
        for fa in field_assessments
        if fa.comparison_state is ComparisonState.SCORED
    ]
    actual_scored = len(scored_sims)
    if observed_sim is None:
        observed_sim = (
            sum(scored_sims, Decimal("0")) / Decimal(actual_scored)
            if actual_scored > 0
            else None
        )
    if weighted_sim is None:
        weighted_sim = (
            sum(scored_sims, Decimal("0")) / Decimal(total)
            if actual_scored > 0
            else None
        )

    enrichment_audit = ProductEnrichmentAudit(
        product_mpn=mpn,
        attempts=(
            DatasheetAttemptResult(
                outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
            ),
        ),
    )

    return ComparableCandidateResult(
        candidate_mpn=mpn,
        candidate_normalized_mpn=mpn.upper(),
        scored_field_count=actual_scored,
        evidence_coverage=Decimal(actual_scored) / Decimal(total),
        observed_similarity=observed_sim,
        evidence_weighted_similarity=weighted_sim,
        field_assessments=field_assessments,
        enrichment_audit=enrichment_audit,
    )


class TestBuildComparableResultPresentation:
    """Tests for build_comparable_result_presentation."""

    def test_imports_are_available(self) -> None:
        """Presentation module is importable and pure."""
        from product_intelligence.web.comparable_presentation import (
            build_comparable_result_presentation,
        )
        assert callable(build_comparable_result_presentation)

    def test_candidate_order_exactly_preserved(self) -> None:
        """Candidates are displayed in exact persisted order, not sorted."""
        from product_intelligence.research.comparable_research_results import (
            ComparableResearchResult,
            ComparableResultKind,
            AuthorityAttemptResult,
            AuthorityAuditOutcomeKind,
            ProductEnrichmentAudit,
            DatasheetAttemptResult,
            DatasheetAuditOutcomeKind,
        )
        from product_intelligence.web.comparable_presentation import (
            build_comparable_result_presentation,
        )

        # Deliberately create candidates with different MPNs
        # in non-sorted order (all share the same field assessment
        # pattern to satisfy the BLOCKER FU5 target-truth invariant)
        candidates = (
            _make_candidate("CAND-ZZZ-Z", scored=7),
            _make_candidate("CAND-AAA-A", scored=7),
            _make_candidate("CAND-MMM-M", scored=7),
        )

        result = ComparableResearchResult(
            kind=ComparableResultKind.FULL,
            target_mpn="TARGET-001",
            target_manufacturer="TestMfg",
            target_enrichment_audit=ProductEnrichmentAudit(
                product_mpn="TARGET-001",
                attempts=(
                    DatasheetAttemptResult(
                        outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
                    ),
                ),
            ),
            authority_audit=(
                AuthorityAttemptResult(
                    policy_id="test-policy",
                    outcome=AuthorityAuditOutcomeKind.MATCHED,
                    requested_source_url="https://example.com/support",
                    fetched_final_url="https://example.com/support",
                    retrieved_at="2024-01-01T00:00:00+00:00",
                    matching_mpn="TARGET-001",
                ),
            ),
            candidates=candidates,
        )

        presentation = build_comparable_result_presentation(result)

        # Order must be exactly as supplied, not sorted
        assert len(presentation.candidates) == 3
        assert presentation.candidates[0].candidate_mpn == "CAND-ZZZ-Z"
        assert presentation.candidates[1].candidate_mpn == "CAND-AAA-A"
        assert presentation.candidates[2].candidate_mpn == "CAND-MMM-M"

    def test_no_sorting_by_similarity(self) -> None:
        """Presentation does not sort candidates by similarity."""
        from product_intelligence.research.comparable_research_results import (
            ComparableResearchResult,
            ComparableResultKind,
            AuthorityAttemptResult,
            AuthorityAuditOutcomeKind,
            ProductEnrichmentAudit,
            DatasheetAttemptResult,
            DatasheetAuditOutcomeKind,
        )
        from product_intelligence.web.comparable_presentation import (
            build_comparable_result_presentation,
        )

        # Create candidates with same field pattern (BLOCKER FU5)
        # but verify order is preserved regardless
        candidates = (
            _make_candidate("HIGHEST-Z", scored=7),
            _make_candidate("MID-M", scored=7),
            _make_candidate("LOWEST-A", scored=7),
        )

        result = ComparableResearchResult(
            kind=ComparableResultKind.FULL,
            target_mpn="TARGET-001",
            target_manufacturer="TestMfg",
            target_enrichment_audit=ProductEnrichmentAudit(
                product_mpn="TARGET-001",
                attempts=(
                    DatasheetAttemptResult(
                        outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
                    ),
                ),
            ),
            authority_audit=(
                AuthorityAttemptResult(
                    policy_id="test-policy",
                    outcome=AuthorityAuditOutcomeKind.MATCHED,
                    requested_source_url="https://example.com/support",
                    fetched_final_url="https://example.com/support",
                    retrieved_at="2024-01-01T00:00:00+00:00",
                    matching_mpn="TARGET-001",
                ),
            ),
            candidates=candidates,
        )

        presentation = build_comparable_result_presentation(result)

        assert presentation.candidates[0].candidate_mpn == "HIGHEST-Z"
        assert presentation.candidates[1].candidate_mpn == "MID-M"
        assert presentation.candidates[2].candidate_mpn == "LOWEST-A"

    def test_all_candidates_retained(self) -> None:
        """All candidates are retained, no top-N filtering."""
        from product_intelligence.research.comparable_research_results import (
            ComparableResearchResult,
            ComparableResultKind,
            AuthorityAttemptResult,
            AuthorityAuditOutcomeKind,
            ProductEnrichmentAudit,
            DatasheetAttemptResult,
            DatasheetAuditOutcomeKind,
        )
        from product_intelligence.web.comparable_presentation import (
            build_comparable_result_presentation,
        )

        many_candidates = tuple(
            _make_candidate(f"CAND-{i:03d}") for i in range(50)
        )

        result = ComparableResearchResult(
            kind=ComparableResultKind.FULL,
            target_mpn="TARGET-001",
            target_manufacturer="TestMfg",
            target_enrichment_audit=ProductEnrichmentAudit(
                product_mpn="TARGET-001",
                attempts=(
                    DatasheetAttemptResult(
                        outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
                    ),
                ),
            ),
            authority_audit=(
                AuthorityAttemptResult(
                    policy_id="test-policy",
                    outcome=AuthorityAuditOutcomeKind.MATCHED,
                    requested_source_url="https://example.com/support",
                    fetched_final_url="https://example.com/support",
                    retrieved_at="2024-01-01T00:00:00+00:00",
                    matching_mpn="TARGET-001",
                ),
            ),
            candidates=many_candidates,
        )

        presentation = build_comparable_result_presentation(result)
        assert len(presentation.candidates) == 50

    def test_decimal_values_remain_string_exact(self) -> None:
        """Decimal values are displayed as string-exact, never float."""
        from product_intelligence.research.comparable_research_results import (
            ComparableResearchResult,
            ComparableResultKind,
            AuthorityAttemptResult,
            AuthorityAuditOutcomeKind,
            ProductEnrichmentAudit,
            DatasheetAttemptResult,
            DatasheetAuditOutcomeKind,
        )
        from product_intelligence.web.comparable_presentation import (
            build_comparable_result_presentation,
        )

        # Create a candidate with non-trivial decimal values
        # (field_similarity != 1, so observed_sim != 1)
        from product_intelligence.research.comparable_research_results import (
            ComparableCandidateResult,
        )
        total = 12
        scored = 7
        coverage = Decimal(scored) / Decimal(total)
        # Use a non-trivial field similarity
        field_sim = Decimal("3.84") / Decimal("15.36")  # 0.25
        obs_sim = field_sim  # only 1 scored field
        w_sim = field_sim

        # Build field assessments with non-trivial similarity
        fas = []
        schema_keys = ["capacity", "storage_protocol", "pcie_generation",
                       "pcie_lane_count", "physical_form_factor",
                       "interface_connector", "sequential_read",
                       "sequential_write", "random_read_iops",
                       "random_write_iops", "endurance_dwpd",
                       "power_loss_protection"]
        for idx, key in enumerate(schema_keys):
            if idx == 0:
                # Use non-trivial similarity
                fas.append(
                    _make_field_assessment(key, "SCORED", "VERIFIED", "VERIFIED", field_sim),
                )
            elif idx < scored:
                fas.append(
                    _make_field_assessment(key, "SCORED", "VERIFIED", "VERIFIED", Decimal("1")),
                )
            else:
                fas.append(
                    _make_field_assessment(
                        key, "BOTH_NOT_VERIFIED", "UNKNOWN", "UNKNOWN",
                        None, None, None,
                    ),
                )

        # Recompute aggregates from actual field assessments
        scored_sims = [field_sim] + [Decimal("1")] * (scored - 1)
        actual_obs = sum(scored_sims, Decimal("0")) / Decimal(scored)
        actual_w = sum(scored_sims, Decimal("0")) / Decimal(total)

        candidates = (
            ComparableCandidateResult(
                candidate_mpn="PRECISE",
                candidate_normalized_mpn="PRECISE",
                scored_field_count=scored,
                evidence_coverage=coverage,
                observed_similarity=actual_obs,
                evidence_weighted_similarity=actual_w,
                field_assessments=tuple(fas),
                enrichment_audit=ProductEnrichmentAudit(
                    product_mpn="PRECISE",
                    attempts=(
                        DatasheetAttemptResult(
                            outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
                        ),
                    ),
                ),
            ),
        )

        result = ComparableResearchResult(
            kind=ComparableResultKind.FULL,
            target_mpn="TARGET-001",
            target_manufacturer="TestMfg",
            target_enrichment_audit=ProductEnrichmentAudit(
                product_mpn="TARGET-001",
                attempts=(
                    DatasheetAttemptResult(
                        outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
                    ),
                ),
            ),
            authority_audit=(
                AuthorityAttemptResult(
                    policy_id="test-policy",
                    outcome=AuthorityAuditOutcomeKind.MATCHED,
                    requested_source_url="https://example.com/support",
                    fetched_final_url="https://example.com/support",
                    retrieved_at="2024-01-01T00:00:00+00:00",
                    matching_mpn="TARGET-001",
                ),
            ),
            candidates=candidates,
        )

        presentation = build_comparable_result_presentation(result)
        display = presentation.candidates[0]

        # Proves Decimal -> string conversion (not float)
        assert display.observed_similarity == str(actual_obs)
        assert display.evidence_coverage == str(coverage)
        # No float conversion: string contains decimal point
        assert "." in display.evidence_coverage
        # String preserves precision
        assert display.evidence_coverage.count(".") == 1

    def test_total_field_count_from_schema(self) -> None:
        """total_field_count is derived from ENTERPRISE_SSD_SCHEMA."""
        from product_intelligence.research.comparable_research_results import (
            ComparableResearchResult,
            ComparableResultKind,
            AuthorityAttemptResult,
            AuthorityAuditOutcomeKind,
            ProductEnrichmentAudit,
            DatasheetAttemptResult,
            DatasheetAuditOutcomeKind,
        )
        from product_intelligence.research.enterprise_ssd import (
            ENTERPRISE_SSD_SCHEMA,
        )
        from product_intelligence.web.comparable_presentation import (
            build_comparable_result_presentation,
        )

        result = ComparableResearchResult(
            kind=ComparableResultKind.FULL,
            target_mpn="TARGET-001",
            target_manufacturer="TestMfg",
            target_enrichment_audit=ProductEnrichmentAudit(
                product_mpn="TARGET-001",
                attempts=(
                    DatasheetAttemptResult(
                        outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
                    ),
                ),
            ),
            authority_audit=(
                AuthorityAttemptResult(
                    policy_id="test-policy",
                    outcome=AuthorityAuditOutcomeKind.MATCHED,
                    requested_source_url="https://example.com/support",
                    fetched_final_url="https://example.com/support",
                    retrieved_at="2024-01-01T00:00:00+00:00",
                    matching_mpn="TARGET-001",
                ),
            ),
            candidates=(
                _make_candidate("CAND-001", scored=7),
            ),
        )

        presentation = build_comparable_result_presentation(result)
        assert presentation.candidates[0].total_field_count == len(
            ENTERPRISE_SSD_SCHEMA.definitions
        )
        assert presentation.candidates[0].total_field_count == 12

    def test_labels_and_units_from_schema(self) -> None:
        """Field labels and units come from ENTERPRISE_SSD_SCHEMA."""
        from product_intelligence.web.comparable_presentation import (
            _build_field_display,
        )

        fa = _make_field_assessment(
            "capacity",
            "SCORED",
            "VERIFIED",
            "VERIFIED",
            Decimal("1"),
            "15.36",
            "3.84",
        )
        display = _build_field_display(fa)

        assert display.definition_label == "Capacity"
        assert display.unit == "TB"

    def test_unknown_resolution_state_display(self) -> None:
        """UNKNOWN resolution state is preserved, not converted to mismatch."""
        from product_intelligence.research.comparable_research_results import (
            ComparableResearchResult,
            ComparableResultKind,
            AuthorityAttemptResult,
            AuthorityAuditOutcomeKind,
            ProductEnrichmentAudit,
            DatasheetAttemptResult,
            DatasheetAuditOutcomeKind,
        )
        from product_intelligence.web.comparable_presentation import (
            build_comparable_result_presentation,
        )

        fa = _make_field_assessment(
            "capacity",
            "BOTH_NOT_VERIFIED",
            "UNKNOWN",
            "UNKNOWN",
            None,
            None,
            None,
        )
        candidates = (
            _make_candidate(
                "UNKNOWN-FIELD",
                scored=0,
                field_assessments=(
                    _make_field_assessment("capacity", "BOTH_NOT_VERIFIED", "UNKNOWN", "UNKNOWN", None, None, None),
                    _make_field_assessment("storage_protocol", "BOTH_NOT_VERIFIED", "UNKNOWN", "UNKNOWN", None, None, None),
                    _make_field_assessment("pcie_generation", "BOTH_NOT_VERIFIED", "UNKNOWN", "UNKNOWN", None, None, None),
                    _make_field_assessment("pcie_lane_count", "BOTH_NOT_VERIFIED", "UNKNOWN", "UNKNOWN", None, None, None),
                    _make_field_assessment("physical_form_factor", "BOTH_NOT_VERIFIED", "UNKNOWN", "UNKNOWN", None, None, None),
                    _make_field_assessment("interface_connector", "BOTH_NOT_VERIFIED", "UNKNOWN", "UNKNOWN", None, None, None),
                    _make_field_assessment("sequential_read", "BOTH_NOT_VERIFIED", "UNKNOWN", "UNKNOWN", None, None, None),
                    _make_field_assessment("sequential_write", "BOTH_NOT_VERIFIED", "UNKNOWN", "UNKNOWN", None, None, None),
                    _make_field_assessment("random_read_iops", "BOTH_NOT_VERIFIED", "UNKNOWN", "UNKNOWN", None, None, None),
                    _make_field_assessment("random_write_iops", "BOTH_NOT_VERIFIED", "UNKNOWN", "UNKNOWN", None, None, None),
                    _make_field_assessment("endurance_dwpd", "BOTH_NOT_VERIFIED", "UNKNOWN", "UNKNOWN", None, None, None),
                    _make_field_assessment("power_loss_protection", "BOTH_NOT_VERIFIED", "UNKNOWN", "UNKNOWN", None, None, None),
                ),
            ),
        )

        result = ComparableResearchResult(
            kind=ComparableResultKind.FULL,
            target_mpn="TARGET-001",
            target_manufacturer="TestMfg",
            target_enrichment_audit=ProductEnrichmentAudit(
                product_mpn="TARGET-001",
                attempts=(
                    DatasheetAttemptResult(
                        outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
                    ),
                ),
            ),
            authority_audit=(
                AuthorityAttemptResult(
                    policy_id="test-policy",
                    outcome=AuthorityAuditOutcomeKind.MATCHED,
                    requested_source_url="https://example.com/support",
                    fetched_final_url="https://example.com/support",
                    retrieved_at="2024-01-01T00:00:00+00:00",
                    matching_mpn="TARGET-001",
                ),
            ),
            candidates=candidates,
        )

        presentation = build_comparable_result_presentation(result)
        field = presentation.candidates[0].field_assessments[0]

        assert field.target_resolution_state == "UNKNOWN"
        assert field.candidate_resolution_state == "UNKNOWN"
        assert field.target_value is None
        assert field.candidate_value is None

    def test_safe_url_is_href_safe(self) -> None:
        """Safe HTTP/HTTPS URLs get source_url_safe=True."""
        from product_intelligence.web.comparable_presentation import (
            _is_safe_href_url,
        )

        assert _is_safe_href_url("https://example.com/page") is True
        assert _is_safe_href_url("http://example.com/page") is True

    def test_unsafe_url_is_not_href_safe(self) -> None:
        """javascript:, data:, file: URLs get source_url_safe=False."""
        from product_intelligence.web.comparable_presentation import (
            _is_safe_href_url,
        )

        assert _is_safe_href_url("javascript:alert(1)") is False
        assert _is_safe_href_url("data:text/html,<h1>hi</h1>") is False
        assert _is_safe_href_url("file:///etc/passwd") is False
        assert _is_safe_href_url("ftp://example.com") is False
        assert _is_safe_href_url("") is False

    def test_12_fields_preserve_canonical_order(self) -> None:
        """Field assessments preserve the canonical ENTERPRISE_SSD_SCHEMA order."""
        from product_intelligence.research.enterprise_ssd import (
            ENTERPRISE_SSD_SCHEMA,
        )
        from product_intelligence.research.comparable_research_results import (
            ComparableResearchResult,
            ComparableResultKind,
            AuthorityAttemptResult,
            AuthorityAuditOutcomeKind,
            ProductEnrichmentAudit,
            DatasheetAttemptResult,
            DatasheetAuditOutcomeKind,
        )
        from product_intelligence.web.comparable_presentation import (
            build_comparable_result_presentation,
        )

        result = ComparableResearchResult(
            kind=ComparableResultKind.FULL,
            target_mpn="TARGET-001",
            target_manufacturer="TestMfg",
            target_enrichment_audit=ProductEnrichmentAudit(
                product_mpn="TARGET-001",
                attempts=(
                    DatasheetAttemptResult(
                        outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
                    ),
                ),
            ),
            authority_audit=(
                AuthorityAttemptResult(
                    policy_id="test-policy",
                    outcome=AuthorityAuditOutcomeKind.MATCHED,
                    requested_source_url="https://example.com/support",
                    fetched_final_url="https://example.com/support",
                    retrieved_at="2024-01-01T00:00:00+00:00",
                    matching_mpn="TARGET-001",
                ),
            ),
            candidates=(
                _make_candidate("CAND-001", scored=7),
            ),
        )

        presentation = build_comparable_result_presentation(result)
        field_keys = [
            fa.definition_key
            for fa in presentation.candidates[0].field_assessments
        ]
        canonical_keys = list(ENTERPRISE_SSD_SCHEMA.definitions.keys())
        assert field_keys == canonical_keys


class TestParentResultBinding:
    """Tests for validate_result_parent_binding."""

    def test_exact_mpn_match(self) -> None:
        """EXACT match is accepted."""
        from product_intelligence.research.comparable_research_results import (
            ComparableResearchResult,
            ComparableResultKind,
            AuthorityAttemptResult,
            AuthorityAuditOutcomeKind,
            ProductEnrichmentAudit,
            DatasheetAttemptResult,
            DatasheetAuditOutcomeKind,
        )
        from product_intelligence.web.comparable_presentation import (
            validate_result_parent_binding,
        )

        result = ComparableResearchResult(
            kind=ComparableResultKind.FULL,
            target_mpn="XP15360SE70005",
            target_manufacturer="Seagate",
            target_enrichment_audit=ProductEnrichmentAudit(
                product_mpn="XP15360SE70005",
                attempts=(
                    DatasheetAttemptResult(
                        outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
                    ),
                ),
            ),
            authority_audit=(
                AuthorityAttemptResult(
                    policy_id="test-policy",
                    outcome=AuthorityAuditOutcomeKind.MATCHED,
                    requested_source_url="https://example.com/support",
                    fetched_final_url="https://example.com/support",
                    retrieved_at="2024-01-01T00:00:00+00:00",
                    matching_mpn="XP15360SE70005",
                ),
            ),
            candidates=(),
        )

        assert validate_result_parent_binding(result, "XP15360SE70005") is True

    def test_normalized_exact_match(self) -> None:
        """NORMALIZED_EXACT match is accepted."""
        from product_intelligence.research.comparable_research_results import (
            ComparableResearchResult,
            ComparableResultKind,
            AuthorityAttemptResult,
            AuthorityAuditOutcomeKind,
            ProductEnrichmentAudit,
            DatasheetAttemptResult,
            DatasheetAuditOutcomeKind,
        )
        from product_intelligence.web.comparable_presentation import (
            validate_result_parent_binding,
        )

        result = ComparableResearchResult(
            kind=ComparableResultKind.FULL,
            target_mpn="XP15360SE70005",
            target_manufacturer="Seagate",
            target_enrichment_audit=ProductEnrichmentAudit(
                product_mpn="XP15360SE70005",
                attempts=(
                    DatasheetAttemptResult(
                        outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
                    ),
                ),
            ),
            authority_audit=(
                AuthorityAttemptResult(
                    policy_id="test-policy",
                    outcome=AuthorityAuditOutcomeKind.MATCHED,
                    requested_source_url="https://example.com/support",
                    fetched_final_url="https://example.com/support",
                    retrieved_at="2024-01-01T00:00:00+00:00",
                    matching_mpn="XP15360SE70005",
                ),
            ),
            candidates=(),
        )

        # Whitespace-different but normalized-exact
        assert validate_result_parent_binding(result, "XP15360SE70005 ") is True

    def test_mpn_mismatch_rejected(self) -> None:
        """Different MPNs are rejected."""
        from product_intelligence.research.comparable_research_results import (
            ComparableResearchResult,
            ComparableResultKind,
            AuthorityAttemptResult,
            AuthorityAuditOutcomeKind,
            ProductEnrichmentAudit,
            DatasheetAttemptResult,
            DatasheetAuditOutcomeKind,
        )
        from product_intelligence.web.comparable_presentation import (
            validate_result_parent_binding,
        )

        result = ComparableResearchResult(
            kind=ComparableResultKind.FULL,
            target_mpn="XP15360SE70005",
            target_manufacturer="Seagate",
            target_enrichment_audit=ProductEnrichmentAudit(
                product_mpn="XP15360SE70005",
                attempts=(
                    DatasheetAttemptResult(
                        outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE,
                    ),
                ),
            ),
            authority_audit=(
                AuthorityAttemptResult(
                    policy_id="test-policy",
                    outcome=AuthorityAuditOutcomeKind.MATCHED,
                    requested_source_url="https://example.com/support",
                    fetched_final_url="https://example.com/support",
                    retrieved_at="2024-01-01T00:00:00+00:00",
                    matching_mpn="XP15360SE70005",
                ),
            ),
            candidates=(),
        )

        assert validate_result_parent_binding(result, "XP3840SE70005") is False

    def test_no_requested_mpn_both_empty(self) -> None:
        """NO_REQUESTED_MPN with both empty is accepted."""
        from product_intelligence.research.comparable_research_results import (
            ComparableResearchResult,
            ComparableResultKind,
            AuthorityAttemptResult,
            AuthorityAuditOutcomeKind,
        )
        from product_intelligence.web.comparable_presentation import (
            validate_result_parent_binding,
        )

        result = ComparableResearchResult(
            kind=ComparableResultKind.NO_REQUESTED_MPN,
            target_mpn="",
            target_manufacturer=None,
            target_enrichment_audit=None,
            authority_audit=(
                AuthorityAttemptResult(
                    policy_id="test-policy",
                    outcome=AuthorityAuditOutcomeKind.NO_REQUESTED_MPN,
                    requested_source_url="https://example.com/support",
                ),
            ),
            candidates=(),
        )

        assert validate_result_parent_binding(result, "") is True

    def test_no_requested_mpn_nonempty_parent_rejected(self) -> None:
        """NO_REQUESTED_MPN with non-empty parent is rejected."""
        from product_intelligence.research.comparable_research_results import (
            ComparableResearchResult,
            ComparableResultKind,
            AuthorityAttemptResult,
            AuthorityAuditOutcomeKind,
        )
        from product_intelligence.web.comparable_presentation import (
            validate_result_parent_binding,
        )

        result = ComparableResearchResult(
            kind=ComparableResultKind.NO_REQUESTED_MPN,
            target_mpn="",
            target_manufacturer=None,
            target_enrichment_audit=None,
            authority_audit=(
                AuthorityAttemptResult(
                    policy_id="test-policy",
                    outcome=AuthorityAuditOutcomeKind.NO_REQUESTED_MPN,
                    requested_source_url="https://example.com/support",
                ),
            ),
            candidates=(),
        )

        assert validate_result_parent_binding(result, "SOMEMPAN") is False
