"""Test session bootstrap.

PRODUCT-INTEL.1A is the first phase with a database, so the suite now needs a
configured Django and a test database. Both are set up here rather than by
adding a plugin dependency: the project's rule is that a dependency arrives with
the phase that needs it, and twenty lines of standard Django test setup does not
need one.

The test database is SQLite in memory (Django's default for a SQLite backend),
so the suite stays deterministic, leaves no file behind, and still exercises the
real migration — `create_test_db` migrates, so a broken migration fails here.

Tests that never touch the database are unaffected: the domain and evaluation
guards continue to run in clean subprocesses and remain framework-free.

Per-test isolation is provided by Django's `TestCase` subclasses (transaction
rollback) or by narrowly-scoped fixtures in individual test modules. There is
no global post-test database cleanup: each test that needs isolation owns it.
"""

from __future__ import annotations

import os
from typing import Iterator

import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402  (must follow the settings assignment above)

django.setup()


@pytest.fixture(scope="session", autouse=True)
def django_test_database() -> Iterator[None]:
    """Create the test database once for the session, and remove it after."""
    from django.db import connections
    from django.test.utils import setup_test_environment, teardown_test_environment

    setup_test_environment()
    creation = connections["default"].creation
    # serialize=False: nothing here uses `serialized_rollback`, and the
    # serialization step would otherwise read every table at setup.
    old_config = creation.create_test_db(verbosity=0, serialize=False)
    try:
        yield
    finally:
        creation.destroy_test_db(old_config, verbosity=0)
        teardown_test_environment()


@pytest.fixture(autouse=True)
def bounded_v2_semantic_runtime_default(monkeypatch) -> Iterator[None]:
    """S2-C: the live V2 semantic execution path never reaches a real
    provider in tests.

    Full-orchestration tests (execution / web / runs) that exercise
    ``execute_research_run`` with V2-eligible candidates now also run the
    S2-C V2 semantic path. The default V2 runtime is therefore resolved
    to a bounded fake-transport runtime for every test: both the primary
    and the fallback attempts fail with a deterministic
    CONNECTION_ERROR (zero network), so V2 candidates ledger a bounded
    RUNTIME_FAILURE record instead of a live model call. Tests that need
    specific V2 outcomes inject their own ``SemanticRuntimeV2`` (with
    ``FakeSemanticModelTransport``) explicitly; the V1 default-runtime
    patching in the FU3B tests is untouched.
    """
    from product_intelligence.execution import (
        semantic_decision_v2_execution as v2exec,
    )
    from product_intelligence.semantic.runtime_v2 import SemanticRuntimeV2
    from product_intelligence.semantic.transport import (
        FakeSemanticModelTransport,
    )

    def _bounded_fake_v2_runtime() -> SemanticRuntimeV2:
        return SemanticRuntimeV2(
            primary_transport=FakeSemanticModelTransport(
                failures={"UNKNOWN"},
            ),
            fallback_transport=FakeSemanticModelTransport(
                failures={"UNKNOWN"},
            ),
        )

    monkeypatch.setattr(
        v2exec, "get_default_runtime_v2", _bounded_fake_v2_runtime
    )
    yield
