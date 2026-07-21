# Proposal — `canonical-domain-models-and-capabilities`

## Intent

Evolucionar los modelos de dominio e introducir abstracciones canónicas (`QualifiedName`, `SqlType`, `TypeFamily`, `ProviderCapabilities` y `ComparisonMode`) para representar metadatos de múltiples motores de base de datos (PostgreSQL, Oracle, MySQL, SQLite, SQL Server) manteniendo 100% de retrocompatibilidad con las pruebas y contratos existentes.

## Scope

1. **`QualifiedName`**:
   - Introducir `QualifiedName(object_name, schema_name=None, catalog_name=None)` en `domain/schema/qualified_name.py`.
2. **`SqlType` & `TypeFamily`**:
   - Introducir `TypeFamily` (enum) y `SqlType` en `domain/schema/types.py`.
3. **`ColumnSnapshot` & `ColumnAttributes`**:
   - Extender `ColumnSnapshot` y `ColumnAttributes` con los campos opcionales `default_expression`, `is_identity` y `collation`.
4. **`ProviderCapabilities` & `ComparisonMode`**:
   - Crear `domain/capabilities.py` definiendo las capacidades por motor y las políticas de comparación (`native-strict`).

## Rollback Plan

Revertir los archivos añadidos bajo `src/schema_comparator/domain/` y restaurar `models.py`.
