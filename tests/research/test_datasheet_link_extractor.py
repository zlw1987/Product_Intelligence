"""Tests for support-record datasheet-link extraction (PRODUCT-INTEL.6D).

Proves the authoritative source chain:
    exact skuNumber -> exact datasheet field -> absolute URL resolution
"""

from pathlib import Path

import pytest
from product_intelligence.research.datasheet_link_extractor import (
    extract_datasheet_link,
    SupportRecordDatasheetLink,
)


# ---------------------------------------------------------------------------
# Real fixture document (actual frozen manufacturer support page)
# ---------------------------------------------------------------------------

_FIXTURE_DIR = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "specifications"
_REAL_SUPPORT_FIXTURE = (
    _FIXTURE_DIR / "real_seagate_nytro_5050_xp15360se70005.html"
)


def _load_real_support_document() -> str:
    """Load the actual frozen Seagate support page fixture."""
    return _REAL_SUPPORT_FIXTURE.read_text(encoding="utf-8")


REAL_SUPPORT_DOC = _load_real_support_document()


# ---------------------------------------------------------------------------
# SupportRecordDatasheetLink validation
# ---------------------------------------------------------------------------

class TestSupportRecordDatasheetLink:
    """SupportRecordDatasheetLink constructor validation."""

    def test_valid_link(self) -> None:
        link = SupportRecordDatasheetLink(
            sku_number="XP15360SE70005",
            datasheet_path="/content/dam/seagate/datasheet.pdf",
        )
        assert link.sku_number == "XP15360SE70005"
        assert link.datasheet_path == "/content/dam/seagate/datasheet.pdf"

    def test_empty_sku_number_refused(self) -> None:
        with pytest.raises(ValueError, match="sku_number must be a non-empty"):
            SupportRecordDatasheetLink(
                sku_number="",
                datasheet_path="/path.pdf",
            )

    def test_empty_datasheet_path_refused(self) -> None:
        with pytest.raises(ValueError, match="datasheet_path must be a non-empty"):
            SupportRecordDatasheetLink(
                sku_number="XP123",
                datasheet_path="",
            )


# ---------------------------------------------------------------------------
# extract_datasheet_link — happy path
# ---------------------------------------------------------------------------

class TestExtractDatasheetLinkHappyPath:
    """Exact skuNumber match returns the datasheet field (real fixture)."""

    def test_target_sku_xp15360se70005(self) -> None:
        result = extract_datasheet_link(
            document=REAL_SUPPORT_DOC,
            sku_number="XP15360SE70005",
        )
        assert result is not None
        assert result.sku_number == "XP15360SE70005"
        assert (
            result.datasheet_path
            == "/content/dam/seagate/en/content-fragments/products/datasheets/"
            "enterprise-rebranding/nytro-5550-5350-ssd/"
            "nytro-5550-5350-ssd-DS2099-4-2410US-en_US.pdf"
        )

    def test_sed_sku_xp15360se70015(self) -> None:
        result = extract_datasheet_link(
            document=REAL_SUPPORT_DOC,
            sku_number="XP15360SE70015",
        )
        assert result is not None
        assert result.sku_number == "XP15360SE70015"
        assert (
            result.datasheet_path
            == "/content/dam/seagate/en/content-fragments/products/datasheets/"
            "enterprise-rebranding/nytro-5550-5350-ssd/"
            "nytro-5550-5350-ssd-DS2099-4-2410US-en_US.pdf"
        )

    def test_different_capacity_sku_xp3840se70005(self) -> None:
        result = extract_datasheet_link(
            document=REAL_SUPPORT_DOC,
            sku_number="XP3840SE70005",
        )
        assert result is not None
        assert result.sku_number == "XP3840SE70005"
        assert (
            result.datasheet_path
            == "/content/dam/seagate/en/content-fragments/products/datasheets/"
            "enterprise-rebranding/nytro-5550-5350-ssd/"
            "nytro-5550-5350-ssd-DS2099-4-2410US-en_US.pdf"
        )

    def test_all_three_share_same_datasheet(self) -> None:
        """XP15360SE70005, XP15360SE70015, XP3840SE70005 all point to same PDF."""
        paths: list[str] = []
        for sku in ("XP15360SE70005", "XP15360SE70015", "XP3840SE70005"):
            result = extract_datasheet_link(document=REAL_SUPPORT_DOC, sku_number=sku)
            assert result is not None, f"No datasheet link for {sku}"
            paths.append(result.datasheet_path)
        assert len(set(paths)) == 1, (
            f"Expected all three SKUs to share one datasheet path, got {len(set(paths))}"
        )


# ---------------------------------------------------------------------------
# extract_datasheet_link — abstention
# ---------------------------------------------------------------------------

