"""Tests for the bounded sales-unit evidence extraction layer
(PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-B5-P2).

Covers ``product_intelligence.research.sales_unit_extraction`` — the pure,
deterministic, versioned (schema v1) extraction and validation layer of the
Q3-B4 decision's Option D observability phase (roadmap row P2):

* P1. UNAMBIGUOUS RECOGNITION (preservation of valid observations) — the
  single retail unit, a pack of N, an N-unit factory pack, a tray with an
  established quantity, and a bundle with PUBLISHED CONTENTS are recorded
  as bounded cues with their full provenance (a bundle count WITHOUT
  published contents is ambiguous, never established — the Q3-B5-P2-FU1
  correction), and the fail-closed mapping fills the frozen S2-C-FU1
  channel's OBSERVED state (kind + quantity + the exact published text +
  the cue's source). An independently unresolved ambiguous cue — of ANY
  kind, including the established kind — blocks OBSERVED_UNAMBIGUOUS;
  only a genuine duplicate / subsumed cue deterministically proven by the
  exact published spans is admitted (the documented subsumption rule).
* P2. SPECIFICATION QUANTITIES ARE NOT SALES QUANTITIES (false-positive
  resistance) — capacity values (4 TB / 3.84TB), chassis height (2U / 1U),
  dual-port networking, channel / lane counts (8-channel, PCIe 4.0 x4,
  1 DWPD), product revision numbers, and non-canonical or capacity-
  attached counts never establish a sales unit; bare "pack" / "bundle"
  words are ambiguous cues, not observations.
* P3. NEVER INFERRED — a missing packaging field, an exact MPN, one
  listing, one price, or one product image never becomes SINGLE_UNIT; the
  opaque raw reference is never read; no input member is a model claim and
  no model output is an input.
* P4. IDENTIFIER FIELDS ARE OUT OF SCOPE — a seller SKU or published MPN
  containing a quantity-like token is recorded as set aside (provenance),
  never used as packaging evidence.
* P5. AMBIGUITY / CONTRADICTION REPRESENTATION — the versioned result
  distinguishes OBSERVED_UNAMBIGUOUS / AMBIGUOUS_CUE / CONTRADICTED_CUES /
  NO_PACKAGING_PUBLISHED with every cue recorded (field, source, full
  published value, verbatim cue text, span, kind, quantity, disposition,
  bounded reason); the frozen channel has no ambiguous / contradicted
  state, and the mapping is fail-closed: only an unambiguous result
  becomes OBSERVED, everything else stays the recorded UNAVAILABLE absence
  (neither side of a contradiction is ever presented as THE unit).
* P6. PROVENANCE CONTRACT — the result is immutable, deterministic, bound
  to the exact examined input (input digest over the named 3A fields,
  raw_reference excluded), self-verified (result digest), and the channel
  mapping refuses a tampered / forged result; a cue cannot claim text its
  field never published, and no cue carries a foreign (model-claim or
  non-extractor) provenance source.
* P7. FU3 INTERACTION — the mapped channel drives the separately versioned
  FU3 derivation exactly as the approved contract specifies: observed
  single unit PROVEN_EQUIVALENT, published incompatible unit CONTRADICTED
  (never auto-priced), recorded absence / ambiguity / contradiction
  UNPROVEN (capped at NEEDS_REVIEW), and the old token's replay is
  unchanged (the frozen live builder still records UNAVAILABLE; no live
  module references the extractor; V2_AUTHORITY_QUALIFIED stays False).

Every case is an offline construction: no network call, no model call, no
page fetch. The recorded-page integration over the real 3A fixtures is in
``test_sales_unit_extraction_recorded_pages.py``.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.research import (
    AUTHORITY_CONTRACT_VERSION_V2,
    AuthorityRuleV2FU3,
    AuthorityTier,
    CandidateEvidenceSourceV2,
    CandidateProductEvidenceSource,
    CandidateSalesUnitEvidenceV2,
    ConflictClass,
    ExtractionMethod,
    HumanReviewStateV2,
    IdentityStateAssessmentV2,
    ListingObservation,
    PackagingEvidenceStateV2,
    ProductEvidenceDimension,
    ProductEvidenceFactV2,
    ProductEvidenceProfileV2,
    ProductEvidenceQuality,
    SALES_UNIT_EVIDENCE_UNAVAILABLE,
    SalesUnitKindV2,
    SemanticEvaluationStateV2,
    SemanticEvaluationV2,
    UncertainSubstateV2,
    V2Confidence,
    V2SemanticDecision,
    assess_listing_identity,
    build_candidate_commercial_evidence_v2,
    build_semantic_match_case_v2,
    build_v2_product_evidence_profile,
    derive_identity_state_v2,
    normalize_listing_observation,
)
from product_intelligence.research import sales_unit_extraction as sui
from product_intelligence.research import semantic_authority_fu3 as fu3
from product_intelligence.research.semantic_authority_fu3 import (
    AUTHORITY_CONTRACT_VERSION_V2_FU3,
    SalesUnitAuthorityV2,
    TargetSalesUnitFormV2,
    TargetSalesUnitEvidenceSourceV2,
    TargetSalesUnitEvidenceV2,
    derive_authority_tier_for_contract,
    sales_unit_authority_from_channel,
)
from product_intelligence.research.semantic_v2 import SemanticMatchCaseV2

REPO_ROOT = Path(__file__).resolve().parents[2]

REQUEST = ResearchRequest(
    manufacturer_part_number="ABC-123", description="A test product"
)

TITLE_SOURCES = frozenset(
    {CandidateProductEvidenceSource.LISTING_PRODUCT_TITLE}
)


# -- Construction helpers ----------------------------------------------------


def _observation(
    title: str | None = "Test Product",
    sku: str | None = None,
    mpn: str | None = None,
    source_url: str = "https://example.com/product",
    offer_url: str | None = None,
    raw_reference: str | None = None,
) -> ListingObservation:
    return ListingObservation(
        source_url=source_url,
        extraction_method=ExtractionMethod.JSON_LD,
        product_title=title,
        brand_text=None,
        manufacturer_part_number_text=mpn,
        sku_text=sku,
        price_text="100",
        currency_text="USD",
        availability_text="In stock",
        condition_text="New",
        seller_text=None,
        offer_url_text=offer_url,
        raw_reference=raw_reference,
    )


def _extract(
    title: str | None,
    sku: str | None = None,
    mpn: str | None = None,
    structured: str | None = None,
    **obs_kwargs,
) -> sui.SalesUnitExtractionResult:
    return sui.extract_sales_unit_evidence(
        _observation(title=title, sku=sku, mpn=mpn, **obs_kwargs),
        structured,
    )


def _channel(
    title: str | None,
    sku: str | None = None,
    mpn: str | None = None,
    structured: str | None = None,
    **obs_kwargs,
) -> CandidateSalesUnitEvidenceV2:
    return sui.sales_unit_channel_from_extraction(
        _extract(title, sku=sku, mpn=mpn, structured=structured, **obs_kwargs)
    )


def _match(high: bool = True, conflicts=frozenset()) -> SemanticEvaluationV2:
    return SemanticEvaluationV2.evaluated(
        V2SemanticDecision.MATCH,
        V2Confidence.HIGH if high else V2Confidence.MEDIUM,
        frozenset(conflicts),
    )


def _strong_profile() -> ProductEvidenceProfileV2:
    """The future qualified-state simulation input (dimension A = STRONG):
    a usable title plus two matched facts on two distinct hard product
    dimensions, grounded in the listing title (never a model claim)."""
    return ProductEvidenceProfileV2(
        has_usable_product_title=True,
        matched_facts=frozenset(
            {
                ProductEvidenceFactV2(
                    ProductEvidenceDimension.CAPACITY, TITLE_SOURCES
                ),
                ProductEvidenceFactV2(
                    ProductEvidenceDimension.INTERFACE, TITLE_SOURCES
                ),
            }
        ),
    )


def _u1_assessment(
    title: str = "Has ABC-123 in the title",
) -> IdentityStateAssessmentV2:
    """The real frozen chain over a U1 (title MPN) observation — the
    §4.1 invariant composition's identifier shape."""
    normalized = normalize_listing_observation(_observation(title=title))
    return assess_listing_identity(REQUEST, normalized)


def _u1_v2(title: str = "Has ABC-123 in the title") -> IdentityStateAssessmentV2:
    return derive_identity_state_v2(_u1_assessment(title=title))


def _target(
    form: TargetSalesUnitFormV2,
    quantity: int | None = None,
) -> TargetSalesUnitEvidenceV2:
    return TargetSalesUnitEvidenceV2(
        form=form,
        quantity=quantity,
        source=TargetSalesUnitEvidenceSourceV2.REVIEWED_TARGET_CONTEXT,
    )


OBS = sui.SalesUnitExtractionState.OBSERVED_UNAMBIGUOUS
AMB = sui.SalesUnitExtractionState.AMBIGUOUS_CUE
CON = sui.SalesUnitExtractionState.CONTRADICTED_CUES
NONE_STATE = sui.SalesUnitExtractionState.NO_PACKAGING_PUBLISHED
EST = sui.SalesUnitCueDisposition.ESTABLISHED
AMBD = sui.SalesUnitCueDisposition.AMBIGUOUS
REASON = sui.SalesUnitCueReason
FIELD = sui.SalesUnitCueField


def _cue_state(result, expected):
    assert len(result.cues) == len(expected)
    for cue, (kind, quantity, disposition, reason) in zip(result.cues, expected):
        assert cue.kind is kind, (cue, kind)
        assert cue.quantity == quantity, (cue, quantity)
        assert cue.disposition is disposition, (cue, disposition)
        assert cue.reason is reason, (cue, reason)


# ===========================================================================
# P1. UNAMBIGUOUS RECOGNITION (preservation of valid observations)
# ===========================================================================


