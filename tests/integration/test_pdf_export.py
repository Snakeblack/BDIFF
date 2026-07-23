"""Integration spike-test: real, un-mocked xhtml2pdf against the actual
report template + overlay CSS. This is the required CSS-compatibility
check from the proposal — kept afterward as a permanent regression guard
so a future CSS change that xhtml2pdf cannot render fails loudly here
rather than only surfacing as a silent PdfExportError in production."""

from schema_comparator.compare.models import ColumnMismatch, ComparisonResult
from schema_comparator.compare.models import (
    ColumnAttributes,
    MissingColumn,
    MissingTable,
)
from schema_comparator.report.html import render_html
from schema_comparator.report.pdf import export_pdf


def _fixture_result() -> ComparisonResult:
    return ComparisonResult(
        compared_profiles=("a", "b", "c"),
        entries=(
            MissingColumn(
                schema_name="sales",
                table_name="Invoice",
                column_name="notes",
                missing_from_profile="c",
            ),
            ColumnMismatch(
                schema_name="sales",
                table_name="Invoice",
                column_name="amount",
                values_by_profile=(
                    (
                        "a",
                        ColumnAttributes(
                            data_type="decimal",
                            character_maximum_length=None,
                            numeric_precision=10,
                            numeric_scale=2,
                            is_nullable=False,
                        ),
                    ),
                    (
                        "b",
                        ColumnAttributes(
                            data_type="decimal",
                            character_maximum_length=None,
                            numeric_precision=12,
                            numeric_scale=2,
                            is_nullable=False,
                        ),
                    ),
                ),
            ),
            MissingTable(
                schema_name="sales",
                table_name="Payment",
                missing_from_profile="c",
            ),
        ),
    )


def test_export_pdf_produces_valid_pdf_bytes_from_rendered_html() -> None:
    html = render_html(_fixture_result())

    pdf_bytes = export_pdf(html)

    assert pdf_bytes
    assert pdf_bytes.startswith(b"%PDF-")
