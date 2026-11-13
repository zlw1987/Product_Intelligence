"""Vendor API status presentation (PRODUCT-INTEL.PILOT-VENDOR-STATUS-UX-A).

Pure display-only module. Consumes the already-decoded, already-validated
vendor supplement result (or ``None`` when the run has no persisted
supplement snapshot) as exposed by the ALLOWED-branch historical replay,
and produces the bounded "Vendor API status" notice rendered inside the
Quote & Market Summary section.

This module MUST NOT:
* read the database
* decode or encode persisted payloads (the replay boundary is the sole
  decoder; this module only formats facts it is handed)
* call providers or perform any network work
* execute research
* import execution, runs, providers, Django, or the commercial
  supplement codec

Security contract:
* It is invoked ONLY from the view's ALLOWED branch — after the
  server-side REMOTE_ADDR/CIDR access gate has already authorized the
  connection. The view never calls it for a DENIED request and never
  places its output in a DENIED template context, so an unauthorized
  connection learns nothing about the vendor snapshot: not its
  existence, not its status, not its sources, prices, or counts.
* It does not invent. Every displayed fact is carried by the decoded,
  codec-validated supplement result: the bounded lookup status, the
  identity-bound observation count, and the bounded per-source issues.
  The frozen supplement codec persists NO free-text failure cause, so a
  FAILED lookup without persisted bounded per-source results is
  displayed with the explicit statement that the cause was not
  recorded — never a guessed reason.
* It emits no raw codec field names (``lookup_status``,
  ``vendor_commercial_result``, ``price_basis``,
  ``explicit_candidate_mpn``, ``VENDOR_API_POLICY`` ...), no exception
  text, no internal identifiers, and no prices: status is about
  availability of vendor evidence, and the vendor prices themselves are
  displayed only in the existing vendor quote rows.

Display states (exactly one is produced per call):

* ``not-recorded`` — no persisted supplement snapshot for this run
  (NOT_ATTEMPTED): the lookup was not recorded; no reason is stated.
* ``failed`` — persisted lookup status FAILED: the lookup failed and
  (absent persisted bounded evidence to the contrary) no vendor
  evidence was obtained. A specific cause is shown ONLY when the
  persisted result records bounded per-source issues; otherwise the
  notice explicitly says the cause was not recorded.
* ``completed-no-quote`` — persisted lookup status SUCCESS with zero
  observations: the lookup completed but produced no usable
  identity-bound vendor quote.
* ``partial`` — persisted lookup status PARTIAL: some vendor results
  were obtained while other sources had bounded failures or were
  excluded.
* ``completed`` — persisted lookup status SUCCESS with observations:
  the usual vendor quotes are shown in the table; a compact successful
  status accompanies them.

The frozen codec guarantees the values it hands over (the lookup status
is one of SUCCESS / PARTIAL / FAILED and the issue outcomes are the
bounded vocabulary), so this module compares against those literals;
any value outside them (unreachable over a decoded result) fails
closed to the most conservative notice — "not recorded" facts are
never upgraded into a success or a partial-public claim.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Frozen codec vocabulary literals (comparison only — no codec import,
# per the web read-side boundary; the decoded object has already been
# validated against exactly these values).
_LOOKUP_SUCCESS = "SUCCESS"
_LOOKUP_PARTIAL = "PARTIAL"
_LOOKUP_FAILED = "FAILED"

_ISSUE_NOT_FOUND = "NOT_FOUND"
_ISSUE_MALFORMED_SECTION = "MALFORMED_SECTION"
_ISSUE_MISSING_EXPLICIT_MPN = "MISSING_EXPLICIT_MPN"
_ISSUE_MPN_MISMATCH = "MPN_MISMATCH"
_ISSUE_USABLE = "USABLE"

_DETAIL_VENDOR_MPN_MISMATCH = "vendor_mpn_mismatch"


@dataclass(frozen=True)
class VendorApiStatusPresentation:
    """One bounded, display-only Vendor API status notice.

    Attributes:
        state: Safe CSS slug identifying the display state
            (``not-recorded`` / ``failed`` / ``completed-no-quote`` /
            ``partial`` / ``completed``).
        state_label: Short business label after "Vendor API status:".
        lines: Bounded supporting lines (one or more), each a complete
            display sentence. Source names appear only as recorded in
            the decoded, persisted result (the same names the vendor
            quote rows display for this connection).
    """

    state: str
    state_label: str
    lines: tuple[str, ...]


def _enum_value(value: Any) -> Any:
    """Return an enum's value without importing the codec."""
    return getattr(value, "value", value)


