"""MySQL & MariaDB DDL script generator."""

import datetime
import re
from typing import Sequence

from schema_comparator.config.models import ConnectionProfile
from schema_comparator.domain.comparison.models import ColumnAttributes


def quote_identifier(identifier: str) -> str:
    """Quote a MySQL/MariaDB identifier using backticks."""
    escaped = identifier.replace("`", "``")
    return f"`{escaped}`"


def format_mysql_data_type(attrs: ColumnAttributes) -> str:
    """Format MySQL data type string including length, precision, and scale."""
    clean_type = re.sub(r"\s*\(.*\)", "", attrs.data_type).strip()
    type_lower = clean_type.lower()

    if attrs.character_maximum_length is not None and type_lower in ("varchar", "char", "binary", "varbinary"):
        return f"{clean_type}({attrs.character_maximum_length})"
    if attrs.numeric_precision is not None and type_lower in ("decimal", "numeric"):
        if attrs.numeric_scale is not None:
            return f"{clean_type}({attrs.numeric_precision}, {attrs.numeric_scale})"
        return f"{clean_type}({attrs.numeric_precision})"
    # If the original data_type already included custom parameterization (e.g. ENUM, SET, DATETIME(6)), keep it intact
    if "(" in attrs.data_type and ")" in attrs.data_type:
        return attrs.data_type
    return clean_type


def format_mysql_column_definition(col_name: str, attrs: ColumnAttributes) -> str:
    """Format MySQL column definition clause."""
    quoted_col = quote_identifier(col_name)
    type_str = format_mysql_data_type(attrs)
    nullability = "NULL" if attrs.is_nullable else "NOT NULL"

    parts = [quoted_col, type_str, nullability]

    if getattr(attrs, "default_expression", None):
        parts.append(f"DEFAULT {attrs.default_expression}")
    if getattr(attrs, "is_identity", False):
        parts.append("AUTO_INCREMENT")

    return " ".join(parts)


def generate_mysql_script(
    target_profile: ConnectionProfile,
    missing_tables: Sequence[tuple[str, str, Sequence[tuple[str, ColumnAttributes]]]],
    missing_columns: Sequence[tuple[str, str, str, ColumnAttributes]],
    discrepant_columns: Sequence[tuple[str, str, str, ColumnAttributes, ColumnAttributes]],
) -> str:
    """Generate an executable MySQL/MariaDB DDL migration script."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "-- ===========================================================================",
        "-- SCRIPT DE MIGRACIÓN/CORRECCIÓN DE ESQUEMA MYSQL / MARIADB",
        f"-- Perfil Destino: {target_profile.name}",
        f"-- Generado el: {timestamp}",
        "-- ===========================================================================",
        "",
        "SET FOREIGN_KEY_CHECKS = 0;",
        "",
    ]

    # Create missing tables
    if missing_tables:
        lines.append("-- ---------------------------------------------------------------------------")
        lines.append("-- 1. CREACIÓN DE TABLAS FALTANTES")
        lines.append("-- ---------------------------------------------------------------------------")
        for schema, table, columns in missing_tables:
            table_ref = f"{quote_identifier(schema)}.{quote_identifier(table)}" if schema else quote_identifier(table)
            lines.append(f"CREATE TABLE IF NOT EXISTS {table_ref} (")
            col_defs = [f"    {format_mysql_column_definition(cname, attrs)}" for cname, attrs in columns]
            lines.append(",\n".join(col_defs))
            lines.append(") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;")
            lines.append("")

    # Add missing columns
    if missing_columns:
        lines.append("-- ---------------------------------------------------------------------------")
        lines.append("-- 2. ADICIÓN DE COLUMNAS FALTANTES")
        lines.append("-- ---------------------------------------------------------------------------")
        for schema, table, col_name, attrs in missing_columns:
            table_ref = f"{quote_identifier(schema)}.{quote_identifier(table)}" if schema else quote_identifier(table)
            col_def = format_mysql_column_definition(col_name, attrs)
            lines.append(f"ALTER TABLE {table_ref} ADD COLUMN {col_def};")
        lines.append("")

    # Alter discrepant columns
    if discrepant_columns:
        lines.append("-- ---------------------------------------------------------------------------")
        lines.append("-- 3. MODIFICACIÓN DE COLUMNAS CON DISCREPANCIAS")
        lines.append("-- ---------------------------------------------------------------------------")
        for schema, table, col_name, _baseline_attrs, target_attrs in discrepant_columns:
            table_ref = f"{quote_identifier(schema)}.{quote_identifier(table)}" if schema else quote_identifier(table)
            col_def = format_mysql_column_definition(col_name, target_attrs)
            lines.append(f"ALTER TABLE {table_ref} MODIFY COLUMN {col_def};")
        lines.append("")

    lines.append("SET FOREIGN_KEY_CHECKS = 1;")
    lines.append("")
    return "\n".join(lines)
