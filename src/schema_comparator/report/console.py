"""Plain-text console summary of a ComparisonResult (no HTML/PDF I/O)."""

from itertools import groupby

from schema_comparator.compare.models import (
    ColumnMismatch,
    ComparisonResult,
    MissingColumn,
    MissingTable,
)

_TYPE_LABELS = {
    MissingTable: "Missing tables",
    MissingColumn: "Missing columns",
    ColumnMismatch: "Column mismatches",
}


def render_console(result: ComparisonResult) -> str:
    """Render a human-readable console summary of `result`.

    Pure function of `ComparisonResult` only — never receives HTML/PDF
    output, so it is independent of whether those steps succeeded.
    """
    lines: list[str] = []
    lines.append("Schema Drift Report - Console Summary")
    lines.append(f"Compared profiles: {', '.join(result.compared_profiles)}")
    lines.append("")

    if not result.entries:
        lines.append("No drift detected across all compared profiles.")
        return "\n".join(lines)

    counts = dict.fromkeys(_TYPE_LABELS, 0)
    for entry in result.entries:
        counts[type(entry)] += 1
    lines.append("Findings by category:")
    for entry_type, label in _TYPE_LABELS.items():
        lines.append(f"  {label}: {counts[entry_type]}")
    lines.append("")

    lines.append("Per-table breakdown:")
    for (schema, table), entries in groupby(result.entries, key=lambda e: e.qualified_name):
        table_entries = list(entries)
        lines.append(f"  {schema}.{table}: {len(table_entries)} finding(s)")
        for entry in table_entries:
            if isinstance(entry, MissingTable):
                lines.append(f"    - missing table (from {entry.missing_from_profile})")
            elif isinstance(entry, MissingColumn):
                lines.append(
                    f"    - {entry.column_name}: missing column "
                    f"(from {entry.missing_from_profile})"
                )
            else:
                profiles = ", ".join(p for p, _ in entry.values_by_profile)
                lines.append(
                    f"    - {entry.column_name}: attribute mismatch across {profiles}"
                )

    return "\n".join(lines)
