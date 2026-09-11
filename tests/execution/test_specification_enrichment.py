"""Tests for specification enrichment execution (PRODUCT-INTEL.6D — execution layer).

Tests the full pipeline: document acquisition, table parsing, extraction,
normalization, resolution, result composition, and result self-audit.
"""

import pytest
import io
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from product_intelligence.domain.enums import IdentityMatchType
from product_intelligence.domain.models import ProductIdentity
from product_intelligence.research.enterprise_ssd import (
    ENTERPRISE_SSD_SCHEMA,
    normalize_enterprise_ssd_observation,
)
from product_intelligence.research.specifications import (
    ResolutionState,
    SourceAuthority,
    SpecificationObservation,
    NormalizedSpecificationObservation,
    SpecificationValue,
    ProductSpecificationSet,
    resolve_specification,
)
from product_intelligence.execution.specification_enrichment import (
    DatasheetSource,
    DatasheetSourceOutcome,
    DatasheetOutcomeState,
    SpecificationEnrichmentResult,
    enrich_enterprise_ssd_specifications,
    _enrich_from_datasheet_sources_internal,
    compose_6c_6d_specifications,
)
from product_intelligence.providers.document import (
    DocumentFetchError,
    DocumentFetchRequest,
    UnsafeDocumentTargetError,
    FetchedDocument,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

RETRIEVED_AT = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
SOURCE_URL = "https://www.seagate.com/datasheet.pdf"


def _make_identity(mpn: str) -> ProductIdentity:
    return ProductIdentity(
        manufacturer=None,
        manufacturer_part_number=mpn,
        match_type=IdentityMatchType.EXACT,
    )


REAL_PDF_PATH = "tests/fixtures/specifications/real_seagate_nytro_5550_5350_datasheet.pdf"


class _FilePdfFetcher:
    """Fetcher that reads from a local file instead of HTTP."""

    def __init__(self, pdf_path: str, final_url: str = SOURCE_URL):
        self._pdf_path = pdf_path
        self._final_url = final_url

    def fetch(self, request: DocumentFetchRequest) -> FetchedDocument:
        with open(self._pdf_path, "rb") as f:
            data = f.read()
        return FetchedDocument(
            requested_url=request.url,
            final_url=self._final_url,
            retrieved_at=RETRIEVED_AT,
            content_type="application/pdf",
            body_bytes=data,
            body_byte_count=len(data),
            redirect_count=0,
            fetcher_id="file-pdf",
        )


class _ErrorPdfFetcher:
    def __init__(self, error_type: type):
        self._error_type = error_type

    def fetch(self, request: DocumentFetchRequest) -> FetchedDocument:
        raise self._error_type("simulated fetch failure")


class _EmptyPdfFetcher:
    def fetch(self, request: DocumentFetchRequest) -> FetchedDocument:
        return FetchedDocument(
            requested_url=request.url,
            final_url=request.url,
            retrieved_at=RETRIEVED_AT,
            content_type="application/pdf",
            body_bytes=b"%PDF-1.4 minimal\n",
            body_byte_count=17,
            redirect_count=0,
            fetcher_id="empty-pdf",
        )


# ---------------------------------------------------------------------------
# DatasheetSource validation
# ---------------------------------------------------------------------------

class TestDatasheetSource:
    def test_valid_source(self) -> None:
        identity = _make_identity("XP123")
        source = DatasheetSource(
            product_identity=identity,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        assert source.source_url == SOURCE_URL

    def test_unestablished_identity_refused(self) -> None:
        identity = ProductIdentity(
            manufacturer_part_number="XP123",
            match_type=IdentityMatchType.UNKNOWN,
        )
        with pytest.raises(ValueError, match="requires an established"):
            DatasheetSource(
                product_identity=identity,
                source_name="Test",
                source_url=SOURCE_URL,
                source_authority=SourceAuthority.AUTHORITATIVE,
            )

    def test_invalid_url_refused(self) -> None:
        identity = _make_identity("XP123")
        with pytest.raises(ValueError, match="must be an absolute"):
            DatasheetSource(
                product_identity=identity,
                source_name="Test",
                source_url="file:///local.pdf",
                source_authority=SourceAuthority.AUTHORITATIVE,
            )

    def test_credential_url_refused(self) -> None:
        identity = _make_identity("XP123")
        with pytest.raises(ValueError, match="must not embed credentials"):
            DatasheetSource(
                product_identity=identity,
                source_name="Test",
                source_url="https://user:pass@example.com/doc.pdf",
                source_authority=SourceAuthority.AUTHORITATIVE,
            )


# ---------------------------------------------------------------------------
# AUTHORITATIVE-only enforcement
# ---------------------------------------------------------------------------

class TestDatasheetSourceAuthorityEnforcement:
    """DatasheetSource must reject SECONDARY authority."""

    def test_authoritative_accepted(self) -> None:
        """AUTHORITATIVE is the only accepted authority."""
        source = DatasheetSource(
            product_identity=_make_identity("XP123"),
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        assert source.source_authority is SourceAuthority.AUTHORITATIVE

    def test_secondary_rejected(self) -> None:
        """SECONDARY must be rejected before any fetch."""
        with pytest.raises(ValueError, match="AUTHORITATIVE"):
            DatasheetSource(
                product_identity=_make_identity("XP123"),
                source_name="Retailer Datasheet",
                source_url=SOURCE_URL,
                source_authority=SourceAuthority.SECONDARY,
            )


# ---------------------------------------------------------------------------
# DatasheetSourceOutcome validation
# ---------------------------------------------------------------------------

class TestDatasheetSourceOutcome:
    def _make_source(self) -> DatasheetSource:
        return DatasheetSource(
            product_identity=_make_identity("XP123"),
            source_name="Test",
            source_url=SOURCE_URL,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )

    def test_enriched_outcome(self) -> None:
        outcome = DatasheetSourceOutcome(
            source=self._make_source(),
            final_url=SOURCE_URL,
            retrieved_at=RETRIEVED_AT,
            outcome_state=DatasheetOutcomeState.ENRICHED,
            observation_count=6,
        )
        assert outcome.observation_count == 6

    def test_enriched_requires_observation_count_gt_0(self) -> None:
        with pytest.raises(ValueError, match="ENRICHED requires observation_count > 0"):
            DatasheetSourceOutcome(
                source=self._make_source(),
                final_url=SOURCE_URL,
                retrieved_at=RETRIEVED_AT,
                outcome_state=DatasheetOutcomeState.ENRICHED,
                observation_count=0,
            )

    def test_fetch_failed(self) -> None:
        outcome = DatasheetSourceOutcome(
            source=self._make_source(),
            final_url=None,
            retrieved_at=None,
            outcome_state=DatasheetOutcomeState.FETCH_FAILED,
            observation_count=0,
        )
        assert outcome.final_url is None

    def test_parse_failed(self) -> None:
        outcome = DatasheetSourceOutcome(
            source=self._make_source(),
            final_url=SOURCE_URL,
            retrieved_at=RETRIEVED_AT,
            outcome_state=DatasheetOutcomeState.PARSE_FAILED,
            observation_count=0,
        )
        assert outcome.outcome_state == DatasheetOutcomeState.PARSE_FAILED


# ---------------------------------------------------------------------------
# URL validation
# ---------------------------------------------------------------------------

class TestUrlValidation:
    def test_no_host_refused_in_source(self) -> None:
        with pytest.raises(ValueError, match="must include a host"):
            DatasheetSource(
                product_identity=_make_identity("XP123"),
                source_name="Test",
                source_url="https:///path",
                source_authority=SourceAuthority.AUTHORITATIVE,
            )

    def test_non_https_refused_in_source(self) -> None:
        with pytest.raises(ValueError, match="must be an absolute http:// or https://"):
            DatasheetSource(
                product_identity=_make_identity("XP123"),
                source_name="Test",
                source_url="ftp://example.com/doc.pdf",
                source_authority=SourceAuthority.AUTHORITATIVE,
            )


# ---------------------------------------------------------------------------
# enrich_enterprise_ssd_specifications — real PDF
# ---------------------------------------------------------------------------

class TestEnrichRealPdf:
    """Full enrichment pipeline against the real Seagate PDF fixture.

    Uses _enrich_from_datasheet_sources_internal() — the internal helper
    that operates on already-derived DatasheetSource objects.
    """

    def test_target_xp15360se70005(self) -> None:
        identity = _make_identity("XP15360SE70005")
        source = DatasheetSource(
            product_identity=identity,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        fetcher = _FilePdfFetcher(REAL_PDF_PATH, SOURCE_URL)

        result = _enrich_from_datasheet_sources_internal(
            product_identity=identity,
            sources=(source,),
            document_fetcher=fetcher,
        )

        assert len(result.raw_observations) == 6
        assert len(result.normalized_observations) == 6
        assert result.source_outcomes[0].outcome_state == DatasheetOutcomeState.ENRICHED

        spec_set = result.product_specification_set
        assert spec_set.resolutions["capacity"].state == ResolutionState.VERIFIED
        assert spec_set.resolutions["sequential_read"].state == ResolutionState.VERIFIED
        assert spec_set.resolutions["sequential_write"].state == ResolutionState.VERIFIED
        assert spec_set.resolutions["random_read_iops"].state == ResolutionState.VERIFIED
        assert spec_set.resolutions["random_write_iops"].state == ResolutionState.VERIFIED
        assert spec_set.resolutions["endurance_dwpd"].state == ResolutionState.VERIFIED
        assert spec_set.resolutions["physical_form_factor"].state == ResolutionState.UNKNOWN

    def test_candidate_xp15360se70015(self) -> None:
        identity = _make_identity("XP15360SE70015")
        source = DatasheetSource(
            product_identity=identity,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        fetcher = _FilePdfFetcher(REAL_PDF_PATH, SOURCE_URL)

        result = _enrich_from_datasheet_sources_internal(
            product_identity=identity,
            sources=(source,),
            document_fetcher=fetcher,
        )
        spec_set = result.product_specification_set
        assert spec_set.resolutions["capacity"].resolved_value.value == Decimal('15.36')

    def test_candidate_xp3840se70005(self) -> None:
        identity = _make_identity("XP3840SE70005")
        source = DatasheetSource(
            product_identity=identity,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        fetcher = _FilePdfFetcher(REAL_PDF_PATH, SOURCE_URL)

        result = _enrich_from_datasheet_sources_internal(
            product_identity=identity,
            sources=(source,),
            document_fetcher=fetcher,
        )
        spec_set = result.product_specification_set
        assert spec_set.resolutions["capacity"].resolved_value.value == Decimal('3.84')

    def test_complete_specification_set(self) -> None:
        identity = _make_identity("XP15360SE70005")
        source = DatasheetSource(
            product_identity=identity,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        fetcher = _FilePdfFetcher(REAL_PDF_PATH, SOURCE_URL)

        result = _enrich_from_datasheet_sources_internal(
            product_identity=identity,
            sources=(source,),
            document_fetcher=fetcher,
        )
        assert len(result.product_specification_set.resolutions) == 12


# ---------------------------------------------------------------------------
# Fetch failure handling
# ---------------------------------------------------------------------------

class TestEnrichFetchFailure:
    def test_document_fetch_error_produces_fetch_failed(self) -> None:
        identity = _make_identity("XP15360SE70005")
        source = DatasheetSource(
            product_identity=identity,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        fetcher = _ErrorPdfFetcher(DocumentFetchError)

        result = _enrich_from_datasheet_sources_internal(
            product_identity=identity,
            sources=(source,),
            document_fetcher=fetcher,
        )
        assert result.source_outcomes[0].outcome_state == DatasheetOutcomeState.FETCH_FAILED
        assert result.raw_observations == ()

    def test_unsafe_target_produces_source_refused(self) -> None:
        identity = _make_identity("XP15360SE70005")
        source = DatasheetSource(
            product_identity=identity,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        fetcher = _ErrorPdfFetcher(UnsafeDocumentTargetError)

        result = _enrich_from_datasheet_sources_internal(
            product_identity=identity,
            sources=(source,),
            document_fetcher=fetcher,
        )
        assert result.source_outcomes[0].outcome_state == DatasheetOutcomeState.SOURCE_REFUSED

    def test_fetch_failure_does_not_fabricate_values(self) -> None:
        identity = _make_identity("XP15360SE70005")
        source = DatasheetSource(
            product_identity=identity,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        fetcher = _ErrorPdfFetcher(DocumentFetchError)

        result = _enrich_from_datasheet_sources_internal(
            product_identity=identity,
            sources=(source,),
            document_fetcher=fetcher,
        )
        for key in ENTERPRISE_SSD_SCHEMA.definitions:
            assert result.product_specification_set.resolutions[key].state == ResolutionState.UNKNOWN


# ---------------------------------------------------------------------------
# Empty PDF
# ---------------------------------------------------------------------------

class TestEnrichEmptyPdf:
    def test_no_tables_returns_no_observations(self) -> None:
        identity = _make_identity("XP15360SE70005")
        source = DatasheetSource(
            product_identity=identity,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        fetcher = _EmptyPdfFetcher()

        result = _enrich_from_datasheet_sources_internal(
            product_identity=identity,
            sources=(source,),
            document_fetcher=fetcher,
        )
        assert len(result.raw_observations) == 0


# ---------------------------------------------------------------------------
# URL deduplication
# ---------------------------------------------------------------------------

class TestEnrichUrlDeduplication:
    def test_same_url_fetched_once(self) -> None:
        identity = _make_identity("XP15360SE70005")
        source1 = DatasheetSource(
            product_identity=identity,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        source2 = DatasheetSource(
            product_identity=identity,
            source_name="Seagate Datasheet (duplicate)",
            source_url=SOURCE_URL,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        fetcher = _FilePdfFetcher(REAL_PDF_PATH, SOURCE_URL)

        result = _enrich_from_datasheet_sources_internal(
            product_identity=identity,
            sources=(source1, source2),
            document_fetcher=fetcher,
        )
        assert len(result.source_outcomes) == 1


# ---------------------------------------------------------------------------
# Cross-product evidence rejected
# ---------------------------------------------------------------------------

class TestCrossProductEvidenceRejected:
    def test_cross_product_source_rejected(self) -> None:
        identity1 = _make_identity("XP15360SE70005")
        identity2 = _make_identity("XP3840SE70005")
        source = DatasheetSource(
            product_identity=identity2,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        with pytest.raises(ValueError, match="Cross-product source rejected"):
            _enrich_from_datasheet_sources_internal(
                product_identity=identity1,
                sources=(source,),
                document_fetcher=_EmptyPdfFetcher(),
            )


# ---------------------------------------------------------------------------
# Provenance audit
# ---------------------------------------------------------------------------

class TestProvenanceAudit:
    def test_final_url_preserved(self) -> None:
        identity = _make_identity("XP15360SE70005")
        source = DatasheetSource(
            product_identity=identity,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        fetcher = _FilePdfFetcher(REAL_PDF_PATH, SOURCE_URL)

        result = _enrich_from_datasheet_sources_internal(
            product_identity=identity,
            sources=(source,),
            document_fetcher=fetcher,
        )
        assert result.source_outcomes[0].final_url == SOURCE_URL
        assert result.source_outcomes[0].retrieved_at == RETRIEVED_AT

    def test_source_authority_stays_authoritative(self) -> None:
        identity = _make_identity("XP15360SE70005")
        source = DatasheetSource(
            product_identity=identity,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        fetcher = _FilePdfFetcher(REAL_PDF_PATH, SOURCE_URL)

        result = _enrich_from_datasheet_sources_internal(
            product_identity=identity,
            sources=(source,),
            document_fetcher=fetcher,
        )
        for obs in result.raw_observations:
            assert obs.source_authority is SourceAuthority.AUTHORITATIVE

    def test_identity_binding_exact(self) -> None:
        identity = _make_identity("XP15360SE70005")
        source = DatasheetSource(
            product_identity=identity,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        fetcher = _FilePdfFetcher(REAL_PDF_PATH, SOURCE_URL)

        result = _enrich_from_datasheet_sources_internal(
            product_identity=identity,
            sources=(source,),
            document_fetcher=fetcher,
        )
        for obs in result.raw_observations:
            assert obs.product_identity is identity
        assert result.product_specification_set.product_identity is identity


# ---------------------------------------------------------------------------
# Parser exception boundary
# ---------------------------------------------------------------------------

class TestParserExceptionBoundary:
    """Bounded parser exception handling: only pdfminer exceptions -> PARSE_FAILED.

    Programming exceptions (RuntimeError, TypeError, etc.) propagate even if
    raised while inside pdfplumber.open() or page.extract_tables().
    """

    def _make_source(self) -> DatasheetSource:
        return DatasheetSource(
            product_identity=_make_identity("XP15360SE70005"),
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )

    def _enrich(self, source, document_fetcher):
        return _enrich_from_datasheet_sources_internal(
            product_identity=source.product_identity,
            sources=(source,),
            document_fetcher=document_fetcher,
        )

    def test_malformed_pdf_parse_failed(self) -> None:
        class _MalformedFetcher:
            def fetch(self, request):
                return FetchedDocument(
                    requested_url=request.url,
                    final_url=request.url,
                    retrieved_at=RETRIEVED_AT,
                    content_type="application/pdf",
                    body_bytes=b"THIS IS NOT A PDF",
                    body_byte_count=17,
                    redirect_count=0,
                    fetcher_id="malformed",
                )

        source = self._make_source()
        result = self._enrich(source, _MalformedFetcher())
        assert result.source_outcomes[0].outcome_state == DatasheetOutcomeState.PARSE_FAILED
        assert len(result.raw_observations) == 0

    def test_runtimeerror_propagates(self) -> None:
        """RuntimeError from fetcher must propagate, not become PARSE_FAILED."""
        class _RuntimeErrorFetcher:
            def fetch(self, request):
                raise RuntimeError("programming error")

        source = self._make_source()
        with pytest.raises(RuntimeError, match="programming error"):
            self._enrich(source, _RuntimeErrorFetcher())

    def test_pdfplumber_open_parser_exception_parse_failed(self, monkeypatch) -> None:
        """A: monkeypatch pdfplumber.open to raise PDFSyntaxError -> PARSE_FAILED."""
        from pdfminer.pdfparser import PDFSyntaxError
        import pdfplumber

        monkeypatch.setattr(
            pdfplumber, "open",
            lambda *a, **k: (_ for _ in ()).throw(PDFSyntaxError("fake syntax")),
        )

        source = self._make_source()
        result = self._enrich(source, _EmptyPdfFetcher())
        assert result.source_outcomes[0].outcome_state == DatasheetOutcomeState.PARSE_FAILED

    def test_pdfplumber_open_runtime_error_propagates(self, monkeypatch) -> None:
        """B: monkeypatch pdfplumber.open to raise RuntimeError -> propagates."""
        import pdfplumber

        monkeypatch.setattr(
            pdfplumber, "open",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("programming error")),
        )

        source = self._make_source()
        with pytest.raises(RuntimeError, match="programming error"):
            self._enrich(source, _FilePdfFetcher(REAL_PDF_PATH, SOURCE_URL))

    def test_page_extract_tables_parser_exception_parse_failed(self, monkeypatch) -> None:
        """C: fake page.extract_tables raises PDFSyntaxError -> PARSE_FAILED."""
        import pdfplumber

        class _FakePdf:
            def __init__(self):
                self._closed = False

            @property
            def pages(self):
                class _FakePage:
                    def extract_tables(self):
                        from pdfminer.pdfparser import PDFSyntaxError
                        raise PDFSyntaxError("fake table parse error")
                return [_FakePage()]

            def close(self):
                self._closed = True

        monkeypatch.setattr(
            pdfplumber, "open",
            lambda *a, **k: _FakePdf(),
        )

        source = self._make_source()
        result = self._enrich(source, _FilePdfFetcher(REAL_PDF_PATH, SOURCE_URL))
        assert result.source_outcomes[0].outcome_state == DatasheetOutcomeState.PARSE_FAILED

    def test_page_extract_tables_runtime_error_propagates(self, monkeypatch) -> None:
        """D: fake page.extract_tables raises RuntimeError -> propagates."""
        import pdfplumber

        class _FakePdf:
            @property
            def pages(self):
                class _FakePage:
                    def extract_tables(self):
                        raise RuntimeError("programming error in extract_tables")
                return [_FakePage()]

            def close(self):
                pass

        monkeypatch.setattr(
            pdfplumber, "open",
            lambda *a, **k: _FakePdf(),
        )

        source = self._make_source()
        with pytest.raises(RuntimeError, match="programming error in extract_tables"):
            self._enrich(source, _FilePdfFetcher(REAL_PDF_PATH, SOURCE_URL))

    def test_mpn_ambiguity_valueerror_propagates(self, monkeypatch) -> None:
        """E: whole-document MPN ambiguity ValueError propagates, never PARSE_FAILED."""
        import pdfplumber

        class _FakePdf:
            @property
            def pages(self):
                class _FakePage:
                    def extract_tables(self):
                        # Return a table with ambiguous MPN
                        return [[
                            ["Standard Model", "XP15360SE70005", "XP15360SE70005"],
                            ["Capacity", "1TB", "2TB"],
                        ]]
                return [_FakePage()]

            def close(self):
                pass

        monkeypatch.setattr(
            pdfplumber, "open",
            lambda *a, **k: _FakePdf(),
        )

        source = self._make_source()
        with pytest.raises(ValueError, match="ambiguous"):
            self._enrich(source, _FilePdfFetcher(REAL_PDF_PATH, SOURCE_URL))


# ---------------------------------------------------------------------------
# Result self-audit — adversarial tests
# ---------------------------------------------------------------------------

class TestResultSelfAudit:
    """SpecificationEnrichmentResult must be genuinely self-auditing.

    Tests build valid results, then create tampered copies using
    test-only object.__setattr__ or reconstructed frozen objects.
    Every tampered copy must be rejected at construction.
    """

    def _make_valid_result(self) -> SpecificationEnrichmentResult:
        """Build a valid result through the real pipeline."""
        identity = _make_identity("XP15360SE70005")
        source = DatasheetSource(
            product_identity=identity,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        fetcher = _FilePdfFetcher(REAL_PDF_PATH, SOURCE_URL)
        return _enrich_from_datasheet_sources_internal(
            product_identity=identity,
            sources=(source,),
            document_fetcher=fetcher,
        )

    def test_valid_result_construction_succeeds(self) -> None:
        """A legitimately constructed result passes all self-audits."""
        result = self._make_valid_result()
        # If we got here, self-audit passed
        assert len(result.raw_observations) == 6

    # -- REAL constructor rejection tests --

    def test_enriched_count_positive_zero_raw_rejected(self) -> None:
        """ENRICHED count > 0 + zero raw observations must reject."""
        identity = _make_identity("XP15360SE70005")
        source = DatasheetSource(
            product_identity=identity,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        outcome = DatasheetSourceOutcome(
            source=source,
            final_url=SOURCE_URL,
            retrieved_at=RETRIEVED_AT,
            outcome_state=DatasheetOutcomeState.ENRICHED,
            observation_count=6,
        )
        # Build an empty spec set (all UNKNOWN)
        from product_intelligence.research.specifications import resolve_specification
        resolutions = {}
        for key, defn in ENTERPRISE_SSD_SCHEMA.definitions.items():
            resolutions[key] = resolve_specification(identity, defn, ())
        spec_set = ProductSpecificationSet(
            product_identity=identity,
            category_schema=ENTERPRISE_SSD_SCHEMA,
            resolutions=resolutions,
        )
        # ENRICHED outcome claims 6 observations but zero raw -> reject
        with pytest.raises(ValueError, match="fabricated evidence"):
            SpecificationEnrichmentResult(
                product_identity=identity,
                source_outcomes=(outcome,),
                raw_observations=(),
                normalized_observations=(),
                product_specification_set=spec_set,
            )

    def test_wrong_final_url_rejected(self) -> None:
        """Observation with wrong final_url relative to outcome -> reject."""
        result = self._make_valid_result()
        # Tamper the outcome's final_url
        tampered_outcome = DatasheetSourceOutcome(
            source=result.source_outcomes[0].source,
            final_url="https://evil.com/datasheet.pdf",
            retrieved_at=result.source_outcomes[0].retrieved_at,
            outcome_state=result.source_outcomes[0].outcome_state,
            observation_count=result.source_outcomes[0].observation_count,
        )
        with pytest.raises(ValueError, match="does not trace"):
            SpecificationEnrichmentResult(
                product_identity=result.product_identity,
                source_outcomes=(tampered_outcome,),
                raw_observations=result.raw_observations,
                normalized_observations=result.normalized_observations,
                product_specification_set=result.product_specification_set,
            )

    def test_wrong_retrieved_at_rejected(self) -> None:
        """Observation with wrong retrieved_at relative to outcome -> reject."""
        result = self._make_valid_result()
        from datetime import timedelta
        tampered_outcome = DatasheetSourceOutcome(
            source=result.source_outcomes[0].source,
            final_url=result.source_outcomes[0].final_url,
            retrieved_at=RETRIEVED_AT - timedelta(hours=1),
            outcome_state=result.source_outcomes[0].outcome_state,
            observation_count=result.source_outcomes[0].observation_count,
        )
        with pytest.raises(ValueError, match="does not trace"):
            SpecificationEnrichmentResult(
                product_identity=result.product_identity,
                source_outcomes=(tampered_outcome,),
                raw_observations=result.raw_observations,
                normalized_observations=result.normalized_observations,
                product_specification_set=result.product_specification_set,
            )

    def test_wrong_source_name_rejected(self) -> None:
        """Observation with wrong source_name relative to outcome -> reject."""
        result = self._make_valid_result()
        tampered_source = DatasheetSource(
            product_identity=result.source_outcomes[0].source.product_identity,
            source_name="Wrong Name Datasheet",
            source_url=SOURCE_URL,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        tampered_outcome = DatasheetSourceOutcome(
            source=tampered_source,
            final_url=result.source_outcomes[0].final_url,
            retrieved_at=result.source_outcomes[0].retrieved_at,
            outcome_state=result.source_outcomes[0].outcome_state,
            observation_count=result.source_outcomes[0].observation_count,
        )
        with pytest.raises(ValueError, match="does not trace"):
            SpecificationEnrichmentResult(
                product_identity=result.product_identity,
                source_outcomes=(tampered_outcome,),
                raw_observations=result.raw_observations,
                normalized_observations=result.normalized_observations,
                product_specification_set=result.product_specification_set,
            )

    def test_wrong_source_authority_rejected(self) -> None:
        """Observation with SECONDARY authority cannot trace to AUTHORITATIVE outcome -> reject.

        DatasheetSource requires AUTHORITATIVE, so the outcome's source authority
        is always AUTHORITATIVE. Tamper one raw observation to SECONDARY authority
        using object.__setattr__ (test-only frozen bypass), rebuild its normalized
        wrapper, and prove the result constructor rejects it during provenance audit.
        """
        result = self._make_valid_result()

        # Tamper the first raw observation's source_authority to SECONDARY
        tampered_obs = result.raw_observations[0]
        object.__setattr__(
            tampered_obs, "source_authority", SourceAuthority.SECONDARY
        )

        # Rebuild normalized observation wrapping the tampered raw observation
        tampered_norm = normalize_enterprise_ssd_observation(tampered_obs)

        # Build new tuples preserving the tampered first observation
        new_raw = (tampered_obs, *result.raw_observations[1:])
        new_norm = (tampered_norm, *result.normalized_observations[1:])

        with pytest.raises(ValueError, match="does not trace"):
            SpecificationEnrichmentResult(
                product_identity=result.product_identity,
                source_outcomes=result.source_outcomes,
                raw_observations=new_raw,
                normalized_observations=new_norm,
                product_specification_set=result.product_specification_set,
            )

    def test_evidence_only_matches_failed_source_rejected(self) -> None:
        """ENRICHED observations cannot trace to a FETCH_FAILED outcome."""
        result = self._make_valid_result()
        # Replace ENRICHED outcome with FETCH_FAILED
        tampered_outcome = DatasheetSourceOutcome(
            source=result.source_outcomes[0].source,
            final_url=None,
            retrieved_at=None,
            outcome_state=DatasheetOutcomeState.FETCH_FAILED,
            observation_count=0,
        )
        with pytest.raises(ValueError, match="does not trace"):
            SpecificationEnrichmentResult(
                product_identity=result.product_identity,
                source_outcomes=(tampered_outcome,),
                raw_observations=result.raw_observations,
                normalized_observations=result.normalized_observations,
                product_specification_set=result.product_specification_set,
            )

    def test_substituted_normalized_observation_rejected(self) -> None:
        """A normalized observation that references a foreign raw obs -> reject."""
        result = self._make_valid_result()
        # Build a foreign raw observation
        foreign_identity = _make_identity("FOREIGN123")
        foreign_obs = SpecificationObservation(
            product_identity=foreign_identity,
            definition=ENTERPRISE_SSD_SCHEMA.definitions["capacity"],
            source_name="Foreign",
            source_url="https://foreign.com/datasheet.pdf",
            retrieved_at=RETRIEVED_AT,
            raw_value="99.99TB",
            source_authority=SourceAuthority.AUTHORITATIVE,
            raw_reference="foreign",
        )
        foreign_norm = normalize_enterprise_ssd_observation(foreign_obs)
        # Build a new tuple with the foreign normalized observation
        tampered_normalized = (foreign_norm, *result.normalized_observations[1:])
        with pytest.raises(ValueError, match="Cross-product"):
            SpecificationEnrichmentResult(
                product_identity=result.product_identity,
                source_outcomes=result.source_outcomes,
                raw_observations=result.raw_observations,
                normalized_observations=tampered_normalized,
                product_specification_set=result.product_specification_set,
            )

    def test_reordered_normalized_observations_rejected(self) -> None:
        """Reordering normalized observations breaks raw-norm binding -> reject."""
        result = self._make_valid_result()
        # Reverse the normalized observations
        reversed_norm = tuple(reversed(result.normalized_observations))
        with pytest.raises(ValueError, match="Raw-normalized binding broken"):
            SpecificationEnrichmentResult(
                product_identity=result.product_identity,
                source_outcomes=result.source_outcomes,
                raw_observations=result.raw_observations,
                normalized_observations=reversed_norm,
                product_specification_set=result.product_specification_set,
            )

    def test_foreign_normalized_evidence_rejected(self) -> None:
        """ProductSpecificationSet built from foreign normalized evidence -> reject."""
        result = self._make_valid_result()
        # Build a spec set from empty evidence (all UNKNOWN)
        resolutions = {}
        for key, defn in ENTERPRISE_SSD_SCHEMA.definitions.items():
            resolutions[key] = resolve_specification(
                result.product_identity, defn, ()
            )
        foreign_spec_set = ProductSpecificationSet(
            product_identity=result.product_identity,
            category_schema=ENTERPRISE_SSD_SCHEMA,
            resolutions=resolutions,
        )
        with pytest.raises(ValueError, match="state mismatch"):
            SpecificationEnrichmentResult(
                product_identity=result.product_identity,
                source_outcomes=result.source_outcomes,
                raw_observations=result.raw_observations,
                normalized_observations=result.normalized_observations,
                product_specification_set=foreign_spec_set,
            )

    def test_per_source_count_mismatch_rejected(self) -> None:
        """Outcome claims 6 observations but only 5 trace -> reject."""
        result = self._make_valid_result()
        # Tamper outcome to claim one more observation than exists
        tampered_outcome = DatasheetSourceOutcome(
            source=result.source_outcomes[0].source,
            final_url=result.source_outcomes[0].final_url,
            retrieved_at=result.source_outcomes[0].retrieved_at,
            outcome_state=result.source_outcomes[0].outcome_state,
            observation_count=7,  # one more than actual
        )
        with pytest.raises(ValueError, match="Per-source audit"):
            SpecificationEnrichmentResult(
                product_identity=result.product_identity,
                source_outcomes=(tampered_outcome,),
                raw_observations=result.raw_observations,
                normalized_observations=result.normalized_observations,
                product_specification_set=result.product_specification_set,
            )

    def test_ambiguous_duplicate_provenance_rejected(self) -> None:
        """Two ENRICHED outcomes with identical provenance -> reject."""
        result = self._make_valid_result()
        # Create two ENRICHED outcomes with identical provenance
        dup_outcome = DatasheetSourceOutcome(
            source=result.source_outcomes[0].source,
            final_url=result.source_outcomes[0].final_url,
            retrieved_at=result.source_outcomes[0].retrieved_at,
            outcome_state=DatasheetOutcomeState.ENRICHED,
            observation_count=result.source_outcomes[0].observation_count,
        )
        with pytest.raises(ValueError, match="Ambiguous duplicate provenance"):
            SpecificationEnrichmentResult(
                product_identity=result.product_identity,
                source_outcomes=(
                    result.source_outcomes[0],
                    dup_outcome,
                ),
                raw_observations=result.raw_observations,
                normalized_observations=result.normalized_observations,
                product_specification_set=result.product_specification_set,
            )


# ---------------------------------------------------------------------------
# 6C + 6D composition
# ---------------------------------------------------------------------------

class TestComposition:
    """Real frozen 6C + 6D evidence composition.

    Uses actual frozen 6C extraction from the real Seagate HTML fixture
    plus actual 6D enrichment from the real PDF fixture.
    """

    def test_real_frozen_6c_plus_6d_composition(self) -> None:
        """Run frozen 6C extraction, then compose with actual 6D evidence."""
        from product_intelligence.execution.specification_evidence import (
            research_enterprise_ssd_specifications,
            SpecificationEvidenceSource,
        )

        identity = _make_identity("XP15360SE70005")

        # --- Frozen 6C: extract from real Seagate HTML fixture ---
        FIXTURE_DIR = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "specifications"
        REAL_HTML = FIXTURE_DIR / "real_seagate_nytro_5050_xp15360se70005.html"
        real_html_content = REAL_HTML.read_text(encoding="utf-8")

        class _FilePageFetcher:
            def fetch(self, request):
                from product_intelligence.providers.page import FetchedPage
                return FetchedPage(
                    requested_url=request.url,
                    final_url=request.url,
                    body_text=real_html_content,
                    content_type="text/html",
                    status_code=200,
                    retrieved_at=RETRIEVED_AT,
                )

        six_c_source = SpecificationEvidenceSource(
            product_identity=identity,
            source_name="Seagate Support",
            source_url="https://www.seagate.com/support/enterprise-storage/solid-state-drives/nytro-5050/",
            source_authority=SourceAuthority.AUTHORITATIVE,
        )

        six_c_result = research_enterprise_ssd_specifications(
            product_identity=identity,
            sources=(six_c_source,),
            page_fetcher=_FilePageFetcher(),
        )

        # Verify frozen 6C contributes: physical_form_factor VERIFIED "2.5-inch"
        ff = six_c_result.product_specification_set.resolutions["physical_form_factor"]
        assert ff.state == ResolutionState.VERIFIED
        assert ff.resolved_value.value == "2.5-inch"

        # --- Frozen 6D: enrich from real PDF fixture ---
        source = DatasheetSource(
            product_identity=identity,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        fetcher = _FilePdfFetcher(REAL_PDF_PATH, SOURCE_URL)
        enrichment = _enrich_from_datasheet_sources_internal(
            product_identity=identity,
            sources=(source,),
            document_fetcher=fetcher,
        )

        # Verify 6D contributes: capacity VERIFIED
        cap = enrichment.product_specification_set.resolutions["capacity"]
        assert cap.state == ResolutionState.VERIFIED

        # --- Compose: 6C normalized evidence + 6D normalized evidence ---
        combined = compose_6c_6d_specifications(
            product_identity=identity,
            frozen_6c_spec_set=six_c_result.product_specification_set,
            enrichment_result=enrichment,
        )

        assert combined.product_identity is identity
        assert combined.category_schema is ENTERPRISE_SSD_SCHEMA
        assert len(combined.resolutions) == 12

        # physical_form_factor: VERIFIED from 6C
        assert combined.resolutions["physical_form_factor"].state == ResolutionState.VERIFIED
        # capacity: VERIFIED from 6D
        assert combined.resolutions["capacity"].state == ResolutionState.VERIFIED
        # sequential_read: VERIFIED from 6D
        assert combined.resolutions["sequential_read"].state == ResolutionState.VERIFIED

    def test_cross_product_composition_rejected(self) -> None:
        identity1 = _make_identity("XP15360SE70005")
        identity2 = _make_identity("XP3840SE70005")

        source = DatasheetSource(
            product_identity=identity1,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        fetcher = _FilePdfFetcher(REAL_PDF_PATH, SOURCE_URL)
        enrichment = _enrich_from_datasheet_sources_internal(
            product_identity=identity1,
            sources=(source,),
            document_fetcher=fetcher,
        )

        with pytest.raises(ValueError, match="Cross-product"):
            compose_6c_6d_specifications(
                product_identity=identity2,
                frozen_6c_spec_set=enrichment.product_specification_set,
                enrichment_result=enrichment,
            )


# ---------------------------------------------------------------------------
# Programming exception propagation
# ---------------------------------------------------------------------------

class TestProgrammingExceptionPropagation:
    def test_unestablished_identity_raises(self) -> None:
        identity = ProductIdentity(
            manufacturer_part_number="XP123",
            match_type=IdentityMatchType.UNKNOWN,
        )
        with pytest.raises(ValueError, match="requires an established"):
            _enrich_from_datasheet_sources_internal(
                product_identity=identity,
                sources=(),
                document_fetcher=_EmptyPdfFetcher(),
            )


# ---------------------------------------------------------------------------
# Real frozen 7B vertical slice (Section 10) + one-fetch proof (Section 11)
# ---------------------------------------------------------------------------

class TestReal7BVerticalSlice:
    """Real frozen 7A + 6C + 6D + 7B vertical slice.

    Runs the actual chain:
    frozen 6C target + 6D target -> combined target spec set
    frozen 7A candidate discovery -> exact candidates
    frozen 7B establish_candidate_product_identity(candidate)
    frozen 6C candidate evidence + 6D candidate evidence -> combined candidate spec set
    frozen ComparableCandidateSpecificationProfile
    frozen score_enterprise_ssd_candidate_similarity(...)
    """

    def _load_real_html(self) -> str:
        FIXTURE_DIR = (
            Path(__file__).resolve().parents[2]
            / "tests" / "fixtures" / "specifications"
        )
        return (
            FIXTURE_DIR / "real_seagate_nytro_5050_xp15360se70005.html"
        ).read_text(encoding="utf-8")

    def _make_page_fetcher(self, html_content: str):
        class _FilePageFetcher:
            def __init__(self, content):
                self._content = content
                self.fetch_count = 0

            def fetch(self, request):
                from product_intelligence.providers.page import FetchedPage
                self.fetch_count += 1
                return FetchedPage(
                    requested_url=request.url,
                    final_url=request.url,
                    body_text=self._content,
                    content_type="text/html",
                    status_code=200,
                    retrieved_at=RETRIEVED_AT,
                )
        return _FilePageFetcher(html_content)

    def _make_pdf_fetcher(self):
        class _FilePdfFetcher:
            def __init__(self):
                self.fetch_count = 0

            def fetch(self, request):
                self.fetch_count += 1
                with open(REAL_PDF_PATH, "rb") as f:
                    data = f.read()
                return FetchedDocument(
                    requested_url=request.url,
                    final_url=SOURCE_URL,
                    retrieved_at=RETRIEVED_AT,
                    content_type="application/pdf",
                    body_bytes=data,
                    body_byte_count=len(data),
                    redirect_count=0,
                    fetcher_id="file-pdf",
                )
        return _FilePdfFetcher()

    def _extracted_outcome_from_discovery(self, discovery_result):
        """Find the EXTRACTED outcome from a discovery result."""
        from product_intelligence.execution.comparable_discovery import (
            ComparableCandidateSourceOutcomeState as DSOutcomeState,
        )
        for o in discovery_result.source_outcomes:
            if o.outcome_state is DSOutcomeState.EXTRACTED:
                return o
        return None

    def test_real_7b_vertical_slice_with_enrichment(self) -> None:
        """Full chain: 6C + 6D -> 7A -> 7B with real fixtures.

        Required candidates: XP15360SE70015, XP3840SE70005.
        Uses the PUBLIC authority-grounded API for all 6D enrichment.
        """
        from product_intelligence.execution.comparable_discovery import (
            discover_enterprise_ssd_comparable_candidates,
            ComparableCandidateSource,
        )
        from product_intelligence.execution.specification_evidence import (
            research_enterprise_ssd_specifications,
            SpecificationEvidenceSource,
        )
        from product_intelligence.research.enterprise_ssd_similarity import (
            ComparableCandidateSpecificationProfile,
            establish_candidate_product_identity,
            score_enterprise_ssd_candidate_similarity,
        )

        target_identity = _make_identity("XP15360SE70005")
        html_content = self._load_real_html()

        # --- Frozen 7A candidate source ---
        support_source = ComparableCandidateSource(
            source_name="Seagate Support",
            source_url="https://www.seagate.com/support/enterprise-storage/solid-state-drives/nytro-5050/",
            source_authority=SourceAuthority.AUTHORITATIVE,
        )

        page_fetcher = self._make_page_fetcher(html_content)

        # --- Frozen 6C target evidence ---
        six_c_source = SpecificationEvidenceSource(
            product_identity=target_identity,
            source_name=support_source.source_name,
            source_url=support_source.source_url,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )

        six_c_result = research_enterprise_ssd_specifications(
            product_identity=target_identity,
            sources=(six_c_source,),
            page_fetcher=page_fetcher,
        )

        # --- Frozen 7A candidate discovery ---
        discovery_result = discover_enterprise_ssd_comparable_candidates(
            target_identity=target_identity,
            target_specification_set=six_c_result.product_specification_set,
            sources=(support_source,),
            page_fetcher=page_fetcher,
        )

        # Find required candidates
        candidate_mpn_to_candidate = {}
        for candidate in discovery_result.candidates:
            candidate_mpn_to_candidate[
                candidate.normalized_part_number
            ] = candidate

        assert "XP15360SE70015" in candidate_mpn_to_candidate, (
            "XP15360SE70015 not found in 7A candidates"
        )
        assert "XP3840SE70005" in candidate_mpn_to_candidate, (
            "XP3840SE70005 not found in 7A candidates"
        )

        # --- 6D target enrichment via PUBLIC authority-grounded API ---
        pdf_fetcher = self._make_pdf_fetcher()
        extracted_outcome = self._extracted_outcome_from_discovery(discovery_result)
        assert extracted_outcome is not None

        six_d_result = enrich_enterprise_ssd_specifications(
            product_identity=target_identity,
            discovery_result=discovery_result,
            source_outcome=extracted_outcome,
            page_fetcher=page_fetcher,
            document_fetcher=pdf_fetcher,
        )

        # --- Combined target spec set ---
        combined_target_spec = compose_6c_6d_specifications(
            product_identity=target_identity,
            frozen_6c_spec_set=six_c_result.product_specification_set,
            enrichment_result=six_d_result,
        )

        # --- For each required candidate: 6C + 6D composition + scoring ---
        # Candidate 6C evidence extracted from the already-held support page
        # document (same approach as frozen 7B). No extra page fetch required.
        from product_intelligence.research.enterprise_ssd_extraction import (
            extract_enterprise_ssd_specification_observations,
        )
        from product_intelligence.research.specifications import resolve_specification

        # Per-candidate exact expected values (derived from real fixtures):
        # XP15360SE70015: all 7 shared fields match target exactly
        # XP3840SE70005: capacity differs (3.84 vs 15.36 -> 0.25),
        #                sequential_write differs (6900 vs 7200 -> 0.95833...)
        EXPECTED_SCORED_FIELD_COUNT = 7  # 1 (6C form factor) + 6 (6D datasheet fields)
        EXPECTED_EVIDENCE_COVERAGE = Decimal(7) / Decimal(12)
        EXPECTED_OBSERVED_SIMILARITY_XP15360 = Decimal("1")
        EXPECTED_EW_SIMILARITY_XP15360 = Decimal("7") / Decimal("12")
        # XP3840: (0.25 + 1 + 1 + 0.958333... + 1 + 1 + 1) / 7 = observed
        #         (0.25 + 1 + 1 + 0.958333... + 1 + 1 + 1) / 12 = evidence_weighted
        EXPECTED_CAP_SIM_XP3840 = Decimal("3.84") / Decimal("15.36")  # 0.25
        EXPECTED_SW_SIM_XP3840 = Decimal("6900") / Decimal("7200")   # 0.958333...
        EXPECTED_OBSERVED_SIMILARITY_XP3840 = (
            EXPECTED_CAP_SIM_XP3840 + Decimal("5") + EXPECTED_SW_SIM_XP3840
        ) / Decimal("7")
        EXPECTED_EW_SIMILARITY_XP3840 = (
            EXPECTED_CAP_SIM_XP3840 + Decimal("5") + EXPECTED_SW_SIM_XP3840
        ) / Decimal("12")

        for candidate_key, expected_capacity in (
            ("XP15360SE70015", Decimal("15.36")),
            ("XP3840SE70005", Decimal("3.84")),
        ):
            candidate = candidate_mpn_to_candidate[candidate_key]

            # 7B bridge: establish candidate identity
            candidate_identity = establish_candidate_product_identity(candidate)
            assert candidate_identity.is_established

            # --- Frozen 6C candidate evidence (from held document, no new fetch) ---
            # Extract raw observations from the support page's supportSpecsData JSON
            # using the same frozen extraction function that 6C/7B use internally.
            cand_6c_raw_obs = list(
                extract_enterprise_ssd_specification_observations(
                    product_identity=candidate_identity,
                    document=html_content,
                    source_name=support_source.source_name,
                    source_url=support_source.source_url,
                    final_url=support_source.source_url,
                    retrieved_at=RETRIEVED_AT,
                    source_authority=SourceAuthority.AUTHORITATIVE,
                )
            )
            # Normalize via frozen 6B
            cand_6c_normalized: list[NormalizedSpecificationObservation] = []
            for obs in cand_6c_raw_obs:
                cand_6c_normalized.append(normalize_enterprise_ssd_observation(obs))
            # Resolve via frozen 6A
            cand_6c_obs_by_def: dict[str, list[NormalizedSpecificationObservation]] = {
                key: [] for key in ENTERPRISE_SSD_SCHEMA.definitions
            }
            for norm_obs in cand_6c_normalized:
                key = norm_obs.observation.definition.key
                if key in cand_6c_obs_by_def:
                    cand_6c_obs_by_def[key].append(norm_obs)
            cand_6c_resolutions: dict[str, Any] = {}
            for key, definition in ENTERPRISE_SSD_SCHEMA.definitions.items():
                cand_6c_resolutions[key] = resolve_specification(
                    candidate_identity, definition, tuple(cand_6c_obs_by_def[key])
                )
            cand_6c_spec_set = ProductSpecificationSet(
                product_identity=candidate_identity,
                category_schema=ENTERPRISE_SSD_SCHEMA,
                resolutions=cand_6c_resolutions,
            )
            # Verify 6C provides physical_form_factor VERIFIED
            assert (
                cand_6c_spec_set.resolutions["physical_form_factor"].state
                == ResolutionState.VERIFIED
            ), (
                f"{candidate_key}: 6C should provide physical_form_factor VERIFIED"
            )

            # --- 6D candidate enrichment via PUBLIC authority-grounded API ---
            candidate_enrichment = enrich_enterprise_ssd_specifications(
                product_identity=candidate_identity,
                discovery_result=discovery_result,
                source_outcome=extracted_outcome,
                page_fetcher=page_fetcher,
                document_fetcher=pdf_fetcher,
            )

            # --- Compose frozen 6C + 6D candidate evidence ---
            combined_candidate_spec = compose_6c_6d_specifications(
                product_identity=candidate_identity,
                frozen_6c_spec_set=cand_6c_spec_set,
                enrichment_result=candidate_enrichment,
            )

            # Verify composition preserves 6C evidence
            assert (
                combined_candidate_spec.resolutions["physical_form_factor"].state
                == ResolutionState.VERIFIED
            ), (
                f"{candidate_key}: composition lost physical_form_factor VERIFIED from 6C"
            )
            assert (
                combined_candidate_spec.resolutions["capacity"].state
                == ResolutionState.VERIFIED
            ), (
                f"{candidate_key}: composition should have capacity VERIFIED from 6D"
            )
            assert (
                combined_candidate_spec.resolutions["capacity"].resolved_value.value
                == expected_capacity
            ), (
                f"{candidate_key}: capacity should be {expected_capacity}"
            )

            # Build profile and score
            profile = ComparableCandidateSpecificationProfile(
                candidate=candidate,
                candidate_identity=candidate_identity,
                specification_set=combined_candidate_spec,
            )

            similarity = score_enterprise_ssd_candidate_similarity(
                target_specification_set=combined_target_spec,
                candidate_profile=profile,
            )

            # --- Exact post-6D assertions ---
            assert similarity.scored_field_count == EXPECTED_SCORED_FIELD_COUNT, (
                f"{candidate_key}: expected {EXPECTED_SCORED_FIELD_COUNT} scored fields, "
                f"got {similarity.scored_field_count}"
            )
            assert similarity.evidence_coverage == EXPECTED_EVIDENCE_COVERAGE, (
                f"{candidate_key}: expected evidence_coverage {EXPECTED_EVIDENCE_COVERAGE}, "
                f"got {similarity.evidence_coverage}"
            )

            # Exact observed_similarity and evidence_weighted_similarity
            if candidate_key == "XP15360SE70015":
                assert similarity.observed_similarity == EXPECTED_OBSERVED_SIMILARITY_XP15360, (
                    f"{candidate_key}: expected observed_similarity {EXPECTED_OBSERVED_SIMILARITY_XP15360}, "
                    f"got {similarity.observed_similarity}"
                )
                assert similarity.evidence_weighted_similarity == EXPECTED_EW_SIMILARITY_XP15360, (
                    f"{candidate_key}: expected evidence_weighted_similarity "
                    f"{EXPECTED_EW_SIMILARITY_XP15360}, got {similarity.evidence_weighted_similarity}"
                )
            else:  # XP3840SE70005
                assert similarity.observed_similarity == EXPECTED_OBSERVED_SIMILARITY_XP3840, (
                    f"{candidate_key}: expected observed_similarity {EXPECTED_OBSERVED_SIMILARITY_XP3840}, "
                    f"got {similarity.observed_similarity}"
                )
                assert similarity.evidence_weighted_similarity == EXPECTED_EW_SIMILARITY_XP3840, (
                    f"{candidate_key}: expected evidence_weighted_similarity "
                    f"{EXPECTED_EW_SIMILARITY_XP3840}, got {similarity.evidence_weighted_similarity}"
                )

            # Verify exact field states
            field_states = {
                fa.definition.key: fa
                for fa in similarity.field_assessments
            }

            # physical_form_factor must be SCORED (preserved from 6C)
            assert (
                field_states["physical_form_factor"].comparison_state.value == "SCORED"
            ), (
                f"{candidate_key}: physical_form_factor must be SCORED (from 6C)"
            )
            assert field_states["physical_form_factor"].field_similarity == 1, (
                f"{candidate_key}: physical_form_factor should match exactly"
            )

            # All six 6D fields must be SCORED
            for field_key in (
                "capacity",
                "sequential_read",
                "sequential_write",
                "random_read_iops",
                "random_write_iops",
                "endurance_dwpd",
            ):
                assert (
                    field_states[field_key].comparison_state.value == "SCORED"
                ), (
                    f"{candidate_key}: {field_key} must be SCORED (from 6D)"
                )

            # Exact field_similarity for non-trivial comparisons
            if candidate_key == "XP15360SE70015":
                # All 7 scored fields match exactly
                assert field_states["capacity"].field_similarity == 1
                assert field_states["sequential_write"].field_similarity == 1
            else:  # XP3840SE70005
                assert field_states["capacity"].field_similarity == EXPECTED_CAP_SIM_XP3840, (
                    f"{candidate_key}: capacity field_similarity should be {EXPECTED_CAP_SIM_XP3840}"
                )
                assert field_states["sequential_write"].field_similarity == EXPECTED_SW_SIM_XP3840, (
                    f"{candidate_key}: sequential_write field_similarity should be {EXPECTED_SW_SIM_XP3840}"
                )
                # Remaining 6D fields match exactly
                for fk in ("sequential_read", "random_read_iops", "random_write_iops", "endurance_dwpd"):
                    assert field_states[fk].field_similarity == 1

            # All non-scored fields must be BOTH_NOT_VERIFIED
            for field_key in (
                "storage_protocol",
                "pcie_generation",
                "pcie_lane_count",
                "interface_connector",
                "power_loss_protection",
            ):
                assert (
                    field_states[field_key].comparison_state.value
                    == "BOTH_NOT_VERIFIED"
                ), (
                    f"{candidate_key}: {field_key} must be BOTH_NOT_VERIFIED"
                )

    def test_real_one_fetch_proof(self) -> None:
        """Same URL passed twice in one call -> ONE fetch (per-call dedup).
        Uses _enrich_from_datasheet_sources_internal() for URL dedup proof.
        """
        identity = _make_identity("XP15360SE70005")

        class _CountingPdfFetcher:
            def __init__(self):
                self.fetch_count = 0

            def fetch(self, request):
                self.fetch_count += 1
                with open(REAL_PDF_PATH, "rb") as f:
                    data = f.read()
                return FetchedDocument(
                    requested_url=request.url,
                    final_url=request.url,
                    retrieved_at=RETRIEVED_AT,
                    content_type="application/pdf",
                    body_bytes=data,
                    body_byte_count=len(data),
                    redirect_count=0,
                    fetcher_id="counting-pdf",
                )

        pdf_fetcher = _CountingPdfFetcher()

        # Same URL passed twice in one call -> deduplicated to ONE fetch
        source1 = DatasheetSource(
            product_identity=identity,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        source2 = DatasheetSource(
            product_identity=identity,
            source_name="Seagate Datasheet (duplicate)",
            source_url=SOURCE_URL,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        result = _enrich_from_datasheet_sources_internal(
            product_identity=identity,
            sources=(source1, source2),
            document_fetcher=pdf_fetcher,
        )
        assert len(result.raw_observations) == 6

        # Two sources, same URL -> ONE fetch (URL dedup within the call)
        assert pdf_fetcher.fetch_count == 1, (
            f"Expected 1 PDF fetch (URL dedup), got {pdf_fetcher.fetch_count}"
        )

    def test_real_one_fetch_proof_batch(self) -> None:
        """Batch: 3 identities, 1 support page, 1 PDF -> 1 of each.

        Uses a real 7A ComparableCandidateDiscoveryResult as authority.
        """
        from product_intelligence.execution.comparable_discovery import (
            discover_enterprise_ssd_comparable_candidates,
        )
        from product_intelligence.execution.specification_enrichment import (
            enrich_enterprise_ssd_specifications_batch,
        )
        from product_intelligence.execution.specification_evidence import (
            research_enterprise_ssd_specifications,
            SpecificationEvidenceSource,
        )
        from product_intelligence.research.comparable_candidates import (
            ComparableCandidateSource,
        )

        identities = tuple([
            _make_identity("XP15360SE70005"),
            _make_identity("XP15360SE70015"),
            _make_identity("XP3840SE70005"),
        ])
        html_content = self._load_real_html()
        target_identity = _make_identity("XP15360SE70005")

        # --- Build real 7A discovery result (authority source) ---
        support_source = ComparableCandidateSource(
            source_name="Seagate Support",
            source_url="https://www.seagate.com/support/enterprise-storage/solid-state-drives/nytro-5050/",
            source_authority=SourceAuthority.AUTHORITATIVE,
        )

        # Page fetcher for 7A discovery
        class _DiscoveryPageFetcher:
            def __init__(self, content):
                self._content = content
                self.fetch_count = 0

            def fetch(self, request):
                from product_intelligence.providers.page import FetchedPage
                self.fetch_count += 1
                return FetchedPage(
                    requested_url=request.url,
                    final_url=request.url,
                    body_text=self._content,
                    content_type="text/html",
                    status_code=200,
                    retrieved_at=RETRIEVED_AT,
                )

        discovery_page_fetcher = _DiscoveryPageFetcher(html_content)

        # 6C target evidence for discovery
        six_c_source = SpecificationEvidenceSource(
            product_identity=target_identity,
            source_name=support_source.source_name,
            source_url=support_source.source_url,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        six_c_result = research_enterprise_ssd_specifications(
            product_identity=target_identity,
            sources=(six_c_source,),
            page_fetcher=discovery_page_fetcher,
        )

        # 7A candidate discovery
        discovery_result = discover_enterprise_ssd_comparable_candidates(
            target_identity=target_identity,
            target_specification_set=six_c_result.product_specification_set,
            sources=(support_source,),
            page_fetcher=discovery_page_fetcher,
        )

        # --- Batch enrichment with fresh counting fetchers ---
        page_fetcher = _DiscoveryPageFetcher(html_content)

        class _CountingPdfFetcher:
            def __init__(self):
                self.fetch_count = 0

            def fetch(self, request):
                self.fetch_count += 1
                with open(REAL_PDF_PATH, "rb") as f:
                    data = f.read()
                return FetchedDocument(
                    requested_url=request.url,
                    final_url=request.url,
                    retrieved_at=RETRIEVED_AT,
                    content_type="application/pdf",
                    body_bytes=data,
                    body_byte_count=len(data),
                    redirect_count=0,
                    fetcher_id="counting-pdf",
                )

        pdf_fetcher = _CountingPdfFetcher()

        results = enrich_enterprise_ssd_specifications_batch(
            identities=identities,
            discovery_result=discovery_result,
            page_fetcher=page_fetcher,
            document_fetcher=pdf_fetcher,
        )

        assert len(results) == 3

        # One support page fetch (3 identities, 1 unique source)
        assert page_fetcher.fetch_count == 1, (
            f"Expected 1 page fetch, got {page_fetcher.fetch_count}"
        )

        # One PDF fetch (3 identities share one PDF)
        assert pdf_fetcher.fetch_count == 1, (
            f"Expected 1 PDF fetch, got {pdf_fetcher.fetch_count}"
        )

        # All identities got enriched
        for result in results:
            assert result.enrichment_result is not None
            assert len(result.enrichment_result.raw_observations) == 6


# ---------------------------------------------------------------------------
# BLOCKER 1 — Authority Chain regression tests
# ---------------------------------------------------------------------------

class TestAuthorityChain:
    """BLOCKER 1: 7A -> 6D authority chain must be closed.

    Proves that:
    1. fake/duck-typed discovery result rejected before any fetch
    2. caller-created AUTHORITATIVE ComparableCandidateSource not present
       in the discovery result cannot establish a datasheet
    3. value-equal copied source descriptor is rejected
    4. non-EXTRACTED 7A source outcome cannot establish datasheet authority
    5. SECONDARY cannot establish authority
    6. arbitrary caller-provided DatasheetSource/PDF URL cannot enter the
       public authoritative enrichment path
    7. the real frozen 7A Seagate discovery result still derives the real
       datasheet successfully
    """

    def _build_discovery(self, html_content: str):
        """Build a real 7A ComparableCandidateDiscoveryResult."""
        from product_intelligence.execution.comparable_discovery import (
            discover_enterprise_ssd_comparable_candidates,
        )
        from product_intelligence.execution.specification_evidence import (
            research_enterprise_ssd_specifications,
            SpecificationEvidenceSource,
        )
        from product_intelligence.research.comparable_candidates import (
            ComparableCandidateSource,
        )

        target = _make_identity("XP15360SE70005")
        source = ComparableCandidateSource(
            source_name="Seagate Support",
            source_url="https://www.seagate.com/support/enterprise-storage/solid-state-drives/nytro-5050/",
            source_authority=SourceAuthority.AUTHORITATIVE,
        )

        class _PageFetcher:
            def __init__(self, content):
                self._content = content

            def fetch(self, request):
                from product_intelligence.providers.page import FetchedPage
                return FetchedPage(
                    requested_url=request.url,
                    final_url=request.url,
                    body_text=self._content,
                    content_type="text/html",
                    status_code=200,
                    retrieved_at=RETRIEVED_AT,
                )

        pf = _PageFetcher(html_content)
        six_c_src = SpecificationEvidenceSource(
            product_identity=target,
            source_name=source.source_name,
            source_url=source.source_url,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        six_c = research_enterprise_ssd_specifications(
            product_identity=target,
            sources=(six_c_src,),
            page_fetcher=pf,
        )
        return discover_enterprise_ssd_comparable_candidates(
            target_identity=target,
            target_specification_set=six_c.product_specification_set,
            sources=(source,),
            page_fetcher=pf,
        )

    def _make_page_fetcher(self, html_content: str):
        class _PageFetcher:
            def __init__(self, content):
                self._content = content

            def fetch(self, request):
                from product_intelligence.providers.page import FetchedPage
                return FetchedPage(
                    requested_url=request.url,
                    final_url=request.url,
                    body_text=self._content,
                    content_type="text/html",
                    status_code=200,
                    retrieved_at=RETRIEVED_AT,
                )
        return _PageFetcher(html_content)

    def test_fake_discovery_result_rejected_before_fetch(self) -> None:
        """A: fake/duck-typed discovery result rejected BEFORE any fetch."""
        from product_intelligence.execution.specification_enrichment import (
            enrich_enterprise_ssd_specifications_batch,
        )

        class FakeDiscoveryResult:
            source_outcomes = ()
            candidates = ()
            target_identity = _make_identity("XP15360SE70005")

        class _CountingFetcher:
            def __init__(self):
                self.fetch_count = 0
            def fetch(self, request):
                self.fetch_count += 1
                raise RuntimeError("should not be called")

        pf = _CountingFetcher()
        df = _CountingFetcher()

        with pytest.raises(TypeError, match="ComparableCandidateDiscoveryResult"):
            enrich_enterprise_ssd_specifications_batch(
                identities=(_make_identity("XP15360SE70005"),),
                discovery_result=FakeDiscoveryResult(),
                page_fetcher=pf,
                document_fetcher=df,
            )

        assert pf.fetch_count == 0
        assert df.fetch_count == 0

    def test_caller_created_source_not_in_discovery_rejected(self) -> None:
        """B: caller-created AUTHORITATIVE ComparableCandidateSource not in
        discovery result cannot establish a datasheet via the authority path."""
        from product_intelligence.execution.comparable_discovery import (
            ComparableCandidateSourceOutcome,
            ComparableCandidateSourceOutcomeState,
        )
        from product_intelligence.execution.specification_enrichment import (
            derive_datasheet_source_from_discovery,
        )
        from product_intelligence.research.comparable_candidates import (
            ComparableCandidateSource,
        )

        html_content = (
            Path(__file__).resolve().parents[2]
            / "tests" / "fixtures" / "specifications"
            / "real_seagate_nytro_5050_xp15360se70005.html"
        ).read_text(encoding="utf-8")

        discovery = self._build_discovery(html_content)

        extracted_outcome = None
        for o in discovery.source_outcomes:
            if o.outcome_state is ComparableCandidateSourceOutcomeState.EXTRACTED:
                extracted_outcome = o
                break
        assert extracted_outcome is not None

        caller_source = ComparableCandidateSource(
            source_name=extracted_outcome.source.source_name,
            source_url=extracted_outcome.source.source_url,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )

        fake_outcome = ComparableCandidateSourceOutcome(
            source=caller_source,
            final_url=extracted_outcome.final_url,
            retrieved_at=RETRIEVED_AT,
            outcome_state=ComparableCandidateSourceOutcomeState.EXTRACTED,
            observation_count=extracted_outcome.observation_count,
        )

        with pytest.raises(ValueError, match="not from the given discovery_result"):
            derive_datasheet_source_from_discovery(
                product_identity=_make_identity("XP15360SE70005"),
                discovery_result=discovery,
                source_outcome=fake_outcome,
                page_fetcher=self._make_page_fetcher(html_content),
            )

    def test_value_equal_copied_source_rejected(self) -> None:
        """C: value-equal copied source descriptor is rejected if exact
        source-object binding is required."""
        from product_intelligence.execution.comparable_discovery import (
            ComparableCandidateSourceOutcome,
            ComparableCandidateSourceOutcomeState,
        )
        from product_intelligence.execution.specification_enrichment import (
            derive_datasheet_source_from_discovery,
        )
        from product_intelligence.research.comparable_candidates import (
            ComparableCandidateSource,
        )

        html_content = (
            Path(__file__).resolve().parents[2]
            / "tests" / "fixtures" / "specifications"
            / "real_seagate_nytro_5050_xp15360se70005.html"
        ).read_text(encoding="utf-8")

        discovery = self._build_discovery(html_content)

        extracted_outcome = None
        for o in discovery.source_outcomes:
            if o.outcome_state is ComparableCandidateSourceOutcomeState.EXTRACTED:
                extracted_outcome = o
                break
        assert extracted_outcome is not None

        copied_source = ComparableCandidateSource(
            source_name=extracted_outcome.source.source_name,
            source_url=extracted_outcome.source.source_url,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        assert copied_source == extracted_outcome.source
        assert copied_source is not extracted_outcome.source

        fake_outcome = ComparableCandidateSourceOutcome(
            source=copied_source,
            final_url=extracted_outcome.final_url,
            retrieved_at=RETRIEVED_AT,
            outcome_state=ComparableCandidateSourceOutcomeState.EXTRACTED,
            observation_count=extracted_outcome.observation_count,
        )

        with pytest.raises(ValueError, match="not from the given discovery_result"):
            derive_datasheet_source_from_discovery(
                product_identity=_make_identity("XP15360SE70005"),
                discovery_result=discovery,
                source_outcome=fake_outcome,
                page_fetcher=self._make_page_fetcher(html_content),
            )

    def test_non_extracted_outcome_rejected(self) -> None:
        """D: non-EXTRACTED 7A source outcome cannot establish datasheet authority.

        Uses a REAL non-EXTRACTED outcome from a valid frozen 7A result
        (a second source that FETCH_FAILED).
        """
        from product_intelligence.execution.comparable_discovery import (
            ComparableCandidateSourceOutcome,
            ComparableCandidateSourceOutcomeState,
        )
        from product_intelligence.execution.specification_enrichment import (
            derive_datasheet_source_from_discovery,
        )
        from product_intelligence.execution.specification_evidence import (
            SpecificationEvidenceSource,
        )
        from product_intelligence.research.comparable_candidates import (
            ComparableCandidateSource,
        )

        html_content = (
            Path(__file__).resolve().parents[2]
            / "tests" / "fixtures" / "specifications"
            / "real_seagate_nytro_5050_xp15360se70005.html"
        ).read_text(encoding="utf-8")

        # Build a 7A result with TWO sources: one EXTRACTED (Seagate),
        # one FETCH_FAILED (bad source). This gives us a real non-EXTRACTED
        # outcome that is an ACTUAL member of the discovery result.
        from product_intelligence.execution.comparable_discovery import (
            discover_enterprise_ssd_comparable_candidates,
        )

        target = _make_identity("XP15360SE70005")
        good_source = ComparableCandidateSource(
            source_name="Seagate Support",
            source_url="https://www.seagate.com/support/enterprise-storage/solid-state-drives/nytro-5050/",
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        bad_source = ComparableCandidateSource(
            source_name="Bad Source",
            source_url="https://www.seagate.com/support/enterprise-storage/solid-state-drives/nytro-5050/",
            source_authority=SourceAuthority.AUTHORITATIVE,
        )

        class _TwoSourcePageFetcher:
            def __init__(self, content):
                self._content = content
                self._call_count = 0
            def fetch(self, request):
                from product_intelligence.providers.page import FetchedPage, PageFetchError
                self._call_count += 1
                if self._call_count == 1:
                    # First source (good) returns content
                    return FetchedPage(
                        requested_url=request.url,
                        final_url=request.url,
                        body_text=self._content,
                        content_type="text/html",
                        status_code=200,
                        retrieved_at=RETRIEVED_AT,
                    )
                else:
                    # Second source (bad) fails
                    raise PageFetchError("simulated failure")

        class _FilePageFetcher2:
            def __init__(self, content):
                self._content = content
            def fetch(self, request):
                from product_intelligence.providers.page import FetchedPage
                return FetchedPage(
                    requested_url=request.url,
                    final_url=request.url,
                    body_text=self._content,
                    content_type="text/html",
                    status_code=200,
                    retrieved_at=RETRIEVED_AT,
                )

        # 6C target evidence (for 7A discovery)
        pf_good = _FilePageFetcher2(html_content)
        six_c_src = SpecificationEvidenceSource(
            product_identity=target,
            source_name=good_source.source_name,
            source_url=good_source.source_url,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        from product_intelligence.execution.specification_evidence import (
            research_enterprise_ssd_specifications,
        )
        six_c = research_enterprise_ssd_specifications(
            product_identity=target,
            sources=(six_c_src,),
            page_fetcher=pf_good,
        )

        # 7A discovery with two sources -> one EXTRACTED, one FETCH_FAILED
        pf_two = _TwoSourcePageFetcher(html_content)
        discovery = discover_enterprise_ssd_comparable_candidates(
            target_identity=target,
            target_specification_set=six_c.product_specification_set,
            sources=(good_source, bad_source),
            page_fetcher=pf_two,
        )

        # Find the real non-EXTRACTED outcome (FETCH_FAILED)
        non_extracted_outcome = None
        for o in discovery.source_outcomes:
            if o.outcome_state is not ComparableCandidateSourceOutcomeState.EXTRACTED:
                non_extracted_outcome = o
                break
        assert non_extracted_outcome is not None, (
            "Expected a non-EXTRACTED outcome in the discovery result"
        )
        # Verify this is an ACTUAL member of the discovery result
        assert non_extracted_outcome in discovery.source_outcomes
        assert non_extracted_outcome.outcome_state is ComparableCandidateSourceOutcomeState.FETCH_FAILED

        # Now prove the EXTRACTED authority gate rejects it
        with pytest.raises(ValueError, match="must be EXTRACTED"):
            derive_datasheet_source_from_discovery(
                product_identity=_make_identity("XP15360SE70005"),
                discovery_result=discovery,
                source_outcome=non_extracted_outcome,
                page_fetcher=self._make_page_fetcher(html_content),
            )

    def test_secondary_source_rejected_by_datasheet_source(self) -> None:
        """E: SECONDARY authority cannot construct a DatasheetSource."""
        with pytest.raises(ValueError, match="AUTHORITATIVE"):
            DatasheetSource(
                product_identity=_make_identity("XP123"),
                source_name="Retailer Datasheet",
                source_url=SOURCE_URL,
                source_authority=SourceAuthority.SECONDARY,
            )

    def test_arbitrary_caller_datasheet_not_authority_path(self) -> None:
        """F: arbitrary caller-provided DatasheetSource/PDF URL cannot enter
        the public authoritative enrichment operation.

        Proves that even a valid AUTHORITATIVE DatasheetSource with an
        arbitrary URL cannot be passed into the public 6D enrichment
        function, because the public function requires a frozen 7A
        ComparableCandidateDiscoveryResult and an EXACT member outcome.
        """
        from product_intelligence.providers.document import (
            DocumentFetchRequest,
        )

        arbitrary_source = DatasheetSource(
            product_identity=_make_identity("XP15360SE70005"),
            source_name="Arbitrary Datasheet",
            source_url="https://arbitrary.example/datasheet.pdf",
            source_authority=SourceAuthority.AUTHORITATIVE,
        )

        class _CountingPdfFetcher:
            def __init__(self):
                self.fetch_count = 0
            def fetch(self, request: DocumentFetchRequest):
                self.fetch_count += 1
                raise RuntimeError("should not be called")

        df = _CountingPdfFetcher()

        # The public API requires discovery_result and source_outcome,
        # so a caller cannot pass arbitrary DatasheetSource objects.
        # Any attempt to use enrich_enterprise_ssd_specifications() without
        # a valid 7A discovery result is rejected at the type level.
        with pytest.raises(TypeError, match="ComparableCandidateDiscoveryResult"):
            enrich_enterprise_ssd_specifications(
                product_identity=_make_identity("XP15360SE70005"),
                discovery_result=None,  # type: ignore
                source_outcome=None,  # type: ignore
                page_fetcher=None,  # type: ignore
                document_fetcher=df,
            )

        # No PDF fetch attempted — arbitrary source rejected at API boundary
        assert df.fetch_count == 0

    def test_real_discovery_result_derivies_datasheet(self) -> None:
        """G: the real frozen 7A Seagate discovery result still derives the
        real datasheet successfully."""
        from product_intelligence.execution.comparable_discovery import (
            ComparableCandidateSourceOutcomeState,
        )
        from product_intelligence.execution.specification_enrichment import (
            derive_datasheet_source_from_discovery,
        )

        html_content = (
            Path(__file__).resolve().parents[2]
            / "tests" / "fixtures" / "specifications"
            / "real_seagate_nytro_5050_xp15360se70005.html"
        ).read_text(encoding="utf-8")

        discovery = self._build_discovery(html_content)
        page_fetcher = self._make_page_fetcher(html_content)

        extracted_outcome = None
        for o in discovery.source_outcomes:
            if o.outcome_state is ComparableCandidateSourceOutcomeState.EXTRACTED:
                extracted_outcome = o
                break
        assert extracted_outcome is not None

        datasheet_source = derive_datasheet_source_from_discovery(
            product_identity=_make_identity("XP15360SE70005"),
            discovery_result=discovery,
            source_outcome=extracted_outcome,
            page_fetcher=page_fetcher,
        )

        assert datasheet_source is not None
        assert datasheet_source.source_authority is SourceAuthority.AUTHORITATIVE
        assert "nytro-5550" in datasheet_source.source_url
        assert "pdf" in datasheet_source.source_url


# ---------------------------------------------------------------------------
# Abstention-path regression tests
# ---------------------------------------------------------------------------

class TestAbstentionPaths:
    """Abstention paths must return valid empty SpecificationEnrichmentResult,
    not ValueError from DatasheetSourceOutcome invariant violation.

    When derive_datasheet_source_from_discovery() returns None:
        source_outcomes == ()
        raw_observations == ()
        normalized_observations == ()
        all 12 resolutions UNKNOWN
    """

    def _build_discovery(self, html_content: str):
        """Build a real 7A ComparableCandidateDiscoveryResult."""
        from product_intelligence.execution.comparable_discovery import (
            discover_enterprise_ssd_comparable_candidates,
        )
        from product_intelligence.execution.specification_evidence import (
            research_enterprise_ssd_specifications,
            SpecificationEvidenceSource,
        )
        from product_intelligence.research.comparable_candidates import (
            ComparableCandidateSource,
        )

        target = _make_identity("XP15360SE70005")
        source = ComparableCandidateSource(
            source_name="Seagate Support",
            source_url="https://www.seagate.com/support/enterprise-storage/solid-state-drives/nytro-5050/",
            source_authority=SourceAuthority.AUTHORITATIVE,
        )

        class _PageFetcher:
            def __init__(self, content):
                self._content = content

            def fetch(self, request):
                from product_intelligence.providers.page import FetchedPage
                return FetchedPage(
                    requested_url=request.url,
                    final_url=request.url,
                    body_text=self._content,
                    content_type="text/html",
                    status_code=200,
                    retrieved_at=RETRIEVED_AT,
                )

        pf = _PageFetcher(html_content)
        six_c_src = SpecificationEvidenceSource(
            product_identity=target,
            source_name=source.source_name,
            source_url=source.source_url,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        six_c = research_enterprise_ssd_specifications(
            product_identity=target,
            sources=(six_c_src,),
            page_fetcher=pf,
        )
        return discover_enterprise_ssd_comparable_candidates(
            target_identity=target,
            target_specification_set=six_c.product_specification_set,
            sources=(source,),
            page_fetcher=pf,
        )

    def test_page_fetch_error_returns_empty_result(self) -> None:
        """A: Public authority path + support-page PageFetchError.

        Valid frozen 7A discovery result + EXTRACTED outcome + page fetcher
        that raises PageFetchError -> valid empty SpecificationEnrichmentResult.
        """
        from product_intelligence.execution.comparable_discovery import (
            ComparableCandidateSourceOutcomeState,
        )
        from product_intelligence.providers.page import PageFetchError

        html_content = (
            Path(__file__).resolve().parents[2]
            / "tests" / "fixtures" / "specifications"
            / "real_seagate_nytro_5050_xp15360se70005.html"
        ).read_text(encoding="utf-8")

        discovery = self._build_discovery(html_content)

        extracted_outcome = None
        for o in discovery.source_outcomes:
            if o.outcome_state is ComparableCandidateSourceOutcomeState.EXTRACTED:
                extracted_outcome = o
                break
        assert extracted_outcome is not None

        # Page fetcher that always fails
        class _FailingPageFetcher:
            def fetch(self, request):
                raise PageFetchError("simulated network failure")

        # Document fetcher that must NOT be called
        class _CountingPdfFetcher:
            def __init__(self):
                self.fetch_count = 0
            def fetch(self, request):
                self.fetch_count += 1
                raise RuntimeError("should not be called")

        df = _CountingPdfFetcher()

        result = enrich_enterprise_ssd_specifications(
            product_identity=_make_identity("XP15360SE70005"),
            discovery_result=discovery,
            source_outcome=extracted_outcome,
            page_fetcher=_FailingPageFetcher(),
            document_fetcher=df,
        )

        # Valid empty result — NOT ValueError
        assert result.product_identity.is_established
        assert result.source_outcomes == ()
        assert result.raw_observations == ()
        assert result.normalized_observations == ()
        assert df.fetch_count == 0
        # All 12 resolutions UNKNOWN
        for key in ENTERPRISE_SSD_SCHEMA.definitions:
            assert (
                result.product_specification_set.resolutions[key].state
                == ResolutionState.UNKNOWN
            )

    def test_no_matching_datasheet_returns_empty_result(self) -> None:
        """B: Public authority path + support page fetched but no matching
        skuNumber -> valid empty result.

        Uses a valid 7A discovery but a page fetcher that returns HTML with
        NO supportSpecsData JSON (so no datasheet link can be extracted).
        """
        from product_intelligence.execution.comparable_discovery import (
            ComparableCandidateSourceOutcomeState,
        )
        from product_intelligence.providers.page import FetchedPage

        discovery = self._build_discovery(
            (
                Path(__file__).resolve().parents[2]
                / "tests" / "fixtures" / "specifications"
                / "real_seagate_nytro_5050_xp15360se70005.html"
            ).read_text(encoding="utf-8")
        )

        extracted_outcome = None
        for o in discovery.source_outcomes:
            if o.outcome_state is ComparableCandidateSourceOutcomeState.EXTRACTED:
                extracted_outcome = o
                break
        assert extracted_outcome is not None

        # Page fetcher returns HTML with no supportSpecsData
        class _EmptyPageFetcher:
            def fetch(self, request):
                return FetchedPage(
                    requested_url=request.url,
                    final_url=request.url,
                    body_text="<html><body>No supportSpecsData here</body></html>",
                    content_type="text/html",
                    status_code=200,
                    retrieved_at=RETRIEVED_AT,
                )

        class _CountingPdfFetcher:
            def __init__(self):
                self.fetch_count = 0
            def fetch(self, request):
                self.fetch_count += 1
                raise RuntimeError("should not be called")

        df = _CountingPdfFetcher()

        result = enrich_enterprise_ssd_specifications(
            product_identity=_make_identity("XP15360SE70005"),
            discovery_result=discovery,
            source_outcome=extracted_outcome,
            page_fetcher=_EmptyPageFetcher(),
            document_fetcher=df,
        )

        # Valid empty result
        assert result.source_outcomes == ()
        assert result.raw_observations == ()
        assert result.normalized_observations == ()
        assert df.fetch_count == 0
        for key in ENTERPRISE_SSD_SCHEMA.definitions:
            assert (
                result.product_specification_set.resolutions[key].state
                == ResolutionState.UNKNOWN
            )

    def test_fetched_datasheet_no_observations(self, monkeypatch) -> None:
        """C: Successfully derived and fetched datasheet but no extracted
        observations -> NO_OBSERVATIONS outcome with final_url + retrieved_at.

        Monkeypatches the datasheet extractor to return zero observations,
        exercising the path: valid PDF fetch -> valid parse -> zero
        extraction results -> NO_OBSERVATIONS.
        """
        import pdfplumber

        class _ValidEmptyPdf:
            """A fake pdfplumber PDF that opens and has pages with tables,
            but the extractor is monkeypatched to return zero observations."""
            @property
            def pages(self):
                class _FakePage:
                    def extract_tables(self):
                        # Valid tables — the extractor decides they have no MPN
                        return [[
                            ["Field", "Value"],
                            ["Something", "Else"],
                        ]]
                return [_FakePage()]

            def close(self):
                pass

        monkeypatch.setattr(
            pdfplumber, "open",
            lambda *a, **k: _ValidEmptyPdf(),
        )

        # Monkeypatch extractor to return empty observations
        monkeypatch.setattr(
            "product_intelligence.execution.specification_enrichment.extract_datasheet_observations_from_document",
            lambda *a, **k: [],
        )

        identity = _make_identity("XP15360SE70005")
        source = DatasheetSource(
            product_identity=identity,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        fetcher = _FilePdfFetcher(REAL_PDF_PATH, SOURCE_URL)

        result = _enrich_from_datasheet_sources_internal(
            product_identity=identity,
            sources=(source,),
            document_fetcher=fetcher,
        )

        # NO_OBSERVATIONS outcome — NOT abstention (datasheet was fetched)
        assert len(result.source_outcomes) == 1
        outcome = result.source_outcomes[0]
        assert outcome.outcome_state is DatasheetOutcomeState.NO_OBSERVATIONS
        # NO_OBSERVATIONS requires final_url + retrieved_at present
        assert outcome.final_url is not None
        assert outcome.retrieved_at is not None
        assert outcome.observation_count == 0
        # Zero observations
        assert result.raw_observations == ()
        assert result.normalized_observations == ()
        # All 12 resolutions UNKNOWN
        for key in ENTERPRISE_SSD_SCHEMA.definitions:
            assert (
                result.product_specification_set.resolutions[key].state
                == ResolutionState.UNKNOWN
            )


# ---------------------------------------------------------------------------
# BLOCKER 2 — Dedup Support-Page Fetches regression
# ---------------------------------------------------------------------------

class TestBatchDeduplication:
    """BLOCKER 2: Support page fetches must be deduplicated BEFORE fetching."""

    def test_duplicate_sources_fetched_once(self) -> None:
        """Two EXTRACTED outcomes with identical source descriptors
        (same name, URL, authority) -> exactly one page_fetcher.fetch() call.

        Creates two ComparableCandidateSource objects with identical values.
        Both are passed to 7A discovery, producing two EXTRACTED outcomes.
        The batch handler deduplicates by source descriptor value equality
        and fetches the support page only once.
        """
        from product_intelligence.execution.comparable_discovery import (
            ComparableCandidateSourceOutcomeState,
            discover_enterprise_ssd_comparable_candidates,
        )
        from product_intelligence.execution.specification_enrichment import (
            enrich_enterprise_ssd_specifications_batch,
        )
        from product_intelligence.execution.specification_evidence import (
            research_enterprise_ssd_specifications,
            SpecificationEvidenceSource,
        )
        from product_intelligence.research.comparable_candidates import (
            ComparableCandidateSource,
        )

        html_content = (
            Path(__file__).resolve().parents[2]
            / "tests" / "fixtures" / "specifications"
            / "real_seagate_nytro_5050_xp15360se70005.html"
        ).read_text(encoding="utf-8")

        target = _make_identity("XP15360SE70005")
        # Two sources with IDENTICAL values (name, URL, authority)
        source1 = ComparableCandidateSource(
            source_name="Seagate Support",
            source_url="https://www.seagate.com/support/enterprise-storage/solid-state-drives/nytro-5050/",
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        source2 = ComparableCandidateSource(
            source_name="Seagate Support",
            source_url="https://www.seagate.com/support/enterprise-storage/solid-state-drives/nytro-5050/",
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        assert source1 == source2  # value-equal
        assert source1 is not source2  # different objects

        class _PageFetcher:
            def __init__(self, content):
                self._content = content
            def fetch(self, request):
                from product_intelligence.providers.page import FetchedPage
                return FetchedPage(
                    requested_url=request.url,
                    final_url=request.url,
                    body_text=self._content,
                    content_type="text/html",
                    status_code=200,
                    retrieved_at=RETRIEVED_AT,
                )

        pf = _PageFetcher(html_content)
        six_c_src = SpecificationEvidenceSource(
            product_identity=target,
            source_name="Seagate Support",
            source_url="https://www.seagate.com/support/enterprise-storage/solid-state-drives/nytro-5050/",
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        six_c = research_enterprise_ssd_specifications(
            product_identity=target,
            sources=(six_c_src,),
            page_fetcher=pf,
        )

        # 7A discovery with two identical sources
        # Both produce EXTRACTED outcomes -> two outcomes in the result
        discovery = discover_enterprise_ssd_comparable_candidates(
            target_identity=target,
            target_specification_set=six_c.product_specification_set,
            sources=(source1, source2),
            page_fetcher=pf,
        )

        # Verify we have two EXTRACTED outcomes with identical source descriptors
        extracted_outcomes = [
            o for o in discovery.source_outcomes
            if o.outcome_state is ComparableCandidateSourceOutcomeState.EXTRACTED
        ]
        assert len(extracted_outcomes) == 2, (
            f"Expected 2 EXTRACTED outcomes from duplicate sources, "
            f"got {len(extracted_outcomes)}"
        )
        # Both outcomes reference value-equal source descriptors
        assert extracted_outcomes[0].source == extracted_outcomes[1].source

        # --- Run batch with counting fetchers ---
        class _CountingPageFetcher:
            def __init__(self, content):
                self._content = content
                self.fetch_count = 0
            def fetch(self, request):
                from product_intelligence.providers.page import FetchedPage
                self.fetch_count += 1
                return FetchedPage(
                    requested_url=request.url,
                    final_url=request.url,
                    body_text=self._content,
                    content_type="text/html",
                    status_code=200,
                    retrieved_at=RETRIEVED_AT,
                )

        batch_page_fetcher = _CountingPageFetcher(html_content)

        class _CountingPdfFetcher:
            def __init__(self):
                self.fetch_count = 0
            def fetch(self, request):
                self.fetch_count += 1
                with open(REAL_PDF_PATH, "rb") as f:
                    data = f.read()
                return FetchedDocument(
                    requested_url=request.url,
                    final_url=request.url,
                    retrieved_at=RETRIEVED_AT,
                    content_type="application/pdf",
                    body_bytes=data,
                    body_byte_count=len(data),
                    redirect_count=0,
                    fetcher_id="counting-pdf",
                )

        pdf_fetcher = _CountingPdfFetcher()

        identities = tuple([
            _make_identity("XP15360SE70005"),
            _make_identity("XP15360SE70015"),
            _make_identity("XP3840SE70005"),
        ])

        results = enrich_enterprise_ssd_specifications_batch(
            identities=identities,
            discovery_result=discovery,
            page_fetcher=batch_page_fetcher,
            document_fetcher=pdf_fetcher,
        )

        assert len(results) == 3
        # Two EXTRACTED outcomes with identical source descriptors -> ONE page fetch
        assert batch_page_fetcher.fetch_count == 1, (
            f"Expected 1 page fetch (duplicate source dedup), "
            f"got {batch_page_fetcher.fetch_count}"
        )
        assert pdf_fetcher.fetch_count == 1, (
            f"Expected 1 PDF fetch, got {pdf_fetcher.fetch_count}"
        )
        for r in results:
            assert r.enrichment_result is not None
            assert len(r.enrichment_result.raw_observations) == 6


# ---------------------------------------------------------------------------
# BLOCKER 3 — Batch Parser Fail-Closed regression
# ---------------------------------------------------------------------------

class TestBatchParserFailClosed:
    """BLOCKER 3: Parser failure must fail CLOSED in batch.

    On parser exception: discard ALL tables, PARSE_FAILED, zero observations.
    RuntimeError propagates.
    """

    def _build_discovery_for_batch(self, html_content: str):
        """Build discovery result."""
        from product_intelligence.execution.comparable_discovery import (
            discover_enterprise_ssd_comparable_candidates,
        )
        from product_intelligence.execution.specification_evidence import (
            research_enterprise_ssd_specifications,
            SpecificationEvidenceSource,
        )
        from product_intelligence.research.comparable_candidates import (
            ComparableCandidateSource,
        )

        target = _make_identity("XP15360SE70005")
        source = ComparableCandidateSource(
            source_name="Seagate Support",
            source_url="https://www.seagate.com/support/enterprise-storage/solid-state-drives/nytro-5050/",
            source_authority=SourceAuthority.AUTHORITATIVE,
        )

        class _PageFetcher:
            def __init__(self, content):
                self._content = content
            def fetch(self, request):
                from product_intelligence.providers.page import FetchedPage
                return FetchedPage(
                    requested_url=request.url,
                    final_url=request.url,
                    body_text=self._content,
                    content_type="text/html",
                    status_code=200,
                    retrieved_at=RETRIEVED_AT,
                )

        pf = _PageFetcher(html_content)
        six_c_src = SpecificationEvidenceSource(
            product_identity=target,
            source_name=source.source_name,
            source_url=source.source_url,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        six_c = research_enterprise_ssd_specifications(
            product_identity=target,
            sources=(six_c_src,),
            page_fetcher=pf,
        )
        return discover_enterprise_ssd_comparable_candidates(
            target_identity=target,
            target_specification_set=six_c.product_specification_set,
            sources=(source,),
            page_fetcher=pf,
        )

    def test_pdfplumber_open_pdfsyntax_error_batch_parse_failed(self, monkeypatch) -> None:
        """A: pdfplumber.open PDFSyntaxError -> batch PARSE_FAILED."""
        from pdfminer.pdfparser import PDFSyntaxError
        import pdfplumber
        from product_intelligence.execution.specification_enrichment import (
            enrich_enterprise_ssd_specifications_batch,
        )

        html_content = (
            Path(__file__).resolve().parents[2]
            / "tests" / "fixtures" / "specifications"
            / "real_seagate_nytro_5050_xp15360se70005.html"
        ).read_text(encoding="utf-8")

        discovery = self._build_discovery_for_batch(html_content)

        class _PageFetcher:
            def __init__(self, content):
                self._content = content
            def fetch(self, request):
                from product_intelligence.providers.page import FetchedPage
                return FetchedPage(
                    requested_url=request.url,
                    final_url=request.url,
                    body_text=self._content,
                    content_type="text/html",
                    status_code=200,
                    retrieved_at=RETRIEVED_AT,
                )

        class _PdfFetcher:
            def fetch(self, request):
                with open(REAL_PDF_PATH, "rb") as f:
                    data = f.read()
                return FetchedDocument(
                    requested_url=request.url,
                    final_url=request.url,
                    retrieved_at=RETRIEVED_AT,
                    content_type="application/pdf",
                    body_bytes=data,
                    body_byte_count=len(data),
                    redirect_count=0,
                    fetcher_id="test-pdf",
                )

        monkeypatch.setattr(
            pdfplumber, "open",
            lambda *a, **k: (_ for _ in ()).throw(PDFSyntaxError("fake syntax")),
        )

        identities = (_make_identity("XP15360SE70005"),)
        results = enrich_enterprise_ssd_specifications_batch(
            identities=identities,
            discovery_result=discovery,
            page_fetcher=_PageFetcher(html_content),
            document_fetcher=_PdfFetcher(),
        )

        assert len(results) == 1
        assert results[0].enrichment_result is not None
        outcome = results[0].enrichment_result.source_outcomes[0]
        assert outcome.outcome_state is DatasheetOutcomeState.PARSE_FAILED
        assert outcome.observation_count == 0
        assert results[0].enrichment_result.raw_observations == ()

    def test_page_extract_tables_pdfsyntax_error_batch_parse_failed(
        self, monkeypatch
    ) -> None:
        """B: page.extract_tables PDFSyntaxError on first page -> batch PARSE_FAILED."""
        from pdfminer.pdfparser import PDFSyntaxError
        import pdfplumber
        from product_intelligence.execution.specification_enrichment import (
            enrich_enterprise_ssd_specifications_batch,
        )

        html_content = (
            Path(__file__).resolve().parents[2]
            / "tests" / "fixtures" / "specifications"
            / "real_seagate_nytro_5050_xp15360se70005.html"
        ).read_text(encoding="utf-8")

        discovery = self._build_discovery_for_batch(html_content)

        class _PageFetcher:
            def __init__(self, content):
                self._content = content
            def fetch(self, request):
                from product_intelligence.providers.page import FetchedPage
                return FetchedPage(
                    requested_url=request.url,
                    final_url=request.url,
                    body_text=self._content,
                    content_type="text/html",
                    status_code=200,
                    retrieved_at=RETRIEVED_AT,
                )

        class _PdfFetcher:
            def fetch(self, request):
                with open(REAL_PDF_PATH, "rb") as f:
                    data = f.read()
                return FetchedDocument(
                    requested_url=request.url,
                    final_url=request.url,
                    retrieved_at=RETRIEVED_AT,
                    content_type="application/pdf",
                    body_bytes=data,
                    body_byte_count=len(data),
                    redirect_count=0,
                    fetcher_id="test-pdf",
                )

        class _FakePdf:
            @property
            def pages(self):
                class _FakePage:
                    def extract_tables(self):
                        raise PDFSyntaxError("fake table parse error")
                return [_FakePage()]

            def close(self):
                pass

        monkeypatch.setattr(pdfplumber, "open", lambda *a, **k: _FakePdf())

        identities = (_make_identity("XP15360SE70005"),)
        results = enrich_enterprise_ssd_specifications_batch(
            identities=identities,
            discovery_result=discovery,
            page_fetcher=_PageFetcher(html_content),
            document_fetcher=_PdfFetcher(),
        )

        assert results[0].enrichment_result is not None
        outcome = results[0].enrichment_result.source_outcomes[0]
        assert outcome.outcome_state is DatasheetOutcomeState.PARSE_FAILED
        assert results[0].enrichment_result.raw_observations == ()

    def test_parser_exception_after_valid_tables_batch_parse_failed(
        self, monkeypatch
    ) -> None:
        """C: parser exception AFTER an earlier page produced valid tables
        -> batch PARSE_FAILED with ZERO raw observations (no partial evidence)."""
        from pdfminer.pdfparser import PDFSyntaxError
        import pdfplumber
        from product_intelligence.execution.specification_enrichment import (
            enrich_enterprise_ssd_specifications_batch,
        )

        html_content = (
            Path(__file__).resolve().parents[2]
            / "tests" / "fixtures" / "specifications"
            / "real_seagate_nytro_5050_xp15360se70005.html"
        ).read_text(encoding="utf-8")

        discovery = self._build_discovery_for_batch(html_content)

        class _PageFetcher:
            def __init__(self, content):
                self._content = content
            def fetch(self, request):
                from product_intelligence.providers.page import FetchedPage
                return FetchedPage(
                    requested_url=request.url,
                    final_url=request.url,
                    body_text=self._content,
                    content_type="text/html",
                    status_code=200,
                    retrieved_at=RETRIEVED_AT,
                )

        class _PdfFetcher:
            def fetch(self, request):
                with open(REAL_PDF_PATH, "rb") as f:
                    data = f.read()
                return FetchedDocument(
                    requested_url=request.url,
                    final_url=request.url,
                    retrieved_at=RETRIEVED_AT,
                    content_type="application/pdf",
                    body_bytes=data,
                    body_byte_count=len(data),
                    redirect_count=0,
                    fetcher_id="test-pdf",
                )

        class _FakePdf:
            def __init__(self):
                self._page = 0

            @property
            def pages(self):
                return self

            def __iter__(self):
                self._page = 0
                return self

            def __next__(self):
                if self._page == 0:
                    self._page = 1
                    return _ValidPage()
                elif self._page == 1:
                    self._page = 2
                    return _ErrorPage()
                else:
                    raise StopIteration

            def close(self):
                pass

        class _ValidPage:
            def extract_tables(self):
                return [[
                    ["Standard Model", "XP15360SE70005"],
                    ["Capacity", "1TB"],
                ]]

        class _ErrorPage:
            def extract_tables(self):
                raise PDFSyntaxError("error on page 2")

        monkeypatch.setattr(pdfplumber, "open", lambda *a, **k: _FakePdf())

        identities = (_make_identity("XP15360SE70005"),)
        results = enrich_enterprise_ssd_specifications_batch(
            identities=identities,
            discovery_result=discovery,
            page_fetcher=_PageFetcher(html_content),
            document_fetcher=_PdfFetcher(),
        )

        assert results[0].enrichment_result is not None
        outcome = results[0].enrichment_result.source_outcomes[0]
        assert outcome.outcome_state is DatasheetOutcomeState.PARSE_FAILED
        assert outcome.observation_count == 0
        assert results[0].enrichment_result.raw_observations == ()

    def test_runtimeerror_from_pdfplumber_open_propagates(
        self, monkeypatch
    ) -> None:
        """D: RuntimeError from pdfplumber.open propagates."""
        import pdfplumber
        from product_intelligence.execution.specification_enrichment import (
            enrich_enterprise_ssd_specifications_batch,
        )

        html_content = (
            Path(__file__).resolve().parents[2]
            / "tests" / "fixtures" / "specifications"
            / "real_seagate_nytro_5050_xp15360se70005.html"
        ).read_text(encoding="utf-8")

        discovery = self._build_discovery_for_batch(html_content)

        class _PageFetcher:
            def __init__(self, content):
                self._content = content
            def fetch(self, request):
                from product_intelligence.providers.page import FetchedPage
                return FetchedPage(
                    requested_url=request.url,
                    final_url=request.url,
                    body_text=self._content,
                    content_type="text/html",
                    status_code=200,
                    retrieved_at=RETRIEVED_AT,
                )

        class _PdfFetcher:
            def fetch(self, request):
                with open(REAL_PDF_PATH, "rb") as f:
                    data = f.read()
                return FetchedDocument(
                    requested_url=request.url,
                    final_url=request.url,
                    retrieved_at=RETRIEVED_AT,
                    content_type="application/pdf",
                    body_bytes=data,
                    body_byte_count=len(data),
                    redirect_count=0,
                    fetcher_id="test-pdf",
                )

        monkeypatch.setattr(
            pdfplumber, "open",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("programming error")),
        )

        with pytest.raises(RuntimeError, match="programming error"):
            enrich_enterprise_ssd_specifications_batch(
                identities=(_make_identity("XP15360SE70005"),),
                discovery_result=discovery,
                page_fetcher=_PageFetcher(html_content),
                document_fetcher=_PdfFetcher(),
            )

    def test_runtimeerror_from_extract_tables_propagates(self, monkeypatch) -> None:
        """E: RuntimeError from page.extract_tables propagates."""
        import pdfplumber
        from product_intelligence.execution.specification_enrichment import (
            enrich_enterprise_ssd_specifications_batch,
        )

        html_content = (
            Path(__file__).resolve().parents[2]
            / "tests" / "fixtures" / "specifications"
            / "real_seagate_nytro_5050_xp15360se70005.html"
        ).read_text(encoding="utf-8")

        discovery = self._build_discovery_for_batch(html_content)

        class _PageFetcher:
            def __init__(self, content):
                self._content = content
            def fetch(self, request):
                from product_intelligence.providers.page import FetchedPage
                return FetchedPage(
                    requested_url=request.url,
                    final_url=request.url,
                    body_text=self._content,
                    content_type="text/html",
                    status_code=200,
                    retrieved_at=RETRIEVED_AT,
                )

        class _PdfFetcher:
            def fetch(self, request):
                with open(REAL_PDF_PATH, "rb") as f:
                    data = f.read()
                return FetchedDocument(
                    requested_url=request.url,
                    final_url=request.url,
                    retrieved_at=RETRIEVED_AT,
                    content_type="application/pdf",
                    body_bytes=data,
                    body_byte_count=len(data),
                    redirect_count=0,
                    fetcher_id="test-pdf",
                )

        class _FakePdf:
            @property
            def pages(self):
                class _FakePage:
                    def extract_tables(self):
                        raise RuntimeError("programming error in extract_tables")
                return [_FakePage()]

            def close(self):
                pass

        monkeypatch.setattr(pdfplumber, "open", lambda *a, **k: _FakePdf())

        with pytest.raises(RuntimeError, match="programming error in extract_tables"):
            enrich_enterprise_ssd_specifications_batch(
                identities=(_make_identity("XP15360SE70005"),),
                discovery_result=discovery,
                page_fetcher=_PageFetcher(html_content),
                document_fetcher=_PdfFetcher(),
            )


# ---------------------------------------------------------------------------
# BLOCKER 4 — SOURCE_REFUSED vs FETCH_FAILED in batch
# ---------------------------------------------------------------------------

class TestBatchSourceRefusedVsFetchFailed:
    """BLOCKER 4: Preserve SOURCE_REFUSED vs FETCH_FAILED in batch outcomes."""

    def _build_discovery_for_batch(self, html_content: str):
        """Build discovery result."""
        from product_intelligence.execution.comparable_discovery import (
            discover_enterprise_ssd_comparable_candidates,
        )
        from product_intelligence.execution.specification_evidence import (
            research_enterprise_ssd_specifications,
            SpecificationEvidenceSource,
        )
        from product_intelligence.research.comparable_candidates import (
            ComparableCandidateSource,
        )

        target = _make_identity("XP15360SE70005")
        source = ComparableCandidateSource(
            source_name="Seagate Support",
            source_url="https://www.seagate.com/support/enterprise-storage/solid-state-drives/nytro-5050/",
            source_authority=SourceAuthority.AUTHORITATIVE,
        )

        class _PageFetcher:
            def __init__(self, content):
                self._content = content
            def fetch(self, request):
                from product_intelligence.providers.page import FetchedPage
                return FetchedPage(
                    requested_url=request.url,
                    final_url=request.url,
                    body_text=self._content,
                    content_type="text/html",
                    status_code=200,
                    retrieved_at=RETRIEVED_AT,
                )

        pf = _PageFetcher(html_content)
        six_c_src = SpecificationEvidenceSource(
            product_identity=target,
            source_name=source.source_name,
            source_url=source.source_url,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        six_c = research_enterprise_ssd_specifications(
            product_identity=target,
            sources=(six_c_src,),
            page_fetcher=pf,
        )
        return discover_enterprise_ssd_comparable_candidates(
            target_identity=target,
            target_specification_set=six_c.product_specification_set,
            sources=(source,),
            page_fetcher=pf,
        )

    def test_unsafe_document_target_produces_source_refused(self) -> None:
        """UnsafeDocumentTargetError -> SOURCE_REFUSED."""
        from product_intelligence.execution.specification_enrichment import (
            enrich_enterprise_ssd_specifications_batch,
        )

        html_content = (
            Path(__file__).resolve().parents[2]
            / "tests" / "fixtures" / "specifications"
            / "real_seagate_nytro_5050_xp15360se70005.html"
        ).read_text(encoding="utf-8")

        discovery = self._build_discovery_for_batch(html_content)

        class _PageFetcher:
            def __init__(self, content):
                self._content = content
            def fetch(self, request):
                from product_intelligence.providers.page import FetchedPage
                return FetchedPage(
                    requested_url=request.url,
                    final_url=request.url,
                    body_text=self._content,
                    content_type="text/html",
                    status_code=200,
                    retrieved_at=RETRIEVED_AT,
                )

        class _RefusedPdfFetcher:
            def fetch(self, request):
                raise UnsafeDocumentTargetError("unsafe target")

        results = enrich_enterprise_ssd_specifications_batch(
            identities=(_make_identity("XP15360SE70005"),),
            discovery_result=discovery,
            page_fetcher=_PageFetcher(html_content),
            document_fetcher=_RefusedPdfFetcher(),
        )

        assert results[0].enrichment_result is not None
        outcome = results[0].enrichment_result.source_outcomes[0]
        assert outcome.outcome_state is DatasheetOutcomeState.SOURCE_REFUSED
        assert outcome.final_url is None
        assert outcome.retrieved_at is None
        assert outcome.observation_count == 0

    def test_document_fetch_error_produces_fetch_failed(self) -> None:
        """DocumentFetchError -> FETCH_FAILED."""
        from product_intelligence.execution.specification_enrichment import (
            enrich_enterprise_ssd_specifications_batch,
        )

        html_content = (
            Path(__file__).resolve().parents[2]
            / "tests" / "fixtures" / "specifications"
            / "real_seagate_nytro_5050_xp15360se70005.html"
        ).read_text(encoding="utf-8")

        discovery = self._build_discovery_for_batch(html_content)

        class _PageFetcher:
            def __init__(self, content):
                self._content = content
            def fetch(self, request):
                from product_intelligence.providers.page import FetchedPage
                return FetchedPage(
                    requested_url=request.url,
                    final_url=request.url,
                    body_text=self._content,
                    content_type="text/html",
                    status_code=200,
                    retrieved_at=RETRIEVED_AT,
                )

        class _FailedPdfFetcher:
            def fetch(self, request):
                raise DocumentFetchError("network error")

        results = enrich_enterprise_ssd_specifications_batch(
            identities=(_make_identity("XP15360SE70005"),),
            discovery_result=discovery,
            page_fetcher=_PageFetcher(html_content),
            document_fetcher=_FailedPdfFetcher(),
        )

        assert results[0].enrichment_result is not None
        outcome = results[0].enrichment_result.source_outcomes[0]
        assert outcome.outcome_state is DatasheetOutcomeState.FETCH_FAILED
        assert outcome.final_url is None
        assert outcome.retrieved_at is None
        assert outcome.observation_count == 0
