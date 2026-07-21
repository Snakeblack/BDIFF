# Design Document: MySQL & MariaDB Provider

## Overview
Implementación de los proveedores de infraestructura `mysql` y `mariadb` reutilizando abstracciones comunes bajo `mysql_family`.

## Architecture & Component Design
- `infrastructure/providers/mysql_family/`:
  - `profile_parser.py`: Parsea host, port, user, password, database, options desde `ConnectionProfile`.
  - `introspector.py`: Mapea tipos de MySQL (`int`, `varchar`, `datetime`, `enum`, `tinyint(1)`) a `SqlType` y `SchemaSnapshot`.
  - `ddl_renderer.py`: Renderiza sentencias `CREATE TABLE`, `ALTER TABLE ADD COLUMN`, `ALTER TABLE MODIFY COLUMN`, `ALTER TABLE DROP COLUMN`.
- `infrastructure/providers/mysql/`:
  - `provider.py`: Implementa `DatabaseProvider` con `name="mysql"` y capacidades específicas.
- `infrastructure/providers/mariadb/`:
  - `provider.py`: Implementa `DatabaseProvider` con `name="mariadb"` y capacidades específicas.

## Quoting & Data Types
- Identificadores: `` `table_name` ``, `` `column_name` ``
- Modificadores de columna: `AUTO_INCREMENT`, `UNSIGNED`, `CHARACTER SET utf8mb4`
