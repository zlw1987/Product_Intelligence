"""VENDOR-REFRESH-WEB FU1 — status truthfulness and the last usable
vendor quote (corrective regression suite).

Focused coverage for the FU1 corrections on top of the pinned
VENDOR-REFRESH-WEB contracts (``test_vendor_refresh_web.py`` remains
untouched):

* **F1 — URL-controlled success claims.** The ``?vendor_refresh=``
  query flag is a client-supplied CANDIDATE: a forged flag with no
  refresh record, or with conflicting persisted states, must never
  create a false success, failure, in-progress, cooldown, or
  not-eligible claim. Each claim renders only when the ACTUAL
  persisted refresh state of the parent backs it (the same persisted
  facts the shared decision service acts on). The bounded error
  notice asserts no recorded fact. POST/Redirect/GET, CSRF, and the
  corporate CIDR boundaries are preserved (the pinned parent suite
  covers them unchanged).
* **F2 — last usable vendor quote.** The latest refresh attempt and
  the last usable vendor quote (design §8.3 concept 3: the newest
  codec-validated COMPLETED refresh with a SUCCESS/PARTIAL lookup and
  at least one identity-bound observation) are presented SEPARATELY.
  A later FAILED / in-progress / no-quote attempt never hides an
  earlier usable quote, which stays visible with its ORIGINAL
  retrieval timestamp and an explicit historical label (never
  described as current). Malformed or unreadable rows are never
  selected and never fabricate prices. The original report region
  and the DENIED zero-knowledge boundary remain untouched.
* **F3 — error assurance.** The bounded error notice no longer
  claims "No vendor data was changed"; it asserts no rollback and no
  terminal outcome. FU2 (F5) corrects the forged-no-record case in
  place: with NO persisted refresh attempt the error flag renders the
  neutral no-record line instead of the operation-failure assertion
  (the two affected nodes keep their names and contracts; their
  expectations are strengthened, not weakened). FINAL-CORRECTION (F5
  truthfulness) rewords the with-record error line in place: it is
  NEUTRAL in both shapes — it reports the page's error indication and
  directs the user to the actual persisted refresh state shown below,
  never claiming that the particular request failed (a historical row
  — even a successfully COMPLETED one — is not proof of that); the
  affected error-notice nodes keep their names and safety contracts;
  their expectations are adjusted/strengthened, not weakened.

Class discipline: deterministic D nodes over the in-memory suite
database with pinned terminal instants (``at=`` on the CAS
primitives) so the canonical ``finished_at DESC, id DESC`` ordering is
deterministic independent of the wall clock.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone as dt_timezone
from decimal import Decimal
from unittest.mock import patch

from django.test import Client, TestCase
from urllib.parse import quote

from product_intelligence.research.commercial_supplement_codec import (
    ResearchSupplementResult,
    VendorCommercialResult,
    encode_research_supplement_result,
)
from product_intelligence.runs import (
    claim_vendor_refresh,
    complete_vendor_refresh,
    fail_vendor_refresh,
    trigger_vendor_refresh,
)
from product_intelligence.runs.models import (
    PriceIntelligenceSnapshot,
    ResearchSupplementSnapshot,
    VendorRefreshExecution,
    VendorRefreshFailureReason,
    VendorRefreshState,
)

from tests.web.test_vendor_refresh_web import (
    ALLOWED_ADDR,
    CIDRS,
    PINNED,
    _detail_url,
    _make_completed_run,
    _original_observation,
    _post_refresh,
    _settings_mock,
)

# Deterministic terminal instants (newest-last), independent of the
# wall clock: T1 < T2 < T3.
T1 = PINNED
T2 = PINNED + timedelta(hours=1)
T3 = PINNED + timedelta(hours=2)

# The ORIGINAL retrieval instant of the historical quotes below
# (distinct from the terminal instants: the display must carry this
# payload-owned timestamp, not the row's finished_at).
RETRIEVED_R1 = datetime(2025, 12, 1, 8, 0, 0, tzinfo=dt_timezone.utc)

# Notice lines (fixed vocabulary of the section).
LINE_SUCCESS = "Vendor prices were refreshed"
LINE_COMPLETED_NO_QUOTE = (
    "The vendor refresh completed but did not record a usable vendor quote"
)
LINE_FAILED = "The vendor refresh did not complete successfully"
LINE_IN_PROGRESS = "already in progress"
LINE_COOLDOWN = "Refreshes are limited to one per five minutes"
LINE_NOT_ELIGIBLE = "not eligible"
# FINAL-CORRECTION (F5 truthfulness): the with-record error line is
# NEUTRAL — it reports the page's error indication and directs the
# user to the actual persisted refresh state shown below; it never
# claims that the particular request failed.
LINE_ERROR = "The page reports a vendor refresh error"
LINE_ERROR_INSPECT = "The latest persisted refresh state is shown below"
# The FU1 operation-failure assertion — must NEVER render again.
LINE_ERROR_OLD_ASSERTION = "could not be completed for this request"
LINE_ERROR_NEUTRAL = (
    "No vendor refresh is recorded for this run, so no refresh result "
    "is available"
)
LINE_NO_RECORD = "No vendor refresh has been recorded for this run yet."
LINE_OLD_ASSURANCE = "No vendor data was changed"  # FU1 F3: must be GONE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _allowed_client() -> Client:
    return Client(REMOTE_ADDR=ALLOWED_ADDR)


def _get_flag(client: Client, run, flag: str) -> str:
    return client.get(
        f"{_detail_url(run.id)}?vendor_refresh={quote(flag, safe='')}"
    ).content.decode()


def _get_detail(client: Client, run) -> str:
    return client.get(_detail_url(run.id)).content.decode()


def _with_settings(cidrs: str | None):
    return patch(
        "product_intelligence.web.commercial_access._django_settings",
        _settings_mock(cidrs),
    )


def _refresh_section(html: str) -> str:
    start = html.index('aria-label="Vendor refresh"')
    end = html.index("</section>", start)
    return html[start:end]


def _original_region(html: str) -> str:
    start = html.index("Quote & Market Summary")
    end = html.index("</section>", start)
    return html[start:end]


def _completed_child(
    run,
    *,
    at,
    operator: str = "op-u",
    lookup_status: str = "SUCCESS",
    observations=(),
    retrieved_at=None,
    payload=None,
) -> VendorRefreshExecution:
    # A lookup that recorded observations carries its retrieval
    # instant (the payload-owned ORIGINAL retrieval timestamp); a
    # no-quote lookup carries none.
    if retrieved_at is None and observations:
        retrieved_at = RETRIEVED_R1
    child = claim_vendor_refresh(trigger_vendor_refresh(run.id, operator=operator).id)
    if payload is not None:
        complete_vendor_refresh(child.id, 1, payload, at=at)
    else:
        complete_vendor_refresh(
            child.id,
            1,
            encode_research_supplement_result(
                ResearchSupplementResult(
                    vendor_commercial_result=VendorCommercialResult(
                        lookup_status=lookup_status,
                        retrieved_at=retrieved_at,
                        observations=observations,
                        source_issues=(),
                    )
                )
            ),
            at=at,
        )
    return child


def _failed_child(
    run,
    *,
    at,
    operator: str = "op-f",
    reason=VendorRefreshFailureReason.INTERNAL_ERROR,
) -> VendorRefreshExecution:
    child = claim_vendor_refresh(trigger_vendor_refresh(run.id, operator=operator).id)
    fail_vendor_refresh(child.id, reason, at=at)
    return child


def _active_child(
    run, *, operator: str = "op-a", claimed: bool = True
) -> VendorRefreshExecution:
    child = trigger_vendor_refresh(run.id, operator=operator)
    if claimed:
        child = claim_vendor_refresh(child.id)
    return child


def _corrupted_completed_child(
    run, *, at, operator: str = "op-c"
) -> VendorRefreshExecution:
    """A COMPLETED lifecycle shape with a non-codec payload (the
    tamper/corruption scenario: the storage CHECK admits any dict
    payload; the codec owns validity)."""
    child = claim_vendor_refresh(trigger_vendor_refresh(run.id, operator=operator).id)
    VendorRefreshExecution.objects.filter(id=child.id).update(
        state=VendorRefreshState.COMPLETED,
        active_slot=None,
        finished_at=at,
        result_schema_version=1,
        result_payload={"not": "a codec payload"},
    )
    return VendorRefreshExecution.objects.get(id=child.id)


def _no_claim_lines(html: str) -> None:
    """Assert that NO success / failure / in-progress claim line
    renders (the F1 invariant for a forged flag)."""
    assert LINE_SUCCESS not in html
    assert LINE_COMPLETED_NO_QUOTE not in html
    assert LINE_FAILED not in html
    assert LINE_IN_PROGRESS not in html


# ---------------------------------------------------------------------------
# F1 — forged GET flags with NO refresh record
# ---------------------------------------------------------------------------


class TestForgedGetFlagsNoRecord(TestCase):
    """A forged ?vendor_refresh= flag over a parent with NO persisted
    refresh record must never create a success, failure, in-progress,
    cooldown, or not-eligible claim. The section still shows the
    persisted truth ("no record yet")."""

    def _html_for_flag(self, run, flag: str) -> str:
        with _with_settings(CIDRS):
            return _get_flag(_allowed_client(), run, flag)

    def test_forged_completed_flag_with_no_record_shows_no_success_claim(self):
        run = _make_completed_run()
        html = self._html_for_flag(run, "completed")
        _no_claim_lines(html)
        assert html.count("Vendor prices were refreshed") == 0
        assert LINE_NO_RECORD in html  # the persisted truth remains

    def test_forged_failed_flag_with_no_record_shows_no_failure_claim(self):
        run = _make_completed_run()
        html = self._html_for_flag(run, "failed")
        assert LINE_FAILED not in html
        assert LINE_SUCCESS not in html
        assert LINE_NO_RECORD in html

    def test_forged_in_progress_flag_with_no_record_shows_no_claim(self):
        run = _make_completed_run()
        html = self._html_for_flag(run, "in_progress")
        assert LINE_IN_PROGRESS not in html
        assert LINE_NO_RECORD in html

    def test_forged_cooldown_flag_with_no_record_shows_no_claim(self):
        run = _make_completed_run()
        html = self._html_for_flag(run, "cooldown")
        assert LINE_COOLDOWN not in html
        assert "A vendor refresh finished recently" not in html
        assert LINE_NO_RECORD in html

    def test_forged_not_eligible_flag_on_eligible_run_shows_no_claim(self):
        run = _make_completed_run()  # COMPLETED + snapshot + MPN: eligible
        html = self._html_for_flag(run, "not_eligible")
        assert LINE_NOT_ELIGIBLE not in html
        assert LINE_NO_RECORD in html

    def test_forged_error_flag_with_no_record_renders_only_the_bounded_transient_line(self):
        run = _make_completed_run()
        html = self._html_for_flag(run, "error")
        # FU2 (F5) + FINAL-CORRECTION (F5 truthfulness): with NO
        # persisted refresh attempt the forged flag renders the
        # NEUTRAL no-record line — it must not assert that a refresh
        # occurred, failed, or was rolled back, and the operation-
        # failure assertion no longer renders in ANY shape. It makes
        # no success / failure / in-progress claim.
        assert LINE_ERROR_NEUTRAL in html
        assert LINE_ERROR not in html
        assert LINE_ERROR_OLD_ASSERTION not in html
        _no_claim_lines(html)
        assert LINE_OLD_ASSURANCE not in html  # FU1 F3
        assert LINE_NO_RECORD in html

    def test_flag_outside_vocabulary_renders_no_notice_and_is_not_reflected(self):
        run = _make_completed_run()
        with _with_settings(CIDRS):
            client = _allowed_client()
            html_banana = _get_flag(client, run, "banana")
            html_script = _get_flag(
                client, run, "<script>alert(1)</script>"
            )
        for html in (html_banana, html_script):
            _no_claim_lines(html)
            assert LINE_COOLDOWN not in html
            assert LINE_NOT_ELIGIBLE not in html
            assert LINE_ERROR not in html
            assert LINE_NO_RECORD in html
        # The raw client value is never reflected into the page.
        assert "<script>alert(1)</script>" not in html_script
        assert "alert(1)" not in html_script
        assert "banana" not in html_banana


# ---------------------------------------------------------------------------
# F1 — forged GET flags with CONFLICTING persisted states
# ---------------------------------------------------------------------------


class TestForgedGetFlagsConflictingState(TestCase):
    """A forged flag over persisted state that CONFLICTS with it must
    not render the conflicting claim; a flag that AGREES with the
    persisted state is backed and renders."""

    def _html_for_flag(self, run, flag: str) -> str:
        with _with_settings(CIDRS):
            return _get_flag(_allowed_client(), run, flag)

    def test_forged_cooldown_flag_over_old_terminal_shows_no_claim(self):
        """A terminal record finished 600 s ago is NOT 'recently
        finished': the cooldown claim is not backed."""
        run = _make_completed_run()
        _completed_child(
            run,
            at=PINNED - timedelta(seconds=600),
            lookup_status="FAILED",
            observations=(),
        )
        with patch("django.utils.timezone.now", lambda: PINNED), _with_settings(CIDRS):
            html = _get_flag(_allowed_client(), run, "cooldown")
        assert LINE_COOLDOWN not in html
        assert "A vendor refresh finished recently" not in html

    def test_forged_not_eligible_flag_over_ineligible_run_is_backed(self):
        """The one backed not-eligible shape over a COMPLETED parent:
        the defensive trigger checks (no price snapshot / no MPN)."""
        run = _make_completed_run()
        PriceIntelligenceSnapshot.objects.filter(run=run).delete()
        html = self._html_for_flag(run, "not_eligible")
        assert LINE_NOT_ELIGIBLE in html
        _no_claim_lines(html)

    def test_completed_flag_over_latest_failed_terminal_is_not_backed(self):
        """Latest attempt is a FAILED terminal record: the forged
        success claim is not backed (the failure + the earlier usable
        quote remain visible — F2)."""
        run = _make_completed_run()
        _completed_child(
            run,
            at=T1,
            observations=(_original_observation("CDW", Decimal("1999.99"), "USD"),),
        )
        _failed_child(run, at=T2)
        html = self._html_for_flag(run, "completed")
        assert LINE_SUCCESS not in html
        assert LINE_COMPLETED_NO_QUOTE not in html
        assert LINE_FAILED not in html  # a forged failed claim would NOT render either
        # The persisted truth: the failed latest attempt + the
        # historical usable quote.
        assert "An internal error stopped the refresh." in html
        assert "$1,999.99 USD" in html
        assert "Last usable vendor quote (historical)" in html

    def test_failed_flag_over_latest_completed_terminal_is_not_backed(self):
        """Latest attempt is a usable COMPLETED record: the forged
        failure claim is not backed."""
        run = _make_completed_run()
        _completed_child(
            run,
            at=T1,
            observations=(_original_observation("CDW", Decimal("1999.99"), "USD"),),
        )
        html = self._html_for_flag(run, "failed")
        assert LINE_FAILED not in html
        assert LINE_SUCCESS not in html

    def test_completed_flag_over_active_latest_attempt_is_not_backed(self):
        """An active (PENDING) child is the latest attempt: the forged
        success claim is not backed."""
        run = _make_completed_run()
        _completed_child(
            run,
            at=T1,
            observations=(_original_observation("CDW", Decimal("1999.99"), "USD"),),
        )
        _active_child(run, claimed=False)  # a PENDING orphan (never claimed)
        html = self._html_for_flag(run, "completed")
        assert LINE_SUCCESS not in html
        assert LINE_COMPLETED_NO_QUOTE not in html
        assert "In progress" in html  # the persisted truth of the latest attempt

    def test_in_progress_flag_over_active_row_is_backed(self):
        run = _make_completed_run()
        _active_child(run, claimed=False)
        html = self._html_for_flag(run, "in_progress")
        assert LINE_IN_PROGRESS in html

    def test_failed_flag_over_failed_latest_is_backed(self):
        run = _make_completed_run()
        _completed_child(
            run,
            at=T1,
            observations=(_original_observation("CDW", Decimal("1999.99"), "USD"),),
        )
        _failed_child(run, at=T2)
        html = self._html_for_flag(run, "failed")
        assert LINE_FAILED in html
        assert LINE_SUCCESS not in html

    def test_completed_flag_over_completed_no_quote_latest_is_the_bounded_no_quote_line(self):
        """Latest attempt is a COMPLETED lookup with NO usable quote:
        the success line is not backed; the bounded no-quote line is
        (the refresh completed, the quote was not)."""
        run = _make_completed_run()
        _completed_child(
            run,
            at=T2,
            lookup_status="FAILED",
            observations=(),
        )
        html = self._html_for_flag(run, "completed")
        assert LINE_SUCCESS not in html
        assert LINE_COMPLETED_NO_QUOTE in html

    def test_cooldown_flag_backed_only_inside_the_strict_300s_window(self):
        """The cooldown claim mirrors the service's STRICT < 300 s
        safeguard fact: backed inside the window, not backed at or
        outside the boundary."""
        # Inside (299 s): backed.
        run_in = _make_completed_run(description="in")
        _completed_child(
            run_in,
            at=PINNED - timedelta(seconds=299),
            lookup_status="FAILED",
            observations=(),
        )
        with patch("django.utils.timezone.now", lambda: PINNED), _with_settings(CIDRS):
            html_in = _get_flag(_allowed_client(), run_in, "cooldown")
        assert LINE_COOLDOWN in html_in
        # Exactly at the boundary (300 s): NOT backed (STRICT <).
        run_eq = _make_completed_run(description="eq")
        _completed_child(
            run_eq,
            at=PINNED - timedelta(seconds=300),
            lookup_status="FAILED",
            observations=(),
        )
        with patch("django.utils.timezone.now", lambda: PINNED), _with_settings(CIDRS):
            html_eq = _get_flag(_allowed_client(), run_eq, "cooldown")
        assert LINE_COOLDOWN not in html_eq
        # Outside (301 s): not backed.
        run_out = _make_completed_run(description="out")
        _completed_child(
            run_out,
            at=PINNED - timedelta(seconds=301),
            lookup_status="FAILED",
            observations=(),
        )
        with patch("django.utils.timezone.now", lambda: PINNED), _with_settings(CIDRS):
            html_out = _get_flag(_allowed_client(), run_out, "cooldown")
        assert LINE_COOLDOWN not in html_out


