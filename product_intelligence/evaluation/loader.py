"""Loading the evaluation corpus from disk.

One loader, so that later phases measure themselves against the same corpus in
the same way instead of each inventing its own JSON parsing — and so that any
change to the corpus format has exactly one place to be handled.

The only I/O performed anywhere in this package is reading the corpus files
named here. No network call is made, and the provenance URLs the corpus carries
are data, never requests.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Sequence

from product_intelligence.evaluation.cases import EvaluationCase, EvaluationCorpus
from product_intelligence.evaluation.validation import (
    CorpusValidationError,
    build_corpus_file,
    validate_corpus,
)

# The corpus lives outside the Python package, at the repository root, because
# it is reviewable reference data rather than application code — see
# evaluation/README.md. Resolving it relative to this file keeps the tests and
# any future evaluation run independent of the working directory.
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIRECTORY = REPOSITORY_ROOT / "evaluation" / "corpus"

REAL_VERIFIED_CORPUS_PATH = CORPUS_DIRECTORY / "real_verified.json"
SYNTHETIC_CORPUS_PATH = CORPUS_DIRECTORY / "synthetic.json"


def default_corpus_paths() -> tuple[Path, ...]:
    """The corpus files that make up the standard evaluation set."""
    return (REAL_VERIFIED_CORPUS_PATH, SYNTHETIC_CORPUS_PATH)


def load_corpus_file(path: Path) -> tuple[EvaluationCase, ...]:
    """Read and validate one corpus file.

    Returns its cases. Cross-case invariants (unique ids, deliberate identity
    sharing, derivation references) need the whole corpus and are checked by
    ``load_corpus``.
    """
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as error:
        raise CorpusValidationError(f"{path}: cannot be read ({error})") from error

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise CorpusValidationError(f"{path}: is not valid JSON ({error})") from error

    return build_corpus_file(payload, where=str(Path(path).name))


def load_corpus(paths: Iterable[Path] | None = None) -> EvaluationCorpus:
    """Load, validate, and return the evaluation corpus.

    ``paths`` defaults to :func:`default_corpus_paths`. Raises
    ``CorpusValidationError`` if any file or any invariant is invalid — a
    partially valid corpus is never returned, because a benchmark that silently
    dropped its hardest cases would still look like it passed.
    """
    resolved: Sequence[Path] = tuple(default_corpus_paths() if paths is None else paths)

    cases: list[EvaluationCase] = []
    for path in resolved:
        cases.extend(load_corpus_file(path))

    return validate_corpus(cases)
