"""VREF-R1-2 — provider/network boundary + exact surface pins (AST).

Covers the approved R1-2 Stage A surface pin (design section 11 row 2 —
the in-place evolution of the R0
``TestNoRecoverySurface::test_no_vendor_refresh_execution_module_exists``
node, mirrored here at the AST level) and the design section 12 row 15/
row 19 AST guards for the two NEW production modules:

* ``product_intelligence/execution/vendor_refresh.py`` — the
  POST-CLAIM execution core: the exact import allowlist; NO provider
  class in any form (I13); NO claim reference in any form (FU1-F1);
  NO claim error caught in any form (FU3-F1); the terminal-CAS catch
  shape pinned read-only (no second terminal write, no retry, no
  factory/lookup call inside a CAS/DB-error handler); the factory is
  invoked exactly once; no transaction surface (I10); no network-I/O
  module.
* ``product_intelligence/execution/vendor_refresh_runtime.py`` — the
  ONLY R1 module importing ``providers.internal_vendor``
  (function-level, as factory source); it constructs nothing itself
  (O9) and delegates exactly once.
* the frozen surfaces stay byte-identical to the approved R1-1
  implementation base SHA ``6c123229bf075d72704f233f7176651656540cf9``
  (task section 2: R1-1 source byte-identical; no other production
  file changes).
* no executable command or recovery surface exists at R1-2 (R1-3
  command and R1-4 recovery are not authorized here).
* the ``product_intelligence.execution`` public export surface gains
  exactly the three approved names (additive).
"""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import product_intelligence.execution.vendor_refresh as core
import product_intelligence.execution.vendor_refresh_runtime as runtime
import pytest
from django.test import TestCase

PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "product_intelligence"
EXECUTION_ROOT = PACKAGE_ROOT / "execution"
CORE_PATH = EXECUTION_ROOT / "vendor_refresh.py"
RUNTIME_PATH = EXECUTION_ROOT / "vendor_refresh_runtime.py"
HELPER_PATH = EXECUTION_ROOT / "vendor_commercial_binding.py"

_FORBIDDEN_SURFACE_TOKENS = (
    "reclaim",
    "reset",
    "retry",
    "recover",
    "recovery",
    "force",
    "stale",
    "reassign",
    "resurrect",
    "interrupt",
)

# The approved executor names carry "claimed" (post-claim semantics,
# design section 3.2); they are NOT references to the claim primitive.
_APPROVED_CLAIMED_EXECUTOR_NAMES = {
    "execute_claimed_vendor_refresh",
    "execute_claimed_vendor_refresh_with_default_providers",
}


def _claim_identifier_offenders(tree: ast.Module) -> list[str]:
    """Identifiers containing 'claim' that are not the approved
    post-claim executor names (FU1-F1: no reference to the claim
    primitive / claim errors in any form)."""
    offenders: list[str] = []
    for node in ast.walk(tree):
        identifiers: list[str] = []
        if isinstance(node, ast.Name):
            identifiers.append(node.id)
        elif isinstance(node, ast.Attribute):
            identifiers.append(node.attr)
        elif isinstance(node, ast.ImportFrom):
            identifiers.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            identifiers.extend(
                (alias.name or alias.asname or "") for alias in node.names
            )
        for identifier in identifiers:
            lowered = identifier.lower()
            if "claim" in lowered and identifier not in _APPROVED_CLAIMED_EXECUTOR_NAMES:
                offenders.append(identifier)
    return offenders


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def _imported_modules(tree: ast.Module) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)
    return modules


def _function_names(tree: ast.Module) -> list[str]:
    return [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]


# ---------------------------------------------------------------------------
# Exact surface pins (Stage A, AST level)
# ---------------------------------------------------------------------------


