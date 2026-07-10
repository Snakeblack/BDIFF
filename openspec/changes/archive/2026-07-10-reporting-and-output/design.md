# Design: Reporting and Output

Change: `reporting-and-output`
Status: design (phase artifact)
Scope: three read-only renderers over a `ComparisonResult` — an HTML report
(Jinja2), a PDF export derived from that same HTML (`xhtml2pdf`), and a
plain-text console summary — plus enough `cli.py` argument parsing to run a
comparison and invoke all three with per-format failure isolation. No
diff-detection logic changes; `compare/` is a frozen, read-only input.

This design realizes the 7 requirements / 20 scenarios in
`openspec/changes/reporting-and-output/specs/reporting-and-output/spec.md`
and the four decisions recorded in
`openspec/changes/reporting-and-output/proposal.md` (timestamped file
naming, N-way column-per-profile layout, no CLI `--format` flag in v1,
`Jinja2` + `xhtml2pdf` as new dependencies).

---

## 1. Module / file layout

```text
src/schema_comparator/report/
  __init__.py            # public API surface: re-exports render_html, export_pdf,
                          # render_console, write_reports
  html.py                # render_html(result) -> str  (Jinja2)
  pdf.py                 # export_pdf(html) -> bytes    (xhtml2pdf, may raise PdfExportError)
  console.py             # render_console(result) -> str
  errors.py              # PdfExportError
  templates/
    report.html.jinja    # single Jinja2 template, inline Pico.css + overlay <style>

src/schema_comparator/cli.py   # extended: argparse + write_reports() orchestration
```

`tui/` is **not touched** by this change (per the proposal's Out of Scope
and Decision 3): `src/schema_comparator/tui/__init__.py` remains the
existing docstring-only placeholder for the future interactive Textual
shell. Nothing in this change's scope (HTML/PDF/console rendering, CLI
argument parsing for report output) belongs there.

This mirrors the `compare/` and `discovery/` package shape (`models`-less
here since `report/` has no data model of its own — it only ever reads
`compare.models` types — but keeps the same `errors.py` + one-module-per-
concern split). `templates/` is new and specific to this package, holding
the one Jinja2 template asset.

### Public API (`report/__init__.py`)

```python
from schema_comparator.report.html import render_html
from schema_comparator.report.pdf import export_pdf
from schema_comparator.report.console import render_console
from schema_comparator.report.errors import PdfExportError
from schema_comparator.report.write import write_reports

__all__ = [
    "render_html",
    "export_pdf",
    "render_console",
    "PdfExportError",
    "write_reports",
]
```

`write_reports(result, *, out=sys.stdout)` (in a new `report/write.py`) is
the single orchestration function `cli.py` calls: it owns the shared run
timestamp, the failure-isolation wrapping described in §5, and prints the
console summary. Keeping this orchestration inside `report/` (not inline in
`cli.py`) keeps `cli.py` a thin argument-parsing shell and makes the
failure-isolation behavior itself unit-testable without invoking argparse.

---

## 2. Input contract: `ComparisonResult` (read-only)

All three renderers accept only `schema_comparator.compare.models.
ComparisonResult` (and, transitively, `MissingTable`, `MissingColumn`,
`ColumnMismatch`, `ColumnAttributes`) as already defined in
[models.py](../../../src/schema_comparator/compare/models.py). No new
model is introduced in `report/`. Each entry type's exact fields, as
consumed by rendering:

| Type | Fields used | Rendering role |
|---|---|---|
| `MissingTable` | `schema_name`, `table_name`, `missing_from_profile` | one row; missing marker in one profile column |
| `MissingColumn` | `schema_name`, `table_name`, `column_name`, `missing_from_profile` | one row; missing marker in one profile column |
| `ColumnMismatch` | `schema_name`, `table_name`, `column_name`, `values_by_profile: tuple[tuple[str, ColumnAttributes], ...]` | one row; compact attribute string per present profile |
| `ComparisonResult` | `compared_profiles: tuple[str, ...]`, `entries: tuple[DiffEntry, ...]` | header row profile order; `entries` iterated as-is (already sorted by the engine — never re-sorted here) |