# ---------------------------------------------------------------------------
# F2 — the last usable vendor quote stays visible
# ---------------------------------------------------------------------------


class TestLastUsableQuoteVisibility(TestCase):
    """The latest refresh attempt and the last usable vendor quote are
    presented separately; a later failed / in-progress / no-quote
    attempt never hides an earlier usable quote (which keeps its
    ORIGINAL retrieval timestamp and an explicit historical label);
    malformed rows never fabricate prices; the original report region
    and the DENIED zero-knowledge boundary are untouched."""

    def _detail_html(self, run) -> str:
        with _with_settings(CIDRS):
            return _get_detail(_allowed_client(), run)

    def test_failed_attempt_does_not_hide_earlier_usable_quote(self):
        run = _make_completed_run()
        _completed_child(
            run,
            at=T1,
            observations=(_original_observation("CDW", Decimal("1999.99"), "USD"),),
        )
        _failed_child(run, at=T2)
        html = self._detail_html(run)
        section = _refresh_section(html)
        # 1. Latest refresh attempt: the FAILED record, with its
        #    failure notice preserved.
        assert "Latest refresh attempt" in section
        assert "An internal error stopped the refresh." in section
        # 2. Last usable vendor quote: the EARLIER COMPLETED quote,
        #    explicitly historical, with its ORIGINAL retrieval
        #    timestamp — never described as current.
        assert section.index("Latest refresh attempt") < section.index(
            "Last usable vendor quote"
        )
        assert "Last usable vendor quote (historical)" in section
        assert "not the current vendor prices" in section
        assert "$1,999.99 USD" in section
        assert "Prices retrieved (original)" in section
        assert "2025-12-01 08:00 UTC" in section  # the payload's original instant
        # The failure row is not a quotation: the only price in the
        # section is the historical quote's (rendered exactly once).
        assert section.count("$1,999.99 USD") == 1

    def test_in_progress_attempt_keeps_earlier_usable_quote_visible(self):
        run = _make_completed_run()
        _completed_child(
            run,
            at=T1,
            observations=(_original_observation("CDW", Decimal("1999.99"), "USD"),),
        )
        _active_child(run, claimed=False)
        html = self._detail_html(run)
        section = _refresh_section(html)
        assert "Latest refresh attempt" in section
        assert "In progress" in section
        assert "Last usable vendor quote (historical)" in section
        assert "$1,999.99 USD" in section
        assert "not the current vendor prices" in section

    def test_latest_attempt_that_is_itself_the_usable_quote_shows_no_historical_block(self):
        run = _make_completed_run()
        _completed_child(
            run,
            at=T1,
            observations=(_original_observation("CDW", Decimal("1999.99"), "USD"),),
        )
        html = self._detail_html(run)
        section = _refresh_section(html)
        # The quote is THE latest attempt: shown once, as the latest —
        # never labeled historical.
        assert "$1,999.99 USD" in section
        assert "Last usable vendor quote" not in section
        assert "historical" not in section
        assert "Latest refresh attempt" in section

    def test_completed_no_quote_latest_shows_earlier_usable_quote_historically(self):
        run = _make_completed_run()
        _completed_child(
            run,
            at=T1,
            observations=(_original_observation("CDW", Decimal("1999.99"), "USD"),),
        )
        _completed_child(
            run, at=T2, lookup_status="FAILED", observations=()
        )
        html = self._detail_html(run)
        section = _refresh_section(html)
        # The latest attempt (executed lookup, FAILED result) stays
        # labeled as such.
        assert "Lookup failed — no vendor quote obtained" in section
        assert "No usable vendor quote was recorded for this refresh." in section
        # The earlier usable quote remains visible, historical.
        assert "Last usable vendor quote (historical)" in section
        assert "$1,999.99 USD" in section
        assert "not the current vendor prices" in section

    def test_unreadable_completed_row_is_never_selected_as_the_usable_quote(self):
        run = _make_completed_run()
        _completed_child(
            run,
            at=T1,
            observations=(_original_observation("CDW", Decimal("1999.99"), "USD"),),
        )
        _corrupted_completed_child(run, at=T2)
        html = self._detail_html(run)
        section = _refresh_section(html)
        # The corrupted latest attempt fails closed...
        assert "could not be read" in section
        # ...and is NEVER selected as the usable quote: the earlier
        # codec-validated quote is the historical one.
        assert "Last usable vendor quote (historical)" in section
        assert "$1,999.99 USD" in section
        assert "not a codec payload" not in html  # no raw payload content

    def test_corrupted_only_completed_row_fabricates_nothing(self):
        run = _make_completed_run()
        _corrupted_completed_child(run, at=T1)
        html = self._detail_html(run)
        section = _refresh_section(html)
        assert "could not be read" in section
        assert "Last usable vendor quote" not in section
        assert "$" not in section  # no price fabricated

    def test_usable_quote_selection_prefers_newest_over_older(self):
        run = _make_completed_run()
        _completed_child(
            run,
            at=T1,
            observations=(_original_observation("CDW", Decimal("1999.99"), "USD"),),
        )
        _completed_child(
            run,
            at=T2,
            observations=(_original_observation("Ingram", Decimal("2400.00"), "USD"),),
        )
        _failed_child(run, at=T3)
        html = self._detail_html(run)
        section = _refresh_section(html)
        # The NEWEST usable quote (T2) is the historical one; the older
        # (T1) is not displayed at all.
        assert "$2,400.00 USD" in section
        assert "$1,999.99 USD" not in section
        assert "Ingram" in section

    def test_zero_observation_success_lookup_is_not_selected_as_usable(self):
        run = _make_completed_run()
        _completed_child(
            run,
            at=T1,
            observations=(_original_observation("CDW", Decimal("1999.99"), "USD"),),
        )
        # A SUCCESS lookup with ZERO observations is not a usable
        # quotation (concept 3: at least one observation).
        _completed_child(run, at=T2, lookup_status="SUCCESS", observations=())
        html = self._detail_html(run)
        section = _refresh_section(html)
        assert "No usable vendor quote was recorded for this refresh." in section
        assert "Last usable vendor quote (historical)" in section
        assert "$1,999.99 USD" in section

    def test_original_report_region_unchanged_with_historical_quote_displayed(self):
        """The original research report / vendor supplement region is
        byte-identical with (and without) refresh history displayed —
        the historical quote never leaks into the original region."""
        run = _make_completed_run()
        original = ResearchSupplementResult(
            vendor_commercial_result=VendorCommercialResult(
                lookup_status="SUCCESS",
                retrieved_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=dt_timezone.utc),
                observations=(_original_observation("CDW", Decimal("1999.99"), "USD"),),
                source_issues=(),
            )
        )
        ResearchSupplementSnapshot.objects.create(
            run=run, schema_version=1, payload=encode_research_supplement_result(original)
        )
        with _with_settings(CIDRS):
            client = _allowed_client()
            before = _original_region(_get_detail(client, run))
        _completed_child(
            run,
            at=T1,
            observations=(_original_observation("Ingram", Decimal("2400.00"), "USD"),),
        )
        _failed_child(run, at=T2)
        with _with_settings(CIDRS):
            after = _original_region(_get_detail(_allowed_client(), run))
        assert before == after  # byte-identical original region
        assert "$2,400.00 USD" not in after  # no historical quote in the region
        # The original supplement row is untouched in the database.
        row = ResearchSupplementSnapshot.objects.get(run=run)
        assert row.payload == encode_research_supplement_result(original)

    def test_denied_connection_stays_zero_knowledge_with_historical_quote(self):
        """A DENIED connection learns nothing about the dual display:
        no section, no state, no operator, no price, no label."""
        run = _make_completed_run()
        _completed_child(
            run,
            at=T1,
            operator="op-u",
            observations=(_original_observation("Ingram", Decimal("2400.00"), "USD"),),
        )
        _failed_child(run, at=T2, operator="op-f")
        with _with_settings(None):
            html = _get_detail(Client(REMOTE_ADDR=ALLOWED_ADDR), run)
        assert "Vendor refresh" not in html
        assert "Last usable vendor quote" not in html
        assert "historical" not in html
        assert "$2,400.00 USD" not in html
        assert "op-u" not in html
        assert "op-f" not in html


