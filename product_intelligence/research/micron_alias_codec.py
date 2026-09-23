"""Versioned codec for the Micron alias snapshot (PRODUCT-INTEL.4D-D).

This module encodes and decodes the ``ResearchMicronAliasSnapshot`` payload
(``schema_version`` 1). It is pure Python and has no dependencies on
Django, providers, runs, or evaluation — the same storage-not-
interpretation split the price-result, FX, and supplemental codecs use:
``runs/`` stores the opaque JSON box, this codec owns the schema.

Codec rules:

* Strict required keys — reject missing keys
* Reject extra keys (fail closed)
* Timezone-aware datetime encoded deterministically (ISO 8601 UTC)
* ``None`` fields stay ``null``; strings stay strings; no coercion
* The decode path reconstructs the self-validating
  ``MicronAliasEligibilityResult``: every authority-bearing binding is
  re-derived by the contract itself (policy pin, customer-rule derivation,
  frozen-2A match re-derivation, origin boundary, SSD evidence, family
  relation), so a tampered or corrupt persisted payload cannot construct a
  valid result and fails closed with ``MicronAliasCodecError``
* Bounded provenance only: the payload carries the body SHA-256, never the
  catalog body

The payload persists the bounded audit of ONE authority acquisition for one
non-empty-MPN run: ESTABLISHED and bounded non-established results alike.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import IdentityMatchType
from product_intelligence.research.identity import PartNumberMatchAssessment
from product_intelligence.research.micron_packaging_alias import (
    MicronAliasEligibilityResult,
    MicronAliasEligibilityStatus,
    MicronPackagingAliasRelation,
    MicronSsdCategoryEvidence,
)


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class MicronAliasCodecError(Exception):
    """Error encoding or decoding a Micron alias snapshot payload.

    Raised for any structural corruption of a persisted payload (wrong
    types, missing/extra keys, unsupported schema version, values the
    self-validating contract refuses). A programming defect at encode time
    raises here as well — the encoder only ever receives already-validated
    results, so an encode failure is a contract violation, not a bounded
    authority outcome.
    """


# ---------------------------------------------------------------------------
# V1 schema
# ---------------------------------------------------------------------------

_SCHEMA_VERSION_V1 = 1

_V1_TOP_KEYS = frozenset(
    {
        "schema_version",
        "status",
        "requested_mpn",
        "description",
        "lookup_base_candidate",
        "policy_id",
        "manufacturer",
        "category",
        "requested_source_url",
        "fetched_final_url",
        "retrieved_at",
        "source_name",
        "matched_base_mpn",
        "part_number_match",
        "ssd_category_evidence",
        "alias_relation",
        "body_sha256",
    }
)

_V1_MATCH_KEYS = frozenset(
    {
        "requested_part_number",
        "candidate_part_number",
        "normalized_requested_part_number",
        "normalized_candidate_part_number",
        "match_type",
    }
)

_V1_SSD_KEYS = frozenset({"attr_name", "attr_id", "attr_value"})

_V1_RELATION_KEYS = frozenset({"requested_mpn", "base_mpn", "aliases"})


# ---------------------------------------------------------------------------
# V1 scalar helpers
# ---------------------------------------------------------------------------


def _encode_str(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise MicronAliasCodecError(
            f"{field_name} must be str or None, got {type(value).__name__}"
        )
    return value


def _decode_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise MicronAliasCodecError(
            f"{field_name} must be a string, got {type(value).__name__}"
        )
    return value


def _decode_optional_str(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise MicronAliasCodecError(
            f"{field_name} must be a string or null, got {type(value).__name__}"
        )
    return value


def _encode_datetime(value: datetime | None, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, datetime):
        raise MicronAliasCodecError(
            f"{field_name} must be a datetime or None, got {type(value).__name__}"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise MicronAliasCodecError(
            f"{field_name} must be timezone-aware; cannot encode a naive datetime"
        )
    utc_dt = value.astimezone(timezone.utc)
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _decode_datetime(value: Any, field_name: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise MicronAliasCodecError(
            f"{field_name} must be a string or null, got {type(value).__name__}"
        )
    # Accept the deterministic UTC form the encoder produces.
    if value.endswith("+00:00"):
        base = value[:-6]
    elif value.endswith("Z"):
        base = value[:-1]
    else:
        raise MicronAliasCodecError(
            f"{field_name} must be UTC (ends with +00:00 or Z): {value!r}"
        )
    try:
        parsed = datetime.strptime(base, "%Y-%m-%dT%H:%M:%S")
    except ValueError as exc:
        raise MicronAliasCodecError(
            f"{field_name} is not a valid datetime: {value!r}"
        ) from exc
    return parsed.replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# V1 nested helpers
# ---------------------------------------------------------------------------


def _decode_match(value: Any) -> PartNumberMatchAssessment | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise MicronAliasCodecError(
            f"part_number_match must be a mapping or null, "
            f"got {type(value).__name__}"
        )
    keys = set(value.keys())
    if keys - _V1_MATCH_KEYS:
        raise MicronAliasCodecError(
            f"unexpected keys in part_number_match: {sorted(keys - _V1_MATCH_KEYS)}"
        )
    if _V1_MATCH_KEYS - keys:
        raise MicronAliasCodecError(
            f"missing keys in part_number_match: {sorted(_V1_MATCH_KEYS - keys)}"
        )
    match_type = _decode_str(value["match_type"], "part_number_match.match_type")
    try:
        match_enum = IdentityMatchType(match_type)
    except ValueError as exc:
        raise MicronAliasCodecError(
            f"part_number_match.match_type is not a known match type: "
            f"{match_type!r}"
        ) from exc
    return PartNumberMatchAssessment(
        requested_part_number=_decode_str(
            value["requested_part_number"], "part_number_match.requested_part_number"
        ),
        candidate_part_number=_decode_str(
            value["candidate_part_number"], "part_number_match.candidate_part_number"
        ),
        normalized_requested_part_number=_decode_str(
            value["normalized_requested_part_number"],
            "part_number_match.normalized_requested_part_number",
        ),
        normalized_candidate_part_number=_decode_str(
            value["normalized_candidate_part_number"],
            "part_number_match.normalized_candidate_part_number",
        ),
        match_type=match_enum,
    )


def _decode_ssd_evidence(value: Any) -> MicronSsdCategoryEvidence | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise MicronAliasCodecError(
            f"ssd_category_evidence must be a mapping or null, "
            f"got {type(value).__name__}"
        )
    keys = set(value.keys())
    if keys - _V1_SSD_KEYS:
        raise MicronAliasCodecError(
            f"unexpected keys in ssd_category_evidence: {sorted(keys - _V1_SSD_KEYS)}"
        )
    if _V1_SSD_KEYS - keys:
        raise MicronAliasCodecError(
            f"missing keys in ssd_category_evidence: {sorted(_V1_SSD_KEYS - keys)}"
        )
    attr_value = value["attr_value"]
    if type(attr_value) is not bool:
        raise MicronAliasCodecError(
            f"ssd_category_evidence.attr_value must be a boolean, "
            f"got {type(attr_value).__name__}"
        )
    return MicronSsdCategoryEvidence(
        attr_name=_decode_optional_str(
            value["attr_name"], "ssd_category_evidence.attr_name"
        ),
        attr_id=_decode_str(value["attr_id"], "ssd_category_evidence.attr_id"),
        attr_value=attr_value,
    )


def _decode_relation(value: Any) -> MicronPackagingAliasRelation | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise MicronAliasCodecError(
            f"alias_relation must be a mapping or null, got {type(value).__name__}"
        )
    keys = set(value.keys())
    if keys - _V1_RELATION_KEYS:
        raise MicronAliasCodecError(
            f"unexpected keys in alias_relation: {sorted(keys - _V1_RELATION_KEYS)}"
        )
    if _V1_RELATION_KEYS - keys:
        raise MicronAliasCodecError(
            f"missing keys in alias_relation: {sorted(_V1_RELATION_KEYS - keys)}"
        )
    aliases_raw = value["aliases"]
    if not isinstance(aliases_raw, list):
        raise MicronAliasCodecError(
            f"alias_relation.aliases must be a list, got {type(aliases_raw).__name__}"
        )
    aliases = tuple(
        _decode_str(alias, f"alias_relation.aliases[{i}]")
        for i, alias in enumerate(aliases_raw)
    )
    return MicronPackagingAliasRelation(
        requested_mpn=_decode_str(
            value["requested_mpn"], "alias_relation.requested_mpn"
        ),
        base_mpn=_decode_str(value["base_mpn"], "alias_relation.base_mpn"),
        aliases=aliases,
    )


# ---------------------------------------------------------------------------
# Public encode/decode
# ---------------------------------------------------------------------------


def encode_micron_alias_snapshot(result: MicronAliasEligibilityResult) -> dict[str, Any]:
    """Encode one self-validated eligibility result into a V1 payload dict.

    The input must be a constructed ``MicronAliasEligibilityResult`` — its
    ``__post_init__`` already re-derived every authority-bearing binding, so
    the encoder only serializes. Any serialization failure (wrong type,
    naive datetime) is a contract violation and raises
    ``MicronAliasCodecError``.
    """
    if not isinstance(result, MicronAliasEligibilityResult):
        raise MicronAliasCodecError(
            f"result must be a MicronAliasEligibilityResult, got "
            f"{type(result).__name__}"
        )

    part_number_match = result.part_number_match
    match_dict: dict[str, Any] | None = None
    if part_number_match is not None:
        match_dict = {
            "requested_part_number": part_number_match.requested_part_number,
            "candidate_part_number": part_number_match.candidate_part_number,
            "normalized_requested_part_number": (
                part_number_match.normalized_requested_part_number
            ),
            "normalized_candidate_part_number": (
                part_number_match.normalized_candidate_part_number
            ),
            "match_type": part_number_match.match_type.value,
        }

    ssd = result.ssd_category_evidence
    ssd_dict: dict[str, Any] | None = None
    if ssd is not None:
        ssd_dict = {
            "attr_name": ssd.attr_name,
            "attr_id": ssd.attr_id,
            "attr_value": ssd.attr_value,
        }

    relation = result.alias_relation
    relation_dict: dict[str, Any] | None = None
    if relation is not None:
        relation_dict = {
            "requested_mpn": relation.requested_mpn,
            "base_mpn": relation.base_mpn,
            "aliases": list(relation.aliases),
        }

    return {
        "schema_version": _SCHEMA_VERSION_V1,
        "status": result.status.value,
        "requested_mpn": result.request.manufacturer_part_number,
        "description": result.request.description,
        "lookup_base_candidate": _encode_str(
            result.lookup_base_candidate, "lookup_base_candidate"
        ),
        "policy_id": _encode_str(result.policy_id, "policy_id"),
        "manufacturer": _encode_str(result.manufacturer, "manufacturer"),
        "category": _encode_str(result.category, "category"),
        "requested_source_url": _encode_str(
            result.requested_source_url, "requested_source_url"
        ),
        "fetched_final_url": _encode_str(result.fetched_final_url, "fetched_final_url"),
        "retrieved_at": _encode_datetime(result.retrieved_at, "retrieved_at"),
        "source_name": _encode_str(result.source_name, "source_name"),
        "matched_base_mpn": _encode_str(result.matched_base_mpn, "matched_base_mpn"),
        "part_number_match": match_dict,
        "ssd_category_evidence": ssd_dict,
        "alias_relation": relation_dict,
        "body_sha256": _encode_str(result.body_sha256, "body_sha256"),
    }


def decode_micron_alias_snapshot(
    payload: dict[str, Any],
    schema_version: int | None = None,
) -> MicronAliasEligibilityResult:
    """Decode a persisted V1 payload back into the self-validating result.

    ``schema_version`` (the model column) must agree with the payload's own
    ``schema_version``. Any structural corruption, unknown version, or value
    the self-validating contract refuses raises ``MicronAliasCodecError`` —
    the historical report fails closed on the alias section rather than
    rendering partial or re-acquired alias data.
    """
    if not isinstance(payload, dict):
        raise MicronAliasCodecError(
            f"payload must be a dict, got {type(payload).__name__}"
        )

    top_keys = set(payload.keys())
    extra_keys = top_keys - _V1_TOP_KEYS
    if extra_keys:
        raise MicronAliasCodecError(
            f"unexpected top-level keys: {sorted(extra_keys)}"
        )
    missing_keys = _V1_TOP_KEYS - top_keys
    if missing_keys:
        raise MicronAliasCodecError(f"missing top-level keys: {sorted(missing_keys)}")

    stored_version = payload["schema_version"]
    if stored_version != _SCHEMA_VERSION_V1:
        raise MicronAliasCodecError(
            f"unsupported schema_version: {stored_version!r}; "
            f"expected {_SCHEMA_VERSION_V1}"
        )
    if schema_version is not None and schema_version != stored_version:
        raise MicronAliasCodecError(
            f"model schema_version {schema_version!r} disagrees with payload "
            f"schema_version {stored_version!r}"
        )

    status_raw = _decode_str(payload["status"], "status")
    try:
        status = MicronAliasEligibilityStatus(status_raw)
    except ValueError as exc:
        raise MicronAliasCodecError(
            f"status is not a known eligibility status: {status_raw!r}"
        ) from exc

    requested_mpn = _decode_str(payload["requested_mpn"], "requested_mpn")
    description = _decode_str(payload["description"], "description")
    try:
        request = ResearchRequest(
            manufacturer_part_number=requested_mpn,
            description=description,
        )
    except Exception as exc:
        raise MicronAliasCodecError(
            f"payload does not carry a canonical research request: {exc}"
        ) from exc

    try:
        return MicronAliasEligibilityResult(
            status=status,
            request=request,
            lookup_base_candidate=_decode_optional_str(
                payload["lookup_base_candidate"], "lookup_base_candidate"
            ),
            policy_id=_decode_str(payload["policy_id"], "policy_id"),
            manufacturer=_decode_optional_str(payload["manufacturer"], "manufacturer"),
            category=_decode_optional_str(payload["category"], "category"),
            requested_source_url=_decode_optional_str(
                payload["requested_source_url"], "requested_source_url"
            ),
            fetched_final_url=_decode_optional_str(
                payload["fetched_final_url"], "fetched_final_url"
            ),
            retrieved_at=_decode_datetime(payload["retrieved_at"], "retrieved_at"),
            source_name=_decode_optional_str(payload["source_name"], "source_name"),
            matched_base_mpn=_decode_optional_str(
                payload["matched_base_mpn"], "matched_base_mpn"
            ),
            part_number_match=_decode_match(payload["part_number_match"]),
            ssd_category_evidence=_decode_ssd_evidence(payload["ssd_category_evidence"]),
            alias_relation=_decode_relation(payload["alias_relation"]),
            body_sha256=_decode_optional_str(payload["body_sha256"], "body_sha256"),
        )
    except MicronAliasCodecError:
        raise
    except (TypeError, ValueError) as exc:
        # A structurally intact payload whose values the self-validating
        # contract refuses is a tampered/corrupt persisted result.
        raise MicronAliasCodecError(
            f"payload failed the eligibility contract: {exc}"
        ) from exc
