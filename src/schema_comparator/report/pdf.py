"""Convert an already-rendered HTML string to PDF bytes via xhtml2pdf."""

import io

from xhtml2pdf import pisa

from schema_comparator.report.errors import PdfExportError


def export_pdf(html: str) -> bytes:
    """Convert `html` to PDF bytes.

    Raises `PdfExportError` (never a raw xhtml2pdf/reportlab exception) if
    conversion fails outright or `pisa.CreatePDF` reports unrecoverable
    errors. `xhtml2pdf` does not always raise on unsupported CSS — it can
    return `err > 0` while still producing partial bytes — so both paths
    (exception, and non-zero `err`) are normalized to the same
    `PdfExportError`.
    """
    buffer = io.BytesIO()
    try:
        result = pisa.CreatePDF(src=html, dest=buffer)
    except Exception as exc:  # xhtml2pdf/reportlab exception types vary
        raise PdfExportError(f"PDF conversion failed: {exc}") from exc

    if result.err:
        raise PdfExportError(
            f"PDF conversion reported {result.err} error(s) "
            "(unsupported CSS or malformed HTML)."
        )

    return buffer.getvalue()
