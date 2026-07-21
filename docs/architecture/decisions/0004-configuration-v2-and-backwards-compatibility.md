# 0004. Configuración v2 y Retrocompatibilidad

* Status: accepted
* Date: 2026-07-20

## Context

La configuración v1 de BDIFF utilizaba una clave de nivel superior `databases:` que mapeaba nombres de perfil directamente a cadenas de conexión de SQL Server (`pyodbc` / ADO.NET).

Con la introducción de múltiples proveedores de bases de datos y opciones específicas por motor (como timeouts, rutas de archivo SQLite, o inclusión de esquemas), el formato de configuración debe evolucionar.

## Decision

1. **Nuevo Formato v2 (`profiles:`)**:
   ```yaml
   profiles:
     billing-sqlserver:
       provider: sqlserver
       connection_string: "Driver={ODBC Driver 17 for SQL Server};Server=..."
       options:
         include_schemas: [dbo]
     local-sqlite:
       provider: sqlite
       connection_string: "./data/local.db"
   ```

2. **Retrocompatibilidad Transparente**:
   - Si un archivo YAML utiliza el formato legacy (`databases:`), el cargador de configuración lo adaptará automáticamente en memoria asignándole `provider: sqlserver`.
   - Se mantendrán advertencias de deprecación recomendando migrar al formato v2.

3. **Extras Opcionales en Packaging**:
   - El archivo `pyproject.toml` definirá extras opcionales (`bdiff[sqlserver]`, `bdiff[postgresql]`, `bdiff[oracle]`, `bdiff[all]`).
   - SQLite utiliza `sqlite3` de la biblioteca estándar de Python y no requiere extras.

## Consequences

- **Positivas**:
  - Transición suave para usuarios existentes de SQL Server.
  - Formato extensible y limpio para nuevos proveedores.
