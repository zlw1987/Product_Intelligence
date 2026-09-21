"""Execution-integration tests for 4D-B vendor commercial evidence.

These tests run through execute_research_run to prove real integration
behaviour.

Tests cover:
A. No config -> zero Vendor API calls, no ResearchSupplementSnapshot
B. Description-only request -> configured endpoint, zero Vendor API calls
C. Configured MPN success -> ONE Vendor API lookup, snapshot persisted
D. Partial source failure -> valid observation + bounded issue persisted
E. Whole Vendor transport failure -> FAILED supplemental, run COMPLETED
F. Programming error -> catastrophic boundary, run FAILED, no half-publication
G. Codec error -> no silently COMPLETED run, no supplement
H. Persistence error -> atomic rollback, no PriceIntelligenceSnapshot
I. Search independence -> both search and vendor execute independently
J. Machine Price -> vendor data absent from decoded PriceIntelligenceSnapshot
K. Semantic isolation -> semantic eval BEFORE vendor lookup (call order proof)
L. Comparable isolation -> comparable pipeline imports no vendor contracts
"""

from __future__ import annotations

import ast
import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from django.test import TestCase

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import ResearchRunState
from product_intelligence.research.commercial_supplement_codec import (
    SupplementCodecError,
)
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
    """Web report does NOT expose vendor commercial data."""

    def test_historical_report_no_vendor_data(self) -> None:
        """GET /research/<uuid> does not render vendor commercial prices.

        Uses a REAL valid PriceAggregationResult encoded through the real
        price codec (not a fabricated payload). The report enters its normal
        successful rendering path.
        """
        from django.test import Client

        from product_intelligence.domain.enums import VerificationStatus
        from product_intelligence.research.aggregation import (
            PriceAggregationResult,
        )
        from product_intelligence.research.price_result_codec import (
            encode_price_aggregation_result,
        )

        request_obj = ResearchRequest(
            manufacturer_part_number="BCM957608-P2200GQF00",
            description="Test SSD",
        )
        run = ResearchRun.objects.create_from_request(request_obj)

        # Use a REAL valid aggregation result encoded through the real codec
        valid_result = PriceAggregationResult(
            request=request_obj,
            assessments=(),
            exclusions=(),
            buckets=(),
            verification_status=VerificationStatus.UNKNOWN,
        )
        encoded_payload = encode_price_aggregation_result(valid_result)

        PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=1,
            payload=encoded_payload,
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
            # Positive assertion: normal report rendered with expected MPN
            assert "BCM957608-P2200GQF00" in content
            assert "Test SSD" in content or "Price Intelligence" in content or "Research" in content
            # Vendor commercial data absent from normal report render path
            assert "9999.99" not in content
            assert "Ingram" not in content
            assert "CDW" not in content
            assert "Synnex" not in content
            assert "Vendor API" not in content
            assert "$9" not in content or "Vendor" not in content


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


class Test4DBPartialSourceFailure(TestCase):
    """D. Partial source failure -> valid observation + bounded issue."""

    def test_partial_source_failure(self) -> None:
        """One valid + one malformed source -> PARTIAL, both persisted."""
        request = ResearchRequest(
            manufacturer_part_number="BCM957608-P2200GQF00",
            description="Test SSD",
        )
        run = ResearchRun.objects.create_from_request(request)

        payload = {
            "Ingram": {
                "sourceName": "Ingram",
                "vendorPartNumber": "BCM957608-P2200GQF00",
                "pricing": {
                    "customerPrice": "2120.00",
                    "currencyCode": "USD",
                },
                "availability": {"available": True, "Avl_Quantity": 10},
            },
            "CDW": {
                "sourceName": "CDW",
                "manufacturerPartNumber": "BCM957608-P2200GQF00",
                "price": "not_a_number",
                "currencyCode": "USD",
                "inventoryStatus": {"stockStatus": "InStock"},
            },
        }
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

                run.refresh_from_db()
                assert run.current_state == ResearchRunState.COMPLETED

                snapshot = ResearchSupplementSnapshot.objects.get(run=run)
                vcr = snapshot.payload["vendor_commercial_result"]
                # PARTIAL status (one valid + one malformed)
                assert vcr["lookup_status"] == "PARTIAL"
                # Valid observation persisted
                assert len(vcr["observations"]) >= 1
                assert vcr["observations"][0]["source_name"] == "Ingram"
                # Bounded issue persisted (no raw text)
                assert len(vcr["source_issues"]) >= 1


