"""Contract tests for EvidenceReference."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from product_intelligence.domain import (
    ConfidenceLevel,
    DomainValidationError,
    EvidenceDecision,
    EvidenceReference,
)

RETRIEVED_AT = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


def test_evidence_records_attribution() -> None:
    evidence = EvidenceReference(
        source="example-marketplace",
        retrieved_at=RETRIEVED_AT,
        source_url="https://example.invalid/listing/1",
        raw_reference="Acme ABC123-X 24-port switch - $412.00",
        normalized_value="412.00 USD",
        decision=EvidenceDecision.ACCEPTED,
        reason="Part number matched exactly in the listing title",
        confidence=ConfidenceLevel.HIGH,
    )

    assert evidence.source == "example-marketplace"
    assert evidence.retrieved_at == RETRIEVED_AT
    assert evidence.source_url == "https://example.invalid/listing/1"
    assert evidence.decision is EvidenceDecision.ACCEPTED


def test_evidence_defaults_to_undecided_and_unknown_confidence() -> None:
    evidence = EvidenceReference(source="example-marketplace", retrieved_at=RETRIEVED_AT)

    assert evidence.decision is EvidenceDecision.UNDECIDED
    assert evidence.confidence is ConfidenceLevel.UNKNOWN
    assert evidence.reason is None


@pytest.mark.parametrize("bad_source", ["", "   "])
def test_evidence_requires_a_source(bad_source: str) -> None:
    with pytest.raises(DomainValidationError):
        EvidenceReference(source=bad_source, retrieved_at=RETRIEVED_AT)


def test_rejected_evidence_must_say_why() -> None:
    with pytest.raises(DomainValidationError):
        EvidenceReference(
            source="example-marketplace",
            retrieved_at=RETRIEVED_AT,
            decision=EvidenceDecision.REJECTED,
        )

    rejected = EvidenceReference(
        source="example-marketplace",
        retrieved_at=RETRIEVED_AT,
        decision=EvidenceDecision.REJECTED,
        reason="Listing part number differed by one character",
    )

    assert rejected.reason == "Listing part number differed by one character"


def test_retrieval_time_must_be_timezone_aware() -> None:
    with pytest.raises(DomainValidationError):
        EvidenceReference(
            source="example-marketplace",
            retrieved_at=datetime(2026, 1, 2, 3, 4, 5),
        )


def test_non_utc_timezone_is_accepted() -> None:
    local = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone(timedelta(hours=-5)))

    evidence = EvidenceReference(source="example-marketplace", retrieved_at=local)

    assert evidence.retrieved_at == local


def test_retrieval_time_is_never_generated_by_the_domain() -> None:
    """Callers supply time, so behaviour stays deterministic and testable."""
    with pytest.raises(TypeError):
        EvidenceReference(source="example-marketplace")
