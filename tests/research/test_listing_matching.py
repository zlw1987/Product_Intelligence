"""Tests for the 3C matching module — synthetic data only.

The same fixture corpus used in 3A/3B tests for extraction and normalisation
is reused here for a separate file (``test_listing_matching_real_fixtures.py``)
that proves real pages classify correctly.
"""

from __future__ import annotations

from decimal import Decimal

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import (
    EvidenceDecision,
    IdentityMatchType,
)
from product_intelligence.research import (
    EvidenceSource,
    ExtractionMethod,
    IdentityRejectionReason,
    ListingIdentityAssessment,
    ListingObservation,
    NormalizedAvailability,
    NormalizedCondition,
    NormalizedListingObservation,
    NormalizationIssue,
    NormalizationIssueCode,
    assess_listing_identity,
    assess_listing_identities,
    normalize_listing_observation,
)
from product_intelligence.research.matching import (
    _clean_mpn_field_wrapper,
    _classify_partial,
)


# -- Helpers ----------------------------------------------------------------


def _make_observation(
    mpn_text: str | None = None,
    sku_text: str | None = None,
    product_title: str | None = None,
    price_text: str | None = None,
    **kwargs: object,
) -> ListingObservation:
    """Build a synthetic ``ListingObservation`` with defaults for
    fields under test.
    """
    method = kwargs.get("extraction_method", ExtractionMethod.JSON_LD)
    return ListingObservation(
        source_url="https://example.com/product",
        product_title=product_title or "Test Product",
        brand_text=kwargs.get("brand_text", None),
        manufacturer_part_number_text=mpn_text,
        sku_text=sku_text,
        price_text=price_text,
        currency_text=kwargs.get("currency_text", None),
        availability_text=kwargs.get("availability_text", None),
        condition_text=kwargs.get("condition_text", None),
        seller_text=kwargs.get("seller_text", None),
        extraction_method=method,
        raw_reference=kwargs.get("raw_reference", None),
    )


def _make_normalized(
    observation: ListingObservation,
) -> NormalizedListingObservation:
    """Normalise an observation for the matching tests.

    The actual normalised values don't affect matching, but the API requires
    a full ``NormalizedListingObservation``.
    """
    return normalize_listing_observation(observation)


def _make_request(
    mpn: str = "MZ-QL23T800",
    description: str = "Test product",
) -> ResearchRequest:
    return ResearchRequest(
        manufacturer_part_number=mpn,
        description=description,
    )


# -- Wrapper cleanup --------------------------------------------------------


class TestWrapperCleanup:
    """The ``mpn:`` prefix stripping is narrow and source-specific."""

    def test_strips_mpnlower_prefix(self) -> None:
        result = _clean_mpn_field_wrapper("mpn:MZ-QL23T800")
        assert result == "MZ-QL23T800"

    def test_strips_mpnlowercase_prefix(self) -> None:
        result = _clean_mpn_field_wrapper("MPN:MZ-QL23T800")
        assert result == "MZ-QL23T800"

    def test_strips_mixedcase_prefix(self) -> None:
        result = _clean_mpn_field_wrapper("Mpn:MZ-QL23T800")
        assert result == "MZ-QL23T800"

    def test_leaves_other_prefixes_untouched(self) -> None:
        result = _clean_mpn_field_wrapper("brand:MZ-QL23T800")
        assert result == "brand:MZ-QL23T800"

    def test_leaves_no_prefix_untouched(self) -> None:
        result = _clean_mpn_field_wrapper("MZ-QL23T800")
        assert result == "MZ-QL23T800"

    def test_leaves_colon_in_middle(self) -> None:
        result = _clean_mpn_field_wrapper("MZ:QL:23T800")
        assert result == "MZ:QL:23T800"

    def test_preserves_trailing_text_after_strip(self) -> None:
        result = _clean_mpn_field_wrapper("mpn:  ABC-123  ")
        # strip() removes surrounding whitespace, wrapper is then removed.
        assert result == "  ABC-123"


# -- Narrow PARTIAL classification ------------------------------------------


class TestClassifyPartial:
    """PARTIAL requires an explicit boundary after the prefix."""

    def test_partial_at_hyphen_boundary(self) -> None:
        result = _classify_partial("MZ", "MZ-QL23T800")
        assert result is IdentityMatchType.PARTIAL

    def test_partial_at_underscore_boundary(self) -> None:
        result = _classify_partial("ABC", "ABC_DEF")
        assert result is IdentityMatchType.PARTIAL

    def test_partial_at_slash_boundary(self) -> None:
        result = _classify_partial("ABC", "ABC/DEF")
        assert result is IdentityMatchType.PARTIAL

    def test_partial_at_dot_boundary(self) -> None:
        result = _classify_partial("ABC", "ABC.DEF")
        assert result is IdentityMatchType.PARTIAL

    def test_no_partial_when_prefix_is_not_at_boundary(self) -> None:
        result = _classify_partial("ABC123", "ABC1234")
        assert result is None

    def test_no_partial_for_different_strings(self) -> None:
        result = _classify_partial("ABC123", "XYZ789")
        assert result is None

    def test_no_partial_for_equal_strings(self) -> None:
        result = _classify_partial("ABC123", "ABC123")
        assert result is None

    def test_no_partial_for_empty_requested(self) -> None:
        result = _classify_partial("", "ABC123")
        assert result is None

    def test_no_partial_for_empty_candidate(self) -> None:
        result = _classify_partial("ABC123", "")
        assert result is None

    def test_partial_reversed_order(self) -> None:
        result = _classify_partial("MZ-QL23T800", "MZ")
        assert result is IdentityMatchType.PARTIAL

    def test_same_length_different_not_partial(self) -> None:
        result = _classify_partial("ABC123", "XYZ123")
        assert result is None


# -- Acceptance: explicit MPN, EXACT match ----------------------------------


class TestAcceptExactMatch:
    """EXACT match on explicit MPN produces ACCEPTED."""

    def test_exact_character_for_character(self) -> None:
        obs = _make_observation(mpn_text="MZ-QL23T800")
        norm = _make_normalized(obs)
        req = _make_request("MZ-QL23T800")

        result = assess_listing_identity(req, norm)

        assert result.decision is EvidenceDecision.ACCEPTED
        assert result.match_type is IdentityMatchType.EXACT
        assert result.candidate_evidence_source is EvidenceSource.EXPLICIT_MPN_FIELD
        assert result.rejection_reason is None

    def test_exact_match_preserves_audit_trail(self) -> None:
        obs = _make_observation(mpn_text="MZ-QL23T800")
        norm = _make_normalized(obs)
        req = _make_request("MZ-QL23T800")

        result = assess_listing_identity(req, norm)

        assert result.requested_part_number == "MZ-QL23T800"
        assert result.candidate_part_number_raw == "MZ-QL23T800"
        assert result.candidate_part_number_compared == "MZ-QL23T800"


# -- Acceptance: explicit MPN, NORMALIZED_EXACT match -----------------------


