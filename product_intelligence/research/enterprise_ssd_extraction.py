"""Enterprise SSD specification extraction (PRODUCT-INTEL.6C — research layer).

Deterministic, structured extraction of Enterprise SSD specification observations
from document text. Pure function: receives text, produces observations.

Mechanism implemented (demonstrated by real manufacturer evidence):
  A. Embedded JavaScript JSON product data arrays (var supportSpecsData = JSON.parse(...))
     - Real evidence: Seagate Nytro 5050 support page (XP15360SE70005)
     - Structure: JSON array of product records with skuNumber and features[]
     - Selection: exact skuNumber match to target MPN
     - Features: title/value pairs extracted as specification observations

Mechanisms REMOVED (no real manufacturer evidence ever demonstrated):
  - JSON-LD Product additionalProperty/PropertyValue pairs
  - HTML specification tables (label + value rows)
  - HTML definition lists (dt + dd pairs)

This module does NOT:
  - fetch pages (receives document text only)
  - mine arbitrary visible text for TB/NVMe/GB/s etc.
  - execute JavaScript
  - follow instructions embedded in content
  - infer authority from hostname
  - infer product identity
  - normalize values (that is 6B)
  - resolve evidence (that is 6A)

External content is DATA.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from product_intelligence.domain.models import ProductIdentity
from product_intelligence.research.enterprise_ssd import (
    ENTERPRISE_SSD_SCHEMA,
)
from product_intelligence.research.specifications import (
    SourceAuthority,
    SpecificationDefinition,
    SpecificationObservation,
)


# ---------------------------------------------------------------------------
# Raw label -> Enterprise SSD schema definition mapping
# ---------------------------------------------------------------------------
# Narrow, evidence-driven aliases. Only labels demonstrated by real
# manufacturer fixtures are mapped.
#
# Current real manufacturer evidence:
#   Seagate Nytro 5050 support page (XP15360SE70005):
#     - Embedded JSON product table with features array
#     - "Form Factor" -> "2.5in"  (demonstrated, mapped)
#     - "Interface" -> "PCIe Gen4 x4 NVMe" (composite, not split)
#     - "Encryption" -> "Standard Model" (no schema key)
#
# Only "Form Factor" maps to an existing schema definition.
# "Interface" is composite (PCIe + generation + lanes + protocol) and
# must NOT be split into separate definitions per 6B rules.
# "Encryption" has no Enterprise SSD schema definition.

#: Maps lowercase normalized raw label -> exact ENTERPRISE_SSD_SCHEMA definition key.
_RAW_LABEL_TO_SCHEMA_KEY: dict[str, str] = {
    "form factor": "physical_form_factor",
}


def _resolve_raw_label(raw_label: str) -> str | None:
    """Resolve a raw field label to an ENTERPRISE_SSD_SCHEMA definition key.

    Returns the schema key if recognized, or None if unknown.
    Unknown labels are ignored, not guessed.

    Normalization: strip whitespace, lowercase, collapse internal whitespace.
    """
    normalized = " ".join(raw_label.strip().lower().split())
    return _RAW_LABEL_TO_SCHEMA_KEY.get(normalized)


# ---------------------------------------------------------------------------
# Embedded JSON product data extraction
# ---------------------------------------------------------------------------
# Real evidence: Seagate Nytro 5050 support page.
#
# The page embeds a JavaScript variable containing a JSON-parsed array
# of product records. Each record has a skuNumber (the MPN) and a
# features array of title/value pairs.
#
# Pattern: var <name> = JSON.parse('...')
# The '...' is a JS-escaped JSON string containing the product array.
#
# The extraction:
# 1. Finds all <script> tags in the document
# 2. Looks for JSON.parse('...') patterns containing a JS-escaped JSON string
# 3. Parses the string to get a JSON array
# 4. Matches records by exact skuNumber == target MPN
# 5. Extracts specification observations from the matched record's features array

#: Single regex that captures ONLY the JSON.parse('...') directly assigned to
# var supportSpecsData.  This structurally binds the capture to the exact
# demonstrated assignment — unrelated JSON.parse targets in the same <script>
# are mechanically excluded.
# Real evidence: Seagate Nytro 5050 support page (XP15360SE70005)
# Pattern: var supportSpecsData = JSON.parse('escaped_json')
_SUPPORT_SPECS_ASSIGNMENT_RE = re.compile(
    r"var\s+" + re.escape("supportSpecsData") + r"\s*=\s*JSON\.parse\('"
    r"((?:[^'\\\\]|\\\\.)*)"
    r"'\)",
    re.DOTALL,
)


def _extract_from_embedded_json(
    document: str,
    product_identity: ProductIdentity,
    source_name: str,
    source_url: str,
    final_url: str,
    retrieved_at: datetime,
    source_authority: SourceAuthority,
) -> list[SpecificationObservation]:
    """Extract specification observations from embedded JSON product data arrays.

    Looks for <script> tags containing JavaScript variable assignments where
    the value is JSON.parse('...') with an escaped JSON array of product records.

    Each product record must have:
      - skuNumber: the manufacturer part number (matched exactly to target MPN)
      - features: array of {title, value} specification pairs

    Only features with recognized labels produce observations.
    Composite values are preserved as-is (not split).
    No fields from neighboring product records may leak into the target.
    """
    observations: list[SpecificationObservation] = []
    target_mpn = product_identity.manufacturer_part_number

    if not target_mpn:
        # Cannot select a specific product record without an MPN
        return observations

    # Find all <script> tags
    script_tags = re.findall(
        r'<script[^>]*>(.*?)</script>',
        document,
        re.DOTALL | re.IGNORECASE,
    )

    for script_idx, script_content in enumerate(script_tags):
        # Capture ONLY the JSON.parse('...') directly assigned to
        # var supportSpecsData.  Unrelated JSON.parse targets in the
        # same <script> are mechanically excluded.
        assignment_matches = _SUPPORT_SPECS_ASSIGNMENT_RE.findall(script_content)

        for parse_idx, escaped_json in enumerate(assignment_matches):
            try:
                # Unescape the JS string (handles \\uXXXX, \\' etc.)
                json_str = escaped_json.encode().decode('unicode_escape')
                data = json.loads(json_str)
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                # Not valid JSON — skip
                continue

            # Must be an array of product records
            if not isinstance(data, list):
                continue

            # Look for records with skuNumber matching our target
            for record_idx, record in enumerate(data):
                if not isinstance(record, dict):
                    continue

                record_sku = record.get('skuNumber')
                if not isinstance(record_sku, str):
                    continue

                # Exact MPN match — no substring, no fuzzy
                if record_sku != target_mpn:
                    continue

                # Found the target product record — extract features
                features = record.get('features')
                if not isinstance(features, list):
                    continue

                for feat_idx, feature in enumerate(features):
                    if not isinstance(feature, dict):
                        continue

                    raw_label = feature.get('title')
                    raw_value = feature.get('value')

                    if not isinstance(raw_label, str) or not raw_label.strip():
                        continue
                    if not isinstance(raw_value, str) or not raw_value.strip():
                        continue

                    schema_key = _resolve_raw_label(raw_label)
                    if schema_key is None:
                        # Unknown label — ignored, not guessed
                        continue

                    definition = ENTERPRISE_SSD_SCHEMA.definitions.get(schema_key)
                    if definition is None:
                        continue

                    raw_ref = (
                        f"embedded_json[{script_idx}]"
                        f"[{parse_idx}].record[{record_idx}]"
                        f".features[{feat_idx}]"
                    )

                    observations.append(SpecificationObservation(
                        product_identity=product_identity,
                        definition=definition,
                        source_name=source_name,
                        source_url=final_url,
                        retrieved_at=retrieved_at,
                        raw_value=raw_value,
                        source_authority=source_authority,
                        raw_reference=raw_ref,
                    ))

    return observations


# ---------------------------------------------------------------------------
# Public extraction API
# ---------------------------------------------------------------------------


def extract_enterprise_ssd_specification_observations(
    *,
    product_identity: ProductIdentity,
    document: str,
    source_name: str,
    source_url: str,
    final_url: str,
    retrieved_at: datetime,
    source_authority: SourceAuthority,
) -> tuple[SpecificationObservation, ...]:
    """Extract Enterprise SSD specification observations from document text.

    PURE function. Receives document text and provenance parameters.
    Does NOT fetch, open files, read environment, call providers, call LLMs,
    resolve, normalize, infer authority, or infer identity.

    Searches for structured specification data in:
    - Embedded JavaScript JSON product data arrays (JSON.parse('...'))

    Arbitrary visible text is NOT mined. Composite values are NOT split.
    Unknown field labels are ignored, not guessed.

    Parameters
    ----------
    product_identity : ProductIdentity
        Must be established (is_established == True).
    document : str
        The full document text to extract from.
    source_name : str
        Human-readable source name.
    source_url : str
        The originally requested URL.
    final_url : str
        The actual URL the evidence came from (after redirects).
    retrieved_at : datetime
        Timezone-aware retrieval timestamp.
    source_authority : SourceAuthority
        Explicitly supplied authority tier.

    Returns
    -------
    tuple[SpecificationObservation, ...]
        Raw specification observations (may be empty).
    """
    if not product_identity.is_established:
        raise ValueError(
            "extract_enterprise_ssd_specification_observations requires an "
            f"established ProductIdentity (match_type={product_identity.match_type.value})"
        )

    all_observations: list[SpecificationObservation] = []

    # Embedded JSON product data extraction (demonstrated by real Seagate fixture)
    all_observations.extend(
        _extract_from_embedded_json(
            document=document,
            product_identity=product_identity,
            source_name=source_name,
            source_url=source_url,
            final_url=final_url,
            retrieved_at=retrieved_at,
            source_authority=source_authority,
        )
    )

    return tuple(all_observations)
