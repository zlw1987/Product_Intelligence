"""VENDOR-REFRESH-WEB FU2 — final review corrections (F4/F5).

Focused coverage for the FU2 corrections on top of the pinned
VENDOR-REFRESH-WEB (``test_vendor_refresh_web.py``) and FU1
(``test_vendor_refresh_web_fu1.py``) contracts:

* **F4 — persisted quote identity verification.** The FU1
  ``_decoded_result_has_usable_quote`` predicate assumed codec-valid
  observations are identity-bound to the current ResearchRun; the
  frozen codec alone does not establish that. At the authorized
  refresh presentation boundary the binding is now re-established
  with the frozen 2A comparator (``compare_part_numbers``):
  - the persisted row's ``requested_mpn`` must agree with the parent
    ResearchRun's MPN (an established EXACT / NORMALIZED_EXACT match);
  - EVERY price observation's ``explicit_candidate_mpn`` must be an
    actually established EXACT / NORMALIZED_EXACT match against the
    requested MPN, consistent with the recorded
    ``vendor_mpn_match_type`` (an over- or under-claim is refused).
  A codec-valid payload with an unrelated MPN never appears as a
  usable quote: the latest refresh display fails closed (no payload
  fact — price, lookup status, retrieval instant, or issue — is
  shown) and the row is never selected as the last usable vendor
  quote (historical). A legitimate NORMALIZED_EXACT observation is
  still a usable quote (correct-price behavior preserved).
* **F5 — the error notice is neutral in every shape.** A standalone
  ``GET ?vendor_refresh=error`` must never claim that the particular
  request failed: with NO persisted refresh attempt the neutral
  no-record line renders (no refresh asserted to have occurred,
  succeeded, failed, or rolled back); with a persisted attempt
  (active or terminal — including a successfully COMPLETED one) the
  NEUTRAL error line renders: it reports the page's error indication
  and directs the user to the actual persisted refresh state shown
  below (FINAL-CORRECTION: the old "could not be completed for this
  request" operation-failure assertion no longer renders in any
  shape; a historical row is not proof that the current browser
  request failed).

Class discipline: deterministic D nodes over the in-memory suite
database, reusing the pinned parent + FU1 helpers; pinned terminal
instants (T1 < T2 < T3) for the canonical ordering.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.test import Client, TestCase

from product_intelligence.research.commercial_supplement_codec import (
    SupplementSourceObservation,
)
from product_intelligence.runs.models import VendorRefreshExecution

from tests.web.test_vendor_refresh_web import (
    ALLOWED_ADDR,
    CIDRS,
    PINNED,
    TEST_MPN,
    _make_completed_run,
    _settings_mock,
)
from tests.web.test_vendor_refresh_web_fu1 import (
    LINE_COMPLETED_NO_QUOTE,
    LINE_ERROR,
    LINE_ERROR_INSPECT,
    LINE_ERROR_NEUTRAL,
    LINE_ERROR_OLD_ASSERTION,
    LINE_NO_RECORD,
    LINE_SUCCESS,
    T1,
    T2,
    _active_child,
    _allowed_client,
    _completed_child,
    _failed_child,
    _get_detail,
    _get_flag,
    _no_claim_lines,
    _original_observation,
    _refresh_section,
    _with_settings,
)

# A codec-valid but UNRELATED part number (never matches TEST_MPN
# under the frozen 2A comparator: different structure -> UNKNOWN).
WRONG_MPN = "OTHER-MPN-999"
# The legitimate normalized variant of TEST_MPN (frozen 2A:
# differs only by ASCII letter case -> NORMALIZED_EXACT).
MPN_NORMALIZED_VARIANT = TEST_MPN.lower()

# Bounded display lines (fixed vocabulary of the section).
LINE_IDENTITY_UNVERIFIED = (
    "part-number identity could not be verified against this run"
)
LINE_NO_USABLE = "No usable vendor quote was recorded for this refresh."


def _observation(
    source_name: str,
    price: Decimal,
    currency: str,
    *,
    mpn: str = TEST_MPN,
    match_type: str = "EXACT",
) -> SupplementSourceObservation:
    """One codec-legal observation with a caller-controlled explicit
    candidate MPN + recorded match type (the F4 adversarial shapes:
    the codec admits the type vocabulary, it does not verify the
    claim against any requested part number)."""
    return SupplementSourceObservation(
        source_name=source_name,
        explicit_candidate_mpn=mpn,
        vendor_mpn_match_type=match_type,
        price_amount=price,
        currency_code=currency,
        availability="IN_STOCK",
        price_basis="CUSTOMER_PRICE",
        quantity=1,
        note_kind=None,
        brand_new=True,
        brand_new_basis="VENDOR_API_POLICY",
    )


def _tamper_requested_mpn(child: VendorRefreshExecution, mpn: str) -> None:
    """The wrong parent/child binding shape: the persisted row's
    captured MPN no longer agrees with the parent (the storage CHECK
    admits any non-empty value; the binding is a recorded fact, not a
    schema guarantee — exactly why the display re-verifies)."""
    VendorRefreshExecution.objects.filter(id=child.id).update(requested_mpn=mpn)


class _DetailMixin:
    def _detail_section(self, run) -> str:
        with _with_settings(CIDRS):
            html = _get_detail(_allowed_client(), run)
        return _refresh_section(html)


# ---------------------------------------------------------------------------
# F4 — a codec-valid but wrong-MPN observation is never a usable quote
# ---------------------------------------------------------------------------


class TestWrongMpnObservation(_DetailMixin, TestCase):
    """A codec-valid payload whose observation MPN is unrelated to the
    requested part number fails closed at the presentation boundary:
    never a price in the latest display, never selected historically,
    never backs a forged success flag."""

    def _wrong_mpn_child(self, run, *, at, mpn: str = WRONG_MPN,
                         match_type: str = "EXACT"):
        return _completed_child(
            run,
            at=at,
            observations=(
                _observation("CDW", Decimal("1999.99"), "USD",
                             mpn=mpn, match_type=match_type),
            ),
        )

    def test_wrong_mpn_observation_latest_display_fails_closed(self):
        run = _make_completed_run()
        self._wrong_mpn_child(run, at=T1)
        section = self._detail_section(run)
        # No price, no retrieval instant, no lookup-status claim, no
        # FX notice from the unverified payload (payload facts
        # suppressed; the row's lifecycle state remains a row fact).
        assert "$1,999.99 USD" not in section
        assert "Prices retrieved" not in section
        assert "Vendor lookup" not in section
        assert "Not converted" not in section
        assert "CDW" not in section
        assert LINE_IDENTITY_UNVERIFIED in section
        assert "Completed" in section  # the row's lifecycle state
        # Not a usable quote: no historical block, no success line.
        assert "Last usable vendor quote" not in section
        assert LINE_NO_USABLE not in section

    def test_wrong_mpn_observation_with_recorded_normalized_claim_fails_closed(self):
        """A recorded NORMALIZED_EXACT claim over an actually
        unrelated MPN is refused the same way (the recorded type is
        never trusted over the frozen comparator)."""
        run = _make_completed_run()
        self._wrong_mpn_child(run, at=T1, match_type="NORMALIZED_EXACT")
        section = self._detail_section(run)
        assert "$1,999.99 USD" not in section
        assert LINE_IDENTITY_UNVERIFIED in section
        assert "Last usable vendor quote" not in section

    def test_wrong_mpn_observation_is_never_selected_historically(self):
        """An earlier LEGITIMATE quote stays the historical one; the
        newer wrong-MPN row is not selected and its price never
        appears."""
        run = _make_completed_run()
        _completed_child(
            run,
            at=T1,
            observations=(_original_observation("CDW", Decimal("1999.99"), "USD"),),
        )
        _completed_child(
            run,
            at=T2,
            observations=(
                _observation("Ingram", Decimal("2400.00"), "USD", mpn=WRONG_MPN),
            ),
        )
        section = self._detail_section(run)
        # The latest attempt (T2) fails closed...
        assert LINE_IDENTITY_UNVERIFIED in section
        assert "$2,400.00 USD" not in section
        # ...and the historical quote is the legitimate T1 row.
        assert "Last usable vendor quote (historical)" in section
        assert "$1,999.99 USD" in section
        assert "Prices retrieved (original)" in section

    def test_wrong_mpn_observation_forged_completed_flag_is_not_backed(self):
        """The success claim requires the latest attempt to BE the
        last usable quote; a wrong-MPN row is not one: the bounded
        no-quote line renders instead (never success)."""
        run = _make_completed_run()
        self._wrong_mpn_child(run, at=T1)
        with _with_settings(CIDRS):
            html = _get_flag(_allowed_client(), run, "completed")
        assert LINE_SUCCESS not in html
        assert LINE_COMPLETED_NO_QUOTE in html
        assert "$1,999.99 USD" not in html


# ---------------------------------------------------------------------------
# F4 — a wrong parent/child binding is never a usable quote
# ---------------------------------------------------------------------------


class TestWrongParentChildBinding(_DetailMixin, TestCase):
    """A persisted row whose ``requested_mpn`` no longer agrees with
    the parent ResearchRun's MPN (the observations may even be bound
    to that tampered value) fails closed: no payload fact is shown
    and the row is never selected historically."""

    def _tampered_child(self, run, *, at):
        child = _completed_child(
            run,
            at=at,
            observations=(_original_observation("CDW", Decimal("1999.99"), "USD"),),
        )
        _tamper_requested_mpn(child, WRONG_MPN)
        return child

    def test_tampered_requested_mpn_latest_display_fails_closed(self):
        run = _make_completed_run()
        self._tampered_child(run, at=T1)
        section = self._detail_section(run)
        assert "$1,999.99 USD" not in section
        assert "Prices retrieved" not in section
        assert "Vendor lookup" not in section
        assert "CDW" not in section
        assert LINE_IDENTITY_UNVERIFIED in section
        assert "Last usable vendor quote" not in section

    def test_tampered_requested_mpn_is_never_selected_historically(self):
        """The earlier legitimate quote (bound to the parent) remains
        the historical one; the tampered newer row is skipped."""
        run = _make_completed_run()
        _completed_child(
            run,
            at=T1,
            observations=(_original_observation("CDW", Decimal("1999.99"), "USD"),),
        )
        child2 = _completed_child(
            run,
            at=T2,
            observations=(_original_observation("Ingram", Decimal("2400.00"), "USD"),),
        )
        _tamper_requested_mpn(child2, WRONG_MPN)
        section = self._detail_section(run)
        assert LINE_IDENTITY_UNVERIFIED in section
        assert "$2,400.00 USD" not in section
        assert "Last usable vendor quote (historical)" in section
        assert "$1,999.99 USD" in section

    def test_tampered_requested_mpn_forged_completed_flag_is_not_backed(self):
        run = _make_completed_run()
        self._tampered_child(run, at=T1)
        with _with_settings(CIDRS):
            html = _get_flag(_allowed_client(), run, "completed")
        assert LINE_SUCCESS not in html
        assert LINE_COMPLETED_NO_QUOTE in html
        assert "$1,999.99 USD" not in html


# ---------------------------------------------------------------------------
# F4 — a legitimate NORMALIZED_EXACT observation is still a usable quote
# ---------------------------------------------------------------------------


class TestLegitimateNormalizedExactQuote(_DetailMixin, TestCase):
    """The frozen 2A comparator establishes NORMALIZED_EXACT for the
    case-variant of the requested MPN; such a codec-validated,
    actually-bound observation remains a usable quote (correct-price
    behavior preserved). A recorded type inconsistent with the actual
    comparison is refused (no over-claim)."""

    def _normalized_exact_child(self, run, *, at, price=Decimal("1999.99")):
        return _completed_child(
            run,
            at=at,
            observations=(
                _observation("CDW", price, "USD",
                             mpn=MPN_NORMALIZED_VARIANT,
                             match_type="NORMALIZED_EXACT"),
            ),
        )

    def test_normalized_exact_observation_is_displayed_as_usable_quote(self):
        run = _make_completed_run()
        self._normalized_exact_child(run, at=T1)
        section = self._detail_section(run)
        # The correct price is displayed (frozen _format_price
        # convention + the frozen inventory mapping).
        assert "$1,999.99 USD" in section
        assert "In Stock" in section
        assert "Prices retrieved" in section
        assert LINE_IDENTITY_UNVERIFIED not in section
        # The latest attempt IS the quote: no historical block.
        assert "Last usable vendor quote" not in section

    def test_normalized_exact_observation_backs_the_completed_flag(self):
        run = _make_completed_run()
        self._normalized_exact_child(run, at=T1)
        with _with_settings(CIDRS):
            html = _get_flag(_allowed_client(), run, "completed")
        assert LINE_SUCCESS in html  # backed: the latest IS the usable quote
        assert "$1,999.99 USD" in html

    def test_normalized_exact_quote_is_selected_historically_over_later_failed(self):
        run = _make_completed_run()
        self._normalized_exact_child(run, at=T1)
        _failed_child(run, at=T2)
        section = self._detail_section(run)
        assert "Latest refresh attempt" in section
        assert "Last usable vendor quote (historical)" in section
        assert "$1,999.99 USD" in section
        assert "Prices retrieved (original)" in section
        assert "not the current vendor prices" in section
        assert LINE_IDENTITY_UNVERIFIED not in section

    def test_recorded_type_overclaim_fails_closed(self):
        """Recorded EXACT while the frozen comparator establishes only
        NORMALIZED_EXACT (a claim of more certainty than the evidence
        holds): refused — the identity must be consistent with the
        recorded match type."""
        run = _make_completed_run()
        _completed_child(
            run,
            at=T1,
            observations=(
                _observation("CDW", Decimal("1999.99"), "USD",
                             mpn=MPN_NORMALIZED_VARIANT, match_type="EXACT"),
            ),
        )
        section = self._detail_section(run)
        assert "$1,999.99 USD" not in section
        assert LINE_IDENTITY_UNVERIFIED in section
        assert "Last usable vendor quote" not in section


# ---------------------------------------------------------------------------
# F5 — the error notice is neutral without an established operation
# ---------------------------------------------------------------------------


class TestErrorNoticeNeutrality(_DetailMixin, TestCase):
    """A standalone GET ?vendor_refresh=error never claims that the
    particular request failed: with NO persisted refresh attempt the
    neutral no-record line renders (it asserts no refresh occurred,
    succeeded, failed, or rolled back); with a persisted attempt
    (active or terminal — including a successfully COMPLETED one) the
    NEUTRAL error line renders, directing the user to the actual
    persisted refresh state shown below. A DENIED connection learns
    nothing."""

    def test_forged_error_flag_with_no_record_is_neutral(self):
        run = _make_completed_run()
        with _with_settings(CIDRS):
            html = _get_flag(_allowed_client(), run, "error")
        assert LINE_ERROR_NEUTRAL in html
        assert LINE_ERROR not in html  # the with-record neutral line too
        assert LINE_ERROR_OLD_ASSERTION not in html  # no failure assertion
        _no_claim_lines(html)
        assert LINE_NO_RECORD in html  # the persisted truth remains

    def test_forged_error_flag_over_terminal_record_keeps_the_bounded_line(self):
        """A persisted terminal attempt establishes an actual
        operation: the bounded error line still renders — but
        NEUTRAL (FINAL-CORRECTION F5 truthfulness): it reports the
        page's error indication and directs to the actual persisted
        state, never claiming that this request failed."""
        run = _make_completed_run()
        _completed_child(
            run,
            at=PINNED - timedelta(seconds=600),
            lookup_status="FAILED",
            observations=(),
        )
        with _with_settings(CIDRS):
            html = _get_flag(_allowed_client(), run, "error")
        assert LINE_ERROR in html
        assert LINE_ERROR_INSPECT in html
        assert LINE_ERROR_OLD_ASSERTION not in html
        assert LINE_ERROR_NEUTRAL not in html  # a record exists
        assert LINE_NO_RECORD not in html

    def test_forged_error_flag_over_active_record_keeps_the_bounded_line(self):
        """A persisted active attempt likewise establishes an actual
        operation: the bounded error line renders — NEUTRAL (FINAL-
        CORRECTION F5 truthfulness), never an operation-failure
        assertion for this request."""
        run = _make_completed_run()
        _active_child(run, claimed=False)
        with _with_settings(CIDRS):
            html = _get_flag(_allowed_client(), run, "error")
        assert LINE_ERROR in html
        assert LINE_ERROR_INSPECT in html
        assert LINE_ERROR_OLD_ASSERTION not in html
        assert LINE_ERROR_NEUTRAL not in html

    def test_forged_error_flag_over_completed_success_never_claims_failure(self):
        """FINAL-CORRECTION (F5 truthfulness): a successfully
        COMPLETED refresh (a usable identity-bound quote) followed by
        a forged ?vendor_refresh=error GET must NOT claim that that
        request failed — a historical row is not proof that the
        current browser request failed. The bounded error line
        renders (the persisted attempt establishes the operation) —
        NEUTRAL, directing the user to the actual persisted state
        shown below — and the old operation-failure assertion never
        renders; the successful result (its state + identity-bound
        quote) is displayed undimmed by the forged flag."""
        run = _make_completed_run()
        _completed_child(
            run,
            at=T1,
            observations=(_original_observation("CDW", Decimal("1999.99"), "USD"),),
        )
        with _with_settings(CIDRS):
            html = _get_flag(_allowed_client(), run, "error")
        # The bounded error line renders (a persisted attempt
        # exists)...
        assert LINE_ERROR in html
        assert LINE_ERROR_INSPECT in html
        # ...but never the operation-failure assertion for this
        # request, and never the no-record line (a record exists).
        assert LINE_ERROR_OLD_ASSERTION not in html
        assert LINE_ERROR_NEUTRAL not in html
        assert LINE_NO_RECORD not in html
        # No success NOTICE line (the flag is error, not completed)
        # and no claim line of any other kind.
        assert LINE_SUCCESS not in html
        _no_claim_lines(html)
        # The actual persisted refresh state is displayed: the
        # successful result with its identity-bound quote, undimmed
        # by the forged flag.
        section = _refresh_section(html)
        assert "Latest refresh attempt" in section
        assert "Completed" in section
        assert "$1,999.99 USD" in section
        assert "In Stock" in section
        assert LINE_IDENTITY_UNVERIFIED not in section

    def test_denied_forged_error_flag_learns_nothing(self):
        """DENIED zero-knowledge holds for the neutral lines too: the
        section (and every refresh fact) never renders."""
        run = _make_completed_run()
        with _with_settings(None):
            html = _get_flag(Client(REMOTE_ADDR=ALLOWED_ADDR), run, "error")
        assert "Vendor refresh" not in html
        assert LINE_ERROR not in html
        assert LINE_ERROR_OLD_ASSERTION not in html
        assert LINE_ERROR_NEUTRAL not in html
        assert LINE_NO_RECORD not in html
