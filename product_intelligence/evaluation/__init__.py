"""Evaluation corpus contracts, validation, and loader (PRODUCT-INTEL.0B).

This package is **evaluation infrastructure**, not Product Intelligence runtime
state. It exists so that later phases can be *measured* against a stable
benchmark instead of against whatever the newest implementation happens to
produce.

Boundaries this package keeps:

* standard library plus ``product_intelligence.domain`` only — no Django, no
  ORM, no persistence, no HTTP, no search provider, no LLM provider;
* it reads JSON files from ``evaluation/corpus/`` and never contacts a network,
  including the provenance URLs it carries as data;
* it depends on the domain (to prove every case input is a valid
  ``ResearchRequest``); the domain never depends on it.

What it deliberately does **not** contain: a product resolver, part-number
normalization, identity matching, listing extraction, pricing, or metric
computation. No resolver exists to score, so nothing here scores one. The
metric *definitions* live in ``evaluation/README.md``.
"""

from product_intelligence.evaluation.cases import (
    AuthoritativeProvenance,
    CaseInput,
    EvaluationCase,
    EvaluationCorpus,
    Expectation,
    SyntheticProvenance,
)
from product_intelligence.evaluation.loader import (
    default_corpus_paths,
    load_corpus,
    load_corpus_file,
)
from product_intelligence.evaluation.validation import (
    SUPPORTED_CORPUS_VERSION,
    CorpusValidationError,
    build_case,
    build_corpus_file,
    validate_corpus,
)
from product_intelligence.evaluation.vocabulary import (
    ABSTAINING_RESOLUTIONS,
    AUTHORITATIVE_PROVENANCE_KINDS,
    REQUIRED_SYNTHETIC_CHALLENGE_TAGS,
    CaseKind,
    ChallengeTag,
    ExpectedResolution,
    ProvenanceKind,
)

__all__ = [
    "ABSTAINING_RESOLUTIONS",
    "AUTHORITATIVE_PROVENANCE_KINDS",
    "AuthoritativeProvenance",
    "CaseInput",
    "CaseKind",
    "ChallengeTag",
    "CorpusValidationError",
    "EvaluationCase",
    "EvaluationCorpus",
    "Expectation",
    "ExpectedResolution",
    "ProvenanceKind",
    "REQUIRED_SYNTHETIC_CHALLENGE_TAGS",
    "SUPPORTED_CORPUS_VERSION",
    "SyntheticProvenance",
    "build_case",
    "build_corpus_file",
    "default_corpus_paths",
    "load_corpus",
    "load_corpus_file",
    "validate_corpus",
]
