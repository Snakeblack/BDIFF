# Apply Progress — `provider-sqlserver-extraction`

## Status

Completed.

## Tasks Completed

- [x] Crear arquitectura de proveedores en `infrastructure/providers/`: `registry.py` con `ProviderRegistry`.
- [x] Extraer adaptador completo de SQL Server a `infrastructure/providers/sqlserver/`:
  - `connection.py`
  - `introspector.py`
  - `profile_parser.py`
  - `ddl_renderer.py`
  - `errors.py`
  - `provider.py` (`SqlServerProvider`)
- [x] Mover y re-exportar funciones desde módulos legacy (`connectors`, `discovery.queries`, `config.connection_string`, `compare.consolidation`).
- [x] Crear pruebas unitarias para `ProviderRegistry` y `SqlServerProvider`.
- [x] Ejecutar la suite completa de pytest y verificar que 334 pruebas pasan verde.
