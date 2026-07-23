"""Plain-text console summary of a ComparisonResult (no HTML/PDF I/O)."""

from itertools import groupby

from schema_comparator.compare.models import (
    ColumnMismatch,
    ComparisonResult,
    ForeignKeyMismatch,
    IndexMismatch,
    MissingColumn,
    MissingProcedure,
    MissingTable,
    PrimaryKeyMismatch,
    ProcedureMismatch,
)
from schema_comparator.report.attributes import format_attributes

_TYPE_LABELS = {
    MissingTable: "Tablas faltantes",
    MissingColumn: "Columnas faltantes",
    ColumnMismatch: "Discrepancias de columnas",
    PrimaryKeyMismatch: "Discrepancias de PK",
    ForeignKeyMismatch: "Discrepancias de FK",
    IndexMismatch: "Discrepancias de índices",
    MissingProcedure: "Procedimientos almacenados faltantes",
    ProcedureMismatch: "Discrepancias de procedimientos almacenados",
}


def render_console(result: ComparisonResult) -> str:
    """Render a human-readable console summary of `result`.

    Pure function of `ComparisonResult` only — never receives HTML/PDF
    output, so it is independent of whether those steps succeeded.
    """
    lines: list[str] = []
    lines.append("Reporte de Diferencias de Esquema - Resumen de Consola")
    lines.append(f"Perfiles comparados: {', '.join(result.compared_profiles)}")
    lines.append("")

    if not result.entries:
        lines.append("No se detectaron diferencias entre los perfiles comparados.")
        return "\n".join(lines)

    counts = {t: 0 for t in _TYPE_LABELS}
    for entry in result.entries:
        if type(entry) in counts:
            counts[type(entry)] += 1
    lines.append("Hallazgos por categoría:")
    for entry_type, label in _TYPE_LABELS.items():
        if counts[entry_type] > 0 or entry_type in (MissingTable, MissingColumn, ColumnMismatch):
            lines.append(f"  {label}: {counts[entry_type]}")
    lines.append("")

    lines.append("Detalle por objeto/tabla/procedimiento:")
    for (schema, table), entries in groupby(result.entries, key=lambda e: e.qualified_name):
        table_entries = list(entries)
        lines.append(f"  {schema}.{table}: {len(table_entries)} hallazgo(s)")
        for entry in table_entries:
            if isinstance(entry, MissingTable):
                lines.append(f"    - tabla faltante (de {entry.missing_from_profile})")
            elif isinstance(entry, MissingColumn):
                present = ", ".join(
                    f"{profile}={format_attributes(attrs)}"
                    for profile, attrs in entry.present_attributes
                )
                suffix = f" (presente como {present})" if present else ""
                lines.append(
                    f"    - {entry.column_name}: columna faltante "
                    f"(de {entry.missing_from_profile}){suffix}"
                )
            elif isinstance(entry, MissingProcedure):
                lines.append(
                    f"    - procedimiento almacenado/rutina faltante (de {entry.missing_from_profile})"
                )
            elif isinstance(entry, ProcedureMismatch):
                profiles = ", ".join(p for p, _ in entry.values_by_profile)
                lines.append(
                    f"    - procedimiento almacenado/rutina: discrepancia de código o parámetros entre {profiles}"
                )
            elif isinstance(entry, ColumnMismatch):
                profiles = ", ".join(p for p, _ in entry.values_by_profile)
                lines.append(
                    f"    - {entry.column_name}: discrepancia de atributos entre {profiles}"
                )
            else:
                lines.append(f"    - discrepancia en {type(entry).__name__}")

    return "\n".join(lines)

