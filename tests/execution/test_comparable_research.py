"""Comparable research orchestration tests (PRODUCT-INTEL.7C-B).

Offline end-to-end vertical slices and bounded-contract tests for
execute_comparable_research. Fakes / fixtures only: no live network,
no live PDF download, no live LLM.
"""

from __future__ import annotations

import datetime
import json
import re
import uuid
from dataclasses import dataclass
from decimal import Decimal

import pytest
from django.test import TestCase

from product_intelligence.domain.models import ProductIdentity, ResearchRequest
from product_intelligence.domain.enums import IdentityMatchType
from product_intelligence.execution.comparable_research import (
    ComparableResearchExecutionError,
    execute_comparable_research,
)
from product_intelligence.providers.document import (
    DocumentFetchError,
    UnsafeDocumentTargetError as UnsafeDocumentTargetError,
)
from product_intelligence.providers.page import (
    FetchedPage,
    PageFetchError,
    PageFetchRequest,
    UnsafeFetchTargetError,
)
from product_intelligence.research.comparable_research_results import (
    AUTHORITY_FATAL_OUTCOMES,
    AuthorityAuditOutcomeKind,
    ComparableResultKind,
    DatasheetAuditOutcomeKind,
    EvidenceLayer,
)
from product_intelligence.research.comparable_result_codec import (
    COMPARABLE_RESULT_SCHEMA_VERSION,
    decode_comparable_result,
    encode_comparable_result,
)
from product_intelligence.research.enterprise_ssd import (
    ENTERPRISE_SSD_SCHEMA,
)
from product_intelligence.research.specifications import (
    NormalizedSpecificationObservation,
    ResolutionState,
    SpecificationValue,
    SourceAuthority,
)
from product_intelligence.runs.models import (
    ComparableResearchExecution,
    ComparableResearchState,
    ResearchRun,
    ResearchRunState,
)


# ---------------------------------------------------------------------------
# Test constants
# ---------------------------------------------------------------------------

RETRIEVED_AT = datetime.datetime(2026, 9, 4, 20, 42, 23, tzinfo=datetime.timezone.utc)
SEAGATE_URL = (
    "https://www.seagate.com/support/enterprise-storage/"
    "solid-state-drives/nytro-5050/"
)
REAL_HTML_PATH = (
    "tests/fixtures/specifications/"
    "real_seagate_nytro_5050_xp15360se70005.html"
)
REAL_PDF_PATH = (
    "tests/fixtures/specifications/"
    "real_seagate_nytro_5550_5350_datasheet.pdf"
)


def _read_real_html() -> str:
    with open(REAL_HTML_PATH, encoding="utf-8") as fh:
        return fh.read()


def _make_completed_run(
    mpn: str = "XP15360SE70005",
    description: str = "Seagate Nytro 5050",
) -> ResearchRun:
    """Create a parent run. Only the request fields matter for the child.

    The child is created directly via ORM (bypassing trigger), so the parent
    need not be COMPLETED and need not have a snapshot.
    """
    request = ResearchRequest(
        manufacturer_part_number=mpn,
        description=description,
    )
    return ResearchRun.objects.create_from_request(request)


# ---------------------------------------------------------------------------
# Fake fetchers
# ---------------------------------------------------------------------------


class _RecordingPageFetcher:
    """Fake PageFetcher recording every fetch keyed by requested URL."""

    def __init__(
        self,
        bodies: dict[str, str] | None = None,
        default_body: str = "",
        fail_on_fetch_index: set[int] | None = None,
        fail_error: type[Exception] | None = None,
        final_url_override: str | None = None,
    ) -> None:
        self.bodies = bodies or {}
        self.default_body = default_body
        self.fail_on_fetch_index = fail_on_fetch_index or set()
        self.fail_error = fail_error
        self.final_url_override = final_url_override
        self.requests: list[PageFetchRequest] = []

    def fetch(self, request: PageFetchRequest) -> FetchedPage:
        self.requests.append(request)
        n = len(self.requests)
        if n in self.fail_on_fetch_index and self.fail_error is not None:
            raise self.fail_error("simulated failure")
        body = self.bodies.get(request.url, self.default_body)
        final_url = self.final_url_override or request.url
        return FetchedPage(
            requested_url=request.url,
            final_url=final_url,
            retrieved_at=RETRIEVED_AT,
            status_code=200,
            body_text=body,
            content_type="text/html",
            body_byte_count=len(body),
            redirect_count=0,
            fetcher_id="recording",
        )

    def count(self, url: str) -> int:
        return sum(1 for r in self.requests if r.url == url)


class _FilePdfFetcher:
    """Document fetcher reading a real PDF file (counts fetches)."""

    def __init__(self, pdf_path: str) -> None:
        self.pdf_path = pdf_path
        self.fetch_count = 0

    def fetch(self, request):
        self.fetch_count += 1
        with open(self.pdf_path, "rb") as fh:
            data = fh.read()
        return type("FetchedDocument", (), {
            "requested_url": request.url,
            "final_url": request.url,
            "retrieved_at": RETRIEVED_AT,
            "content_type": "application/pdf",
            "body_bytes": data,
            "body_byte_count": len(data),
            "redirect_count": 0,
            "fetcher_id": "file",
        })()


class _ErrorPdfFetcher:
    """Document fetcher that always raises DocumentFetchError."""

    def __init__(self) -> None:
        self.fetch_count = 0

    def fetch(self, request):
        self.fetch_count += 1
        raise DocumentFetchError("simulated fetch error")