class TestAcceptNormalizedExactMatch:
    """NORMALIZED_EXACT match on explicit MPN produces ACCEPTED."""

    def test_normalized_exact_case_and_whitespace(self) -> None:
        obs = _make_observation(mpn_text="mz-ql23t800")
        norm = _make_normalized(obs)
        req = _make_request("MZ-QL23T800")

        result = assess_listing_identity(req, norm)

        assert result.decision is EvidenceDecision.ACCEPTED
        assert result.match_type is IdentityMatchType.NORMALIZED_EXACT
        assert result.rejection_reason is None

    def test_normalized_exact_multiple_whitespace_runs(self) -> None:
        obs = _make_observation(mpn_text="MZ  QL23T800")
        norm = _make_normalized(obs)
        req = _make_request("MZ-QL23T800")

        result = assess_listing_identity(req, norm)

        assert result.decision is EvidenceDecision.ACCEPTED
        assert result.match_type is IdentityMatchType.NORMALIZED_EXACT

    def test_wrapper_cleaned_then_normalized_exact(self) -> None:
        obs = _make_observation(mpn_text="mpn:MZ-QL23T800")
        norm = _make_normalized(obs)
        req = _make_request("MZ-QL23T800")

        result = assess_listing_identity(req, norm)

        assert result.decision is EvidenceDecision.ACCEPTED
        assert result.match_type is IdentityMatchType.EXACT
        assert result.candidate_part_number_raw == "mpn:MZ-QL23T800"
        assert result.candidate_part_number_compared == "MZ-QL23T800"


# -- Rejection: no requested MPN --------------------------------------------


class TestRejectionNoRequestedMPN:
    """Description-only request cannot establish identity."""

    def test_description_only_undecided(self) -> None:
        obs = _make_observation(mpn_text="MZ-QL23T800")
        norm = _make_normalized(obs)
        req = ResearchRequest(
            manufacturer_part_number="",
            description="Some SSD",
        )

        result = assess_listing_identity(req, norm)

        assert result.decision is EvidenceDecision.UNDECIDED
        assert result.rejection_reason is IdentityRejectionReason.NO_REQUESTED_MPN
        assert result.match_type is IdentityMatchType.UNKNOWN
        assert result.requested_part_number == ""

    def test_description_only_wrapped_explicit_mpn(self) -> None:
        """A: Description-only request + wrapped explicit MPN (mpn: prefix).

        Regression: the builder must apply mpn: wrapper cleanup even when
        there is no requested MPN to compare against. The constructor
        invariant requires compared == _clean_mpn_field_wrapper(raw) for
        EXPLICIT_MPN_FIELD regardless of decision.
        """
        obs = _make_observation(mpn_text="mpn:MZ-QL23T800")
        norm = _make_normalized(obs)
        req = ResearchRequest(
            manufacturer_part_number="",
            description="Samsung PM9A3 SSD",
        )

        result = assess_listing_identity(req, norm)

        assert result.decision is EvidenceDecision.UNDECIDED
        assert result.match_type is IdentityMatchType.UNKNOWN
        assert result.rejection_reason is IdentityRejectionReason.NO_REQUESTED_MPN
        assert result.candidate_evidence_source is EvidenceSource.EXPLICIT_MPN_FIELD
        assert result.candidate_part_number_raw == "mpn:MZ-QL23T800"
        assert result.candidate_part_number_compared == "MZ-QL23T800"

    def test_description_only_wrapper_only_field(self) -> None:
        """B: Description-only request + mpn: wrapper with no actual value.

        mpn_text='mpn:' -> raw='mpn:', compared='' after cleanup.
        No exception — UNDECIDED with NO_REQUESTED_MPN.
        """
        obs = _make_observation(mpn_text="mpn:")
        norm = _make_normalized(obs)
        req = ResearchRequest(
            manufacturer_part_number="",
            description="Some SSD",
        )

        result = assess_listing_identity(req, norm)

        assert result.decision is EvidenceDecision.UNDECIDED
        assert result.match_type is IdentityMatchType.UNKNOWN
        assert result.rejection_reason is IdentityRejectionReason.NO_REQUESTED_MPN
        assert result.candidate_evidence_source is EvidenceSource.EXPLICIT_MPN_FIELD
        assert result.candidate_part_number_raw == "mpn:"
        assert result.candidate_part_number_compared == ""

    def test_description_only_sku_unchanged(self) -> None:
        """C: Description-only request + SKU field (no transformation).

        Existing behavior: SKU text is raw and compared both unchanged.
        """
        obs = _make_observation(mpn_text=None, sku_text="RETAIL-501489")
        norm = _make_normalized(obs)
        req = ResearchRequest(
            manufacturer_part_number="",
            description="Some SSD",
        )

        result = assess_listing_identity(req, norm)

        assert result.decision is EvidenceDecision.UNDECIDED
        assert result.rejection_reason is IdentityRejectionReason.NO_REQUESTED_MPN
        assert result.candidate_evidence_source is EvidenceSource.SKU_FIELD
        assert result.candidate_part_number_raw == "RETAIL-501489"
        assert result.candidate_part_number_compared == "RETAIL-501489"

    def test_description_only_no_evidence(self) -> None:
        """C (cont.): Description-only request + no evidence at all.

        Existing behavior: NONE source with empty raw/compared.
        """
        obs = _make_observation(
            mpn_text=None, sku_text=None, product_title="Generic Storage",
        )
        norm = _make_normalized(obs)
        req = ResearchRequest(
            manufacturer_part_number="",
            description="Some SSD",
        )

        result = assess_listing_identity(req, norm)

        assert result.decision is EvidenceDecision.UNDECIDED
        assert result.rejection_reason is IdentityRejectionReason.NO_REQUESTED_MPN
        assert result.candidate_evidence_source is EvidenceSource.NONE
        assert result.candidate_part_number_raw == ""
        assert result.candidate_part_number_compared == ""


# -- Rejection: no explicit MPN evidence ------------------------------------


class TestRejectionNoExplicitMPN:
    """SKU and title text alone produce REJECTED, never ACCEPTED."""

    def test_sku_only_rejected(self) -> None:
        obs = _make_observation(
            sku_text="MZ-QL23T800",
            mpn_text=None,
        )
        norm = _make_normalized(obs)
        req = _make_request("MZ-QL23T800")

        result = assess_listing_identity(req, norm)

        assert result.decision is EvidenceDecision.REJECTED
        assert result.rejection_reason is IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE
        assert result.candidate_evidence_source is EvidenceSource.SKU_FIELD

    def test_sku_not_matching_rejected(self) -> None:
        obs = _make_observation(
            sku_text="RETAIL-501489",
            mpn_text=None,
        )
        norm = _make_normalized(obs)
        req = _make_request("MZ-QL23T800")

        result = assess_listing_identity(req, norm)

        assert result.decision is EvidenceDecision.REJECTED
        assert result.rejection_reason is IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE
        assert result.candidate_evidence_source is EvidenceSource.SKU_FIELD

    def test_title_match_only_rejected(self) -> None:
        obs = _make_observation(
            product_title="Samsung MZ-QL23T800 PM9A3 3.84TB SSD",
            mpn_text=None,
            sku_text=None,
        )
        norm = _make_normalized(obs)
        req = _make_request("MZ-QL23T800")

        result = assess_listing_identity(req, norm)

        assert result.decision is EvidenceDecision.REJECTED
        assert result.rejection_reason is IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE
        assert result.candidate_evidence_source is EvidenceSource.TITLE_TEXT

    def test_no_evidence_at_all_rejected(self) -> None:
        obs = _make_observation(
            product_title="Generic Storage Device",
            mpn_text=None,
            sku_text=None,
        )
        norm = _make_normalized(obs)
        req = _make_request("MZ-QL23T800")

        result = assess_listing_identity(req, norm)

        assert result.decision is EvidenceDecision.REJECTED
        assert result.rejection_reason is IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE
        assert result.candidate_evidence_source is EvidenceSource.NONE

    def test_title_partial_word_match_not_recorded(self) -> None:
        """MPN appearing inside another word in the title is not evidence."""
        obs = _make_observation(
            product_title="Samsung MZQL23T8000 Ultra SSD",
            mpn_text=None,
            sku_text=None,
        )
        norm = _make_normalized(obs)
        req = _make_request("MZ-QL23T800")

        result = assess_listing_identity(req, norm)

        # Not matched as a token — no evidence source from title.
        assert result.candidate_evidence_source is EvidenceSource.NONE
        assert result.decision is EvidenceDecision.REJECTED