class TestStageASurfacePin(TestCase):
    """The approved R1-2 execution surface, pinned exactly."""

    def test_execution_vendor_refresh_glob_is_exactly_the_approved_pair(self) -> None:
        globbed = {p.name for p in EXECUTION_ROOT.glob("vendor_refresh*.py")}
        assert globbed == {"vendor_refresh.py", "vendor_refresh_runtime.py"}

    def test_refresh_feature_module_set_is_exactly_the_approved_three(self) -> None:
        feature = {p.name for p in EXECUTION_ROOT.glob("vendor_*.py")}
        assert feature == {
            "vendor_commercial_binding.py",
            "vendor_refresh.py",
            "vendor_refresh_runtime.py",
        }

    def test_no_unapproved_execution_or_recovery_module(self) -> None:
        assert not list(PACKAGE_ROOT.rglob("vendor_refresh_recovery.py")), (
            "the R1-4 recovery module must not exist while R1-4 is BLOCKED"
        )
        for path in EXECUTION_ROOT.glob("*.py"):
            lowered = path.name.lower()
            assert not any(token in lowered for token in _FORBIDDEN_SURFACE_TOKENS), (
                f"execution module name carries a forbidden surface token: {path.name}"
            )

    def test_no_vendor_refresh_command_or_recovery_symbol(self) -> None:
        """The EXACT approved R1-3 command surface (VREF-R1-3, in-place
        evolution of the R1-2 command-absence pin; node ID preserved):
        the only ``vendor_refresh*`` command file is
        ``vendor_refresh.py`` (R1-4 recovery remains prohibited — any
        additional vendor_refresh-prefixed command, recovery command,
        or recovery symbol fails closed). The runs public-export pin
        (exactly the thirteen frozen R0 VendorRefresh-related names) is
        preserved unchanged.
        """
        commands_root = PACKAGE_ROOT / "runs" / "management" / "commands"
        assert commands_root.is_dir()
        assert {
            p.name for p in commands_root.glob("vendor_refresh*")
        } == {"vendor_refresh.py"}
        import product_intelligence.runs as runs_pkg

        vendor_symbols = {n for n in runs_pkg.__all__ if "vendor" in n.lower()}
        # Exactly the frozen R0 public surface (four primitives + five
        # bounded errors + the model/vocabulary exports) — no R1
        # additions pre-R1-4 (the R1-4 recovery symbols do not exist).
        assert vendor_symbols == {
            "VendorRefreshError",
            "VendorRefreshTriggerError",
            "VendorRefreshClaimError",
            "VendorRefreshCompletionError",
            "VendorRefreshFailureError",
            "VendorRefreshExecution",
            "VendorRefreshState",
            "VendorRefreshFailureReason",
            "VendorRefreshTriggerSource",
            "trigger_vendor_refresh",
            "claim_vendor_refresh",
            "complete_vendor_refresh",
            "fail_vendor_refresh",
        }

    def test_r1_2_module_function_names_token_free(self) -> None:
        for path in (CORE_PATH, RUNTIME_PATH):
            for name in _function_names(_tree(path)):
                lowered = name.lower()
                assert not any(
                    token in lowered for token in _FORBIDDEN_SURFACE_TOKENS
                ), f"R1-2 module function carries a forbidden surface token: {name}"

    def test_execution_public_export_surface_is_additive_exact(self) -> None:
        """The execution package export surface gains EXACTLY the three
        approved R1-2 names over the frozen R1-1 set (adversarial
        exact-set pin; nothing else moves)."""
        import product_intelligence.execution as execution_pkg

        frozen_r1_1_surface = {
            "ComparableCandidateDiscoveryResult",
            "ComparableCandidateSourceOutcome",
            "ComparableCandidateSourceOutcomeState",
            "ComparableResearchExecutionError",
            "ExecutionError",
            "ExecutionResult",
            "SpecificationEvidenceResult",
            "SpecificationEvidenceSource",
            "SpecificationSourceOutcome",
            "SourceOutcomeState",
            "AiAssistedMatchResult",
            "discover_enterprise_ssd_comparable_candidates",
            "execute_comparable_research",
            "execute_comparable_research_with_default_providers",
            "execute_research_run",
            "research_enterprise_ssd_specifications",
            "replay_compact_quote_projection",
            "replay_public_compact_quote_projection",
        }
        assert set(execution_pkg.__all__) == frozen_r1_1_surface | {
            "execute_claimed_vendor_refresh",
            "execute_claimed_vendor_refresh_with_default_providers",
            "VendorRefreshExecutionError",
        }
        # Every exported name resolves.
        for name in execution_pkg.__all__:
            assert hasattr(execution_pkg, name), f"export {name!r} does not resolve"


