# Tasks — `architecture-layered-domain`

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Low

## Phase 1 — Create Domain Package Structure
- [x] 1.1 Crear `src/schema_comparator/domain/__init__.py`
- [x] 1.2 Crear `src/schema_comparator/domain/schema/__init__.py`
- [x] 1.3 Crear `src/schema_comparator/domain/schema/models.py`
- [x] 1.4 Crear `src/schema_comparator/domain/comparison/__init__.py`
- [x] 1.5 Crear `src/schema_comparator/domain/comparison/models.py`

## Phase 2 — Refactor Discovery & Compare Re-exports
- [x] 2.1 Refactorizar `src/schema_comparator/discovery/models.py`
- [x] 2.2 Refactorizar `src/schema_comparator/compare/models.py`

## Phase 3 — Verification
- [x] 3.1 Ejecutar suite completa de tests de pytest y verificar 0 fallos.
