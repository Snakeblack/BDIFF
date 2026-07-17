"""Logic for schema consolidation decisions and SQL Server DDL generation (Enterprise-grade)."""

import re
import datetime
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from schema_comparator.compare.models import ColumnAttributes, NamedColumnAttributes
from schema_comparator.config.models import ConnectionProfile


@dataclass(frozen=True, slots=True)
class ColumnResolution:
    """Represents a decision to consolidate a single column mismatch or missing column."""

    schema_name: str
    table_name: str
    column_name: str
    target_attributes: ColumnAttributes
    profiles_to_update: tuple[str, ...]
    is_missing_column: bool


@dataclass(frozen=True, slots=True)
class TableResolution:
    """Represents a decision to create a missing table with the full column definition."""

    schema_name: str
    table_name: str
    columns: tuple[NamedColumnAttributes, ...]
    profiles_to_update: tuple[str, ...]


class TableAction(str, Enum):
    """Actions available for a table-level consolidation decision."""

    DROP = "drop"


@dataclass(frozen=True, slots=True)
class TableDeletionResolution:
    """Represents a decision to remove a table from selected profiles."""

    schema_name: str
    table_name: str
    profiles_to_update: tuple[str, ...]


class ColumnAction(str, Enum):
    """Actions available for a column-level consolidation decision."""

    DROP = "drop"


@dataclass(frozen=True, slots=True)
class ColumnDeletionResolution:
    """Represents a decision to remove a column from selected profiles."""

    schema_name: str
    table_name: str
    column_name: str
    profiles_to_update: tuple[str, ...]


def extract_database_name(connection_string: str) -> str | None:
    """Extract the database name (Initial Catalog or Database) from a SQL Server connection string."""
    pattern = re.compile(r'(?:database|initial catalog|db)\s*=\s*([^;]+)', re.IGNORECASE)
    match = pattern.search(connection_string)
    if match:
        return match.group(1).strip()
    return None


def format_sql_column_definition(attrs: ColumnAttributes) -> str:
    """Format column attributes to their corresponding SQL Server (T-SQL) definition."""
    if attrs.character_maximum_length is not None:
        size = "MAX" if attrs.character_maximum_length == -1 else str(attrs.character_maximum_length)
        type_str = f"{attrs.data_type}({size})"
    elif attrs.numeric_precision is not None:
        if attrs.numeric_scale is not None:
            type_str = f"{attrs.data_type}({attrs.numeric_precision}, {attrs.numeric_scale})"
        else:
            type_str = f"{attrs.data_type}({attrs.numeric_precision})"
    else:
        type_str = attrs.data_type

    nullability = "NULL" if attrs.is_nullable else "NOT NULL"
    return f"{type_str} {nullability}"


