"""Enterprise SSD datasheet table interpretation (PRODUCT-INTEL.6D — research layer).

Deterministic, pure interpretation of already-extracted PDF table data into
SpecificationObservation values.

This module is PURE: no I/O, no providers, no network, no LLM, no PDF parsing
library. It receives structured table data (list of rows, each row a list of
cell strings) and produces SpecificationObservation values.

Core invariant: MPN -> table -> column -> row binding.

A manufacturer datasheet contains multiple product-family tables and multiple
model columns. Given an exact candidate MPN:

    1. Locate the EXACT MPN token in a model-identification row.
    2. Determine exact table, exact column index.
    3. Only values from that exact column in the same table are emitted.

No family-wide value may leak across columns/products.

Extracted fields (6D v1 allowlist):
    capacity
    sequential_read
    sequential_write
    random_read_iops
    random_write_iops
    endurance_dwpd

When a recognized row's cell value lacks the unit that the row header
explicitly defines, the unit is incorporated into raw_value so that
frozen 6B normalization succeeds. This is structurally justified by
the table's own row label — the table declares the unit for every cell
in that row.

Bounded grammar: only the exact demonstrated row labels from the real
Seagate Nytro 5550/5350 datasheet are recognized. No generic prefix
matching. No inference from hostname. No arbitrary "model" keyword.

Raw evidence fidelity: MPN cells and spec cells are compared/used with
exact text. No .strip() before MPN equality. Specification cell values
are preserved without silent trimming.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from product_intelligence.domain.models import ProductIdentity
from product_intelligence.research.enterprise_ssd import (
    ENTERPRISE_SSD_SCHEMA,
)
from product_intelligence.research.specifications import (
    SourceAuthority,
    SpecificationObservation,
)


# ---------------------------------------------------------------------------
# Bounded demonstrated label grammar (replaces generic prefix matching)
# ---------------------------------------------------------------------------
# Only the six exact row meanings demonstrated by the real Seagate
# Nytro 5550/5350 datasheet are mapped here. Footnote formatting
# (superscript numbers) is handled by allowing bounded trailing
# punctuation/digits after the structural core.
#
# Each entry maps a normalized-label regex -> (schema_key, unit).
# The regex matches the ENTIRE normalized label, not just a prefix.

class _RowGrammarEntry:
    """One recognized datasheet row label with bounded regex."""
    regex: "re.Pattern[str]"
    schema_key: str
    unit: str | None


#: Bounded grammar — only demonstrated labels
_ROW_GRAMMAR: list[_RowGrammarEntry] = []


def _register_grammar(pattern: str, schema_key: str, unit: str | None) -> None:
    entry = _RowGrammarEntry()
    entry.regex = re.compile(f"^{pattern}$")
    entry.schema_key = schema_key
    entry.unit = unit
    _ROW_GRAMMAR.append(entry)


# Capacity row — unit is part of the cell value
_register_grammar(r"capacity(?:\s*[\u2070-\u2079\d]*)?", "capacity", None)

# Sequential throughput — row header defines unit
_register_grammar(
    r"sequential read\s+\(mb/s\)\s+sustained\s*,\s*128kb(?:[\u2070-\u2079\d]*)?",
    "sequential_read", "MB/s",
)
_register_grammar(
    r"sequential write\s+\(mb/s\)\s+sustained\s*,\s*128kb(?:[\u2070-\u2079\d]*)?",
    "sequential_write", "MB/s",
)

# Random IOPS — row header defines unit
_register_grammar(
    r"random read\s+\(iops\)\s+sustained\s*,\s*4kb(?:[\u2070-\u2079\d]*)?",
    "random_read_iops", "IOPS",
)
_register_grammar(
    r"random write\s+\(iops\)\s+sustained\s*,\s*4kb(?:[\u2070-\u2079\d]*)?",
    "random_write_iops", "IOPS",
)

# Endurance — DWPD normalizer accepts plain numeric
_register_grammar(
    r"lifetime endurance\s+\(drive writes per day\)(?:[\u2070-\u2079\d]*)?",
    "endurance_dwpd", None,
)

# Allowlist: exactly the six 6D v1 fields
_ALLOWED_SCHEMA_KEYS: frozenset[str] = frozenset({
    "capacity",
    "sequential_read",
    "sequential_write",
    "random_read_iops",
    "random_write_iops",
    "endurance_dwpd",
})


# ---------------------------------------------------------------------------
# Row label normalization
# ---------------------------------------------------------------------------


def _normalize_label(raw_label: str) -> str:
    """Normalize a raw row label for grammar lookup.

    Strip whitespace, lowercase, collapse internal whitespace.
    """
    return " ".join(raw_label.strip().lower().split())


# ---------------------------------------------------------------------------
# Row label resolution (bounded grammar)
# ---------------------------------------------------------------------------


def _resolve_row_label(raw_label: str) -> tuple[_RowGrammarEntry, str] | None:
    """Resolve a raw row label to a recognized grammar entry.

    Uses exact regex matching against the bounded demonstrated label grammar.
    Returns (entry, schema_key) if matched, or None if no grammar entry matches.

    No prefix matching. The entire normalized label must match one grammar
    entry's regex.
    """
    normalized = _normalize_label(raw_label)

    for entry in _ROW_GRAMMAR:
        if entry.regex.match(normalized):
            return (entry, entry.schema_key)

    return None


# ---------------------------------------------------------------------------
# Model-identification row detection — bounded grammar
# ---------------------------------------------------------------------------
# Only the three exact demonstrated model-identification row forms
# from the real Seagate Nytro 5550/5350 datasheet are recognized.
# Bounded footnote/superscript variants allowed (e.g. "Model1", "Model²").
#
# Adversarial rows like "Recommended Model", "Controller Model",
# "Model Notes" are NOT recognized.

_MODEL_ROW_LABELS: frozenset[str] = frozenset({
    "standard model",
    "sed model",
    "fips 140-3/common criteria model",
})


def _is_model_row(raw_label: str) -> bool:
    """Check whether a row label is a model-identification row.

    Only the three exact demonstrated forms are accepted:
        Standard Model
        SED Model (with optional footnote marker)
        FIPS 140-3/Common Criteria Model (with optional footnote marker)

    Arbitrary strings containing "model" are NOT accepted.
    """
    normalized = _normalize_label(raw_label)
    # Strip trailing footnote/superscript digits from the normalized form
    stripped = re.sub(r'\s*[\u2070-\u2079\d]+$', '', normalized)
    return stripped in _MODEL_ROW_LABELS


# ---------------------------------------------------------------------------
# Unit incorporation
# ---------------------------------------------------------------------------


def _incorporate_row_unit(cell_value: str, row_unit: str | None) -> str:
    """Incorporate a row-defined unit into a cell value if the cell lacks it.

    If the cell already contains the unit (e.g. "7400MB/s" already has
    "MB/s"), return it as-is. If the cell is a bare number, append the
    unit with a space (e.g. "7200" + " MB/s" -> "7200 MB/s").

    This preserves the raw cell when the PDF happens to include the unit
    in the cell, and adds structural evidence when the table's row header
    defines the unit for every cell.
    """
    if row_unit is None:
        return cell_value

    # Use the exact cell value (not stripped) for unit check
    if row_unit in cell_value:
        return cell_value

    # Unit not in cell — strip only for the appended form
    stripped = cell_value.strip()
    if not stripped:
        return cell_value

    return f"{stripped} {row_unit}"


# ---------------------------------------------------------------------------
# MPN -> column binding (single table)
# ---------------------------------------------------------------------------


def _find_mpn_column(
    table: list[list[str | None]],
    mpn: str,
) -> tuple[int, int] | None:
    """Find the exact (row_index, column_index) of an MPN in model rows.

    Searches model-identification rows (Standard Model, SED Model, etc.)
    for an EXACT match to the target MPN.

    MPN comparison is EXACT: no .strip() on the cell text before comparison.
    Whitespace-mutated MPN cells do NOT match.

    Returns (row_index, column_index) if found exactly once, or None if
    not found or found ambiguously (more than one match).

    Raises ValueError if found more than once (ambiguous MPN).
    """
    matches: list[tuple[int, int]] = []

    for row_idx, row in enumerate(table):
        if not row:
            continue
        # Check if this is a model-identification row
        label = (row[0] or "")
        if not _is_model_row(label):
            continue

        # Search columns (skip column 0 which is the label)
        for col_idx in range(1, len(row)):
            cell = row[col_idx] or ""
            # EXACT raw MPN equality — no normalization, no strip
            if cell == mpn:
                matches.append((row_idx, col_idx))

    if not matches:
        return None

    if len(matches) > 1:
        raise ValueError(
            f"MPN '{mpn}' found ambiguously in {len(matches)} locations: "
            f"{matches}. Failing closed — cannot determine unique column."
        )

    return matches[0]


# ---------------------------------------------------------------------------
# Global MPN uniqueness across ALL tables (whole-PDF binding)
# ---------------------------------------------------------------------------


def _find_mpn_column_global(
    all_tables: list[tuple[int, int, list[list[str | None]]]],
    mpn: str,
) -> tuple[int, int, int, int, int] | None:
    """Find the exact MPN column binding across ALL tables in a document.

    Parameters
    ----------
    all_tables : list of (page_idx, table_idx, table_data)
        All extracted tables, each bound to its page + table index.
    mpn : str
        The exact target MPN.

    Returns
    -------
    (list_index, page_idx, table_idx, row_idx, col_idx) if found exactly once globally,
    or None if not found.

    Raises
    ------
    ValueError
        If MPN appears in more than one table/column globally (fail closed).
    """
    all_matches: list[tuple[int, int, int, int, int]] = []

    for list_idx, (page_idx, table_idx, table) in enumerate(all_tables):
        try:
            result = _find_mpn_column(table, mpn)
            if result is not None:
                row_idx, col_idx = result
                all_matches.append((list_idx, page_idx, table_idx, row_idx, col_idx))
        except ValueError:
            raise ValueError(
                f"MPN '{mpn}' is ambiguous within a single table "
                f"at page[{page_idx}][table{table_idx}]. Failing closed."
            )

    if not all_matches:
        return None

    if len(all_matches) > 1:
        raise ValueError(
            f"MPN '{mpn}' found in {len(all_matches)} table locations globally: "
            f"{[(m[1], m[2]) for m in all_matches]}. "
            "Failing closed — whole-PDF MPN uniqueness violated."
        )

    # Return (list_index, page_idx, table_idx, row_idx, col_idx)
    match = all_matches[0]
    return (match[0], match[1], match[2], match[3], match[4])


# ---------------------------------------------------------------------------
# Row value extraction for a fixed column
# ---------------------------------------------------------------------------


def _extract_value_for_row(
    table: list[list[str | None]],
    col_idx: int,
    row_label_raw: str,
    entry: _RowGrammarEntry,
) -> str | None:
    """Extract the cell value at the intersection of a recognized row and column.

    Scans the table for a row whose label matches the given raw_label.
    Returns the raw cell value if found, or None if the row is absent.

    If the entry defines a unit and the cell lacks it, the unit
    is incorporated into the returned value.

    Raw cell value is NOT silently stripped. The exact parser cell text
    is preserved as evidence.
    """
    target_normalized = _normalize_label(row_label_raw)

    for row in table:
        if not row:
            continue
        label = (row[0] or "")
        if _normalize_label(label) == target_normalized:
            if col_idx < len(row):
                cell = row[col_idx]
                if cell is None:
                    return None
                # Check blank by stripped form but preserve exact value
                if not cell.strip():
                    return None
                return _incorporate_row_unit(cell, entry.unit)

    return None


# ---------------------------------------------------------------------------
# Public extraction API (single table — backward compatible)
# ---------------------------------------------------------------------------


def extract_datasheet_observations(
    *,
    product_identity: ProductIdentity,
    table: list[list[str | None]],
    table_page: int,
    table_index: int,
    source_name: str,
    source_url: str,
    retrieved_at: datetime,
    source_authority: SourceAuthority,
) -> list[SpecificationObservation]:
    """Extract specification observations from one datasheet table for one MPN.

    PURE function. Receives already-extracted table data and provenance.
    Does NOT fetch, parse PDFs, open files, or call any provider.

    The table is expected to be in row-major order where:
        - row[0] is the row label / specification name
        - row[1:] are the column values for each product model

    MPN -> column binding:
        1. Locate exact MPN in a model-identification row
        2. Use that column for all six specification rows
        3. If MPN not found -> return empty list (abstention)
        4. If MPN found ambiguously -> raise ValueError (fail closed)

    Parameters
    ----------
    product_identity : ProductIdentity
        Must be established (is_established == True).
    table : list of list of str | None
        Extracted table data (rows x columns).
    table_page : int
        0-based page index where this table appears.
    table_index : int
        0-based table index on that page.
    source_name : str
        Human-readable source name.
    source_url : str
        The actual URL the PDF came from.
    retrieved_at : datetime
        Timezone-aware retrieval timestamp.
    source_authority : SourceAuthority
        Explicitly supplied authority tier.

    Returns
    -------
    list[SpecificationObservation]
        Raw specification observations (may be empty if MPN not found).

    Raises
    ------
    ValueError
        If MPN is found ambiguously (more than once in model rows).
        Programming error if product_identity is not established.
    """
    if not product_identity.is_established:
        raise ValueError(
            "extract_datasheet_observations requires an established "
            f"ProductIdentity (match_type={product_identity.match_type.value})"
        )

    target_mpn = product_identity.manufacturer_part_number
    if not target_mpn:
        return []

    # Step 1: Find the exact MPN column
    location = _find_mpn_column(table, target_mpn)
    if location is None:
        # MPN not found in this table -> abstain (zero observations)
        return []

    model_row_idx, col_idx = location

    # Step 2: Extract the six recognized specification rows
    observations: list[SpecificationObservation] = []
    seen_keys: set[str] = set()

    for row_idx, row in enumerate(table):
        if not row:
            continue
        label = (row[0] or "")
        if not label:
            continue

        resolution = _resolve_row_label(label)
        if resolution is None:
            continue

        entry, schema_key = resolution
        if schema_key not in _ALLOWED_SCHEMA_KEYS:
            continue

        if schema_key in seen_keys:
            continue
        seen_keys.add(schema_key)

        value = _extract_value_for_row(table, col_idx, label, entry)
        if value is None:
            continue

        definition = ENTERPRISE_SSD_SCHEMA.definitions.get(schema_key)
        if definition is None:
            continue

        raw_ref = (
            f"pdf_page[{table_page}]"
            f"[table{table_index}]"
            f".row[model_{model_row_idx}:col_{col_idx}]"
        )

        observations.append(SpecificationObservation(
            product_identity=product_identity,
            definition=definition,
            source_name=source_name,
            source_url=source_url,
            retrieved_at=retrieved_at,
            raw_value=value,
            source_authority=source_authority,
            raw_reference=raw_ref,
        ))

    return observations


# ---------------------------------------------------------------------------
# Public extraction API (whole document — global MPN uniqueness)
# ---------------------------------------------------------------------------


def extract_datasheet_observations_from_document(
    *,
    product_identity: ProductIdentity,
    all_tables: list[tuple[int, int, list[list[str | None]]]],
    source_name: str,
    source_url: str,
    retrieved_at: datetime,
    source_authority: SourceAuthority,
) -> list[SpecificationObservation]:
    """Extract specification observations from all tables, enforcing global MPN uniqueness.

    PURE function. Receives all extracted tables from the document, each
    bound to its page + table index, and enforces whole-PDF MPN uniqueness
    before extracting observations from the single matching table.

    If the MPN appears in more than one table/column globally, this raises
    ValueError (fail closed) rather than mixing observations from multiple
    tables.

    Parameters
    ----------
    product_identity : ProductIdentity
        Must be established.
    all_tables : list of (page_idx, table_idx, table_data)
        All extracted tables, each bound to page + table index.
    source_name : str
        Human-readable source name.
    source_url : str
        The actual URL the PDF came from.
    retrieved_at : datetime
        Timezone-aware retrieval timestamp.
    source_authority : SourceAuthority
        Explicitly supplied authority tier.

    Returns
    -------
    list[SpecificationObservation]
        Raw specification observations (may be empty if MPN not found).

    Raises
    ------
    ValueError
        If MPN is found ambiguously across tables globally.
        Programming error if product_identity is not established.
    """
    if not product_identity.is_established:
        raise ValueError(
            "extract_datasheet_observations_from_document requires an established "
            f"ProductIdentity (match_type={product_identity.match_type.value})"
        )

    target_mpn = product_identity.manufacturer_part_number
    if not target_mpn:
        return []

    # Step 1: Global MPN uniqueness check
    location = _find_mpn_column_global(all_tables, target_mpn)
    if location is None:
        return []

    list_idx, page_idx, table_idx, row_idx, col_idx = location

    # Step 2: Extract from the single matching table
    table = all_tables[list_idx][2]
    return extract_datasheet_observations(
        product_identity=product_identity,
        table=table,
        table_page=page_idx,
        table_index=table_idx,
        source_name=source_name,
        source_url=source_url,
        retrieved_at=retrieved_at,
        source_authority=source_authority,
    )
