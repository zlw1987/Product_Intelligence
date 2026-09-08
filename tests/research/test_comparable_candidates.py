"""Comparable candidate contract tests (PRODUCT-INTEL.7A).

Tests the immutable data contracts, target-self exclusion, deduplication,
and candidate construction invariants.
"""

from __future__ import annotations

from datetime import datetime, timezone

from product_intelligence.domain.enums import IdentityMatchType
from product_intelligence.domain.models import ProductIdentity
from product_intelligence.research.comparable_candidates import (
    ComparableCandidate,
    ComparableCandidateAssessment,
    ComparableCandidateObservation,
    ComparableCandidateSource,
    CandidateDisposition,
    deduplicate_candidate_assessments,
)
from product_intelligence.research.specifications import SourceAuthority

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RETRIEVED_AT = datetime(2026, 9, 4, 20, 42, 23, tzinfo=timezone.utc)
_SOURCE_NAME = "Seagate Enterprise Support"
_SOURCE_URL = "https://www.seagate.com/support/enterprise-storage/solid-state-drives/nytro-5050/"
_AUTHORITY = SourceAuthority.AUTHORITATIVE


def _make_observation(
    mpn: str,
    title: str | None = None,
    source_name: str = _SOURCE_NAME,
    source_url: str = _SOURCE_URL,
    retrieved_at: datetime = _RETRIEVED_AT,
    authority: SourceAuthority = _AUTHORITY,
) -> ComparableCandidateObservation:
    return ComparableCandidateObservation(
        manufacturer_part_number_raw=mpn,
        product_name_raw=title,
        source_name=source_name,
        source_url=source_url,
        retrieved_at=retrieved_at,
        source_authority=authority,
    )


def _make_target(mpn: str) -> ProductIdentity:
    return ProductIdentity(
        manufacturer="Seagate",
        manufacturer_part_number=mpn,
        normalized_part_number=mpn.upper(),
        match_type=IdentityMatchType.EXACT,
    )


# ---------------------------------------------------------------------------
# ComparableCandidateSource
# ---------------------------------------------------------------------------


class TestComparableCandidateSource:
    def test_valid_source(self) -> None:
        source = ComparableCandidateSource(
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            source_authority=_AUTHORITY,
        )
        assert source.source_name == _SOURCE_NAME
        assert source.source_url == _SOURCE_URL
        assert source.source_authority is _AUTHORITY

    def test_empty_source_name_rejected(self) -> None:
        import pytest

        with pytest.raises(ValueError):
            ComparableCandidateSource(
                source_name="",
                source_url=_SOURCE_URL,
                source_authority=_AUTHORITY,
            )

    def test_invalid_url_rejected(self) -> None:
        import pytest

        with pytest.raises(ValueError):
            ComparableCandidateSource(
                source_name=_SOURCE_NAME,
                source_url="not-a-url",
                source_authority=_AUTHORITY,
            )

    def test_secondarity_source_rejected_in_v1(self) -> None:
        """7A v1 requires AUTHORITATIVE; SECONDARY is a configuration error."""
        source = ComparableCandidateSource(
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            source_authority=SourceAuthority.SECONDARY,
        )
        assert source.source_authority is SourceAuthority.SECONDARY
        # The source can be constructed; validation happens in execution


# ---------------------------------------------------------------------------
# ComparableCandidateObservation
# ---------------------------------------------------------------------------