`entries` is consumed strictly in the order the engine already produced
(REQ-reporting-and-output-001's "without re-sorting or reshaping the
sequence"). All three renderers group by `(schema_name, table_name)` for
display purposes only, using `itertools.groupby` over the already-sorted
sequence (valid because the engine's `_sort_key` groups by qualified table
identity first) — never `sorted()`/`dict`-then-iterate, which would risk
silently reordering.

---

## 3. HTML rendering (`report/html.py` + Jinja2 template)

### 3.1 Context-building function

```python
# report/html.py
from dataclasses import asdict
from itertools import groupby

from jinja2 import Environment, PackageLoader, select_autoescape

from schema_comparator.compare.models import (
    ColumnMismatch, ComparisonResult, MissingColumn, MissingTable,
)

_env = Environment(
    loader=PackageLoader("schema_comparator.report", "templates"),
    autoescape=select_autoescape(["html", "jinja"]),
)


def _format_attributes(attrs) -> str:
    """`varchar(50), NULL` / `decimal(10,2), NOT NULL` style compact string."""
    if attrs.character_maximum_length is not None:
        size = f"({attrs.character_maximum_length})"
    elif attrs.numeric_precision is not None:
        scale = f",{attrs.numeric_scale}" if attrs.numeric_scale is not None else ""
        size = f"({attrs.numeric_precision}{scale})"
    else:
        size = ""
    nullability = "NULL" if attrs.is_nullable else "NOT NULL"
    return f"{attrs.data_type}{size}, {nullability}"


def _row_for_entry(entry, profiles: tuple[str, ...]) -> dict:
    """Build a {profile_name: cell_value_or_None} dict, plus row metadata,
    for one diff entry — the one row-rendering shape shared by all three
    DiffEntry variants."""
    cells = dict.fromkeys(profiles)
    if isinstance(entry, (MissingTable, MissingColumn)):
        cells[entry.missing_from_profile] = {"kind": "missing", "text": "—"}
        row_label = entry.column_name if isinstance(entry, MissingColumn) else None
    elif isinstance(entry, ColumnMismatch):
        for profile, attrs in entry.values_by_profile:
            cells[profile] = {"kind": "value", "text": _format_attributes(attrs)}
        row_label = entry.column_name
    return {
        "diff_type": type(entry).__name__,
        "column_name": row_label,
        "cells": cells,
    }


def build_context(result: ComparisonResult) -> dict:
    groups = []
    for (schema, table), entries in groupby(
        result.entries, key=lambda e: e.qualified_name
    ):
        rows = [_row_for_entry(e, result.compared_profiles) for e in entries]
        groups.append({"schema_name": schema, "table_name": table, "rows": rows})
    return {
        "compared_profiles": result.compared_profiles,
        "groups": groups,
        "has_findings": bool(result.entries),
    }


def render_html(result: ComparisonResult) -> str:
    template = _env.get_template("report.html.jinja")
    return template.render(**build_context(result))
```

`build_context` is a pure function, independently unit-testable without
touching Jinja2 at all (asserts on the dict shape), matching
`stack-python-testing`'s "test one thing per test."

### 3.2 Template data context (passed to `report.html.jinja`)

```text
compared_profiles: tuple[str, ...]        # header row order
groups: list[{
    schema_name: str,
    table_name: str,
    rows: list[{
        diff_type: "MissingTable" | "MissingColumn" | "ColumnMismatch",
        column_name: str | None,           # None for MissingTable
        cells: dict[profile_name, {"kind": "missing" | "value", "text": str} | None],
    }]
}]
has_findings: bool                         # False => render "no drift detected" block only
```

### 3.3 Template structure (`templates/report.html.jinja`)

```jinja
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Schema Drift Report</title>
  <style>
    {# Pico.css minified content inlined verbatim here — technical-baseline
       decision #9. No <link> to an external stylesheet. #}
    {{ pico_css_inline }}
    /* --- overlay: diff-type row coloring, kept deliberately simple
       (background-color, borders, basic fonts) per xhtml2pdf's constrained
       CSS subset --- */
    .diff-missing-table  { background-color: #fde2e1; }
    .diff-missing-column { background-color: #fff3cd; }
    .diff-mismatch        { background-color: #d9edf7; }
    td.cell-missing       { text-align: center; color: #999; }
    .no-drift              { border: 1px solid #2e7d32; padding: 1rem; }
  </style>
</head>
<body>
  <main class="container">
    <h1>Schema Drift Report</h1>
    <p>Compared profiles: {{ compared_profiles | join(", ") }}</p>

    {% if not has_findings %}
      <p class="no-drift">No drift detected across all compared profiles.</p>
    {% else %}
      {% for group in groups %}
        <h2>{{ group.schema_name }}.{{ group.table_name }}</h2>
        <table>
          <thead>
            <tr>
              <th>Column</th>
              {% for profile in compared_profiles %}<th>{{ profile }}</th>{% endfor %}
            </tr>
          </thead>
          <tbody>
            {% for row in group.rows %}
              <tr class="diff-{{ row.diff_type | lower_kebab }}">
                <td>{{ row.column_name or "(table)" }}</td>
                {% for profile in compared_profiles %}
                  {% set cell = row.cells[profile] %}
                  <td class="{{ 'cell-missing' if cell and cell.kind == 'missing' else '' }}">
                    {{ cell.text if cell else "" }}
                  </td>
                {% endfor %}
              </tr>
            {% endfor %}
          </tbody>
        </table>
      {% endfor %}
    {% endif %}
  </main>
</body>
</html>
```

`pico_css_inline` is passed into the render call as a module-level constant
string (Pico.css's minified content, read once from a small vendored asset
file at import time) — not fetched at render time, keeping `render_html`
free of I/O beyond the one-time module import.

This directly satisfies REQ-reporting-and-output-001 (grouped/ordered
findings, header row lists every profile) and REQ-reporting-and-output-006
(explicit "no drift detected" block, never an empty table).

---

## 4. PDF export (`report/pdf.py`) — signature and graceful degradation

```python
# report/pdf.py
import io

from xhtml2pdf import pisa

from schema_comparator.report.errors import PdfExportError


def export_pdf(html: str) -> bytes:
    """Convert an already-rendered HTML string to PDF bytes via xhtml2pdf.

    Raises `PdfExportError` (never a raw xhtml2pdf/lower-level exception)
    if conversion fails outright or `pisa.CreatePDF` reports unrecoverable
    errors. `xhtml2pdf` does not always raise on unsupported CSS — it can
    return `err > 0` while still producing partial bytes — so both paths
    (exception, and non-zero `err` with empty output) are normalized to the
    same `PdfExportError`.
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
```

```python
# report/errors.py
class PdfExportError(Exception):
    """Raised when xhtml2pdf fails or reports unrecoverable errors."""
```

`export_pdf` never writes to disk — it takes/returns strings/bytes only
(mirrors `render_html`'s no-I/O discipline). The caller (`write_reports`,
§5) is responsible for both catching `PdfExportError` and for the
file-write step, keeping this function's contract narrow and independently
unit-testable by mocking `pisa.CreatePDF`.

---

## 5. Console summary (`report/console.py`) — exact text structure

```python
# report/console.py
from schema_comparator.compare.models import ColumnMismatch, ComparisonResult, MissingColumn, MissingTable

_TYPE_LABELS = {
    MissingTable: "Missing tables",
    MissingColumn: "Missing columns",
    ColumnMismatch: "Column mismatches",
}


def render_console(result: ComparisonResult) -> str:
    lines: list[str] = []
    lines.append("Schema Drift Report — Console Summary")
    lines.append(f"Compared profiles: {', '.join(result.compared_profiles)}")
    lines.append("")

    if not result.entries:
        lines.append("No drift detected across all compared profiles.")
        return "\n".join(lines)

    counts = {t: 0 for t in _TYPE_LABELS}
    for entry in result.entries:
        counts[type(entry)] += 1
    lines.append("Findings by category:")
    for entry_type, label in _TYPE_LABELS.items():
        lines.append(f"  {label}: {counts[entry_type]}")
    lines.append("")

    lines.append("Per-table breakdown:")
    from itertools import groupby
    for (schema, table), entries in groupby(result.entries, key=lambda e: e.qualified_name):
        entries = list(entries)
        lines.append(f"  {schema}.{table}: {len(entries)} finding(s)")
        for e in entries:
            if isinstance(e, MissingTable):
                lines.append(f"    - missing table (from {e.missing_from_profile})")
            elif isinstance(e, MissingColumn):
                lines.append(f"    - {e.column_name}: missing column (from {e.missing_from_profile})")
            else:
                profiles = ", ".join(p for p, _ in e.values_by_profile)
                lines.append(f"    - {e.column_name}: attribute mismatch across {profiles}")

    return "\n".join(lines)
```

Example output (no-drift case, REQ-reporting-and-output-006):

```
Schema Drift Report — Console Summary
Compared profiles: a, b

No drift detected across all compared profiles.
```

Example output (with findings, REQ-reporting-and-output-005):

```
Schema Drift Report — Console Summary
Compared profiles: a, b, c

Findings by category:
  Missing tables: 2
  Missing columns: 3
  Column mismatches: 1

Per-table breakdown:
  sales.Invoice: 2 finding(s)
    - notes: missing column (from c)
    - amount: attribute mismatch across a, b
  sales.Payment: 4 finding(s)
    - missing table (from c)
    ...
```

`render_console` is a pure function of `ComparisonResult` with zero
dependency on `render_html`/`export_pdf` — it satisfies
REQ-reporting-and-output-005's "independent of whether HTML or PDF
generation succeeded or failed" by construction (it is never called with
their output, only with the shared `ComparisonResult`).