class TestExtractDatasheetLinkAbstention:
    """Absent/unmatched conditions return None."""

    def test_sku_not_found_returns_none(self) -> None:
        result = extract_datasheet_link(
            document=REAL_SUPPORT_DOC,
            sku_number="NONEXISTENT999",
        )
        assert result is None

    def test_no_support_specs_data_returns_none(self) -> None:
        result = extract_datasheet_link(
            document="<html><body>No scripts here</body></html>",
            sku_number="XP123",
        )
        assert result is None

    def test_empty_document_returns_none(self) -> None:
        result = extract_datasheet_link(
            document="",
            sku_number="XP123",
        )
        assert result is None


# ---------------------------------------------------------------------------
# extract_datasheet_link — fail closed
# ---------------------------------------------------------------------------

class TestExtractDatasheetLinkFailClosed:
    """Ambiguous conditions raise ValueError."""

    def test_duplicate_sku_raises(self) -> None:
        doc = """
        <script>
        var supportSpecsData = JSON.parse('[{"skuNumber":"XP123","datasheet":"/a.pdf"},{"skuNumber":"XP123","datasheet":"/b.pdf"}]')
        </script>
        """
        with pytest.raises(ValueError, match="Ambiguous match"):
            extract_datasheet_link(document=doc, sku_number="XP123")


# ---------------------------------------------------------------------------
# extract_datasheet_link — missing datasheet field
# ---------------------------------------------------------------------------

class TestExtractDatasheetLinkMissingDatasheet:
    """Record without datasheet field -> abstain."""

    def test_record_no_datasheet_field(self) -> None:
        doc = """
        <script>
        var supportSpecsData = JSON.parse('[{"skuNumber":"XP123","title":"No datasheet"}]')
        </script>
        """
        result = extract_datasheet_link(document=doc, sku_number="XP123")
        assert result is None

    def test_blank_datasheet_field(self) -> None:
        doc = """
        <script>
        var supportSpecsData = JSON.parse('[{"skuNumber":"XP123","datasheet":""}]')
        </script>
        """
        result = extract_datasheet_link(document=doc, sku_number="XP123")
        assert result is None

    def test_datasheet_not_string(self) -> None:
        doc = """
        <script>
        var supportSpecsData = JSON.parse('[{"skuNumber":"XP123","datasheet":123}]')
        </script>
        """
        result = extract_datasheet_link(document=doc, sku_number="XP123")
        assert result is None


# ---------------------------------------------------------------------------
# extract_datasheet_link — input validation
# ---------------------------------------------------------------------------

class TestExtractDatasheetLinkInputValidation:
    """Wrong types raise TypeError/ValueError."""

    def test_non_string_document_raises(self) -> None:
        with pytest.raises(TypeError, match="document must be a string"):
            extract_datasheet_link(document=123, sku_number="XP123")  # type: ignore

    def test_empty_sku_raises(self) -> None:
        with pytest.raises(ValueError, match="sku_number must be a non-empty"):
            extract_datasheet_link(document="anything", sku_number="")

    def test_non_string_sku_raises(self) -> None:
        with pytest.raises(TypeError, match="sku_number must be a string"):
            extract_datasheet_link(document="anything", sku_number=123)  # type: ignore


# ---------------------------------------------------------------------------
# Real manufacturer URL resolution proof
# ---------------------------------------------------------------------------

class TestRealUrlResolution:
    """Prove that the relative datasheet path resolves to the known public URL."""

    def test_real_seagate_path_resolves(self) -> None:
        """Mechanically prove the real support record path resolves correctly."""
        from urllib.parse import urljoin

        result = extract_datasheet_link(
            document=REAL_SUPPORT_DOC,
            sku_number="XP15360SE70005",
        )
        assert result is not None

        # Resolve relative path against manufacturer base
        manufacturer_base = "https://www.seagate.com"
        absolute_url = urljoin(manufacturer_base, result.datasheet_path)

        assert absolute_url == (
            "https://www.seagate.com"
            "/content/dam/seagate/en/content-fragments/products/datasheets/"
            "enterprise-rebranding/nytro-5550-5350-ssd/"
            "nytro-5550-5350-ssd-DS2099-4-2410US-en_US.pdf"
        )

    def test_raw_path_preserved(self) -> None:
        """Raw datasheet path from the record is preserved exactly."""
        result = extract_datasheet_link(
            document=REAL_SUPPORT_DOC,
            sku_number="XP15360SE70005",
        )
        assert result is not None
        # Exact raw path from the support record
        assert result.datasheet_path.startswith("/content/dam/seagate")
        assert result.datasheet_path.endswith("-en_US.pdf")
