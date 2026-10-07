"""Semantic decision persistence service (S2-B / S2-B-FU1).

The API that future S2-C live execution will call to persist — and to
replay — the semantic-decision artifact. In S2-B this service EXISTS but
is NOT called from the live execution path: current V1 execution produces
exactly what it produced before and writes ZERO ``SemanticDecisionRecord``
rows (guarded by tests). Live wiring is S2-C, together with the final V2
input/output contract, so S2-B does not persist a temporary contract that
would immediately become obsolete.

Layering: this is an execution-layer service — it composes research
(envelope codec + universal replay dispatch: interpretation) with runs
(the model: storage). The runs layer stores, it does not interpret; this
service is the single owner of the ledger's write path and of the read +
replay paths with their integrity verification.

S2-B-FU1 made the service contract-agnostic: it owns no semantic-
contract-specific assumption (no provider/model route, no prompt version,
no section shape). Persisting dispatches the artifact to its REGISTERED
contract adapter (currently exactly the Semantic V1 adapter); loading
decodes through the universal envelope (digest verification + strict
dispatch — unknown or future semantic contracts fail closed); replay
verifies the universal binding against the run's persisted evidence, runs
the adapter-specific recorded-request-identity check through the
registered adapter, and then dispatches the pure zero-live replay by the
recorded contract/version.

* ``persist_semantic_decision`` — encode the artifact through its
  registered adapter, compute the canonical payload digest, create the row
  (transactional). NEVER overwrites an existing (run, assessment_index)
  record: the ledger is append-only at the application level.
* ``load_semantic_decision`` — row -> digest verification -> strict
  universal decode (adapter dispatch). Absence is ``None``: a run without
  a record has "legacy semantic provenance unavailable under V2" — NOT
  NO_MATCH, NOT NOT_EVALUATED, NOT an AI failure. Nothing is fabricated.
* ``replay_semantic_decision_record`` — load + universal binding
  verification against the run's persisted evidence (the canonical request
  identity through the registered adapter, and the snapshot's assessment
  binding at the recorded index) + the universal zero-live replay
  dispatch (explicit version-specific support; unknown / future versions
  refused — never silently reinterpreted).
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
    adapter_for_record,
    canonical_payload_digest,
    decode_semantic_decision_record,
    encode_semantic_decision_record,
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
    artifact: object,
) -> SemanticDecisionRecordRow:
    """Persist one semantic decision artifact for ``run``.

    The service is the only write path. The artifact must be the typed
    record of a REGISTERED semantic contract adapter (currently exactly
    the Semantic V1 adapter's ``SemanticDecisionRecordV1``) and must bind
    to ``run`` (its ``run_id`` is the run's canonical UUID string). The
    row stores the codec-encoded payload plus the separate canonical
    digest; the row's ``schema_version`` column carries the payload
    ENVELOPE version (independent of the semantic contract version
    recorded inside the payload). A second persist for the same
    (run, assessment_index) fails closed rather than overwriting.

    Immutability note: the row's artifact columns are ``editable=False``;
    that flag is NOT database immutability enforcement (it keeps the
    fields out of Django auto-generated forms). The ledger's immutability
    is the application contract: this single service-owned append-only
    write path, the (run, assessment_index) uniqueness constraint, and the
    whole-artifact digest verified on every read — out-of-band mutation
    (``QuerySet.update()`` / raw SQL) bypasses the service and is detected
    on read where the digest anchor differs (fail closed).

    Note: the full evidence binding (snapshot assessment at the recorded
    index) is verified on the READ path (``replay_semantic_decision_
    record``); the write path stays order-independent so S2-C can persist
    inside its atomic publication block.
    """
    if not isinstance(run, ResearchRun):
        raise TypeError(
            "run must be a ResearchRun, got "
            f"{type(run).__name__}"
        )
    adapter = adapter_for_record(artifact)
    if adapter is None:
        raise TypeError(
            "artifact must be a registered semantic-decision record "
            "artifact (see the codec's adapter registry), got "
            f"{type(artifact).__name__}"
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
) -> object | None:
    """Load the persisted artifact for one (run, assessment_index).

    Returns ``None`` when no record exists: for runs created before S2-B
    (or before the S2-C live wiring) that means "legacy semantic provenance
    unavailable under V2" — NOT NO_MATCH, NOT NOT_EVALUATED, and NOT an AI
    failure. Callers must preserve that distinction.

    Otherwise returns the registered adapter's validated typed record for
    the payload's RECORDED semantic contract version (currently: the
    Semantic V1 adapter's ``SemanticDecisionRecordV1``).

    Raises ``SemanticDecisionPayloadTamperedError`` when the payload does
    not match the row's digest, and ``SemanticDecisionCodecError`` when
    the payload is malformed, of an unsupported envelope schema version,
    names a semantic contract version with no registered adapter (unknown
    or future contracts fail closed — never best-effort decoded), or
    violates the recorded contract's artifact rules.
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
    3. The payload decodes strictly through the universal envelope (the
       row's envelope schema version gates the payload format; the
       payload's recorded semantic contract version dispatches to its
       registered adapter — unknown / future semantic contracts fail
       closed rather than being best-effort decoded).
    4. The record's universal binding verifies against the run's persisted
       evidence: the recorded source URL binds to the run's snapshot
       assessment at the recorded index, and the adapter-specific recorded
       request identity (for the V1 adapter: the prompt-input target
       MPN / description) equals the run's canonical request (a
       same-request cross-run or out-of-range artifact cannot replay over
       this run's evidence).
    5. The universal zero-live replay dispatch runs: the exact recorded
       contract binding must be one this code supports explicitly
       (unknown / future versions refused — never silently
       reinterpreted), and the registered adapter performs the
       version-specific reconstruction and re-derivation agreement proof.
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
    adapter = adapter_for_record(record)
    if adapter is None:
        # Unreachable: the record decoded through the registry. Fail
        # closed if the registry and the dispatch ever drift apart.
        raise SemanticDecisionPersistenceError(
            "the decoded record has no registered contract adapter; the "
            "binding verification cannot be dispatched"
        )
    violation = adapter.run_binding_violation(
        record,
        request_mpn=request.manufacturer_part_number,
        request_description=request.description,
    )
    if violation is not None:
        raise SemanticDecisionBindingError(violation)

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