# ---------------------------------------------------------------------------
# Core import allowlist + no-claim + no-provider (I13 / FU1-F1)
# ---------------------------------------------------------------------------


class TestCoreImportBoundary(TestCase):
    """The execution core's exact import allowlist (design section
    10.1) and the FU1-F1/FU3-F1 AST pins."""

    def test_core_imports_only_the_pinned_allowlist(self) -> None:
        imported = _imported_modules(_tree(CORE_PATH))
        allowlist = {
            "__future__",
            "os",
            "uuid",
            "typing",
            # The T3/T4 reconciliation requires the Django database
            # error class (the only Django import; no
            # django.db.transaction — I10).
            "django.db",
            "product_intelligence.runs",
            "product_intelligence.execution.vendor_commercial_binding",
            "product_intelligence.providers.commercial",
        }
        offenders = imported - allowlist
        assert not offenders, f"core imports outside the pinned allowlist: {offenders}"

    def test_core_t4_fresh_read_close_is_gated_not_blind(self) -> None:
        """FU1-F2 — the T4 reconciliation's connection close is
        explicitly gated, never blind: the function that closes the
        default connection also checks the atomic-block state (no
        close inside a managed transaction) and the in-memory
        database form (no in-memory test DB destruction)."""
        tree = _tree(CORE_PATH)
        funcs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        close_funcs = [
            f
            for f in funcs
            if any(
                isinstance(sub, ast.Call)
                and isinstance(sub.func, ast.Attribute)
                and sub.func.attr == "close"
                for sub in ast.walk(f)
            )
        ]
        assert close_funcs, (
            "the T4 fresh read must explicitly close the possibly-"
            "compromised connection outside a managed transaction"
        )
        for func in close_funcs:
            attrs = {
                sub.attr for sub in ast.walk(func) if isinstance(sub, ast.Attribute)
            }
            names = {
                sub.id for sub in ast.walk(func) if isinstance(sub, ast.Name)
            }
            assert "in_atomic_block" in attrs, (
                f"{func.name}: the connection close is not gated on the "
                "atomic-block state (blind close risk inside a managed "
                "transaction)"
            )
            assert "_is_in_memory_database_name" in names, (
                f"{func.name}: the connection close is not gated on the "
                "in-memory database form (in-memory test DB destroy risk)"
            )

    def test_core_imports_no_provider_class_in_any_form(self) -> None:
        imported = _imported_modules(_tree(CORE_PATH))
        for module in imported:
            if module == "product_intelligence.providers.commercial":
                continue  # the network-free contract type
            assert not (
                module == "product_intelligence.providers"
                or module.startswith("product_intelligence.providers.")
            ), f"core imports a provider module in some form: {module}"
        tree = _tree(CORE_PATH)
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                assert node.id != "InternalVendorAdapter"
            elif isinstance(node, ast.Attribute):
                assert node.attr != "InternalVendorAdapter"

    def test_core_references_no_claim_symbol_in_any_form(self) -> None:
        """FU1-F1: the core does not reference ``claim_vendor_refresh``
        (or any claim symbol) in any form — import, call, or name."""
        offenders = _claim_identifier_offenders(_tree(CORE_PATH))
        assert not offenders, f"core references claim symbols: {offenders}"

    def test_runtime_references_no_claim_symbol_in_any_form(self) -> None:
        offenders = _claim_identifier_offenders(_tree(RUNTIME_PATH))
        assert not offenders, f"runtime references claim symbols: {offenders}"

    def test_core_catches_no_claim_error(self) -> None:
        """FU3-F1: no R1 module catches VendorRefreshClaimError (or
        any claim error) in any form."""
        for path in (CORE_PATH, RUNTIME_PATH):
            tree = _tree(path)
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler):
                    for entry in _handler_type_names(node):
                        assert "claim" not in entry.lower(), (
                            f"{path.name} catches a claim error: {entry}"
                        )

    def test_terminal_cas_error_catches_are_pinned_read_only(self) -> None:
        """FU3-F1: VendorRefreshCompletionError /
        VendorRefreshFailureError / Django DatabaseError are caught
        ONLY in the pinned reconciliation shape — the handler bodies
        issue no second terminal write, no retry, no factory
        invocation, and no lookup call."""
        tree = _tree(CORE_PATH)
        cas_error_names = {
            "VendorRefreshCompletionError",
            "VendorRefreshFailureError",
            "DatabaseError",
        }
        saw_cas_handler = False
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            names = _handler_type_names(node)
            if not (set(names) & cas_error_names or "DoesNotExist" in names):
                continue
            saw_cas_handler = True
            body_calls: set[str] = set()
            for stmt in node.body:
                for sub in ast.walk(stmt):
                    if isinstance(sub, ast.Call):
                        func = sub.func
                        call_name = (
                            func.id
                            if isinstance(func, ast.Name)
                            else func.attr
                            if isinstance(func, ast.Attribute)
                            else None
                        )
                        if call_name:
                            body_calls.add(call_name)
            for call in sorted(body_calls):
                assert call not in {
                    "complete_vendor_refresh",
                    "fail_vendor_refresh",
                    "_outer_boundary_fail",
                }, f"CAS/DB-error handler issues a terminal write: {call}"
                assert call != "vendor_adapter_factory", (
                    "CAS/DB-error handler invokes the factory"
                )
                assert call != "lookup", "CAS/DB-error handler calls lookup()"
        assert saw_cas_handler, (
            "no CAS/DB-error handler found — the T1-T4 reconciliation "
            "site is missing"
        )

    def test_core_has_no_transaction_surface(self) -> None:
        """I10 — no database transaction may remain open across
        adapter.lookup: the core opens none at all (no
        django.db.transaction import, no atomic/savepoint call)."""
        imported = _imported_modules(_tree(CORE_PATH))
        assert "django.db.transaction" not in imported
        tree = _tree(CORE_PATH)
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                assert node.attr not in ("atomic", "savepoint"), (
                    f"core touches a transaction surface: {node.attr}"
                )

    def test_core_factory_invoked_exactly_once_and_single_lookup_site(self) -> None:
        """The lazy factory is invoked exactly once (S7 — the first and
        only construction, I13) and there is exactly one lookup call
        site (no retry structure)."""
        tree = _tree(CORE_PATH)
        factory_calls = 0
        lookup_calls = 0
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name) and node.func.id == "vendor_adapter_factory":
                factory_calls += 1
            if isinstance(node.func, ast.Attribute) and node.func.attr == "lookup":
                lookup_calls += 1
        assert factory_calls == 1, (
            f"the factory must be invoked exactly once, saw {factory_calls}"
        )
        assert lookup_calls == 1, (
            f"exactly one lookup call site (no retry), saw {lookup_calls}"
        )

    def test_core_imports_no_network_io_module(self) -> None:
        imported = _imported_modules(_tree(CORE_PATH))
        for module in imported:
            root = module.split(".")[0]
            assert root not in {"urllib", "socket", "http", "requests"}, (
                f"core imports a network I/O module: {module}"
            )

    def test_core_imports_no_forbidden_project_surface(self) -> None:
        imported = _imported_modules(_tree(CORE_PATH))
        forbidden_roots = (
            "product_intelligence.web",
            "product_intelligence.research",
            "product_intelligence.domain",
            "product_intelligence.execution.fx_observation_cache",
            "product_intelligence.execution.semantic_integration",
            "product_intelligence.execution.comparable_research",
            "product_intelligence.execution.comparable_runtime",
            "product_intelligence.execution.search_query",
            "product_intelligence.execution.page_fetch",
            "product_intelligence.execution.orchestration",
            "product_intelligence.providers.serper",
            "product_intelligence.providers.http_page",
            "product_intelligence.providers.http_pdf",
            "product_intelligence.providers.fx",
            "product_intelligence.providers.internal_vendor",
        )
        for module in imported:
            assert not any(
                module == forbidden or module.startswith(forbidden + ".")
                for forbidden in forbidden_roots
            ), f"core imports a forbidden project surface: {module}"


