# Proposal — `architecture-application-use-cases`

## Intent

Introducir los puertos y el caso de uso `CompareProfilesUseCase` en la capa `application` para que actúe como frontera limpia y orquestador único entre la capa de presentación (CLI/TUI) y la lógica de dominio.

## Scope

- Crear `src/schema_comparator/application/__init__.py`
- Crear `src/schema_comparator/application/ports/database_provider.py` (Protocol)
- Crear `src/schema_comparator/application/ports/profile_repository.py` (Protocol)
- Crear `src/schema_comparator/application/ports/report_sink.py` (Protocol)
- Crear `src/schema_comparator/application/ports/script_sink.py` (Protocol)
- Crear `src/schema_comparator/application/use_cases/compare_profiles.py` (`CompareProfilesUseCase`)
- Refactorizar `tui/actions.py` para usar `CompareProfilesUseCase`
- Refactorizar `cli.py` como *composition root* que invoca la capa de aplicación.

## Rollback Plan

Revertir los archivos creados en `src/schema_comparator/application/` y restaurar `cli.py` y `tui/actions.py`.
