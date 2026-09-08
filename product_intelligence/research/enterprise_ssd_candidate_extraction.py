"""Enterprise SSD candidate extraction (PRODUCT-INTEL.7A — research layer).

Deterministic, structured extraction of comparable-product candidate observations
from manufacturer catalog document text. Pure function: receives text, produces
candidate observations.

This module discovers candidate product records from the same embedded JSON
product data arrays used by frozen 6C specification extraction, but outputs
candidate observations rather than specification observations.

Mechanism implemented:
  A. Embedded JavaScript JSON product data arrays (var supportSpecsData = JSON.parse(...))
     - Real evidence: Seagate Nytro 5050 support page (XP15360SE70005)
     - Structure: JSON array of product records with skuNumber and title
     - Selection: ALL records with valid skuNumber (candidate discovery)
     - Fields used: skuNumber (identity) + title (optional name)

This module does NOT:
  - fetch pages (receives document text only)
  - use features/capacity/performance for inclusion/exclusion (that is 7B)
  - mine arbitrary visible text for MPNs
  - infer MPN from title or URL
  - normalize part numbers (assessment does that)
  - compare to a target (assessment does that)
  - score, rank, or filter candidates
  - call LLMs, execute JavaScript, or open network connections

External content is DATA.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from product_intelligence.research.comparable_candidates import (
    ComparableCandidateObservation,
)
from product_intelligence.research.specifications import SourceAuthority


# ---------------------------------------------------------------------------
# Structural extraction: var supportSpecsData = JSON.parse('...')
# ---------------------------------------------------------------------------
# Same structural anchor as frozen 6C. This is the ONLY mechanism.
# The regex captures ONLY the JSON.parse('...') directly assigned to
# var supportSpecsData.  Unrelated JSON.parse targets in the same
# <script> are mechanically excluded.
# Real evidence: Seagate Nytro 5050 support page (XP15360SE70005)
# Pattern: var supportSpecsData = JSON.parse('escaped_json')
_SUPPORT_SPECS_ASSIGNMENT_RE = re.compile(
    r"var\s+" + re.escape("supportSpecsData") + r"\s*=\s*JSON\.parse\('"
    r"((?:[^'\\\\]|\\\\.)*)"
    r"'\)",
    re.DOTALL,
)


# ---------------------------------------------------------------------------
# Bounded JavaScript single-quoted string unescape
# ---------------------------------------------------------------------------
# The Seagate supportSpecsData payload uses JavaScript single-quoted strings
# that contain JSON. The JSON itself uses \uXXXX escapes for special characters
# (e.g. \u003csup\u003e for <sup>).
#
# The old implementation used .encode().decode("unicode_escape") which
# corrupts literal non-ASCII Unicode text by re-interpreting UTF-8 bytes.
# Instead, we use a bounded decoder that handles only the escape forms
# actually needed by the supported structure.

def _unescape_js_single_quoted_string(text: str) -> str:
    """Unescape a JavaScript single-quoted string payload.

    Handles the escape sequences actually present in the real fixture:
    - \\' -> '        (escaped single quote)
    - \\\\ -> \\       (escaped backslash)
    - \\n -> newline
    - \\r -> carriage return
    - \\t -> tab
    - \\b -> backspace
    - \\f -> form feed
    - \\uXXXX -> Unicode code point

    Already-literal Unicode text is preserved exactly (no re-encoding
    through UTF-8 bytes + unicode_escape which corrupts non-ASCII).

    Parameters
    ----------
    text : str
        The raw captured text from JSON.parse('...').

    Returns
    -------
    str
        The unescaped string suitable for JSON parsing.
    """
    result: list[str] = []
    i = 0
    length = len(text)
    while i < length:
        ch = text[i]
        if ch == '\\' and i + 1 < length:
            next_ch = text[i + 1]
            if next_ch == "'":
                result.append("'")
                i += 2
            elif next_ch == '\\':
                result.append('\\')
                i += 2
            elif next_ch == 'n':
                result.append('\n')
                i += 2
            elif next_ch == 'r':
                result.append('\r')
                i += 2
            elif next_ch == 't':
                result.append('\t')
                i += 2
            elif next_ch == 'b':
                result.append('\b')
                i += 2
            elif next_ch == 'f':
                result.append('\f')
                i += 2
            elif next_ch == 'u' and i + 5 < length:
                # \uXXXX
                hex_str = text[i + 2:i + 6]
                if len(hex_str) == 4 and all(
                    c in "0123456789abcdefABCDEF" for c in hex_str
                ):
                    result.append(chr(int(hex_str, 16)))
                    i += 6
                else:
                    # Invalid \uXXXX — pass through literally
                    result.append(ch)
                    i += 1
            else:
                # Unknown escape — pass through literally
                result.append(ch)
                i += 1
        else:
            # Literal character — preserved exactly (including non-ASCII)
            result.append(ch)
            i += 1
    return "".join(result)


def extract_enterprise_ssd_candidate_observations(
    *,
    document: str,
    source_name: str,
    source_url: str,
    retrieved_at: datetime,
    source_authority: SourceAuthority,
) -> tuple[ComparableCandidateObservation, ...]:
    """Extract candidate product observations from embedded JSON product data.

    PURE function. Receives document text and provenance parameters.
    Does NOT fetch, open files, read environment, call providers, call LLMs,
    resolve, normalize, infer authority, or infer identity.

    Searches for structured product data in:
    - Embedded JavaScript JSON product data arrays (var supportSpecsData)

    Each product record in the array is a candidate if it has a valid
    skuNumber. Title is preserved when present but is never used as
    identity authority.

    Features, capacity, performance, encryption, warranty, and all other
    fields are IGNORED for candidate discovery. They are 7B concerns.

    Parameters
    ----------
    document : str
        The full document text to extract from.
    source_name : str
        Human-readable source name.
    source_url : str
        The source URL.
    retrieved_at : datetime
        Timezone-aware retrieval timestamp.
    source_authority : SourceAuthority
        Explicitly supplied authority tier.

    Returns
    -------
    tuple[ComparableCandidateObservation, ...]
        Raw candidate observations (may be empty).
    """
    observations: list[ComparableCandidateObservation] = []

    # Validate inputs are correct types
    if not isinstance(document, str):
        raise TypeError(f"document must be a string, got {type(document).__name__}")

    if not isinstance(source_name, str) or not source_name.strip():
        raise ValueError("source_name must be a non-empty string")

    if not isinstance(source_url, str) or not source_url.strip():
        raise ValueError("source_url must be a non-empty string")

    if not isinstance(retrieved_at, datetime):
        raise TypeError(
            f"retrieved_at must be a datetime, got {type(retrieved_at).__name__}"
        )
    if retrieved_at.tzinfo is None or retrieved_at.utcoffset() is None:
        raise ValueError("retrieved_at must be timezone-aware")

    if not isinstance(source_authority, SourceAuthority):
        raise TypeError(
            f"source_authority must be a SourceAuthority, got "
            f"{type(source_authority).__name__}"
        )

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
                # Unescape the JS single-quoted string using bounded decoder
                # (does not corrupt literal non-ASCII Unicode text)
                json_str = _unescape_js_single_quoted_string(escaped_json)
                data = json.loads(json_str)
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                # Not valid JSON — skip
                continue

            # Must be an array of product records
            if not isinstance(data, list):
                continue

            for record_idx, record in enumerate(data):
                if not isinstance(record, dict):
                    continue

                # skuNumber is required for a candidate
                sku_number = record.get("skuNumber")
                if not isinstance(sku_number, str):
                    continue
                if not sku_number.strip():
                    continue

                # title is optional — preserved exactly as published
                title = record.get("title")
                if isinstance(title, str):
                    product_name_raw = title
                else:
                    product_name_raw = None

                # Build bounded raw reference
                raw_ref = (
                    f"embedded_json[{script_idx}]"
                    f"[{parse_idx}].record[{record_idx}]"
                )

                observations.append(
                    ComparableCandidateObservation(
                        manufacturer_part_number_raw=sku_number,
                        product_name_raw=product_name_raw,
                        source_name=source_name,
                        source_url=source_url,
                        retrieved_at=retrieved_at,
                        source_authority=source_authority,
                        raw_reference=raw_ref,
                    )
                )

    return tuple(observations)
