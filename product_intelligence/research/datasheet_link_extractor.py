"""Support-record datasheet-link extraction (PRODUCT-INTEL.6D — research layer).

Deterministic extraction of the manufacturer datasheet URL path from a
structured support-page JSON record.

This module provides the authoritative source chain for 6D datasheet
acquisition. A caller CANNOT gain AUTHORITATIVE datasheet authority by
constructing:

    DatasheetSource(url="https://...")

with an arbitrary URL. Instead, the datasheet path must be mechanically
derived from the manufacturer's own supportSpecsData JSON record for the
exact matching skuNumber.

The exact supportSpecsData anchor:

    var supportSpecsData = JSON.parse('...')

is shared with frozen 6C and frozen 7A. The structural parser is minimal
— only the JSON array extraction needed to access the `datasheet` field.

This module is PURE: no I/O, no providers, no network, no LLM, no PDF
parsing. It receives document text and produces a structured datasheet path.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# Structural anchor (shared with frozen 6C/7A)
# ---------------------------------------------------------------------------
# Pattern: var supportSpecsData = JSON.parse('escaped_json')
# Only the JSON.parse directly assigned to supportSpecsData is extracted.
_SUPPORT_SPECS_ASSIGNMENT_RE = re.compile(
    r"var\s+" + re.escape("supportSpecsData") + r"\s*=\s*JSON\.parse\('"
    r"((?:[^'\\\\]|\\\\.)*)"
    r"'\)",
    re.DOTALL,
)


# ---------------------------------------------------------------------------
# Bounded JavaScript single-quoted string unescape (bounded copy)
# ---------------------------------------------------------------------------
# Bounded decoder that handles only the escape forms actually needed.
# Does NOT corrupt literal non-ASCII Unicode text.


def _unescape_js_single_quoted_string(text: str) -> str:
    """Unescape a JavaScript single-quoted string payload.

    Handles: \\', \\\\, \\n, \\r, \\t, \\b, \\f, \\uXXXX
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
                hex_str = text[i + 2:i + 6]
                if len(hex_str) == 4 and all(
                    c in "0123456789abcdefABCDEF" for c in hex_str
                ):
                    result.append(chr(int(hex_str, 16)))
                    i += 6
                else:
                    result.append(ch)
                    i += 1
            else:
                result.append(ch)
                i += 1
        else:
            result.append(ch)
            i += 1
    return "".join(result)


# ---------------------------------------------------------------------------
# Result contract
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SupportRecordDatasheetLink:
    """One mechanically derived datasheet link from a support record.

    Produced by exact skuNumber match against the `datasheet` field of
    a single supportSpecsData record. No guessing, no filename construction,
    no title lookup, no hostname inference.

    Attributes
    ----------
    sku_number : str
        The exact skuNumber from the matched support record.
    datasheet_path : str
        The exact `datasheet` field value from the matched record.
        This is typically a relative path (e.g. /content/dam/seagate/...).
        The caller is responsible for resolving it to an absolute URL.
    """

    sku_number: str
    datasheet_path: str

    def __post_init__(self) -> None:
        if not isinstance(self.sku_number, str) or not self.sku_number.strip():
            raise ValueError("sku_number must be a non-empty string")
        if not isinstance(self.datasheet_path, str) or not self.datasheet_path.strip():
            raise ValueError("datasheet_path must be a non-empty string")


# ---------------------------------------------------------------------------
# Extraction API
# ---------------------------------------------------------------------------


def extract_datasheet_link(
    *,
    document: str,
    sku_number: str,
) -> SupportRecordDatasheetLink | None:
    """Extract the datasheet link for an exact skuNumber from supportSpecsData.

    Searches the document text for the structural anchor:
        var supportSpecsData = JSON.parse('...')

    Then selects the single record whose `skuNumber` field matches exactly.
    Returns the `datasheet` field from that record.

    Fail-closed rules:
        - No supportSpecsData anchor found -> None (abstain)
        - No record with exact skuNumber match -> None (abstain)
        - Multiple records with exact skuNumber match -> raises ValueError
          (ambiguous, fail closed)
        - Matched record has no `datasheet` field -> None (abstain)
        - Matched record's `datasheet` field is blank/empty -> None (abstain)
        - Matched record's `datasheet` field is not a string -> None (abstain)

    Parameters
    ----------
    document : str
        The full document text to extract from.
    sku_number : str
        The exact manufacturer skuNumber to match.

    Returns
    -------
    SupportRecordDatasheetLink | None
        The extracted datasheet link, or None if not found.

    Raises
    ------
    ValueError
        If sku_number matches multiple records (ambiguous -> fail closed).
    TypeError
        If inputs are wrong type.
    """
    if not isinstance(document, str):
        raise TypeError(f"document must be a string, got {type(document).__name__}")
    if not isinstance(sku_number, str):
        raise TypeError(f"sku_number must be a string, got {type(sku_number).__name__}")
    if not sku_number.strip():
        raise ValueError("sku_number must be a non-empty string")

    # Find all <script> tags
    script_tags = re.findall(
        r'<script[^>]*>(.*?)</script>',
        document,
        re.DOTALL | re.IGNORECASE,
    )

    all_records: list[dict[str, Any]] = []

    for script_content in script_tags:
        assignment_matches = _SUPPORT_SPECS_ASSIGNMENT_RE.findall(script_content)

        for escaped_json in assignment_matches:
            try:
                json_str = _unescape_js_single_quoted_string(escaped_json)
                data = json.loads(json_str)
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                continue

            if not isinstance(data, list):
                continue

            for record in data:
                if isinstance(record, dict):
                    all_records.append(record)

    if not all_records:
        return None

    # Find records with exact skuNumber match
    matching_records: list[dict[str, Any]] = []
    for record in all_records:
        record_sku = record.get("skuNumber")
        if isinstance(record_sku, str) and record_sku == sku_number:
            matching_records.append(record)

    if not matching_records:
        return None

    if len(matching_records) > 1:
        raise ValueError(
            f"skuNumber '{sku_number}' matches {len(matching_records)} records "
            "in supportSpecsData. Ambiguous match — failing closed."
        )

    record = matching_records[0]

    # Extract the `datasheet` field
    datasheet_value = record.get("datasheet")

    if not isinstance(datasheet_value, str):
        # Not a string — no datasheet path
        return None

    if not datasheet_value.strip():
        # Blank/empty datasheet field — abstain
        return None

    return SupportRecordDatasheetLink(
        sku_number=sku_number,
        datasheet_path=datasheet_value,
    )
