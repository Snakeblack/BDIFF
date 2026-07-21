# Proposal — `architecture-layered-domain`

## Intent

Extraer los modelos de datos de esquemas y de comparación a los paquetes de dominio neutros `domain/schema` y `domain/comparison`.
Eliminar la dependencia directa de `compare.models` hacia `discovery.models`, logrando que ambas capas utilicen los modelos de dominio compartidos y manteniendo retrocompatibilidad mediante re-exportación.

## Scope

- Crear `src/schema_comparator/domain/__init__.py`
- Crear `src/schema_comparator/domain/schema/__init__.py`
- Crear `src/schema_comparator/domain/schema/models.py` con `ColumnSnapshot`, `TableSnapshot` y `SchemaSnapshot`
- Crear `src/schema_comparator/domain/comparison/__init__.py`
- Crear `src/schema_comparator/domain/comparison/models.py` con `ColumnAttributes`, `NamedColumnAttributes`, `MissingTable`, `MissingColumn`, `ColumnMismatch`, `DiffEntry` y `ComparisonResult`
- Refactorizar `src/schema_comparator/discovery/models.py` para re-exportar desde `domain.schema.models`
- Refactorizar `src/schema_comparator/compare/models.py` para re-exportar desde `domain.comparison.models`

## Rollback Plan

Si ocurriera algún problema de importación o compatibilidad, la refactorización puede revertirse restaurando `discovery/models.py` y `compare/models.py` a sus versiones previas.