# -- Rejection: MPN mismatch -----------------------------------------------


class TestRejectionMPNMismatch:
    """Explicit MPN that doesn't match is REJECTED with MPN_MISMATCH."""

    def test_different_mpn_rejected(self) -> None:
        obs = _make_observation(mpn_text="ABC-123")
        norm = _make_normalized(obs)
        req = _make_request("MZ-QL23T800")

        result = assess_listing_identity(req, norm)

        assert result.decision is EvidenceDecision.REJECTED
        assert result.rejection_reason is IdentityRejectionReason.MPN_MISMATCH
        assert result.match_type is IdentityMatchType.UNKNOWN

    def test_one_character_difference_rejected(self) -> None:
        obs = _make_observation(mpn_text="MZ-QL23T801")
        norm = _make_normalized(obs)
        req = _make_request("MZ-QL23T800")

        result = assess_listing_identity(req, norm)

        assert result.decision is EvidenceDecision.REJECTED
        assert result.rejection_reason is IdentityRejectionReason.MPN_MISMATCH

    def test_similar_but_different_rejected(self) -> None:
        obs = _make_observation(mpn_text="MZ-QL23T800-1")
        norm = _make_normalized(obs)
        req = _make_request("MZ-QL23T800")

        result = assess_listing_identity(req, norm)

        assert result.decision is EvidenceDecision.REJECTED


# -- Rejection: PARTIAL only ------------------------------------------------


class TestRejectionPartial:
    """PARTIAL MPN match is explicitly rejected."""

    def test_partial_mpn_rejected(self) -> None:
        obs = _make_observation(mpn_text="MZ")
        norm = _make_normalized(obs)
        req = _make_request("MZ-QL23T800")

        result = assess_listing_identity(req, norm)

        assert result.decision is EvidenceDecision.REJECTED
        assert result.rejection_reason is IdentityRejectionReason.PARTIAL_MPN_ONLY
        assert result.match_type is IdentityMatchType.PARTIAL

    def test_partial_not_when_prefix_ends_mid_token(self) -> None:
        """MZ_QL vs MZ_QL23T800: the prefix ends mid-alphanumeric token, so
        it is not classified as partial (boundary is '2', not a separator)."""
        obs = _make_observation(mpn_text="MZ_QL")
        norm = _make_normalized(obs)
        req = _make_request("MZ_QL23T800")

        result = assess_listing_identity(req, norm)

        assert result.decision is EvidenceDecision.REJECTED
        assert result.rejection_reason is IdentityRejectionReason.MPN_MISMATCH

    def test_different_separator_not_partial(self) -> None:
        """Underscore vs hyphen are different separators — no partial."""
        obs = _make_observation(mpn_text="MZ_QL")
        norm = _make_normalized(obs)
        req = _make_request("MZ-QL23T800")

        result = assess_listing_identity(req, norm)

        assert result.decision is EvidenceDecision.REJECTED
        assert result.rejection_reason is IdentityRejectionReason.MPN_MISMATCH

    def test_partial_not_at_boundary_not_classified(self) -> None:
        obs = _make_observation(mpn_text="MZQL")
        norm = _make_normalized(obs)
        req = _make_request("MZ-QL23T800")

        result = assess_listing_identity(req, norm)

        assert result.decision is EvidenceDecision.REJECTED
        assert result.rejection_reason is IdentityRejectionReason.MPN_MISMATCH
        assert result.match_type is IdentityMatchType.UNKNOWN

    def test_longer_is_partial_of_shorter(self) -> None:
        obs = _make_observation(mpn_text="MZ-QL23T800")
        norm = _make_normalized(obs)
        req = _make_request("MZ")

        result = assess_listing_identity(req, norm)

        assert result.decision is EvidenceDecision.REJECTED
        assert result.rejection_reason is IdentityRejectionReason.PARTIAL_MPN_ONLY


# -- Assessment dataclass ---------------------------------------------------


class TestAssessmentContract:
    """The assessment contract is frozen and auditable."""

    def test_assessment_is_frozen(self) -> None:
        obs = _make_observation(mpn_text="MZ-QL23T800")
        norm = _make_normalized(obs)
        req = _make_request("MZ-QL23T800")

        result = assess_listing_identity(req, norm)

        import pytest

        with pytest.raises(Exception):
            result.decision = EvidenceDecision.REJECTED  # type: ignore

    def test_normalized_listing_reachable(self) -> None:
        obs = _make_observation(mpn_text="MZ-QL23T800")
        norm = _make_normalized(obs)
        req = _make_request("MZ-QL23T800")

        result = assess_listing_identity(req, norm)

        assert result.normalized_listing is norm
        assert result.normalized_listing.observation is obs

    def test_rejection_reason_none_when_accepted(self) -> None:
        obs = _make_observation(mpn_text="MZ-QL23T800")
        norm = _make_normalized(obs)
        req = _make_request("MZ-QL23T800")

        result = assess_listing_identity(req, norm)

        assert result.decision is EvidenceDecision.ACCEPTED
        assert result.rejection_reason is None


# -- Batch entry point -----------------------------------------------------


class TestBatchAssessment:
    """assess_listing_identities processes a sequence."""

    def test_processes_multiple_listings(self) -> None:
        obs1 = _make_observation(mpn_text="MZ-QL23T800")
        obs2 = _make_observation(mpn_text="DIFFERENT-123")
        obs3 = _make_observation(mpn_text=None, sku_text="RETAIL-001")
        norm1 = _make_normalized(obs1)
        norm2 = _make_normalized(obs2)
        norm3 = _make_normalized(obs3)
        req = _make_request("MZ-QL23T800")

        results = assess_listing_identities(req, (norm1, norm2, norm3))

        assert len(results) == 3
        assert results[0].decision is EvidenceDecision.ACCEPTED
        assert results[1].decision is EvidenceDecision.REJECTED
        assert results[2].decision is EvidenceDecision.REJECTED

    def test_returns_tuple(self) -> None:
        obs = _make_observation(mpn_text="MZ-QL23T800")
        norm = _make_normalized(obs)
        req = _make_request("MZ-QL23T800")

        results = assess_listing_identities(req, (norm,))

        assert isinstance(results, tuple)

    def test_empty_sequence(self) -> None:
        req = _make_request("MZ-QL23T800")
        results = assess_listing_identities(req, ())
        assert results == ()


# -- Edge cases --------------------------------------------------------------


