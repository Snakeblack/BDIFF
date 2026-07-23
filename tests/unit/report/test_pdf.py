"""Unit tests for report.pdf: export_pdf with a mocked xhtml2pdf.pisa."""

from unittest.mock import MagicMock, patch

import pytest

from schema_comparator.report.errors import PdfExportError
from schema_comparator.report.pdf import export_pdf


def test_export_pdf_returns_bytes_unchanged_on_success() -> None:
    def fake_create_pdf(src, dest):
        dest.write(b"%PDF-1.4 fake pdf bytes")
        result = MagicMock()
        result.err = 0
        return result

    with patch(
        "schema_comparator.report.pdf.pisa.CreatePDF", side_effect=fake_create_pdf
    ):
        pdf_bytes = export_pdf("<html><body>hi</body></html>")

    assert pdf_bytes == b"%PDF-1.4 fake pdf bytes"


def test_export_pdf_raises_pdf_export_error_when_err_greater_than_zero() -> None:
    fake_result = MagicMock()
    fake_result.err = 2

    with patch("schema_comparator.report.pdf.pisa.CreatePDF", return_value=fake_result):
        with pytest.raises(PdfExportError):
            export_pdf("<html><body>bad css</body></html>")


def test_export_pdf_wraps_underlying_exception_as_pdf_export_error() -> None:
    with patch(
        "schema_comparator.report.pdf.pisa.CreatePDF",
        side_effect=RuntimeError("boom"),
    ):
        with pytest.raises(PdfExportError):
            export_pdf("<html><body>x</body></html>")
