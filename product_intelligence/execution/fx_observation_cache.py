"""Cross-run canonical ECB FX observation cache service (8A-FX-A1).

Owns the LOOKUP and the bounded WRITE of the cross-run observation
content (``runs.FxObservationStore``). The cache substitutes ONLY the
external acquisition of the canonical production ECB daily
reference-rate document. Everything downstream (currency discovery,
projection, the existing per-run FX codec, ``ResearchFxSnapshot``
publication, failure boundaries, authority decisions) is unchanged.

Eligibility is NOT decided here
--------------------------------

Cache eligibility is declared by the caller at the canonical-default
construction site (orchestration: ``fx_provider is None``). ANY
explicitly injected provider — a fake, an ``EcbFxProvider`` instance, a
subclass, a wrapper — bypasses the cache entirely and never reaches
this module. Provider class identity is not business/cache semantics;
no ``isinstance``/``issubclass`` check on a provider object exists in
this package (guarded by test).

Failure semantics (fail closed)
-------------------------------

* No row            -> ordinary cache miss (``None``); the caller live-fetches.
* Row exists and its codec/integrity validation fails (malformed
  payload, unsupported codec version, digest mismatch, feed-invariant
  or cross-field violation, impossible stored timestamps) ->
  PROPAGATE. A malformed or unsupported existing cache payload is NOT
  a cache miss and is never silently converted into a live acquisition.
* Freshness predicate false at ``now`` -> not reusable (``None``); the
  caller live-fetches. This is policy, not corruption.
* Coverage gap (stored full set lacks a required currency) -> not
  reusable (``None``); the caller live-fetches.
* Uniqueness race on insert -> bounded reconciliation ONLY for the
  specifically understood race: fetch the competing row, validate exact
  semantic/content identity, converge (convergent conditional
  ``last_proven_at`` re-proof) if identical, otherwise fail closed.
  Any other ``IntegrityError`` (no competing row for the exact content
  identity) propagates.
* Any other database/storage error -> propagate. A cache persistence
  failure after a successful live fetch is NOT silently swallowed.

Concurrency
-----------

No distributed locking, no ``select_for_update``. Deterministic
uniqueness (``feed_id, observation_date, content_sha256``) plus the
bounded reconciliation is the entire mechanism. Two concurrent
canonical runs may both live-fetch the same observation; identical
content converges on one row, distinct content (a correction) yields
distinct rows. A correction is never overwritten merely because the
observation_date matches.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from django.db import IntegrityError, transaction

from product_intelligence.providers.fx import (
    FX_FEED_ID_ECB_DAILY,
    FxObservationSet,
    FxRateObservation,
)
from product_intelligence.research.fx_cache_contract import (
    fx_document_content_sha256,
    no_publication_possible_between,
    project_required_rates,
)
from product_intelligence.research.fx_codec import (
    decode_fx_observation,
    encode_fx_observation,
)
from product_intelligence.runs.models import FxObservationStore

logger = logging.getLogger(__name__)

# The publication-contract zone of the ECB daily reference-rate feed:
# Europe/Brussels (CET/CEST, DST-aware via zoneinfo). It is applied ONLY
# inside the freshness predicate; storage and comparison stay UTC.
# (Constructed here, in the I/O-permitted execution layer, so the pure
# research contract module stays import-free of timezone data.)
ECB_CALENDAR_ZONE = ZoneInfo("Europe/Brussels")

# Feed invariants of the canonical feed (hard-coded by the ECB adapter;
# the checks make the binding explicit and fail closed on drift).
ECB_FEED_PROVIDER_ID = "ECB"
ECB_FEED_BASE_CURRENCY = "EUR"


class FxObservationStoreIntegrityError(ValueError):
    """A persisted cache row or live observation violates its contract.

    Programming/contract defect class: it PROPAGATES (fail closed). It
    is never a cache miss and never converted into a live fallback.
    """


def _utc_now() -> datetime:
    """The wall clock seam: timezone-aware UTC now.

    An explicit, patchable function (not a hidden module global) so
    deterministic tests can pin the current instant without new
    dependencies.
    """
    return datetime.now(timezone.utc)


def _resolve_now(now: datetime | None) -> datetime:
    """Validate an explicit ``now`` or fall back to the wall clock.

    Naive or non-datetime values fail closed (programming defects).
    """
    if now is None:
        return _utc_now()
    if not isinstance(now, datetime):
        raise TypeError(f"now must be a datetime, got {type(now).__name__}")
    if now.tzinfo is None or now.utcoffset() is None:
        raise TypeError("now must be timezone-aware")
    return now


# ---------------------------------------------------------------------------
# READ: latest valid cached observation, subject to the freshness contract
# ---------------------------------------------------------------------------


def try_reuse_latest_observation(
    required_currencies: frozenset[str] | set[str],
    *,
    now: datetime | None = None,
) -> FxObservationSet | None:
    """Return the latest reusable canonical observation, or ``None``.

    Sequence (A1 CACHE_HIT path):
    1. load the latest stored observation for the canonical feed
       (``observation_date`` desc, then ``last_proven_at`` desc);
    2. decode and validate it (fail closed — see module rules);
    3. apply the pure freshness predicate using the row's ACTUAL
       ``last_proven_at`` instant T and the current instant N (never a
       truncated date);
    4. if reusable: project the required currencies from the FULL
       cached set and return an ``FxObservationSet`` carrying the
       ORIGINAL provider ``retrieved_at`` — zero provider calls.

    ``None`` means "not reusable right now" (no row / freshness /
    coverage) — an ordinary miss, not an error.
    """
    use_instant = _resolve_now(now)

    row = (
        FxObservationStore.objects.filter(feed_id=FX_FEED_ID_ECB_DAILY)
        .order_by("-observation_date", "-last_proven_at")
        .first()
    )
    if row is None:
        return None  # ordinary cache miss

    # Fail-closed decode: FxCodecError (malformed payload, unsupported
    # schema version, malformed rate payload) PROPAGATES — it is never
    # treated as a miss.
    decoded = decode_fx_observation(row.payload)

    _validate_row_integrity(row, decoded)

    # Freshness: the ACTUAL proof instant T and current instant N.
    if not no_publication_possible_between(
        row.last_proven_at, use_instant, ECB_CALENDAR_ZONE
    ):
        return None  # not reusable at now (policy, not corruption)

    # Coverage: the stored FULL set must cover every required currency.
    stored_codes = {entry.currency_code for entry in decoded.rates}
    required_upper = frozenset(str(c).strip().upper() for c in required_currencies)
    if not required_upper.issubset(stored_codes):
        return None  # coverage gap -> live acquisition

    # Original provider retrieval instant (preserved, never the serving
    # time). Its presence is part of row integrity (checked above).
    retrieved_at = _parse_retrieved_at(decoded.retrieved_at, row)

    full_observations = tuple(
        FxRateObservation(currency_code=entry.currency_code, rate=entry.rate)
        for entry in decoded.rates
    )
    projected = project_required_rates(full_observations, required_upper)

    return FxObservationSet(
        provider_id=decoded.provider_id,
        observation_date=date.fromisoformat(decoded.observation_date),
        base_currency=decoded.base_currency,
        rates=projected,
        retrieved_at=retrieved_at,
    )


def _parse_retrieved_at(value: str, row: FxObservationStore) -> datetime:
    """Parse the stored original provider retrieval instant (fail closed)."""
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise FxObservationStoreIntegrityError(
            f"store row {row.pk}: stored retrieved_at is not timezone-aware"
        )
    parsed = parsed.astimezone(timezone.utc)
    if parsed > row.last_proven_at:
        raise FxObservationStoreIntegrityError(
            f"store row {row.pk}: stored retrieved_at "
            f"({value}) postdates the proof instant (impossible)"
        )
    return parsed


def _validate_row_integrity(row: FxObservationStore, decoded) -> None:
    """Validate a decoded store row against its columns and the feed.

    Every violation is a fail-closed integrity defect (propagates).
    The row is NEVER deleted or skipped: persisted corruption must
    remain visible.
    """
    # Feed invariants: the canonical feed is ECB/EUR.
    if decoded.provider_id != ECB_FEED_PROVIDER_ID:
        raise FxObservationStoreIntegrityError(
            f"store row {row.pk}: decoded provider_id "
            f"{decoded.provider_id!r} violates the canonical feed invariant "
            f"{ECB_FEED_PROVIDER_ID!r}"
        )
    if decoded.base_currency != ECB_FEED_BASE_CURRENCY:
        raise FxObservationStoreIntegrityError(
            f"store row {row.pk}: decoded base_currency "
            f"{decoded.base_currency!r} violates the canonical feed invariant "
            f"{ECB_FEED_BASE_CURRENCY!r}"
        )

    # Row/column cross-field consistency.
    if row.provider_id != decoded.provider_id:
        raise FxObservationStoreIntegrityError(
            f"store row {row.pk}: column provider_id {row.provider_id!r} "
            f"does not match payload provider_id {decoded.provider_id!r}"
        )
    if row.base_currency != decoded.base_currency:
        raise FxObservationStoreIntegrityError(
            f"store row {row.pk}: column base_currency {row.base_currency!r} "
            f"does not match payload base_currency {decoded.base_currency!r}"
        )
    decoded_date = date.fromisoformat(decoded.observation_date)
    if row.observation_date != decoded_date:
        raise FxObservationStoreIntegrityError(
            f"store row {row.pk}: column observation_date "
            f"{row.observation_date.isoformat()} does not match payload "
            f"{decoded.observation_date!r}"
        )

    # The original provider retrieved_at must be present (a canonical
    # row always carries it) — and EXACTLY consistent with the column.
    # The payload retrieved_at and original_retrieved_at are the SAME
    # immutable provenance fact (the original provider retrieval
    # instant of this exact stored content): any disagreement in
    # EITHER direction is corrupt (fail closed; never a miss).
    if decoded.retrieved_at is None:
        raise FxObservationStoreIntegrityError(
            f"store row {row.pk}: payload is missing the original "
            "provider retrieved_at (impossible for a canonical row)"
        )
    parsed_retrieved = _parse_retrieved_at(decoded.retrieved_at, row)
    if parsed_retrieved != row.original_retrieved_at:
        raise FxObservationStoreIntegrityError(
            f"store row {row.pk}: stored payload retrieved_at "
            f"({decoded.retrieved_at!r}) is not the same instant as "
            f"original_retrieved_at ({row.original_retrieved_at}); "
            "both directions of disagreement are corrupt"
        )

    # Content digest binding: the stored digest must equal the canonical
    # digest recomputed from the FULL decoded rate observation.
    expected_digest = fx_document_content_sha256(
        provider_id=decoded.provider_id,
        base_currency=decoded.base_currency,
        observation_date=decoded_date,
        rates=[(entry.currency_code, entry.rate) for entry in decoded.rates],
    )
    if row.content_sha256 != expected_digest:
        raise FxObservationStoreIntegrityError(
            f"store row {row.pk}: stored content digest {row.content_sha256} "
            f"does not match the canonical digest {expected_digest} of the "
            "decoded payload (tampered or inconsistent row)"
        )

    # Impossible stored timestamps (fail closed).
    if row.last_proven_at < row.original_retrieved_at:
        raise FxObservationStoreIntegrityError(
            f"store row {row.pk}: last_proven_at precedes "
            "original_retrieved_at (impossible)"
        )
    if row.created_at > row.last_proven_at:
        raise FxObservationStoreIntegrityError(
            f"store row {row.pk}: created_at is after last_proven_at "
            "(impossible)"
        )


# ---------------------------------------------------------------------------
# WRITE: record a successful canonical live observation (bounded)
# ---------------------------------------------------------------------------


def record_live_observation(
    full_set: FxObservationSet,
    feed_id: str,
    *,
    now: datetime | None = None,
) -> FxObservationStore:
    """Persist/reconcile the FULL observed set from a live acquisition.

    Only the canonical live acquisition calls this (the store is
    written by no other path). Steps:

    1. validate the returned observation against the canonical feed
       binding (contract defect -> propagate);
    2. calculate the canonical content digest of the FULL parsed set;
    3. encode the FULL set through the existing fail-closed FX codec V1
       (the original provider ``retrieved_at`` is preserved);
    4. INSERT the content row in its OWN transaction (independent of
       the run's atomic final publication) with
       ``last_proven_at = now`` (the successful proof instant);
    5. on the understood uniqueness race only: reconcile (bounded).

    Returns the row now holding this content identity. Unexpected
    storage failures propagate.
    """
    proof_instant = _resolve_now(now)
    now_utc = proof_instant.astimezone(timezone.utc)

    # Canonical feed binding of the live observation (fail closed).
    if full_set.provider_id != ECB_FEED_PROVIDER_ID:
        raise FxObservationStoreIntegrityError(
            f"canonical feed binding violated: live observation carries "
            f"provider_id {full_set.provider_id!r} (expected "
            f"{ECB_FEED_PROVIDER_ID!r})"
        )
    if full_set.base_currency != ECB_FEED_BASE_CURRENCY:
        raise FxObservationStoreIntegrityError(
            f"canonical feed binding violated: live observation carries "
            f"base_currency {full_set.base_currency!r} (expected "
            f"{ECB_FEED_BASE_CURRENCY!r})"
        )
    if full_set.retrieved_at is None:
        raise FxObservationStoreIntegrityError(
            "canonical live observation is missing the provider retrieved_at"
        )
    utc_retrieved = full_set.retrieved_at.astimezone(timezone.utc)
    if now_utc < utc_retrieved:
        raise FxObservationStoreIntegrityError(
            f"proof instant {now_utc.isoformat()} precedes the provider "
            f"retrieval instant {utc_retrieved.isoformat()} (impossible)"
        )

    # The codec V1's deterministic representation is whole-second
    # precision. The payload retrieved_at and the immutable
    # original_retrieved_at column are the SAME provenance fact, and
    # row integrity requires EXACT instant equality between them — so
    # the column is pinned to the codec's precision ONCE here, at the
    # write boundary (never truncated read-side: that would silently
    # accept a corrupt row).
    stored_retrieved = utc_retrieved.replace(microsecond=0)

    digest = fx_document_content_sha256(
        provider_id=full_set.provider_id,
        base_currency=full_set.base_currency,
        observation_date=full_set.observation_date,
        rates=[(obs.currency_code, obs.rate) for obs in full_set.rates],
    )
    payload = encode_fx_observation(
        provider_id=full_set.provider_id,
        observation_date=full_set.observation_date,
        base_currency=full_set.base_currency,
        rates=full_set.rates,
        retrieved_at=stored_retrieved,
    )

    try:
        with transaction.atomic():
            row = FxObservationStore.objects.create(
                feed_id=feed_id,
                provider_id=full_set.provider_id,
                base_currency=full_set.base_currency,
                observation_date=full_set.observation_date,
                content_sha256=digest,
                payload=payload,
                original_retrieved_at=stored_retrieved,
                last_proven_at=now_utc,
                created_at=now_utc,
            )
        return row
    except IntegrityError:
        # ONLY the specifically understood uniqueness race is
        # reconciled; anything else propagates (not swallowed).
        return _reconcile_uniqueness_race(
            feed_id=feed_id,
            full_set=full_set,
            digest=digest,
            now_utc=now_utc,
        )


def _reconcile_uniqueness_race(
    *,
    feed_id: str,
    full_set: FxObservationSet,
    digest: str,
    now_utc: datetime,
) -> FxObservationStore:
    """Bounded reconciliation of the content-identity uniqueness race.

    After an INSERT IntegrityError, a competing row holding the EXACT
    (feed_id, observation_date, content_sha256) identity may exist —
    a concurrent canonical run proved the same content. If and only if
    it exists AND its decoded content is EXACTLY the same observation
    (same provider/base/date, same multiset of exact rates), converge:
    a conditional re-proof advances ``last_proven_at`` only (content
    fields and ``original_retrieved_at`` untouched).

    No competing row for the exact identity -> the IntegrityError was
    NOT the understood race -> the ORIGINAL error propagates.
    Competing row with different content under the same identity, or a
    corrupt competing row -> fail closed (propagates).
    """
    competing = (
        FxObservationStore.objects.filter(
            feed_id=feed_id,
            observation_date=full_set.observation_date,
            content_sha256=digest,
        )
        .order_by("last_proven_at")
        .first()
    )
    if competing is None:
        # Re-raise the original IntegrityError: not the understood race.
        raise
    _validate_competing_content_identity(competing, full_set)

    # Convergent conditional re-proof: the row we read is still at the
    # last_proven_at we read, so advance it; content is untouched.
    with transaction.atomic():
        updated = (
            FxObservationStore.objects.filter(
                id=competing.id,
                last_proven_at=competing.last_proven_at,
            )
            .update(last_proven_at=now_utc)
        )
    if updated:
        logger.info(
            "FX observation store: uniqueness race reconciled; re-proved "
            "existing content identity (%s, %s)",
            feed_id,
            full_set.observation_date.isoformat(),
        )
        competing.refresh_from_db()
        return competing

    # A concurrent re-proof advanced the instant in between. Every
    # re-prover of identical content is a valid proof of the same
    # document: accept the competing value after re-validating exact
    # content identity on the refreshed row (convergent).
    refreshed = FxObservationStore.objects.get(id=competing.id)
    _validate_competing_content_identity(refreshed, full_set)
    logger.info(
        "FX observation store: uniqueness race reconciled against a "
        "concurrent re-proof (%s, %s)",
        feed_id,
        full_set.observation_date.isoformat(),
    )
    return refreshed


def _validate_competing_content_identity(
    row: FxObservationStore, full_set: FxObservationSet
) -> None:
    """Validate EXACT semantic/content identity with the new observation.

    The row already matched (feed_id, observation_date, content_sha256)
    by construction; this proves the decoded PAYLOAD carries the exact
    same observation. Any deviation — including a corrupt competing
    payload — fails closed (propagates).
    """
    decoded = decode_fx_observation(row.payload)  # FxCodecError propagates
    if row.provider_id != full_set.provider_id:
        raise FxObservationStoreIntegrityError(
            f"store row {row.pk}: competing row provider_id "
            f"{row.provider_id!r} differs from the live observation "
            f"{full_set.provider_id!r} under the same content identity"
        )
    if row.base_currency != full_set.base_currency:
        raise FxObservationStoreIntegrityError(
            f"store row {row.pk}: competing row base_currency "
            f"{row.base_currency!r} differs from the live observation "
            f"{full_set.base_currency!r} under the same content identity"
        )
    if date.fromisoformat(decoded.observation_date) != full_set.observation_date:
        raise FxObservationStoreIntegrityError(
            f"store row {row.pk}: competing payload observation_date "
            f"{decoded.observation_date!r} differs from the live "
            f"observation {full_set.observation_date.isoformat()}"
        )
    if decoded.provider_id != full_set.provider_id or (
        decoded.base_currency != full_set.base_currency
    ):
        raise FxObservationStoreIntegrityError(
            f"store row {row.pk}: competing payload feed identity differs "
            "from the live observation under the same content identity"
        )
    stored_rates = sorted(
        (entry.currency_code, str(entry.rate)) for entry in decoded.rates
    )
    live_rates = sorted(
        (obs.currency_code, str(obs.rate)) for obs in full_set.rates
    )
    if stored_rates != live_rates:
        raise FxObservationStoreIntegrityError(
            f"store row {row.pk}: competing payload rate content differs "
            "from the live observation under the same content identity "
            "(a correction must carry a distinct content identity, not "
            "reuse another's row)"
        )
