"""Cache service contract tests (PRODUCT-INTEL.8A-FX-A1).

Covers ``product_intelligence/execution/fx_observation_cache.py``
directly (no orchestration): the READ (latest selection, fail-closed
integrity validation, freshness predicate over ACTUAL instants,
coverage, projection, original retrieved_at preservation) and the
WRITE (digest binding, re-proof convergence, correction distinctness,
bounded uniqueness-race reconciliation, and the fail-closed behavior
for unrelated storage errors).

All instants are pinned (deterministic on any weekday); the ECB
calendar zone is the real ``Europe/Brussels`` via zoneinfo.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from django.db import IntegrityError, OperationalError, transaction

from product_intelligence.execution import fx_observation_cache
from product_intelligence.execution.fx_observation_cache import (
    ECB_CALENDAR_ZONE,
    FxObservationStoreIntegrityError,
    record_live_observation,
    try_reuse_latest_observation,
)
from product_intelligence.providers.fx import (
    FX_FEED_ID_ECB_DAILY,
    FxObservationSet,
    FxRateObservation,
)
from product_intelligence.research.fx_cache_contract import (
    fx_document_content_sha256,
)
from product_intelligence.research.fx_codec import (
    FxCodecError,
    encode_fx_observation,
)
from product_intelligence.runs.models import FxObservationStore

# This repo has no pytest-django: the session test database (in-memory
# SQLite) is shared, so DB tests own their cleanup via fixtures below.

UTC = timezone.utc

# Pinned 2026 weekend: Fri 2026-01-09 .. Mon 2026-01-12 (Brussels = CET
# in January, UTC+1).
OBS_DATE = date(2026, 1, 9)                 # Friday document
FRI_17_00_BRU = datetime(2026, 1, 9, 16, 0, tzinfo=UTC)    # Fri 17:00 Brussels
SAT_09_00_BRU = datetime(2026, 1, 10, 8, 0, tzinfo=UTC)    # Sat 09:00 Brussels
SUN_10_00_BRU = datetime(2026, 1, 11, 9, 0, tzinfo=UTC)    # Sun 10:00 Brussels
MON_00_00_BRU = datetime(2026, 1, 12, 0, 0, tzinfo=UTC)    # Mon 00:00 Brussels
MON_09_00_BRU = datetime(2026, 1, 12, 8, 0, tzinfo=UTC)    # Mon 09:00 Brussels
NEXT_SAT = datetime(2026, 1, 17, 8, 0, tzinfo=UTC)         # following Saturday
RETRIEVED = datetime(2026, 1, 10, 7, 59, tzinfo=UTC)       # Sat 08:59 Brussels


def _rates() -> tuple[FxRateObservation, ...]:
    return (
        FxRateObservation(currency_code="USD", rate=Decimal("1.0934")),
        FxRateObservation(currency_code="GBP", rate=Decimal("0.8567")),
        FxRateObservation(currency_code="ZAR", rate=Decimal("18.6836")),
    )


def _full_set(
    *,
    rates: tuple[FxRateObservation, ...] | None = None,
    observation_date: date = OBS_DATE,
    retrieved_at: datetime = RETRIEVED,
    provider_id: str = "ECB",
    base_currency: str = "EUR",
) -> FxObservationSet:
    return FxObservationSet(
        provider_id=provider_id,
        observation_date=observation_date,
        base_currency=base_currency,
        rates=rates if rates is not None else _rates(),
        retrieved_at=retrieved_at,
    )


def _seed_row(
    *,
    last_proven_at: datetime = SAT_09_00_BRU,
    original_retrieved_at: datetime = RETRIEVED,
    rates: tuple[FxRateObservation, ...] | None = None,
    observation_date: date = OBS_DATE,
    payload: dict | None = None,
    content_sha256: str | None = None,
    provider_id: str = "ECB",
    base_currency: str = "EUR",
) -> FxObservationStore:
    rates = rates if rates is not None else _rates()
    return FxObservationStore.objects.create(
        feed_id=FX_FEED_ID_ECB_DAILY,
        provider_id=provider_id,
        base_currency=base_currency,
        observation_date=observation_date,
        content_sha256=content_sha256
        if content_sha256 is not None
        else fx_document_content_sha256(
            provider_id=provider_id,
            base_currency=base_currency,
            observation_date=observation_date,
            rates=[(r.currency_code, r.rate) for r in rates],
        ),
        payload=payload
        if payload is not None
        else encode_fx_observation(
            provider_id=provider_id,
            observation_date=observation_date,
            base_currency=base_currency,
            rates=rates,
            retrieved_at=original_retrieved_at,
        ),
        original_retrieved_at=original_retrieved_at,
        last_proven_at=last_proven_at,
        created_at=original_retrieved_at,
    )


@pytest.fixture(autouse=True)
def _clean_store():
    yield
    FxObservationStore.objects.all().delete()


# ===========================================================================
# READ: freshness policy over ACTUAL proof/use instants
# ===========================================================================


class TestReadFreshness:
    def test_no_row_is_an_ordinary_miss(self) -> None:
        assert try_reuse_latest_observation(
            frozenset({"USD", "GBP"}), now=SUN_10_00_BRU,
        ) is None

    def test_weekend_valid_proof_reuses(self) -> None:
        _seed_row()  # proven Sat 09:00 Brussels
        hit = try_reuse_latest_observation(
            frozenset({"USD", "GBP"}), now=SUN_10_00_BRU,
        )
        assert hit is not None
        assert hit.provider_id == "ECB"
        assert hit.base_currency == "EUR"
        assert hit.observation_date == OBS_DATE
        # Original provider retrieved_at preserved — never the serving time.
        assert hit.retrieved_at == RETRIEVED
        # Projected to the required currencies from the FULL cached set.
        assert [r.currency_code for r in hit.rates] == ["USD", "GBP"]
        assert hit.rates[0].rate == Decimal("1.0934")
        assert hit.rates[1].rate == Decimal("0.8567")

    def test_saturday_to_saturday_reuses(self) -> None:
        _seed_row()
        assert try_reuse_latest_observation(
            frozenset({"USD"}), now=datetime(2026, 1, 10, 16, 0, tzinfo=UTC),
        ) is not None

    def test_sunday_to_sunday_reuses(self) -> None:
        _seed_row(last_proven_at=datetime(2026, 1, 11, 9, 0, tzinfo=UTC))
        assert try_reuse_latest_observation(
            frozenset({"USD"}),
            now=datetime(2026, 1, 11, 17, 0, tzinfo=UTC),
        ) is not None

    def test_working_day_proof_never_reuses(self) -> None:
        # Friday 17:00 Brussels proof (post-publication working day):
        # no reuse at all (C2 conservatism), even on Saturday.
        _seed_row(
            last_proven_at=FRI_17_00_BRU,
            original_retrieved_at=datetime(2026, 1, 9, 15, 59, tzinfo=UTC),
        )
        assert try_reuse_latest_observation(
            frozenset({"USD"}), now=SAT_09_00_BRU,
        ) is None
        # ...and even on a working day after the proof.
        assert try_reuse_latest_observation(
            frozenset({"USD"}), now=MON_09_00_BRU,
        ) is None

    def test_monday_boundary_live_revalidation(self) -> None:
        # Saturday proof; use exactly at Monday 00:00 Brussels -> live.
        _seed_row()
        assert try_reuse_latest_observation(
            frozenset({"USD"}), now=MON_00_00_BRU,
        ) is None

    def test_cross_weekend_gap_not_reusable(self) -> None:
        _seed_row()
        assert try_reuse_latest_observation(
            frozenset({"USD"}), now=NEXT_SAT,
        ) is None

    def test_coverage_gap_falls_to_live(self) -> None:
        _seed_row()
        # AUD is absent from the stored full set -> not reusable.
        assert try_reuse_latest_observation(
            frozenset({"USD", "AUD"}), now=SUN_10_00_BRU,
        ) is None

    def test_corruption_is_visible_even_when_freshness_would_fail(self) -> None:
        # A Friday-proven row (NOT reusable at Sunday) that is ALSO
        # corrupt must still fail closed: persistence corruption is
        # never hidden behind a freshness miss.
        _seed_row(
            last_proven_at=FRI_17_00_BRU,
            original_retrieved_at=datetime(2026, 1, 9, 15, 59, tzinfo=UTC),
            payload={"garbage": True},
        )
        with pytest.raises(FxCodecError):
            try_reuse_latest_observation(frozenset({"USD"}), now=SUN_10_00_BRU)

    def test_naive_now_fails_closed(self) -> None:
        _seed_row()
        with pytest.raises(TypeError):
            try_reuse_latest_observation(
                frozenset({"USD"}), now=SUN_10_00_BRU.replace(tzinfo=None),
            )


# ===========================================================================
# READ: fail-closed integrity validation (NOT a cache miss)
# ===========================================================================


class TestReadIntegrityFailClosed:
    REQUIRED = frozenset({"USD"})
    NOW = SUN_10_00_BRU

    def test_malformed_payload_propagates(self) -> None:
        _seed_row(payload={"garbage": True})
        with pytest.raises(FxCodecError):
            try_reuse_latest_observation(self.REQUIRED, now=self.NOW)

    def test_unsupported_schema_version_propagates(self) -> None:
        payload = encode_fx_observation(
            provider_id="ECB", observation_date=OBS_DATE,
            base_currency="EUR", rates=_rates(), retrieved_at=RETRIEVED,
        )
        payload["schema_version"] = 99
        _seed_row(payload=payload)
        with pytest.raises(FxCodecError):
            try_reuse_latest_observation(self.REQUIRED, now=self.NOW)

    def test_malformed_rate_payload_propagates(self) -> None:
        payload = encode_fx_observation(
            provider_id="ECB", observation_date=OBS_DATE,
            base_currency="EUR", rates=_rates(), retrieved_at=RETRIEVED,
        )
        del payload["rates"][0]["rate"]
        _seed_row(payload=payload)
        with pytest.raises(FxCodecError):
            try_reuse_latest_observation(self.REQUIRED, now=self.NOW)

    def test_tampered_digest_propagates(self) -> None:
        _seed_row(content_sha256="0" * 64)
        with pytest.raises(FxObservationStoreIntegrityError):
            try_reuse_latest_observation(self.REQUIRED, now=self.NOW)

    def test_provider_mismatch_decoded_propagates(self) -> None:
        payload = encode_fx_observation(
            provider_id="XXX", observation_date=OBS_DATE,
            base_currency="EUR", rates=_rates(), retrieved_at=RETRIEVED,
        )
        _seed_row(payload=payload, provider_id="XXX")
        with pytest.raises(FxObservationStoreIntegrityError):
            try_reuse_latest_observation(self.REQUIRED, now=self.NOW)

    def test_base_mismatch_decoded_propagates(self) -> None:
        payload = encode_fx_observation(
            provider_id="ECB", observation_date=OBS_DATE,
            base_currency="USD", rates=_rates(), retrieved_at=RETRIEVED,
        )
        _seed_row(payload=payload, base_currency="USD")
        with pytest.raises(FxObservationStoreIntegrityError):
            try_reuse_latest_observation(self.REQUIRED, now=self.NOW)

    def test_column_payload_cross_field_mismatch_propagates(self) -> None:
        # Column observation_date disagrees with the payload's.
        payload = encode_fx_observation(
            provider_id="ECB", observation_date=OBS_DATE,
            base_currency="EUR", rates=_rates(), retrieved_at=RETRIEVED,
        )
        _seed_row(
            payload=payload,
            content_sha256=fx_document_content_sha256(
                provider_id="ECB", base_currency="EUR",
                observation_date=date(2026, 1, 8),
                rates=[(r.currency_code, r.rate) for r in _rates()],
            ),
            observation_date=date(2026, 1, 8),
        )
        with pytest.raises(FxObservationStoreIntegrityError):
            try_reuse_latest_observation(self.REQUIRED, now=self.NOW)

    def test_impossible_stored_timestamp_propagates(self) -> None:
        # Proof before the original retrieval: impossible.
        _seed_row(
            last_proven_at=datetime(2026, 1, 10, 7, 0, tzinfo=UTC),
            original_retrieved_at=RETRIEVED,
        )
        with pytest.raises(FxObservationStoreIntegrityError):
            try_reuse_latest_observation(self.REQUIRED, now=self.NOW)

    def test_missing_stored_retrieved_at_propagates(self) -> None:
        payload = encode_fx_observation(
            provider_id="ECB", observation_date=OBS_DATE,
            base_currency="EUR", rates=_rates(), retrieved_at=None,
        )
        _seed_row(payload=payload)
        with pytest.raises(FxObservationStoreIntegrityError):
            try_reuse_latest_observation(self.REQUIRED, now=self.NOW)

    def test_payload_retrieved_at_earlier_than_column_propagates(self) -> None:
        # 8A-FX-A1-FU1: the payload retrieved_at PRECEDES the immutable
        # original_retrieved_at column. The two values are the SAME
        # provenance fact, so this direction is corrupt too — it must
        # fail closed, not be accepted (and not become a miss).
        payload = encode_fx_observation(
            provider_id="ECB", observation_date=OBS_DATE,
            base_currency="EUR", rates=_rates(),
            retrieved_at=datetime(2026, 1, 10, 6, 59, tzinfo=UTC),
        )
        row = _seed_row(payload=payload)  # column: RETRIEVED (07:59)
        with pytest.raises(FxObservationStoreIntegrityError):
            try_reuse_latest_observation(self.REQUIRED, now=self.NOW)
        # The corrupted row remains (forensics; never deleted/repaired).
        assert FxObservationStore.objects.filter(id=row.id).exists()

    def test_payload_retrieved_at_later_than_column_propagates(self) -> None:
        # 8A-FX-A1-FU1: the payload retrieved_at POSTDATES the immutable
        # original_retrieved_at column (yet still precedes the proof
        # instant, isolating THIS check): corrupt — fail closed.
        payload = encode_fx_observation(
            provider_id="ECB", observation_date=OBS_DATE,
            base_currency="EUR", rates=_rates(),
            retrieved_at=datetime(2026, 1, 10, 8, 30, tzinfo=UTC),
        )
        row = _seed_row(
            payload=payload,
            original_retrieved_at=RETRIEVED,  # 07:59
            last_proven_at=datetime(2026, 1, 10, 9, 0, tzinfo=UTC),
        )
        with pytest.raises(FxObservationStoreIntegrityError):
            try_reuse_latest_observation(self.REQUIRED, now=self.NOW)
        assert FxObservationStore.objects.filter(id=row.id).exists()

    def test_payload_retrieved_at_same_instant_equivalent_offset_accepted(
        self,
    ) -> None:
        # 8A-FX-A1-FU1: the EXACT same instant represented with an
        # equivalent timezone offset is NOT a mismatch — instant
        # equality after normalization. The column is seeded with the
        # Brussels representation of RETRIEVED (07:59 UTC = 08:59 CET);
        # the payload carries the codec-deterministic UTC encoding.
        bru_repr = datetime(2026, 1, 10, 8, 59,
                            tzinfo=ZoneInfo("Europe/Brussels"))
        assert bru_repr.astimezone(UTC) == RETRIEVED
        _seed_row(original_retrieved_at=bru_repr)
        hit = try_reuse_latest_observation(self.REQUIRED, now=self.NOW)
        assert hit is not None
        assert hit.retrieved_at == RETRIEVED

    def test_payload_retrieved_at_z_suffix_same_instant_accepted(self) -> None:
        # 8A-FX-A1-FU1: the codec also accepts the 'Z' UTC designator —
        # the same instant under the equivalent representation is valid.
        payload = encode_fx_observation(
            provider_id="ECB", observation_date=OBS_DATE,
            base_currency="EUR", rates=_rates(), retrieved_at=RETRIEVED,
        )
        assert payload["retrieved_at"].endswith("+00:00")
        payload["retrieved_at"] = payload["retrieved_at"][:-6] + "Z"
        _seed_row(payload=payload)
        hit = try_reuse_latest_observation(self.REQUIRED, now=self.NOW)
        assert hit is not None
        assert hit.retrieved_at == RETRIEVED

    def test_corrupted_row_is_never_deleted(self) -> None:
        row = _seed_row(payload={"garbage": True})
        with pytest.raises(FxCodecError):
            try_reuse_latest_observation(self.REQUIRED, now=self.NOW)
        # The row remains (forensics); the failure is visible.
        assert FxObservationStore.objects.filter(id=row.id).exists()


# ===========================================================================
# WRITE: record_live_observation
# ===========================================================================


class TestRecordLive:
    def test_insert_full_document(self) -> None:
        row = record_live_observation(
            _full_set(), FX_FEED_ID_ECB_DAILY, now=SAT_09_00_BRU,
        )
        assert FxObservationStore.objects.count() == 1
        assert row.feed_id == FX_FEED_ID_ECB_DAILY
        assert row.provider_id == "ECB"
        assert row.base_currency == "EUR"
        assert row.observation_date == OBS_DATE
        assert row.original_retrieved_at == RETRIEVED
        assert row.last_proven_at == SAT_09_00_BRU
        assert row.created_at == SAT_09_00_BRU
        # The payload carries the FULL set (not a projection).
        codes = {e["currency_code"] for e in row.payload["rates"]}
        assert codes == {"USD", "GBP", "ZAR"}
        # The digest binds the full parsed observation.
        expected = fx_document_content_sha256(
            provider_id="ECB", base_currency="EUR", observation_date=OBS_DATE,
            rates=[(r.currency_code, r.rate) for r in _rates()],
        )
        assert row.content_sha256 == expected

    def test_reproof_identical_content_converges(self) -> None:
        record_live_observation(_full_set(), FX_FEED_ID_ECB_DAILY,
                                now=SAT_09_00_BRU)
        later = datetime(2026, 1, 11, 9, 0, tzinfo=UTC)  # Sunday proof
        record_live_observation(_full_set(), FX_FEED_ID_ECB_DAILY,
                                now=later)
        rows = list(FxObservationStore.objects.all())
        assert len(rows) == 1
        row = rows[0]
        assert row.last_proven_at == later
        # original_retrieved_at / created_at / payload are UNTOUCHED.
        assert row.original_retrieved_at == RETRIEVED
        assert row.created_at == SAT_09_00_BRU
        assert row.payload["retrieved_at"] == "2026-01-10T07:59:00+00:00"

    def test_correction_same_date_distinct_row(self) -> None:
        record_live_observation(_full_set(), FX_FEED_ID_ECB_DAILY,
                                now=SAT_09_00_BRU)
        corrected = (
            FxRateObservation(currency_code="USD", rate=Decimal("1.0950")),
        ) + _rates()[1:]
        record_live_observation(
            _full_set(rates=corrected), FX_FEED_ID_ECB_DAILY,
            now=datetime(2026, 1, 11, 9, 0, tzinfo=UTC),
        )
        assert FxObservationStore.objects.count() == 2
        # The correction never overwrote the superseded revision.
        digests = set(FxObservationStore.objects.values_list(
            "content_sha256", flat=True))
        assert len(digests) == 2

    def test_feed_binding_violation_fails_closed(self) -> None:
        with pytest.raises(FxObservationStoreIntegrityError):
            record_live_observation(
                _full_set(provider_id="XXX"), FX_FEED_ID_ECB_DAILY,
                now=SAT_09_00_BRU,
            )
        assert FxObservationStore.objects.count() == 0

    def test_base_binding_violation_fails_closed(self) -> None:
        with pytest.raises(FxObservationStoreIntegrityError):
            record_live_observation(
                _full_set(base_currency="USD"), FX_FEED_ID_ECB_DAILY,
                now=SAT_09_00_BRU,
            )
        assert FxObservationStore.objects.count() == 0

    def test_missing_retrieved_at_fails_closed(self) -> None:
        bad = FxObservationSet(
            provider_id="ECB", observation_date=OBS_DATE, base_currency="EUR",
            rates=_rates(), retrieved_at=None,
        )
        with pytest.raises(FxObservationStoreIntegrityError):
            record_live_observation(bad, FX_FEED_ID_ECB_DAILY,
                                    now=SAT_09_00_BRU)

    def test_proof_before_retrieval_fails_closed(self) -> None:
        with pytest.raises(FxObservationStoreIntegrityError):
            record_live_observation(
                _full_set(), FX_FEED_ID_ECB_DAILY,
                now=datetime(2026, 1, 10, 6, 59, tzinfo=UTC),  # before
            )
        assert FxObservationStore.objects.count() == 0

    def test_naive_now_fails_closed(self) -> None:
        with pytest.raises(TypeError):
            record_live_observation(
                _full_set(), FX_FEED_ID_ECB_DAILY,
                now=SAT_09_00_BRU.replace(tzinfo=None),
            )

    def test_later_reproof_of_identical_content_preserves_original_provenance(
        self,
    ) -> None:
        # 8A-FX-A1-FU1: a LATER live fetch of the SAME content — the
        # provider returns a later retrieved_at (T2). The existing row
        # must keep the original provenance (T1 in BOTH the column and
        # the stored payload) and advance ONLY last_proven_at: the
        # re-proof input never replaces either stored instant.
        record_live_observation(_full_set(), FX_FEED_ID_ECB_DAILY,
                                now=SAT_09_00_BRU)
        later_retrieved = datetime(2026, 1, 11, 8, 30, tzinfo=UTC)  # T2
        later_proof = datetime(2026, 1, 11, 9, 0, tzinfo=UTC)
        row = record_live_observation(
            _full_set(retrieved_at=later_retrieved),
            FX_FEED_ID_ECB_DAILY, now=later_proof,
        )
        assert FxObservationStore.objects.count() == 1
        assert row.last_proven_at == later_proof
        # Original provenance unchanged (T1, never T2):
        assert row.original_retrieved_at == RETRIEVED
        assert row.created_at == SAT_09_00_BRU
        assert row.payload["retrieved_at"] == "2026-01-10T07:59:00+00:00"

    def test_write_pins_column_to_codec_precision_exact_instant(self) -> None:
        # 8A-FX-A1-FU1: the provider's wall-clock retrieved_at carries
        # sub-second precision; the codec V1's deterministic
        # representation is whole-second. The row MUST hold the SAME
        # instant in both places (the column is pinned at the write
        # boundary), so the row passes its own exact-instant integrity
        # check on the next read.
        with_micros = datetime(2026, 1, 10, 7, 59, 0, 390049, tzinfo=UTC)
        row = record_live_observation(
            _full_set(retrieved_at=with_micros), FX_FEED_ID_ECB_DAILY,
            now=SAT_09_00_BRU,
        )
        assert row.original_retrieved_at == RETRIEVED
        assert row.payload["retrieved_at"] == "2026-01-10T07:59:00+00:00"
        hit = try_reuse_latest_observation(
            frozenset({"USD"}), now=SUN_10_00_BRU,
        )
        assert hit is not None
        assert hit.retrieved_at == RETRIEVED


# ===========================================================================
# WRITE: bounded uniqueness-race reconciliation
# ===========================================================================


class TestUniquenessRace:
    """Only the specifically understood race is reconciled."""

    def _seed_competing(self) -> FxObservationStore:
        return _seed_row()

    def test_race_converges_on_exact_identity(self) -> None:
        competing = self._seed_competing()
        original_created = competing.created_at

        with patch.object(
            FxObservationStore.objects, "create",
            side_effect=IntegrityError(
                "UNIQUE constraint failed: "
                "fx_observationstore.feed_id, fx_observationstore."
                "observation_date, fx_observationstore.content_sha256"
            ),
        ):
            row = record_live_observation(
                _full_set(), FX_FEED_ID_ECB_DAILY,
                now=datetime(2026, 1, 11, 9, 0, tzinfo=UTC),
            )

        # Converged: no exception, one row, re-proof advanced.
        assert FxObservationStore.objects.count() == 1
        assert row.id == competing.id
        assert row.last_proven_at == datetime(2026, 1, 11, 9, 0, tzinfo=UTC)
        # Original retrieval / creation / content untouched.
        assert row.original_retrieved_at == RETRIEVED
        assert row.created_at == original_created

    def test_unrelated_integrity_error_propagates(self) -> None:
        # Empty store: an IntegrityError with NO competing row for the
        # exact content identity is not the understood race -> the
        # original error propagates (not swallowed).
        with patch.object(
            FxObservationStore.objects, "create",
            side_effect=IntegrityError(
                "CHECK constraint failed: some_other_constraint"
            ),
        ):
            with pytest.raises(IntegrityError):
                record_live_observation(
                    _full_set(), FX_FEED_ID_ECB_DAILY, now=SAT_09_00_BRU,
                )
        assert FxObservationStore.objects.count() == 0

    def test_operational_error_propagates(self) -> None:
        with patch.object(
            FxObservationStore.objects, "create",
            side_effect=OperationalError("database is locked"),
        ):
            with pytest.raises(OperationalError):
                record_live_observation(
                    _full_set(), FX_FEED_ID_ECB_DAILY, now=SAT_09_00_BRU,
                )

    def test_corrupt_competing_row_fails_closed(self) -> None:
        # A competing row for the exact content identity whose PAYLOAD
        # is corrupt: the reconciliation decodes it and fails closed —
        # it never converges on corruption.
        _seed_row(payload={"garbage": True})
        with patch.object(
            FxObservationStore.objects, "create",
            side_effect=IntegrityError("UNIQUE constraint failed"),
        ):
            with pytest.raises(FxCodecError):
                record_live_observation(
                    _full_set(), FX_FEED_ID_ECB_DAILY,
                    now=datetime(2026, 1, 11, 9, 0, tzinfo=UTC),
                )

    def test_content_divergent_competing_row_fails_closed(self) -> None:
        # A competing row under the same (feed, date, digest) identity
        # whose column-level identity diverges from the live observation:
        # exact-identity reconciliation refuses to converge.
        ecb_digest = fx_document_content_sha256(
            provider_id="ECB", base_currency="EUR", observation_date=OBS_DATE,
            rates=[(r.currency_code, r.rate) for r in _rates()],
        )
        _seed_row(provider_id="XXX", content_sha256=ecb_digest)
        with patch.object(
            FxObservationStore.objects, "create",
            side_effect=IntegrityError("UNIQUE constraint failed"),
        ):
            with pytest.raises(FxObservationStoreIntegrityError):
                record_live_observation(
                    _full_set(), FX_FEED_ID_ECB_DAILY,
                    now=datetime(2026, 1, 11, 9, 0, tzinfo=UTC),
                )

    def test_concurrent_reproof_advances_and_converges(self) -> None:
        # Two sequential "concurrent" recorders of identical content at
        # different proof instants converge on the most recent proof.
        record_live_observation(_full_set(), FX_FEED_ID_ECB_DAILY,
                                now=SAT_09_00_BRU)
        record_live_observation(_full_set(), FX_FEED_ID_ECB_DAILY,
                                now=SUN_10_00_BRU)
        row = FxObservationStore.objects.get()
        assert row.last_proven_at == SUN_10_00_BRU
        assert row.original_retrieved_at == RETRIEVED


# ===========================================================================
# Module guards
# ===========================================================================


class TestCacheModuleGuards:
    """The cache service keeps provider class identity out of business
    semantics and performs no unbounded exception handling."""

    MODULE = (
        fx_observation_cache.__file__
        .replace("\\", "/")
    )

    def test_no_provider_class_identity_checks(self) -> None:
        import ast
        from pathlib import Path

        tree = ast.parse(Path(self.MODULE).read_text(encoding="utf-8"))
        provider_names = {
            "EcbFxProvider", "FxProvider", "FxObservationSet",
            "FxRateObservation",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in ("isinstance", "issubclass"):
                    for arg in node.args:
                        names = {
                            n.id for n in ast.walk(arg)
                            if isinstance(n, ast.Name)
                        }
                        assert not (names & provider_names), (
                            f"provider class identity used in a "
                            f"{node.func.id}() call: {sorted(names)}"
                        )

    def test_zone_is_europe_brussels(self) -> None:
        assert ECB_CALENDAR_ZONE.key == "Europe/Brussels"

    def test_no_broad_exception_catches(self) -> None:
        import ast
        from pathlib import Path

        tree = ast.parse(Path(self.MODULE).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    raise AssertionError("bare except in cache service")
                if isinstance(node.type, ast.Name):
                    assert node.type.id in {
                        "IntegrityError",
                    }, f"unexpected caught class {node.type.id}"
                elif isinstance(node.type, ast.Tuple):
                    for elt in node.type.elts:
                        assert isinstance(elt, ast.Name) and elt.id in {
                            "IntegrityError",
                        }
