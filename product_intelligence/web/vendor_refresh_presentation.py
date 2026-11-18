"""Vendor refresh display presentation (VENDOR-REFRESH-WEB).

Pure display-only module. Consumes the already-loaded facts of ONE
persisted ``VendorRefreshExecution`` record plus its already-decoded
refresh payload (or ``None``) as handed over by the ALLOWED-branch
research detail view, and produces the bounded "Vendor refresh"
section content rendered on the report page. (VENDOR-REFRESH-WEB FU1:
the view calls this formatter for up to TWO records — the latest
refresh attempt, and, when the latest attempt is not itself a usable
quote, the last usable vendor quote, which the template presents
separately and labels historical with its original retrieval
timestamp. The per-row facts below are identical either way; the
historical framing is template-owned. This module remains stateless
per row.)

This module MUST NOT:
* read the database (no runs/execution/Django imports)
* decode or encode persisted payloads (the view's ALLOWED branch is
  the sole decoder of refresh payloads for this phase)
* call providers or perform any network work
* execute research or transitions

Security contract:
* It is invoked ONLY from the view's ALLOWED branch — after the
  server-side REMOTE_ADDR/CIDR access gate (the existing frozen
  4D-C-SEC corporate Vendor Price access policy) has already
  authorized the connection, and only for a COMPLETED parent run.
  The view never calls it for a DENIED request and never places its
  output in a DENIED template context, so an unauthorized
  connection learns nothing about refresh records: not their
  existence, not their state, not their operator, not their prices.
* It does not invent. Every displayed fact is carried by the
  persisted record or by the decoded, codec-validated payload: the
  bounded lifecycle state, the recorded operator and trigger source,
  the bounded timestamps, the bounded lookup status, the
  identity-bound observations, and the bounded per-source issues.
* Reuses the frozen display mappings — price formatting
  (``research.compact_quote._format_price``) and the vendor-API
  inventory mapping (``research.compact_quote._map_vendor_api_
  inventory``) — and the frozen issue labels of
  ``vendor_status_presentation``; this module never re-derives a
  price, availability, or issue label on its own.
* A COMPLETED record whose payload fails the frozen codec is
  displayed fail-closed as "recorded but unreadable" (the
  ``unreadable`` flag); no numeric fabrication, no partial rows.

Display states (exactly one primary state per call):

* ``pending`` / ``running`` — a refresh is in progress (bounded
  "started" instant where recorded); no result is shown.
* ``completed`` — the durably stored refresh result: the bounded
  lookup status, the prices retrieved instant (where recorded), the
  identity-bound observations (source, price, currency,
  availability), and the bounded per-source issues.
* ``failed`` — the refresh machinery defect with its bounded
  display label; no vendor result is claimed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from product_intelligence.research.compact_quote import (
    _format_price,
    _map_vendor_api_inventory,
)

from product_intelligence.web.vendor_status_presentation import (
    _enum_value,
    _issue_label,
)

# Frozen bounded vocabularies (comparison only — no model import):
# lifecycle states, the two trigger sources, the lookup statuses, and
# the failure reasons exactly as the runs layer stores them.
_STATE_PENDING = "PENDING"
_STATE_RUNNING = "RUNNING"
_STATE_COMPLETED = "COMPLETED"
_STATE_FAILED = "FAILED"

_TRIGGER_MANAGEMENT_COMMAND = "MANAGEMENT_COMMAND"
_TRIGGER_WEB_UI = "WEB_UI"

_LOOKUP_SUCCESS = "SUCCESS"
_LOOKUP_PARTIAL = "PARTIAL"
_LOOKUP_FAILED = "FAILED"

# Bounded failure-reason vocabulary (runs.VendorRefreshFailureReason)
# -> display label. An unknown value (unreachable over a persisted
# row) is labeled neutrally; the raw value is never emitted.
_FAILURE_LABELS = {
    "VENDOR_LOOKUP_CONFIG_MISSING": (
        "The vendor lookup configuration is missing on this "
        "deployment, so the refresh was not attempted."
    ),
    "MPN_BINDING_VIOLATION": (
        "The recorded part-number binding for this run is "
        "inconsistent, so the refresh was not attempted."
    ),
    "MPN_QUERY_NORMALIZATION_MISMATCH": (
        "The recorded part number could not be transmitted "
        "unchanged, so the refresh was not attempted."
    ),
    "RESULT_ENCODING_FAILED": (
        "The vendor lookup result could not be recorded."
    ),
    "EXECUTION_INTERRUPTED": (
        "The refresh was interrupted and recorded for operational "
        "recovery."
    ),
    "INTERNAL_ERROR": "An internal error stopped the refresh.",
}


@dataclass(frozen=True)
class VendorRefreshObservationPresentation:
    """One identity-bound observation of a decoded refresh result."""

    source: str
    price: str  # frozen ``_format_price`` convention (e.g. "$2,023.27 USD")
    currency: str
    availability: str  # frozen vendor-API inventory mapping display label


@dataclass(frozen=True)
class VendorRefreshPresentation:
    """One bounded, display-only vendor refresh section payload.

    Attributes:
        state: The persisted lifecycle state (PENDING / RUNNING /
            COMPLETED / FAILED).
        state_label: Business label for the state.
        triggered_by: Bounded trigger-source label.
        operator: The recorded self-reported trigger initiator
            (veracity is a provenance fact, not an identity claim).
        requested_mpn: The bound part number (displayed to prove the
            binding).
        created_at / started_at / finished_at: Bounded display
            instants (UTC second precision) or None.
        lookup_status: The persisted lookup status for a COMPLETED
            record (SUCCESS / PARTIAL / FAILED) or None.
        lookup_status_label: Business label for the lookup status.
        retrieved_at: The payload's own retrieval instant (where
            recorded) or None.
        observations: The identity-bound observation rows.
        issue_lines: Bounded per-source issue lines.
        unreadable: True for a COMPLETED record whose payload failed
            the frozen codec (displayed fail-closed; no data shown).
        failure_label: Bounded display label for a FAILED record.
    """

    state: str
    state_label: str
    triggered_by: str
    operator: str
    requested_mpn: str
    created_at: "str | None"
    started_at: "str | None"
    finished_at: "str | None"
    lookup_status: "str | None"
    lookup_status_label: "str | None"
    retrieved_at: "str | None"
    observations: tuple[VendorRefreshObservationPresentation, ...]
    issue_lines: tuple[str, ...]
    unreadable: bool
    failure_label: "str | None"


def _format_instant(value: Any) -> "str | None":
    """Bounded UTC display instant (the report's existing convention:
    ``%Y-%m-%d %H:%M UTC``); a non-datetime value renders nothing."""
    if not isinstance(value, datetime):
        return None
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _state_label(state: Any) -> str:
    state = _enum_value(state)
    if state == _STATE_PENDING:
        return "In progress (queued)"
    if state == _STATE_RUNNING:
        return "In progress"
    if state == _STATE_COMPLETED:
        return "Completed"
    if state == _STATE_FAILED:
        return "Failed"
    # Unreachable over a persisted row (the storage CHECK admits
    # exactly the four states); fail closed to a neutral label.
    return "State not recorded"


def _triggered_by(trigger_source: Any) -> str:
    trigger_source = _enum_value(trigger_source)
    if trigger_source == _TRIGGER_MANAGEMENT_COMMAND:
        return "Management command"
    if trigger_source == _TRIGGER_WEB_UI:
        return "Web UI"
    # Unreachable over a persisted row (the storage CHECK admits
    # exactly the bounded vocabulary); fail closed to a neutral label.
    return "Trigger source not recorded"


def _lookup_status_label(status: Any) -> str:
    status = _enum_value(status)
    if status == _LOOKUP_SUCCESS:
        return "Completed"
    if status == _LOOKUP_PARTIAL:
        return "Partially completed"
    if status == _LOOKUP_FAILED:
        return "Lookup failed — no vendor quote obtained"
    return "Status not recorded"


def _observation_lines(decoded: Any) -> tuple:
    """One display row per identity-bound observation of the decoded,
    codec-validated payload. The frozen ``_format_price`` + vendor-API
    inventory mappings are reused verbatim (display-only)."""
    vcr = getattr(decoded, "vendor_commercial_result", None)
    if vcr is None:
        return ()
    rows: list[VendorRefreshObservationPresentation] = []
    for obs in tuple(vcr.observations):
        price_amount = getattr(obs, "price_amount", None)
        currency = str(getattr(obs, "currency_code", "")).strip() or "N/A"
        availability = _enum_value(getattr(obs, "availability", None))
        if price_amount is not None:
            try:
                price = _format_price(price_amount, currency)
            except Exception:
                price = currency  # bounded fallback; never raw input text
        else:
            price = currency
        inventory_label, _note = _map_vendor_api_inventory(availability)
        source = str(getattr(obs, "source_name", "")).strip() or "Recorded source"
        rows.append(
            VendorRefreshObservationPresentation(
                source=source,
                price=price,
                currency=currency,
                availability=inventory_label,
            )
        )
    return tuple(rows)


def _issue_lines(decoded: Any) -> tuple[str, ...]:
    """One bounded display line per persisted per-source issue (the
    frozen label vocabulary of the Vendor API status notice)."""
    vcr = getattr(decoded, "vendor_commercial_result", None)
    if vcr is None:
        return ()
    lines: list[str] = []
    for issue in tuple(vcr.source_issues):
        source = str(getattr(issue, "source_name", "")).strip() or "Recorded source"
        label = _issue_label(
            _enum_value(getattr(issue, "outcome", None)),
            _enum_value(getattr(issue, "detail", None)),
        )
        lines.append(f"{source} — {label}")
    return tuple(lines)


def build_vendor_refresh_presentation(
    *,
    state: Any,
    operator: Any,
    trigger_source: Any,
    requested_mpn: Any,
    created_at: Any,
    started_at: Any,
    finished_at: Any,
    failure_reason: Any,
    decoded: Any,
    unreadable: bool,
) -> VendorRefreshPresentation:
    """Build the bounded display payload for ONE persisted refresh
    record. Never raises for structurally persisted input; a
    structurally unexpected value fails closed to the most
    conservative label."""
    state = _enum_value(state)

    lookup_status = None
    lookup_status_label = None
    retrieved_at = None
    observations: tuple = ()
    issue_lines: tuple[str, ...] = ()

    if state == _STATE_COMPLETED:
        if unreadable:
            # Fail-closed: the record exists but its payload did not
            # pass the frozen codec; no vendor fact is displayed.
            pass
        elif decoded is not None:
            vcr = getattr(decoded, "vendor_commercial_result", None)
            if vcr is not None:
                raw_status = _enum_value(getattr(vcr, "lookup_status", None))
                if raw_status in (_LOOKUP_SUCCESS, _LOOKUP_PARTIAL, _LOOKUP_FAILED):
                    lookup_status = raw_status
                    lookup_status_label = _lookup_status_label(raw_status)
                raw_retrieved = getattr(vcr, "retrieved_at", None)
                if isinstance(raw_retrieved, datetime):
                    retrieved_at = _format_instant(raw_retrieved)
                observations = _observation_lines(decoded)
                issue_lines = _issue_lines(decoded)

    failure_label = None
    if state == _STATE_FAILED:
        raw_reason = _enum_value(failure_reason)
        if raw_reason in _FAILURE_LABELS:
            failure_label = _FAILURE_LABELS[raw_reason]
        else:
            # Bounded neutral label; the raw value is never emitted.
            failure_label = "The refresh failed; the specific cause was not recorded."

    return VendorRefreshPresentation(
        state=state if state in (_STATE_PENDING, _STATE_RUNNING, _STATE_COMPLETED, _STATE_FAILED) else "NOT_RECORDED",
        state_label=_state_label(state),
        triggered_by=_triggered_by(trigger_source),
        operator=str(operator) if isinstance(operator, str) and operator else "Not recorded",
        requested_mpn=str(requested_mpn) if isinstance(requested_mpn, str) and requested_mpn else "Not recorded",
        created_at=_format_instant(created_at),
        started_at=_format_instant(started_at),
        finished_at=_format_instant(finished_at),
        lookup_status=lookup_status,
        lookup_status_label=lookup_status_label,
        retrieved_at=retrieved_at,
        observations=observations,
        issue_lines=issue_lines,
        unreadable=bool(unreadable),
        failure_label=failure_label,
    )