class TestUnambiguousRecognition:
    @pytest.mark.parametrize(
        ("title", "cue_text"),
        [
            ("Single Unit", "Single Unit"),
            ("single-unit SSD", "single-unit"),
            ("1 Unit", "1 Unit"),
            ("1-unit SSD", "1-unit"),
        ],
        ids=["single-unit-phrase", "hyphenated", "one-unit", "one-unit-hyphen"],
    )
    def test_single_retail_unit_phrases_are_observed(self, title, cue_text) -> None:
        result = _extract(title)
        assert result.state is OBS
        assert result.established_kind is SalesUnitKindV2.SINGLE_UNIT
        assert result.established_quantity is None
        assert len(result.cues) == 1
        _cue_state(result, [(SalesUnitKindV2.SINGLE_UNIT, None, EST, None)])
        channel = sui.sales_unit_channel_from_extraction(result)
        assert channel.state is PackagingEvidenceStateV2.OBSERVED
        assert channel.kind is SalesUnitKindV2.SINGLE_UNIT
        assert channel.quantity is None
        assert channel.source is CandidateEvidenceSourceV2.LISTING_TITLE
        # The raw detail is the exact published phrase, original case.
        assert channel.raw_detail == cue_text

    @pytest.mark.parametrize(
        "title, cue_text",
        [
            ("1.92TB M.2 NVMe SSD (pack of 4)", "pack of 4"),
            ("SSD 4TB - 4-Pack", "4-Pack"),
            ("960GB Drive 4 Pack", "4 Pack"),
        ],
        ids=["pack-of-n", "n-pack", "n-space-pack"],
    )
    def test_pack_of_n_phrases_are_observed(self, title, cue_text) -> None:
        result = _extract(title)
        assert result.state is OBS
        assert result.established_kind is SalesUnitKindV2.PACK_QUANTITY
        assert result.established_quantity == 4
        _cue_state(result, [(SalesUnitKindV2.PACK_QUANTITY, 4, EST, None)])
        channel = sui.sales_unit_channel_from_extraction(result)
        assert channel.state is PackagingEvidenceStateV2.OBSERVED
        assert channel.kind is SalesUnitKindV2.PACK_QUANTITY
        assert channel.quantity == 4
        assert channel.raw_detail == cue_text

    @pytest.mark.parametrize(
        "title, quantity",
        [
            ("10-unit factory pack SSD", 10),
            ("Factory Pack of 10", 10),
            ("factory pack", None),
        ],
        ids=["n-unit-factory-pack", "factory-pack-of-n", "bare-factory-pack"],
    )
    def test_n_unit_factory_pack_phrases_are_observed(self, title, quantity) -> None:
        result = _extract(title)
        assert result.state is OBS
        assert result.established_kind is SalesUnitKindV2.TRAY_OR_FACTORY_PACK
        assert result.established_quantity == quantity
        _cue_state(
            result,
            [(SalesUnitKindV2.TRAY_OR_FACTORY_PACK, quantity, EST, None)],
        )
        channel = sui.sales_unit_channel_from_extraction(result)
        assert channel.kind is SalesUnitKindV2.TRAY_OR_FACTORY_PACK
        assert channel.quantity == quantity

    @pytest.mark.parametrize(
        "title, quantity",
        [
            ("3.84TB U.3 NVMe SSD, data center (tray)", None),
            ("OEM Tray of 10", 10),
            ("OEM Tray", None),
            ("tray of 20", 20),
        ],
        ids=["bare-tray", "oem-tray-of-n", "bare-oem-tray", "tray-of-n"],
    )
    def test_tray_phrases_are_observed_with_their_published_quantity(
        self, title, quantity
    ) -> None:
        result = _extract(title)
        assert result.state is OBS
        assert result.established_kind is SalesUnitKindV2.TRAY_OR_FACTORY_PACK
        # A tray with an unknown quantity is still an observation: the
        # quantity is absent (None), never invented.
        assert result.established_quantity == quantity
        _cue_state(
            result,
            [(SalesUnitKindV2.TRAY_OR_FACTORY_PACK, quantity, EST, None)],
        )
        channel = sui.sales_unit_channel_from_extraction(result)
        assert channel.state is PackagingEvidenceStateV2.OBSERVED
        assert channel.quantity == quantity

    def test_bundle_with_established_contents_and_quantity(self) -> None:
        # Q3-B5-P2-FU1 corrected contract (this node previously asserted
        # the reviewed defective contract): "bundle of 3" publishes the
        # bundle form + a count but NOT the composition. A published
        # count alone is not the complete identity of a bundle, so the
        # cue is ambiguous (BUNDLE_WITHOUT_CONTENTS), never established;
        # the count stays verbatim in the cue text and is never bound to
        # a quantity.
        result = _extract("bundle of 3 drives")
        assert result.state is AMB
        assert result.established_kind is None
        assert result.established_quantity is None
        _cue_state(
            result,
            [(SalesUnitKindV2.BUNDLE, None, AMBD, REASON.BUNDLE_WITHOUT_CONTENTS)],
        )
        assert result.cues[0].cue_text == "bundle of 3"
        channel = sui.sales_unit_channel_from_extraction(result)
        assert channel.state is PackagingEvidenceStateV2.UNAVAILABLE

    def test_bundle_contents_marker_records_the_published_contents(self) -> None:
        title = "bundle: 2x RAM + 1x CPU"
        result = _extract(title)
        assert result.state is OBS
        assert result.established_kind is SalesUnitKindV2.BUNDLE
        assert result.established_quantity is None
        cue = result.cues[0]
        assert cue.disposition is EST
        # The cue text is the verbatim published phrase INCLUDING the
        # contents clause (what the page says the bundle contains).
        assert cue.cue_text == "bundle: 2x RAM + 1x CPU"
        assert cue.raw_field_value[cue.cue_start : cue.cue_end] == cue.cue_text
        channel = sui.sales_unit_channel_from_extraction(result)
        assert channel.raw_detail == "bundle: 2x RAM + 1x CPU"

    def test_n_unit_bundle_phrases_are_observed(self) -> None:
        # Q3-B5-P2-FU1 corrected contract (this node previously asserted
        # the reviewed defective contract): "3-Unit Bundle" publishes a
        # bundle count WITHOUT the composition — ambiguous (observed
        # bundle form/count; composition unverified), never established.
        result = _extract("3-Unit Bundle")
        assert result.state is AMB
        assert result.established_kind is None
        assert result.established_quantity is None
        _cue_state(
            result,
            [(SalesUnitKindV2.BUNDLE, None, AMBD, REASON.BUNDLE_WITHOUT_CONTENTS)],
        )
        assert result.cues[0].cue_text == "3-Unit Bundle"
        channel = sui.sales_unit_channel_from_extraction(result)
        assert channel.state is PackagingEvidenceStateV2.UNAVAILABLE

    def test_structured_field_cue_is_observed_with_its_provenance(self) -> None:
        result = _extract("Plain SSD title", structured="Pack of 4")
        assert result.state is OBS
        assert result.established_kind is SalesUnitKindV2.PACK_QUANTITY
        assert result.established_quantity == 4
        cue = result.cues[0]
        assert cue.field is FIELD.STRUCTURED_PACKAGING_FIELD
        assert cue.source is CandidateEvidenceSourceV2.PUBLISHED_STRUCTURED_FIELD
        assert cue.raw_field_value == "Pack of 4"
        assert cue.cue_text == "Pack of 4"
        channel = sui.sales_unit_channel_from_extraction(result)
        assert channel.source is (
            CandidateEvidenceSourceV2.PUBLISHED_STRUCTURED_FIELD
        )
        assert channel.quantity == 4
        assert channel.raw_detail == "Pack of 4"

    def test_structured_field_and_title_corroboration_is_unambiguous(self) -> None:
        result = _extract("4-Pack SSD", structured="pack of 4")
        assert result.state is OBS
        assert result.established_kind is SalesUnitKindV2.PACK_QUANTITY
        assert result.established_quantity == 4
        assert len(result.cues) == 2
        # Both cues are recorded with their own provenance; the channel's
        # primary detail is the structured-field cue (the deliberately
        # published field precedes the raw title).
        fields = [c.field for c in result.cues]
        assert fields == [
            FIELD.STRUCTURED_PACKAGING_FIELD,
            FIELD.PRODUCT_TITLE,
        ]
        channel = sui.sales_unit_channel_from_extraction(result)
        assert channel.raw_detail == "pack of 4"
        assert channel.source is (
            CandidateEvidenceSourceV2.PUBLISHED_STRUCTURED_FIELD
        )

    def test_consistent_repeated_cues_are_unambiguous(self) -> None:
        result = _extract("Tray of 10 / Factory Pack of 10")
        assert result.state is OBS
        assert result.established_kind is SalesUnitKindV2.TRAY_OR_FACTORY_PACK
        assert result.established_quantity == 10
        assert len(result.cues) == 2

    def test_sentence_final_period_is_not_part_of_the_count(self) -> None:
        result = _extract("pack of 4. New arrival")
        assert result.state is OBS
        assert result.established_quantity == 4
        assert result.cues[0].cue_text == "pack of 4"


# ===========================================================================
# P2. SPECIFICATION QUANTITIES ARE NOT SALES QUANTITIES (false-positive
# resistance)
# ===========================================================================


class TestSpecificationQuantitiesAreNotSalesQuantities:
    @pytest.mark.parametrize(
        "title",
        [
            "4 TB SSD",
            "PM9A3 NVMe U.2 3.84TB",
            "960GB M.2 22110 NVMe Gen4",
        ],
        ids=["capacity-tb", "capacity-tb-attached", "capacity-gb"],
    )
    def test_capacity_values_are_not_pack_quantities(self, title) -> None:
        result = _extract(title)
        assert result.state is NONE_STATE
        assert result.cues == ()
        assert result.established_kind is None
        channel = sui.sales_unit_channel_from_extraction(result)
        assert channel.state is PackagingEvidenceStateV2.UNAVAILABLE

    @pytest.mark.parametrize(
        "title",
        ["2U rack mount SSD", "1U chassis, 4TB"],
        ids=["two-u", "one-u"],
    )
    def test_chassis_height_is_not_a_unit_count(self, title) -> None:
        result = _extract(title)
        assert result.state is NONE_STATE
        assert result.cues == ()

    def test_dual_port_networking_is_not_a_two_pack(self) -> None:
        result = _extract("BCM957608-P2200GQF00 - 400GbE Dual-Port QSFP112 PCI")
        assert result.state is NONE_STATE
        assert result.cues == ()

    @pytest.mark.parametrize(
        "title",
        [
            "8-channel memory module",
            "PCIe 4.0 x4 NVMe SSD",
            "3.84 TB SSD - 1 DWPD - 256-bit AES",
        ],
        ids=["8-channel", "x4-lanes", "1-dwpd"],
    )
    def test_channel_lane_and_wear_quantities_are_not_product_counts(
        self, title
    ) -> None:
        result = _extract(title)
        assert result.state is NONE_STATE
        assert result.cues == ()

    @pytest.mark.parametrize(
        "title",
        ["pack of 4TB", "tray of 2TiB", "bundle of 1GB"],
        ids=["tb-attached", "tib-attached", "gb-attached"],
    )
    def test_capacity_attached_counts_are_ambiguous_not_established(
        self, title
    ) -> None:
        result = _extract(title)
        assert result.state is AMB
        assert result.established_kind is None
        _cue_state(
            result,
            [
                (
                    {"pack": SalesUnitKindV2.PACK_QUANTITY,
                     "tray": SalesUnitKindV2.TRAY_OR_FACTORY_PACK,
                     "bundle": SalesUnitKindV2.BUNDLE}[
                        title.split()[0]
                    ],
                    None,
                    AMBD,
                    REASON.CAPACITY_ATTACHED_QUANTITY,
                )
            ],
        )
        channel = sui.sales_unit_channel_from_extraction(result)
        assert channel.state is PackagingEvidenceStateV2.UNAVAILABLE

    @pytest.mark.parametrize(
        "title",
        ["pack of 3.84", "pack of 04", "pack of 100000", "014-pack"],
        ids=["decimal", "leading-zero", "oversized", "leading-zero-n-pack"],
    )
    def test_non_canonical_counts_are_ambiguous_not_established(
        self, title
    ) -> None:
        result = _extract(title)
        assert result.state is AMB
        assert result.established_kind is None
        assert result.cues[0].reason is REASON.NON_CANONICAL_QUANTITY
        channel = sui.sales_unit_channel_from_extraction(result)
        assert channel.state is PackagingEvidenceStateV2.UNAVAILABLE

    def test_bare_pack_word_is_ambiguous_never_established(self) -> None:
        result = _extract("4TB SSD (pack)")
        assert result.state is AMB
        _cue_state(
            result,
            [(SalesUnitKindV2.PACK_QUANTITY, None, AMBD, REASON.PACK_WITHOUT_COUNT)],
        )
        channel = sui.sales_unit_channel_from_extraction(result)
        assert channel.state is PackagingEvidenceStateV2.UNAVAILABLE

    def test_bare_bundle_word_is_ambiguous_never_established(self) -> None:
        result = _extract("SSD bundle")
        assert result.state is AMB
        _cue_state(
            result,
            [(SalesUnitKindV2.BUNDLE, None, AMBD, REASON.BUNDLE_WITHOUT_CONTENTS)],
        )
        channel = sui.sales_unit_channel_from_extraction(result)
        assert channel.state is PackagingEvidenceStateV2.UNAVAILABLE

    @pytest.mark.parametrize(
        "title",
        [
            "2x Power Cable + Bracket Kit",
            "case of parts",
            "multipack",
            "Packard Bell SSD",
            "Packing material included",
            "4pack",
        ],
        ids=["kit", "case", "multipack", "packard", "packing", "glued-n-pack"],
    )
    def test_unbounded_words_are_not_cues(self, title) -> None:
        # "kit" / "case" / "multipack" / "Packard" / "Packing" / a glued
        # "4pack" carry no bounded packaging phrase: no cue at all.
        result = _extract(title)
        assert result.state is NONE_STATE
        assert result.cues == ()
        channel = sui.sales_unit_channel_from_extraction(result)
        assert channel.state is PackagingEvidenceStateV2.UNAVAILABLE

    def test_product_revision_numbers_are_not_quantities(self) -> None:
        # Revision / generation digits and an MPN-shaped suffix: no
        # packaging word is present anywhere, so nothing is a cue.
        result = _extract(
            "MTFDKCC3T8TGP-1BK1DABYY Gen 2 Rev A SSD",
            mpn="MTFDKCC3T8TGP-1BK1DABYY",
            sku="REV-2-001",
        )
        assert result.state is NONE_STATE
        assert result.cues == ()
        # The SKU's "REV" carries no packaging token; the MPN is set
        # aside only if a packaging-like token appears (none here).
        assert result.identifier_field_notes == ()
        channel = sui.sales_unit_channel_from_extraction(result)
        assert channel.state is PackagingEvidenceStateV2.UNAVAILABLE

    def test_two_digit_count_reads_whole(self) -> None:
        # "14-pack" is fourteen, not a leading "1" plus "4-pack".
        result = _extract("14-pack")
        assert result.state is OBS
        assert result.established_quantity == 14


