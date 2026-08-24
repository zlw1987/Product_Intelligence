"""Execution evidence vocabularies.

PRODUCT-INTEL.4C-A introduces durable execution-evidence primitives. These
contracts fix the *vocabulary* for execution attempts, stages, and outcomes.
The orchestration layer (4C) owns when they are assigned; the domain only
provides the controlled vocabularies.

Design rules:

* Execution evidence is separate from PriceIntelligenceSnapshot.
  The snapshot preserves the final price conclusion; evidence preserves
  every attempt that led to it (or failed to lead to it).

* Evidence is ordered and immutable. Each attempt produces one record.

* Machine-readable detail codes must be stable. Never persist raw exception
  text or arbitrary provider payloads.

* URLs must follow the repository's existing safe URL/provenance philosophy.
  They are stored exactly as observed, never inferred or fabricated.

* Execution-attempt failures do not automatically mark the whole run FAILED.
  A failed FETCH or EXTRACT may coexist with a successfully completed run.

* No sensitive data (credentials, raw payloads, exception dumps) may be
  persisted through the evidence API. detail_message is intentionally absent
  from the contract to prevent accidental leakage.
"""

from __future__ import annotations

from enum import Enum


class ExecutionStage(str, Enum):
    """An execution attempt's position in the research pipeline.

    The stages are deliberately narrow and tied to concrete primitives:

    * SEARCH: calling a SearchProvider with a query
    * FETCH: opening a candidate URL safely
    * EXTRACT: reading listing observations from a page
    * NORMALIZE: converting raw observations to normalized form
    * MATCH: deciding whether a listing belongs to the requested product
    * AGGREGATE: computing price statistics from accepted listings

    These stages map to the 4A-4B pipeline: search candidates, fetch
    candidates, extract listings, normalize listings, match listings to
    the request, aggregate accepted prices.

    A stage is not "step in pipeline" — it is "one primitive was called".
    The orchestration layer decides when to invoke each primitive.
    """

    SEARCH = "SEARCH"
    """A SearchProvider.search() call."""

    FETCH = "FETCH"
    """A PageFetcher.fetch() call on a candidate URL."""

    EXTRACT = "EXTRACT"
    """extract_listing_observations() on a FetchedPage."""

    NORMALIZE = "NORMALIZE"
    """normalize_listing_observation() on a ListingObservation."""

    MATCH = "MATCH"
    """assess_listing_identity() on a NormalizedListingObservation."""

    AGGREGATE = "AGGREGATE"
    """aggregate_listing_prices() on a set of assessments."""


class ExecutionOutcome(str, Enum):
    """The result of one execution attempt."""

    SUCCESS = "SUCCESS"
    """The primitive completed successfully."""

    FAILED = "FAILED"
    """The primitive failed (provider error, fetch failure, parse error)."""

    SKIPPED = "SKIPPED"
    """The primitive was not invoked (no candidate URL, no raw observation)."""

    BLOCKED = "BLOCKED"
    """The primitive was intentionally not invoked (safe-URL refusal, etc)."""

    EMPTY = "EMPTY"
    """The primitive ran but produced no usable observations."""