# ---------------------------------------------------------------------------
# F3 — the error notice makes no unestablished assurance
# ---------------------------------------------------------------------------


class TestErrorNoticeWording(TestCase):
    """The bounded error notice no longer claims 'No vendor data was
    changed' (not established for every error or outcome-unknown
    path); it asserts no rollback and no terminal outcome, and points
    to the persisted record shown below. FU2 (F5): over NO persisted
    refresh attempt the notice is the neutral no-record line — the
    client-controlled flag alone never asserts that an operation
    occurred, failed, or was rolled back. FINAL-CORRECTION (F5
    truthfulness): over a persisted attempt the error line is NEUTRAL
    too — it reports the page's error indication and directs the user
    to the actual persisted refresh state shown below; it never claims
    that the particular request failed (a historical row — even a
    successfully COMPLETED one — is not proof of that)."""

    def test_error_notice_makes_no_unchanged_data_claim_after_real_post_error(self):
        """A real POST whose executor raises a non-bounded error
        (outcome unknown; the child stays RUNNING) renders the
        bounded NEUTRAL error line (FINAL-CORRECTION F5 truthfulness:
        no operation-failure assertion for this request) — with no
        data-assurance claim."""
        run = _make_completed_run()

        def _boom(child_id):
            raise RuntimeError("non-bounded executor failure")

        with (
            _with_settings(CIDRS),
            patch.dict(
                "os.environ", {"PI_VENDOR_LOOKUP_BASE_URL": "http://vendor.internal/api"}
            ),
            patch(
                "product_intelligence.web.views."
                "execute_claimed_vendor_refresh_with_default_providers",
                _boom,
            ),
        ):
            client = _allowed_client()
            html = _post_refresh(client, run).content.decode()
        # The bounded NEUTRAL line (FU1 F3 + FINAL-CORRECTION F5):
        # it directs to the actual persisted state, never claims this
        # request failed, and asserts no unchanged data.
        assert LINE_ERROR in html
        assert LINE_ERROR_INSPECT in html
        assert LINE_ERROR_OLD_ASSERTION not in html
        # The old unestablished assurance is gone.
        assert LINE_OLD_ASSURANCE not in html
        # The persisted truth is shown: the child is RUNNING (outcome
        # unknown), displayed as in-progress — the error line implies
        # neither success nor a data rollback.
        assert "In progress" in html

    def test_error_notice_line_over_forged_flag_makes_no_unchanged_data_claim(self):
        run = _make_completed_run()
        with _with_settings(CIDRS):
            html = _get_flag(_allowed_client(), run, "error")
        # FU2 (F5) + FINAL-CORRECTION (F5 truthfulness): no persisted
        # attempt -> the neutral no-record line; the operation-failure
        # assertion renders never, in any shape.
        assert LINE_ERROR_NEUTRAL in html
        assert LINE_ERROR not in html
        assert LINE_ERROR_OLD_ASSERTION not in html
        assert LINE_OLD_ASSURANCE not in html
        _no_claim_lines(html)