class TestEdgeCases:
    """Boundary conditions and unusual inputs."""

    def test_mpn_with_underscore_data_not_treated_as_separator(self) -> None:
        """_ is data, not a hyphen."""
        obs = _make_observation(mpn_text="MZ_QL23T800")
        norm = _make_normalized(obs)
        req = _make_request("MZ-QL23T800")

        result = assess_listing_identity(req, norm)

        # _ and - are different; not an exact or normalized match.
        assert result.decision is EvidenceDecision.REJECTED

    def test_mpn_with_slash_not_treated_as_separator(self) -> None:
        obs = _make_observation(mpn_text="MZ/QL23T800")
        norm = _make_normalized(obs)
        req = _make_request("MZ-QL23T800")

        result = assess_listing_identity(req, norm)

        assert result.decision is EvidenceDecision.REJECTED

    def test_whitespace_only_mpn_treated_as_missing(self) -> None:
        """ResearchRequest strips whitespace; "" is treated as missing."""
        obs = _make_observation(mpn_text="MZ-QL23T800")
        norm = _make_normalized(obs)
        # ResearchRequest.strip() turns "   " into "".
        req = ResearchRequest(
            manufacturer_part_number="   ",
            description="Something",
        )
        assert req.manufacturer_part_number == ""

        result = assess_listing_identity(req, norm)

        assert result.decision is EvidenceDecision.UNDECIDED

    def test_both_fields_empty_request(self) -> None:
        """A request with no MPN and no description can still be constructed
        (the contract says at least one must be non-empty)."""
        obs = _make_observation(mpn_text="MZ-QL23T800")
        norm = _make_normalized(obs)

        # ResearchRequest raises when both are empty.
        import pytest

        with pytest.raises(ValueError):
            ResearchRequest(manufacturer_part_number="", description="")

    def test_mpn_wrapper_with_trailing_colon(self) -> None:
        """mpn: prefix with nothing after is still stripped."""
        result = _clean_mpn_field_wrapper("mpn:")
        assert result == ""

    def test_title_text_match_case_sensitivity(self) -> None:
        """Title text search is case-sensitive for the MPN token."""
        obs = _make_observation(
            product_title="Samsung MZ-QL23T800 Enterprise SSD",
            mpn_text=None,
            sku_text=None,
        )
        norm = _make_normalized(obs)
        req = _make_request("MZ-QL23T800")

        result = assess_listing_identity(req, norm)

        assert result.candidate_evidence_source is EvidenceSource.TITLE_TEXT
        assert result.decision is EvidenceDecision.REJECTED

    def test_evidence_priority_mpn_over_sku(self) -> None:
        """When both MPN and SKU exist, MPN wins."""
        obs = _make_observation(
            mpn_text="REQ-MPN",
            sku_text="MZ-QL23T800",
        )
        norm = _make_normalized(obs)
        req = _make_request("REQ-MPN")

        result = assess_listing_identity(req, norm)

        assert result.candidate_evidence_source is EvidenceSource.EXPLICIT_MPN_FIELD
        assert result.decision is EvidenceDecision.ACCEPTED
        assert result.match_type is IdentityMatchType.EXACT

    def test_sku_matching_requested_mpn_still_rejected(self) -> None:
        """Even if the SKU happens to equal the requested MPN, no accept."""
        obs = _make_observation(
            mpn_text=None,
            sku_text="MZ-QL23T800",
        )
        norm = _make_normalized(obs)
        req = _make_request("MZ-QL23T800")

        result = assess_listing_identity(req, norm)

        assert result.decision is EvidenceDecision.REJECTED
        assert result.rejection_reason is IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE


# -- Historical / adversarial regressions (2A-FU1 safety property) -----------


class TestStructurePreservingNonMatches:
    """Cases that MUST NOT produce NORMALIZED_EXACT.

    These are the exact failures 2A-FU1 corrected. They are regression tests:
    if any of them starts passing as NORMALIZED_EXACT, the normalization has
    regressed to deleting separator position, which is the false-exact failure
    this system exists to avoid.
    """

    def test_missing_boundary_rejected_unknown(self) -> None:
        """ABC123 (no boundary) vs ABC-123 (with boundary) — UNKNOWN, not
        NORMALIZED_EXACT. The 2A-FU1 canonical case."""
        obs = _make_observation(mpn_text="ABC123")
        norm = _make_normalized(obs)
        req = _make_request("ABC-123")

        result = assess_listing_identity(req, norm)

        assert result.decision is EvidenceDecision.REJECTED
        assert result.match_type is IdentityMatchType.UNKNOWN
        assert result.rejection_reason is IdentityRejectionReason.MPN_MISMATCH

    def test_moved_boundary_rejected_unknown(self) -> None:
        """AB-C123 vs ABC-123 — boundary in different place — UNKNOWN."""
        obs = _make_observation(mpn_text="AB-C123")
        norm = _make_normalized(obs)
        req = _make_request("ABC-123")

        result = assess_listing_identity(req, norm)

        assert result.decision is EvidenceDecision.REJECTED
        assert result.match_type is IdentityMatchType.UNKNOWN

    def test_underscore_not_hyphen_rejected_unknown(self) -> None:
        """ABC_123 vs ABC-123 — underscore is data, not a hyphen."""
        obs = _make_observation(mpn_text="ABC_123")
        norm = _make_normalized(obs)
        req = _make_request("ABC-123")

        result = assess_listing_identity(req, norm)

        assert result.decision is EvidenceDecision.REJECTED
        assert result.match_type is IdentityMatchType.UNKNOWN

    def test_double_hyphen_not_single_rejected_unknown(self) -> None:
        """ABC--123 vs ABC-123 — repeated punctuation is not collapsed."""
        obs = _make_observation(mpn_text="ABC--123")
        norm = _make_normalized(obs)
        req = _make_request("ABC-123")

        result = assess_listing_identity(req, norm)

        assert result.decision is EvidenceDecision.REJECTED
        assert result.match_type is IdentityMatchType.UNKNOWN


class TestNearMissNoCorrection:
    """One-character difference stays a difference. No O/0 correction."""

    def test_letter_o_vs_digit_0_rejected(self) -> None:
        """MZ-QL23T8OO (letter O) vs MZ-QL23T800 (digit 0) — REJECTED.
        No character-confusion table exists."""
        obs = _make_observation(mpn_text="MZ-QL23T8OO")
        norm = _make_normalized(obs)
        req = _make_request("MZ-QL23T800")

        result = assess_listing_identity(req, norm)

        assert result.decision is EvidenceDecision.REJECTED
        assert result.match_type is IdentityMatchType.UNKNOWN


class TestRealisticPartial:
    """Real-world PARTIAL cases and the boundary between partial and unknown."""

    def test_realistic_long_partial_rejected(self) -> None:
        """MTFDKCC3T8TFR vs MTFDKCC3T8TFR-1BC1ZABYY — full prefix ending at
        a hyphen boundary — PARTIAL, REJECTED."""
        obs = _make_observation(mpn_text="MTFDKCC3T8TFR")
        norm = _make_normalized(obs)
        req = _make_request("MTFDKCC3T8TFR-1BC1ZABYY")

        result = assess_listing_identity(req, norm)

        assert result.decision is EvidenceDecision.REJECTED
        assert result.match_type is IdentityMatchType.PARTIAL
        assert result.rejection_reason is IdentityRejectionReason.PARTIAL_MPN_ONLY

    def test_mid_token_prefix_not_partial(self) -> None:
        """ABC123 vs ABC1234 — one is a prefix of the other, but the boundary
        character after the prefix ('4') is not a separator. This is UNKNOWN,
        not PARTIAL."""
        obs = _make_observation(mpn_text="ABC1234")
        norm = _make_normalized(obs)
        req = _make_request("ABC123")

        result = assess_listing_identity(req, norm)

        assert result.decision is EvidenceDecision.REJECTED
        assert result.match_type is IdentityMatchType.UNKNOWN
        assert result.rejection_reason is IdentityRejectionReason.MPN_MISMATCH


# -- Empty / structure-only explicit MPN reasoning --------------------------


