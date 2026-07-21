# Proposal — `docs-roadmap-and-adrs`

## Intent

Formalizar la Fase 0 de la migración hacia la arquitectura multibase de datos (BDIFF) mediante:
1. La redacción de los 5 ADRs fundamentales (Hexagonal Architecture, Internal Provider Registry, Canonical Types, Configuration v2, Decoupled Script Generation).
2. La congelación del comportamiento actual del proveedor de SQL Server a través de una suite de pruebas de caracterización y golden files de snapshots/DDL T-SQL.
3. El aseguramiento de la regla de dependencias para evitar acoplamiento involuntario entre capas.

## Scope

- Redactar `docs/architecture/decisions/0001-hexagonal-architecture-and-dependency-rules.md`
- Redactar `docs/architecture/decisions/0002-internal-provider-registry.md`
- Redactar `docs/architecture/decisions/0003-canonical-type-system-and-comparison-modes.md`
- Redactar `docs/architecture/decisions/0004-configuration-v2-and-backwards-compatibility.md`
- Redactar `docs/architecture/decisions/0005-decoupled-write-only-script-generation.md`
- Crear la suite de pruebas de caracterización en `tests/unit/sqlserver/test_characterization.py`
- Crear golden files representativos en `tests/fixtures/golden/sqlserver/`

## Rollback Plan

Dado que este cambio es puramente de documentación y adición de pruebas de caracterización sin modificar la lógica en producción, el rollback consiste simplemente en descartar los archivos añadidos si fuera necesario.
