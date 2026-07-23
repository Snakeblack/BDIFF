"""SP dependency checking and post-consolidation verification via sp_refreshsqlmodule."""

from dataclasses import dataclass
import pyodbc


@dataclass(frozen=True, slots=True)
class DependentObject:
    """A database routine or view that depends on a table being consolidated."""

    schema_name: str
    object_name: str
    object_type: str
    referenced_table: str


@dataclass(frozen=True, slots=True)
class RefreshResult:
    """The outcome of executing sp_refreshsqlmodule on a procedure or view."""

    schema_name: str
    object_name: str
    is_success: bool
    error_message: str | None = None


def find_dependent_objects(
    conn: pyodbc.Connection,
    table_names: set[str],
) -> tuple[DependentObject, ...]:
    """Query sys.sql_expression_dependencies for routines depending on table_names."""
    if not table_names:
        return ()

    table_list = list(table_names)
    results: list[DependentObject] = []
    cursor = conn.cursor()

    # Batch queries in chunks of 1000 to respect SQL Server 2100 parameter limit
    chunk_size = 1000
    try:
        for i in range(0, len(table_list), chunk_size):
            chunk = table_list[i : i + chunk_size]
            placeholders = ", ".join("?" for _ in chunk)
            sql = f"""
            SELECT DISTINCT
                s.name AS schema_name,
                o.name AS object_name,
                o.type_desc AS object_type,
                d.referenced_entity_name AS referenced_table
            FROM sys.sql_expression_dependencies d
            JOIN sys.objects o ON d.referencing_id = o.object_id
            JOIN sys.schemas s ON o.schema_id = s.schema_id
            WHERE d.referenced_entity_name IN ({placeholders})
              AND o.type IN ('P', 'FN', 'IF', 'TF', 'TR', 'V')
            ORDER BY schema_name, object_name
            """.strip()

            cursor.execute(sql, chunk)
            for sch, obj, obj_type, ref_tbl in cursor.fetchall():
                results.append(
                    DependentObject(
                        schema_name=sch,
                        object_name=obj,
                        object_type=obj_type,
                        referenced_table=ref_tbl,
                    )
                )
    except pyodbc.Error:
        pass
    finally:
        cursor.close()

    return tuple(results)


def verify_sps_with_refresh(
    conn: pyodbc.Connection,
    objects_to_refresh: tuple[tuple[str, str], ...] | None = None,
) -> tuple[RefreshResult, ...]:
    """Execute sp_refreshsqlmodule for routines and views to detect compilation errors.

    If objects_to_refresh is None, queries all user procedures and views in the database.
    """
    targets: list[tuple[str, str]] = []
    cursor = conn.cursor()

    if objects_to_refresh is None:
        sql = """
        SELECT s.name, o.name
        FROM sys.objects o
        JOIN sys.schemas s ON o.schema_id = s.schema_id
        WHERE o.type IN ('P', 'FN', 'IF', 'TF', 'V') AND o.is_ms_shipped = 0
        ORDER BY s.name, o.name
        """
        try:
            cursor.execute(sql)
            targets = cursor.fetchall()
        except pyodbc.Error:
            targets = []
    else:
        targets = list(objects_to_refresh)

    results: list[RefreshResult] = []
    for schema_name, object_name in targets:
        safe_sch = schema_name.replace("]", "]]")
        safe_obj = object_name.replace("]", "]]")
        qualified = f"[{safe_sch}].[{safe_obj}]"
        try:
            cursor.execute("EXEC sp_refreshsqlmodule @name = ?", (qualified,))
            results.append(
                RefreshResult(
                    schema_name=schema_name,
                    object_name=object_name,
                    is_success=True,
                )
            )
        except pyodbc.Error as exc:
            err_msg = str(exc)
            results.append(
                RefreshResult(
                    schema_name=schema_name,
                    object_name=object_name,
                    is_success=False,
                    error_message=err_msg,
                )
            )

    cursor.close()
    return tuple(results)