def generate_ddl_for_profile(
    resolutions: list[ColumnResolution],
    profile: ConnectionProfile,
    timestamp: datetime.datetime | None = None,
    table_resolutions: list[TableResolution] | None = None,
    table_deletions: list[TableDeletionResolution] | None = None,
    column_deletions: list[ColumnDeletionResolution] | None = None,
) -> str:
    """Generate transactional, idempotent, enterprise-grade T-SQL scripts for a profile."""
    ts = timestamp or datetime.datetime.now()
    db_name = extract_database_name(profile.connection_string) or profile.name
    
    lines = [
        f"-- Script de corrección para la base de datos del perfil: {profile.name}",
        f"-- Generado por BDIFF el {ts.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"USE [{db_name}];",
        "GO",
        "",
        "SET NUMERIC_ROUNDABORT OFF;",
        "SET ANSI_PADDING, ANSI_WARNINGS, CONCAT_NULL_YIELDS_NULL, ARITHABORT, QUOTED_IDENTIFIER, ANSI_NULLS ON;",
        "GO",
        "",
        "BEGIN TRANSACTION;",
        "BEGIN TRY",
    ]
    
    statements_added = False

    # CREATE TABLE statements (tables missing from this profile)
    for tres in (table_resolutions or []):
        if profile.name in tres.profiles_to_update:
            col_defs = []
            for ncol in tres.columns:
                col_def = format_sql_column_definition(ncol.attributes)
                col_defs.append(f"        [{ncol.name}] {col_def}")
            col_list = ",\n".join(col_defs)

            sql = (
                f"    IF NOT EXISTS (\n"
                f"        SELECT 1\n"
                f"        FROM sys.objects o\n"
                f"        JOIN sys.schemas s ON o.schema_id = s.schema_id\n"
                f"        WHERE s.name = '{tres.schema_name}' AND o.name = '{tres.table_name}' AND o.type = 'U'\n"
                f"    )\n"
                f"    BEGIN\n"
                f"        CREATE TABLE [{tres.schema_name}].[{tres.table_name}] (\n"
                f"{col_list}\n"
                f"        );\n"
                f"        PRINT 'Tabla [{tres.schema_name}].[{tres.table_name}] creada con exito.';\n"
                f"    END"
            )
            lines.append(sql)
            statements_added = True

    # DROP TABLE statements (tables selected for removal from this profile)
    for deletion in (table_deletions or []):
        if profile.name in deletion.profiles_to_update:
            sql = (
                f"    IF EXISTS (\n"
                f"        SELECT 1\n"
                f"        FROM sys.objects o\n"
                f"        JOIN sys.schemas s ON o.schema_id = s.schema_id\n"
                f"        WHERE s.name = '{deletion.schema_name}' AND o.name = '{deletion.table_name}' AND o.type = 'U'\n"
                f"    )\n"
                f"    BEGIN\n"
                f"        DROP TABLE [{deletion.schema_name}].[{deletion.table_name}];\n"
                f"        PRINT 'Tabla [{deletion.schema_name}].[{deletion.table_name}] eliminada con exito.';\n"
                f"    END"
            )
            lines.append(sql)
            statements_added = True

    # DROP COLUMN statements (columns selected for removal from this profile)
    for deletion in (column_deletions or []):
        if profile.name in deletion.profiles_to_update:
            sql = (
                f"    IF EXISTS (\n"
                f"        SELECT 1\n"
                f"        FROM sys.columns c\n"
                f"        JOIN sys.objects o ON c.object_id = o.object_id\n"
                f"        JOIN sys.schemas s ON o.schema_id = s.schema_id\n"
                f"        WHERE s.name = '{deletion.schema_name}' AND o.name = '{deletion.table_name}' AND c.name = '{deletion.column_name}'\n"
                f"    )\n"
                f"    BEGIN\n"
                f"        ALTER TABLE [{deletion.schema_name}].[{deletion.table_name}] DROP COLUMN [{deletion.column_name}];\n"
                f"        PRINT 'Columna [{deletion.column_name}] eliminada con exito de [{deletion.schema_name}].[{deletion.table_name}].';\n"
                f"    END"
            )
            lines.append(sql)
            statements_added = True

    # ALTER TABLE / ADD COLUMN statements
    for res in resolutions:
        if profile.name in res.profiles_to_update:
            col_def = format_sql_column_definition(res.target_attributes)
            if res.is_missing_column:
                # Idempotency check: Add column only if it does not already exist
                sql = (
                    f"    IF NOT EXISTS (\n"
                    f"        SELECT 1 \n"
                    f"        FROM sys.columns c\n"
                    f"        JOIN sys.objects o ON c.object_id = o.object_id\n"
                    f"        JOIN sys.schemas s ON o.schema_id = s.schema_id\n"
                    f"        WHERE s.name = '{res.schema_name}' AND o.name = '{res.table_name}' AND c.name = '{res.column_name}'\n"
                    f"    )\n"
                    f"    BEGIN\n"
                    f"        ALTER TABLE [{res.schema_name}].[{res.table_name}] ADD [{res.column_name}] {col_def};\n"
                    f"        PRINT 'Columna [{res.column_name}] agregada con exito a [{res.schema_name}].[{res.table_name}].';\n"
                    f"    END"
                )
            else:
                # Idempotency check: Alter column only if it exists
                sql = (
                    f"    IF EXISTS (\n"
                    f"        SELECT 1 \n"
                    f"        FROM sys.columns c\n"
                    f"        JOIN sys.objects o ON c.object_id = o.object_id\n"
                    f"        JOIN sys.schemas s ON o.schema_id = s.schema_id\n"
                    f"        WHERE s.name = '{res.schema_name}' AND o.name = '{res.table_name}' AND c.name = '{res.column_name}'\n"
                    f"    )\n"
                    f"    BEGIN\n"
                    f"        ALTER TABLE [{res.schema_name}].[{res.table_name}] ALTER COLUMN [{res.column_name}] {col_def};\n"
                    f"        PRINT 'Columna [{res.column_name}] de [{res.schema_name}].[{res.table_name}] modificada con exito.';\n"
                    f"    END"
                )
            lines.append(sql)
            statements_added = True

    if not statements_added:
        lines.append("    PRINT 'No se requieren cambios para este perfil.';")
        
    lines.extend([
        "",
        "    COMMIT TRANSACTION;",
        "    PRINT 'Transaccion confirmada con exito.';",
        "END TRY",
        "BEGIN CATCH",
        "    IF @@TRANCOUNT > 0",
        "    BEGIN",
        "        ROLLBACK TRANSACTION;",
        "        PRINT 'Transaccion abortada debido a un error.';",
        "    END",
        "    DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();",
        "    DECLARE @ErrorSeverity INT = ERROR_SEVERITY();",
        "    DECLARE @ErrorState INT = ERROR_STATE();",
        "    RAISERROR(@ErrorMessage, @ErrorSeverity, @ErrorState);",
        "END CATCH;",
        "GO",
    ])
    
    return "\n".join(lines) + "\n"


