"""SEMANTIC-V2-A1 — the versioned price-result codec (schema 2).

Positive and negative acceptance over:

* the FROZEN schema-1 path (historical byte compatibility — the V1
  encoder's exact JSON bytes are golden-pinned, and the V1 decoder's
  extra-key strictness still refuses ANY unexpected key, incl. a
  ``description_text`` smuggled into a schema-1 payload — N5);
* the NEW schema-2 path (the V1 payload plus exactly one additive key
  per observation: ``description_text`` — nullable, always present,
  null when absent; round trip incl. the nullable shape);
* the version dispatcher (1 ⇒ frozen V1 decode, 2 ⇒ V2 decode,
  anything else ⇒ fail closed — no best-effort migration);
* cross-version refusal (a schema-2 payload presented as schema 1, and
  a schema-1 payload presented as schema 2, both fail closed).

The frozen V1 suite (``test_price_result_codec.py``) passes UNCHANGED
over this phase — it is the behavioral byte-compatibility anchor.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.research import (
    CURRENT_PRICE_RESULT_SCHEMA_VERSION,
    PRICE_RESULT_SCHEMA_VERSION,
    PRICE_RESULT_SCHEMA_VERSION_2,
    ExtractionMethod,
    ListingObservation,
    PriceAggregationResult,
    PriceResultCodecError,
    aggregate_listing_prices,
    assess_listing_identity,
    decode_price_aggregation_result,
    encode_price_aggregation_result,
    encode_price_aggregation_result_v2,
)
from product_intelligence.research.normalization import normalize_listing_observation

DESCRIPTON_TEXT = (
    "3.84TB enterprise NVMe SSD with U.2 interface, "
    "next-generation 6900/4100 MB/s sequential performance."
)


def _request() -> ResearchRequest:
    return ResearchRequest("MZ-SV2A1-1", "enterprise drive")


def _observation(description_text: str | None = None) -> ListingObservation:
    return ListingObservation(
        source_url="https://example.com/sv2a1",
        extraction_method=ExtractionMethod.JSON_LD,
        product_title="SV2-A1 drive 1TB",
        manufacturer_part_number_text="MZ-SV2A1-1",
        sku_text="SV2A1-1",
        brand_text="Example",
        price_text="99.00",
        currency_text="USD",
        availability_text="In Stock",
        condition_text="New",
        seller_text="Example Store",
        offer_url_text="https://example.com/offer",
        raw_reference='{"@type": "Product"}',
        description_text=description_text,
    )


def _result(description_text: str | None = None) -> PriceAggregationResult:
    observation = _observation(description_text)
    assessment = assess_listing_identity(
        _request(), normalize_listing_observation(observation)
    )
    return aggregate_listing_prices(_request(), (assessment,))


def _canonical_json(payload: dict) -> str:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


# ---------------------------------------------------------------------------
# 1. The frozen constants
# ---------------------------------------------------------------------------


class TestVersionConstants:
    def test_the_frozen_v1_constant_is_unchanged(self) -> None:
        assert PRICE_RESULT_SCHEMA_VERSION == 1

    def test_the_v2_constant_is_two(self) -> None:
        assert PRICE_RESULT_SCHEMA_VERSION_2 == 2

    def test_the_publication_constant_is_the_gated_v2_value(self) -> None:
        """SEMANTIC-V2-A1 advanced the frozen publication constant from 1
        to 2 under the gated approval only; publication selects the
        encoder + recorded schema_version from it."""
        assert CURRENT_PRICE_RESULT_SCHEMA_VERSION == (
            PRICE_RESULT_SCHEMA_VERSION_2
        )


# ---------------------------------------------------------------------------
# 2. Schema-1 historical byte compatibility (the golden anchor)
# ---------------------------------------------------------------------------

# The exact canonical-JSON bytes the FROZEN V1 encoder produced for the
# golden result below, pinned character-for-character. The V1 encoder is
# byte-identical through SEMANTIC-V2-A1: this pin proves a historical
# schema-1 payload is reproduced exactly, and its SHA-256 is recorded
# for independent verification.
GOLDEN_REQUEST_MPN = "MZ-GOLD-1"
GOLDEN_REQUEST_DESCRIPTION = "golden round trip drive"
GOLDEN_SHA256 = (
    "75ed287ca0c2f81d61673da01ccca01ecd56e2523fffae7d48d62b0fb76d8d95"
)


def _golden_result() -> PriceAggregationResult:
    request = ResearchRequest(GOLDEN_REQUEST_MPN, GOLDEN_REQUEST_DESCRIPTION)
    observation = ListingObservation(
        source_url="https://example.com/golden",
        extraction_method=ExtractionMethod.JSON_LD,
        product_title="Golden 1TB",
        manufacturer_part_number_text=GOLDEN_REQUEST_MPN,
        sku_text="G-1",
        brand_text="Example",
        price_text="99.00",
        currency_text="USD",
        availability_text="In Stock",
        condition_text="New",
        seller_text="Example Store",
        offer_url_text="https://example.com/offer",
        raw_reference='{"@type": "Product"}',
    )
    assessment = assess_listing_identity(
        request, normalize_listing_observation(observation)
    )
    return aggregate_listing_prices(request, (assessment,))


class TestSchema1HistoricalByteCompatibility:
    def test_the_v1_encoder_reproduces_the_golden_bytes_exactly(self) -> None:
        payload = encode_price_aggregation_result(_golden_result())
        canonical = _canonical_json(payload)
        assert hashlib.sha256(canonical.encode("utf-8")).hexdigest() == (
            GOLDEN_SHA256
        )

    def test_the_golden_payload_carries_exactly_the_13_frozen_observation_keys(
        self,
    ) -> None:
        payload = encode_price_aggregation_result(_golden_result())
        observation = payload["assessments"][0]["normalized_listing"]["observation"]
        assert set(observation) == {
            "source_url",
            "extraction_method",
            "product_title",
            "manufacturer_part_number_text",
            "sku_text",
            "brand_text",
            "price_text",
            "currency_text",
            "availability_text",
            "condition_text",
            "seller_text",
            "offer_url_text",
            "raw_reference",
        }
        assert "description_text" not in observation

    def test_the_golden_payload_round_trips_through_the_v1_path(self) -> None:
        result = _golden_result()
        payload = encode_price_aggregation_result(result)
        decoded = decode_price_aggregation_result(
            json.loads(_canonical_json(payload)),
            schema_version=PRICE_RESULT_SCHEMA_VERSION,
        )
        assert decoded == result

    def test_the_v1_encoder_never_writes_description_text_even_when_present(
        self,
    ) -> None:
        """A result whose observation carries a description is still
        written by the V1 encoder as the fixed 13 keys (the field simply
        has no schema-1 representation — that is WHY schema 2 exists;
        publication uses the V2 encoder for exactly this reason)."""
        result = _result(DESCRIPTON_TEXT)
        payload = encode_price_aggregation_result(result)
        observation = payload["assessments"][0]["normalized_listing"]["observation"]
        assert "description_text" not in observation
        assert len(observation) == 13


# ---------------------------------------------------------------------------
# 3. Schema-1 extra-field refusal (N5 — fail closed)
# ---------------------------------------------------------------------------


class TestSchema1ExtraFieldRefusal:
    def test_a_schema1_payload_with_an_unexpected_description_field_fails_closed(
        self,
    ) -> None:
        """MANDATED: a schema-1 payload containing an unexpected
        description field MUST continue to fail closed through the
        unchanged V1 decoder's extra-key strictness."""
        payload = json.loads(
            _canonical_json(encode_price_aggregation_result(_result()))
        )
        observation = payload["assessments"][0]["normalized_listing"]["observation"]
        observation["description_text"] = "smuggled"
        with pytest.raises(
            PriceResultCodecError, match="unexpected keys .*description_text"
        ):
            decode_price_aggregation_result(
                payload, schema_version=PRICE_RESULT_SCHEMA_VERSION
            )

    def test_a_schema1_payload_with_any_other_unexpected_key_still_fails(self) -> None:
        payload = json.loads(
            _canonical_json(encode_price_aggregation_result(_result()))
        )
        observation = payload["assessments"][0]["normalized_listing"]["observation"]
        observation["some_future_field"] = "x"
        with pytest.raises(PriceResultCodecError, match="unexpected keys"):
            decode_price_aggregation_result(
                payload, schema_version=PRICE_RESULT_SCHEMA_VERSION
            )