# ===========================================================================
# P3. NEVER INFERRED (absence, exact MPN, one listing / price / image)
# ===========================================================================


class TestNeverInferred:
    def test_missing_packaging_is_a_recorded_absence_never_single_unit(
        self,
    ) -> None:
        # Exact MPN in the title, one price, one listing, no packaging
        # field: the unit is NOT inferred to be a single unit.
        result = _extract(
            "ABC-123 3.84TB NVMe SSD",
            mpn=None,
        )
        assert result.state is NONE_STATE
        assert result.established_kind is None
        channel = sui.sales_unit_channel_from_extraction(result)
        assert channel.state is PackagingEvidenceStateV2.UNAVAILABLE
        assert channel.kind is None
        assert channel.quantity is None
        assert channel.raw_detail is None
        assert channel.source is None

    def test_silent_multi_pack_with_exact_mpn_stays_unproven(self) -> None:
        """Adversarial row 1: a silent multi-pack publishes no cue at all.
        The extraction records the absence, the mapped channel stays
        UNAVAILABLE, and the FU3 derivation yields UNPROVEN (never
        PROVEN_EQUIVALENT) — the tier is capped under the separately
        versioned contract while the old token's replay is unchanged."""
        title = "Has ABC-123 in the title"
        result = _extract(title)
        assert result.state is NONE_STATE
        channel = sui.sales_unit_channel_from_extraction(result)
        assert channel is SALES_UNIT_EVIDENCE_UNAVAILABLE or (
            channel.state is PackagingEvidenceStateV2.UNAVAILABLE
        )
        assert (
            sales_unit_authority_from_channel(channel)
            is SalesUnitAuthorityV2.UNPROVEN
        )
        assessment_v2 = _u1_v2(title=title)
        old = derive_authority_tier_for_contract(
            AUTHORITY_CONTRACT_VERSION_V2, assessment_v2, _match(), frozenset(),
            _strong_profile(),
        )
        new = derive_authority_tier_for_contract(
            AUTHORITY_CONTRACT_VERSION_V2_FU3,
            assessment_v2,
            _match(),
            frozenset(),
            _strong_profile(),
            sales_unit_channel=channel,
        )
        # The old token's replay: unchanged (the R14 exposure, recorded).
        assert old.tier is AuthorityTier.AI_ASSISTED_COMPARABLE
        # The FU3 contract: the recorded absence caps the automatic tier.
        assert new.tier is AuthorityTier.NEEDS_REVIEW
        assert new.sales_unit_authority is SalesUnitAuthorityV2.UNPROVEN
        assert AuthorityRuleV2FU3.CEILING_SALES_UNIT_NOT_PROVEN in new.fired_rules

    def test_no_input_member_is_a_model_claim(self) -> None:
        import inspect

        parameters = set(
            inspect.signature(sui.extract_sales_unit_evidence).parameters
        )
        assert parameters == {"observation", "structured_packaging_text"}
        # The examined-field vocabulary has exactly the two published
        # positions — no model-claim member, no raw-reference member.
        assert {f.value for f in sui.SalesUnitCueField} == {
            "PRODUCT_TITLE",
            "STRUCTURED_PACKAGING_FIELD",
        }
        # The extractor's provenance sources are exactly the two frozen
        # non-model members.
        assert {
            sui._cue_source_for(f) for f in sui.SalesUnitCueField
        } == {
            CandidateEvidenceSourceV2.LISTING_TITLE,
            CandidateEvidenceSourceV2.PUBLISHED_STRUCTURED_FIELD,
        }

    def test_raw_reference_is_never_read(self) -> None:
        plain = _observation(title="4TB NVMe SSD")
        # A "pack of 4" inside the opaque raw reference is not an
        # examined field: no cue, and the digest does not bind it.
        with_reference = dataclasses.replace(
            plain, raw_reference='{"description": "pack of 4 special offer"}'
        )
        without_reference = dataclasses.replace(plain, raw_reference=None)
        result_ref = sui.extract_sales_unit_evidence(with_reference)
        result_plain = sui.extract_sales_unit_evidence(without_reference)
        assert result_ref.state is NONE_STATE
        assert result_ref.cues == ()
        assert result_ref.input_digest == result_plain.input_digest
        assert result_ref.result_digest == result_plain.result_digest
        # Identical results for identical named fields (determinism).
        assert result_ref == result_plain


# ===========================================================================
# P4. IDENTIFIER FIELDS ARE OUT OF SCOPE
# ===========================================================================


class TestIdentifierFieldsAreOutOfScope:
    def test_seller_sku_with_quantity_like_token_is_set_aside(self) -> None:
        result = _extract("4TB NVMe SSD", sku="4PACK-SSD-001")
        assert result.state is NONE_STATE
        assert result.established_kind is None
        # The SKU's packaging-like token is RECORDED (provenance that the
        # field was examined and deliberately not used), never a cue.
        assert result.identifier_field_notes == (
            sui.SalesUnitIdentifierFieldNoteV1(
                field_name="sku", token_text="PACK"
            ),
        )
        channel = sui.sales_unit_channel_from_extraction(result)
        assert channel.state is PackagingEvidenceStateV2.UNAVAILABLE

    def test_mpn_field_with_packaging_like_token_is_set_aside(self) -> None:
        result = _extract("4TB NVMe SSD", mpn="TRAY-10-MPN")
        assert result.state is NONE_STATE
        assert result.identifier_field_notes == (
            sui.SalesUnitIdentifierFieldNoteV1(
                field_name="mpn", token_text="TRAY"
            ),
        )
        channel = sui.sales_unit_channel_from_extraction(result)
        assert channel.state is PackagingEvidenceStateV2.UNAVAILABLE

    def test_identifier_notes_never_establish_a_unit(self) -> None:
        # Even with packaging-like tokens in BOTH identifier fields, the
        # state is the recorded absence and the channel is UNAVAILABLE:
        # an identifier token is never packaging evidence.
        result = _extract(
            "4TB NVMe SSD", sku="2-BUNDLE-001", mpn="FACTORY-PACK-9"
        )
        assert result.state is NONE_STATE
        assert result.established_kind is None
        assert result.established_quantity is None
        names = {n.field_name for n in result.identifier_field_notes}
        assert names == {"sku", "mpn"}
        channel = sui.sales_unit_channel_from_extraction(result)
        assert channel.state is PackagingEvidenceStateV2.UNAVAILABLE


# ===========================================================================
# P5. AMBIGUITY / CONTRADICTION REPRESENTATION
# ===========================================================================


