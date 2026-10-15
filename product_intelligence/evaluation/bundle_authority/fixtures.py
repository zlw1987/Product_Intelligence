"""The family case-authoring source + corpus document builder skeleton
(Q3-C-C1; design sections 4.2 / 9.3).

The semantic family's auditable-source pattern, adopted: the declarative
case set runs the exact family builder chain, and regeneration from this
module must reproduce the sealed corpus artifact byte-for-byte (the P1
regeneration property, family version).

C1 scope (design section 9.3): the case set is EMPTY (the 0-case
skeleton seal — the integrity property the C1 acceptance demonstrates:
a 0-case corpus builds, seals, loads, and regenerates byte-for-byte).
C1 creates NO qualification cases and NO labels; the independently
labeled v1.0.0 population is the separately approved C2 deliverable,
authored through the two-identity workflow of design section 8.2 under
the label independence contract of design section 4.6 (which C2's own
guard test enforces over this module — the import prohibition: this
file may import the frozen P2 extraction module (evidence acquisition)
and the frozen S2-C / domain types (case construction), but NOT
``semantic_authority_fu4`` / ``semantic_decision_v2_fu4`` /
``semantic_authority_v2`` / ``semantic_authority_fu3`` (the
label-determining derivations)).

This module is deliberately research-independent at C1: it imports only
the family's own ``corpus`` module (the digest + identity primitives).
The C2 population adds the frozen P2 / S2-C imports that case
construction requires — the C1 import-scan test pins this module's
current import set, and the C2 guard pins the prohibition set.
"""

from __future__ import annotations

from typing import Any, Final

from product_intelligence.evaluation.bundle_authority import corpus

__all__ = [
    "CASES",
    "build_corpus_document",
    "corpus_bytes",
    "corpus_document_bytes",
]

#: The declared family case set — EMPTY at C1 (the 0-case skeleton
#: seal; the C2 deliverable populates it with the section 5 matrix).
CASES: Final[tuple[dict[str, Any], ...]] = ()

#: The family artifact file names (the storage layout of design
#: section 4.2).
CORPUS_FILE_NAME: Final[str] = "corpus_v1.json"
MANIFEST_FILE_NAME: Final[str] = "manifest_v1.json"


def build_corpus_document(
    created_utc: str,
    cases: tuple[dict[str, Any], ...] = CASES,
    label_revisions: tuple[dict[str, Any], ...] = (),
) -> dict[str, Any]:
    """Build the family corpus document over the declared case set.

    Each declarative case document must be the exact sealed shape minus
    its ``case_digest`` (the builder computes and inserts the per-case
    digest — a pre-sealed ``case_digest`` is verified, never trusted
    blindly). The corpus digest covers the full state view (all
    per-case digests + version + binding + id + schema + created +
    label revisions; design section 4.2). The case list is sealed in
    case-id order (the deterministic sealing convention — the corpus
    digest then binds the order: a reorder without re-sealing is a
    detected tamper).
    """
    corpus.utc_instant(
        created_utc, "fixtures: created_utc"
    )  # the builder's own strictness
    if cases:
        ordered = sorted(cases, key=lambda case: case["case_id"])
        sealed_cases: list[dict[str, Any]] = []
        for case in ordered:
            sealed = dict(case)
            if "case_digest" in sealed:
                # Verify any pre-computed digest the authoring source
                # carries (never trust a declared digest blindly).
                expected = corpus.case_state_digest(sealed)
                if expected != sealed["case_digest"]:
                    raise corpus.BundleAuthorityDigestError(
                        "DIGEST_INTEGRITY",
                        f"case {sealed['case_id']}: the declared "
                        "case_digest does not verify over the "
                        "authoring case document",
                    )
            else:
                sealed["case_digest"] = corpus.case_state_digest(sealed)
            sealed_cases.append(sealed)
    else:
        sealed_cases = []
    document: dict[str, Any] = {
        "corpus_id": corpus.CORPUS_ID,
        "corpus_schema_version": corpus.CORPUS_SCHEMA_VERSION,
        "corpus_version": corpus.FIRST_CORPUS_VERSION,
        "corpus_label": corpus.CORPUS_LABEL,
        "created_utc": created_utc,
        "semantic_contract_binding": list(corpus.FU4_BINDING),
        "cases": sealed_cases,
        "label_revisions": list(label_revisions),
    }
    document["corpus_digest"] = corpus.corpus_state_digest(document)
    return document


def corpus_bytes(document: dict[str, Any]) -> bytes:
    """The stable canonical serialization of one corpus document (the
    house form: sorted keys, indent 1, ASCII, trailing newline — the
    byte-for-byte regeneration target)."""
    return corpus.canonically_serialize(document)


def corpus_document_bytes(
    created_utc: str,
    cases: tuple[dict[str, Any], ...] = CASES,
    label_revisions: tuple[dict[str, Any], ...] = (),
) -> bytes:
    """Build + serialize in one step (the CLI corpus-build target)."""
    return corpus_bytes(
        build_corpus_document(created_utc, cases, label_revisions)
    )


def build_manifest_bytes(document: dict[str, Any]) -> bytes:
    """The reproducible manifest for one verified corpus document
    (the builder delegates to the family loader's manifest contract)."""
    return corpus.canonically_serialize(
        corpus.build_manifest_document(document)
    )