class TestComparableCandidateObservation:
    def test_valid_observation(self) -> None:
        obs = _make_observation("XP15360SE70005", "Test Product")
        assert obs.manufacturer_part_number_raw == "XP15360SE70005"
        assert obs.product_name_raw == "Test Product"
        assert obs.source_authority is _AUTHORITY

    def test_empty_mpn_rejected(self) -> None:
        import pytest

        with pytest.raises(ValueError):
            _make_observation("")

    def test_title_optional(self) -> None:
        obs = _make_observation("XP15360SE70005")
        assert obs.product_name_raw is None

    def test_title_blank_preserved_as_blank(self) -> None:
        """Blank title string is preserved exactly (not converted to None).
        Raw evidence stays raw — blank means the source published blanks."""
        obs = _make_observation("XP15360SE70005", "   ")
        assert obs.product_name_raw == "   "

    def test_mpn_surrounding_whitespace_preserved_raw(self) -> None:
        """MPN raw evidence preserves surrounding whitespace exactly.
        Validation checks non-empty after strip, but storage is exact."""
        obs = _make_observation("  XP15360SE70005  ")
        assert obs.manufacturer_part_number_raw == "  XP15360SE70005  "

    def test_raw_mpn_exactly_preserved(self) -> None:
        """raw MPN '  XP15360SE70005  ' remains exactly that string."""
        obs = ComparableCandidateObservation(
            manufacturer_part_number_raw="  XP15360SE70005  ",
            product_name_raw=None,
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            source_authority=_AUTHORITY,
        )
        assert obs.manufacturer_part_number_raw == "  XP15360SE70005  "

    def test_raw_title_exactly_preserved(self) -> None:
        """raw title '  Nytro Test  ' remains exactly that string."""
        obs = ComparableCandidateObservation(
            manufacturer_part_number_raw="ABC123",
            product_name_raw="  Nytro Test  ",
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            source_authority=_AUTHORITY,
        )
        assert obs.product_name_raw == "  Nytro Test  "

    def test_naive_datetime_rejected(self) -> None:
        import pytest

        naive = datetime(2026, 1, 1)
        with pytest.raises(ValueError):
            ComparableCandidateObservation(
                manufacturer_part_number_raw="ABC",
                product_name_raw=None,
                source_name=_SOURCE_NAME,
                source_url=_SOURCE_URL,
                retrieved_at=naive,
                source_authority=_AUTHORITY,
            )


# ---------------------------------------------------------------------------
# TARGET: ComparableCandidateAssessment
# ---------------------------------------------------------------------------