def write_sql_scripts(
    resolutions: list[ColumnResolution],
    repo_root: str | Path,
    profiles: list[ConnectionProfile],
    timestamp: datetime.datetime | None = None,
    table_resolutions: list[TableResolution] | None = None,
    table_deletions: list[TableDeletionResolution] | None = None,
    column_deletions: list[ColumnDeletionResolution] | None = None,
) -> list[str]:
    """Create the 'scripts-db' directory and write transactional DDL files for all affected profiles."""
    root_path = Path(repo_root)
    output_dir = root_path / "scripts-db"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    ts = timestamp or datetime.datetime.now()
    profile_map = {p.name: p for p in profiles}
    
    # We collect all profiles that need updates
    all_profiles_names = set()
    for res in resolutions:
        all_profiles_names.update(res.profiles_to_update)
    for tres in (table_resolutions or []):
        all_profiles_names.update(tres.profiles_to_update)
    for deletion in (table_deletions or []):
        all_profiles_names.update(deletion.profiles_to_update)
    for deletion in (column_deletions or []):
        all_profiles_names.update(deletion.profiles_to_update)
        
    written_files = []
    for profile_name in sorted(all_profiles_names):
        # Fallback profile creation if not matched (e.g. legacy tests)
        profile = profile_map.get(
            profile_name, 
            ConnectionProfile(name=profile_name, connection_string=f"Database={profile_name};")
        )
        ddl = generate_ddl_for_profile(
            resolutions,
            profile,
            timestamp=ts,
            table_resolutions=table_resolutions,
            table_deletions=table_deletions,
            column_deletions=column_deletions,
        )
        safe_profile = Path(profile_name).name
        file_path = output_dir / f"{safe_profile}.sql"
        file_path.write_text(ddl, encoding="utf-8")
        written_files.append(str(file_path.resolve()))
        
    return written_files