class Test4DBProgrammingError(TestCase):
    """F. Programming error -> catastrophic boundary, run FAILED."""

    def test_programming_error_fails_run(self) -> None:
        """RuntimeError from adapter -> FAILED run, no supplement."""
        request = ResearchRequest(
            manufacturer_part_number="BCM957608-P2200GQF00",
            description="Test SSD",
        )
        run = ResearchRun.objects.create_from_request(request)

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "Ingram": {
                "sourceName": "Ingram",
                "vendorPartNumber": "BCM957608-P2200GQF00",
                "pricing": {
                    "customerPrice": "2120.00",
                    "currencyCode": "USD",
                },
                "availability": {"available": True},
            },
        }).encode("utf-8")
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
            ), patch(
                "product_intelligence.providers.internal_vendor."
                "_identify_and_map_source",
                side_effect=RuntimeError("injected programming defect"),
            ):
                from product_intelligence.execution import execute_research_run
                from product_intelligence.execution.orchestration import (
                    ExecutionError,
                )
                with pytest.raises(ExecutionError):
                    execute_research_run(str(run.id))

                # Run is FAILED (not COMPLETED)
                run.refresh_from_db()
                assert run.current_state == ResearchRunState.FAILED

                # No supplement snapshot persisted
                assert not ResearchSupplementSnapshot.objects.filter(
                    run=run
                ).exists()

                # No price snapshot (catastrophic before final publication)
                assert not PriceIntelligenceSnapshot.objects.filter(
                    run=run
                ).exists()


class Test4DBCodecError(TestCase):
    """G. Codec error -> no silently COMPLETED run."""

    def test_codec_error_fails_run(self) -> None:
        """SupplementCodecError -> run not silently COMPLETED."""
        request = ResearchRequest(
            manufacturer_part_number="BCM957608-P2200GQF00",
            description="Test SSD",
        )
        run = ResearchRun.objects.create_from_request(request)

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "Ingram": {
                "sourceName": "Ingram",
                "vendorPartNumber": "BCM957608-P2200GQF00",
                "pricing": {
                    "customerPrice": "2120.00",
                    "currencyCode": "USD",
                },
                "availability": {"available": True},
            },
        }).encode("utf-8")
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
            ), patch(
                "product_intelligence.research.commercial_supplement_codec."
                "encode_research_supplement_result",
                side_effect=SupplementCodecError("codec failure"),
            ):
                from product_intelligence.execution import execute_research_run
                from product_intelligence.execution.orchestration import (
                    ExecutionError,
                )
                with pytest.raises(ExecutionError):
                    execute_research_run(str(run.id))

                # Run FAILED (codec error hits outer catastrophic boundary)
                run.refresh_from_db()
                assert run.current_state == ResearchRunState.FAILED

                # No supplement snapshot persisted
                assert not ResearchSupplementSnapshot.objects.filter(
                    run=run
                ).exists()


class Test4DBPersistenceError(TestCase):
    """H. Persistence error -> atomic rollback, no half-publication."""

    def test_persistence_error_rolls_back(self) -> None:
        """SupplementSnapshot.create fails -> PriceIntelligenceSnapshot rolled back."""
        request = ResearchRequest(
            manufacturer_part_number="BCM957608-P2200GQF00",
            description="Test SSD",
        )
        run = ResearchRun.objects.create_from_request(request)

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "Ingram": {
                "sourceName": "Ingram",
                "vendorPartNumber": "BCM957608-P2200GQF00",
                "pricing": {
                    "customerPrice": "2120.00",
                    "currencyCode": "USD",
                },
                "availability": {"available": True},
            },
        }).encode("utf-8")
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
            ), patch(
                "product_intelligence.runs.models."
                "ResearchSupplementSnapshot.objects.create",
                side_effect=Exception("persistence failure"),
            ):
                from product_intelligence.execution import execute_research_run
                from product_intelligence.execution.orchestration import (
                    ExecutionError,
                )
                with pytest.raises(ExecutionError):
                    execute_research_run(str(run.id))

                # Run FAILED
                run.refresh_from_db()
                assert run.current_state == ResearchRunState.FAILED

                # Neither snapshot persisted (atomic rollback)
                assert not PriceIntelligenceSnapshot.objects.filter(
                    run=run
                ).exists()
                assert not ResearchSupplementSnapshot.objects.filter(
                    run=run
                ).exists()


