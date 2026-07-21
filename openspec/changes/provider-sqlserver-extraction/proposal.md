# Proposal — `provider-sqlserver-extraction`

## Intent

Extraer y encapsular todo el código específico de SQL Server (conexión pyodbc, consulta `INFORMATION_SCHEMA`, formateador de cadenas de conexión ADO.NET y renderizador DDL T-SQL) dentro de su propio proveedor de infraestructura bajo `src/schema_comparator/infrastructure/providers/sqlserver/`.

## Scope

- Crear `infrastructure/providers/registry.py` con `ProviderRegistry`.
- Crear `infrastructure/providers/sqlserver/`:
  - `connection.py`
  - `introspector.py`
  - `profile_parser.py`
  - `ddl_renderer.py`
  - `errors.py`
  - `provider.py` (`SqlServerProvider`)
- Re-exportar desde los módulos legacy (`connectors`, `discovery.queries`, `config.connection_string`, `compare.consolidation`) para mantener 100% retrocompatibilidad con la suite de pruebas.

## Rollback Plan

Revertir la carpeta `infrastructure/providers/sqlserver` y restaurar los archivos originales.