class TestContradictionAndAmbiguityRepresentation:
    def test_conflicting_title_and_structured_packaging_is_contradicted(
        self,
    ) -> None:
        """Adversarial row: the structured field says single unit, the
        title says pack of four. Both sides are recorded with their full
        provenance; the frozen channel has no contradiction state, so the
        mapping is fail-closed (UNAVAILABLE) — neither side is presented
        as THE recorded unit."""
        result = _extract("ABC-123 SSD (pack of 4)", structured="Single Unit")
        assert result.state is CON
        assert result.established_kind is None
        assert result.established_quantity is None
        # Both established cues, each with its own source.
        by_field = {c.field: c for c in result.cues}
        assert set(by_field) == {
            FIELD.STRUCTURED_PACKAGING_FIELD,
            FIELD.PRODUCT_TITLE,
        }
        structured_cue = by_field[FIELD.STRUCTURED_PACKAGING_FIELD]
        title_cue = by_field[FIELD.PRODUCT_TITLE]
        assert structured_cue.kind is SalesUnitKindV2.SINGLE_UNIT
        assert structured_cue.source is (
            CandidateEvidenceSourceV2.PUBLISHED_STRUCTURED_FIELD
        )
        assert title_cue.kind is SalesUnitKindV2.PACK_QUANTITY
        assert title_cue.quantity == 4
        assert title_cue.source is CandidateEvidenceSourceV2.LISTING_TITLE
        # The fail-closed mapping: the recorded absence, not either side.
        channel = sui.sales_unit_channel_from_extraction(result)
        assert channel.state is PackagingEvidenceStateV2.UNAVAILABLE
        assert (
            sales_unit_authority_from_channel(channel)
            is SalesUnitAuthorityV2.UNPROVEN
        )

    def test_conflicting_kinds_in_one_title_are_contradicted(self) -> None:
        result = _extract("4-Pack / Tray of 10")
        assert result.state is CON
        kinds = {c.kind for c in result.cues}
        assert kinds == {
            SalesUnitKindV2.PACK_QUANTITY,
            SalesUnitKindV2.TRAY_OR_FACTORY_PACK,
        }
        channel = sui.sales_unit_channel_from_extraction(result)
        assert channel.state is PackagingEvidenceStateV2.UNAVAILABLE

    def test_conflicting_quantities_in_one_kind_are_contradicted(self) -> None:
        result = _extract("Tray of 10, Tray of 20")
        assert result.state is CON
        quantities = {c.quantity for c in result.cues}
        assert quantities == {10, 20}
        channel = sui.sales_unit_channel_from_extraction(result)
        assert channel.state is PackagingEvidenceStateV2.UNAVAILABLE

    def test_ambiguous_cue_of_another_kind_blocks_the_established_claim(
        self,
    ) -> None:
        # An established tray claim plus an unclassifiable bundle word:
        # the published unit is NOT unambiguously established.
        result = _extract("Tray of 10 (bundle)")
        assert result.state is AMB
        assert result.established_kind is None
        assert result.established_quantity is None
        dispositions = {c.disposition for c in result.cues}
        assert dispositions == {EST, AMBD}
        channel = sui.sales_unit_channel_from_extraction(result)
        assert channel.state is PackagingEvidenceStateV2.UNAVAILABLE

    def test_structured_field_without_vocabulary_blocks_the_established_claim(
        self,
    ) -> None:
        # The page published something in a packaging position ("4") that
        # carries no bounded vocabulary: an established title claim does
        # not make the published unit unambiguous.
        result = _extract("Tray of 10", structured="4")
        assert result.state is AMB
        assert result.established_kind is None
        ambiguous = [c for c in result.cues if c.disposition is AMBD]
        assert len(ambiguous) == 1
        assert ambiguous[0].reason is REASON.NO_PACKAGING_VOCABULARY
        assert ambiguous[0].kind is None
        channel = sui.sales_unit_channel_from_extraction(result)
        assert channel.state is PackagingEvidenceStateV2.UNAVAILABLE

    def test_same_kind_ambiguous_cue_is_subsumed_by_the_established_claim(
        self,
    ) -> None:
        # Q3-B5-P2-FU1 corrected contract (this node previously asserted
        # the reviewed defective contract): "4-Pack (pack)" — the bare
        # second "pack" word is an INDEPENDENT, unresolved ambiguous cue
        # of the established kind. Matching packaging kinds alone never
        # prove that it describes the same commercial unit (it could be
        # a further, nested pack), so it blocks the established claim.
        # Genuine subsumed duplicates are admitted only when their
        # relationship is deterministically proven by the exact published
        # spans (TestQ3B5P2FU1PackagingAmbiguityAndBundleIdentity).
        result = _extract("4-Pack (pack)")
        assert result.state is AMB
        assert result.established_kind is None
        assert result.established_quantity is None
        _cue_state(
            result,
            [
                (SalesUnitKindV2.PACK_QUANTITY, 4, EST, None),
                (SalesUnitKindV2.PACK_QUANTITY, None, AMBD, REASON.PACK_WITHOUT_COUNT),
            ],
        )
        # Every cue (established and ambiguous) is preserved with its
        # full provenance in the blocked result.
        assert len(result.cues) == 2
        channel = sui.sales_unit_channel_from_extraction(result)
        assert channel.state is PackagingEvidenceStateV2.UNAVAILABLE

    def test_state_vocabulary_is_bounded_to_exactly_four_states(self) -> None:
        assert {s.value for s in sui.SalesUnitExtractionState} == {
            "NO_PACKAGING_PUBLISHED",
            "OBSERVED_UNAMBIGUOUS",
            "AMBIGUOUS_CUE",
            "CONTRADICTED_CUES",
        }

    def test_disposition_and_reason_vocabularies_are_bounded(self) -> None:
        assert {d.value for d in sui.SalesUnitCueDisposition} == {
            "ESTABLISHED",
            "AMBIGUOUS",
        }
        assert {r.value for r in REASON} == {
            "PACK_WITHOUT_COUNT",
            "BUNDLE_WITHOUT_CONTENTS",
            "NON_CANONICAL_QUANTITY",
            "CAPACITY_ATTACHED_QUANTITY",
            "NO_PACKAGING_VOCABULARY",
        }


# ===========================================================================
# P6. PROVENANCE CONTRACT (determinism, binding, self-verification,
# anti-forgery)
# ===========================================================================