# ---------------------------------------------------------------------------
# 4. Schema-2 encoding
# ---------------------------------------------------------------------------


class TestSchema2Encoding:
    def test_the_v2_payload_is_the_v1_payload_plus_exactly_one_key(self) -> None:
        result = _result(DESCRIPTON_TEXT)
        v1_raw = encode_price_aggregation_result(result)
        v2_raw = encode_price_aggregation_result_v2(result)
        v1 = json.loads(_canonical_json(v1_raw))
        v2 = json.loads(_canonical_json(v2_raw))
        for section in ("request", "buckets", "exclusions", "verification_status"):
            assert v2[section] == v1[section]
        assert len(v2["assessments"]) == len(v1["assessments"])
        for (a1, a2), (raw1, raw2) in zip(
            zip(v1["assessments"], v2["assessments"]),
            zip(v1_raw["assessments"], v2_raw["assessments"]),
        ):
            o1 = a1["normalized_listing"]["observation"]
            o2 = a2["normalized_listing"]["observation"]
            assert {k: v for k, v in o2.items() if k != "description_text"} == o1
            # The frozen 13 keys keep their exact encoder order; the
            # additive key is appended last in the raw payload.
            o1_raw = raw1["normalized_listing"]["observation"]
            o2_raw = raw2["normalized_listing"]["observation"]
            assert [k for k in o2_raw if k != "description_text"] == list(o1_raw)
            assert list(o2_raw)[-1] == "description_text"

    def test_the_description_key_is_always_present(self) -> None:
        v2 = encode_price_aggregation_result_v2(_result())
        observation = v2["assessments"][0]["normalized_listing"]["observation"]
        assert "description_text" in observation
        assert observation["description_text"] is None

    def test_a_published_description_is_written_verbatim(self) -> None:
        v2 = encode_price_aggregation_result_v2(_result(DESCRIPTON_TEXT))
        observation = v2["assessments"][0]["normalized_listing"]["observation"]
        assert observation["description_text"] == DESCRIPTON_TEXT

    def test_the_v2_payload_is_json_serializable_without_native_leaks(self) -> None:
        payload = encode_price_aggregation_result_v2(_result(DESCRIPTON_TEXT))
        json.dumps(payload)  # no Decimal / Enum / dataclass leak

    def test_encode_v2_wrong_type_raises(self) -> None:
        with pytest.raises(TypeError, match="expected PriceAggregationResult"):
            encode_price_aggregation_result_v2("not a result")