class TestTargetSelfExclusion:
    def test_unestablished_target_rejected(self) -> None:
        import pytest

        unestablished = ProductIdentity(
            manufacturer_part_number="ABC",
            match_type=IdentityMatchType.UNKNOWN,
        )
        obs = _make_observation("ABC123")
        with pytest.raises(ValueError):
            ComparableCandidateAssessment.build(unestablished, obs)

    def test_target_exact_mpn(self) -> None:
        """Exact MPN match -> TARGET_SELF."""
        target = _make_target("XP15360SE70005")
        obs = _make_observation("XP15360SE70005")
        assessment = ComparableCandidateAssessment.build(target, obs)
        assert assessment.disposition is CandidateDisposition.TARGET_SELF

    def test_target_normalized_exact_spelling(self) -> None:
        """Normalized-exact spelling -> TARGET_SELF.
        'xp15360se70005' normalizes to 'XP15360SE70005' which matches."""
        target = _make_target("XP15360SE70005")
        obs = _make_observation("xp15360se70005")
        assessment = ComparableCandidateAssessment.build(target, obs)
        assert assessment.disposition is CandidateDisposition.TARGET_SELF

    def test_target_normalized_exact_with_whitespace_boundary(self) -> None:
        """'XP15 360SE70005' has a whitespace run that normalizes to hyphen.
        Target 'XP15360SE70005' has no such boundary, so they normalize
        differently -> CANDIDATE (not TARGET_SELF)."""
        target = _make_target("XP15360SE70005")
        obs = _make_observation("XP15 360SE70005")
        assessment = ComparableCandidateAssessment.build(target, obs)
        # XP15360SE70005 normalizes to XP15360SE70005
        # XP15 360SE70005 normalizes to XP15-360SE70005
        # These are different -> CANDIDATE
        assert assessment.disposition is CandidateDisposition.CANDIDATE

    def test_different_mpn(self) -> None:
        """Different MPN -> CANDIDATE."""
        target = _make_target("XP15360SE70005")
        obs = _make_observation("XP15360SE70015")
        assessment = ComparableCandidateAssessment.build(target, obs)
        assert assessment.disposition is CandidateDisposition.CANDIDATE

    def test_partial_family_prefix_remains_candidate(self) -> None:
        """A PARTIAL/family-related MPN remains CANDIDATE.
        7B decides whether it is similar — not 7A."""
        target = _make_target("XP15360SE70005")
        obs = _make_observation("XP15360")  # Family prefix
        assessment = ComparableCandidateAssessment.build(target, obs)
        assert assessment.disposition is CandidateDisposition.CANDIDATE

    def test_normalized_part_number_self_derived(self) -> None:
        """normalized_part_number must equal frozen 2A output."""
        target = _make_target("XP15360SE70005")
        obs = _make_observation("xp15360se70015")
        assessment = ComparableCandidateAssessment.build(target, obs)
        assert assessment.normalized_part_number == "XP15360SE70015"

    def test_impossible_direct_construction_rejected(self) -> None:
        """Direct construction with fabricated normalized key is rejected
        because __post_init__ re-validates the normalized key."""
        import pytest

        target = _make_target("XP15360SE70005")
        obs = _make_observation("XP15360SE70005")
        with pytest.raises(ValueError):
            ComparableCandidateAssessment(
                target_identity=target,
                observation=obs,
                normalized_part_number="WRONG_KEY",
                disposition=CandidateDisposition.CANDIDATE,
            )

    def test_fabricated_target_self_rejected(self) -> None:
        """Cannot fabricate TARGET_SELF for a different MPN.
        Direct construction with TARGET_SELF for a non-matching MPN
        is rejected because __post_init__ re-derives disposition."""
        import pytest

        target = _make_target("XP15360SE70005")
        obs = _make_observation("DIFFERENT_MPN")
        with pytest.raises(ValueError, match="disposition"):
            ComparableCandidateAssessment(
                target_identity=target,
                observation=obs,
                normalized_part_number="DIFFERENT_MPN",
                disposition=CandidateDisposition.TARGET_SELF,
            )

    def test_fabricated_candidate_for_target_rejected(self) -> None:
        """Cannot fabricate CANDIDATE for the target's own MPN.
        Direct construction with CANDIDATE for an exact-match MPN
        is rejected because __post_init__ re-derives disposition."""
        import pytest

        target = _make_target("XP15360SE70005")
        obs = _make_observation("XP15360SE70005")
        with pytest.raises(ValueError, match="disposition"):
            ComparableCandidateAssessment(
                target_identity=target,
                observation=obs,
                normalized_part_number="XP15360SE70005",
                disposition=CandidateDisposition.CANDIDATE,
            )

    def test_unrelated_mpn_target_self_rejected(self) -> None:
        """Different MPN + TARGET_SELF disposition is rejected."""
        import pytest

        target = _make_target("XP15360SE70005")
        obs = _make_observation("TOTALLY_DIFFERENT")
        with pytest.raises(ValueError, match="disposition"):
            ComparableCandidateAssessment(
                target_identity=target,
                observation=obs,
                normalized_part_number="TOTALLY_DIFFERENT",
                disposition=CandidateDisposition.TARGET_SELF,
            )

    def test_product_identity_subclass_rejected(self) -> None:
        """ComparableCandidateAssessment requires exact ProductIdentity type.
        Subclasses are rejected even though isinstance would pass."""
        import pytest

        class FakeProductIdentity(ProductIdentity):
            """Subclass of ProductIdentity — should be rejected."""

        fake = FakeProductIdentity(
            manufacturer="Seagate",
            manufacturer_part_number="ABC123",
            normalized_part_number="ABC123",
            match_type=IdentityMatchType.EXACT,
        )
        obs = _make_observation("XYZ999")
        # build() must reject subclasses
        with pytest.raises(TypeError, match="ProductIdentity"):
            ComparableCandidateAssessment.build(fake, obs)
        # Direct construction must also reject
        with pytest.raises(TypeError, match="ProductIdentity"):
            ComparableCandidateAssessment(
                target_identity=fake,
                observation=obs,
                normalized_part_number="XYZ999",
                disposition=CandidateDisposition.CANDIDATE,
            )


# ---------------------------------------------------------------------------
# DEDUP: deduplicate_candidate_assessments
# ---------------------------------------------------------------------------