class TestProvenanceContract:
    def test_every_cue_records_full_provenance(self) -> None:
        title = "1.92TB M.2 NVMe SSD (pack of 4)"
        result = _extract(title)
        cue = result.cues[0]
        assert cue.field is FIELD.PRODUCT_TITLE
        assert cue.source is CandidateEvidenceSourceV2.LISTING_TITLE
        assert cue.raw_field_value == title
        assert cue.cue_text == "pack of 4"
        assert title[cue.cue_start : cue.cue_end] == "pack of 4"
        assert cue.cue_start == title.index("pack of 4")
        assert cue.cue_end == cue.cue_start + len("pack of 4")
        assert cue.kind is SalesUnitKindV2.PACK_QUANTITY
        assert cue.quantity == 4
        assert cue.disposition is EST
        assert cue.reason is None

    def test_a_cue_cannot_claim_text_its_field_never_published(self) -> None:
        with pytest.raises(ValueError, match="verbatim"):
            sui.SalesUnitCueV1(
                field=FIELD.PRODUCT_TITLE,
                source=CandidateEvidenceSourceV2.LISTING_TITLE,
                raw_field_value="4TB SSD",
                cue_text="pack of 9",
                cue_start=0,
                cue_end=9,
                kind=SalesUnitKindV2.PACK_QUANTITY,
                quantity=9,
                disposition=EST,
                reason=None,
            )

    @pytest.mark.parametrize(
        "source",
        [
            CandidateEvidenceSourceV2.SPECIFICATION_TEXT,
            CandidateEvidenceSourceV2.REVIEWED_PRODUCT_CONTEXT,
        ],
        ids=["specification-text", "reviewed-product-context"],
    )
    def test_a_cue_cannot_carry_a_foreign_provenance_source(self, source) -> None:
        # Forged / model-generated evidence has no representable source:
        # the extractor's cue provenance is exactly the two published
        # positions. No cue can present a specification-text or reviewed-
        # context source (and no member is a model claim).
        with pytest.raises(ValueError, match="provenance"):
            sui.SalesUnitCueV1(
                field=FIELD.PRODUCT_TITLE,
                source=source,
                raw_field_value="pack of 4",
                cue_text="pack of 4",
                cue_start=0,
                cue_end=9,
                kind=SalesUnitKindV2.PACK_QUANTITY,
                quantity=4,
                disposition=EST,
                reason=None,
            )

    def test_the_input_digest_binds_the_exact_examined_input(self) -> None:
        base = _extract("4TB SSD")
        assert base.input_digest != _extract("4TB SSD 2-Pack").input_digest
        assert base.input_digest != _extract(
            "4TB SSD", sku="X-1"
        ).input_digest
        assert base.input_digest != _extract("4TB SSD", structured="pack").input_digest
        assert base.input_digest != _extract(
            "4TB SSD", mpn="MPN-1"
        ).input_digest
        # Identical named fields -> identical digest (determinism).
        assert base.input_digest == _extract("4TB SSD").input_digest

    def test_the_result_is_deterministic_and_immutable(self) -> None:
        first = _extract("Tray of 10, pack of 4")
        second = _extract("Tray of 10, pack of 4")
        assert first == second
        assert first.result_digest == second.result_digest
        assert json.dumps(first.canonical(), sort_keys=True) == json.dumps(
            second.canonical(), sort_keys=True
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            first.state = NONE_STATE  # type: ignore[misc]

    def test_mapping_refuses_a_tampered_result(self) -> None:
        result = _extract("pack of 4")
        # The untampered result maps cleanly.
        channel = sui.sales_unit_channel_from_extraction(result)
        assert channel.state is PackagingEvidenceStateV2.OBSERVED
        # Tamper with the state (a forged result presented downstream):
        # the self-verification gate refuses it before any mapping.
        object.__setattr__(result, "state", NONE_STATE)
        with pytest.raises(sui.SalesUnitExtractionIntegrityError):
            result.verify_integrity()
        with pytest.raises(sui.SalesUnitExtractionIntegrityError):
            sui.sales_unit_channel_from_extraction(result)

    @pytest.mark.parametrize(
        "kwargs",
        [
            # Established cue carrying an ambiguity reason.
            dict(
                kind=SalesUnitKindV2.PACK_QUANTITY,
                quantity=4,
                disposition=EST,
                reason=REASON.PACK_WITHOUT_COUNT,
            ),
            # Ambiguous cue without a reason.
            dict(
                kind=SalesUnitKindV2.PACK_QUANTITY,
                quantity=None,
                disposition=AMBD,
                reason=None,
            ),
            # Ambiguous cue carrying a salvaged quantity.
            dict(
                kind=SalesUnitKindV2.PACK_QUANTITY,
                quantity=4,
                disposition=AMBD,
                reason=REASON.NON_CANONICAL_QUANTITY,
            ),
            # Established single unit carrying a quantity.
            dict(
                kind=SalesUnitKindV2.SINGLE_UNIT,
                quantity=1,
                disposition=EST,
                reason=None,
            ),
        ],
        ids=[
            "established-with-reason",
            "ambiguous-without-reason",
            "ambiguous-with-quantity",
            "single-with-quantity",
        ],
    )
    def test_cue_construction_is_fail_closed(self, kwargs) -> None:
        with pytest.raises((ValueError, TypeError)):
            sui.SalesUnitCueV1(
                field=FIELD.PRODUCT_TITLE,
                source=CandidateEvidenceSourceV2.LISTING_TITLE,
                raw_field_value="pack of 4",
                cue_text="pack of 4",
                cue_start=0,
                cue_end=9,
                **kwargs,
            )

    def test_a_forged_observed_result_without_consistent_cues_is_unconstructible(
        self,
    ) -> None:
        digest = "0" * 64
        # OBSERVED with no cues at all.
        with pytest.raises(ValueError):
            sui.SalesUnitExtractionResult(
                schema_version=1,
                state=OBS,
                cues=(),
                identifier_field_notes=(),
                established_kind=SalesUnitKindV2.PACK_QUANTITY,
                established_quantity=4,
                input_digest=digest,
                result_digest=digest,
            )
        # CONTRADICTED with a single established kind and quantity.
        cue = sui.SalesUnitCueV1(
            field=FIELD.PRODUCT_TITLE,
            source=CandidateEvidenceSourceV2.LISTING_TITLE,
            raw_field_value="pack of 4",
            cue_text="pack of 4",
            cue_start=0,
            cue_end=9,
            kind=SalesUnitKindV2.PACK_QUANTITY,
            quantity=4,
            disposition=EST,
            reason=None,
        )
        with pytest.raises(ValueError):
            sui.SalesUnitExtractionResult(
                schema_version=1,
                state=CON,
                cues=(cue,),
                identifier_field_notes=(),
                established_kind=None,
                established_quantity=None,
                input_digest=digest,
                result_digest=digest,
            )
        # A non-OBSERVED state claiming an established unit.
        with pytest.raises(ValueError):
            sui.SalesUnitExtractionResult(
                schema_version=1,
                state=NONE_STATE,
                cues=(),
                identifier_field_notes=(),
                established_kind=SalesUnitKindV2.SINGLE_UNIT,
                established_quantity=None,
                input_digest=digest,
                result_digest=digest,
            )
        # An unknown schema version.
        with pytest.raises(ValueError):
            sui.SalesUnitExtractionResult(
                schema_version=9,
                state=NONE_STATE,
                cues=(),
                identifier_field_notes=(),
                established_kind=None,
                established_quantity=None,
                input_digest=digest,
                result_digest=digest,
            )

    def test_extraction_entry_point_fails_closed_on_foreign_inputs(self) -> None:
        with pytest.raises(TypeError):
            sui.extract_sales_unit_evidence("not an observation")  # type: ignore[arg-type]
        with pytest.raises(TypeError):
            sui.extract_sales_unit_evidence(_observation(), 42)  # type: ignore[arg-type]
        with pytest.raises(ValueError):
            sui.extract_sales_unit_evidence(_observation(), "   ")
        with pytest.raises(TypeError):
            sui.sales_unit_channel_from_extraction("not a result")  # type: ignore[arg-type]


# ===========================================================================
# P5b. MULTIPLE OFFERS (one observation = one offer; no cross-contamination)
# ===========================================================================


class TestMultipleOffers:
    def test_multiple_offers_with_different_units_extract_independently(
        self,
    ) -> None:
        offer_a = _observation(
            title="PM9A3 3.84TB (pack of 4)",
            source_url="https://example.com/shop",
            offer_url="/offer/a",
        )
        offer_b = _observation(
            title="PM9A3 3.84TB single unit",
            source_url="https://example.com/shop",
            offer_url="/offer/b",
        )
        result_a = sui.extract_sales_unit_evidence(offer_a)
        result_b = sui.extract_sales_unit_evidence(offer_b)
        assert result_a.state is OBS
        assert result_a.established_kind is SalesUnitKindV2.PACK_QUANTITY
        assert result_a.established_quantity == 4
        assert result_b.state is OBS
        assert result_b.established_kind is SalesUnitKindV2.SINGLE_UNIT
        # Each result is bound to its own offer (distinct digests) and its
        # own published field values (no cross-contamination).
        assert result_a.input_digest != result_b.input_digest
        assert result_a.cues[0].raw_field_value == "PM9A3 3.84TB (pack of 4)"
        assert result_b.cues[0].raw_field_value == "PM9A3 3.84TB single unit"
        channel_a = sui.sales_unit_channel_from_extraction(result_a)
        channel_b = sui.sales_unit_channel_from_extraction(result_b)
        assert channel_a.quantity == 4
        assert channel_b.kind is SalesUnitKindV2.SINGLE_UNIT

    def test_one_observation_is_one_offer(self) -> None:
        import inspect

        # The component's contract is one offer in, one result out: there
        # is no batch parameter by which offers could be mixed.
        signature = inspect.signature(sui.extract_sales_unit_evidence)
        assert list(signature.parameters) == [
            "observation",
            "structured_packaging_text",
        ]
        assert not isinstance(
            signature.parameters["observation"].default, tuple
        )


# ===========================================================================
# P7. FU3 PROVEN / UNPROVEN / CONTRADICTED INTERACTION
# ===========================================================================


class TestFu3Interaction:
    def test_extracted_single_unit_proves_equivalence_under_fu3(self) -> None:
        channel = _channel("Single Unit")
        assert channel.state is PackagingEvidenceStateV2.OBSERVED
        # Against the default single-unit target: proven.
        assert (
            sales_unit_authority_from_channel(channel)
            is SalesUnitAuthorityV2.PROVEN_EQUIVALENT
        )
        # Against an established pack target: the published incompatible
        # unit is contradicted.
        assert (
            sales_unit_authority_from_channel(
                channel, _target(TargetSalesUnitFormV2.PACK_QUANTITY, 4)
            )
            is SalesUnitAuthorityV2.CONTRADICTED
        )

    def test_extracted_pack_of_four_contradicts_the_default_target(self) -> None:
        channel = _channel("pack of 4")
        assert (
            sales_unit_authority_from_channel(channel)
            is SalesUnitAuthorityV2.CONTRADICTED
        )
        # The same published pack against a target-side established pack
        # of the same count: proven (both sides recorded, equal counts).
        assert (
            sales_unit_authority_from_channel(
                channel, _target(TargetSalesUnitFormV2.PACK_QUANTITY, 4)
            )
            is SalesUnitAuthorityV2.PROVEN_EQUIVALENT
        )
        assert (
            sales_unit_authority_from_channel(
                channel, _target(TargetSalesUnitFormV2.PACK_QUANTITY, 2)
            )
            is SalesUnitAuthorityV2.CONTRADICTED
        )

    def test_extracted_tray_and_bundle_forms(self) -> None:
        tray_10 = _channel("Tray of 10")
        tray_none = _channel("(tray)")
        bundle_3 = _channel("bundle of 3")
        # A published tray / bundle is not the default single unit.
        assert (
            sales_unit_authority_from_channel(tray_10)
            is SalesUnitAuthorityV2.CONTRADICTED
        )
        assert (
            sales_unit_authority_from_channel(tray_none)
            is SalesUnitAuthorityV2.CONTRADICTED
        )
        # Matching form, equal published quantities on both sides: proven.
        assert (
            sales_unit_authority_from_channel(
                tray_10, _target(TargetSalesUnitFormV2.TRAY_OR_FACTORY_PACK, 10)
            )
            is SalesUnitAuthorityV2.PROVEN_EQUIVALENT
        )
        # Q3-B5-P2-FU1 corrected contract (this node previously asserted
        # the reviewed defective contract, where "bundle of 3" mapped to
        # an OBSERVED BUNDLE quantity-3 channel and PROVED equivalence
        # against a target-side bundle of the same count): a count-only
        # bundle publishes no established unit (the composition is
        # unverified), so its mapped channel is the recorded absence —
        # UNPROVEN for EVERY target shape, including a target-side
        # bundle of the same count.
        assert bundle_3.state is PackagingEvidenceStateV2.UNAVAILABLE
        assert (
            sales_unit_authority_from_channel(bundle_3)
            is SalesUnitAuthorityV2.UNPROVEN
        )
        assert (
            sales_unit_authority_from_channel(
                bundle_3, _target(TargetSalesUnitFormV2.BUNDLE, 3)
            )
            is SalesUnitAuthorityV2.UNPROVEN
        )
        # The material quantity unverified on one side: unproven.
        assert (
            sales_unit_authority_from_channel(
                tray_10, _target(TargetSalesUnitFormV2.TRAY_OR_FACTORY_PACK)
            )
            is SalesUnitAuthorityV2.UNPROVEN
        )
        assert (
            sales_unit_authority_from_channel(
                tray_none, _target(TargetSalesUnitFormV2.TRAY_OR_FACTORY_PACK, 10)
            )
            is SalesUnitAuthorityV2.UNPROVEN
        )

    @pytest.mark.parametrize(
        "title, structured",
        [
            ("4TB SSD", None),  # no packaging published
            ("pack", None),  # ambiguous
            ("Tray of 10 (bundle)", None),  # blocked ambiguous
            ("pack of 4", "Single Unit"),  # contradicted
            ("bundle of 3", None),  # count-only bundle: composition unverified
        ],
        ids=[
            "missing",
            "ambiguous",
            "blocked-ambiguous",
            "contradicted",
            "count-only-bundle",
        ],
    )
    def test_non_observed_states_are_never_proven_for_any_target(
        self, title, structured
    ) -> None:
        channel = _channel(title, structured=structured)
        assert channel.state is PackagingEvidenceStateV2.UNAVAILABLE
        targets = [
            None,
            _target(TargetSalesUnitFormV2.SINGLE_UNIT),
            _target(TargetSalesUnitFormV2.PACK_QUANTITY, 4),
            _target(TargetSalesUnitFormV2.TRAY_OR_FACTORY_PACK, 10),
            _target(TargetSalesUnitFormV2.BUNDLE, 3),
        ]
        for target in targets:
            assert (
                sales_unit_authority_from_channel(channel, target)
                is SalesUnitAuthorityV2.UNPROVEN
            ), target

    def test_fu3_tier_interaction_match_high_strong(self) -> None:
        """The §4.1 composition over extractor-derived channels:
        MATCH + HIGH + STRONG, U1 exact-identifier shape. The proven unit
        stands; the published incompatible unit never auto-prices; the
        recorded absence / ambiguity / contradiction stays unproven and
        capped."""
        assessment_v2 = _u1_v2()
        proven = derive_authority_tier_for_contract(
            AUTHORITY_CONTRACT_VERSION_V2_FU3,
            assessment_v2,
            _match(),
            frozenset(),
            _strong_profile(),
            sales_unit_channel=_channel("Single Unit"),
        )
        assert proven.tier is AuthorityTier.AI_ASSISTED_COMPARABLE
        assert proven.sales_unit_authority is SalesUnitAuthorityV2.PROVEN_EQUIVALENT
        assert AuthorityRuleV2FU3.CEILING_SALES_UNIT_NOT_PROVEN not in proven.fired_rules
        assert AuthorityRuleV2FU3.CEILING_SALES_UNIT_CONTRADICTED not in proven.fired_rules

        contradicted = derive_authority_tier_for_contract(
            AUTHORITY_CONTRACT_VERSION_V2_FU3,
            assessment_v2,
            _match(),
            frozenset(),
            _strong_profile(),
            sales_unit_channel=_channel("pack of 4"),
        )
        assert contradicted.tier is AuthorityTier.NEEDS_REVIEW
        assert contradicted.sales_unit_authority is SalesUnitAuthorityV2.CONTRADICTED
        assert AuthorityRuleV2FU3.CEILING_SALES_UNIT_CONTRADICTED in (
            contradicted.fired_rules
        )
        assert AuthorityRuleV2FU3.CEILING_SALES_UNIT_NOT_PROVEN not in (
            contradicted.fired_rules
        )

        unproven = derive_authority_tier_for_contract(
            AUTHORITY_CONTRACT_VERSION_V2_FU3,
            assessment_v2,
            _match(),
            frozenset(),
            _strong_profile(),
            sales_unit_channel=_channel("4TB SSD"),
        )
        assert unproven.tier is AuthorityTier.NEEDS_REVIEW
        assert unproven.sales_unit_authority is SalesUnitAuthorityV2.UNPROVEN
        assert AuthorityRuleV2FU3.CEILING_SALES_UNIT_NOT_PROVEN in unproven.fired_rules

        # A candidate-INTERNAL contradiction is not a published
        # incompatible unit against the target: it stays UNPROVEN (the
        # contradiction rule never fires from it).
        internal = derive_authority_tier_for_contract(
            AUTHORITY_CONTRACT_VERSION_V2_FU3,
            assessment_v2,
            _match(),
            frozenset(),
            _strong_profile(),
            sales_unit_channel=_channel("pack of 4", structured="Single Unit"),
        )
        assert internal.tier is AuthorityTier.NEEDS_REVIEW
        assert internal.sales_unit_authority is SalesUnitAuthorityV2.UNPROVEN
        assert AuthorityRuleV2FU3.CEILING_SALES_UNIT_NOT_PROVEN in internal.fired_rules
        assert AuthorityRuleV2FU3.CEILING_SALES_UNIT_CONTRADICTED not in (
            internal.fired_rules
        )

    def test_old_token_replay_is_unchanged_by_the_extractor(self) -> None:
        assessment_v2 = _u1_v2()
        # The frozen contract has no sales-unit input: passing one is
        # contract misuse (the extractor never reinterprets old records).
        with pytest.raises(ValueError, match="no sales-unit input"):
            derive_authority_tier_for_contract(
                AUTHORITY_CONTRACT_VERSION_V2,
                assessment_v2,
                _match(),
                frozenset(),
                _strong_profile(),
                sales_unit_channel=_channel("pack of 4"),
            )
        old = derive_authority_tier_for_contract(
            AUTHORITY_CONTRACT_VERSION_V2,
            assessment_v2,
            _match(),
            frozenset(),
            _strong_profile(),
        )
        assert old.tier is AuthorityTier.AI_ASSISTED_COMPARABLE

    def test_case_level_recorded_input_accepts_the_extracted_channel(self) -> None:
        """Recorded input construction: the frozen chain builds the case;
        the separately gated integration replaces ONLY the channel (the
        dataclasses.replace shape a future versioned input builder would
        use); the FU3 case-level derivation reads exactly that channel."""
        normalized = normalize_listing_observation(
            _observation(title="Has ABC-123 in the title")
        )
        assessment = assess_listing_identity(REQUEST, normalized)
        context = derive_identity_state_v2(assessment)
        profile = build_v2_product_evidence_profile(
            observation=assessment.normalized_listing.observation,
            context_provenances=frozenset(),
            matched_facts=frozenset(),
        )
        case = build_semantic_match_case_v2(
            case_id="p2-gated-0",
            request=REQUEST,
            assessment=assessment,
            context=context,
            product_evidence=profile,
            context_provenances=frozenset(),
            reviewed_target_context=None,
        )
        # The frozen live builder's channel: the recorded absence.
        assert case.candidate_commercial.sales_unit.state is (
            PackagingEvidenceStateV2.UNAVAILABLE
        )
        assert fu3.derive_sales_unit_authority(case) is SalesUnitAuthorityV2.UNPROVEN
        # The gated integration shape: the extracted channel replaces the
        # frozen one; every other section of the recorded input is the
        # frozen builder's.
        extracted = _channel("pack of 4")
        replaced = dataclasses.replace(
            case,
            candidate_commercial=dataclasses.replace(
                case.candidate_commercial, sales_unit=extracted
            ),
        )
        assert isinstance(replaced, SemanticMatchCaseV2)
        assert replaced.candidate_commercial.sales_unit.state is (
            PackagingEvidenceStateV2.OBSERVED
        )
        assert fu3.derive_sales_unit_authority(replaced) is (
            SalesUnitAuthorityV2.CONTRADICTED
        )

    def test_extracted_evidence_never_reaches_the_authority_side(self) -> None:
        import inspect

        # The authority-side profile builder has no extraction input: the
        # parameters are the frozen ones (observation, provenances,
        # matched facts).
        parameters = set(
            inspect.signature(build_v2_product_evidence_profile).parameters
        )
        assert parameters == {
            "observation",
            "context_provenances",
            "matched_facts",
        }
        # An observation with a loud packaging cue still grounds no
        # matched fact: the authority profile is unchanged (with the
        # live matched_facts=frozenset(), quality stays at most
        # LIMITED — the cue is commercial evidence, never a product fact).
        profile = build_v2_product_evidence_profile(
            observation=_observation(title="pack of 4 ABC-123 SSD"),
            context_provenances=frozenset(),
            matched_facts=frozenset(),
        )
        assert profile.matched_facts == frozenset()
        from product_intelligence.research import derive_product_evidence_quality

        assert derive_product_evidence_quality(profile, frozenset()) in (
            ProductEvidenceQuality.LIMITED,
            ProductEvidenceQuality.WEAK,
        )
        # The mapped channel is commercial observation evidence: it
        # carries no authority-side source member and grants nothing.
        channel = _channel("pack of 4")
        assert channel.source in (
            CandidateEvidenceSourceV2.LISTING_TITLE,
            CandidateEvidenceSourceV2.PUBLISHED_STRUCTURED_FIELD,
        )


# ===========================================================================
# P7-FU1. Q3-B5-P2-FU1 — Packaging ambiguity and bundle identity
# correction (mandated regression matrix over the independent source
# review)
# ===========================================================================


class TestQ3B5P2FU1PackagingAmbiguityAndBundleIdentity:
    """The Q3-B5-P2-FU1 corrected contract:

    * an independently unresolved ambiguous cue — of ANY kind, including
      the established kind — prevents OBSERVED_UNAMBIGUOUS (matching
      packaging kinds alone never prove that the ambiguous cue describes
      the same commercial unit);
    * a genuine duplicate / subsumed cue is admitted only when its
      relationship is deterministically proven by the exact published
      spans (the documented subsumption rule), enforced identically by
      the state resolution and the result constructor;
    * a published bundle count is NOT the complete identity of a bundle
      (observed form/count vs verified composition): a count-only bundle
      is ambiguous, never established, and the frozen FU3 derivation is
      never PROVEN for it — including against a target-side bundle of
      the same count.
    """

    # -- Blocker 1: ambiguous cues must prevent OBSERVED_UNAMBIGUOUS ----

    def test_pack_of_four_plus_unresolved_pack_blocks_observed(self) -> None:
        """Mandated regression 1: an established "pack of 4" plus an
        unresolved bare "pack" of the same kind. The independent bare
        pack is not proven to describe the same commercial unit — the
        established claim is blocked, every cue is preserved with its
        full provenance, and the channel fails closed to the recorded
        absence (FU3: UNPROVEN for every target shape)."""
        result = _extract("1.92TB M.2 SSD, pack of 4 (pack)")
        assert result.state is AMB
        assert result.established_kind is None
        assert result.established_quantity is None
        _cue_state(
            result,
            [
                (SalesUnitKindV2.PACK_QUANTITY, 4, EST, None),
                (SalesUnitKindV2.PACK_QUANTITY, None, AMBD, REASON.PACK_WITHOUT_COUNT),
            ],
        )
        channel = sui.sales_unit_channel_from_extraction(result)
        assert channel.state is PackagingEvidenceStateV2.UNAVAILABLE
        for target in (
            None,
            _target(TargetSalesUnitFormV2.PACK_QUANTITY, 4),
            _target(TargetSalesUnitFormV2.SINGLE_UNIT),
        ):
            assert (
                sales_unit_authority_from_channel(channel, target)
                is SalesUnitAuthorityV2.UNPROVEN
            ), target

    def test_pack_of_four_plus_pack_of_eight_is_contradicted(self) -> None:
        """Mandated regression 2: two established cues of the same kind
        publish incompatible counts — every side is recorded with its
        full provenance; the channel is the fail-closed recorded absence
        (a candidate-internal contradiction stays UNPROVEN, never
        CONTRADICTED at the derivation level, never proven)."""
        result = _extract("SSD pack of 4 ... pack of 8")
        assert result.state is CON
        assert result.established_kind is None
        assert result.established_quantity is None
        _cue_state(
            result,
            [
                (SalesUnitKindV2.PACK_QUANTITY, 4, EST, None),
                (SalesUnitKindV2.PACK_QUANTITY, 8, EST, None),
            ],
        )
        channel = sui.sales_unit_channel_from_extraction(result)
        assert channel.state is PackagingEvidenceStateV2.UNAVAILABLE
        for target in (
            None,
            _target(TargetSalesUnitFormV2.PACK_QUANTITY, 4),
            _target(TargetSalesUnitFormV2.PACK_QUANTITY, 8),
        ):
            assert (
                sales_unit_authority_from_channel(channel, target)
                is SalesUnitAuthorityV2.UNPROVEN
            ), target

    def test_exact_duplicate_pack_of_four_cues_are_observed(self) -> None:
        """Mandated regression 3: the exact repeated publication of the
        same established claim ("pack of 4" twice) is a consistent
        repetition — still OBSERVED_UNAMBIGUOUS with both cues recorded,
        the channel is OBSERVED, and FU3 proves it against a target-side
        pack of the same count (contradicts a different one)."""
        result = _extract("pack of 4, pack of 4")
        assert result.state is OBS
        assert result.established_kind is SalesUnitKindV2.PACK_QUANTITY
        assert result.established_quantity == 4
        _cue_state(
            result,
            [
                (SalesUnitKindV2.PACK_QUANTITY, 4, EST, None),
                (SalesUnitKindV2.PACK_QUANTITY, 4, EST, None),
            ],
        )
        channel = sui.sales_unit_channel_from_extraction(result)
        assert channel.state is PackagingEvidenceStateV2.OBSERVED
        assert channel.quantity == 4
        assert (
            sales_unit_authority_from_channel(
                channel, _target(TargetSalesUnitFormV2.PACK_QUANTITY, 4)
            )
            is SalesUnitAuthorityV2.PROVEN_EQUIVALENT
        )
        assert (
            sales_unit_authority_from_channel(
                channel, _target(TargetSalesUnitFormV2.PACK_QUANTITY, 8)
            )
            is SalesUnitAuthorityV2.CONTRADICTED
        )

    def test_structured_packaging_conflicting_with_title_reverse_roles(
        self,
    ) -> None:
        """Mandated regression 4 (reverse roles over the existing
        title-contradiction node): the structured field says pack of
        four, the title says single unit. Both sides are recorded with
        their own provenance; the channel is the fail-closed recorded
        absence, never either side."""
        result = _extract("ABC-123 SSD single unit", structured="pack of 4")
        assert result.state is CON
        assert result.established_kind is None
        assert result.established_quantity is None
        by_field = {c.field: c for c in result.cues}
        assert set(by_field) == {
            FIELD.STRUCTURED_PACKAGING_FIELD,
            FIELD.PRODUCT_TITLE,
        }
        structured_cue = by_field[FIELD.STRUCTURED_PACKAGING_FIELD]
        title_cue = by_field[FIELD.PRODUCT_TITLE]
        assert structured_cue.kind is SalesUnitKindV2.PACK_QUANTITY
        assert structured_cue.quantity == 4
        assert structured_cue.source is (
            CandidateEvidenceSourceV2.PUBLISHED_STRUCTURED_FIELD
        )
        assert title_cue.kind is SalesUnitKindV2.SINGLE_UNIT
        assert title_cue.source is CandidateEvidenceSourceV2.LISTING_TITLE
        channel = sui.sales_unit_channel_from_extraction(result)
        assert channel.state is PackagingEvidenceStateV2.UNAVAILABLE
        assert (
            sales_unit_authority_from_channel(channel)
            is SalesUnitAuthorityV2.UNPROVEN
        )

    def test_same_kind_noncanonical_quantity_cue_blocks_observed(self) -> None:
        # The Blocker-1 rule is not pack-specific: an independent
        # non-canonical quantity cue of the established kind also blocks
        # the established claim (matching packaging kinds never prove
        # the ambiguous cue describes the same commercial unit).
        result = _extract("Tray of 10, tray of 10.5")
        assert result.state is AMB
        assert result.established_kind is None
        assert result.established_quantity is None
        _cue_state(
            result,
            [
                (SalesUnitKindV2.TRAY_OR_FACTORY_PACK, 10, EST, None),
                (
                    SalesUnitKindV2.TRAY_OR_FACTORY_PACK,
                    None,
                    AMBD,
                    REASON.NON_CANONICAL_QUANTITY,
                ),
            ],
        )
        channel = sui.sales_unit_channel_from_extraction(result)
        assert channel.state is PackagingEvidenceStateV2.UNAVAILABLE

    # -- The documented subsumed-duplicate rule --------------------------

    @staticmethod
    def _hand_cue(
        raw: str,
        start: int,
        end: int,
        kind: SalesUnitKindV2,
        quantity: int | None,
        disposition: sui.SalesUnitCueDisposition,
        reason: sui.SalesUnitCueReason | None = None,
        field: sui.SalesUnitCueField = FIELD.PRODUCT_TITLE,
    ) -> sui.SalesUnitCueV1:
        source = (
            CandidateEvidenceSourceV2.LISTING_TITLE
            if field is FIELD.PRODUCT_TITLE
            else CandidateEvidenceSourceV2.PUBLISHED_STRUCTURED_FIELD
        )
        return sui.SalesUnitCueV1(
            field=field,
            source=source,
            raw_field_value=raw,
            cue_text=raw[start:end],
            cue_start=start,
            cue_end=end,
            kind=kind,
            quantity=quantity,
            disposition=disposition,
            reason=reason,
        )

    def _hand_result(
        self,
        state: sui.SalesUnitExtractionState,
        cues: list[sui.SalesUnitCueV1],
        kind: SalesUnitKindV2 | None = None,
        quantity: int | None = None,
    ) -> sui.SalesUnitExtractionResult:
        """A hand-built result with the correct result digest over the
        canonical (sorted) cue order — proves the constructor-level
        safety rule directly, independent of the scan engine."""
        ordered = tuple(
            sorted(
                cues,
                key=lambda c: (
                    list(FIELD).index(c.field),
                    c.cue_start,
                    c.cue_end,
                ),
            )
        )
        input_digest = "0" * 64
        return sui.SalesUnitExtractionResult(
            schema_version=1,
            state=state,
            cues=ordered,
            identifier_field_notes=(),
            established_kind=kind,
            established_quantity=quantity,
            input_digest=input_digest,
            result_digest=sui._result_digest(
                1, state, ordered, (), kind, quantity, input_digest
            ),
        )

    def test_constructor_rejects_independent_same_kind_ambiguous_cue(
        self,
    ) -> None:
        # The result constructor validates the SAME safety rule as state
        # resolution: a hand-built OBSERVED result whose ambiguous cue is
        # an independent published occurrence (a separate span) of the
        # established kind is un-constructible.
        raw = "4-Pack (pack)"
        est = self._hand_cue(
            raw, 0, 6, SalesUnitKindV2.PACK_QUANTITY, 4, EST
        )
        ind = self._hand_cue(
            raw,
            8,
            12,
            SalesUnitKindV2.PACK_QUANTITY,
            None,
            AMBD,
            REASON.PACK_WITHOUT_COUNT,
        )
        with pytest.raises(ValueError, match="subsumed-duplicate"):
            self._hand_result(OBS, [est, ind], SalesUnitKindV2.PACK_QUANTITY, 4)
        # The same cues ARE constructible under AMBIGUOUS_CUE (blocked,
        # every side recorded) — provenance is preserved, never dropped.
        result = self._hand_result(AMB, [est, ind])
        assert len(result.cues) == 2

    def test_constructor_admits_exact_span_proven_subsumed_cue(self) -> None:
        # The documented subsumption rule: an ambiguous cue is a genuine
        # duplicate / subsumed cue of the established claim only when its
        # relationship is deterministically proven by the exact published
        # spans (same examined field, span contained in the established
        # cue's span, same kind — a fragment of the same published
        # phrase). The constructor admits exactly that shape.
        raw = "bundle: 2x RAM + 1x CPU"
        est = self._hand_cue(raw, 0, len(raw), SalesUnitKindV2.BUNDLE, None, EST)
        sub = self._hand_cue(
            raw,
            0,
            6,
            SalesUnitKindV2.BUNDLE,
            None,
            AMBD,
            REASON.BUNDLE_WITHOUT_CONTENTS,
        )
        result = self._hand_result(OBS, [est, sub], SalesUnitKindV2.BUNDLE, None)
        assert result.state is OBS
        assert len(result.cues) == 2
        # The scan engine's ordered alternatives never emit an
        # overlapping pair, so no extracted result depends on this path:
        # it is the documented, deterministically proven rule only.

    @pytest.mark.parametrize(
        ("start", "end", "field", "kind"),
        [
            (17, 23, FIELD.PRODUCT_TITLE, SalesUnitKindV2.BUNDLE),
            (0, 6, FIELD.STRUCTURED_PACKAGING_FIELD, SalesUnitKindV2.BUNDLE),
            (0, 6, FIELD.PRODUCT_TITLE, SalesUnitKindV2.PACK_QUANTITY),
        ],
        ids=["non-contained-span", "different-field", "different-kind"],
    )
    def test_constructor_rejects_unproven_subsumption_shapes(
        self, start, end, field, kind
    ) -> None:
        # Subsumption is proven ONLY by the exact published spans: a
        # non-contained span, a different examined field, or a different
        # kind is never a subsumed duplicate — the OBSERVED result is
        # un-constructible.
        raw = "bundle: 2x RAM. bundle"
        est = self._hand_cue(raw, 0, 14, SalesUnitKindV2.BUNDLE, None, EST)
        bad = self._hand_cue(
            raw, start, end, kind, None, AMBD, REASON.BUNDLE_WITHOUT_CONTENTS,
            field=field,
        )
        with pytest.raises((ValueError, TypeError)):
            self._hand_result(OBS, [est, bad], SalesUnitKindV2.BUNDLE, None)

    # -- Blocker 2: bundle form/count vs verified composition -----------

    def test_bundle_of_three_without_contents(self) -> None:
        """Mandated regression 5: "bundle of 3" — a published count, no
        published contents. The observed bundle form/count is not the
        verified bundle composition: the cue is ambiguous (never
        established), the count is never bound to a quantity, the
        channel is the recorded absence, and the frozen FU3 derivation
        is UNPROVEN for every target shape — including a target-side
        bundle of the same count."""
        result = _extract("bundle of 3")
        assert result.state is AMB
        assert result.established_kind is None
        assert result.established_quantity is None
        _cue_state(
            result,
            [(SalesUnitKindV2.BUNDLE, None, AMBD, REASON.BUNDLE_WITHOUT_CONTENTS)],
        )
        # The published count stays verbatim in the cue text.
        assert result.cues[0].cue_text == "bundle of 3"
        channel = sui.sales_unit_channel_from_extraction(result)
        assert channel.state is PackagingEvidenceStateV2.UNAVAILABLE
        targets = [
            None,
            _target(TargetSalesUnitFormV2.SINGLE_UNIT),
            _target(TargetSalesUnitFormV2.PACK_QUANTITY, 4),
            _target(TargetSalesUnitFormV2.TRAY_OR_FACTORY_PACK, 10),
            _target(TargetSalesUnitFormV2.BUNDLE, 3),
            _target(TargetSalesUnitFormV2.BUNDLE),
        ]
        for target in targets:
            assert (
                sales_unit_authority_from_channel(channel, target)
                is SalesUnitAuthorityV2.UNPROVEN
            ), target

    def test_two_bundles_with_equal_counts_but_different_contents(self) -> None:
        """Mandated regression 6: two bundles with equal counts but
        different contents are not commercially equivalent. Under the
        frozen contract, no extraction-derived bundle channel proves
        equivalence against a target-side bundle of the same count:
        the count-only bundle publishes the recorded absence, and the
        composition-verified bundle publishes a quantity-None channel
        (the material count unverified on that side)."""
        count_only = _channel("bundle of 3")
        assert count_only.state is PackagingEvidenceStateV2.UNAVAILABLE
        assert (
            sales_unit_authority_from_channel(
                count_only, _target(TargetSalesUnitFormV2.BUNDLE, 3)
            )
            is SalesUnitAuthorityV2.UNPROVEN
        )
        verified = _channel("bundle: 2x RAM + 1x CPU")
        assert verified.state is PackagingEvidenceStateV2.OBSERVED
        assert verified.kind is SalesUnitKindV2.BUNDLE
        assert verified.quantity is None
        assert verified.raw_detail == "bundle: 2x RAM + 1x CPU"
        # Contents verified on the candidate side, count-only target:
        # never proven (the count is material and unverified on the
        # candidate side).
        assert (
            sales_unit_authority_from_channel(
                verified, _target(TargetSalesUnitFormV2.BUNDLE, 3)
            )
            is SalesUnitAuthorityV2.UNPROVEN
        )
        assert (
            sales_unit_authority_from_channel(
                verified, _target(TargetSalesUnitFormV2.BUNDLE)
            )
            is SalesUnitAuthorityV2.UNPROVEN
        )
        # Against the default single-unit target the published bundle is
        # a published incompatible unit (contradicted, never proven).
        assert (
            sales_unit_authority_from_channel(verified)
            is SalesUnitAuthorityV2.CONTRADICTED
        )

    def test_bundle_contents_known_on_only_one_side(self) -> None:
        """Mandated regression 7: the composition is verified on only
        the candidate side ("bundle: 2x RAM + 1x CPU"); the frozen
        target-side record carries a form + optional count, no
        composition field. The material count is unverified on the
        candidate side -> UNPROVEN (the frozen channel cannot prove
        composition equivalence from one side's record)."""
        verified = _channel("bundle: 2x RAM + 1x CPU")
        assert (
            sales_unit_authority_from_channel(
                verified, _target(TargetSalesUnitFormV2.BUNDLE, 3)
            )
            is SalesUnitAuthorityV2.UNPROVEN
        )
        assert (
            sales_unit_authority_from_channel(
                verified, _target(TargetSalesUnitFormV2.BUNDLE)
            )
            is SalesUnitAuthorityV2.UNPROVEN
        )
        # And the count-only candidate against a target-side bundle
        # record (contents known on only one side is not representable
        # in the frozen target record): the recorded absence.
        count_only = _channel("bundle of 3")
        assert (
            sales_unit_authority_from_channel(
                count_only, _target(TargetSalesUnitFormV2.BUNDLE, 3)
            )
            is SalesUnitAuthorityV2.UNPROVEN
        )

    def test_two_identical_independently_verified_bundle_compositions(self) -> None:
        """Mandated regression 8: two identical, independently verified
        bundle compositions. The extraction layer establishes each one
        (OBSERVED BUNDLE, the contents verbatim in the cue and the
        channel raw detail, quantity None — the count is never salvaged
        from the composition); the frozen FU3 derivation still cannot
        prove equivalence (the frozen channel carries no composition
        fact and the derivation reads form + count only) -> UNPROVEN,
        never PROVEN. The exact versioned contract amendment that WOULD
        represent composition equivalence is reported (separately
        approval-gated; the frozen FU3 implementation and acceptance
        criteria are unchanged)."""
        result_a = _extract("bundle: 2x RAM + 1x CPU")
        result_b = _extract("bundle: 2x RAM + 1x CPU", sku="OTHER-OFFER-SKU")
        assert result_a.state is OBS
        assert result_b.state is OBS
        assert result_a.established_kind is SalesUnitKindV2.BUNDLE
        assert result_b.established_kind is SalesUnitKindV2.BUNDLE
        assert result_a.established_quantity is None
        assert result_b.established_quantity is None
        assert result_a.cues[0].cue_text == "bundle: 2x RAM + 1x CPU"
        assert result_b.cues[0].cue_text == "bundle: 2x RAM + 1x CPU"
        # Independent offers: distinct input bindings.
        assert result_a.input_digest != result_b.input_digest
        channel_a = sui.sales_unit_channel_from_extraction(result_a)
        channel_b = sui.sales_unit_channel_from_extraction(result_b)
        assert channel_a.raw_detail == channel_b.raw_detail
        assert channel_a.quantity is None and channel_b.quantity is None
        assert (
            sales_unit_authority_from_channel(
                channel_a, _target(TargetSalesUnitFormV2.BUNDLE)
            )
            is SalesUnitAuthorityV2.UNPROVEN
        )
        assert (
            sales_unit_authority_from_channel(
                channel_a, _target(TargetSalesUnitFormV2.BUNDLE, 3)
            )
            is SalesUnitAuthorityV2.UNPROVEN
        )
        assert (
            sales_unit_authority_from_channel(
                channel_b, _target(TargetSalesUnitFormV2.BUNDLE)
            )
            is SalesUnitAuthorityV2.UNPROVEN
        )

    def test_tray_quantity_missing_on_one_side(self) -> None:
        """Mandated regression 9: a tray count is MATERIAL — missing on
        either side is UNPROVEN (a 20-unit tray is not a 10-unit tray;
        a bare tray never proves against a counted one); equal published
        counts prove, unequal published counts contradict."""
        tray_10 = _channel("Tray of 10")
        tray_bare = _channel("(tray)")
        assert (
            sales_unit_authority_from_channel(
                tray_10, _target(TargetSalesUnitFormV2.TRAY_OR_FACTORY_PACK, 10)
            )
            is SalesUnitAuthorityV2.PROVEN_EQUIVALENT
        )
        assert (
            sales_unit_authority_from_channel(
                tray_10, _target(TargetSalesUnitFormV2.TRAY_OR_FACTORY_PACK)
            )
            is SalesUnitAuthorityV2.UNPROVEN
        )
        assert (
            sales_unit_authority_from_channel(
                tray_bare, _target(TargetSalesUnitFormV2.TRAY_OR_FACTORY_PACK, 10)
            )
            is SalesUnitAuthorityV2.UNPROVEN
        )
        assert (
            sales_unit_authority_from_channel(
                tray_bare, _target(TargetSalesUnitFormV2.TRAY_OR_FACTORY_PACK)
            )
            is SalesUnitAuthorityV2.UNPROVEN
        )
        assert (
            sales_unit_authority_from_channel(
                tray_10, _target(TargetSalesUnitFormV2.TRAY_OR_FACTORY_PACK, 20)
            )
            is SalesUnitAuthorityV2.CONTRADICTED
        )

    def test_fu3_pricing_ceiling_match_high_strong_over_corrected_bundle_shapes(
        self,
    ) -> None:
        """Mandated regression 12: under MATCH + HIGH + STRONG (the fully
        qualified semantic shape), the corrected bundle shapes never
        reach the automatic pricing tier: the count-only bundle is
        UNPROVEN (capped at NEEDS_REVIEW by
        CEILING_SALES_UNIT_NOT_PROVEN), and the composition-verified
        bundle against the default single-unit target is CONTRADICTED
        (capped at NEEDS_REVIEW by CEILING_SALES_UNIT_CONTRADICTED)."""
        assessment_v2 = _u1_v2()
        count_only = derive_authority_tier_for_contract(
            AUTHORITY_CONTRACT_VERSION_V2_FU3,
            assessment_v2,
            _match(),
            frozenset(),
            _strong_profile(),
            sales_unit_channel=_channel("bundle of 3"),
        )
        assert count_only.tier is AuthorityTier.NEEDS_REVIEW
        assert count_only.sales_unit_authority is SalesUnitAuthorityV2.UNPROVEN
        assert AuthorityRuleV2FU3.CEILING_SALES_UNIT_NOT_PROVEN in count_only.fired_rules
        assert AuthorityRuleV2FU3.CEILING_SALES_UNIT_CONTRADICTED not in (
            count_only.fired_rules
        )
        verified = derive_authority_tier_for_contract(
            AUTHORITY_CONTRACT_VERSION_V2_FU3,
            assessment_v2,
            _match(),
            frozenset(),
            _strong_profile(),
            sales_unit_channel=_channel("bundle: 2x RAM + 1x CPU"),
        )
        assert verified.tier is AuthorityTier.NEEDS_REVIEW
        assert verified.sales_unit_authority is SalesUnitAuthorityV2.CONTRADICTED
        assert AuthorityRuleV2FU3.CEILING_SALES_UNIT_CONTRADICTED in (
            verified.fired_rules
        )


# ===========================================================================
# P7b. FROZEN REPLAY AND ISOLATION
# ===========================================================================


class TestFrozenReplayAndIsolation:
    def test_the_live_main_flow_builder_still_records_unavailable(self) -> None:
        # Frozen S2-C behavior: the live builder hard-wires UNAVAILABLE
        # even when the title carries a loud cue. The separately gated
        # integration is proposed, not active.
        observation = _observation(title="4TB SSD (pack of 4)")
        commercial = build_candidate_commercial_evidence_v2(observation)
        assert commercial.sales_unit.state is PackagingEvidenceStateV2.UNAVAILABLE
        assert commercial.sales_unit.kind is None
        assert commercial.sales_unit.quantity is None
        assert commercial.sales_unit.raw_detail is None
        assert commercial.sales_unit.source is None

    def test_no_live_module_references_the_extractor(self) -> None:
        import ast

        production_roots = (
            REPO_ROOT / "product_intelligence" / "semantic",
            REPO_ROOT / "product_intelligence" / "execution",
            REPO_ROOT / "product_intelligence" / "runs",
            REPO_ROOT / "product_intelligence" / "web",
            REPO_ROOT / "product_intelligence" / "providers",
        )
        for root in production_roots:
            for path in sorted(root.rglob("*.py")):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and node.module:
                        assert "sales_unit_extraction" not in node.module, path
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            assert "sales_unit_extraction" not in alias.name, path

    def test_v2_authority_qualified_remains_false(self) -> None:
        from product_intelligence.research import V2_AUTHORITY_QUALIFIED
        from product_intelligence.semantic.runtime_v2 import (
            V2_AUTHORITY_QUALIFIED as RUNTIME_MARKER,
        )

        assert V2_AUTHORITY_QUALIFIED is False
        assert RUNTIME_MARKER is False

    def test_the_frozen_corpus_and_binding_artifacts_are_unchanged(self) -> None:
        corpus_root = REPO_ROOT / "evaluation" / "semantic_v2_qualification"
        v1 = json.loads((corpus_root / "corpus_v1.json").read_text(encoding="utf-8"))
        v2_1 = json.loads((corpus_root / "corpus_2_1.json").read_text(encoding="utf-8"))
        assert v1["corpus_version"] == "1.0.0"
        assert v1["corpus_digest"] == (
            "2c37ba088c317d8cefc6ad0dd7e0d73cfd085f6474ef43eb6953e3cf0170b549"
        )
        assert v1["semantic_contract_binding"] == [
            "V2",
            "2.0",
            1,
            1,
            "SEMANTIC_AUTHORITY_V2_S2A_FU2",
        ]
        assert v2_1["corpus_version"] == "1.1.0"
        assert v2_1["corpus_digest"] == (
            "14396eae884841e20063cb4da0d4424ce8f05ff8745f2c787fc395d250ea8dcd"
        )
        assert v2_1["semantic_contract_binding"] == [
            "V2",
            "2.1",
            1,
            1,
            "SEMANTIC_AUTHORITY_V2_S2A_FU3",
        ]
        # The frozen prompt 2.0 identity is unchanged.
        from product_intelligence.research import V2_CONTRACT_BINDING
        from product_intelligence.semantic.contract_v2 import (
            SEMANTIC_PROMPT_VERSION_V2,
        )

        assert SEMANTIC_PROMPT_VERSION_V2 == "2.0"
        assert V2_CONTRACT_BINDING == (
            "V2",
            "2.0",
            1,
            1,
            "SEMANTIC_AUTHORITY_V2_S2A_FU2",
        )

    def test_the_module_is_research_pure(self) -> None:
        import ast
        import sys

        path = (
            REPO_ROOT
            / "product_intelligence"
            / "research"
            / "sales_unit_extraction.py"
        )
        source = path.read_text(encoding="utf-8")
        modules: set[str] = set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Import):
                modules.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                modules.add(node.module.split(".")[0])
        disallowed = {
            module
            for module in modules
            if module != "product_intelligence" and module not in sys.stdlib_module_names
        }
        assert not disallowed, disallowed
        io_modules = {
            "requests",
            "httpx",
            "urllib.request",
            "socket",
            "ssl",
            "http",
            "pathlib",
            "sqlite3",
            "os",
            "shutil",
            "tempfile",
            "subprocess",
            "webbrowser",
        }
        assert not (modules & io_modules)
        for name, value in vars(sui).items():
            if name.startswith("__"):
                continue
            assert not isinstance(value, (dict, list, set)), name

    def test_the_module_names_no_vendor_or_caller_system(self) -> None:
        from tests.domain.test_domain_boundaries import (
            CALLER_TOKENS,
            VENDOR_TOKENS,
            _find_tokens,
        )

        source = (
            REPO_ROOT
            / "product_intelligence"
            / "research"
            / "sales_unit_extraction.py"
        ).read_text(encoding="utf-8")
        assert not _find_tokens(source, VENDOR_TOKENS)
        assert not _find_tokens(source, CALLER_TOKENS)
