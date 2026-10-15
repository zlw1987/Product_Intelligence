"""The family offline CLI (Q3-C-C1; design section 9.3).

Exactly three commands, all offline (no network, no clock, no model):

* ``corpus-build`` — build the corpus document from the declared
  fixtures case set + the reproducible manifest, writing both
  artifacts in the stable canonical serialization (the byte-for-byte
  regeneration target; the C2 seal is this command's output);
* ``corpus-digest`` — load + strictly verify a sealed corpus file and
  print its verified corpus digest;
* ``corpus-manifest`` — load + strictly verify a sealed corpus file
  and write the reproducible manifest (or verify the committed one).

The builder takes an EXPLICIT ``--created-utc`` (the record reads no
clock — the sealing instant is the operator's recorded input, the
semantic family's convention).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _write_json(path: Path, document: dict) -> None:
    from product_intelligence.evaluation.bundle_authority.corpus import (
        canonically_serialize,
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonically_serialize(document))


def _cmd_corpus_build(args: argparse.Namespace) -> int:
    from product_intelligence.evaluation.bundle_authority.corpus import (
        BundleAuthorityCorpusError,
        build_manifest_document,
        verify_corpus_document,
    )
    from product_intelligence.evaluation.bundle_authority.fixtures import (
        CASES,
        build_corpus_document,
    )

    out_dir = Path(args.out_dir)
    try:
        corpus_doc = build_corpus_document(args.created_utc, CASES)
        verify_corpus_document(corpus_doc)
        manifest = build_manifest_document(corpus_doc)
        _write_json(out_dir / "corpus_v1.json", corpus_doc)
        _write_json(out_dir / "manifest_v1.json", manifest)
    except BundleAuthorityCorpusError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"corpus digest: {corpus_doc['corpus_digest']}")
    print(f"manifest digest: {manifest['manifest_digest']}")
    print(f"cases: {len(corpus_doc['cases'])}")
    return 0


def _cmd_corpus_digest(args: argparse.Namespace) -> int:
    from product_intelligence.evaluation.bundle_authority.corpus import (
        BundleAuthorityCorpusError,
        load_corpus,
    )

    try:
        corpus = load_corpus(args.corpus)
    except BundleAuthorityCorpusError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(corpus.corpus_digest)
    return 0


def _cmd_corpus_manifest(args: argparse.Namespace) -> int:
    from product_intelligence.evaluation.bundle_authority.corpus import (
        BundleAuthorityCorpusError,
        build_manifest_document,
        load_corpus,
        verify_manifest,
    )

    try:
        corpus = load_corpus(args.corpus)
    except BundleAuthorityCorpusError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.out:
        manifest = build_manifest_document(corpus.document)
        _write_json(Path(args.out), manifest)
        print(f"manifest digest: {manifest['manifest_digest']}")
    else:
        import json

        manifest = json.loads(Path(args.verify).read_text(encoding="utf-8"))
        verify_manifest(corpus, manifest)
        print(f"manifest verified: {manifest['manifest_digest']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bundle-authority-corpus",
        description="The FU4 Bundle authority qualification corpus "
        "family CLI (offline only).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_build = sub.add_parser(
        "corpus-build", help="build the corpus + manifest from the fixtures"
    )
    p_build.add_argument("--out-dir", required=True)
    p_build.add_argument(
        "--created-utc",
        required=True,
        help="the explicit sealing instant (ISO-8601 UTC 'Z')",
    )
    p_build.set_defaults(func=_cmd_corpus_build)

    p_digest = sub.add_parser(
        "corpus-digest", help="verify a sealed corpus + print its digest"
    )
    p_digest.add_argument("--corpus", required=True)
    p_digest.set_defaults(func=_cmd_corpus_digest)

    p_manifest = sub.add_parser(
        "corpus-manifest",
        help="write the reproducible manifest for a sealed corpus "
        "(or verify the committed one)",
    )
    p_manifest.add_argument("--corpus", required=True)
    p_manifest.add_argument("--out", default=None)
    p_manifest.add_argument("--verify", default=None)
    p_manifest.set_defaults(func=_cmd_corpus_manifest)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