# ---------------------------------------------------------------------------
# Runtime boundary (O9: the only concrete-adapter importer)
# ---------------------------------------------------------------------------


class TestRuntimeImportBoundary(TestCase):
    """The runtime is the ONLY R1 module importing the concrete
    provider class (function-level, as factory source), and it
    constructs nothing itself."""

    def test_runtime_imports_only_the_pinned_allowlist(self) -> None:
        imported = _imported_modules(_tree(RUNTIME_PATH))
        allowlist = {
            "__future__",
            "uuid",
            "typing",
            "product_intelligence.execution.vendor_refresh",
            "product_intelligence.providers.internal_vendor",
            "product_intelligence.runs.models",  # TYPE_CHECKING annotation only
        }
        offenders = imported - allowlist
        assert not offenders, f"runtime imports outside the pinned allowlist: {offenders}"

    def test_runtime_is_the_only_r1_internal_vendor_importer(self) -> None:
        feature_modules = sorted(EXECUTION_ROOT.glob("vendor_*.py"))
        importers = []
        for path in feature_modules:
            if "product_intelligence.providers.internal_vendor" in _imported_modules(
                _tree(path)
            ):
                importers.append(path.name)
        assert importers == ["vendor_refresh_runtime.py"]

    def test_runtime_internal_vendor_import_is_function_level(self) -> None:
        tree = _tree(RUNTIME_PATH)
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith(
                "product_intelligence.providers.internal_vendor"
            ):
                pytest.fail(
                    "the runtime's providers.internal_vendor import must be "
                    "function-level (lazy factory source), not module-level"
                )

    def test_runtime_constructs_nothing_itself(self) -> None:
        """O9 — the runtime passes the adapter CLASS as the factory;
        it contains no InternalVendorAdapter() construction call."""
        tree = _tree(RUNTIME_PATH)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                name = (
                    func.id if isinstance(func, ast.Name) else
                    func.attr if isinstance(func, ast.Attribute) else None
                )
                assert name != "InternalVendorAdapter", (
                    "runtime must not construct the adapter itself"
                )

    def test_runtime_delegates_exactly_once(self) -> None:
        tree = _tree(RUNTIME_PATH)
        delegations = 0
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "execute_claimed_vendor_refresh"
            ):
                delegations += 1
        assert delegations == 1


