# Tasks — `canonical-domain-models-and-capabilities`

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Low

## Phase 1 — Canonical Domain Types
- [x] 1.1 Crear `src/schema_comparator/domain/schema/qualified_name.py` (`QualifiedName`).
- [x] 1.2 Crear `src/schema_comparator/domain/schema/types.py` (`TypeFamily`, `SqlType`).
- [x] 1.3 Extender `ColumnSnapshot` en `domain/schema/models.py` con `default_expression`, `is_identity` y `collation`.
- [x] 1.4 Extender `ColumnAttributes` en `domain/comparison/models.py`.

## Phase 2 — Capabilities & Comparison Policies
- [x] 2.1 Crear `src/schema_comparator/domain/capabilities.py` (`ProviderCapabilities`, `ComparisonMode`).
- [x] 2.2 Re-exportar todas las entidades canónicas desde `src/schema_comparator/domain/__init__.py`.

## Phase 3 — Verification
- [x] 3.1 Crear pruebas unitarias para `QualifiedName`, `SqlType`, `ProviderCapabilities` y extensiones de `ColumnSnapshot`.
- [x] 3.2 Ejecutar la suite completa de pruebas de pytest y asegurar 0 regresiones.
