# Change Proposal: `provider-mysql-mariadb`

## Summary
Incorpora soporte completo para la familia MySQL (MySQL y MariaDB) como proveedores de base de datos de BDIFF (`MySqlProvider` y `MariaDbProvider`). Permite introspección de esquemas mediante `information_schema`, quoting con backticks (`` `name` ``), gestión de atributos de tipo nativos (`UNSIGNED`, `AUTO_INCREMENT`, `ENUM`, `SET`, `TINYINT(1)`/`BOOLEAN`) y generación de DDL de migración (`MODIFY COLUMN` / `CHANGE COLUMN`).

## Motivation
Extender la compatibilidad de BDIFF a motores de base de datos relacionales ampliamente utilizados (MySQL y MariaDB) en arquitecturas de microservicios.

## Proposed Scope
- Crear utilidades compartidas en `src/schema_comparator/infrastructure/providers/mysql_family/`.
- Crear adaptadores independientes `MySqlProvider` (`providers/mysql/`) y `MariaDbProvider` (`providers/mariadb/`).
- Registro diferido en `ProviderRegistry` para las claves `mysql` y `mariadb`.
- Definir dependencias opcionales `mysql` y `mariadb` (`pymysql>=1.1`) en `pyproject.toml`.
- Renderer DDL específico con soporte para `MODIFY COLUMN`, `ADD COLUMN`, `DROP COLUMN` y backticks.
- Pruebas unitarias de introspección, parsing de perfiles, registro de proveedores y renderizado DDL.

## Risk & Safety Assessment
- **Risk:** Bajo. Se añade un nuevo proveedor aislado sin modificar los de SQL Server, PostgreSQL o SQLite.
- **Rollback:** Eliminar el directorio `mysql_family`, `mysql` y `mariadb` e los registros del `ProviderRegistry`.