# ---------------------------------------------------------------------------
# Frozen surfaces byte-identical to the approved R1-1 base
# ---------------------------------------------------------------------------


# SHA-256 digests of the frozen production surfaces at the approved R1-1
# implementation base SHA 6c123229bf075d72704f233f7176651656540cf9
# (task section 2: R1-1 source must remain byte-identical; no other
# production file may change in R1-2).
#
# Recorded re-pin (PRODUCT-INTEL.MAIN-MERGE-FU1): the user-authorized
# merge commit 5ead1624069bdea9bd265432d33bef3995d7b6c6 (approved merged
# main) legitimately carries Semantic Authority S2-B/C changes in exactly
# two protected files -- orchestration.py and runs/models.py. Their
# full-file digests below are re-pinned to the approved merged-main
# baseline (committed bytes, CRLF-normalized to LF exactly as this test
# hashes them). The other seven digests remain byte-identical to the
# approved R1-1 base. The protection contract is unchanged: any future
# change to any of the nine protected files still fails this pin.
_FROZEN_DIGESTS = {
    "product_intelligence/execution/vendor_commercial_binding.py": (
        "a1747442d9e935185840fd79a409368adf1fd263bcba6add2bd3b8af46b2ca56"
    ),
    # Re-pinned (PRODUCT-INTEL.MAIN-MERGE-FU1) to the approved merged-main
    # baseline 5ead162: legitimate Semantic Authority S2-B/C changes.
    "product_intelligence/execution/orchestration.py": (
        "29667958e499726b1aa1dfbb264b700cceb91311f5407b791d1b5b0a164bf8f9"
    ),
    "product_intelligence/runs/vendor_refresh_claims.py": (
        "33c5a6434a2f724dbb54ba07a380e79f4d211fed2128edfc45a1344e2c46e8c9"
    ),
    # Re-pinned (PRODUCT-INTEL.MAIN-MERGE-FU1) to the approved merged-main
    # baseline 5ead162: legitimate Semantic Authority S2-B/C changes.
    "product_intelligence/runs/models.py": (
        "5c7c733d951b64be507ebee019ce9ba259f55315eb50e241b76fe8ac442e646e"
    ),
    "product_intelligence/runs/errors.py": (
        "37231afca4d83eafd0bc966103830c4f178d182edc28ef732efe6cde6629b66e"
    ),
    "product_intelligence/providers/internal_vendor.py": (
        "a6f84a9f151ddcbe97bb58ab01a54d941d6e12d84d9f93c5be15edf0d8316fb8"
    ),
    "product_intelligence/providers/commercial.py": (
        "f33729276c195c79cae109ecdce9cd5bcd462ce047ddb9c4367716789e506074"
    ),
    "product_intelligence/research/commercial_supplement_codec.py": (
        "53627d8aab02190171f86aa7b8511c3a7de0f93c1ceb8bc7db084e161dd786f5"
    ),
    "product_intelligence/research/identity.py": (
        "13c7e4656ad58626a6bcf9009992a0e6440b8f5811e3e6203d61da151277c7b6"
    ),
}


