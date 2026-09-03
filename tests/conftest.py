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
