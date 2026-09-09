"""Enterprise SSD similarity scoring tests (PRODUCT-INTEL.7B).

Tests the pure research layer: field similarity computation, VERIFIED-only
scoring, aggregate formulas, self-validation, and the candidate->ProductIdentity
bridge.

No I/O, no providers, no network.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from decimal import Decimal

from product_intelligence.domain.enums import IdentityMatchType
from product_intelligence.domain.models import ProductIdentity
from product_intelligence.research.comparable_candidates import (
    ComparableCandidate,
    ComparableCandidateAssessment,
    ComparableCandidateObservation,
    CandidateDisposition,
)
from product_intelligence.research.enterprise_ssd import (
    ENTERPRISE_SSD_SCHEMA,
)
from product_intelligence.research.enterprise_ssd_similarity import (
    ComparisonState,
    ComparableCandidateSpecificationProfile,
    EnterpriseSsdCandidateSimilarity,
    SpecificationSimilarityFieldAssessment,
    establish_candidate_product_identity,
    score_enterprise_ssd_candidate_similarity,
)
from product_intelligence.research.specifications import (
    NormalizedSpecificationObservation,
    ProductSpecificationSet,
    ResolutionState,
    SpecificationDefinition,
    SpecificationObservation,
    SpecificationResolution,
    SpecificationValue,
    SourceAuthority,
    resolve_specification,
)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

_RETRIEVED_AT = datetime(2026, 9, 4, 20, 42, 23, tzinfo=timezone.utc)


def _make_target_identity(mpn: str = "XP15360SE70005") -> ProductIdentity:
    return ProductIdentity(
        manufacturer="Seagate",
        manufacturer_part_number=mpn,
        normalized_part_number=mpn.upper(),
        match_type=IdentityMatchType.EXACT,
    )


def _make_candidate_observation(
    mpn: str = "XP15360SE70015",
    target_mpn: str = "XP15360SE70005",
) -> ComparableCandidateObservation:
    return ComparableCandidateObservation(
        manufacturer_part_number_raw=mpn,
        product_name_raw=None,
        source_name="Seagate Enterprise Support",
        source_url="https://www.seagate.com/support/enterprise-storage/solid-state-drives/nytro-5050/",
        retrieved_at=_RETRIEVED_AT,
        source_authority=SourceAuthority.AUTHORITATIVE,
    )


def _make_candidate(
    mpn: str = "XP15360SE70015",
    target_mpn: str = "XP15360SE70005",
) -> ComparableCandidate:
    target = _make_target_identity(target_mpn)
    obs = _make_candidate_observation(mpn, target_mpn)
    assessment = ComparableCandidateAssessment.build(target, obs)
    return ComparableCandidate.build((assessment,))


def _make_spec_resolution(
    identity: ProductIdentity,
    definition: SpecificationDefinition,
    state: ResolutionState,
    value: object = None,
) -> SpecificationResolution:
    """Build a SpecificationResolution with the given state and value.

    Uses zero evidence (UNKNOWN) as base, or builds a synthetic verified
    resolution with one observation when state is VERIFIED.
    """
    if state is ResolutionState.VERIFIED:
        obs = SpecificationObservation(
            product_identity=identity,
            definition=definition,
            source_name="Test Source",
            source_url="https://test.example.com/",
            retrieved_at=_RETRIEVED_AT,
            raw_value="test",
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        normalized = NormalizedSpecificationObservation(
            observation=obs,
            canonical_value=SpecificationValue(value=value),
        )
        return resolve_specification(identity, definition, (normalized,))
    elif state is ResolutionState.UNVERIFIED:
        obs = SpecificationObservation(
            product_identity=identity,
            definition=definition,
            source_name="Test Source",
            source_url="https://test.example.com/",
            retrieved_at=_RETRIEVED_AT,
            raw_value="test",
            source_authority=SourceAuthority.SECONDARY,
        )
        normalized = NormalizedSpecificationObservation(
            observation=obs,
            canonical_value=SpecificationValue(value=value),
        )
        return resolve_specification(identity, definition, (normalized,))
    elif state is ResolutionState.CONFLICT:
        # Value 1
        if value is not None:
            val1 = value
        elif definition.value_kind.value == "DECIMAL":
            val1 = Decimal("100")
        elif definition.value_kind.value == "BOOLEAN":
            val1 = True
        else:
            val1 = "val_a"

        # Value 2 — different
        if definition.value_kind.value == "DECIMAL":
            val2 = Decimal("999")
        elif definition.value_kind.value == "BOOLEAN":
            val2 = False
        else:
            val2 = "val_b"

        obs1 = SpecificationObservation(
            product_identity=identity,
            definition=definition,
            source_name="Test Source 1",
            source_url="https://test1.example.com/",
            retrieved_at=_RETRIEVED_AT,
            raw_value="test1",
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        norm1 = NormalizedSpecificationObservation(
            observation=obs1,
            canonical_value=SpecificationValue(value=val1),
        )
        obs2 = SpecificationObservation(
            product_identity=identity,
            definition=definition,
            source_name="Test Source 2",
            source_url="https://test2.example.com/",
            retrieved_at=_RETRIEVED_AT,
            raw_value="test2",
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        norm2 = NormalizedSpecificationObservation(
            observation=obs2,
            canonical_value=SpecificationValue(value=val2),
        )
        return resolve_specification(identity, definition, (norm1, norm2))
    else:
        return resolve_specification(identity, definition, ())


def _make_spec_set(
    identity: ProductIdentity,
    resolutions: dict[str, tuple[ResolutionState, object | None]],
) -> ProductSpecificationSet:
    """Build a ProductSpecificationSet from a dict of key -> (state, value)."""
    all_resolutions: dict[str, SpecificationResolution] = {}
    for key, definition in ENTERPRISE_SSD_SCHEMA.definitions.items():
        state, value = resolutions.get(key, (ResolutionState.UNKNOWN, None))
        all_resolutions[key] = _make_spec_resolution(
            identity, definition, state, value
        )
    return ProductSpecificationSet(
        product_identity=identity,
        category_schema=ENTERPRISE_SSD_SCHEMA,
        resolutions=all_resolutions,
    )


def _make_profile(
    candidate: ComparableCandidate,
    resolutions: dict[str, tuple[ResolutionState, object | None]],
) -> ComparableCandidateSpecificationProfile:
    """Helper: build a profile for a candidate with given resolutions."""
    identity = establish_candidate_product_identity(candidate)
    spec_set = _make_spec_set(identity, resolutions)
    return ComparableCandidateSpecificationProfile(
        candidate=candidate,
        candidate_identity=identity,
        specification_set=spec_set,
    )


# ---------------------------------------------------------------------------
# CANDIDATE -> ProductIdentity Bridge
# ---------------------------------------------------------------------------


class TestEstablishCandidateProductIdentity:
    def test_bridge_produces_exact_identity(self) -> None:
        """Bridge produces an EXACT ProductIdentity with correct MPN."""
        candidate = _make_candidate("XP15360SE70015")
        identity = establish_candidate_product_identity(candidate)
        assert identity.manufacturer_part_number == "XP15360SE70015"
        assert identity.normalized_part_number == "XP15360SE70015"
        assert identity.match_type is IdentityMatchType.EXACT

    def test_bridge_does_not_guess_manufacturer(self) -> None:
        """Manufacturer is NOT guessed from source hostname or target."""
        candidate = _make_candidate("XP15360SE70015")
        identity = establish_candidate_product_identity(candidate)
        assert identity.manufacturer is None

    def test_bridge_does_not_guess_product_name(self) -> None:
        """Product name is NOT inferred from evidence titles."""
        target = _make_target_identity()
        obs = ComparableCandidateObservation(
            manufacturer_part_number_raw="XP15360SE70015",
            product_name_raw="Seagate Nytro 5050 SSD",
            source_name="Seagate Enterprise Support",
            source_url="https://www.seagate.com/support/enterprise-storage/solid-state-drives/nytro-5050/",
            retrieved_at=_RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        assessment = ComparableCandidateAssessment.build(target, obs)
        candidate = ComparableCandidate.build((assessment,))
        identity = establish_candidate_product_identity(candidate)
        assert identity.product_name is None

    def test_bridge_rejects_comparable_candidate_subclass(self) -> None:
        """Subclass of ComparableCandidate is rejected by exact type check.

        establish_candidate_product_identity requires EXACT
        ComparableCandidate type — subclasses are rejected even if they
        contain valid inherited candidate evidence.
        """
        from dataclasses import dataclass

        # Build a frozen subclass with valid inherited fields
        @dataclass(frozen=True)
        class ComparableCandidateSubclass(ComparableCandidate):
            """Subclass with extra field to prove it is not the base type."""

            extra_tag: str

        # Create a valid base candidate to extract fields from
        base_candidate = _make_candidate("XP15360SE70015")

        subclass_candidate = ComparableCandidateSubclass(
            manufacturer_part_number=base_candidate.manufacturer_part_number,
            normalized_part_number=base_candidate.normalized_part_number,
            evidence=base_candidate.evidence,
            extra_tag="subclass",
        )

        # Bridge must reject subclasses by exact type check
        with pytest.raises(TypeError, match="ComparableCandidate"):
            establish_candidate_product_identity(subclass_candidate)

    def test_bridge_requires_comparable_candidate_type(self) -> None:
        """Non-ComparableCandidate raises TypeError."""
        with pytest.raises(TypeError, match="ComparableCandidate"):
            establish_candidate_product_identity("not a candidate")  # type: ignore[arg-type]

    def test_bridge_identity_is_established(self) -> None:
        """Bridge identity is established (EXACT requires MPN)."""
        candidate = _make_candidate("XP15360SE70015")
        identity = establish_candidate_product_identity(candidate)
        assert identity.is_established

    def test_target_identity_not_reused(self) -> None:
        """The bridge creates a new identity, not the target's identity."""
        candidate = _make_candidate("XP15360SE70015")
        identity = establish_candidate_product_identity(candidate)
        target = _make_target_identity("XP15360SE70005")
        assert identity is not target
        assert identity.manufacturer_part_number != target.manufacturer_part_number

    def test_non_authoritative_evidence_rejected(self) -> None:
        """Non-AUTHORITATIVE evidence cannot establish the bridge.

        ComparableCandidate rejects non-AUTHORITATIVE at construction,
        so we use TEST-ONLY object.__setattr__ to tamper an otherwise
        valid AUTHORITATIVE candidate's evidence authority.
        """
        # Build a valid AUTHORITATIVE candidate
        target = _make_target_identity()
        obs = ComparableCandidateObservation(
            manufacturer_part_number_raw="XP15360SE70015",
            product_name_raw=None,
            source_name="Seagate Enterprise Support",
            source_url="https://www.seagate.com/support/enterprise-storage/solid-state-drives/nytro-5050/",
            retrieved_at=_RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        assessment = ComparableCandidateAssessment.build(target, obs)
        candidate = ComparableCandidate.build((assessment,))

        # TEST-ONLY: tamper the observation's authority to SECONDARY
        # This cannot happen through normal construction because
        # ComparableCandidate.__post_init__ validates AUTHORITATIVE-only
        object.__setattr__(
            candidate.evidence[0].observation,
            "source_authority",
            SourceAuthority.SECONDARY,
        )

        # Bridge must reject non-AUTHORITATIVE evidence
        with pytest.raises(ValueError, match="AUTHORITATIVE"):
            establish_candidate_product_identity(candidate)


# ---------------------------------------------------------------------------
# ComparableCandidateSpecificationProfile
# ---------------------------------------------------------------------------


class TestCandidateSpecificationProfile:
    def test_profile_construction(self) -> None:
        """Profile binds candidate, identity, and spec set."""
        candidate = _make_candidate("XP15360SE70015")
        identity = establish_candidate_product_identity(candidate)
        spec_set = _make_spec_set(identity, {})
        profile = ComparableCandidateSpecificationProfile(
            candidate=candidate,
            candidate_identity=identity,
            specification_set=spec_set,
        )
        assert profile.candidate is candidate
        assert profile.candidate_identity is identity
        assert profile.specification_set is spec_set

    def test_cross_candidate_rejected(self) -> None:
        """Profile rejects candidate that doesn't match the identity."""
        candidate1 = _make_candidate("XP15360SE70015")
        candidate2 = _make_candidate("XP3840SE70005")
        identity = establish_candidate_product_identity(candidate1)
        spec_set = _make_spec_set(identity, {})
        with pytest.raises(ValueError):
            ComparableCandidateSpecificationProfile(
                candidate=candidate2,
                candidate_identity=identity,
                specification_set=spec_set,
            )

    def test_wrong_identity_rejected(self) -> None:
        """Profile rejects identity with wrong MPN."""
        candidate = _make_candidate("XP15360SE70015")
        wrong_identity = _make_target_identity("WRONG_MPN")
        wrong_spec_set = _make_spec_set(wrong_identity, {})
        with pytest.raises(ValueError):
            ComparableCandidateSpecificationProfile(
                candidate=candidate,
                candidate_identity=wrong_identity,
                specification_set=wrong_spec_set,
            )

    def test_spec_set_identity_mismatch_rejected(self) -> None:
        """Profile rejects spec set bound to different identity."""
        candidate = _make_candidate("XP15360SE70015")
        identity = establish_candidate_product_identity(candidate)
        other_identity = establish_candidate_product_identity(
            _make_candidate("XP3840SE70005")
        )
        other_spec_set = _make_spec_set(other_identity, {})
        with pytest.raises(ValueError, match="product_identity"):
            ComparableCandidateSpecificationProfile(
                candidate=candidate,
                candidate_identity=identity,
                specification_set=other_spec_set,
            )

    def test_wrong_schema_rejected(self) -> None:
        """Profile rejects non-ENTERPRISE_SSD_SCHEMA."""
        from product_intelligence.research.specifications import (
            CategorySchema,
            SpecificationDefinition,
            SpecificationValueKind,
        )
        fake_schema = CategorySchema(
            schema_id="fake",
            schema_version="1.0",
            label="Fake",
            definitions={
                "f": SpecificationDefinition(
                    key="f", label="F", value_kind=SpecificationValueKind.TEXT,
                ),
            },
        )
        candidate = _make_candidate("XP15360SE70015")
        identity = establish_candidate_product_identity(candidate)
        resolutions: dict[str, SpecificationResolution] = {}
        for key, defn in fake_schema.definitions.items():
            resolutions[key] = resolve_specification(identity, defn, ())
        wrong_spec_set = ProductSpecificationSet(
            product_identity=identity,
            category_schema=fake_schema,
            resolutions=resolutions,
        )
        with pytest.raises(ValueError, match="ENTERPRISE_SSD_SCHEMA"):
            ComparableCandidateSpecificationProfile(
                candidate=candidate,
                candidate_identity=identity,
                specification_set=wrong_spec_set,
            )

    def test_enriched_identity_rejected(self) -> None:
        """Profile rejects identity with injected metadata (manufacturer,
        product_name, category) that is NOT the bridge output.

        Even if MPN, normalized MPN, and match_type are correct, extra
        metadata means the identity is not the exact bridge output.
        """
        candidate = _make_candidate("XP15360SE70015")
        # Build an identity with correct MPN but injected metadata
        enriched_identity = ProductIdentity(
            manufacturer="Seagate",
            manufacturer_part_number="XP15360SE70015",
            normalized_part_number="XP15360SE70015",
            product_name="Nytro 5050",
            product_family=None,
            category="SSD",
            match_type=IdentityMatchType.EXACT,
        )
        spec_set = _make_spec_set(enriched_identity, {})

        with pytest.raises(ValueError, match="exact output"):
            ComparableCandidateSpecificationProfile(
                candidate=candidate,
                candidate_identity=enriched_identity,
                specification_set=spec_set,
            )

    def test_enriched_identity_all_fields_rejected(self) -> None:
        """Profile rejects identity with ALL metadata fields injected,
        even though MPN/norm/match_type are identical to bridge output.
        """
        candidate = _make_candidate("XP15360SE70015")
        enriched_identity = ProductIdentity(
            manufacturer="Seagate",
            manufacturer_part_number="XP15360SE70015",
            normalized_part_number="XP15360SE70015",
            product_name="Nytro 5050 SSD",
            product_family="Nytro",
            category="Enterprise SSD",
            match_type=IdentityMatchType.EXACT,
        )
        spec_set = _make_spec_set(enriched_identity, {})

        with pytest.raises(ValueError, match="exact output"):
            ComparableCandidateSpecificationProfile(
                candidate=candidate,
                candidate_identity=enriched_identity,
                specification_set=spec_set,
            )


# ---------------------------------------------------------------------------
# Field Similarity — TEXT (production scoring)
# ---------------------------------------------------------------------------


class TestTextSimilarity:
    def test_text_equal(self) -> None:
        """Equal TEXT values produce similarity 1 (via production scoring)."""
        target = _make_target_identity()
        candidate = _make_candidate("XP15360SE70015")

        target_spec = _make_spec_set(
            target,
            {"interface_connector": (ResolutionState.VERIFIED, "U.2")},
        )
        profile = _make_profile(
            candidate,
            {"interface_connector": (ResolutionState.VERIFIED, "U.2")},
        )

        result = score_enterprise_ssd_candidate_similarity(
            target_specification_set=target_spec,
            candidate_profile=profile,
        )

        for a in result.field_assessments:
            if a.definition.key == "interface_connector":
                assert a.comparison_state is ComparisonState.SCORED
                assert a.field_similarity == Decimal("1")
                return
        pytest.fail("interface_connector assessment not found")

    def test_text_different(self) -> None:
        """Different TEXT values produce similarity 0 (via production scoring)."""
        target = _make_target_identity()
        candidate = _make_candidate("XP15360SE70015")

        target_spec = _make_spec_set(
            target,
            {"interface_connector": (ResolutionState.VERIFIED, "U.2")},
        )
        profile = _make_profile(
            candidate,
            {"interface_connector": (ResolutionState.VERIFIED, "U.3")},
        )

        result = score_enterprise_ssd_candidate_similarity(
            target_specification_set=target_spec,
            candidate_profile=profile,
        )

        for a in result.field_assessments:
            if a.definition.key == "interface_connector":
                assert a.comparison_state is ComparisonState.SCORED
                assert a.field_similarity == Decimal("0")
                return
        pytest.fail("interface_connector assessment not found")


# ---------------------------------------------------------------------------
# Field Similarity — ENUM (production scoring)
# ---------------------------------------------------------------------------


class TestEnumSimilarity:
    def test_enum_equal(self) -> None:
        """Equal ENUM values produce similarity 1 (via production scoring)."""
        target = _make_target_identity()
        candidate = _make_candidate("XP15360SE70015")

        target_spec = _make_spec_set(
            target,
            {"physical_form_factor": (ResolutionState.VERIFIED, "2.5-inch")},
        )
        profile = _make_profile(
            candidate,
            {"physical_form_factor": (ResolutionState.VERIFIED, "2.5-inch")},
        )

        result = score_enterprise_ssd_candidate_similarity(
            target_specification_set=target_spec,
            candidate_profile=profile,
        )

        for a in result.field_assessments:
            if a.definition.key == "physical_form_factor":
                assert a.comparison_state is ComparisonState.SCORED
                assert a.field_similarity == Decimal("1")
                return
        pytest.fail("physical_form_factor assessment not found")

    def test_enum_different(self) -> None:
        """Different ENUM values produce similarity 0 (via production scoring)."""
        target = _make_target_identity()
        candidate = _make_candidate("XP15360SE70015")

        target_spec = _make_spec_set(
            target,
            {"physical_form_factor": (ResolutionState.VERIFIED, "2.5-inch")},
        )
        profile = _make_profile(
            candidate,
            {"physical_form_factor": (ResolutionState.VERIFIED, "M.2")},
        )

        result = score_enterprise_ssd_candidate_similarity(
            target_specification_set=target_spec,
            candidate_profile=profile,
        )

        for a in result.field_assessments:
            if a.definition.key == "physical_form_factor":
                assert a.comparison_state is ComparisonState.SCORED
                assert a.field_similarity == Decimal("0")
                return
        pytest.fail("physical_form_factor assessment not found")


# ---------------------------------------------------------------------------
# Field Similarity — BOOLEAN (production scoring)
# ---------------------------------------------------------------------------


class TestBooleanSimilarity:
    def test_boolean_equal_true(self) -> None:
        """Equal BOOLEAN True -> similarity 1 (via production scoring)."""
        target = _make_target_identity()
        candidate = _make_candidate("XP15360SE70015")

        target_spec = _make_spec_set(
            target,
            {"power_loss_protection": (ResolutionState.VERIFIED, True)},
        )
        profile = _make_profile(
            candidate,
            {"power_loss_protection": (ResolutionState.VERIFIED, True)},
        )

        result = score_enterprise_ssd_candidate_similarity(
            target_specification_set=target_spec,
            candidate_profile=profile,
        )

        for a in result.field_assessments:
            if a.definition.key == "power_loss_protection":
                assert a.comparison_state is ComparisonState.SCORED
                assert a.field_similarity == Decimal("1")
                return
        pytest.fail("power_loss_protection assessment not found")

    def test_boolean_equal_false(self) -> None:
        """Equal BOOLEAN False -> similarity 1 (via production scoring)."""
        target = _make_target_identity()
        candidate = _make_candidate("XP15360SE70015")

        target_spec = _make_spec_set(
            target,
            {"power_loss_protection": (ResolutionState.VERIFIED, False)},
        )
        profile = _make_profile(
            candidate,
            {"power_loss_protection": (ResolutionState.VERIFIED, False)},
        )

        result = score_enterprise_ssd_candidate_similarity(
            target_specification_set=target_spec,
            candidate_profile=profile,
        )

        for a in result.field_assessments:
            if a.definition.key == "power_loss_protection":
                assert a.comparison_state is ComparisonState.SCORED
                assert a.field_similarity == Decimal("1")
                return
        pytest.fail("power_loss_protection assessment not found")

    def test_boolean_different(self) -> None:
        """Different BOOLEAN -> similarity 0 (via production scoring)."""
        target = _make_target_identity()
        candidate = _make_candidate("XP15360SE70015")

        target_spec = _make_spec_set(
            target,
            {"power_loss_protection": (ResolutionState.VERIFIED, True)},
        )
        profile = _make_profile(
            candidate,
            {"power_loss_protection": (ResolutionState.VERIFIED, False)},
        )

        result = score_enterprise_ssd_candidate_similarity(
            target_specification_set=target_spec,
            candidate_profile=profile,
        )

        for a in result.field_assessments:
            if a.definition.key == "power_loss_protection":
                assert a.comparison_state is ComparisonState.SCORED
                assert a.field_similarity == Decimal("0")
                return
        pytest.fail("power_loss_protection assessment not found")


# ---------------------------------------------------------------------------
# Field Similarity — DECIMAL (production scoring)
# ---------------------------------------------------------------------------


class TestDecimalSimilarity:
    def test_decimal_equal(self) -> None:
        """Equal DECIMAL -> similarity 1 (via production scoring)."""
        target = _make_target_identity()
        candidate = _make_candidate("XP15360SE70015")

        target_spec = _make_spec_set(
            target,
            {"capacity": (ResolutionState.VERIFIED, Decimal("3.84"))},
        )
        profile = _make_profile(
            candidate,
            {"capacity": (ResolutionState.VERIFIED, Decimal("3.84"))},
        )

        result = score_enterprise_ssd_candidate_similarity(
            target_specification_set=target_spec,
            candidate_profile=profile,
        )

        for a in result.field_assessments:
            if a.definition.key == "capacity":
                assert a.comparison_state is ComparisonState.SCORED
                assert a.field_similarity == Decimal("1")
                return
        pytest.fail("capacity assessment not found")

    def test_decimal_384_vs_768(self) -> None:
        """3.84 vs 7.68 -> 0.5 (via production scoring)."""
        target = _make_target_identity()
        candidate = _make_candidate("XP15360SE70015")

        target_spec = _make_spec_set(
            target,
            {"capacity": (ResolutionState.VERIFIED, Decimal("3.84"))},
        )
        profile = _make_profile(
            candidate,
            {"capacity": (ResolutionState.VERIFIED, Decimal("7.68"))},
        )

        result = score_enterprise_ssd_candidate_similarity(
            target_specification_set=target_spec,
            candidate_profile=profile,
        )

        for a in result.field_assessments:
            if a.definition.key == "capacity":
                assert a.comparison_state is ComparisonState.SCORED
                assert a.field_similarity == Decimal("0.5")
                return
        pytest.fail("capacity assessment not found")

    def test_decimal_768_vs_384(self) -> None:
        """7.68 vs 3.84 -> 0.5 (symmetric, via production scoring)."""
        target = _make_target_identity()
        candidate = _make_candidate("XP15360SE70015")

        target_spec = _make_spec_set(
            target,
            {"capacity": (ResolutionState.VERIFIED, Decimal("7.68"))},
        )
        profile = _make_profile(
            candidate,
            {"capacity": (ResolutionState.VERIFIED, Decimal("3.84"))},
        )

        result = score_enterprise_ssd_candidate_similarity(
            target_specification_set=target_spec,
            candidate_profile=profile,
        )

        for a in result.field_assessments:
            if a.definition.key == "capacity":
                assert a.comparison_state is ComparisonState.SCORED
                assert a.field_similarity == Decimal("0.5")
                return
        pytest.fail("capacity assessment not found")

    def test_decimal_7000_vs_6300(self) -> None:
        """7000 vs 6300 -> 0.9 (via production scoring)."""
        target = _make_target_identity()
        candidate = _make_candidate("XP15360SE70015")

        target_spec = _make_spec_set(
            target,
            {"sequential_read": (ResolutionState.VERIFIED, Decimal("7000"))},
        )
        profile = _make_profile(
            candidate,
            {"sequential_read": (ResolutionState.VERIFIED, Decimal("6300"))},
        )

        result = score_enterprise_ssd_candidate_similarity(
            target_specification_set=target_spec,
            candidate_profile=profile,
        )

        for a in result.field_assessments:
            if a.definition.key == "sequential_read":
                assert a.comparison_state is ComparisonState.SCORED
                assert a.field_similarity == Decimal("0.9")
                return
        pytest.fail("sequential_read assessment not found")

    def test_decimal_no_float(self) -> None:
        """DECIMAL similarity uses Decimal, not float (via production scoring)."""
        target = _make_target_identity()
        candidate = _make_candidate("XP15360SE70015")

        target_spec = _make_spec_set(
            target,
            {"capacity": (ResolutionState.VERIFIED, Decimal("3.84"))},
        )
        profile = _make_profile(
            candidate,
            {"capacity": (ResolutionState.VERIFIED, Decimal("7.68"))},
        )

        result = score_enterprise_ssd_candidate_similarity(
            target_specification_set=target_spec,
            candidate_profile=profile,
        )

        for a in result.field_assessments:
            if a.definition.key == "capacity":
                assert a.comparison_state is ComparisonState.SCORED
                assert type(a.field_similarity) is Decimal
                return
        pytest.fail("capacity assessment not found")

    def test_fabricated_decimal_rejected(self) -> None:
        """Field similarity outside [0,1] is rejected."""
        target = _make_target_identity()
        identity = establish_candidate_product_identity(_make_candidate("XP15360SE70015"))

        definition = ENTERPRISE_SSD_SCHEMA.definitions["capacity"]

        target_res = _make_spec_resolution(
            target, definition, ResolutionState.VERIFIED, Decimal("3.84")
        )
        candidate_res = _make_spec_resolution(
            identity, definition, ResolutionState.VERIFIED, Decimal("7.68")
        )

        with pytest.raises(ValueError, match="not in range"):
            SpecificationSimilarityFieldAssessment(
                definition=definition,
                target_resolution=target_res,
                candidate_resolution=candidate_res,
                comparison_state=ComparisonState.SCORED,
                field_similarity=Decimal("2"),
            )


# ---------------------------------------------------------------------------
# WRONG-IN-RANGE SCORE REJECTION TESTS
# ---------------------------------------------------------------------------
# These prove that SpecificationSimilarityFieldAssessment recomputes the
# actual score from raw resolutions and rejects a wrong-but-in-range value.


class TestWrongInRangeScoreRejection:
    def test_decimal_wrong_score_rejected(self) -> None:
        """DECIMAL 3.84 vs 7.68 should be 0.5, not 0.73.

        Supplying Decimal("0.73") must be rejected because the
        production formula recomputes 0.5.
        """
        target = _make_target_identity()
        identity = establish_candidate_product_identity(_make_candidate("XP15360SE70015"))

        definition = ENTERPRISE_SSD_SCHEMA.definitions["capacity"]

        target_res = _make_spec_resolution(
            target, definition, ResolutionState.VERIFIED, Decimal("3.84")
        )
        candidate_res = _make_spec_resolution(
            identity, definition, ResolutionState.VERIFIED, Decimal("7.68")
        )

        with pytest.raises(ValueError, match="re-derived"):
            SpecificationSimilarityFieldAssessment(
                definition=definition,
                target_resolution=target_res,
                candidate_resolution=candidate_res,
                comparison_state=ComparisonState.SCORED,
                field_similarity=Decimal("0.73"),  # wrong! actual is 0.5
            )

    def test_equal_text_wrong_score_rejected(self) -> None:
        """Equal TEXT should be 1, not 0.5.

        Supplying Decimal("0.5") for equal text values must be rejected.
        """
        target = _make_target_identity()
        identity = establish_candidate_product_identity(_make_candidate("XP15360SE70015"))

        definition = ENTERPRISE_SSD_SCHEMA.definitions["interface_connector"]

        target_res = _make_spec_resolution(
            target, definition, ResolutionState.VERIFIED, "U.2"
        )
        candidate_res = _make_spec_resolution(
            identity, definition, ResolutionState.VERIFIED, "U.2"
        )

        with pytest.raises(ValueError, match="re-derived"):
            SpecificationSimilarityFieldAssessment(
                definition=definition,
                target_resolution=target_res,
                candidate_resolution=candidate_res,
                comparison_state=ComparisonState.SCORED,
                field_similarity=Decimal("0.5"),  # wrong! actual is 1
            )

    def test_different_enum_wrong_score_rejected(self) -> None:
        """Different ENUM should be 0, not 1.

        Supplying Decimal("1") for different enum values must be rejected.
        """
        target = _make_target_identity()
        identity = establish_candidate_product_identity(_make_candidate("XP15360SE70015"))

        definition = ENTERPRISE_SSD_SCHEMA.definitions["physical_form_factor"]

        target_res = _make_spec_resolution(
            target, definition, ResolutionState.VERIFIED, "2.5-inch"
        )
        candidate_res = _make_spec_resolution(
            identity, definition, ResolutionState.VERIFIED, "M.2"
        )

        with pytest.raises(ValueError, match="re-derived"):
            SpecificationSimilarityFieldAssessment(
                definition=definition,
                target_resolution=target_res,
                candidate_resolution=candidate_res,
                comparison_state=ComparisonState.SCORED,
                field_similarity=Decimal("1"),  # wrong! actual is 0
            )

    def test_different_boolean_wrong_score_rejected(self) -> None:
        """Different BOOLEAN should be 0, not 0.25.

        Supplying Decimal("0.25") for different boolean values must be rejected.
        """
        target = _make_target_identity()
        identity = establish_candidate_product_identity(_make_candidate("XP15360SE70015"))

        definition = ENTERPRISE_SSD_SCHEMA.definitions["power_loss_protection"]

        target_res = _make_spec_resolution(
            target, definition, ResolutionState.VERIFIED, True
        )
        candidate_res = _make_spec_resolution(
            identity, definition, ResolutionState.VERIFIED, False
        )

        with pytest.raises(ValueError, match="re-derived"):
            SpecificationSimilarityFieldAssessment(
                definition=definition,
                target_resolution=target_res,
                candidate_resolution=candidate_res,
                comparison_state=ComparisonState.SCORED,
                field_similarity=Decimal("0.25"),  # wrong! actual is 0
            )


# ---------------------------------------------------------------------------
# Evidence State — VERIFIED-only scoring
# ---------------------------------------------------------------------------


class TestEvidenceState:
    def test_target_unknown_not_scored(self) -> None:
        """UNKNOWN target -> TARGET_NOT_VERIFIED, not scored."""
        target = _make_target_identity()
        identity = establish_candidate_product_identity(_make_candidate("XP15360SE70015"))

        definition = ENTERPRISE_SSD_SCHEMA.definitions["capacity"]

        target_res = _make_spec_resolution(
            target, definition, ResolutionState.UNKNOWN, None
        )
        candidate_res = _make_spec_resolution(
            identity, definition, ResolutionState.VERIFIED, Decimal("3.84")
        )

        with pytest.raises(ValueError, match="re-derived"):
            SpecificationSimilarityFieldAssessment(
                definition=definition,
                target_resolution=target_res,
                candidate_resolution=candidate_res,
                comparison_state=ComparisonState.SCORED,
                field_similarity=Decimal("1"),
            )

    def test_candidate_unknown_not_scored(self) -> None:
        """UNKNOWN candidate -> CANDIDATE_NOT_VERIFIED, not scored."""
        target = _make_target_identity()
        identity = establish_candidate_product_identity(_make_candidate("XP15360SE70015"))

        definition = ENTERPRISE_SSD_SCHEMA.definitions["capacity"]

        target_res = _make_spec_resolution(
            target, definition, ResolutionState.VERIFIED, Decimal("3.84")
        )
        candidate_res = _make_spec_resolution(
            identity, definition, ResolutionState.UNKNOWN, None
        )

        with pytest.raises(ValueError, match="re-derived"):
            SpecificationSimilarityFieldAssessment(
                definition=definition,
                target_resolution=target_res,
                candidate_resolution=candidate_res,
                comparison_state=ComparisonState.SCORED,
                field_similarity=Decimal("1"),
            )

    def test_target_unverified_not_scored(self) -> None:
        """UNVERIFIED target -> TARGET_NOT_VERIFIED."""
        target = _make_target_identity()
        identity = establish_candidate_product_identity(_make_candidate("XP15360SE70015"))

        definition = ENTERPRISE_SSD_SCHEMA.definitions["capacity"]

        target_res = _make_spec_resolution(
            target, definition, ResolutionState.UNVERIFIED, Decimal("3.84")
        )
        candidate_res = _make_spec_resolution(
            identity, definition, ResolutionState.VERIFIED, Decimal("3.84")
        )

        with pytest.raises(ValueError, match="re-derived"):
            SpecificationSimilarityFieldAssessment(
                definition=definition,
                target_resolution=target_res,
                candidate_resolution=candidate_res,
                comparison_state=ComparisonState.SCORED,
                field_similarity=Decimal("1"),
            )

    def test_candidate_unverified_not_scored(self) -> None:
        """UNVERIFIED candidate -> CANDIDATE_NOT_VERIFIED."""
        target = _make_target_identity()
        identity = establish_candidate_product_identity(_make_candidate("XP15360SE70015"))

        definition = ENTERPRISE_SSD_SCHEMA.definitions["capacity"]

        target_res = _make_spec_resolution(
            target, definition, ResolutionState.VERIFIED, Decimal("3.84")
        )
        candidate_res = _make_spec_resolution(
            identity, definition, ResolutionState.UNVERIFIED, Decimal("3.84")
        )

        with pytest.raises(ValueError, match="re-derived"):
            SpecificationSimilarityFieldAssessment(
                definition=definition,
                target_resolution=target_res,
                candidate_resolution=candidate_res,
                comparison_state=ComparisonState.SCORED,
                field_similarity=Decimal("1"),
            )

    def test_target_conflict_not_scored(self) -> None:
        """CONFLICT target -> TARGET_NOT_VERIFIED."""
        target = _make_target_identity()
        identity = establish_candidate_product_identity(_make_candidate("XP15360SE70015"))

        definition = ENTERPRISE_SSD_SCHEMA.definitions["capacity"]

        target_res = _make_spec_resolution(
            target, definition, ResolutionState.CONFLICT, None
        )
        candidate_res = _make_spec_resolution(
            identity, definition, ResolutionState.VERIFIED, Decimal("3.84")
        )

        with pytest.raises(ValueError, match="re-derived"):
            SpecificationSimilarityFieldAssessment(
                definition=definition,
                target_resolution=target_res,
                candidate_resolution=candidate_res,
                comparison_state=ComparisonState.SCORED,
                field_similarity=Decimal("1"),
            )

    def test_candidate_conflict_not_scored(self) -> None:
        """CONFLICT candidate -> CANDIDATE_NOT_VERIFIED."""
        target = _make_target_identity()
        identity = establish_candidate_product_identity(_make_candidate("XP15360SE70015"))

        definition = ENTERPRISE_SSD_SCHEMA.definitions["capacity"]

        target_res = _make_spec_resolution(
            target, definition, ResolutionState.VERIFIED, Decimal("3.84")
        )
        candidate_res = _make_spec_resolution(
            identity, definition, ResolutionState.CONFLICT, None
        )

        with pytest.raises(ValueError, match="re-derived"):
            SpecificationSimilarityFieldAssessment(
                definition=definition,
                target_resolution=target_res,
                candidate_resolution=candidate_res,
                comparison_state=ComparisonState.SCORED,
                field_similarity=Decimal("1"),
            )

    def test_both_not_verified(self) -> None:
        """Both UNKNOWN -> BOTH_NOT_VERIFIED."""
        target = _make_target_identity()
        identity = establish_candidate_product_identity(_make_candidate("XP15360SE70015"))

        definition = ENTERPRISE_SSD_SCHEMA.definitions["capacity"]

        target_res = _make_spec_resolution(
            target, definition, ResolutionState.UNKNOWN, None
        )
        candidate_res = _make_spec_resolution(
            identity, definition, ResolutionState.UNKNOWN, None
        )

        assessment = SpecificationSimilarityFieldAssessment(
            definition=definition,
            target_resolution=target_res,
            candidate_resolution=candidate_res,
            comparison_state=ComparisonState.BOTH_NOT_VERIFIED,
            field_similarity=None,
        )
        assert assessment.comparison_state is ComparisonState.BOTH_NOT_VERIFIED
        assert assessment.field_similarity is None


# ---------------------------------------------------------------------------
# Aggregate — EnterpriseSsdCandidateSimilarity
# ---------------------------------------------------------------------------


class TestAggregateSimilarity:
    def test_zero_scored_fields(self) -> None:
        """Zero scored fields -> observed and weighted are None."""
        target = _make_target_identity()
        candidate = _make_candidate("XP15360SE70015")

        target_spec = _make_spec_set(target, {})
        profile = _make_profile(candidate, {})

        result = score_enterprise_ssd_candidate_similarity(
            target_specification_set=target_spec,
            candidate_profile=profile,
        )

        assert result.scored_field_count == 0
        assert result.evidence_coverage == Decimal("0") / Decimal("12")
        assert result.observed_similarity is None
        assert result.evidence_weighted_similarity is None

    def test_one_exact_field(self) -> None:
        """One exact field -> observed=1, coverage=1/12, weighted=1/12."""
        target = _make_target_identity()
        candidate = _make_candidate("XP15360SE70015")

        target_spec = _make_spec_set(
            target,
            {"physical_form_factor": (ResolutionState.VERIFIED, "2.5-inch")},
        )
        profile = _make_profile(
            candidate,
            {"physical_form_factor": (ResolutionState.VERIFIED, "2.5-inch")},
        )

        result = score_enterprise_ssd_candidate_similarity(
            target_specification_set=target_spec,
            candidate_profile=profile,
        )

        assert result.scored_field_count == 1
        assert result.evidence_coverage == Decimal("1") / Decimal("12")
        assert result.observed_similarity == Decimal("1")
        assert result.evidence_weighted_similarity == Decimal("1") / Decimal("12")

    def test_one_mismatch_field(self) -> None:
        """One mismatch field -> observed=0, coverage=1/12, weighted=0."""
        target = _make_target_identity()
        candidate = _make_candidate("XP15360SE70015")

        target_spec = _make_spec_set(
            target,
            {"physical_form_factor": (ResolutionState.VERIFIED, "2.5-inch")},
        )
        profile = _make_profile(
            candidate,
            {"physical_form_factor": (ResolutionState.VERIFIED, "M.2")},
        )

        result = score_enterprise_ssd_candidate_similarity(
            target_specification_set=target_spec,
            candidate_profile=profile,
        )

        assert result.scored_field_count == 1
        assert result.evidence_coverage == Decimal("1") / Decimal("12")
        assert result.observed_similarity == Decimal("0")
        assert result.evidence_weighted_similarity == Decimal("0")

    def test_mixed_fields(self) -> None:
        """Mixed numeric and categorical fields are scored independently."""
        target = _make_target_identity()
        candidate = _make_candidate("XP15360SE70015")

        target_spec = _make_spec_set(
            target,
            {
                "physical_form_factor": (ResolutionState.VERIFIED, "2.5-inch"),
                "capacity": (ResolutionState.VERIFIED, Decimal("3.84")),
            },
        )
        profile = _make_profile(
            candidate,
            {
                "physical_form_factor": (ResolutionState.VERIFIED, "2.5-inch"),
                "capacity": (ResolutionState.VERIFIED, Decimal("7.68")),
            },
        )

        result = score_enterprise_ssd_candidate_similarity(
            target_specification_set=target_spec,
            candidate_profile=profile,
        )

        assert result.scored_field_count == 2
        assert result.evidence_coverage == Decimal("2") / Decimal("12")
        assert result.observed_similarity == Decimal("0.75")
        assert result.evidence_weighted_similarity == Decimal("0.125")

    def test_field_count_exactly_12(self) -> None:
        """Every candidate has exactly 12 field assessments."""
        target = _make_target_identity()
        candidate = _make_candidate("XP15360SE70015")

        target_spec = _make_spec_set(target, {})
        profile = _make_profile(candidate, {})

        result = score_enterprise_ssd_candidate_similarity(
            target_specification_set=target_spec,
            candidate_profile=profile,
        )

        assert len(result.field_assessments) == 12

    def test_no_omitted_unknown_fields(self) -> None:
        """All 12 definitions have assessments even when UNKNOWN."""
        target = _make_target_identity()
        candidate = _make_candidate("XP15360SE70015")

        target_spec = _make_spec_set(target, {})
        profile = _make_profile(candidate, {})

        result = score_enterprise_ssd_candidate_similarity(
            target_specification_set=target_spec,
            candidate_profile=profile,
        )

        definition_keys = {
            d.key for d in ENTERPRISE_SSD_SCHEMA.definitions.values()
        }
        assessment_keys = {a.definition.key for a in result.field_assessments}
        assert assessment_keys == definition_keys

    def test_fabricated_score_rejected(self) -> None:
        """Manually constructing with wrong observed_similarity fails."""
        target = _make_target_identity()
        candidate = _make_candidate("XP15360SE70015")

        target_spec = _make_spec_set(
            target,
            {"physical_form_factor": (ResolutionState.VERIFIED, "2.5-inch")},
        )
        profile = _make_profile(
            candidate,
            {"physical_form_factor": (ResolutionState.VERIFIED, "2.5-inch")},
        )

        result = score_enterprise_ssd_candidate_similarity(
            target_specification_set=target_spec,
            candidate_profile=profile,
        )

        with pytest.raises(ValueError, match="observed_similarity"):
            EnterpriseSsdCandidateSimilarity(
                candidate_profile=profile,
                target_specification_set=target_spec,
                field_assessments=result.field_assessments,
                scored_field_count=result.scored_field_count,
                evidence_coverage=result.evidence_coverage,
                observed_similarity=Decimal("0"),  # fabricated! actual is 1
                evidence_weighted_similarity=result.evidence_weighted_similarity,
            )

    def test_fabricated_coverage_rejected(self) -> None:
        """Manually constructing with wrong coverage fails."""
        target = _make_target_identity()
        candidate = _make_candidate("XP15360SE70015")

        target_spec = _make_spec_set(
            target,
            {"physical_form_factor": (ResolutionState.VERIFIED, "2.5-inch")},
        )
        profile = _make_profile(
            candidate,
            {"physical_form_factor": (ResolutionState.VERIFIED, "2.5-inch")},
        )

        result = score_enterprise_ssd_candidate_similarity(
            target_specification_set=target_spec,
            candidate_profile=profile,
        )

        with pytest.raises(ValueError, match="evidence_coverage"):
            EnterpriseSsdCandidateSimilarity(
                candidate_profile=profile,
                target_specification_set=target_spec,
                field_assessments=result.field_assessments,
                scored_field_count=result.scored_field_count,
                evidence_coverage=Decimal("1"),  # fabricated!
                observed_similarity=result.observed_similarity,
                evidence_weighted_similarity=result.evidence_weighted_similarity,
            )

    def test_substituted_field_assessment_rejected(self) -> None:
        """Substituting a resolution in a field assessment is rejected."""
        target = _make_target_identity()
        candidate = _make_candidate("XP15360SE70015")

        target_spec = _make_spec_set(
            target,
            {"capacity": (ResolutionState.VERIFIED, Decimal("3.84"))},
        )
        profile = _make_profile(
            candidate,
            {"capacity": (ResolutionState.VERIFIED, Decimal("3.84"))},
        )

        result = score_enterprise_ssd_candidate_similarity(
            target_specification_set=target_spec,
            candidate_profile=profile,
        )

        # Build a different target spec set
        other_target = _make_target_identity("OTHER")
        other_target_spec = _make_spec_set(
            other_target,
            {"capacity": (ResolutionState.VERIFIED, Decimal("7.68"))},
        )

        definition = ENTERPRISE_SSD_SCHEMA.definitions["capacity"]
        capacity_idx = None
        for i, a in enumerate(result.field_assessments):
            if a.definition.key == "capacity":
                capacity_idx = i
                break
        assert capacity_idx is not None

        original_assessment = result.field_assessments[capacity_idx]
        substituted_assessment = SpecificationSimilarityFieldAssessment(
            definition=definition,
            target_resolution=other_target_spec.resolutions[definition.key],
            candidate_resolution=original_assessment.candidate_resolution,
            comparison_state=ComparisonState.SCORED,
            field_similarity=Decimal("0.5"),
        )

        modified_assessments = list(result.field_assessments)
        modified_assessments[capacity_idx] = substituted_assessment

        with pytest.raises(ValueError, match="substituted|not the exact"):
            EnterpriseSsdCandidateSimilarity(
                candidate_profile=profile,
                target_specification_set=target_spec,
                field_assessments=tuple(modified_assessments),
                scored_field_count=1,
                evidence_coverage=Decimal("1") / Decimal("12"),
                observed_similarity=Decimal("0.5"),
                evidence_weighted_similarity=Decimal("0.5") / Decimal("12"),
            )

    def test_no_float_in_similarity(self) -> None:
        """Float field_similarity is rejected."""
        target = _make_target_identity()
        identity = establish_candidate_product_identity(_make_candidate("XP15360SE70015"))

        definition = ENTERPRISE_SSD_SCHEMA.definitions["capacity"]

        target_res = _make_spec_resolution(
            target, definition, ResolutionState.VERIFIED, Decimal("3.84")
        )
        candidate_res = _make_spec_resolution(
            identity, definition, ResolutionState.VERIFIED, Decimal("3.84")
        )

        with pytest.raises(TypeError, match="Decimal"):
            SpecificationSimilarityFieldAssessment(
                definition=definition,
                target_resolution=target_res,
                candidate_resolution=candidate_res,
                comparison_state=ComparisonState.SCORED,
                field_similarity=1.0,
            )


# ---------------------------------------------------------------------------
# EXACT SCALAR TYPE TESTS
# ---------------------------------------------------------------------------
# Prove rejection of numerically-equal wrong types for aggregate scalars.


class TestExactScalarTypes:
    def test_scored_field_count_bool_rejected(self) -> None:
        """scored_field_count=True is rejected (must be int, not bool)."""
        target = _make_target_identity()
        candidate = _make_candidate("XP15360SE70015")

        target_spec = _make_spec_set(target, {})
        profile = _make_profile(candidate, {})

        result = score_enterprise_ssd_candidate_similarity(
            target_specification_set=target_spec,
            candidate_profile=profile,
        )

        with pytest.raises(TypeError, match="int"):
            EnterpriseSsdCandidateSimilarity(
                candidate_profile=profile,
                target_specification_set=target_spec,
                field_assessments=result.field_assessments,
                scored_field_count=True,  # bool, not int!
                evidence_coverage=result.evidence_coverage,
                observed_similarity=result.observed_similarity,
                evidence_weighted_similarity=result.evidence_weighted_similarity,
            )

    def test_scored_field_count_float_rejected(self) -> None:
        """scored_field_count=1.0 is rejected (must be int, not float)."""
        target = _make_target_identity()
        candidate = _make_candidate("XP15360SE70015")

        target_spec = _make_spec_set(
            target,
            {"physical_form_factor": (ResolutionState.VERIFIED, "2.5-inch")},
        )
        profile = _make_profile(
            candidate,
            {"physical_form_factor": (ResolutionState.VERIFIED, "2.5-inch")},
        )

        result = score_enterprise_ssd_candidate_similarity(
            target_specification_set=target_spec,
            candidate_profile=profile,
        )

        with pytest.raises(TypeError, match="int"):
            EnterpriseSsdCandidateSimilarity(
                candidate_profile=profile,
                target_specification_set=target_spec,
                field_assessments=result.field_assessments,
                scored_field_count=1.0,  # float, not int!
                evidence_coverage=result.evidence_coverage,
                observed_similarity=result.observed_similarity,
                evidence_weighted_similarity=result.evidence_weighted_similarity,
            )

    def test_evidence_coverage_int_zero_rejected(self) -> None:
        """evidence_coverage=0 is rejected (must be Decimal("0"), not int)."""
        target = _make_target_identity()
        candidate = _make_candidate("XP15360SE70015")

        target_spec = _make_spec_set(target, {})
        profile = _make_profile(candidate, {})

        result = score_enterprise_ssd_candidate_similarity(
            target_specification_set=target_spec,
            candidate_profile=profile,
        )

        with pytest.raises(TypeError, match="Decimal"):
            EnterpriseSsdCandidateSimilarity(
                candidate_profile=profile,
                target_specification_set=target_spec,
                field_assessments=result.field_assessments,
                scored_field_count=0,
                evidence_coverage=0,  # int, not Decimal!
                observed_similarity=result.observed_similarity,
                evidence_weighted_similarity=result.evidence_weighted_similarity,
            )

    def test_observed_similarity_float_rejected(self) -> None:
        """observed_similarity=1.0 is rejected (must be Decimal("1"), not float)."""
        target = _make_target_identity()
        candidate = _make_candidate("XP15360SE70015")

        target_spec = _make_spec_set(
            target,
            {"physical_form_factor": (ResolutionState.VERIFIED, "2.5-inch")},
        )
        profile = _make_profile(
            candidate,
            {"physical_form_factor": (ResolutionState.VERIFIED, "2.5-inch")},
        )

        result = score_enterprise_ssd_candidate_similarity(
            target_specification_set=target_spec,
            candidate_profile=profile,
        )

        with pytest.raises(TypeError, match="Decimal"):
            EnterpriseSsdCandidateSimilarity(
                candidate_profile=profile,
                target_specification_set=target_spec,
                field_assessments=result.field_assessments,
                scored_field_count=result.scored_field_count,
                evidence_coverage=result.evidence_coverage,
                observed_similarity=1.0,  # float, not Decimal!
                evidence_weighted_similarity=result.evidence_weighted_similarity,
            )

    def test_evidence_weighted_similarity_bool_rejected(self) -> None:
        """evidence_weighted_similarity=True is rejected (must be Decimal)."""
        target = _make_target_identity()
        candidate = _make_candidate("XP15360SE70015")

        target_spec = _make_spec_set(
            target,
            {"physical_form_factor": (ResolutionState.VERIFIED, "2.5-inch")},
        )
        profile = _make_profile(
            candidate,
            {"physical_form_factor": (ResolutionState.VERIFIED, "2.5-inch")},
        )

        result = score_enterprise_ssd_candidate_similarity(
            target_specification_set=target_spec,
            candidate_profile=profile,
        )

        # Build a case where weighted = 1/12
        with pytest.raises(TypeError, match="Decimal"):
            EnterpriseSsdCandidateSimilarity(
                candidate_profile=profile,
                target_specification_set=target_spec,
                field_assessments=result.field_assessments,
                scored_field_count=result.scored_field_count,
                evidence_coverage=result.evidence_coverage,
                observed_similarity=result.observed_similarity,
                evidence_weighted_similarity=True,  # bool, not Decimal!
            )
