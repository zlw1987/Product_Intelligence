"""Deterministic canonical serialization + digest helpers for the
Semantic V2 qualification corpus (Q3-A).

Pure standard library. The same rule is used for every digest in the
qualification system so that historical results remain associated with
their exact corpus and contract identity:

* canonical JSON: sorted keys, compact separators, ASCII only;
* SHA-256 hex digest of the UTF-8 encoding of the canonical JSON.

No floats appear anywhere in corpus or report identity data (a float in
a digest input would make the serialization platform-sensitive); every
value that enters a canonical encoding must be JSON-native
(str / int / bool / None / list / dict).
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

__all__ = [
    "UTC_INSTANT_PATTERN",
    "canonically_encode",
    "canonical_sha256",
    "assert_json_native",
]

#: The strict ISO-8601 UTC instant grammar (microsecond precision, 'Z')
#: shared by every identity-bearing timestamp in the qualification system.
UTC_INSTANT_PATTERN: re.Pattern[str] = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z$"
)


def assert_json_native(value: Any, path: str = "$") -> None:
    """Fail closed on any value the canonical encoding cannot represent
    exactly (floats, tuples, sets, bytes, and every other non-JSON-native
    object). Tuples are rejected on purpose: a tuple that should be a
    list is a contract bug, not a serialization detail."""
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        raise ValueError(
            f"{path}: float {value!r} is not allowed in canonical "
            "serialization (digest inputs are JSON-native only)"
        )
    if isinstance(value, (list, tuple, set, frozenset)):
        for i, item in enumerate(value):
            assert_json_native(item, f"{path}[{i}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(
                    f"{path}: non-string dict key {key!r} is not allowed "
                    "in canonical serialization"
                )
            assert_json_native(item, f"{path}.{key}")
        return
    raise ValueError(
        f"{path}: {type(value).__name__} is not JSON-native and cannot "
        "enter a canonical digest"
    )


def canonically_encode(value: Any) -> str:
    """The canonical JSON encoding of one JSON-native value.

    Sorted keys, compact separators, ASCII-only: byte-stable across
    processes, platforms, and Python versions.
    """
    assert_json_native(value)
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )


def canonical_sha256(value: Any) -> str:
    """SHA-256 hex digest of the canonical encoding of ``value``."""
    encoded = canonically_encode(value)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