class TestEmptyExplicitMPN:
    """When the explicit MPN field carries no part-number content after
    wrapper cleanup, the listing is REJECTED with NO_EXPLICIT_MPN_EVIDENCE,
    not MPN_MISMATCH (there is nothing to mismatch against)."""

    def test_mpn_wrapper_only_rejected_no_evidence(self) -> None:
        """mpn_text='mpn:' -> candidate='' -> no part-number content ->
        NO_EXPLICIT_MPN_EVIDENCE, not MPN_MISMATCH."""
        obs = _make_observation(mpn_text="mpn:")
        norm = _make_normalized(obs)
        req = _make_request("MZ-QL23T800")

        result = assess_listing_identity(req, norm)

        assert result.decision is EvidenceDecision.REJECTED
        assert result.rejection_reason is IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE
        assert result.match_type is IdentityMatchType.UNKNOWN
        assert result.candidate_part_number_raw == "mpn:"
        assert result.candidate_part_number_compared == ""

    def test_structure_only_hyphens_rejected_no_evidence(self) -> None:
        """mpn_text='---' (structure only, no content) -> NO_EXPLICIT_MPN_EVIDENCE."""
        obs = _make_observation(mpn_text="---")
        norm = _make_normalized(obs)
        req = _make_request("MZ-QL23T800")

        result = assess_listing_identity(req, norm)

        assert result.decision is EvidenceDecision.REJECTED
        assert result.rejection_reason is IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE
        assert result.match_type is IdentityMatchType.UNKNOWN

    def test_whitespace_only_mpn_field_rejected_no_evidence(self) -> None:
        """mpn_text='   ' -> strip -> '' -> no content -> NO_EXPLICIT_MPN_EVIDENCE."""
        obs = _make_observation(mpn_text="   ")
        norm = _make_normalized(obs)
        req = _make_request("MZ-QL23T800")

        result = assess_listing_identity(req, norm)

        assert result.decision is EvidenceDecision.REJECTED
        assert result.rejection_reason is IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE


# -- ListingIdentityAssessment constructor invariants -----------------------


class TestAssessmentInvariants:
    """Direct construction of ListingIdentityAssessment enforces the 3C
    state invariants. These tests use the constructor directly, not the
    builder, to prove impossible states are rejected at the type level."""

    def _minimal_observation(self) -> ListingObservation:
        return _make_observation()

    def _minimal_normalized(self) -> NormalizedListingObservation:
        return _make_normalized(self._minimal_observation())

    # -- ACCEPTED invariants --

    def test_accepted_requires_explicit_mpn_evidence(self) -> None:
        """ACCEPTED with SKU_FIELD evidence must fail."""
        import pytest

        with pytest.raises(ValueError, match="EXPLICIT_MPN_FIELD"):
            ListingIdentityAssessment(
                normalized_listing=self._minimal_normalized(),
                requested_part_number="ABC",
                candidate_part_number_raw="ABC",
                candidate_part_number_compared="ABC",
                candidate_evidence_source=EvidenceSource.SKU_FIELD,
                match_type=IdentityMatchType.EXACT,
                decision=EvidenceDecision.ACCEPTED,
                rejection_reason=None,
            )

    def test_accepted_requires_exact_or_normalized_exact(self) -> None:
        """ACCEPTED with UNKNOWN match type must fail."""
        import pytest

        with pytest.raises(ValueError, match="EXACT or NORMALIZED_EXACT"):
            ListingIdentityAssessment(
                normalized_listing=self._minimal_normalized(),
                requested_part_number="ABC",
                candidate_part_number_raw="ABC",
                candidate_part_number_compared="ABC",
                candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
                match_type=IdentityMatchType.UNKNOWN,
                decision=EvidenceDecision.ACCEPTED,
                rejection_reason=None,
            )

    def test_accepted_requires_no_rejection_reason(self) -> None:
        """ACCEPTED with a rejection reason must fail."""
        import pytest

        with pytest.raises(ValueError, match="no rejection reason"):
            ListingIdentityAssessment(
                normalized_listing=self._minimal_normalized(),
                requested_part_number="ABC",
                candidate_part_number_raw="ABC",
                candidate_part_number_compared="ABC",
                candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
                match_type=IdentityMatchType.EXACT,
                decision=EvidenceDecision.ACCEPTED,
                rejection_reason=IdentityRejectionReason.MPN_MISMATCH,
            )

    def test_accepted_with_normalized_exact_is_valid(self) -> None:
        """ACCEPTED with NORMALIZED_EXACT and EXPLICIT_MPN_FIELD is valid."""
        obs = _make_observation(mpn_text="abc")
        norm = _make_normalized(obs)
        assessment = ListingIdentityAssessment(
            normalized_listing=norm,
            requested_part_number="ABC",
            candidate_part_number_raw="abc",
            candidate_part_number_compared="abc",
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.NORMALIZED_EXACT,
            decision=EvidenceDecision.ACCEPTED,
            rejection_reason=None,
        )
        assert assessment.decision is EvidenceDecision.ACCEPTED

    # -- REJECTED invariants --

    def test_rejected_requires_reason(self) -> None:
        """REJECTED with no rejection reason must fail."""
        import pytest

        with pytest.raises(ValueError, match="rejection reason"):
            ListingIdentityAssessment(
                normalized_listing=self._minimal_normalized(),
                requested_part_number="ABC",
                candidate_part_number_raw="",
                candidate_part_number_compared="",
                candidate_evidence_source=EvidenceSource.NONE,
                match_type=IdentityMatchType.UNKNOWN,
                decision=EvidenceDecision.REJECTED,
                rejection_reason=None,
            )

    def test_rejected_with_valid_reason_is_ok(self) -> None:
        """REJECTED with a rejection reason is valid."""
        obs = _make_observation(mpn_text="XYZ")
        norm = _make_normalized(obs)
        assessment = ListingIdentityAssessment(
            normalized_listing=norm,
            requested_part_number="ABC",
            candidate_part_number_raw="XYZ",
            candidate_part_number_compared="XYZ",
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.UNKNOWN,
            decision=EvidenceDecision.REJECTED,
            rejection_reason=IdentityRejectionReason.MPN_MISMATCH,
        )
        assert assessment.decision is EvidenceDecision.REJECTED

    # -- UNDECIDED invariants --

    def test_undecided_requires_unknown_match(self) -> None:
        """UNDECIDED with EXACT match must fail."""
        import pytest

        with pytest.raises(ValueError, match="UNKNOWN match type"):
            ListingIdentityAssessment(
                normalized_listing=self._minimal_normalized(),
                requested_part_number="",
                candidate_part_number_raw="",
                candidate_part_number_compared="",
                candidate_evidence_source=EvidenceSource.NONE,
                match_type=IdentityMatchType.EXACT,
                decision=EvidenceDecision.UNDECIDED,
                rejection_reason=IdentityRejectionReason.NO_REQUESTED_MPN,
            )

    def test_undecided_requires_no_requested_mpn_reason(self) -> None:
        """UNDECIDED with MPN_MISMATCH reason must fail."""
        import pytest

        with pytest.raises(ValueError, match="NO_REQUESTED_MPN"):
            ListingIdentityAssessment(
                normalized_listing=self._minimal_normalized(),
                requested_part_number="",
                candidate_part_number_raw="",
                candidate_part_number_compared="",
                candidate_evidence_source=EvidenceSource.NONE,
                match_type=IdentityMatchType.UNKNOWN,
                decision=EvidenceDecision.UNDECIDED,
                rejection_reason=IdentityRejectionReason.MPN_MISMATCH,
            )

    def test_undecided_valid_shape_is_ok(self) -> None:
        """UNDECIDED with UNKNOWN and NO_REQUESTED_MPN is valid."""
        assessment = ListingIdentityAssessment(
            normalized_listing=self._minimal_normalized(),
            requested_part_number="",
            candidate_part_number_raw="",
            candidate_part_number_compared="",
            candidate_evidence_source=EvidenceSource.NONE,
            match_type=IdentityMatchType.UNKNOWN,
            decision=EvidenceDecision.UNDECIDED,
            rejection_reason=IdentityRejectionReason.NO_REQUESTED_MPN,
        )
        assert assessment.decision is EvidenceDecision.UNDECIDED

    # -- PARTIAL cross-cutting --

    def test_partial_requires_rejected_decision(self) -> None:
        """PARTIAL match with ACCEPTED decision must fail.

        The ACCEPTED invariant fires first: ACCEPTED requires EXACT or
        NORMALIZED_EXACT, so PARTIAL with ACCEPTED is caught there.
        """
        import pytest

        with pytest.raises(ValueError, match="EXACT or NORMALIZED_EXACT"):
            ListingIdentityAssessment(
                normalized_listing=self._minimal_normalized(),
                requested_part_number="ABC",
                candidate_part_number_raw="AB",
                candidate_part_number_compared="AB",
                candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
                match_type=IdentityMatchType.PARTIAL,
                decision=EvidenceDecision.ACCEPTED,
                rejection_reason=IdentityRejectionReason.PARTIAL_MPN_ONLY,
            )

    def test_partial_requires_partial_mpn_only_reason(self) -> None:
        """PARTIAL match with MPN_MISMATCH reason must fail."""
        import pytest

        with pytest.raises(ValueError, match="PARTIAL_MPN_ONLY"):
            ListingIdentityAssessment(
                normalized_listing=self._minimal_normalized(),
                requested_part_number="ABC",
                candidate_part_number_raw="AB",
                candidate_part_number_compared="AB",
                candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
                match_type=IdentityMatchType.PARTIAL,
                decision=EvidenceDecision.REJECTED,
                rejection_reason=IdentityRejectionReason.MPN_MISMATCH,
            )

    def test_partial_valid_shape_is_ok(self) -> None:
        """PARTIAL with REJECTED and PARTIAL_MPN_ONLY is valid when the
        strings actually produce a PARTIAL result through 2A -> UNKNOWN
        followed by _classify_partial -> PARTIAL.

        "MZ" is a prefix of "MZ-QL23T800" at a hyphen boundary.
        """
        obs = _make_observation(mpn_text="MZ")
        norm = _make_normalized(obs)
        assessment = ListingIdentityAssessment(
            normalized_listing=norm,
            requested_part_number="MZ-QL23T800",
            candidate_part_number_raw="MZ",
            candidate_part_number_compared="MZ",
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.PARTIAL,
            decision=EvidenceDecision.REJECTED,
            rejection_reason=IdentityRejectionReason.PARTIAL_MPN_ONLY,
        )
        assert assessment.decision is EvidenceDecision.REJECTED