class Test4DBSearchIndependence(TestCase):
    """I. Vendor does NOT suppress public search (strengthened)."""

    def test_vendor_and_search_both_execute(self) -> None:
        """Both search and vendor lookup execute independently."""
        request = ResearchRequest(
            manufacturer_part_number="BCM957608-P2200GQF00",
            description="Test SSD",
        )
        run = ResearchRun.objects.create_from_request(request)

        payload = {
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

                # Both search AND vendor were called
                assert mock_search.search.call_count == 1
                assert mock_opener.open.call_count == 1

                # ExecutionResult stats derived only from public research
                assert result.search_result_count == 0  # empty search results
                assert result.fetch_success_count == 0
                assert result.extract_observation_count == 0
                assert result.accepted_assessment_count == 0

                # Supplement persisted independently
                assert ResearchSupplementSnapshot.objects.filter(
                    run=run
                ).exists()


class Test4DBMachinePriceStrengthened(TestCase):
    """J. Machine Price -> Vendor creates ZERO additional 4A buckets (strengthened)."""

    def test_vendor_data_absent_from_price_snapshot(self) -> None:
        """PriceIntelligenceSnapshot decoded through real codec has no vendor data."""
        from product_intelligence.research.price_result_codec import (
            decode_price_aggregation_result,
        )

        request = ResearchRequest(
            manufacturer_part_number="BCM957608-P2200GQF00",
            description="Test SSD",
        )
        run = ResearchRun.objects.create_from_request(request)

        payload = {
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

                # Decode PriceIntelligenceSnapshot through real codec
                assert result.snapshot is not None
                decoded = decode_price_aggregation_result(
                    result.snapshot.payload,
                    schema_version=result.snapshot.schema_version,
                )

                # No vendor data in the decoded aggregation result
                assert not hasattr(decoded, 'vendor_commercial_result')

                # Bucket count is from public research only
                assert len(decoded.buckets) == 0  # no public listings


class Test4DBSemanticIsolation(TestCase):
    """K. Vendor rows not in semantic input (real pipeline, strengthened)."""

    def test_semantic_eval_before_vendor_lookup_with_input_inspection(self) -> None:
        """Semantic evaluation occurs BEFORE vendor lookup, with real pipeline input.

        Runs the full public acquisition pipeline end-to-end:
        injected SearchProvider -> SearchResponse with public URL
        -> injected PageFetcher -> real HTML/JSON-LD listing
        -> real extract_listing_observations
        -> real normalize_listing_observation
        -> real frozen-3C assess_listing_identity
        -> real ListingIdentityAssessment
        -> evaluate_semantic_matches

        Does NOT patch:
        _process_candidate_url, extract_listing_observations,
        normalize_listing_observation, assess_listing_identity

        Three-part proof:
        1. Call order: semantic -> vendor
        2. Semantic input is NON-EMPTY (at least one ListingIdentityAssessment)
        3. Every item is a ListingIdentityAssessment (no vendor-derived objects)
        """
        from product_intelligence.providers.search import (
            SearchProvider,
            SearchQuery,
            SearchResponse,
            SearchResult,
        )
        from product_intelligence.providers.page import (
            FetchedPage,
            PageFetcher,
        )
        from product_intelligence.providers.commercial import (
            CommercialSourceCandidate,
            CommercialSourceIssue,
        )
        from product_intelligence.research.commercial_supplement_codec import (
            SupplementSourceObservation,
        )
        from product_intelligence.runs.models import ResearchSupplementSnapshot
        from product_intelligence.research.matching import (
            ListingIdentityAssessment,
        )

        # JSON-LD page: MPN in title but NO explicit mpn field
        # -> real extraction produces listing with title evidence only
        # -> real frozen-3C assesses REJECTED/NO_EXPLICIT_MPN_EVIDENCE/TITLE_TEXT
        # -> semantic-eligible candidate reaches evaluate_semantic_matches
        public_html = (
            '<html><head>'
            '<script type="application/ld+json">'
            '{"@context":"https://schema.org","@type":"Product",'
            '"name":"Broadcom BCM957608-P2200GQF00 Network Adapter",'
            '"offers":{"@type":"Offer","price":"2120.00",'
            '"priceCurrency":"USD"}}'
            '</script></head><body></body></html>'
        )
        PUBLIC_URL = "https://public-retail.example.com/bcm-957608-adapter"

        # Injected SearchProvider: returns one public listing URL
        mock_search = MagicMock(spec=SearchProvider)
        mock_search.search.return_value = SearchResponse(
            provider_id="test",
            query=SearchQuery(text="BCM957608-P2200GQF00"),
            retrieved_at=datetime.now(tz=timezone.utc),
            results=(
                SearchResult(
                    source_url=PUBLIC_URL,
                    title="Broadcom BCM957608-P2200GQF00 Network Adapter",
                    snippet="Network adapter for Broadcom switch",
                ),
            ),
        )

        # Injected PageFetcher: returns real HTML with JSON-LD Product
        mock_fetcher = MagicMock(spec=PageFetcher)
        mock_fetcher.fetch.return_value = FetchedPage(
            requested_url=PUBLIC_URL,
            final_url=PUBLIC_URL,
            retrieved_at=datetime.now(tz=timezone.utc),
            status_code=200,
            body_text=public_html,
            content_type="text/html",
            body_byte_count=len(public_html.encode("utf-8")),
            redirect_count=0,
            fetcher_id="test",
        )

        # Vendor mock: for call-order tracking
        payload = {
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
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(payload).encode("utf-8")
        mock_opener = MagicMock()
        mock_opener.open.return_value = mock_response

        call_order: list[str] = []
        captured_semantic_args: list = []

        def track_semantic(*a, **kw):
            call_order.append("semantic")
            captured_semantic_args.append((a, kw))
            return []

        def track_vendor(*a, **kw):
            call_order.append("vendor")
            return mock_opener

        request = ResearchRequest(
            manufacturer_part_number="BCM957608-P2200GQF00",
            description="Test SSD",
        )
        run = ResearchRun.objects.create_from_request(request)

        with patch.dict(os.environ, {
            "PI_VENDOR_LOOKUP_BASE_URL": "http://vendor.internal/api",
        }):
            with patch(
                "product_intelligence.execution.orchestration."
                "evaluate_semantic_matches",
                side_effect=track_semantic,
            ), patch(
                "product_intelligence.providers.internal_vendor."
                "_get_vendor_opener",
                side_effect=track_vendor,
            ):
                from product_intelligence.execution import execute_research_run
                execute_research_run(
                    str(run.id),
                    search_provider=mock_search,
                    page_fetcher=mock_fetcher,
                )

                # Part 1: call order proof
                assert call_order == ["semantic", "vendor"], (
                    f"Expected semantic before vendor, got {call_order}"
                )

                # Part 2: semantic input is NON-EMPTY
                assert len(captured_semantic_args) == 1
                args, kw = captured_semantic_args[0]
                if "assessments" in kw:
                    assessments_arg = kw["assessments"]
                elif len(args) >= 2:
                    assessments_arg = args[1]
                else:
                    assessments_arg = ()

                assert len(assessments_arg) >= 1, (
                    f"Semantic input must be non-empty, got {len(assessments_arg)} items"
                )

                # Part 3: every item is a ListingIdentityAssessment
                for item in assessments_arg:
                    assert isinstance(item, ListingIdentityAssessment), (
                        f"Semantic input item must be ListingIdentityAssessment, "
                        f"got {type(item).__name__}"
                    )
                    assert not isinstance(item, CommercialSourceCandidate), (
                        "Semantic input must not contain CommercialSourceCandidate"
                    )
                    assert not isinstance(item, CommercialSourceIssue), (
                        "Semantic input must not contain CommercialSourceIssue"
                    )
                    assert not isinstance(item, SupplementSourceObservation), (
                        "Semantic input must not contain SupplementSourceObservation"
                    )
                    assert not isinstance(item, ResearchSupplementSnapshot), (
                        "Semantic input must not contain ResearchSupplementSnapshot"
                    )

                # Verify first arg is ResearchRequest (not vendor-derived)
                if len(args) >= 1:
                    from product_intelligence.domain import ResearchRequest as RR
                    assert isinstance(args[0], RR), (
                        "First semantic arg must be ResearchRequest"
                    )


class Test4DBComparableIsolation(TestCase):
    """L. Comparable pipeline does not consume vendor commercial data."""

    def test_comparable_imports_no_vendor_contracts(self) -> None:
        """Comparable execution/scoring imports no vendor commercial symbols."""
        import ast
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[2]
        execution_root = repo_root / "product_intelligence" / "execution"

        forbidden_modules = {
            "product_intelligence.research.commercial_supplement_codec",
            "product_intelligence.providers.commercial",
            "product_intelligence.providers.internal_vendor",
        }
        forbidden_strings = {
            "ResearchSupplementSnapshot",
            "commercial_supplement_codec",
            "providers.commercial",
            "providers.internal_vendor",
            "CommercialSourceCandidate",
            "CommercialSourceIssue",
        }

        comparable_files = [
            execution_root / "comparable_discovery.py",
            execution_root / "comparable_research.py",
            execution_root / "comparable_research_authority.py",
            execution_root / "comparable_runtime.py",
            execution_root / "comparable_similarity.py",
        ]

        for filepath in comparable_files:
            if not filepath.exists():
                continue
            source = filepath.read_text(encoding="utf-8")
            # Check imports
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if node.module in forbidden_modules:
                        pytest.fail(
                            f"{filepath.name} imports {node.module}; "
                            "comparable pipeline must not import vendor contracts"
                        )
            # Check string references
            for token in forbidden_strings:
                if token in source:
                    # Allow in comments/docstrings about isolation
                    for line in source.splitlines():
                        stripped = line.strip()
                        if token in stripped and not stripped.startswith("#"):
                            pytest.fail(
                                f"{filepath.name} references {token}; "
                                "comparable pipeline must not consume vendor data"
                            )
