"""Error hierarchy for the report package."""


class PdfExportError(Exception):
    """Raised when xhtml2pdf fails or reports unrecoverable errors."""