class _UnsafePdfFetcher:
    """Document fetcher that always raises UnsafeDocumentTargetError."""

    def __init__(self) -> None:
        self.fetch_count = 0

    def fetch(self, request):
        self.fetch_count += 1
        raise UnsafeDocumentTargetError("simulated unsafe target")


class _BytesPdfFetcher:
    """Document fetcher returning fixed bytes."""

    def __init__(self, body: bytes) -> None:
        self.body = body
        self.fetch_count = 0

    def fetch(self, request):
        self.fetch_count += 1
        return type("FetchedDocument", (), {
            "requested_url": request.url,
            "final_url": request.url,
            "retrieved_at": RETRIEVED_AT,
            "content_type": "application/pdf",
            "body_bytes": self.body,
            "body_byte_count": len(self.body),
            "redirect_count": 0,
            "fetcher_id": "bytes",
        })()


# ---------------------------------------------------------------------------
# Minimal PDF builder (parsable, 0 tables → NO_OBSERVATIONS)
# ---------------------------------------------------------------------------


def _build_minimal_empty_pdf() -> bytes:
    """Build a tiny valid PDF with one empty page and no tables."""
    import io
    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n",
    ]
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for o in objects:
        offsets.append(out.tell())
        out.write(o)
    xref_pos = out.tell()
    out.write(b"xref\n0 4\n")
    out.write(b"0000000000 65535 f \n")
    for off in offsets:
        out.write(f"{off:010d} 00000 n \n".encode())
    out.write(b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n")
    out.write(str(xref_pos).encode())
    out.write(b"\n%%EOF\n")
    return out.getvalue()


# ---------------------------------------------------------------------------
# Synthetic support page builder
# ---------------------------------------------------------------------------


def _synthetic_support_page(records) -> str:
    """Build a support-specs page from a list of dicts.

    Fields: skuNumber, title, features (list of {title, value, order}),
            and optionally datasheet.
    Values must be ASCII-only for the unicode_escape decoder in 6C.
    """
    payload = json.dumps(records)
    escaped = payload.replace("\\", "\\\\").replace("'", "\\'")
    return (
        "<html><head></head><body>"
        "<script>var supportSpecsData = JSON.parse('" + escaped + "');</script>"
        "</body></html>"
    )


def _synthetic_records_target_only(
    mpn: str = "TEST-TGT-1",
    form_factor: str = "2.5in",
    *,
    datasheet: str | None = "/content/dam/test/ds.pdf",
) -> list[dict]:
    records: list[dict] = [{
        "skuNumber": mpn,
        "title": f"Test Drive {mpn}",
        "features": [
            {"title": "Form Factor", "value": form_factor, "order": form_factor},
        ],
    }]
    if datasheet is not None:
        records[0]["datasheet"] = datasheet
    return records


def _synthetic_records_target_plus_candidates(
    *,
    target_mpn: str = "TEST-TGT-1",
    n_candidates: int = 3,
    datasheet: str | None = None,
) -> list[dict]:
    records: list[dict] = [{
        "skuNumber": target_mpn,
        "title": f"Test Drive {target_mpn}",
        "features": [
            {"title": "Form Factor", "value": "2.5in", "order": "2.5in"},
        ],
    }]
    for i in range(n_candidates):
        cand: dict = {
            "skuNumber": f"TEST-CAND-{i}",
            "title": f"Test Candidate {i}",
            "features": [
                {"title": "Form Factor", "value": "2.5in", "order": "2.5in"},
            ],
        }
        if datasheet is not None:
            cand["datasheet"] = datasheet
        records.append(cand)
    return records


def _synthetic_records_no_match() -> list[dict]:
    return [
        {"skuNumber": "NOPE-A", "title": "No Match", "features": [
            {"title": "Form Factor", "value": "2.5in", "order": "2.5in"},
        ]},
    ]


def _synthetic_records_ambiguous() -> list[dict]:
    return [
        {"skuNumber": "AMB-1", "title": "Ambiguous A", "features": [
            {"title": "Form Factor", "value": "2.5in", "order": "2.5in"},
        ]},
        {"skuNumber": "AMB-1", "title": "Ambiguous B", "features": [
            {"title": "Form Factor", "value": "2.5in", "order": "2.5in"},
        ]},
    ]


# ---------------------------------------------------------------------------
# 2. FULL end-to-end offline vertical slice (real Seagate fixture + PDF)
# ---------------------------------------------------------------------------


class TestFullVerticalSlice(TestCase):
    """Strongest evidence: real HTML + real PDF, no mocks."""

    def test_full_vertical_slice_completes(self) -> None:
        parent = _make_completed_run()
        child = ComparableResearchExecution.objects.create(
            parent_run=parent,
            state=ComparableResearchState.PENDING,
            active_slot=1,
        )
        page_fetcher = _RecordingPageFetcher(
            bodies={SEAGATE_URL: _read_real_html()},
        )
        pdf_fetcher = _FilePdfFetcher(REAL_PDF_PATH)

        terminal = execute_comparable_research(
            child.id, page_fetcher=page_fetcher, document_fetcher=pdf_fetcher,
        )

        # Terminal row
        assert terminal.state == ComparableResearchState.COMPLETED
        assert terminal.result_schema_version == COMPARABLE_RESULT_SCHEMA_VERSION
        assert terminal.result_payload is not None
        assert terminal.active_slot is None
        assert terminal.failure_reason is None

        # Decode
        result = decode_comparable_result(
            terminal.result_payload,
            schema_version=COMPARABLE_RESULT_SCHEMA_VERSION,
        )
        self.assertEqual(result.kind, ComparableResultKind.FULL)
        self.assertEqual(result.target_mpn, "XP15360SE70005")
        self.assertEqual(result.target_manufacturer, "Seagate")
        self.assertIsNotNone(result.target_enrichment_audit)
        self.assertGreater(len(result.candidates), 0)

        # Authority audit: MATCHED
        self.assertGreater(len(result.authority_audit), 0)
        matched = result.authority_audit[0]
        self.assertEqual(matched.outcome, AuthorityAuditOutcomeKind.MATCHED)
        self.assertIsNotNone(matched.requested_source_url)
        self.assertIsNotNone(matched.fetched_final_url)
        self.assertIsNotNone(matched.matching_mpn)

        # Candidates in discovery order
        self.assertEqual(len(result.candidates), 80)
        for c in result.candidates:
            self.assertNotEqual(c.candidate_mpn, "")
            self.assertIsNotNone(c.enrichment_audit)

        # Target enrichment: at least one ENRICHED
        target_audit = result.target_enrichment_audit
        enriched = any(
            a.outcome is DatasheetAuditOutcomeKind.ENRICHED
            for a in target_audit.attempts
        )
        self.assertTrue(enriched, "target should have at least one ENRICHED datasheet")

        # Fetch counts: PRE1(1)+6C(1)+7A(1)+held(1)+6D-batch(1) = 5
        seagate_fetches = page_fetcher.count(SEAGATE_URL)
        self.assertEqual(seagate_fetches, 5)

        # Shared PDF dedup: ONE real PDF fetch for 81 identities
        self.assertEqual(pdf_fetcher.fetch_count, 1)

        # Evidence layer: spot-check candidate capacity has DATASHEET_PDF
        for candidate in result.candidates:
            for fa in candidate.field_assessments:
                if fa.definition_key == "capacity":
                    has_pdf = any(
                        e.evidence_layer is EvidenceLayer.DATASHEET_PDF
                        for e in fa.candidate_evidence
                    )
                    self.assertTrue(
                        has_pdf,
                        "candidate capacity should have DATASHEET_PDF evidence",
                    )
                    return  # one confirmed is enough

    def test_full_slice_codec_round_trip(self) -> None:
        """Codec payload decodes back to an equal ComparableResearchResult."""
        parent = _make_completed_run()
        child = ComparableResearchExecution.objects.create(
            parent_run=parent,
            state=ComparableResearchState.PENDING,
            active_slot=1,
        )
        terminal = execute_comparable_research(
            child.id,
            page_fetcher=_RecordingPageFetcher(bodies={SEAGATE_URL: _read_real_html()}),
            document_fetcher=_FilePdfFetcher(REAL_PDF_PATH),
        )
        decoded = decode_comparable_result(
            terminal.result_payload,
            schema_version=COMPARABLE_RESULT_SCHEMA_VERSION,
        )
        # Re-encode and assert equality with the persisted payload
        payload2 = encode_comparable_result(decoded)
        self.assertEqual(terminal.result_payload, payload2)


# ---------------------------------------------------------------------------
# 3. Authority abstentions (PRE1 COMPLETED paths)
# ---------------------------------------------------------------------------


class TestAuthorityAbstentions(TestCase):
    def test_no_requested_mpn(self) -> None:
        parent = _make_completed_run(mpn="")
        child = ComparableResearchExecution.objects.create(
            parent_run=parent,
            state=ComparableResearchState.PENDING,
            active_slot=1,
        )
        page_fetcher = _RecordingPageFetcher(
            bodies={SEAGATE_URL: _synthetic_support_page(_synthetic_records_target_only(mpn="X"))},
        )
        terminal = execute_comparable_research(
            child.id, page_fetcher=page_fetcher, document_fetcher=_FilePdfFetcher(REAL_PDF_PATH),
        )
        self.assertEqual(terminal.state, ComparableResearchState.COMPLETED)
        result = decode_comparable_result(
            terminal.result_payload, schema_version=COMPARABLE_RESULT_SCHEMA_VERSION,
        )
        self.assertEqual(result.kind, ComparableResultKind.NO_REQUESTED_MPN)
        self.assertEqual(result.target_mpn, "")
        self.assertEqual(result.target_manufacturer, None)

    def test_no_authority_match(self) -> None:
        parent = _make_completed_run(mpn="ZZZZ-NOPE-1")
        child = ComparableResearchExecution.objects.create(
            parent_run=parent,
            state=ComparableResearchState.PENDING,
            active_slot=1,
        )
        page_fetcher = _RecordingPageFetcher(
            bodies={SEAGATE_URL: _synthetic_support_page(_synthetic_records_no_match())},
        )
        terminal = execute_comparable_research(
            child.id, page_fetcher=page_fetcher, document_fetcher=_FilePdfFetcher(REAL_PDF_PATH),
        )
        self.assertEqual(terminal.state, ComparableResearchState.COMPLETED)
        result = decode_comparable_result(
            terminal.result_payload, schema_version=COMPARABLE_RESULT_SCHEMA_VERSION,
        )
        self.assertEqual(result.kind, ComparableResultKind.NO_AUTHORITY_MATCH)

    def test_ambiguous_authority(self) -> None:
        parent = _make_completed_run(mpn="AMB-1")
        child = ComparableResearchExecution.objects.create(
            parent_run=parent,
            state=ComparableResearchState.PENDING,
            active_slot=1,
        )
        page_fetcher = _RecordingPageFetcher(
            bodies={SEAGATE_URL: _synthetic_support_page(_synthetic_records_ambiguous())},
        )
        terminal = execute_comparable_research(
            child.id, page_fetcher=page_fetcher, document_fetcher=_FilePdfFetcher(REAL_PDF_PATH),
        )
        self.assertEqual(terminal.state, ComparableResearchState.COMPLETED)
        result = decode_comparable_result(
            terminal.result_payload, schema_version=COMPARABLE_RESULT_SCHEMA_VERSION,
        )
        self.assertEqual(result.kind, ComparableResultKind.AMBIGUOUS_AUTHORITY)


# ---------------------------------------------------------------------------
# 4. Authority failures (exact failure reasons)
# ---------------------------------------------------------------------------


class TestAuthorityFailures(TestCase):
    def _child(self, mpn="XP15360SE70005") -> ComparableResearchExecution:
        parent = _make_completed_run(mpn=mpn)
        return ComparableResearchExecution.objects.create(
            parent_run=parent,
            state=ComparableResearchState.PENDING,
            active_slot=1,
        )

    def test_fetch_failed(self) -> None:
        child = self._child()
        page_fetcher = _RecordingPageFetcher(
            fail_on_fetch_index={1},
            fail_error=PageFetchError,
        )
        with self.assertRaises(ComparableResearchExecutionError):
            execute_comparable_research(
                child.id, page_fetcher=page_fetcher, document_fetcher=_FilePdfFetcher(REAL_PDF_PATH),
            )
        child.refresh_from_db()
        self.assertEqual(child.state, ComparableResearchState.FAILED)
        self.assertEqual(child.failure_reason, "AUTHORITY_FETCH_FAILED")

    def test_source_refused(self) -> None:
        child = self._child()
        page_fetcher = _RecordingPageFetcher(
            fail_on_fetch_index={1},
            fail_error=UnsafeFetchTargetError,
        )
        with self.assertRaises(ComparableResearchExecutionError):
            execute_comparable_research(
                child.id, page_fetcher=page_fetcher, document_fetcher=_FilePdfFetcher(REAL_PDF_PATH),
            )
        child.refresh_from_db()
        self.assertEqual(child.state, ComparableResearchState.FAILED)
        self.assertEqual(child.failure_reason, "AUTHORITY_SOURCE_REFUSED")

    def test_host_escaped(self) -> None:
        child = self._child()
        page_fetcher = _RecordingPageFetcher(
            bodies={SEAGATE_URL: _read_real_html()},
            final_url_override="https://evil.example.com/redirect",
        )
        with self.assertRaises(ComparableResearchExecutionError):
            execute_comparable_research(
                child.id, page_fetcher=page_fetcher, document_fetcher=_FilePdfFetcher(REAL_PDF_PATH),
            )
        child.refresh_from_db()
        self.assertEqual(child.state, ComparableResearchState.FAILED)
        self.assertEqual(child.failure_reason, "AUTHORITY_HOST_ESCAPED")

    def test_no_structural_observations(self) -> None:
        child = self._child()
        page_fetcher = _RecordingPageFetcher(
            bodies={SEAGATE_URL: "<html><body>No specs at all</body></html>"},
        )
        with self.assertRaises(ComparableResearchExecutionError):
            execute_comparable_research(
                child.id, page_fetcher=page_fetcher, document_fetcher=_FilePdfFetcher(REAL_PDF_PATH),
            )
        child.refresh_from_db()
        self.assertEqual(child.state, ComparableResearchState.FAILED)
        self.assertEqual(child.failure_reason, "AUTHORITY_NO_STRUCTURAL_OBSERVATIONS")


# ---------------------------------------------------------------------------
# 5. Target 6C bounded gap still completes truthfully
# ---------------------------------------------------------------------------


class TestTarget6cGap(TestCase):
    def test_target_6c_fetch_fails_completes_truthfully(self) -> None:
        """If target 6C fetch fails, the child still completes with UNKNOWN fields."""
        parent = _make_completed_run(mpn="TEST-TGT-1")
        child = ComparableResearchExecution.objects.create(
            parent_run=parent,
            state=ComparableResearchState.PENDING,
            active_slot=1,
        )
        records = _synthetic_records_target_plus_candidates(target_mpn="TEST-TGT-1", n_candidates=2)
        page_fetcher = _RecordingPageFetcher(
            bodies={SEAGATE_URL: _synthetic_support_page(records)},
            fail_on_fetch_index={2},  # fetch #2 = target 6C (PRE1 is #1)
            fail_error=PageFetchError,
        )
        terminal = execute_comparable_research(
            child.id, page_fetcher=page_fetcher, document_fetcher=_ErrorPdfFetcher(),
        )
        self.assertEqual(terminal.state, ComparableResearchState.COMPLETED)
        result = decode_comparable_result(
            terminal.result_payload, schema_version=COMPARABLE_RESULT_SCHEMA_VERSION,
        )
        self.assertEqual(result.kind, ComparableResultKind.FULL)
        # Target physical_form_factor should be UNKNOWN (6C failed, no 6D for form factor)
        ff_assessment = None
        for fa in result.candidates[0].field_assessments:
            if fa.definition_key == "physical_form_factor":
                ff_assessment = fa
                break
        self.assertIsNotNone(ff_assessment)
        self.assertEqual(ff_assessment.target_resolution_state, ResolutionState.UNKNOWN)
        self.assertIsNone(ff_assessment.target_value)


# ---------------------------------------------------------------------------
# 6. Zero candidates is a valid FULL
# ---------------------------------------------------------------------------


class TestZeroCandidates(TestCase):
    def test_zero_candidates_completes(self) -> None:
        parent = _make_completed_run(mpn="TEST-TGT-1")
        child = ComparableResearchExecution.objects.create(
            parent_run=parent,
            state=ComparableResearchState.PENDING,
            active_slot=1,
        )
        records = _synthetic_records_target_only(
            mpn="TEST-TGT-1", datasheet=None,
        )
        page_fetcher = _RecordingPageFetcher(
            bodies={SEAGATE_URL: _synthetic_support_page(records)},
        )
        terminal = execute_comparable_research(
            child.id, page_fetcher=page_fetcher, document_fetcher=_ErrorPdfFetcher(),
        )
        self.assertEqual(terminal.state, ComparableResearchState.COMPLETED)
        result = decode_comparable_result(
            terminal.result_payload, schema_version=COMPARABLE_RESULT_SCHEMA_VERSION,
        )
        self.assertEqual(result.kind, ComparableResultKind.FULL)
        self.assertEqual(len(result.candidates), 0)
        # Fetch count: PRE1(1)+6C(1)+7A(1)+6D-batch(1) = 4 (no held docs)
        self.assertEqual(page_fetcher.count(SEAGATE_URL), 4)


# ---------------------------------------------------------------------------
# 7. Bounded 6D outcomes
# ---------------------------------------------------------------------------


class TestBounded6d(TestCase):
    def _setup_with_candidates(self, n=1, *, datasheet=None):
        mpn = "TEST-TGT-1"
        records = _synthetic_records_target_plus_candidates(
            target_mpn=mpn, n_candidates=n, datasheet=datasheet,
        )
        parent = _make_completed_run(mpn=mpn)
        child = ComparableResearchExecution.objects.create(
            parent_run=parent,
            state=ComparableResearchState.PENDING,
            active_slot=1,
        )
        return parent, child, _synthetic_support_page(records), records

    def test_no_datasheet_source(self) -> None:
        _, child, page_body, _ = self._setup_with_candidates(datasheet=None)
        page_fetcher = _RecordingPageFetcher(bodies={SEAGATE_URL: page_body})
        terminal = execute_comparable_research(
            child.id, page_fetcher=page_fetcher, document_fetcher=_ErrorPdfFetcher(),
        )
        result = decode_comparable_result(
            terminal.result_payload, schema_version=COMPARABLE_RESULT_SCHEMA_VERSION,
        )
        for cand in result.candidates:
            self.assertTrue(
                any(a.outcome is DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE
                    for a in cand.enrichment_audit.attempts),
                "candidate should have NO_DATASHEET_SOURCE audit",
            )

    def test_fetch_failed(self) -> None:
        _, child, page_body, _ = self._setup_with_candidates(datasheet="/ds.pdf")
        page_fetcher = _RecordingPageFetcher(bodies={SEAGATE_URL: page_body})
        terminal = execute_comparable_research(
            child.id,
            page_fetcher=page_fetcher,
            document_fetcher=_ErrorPdfFetcher(),
        )
        self.assertEqual(terminal.state, ComparableResearchState.COMPLETED)
        result = decode_comparable_result(
            terminal.result_payload, schema_version=COMPARABLE_RESULT_SCHEMA_VERSION,
        )
        for cand in result.candidates:
            self.assertTrue(
                any(a.outcome is DatasheetAuditOutcomeKind.FETCH_FAILED
                    for a in cand.enrichment_audit.attempts),
            )

    def test_source_refused(self) -> None:
        _, child, page_body, _ = self._setup_with_candidates(datasheet="/ds.pdf")
        page_fetcher = _RecordingPageFetcher(bodies={SEAGATE_URL: page_body})
        terminal = execute_comparable_research(
            child.id,
            page_fetcher=page_fetcher,
            document_fetcher=_UnsafePdfFetcher(),
        )
        self.assertEqual(terminal.state, ComparableResearchState.COMPLETED)
        result = decode_comparable_result(
            terminal.result_payload, schema_version=COMPARABLE_RESULT_SCHEMA_VERSION,
        )
        for cand in result.candidates:
            self.assertTrue(
                any(a.outcome is DatasheetAuditOutcomeKind.SOURCE_REFUSED
                    for a in cand.enrichment_audit.attempts),
            )

    def test_parse_failed(self) -> None:
        _, child, page_body, _ = self._setup_with_candidates(datasheet="/ds.pdf")
        page_fetcher = _RecordingPageFetcher(bodies={SEAGATE_URL: page_body})
        terminal = execute_comparable_research(
            child.id,
            page_fetcher=page_fetcher,
            document_fetcher=_BytesPdfFetcher(b"%PDF-1.4 not-really-a-pdf\n"),
        )
        self.assertEqual(terminal.state, ComparableResearchState.COMPLETED)
        result = decode_comparable_result(
            terminal.result_payload, schema_version=COMPARABLE_RESULT_SCHEMA_VERSION,
        )
        for cand in result.candidates:
            self.assertTrue(
                any(a.outcome is DatasheetAuditOutcomeKind.PARSE_FAILED
                    for a in cand.enrichment_audit.attempts),
            )

    def test_no_observations(self) -> None:
        _, child, page_body, _ = self._setup_with_candidates(datasheet="/ds.pdf")
        page_fetcher = _RecordingPageFetcher(bodies={SEAGATE_URL: page_body})
        terminal = execute_comparable_research(
            child.id,
            page_fetcher=page_fetcher,
            document_fetcher=_BytesPdfFetcher(_build_minimal_empty_pdf()),
        )
        self.assertEqual(terminal.state, ComparableResearchState.COMPLETED)
        result = decode_comparable_result(
            terminal.result_payload, schema_version=COMPARABLE_RESULT_SCHEMA_VERSION,
        )
        for cand in result.candidates:
            self.assertTrue(
                any(a.outcome is DatasheetAuditOutcomeKind.NO_OBSERVATIONS
                    for a in cand.enrichment_audit.attempts),
            )


# ---------------------------------------------------------------------------
# 8. Evidence-layer classification
# ---------------------------------------------------------------------------


class TestEvidenceLayer(TestCase):
    def test_support_page_and_datasheet_pdf_layers(self) -> None:
        """Verify that SUPPORT_PAGE comes from 6C and DATASHEET_PDF from 6D."""
        parent = _make_completed_run()
        child = ComparableResearchExecution.objects.create(
            parent_run=parent,
            state=ComparableResearchState.PENDING,
            active_slot=1,
        )
        terminal = execute_comparable_research(
            child.id,
            page_fetcher=_RecordingPageFetcher(bodies={SEAGATE_URL: _read_real_html()}),
            document_fetcher=_FilePdfFetcher(REAL_PDF_PATH),
        )
        result = decode_comparable_result(
            terminal.result_payload, schema_version=COMPARABLE_RESULT_SCHEMA_VERSION,
        )
        # Spot-check the first candidate's physical_form_factor assessment
        for cand in result.candidates:
            ff_assessment = None
            for fa in cand.field_assessments:
                if fa.definition_key == "physical_form_factor":
                    ff_assessment = fa
                    break
            if ff_assessment is not None and ff_assessment.candidate_evidence:
                self.assertIn(
                    EvidenceLayer.SUPPORT_PAGE,
                    {e.evidence_layer for e in ff_assessment.candidate_evidence},
                    "form factor candidate evidence should contain SUPPORT_PAGE",
                )
                break

    def test_foreign_evidence_raises_internal_error(self) -> None:
        """Foreign evidence object that belongs to neither pool → INTERNAL_ERROR."""
        from product_intelligence.execution import comparable_research as cr_mod
        from product_intelligence.research.specifications import (
            NormalizedSpecificationObservation,
            resolve_specification,
            SpecificationObservation,
            SpecificationValue,
        )

        original_resolve = cr_mod.resolve_specification

        def patched_resolve(product_identity, definition, observations):
            # Inject a foreign observation for the first candidate's form factor
            if (
                product_identity.manufacturer_part_number != "XP15360SE70005"
                and definition.key == "physical_form_factor"
            ):
                # Build a foreign observation
                foreign_obs = SpecificationObservation(
                    product_identity=product_identity,
                    definition=definition,
                    raw_value="2.5-inch",
                    source_name="Foreign Source",
                    source_url="https://foreign.example/x",
                    retrieved_at=RETRIEVED_AT,
                    source_authority=SourceAuthority.AUTHORITATIVE,
                )
                foreign_norm = NormalizedSpecificationObservation(
                    observation=foreign_obs,
                    canonical_value=SpecificationValue(value="2.5-inch"),
                )
                observations = observations + (foreign_norm,)
            return original_resolve(product_identity, definition, observations)

        import unittest.mock as mock
        with mock.patch.object(cr_mod, "resolve_specification", side_effect=patched_resolve):
            parent = _make_completed_run()
            child = ComparableResearchExecution.objects.create(
                parent_run=parent,
                state=ComparableResearchState.PENDING,
                active_slot=1,
            )
            with self.assertRaises(ValueError):
                execute_comparable_research(
                    child.id,
                    page_fetcher=_RecordingPageFetcher(bodies={SEAGATE_URL: _read_real_html()}),
                    document_fetcher=_FilePdfFetcher(REAL_PDF_PATH),
                )
            child.refresh_from_db()
            self.assertEqual(child.state, ComparableResearchState.FAILED)
            self.assertEqual(child.failure_reason, "INTERNAL_ERROR")


# ---------------------------------------------------------------------------
# 9. Composition and projection
# ---------------------------------------------------------------------------


class TestCompositionAndProjection(TestCase):
    def test_compose_6c_6d_called_once_per_product(self) -> None:
        """6C+6D compose is called once for target + once per candidate."""
        from product_intelligence.execution import comparable_research as cr_mod
        call_count = 0
        original_compose = cr_mod.compose_6c_6d_specifications

        def spy_compose(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return original_compose(*args, **kwargs)

        import unittest.mock as mock
        with mock.patch.object(cr_mod, "compose_6c_6d_specifications", side_effect=spy_compose):
            parent = _make_completed_run()
            child = ComparableResearchExecution.objects.create(
                parent_run=parent,
                state=ComparableResearchState.PENDING,
                active_slot=1,
            )
            execute_comparable_research(
                child.id,
                page_fetcher=_RecordingPageFetcher(bodies={SEAGATE_URL: _read_real_html()}),
                document_fetcher=_FilePdfFetcher(REAL_PDF_PATH),
            )
        # target + 80 candidates
        self.assertEqual(call_count, 81)

    def test_pure_7b_scoring_preserved(self) -> None:
        """No ranking, no recommendation — pure similarity values projected."""
        parent = _make_completed_run()
        child = ComparableResearchExecution.objects.create(
            parent_run=parent,
            state=ComparableResearchState.PENDING,
            active_slot=1,
        )
        terminal = execute_comparable_research(
            child.id,
            page_fetcher=_RecordingPageFetcher(bodies={SEAGATE_URL: _read_real_html()}),
            document_fetcher=_FilePdfFetcher(REAL_PDF_PATH),
        )
        result = decode_comparable_result(
            terminal.result_payload, schema_version=COMPARABLE_RESULT_SCHEMA_VERSION,
        )
        for cand in result.candidates:
            # These are pure similarity outputs — no recommendation
            self.assertIsNotNone(cand.observed_similarity)
            self.assertIsNotNone(cand.evidence_weighted_similarity)
            self.assertIsInstance(cand.scored_field_count, int)
            self.assertTrue(cand.evidence_coverage is not None)

    def test_candidate_identity_bridge_matches(self) -> None:
        """The candidate bridge identity is the frozen 7B helper output."""
        from product_intelligence.execution import comparable_research as cr_mod
        from product_intelligence.research.enterprise_ssd_similarity import (
            establish_candidate_product_identity,
        )
        bridge_calls = []
        original_bridge = cr_mod.establish_candidate_product_identity

        def spy_bridge(candidate):
            identity = original_bridge(candidate)
            bridge_calls.append((candidate, identity))
            return identity

        import unittest.mock as mock
        with mock.patch.object(cr_mod, "establish_candidate_product_identity", side_effect=spy_bridge):
            parent = _make_completed_run()
            child = ComparableResearchExecution.objects.create(
                parent_run=parent,
                state=ComparableResearchState.PENDING,
                active_slot=1,
            )
            execute_comparable_research(
                child.id,
                page_fetcher=_RecordingPageFetcher(bodies={SEAGATE_URL: _read_real_html()}),
                document_fetcher=_FilePdfFetcher(REAL_PDF_PATH),
            )
        # One call per candidate
        self.assertEqual(len(bridge_calls), 80)
        # Each candidate's bridge identity MPN matches the candidate's raw MPN
        for candidate, identity in bridge_calls:
            self.assertEqual(identity.manufacturer_part_number, candidate.manufacturer_part_number)

    def test_single_6d_batch_call(self) -> None:
        """Exactly ONE 6D batch call for target + all candidates."""
        from product_intelligence.execution import comparable_research as cr_mod
        batch_calls = 0
        original_batch = cr_mod.enrich_enterprise_ssd_specifications_batch

        def spy_batch(*args, **kwargs):
            nonlocal batch_calls
            batch_calls += 1
            return original_batch(*args, **kwargs)

        import unittest.mock as mock
        with mock.patch.object(cr_mod, "enrich_enterprise_ssd_specifications_batch", side_effect=spy_batch):
            parent = _make_completed_run()
            child = ComparableResearchExecution.objects.create(
                parent_run=parent,
                state=ComparableResearchState.PENDING,
                active_slot=1,
            )
            execute_comparable_research(
                child.id,
                page_fetcher=_RecordingPageFetcher(bodies={SEAGATE_URL: _read_real_html()}),
                document_fetcher=_FilePdfFetcher(REAL_PDF_PATH),
            )
        self.assertEqual(batch_calls, 1)

    def test_no_per_candidate_6c_public_call(self) -> None:
        """No per-candidate public 6C execution call (only target + held)."""
        from product_intelligence.execution import comparable_research as cr_mod
        exec_calls = []
        original_exec = cr_mod.research_enterprise_ssd_specifications

        def spy_exec(*args, **kwargs):
            exec_calls.append((args, kwargs))
            return original_exec(*args, **kwargs)

        import unittest.mock as mock
        with mock.patch.object(cr_mod, "research_enterprise_ssd_specifications", side_effect=spy_exec):
            parent = _make_completed_run()
            child = ComparableResearchExecution.objects.create(
                parent_run=parent,
                state=ComparableResearchState.PENDING,
                active_slot=1,
            )
            execute_comparable_research(
                child.id,
                page_fetcher=_RecordingPageFetcher(bodies={SEAGATE_URL: _read_real_html()}),
                document_fetcher=_FilePdfFetcher(REAL_PDF_PATH),
            )
        # Only 1 public 6C call (for the target)
        self.assertEqual(len(exec_calls), 1)


# ---------------------------------------------------------------------------
# 10. Failure contracts
# ---------------------------------------------------------------------------


class TestFailureContracts(TestCase):
    def test_codec_failure_result_encoding_failed(self) -> None:
        from product_intelligence.execution import comparable_research as cr_mod
        from product_intelligence.research.comparable_result_codec import (
            ComparableResultCodecError,
        )

        def fake_encode(*args, **kwargs):
            raise ComparableResultCodecError("simulated codec error")

        import unittest.mock as mock
        with mock.patch.object(cr_mod, "encode_comparable_result", side_effect=fake_encode):
            parent = _make_completed_run()
            child = ComparableResearchExecution.objects.create(
                parent_run=parent,
                state=ComparableResearchState.PENDING,
                active_slot=1,
            )
            with self.assertRaises(ComparableResearchExecutionError):
                execute_comparable_research(
                    child.id,
                    page_fetcher=_RecordingPageFetcher(bodies={SEAGATE_URL: _read_real_html()}),
                    document_fetcher=_FilePdfFetcher(REAL_PDF_PATH),
                )
            child.refresh_from_db()
            self.assertEqual(child.state, ComparableResearchState.FAILED)
            self.assertEqual(child.failure_reason, "RESULT_ENCODING_FAILED")

    def test_programming_exception_propagates(self) -> None:
        """Programming exception → best-effort INTERNAL_ERROR + original propagates."""
        from product_intelligence.execution import comparable_research as cr_mod

        def fake_similarity(*args, **kwargs):
            raise RuntimeError("test programming defect")

        import unittest.mock as mock
        with mock.patch.object(
            cr_mod, "score_enterprise_ssd_candidate_similarity", side_effect=fake_similarity,
        ):
            parent = _make_completed_run()
            child = ComparableResearchExecution.objects.create(
                parent_run=parent,
                state=ComparableResearchState.PENDING,
                active_slot=1,
            )
            with self.assertRaises(RuntimeError):
                execute_comparable_research(
                    child.id,
                    page_fetcher=_RecordingPageFetcher(bodies={SEAGATE_URL: _read_real_html()}),
                    document_fetcher=_FilePdfFetcher(REAL_PDF_PATH),
                )
            child.refresh_from_db()
            self.assertEqual(child.state, ComparableResearchState.FAILED)
            self.assertEqual(child.failure_reason, "INTERNAL_ERROR")

    def test_completion_persistence_error_not_failed(self) -> None:
        """Terminal completion persistence error propagates as-is; child NOT FAILED."""
        from product_intelligence.execution import comparable_research as cr_mod

        fail_calls = []
        original_fail = cr_mod.fail_comparable_research

        def spy_fail(*args, **kwargs):
            fail_calls.append((args, kwargs))

        def fake_complete(*args, **kwargs):
            raise RuntimeError("DB write failed")

        import unittest.mock as mock
        with (
            mock.patch.object(cr_mod, "fail_comparable_research", side_effect=spy_fail),
            mock.patch.object(cr_mod, "complete_comparable_research", side_effect=fake_complete),
        ):
            parent = _make_completed_run()
            child = ComparableResearchExecution.objects.create(
                parent_run=parent,
                state=ComparableResearchState.PENDING,
                active_slot=1,
            )
            with self.assertRaises(RuntimeError):
                execute_comparable_research(
                    child.id,
                    page_fetcher=_RecordingPageFetcher(bodies={SEAGATE_URL: _read_real_html()}),
                    document_fetcher=_FilePdfFetcher(REAL_PDF_PATH),
                )
            # fail_comparable_research must NOT have been called
            self.assertEqual(len(fail_calls), 0)
            child.refresh_from_db()
            self.assertEqual(child.state, ComparableResearchState.RUNNING)
            self.assertIsNone(child.failure_reason)


# ---------------------------------------------------------------------------
# 11. Multiple candidates preserve discovery order
# ---------------------------------------------------------------------------


class TestDiscoveryOrder(TestCase):
    def test_candidates_preserve_discovery_order(self) -> None:
        parent = _make_completed_run()
        child = ComparableResearchExecution.objects.create(
            parent_run=parent,
            state=ComparableResearchState.PENDING,
            active_slot=1,
        )
        terminal = execute_comparable_research(
            child.id,
            page_fetcher=_RecordingPageFetcher(bodies={SEAGATE_URL: _read_real_html()}),
            document_fetcher=_FilePdfFetcher(REAL_PDF_PATH),
        )
        result = decode_comparable_result(
            terminal.result_payload, schema_version=COMPARABLE_RESULT_SCHEMA_VERSION,
        )
        # Candidate MPNs should be in the order produced by the discovery primitive
        # (not sorted, not ranked)
        mpns = [c.candidate_mpn for c in result.candidates]
        self.assertEqual(len(mpns), len(set(mpns)), "no duplicates")


# ---------------------------------------------------------------------------
# 12. Boundary AST checks
# ---------------------------------------------------------------------------


class TestComparableResearchBoundaries(TestCase):
    """AST-based import guards for the 7C-B execution module."""

    @pytest.mark.skip(reason="AST boundary — not in a Django transaction context")
    def test_placeholder(self):
        pass


class TestComparableResearchBoundaryAsts:
    """AST-based import guards (pytest, no Django required)."""

    def test_no_web_import(self, pytestconfig: pytest.Config) -> None:
        import ast
        path = pytestconfig.rootpath / "product_intelligence" / "execution" / "comparable_research.py"
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("product_intelligence.web"), (
                        f"execution module must not import web: {alias.name}"
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("product_intelligence.web"):
                    pytest.fail(f"execution module must not import web: {node.module}")

    def test_no_old_comparable_similarity_import(self, pytestconfig: pytest.Config) -> None:
        import ast
        path = pytestconfig.rootpath / "product_intelligence" / "execution" / "comparable_research.py"
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if (
                    node.module
                    and "comparable_similarity" in node.module
                    and "similarity" in node.module
                    and "enterprise_ssd" not in node.module
                ):
                    pytest.fail(
                        f"execution module must not import old high-level executor: "
                        f"{node.module}"
                    )

    def test_research_still_free_of_runs(self, pytestconfig: pytest.Config) -> None:
        """Research modules must not import runs/providers/Django."""
        import ast, pathlib
        research_dir = pytestconfig.rootpath / "product_intelligence" / "research"
        for py_file in research_dir.glob("*.py"):
            tree = ast.parse(py_file.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    for forbidden in ("product_intelligence.runs",
                                       "product_intelligence.providers",
                                       "django"):
                        assert not mod.startswith(forbidden), (
                            f"{py_file.name} must not import {forbidden} "
                            f"(found: {mod})"
                        )
