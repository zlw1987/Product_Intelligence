"""Build fixture-based preview data for the PILOT-UX-WORKBENCH-A1 visual
verification (developer tool, never part of pytest).

Creates a FRESH preview SQLite database — a new, uniquely named file inside
the explicitly designated preview directory — with representative runs
covering the required visual cases:

  P1  completed, multiple supplier quotes (3 vendor + 1 public + FX)
  P2  completed, source-published $0 quote (B1 verification note)
  P3  completed, no usable price evidence (UNKNOWN verification)
  P4  completed, AI-assisted review candidate (needs review)
  P5  completed, comparable research result (FULL, one candidate)
  P6  running research state
  P7  failed research state
  P8  created research state

All data is synthetic; no production data, no live provider calls.

PILOT-UX-WORKBENCH-A1-FU1 safety contract (protects real data BY
CONSTRUCTION, not by operator discipline):

* Refuses to run without an explicit preview configuration: the
  ``PI_PREVIEW_DB_DIR`` environment variable must name a designated,
  disposable preview directory.
* Plans a NEW, uniquely named database file per run
  (``preview_<UTC stamp>_<random token>.sqlite3``). It never
  deletes, truncates, overwrites, or replaces any existing database —
  if the planned file already exists it fails closed before any write.
* The configured database is always the planned file: ``PI_SQLITE_PATH``
  is set to it (overriding any pre-existing value) before Django reads
  settings, so a hostile or stale ``PI_SQLITE_PATH`` can never steer this
  script at another database.
* Rejects the repository root (the default ``db.sqlite3`` location),
  production / staging / deployment-like directory names, and any path
  that does not canonically resolve INSIDE the designated preview
  directory. Paths are canonicalized (``os.path.realpath``: symlinks
  resolved, ``..`` collapsed) before every check — no string-prefix
  trust.
* All validation happens before any database write or migration.
* Prints paths and URLs only; never credentials or connection settings.

Usage:

    set PI_PREVIEW_DB_DIR=C:\\dev\\Product_Intelligence_A1\\tmp_preview
    python scripts/preview_fixtures.py
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

PREVIEW_DB_DIR_ENV = "PI_PREVIEW_DB_DIR"

#: Directory-name components that mark production / staging / deployment
#: locations. Any of them anywhere in the canonical preview path refuses
#: the run (fail closed; an operator who names a disposable directory
#: after a deployment environment gets exactly what they asked for).
FORBIDDEN_PREVIEW_DIR_COMPONENTS = frozenset(
    {
        "production",
        "prod",
        "staging",
        "stage",
        "deploy",
        "deployment",
        "release",
        "live",
    }
)


class PreviewConfigurationError(RuntimeError):
    """The preview configuration is missing, unsafe, or not disposable."""


def plan_preview_database(
    preview_dir: "str | Path | None",
    *,
    base_dir: "str | Path",
    now: datetime,
    token: str,
) -> Path:
    """Plan and validate the fresh preview database path. PURE: no I/O,
    no Django, no database access — it either returns a path guaranteed
    to be a new file strictly inside the designated preview directory,
    or raises PreviewConfigurationError.

    Guarantees (checked in order, all fail closed):

    1. ``preview_dir`` is explicitly configured (non-empty).
    2. The canonical (realpath) preview directory is not the repository
       root — the location of the default ``db.sqlite3`` developer
       database, which is not an authorized disposable target.
    3. No canonical path component is a production / staging /
       deployment-like name.
    4. The planned file (fresh unique name) canonicalizes to a path
       strictly INSIDE the canonical preview directory (no traversal or
       symlink escape).
    5. The planned file is not the repository ``db.sqlite3``.
    6. The planned file does not already exist (and is not a dangling
       symlink). This script never deletes or reuses a database.
    """
    if preview_dir is None or not str(preview_dir).strip():
        raise PreviewConfigurationError(
            "missing preview configuration: set "
            f"{PREVIEW_DB_DIR_ENV} to an explicit, disposable preview "
            "directory before running this script"
        )
    resolved_dir = Path(os.path.realpath(str(preview_dir)))
    resolved_base = Path(os.path.realpath(str(base_dir)))

    if resolved_dir == resolved_base:
        raise PreviewConfigurationError(
            "refusing the repository root as the preview directory: it is "
            "the default db.sqlite3 location, not an authorized disposable "
            "preview target"
        )
    for part in resolved_dir.parts:
        if part.lower() in FORBIDDEN_PREVIEW_DIR_COMPONENTS:
            raise PreviewConfigurationError(
                f"refusing production/deployment-like directory component "
                f"{part!r} in the preview path"
            )

    stamp = now.strftime("%Y%m%dT%H%M%S")
    target = resolved_dir / f"preview_{stamp}_{token}.sqlite3"
    target_resolved = Path(os.path.realpath(str(target)))

    if resolved_dir not in target_resolved.parents:
        raise PreviewConfigurationError(
            "planned preview database path does not canonicalize strictly "
            "inside the designated preview directory (path traversal "
            "refused)"
        )
    if target_resolved == resolved_base / "db.sqlite3":
        raise PreviewConfigurationError(
            "refusing the default repository database (db.sqlite3) as the "
            "preview target"
        )
    if target_resolved.exists() or target_resolved.is_symlink():
        raise PreviewConfigurationError(
            "planned preview database already exists; this script never "
            "deletes, overwrites, or reuses a database — choose a fresh "
            "preview directory or let the next unique name be used"
        )
    return target_resolved


def build(preview_db: Path, urls_out: Path) -> None:
    """Migrate and seed the ALREADY-VALIDATED fresh preview database.

    Reached only after plan_preview_database() succeeded, so this function
    can create exactly one new file: ``preview_db``. It never opens,
    truncates, deletes, or replaces any other file.
    """
    base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, str(base_dir))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    import django  # noqa: E402  (after validation; see module contract)

    django.setup()

    from django.core.management import call_command  # noqa: E402
    from django.db import connections  # noqa: E402

    # --- Construction sanity: the configured DB is the planned preview file,
    # --- and it still does not exist. No migration runs before both hold.
    configured = connections["default"].settings_dict["NAME"]
    if Path(configured).resolve() != preview_db.resolve():
        raise RuntimeError(
            "aborting: Django's configured database is not the planned "
            "preview database"
        )
    if Path(configured).exists():
        raise RuntimeError(
            "aborting: the planned preview database appeared before "
            "migration; this script never overwrites an existing file"
        )
    call_command("migrate", verbosity=0)

    from datetime import date, datetime, timezone  # noqa: E402
    from decimal import Decimal  # noqa: E402

    from product_intelligence.domain import ResearchRequest  # noqa: E402
    from product_intelligence.domain.enums import (  # noqa: E402
        ConfidenceLevel,
        EvidenceDecision,
        IdentityMatchType,
        ResearchRunState,
        VerificationStatus,
    )
    from product_intelligence.research import (  # noqa: E402
        ListingIdentityAssessment,
        ListingObservation,
        PriceAggregateBucket,
        PriceAggregationResult,
        encode_price_aggregation_result,
    )
    from product_intelligence.research.aggregation import (  # noqa: E402
        PriceAggregationExclusion,
        PriceAggregationExclusionReason,
        aggregate_listing_prices,
    )
    from product_intelligence.research.fx_codec import encode_fx_observation  # noqa: E402
    from product_intelligence.research.listings import ExtractionMethod  # noqa: E402
    from product_intelligence.research.matching import (  # noqa: E402
        EvidenceSource,
        IdentityRejectionReason,
    )
    from product_intelligence.research.normalization import (  # noqa: E402
        NormalizedAvailability,
        NormalizedCondition,
        NormalizedListingObservation,
    )
    from product_intelligence.providers.fx import FxRateObservation  # noqa: E402
    from product_intelligence.runs.models import (  # noqa: E402
        AiAssistedReviewCandidate,
        ComparableResearchExecution,
        ComparableResearchState,
        PriceIntelligenceSnapshot,
        ResearchFxSnapshot,
        ResearchRun,
        ResearchSupplementSnapshot,
    )
    from product_intelligence.research.commercial_supplement_codec import (  # noqa: E402
        ResearchSupplementResult,
        SupplementLookupStatus,
        SupplementPriceBasis,
        SupplementSourceObservation,
        VendorCommercialResult,
        encode_research_supplement_result,
    )
    from product_intelligence.research.comparable_result_codec import (  # noqa: E402
        encode_comparable_result,
    )
    from product_intelligence.research.comparable_research_results import (  # noqa: E402
        AuthorityAttemptResult,
        AuthorityAuditOutcomeKind,
        ComparisonState,
        DatasheetAttemptResult,
        DatasheetAuditOutcomeKind,
        EvidenceLayer,
        EvidenceSourceReference,
        ComparableCandidateResult,
        ComparableResearchResult,
        ComparableResultKind,
        FieldAssessmentResult,
        ProductEnrichmentAudit,
        ResolutionState,
        SourceAuthority,
    )

    def _base_run(mpn: str, description: str) -> ResearchRun:
        run = ResearchRun.objects.create_from_request(
            ResearchRequest(manufacturer_part_number=mpn, description=description)
        )
        run.transition_to(ResearchRunState.RUNNING)
        return run

    def _public_assessment(
        run: ResearchRun,
        *,
        source_url: str,
        price: Decimal,
        currency: str,
        availability: NormalizedAvailability = NormalizedAvailability.IN_STOCK,
        title: str = "Preview Product",
    ):
        mpn = run.manufacturer_part_number or "PREVIEW"
        obs = ListingObservation(
            source_url=source_url,
            extraction_method=ExtractionMethod.JSON_LD,
            product_title=title,
            manufacturer_part_number_text=mpn,
            sku_text=None,
            brand_text=None,
            price_text=str(price),
            currency_text=currency,
            availability_text="In Stock"
            if availability is NormalizedAvailability.IN_STOCK
            else "Out of Stock",
            condition_text="New",
            seller_text="Preview Store",
            offer_url_text=None,
            raw_reference=None,
        )
        norm = NormalizedListingObservation(
            observation=obs,
            price_amount=price,
            currency_code=currency,
            availability=availability,
            condition=NormalizedCondition.NEW,
            seller_name="Preview Store",
            normalization_issues=(),
        )
        assess = ListingIdentityAssessment(
            normalized_listing=norm,
            requested_part_number=mpn,
            candidate_part_number_raw=mpn,
            candidate_part_number_compared=mpn,
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.EXACT,
            decision=EvidenceDecision.ACCEPTED,
            rejection_reason=None,
        )
        return obs, assess

    def _persist_price(run: ResearchRun, result: PriceAggregationResult) -> None:
        PriceIntelligenceSnapshot.objects.create(
            run=run, schema_version=1, payload=encode_price_aggregation_result(result)
        )

    def _persist_fx(run: ResearchRun) -> None:
        payload = encode_fx_observation(
            provider_id="ECB",
            observation_date=date(2026, 10, 1),
            base_currency="EUR",
            rates=(
                FxRateObservation(currency_code="USD", rate=Decimal("1.09")),
                FxRateObservation(currency_code="EUR", rate=Decimal("1.0")),
            ),
            retrieved_at=datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc),
        )
        ResearchFxSnapshot.objects.create(run=run, schema_version=1, payload=payload)

    def _persist_vendor(run: ResearchRun) -> None:
        observations = (
            SupplementSourceObservation(
                source_name="Ingram",
                explicit_candidate_mpn=run.manufacturer_part_number,
                vendor_mpn_match_type="EXACT",
                price_amount=Decimal("2023.27"),
                currency_code="USD",
                availability="IN_STOCK",
                price_basis=SupplementPriceBasis.CUSTOMER_PRICE,
                quantity=1,
                note_kind=None,
                brand_new=True,
                brand_new_basis="VENDOR_API_POLICY",
            ),
            SupplementSourceObservation(
                source_name="CDW",
                explicit_candidate_mpn=run.manufacturer_part_number,
                vendor_mpn_match_type="EXACT",
                price_amount=Decimal("1999.99"),
                currency_code="USD",
                availability="OUT_OF_STOCK",
                price_basis=SupplementPriceBasis.CUSTOMER_PRICE,
                quantity=1,
                note_kind=None,
                brand_new=True,
                brand_new_basis="VENDOR_API_POLICY",
            ),
            SupplementSourceObservation(
                source_name="Synnex EU",
                explicit_candidate_mpn=run.manufacturer_part_number,
                vendor_mpn_match_type="EXACT",
                price_amount=Decimal("1705.35"),
                currency_code="EUR",
                availability="IN_STOCK",
                price_basis=SupplementPriceBasis.CUSTOMER_PRICE,
                quantity=1,
                note_kind="NO_RETURNS",
                brand_new=True,
                brand_new_basis="VENDOR_API_POLICY",
            ),
        )
        result = ResearchSupplementResult(
            vendor_commercial_result=VendorCommercialResult(
                lookup_status=SupplementLookupStatus.SUCCESS,
                retrieved_at=datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc),
                observations=observations,
                source_issues=(),
            ),
        )
        ResearchSupplementSnapshot.objects.create(
            run=run,
            schema_version=1,
            payload=encode_research_supplement_result(result),
        )

    urls: list[tuple[str, str]] = []

    # P1 — completed, multiple supplier quotes (3 vendor + 1 public + FX;
    # the ALLOWED server shows the vendor rows, the DENIED server does not)
    run = _base_run("MTFDKCC3T8TGP-1BK1DABYY", "480GB NVMe M.2 solid state drive")
    obs, assess = _public_assessment(
        run,
        source_url="https://www.example.com/ssd/mtfdkcc3t8tgp",
        price=Decimal("1500.00"),
        currency="EUR",
    )
    norm = assess.normalized_listing
    result = PriceAggregationResult(
        request=run.to_research_request(),
        assessments=(assess,),
        exclusions=(),
        buckets=(
            PriceAggregateBucket(
                currency_code="EUR",
                condition=NormalizedCondition.NEW,
                assessments=(assess,),
                count=1,
                low=Decimal("1500.00"),
                median=Decimal("1500.00"),
                high=Decimal("1500.00"),
                market_range_low=None,
                market_range_high=None,
                confidence=ConfidenceLevel.LOW,
            ),
        ),
        verification_status=VerificationStatus.VERIFIED,
    )
    _persist_price(run, result)
    _persist_fx(run)
    _persist_vendor(run)
    run.transition_to(ResearchRunState.COMPLETED)
    urls.append(("multiquote", f"/research/{run.id}"))

    # P2 — completed, source-published $0 quote (B1 note)
    run = _base_run("ZERO-OFFER-MPN", "zero price preview drive")
    obs, assess = _public_assessment(
        run,
        source_url="https://zero-offer.example/product/zero",
        price=Decimal("0"),
        currency="USD",
    )
    _persist_price(run, aggregate_listing_prices(run.to_research_request(), (assess,)))
    run.transition_to(ResearchRunState.COMPLETED)
    urls.append(("zeroquote", f"/research/{run.id}"))

    # P3 — completed, no usable price evidence (UNKNOWN)
    run = _base_run("NO-EVIDENCE-MPN", "no price evidence preview")
    mpn = run.manufacturer_part_number
    obs = ListingObservation(
        source_url="https://example.com/wrong-product",
        extraction_method=ExtractionMethod.JSON_LD,
        product_title="Different Product",
        manufacturer_part_number_text="WRONG-MPN",
        sku_text=None,
        brand_text=None,
        price_text="$50.00",
        currency_text="USD",
        availability_text="In Stock",
        condition_text="New",
        seller_text=None,
        offer_url_text=None,
        raw_reference=None,
    )
    norm = NormalizedListingObservation(
        observation=obs,
        price_amount=Decimal("50.00"),
        currency_code="USD",
        availability=NormalizedAvailability.IN_STOCK,
        condition=NormalizedCondition.NEW,
        seller_name=None,
        normalization_issues=(),
    )
    assess = ListingIdentityAssessment(
        normalized_listing=norm,
        requested_part_number=mpn,
        candidate_part_number_raw="WRONG-MPN",
        candidate_part_number_compared="WRONG-MPN",
        candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
        match_type=IdentityMatchType.UNKNOWN,
        decision=EvidenceDecision.REJECTED,
        rejection_reason=IdentityRejectionReason.MPN_MISMATCH,
    )
    result = PriceAggregationResult(
        request=run.to_research_request(),
        assessments=(assess,),
        exclusions=(
            PriceAggregationExclusion(
                assessment=assess,
                reason=PriceAggregationExclusionReason.IDENTITY_NOT_ACCEPTED,
            ),
        ),
        buckets=(),
        verification_status=VerificationStatus.UNKNOWN,
    )
    _persist_price(run, result)
    run.transition_to(ResearchRunState.COMPLETED)
    urls.append(("noevidence", f"/research/{run.id}"))

    # P4 — completed, AI-assisted review candidate (needs review)
    run = _base_run("AI-REVIEW-MPN", "AI review preview drive")
    obs = ListingObservation(
        source_url="https://example.com/product/ai-review",
        extraction_method=ExtractionMethod.JSON_LD,
        manufacturer_part_number_text="",
        sku_text=None,
        product_title="AI review candidate for AI-REVIEW-MPN",
        price_text="99.99",
        currency_text="USD",
        condition_text="new",
    )
    norm = NormalizedListingObservation(
        observation=obs,
        price_amount=Decimal("99.99"),
        currency_code="USD",
        condition=NormalizedCondition.NEW,
        availability=NormalizedAvailability.UNKNOWN,
        seller_name="Preview Seller",
        normalization_issues=(),
    )
    assess = ListingIdentityAssessment(
        normalized_listing=norm,
        requested_part_number="AI-REVIEW-MPN",
        candidate_part_number_raw="AI-REVIEW-MPN",
        candidate_part_number_compared="AI-REVIEW-MPN",
        candidate_evidence_source=EvidenceSource.TITLE_TEXT,
        match_type=IdentityMatchType.UNKNOWN,
        decision=EvidenceDecision.REJECTED,
        rejection_reason=IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE,
    )
    _persist_price(run, aggregate_listing_prices(run.to_research_request(), (assess,)))
    AiAssistedReviewCandidate.objects.create(
        run=run,
        assessment_index=0,
        source_url=obs.source_url,
        target_mpn=run.manufacturer_part_number,
        target_description=run.description,
        candidate_title=obs.product_title,
        candidate_mpn_field="",
        candidate_sku="",
        evidence_source="TITLE_TEXT",
        actual_provider="amax",
        actual_model="nemotron-3-super",
        prompt_version="v1.1",
    )
    run.transition_to(ResearchRunState.COMPLETED)
    urls.append(("aireview", f"/research/{run.id}"))

    # P5 — completed, comparable research result (FULL, one candidate)
    run = _base_run("COMP-TARGET-MPN", "comparable preview drive")
    _persist_price(
        run,
        PriceAggregationResult(
            request=run.to_research_request(),
            assessments=(),
            exclusions=(),
            buckets=(),
            verification_status=VerificationStatus.UNKNOWN,
        ),
    )
    run.transition_to(ResearchRunState.COMPLETED)
    from product_intelligence.research.enterprise_ssd import ENTERPRISE_SSD_SCHEMA  # noqa: E402

    keys = list(ENTERPRISE_SSD_SCHEMA.definitions.keys())

    def _evidence():
        return (
            EvidenceSourceReference(
                source_name="TestSource",
                source_url="https://example.com/support",
                evidence_layer=EvidenceLayer.SUPPORT_PAGE,
                source_authority=SourceAuthority.AUTHORITATIVE,
                retrieved_at="2024-01-01T00:00:00+00:00",
            ),
        )

    assessments = []
    for idx, key in enumerate(keys):
        if idx < 7:
            assessments.append(
                FieldAssessmentResult(
                    definition_key=key,
                    comparison_state=ComparisonState.SCORED,
                    target_resolution_state=ResolutionState.VERIFIED,
                    candidate_resolution_state=ResolutionState.VERIFIED,
                    field_similarity=Decimal("1"),
                    target_value="test",
                    candidate_value="test",
                    target_evidence=_evidence(),
                    candidate_evidence=_evidence(),
                )
            )
        else:
            assessments.append(
                FieldAssessmentResult(
                    definition_key=key,
                    comparison_state=ComparisonState.BOTH_NOT_VERIFIED,
                    target_resolution_state=ResolutionState.UNKNOWN,
                    candidate_resolution_state=ResolutionState.UNKNOWN,
                    field_similarity=None,
                    target_value=None,
                    candidate_value=None,
                    target_evidence=(),
                    candidate_evidence=(),
                )
            )
    total = len(keys)
    candidate = ComparableCandidateResult(
        candidate_mpn="CAND-001",
        candidate_normalized_mpn="CAND-001",
        scored_field_count=7,
        evidence_coverage=Decimal(7) / Decimal(total),
        observed_similarity=Decimal("1"),
        evidence_weighted_similarity=Decimal(7) / Decimal(total),
        field_assessments=tuple(assessments),
        enrichment_audit=ProductEnrichmentAudit(
            product_mpn="CAND-001",
            attempts=(DatasheetAttemptResult(outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE),),
        ),
    )
    full = ComparableResearchResult(
        kind=ComparableResultKind.FULL,
        target_mpn=run.manufacturer_part_number,
        target_manufacturer="Preview Corp",
        target_enrichment_audit=ProductEnrichmentAudit(
            product_mpn=run.manufacturer_part_number,
            attempts=(DatasheetAttemptResult(outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE),),
        ),
        authority_audit=(
            AuthorityAttemptResult(
                policy_id="preview-policy",
                outcome=AuthorityAuditOutcomeKind.MATCHED,
                requested_source_url="https://example.com/support",
                fetched_final_url="https://example.com/support",
                retrieved_at=datetime.now(timezone.utc).isoformat(),
                matching_mpn=run.manufacturer_part_number,
            ),
        ),
        candidates=(candidate,),
    )
    ComparableResearchExecution.objects.create(
        parent_run=run,
        state=ComparableResearchState.COMPLETED,
        active_slot=None,
        started_at=datetime(2026, 10, 2, 9, 0, 0, tzinfo=timezone.utc),
        finished_at=datetime(2026, 10, 2, 9, 2, 0, tzinfo=timezone.utc),
        result_payload=encode_comparable_result(full),
        result_schema_version=1,
    )
    urls.append(("comparable", f"/research/{run.id}"))

    # P6 — running
    run = _base_run("RUNNING-MPN", "running preview")
    urls.append(("running", f"/research/{run.id}"))

    # P7 — failed
    run = _base_run("FAILED-MPN", "failed preview")
    run.transition_to(ResearchRunState.FAILED)
    urls.append(("failed", f"/research/{run.id}"))

    # P8 — created
    run = ResearchRun.objects.create_from_request(
        ResearchRequest(manufacturer_part_number="CREATED-MPN", description="created preview")
    )
    urls.append(("created", f"/research/{run.id}"))

    # Manifest for the layout probe / screenshot capture (dev tooling reads
    # the CURRENT preview run addresses from here — no hardcoded UUIDs).
    urls_out.write_text(
        json.dumps(
            {
                "preview_db": str(preview_db),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "runs": {key: path for key, path in urls},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print(f"Preview database (new file; nothing deleted): {preview_db}")
    print(f"Preview URLs manifest: {urls_out}")
    labels = {
        "multiquote": "P1 multi-supplier (3 vendor + 1 public + FX)",
        "zeroquote": "P2 source-published $0 quote",
        "noevidence": "P3 no usable price evidence",
        "aireview": "P4 AI review candidate",
        "comparable": "P5 comparable result",
        "running": "P6 running state",
        "failed": "P7 failed state",
        "created": "P8 created state",
    }
    for key, url in urls:
        print(f"{labels[key]}: {url}")
    print()


def main() -> int:
    base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    preview_dir = os.environ.get(PREVIEW_DB_DIR_ENV)
    try:
        planned = plan_preview_database(
            preview_dir,
            base_dir=base_dir,
            now=datetime.now(timezone.utc),
            token=uuid.uuid4().hex[:12],
        )
    except PreviewConfigurationError as exc:
        # Fail closed BEFORE Django is imported or any database is touched.
        print(f"preview_fixtures: REFUSED — {exc}", file=sys.stderr)
        print(
            "preview_fixtures: no database file was created, deleted, "
            "migrated, or modified.",
            file=sys.stderr,
        )
        return 2

    # The preview database is the configured database: override any
    # pre-existing PI_SQLITE_PATH so a stale/hostile value can never steer
    # this script at another database. Set BEFORE Django reads settings.
    os.environ["PI_SQLITE_PATH"] = str(planned)
    build(planned, planned.parent / "preview_urls.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