class TestDeduplication:
    def test_exact_duplicate_observations_merge_evidence(self) -> None:
        """Two observations with exact same MPN merge into one candidate."""
        target = _make_target("XYZ999")
        obs1 = _make_observation("ABC123", "Product A")
        obs2 = _make_observation("ABC123", "Product A")
        a1 = ComparableCandidateAssessment.build(target, obs1)
        a2 = ComparableCandidateAssessment.build(target, obs2)
        candidates = deduplicate_candidate_assessments((a1, a2))
        assert len(candidates) == 1
        assert len(candidates[0].evidence) == 2

    def test_normalized_exact_formatting_variants_merge_evidence(self) -> None:
        """'abc 123' and 'ABC-123' normalize to same key -> one candidate."""
        target = _make_target("XYZ999")
        obs1 = _make_observation("abc 123", "Product A")
        obs2 = _make_observation("ABC-123", "Product A")
        a1 = ComparableCandidateAssessment.build(target, obs1)
        a2 = ComparableCandidateAssessment.build(target, obs2)
        candidates = deduplicate_candidate_assessments((a1, a2))
        assert len(candidates) == 1
        assert candidates[0].normalized_part_number == "ABC-123"
        assert len(candidates[0].evidence) == 2

    def test_structure_different_mpn_remain_separate(self) -> None:
        """'ABC123' and 'ABC-123' have different structure -> two candidates."""
        target = _make_target("XYZ999")
        obs1 = _make_observation("ABC123", "Product A")
        obs2 = _make_observation("ABC-123", "Product B")
        a1 = ComparableCandidateAssessment.build(target, obs1)
        a2 = ComparableCandidateAssessment.build(target, obs2)
        candidates = deduplicate_candidate_assessments((a1, a2))
        assert len(candidates) == 2
        # Both have 1 evidence each
        for c in candidates:
            assert len(c.evidence) == 1

    def test_duplicate_evidence_preserved_not_discarded(self) -> None:
        """Duplicate observations from different sources preserve ALL evidence."""
        target = _make_target("XYZ999")
        source2_url = "https://example.com/catalog/"
        obs1 = _make_observation("ABC123", source_url=_SOURCE_URL)
        obs2 = _make_observation(
            "ABC123",
            source_url=source2_url,
            retrieved_at=_RETRIEVED_AT.replace(second=24),
        )
        a1 = ComparableCandidateAssessment.build(target, obs1)
        a2 = ComparableCandidateAssessment.build(target, obs2)
        candidates = deduplicate_candidate_assessments((a1, a2))
        assert len(candidates) == 1
        assert len(candidates[0].evidence) == 2

    def test_stable_first_seen_order(self) -> None:
        """Candidates appear in stable first-seen order."""
        target = _make_target("ZZZ999")
        obs_a = _make_observation("AAA111")
        obs_b = _make_observation("BBB222")
        obs_c = _make_observation("CCC333")
        a_a = ComparableCandidateAssessment.build(target, obs_a)
        a_b = ComparableCandidateAssessment.build(target, obs_b)
        a_c = ComparableCandidateAssessment.build(target, obs_c)
        candidates = deduplicate_candidate_assessments((a_a, a_b, a_c))
        assert len(candidates) == 3
        assert candidates[0].normalized_part_number == "AAA111"
        assert candidates[1].normalized_part_number == "BBB222"
        assert candidates[2].normalized_part_number == "CCC333"

    def test_target_self_excluded_from_candidates(self) -> None:
        """TARGET_SELF assessments do not appear in candidates."""
        target = _make_target("XP15360SE70005")
        obs_target = _make_observation("XP15360SE70005")
        obs_other = _make_observation("XP15360SE70015")
        a_target = ComparableCandidateAssessment.build(target, obs_target)
        a_other = ComparableCandidateAssessment.build(target, obs_other)
        candidates = deduplicate_candidate_assessments((a_target, a_other))
        assert len(candidates) == 1
        assert candidates[0].normalized_part_number == "XP15360SE70015"
        # No candidate with the target MPN
        for c in candidates:
            assert c.normalized_part_number != "XP15360SE70005"

    def test_dedup_cross_target_rejected(self) -> None:
        """Assessments with the same normalized key but different
        target_identity objects are rejected during deduplication."""
        import pytest

        target1 = _make_target("T1")
        target2 = _make_target("T1")  # same MPN, different object
        assert target1 is not target2

        obs1 = _make_observation("ABC123")
        obs2 = _make_observation("ABC123", retrieved_at=_RETRIEVED_AT.replace(second=25))
        a1 = ComparableCandidateAssessment.build(target1, obs1)
        a2 = ComparableCandidateAssessment.build(target2, obs2)

        assert a1.normalized_part_number == a2.normalized_part_number
        with pytest.raises(ValueError, match="target_identity|Cross-target"):
            deduplicate_candidate_assessments((a1, a2))