# -- Direct-constructor regressions (PRODUCT-INTEL.3C integrity) ------------


class TestDirectConstructorIntegrity:
    """Prove that direct construction of ListingIdentityAssessment rejects
    fabricated states that the normal builder path would never produce.

    These tests exercise the __post_init__ guards that make the public
    assessment contract self-enforcing.
    """

    def _minimal_observation(self) -> ListingObservation:
        return _make_observation()

    def _minimal_normalized(self) -> NormalizedListingObservation:
        return _make_normalized(self._minimal_observation())

    # -- A: fabricated ACCEPTED (completely different strings) --

    def test_fabricated_accepted_different_strings(self) -> None:
        """Test A: requested ABC-123, compared XYZ-999, claimed EXACT/ACCEPTED
        -> ValueError because 2A would return UNKNOWN."""
        import pytest

        with pytest.raises(ValueError, match="established identity"):
            ListingIdentityAssessment(
                normalized_listing=self._minimal_normalized(),
                requested_part_number="ABC-123",
                candidate_part_number_raw="XYZ-999",
                candidate_part_number_compared="XYZ-999",
                candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
                match_type=IdentityMatchType.EXACT,
                decision=EvidenceDecision.ACCEPTED,
                rejection_reason=None,
            )

    # -- B: empty strings claiming EXACT --

    def test_fabricated_accepted_empty_strings(self) -> None:
        """Test B: both empty, claimed EXACT/ACCEPTED -> ValueError.

        Empty strings carry no part-number content, so 2A returns UNKNOWN."""
        import pytest

        with pytest.raises(ValueError, match="established identity"):
            ListingIdentityAssessment(
                normalized_listing=self._minimal_normalized(),
                requested_part_number="",
                candidate_part_number_raw="",
                candidate_part_number_compared="",
                candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
                match_type=IdentityMatchType.EXACT,
                decision=EvidenceDecision.ACCEPTED,
                rejection_reason=None,
            )

    # -- C: case-different strings claiming EXACT when 2A says NORMALIZED_EXACT --

    def test_fabricated_accepted_wrong_match_type(self) -> None:
        """Test C: requested ABC-123, compared abc-123, claimed EXACT/ACCEPTED
        -> ValueError because 2A returns NORMALIZED_EXACT, not EXACT."""
        import pytest

        with pytest.raises(ValueError, match="match type must match"):
            ListingIdentityAssessment(
                normalized_listing=self._minimal_normalized(),
                requested_part_number="ABC-123",
                candidate_part_number_raw="abc-123",
                candidate_part_number_compared="abc-123",
                candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
                match_type=IdentityMatchType.EXACT,
                decision=EvidenceDecision.ACCEPTED,
                rejection_reason=None,
            )

    # -- D: same strings with NORMALIZED_EXACT should be valid --

    def test_valid_normalized_exact_accepted(self) -> None:
        """Test D: requested ABC-123, compared abc-123, claimed
        NORMALIZED_EXACT/ACCEPTED -> valid (2A confirms NORMALIZED_EXACT)."""
        obs = _make_observation(mpn_text="abc-123")
        norm = _make_normalized(obs)
        assessment = ListingIdentityAssessment(
            normalized_listing=norm,
            requested_part_number="ABC-123",
            candidate_part_number_raw="abc-123",
            candidate_part_number_compared="abc-123",
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.NORMALIZED_EXACT,
            decision=EvidenceDecision.ACCEPTED,
            rejection_reason=None,
        )
        assert assessment.decision is EvidenceDecision.ACCEPTED
        assert assessment.match_type is IdentityMatchType.NORMALIZED_EXACT

    # -- E: valid wrapper cleanup audit trail --

    def test_valid_wrapper_cleanup_audit_trail(self) -> None:
        """Test E: raw 'mpn:ABC-123', compared 'ABC-123', exact accepted
        -> valid (wrapper cleanup is correct)."""
        obs = _make_observation(mpn_text="mpn:ABC-123")
        norm = _make_normalized(obs)
        assessment = ListingIdentityAssessment(
            normalized_listing=norm,
            requested_part_number="ABC-123",
            candidate_part_number_raw="mpn:ABC-123",
            candidate_part_number_compared="ABC-123",
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.EXACT,
            decision=EvidenceDecision.ACCEPTED,
            rejection_reason=None,
        )
        assert assessment.decision is EvidenceDecision.ACCEPTED

    # -- F: broken audit trail --

    def test_broken_audit_trail_compared_not_from_raw(self) -> None:
        """Test F: raw 'XYZ-999', compared 'ABC-123', exact accepted
        -> ValueError because compared does not derive from raw."""
        import pytest

        obs = _make_observation(mpn_text="XYZ-999")
        norm = _make_normalized(obs)
        with pytest.raises(ValueError, match="does not derive"):
            ListingIdentityAssessment(
                normalized_listing=norm,
                requested_part_number="ABC-123",
                candidate_part_number_raw="XYZ-999",
                candidate_part_number_compared="ABC-123",
                candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
                match_type=IdentityMatchType.EXACT,
                decision=EvidenceDecision.ACCEPTED,
                rejection_reason=None,
            )

    # -- G: PARTIAL_MPN_ONLY with UNKNOWN match type --

    def test_partial_mpn_only_requires_partial_match_type(self) -> None:
        """Test G: PARTIAL_MPN_ONLY with UNKNOWN match type -> ValueError."""
        import pytest

        with pytest.raises(ValueError, match="PARTIAL_MPN_ONLY requires PARTIAL"):
            ListingIdentityAssessment(
                normalized_listing=self._minimal_normalized(),
                requested_part_number="ABC",
                candidate_part_number_raw="AB",
                candidate_part_number_compared="AB",
                candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
                match_type=IdentityMatchType.UNKNOWN,
                decision=EvidenceDecision.REJECTED,
                rejection_reason=IdentityRejectionReason.PARTIAL_MPN_ONLY,
            )

    # -- H: PARTIAL match whose strings are not actually partial --

    def test_partial_strings_not_actually_partial(self) -> None:
        """Test H: PARTIAL match type with strings that 2A would classify
        as UNKNOWN and _classify_partial would not call PARTIAL."""
        import pytest

        with pytest.raises(ValueError, match="_classify_partial"):
            ListingIdentityAssessment(
                normalized_listing=self._minimal_normalized(),
                requested_part_number="ABC",
                candidate_part_number_raw="XYZ",
                candidate_part_number_compared="XYZ",
                candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
                match_type=IdentityMatchType.PARTIAL,
                decision=EvidenceDecision.REJECTED,
                rejection_reason=IdentityRejectionReason.PARTIAL_MPN_ONLY,
            )

    # -- I: NO_REQUESTED_MPN with non-empty requested MPN --

    def test_no_requested_mpn_with_nonempty_mpn(self) -> None:
        """Test I: NO_REQUESTED_MPN with a non-empty requested part number
        -> ValueError (NO_REQUESTED_MPN means the request had no MPN)."""
        import pytest

        with pytest.raises(ValueError, match="NO_REQUESTED_MPN requires an empty"):
            ListingIdentityAssessment(
                normalized_listing=self._minimal_normalized(),
                requested_part_number="ABC-123",
                candidate_part_number_raw="",
                candidate_part_number_compared="",
                candidate_evidence_source=EvidenceSource.NONE,
                match_type=IdentityMatchType.UNKNOWN,
                decision=EvidenceDecision.UNDECIDED,
                rejection_reason=IdentityRejectionReason.NO_REQUESTED_MPN,
            )

    # -- J: plain-string enum substitution --

    def test_plain_string_decision_raises_type_error(self) -> None:
        """Test J: decision='ACCEPTED' (plain string) -> TypeError."""
        import pytest

        with pytest.raises(TypeError, match="EvidenceDecision"):
            ListingIdentityAssessment(  # type: ignore[arg-type]
                normalized_listing=self._minimal_normalized(),
                requested_part_number="ABC",
                candidate_part_number_raw="ABC",
                candidate_part_number_compared="ABC",
                candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
                match_type=IdentityMatchType.EXACT,
                decision="ACCEPTED",
                rejection_reason=None,
            )

    def test_plain_string_match_type_raises_type_error(self) -> None:
        """match_type='EXACT' (plain string) -> TypeError."""
        import pytest

        with pytest.raises(TypeError, match="IdentityMatchType"):
            ListingIdentityAssessment(  # type: ignore[arg-type]
                normalized_listing=self._minimal_normalized(),
                requested_part_number="ABC",
                candidate_part_number_raw="ABC",
                candidate_part_number_compared="ABC",
                candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
                match_type="EXACT",
                decision=EvidenceDecision.ACCEPTED,
                rejection_reason=None,
            )

    def test_plain_string_source_raises_type_error(self) -> None:
        """candidate_evidence_source='EXPLICIT_MPN_FIELD' (plain string)
        -> TypeError."""
        import pytest

        with pytest.raises(TypeError, match="EvidenceSource"):
            ListingIdentityAssessment(  # type: ignore[arg-type]
                normalized_listing=self._minimal_normalized(),
                requested_part_number="ABC",
                candidate_part_number_raw="ABC",
                candidate_part_number_compared="ABC",
                candidate_evidence_source="EXPLICIT_MPN_FIELD",
                match_type=IdentityMatchType.EXACT,
                decision=EvidenceDecision.ACCEPTED,
                rejection_reason=None,
            )


