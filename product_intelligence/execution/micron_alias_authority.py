"""Micron 7500 SSD packaging-alias authority acquisition (PRODUCT-INTEL.4D-D).

Bounded execution-layer module that acquires the 4D-D v1 alias authority
for one ``ResearchRequest`` using the existing ``PageFetcher`` protocol.

Architecture (follows the PATTERN of frozen 7C-PRE1
``comparable_research_authority.py`` — that module's Seagate policy,
extraction, and private data are NOT imported or reused):

* The reviewed v1 policy is module-private production
  configuration-as-code, built from the reviewed constants the research
  contracts pin against. No environment configuration, no database
  content, no caller injection. Extending it (another manufacturer,
  family, endpoint, or suffix set) requires code review.
* The authority source is the exact reviewed 4D-D-PRE2 Micron 7500 SSD
  family-catalog endpoint on the approved ``https://www.micron.com``
  origin. A successful fetch must remain inside that origin
  (scheme downgrade, host escape, port change, and credentials all fail
  closed).
* The LOOKUP BASE CANDIDATE (derived from the request MPN under the
  customer rule) is compared with EVERY source-published catalog
  ``part-number`` through frozen 2A ``compare_part_numbers``. Only
  EXACT / NORMALIZED_EXACT count. Exactly one matching row is required:
  zero is a bounded abstention, more than one fails closed as
  ambiguity.
* The matched row's own structured ``is-ssd == True`` attribute is the
  category evidence. SSD is never inferred from the request
  description, the URL path, a filename, an MPN prefix, or model
  knowledge.
* R/T per-part detail endpoints and R/T page metadata are NOT authority
  (4D-D-PRE2: they return ``Invalid Partnumber`` / template echoes).
  This module never fetches them.

What this module is NOT:

* It does not establish identity. ESTABLISHED means "the request's
  lookup base candidate is a source-published row of the reviewed Micron
  7500 SSD catalog" — manufacturer/category/base authority. The R/T
  relation it may carry is a customer-defined retrieval relation, not
  manufacturer-published packaging identity.
* It does not swallow classified errors. Expected acquisition failures
  (uncallable fetcher, fetch error, source refusal, non-conforming fetch
  result, unclassified bare-``Exception`` network failure, host escape,
  catalog parse failure, missing/ambiguous match, non-SSD category)
  return a bounded ``MicronAliasEligibilityResult``. Programming/invariant
  errors (classified error types, contract construction failures, wrong
  argument types) propagate to the outer catastrophic boundary.

v1 SCOPE (binding): Micron 7500 SSD ONLY.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import ESTABLISHED_MATCH_TYPES
from product_intelligence.providers.page import (
    FetchedPage,
    PageFetchError,
    PageFetchRequest,
    PageFetcher,
    UnsafeFetchTargetError,
)
from product_intelligence.research.identity import compare_part_numbers
from product_intelligence.research.micron_packaging_alias import (
    MICRON_7500_APPROVED_ORIGIN,
    MICRON_7500_CATEGORY,
    MICRON_7500_MANUFACTURER,
    MICRON_7500_POLICY_ID,
    MICRON_7500_REQUESTED_CATALOG_URL,
    MICRON_7500_SOURCE_NAME,
    MicronAliasEligibilityResult,
    MicronAliasEligibilityStatus,
    MicronCatalogParseError,
    MicronSsdCategoryEvidence,
    build_packaging_alias_relation,
    derive_lookup_base_candidate,
    extract_micron_7500_catalog_records,
    matched_ssd_category_evidence,
    url_within_origin,
    verify_ssd_category_evidence,
)


# ---------------------------------------------------------------------------
# Module-private reviewed authority policy (Micron 7500 SSD ONLY)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _MicronAliasAuthorityPolicy:
    """One reviewed 4D-D v1 alias-authority policy record.

    Module-private. Reviewed production configuration-as-code, built from
    the exact constants the research contracts self-validate against —
    there is no second copy of any value that could drift. Not
    environment configuration, not database content, not caller input.
    """

    policy_id: str
    manufacturer: str
    category: str
    source_name: str
    requested_source_url: str
    approved_authority_origin: str


#: The only 4D-D v1 policy. Extending this requires code review.
_MICRON_7500_ALIAS_POLICY: Final[_MicronAliasAuthorityPolicy] = (
    _MicronAliasAuthorityPolicy(
        policy_id=MICRON_7500_POLICY_ID,
        manufacturer=MICRON_7500_MANUFACTURER,
        category=MICRON_7500_CATEGORY,
        source_name=MICRON_7500_SOURCE_NAME,
        requested_source_url=MICRON_7500_REQUESTED_CATALOG_URL,
        approved_authority_origin=MICRON_7500_APPROVED_ORIGIN,
    )
)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def acquire_micron_alias_eligibility(
    *,
    request: ResearchRequest,
    page_fetcher: PageFetcher,
) -> MicronAliasEligibilityResult:
    """Acquire 4D-D v1 packaging-alias eligibility for one request.

    Public production function. No manufacturer, category, source URL,
    policy, origin, extraction mechanism, or alias semantics argument
    exists — the reviewed v1 policy is module-private.

    Pipeline:

    1. Derive the LOOKUP BASE CANDIDATE from the request MPN (customer
       rule, final uppercase R/T only). A missing/empty request MPN is a
       bounded abstention with zero fetches (NO_REQUESTED_MPN). A
       non-empty MPN whose derivation leaves no usable base (e.g. "-R",
       "-T") is a distinct bounded abstention with zero fetches
       (INVALID_LOOKUP_BASE) — invalid structural input is never
       persisted as missing input.
    2. Fetch the exact reviewed family-catalog URL through the existing
       PageFetcher protocol. Source refusal and fetch failure are
       bounded (SOURCE_REFUSED / FETCH_FAILED).
    3. Verify the fetched final URL remains inside the reviewed
       ``https://www.micron.com`` origin (HOST_ESCAPED otherwise).
    4. Extract catalog rows (pure deterministic research module;
       structural corruption is PARSE_FAILED).
    5. Compare the lookup base candidate against EVERY source-published
       row through frozen 2A. Zero established matches:
       NO_AUTHORITY_MATCH. More than one: AMBIGUOUS_AUTHORITY_MATCH.
    6. Require the matched row's own structured ``is-ssd == True``
       evidence (CATEGORY_NOT_SSD otherwise).
    7. Build the customer-defined retrieval relation against the exact
       source-published base MPN and return ESTABLISHED with complete
       provenance (including the deterministic body SHA-256).

    Expected acquisition failures are nonfatal and bounded.
    Programming/invariant errors propagate.
    """
    if not isinstance(request, ResearchRequest):
        raise TypeError(
            f"request must be a ResearchRequest, got {type(request).__name__}"
        )

    policy = _MICRON_7500_ALIAS_POLICY

    # Step 1: pre-fetch abstentions (zero network, zero provenance).
    if not request.manufacturer_part_number:
        # Missing input: the request carried no MPN at all.
        return MicronAliasEligibilityResult(
            status=MicronAliasEligibilityStatus.NO_REQUESTED_MPN,
            request=request,
            lookup_base_candidate=None,
            policy_id=policy.policy_id,
            manufacturer=None,
            category=None,
            requested_source_url=None,
            fetched_final_url=None,
            retrieved_at=None,
            source_name=None,
            matched_base_mpn=None,
            part_number_match=None,
            ssd_category_evidence=None,
            alias_relation=None,
            body_sha256=None,
        )

    candidate = derive_lookup_base_candidate(request.manufacturer_part_number)
    if candidate is None:
        # Present but structurally unusable input: a distinct persisted
        # state, never conflated with NO_REQUESTED_MPN.
        return MicronAliasEligibilityResult(
            status=MicronAliasEligibilityStatus.INVALID_LOOKUP_BASE,
            request=request,
            lookup_base_candidate=None,
            policy_id=policy.policy_id,
            manufacturer=None,
            category=None,
            requested_source_url=None,
            fetched_final_url=None,
            retrieved_at=None,
            source_name=None,
            matched_base_mpn=None,
            part_number_match=None,
            ssd_category_evidence=None,
            alias_relation=None,
            body_sha256=None,
        )

    def _fetch_failed() -> MicronAliasEligibilityResult:
        """Bounded FETCH_FAILED: the reviewed URL was the target; nothing
        usable was fetched, and no authority may be granted."""
        return MicronAliasEligibilityResult(
            status=MicronAliasEligibilityStatus.FETCH_FAILED,
            request=request,
            lookup_base_candidate=candidate,
            policy_id=policy.policy_id,
            manufacturer=None,
            category=None,
            requested_source_url=policy.requested_source_url,
            fetched_final_url=None,
            retrieved_at=None,
            source_name=None,
            matched_base_mpn=None,
            part_number_match=None,
            ssd_category_evidence=None,
            alias_relation=None,
            body_sha256=None,
        )

    # Step 2: fetch the reviewed catalog endpoint.
    #
    # The bounded failure surface mirrors the frozen 4C candidate-fetch
    # path (_process_candidate_url): a fetcher that cannot perform the
    # fetch, that raises an unclassified bare ``Exception`` (a network
    # failure without a specific error class), or that returns a result
    # that does not conform to the ``FetchedPage`` contract is a bounded
    # authority loss — ``FETCH_FAILED``, no authority, the run continues
    # with the ordinary query. Classified error types (concrete
    # ``Exception`` subclasses) remain programming or environmental
    # defects and propagate to the outer catastrophic boundary.
    fetch = getattr(page_fetcher, "fetch", None)
    if not callable(fetch):
        return _fetch_failed()
    try:
        fetched = fetch(PageFetchRequest(url=policy.requested_source_url))
    except UnsafeFetchTargetError:
        return MicronAliasEligibilityResult(
            status=MicronAliasEligibilityStatus.SOURCE_REFUSED,
            request=request,
            lookup_base_candidate=candidate,
            policy_id=policy.policy_id,
            manufacturer=None,
            category=None,
            requested_source_url=policy.requested_source_url,
            fetched_final_url=None,
            retrieved_at=None,
            source_name=None,
            matched_base_mpn=None,
            part_number_match=None,
            ssd_category_evidence=None,
            alias_relation=None,
            body_sha256=None,
        )
    except PageFetchError:
        return _fetch_failed()
    except Exception as exc:
        if type(exc) is not Exception:
            raise
        return _fetch_failed()

    # The result must conform to the FetchedPage contract for its
    # provenance to be trusted at all. A real HttpPageFetcher always
    # produces a validated FetchedPage, so this is a no-op in production;
    # a non-conforming result (including one whose provenance fields cannot
    # even be read) carries no verifiable provenance and can therefore
    # grant no authority.
    try:
        conforming = (
            isinstance(fetched, FetchedPage)
            and isinstance(fetched.final_url, str)
            and isinstance(fetched.body_text, str)
            and isinstance(fetched.retrieved_at, datetime)
            and fetched.retrieved_at.tzinfo is not None
            and fetched.retrieved_at.utcoffset() is not None
        )
    except AttributeError:
        conforming = False
    if not conforming:
        return _fetch_failed()

    fetched_final_url = fetched.final_url
    retrieved_at = fetched.retrieved_at

    # Step 3: origin boundary (a redirect that escapes the reviewed
    # origin is a fail-closed authority loss, not a normal page).
    if not url_within_origin(fetched_final_url, policy.approved_authority_origin):
        return MicronAliasEligibilityResult(
            status=MicronAliasEligibilityStatus.HOST_ESCAPED,
            request=request,
            lookup_base_candidate=candidate,
            policy_id=policy.policy_id,
            manufacturer=None,
            category=None,
            requested_source_url=policy.requested_source_url,
            fetched_final_url=fetched_final_url,
            retrieved_at=retrieved_at,
            source_name=None,
            matched_base_mpn=None,
            part_number_match=None,
            ssd_category_evidence=None,
            alias_relation=None,
            body_sha256=None,
        )

    body_sha256 = hashlib.sha256(fetched.body_text.encode("utf-8")).hexdigest()

    def _fetched_result(status: MicronAliasEligibilityStatus) -> MicronAliasEligibilityResult:
        return MicronAliasEligibilityResult(
            status=status,
            request=request,
            lookup_base_candidate=candidate,
            policy_id=policy.policy_id,
            manufacturer=None,
            category=None,
            requested_source_url=policy.requested_source_url,
            fetched_final_url=fetched_final_url,
            retrieved_at=retrieved_at,
            source_name=policy.source_name,
            matched_base_mpn=None,
            part_number_match=None,
            ssd_category_evidence=None,
            alias_relation=None,
            body_sha256=body_sha256,
        )

    # Step 4: deterministic catalog extraction (fail closed on
    # structural corruption).
    try:
        records = extract_micron_7500_catalog_records(fetched.body_text)
    except MicronCatalogParseError:
        return _fetched_result(MicronAliasEligibilityStatus.PARSE_FAILED)

    # Step 5: frozen-2A comparison against EVERY source-published row.
    matching = []
    for record in records:
        assessment = compare_part_numbers(candidate, record.part_number)
        if assessment.match_type in ESTABLISHED_MATCH_TYPES:
            matching.append((assessment, record))

    if not matching:
        return _fetched_result(MicronAliasEligibilityStatus.NO_AUTHORITY_MATCH)
    if len(matching) > 1:
        return _fetched_result(
            MicronAliasEligibilityStatus.AMBIGUOUS_AUTHORITY_MATCH
        )

    assessment, record = matching[0]

    # Step 6: the matched row's own structured SSD evidence.
    if not verify_ssd_category_evidence(record):
        return _fetched_result(MicronAliasEligibilityStatus.CATEGORY_NOT_SSD)
    ssd_evidence = matched_ssd_category_evidence(record)

    # Step 7: customer-defined retrieval relation against the exact
    # source-published base MPN. (A construction failure here is a
    # programming/invariant error and propagates — the authority flow
    # can never produce such a pair.)
    relation = build_packaging_alias_relation(
        request.manufacturer_part_number, record.part_number
    )

    return MicronAliasEligibilityResult(
        status=MicronAliasEligibilityStatus.ESTABLISHED,
        request=request,
        lookup_base_candidate=candidate,
        policy_id=policy.policy_id,
        manufacturer=policy.manufacturer,
        category=policy.category,
        requested_source_url=policy.requested_source_url,
        fetched_final_url=fetched_final_url,
        retrieved_at=retrieved_at,
        source_name=policy.source_name,
        matched_base_mpn=record.part_number,
        part_number_match=assessment,
        ssd_category_evidence=MicronSsdCategoryEvidence(
            attr_name=ssd_evidence.name,
            attr_id=ssd_evidence.attr_id,
            attr_value=ssd_evidence.value,
        ),
        alias_relation=relation,
        body_sha256=body_sha256,
    )