def _issue_label(outcome: Any, detail: Any) -> str:
    """Bounded business label for one persisted per-source issue.

    Maps the frozen issue vocabulary to display text. An unknown outcome
    (unreachable over a codec-validated result) is labeled neutrally —
    the raw value is never emitted.
    """
    if outcome == _ISSUE_NOT_FOUND:
        return "not found"
    if outcome == _ISSUE_MALFORMED_SECTION:
        return "response section could not be read"
    if outcome == _ISSUE_MISSING_EXPLICIT_MPN:
        return "no explicit part number published"
    if outcome == _ISSUE_MPN_MISMATCH:
        if detail == _DETAIL_VENDOR_MPN_MISMATCH:
            return (
                "published part number did not match the requested "
                "part number"
            )
        return "part number mismatch"
    if outcome == _ISSUE_USABLE:
        return "usable"
    return "recorded issue"


def _issue_lines(issues: Any) -> tuple[str, ...]:
    """One bounded display line per persisted per-source issue."""
    lines: list[str] = []
    for issue in issues:
        source = str(issue.source_name).strip() or "Recorded source"
        label = _issue_label(
            _enum_value(issue.outcome),
            _enum_value(issue.detail),
        )
        lines.append(f"{source} — {label}")
    return tuple(lines)


def build_vendor_api_status_presentation(
    supplemental_result: Any | None,
) -> VendorApiStatusPresentation:
    """Build the bounded Vendor API status notice for an ALLOWED report.

    Parameters
    ----------
    supplemental_result
        The decoded persisted vendor supplement result exposed by the
        ALLOWED-branch replay, or ``None`` when the run has no persisted
        supplement snapshot (the lookup was not recorded for this run).

    Returns
    -------
    VendorApiStatusPresentation
        A complete display notice. Never raises for codec-validated
        input; a structurally unexpected value fails closed to the
        most conservative notice.
    """
    if supplemental_result is None:
        return VendorApiStatusPresentation(
            state="not-recorded",
            state_label="Not recorded",
            lines=(
                "No vendor lookup was recorded for this research run, "
                "so no reason is stated.",
            ),
        )

    vcr = getattr(supplemental_result, "vendor_commercial_result", None)
    if vcr is None:
        # Structurally impossible over a decoded result; fail closed.
        return VendorApiStatusPresentation(
            state="not-recorded",
            state_label="Not recorded",
            lines=(
                "No vendor lookup was recorded for this research run, "
                "so no reason is stated.",
            ),
        )

    status = _enum_value(vcr.lookup_status)
    observations = tuple(vcr.observations)
    issues = tuple(vcr.source_issues)
    issue_lines = _issue_lines(issues)

    if status == _LOOKUP_FAILED:
        lines: list[str] = []
        if not observations:
            lines.append(
                "The internal vendor lookup for this run failed, and no "
                "vendor quote was obtained."
            )
        else:
            lines.append(
                "The internal vendor lookup for this run failed."
            )
        if issue_lines:
            lines.append(
                "Bounded per-source results recorded by the lookup:"
            )
            lines.extend(issue_lines)
        else:
            lines.append(
                "The specific failure cause was not recorded by the "
                "lookup."
            )
        return VendorApiStatusPresentation(
            state="failed",
            state_label="Lookup failed",
            lines=tuple(lines),
        )

    if status == _LOOKUP_PARTIAL:
        lines = [
            "The internal vendor lookup partially completed: some vendor "
            "results were obtained while other sources had bounded "
            "failures or were excluded.",
        ]
        if not observations:
            lines.append(
                "No usable vendor quote was obtained for this run."
            )
        if issue_lines:
            lines.append(
                "Bounded per-source results recorded by the lookup:"
            )
            lines.extend(issue_lines)
        return VendorApiStatusPresentation(
            state="partial",
            state_label="Partially completed",
            lines=tuple(lines),
        )

    if status == _LOOKUP_SUCCESS:
        if not observations:
            lines = [
                "The internal vendor lookup completed, but it produced "
                "no usable identity-bound vendor quote for this run.",
            ]
            if issue_lines:
                lines.append(
                    "Bounded per-source results recorded by the lookup:"
                )
                lines.extend(issue_lines)
            return VendorApiStatusPresentation(
                state="completed-no-quote",
                state_label="Completed — no usable vendor quote",
                lines=tuple(lines),
            )
        if len(observations) == 1:
            line = (
                "The internal vendor lookup completed; the vendor quote "
                "is shown in the table below."
            )
        else:
            line = (
                "The internal vendor lookup completed; the vendor quotes "
                "are shown in the table below."
            )
        return VendorApiStatusPresentation(
            state="completed",
            state_label="Completed",
            lines=(line,),
        )

    # Unreachable over a codec-validated result (the frozen vocabulary is
    # exactly SUCCESS / PARTIAL / FAILED). Fail closed: report only what
    # is known — a vendor lookup exists but its status was not recorded
    # in a recognized form — and never claim success.
    return VendorApiStatusPresentation(
        state="not-recorded",
        state_label="Status not recorded",
        lines=(
            "A vendor lookup was recorded for this research run, but its "
            "status was not recorded in a recognized form. No vendor "
            "result is claimed.",
        ),
    )
