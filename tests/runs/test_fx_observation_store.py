"""FxObservationStore model + ResearchFxSnapshot.acquisition tests
(PRODUCT-INTEL.8A-FX-A1).

Covers the new cross-run store model's structural contract (frozen
field inventory, uniqueness, correction coexistence, latest-selection
ordering, immutability flags, no run cascade) and the additive
``ResearchFxSnapshot.acquisition`` provenance column (backward-
compatible LIVE default, approved vocabulary).

These are model-level tests; the cache service semantics (digest
binding, fail-closed integrity, bounded reconciliation) are covered by
``tests/execution/test_fx_observation_cache.py``.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from django.db import IntegrityError

from product_intelligence.domain import ResearchRequest
from product_intelligence.providers.fx import (
    FX_FEED_ID_ECB_DAILY,
    FxRateObservation,
)
from product_intelligence.research.fx_cache_contract import (
    fx_document_content_sha256,
)
from product_intelligence.research.fx_codec import encode_fx_observation
from product_intelligence.runs.models import (
    FxObservationStore,
    ResearchFxSnapshot,
    ResearchRun,
)

UTC = timezone.utc

OBS_DATE = date(2026, 1, 9)  # Friday (last working day)
PROOF_INSTANT = datetime(2026, 1, 10, 8, 0, 0, tzinfo=UTC)  # Sat 09:00 CET
RETRIEVED_INSTANT = datetime(2026, 1, 10, 7, 59, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _clean_store_rows():
    """Explicit per-test isolation (shared in-memory test database).

    This repo has no pytest-django; the session test DB is shared, so
    each DB test owns its cleanup (the established pattern of
    ``clean_execution_runs`` / ``human_review_db_isolation``).
    """
    yield
    FxObservationStore.objects.all().delete()
    ResearchFxSnapshot.objects.all().delete()
    ResearchRun.objects.all().delete()


def _full_rates() -> tuple[FxRateObservation, ...]:
    return (
        FxRateObservation(currency_code="USD", rate=Decimal("1.0934")),
        FxRateObservation(currency_code="GBP", rate=Decimal("0.8567")),
        FxRateObservation(currency_code="ZAR", rate=Decimal("18.6836")),
    )


def _digest(rates: tuple[FxRateObservation, ...]) -> str:
    return fx_document_content_sha256(
        provider_id="ECB",
        base_currency="EUR",
        observation_date=OBS_DATE,
        rates=[(r.currency_code, r.rate) for r in rates],
    )


def _make_row(
    *,
    observation_date: date = OBS_DATE,
    rates: tuple[FxRateObservation, ...] | None = None,
    content_sha256: str | None = None,
    last_proven_at: datetime = PROOF_INSTANT,
    original_retrieved_at: datetime = RETRIEVED_INSTANT,
    created_at: datetime | None = None,
    feed_id: str = FX_FEED_ID_ECB_DAILY,
    payload: dict | None = None,
) -> FxObservationStore:
    rates = rates if rates is not None else _full_rates()
    return FxObservationStore.objects.create(
        feed_id=feed_id,
        provider_id="ECB",
        base_currency="EUR",
        observation_date=observation_date,
        content_sha256=content_sha256
        if content_sha256 is not None
        else _digest(rates),
        payload=payload
        if payload is not None
        else encode_fx_observation(
            provider_id="ECB",
            observation_date=observation_date,
            base_currency="EUR",
            rates=rates,
            retrieved_at=original_retrieved_at,
        ),
        original_retrieved_at=original_retrieved_at,
        last_proven_at=last_proven_at,
        created_at=created_at
        if created_at is not None
        else original_retrieved_at,
    )


class TestFxObservationStoreShape:
    """Frozen field inventory + constraints of the new model."""

    EXPECTED_FIELDS = {
        "id",
        "feed_id",
        "provider_id",
        "base_currency",
        "observation_date",
        "content_sha256",
        "payload",
        "original_retrieved_at",
        "last_proven_at",
        "created_at",
    }

    def test_exact_field_inventory(self) -> None:
        assert (
            {f.name for f in FxObservationStore._meta.get_fields()}
            == self.EXPECTED_FIELDS
        )

    def test_no_relation_to_research_run(self) -> None:
        # Cross-run content has no run authority: no FK, no cascade.
        from django.db import models

        rels = [
            f for f in FxObservationStore._meta.get_fields()
            if isinstance(f, (models.ForeignKey, models.OneToOneField))
        ]
        assert rels == []

    def test_content_uniqueness_constraint(self) -> None:
        from django.db import models

        constraints = {c.name: c for c in FxObservationStore._meta.constraints}
        uc = constraints.get("fx_observation_store_unique_feed_date_content")
        assert uc is not None
        assert isinstance(uc, models.UniqueConstraint)
        assert set(uc.fields) == {"feed_id", "observation_date", "content_sha256"}

    def test_not_empty_check_constraints(self) -> None:
        names = {c.name for c in FxObservationStore._meta.constraints}
        assert "fx_observation_store_feed_id_not_empty" in names
        assert "fx_observation_store_provider_id_not_empty" in names
        assert "fx_observation_store_base_currency_not_empty" in names
        assert "fx_observation_store_content_sha256_not_empty" in names

    def test_immutable_fields(self) -> None:
        for name in (
            "feed_id", "provider_id", "base_currency", "observation_date",
            "content_sha256", "payload", "original_retrieved_at",
            "last_proven_at", "created_at",
        ):
            assert FxObservationStore._meta.get_field(name).editable is False

    def test_uuid_primary_key(self) -> None:
        pk = FxObservationStore._meta.get_field("id")
        assert pk.primary_key is True


class TestFxObservationStoreSemantics:
    """Content identity: corrections coexist; latest selection ordering."""

    def test_same_content_insert_twice_is_a_uniqueness_violation(self) -> None:
        _make_row()
        with pytest.raises(IntegrityError):
            _make_row()
        assert FxObservationStore.objects.count() == 1

    def test_correction_same_date_distinct_content_coexists(self) -> None:
        first = _make_row()
        corrected = _full_rates()[:1] + (
            FxRateObservation(currency_code="GBP", rate=Decimal("0.8600")),
        ) + _full_rates()[2:]
        second = _make_row(rates=corrected)
        assert first.content_sha256 != second.content_sha256
        assert FxObservationStore.objects.count() == 2
        # Both revisions remain VALID_HISTORICAL — the correction did
        # not overwrite or destroy the superseded one.
        assert FxObservationStore.objects.filter(observation_date=OBS_DATE).count() == 2

    def test_latest_selection_ordering(self) -> None:
        older = _make_row(
            observation_date=date(2026, 1, 8),
            last_proven_at=datetime(2026, 1, 8, 12, 0, tzinfo=UTC),
            original_retrieved_at=datetime(2026, 1, 8, 11, 59, tzinfo=UTC),
            created_at=datetime(2026, 1, 8, 11, 59, tzinfo=UTC),
        )
        newer = _make_row()  # Jan 9 observed, Jan 10 proven
        assert newer.id != older.id
        latest = (
            FxObservationStore.objects.filter(feed_id=FX_FEED_ID_ECB_DAILY)
            .order_by("-observation_date", "-last_proven_at")
            .first()
        )
        assert latest.id == newer.id

    def test_same_date_revision_tie_break_by_last_proven_at(self) -> None:
        # Two revisions of the same observation date: the more recently
        # live-verified revision is LATEST_KNOWN.
        old_rev = _make_row(
            last_proven_at=datetime(2026, 1, 10, 8, 0, tzinfo=UTC),
        )
        new_rates = _full_rates()[:1] + (
            FxRateObservation(currency_code="GBP", rate=Decimal("0.8599")),
        ) + _full_rates()[2:]
        new_rev = _make_row(
            rates=new_rates,
            last_proven_at=datetime(2026, 1, 10, 12, 0, tzinfo=UTC),
        )
        assert old_rev.content_sha256 != new_rev.content_sha256
        latest = (
            FxObservationStore.objects.filter(feed_id=FX_FEED_ID_ECB_DAILY)
            .order_by("-observation_date", "-last_proven_at")
            .first()
        )
        assert latest.id == new_rev.id

    def test_run_deletion_does_not_cascade_to_store(self) -> None:
        row = _make_row()
        run = ResearchRun.objects.create_from_request(
            ResearchRequest(manufacturer_part_number="STORE-TEST",
                            description="store cascade check")
        )
        run.delete()
        assert FxObservationStore.objects.filter(id=row.id).exists()

    def test_payload_is_the_full_document_codec_v1(self) -> None:
        row = _make_row()
        payload = row.payload
        assert payload["schema_version"] == 1
        # The FULL set is stored (not per-requested-currency entries).
        codes = {entry["currency_code"] for entry in payload["rates"]}
        assert codes == {"USD", "GBP", "ZAR"}
        # The original provider retrieved_at is inside the payload.
        assert payload["retrieved_at"] == "2026-01-10T07:59:00+00:00"
        # Raw provider bodies are never persisted: the payload is the
        # versioned codec dict, JSON-serializable, no XML.
        assert "<Cube" not in json.dumps(payload)


class TestResearchFxSnapshotAcquisition:
    """The additive acquisition provenance column (backward compatible)."""

    def _completed_run(self) -> ResearchRun:
        return ResearchRun.objects.create_from_request(
            ResearchRequest(manufacturer_part_number="ACQ-TEST",
                            description="acquisition column check")
        )

    def test_default_is_live(self) -> None:
        run = self._completed_run()
        row = ResearchFxSnapshot.objects.create(
            run=run, schema_version=1, payload={},
        )
        assert row.acquisition == ResearchFxSnapshot.ACQUISITION_LIVE
        assert row.acquisition == "LIVE"

    def test_approved_vocabulary(self) -> None:
        field = ResearchFxSnapshot._meta.get_field("acquisition")
        assert {code for code, _ in field.choices} == {"LIVE", "CACHE_HIT"}
        assert field.default == "LIVE"
        assert field.editable is False

    def test_cache_hit_value_persisted(self) -> None:
        run = self._completed_run()
        row = ResearchFxSnapshot.objects.create(
            run=run, schema_version=1, payload={},
            acquisition=ResearchFxSnapshot.ACQUISITION_CACHE_HIT,
        )
        row.refresh_from_db()
        assert row.acquisition == "CACHE_HIT"

    def test_replay_never_a_stored_value(self) -> None:
        # The stored vocabulary has exactly two values; REPLAY is a read
        # behavior and must not exist as a persisted acquisition value.
        field = ResearchFxSnapshot._meta.get_field("acquisition")
        assert all(code != "REPLAY" for code, _ in field.choices)
