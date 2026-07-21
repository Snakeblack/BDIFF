# Tasks — `provider-sqlserver-extraction`

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Low

## Phase 1 — Create Provider Architecture
- [x] 1.1 Crear `src/schema_comparator/infrastructure/__init__.py`
- [x] 1.2 Crear `src/schema_comparator/infrastructure/providers/__init__.py`
- [x] 1.3 Crear `src/schema_comparator/infrastructure/providers/registry.py` (`ProviderRegistry`)

## Phase 2 — Extract SQL Server Provider
- [x] 2.1 Crear `src/schema_comparator/infrastructure/providers/sqlserver/connection.py`
- [x] 2.2 Crear `src/schema_comparator/infrastructure/providers/sqlserver/introspector.py`
- [x] 2.3 Crear `src/schema_comparator/infrastructure/providers/sqlserver/profile_parser.py`
- [x] 2.4 Crear `src/schema_comparator/infrastructure/providers/sqlserver/ddl_renderer.py`
- [x] 2.5 Crear `src/schema_comparator/infrastructure/providers/sqlserver/errors.py`
- [x] 2.6 Crear `src/schema_comparator/infrastructure/providers/sqlserver/provider.py` (`SqlServerProvider`)

## Phase 3 — Legacy Module Re-exports
- [x] 3.1 Refactorizar `connectors/__init__.py`
- [x] 3.2 Refactorizar `discovery/queries.py`
- [x] 3.3 Refactorizar `config/connection_string.py`
- [x] 3.4 Refactorizar `compare/consolidation.py`

## Phase 4 — Verification
- [x] 4.1 Ejecutar suite completa de tests de pytest e integración (golden tests incluidos).
