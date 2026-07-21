# Tasks — `architecture-application-use-cases`

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Low

## Phase 1 — Ports & Use Cases
- [x] 1.1 Crear puertos en `src/schema_comparator/application/ports/`
- [x] 1.2 Crear `CompareProfilesUseCase` en `src/schema_comparator/application/use_cases/compare_profiles.py`

## Phase 2 — Refactor Presentation Layer
- [x] 2.1 Actualizar `src/schema_comparator/tui/actions.py` para usar `CompareProfilesUseCase`
- [x] 2.2 Actualizar `src/schema_comparator/cli.py` para usar `CompareProfilesUseCase` y actuar como composition root.

## Phase 3 — Verification
- [x] 3.1 Ejecutar suite completa de tests y verificar 0 fallos.
