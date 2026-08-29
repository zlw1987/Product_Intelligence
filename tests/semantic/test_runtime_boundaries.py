"""Production semantic import boundary tests (PRODUCT-INTEL.SEMANTIC.BOUNDARY).

Importing ``product_intelligence.semantic`` must pull in the neutral semantic
contract and nothing else. Specifically it must NOT import:

* any ``product_intelligence.evaluation.semantic.*`` module. This includes
  ``product_intelligence.evaluation.semantic.transport`` - there is no
  whitelisted exception. The transport implementation production actually
  uses, ``product_intelligence.semantic.transport``, is a separate, neutral
  module that the evaluation harness re-exports; production never imports
  the harness's copy;
* Django;
* any network client (``requests``, ``urllib``, ``urllib3``, ``httpx``,
  ``aiohttp``).

Why the previous approach was replaced
--------------------------------------
The earlier version of this file installed a ``sys.meta_path`` finder and
asserted over the names it happened to observe. A meta-path finder is only
consulted for modules that are NOT already in ``sys.modules``, so once the test
session had imported Django or urllib for any other reason the finder saw
nothing and the assertions passed vacuously. That is a boundary test that
cannot fail.

These tests instead evict the relevant modules from ``sys.modules``, import the
production package into that clean module state, and inspect what actually
landed in ``sys.modules`` as a result. The eviction is undone in ``finally`` by
restoring the exact same module objects, so no other test observes a reimport.

Why the fixture itself needed a second fix (FU3A2D)
-----------------------------------------------------
Restoring ``sys.modules`` alone is not enough. When Python imports
``product_intelligence.semantic``, it also does
``setattr(sys.modules["product_intelligence"], "semantic", <the new module>)``
- the parent package keeps a direct attribute reference to its submodule,
independent of the ``sys.modules`` dict. The original fixture restored
``sys.modules["product_intelligence.semantic"]`` to the old module object but
left ``product_intelligence.semantic`` (the attribute) pointing at the
temporary reimport, because nothing ever set it back. Two different objects
then answered to the same name depending on how a caller reached it -
``sys.modules[name]`` vs. attribute access - which is exactly the kind of
split-identity state that can produce duplicate enum/class identities and
order-dependent test failures elsewhere in the suite.

``_clean_module_state`` now also snapshots, and restores, the parent-package
attribute for every module it evicts - not a semantic-only special case, but
one generic mechanism keyed off each evicted name's own dotted parent.
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from typing import Iterator

# Top-level package names that must never be pulled in by importing the
# production semantic package.
FORBIDDEN_TOP_LEVEL = (
    "django",
    "requests",
    "urllib",
    "urllib3",
    "httpx",
    "aiohttp",
)

# Module-name prefixes that must never be pulled in. evaluation.semantic is
# forbidden WHOLESALE: transport is not whitelisted.
FORBIDDEN_PREFIXES = (
    "product_intelligence.evaluation.semantic",
    "product_intelligence.evaluation",
)


def _is_forbidden(module_name: str) -> bool:
    """True when ``module_name`` must not be loaded by the production import."""
    if module_name.split(".")[0] in FORBIDDEN_TOP_LEVEL:
        return True
    return any(
        module_name == prefix or module_name.startswith(prefix + ".")
        for prefix in FORBIDDEN_PREFIXES
    )


class _Unset:
    """Sentinel distinguishing "attribute was absent" from "attribute was
    None". Using ``None`` itself as the sentinel would make restoration
    delete an attribute that had genuinely been set to ``None``.
    """


_UNSET = _Unset()


def _restore_parent_attributes(
    names: list[str],
) -> list[tuple[object, str, object]]:
    """Snapshot each evicted name's parent-package attribute, for restoration.

    Generic over any dotted module name, not special-cased to
    ``product_intelligence.semantic``: for ``"a.b.c"`` the parent is module
    ``"a.b"`` and the attribute is ``"c"``. A name with no dot (a bare
    top-level module) has no parent attribute to track and is skipped.

    Returns a list of ``(parent_module, attr_name, old_value_or_UNSET)``
    snapshots, in no particular order, to be handed to
    :func:`_apply_parent_attributes` after ``sys.modules`` has been restored.
    """
    snapshots: list[tuple[object, str, object]] = []
    for name in names:
        parent_name, sep, attr = name.rpartition(".")
        if not sep:
            continue  # top-level module: no parent attribute exists
        parent = sys.modules.get(parent_name)
        if parent is None:
            continue  # parent itself isn't loaded; nothing to snapshot
        old_value = getattr(parent, attr, _UNSET)
        snapshots.append((parent, attr, old_value))
    return snapshots


def _apply_parent_attributes(
    snapshots: list[tuple[object, str, object]],
) -> None:
    """Put back exactly what :func:`_restore_parent_attributes` observed.

    An attribute that was absent before is deleted again (if the temporary
    reimport added it); an attribute that held a value is set back to that
    exact value.
    """
    for parent, attr, old_value in snapshots:
        if old_value is _UNSET:
            if hasattr(parent, attr):
                delattr(parent, attr)
        else:
            setattr(parent, attr, old_value)


@contextmanager
def _clean_module_state() -> Iterator[None]:
    """Evict every module relevant to this boundary, then restore it exactly.

    Both the production package and everything it is forbidden to import are
    removed from ``sys.modules``, so a post-import scan reflects only what
    THIS import actually caused. On exit, ``sys.modules`` is restored to the
    exact original objects, AND every affected parent package's attribute
    (e.g. ``product_intelligence.semantic`` as an attribute of the
    ``product_intelligence`` module object, set by Python's import machinery
    whenever a submodule is imported) is restored to what it held before -
    not left holding whatever the temporary reimport inside the ``with``
    block happened to set it to. Restoring only ``sys.modules`` is not
    enough: attribute access and ``sys.modules`` lookup are two independent
    paths to "the same" submodule, and only fixing one of them still leaves
    two different objects answering to one name.
    """
    saved_modules = dict(sys.modules)
    to_evict = [
        name
        for name in sys.modules
        if name.startswith("product_intelligence.semantic") or _is_forbidden(name)
    ]
    parent_attr_snapshots = _restore_parent_attributes(to_evict)

    for name in to_evict:
        del sys.modules[name]

    try:
        yield
    finally:
        sys.modules.clear()
        sys.modules.update(saved_modules)
        _apply_parent_attributes(parent_attr_snapshots)


def _modules_loaded_by_importing_semantic() -> set[str]:
    """Import the production package from clean state; return loaded modules.

    Returns the full post-import ``sys.modules`` key set, captured before the
    saved state is restored.
    """
    with _clean_module_state():
        assert "product_intelligence.semantic" not in sys.modules, (
            "the clean-state fixture must actually evict the production package; "
            "otherwise this test proves nothing"
        )
        import product_intelligence.semantic  # noqa: F401

        return set(sys.modules)


# ---------------------------------------------------------------------------
# The fixture itself must be able to fail
# ---------------------------------------------------------------------------


def test_clean_module_state_actually_evicts_and_restores() -> None:
    """Guard the guard: eviction must be real and restoration must be exact.

    Without this, a fixture that silently evicted nothing would make every
    assertion below vacuous.
    """
    import product_intelligence.semantic as before

    assert "product_intelligence.semantic" in sys.modules

    with _clean_module_state():
        assert "product_intelligence.semantic" not in sys.modules
        # A forbidden module that the test session has certainly imported.
        assert "django" not in sys.modules

    # Restored to the exact same object, not a reimported duplicate.
    assert sys.modules["product_intelligence.semantic"] is before
    assert "django" in sys.modules


def test_clean_module_state_restores_the_parent_package_attribute() -> None:
    """FU3A2D regression: attribute access must agree with ``sys.modules``.

    Importing ``product_intelligence.semantic`` inside the ``with`` block
    makes Python's import machinery overwrite the ``product_intelligence``
    module's ``semantic`` attribute with the temporary reimport. Restoring
    ``sys.modules`` alone (the pre-FU3A2D fixture) leaves that attribute
    pointing at the temporary module even after the context manager exits -
    ``sys.modules["product_intelligence.semantic"]`` and
    ``product_intelligence.semantic`` would then be two different objects
    answering to the same name. Both must come back to the original.
    """
    import product_intelligence
    import product_intelligence.semantic as before

    with _clean_module_state():
        import product_intelligence.semantic as during

        assert during is not before, (
            "the clean-state fixture must actually evict and force a fresh "
            "import; otherwise this test proves nothing"
        )

    assert sys.modules["product_intelligence.semantic"] is before
    assert product_intelligence.semantic is before, (
        "product_intelligence.semantic (attribute access) diverged from "
        "sys.modules['product_intelligence.semantic'] after the context "
        "manager exited - the parent-package attribute was not restored"
    )


def test_importing_semantic_loads_the_production_package() -> None:
    """Sanity: the scan below is performed on a package that really loaded."""
    loaded = _modules_loaded_by_importing_semantic()

    assert "product_intelligence.semantic" in loaded
    assert "product_intelligence.semantic.contract" in loaded
    assert "product_intelligence.semantic.runtime" in loaded


# ---------------------------------------------------------------------------
# The boundary
# ---------------------------------------------------------------------------


def test_semantic_import_pulls_in_no_evaluation_module() -> None:
    """No ``product_intelligence.evaluation`` module may be imported.

    The evaluation harness carries the corpus loader, the model catalog and the
    benchmark runner. None of that belongs on the production path. Production
    resolves the transport lazily via its own neutral
    ``product_intelligence.semantic.transport`` module - never via
    ``product_intelligence.evaluation.semantic.transport``.
    """
    loaded = _modules_loaded_by_importing_semantic()

    offenders = sorted(
        name for name in loaded if name.startswith("product_intelligence.evaluation")
    )

    assert offenders == [], (
        "importing product_intelligence.semantic pulled in evaluation modules "
        f"{offenders}; the production semantic runtime must not depend on the "
        "evaluation harness at import time"
    )


def test_semantic_import_pulls_in_no_evaluation_runner_or_model_catalog() -> None:
    """Named check for the two heaviest evaluation modules.

    Mechanically asserts absence of the runner and the model catalog, the two
    modules a production import must never reach.
    """
    loaded = _modules_loaded_by_importing_semantic()

    assert "product_intelligence.evaluation.semantic.runner" not in loaded
    assert "product_intelligence.evaluation.semantic.model_catalog" not in loaded
    assert "product_intelligence.evaluation.semantic.transport" not in loaded
    assert "product_intelligence.evaluation.semantic.loader" not in loaded


def test_semantic_import_pulls_in_no_django() -> None:
    """Django must not be imported by the production semantic package."""
    loaded = _modules_loaded_by_importing_semantic()

    offenders = sorted(name for name in loaded if name.split(".")[0] == "django")

    assert offenders == [], (
        f"importing product_intelligence.semantic pulled in Django modules "
        f"{offenders}; the semantic runtime must work without Django settings"
    )


def test_semantic_import_pulls_in_no_network_client() -> None:
    """No network client library may be imported at production import time.

    ``urllib`` is included: the transport adapter uses it, and reaching the
    adapter at import time is exactly the coupling this boundary forbids.
    """
    loaded = _modules_loaded_by_importing_semantic()

    network_prefixes = ("requests", "urllib", "urllib3", "httpx", "aiohttp")
    offenders = sorted(
        name for name in loaded if name.split(".")[0] in network_prefixes
    )

    assert offenders == [], (
        f"importing product_intelligence.semantic pulled in network client "
        f"modules {offenders}; I/O belongs behind the lazily built transport"
    )


def test_semantic_import_pulls_in_nothing_forbidden_at_all() -> None:
    """One combined assertion over the whole forbidden set.

    Catches a future import that is forbidden but not covered by one of the
    focused tests above.
    """
    loaded = _modules_loaded_by_importing_semantic()

    offenders = sorted(name for name in loaded if _is_forbidden(name))

    assert offenders == [], (
        f"importing product_intelligence.semantic loaded forbidden modules "
        f"{offenders}"
    )


# ---------------------------------------------------------------------------
# The contract module is itself neutral
# ---------------------------------------------------------------------------


def test_semantic_contract_imports_standalone_and_is_neutral() -> None:
    """The contract module alone must also pull in nothing forbidden.

    The contract is what the evaluation harness re-exports, so it has to stay
    importable without dragging either side's infrastructure along.
    """
    with _clean_module_state():
        from product_intelligence.semantic import contract

        loaded = set(sys.modules)

        assert contract.SEMANTIC_PROMPT_VERSION == "1.1"
        assert hasattr(contract, "build_prompt")
        assert hasattr(contract, "parse_raw_output")
        assert hasattr(contract, "validate_response")
        assert hasattr(contract, "SemanticDecision")
        assert hasattr(contract, "ConfidenceLevel")
        assert hasattr(contract, "SemanticMatchResponse")

    offenders = sorted(name for name in loaded if _is_forbidden(name))
    assert offenders == [], (
        f"product_intelligence.semantic.contract loaded forbidden modules "
        f"{offenders}; the shared contract must stay neutral"
    )


def test_semantic_runtime_source_has_no_module_level_transport_import() -> None:
    """The transport dependency must be lazy, not merely reordered.

    A module-level import of the transport adapter would reintroduce urllib on
    the production import path. This asserts on the parsed module AST so the
    check cannot be satisfied by a comment or a string.
    """
    import ast
    from pathlib import Path

    import product_intelligence.semantic.runtime as runtime_module

    source = Path(runtime_module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)

    module_level_imports: list[str] = []
    for node in tree.body:  # top level only - nested imports are the lazy ones
        if isinstance(node, ast.Import):
            module_level_imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            module_level_imports.append(node.module)

    offenders = sorted(name for name in module_level_imports if _is_forbidden(name))

    assert offenders == [], (
        f"product_intelligence.semantic.runtime imports {offenders} at module "
        "level; the transport dependency must be resolved lazily inside "
        "transport construction"
    )
