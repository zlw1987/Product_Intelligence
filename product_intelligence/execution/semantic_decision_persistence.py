"""Semantic decision persistence service (S2-B).

The API that future S2-C live execution will call to persist — and to
replay — the semantic-decision artifact. In S2-B this service EXISTS but
is NOT called from the live execution path: current V1 execution produces
exactly what it produced before and writes ZERO ``SemanticDecisionRecord``
rows (guarded by tests). Live wiring is S2-C, together with the final V2
input/output contract, so S2-B does not persist a temporary contract that
would immediately become obsolete.

Layering: this is an execution-layer service — it composes research
(artifact + codec + pure replay: interpretation) with runs (the model:
storage). The runs layer stores, it does not interpret; this service is the
single owner of the ledger's write path and of the read + replay paths
with their integrity verification:

* ``persist_semantic_decision`` — encode the artifact, compute the
  canonical payload digest, create the row (transactional). NEVER
  overwrites an existing (run, assessment_index) record: the ledger is
  append-only and immutable.
* ``load_semantic_decision`` — row -> digest verification -> strict
  decode. Absence is ``None``: a run without a record has "legacy
  semantic provenance unavailable under V2" — NOT NO_MATCH, NOT
  NOT_EVALUATED, NOT an AI failure. Nothing is fabricated.
* ``replay_semantic_decision_record`` — load + binding verification
  against the run's persisted evidence (the canonical request identity
  and the snapshot's assessment binding at the recorded index) + the pure
  zero-live replay (contract-binding gate, reconstruction, re-derivation
  agreement proof).
"""

from __future__ import annotations

import uuid

from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction

from product_intelligence.research.price_result_codec import (
    decode_price_aggregation_result,
)
from product_intelligence.research.semantic_decision_codec import (
    SEMANTIC_DECISION_SCHEMA_VERSION,
    canonical_payload_digest,
    decode_semantic_decision_record,
    encode_semantic_decision_record,
)
from product_intelligence.research.semantic_decision_record import (
    SemanticDecisionRecord,
)
from product_intelligence.research.semantic_decision_replay import (
    SemanticDecisionReplay,
    SemanticDecisionReplayError,
    replay_semantic_decision,
)
from product_intelligence.runs.models import (
    ResearchRun,
    SemanticDecisionRecord as SemanticDecisionRecordRow,
)

__all__ = [
    "SemanticDecisionAlreadyRecordedError",
    "SemanticDecisionBindingError",
    "SemanticDecisionPersistenceError",
    "SemanticDecisionPayloadTamperedError",
    "SemanticDecisionRecordNotFoundError",
    "load_semantic_decision",
    "persist_semantic_decision",
    "replay_semantic_decision_record",
]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class SemanticDecisionPersistenceError(Exception):
    """Base error for the semantic decision persistence service."""


class SemanticDecisionAlreadyRecordedError(SemanticDecisionPersistenceError):
    """A record for this (run, assessment_index) already exists.

    The ledger is immutable: persist never overwrites. A second record for
    the same assessment of the same run is a caller defect (or a tamper
    attempt) and fails closed.
    """


class SemanticDecisionPayloadTamperedError(SemanticDecisionPersistenceError):
    """The stored payload does not match the row's separate canonical
    digest column: the whole artifact was altered outside the service.

    This is the integrity backstop for writes that bypass the service
    (``QuerySet.update()`` / raw SQL): the row is never "repaired", and
    every read fails closed.
    """


class SemanticDecisionRecordNotFoundError(SemanticDecisionPersistenceError):
    """A replay was requested for a (run, assessment_index) with no record.

    NOTE the asymmetry with ``load_semantic_decision``: an ABSENT record is
    an ordinary legacy condition there (returns None — "legacy semantic
    provenance unavailable under V2"), but an explicit replay request for a
    record that is not there is a caller error and fails closed.
    """