# ---------------------------------------------------------------------------
# 5. Schema-2 round trip (incl. nullable description)
# ---------------------------------------------------------------------------


class TestSchema2RoundTrip:
    def test_round_trip_preserves_the_published_description(self) -> None:
        result = _result(DESCRIPTON_TEXT)
        payload = encode_price_aggregation_result_v2(result)
        decoded = decode_price_aggregation_result(
            json.loads(_canonical_json(payload)),
            schema_version=PRICE_RESULT_SCHEMA_VERSION_2,
        )
        assert decoded == result
        decoded_observation = decoded.assessments[0].normalized_listing.observation
        assert decoded_observation.description_text == DESCRIPTON_TEXT

    def test_round_trip_preserves_an_explicit_null_description(self) -> None:
        result = _result(None)
        payload = encode_price_aggregation_result_v2(result)
        decoded = decode_price_aggregation_result(
            json.loads(_canonical_json(payload)),
            schema_version=PRICE_RESULT_SCHEMA_VERSION_2,
        )
        assert decoded == result
        decoded_observation = decoded.assessments[0].normalized_listing.observation
        assert decoded_observation.description_text is None

    def test_round_trip_preserves_interior_whitespace_and_newlines(self) -> None:
        published = "Line one \nLine two   with gaps."
        result = _result(published)
        payload = encode_price_aggregation_result_v2(result)
        decoded = decode_price_aggregation_result(
            json.loads(_canonical_json(payload)),
            schema_version=PRICE_RESULT_SCHEMA_VERSION_2,
        )
        assert (
            decoded.assessments[0].normalized_listing.observation.description_text
            == published
        )


# ---------------------------------------------------------------------------
# 6. Schema-2 decode strictness (unexpected fields / structural failure)
# ---------------------------------------------------------------------------