class TestFrozenSurfacesByteIdentical(TestCase):
    """The frozen R0/R1-1 production surfaces are byte-identical to
    the approved R1-1 implementation base (no R0 source change; the
    R1-1 D10 helper unchanged; the frozen 4D-B orchestration
    unchanged).

    Recorded re-pin (PRODUCT-INTEL.MAIN-MERGE-FU1): orchestration.py and
    runs/models.py now use the approved merged-main baseline
    (5ead1624069bdea9bd265432d33bef3995d7b6c6) because the user-authorized
    merge legitimately carries Semantic Authority S2-B/C changes in
    exactly those two files; the other seven protected files still pin
    the approved R1-1 base unchanged.
    """

    def test_frozen_production_surfaces_match_the_approved_r1_1_base(self) -> None:
        for relative_path, expected_digest in _FROZEN_DIGESTS.items():
            with self.subTest(file=relative_path):
                path = PACKAGE_ROOT.parent / relative_path
                # Normalize CRLF -> LF before hashing (git core
                # normalization) so the pin is platform-independent and
                # agrees with the approved base's blob bytes.
                data = path.read_bytes().replace(b"\r\n", b"\n")
                actual = hashlib.sha256(data).hexdigest()
                assert actual == expected_digest, (
                    f"{relative_path} is no longer byte-identical to the "
                    f"approved R1-1 base (digest {actual})"
                )

    def test_helper_remains_pure_r1_1_allowlist(self) -> None:
        """The D10 helper stays on its frozen R1-1 import allowlist
        (pure: no DB, no env, no network, no adapter import)."""
        imported = _imported_modules(_tree(HELPER_PATH))
        allowlist = {
            "__future__",
            "typing",
            "product_intelligence.providers.commercial",
            "product_intelligence.research.identity",
            "product_intelligence.research.commercial_supplement_codec",
        }
        assert imported <= allowlist, (
            f"helper is no longer pure: {imported - allowlist}"
        )


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _handler_type_names(handler: ast.ExceptHandler) -> list[str]:
    names: list[str] = []
    if handler.type is None:
        return names
    node = handler.type
    if isinstance(node, ast.Tuple):
        for elt in node.elts:
            names.extend(_name_parts(elt))
    else:
        names.extend(_name_parts(node))
    return names


def _name_parts(node) -> list[str]:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, ast.Attribute):
        return [node.attr]
    return []