class SemanticDecisionBindingError(SemanticDecisionPersistenceError):
    """The record's binding does not verify against the run's persisted
    evidence (request identity or the snapshot's assessment binding)."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _canonical_run_id(run_id: object) -> uuid.UUID:
    if isinstance(run_id, uuid.UUID):
        return run_id
    if isinstance(run_id, str):
        try:
            return uuid.UUID(run_id)
        except ValueError:
            raise SemanticDecisionPersistenceError(
                f"run_id must be a UUID or canonical UUID string, got "
                f"{run_id!r}"
            ) from None
    raise SemanticDecisionPersistenceError(
        "run_id must be a UUID or canonical UUID string, "
        f"got {type(run_id).__name__}"
    )


def _validate_assessment_index(assessment_index: object) -> int:
    if isinstance(assessment_index, bool) or not isinstance(
        assessment_index, int
    ):
        raise SemanticDecisionPersistenceError(
            "assessment_index must be int, "
            f"got {type(assessment_index).__name__}"
        )
    if assessment_index < 0:
        raise SemanticDecisionPersistenceError(
            f"assessment_index must be >= 0, got {assessment_index}"
        )
    return assessment_index


def _get_row(
    run_id: uuid.UUID, assessment_index: int
) -> SemanticDecisionRecordRow:
    return SemanticDecisionRecordRow.objects.get(
        run_id=run_id, assessment_index=assessment_index
    )


def _verify_row_digest(row: SemanticDecisionRecordRow) -> None:
    """Verify the whole-artifact tamper anchor (the separate column)."""
    if row.payload_digest != canonical_payload_digest(row.payload):
        raise SemanticDecisionPayloadTamperedError(
            f"semantic decision record {row.id}: stored payload does not "
            "match the row's canonical digest; the artifact was altered "
            "outside the persistence service"
        )


# ---------------------------------------------------------------------------
# Write path (the only one)
# ---------------------------------------------------------------------------


def persist_semantic_decision(
    run: ResearchRun,
    artifact: SemanticDecisionRecord,
) -> SemanticDecisionRecordRow:
    """Persist one semantic decision artifact for ``run``.

    The service is the only write path. The artifact must bind to ``run``
    (its ``run_id`` is the run's canonical UUID string). The row stores the
    codec-encoded payload plus the separate canonical digest; both columns
    are ``editable=False`` and the ledger is immutable — a second persist
    for the same (run, assessment_index) fails closed rather than
    overwriting.

    Note: the full evidence binding (snapshot assessment at the recorded
    index) is verified on the READ path (``replay_semantic_decision_record``);
    the write path stays order-independent so S2-C can persist inside its
    atomic publication block.
    """
    if not isinstance(run, ResearchRun):
        raise TypeError(
            "run must be a ResearchRun, got "
            f"{type(run).__name__}"
        )
    if not isinstance(artifact, SemanticDecisionRecord):
        raise TypeError(
            "artifact must be a research-layer SemanticDecisionRecord, "
            f"got {type(artifact).__name__}"
        )
    if str(run.id) != artifact.run_id:
        raise SemanticDecisionPersistenceError(
            "the artifact's run_id does not match the run it is being "
            "persisted for; the ledger binds one record to exactly one "
            "run"
        )

    payload = encode_semantic_decision_record(artifact)
    digest = canonical_payload_digest(payload)

    with transaction.atomic():
        try:
            row = SemanticDecisionRecordRow.objects.create(
                run=run,
                assessment_index=artifact.assessment_index,
                schema_version=SEMANTIC_DECISION_SCHEMA_VERSION,
                payload=payload,
                payload_digest=digest,
            )
        except IntegrityError:
            raise SemanticDecisionAlreadyRecordedError(
                f"a semantic decision record already exists for run "
                f"{run.id} assessment_index {artifact.assessment_index}; "
                "the ledger is immutable and never overwritten"
            ) from None
    return row


# ---------------------------------------------------------------------------
# Read path
# ---------------------------------------------------------------------------


def load_semantic_decision(
    run_id: object,
    assessment_index: object,
) -> SemanticDecisionRecord | None:
    """Load the persisted artifact for one (run, assessment_index).

    Returns ``None`` when no record exists: for runs created before S2-B
    (or before the S2-C live wiring) that means "legacy semantic provenance
    unavailable under V2" — NOT NO_MATCH, NOT NOT_EVALUATED, and NOT an AI
    failure. Callers must preserve that distinction.

    Raises ``SemanticDecisionPayloadTamperedError`` when the payload does
    not match the row's digest, and ``SemanticDecisionCodecError`` when the
    payload is malformed, of an unsupported schema version, or violates
    the v1 artifact contract.
    """
    run_uuid = _canonical_run_id(run_id)
    index = _validate_assessment_index(assessment_index)
    try:
        row = _get_row(run_uuid, index)
    except SemanticDecisionRecordRow.DoesNotExist:
        return None
    _verify_row_digest(row)
    return decode_semantic_decision_record(
        row.payload, schema_version=row.schema_version
    )


# ---------------------------------------------------------------------------
# Replay path (zero live work)
# ---------------------------------------------------------------------------


def replay_semantic_decision_record(
    run_id: object,
    assessment_index: object,
) -> SemanticDecisionReplay:
    """Replay one persisted semantic decision: ZERO live AI calls, ZERO
    provider/network calls.

    Steps (each fails closed):

    1. The row exists (an explicit replay request for an absent record is
       ``SemanticDecisionRecordNotFoundError`` — unlike ``load``, which
       returns None for the ordinary legacy-absence condition).
    2. The row's whole-artifact digest verifies (tamper anchor).
    3. The payload decodes strictly under the row's schema version.
    4. The record's binding verifies against the run's persisted evidence:
       the recorded request identity equals the run's canonical request,
       and the recorded source URL binds to the run's snapshot assessment
       at the recorded index (a same-request cross-run or out-of-range
       artifact cannot replay over this run's evidence).
    5. The pure replay runs: contract-binding gate (unknown / future
       versions refused explicitly — never silently reinterpreted),
       reconstruction of the historical evaluation and the S2-A authority
       inputs, and the derived-agreement proof.
    """
    run_uuid = _canonical_run_id(run_id)
    index = _validate_assessment_index(assessment_index)
    try:
        row = _get_row(run_uuid, index)
    except SemanticDecisionRecordRow.DoesNotExist:
        raise SemanticDecisionRecordNotFoundError(
            f"no semantic decision record for run {run_uuid} assessment_"
            f"index {index}; an explicit replay request fails closed "
            "(a bare load returns None for the legacy-absence condition)"
        ) from None
    _verify_row_digest(row)
    record = decode_semantic_decision_record(
        row.payload, schema_version=row.schema_version
    )

    try:
        run = ResearchRun.objects.get(pk=run_uuid)
    except ResearchRun.DoesNotExist:
        raise SemanticDecisionBindingError(
            f"run {run_uuid} no longer exists; the record cannot be "
            "binding-verified"
        ) from None

    request = run.to_research_request()
    if (
        record.target_mpn != request.manufacturer_part_number
        or record.target_description != request.description
    ):
        raise SemanticDecisionBindingError(
            "the record's request identity does not match the run's "
            "canonical request; the artifact does not bind to this run"
        )

    try:
        snapshot = run.price_intelligence_snapshot
    except ObjectDoesNotExist:
        raise SemanticDecisionBindingError(
            f"run {run_uuid} has no PriceIntelligenceSnapshot; the "
            "record's assessment binding cannot be verified"
        )

    price_result = decode_price_aggregation_result(
        snapshot.payload, schema_version=snapshot.schema_version
    )
    if index >= len(price_result.assessments):
        raise SemanticDecisionBindingError(
            f"assessment_index {index} is out of range for the run's "
            f"persisted assessments (0..{len(price_result.assessments) - 1})"
        )
    assessment = price_result.assessments[index]
    if (
        assessment.normalized_listing.observation.source_url
        != record.source_url
    ):
        raise SemanticDecisionBindingError(
            "the record's source URL does not bind to the run's persisted "
            f"assessment at index {index}; the artifact does not describe "
            "this run's candidate"
        )

    return replay_semantic_decision(record)
