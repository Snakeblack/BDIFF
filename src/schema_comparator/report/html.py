"""Render a self-contained HTML schema-drift report from a ComparisonResult."""

from itertools import groupby

from jinja2 import Environment, PackageLoader, select_autoescape

from schema_comparator.compare.models import (
    ColumnMismatch,
    ComparisonResult,
    MissingColumn,
    MissingTable,
)

_env = Environment(
    loader=PackageLoader("schema_comparator.report", "templates"),
    autoescape=select_autoescape(["html", "jinja"]),
)
_env.filters["lower_kebab"] = lambda value: "".join(
    "-" + c.lower() if c.isupper() else c for c in value
).lstrip("-")

def _read_pico_css() -> str:
    source, _, _ = _env.loader.get_source(_env, "pico.min.css")
    return source


_PICO_CSS_INLINE = _read_pico_css()


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
    cells: dict[str, dict | None] = dict.fromkeys(profiles)
    row_label = None
    if isinstance(entry, (MissingTable, MissingColumn)):
        cells[entry.missing_from_profile] = {"kind": "missing", "text": "\u2014"}
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
    """Build the pure dict-shaped template context for `result` (no Jinja2
    involved). `result.entries` is consumed strictly in engine order — it
    is grouped via `itertools.groupby` for display, never re-sorted."""
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
    """Render `result` to a single self-contained HTML string (inline
    CSS only, no external asset loads)."""
    template = _env.get_template("report.html.jinja")
    return template.render(pico_css_inline=_PICO_CSS_INLINE, **build_context(result))
