"""Dedicated DB isolation for runs/ tests.

No autouse cleanup. Tests that need DB isolation must explicitly request
the `human_review_db_isolation` fixture. Tests that do not request it
rely on their own teardown (Django TestCase transaction rollback).

The fixture is narrowly scoped to the tables used by runs/ tests only.
"""
from __future__ import annotations

import pytest


def _is_django_test_case(cls) -> bool:
    """Return True if cls is a Django TestCase or SimpleTestCase."""
    from django.test import SimpleTestCase
    return issubclass(cls, SimpleTestCase)


@pytest.fixture
def human_review_db_isolation(request) -> None:
    """Dedicated DB isolation for HUMAN-REVIEW tests.

    Only applies to tests that explicitly request this fixture.
    Cleans up runs/-model data after each test in FK-safe order.

    Tests that inherit from django.test.TestCase or
    django.test.SimpleTestCase are skipped because they provide
    their own transaction rollback or do not allow DB access.

    Usage in a test module::

        def test_something(human_review_db_isolation) -> None:
            ...

    Or as a class-level fixture::

        @pytest.mark.usefixtures("human_review_db_isolation")
        class TestReviewActions:
            ...
    """
    yield  # Run the test

    # Skip Django TestCase/SimpleTestCase — they handle isolation
    test_class = getattr(request.node, "cls", None)
    if test_class is not None and _is_django_test_case(test_class):
        return

    # Explicitly no DB
    if "no_django_db" in request.fixturenames:
        return

    from django.db import transaction
    from product_intelligence.runs.models import (
        AiAssistedReviewCandidate,
        ExecutionEvidenceRecord,
        PriceIntelligenceSnapshot,
        ResearchRun,
    )
    with transaction.atomic():
        # FK-safe order: child tables before parent table
        AiAssistedReviewCandidate.objects.all().delete()
        ExecutionEvidenceRecord.objects.all().delete()
        PriceIntelligenceSnapshot.objects.all().delete()
        ResearchRun.objects.all().delete()