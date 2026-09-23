"""Persistence tests for ResearchMicronAliasSnapshot (PRODUCT-INTEL.4D-D).

The model is storage, not interpretation: schema_version + opaque
codec-owned JSON payload + created_at, OneToOne to ResearchRun.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

from django.db import IntegrityError, transaction
from django.test import TestCase

from product_intelligence.domain import ResearchRequest
from product_intelligence.providers.page import FetchedPage, PageFetcher
from product_intelligence.research.micron_alias_codec import (
    decode_micron_alias_snapshot,
    encode_micron_alias_snapshot,
)
from product_intelligence.research.micron_packaging_alias import (
    MICRON_7500_REQUESTED_CATALOG_URL,
    MicronAliasEligibilityStatus,
)
from product_intelligence.runs.models import (
    ResearchMicronAliasSnapshot,
    ResearchRun,
)

FIXTURE_SHA256 = (
    "160d4fe97a5df5249e8f6404f6b005c0515fab4def1b4668fdaf87c727600743"
)


def _make_run(mpn: str = "MTFDKCC3T8TGP-1BK1DABYYR") -> ResearchRun:
    return ResearchRun.objects.create_from_request(
        ResearchRequest(
            manufacturer_part_number=mpn,
            description="Micron 7500 3.84TB datacenter SSD",
        )
    )


def _established_result_payload() -> dict:
    """Encode one real ESTABLISHED acquisition (fake fetch, real fixture)."""
    from pathlib import Path

    from product_intelligence.execution.micron_alias_authority import (
        acquire_micron_alias_eligibility,
    )

    catalog_body = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "pages"
        / "micron_7500_part_catalog.json"
    ).read_text(encoding="utf-8")
    fetcher = MagicMock(spec=PageFetcher)
    fetcher.fetch.return_value = FetchedPage(
        requested_url=MICRON_7500_REQUESTED_CATALOG_URL,
        final_url=MICRON_7500_REQUESTED_CATALOG_URL,
        retrieved_at=datetime(2026, 9, 22, 23, 20, 25, tzinfo=timezone.utc),
        status_code=200,
        body_text=catalog_body,
        content_type="application/json;charset=utf-8",
        body_byte_count=len(catalog_body.encode("utf-8")),
        redirect_count=0,
        fetcher_id="test",
    )
    result = acquire_micron_alias_eligibility(
        request=_make_run_request(),
        page_fetcher=fetcher,
    )
    assert result.status is MicronAliasEligibilityStatus.ESTABLISHED
    return encode_micron_alias_snapshot(result)


def _make_run_request() -> ResearchRequest:
    return ResearchRequest(
        manufacturer_part_number="MTFDKCC3T8TGP-1BK1DABYYR",
        description="Micron 7500 3.84TB datacenter SSD",
    )


class TestResearchMicronAliasSnapshotModel(TestCase):
    def test_one_to_one_primary_key_on_run(self) -> None:
        run = _make_run()
        payload = _established_result_payload()
        snapshot = ResearchMicronAliasSnapshot.objects.create(
            run=run, schema_version=1, payload=payload
        )
        self.assertEqual(snapshot.pk, run.pk)
        self.assertEqual(snapshot.run_id, run.id)

    def test_related_name_reverse_accessor(self) -> None:
        run = _make_run()
        payload = _established_result_payload()
        ResearchMicronAliasSnapshot.objects.create(
            run=run, schema_version=1, payload=payload
        )
        self.assertEqual(
            run.research_micron_alias_snapshot.schema_version, 1
        )

    def test_schema_version_and_payload_round_trip(self) -> None:
        run = _make_run()
        payload = _established_result_payload()
        ResearchMicronAliasSnapshot.objects.create(
            run=run, schema_version=1, payload=payload
        )
        snapshot = ResearchMicronAliasSnapshot.objects.get(run=run)
        self.assertEqual(snapshot.schema_version, 1)
        self.assertEqual(snapshot.payload, payload)
        decoded = decode_micron_alias_snapshot(
            snapshot.payload, schema_version=snapshot.schema_version
        )
        self.assertIs(decoded.status, MicronAliasEligibilityStatus.ESTABLISHED)
        self.assertEqual(decoded.matched_base_mpn, "MTFDKCC3T8TGP-1BK1DABYY")

    def test_created_at_auto_populated_utc(self) -> None:
        run = _make_run()
        ResearchMicronAliasSnapshot.objects.create(
            run=run, schema_version=1, payload={"schema_version": 1}
        )
        snapshot = ResearchMicronAliasSnapshot.objects.get(run=run)
        self.assertIsNotNone(snapshot.created_at)
        self.assertIsNotNone(snapshot.created_at.tzinfo)

    def test_schema_constraint_rejects_version_below_one(self) -> None:
        run = _make_run()
        with self.assertRaises(IntegrityError), transaction.atomic():
            ResearchMicronAliasSnapshot.objects.create(
                run=run, schema_version=0, payload={}
            )

    def test_model_stores_opaque_payload_no_catalog_body_required(self) -> None:
        # The model is storage: it does not interpret payload keys.
        run = _make_run()
        ResearchMicronAliasSnapshot.objects.create(
            run=run, schema_version=1, payload={"anything": "allowed"}
        )
        snapshot = ResearchMicronAliasSnapshot.objects.get(run=run)
        self.assertEqual(snapshot.payload, {"anything": "allowed"})

    def test_encoded_payload_carrying_sha256_not_catalog_body(self) -> None:
        payload = _established_result_payload()
        # Bounded provenance: the body is referenced by SHA-256 only.
        self.assertEqual(payload["body_sha256"], FIXTURE_SHA256)
        self.assertNotIn("details", payload)
        self.assertNotIn("body_text", payload)
        self.assertNotIn("catalog", payload)

    def test_duplicate_snapshot_for_same_run_prohibited(self) -> None:
        run = _make_run()
        ResearchMicronAliasSnapshot.objects.create(
            run=run, schema_version=1, payload={"first": True}
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            ResearchMicronAliasSnapshot.objects.create(
                run=run, schema_version=1, payload={"second": True}
            )
        self.assertEqual(
            ResearchMicronAliasSnapshot.objects.filter(run=run).count(), 1
        )

    def test_cascade_delete_with_run(self) -> None:
        run = _make_run()
        run_id = run.id
        ResearchMicronAliasSnapshot.objects.create(
            run=run, schema_version=1, payload={"first": True}
        )
        self.assertTrue(
            ResearchMicronAliasSnapshot.objects.filter(run_id=run_id).exists()
        )
        run.delete()
        self.assertFalse(
            ResearchMicronAliasSnapshot.objects.filter(run_id=run_id).exists()
        )