---

## 6. CLI wiring and failure isolation (`report/write.py` + `cli.py`)

### 6.1 `report/write.py` — orchestration with per-format isolation

```python
# report/write.py
import sys
from datetime import datetime

from schema_comparator.compare.models import ComparisonResult
from schema_comparator.report.console import render_console
from schema_comparator.report.errors import PdfExportError
from schema_comparator.report.html import render_html
from schema_comparator.report.pdf import export_pdf


def write_reports(result: ComparisonResult, *, out=sys.stdout) -> None:
    """Always attempt all three outputs; one failing MUST NOT block the
    others (REQ-reporting-and-output-007). Failures are printed to `out`
    as clearly labeled messages, never raised past this function."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    html_str: str | None = None

    try:
        html_str = render_html(result)
        html_path = f"schema-diff-report-{timestamp}.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_str)
        print(f"HTML report written: {html_path}", file=out)
    except Exception as exc:
        print(f"[ERROR] HTML report generation failed: {exc}", file=out)

    try:
        if html_str is None:
            raise PdfExportError("skipped: HTML rendering did not complete")
        pdf_bytes = export_pdf(html_str)
        pdf_path = f"schema-diff-report-{timestamp}.pdf"
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)
        print(f"PDF report written: {pdf_path}", file=out)
    except Exception as exc:
        print(f"[ERROR] PDF report generation failed: {exc}", file=out)

    try:
        print(render_console(result), file=out)
    except Exception as exc:
        print(f"[ERROR] Console summary generation failed: {exc}", file=out)
```

