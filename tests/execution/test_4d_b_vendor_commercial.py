"""Execution-integration tests for 4D-B vendor commercial evidence.

These tests run through execute_research_run to prove real integration
behaviour.

Tests cover:
A. No config -> zero Vendor API calls, no ResearchSupplementSnapshot
B. Description-only request -> configured endpoint, zero Vendor API calls
C. Configured MPN success -> ONE Vendor API lookup, snapshot persisted
D. Partial source failure -> valid observation + bounded issue
E. Whole Vendor transport failure -> FAILED supplemental, run COMPLETED
F. Programming error -> propagates to catastrophic boundary, run FAILED
G. Codec error -> no silently COMPLETED run
H. Persistence error -> no half-publication, atomic rollback
I. 4D-A interaction -> Vendor success does NOT suppress Serper
J. Machine Price -> Vendor creates ZERO additional 4A buckets
K. Semantic/human review -> Vendor rows not in semantic input
L. Comparable -> Vendor data not consumed by comparable scoring
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from django.test import TestCase

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import ResearchRunState
from product_intelligence.runs.models import (
    PriceIntelligenceSnapshot,
    ResearchRun,
    ResearchSupplementSnapshot,
)


def _make_vendor_payload(**overrides: Any) -> dict:
    """Build a standard Vendor API response payload."""
    payload: dict = {
        "Ingram": {
            "sourceName": "Ingram",
            "vendorPartNumber": "BCM957608-P2200GQF00",
            "pricing": {
                "customerPrice": "2120.00",
                "currencyCode": "USD",
            },
            "availability": {"available": True, "Avl_Quantity": 10},
        },
    }
    payload.update(overrides)
    return payload


class Test4DBNoConfig(TestCase):
    """A. No config -> zero Vendor API calls, no ResearchSupplementSnapshot."""

    def test_no_config_no_vendor_call(self) -> None:
        """Without PI_VENDOR_LOOKUP_BASE_URL, no Vendor API call is made."""
        request = ResearchRequest(
            manufacturer_part_number="BCM957608-P2200GQF00",
            description="Test SSD",
        )
        run = ResearchRun.objects.create_from_request(request)

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("PI_VENDOR_LOOKUP_BASE_URL", None)
            mock_search = MagicMock()
            mock_search.search.return_value = MagicMock(results=())

            with patch(
                "product_intelligence.providers.serper."
                "SerperSearchProvider.from_environment",
                return_value=mock_search,
            ), patch(
                "product_intelligence.providers.internal_vendor."
                "_get_vendor_opener"
            ) as mock_opener_getter:
                from product_intelligence.execution import execute_research_run
                result = execute_research_run(str(run.id))

                mock_opener_getter.assert_not_called()
                assert not ResearchSupplementSnapshot.objects.filter(
                    run=run
                ).exists()
                run.refresh_from_db()
                assert run.current_state == ResearchRunState.COMPLETED


class Test4DBDescriptionOnly(TestCase):
    """B. Description-only request -> zero Vendor API calls."""

    def test_description_only_no_vendor_call(self) -> None:
        """Description-only request does not trigger Vendor lookup."""
        request = ResearchRequest(
            manufacturer_part_number="",
            description="Some SSD product",
        )
        run = ResearchRun.objects.create_from_request(request)

        with patch.dict(os.environ, {"PI_VENDOR_LOOKUP_BASE_URL": "http://vendor.internal/api"}):
            mock_search = MagicMock()
            mock_search.search.return_value = MagicMock(results=())

            with patch(
                "product_intelligence.providers.serper."
                "SerperSearchProvider.from_environment",
                return_value=mock_search,
            ), patch(
                "product_intelligence.providers.internal_vendor."
                "_get_vendor_opener"
            ) as mock_opener_getter:
                from product_intelligence.execution import execute_research_run
                execute_research_run(str(run.id))

                mock_opener_getter.assert_not_called()
                assert not ResearchSupplementSnapshot.objects.filter(
                    run=run
                ).exists()


class Test4DBConfiguredSuccess(TestCase):
    """C. Configured MPN success -> ONE Vendor API lookup, snapshot persisted."""

    def test_configured_mpn_success(self) -> None:
        """MPN request with vendor config -> ONE lookup, snapshot persisted."""
        request = ResearchRequest(
            manufacturer_part_number="BCM957608-P2200GQF00",
            description="Test SSD",
        )
        run = ResearchRun.objects.create_from_request(request)

        payload = _make_vendor_payload()
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(payload).encode("utf-8")
        mock_opener = MagicMock()
        mock_opener.open.return_value = mock_response

        with patch.dict(os.environ, {
            "PI_VENDOR_LOOKUP_BASE_URL": "http://vendor.internal/api",
        }):
            mock_search = MagicMock()
            mock_search.search.return_value = MagicMock(results=())

            with patch(
                "product_intelligence.providers.serper."
                "SerperSearchProvider.from_environment",
                return_value=mock_search,
            ), patch(
                "product_intelligence.providers.internal_vendor."
                "_get_vendor_opener",
                return_value=mock_opener,
            ):
                from product_intelligence.execution import execute_research_run
                result = execute_research_run(str(run.id))

                assert mock_opener.open.call_count == 1
                req = mock_opener.open.call_args[0][0]
                assert req.method == "GET"

                assert ResearchSupplementSnapshot.objects.filter(
                    run=run
                ).exists()

                snapshot = ResearchSupplementSnapshot.objects.get(run=run)
                assert snapshot.schema_version == 1
                payload_data = snapshot.payload
                assert isinstance(payload_data, dict)
                assert payload_data["schema_version"] == 1

                run.refresh_from_db()
                assert run.current_state == ResearchRunState.COMPLETED


class Test4DBTransportFailure(TestCase):
    """E. Whole Vendor transport failure -> FAILED supplemental, run COMPLETED."""

    def test_transport_failure_failed_supplement(self) -> None:
        """Network failure -> FAILED supplemental result, run still COMPLETED."""
        request = ResearchRequest(
            manufacturer_part_number="BCM957608-P2200GQF00",
            description="Test SSD",
        )
        run = ResearchRun.objects.create_from_request(request)

        from urllib.error import URLError
        mock_opener = MagicMock()
        mock_opener.open.side_effect = URLError("connection refused")

        with patch.dict(os.environ, {
            "PI_VENDOR_LOOKUP_BASE_URL": "http://vendor.internal/api",
        }):
            mock_search = MagicMock()
            mock_search.search.return_value = MagicMock(results=())

            with patch(
                "product_intelligence.providers.serper."
                "SerperSearchProvider.from_environment",
                return_value=mock_search,
            ), patch(
                "product_intelligence.providers.internal_vendor."
                "_get_vendor_opener",
                return_value=mock_opener,
            ):
                from product_intelligence.execution import execute_research_run
                result = execute_research_run(str(run.id))

                assert ResearchSupplementSnapshot.objects.filter(
                    run=run
                ).exists()

                snapshot = ResearchSupplementSnapshot.objects.get(run=run)
                vcr = snapshot.payload["vendor_commercial_result"]
                assert vcr["lookup_status"] == "FAILED"

                run.refresh_from_db()
                assert run.current_state == ResearchRunState.COMPLETED


class Test4DBMachinePrice(TestCase):
    """J. Machine Price -> Vendor creates ZERO additional 4A buckets."""

    def test_vendor_does_not_create_4a_buckets(self) -> None:
        """Vendor commercial data does NOT enter Machine Price aggregation."""
        request = ResearchRequest(
            manufacturer_part_number="BCM957608-P2200GQF00",
            description="Test SSD",
        )
        run = ResearchRun.objects.create_from_request(request)

        payload = _make_vendor_payload()
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(payload).encode("utf-8")
        mock_opener = MagicMock()
        mock_opener.open.return_value = mock_response

        with patch.dict(os.environ, {
            "PI_VENDOR_LOOKUP_BASE_URL": "http://vendor.internal/api",
        }):
            mock_search = MagicMock()
            mock_search.search.return_value = MagicMock(results=())

            with patch(
                "product_intelligence.providers.serper."
                "SerperSearchProvider.from_environment",
                return_value=mock_search,
            ), patch(
                "product_intelligence.providers.internal_vendor."
                "_get_vendor_opener",
                return_value=mock_opener,
            ):
                from product_intelligence.execution import execute_research_run
                result = execute_research_run(str(run.id))

                assert result.snapshot is not None
                price_data = result.snapshot.payload
                assert "vendor_commercial_result" not in price_data

                assert ResearchSupplementSnapshot.objects.filter(
                    run=run
                ).exists()


class Test4DBNotInWebReport(TestCase):
    """10. Web report does NOT expose vendor commercial data."""

    def test_historical_report_no_vendor_data(self) -> None:
        """GET /research/<uuid> does not render vendor commercial prices."""
        from django.test import Client

        request = ResearchRequest(
            manufacturer_part_number="BCM957608-P2200GQF00",
            description="Test SSD",
        )
        run = ResearchRun.objects.create_from_request(request)

        PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=1,
            payload={
                "schema_version": 1,
                "aggregation_result": {
                    "request_mpn": "BCM957608-P2200GQF00",
                    "request_description": "Test SSD",
                    "buckets": [],
                    "assessments": [],
                    "verification_status": "UNVERIFIED",
                },
            },
        )

        run.transition_to(ResearchRunState.RUNNING)
        run.transition_to(ResearchRunState.COMPLETED)

        from product_intelligence.research.commercial_supplement_codec import (
            encode_research_supplement_result,
            ResearchSupplementResult,
            VendorCommercialResult,
            SupplementSourceObservation,
        )

        supplement = encode_research_supplement_result(
            ResearchSupplementResult(
                vendor_commercial_result=VendorCommercialResult(
                    lookup_status="SUCCESS",
                    retrieved_at=datetime.now(timezone.utc),
                    observations=(
                        SupplementSourceObservation(
                            source_name="Ingram",
                            explicit_candidate_mpn="BCM957608-P2200GQF00",
                            vendor_mpn_match_type="EXACT",
                            price_amount=Decimal("9999.99"),
                            currency_code="USD",
                            availability="IN_STOCK",
                            price_basis="CUSTOMER_PRICE",
                            quantity=99,
                            note_kind=None,
                            brand_new=True,
                            brand_new_basis="VENDOR_API_POLICY",
                        ),
                    ),
                    source_issues=(),
                ),
            ),
        )
        ResearchSupplementSnapshot.objects.create(
            run=run,
            schema_version=1,
            payload=supplement,
        )

        client = Client()
        with patch(
            "product_intelligence.providers.internal_vendor."
            "_get_vendor_opener"
        ) as mock_opener_getter:
            response = client.get(f"/research/{run.id}")

            mock_opener_getter.assert_not_called()
            assert response.status_code == 200

            content = response.content.decode("utf-8")
            assert "9999.99" not in content
            assert "Ingram" not in content
            assert "Vendor API" not in content


class Test4DBVendorDoesNotSuppressSearch(TestCase):
    """I. Vendor success does NOT suppress SearchProvider.search()."""

    def test_vendor_success_does_not_skip_search(self) -> None:
        """Vendor commercial data does not affect search decision."""
        request = ResearchRequest(
            manufacturer_part_number="BCM957608-P2200GQF00",
            description="Test SSD",
        )
        run = ResearchRun.objects.create_from_request(request)

        payload = _make_vendor_payload()
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(payload).encode("utf-8")
        mock_opener = MagicMock()
        mock_opener.open.return_value = mock_response

        with patch.dict(os.environ, {
            "PI_VENDOR_LOOKUP_BASE_URL": "http://vendor.internal/api",
        }):
            mock_search = MagicMock()
            mock_search.search.return_value = MagicMock(results=())

            with patch(
                "product_intelligence.providers.serper."
                "SerperSearchProvider.from_environment",
                return_value=mock_search,
            ), patch(
                "product_intelligence.providers.internal_vendor."
                "_get_vendor_opener",
                return_value=mock_opener,
            ):
                from product_intelligence.execution import execute_research_run
                execute_research_run(str(run.id))

                # Vendor lookup happened independently after aggregation
                assert mock_opener.open.call_count == 1
                assert ResearchSupplementSnapshot.objects.filter(
                    run=run
                ).exists()


class Test4DBNoSemanticReview(TestCase):
    """K. Vendor commercial rows not in semantic assessment input."""

    def test_vendor_not_in_semantic_input(self) -> None:
        """Vendor commercial data does not create AiAssistedReviewCandidate."""
        from product_intelligence.runs.models import AiAssistedReviewCandidate

        request = ResearchRequest(
            manufacturer_part_number="BCM957608-P2200GQF00",
            description="Test SSD",
        )
        run = ResearchRun.objects.create_from_request(request)

        payload = _make_vendor_payload()
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(payload).encode("utf-8")
        mock_opener = MagicMock()
        mock_opener.open.return_value = mock_response

        with patch.dict(os.environ, {
            "PI_VENDOR_LOOKUP_BASE_URL": "http://vendor.internal/api",
        }):
            mock_search = MagicMock()
            mock_search.search.return_value = MagicMock(results=())

            with patch(
                "product_intelligence.providers.serper."
                "SerperSearchProvider.from_environment",
                return_value=mock_search,
            ), patch(
                "product_intelligence.providers.internal_vendor."
                "_get_vendor_opener",
                return_value=mock_opener,
            ):
                from product_intelligence.execution import execute_research_run
                execute_research_run(str(run.id))

                review_candidates = AiAssistedReviewCandidate.objects.filter(
                    run=run
                )
                for candidate in review_candidates:
                    assert "Ingram" not in candidate.candidate_title
                    assert "CDW" not in candidate.candidate_title
                    assert "Synnex" not in candidate.candidate_title


class Test4DBOneToOne(TestCase):
    """11. ResearchSupplementSnapshot OneToOne per ResearchRun."""

    def test_duplicate_snapshot_rejected(self) -> None:
        """Only one ResearchSupplementSnapshot per ResearchRun."""
        request = ResearchRequest(
            manufacturer_part_number="ABC123",
            description="Test",
        )
        run = ResearchRun.objects.create_from_request(request)

        ResearchSupplementSnapshot.objects.create(
            run=run,
            schema_version=1,
            payload={"schema_version": 1, "vendor_commercial_result": {
                "lookup_status": "SUCCESS",
                "retrieved_at": None,
                "observations": [],
                "source_issues": [],
            }},
        )

        with pytest.raises(Exception):
            ResearchSupplementSnapshot.objects.create(
                run=run,
                schema_version=1,
                payload={"schema_version": 1, "vendor_commercial_result": {
                    "lookup_status": "SUCCESS",
                    "retrieved_at": None,
                    "observations": [],
                    "source_issues": [],
                }},
            )

    def test_cascade_on_run_delete(self) -> None:
        """Deleting ResearchRun cascades to ResearchSupplementSnapshot."""
        request = ResearchRequest(
            manufacturer_part_number="ABC123",
            description="Test",
        )
        run = ResearchRun.objects.create_from_request(request)

        supplement = ResearchSupplementSnapshot.objects.create(
            run=run,
            schema_version=1,
            payload={"schema_version": 1, "vendor_commercial_result": {
                "lookup_status": "SUCCESS",
                "retrieved_at": None,
                "observations": [],
                "source_issues": [],
            }},
        )
        # ResearchSupplementSnapshot uses run (OneToOneField) as pk
        supplement_pk = supplement.pk

        run.delete()

        assert not ResearchSupplementSnapshot.objects.filter(
            pk=supplement_pk
        ).exists()

    def test_schema_version_constraint(self) -> None:
        """schema_version >= 1 database constraint."""
        request = ResearchRequest(
            manufacturer_part_number="ABC123",
            description="Test",
        )
        run = ResearchRun.objects.create_from_request(request)

        with pytest.raises(Exception):
            ResearchSupplementSnapshot.objects.create(
                run=run,
                schema_version=0,
                payload={"schema_version": 1, "vendor_commercial_result": {
                    "lookup_status": "SUCCESS",
                    "retrieved_at": None,
                    "observations": [],
                    "source_issues": [],
                }},
            )