class TestSchema2DecodeStrictness:
    def _v2_payload(self, description: str | None = None) -> dict:
        return json.loads(
            _canonical_json(encode_price_aggregation_result_v2(_result(description)))
        )

    def test_an_unexpected_key_in_the_v2_observation_fails_closed(self) -> None:
        payload = self._v2_payload()
        observation = payload["assessments"][0]["normalized_listing"]["observation"]
        observation["another_future_field"] = "x"
        with pytest.raises(PriceResultCodecError, match="unexpected keys"):
            decode_price_aggregation_result(
                payload, schema_version=PRICE_RESULT_SCHEMA_VERSION_2
            )

    def test_a_missing_description_key_in_a_v2_payload_fails_closed(self) -> None:
        """The key is ALWAYS present in schema 2 — omission is corruption
        (no defaulting)."""
        payload = self._v2_payload(DESCRIPTON_TEXT)
        observation = payload["assessments"][0]["normalized_listing"]["observation"]
        del observation["description_text"]
        with pytest.raises(PriceResultCodecError, match="missing required key"):
            decode_price_aggregation_result(
                payload, schema_version=PRICE_RESULT_SCHEMA_VERSION_2
            )

    def test_a_non_string_description_in_a_v2_payload_fails_closed(self) -> None:
        payload = self._v2_payload()
        observation = payload["assessments"][0]["normalized_listing"]["observation"]
        observation["description_text"] = ["not", "a", "scalar"]
        with pytest.raises(PriceResultCodecError):
            decode_price_aggregation_result(
                payload, schema_version=PRICE_RESULT_SCHEMA_VERSION_2
            )

    def test_an_unexpected_top_level_key_in_a_v2_payload_fails_closed(self) -> None:
        payload = self._v2_payload()
        payload["future_top_level"] = None
        with pytest.raises(PriceResultCodecError, match="unexpected keys"):
            decode_price_aggregation_result(
                payload, schema_version=PRICE_RESULT_SCHEMA_VERSION_2
            )

    def test_an_unknown_enum_in_a_v2_payload_fails_closed(self) -> None:
        payload = self._v2_payload()
        payload["verification_status"] = "SOME_FUTURE_STATUS"
        with pytest.raises(PriceResultCodecError, match="unknown"):
            decode_price_aggregation_result(
                payload, schema_version=PRICE_RESULT_SCHEMA_VERSION_2
            )


# ---------------------------------------------------------------------------
# 7. Cross-version refusal (fail closed, no reinterpretation)
# ---------------------------------------------------------------------------


class TestCrossVersionRefusal:
    def test_a_v2_payload_presented_as_v1_fails_closed(self) -> None:
        payload = json.loads(
            _canonical_json(encode_price_aggregation_result_v2(_result(None)))
        )
        with pytest.raises(PriceResultCodecError, match="unexpected keys"):
            decode_price_aggregation_result(
                payload, schema_version=PRICE_RESULT_SCHEMA_VERSION
            )

    def test_a_v1_payload_presented_as_v2_fails_closed(self) -> None:
        payload = json.loads(
            _canonical_json(encode_price_aggregation_result(_result()))
        )
        with pytest.raises(PriceResultCodecError, match="missing required key"):
            decode_price_aggregation_result(
                payload, schema_version=PRICE_RESULT_SCHEMA_VERSION_2
            )


# ---------------------------------------------------------------------------
# 8. The version dispatcher
# ---------------------------------------------------------------------------


class TestVersionDispatcher:
    def test_version_one_routes_to_the_frozen_v1_decode(self) -> None:
        result = _result()
        payload = json.loads(
            _canonical_json(encode_price_aggregation_result(result))
        )
        decoded = decode_price_aggregation_result(
            payload, schema_version=1
        )
        assert decoded == result

    def test_version_two_routes_to_the_v2_decode(self) -> None:
        result = _result(DESCRIPTON_TEXT)
        payload = json.loads(
            _canonical_json(encode_price_aggregation_result_v2(result))
        )
        decoded = decode_price_aggregation_result(
            payload, schema_version=2
        )
        assert decoded == result

    @pytest.mark.parametrize("version", [0, 3, 99, -1])
    def test_an_unknown_schema_version_fails_closed(self, version: int) -> None:
        with pytest.raises(PriceResultCodecError, match="unsupported schema_version"):
            decode_price_aggregation_result({}, schema_version=version)

    @pytest.mark.parametrize("version", [True, 1.0, "1", None])
    def test_a_non_int_schema_version_fails_closed(self, version: object) -> None:
        with pytest.raises(PriceResultCodecError, match="schema_version must be int"):
            decode_price_aggregation_result({}, schema_version=version)

    def test_a_non_mapping_payload_fails_closed_for_every_supported_version(self) -> None:
        for version in (1, 2):
            with pytest.raises(PriceResultCodecError, match="payload must be a mapping"):
                decode_price_aggregation_result("not a dict", schema_version=version)
