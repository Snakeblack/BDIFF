# Apply Progress — `architecture-application-use-cases`

## Status

Completed.

## Tasks Completed

- [x] Crear puertos de aplicación en `src/schema_comparator/application/ports/`: `DatabaseProvider`, `ProfileRepository`, `ReportSink`, `ScriptSink`.
- [x] Crear el caso de uso `CompareProfilesUseCase` en `src/schema_comparator/application/use_cases/compare_profiles.py`.
- [x] Refactorizar `tui/actions.py` para usar `CompareProfilesUseCase`.
- [x] Refactorizar `cli.py` como *composition root* apoyado en `CompareProfilesUseCase`.
- [x] Crear tests unitarios para `CompareProfilesUseCase` en `tests/unit/application/test_compare_profiles.py`.
- [x] Verificar ejecuciones y asegurar 0 fallos en la suite de pruebas.
