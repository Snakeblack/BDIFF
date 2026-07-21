# Task Breakdown: `provider-mysql-mariadb`

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Low

## Phase 1: Core Implementation
- [x] 1.1 Crear paquete `mysql_family` con `profile_parser`, `introspector` y `ddl_renderer`.
- [x] 1.2 Implementar adaptadores `MySqlProvider` y `MariaDbProvider`.
- [x] 1.3 Registrar proveedores en `ProviderRegistry` (`mysql` y `mariadb`).
- [x] 1.4 Configurar dependencias opcionales en `pyproject.toml` (`mysql` y `mariadb`).

## Phase 2: Testing & Verification
- [x] 2.1 Pruebas unitarias para `MySqlProvider` y `MariaDbProvider`.
- [x] 2.2 Pruebas de renderizado DDL y quoting con backticks.
- [x] 2.3 Ejecución de suite completa de pruebas.
