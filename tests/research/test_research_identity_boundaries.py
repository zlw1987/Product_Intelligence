"""Architecture guards for the research core (PRODUCT-INTEL.2A).

The research core is the layer most likely to acquire dependencies by
convenience: a database handle "just to look something up", a provider "just to
fetch a candidate", the evaluation corpus "just to check an answer". Each of
those would be a different failure — an engine that cannot be reasoned about
without a database, business logic bound to a vendor, or benchmark answers
leaking into runtime resolution, which is test leakage in its purest form.

Two directions are checked: what the research core may depend on, and who may
depend on it. 2A is a primitive with no candidate source, so nothing wires it
into a run or a page yet, and these guards assert that too.

Deliberately structural. Import inspection answers these questions, so there is
no need for a lexical scan beyond the vendor-name check the other guards already
share.
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# Reused rather than restated, so the lists cannot drift apart.
from tests.domain.test_domain_boundaries import (
    VENDOR_TOKENS,
    _find_tokens,
    _python_files,
    _top_level_imports,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "product_intelligence"
RESEARCH_ROOT = PACKAGE_ROOT / "research"
IDENTITY_MODULE = RESEARCH_ROOT / "identity.py"


# A1-FU2 reviewer-authorized evaluation->research exception (least
# privilege).
#
# The original 2A boundary forbade every product_intelligence.evaluation
# file from importing product_intelligence.research. The promotion-
# regression harness must replay the REAL deterministic identity chain
# (assess_listing_identity) instead of copying it into evaluation, so an
# architecture reviewer authorized a deliberately narrowed exception.
# Reviewer history: A1 introduced a too-broad promotion_regression*
# prefix match (recorded conflict); A1-FU1 authorized the exception and
# exacted it as a two-file allowlist; A1-FU2 tightened it to the single
# file that actually requires the dependency, because
# promotion_regression_cli.py does NOT import research (it consumes the
# harness module) and FU1 had authorized the CLI only IF it actually
# required the dependency. If the CLI or any other evaluation module
# later needs a direct research dependency, that requires a NEW explicit
# architecture-review decision. This is an explicit, reviewer-
# authorized governance decision recorded in
# docs/PRODUCT_INTELLIGENCE_STATUS.md (A1, item 4) and PLAN section 26.16
# (item 7) -- NOT an implementer-authorized redesign. The membership test
# is exact path equality: no prefix, glob, or regex match, so any other
# promotion_regression_* name, in any other location, is outside the
# exception.
PROMOTION_REGRESSION_RESEARCH_EXCEPTION = frozenset(
    {
        "product_intelligence/evaluation/semantic/promotion_regression.py",
    }
)


def _repo_relative_posix(path: Path) -> str | None:
    """Repository-relative POSIX path, or None if not inside the repo."""
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return None


def _is_authorized_research_importer(path: Path) -> bool:
    """True ONLY for the exact allowlisted file above.

    promotion_regression_extra.py, promotion_regression_hack.py, a
    promotion_regression.py in any other directory, or any file outside
    the repository are all outside the exception.
    """
    rel = _repo_relative_posix(path)
    return rel is not None and rel in PROMOTION_REGRESSION_RESEARCH_EXCEPTION


def _imported_modules(path: Path) -> set[str]:
    """Every dotted module name imported by a file, absolute imports only."""
    modules: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            modules.add(node.module)
    return modules


def test_the_research_core_has_source_files_to_check() -> None:
    """Guard against the scans below silently passing on an empty set."""
    assert _python_files(RESEARCH_ROOT)
    assert IDENTITY_MODULE.exists()


@pytest.mark.parametrize("path", _python_files(RESEARCH_ROOT), ids=lambda p: p.name)
def test_the_research_core_imports_only_stdlib_and_the_domain(path: Path) -> None:
    """No framework, no vendor library, no HTTP client, no model client."""
    modules = _top_level_imports(path.read_text(encoding="utf-8"))
    disallowed = {
        module
        for module in modules
        if module != "product_intelligence" and module not in sys.stdlib_module_names
    }

    assert not disallowed, (
        f"{path.name} imports non-stdlib modules {sorted(disallowed)}; the "
        "research core stays free of frameworks and vendors."
    )


@pytest.mark.parametrize("path", _python_files(RESEARCH_ROOT), ids=lambda p: p.name)
def test_the_research_core_imports_no_persistence_provider_or_benchmark(
    path: Path,
) -> None:
    imported = _imported_modules(path)

    for forbidden in (
        "django",
        "product_intelligence.runs",
        "product_intelligence.providers",
        "product_intelligence.evaluation",
        "product_intelligence.web",
    ):
        offending = {
            module
            for module in imported
            if module == forbidden or module.startswith(f"{forbidden}.")
        }
        assert not offending, f"{path.name} imports {sorted(offending)}"


# Modules that reach outside the process: a network stack, a filesystem, a
# database, a subprocess, or the environment. None of them may appear anywhere
# in the research core, which is the durable rule — the core reads nothing,
# fetches nothing, and stores nothing.
#
# `json` and `html.parser` are deliberately **not** here, and that is a
# narrowing made in 3A rather than a relaxation. Both are pure computation over
# a string already held in memory: `json.loads` opens no file and `HTMLParser`
# opens no socket. 2A's version of this list named `json` because nothing in the
# core had a reason to parse anything, so the coarser list cost nothing; 3A's
# deterministic extractor reads JSON-LD blocks out of a document string, which
# is the whole of what it does. The rule the plan and CLAUDE.md actually state
# — "a network or filesystem module" — is what is enforced here. `urllib.parse`
# is absent for the same reason the provider boundary excludes it: splitting a
# URL string is not fetching one.
IO_MODULES = {
    "requests",
    "httpx",
    "urllib.request",
    "urllib.error",
    "urllib.robotparser",
    "urllib3",
    "socket",
    "ssl",
    "http",
    "pathlib",
    "sqlite3",
    "os",
    "shutil",
    "tempfile",
    "subprocess",
    "webbrowser",
}


@pytest.mark.parametrize("path", _python_files(RESEARCH_ROOT), ids=lambda p: p.name)
def test_the_research_core_performs_no_network_or_file_access(path: Path) -> None:
    """The core computes over values it is handed, and reaches nothing."""
    imported = _imported_modules(path) | _top_level_imports(path.read_text(encoding="utf-8"))
    offending = {
        module
        for module in imported
        for forbidden in IO_MODULES
        if module == forbidden or module.startswith(f"{forbidden}.")
    }

    assert not offending, (
        f"{path.name} imports {sorted(offending)}; the research core "
        "reads nothing, fetches nothing, and stores nothing."
    )


def test_the_identity_primitive_still_parses_nothing() -> None:
    """2A's stricter promise, kept for 2A's module specifically.

    The part-number comparison is a pure function of two strings. It has no
    reason to parse a document, a payload, or a URL, and the narrowing above —
    made so 3A's extractor can read JSON-LD — must not quietly widen what
    `identity.py` is allowed to do.
    """
    modules = _top_level_imports(IDENTITY_MODULE.read_text(encoding="utf-8"))

    assert not modules & {"json", "html", "urllib", "xml", "csv", "pickle"}


def test_extraction_computes_no_numbers() -> None:
    """3A observes text. It converts nothing, and it may not acquire the means to.

    `Decimal` in the extractor would be a price becoming a number one layer
    early — before 3B has decided what an unparseable price means and before 3C
    has decided the listing is even about the right product. 3B will import it;
    this module may not.
    """
    extraction = RESEARCH_ROOT / "extraction.py"
    assert extraction.exists()

    modules = _top_level_imports(extraction.read_text(encoding="utf-8"))

    assert not modules & {"decimal", "fractions", "statistics", "numbers", "math"}


@pytest.mark.parametrize("path", _python_files(RESEARCH_ROOT), ids=lambda p: p.name)
def test_the_research_core_names_no_external_vendor(path: Path) -> None:
    found = _find_tokens(path.read_text(encoding="utf-8"), VENDOR_TOKENS)

    assert not found, f"{path.name} references external vendors {found}"


def test_the_research_core_depends_on_the_domain_contracts() -> None:
    """The permitted direction, so the guards above cannot pass vacuously."""
    imported = {
        module for path in _python_files(RESEARCH_ROOT) for module in _imported_modules(path)
    }

    assert any(module.startswith("product_intelligence.domain") for module in imported)


def test_the_domain_does_not_import_the_research_core() -> None:
    """The dependency runs one way: research imports domain, never the reverse."""
    for path in _python_files(PACKAGE_ROOT / "domain"):
        offending = {
            module
            for module in _imported_modules(path)
            if module.startswith("product_intelligence.research")
        }
        assert not offending, f"{path} imports {sorted(offending)}"


@pytest.mark.parametrize(
    "root",
    [PACKAGE_ROOT / "runs", PACKAGE_ROOT / "evaluation"],
    ids=lambda p: p.name,
)
def test_no_outer_layer_is_wired_to_the_identity_primitive_yet(root: Path) -> None:
    """2A supplies a comparison; nothing yet supplies a candidate to compare.

    Persistence and the benchmark are both unchanged by this phase.
    Runtime integration waits for the phase that has real candidate evidence.
    The web layer is excluded from this check because 1B and 4B import
    research contracts (and the codec) for the report view.

    A1-FU2 REVIEWER-AUTHORIZED EXACT-ALLOWLIST EXCEPTION (least
    privilege, tightened from the A1-FU1 two-file allowlist): the
    original 2A evaluation->research boundary was deliberately
    narrowed by an architecture reviewer for EXACTLY ONE promotion-
    regression evaluation module (the harness), named in
    ``PROMOTION_REGRESSION_RESEARCH_EXCEPTION``. The CLI
    (``promotion_regression_cli.py``) is NOT exempt: it does not
    directly depend on research, it consumes the harness module, and a
    future direct research dependency requires a NEW explicit
    architecture-review decision. The exception exists so
    the evaluation harness can exercise the real frozen deterministic
    research chain (``assess_listing_identity``) instead of duplicating
    it. The dependency direction is preserved: the evaluation facility
    imports the research contracts; research never imports the harness
    (the no-production-reference guard in
    ``tests/evaluation/semantic/test_promotion_regression_authority.py``
    enforces that). No prefix/glob/regex match — any other module,
    including future ``promotion_regression_*`` names, is outside the
    exception. The mechanism is locked by
    ``test_promotion_regression_exception_is_an_exact_allowlist``.
    """
    for path in _python_files(root):
        if _is_authorized_research_importer(path):
            continue  # A1-FU2 exact allowlist (see above)
        offending = {
            module
            for module in _imported_modules(path)
            if module.startswith("product_intelligence.research")
        }
        assert not offending, f"{path} imports {sorted(offending)}"


def test_only_promotion_regression_may_wire_research() -> None:
    """The A1-FU2 exception is exactly the one allowlisted file.

    Every OTHER evaluation file must remain research-independent (the
    original 2A-era boundary), and even the excepted file may only
    import research (never execution / runs / web / providers / Django).
    The exception is the explicit reviewer-authorized exact allowlist in
    ``PROMOTION_REGRESSION_RESEARCH_EXCEPTION`` — not a prefix match.
    The existence assertion keeps this test from passing vacuously if an
    allowlisted file is moved or renamed (which would then require an
    explicit reviewer decision, never an implicit match).
    """
    evaluation_root = PACKAGE_ROOT / "evaluation"
    exception_count = 0
    for path in _python_files(evaluation_root):
        imported = _imported_modules(path)
        is_exception = _is_authorized_research_importer(path)
        if is_exception:
            exception_count += 1
            heavy = sorted(
                module
                for module in imported
                if module.startswith(
                    (
                        "product_intelligence.execution",
                        "product_intelligence.runs",
                        "product_intelligence.web",
                        "product_intelligence.providers",
                    )
                )
                or module.split(".")[0] == "django"
            )
            assert not heavy, f"{path} imports {heavy}"
        else:
            offending = sorted(
                module
                for module in imported
                if module.startswith("product_intelligence.research")
            )
            assert not offending, (
                f"{path} imports {offending}; the A1-FU2 exception covers "
                "ONLY the one allowlisted promotion-regression module"
            )
    assert len(PROMOTION_REGRESSION_RESEARCH_EXCEPTION) == 1, (
        "the A1-FU2 least-privilege contract authorizes EXACTLY ONE "
        "evaluation file to import research; any other entry requires a "
        "new explicit reviewer decision"
    )
    assert exception_count == len(PROMOTION_REGRESSION_RESEARCH_EXCEPTION), (
        f"expected exactly the {len(PROMOTION_REGRESSION_RESEARCH_EXCEPTION)} "
        "allowlisted promotion-regression file under evaluation/, found "
        f"{exception_count}; the allowlist must be updated through an "
        "explicit reviewer decision, never implicitly"
    )


def test_promotion_regression_exception_is_an_exact_allowlist() -> None:
    """A1-FU2: the reviewer-authorized exception is EXACTLY ONE file and
    cannot expand implicitly.

    Mechanically demonstrates, against the boundary predicate itself (no
    rogue files are created in the repository):

    A. promotion_regression.py IS authorized — and it currently imports
       product_intelligence.research, so the exception is load-bearing,
       not vestigial;
    B. promotion_regression_cli.py is NOT authorized — under the current
       architecture it does not import research at all (it consumes the
       harness module), so least privilege grants it no exception;
    C. if promotion_regression_cli.py begins importing research in the
       future, the architecture boundary FAILS: this test's predicate
       assertion (B) proves the CLI is unauthorized, so the boundary
       scan in
       ``test_no_outer_layer_is_wired_to_the_identity_primitive_yet`` no
       longer skips it — until a new explicit reviewer decision adds
       that dependency to the allowlist;
    D. arbitrary OTHER promotion_regression_* names — in the same
       directory, in any other directory, or outside the repository —
       are NOT covered (no prefix/glob/regex matching);
    E. every real evaluation file importing product_intelligence.
       research belongs to the exact one-file allowlist (today: the
       harness only).
    """
    evaluation_root = PACKAGE_ROOT / "evaluation"
    semantic = evaluation_root / "semantic"
    harness = semantic / "promotion_regression.py"
    cli = semantic / "promotion_regression_cli.py"

    # The allowlist is exactly the ONE reviewer-authorized file, and it
    # exists: a move or rename must fail this test rather than silently
    # drop out of the exception or of the boundary scan.
    assert PROMOTION_REGRESSION_RESEARCH_EXCEPTION == {
        _repo_relative_posix(harness),
    }
    assert len(PROMOTION_REGRESSION_RESEARCH_EXCEPTION) == 1
    assert harness.is_file()
    assert cli.is_file()

    # A. The harness is authorized and uses the dependency today.
    assert _is_authorized_research_importer(harness)
    assert any(
        module.startswith("product_intelligence.research")
        for module in _imported_modules(harness)
    )

    # B. The CLI is NOT on the allowlist and does not import research:
    # under the current architecture it consumes the harness module, so
    # it requires no exception (C is a direct consequence of B).
    assert not _is_authorized_research_importer(cli)
    assert not any(
        module.startswith("product_intelligence.research")
        for module in _imported_modules(cli)
    )

    # D. No prefix sibling, no other directory, no same name elsewhere,
    # and nothing outside the repository is covered.
    not_covered = [
        semantic / name
        for name in (
            "promotion_regression_extra.py",
            "promotion_regression_hack.py",
            "promotion_regression_temp.py",
            "promotion_regression_database.py",
            "promotion_regression_anything.py",
            "promotion_regression_cli_extra.py",
        )
    ]
    not_covered += [
        evaluation_root / "promotion_regression.py",
        semantic / "nested" / "promotion_regression.py",
        REPO_ROOT / "elsewhere" / "promotion_regression.py",
        REPO_ROOT.parent / "promotion_regression.py",
    ]
    for path in not_covered:
        assert not _is_authorized_research_importer(path), path

    # E. Any evaluation file that imports research must be on the exact
    # allowlist: today that is the harness only, and every unrelated
    # evaluation module (runner, cli, comparison, evaluator, loader, ...)
    # is outside the exception.
    for path in _python_files(evaluation_root):
        if any(
            module.startswith("product_intelligence.research")
            for module in _imported_modules(path)
        ):
            assert _is_authorized_research_importer(path), path
    for name in ("runner.py", "cli.py", "comparison.py", "evaluator.py", "loader.py"):
        assert not _is_authorized_research_importer(semantic / name), name


def test_the_identity_primitive_adds_no_model_and_no_migration() -> None:
    from django.apps import apps

    assert not list(RESEARCH_ROOT.rglob("models.py"))
    assert not list(RESEARCH_ROOT.rglob("migrations"))
    expected = {"runs.ResearchRun", "runs.PriceIntelligenceSnapshot", "runs.ExecutionEvidenceRecord", "runs.AiAssistedReviewCandidate", "runs.ComparableResearchExecution", "runs.ResearchSupplementSnapshot", "runs.ResearchFxSnapshot", "runs.ResearchMicronAliasSnapshot", "runs.FxObservationStore"}
    assert {model._meta.label for model in apps.get_models()} == expected


def test_importing_the_research_core_pulls_in_no_third_party_dependency() -> None:
    """The structural half: import it in a clean interpreter and look.

    A transitive Django import would mean the engine could not be exercised
    without a database, which is the specific thing `research/` exists to avoid.
    """
    script = (
        "import sys, json\n"
        "before = set(sys.modules)\n"
        "import product_intelligence.research\n"
        "loaded = {name.split('.')[0] for name in set(sys.modules) - before}\n"
        "third_party = sorted(\n"
        "    name for name in loaded\n"
        "    if not name.startswith('_')\n"
        "    and name != 'product_intelligence'\n"
        "    and name not in sys.stdlib_module_names\n"
        ")\n"
        "print(json.dumps(third_party))\n"
    )
    env = dict(os.environ, PYTHONPATH=str(REPO_ROOT))

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert json.loads(result.stdout.strip().splitlines()[-1]) == []


def test_the_research_core_exports_the_phase_2a_primitive() -> None:
    import product_intelligence.research as research

    assert {
        "PartNumberMatchAssessment",
        "compare_part_numbers",
        "compare_request_to_candidate",
        "normalize_part_number",
    } <= set(research.__all__)