# -- Evidence provenance regressions (PRODUCT-INTEL.3C integrity) -----------


class TestEvidenceProvenance:
    """Direct construction of ListingIdentityAssessment cannot reference
    evidence the underlying ListingObservation did not publish.

    These tests prove the upstream provenance chain:
    observation -> _find_evidence -> source/raw -> compared -> 2A -> decision.
    An ACCEPTED assessment must not be fabricatable against a listing that
    published no MPN at all.
    """

    # -- A: no underlying MPN, fabricated EXPLICIT_MPN_FIELD --

    def test_no_underlying_mpn_fabricated_explicit_source(self) -> None:
        """A: observation.mpn_text=None, assessment claims EXPLICIT_MPN_FIELD
        with raw='ABC-123' -> ValueError (listing published no MPN)."""
        import pytest

        obs = _make_observation(mpn_text=None, sku_text=None,
                                product_title="Generic Product")
        norm = _make_normalized(obs)
        with pytest.raises(ValueError, match="does not match"):
            ListingIdentityAssessment(
                normalized_listing=norm,
                requested_part_number="ABC-123",
                candidate_part_number_raw="ABC-123",
                candidate_part_number_compared="ABC-123",
                candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
                match_type=IdentityMatchType.EXACT,
                decision=EvidenceDecision.ACCEPTED,
                rejection_reason=None,
            )

    # -- B: different underlying MPN --

    def test_different_underlying_mpn_fabricated_raw(self) -> None:
        """B: observation MPN='XYZ-999', assessment claims raw='ABC-123'
        -> ValueError (the raw does not match the published value)."""
        import pytest

        obs = _make_observation(mpn_text="XYZ-999")
        norm = _make_normalized(obs)
        with pytest.raises(ValueError, match="does not match"):
            ListingIdentityAssessment(
                normalized_listing=norm,
                requested_part_number="ABC-123",
                candidate_part_number_raw="ABC-123",
                candidate_part_number_compared="ABC-123",
                candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
                match_type=IdentityMatchType.EXACT,
                decision=EvidenceDecision.ACCEPTED,
                rejection_reason=None,
            )

    # -- C: valid EXACT provenance --

    def test_valid_exact_provenance(self) -> None:
        """C: observation MPN='ABC-123', raw='ABC-123', compared='ABC-123',
        requested='ABC-123', EXACT/ACCEPTED -> valid."""
        obs = _make_observation(mpn_text="ABC-123")
        norm = _make_normalized(obs)
        assessment = ListingIdentityAssessment(
            normalized_listing=norm,
            requested_part_number="ABC-123",
            candidate_part_number_raw="ABC-123",
            candidate_part_number_compared="ABC-123",
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.EXACT,
            decision=EvidenceDecision.ACCEPTED,
            rejection_reason=None,
        )
        assert assessment.decision is EvidenceDecision.ACCEPTED

    # -- D: valid wrapper provenance --

    def test_valid_wrapper_provenance(self) -> None:
        """D: observation MPN='mpn:ABC-123', raw='mpn:ABC-123',
        compared='ABC-123', requested='ABC-123', EXACT/ACCEPTED -> valid."""
        obs = _make_observation(mpn_text="mpn:ABC-123")
        norm = _make_normalized(obs)
        assessment = ListingIdentityAssessment(
            normalized_listing=norm,
            requested_part_number="ABC-123",
            candidate_part_number_raw="mpn:ABC-123",
            candidate_part_number_compared="ABC-123",
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.EXACT,
            decision=EvidenceDecision.ACCEPTED,
            rejection_reason=None,
        )
        assert assessment.decision is EvidenceDecision.ACCEPTED

    # -- E: source priority cannot be fabricated --

    def test_source_priority_cannot_be_fabricated_mpn_over_sku(self) -> None:
        """E: observation has explicit MPN, assessment claims SKU_FIELD
        instead -> ValueError (MPN takes priority over SKU)."""
        import pytest

        obs = _make_observation(mpn_text="REQ-MPN", sku_text="OTHER-SKU")
        norm = _make_normalized(obs)
        with pytest.raises(ValueError, match="does not match"):
            ListingIdentityAssessment(
                normalized_listing=norm,
                requested_part_number="REQ-MPN",
                candidate_part_number_raw="OTHER-SKU",
                candidate_part_number_compared="OTHER-SKU",
                candidate_evidence_source=EvidenceSource.SKU_FIELD,
                match_type=IdentityMatchType.UNKNOWN,
                decision=EvidenceDecision.REJECTED,
                rejection_reason=IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE,
            )

    def test_source_priority_cannot_be_fabricated_mpn_over_title(self) -> None:
        """E: observation has explicit MPN, assessment claims TITLE_TEXT
        instead -> ValueError (MPN takes priority)."""
        import pytest

        obs = _make_observation(
            mpn_text="PAGE-MPN",
            product_title="Product ABC-123 Edition",
            sku_text=None,
        )
        norm = _make_normalized(obs)
        with pytest.raises(ValueError, match="does not match"):
            ListingIdentityAssessment(
                normalized_listing=norm,
                requested_part_number="ABC-123",
                candidate_part_number_raw="ABC-123",
                candidate_part_number_compared="ABC-123",
                candidate_evidence_source=EvidenceSource.TITLE_TEXT,
                match_type=IdentityMatchType.UNKNOWN,
                decision=EvidenceDecision.REJECTED,
                rejection_reason=IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE,
            )

    # -- F: SKU raw must match observation --

    def test_sku_raw_must_match_observation(self) -> None:
        """F: observation mpn=None, sku='501489', assessment claims
        raw='OTHER-SKU' -> ValueError."""
        import pytest

        obs = _make_observation(mpn_text=None, sku_text="501489")
        norm = _make_normalized(obs)
        with pytest.raises(ValueError, match="does not match"):
            ListingIdentityAssessment(
                normalized_listing=norm,
                requested_part_number="ABC-123",
                candidate_part_number_raw="OTHER-SKU",
                candidate_part_number_compared="OTHER-SKU",
                candidate_evidence_source=EvidenceSource.SKU_FIELD,
                match_type=IdentityMatchType.UNKNOWN,
                decision=EvidenceDecision.REJECTED,
                rejection_reason=IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE,
            )

    # -- G: non-EXPLICIT compared value cannot mutate --

    def test_non_explicit_compared_cannot_mutate(self) -> None:
        """G: observation mpn=None, sku='501489', assessment claims
        raw='501489', compared='ABC-123' -> ValueError
        (SKU cannot have wrapper cleanup or normalization)."""
        import pytest

        obs = _make_observation(mpn_text=None, sku_text="501489")
        norm = _make_normalized(obs)
        with pytest.raises(ValueError, match="does not derive"):
            ListingIdentityAssessment(
                normalized_listing=norm,
                requested_part_number="ABC-123",
                candidate_part_number_raw="501489",
                candidate_part_number_compared="ABC-123",
                candidate_evidence_source=EvidenceSource.SKU_FIELD,
                match_type=IdentityMatchType.UNKNOWN,
                decision=EvidenceDecision.REJECTED,
                rejection_reason=IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE,
            )

    # -- H: builder path unchanged --

    def test_builder_path_produces_all_real_outcomes(self) -> None:
        """H: assess_listing_identity(...) continues to produce all existing
        real and synthetic outcomes unchanged."""
        req = _make_request("MZ-QL23T800")

        # Exact match via builder
        obs_exact = _make_observation(mpn_text="MZ-QL23T800")
        norm_exact = _make_normalized(obs_exact)
        r_exact = assess_listing_identity(req, norm_exact)
        assert r_exact.decision is EvidenceDecision.ACCEPTED
        assert r_exact.match_type is IdentityMatchType.EXACT

        # Normalized exact via builder
        obs_norm_exact = _make_observation(mpn_text="mz-ql23t800")
        norm_norm_exact = _make_normalized(obs_norm_exact)
        r_norm_exact = assess_listing_identity(req, norm_norm_exact)
        assert r_norm_exact.decision is EvidenceDecision.ACCEPTED
        assert r_norm_exact.match_type is IdentityMatchType.NORMALIZED_EXACT

        # Wrapper cleanup via builder
        obs_wrapper = _make_observation(mpn_text="mpn:MZ-QL23T800")
        norm_wrapper = _make_normalized(obs_wrapper)
        r_wrapper = assess_listing_identity(req, norm_wrapper)
        assert r_wrapper.decision is EvidenceDecision.ACCEPTED
        assert r_wrapper.candidate_part_number_raw == "mpn:MZ-QL23T800"
        assert r_wrapper.candidate_part_number_compared == "MZ-QL23T800"

        # Mismatch via builder
        obs_mismatch = _make_observation(mpn_text="XYZ-999")
        norm_mismatch = _make_normalized(obs_mismatch)
        r_mismatch = assess_listing_identity(req, norm_mismatch)
        assert r_mismatch.decision is EvidenceDecision.REJECTED
        assert r_mismatch.rejection_reason is IdentityRejectionReason.MPN_MISMATCH

        # Partial via builder
        obs_partial = _make_observation(mpn_text="MZ")
        norm_partial = _make_normalized(obs_partial)
        r_partial = assess_listing_identity(req, norm_partial)
        assert r_partial.decision is EvidenceDecision.REJECTED
        assert r_partial.match_type is IdentityMatchType.PARTIAL
        assert r_partial.rejection_reason is IdentityRejectionReason.PARTIAL_MPN_ONLY

        # SKU only via builder
        obs_sku = _make_observation(mpn_text=None, sku_text="RETAIL-001")
        norm_sku = _make_normalized(obs_sku)
        r_sku = assess_listing_identity(req, norm_sku)
        assert r_sku.decision is EvidenceDecision.REJECTED
        assert r_sku.candidate_evidence_source is EvidenceSource.SKU_FIELD

        # No evidence via builder
        obs_none = _make_observation(
            mpn_text=None, sku_text=None,
            product_title="Generic Product",
        )
        norm_none = _make_normalized(obs_none)
        r_none = assess_listing_identity(req, norm_none)
        assert r_none.decision is EvidenceDecision.REJECTED
        assert r_none.candidate_evidence_source is EvidenceSource.NONE

        # Description-only via builder
        obs_desc = _make_observation(mpn_text="MZ-QL23T800")
        norm_desc = _make_normalized(obs_desc)
        req_desc = ResearchRequest(
            manufacturer_part_number="",
            description="Some SSD",
        )
        r_desc = assess_listing_identity(req_desc, norm_desc)
        assert r_desc.decision is EvidenceDecision.UNDECIDED
        assert r_desc.rejection_reason is IdentityRejectionReason.NO_REQUESTED_MPN