Each of the three blocks is an independent `try/except Exception`, matching
REQ-reporting-and-output-007's three scenarios verbatim: an HTML failure
still attempts PDF and console; a PDF failure (including the CSS-degradation
case, REQ-reporting-and-output-004) still leaves HTML written and console
printed; a console-formatting failure still leaves HTML/PDF written. The
single shared `timestamp` is computed once, before any block, so both
filenames stay paired even if one of the writes fails.

### 6.2 `cli.py` wiring — placement relative to the engine call

```python
# cli.py (extended)
import argparse

from schema_comparator.compare.engine import compare_snapshots
from schema_comparator.config.loader import load_profiles
from schema_comparator.discovery.service import discover_schema  # existing call site
from schema_comparator.report.write import write_reports


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="schema-comparator")
    parser.add_argument("--config", required=True, help="Path to connection profiles YAML")
    parser.add_argument("--profiles", nargs="+", help="Subset of profile names to compare (default: all)")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_arg_parser().parse_args(argv)
    profiles = load_profiles(args.config)
    if args.profiles:
        profiles = [p for p in profiles if p.name in args.profiles]

    snapshots = [discover_schema(p) for p in profiles]
    result = compare_snapshots(snapshots)

    write_reports(result)  # always all three; no --format flag (Decision 3)


if __name__ == "__main__":
    main()
```

`write_reports(result)` is called exactly once, immediately after
`compare_snapshots` returns and before `main` exits — there is no branching
on a format flag (Decision 3: v1 always produces all three outputs). Any
exception raised by `load_profiles`/`discover_schema`/`compare_snapshots`
themselves (config errors, connection errors, precondition errors) is
**not** caught here — those are pre-existing failure domains outside this
change's scope (config/discovery/compare already define their own error
hierarchies) and MUST still abort the run before any reporting is
attempted, since there is no `ComparisonResult` to report on yet.