# ---------------------------------------------------------------------------
# CONTRACT: ComparableCandidate
# ---------------------------------------------------------------------------


class TestComparableCandidateContract:
    def test_candidate_evidence_non_empty(self) -> None:
        import pytest

        target = _make_target("XYZ999")
        obs = _make_observation("ABC123")
        assessment = ComparableCandidateAssessment.build(target, obs)
        with pytest.raises(ValueError):
            ComparableCandidate.build(())

    def test_candidate_normalized_key_self_derived(self) -> None:
        """normalized_part_number must match frozen 2A of representative MPN."""
        target = _make_target("XYZ999")
        obs = _make_observation("abc 123")
        assessment = ComparableCandidateAssessment.build(target, obs)
        candidate = ComparableCandidate.build((assessment,))
        assert candidate.normalized_part_number == "ABC-123"

    def test_cross_key_evidence_rejected(self) -> None:
        """Evidence with different normalized keys cannot share a candidate."""
        import pytest

        target = _make_target("ZZZ999")
        obs1 = _make_observation("ABC123")
        obs2 = _make_observation("DEF456")
        a1 = ComparableCandidateAssessment.build(target, obs1)
        a2 = ComparableCandidateAssessment.build(target, obs2)
        with pytest.raises(ValueError):
            ComparableCandidate.build((a1, a2))

    def test_secondary_evidence_rejected_in_v1(self) -> None:
        """Non-AUTHORITATIVE evidence is rejected in 7A v1."""
        import pytest

        target = _make_target("XYZ999")
        obs = ComparableCandidateObservation(
            manufacturer_part_number_raw="ABC123",
            product_name_raw=None,
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            source_authority=SourceAuthority.SECONDARY,
        )
        assessment = ComparableCandidateAssessment.build(target, obs)
        with pytest.raises(ValueError):
            ComparableCandidate.build((assessment,))

    def test_candidate_has_no_score_rank_similarity_field(self) -> None:
        """ComparableCandidate has no scoring fields."""
        target = _make_target("XYZ999")
        obs = _make_observation("ABC123")
        assessment = ComparableCandidateAssessment.build(target, obs)
        candidate = ComparableCandidate.build((assessment,))
        # Explicit: these fields must not exist
        for field_name in ("score", "rank", "similarity", "compatibility",
                           "distance", "weight", "threshold", "recommendation"):
            assert not hasattr(candidate, field_name), (
                f"ComparableCandidate must not have a '{field_name}' field"
            )

    def test_impossible_direct_construction_rejected(self) -> None:
        """Direct construction with wrong normalized key is rejected."""
        import pytest

        target = _make_target("XYZ999")
        obs = _make_observation("ABC123")
        assessment = ComparableCandidateAssessment.build(target, obs)
        with pytest.raises(ValueError):
            ComparableCandidate(
                manufacturer_part_number="ABC123",
                normalized_part_number="WRONG_KEY",
                evidence=(assessment,),
            )

    def test_cross_target_evidence_rejected(self) -> None:
        """Evidence from different target_identity objects cannot share
        one candidate, even if normalized keys match."""
        import pytest

        target1 = _make_target("T1")
        target2 = _make_target("T1")  # same MPN, different object
        assert target1 is not target2

        obs = _make_observation("ABC123")
        a1 = ComparableCandidateAssessment.build(target1, obs)

        # Separate observation for target2, same normalized key
        obs2 = _make_observation("ABC123", retrieved_at=_RETRIEVED_AT.replace(second=25))
        a2 = ComparableCandidateAssessment.build(target2, obs2)

        assert a1.normalized_part_number == a2.normalized_part_number
        with pytest.raises(ValueError, match="target_identity"):
            ComparableCandidate.build((a1, a2))