class ExecutionDetailCode(str, Enum):
    """A stable, machine-readable reason for an outcome.

    This is a **controlled vocabulary** — only specific codes are permitted.
    Each stage defines which detail codes are valid. A detail code must never
    be raw exception text — it is a classification the orchestration layer
    applies to the outcome.

    Rules:

    * Detail codes are stable identifiers, not human-readable text.
      Human-readable explanations are not persisted to prevent sensitive data
      leakage. The detail_message field was removed for 4C-A.

    * A detail code is specific enough to enable debugging but generic
      enough to avoid vendor-specific details.

    * Detail codes are per-stage. The same outcome code may have different
      detail codes depending on the stage.

    * Detail codes must not include URLs or credentials. They may reference
      a URL field in the evidence record if needed.
    """

    # Common success codes
    OK = "OK"
    """Generic success indicator (no additional detail)."""

    # Search-specific codes
    PROVIDER_ERROR = "PROVIDER_ERROR"
    """SEARCH/FAILED: provider returned an error."""

    TIMEOUT = "TIMEOUT"
    """SEARCH/FAILED: provider call timed out. Reused for FETCH."""

    ZERO_RESULTS = "ZERO_RESULTS"
    """SEARCH/SUCCESS: zero results returned."""

    # Fetch-specific codes
    NETWORK_ERROR = "NETWORK_ERROR"
    """FETCH/FAILED: network failure."""

    HTTP_ERROR = "HTTP_ERROR"
    """FETCH/FAILED: HTTP error status."""

    SAFE_URL_REFUSED = "SAFE_URL_REFUSED"
    """FETCH/BLOCKED: URL was refused by safe-URL checks."""

    # Extract-specific codes
    NO_LISTING_OBSERVATIONS = "NO_LISTING_OBSERVATIONS"
    """EXTRACT/EMPTY: no listing observations extracted."""

    PARSE_ERROR = "PARSE_ERROR"
    """EXTRACT/FAILED: document parsing failed."""

    # Normalize-specific codes
    NO_PRICE = "NO_PRICE"
    """NORMALIZE/SUCCESS: price could not be parsed."""

    # Match-specific codes
    ACCEPTED = "ACCEPTED"
    """MATCH/SUCCESS: listing was accepted."""

    IDENTITY_REJECTED = "IDENTITY_REJECTED"
    """MATCH/SUCCESS: listing was rejected (identity mismatch)."""

    NO_MPN_IN_OBSERVATION = "NO_MPN_IN_OBSERVATION"
    """MATCH/SUCCESS: listing was rejected (no MPN in observation)."""

    @classmethod
    def for_success(cls) -> ExecutionDetailCode:
        """Generic success code."""
        return cls.OK

    @classmethod
    def for_search_provider_error(cls) -> ExecutionDetailCode:
        """SEARCH/FAILED: provider returned an error."""
        return cls.PROVIDER_ERROR

    @classmethod
    def for_search_timeout(cls) -> ExecutionDetailCode:
        """SEARCH/FAILED: provider call timed out."""
        return cls.TIMEOUT

    @classmethod
    def for_search_empty(cls) -> ExecutionDetailCode:
        """SEARCH/SUCCESS: zero results returned."""
        return cls.ZERO_RESULTS

    @classmethod
    def for_fetch_network_error(cls) -> ExecutionDetailCode:
        """FETCH/FAILED: network failure."""
        return cls.NETWORK_ERROR

    @classmethod
    def for_fetch_http_error(cls) -> ExecutionDetailCode:
        """FETCH/FAILED: HTTP error status."""
        return cls.HTTP_ERROR

    @classmethod
    def for_fetch_timeout(cls) -> ExecutionDetailCode:
        """FETCH/FAILED: fetch timed out."""
        return cls.TIMEOUT

    @classmethod
    def for_fetch_safe_url_refused(cls) -> ExecutionDetailCode:
        """FETCH/BLOCKED: URL was refused by safe-URL checks."""
        return cls.SAFE_URL_REFUSED

    @classmethod
    def for_extract_empty(cls) -> ExecutionDetailCode:
        """EXTRACT/EMPTY: no listing observations extracted."""
        return cls.NO_LISTING_OBSERVATIONS

    @classmethod
    def for_extract_parse_error(cls) -> ExecutionDetailCode:
        """EXTRACT/FAILED: document parsing failed."""
        return cls.PARSE_ERROR

    @classmethod
    def for_normalize_no_price(cls) -> ExecutionDetailCode:
        """NORMALIZE/SUCCESS: price could not be parsed."""
        return cls.NO_PRICE

    @classmethod
    def for_match_accepted(cls) -> ExecutionDetailCode:
        """MATCH/SUCCESS: listing was accepted."""
        return cls.ACCEPTED

    @classmethod
    def for_match_rejected_identity(cls) -> ExecutionDetailCode:
        """MATCH/SUCCESS: listing was rejected (identity mismatch)."""
        return cls.IDENTITY_REJECTED

    @classmethod
    def for_match_rejected_no_mpn(cls) -> ExecutionDetailCode:
        """MATCH/SUCCESS: listing was rejected (no MPN in observation)."""
        return cls.NO_MPN_IN_OBSERVATION

    @classmethod
    def for_aggregate_success(cls) -> ExecutionDetailCode | None:
        """AGGREGATE/SUCCESS has no additional detail."""
        return None
