# Roadmap de OpenSpec Changes: Soporte Multibase de Datos (BDIFF)

Este documento desglosa la secuencia detallada de **OpenSpec Changes (SDDs)** y tareas necesarias para ejecutar la evolución arquitectónica descrita en [analisis-roadmap-multitarget.md](file:///c:/Users/sn4ke/dev/activos/BDIFF/docs/architecture/analisis-roadmap-multitarget.md).

---

## 📍 Índice de Fases y Changes

- [Fase 0 — Congelar el comportamiento actual y registrar decisiones](#fase-0--congelar-el-comportamiento-actual-y-registrar-decisiones)
  - [Change 01: `docs-roadmap-and-adrs`](#change-01-docs-roadmap-and-adrs)
- [Fase 1 — Separar dominio, aplicación y presentación](#fase-1--separar-dominio-aplicación-y-presentación)
  - [Change 02: `architecture-layered-domain`](#change-02-architecture-layered-domain)
  - [Change 03: `architecture-application-use-cases`](#change-03-architecture-application-use-cases)
- [Fase 2 — Extraer el provider SQL Server](#fase-2--extraer-el-provider-sql-server)
  - [Change 04: `provider-sqlserver-extraction`](#change-04-provider-sqlserver-extraction)
- [Fase 3 — Configuración v2 y drivers opcionales](#fase-3--configuración-v2-y-drivers-opcionales)
  - [Change 05: `config-v2-and-optional-dependencies`](#change-05-config-v2-and-optional-dependencies)
- [Fase 4 — Modelo canónico, políticas y capacidades](#fase-4--modelo-canónico-políticas-y-capacidades)
  - [Change 06: `canonical-domain-models-and-capabilities`](#change-06-canonical-domain-models-and-capabilities)
- [Fase 5 — Provider PostgreSQL](#fase-5--provider-postgresql)
  - [Change 07: `provider-postgresql`](#change-07-provider-postgresql)
- [Fase 6 — Provider SQLite](#fase-6--provider-sqlite)
  - [Change 08: `provider-sqlite`](#change-08-provider-sqlite)
- [Fase 7 — Providers MySQL y MariaDB](#fase-7--providers-mysql-y-mariadb)
  - [Change 09: `provider-mysql-mariadb`](#change-09-provider-mysql-mariadb)
- [Fase 8 — Provider Oracle](#fase-8--provider-oracle)
  - [Change 10: `provider-oracle`](#change-10-provider-oracle)
- [Fase 9 — Constraints, índices y metadatos avanzados](#fase-9--constraints-índices-y-metadatos-avanzados)
  - [Change 11: `advanced-schema-objects-comparison`](#change-11-advanced-schema-objects-comparison)
- [Fase 10 — Comparación semántica entre motores y estabilización 1.0](#fase-10--comparación-semántica-entre-motores-y-estabilización-10)
  - [Change 12: `cross-provider-semantic-comparison`](#change-12-cross-provider-semantic-comparison)

---

## Fase 0 — Congelar el comportamiento actual y registrar decisiones

### Change 01: `docs-roadmap-and-adrs`
* **Objetivo:** Asegurar que el comportamiento actual de SQL Server no cambie silenciosamente durante las refactorizaciones y formalizar las decisiones arquitectónicas.
* **Archivos principales involucrados:**
  - `docs/roadmap.md`
  - `docs/architecture/decisions/` (ADR-001 a ADR-005)
  - `tests/unit/` y `tests/fixtures/golden/`
* **Tareas:**
  - [ ] Actualizar `docs/roadmap.md` para reflejar el estado actual del proyecto (exportación a Excel, TUI interactiva y consolidación T-SQL).
  - [ ] Redactar ADR-001: Arquitectura hexagonal ligera y regla de dependencias.
  - [ ] Redactar ADR-002: Registro interno de proveedores vs sistema de plugins.
  - [ ] Redactar ADR-003: Modelo de tipos canónico y modos de comparación (`native-strict` vs `semantic`).
  - [ ] Redactar ADR-004: Configuración v2 y estrategia de retrocompatibilidad.
  - [ ] Redactar ADR-005: Generación de scripts desacoplada (write-only, sin auto-ejecución).
  - [ ] Añadir suite de caracterización para snapshots, findings, reportes y scripts T-SQL de SQL Server.
  - [ ] Generar y guardar golden files representativos del DDL T-SQL actual.
* **Criterio de salida:** Cualquier cambio observable en la extracción o generación de DDL para SQL Server es detectado por la suite de pruebas.

---

## Fase 1 — Separar dominio, aplicación y presentación

### Change 02: `architecture-layered-domain`
* **Objetivo:** Limpiar las dependencias de modelos entre capas sin alterar la funcionalidad existente.
* **Archivos principales involucrados:**
  - `src/schema_comparator/domain/schema/` (nuevo)
  - `src/schema_comparator/domain/comparison/` (nuevo)
  - `src/schema_comparator/discovery/models.py`
  - `src/schema_comparator/compare/models.py`
* **Tareas:**
  - [ ] Crear la estructura de paquetes `domain/schema` y `domain/comparison`.
  - [ ] Mover los modelos de esquema (`SchemaSnapshot`, `TableSnapshot`, `ColumnSnapshot`) a `domain/schema/models.py`.
  - [ ] Mover los modelos de hallazgos y resultados de comparación a `domain/comparison/models.py`.
  - [ ] Eliminar la dependencia directa de `compare.models` sobre `discovery.models`.
* **Criterio de salida:** Los modelos de dominio se pueden importar de manera aislada sin depender de conectores o bibliotecas de presentación.

### Change 03: `architecture-application-use-cases`
* **Objetivo:** Introducir puertos y casos de uso como frontera limpia entre la presentación y el dominio.
* **Archivos principales involucrados:**
  - `src/schema_comparator/application/ports/` (nuevo)
  - `src/schema_comparator/application/use_cases/` (nuevo)
  - `src/schema_comparator/cli.py`
  - `src/schema_comparator/tui/`
* **Tareas:**
  - [ ] Definir puertos con `Protocol` (`DatabaseProvider`, `ProfileRepository`, `ReportSink`, `ScriptSink`).
  - [ ] Crear el caso de uso `CompareProfilesUseCase` como único orquestador de extracción, filtros y comparación.
  - [ ] Mover la lógica de filtrado y exclusiones a una política de dominio/aplicación.
  - [ ] Convertir `cli.py` en *composition root* (construye el registro, asocia adaptadores y llama al caso de uso).
  - [ ] Refactorizar CLI y TUI para que ambos invoquen `CompareProfilesUseCase`.
* **Criterio de salida:** `domain` y `application` se pueden probar e ejecutar sin importar Textual, pyodbc, Jinja2, openpyxl o xhtml2pdf.

---

## Fase 2 — Extraer el provider SQL Server

### Change 04: `provider-sqlserver-extraction`
* **Objetivo:** Encapsular todo el comportamiento específico de SQL Server en su propio adaptador.
* **Archivos principales involucrados:**
  - `src/schema_comparator/infrastructure/providers/sqlserver/` (nuevo)
  - `src/schema_comparator/connectors/__init__.py`
  - `src/schema_comparator/discovery/queries.py`
  - `src/schema_comparator/config/connection_string.py`
  - `src/schema_comparator/compare/consolidation.py`
* **Tareas:**
  - [ ] Crear el paquete `providers/sqlserver/`.
  - [ ] Mover `connectors.connect` a `providers/sqlserver/connection.py`.
  - [ ] Mover las consultas de `INFORMATION_SCHEMA` a `providers/sqlserver/introspector.py`.
  - [ ] Mover la traducción de cadenas de conexión ADO.NET→ODBC a `providers/sqlserver/profile_parser.py`.
  - [ ] Mover el manejo y traducción de errores de `pyodbc` al adaptador de SQL Server.
  - [ ] Mover la sintaxis T-SQL (quoting `[name]`, `USE`, `GO`, `sys.*`) a `providers/sqlserver/ddl_renderer.py`.
  - [ ] Desacoplar `compare/consolidation.py` en operaciones de migración neutras, renderer SQL Server y escritor de archivos.
  - [ ] Registrar `SqlServerProvider` en `ProviderRegistry`.
* **Criterio de salida:** No existen referencias a `pyodbc`, `ODBC Driver`, `sys.columns`, `GO` o corchetes de quoting fuera de `infrastructure/providers/sqlserver`.

---

## Fase 3 — Configuración v2 y drivers opcionales

### Change 05: `config-v2-and-optional-dependencies`
* **Objetivo:** Permitir elegir proveedores sin necesidad de instalar drivers no utilizados.
* **Archivos principales involucrados:**
  - `src/schema_comparator/infrastructure/config/`
  - `pyproject.toml`
  - `run.py`
* **Tareas:**
  - [ ] Rediseñar `ConnectionProfile` para admitir `provider`, `connection_string` y `options`.
  - [ ] Implementar cargador de configuración v2 manteniendo compatibilidad con la sintaxis `databases:` legacy.
  - [ ] Añadir validación de configuración específica por proveedor.
  - [ ] Configurar extras opcionales en `pyproject.toml` (`sqlserver = ["pyodbc"]`, `postgresql = ["psycopg[binary]"]`, etc.).
  - [ ] Implementar la carga diferida (*lazy import*) de adaptadores en el registro.
  - [ ] Traducir `ImportError` a mensajes claros solicitando instalar el extra correspondiente (ej. `pip install bdiff[postgresql]`).
  - [ ] Añadir comandos CLI `bdiff providers list` y `bdiff providers doctor`.
* **Criterio de salida:** Una instalación core + SQLite funciona sin tener instalado `pyodbc`; la configuración legacy sigue funcionando identificándose automáticamente como SQL Server.

---

## Fase 4 — Modelo canónico, políticas y capacidades

### Change 06: `canonical-domain-models-and-capabilities`
* **Objetivo:** Preparar el motor de dominio para diferencias estructurales entre motores.
* **Archivos principales involucrados:**
  - `src/schema_comparator/domain/schema/`
  - `src/schema_comparator/domain/comparison/`
* **Tareas:**
  - [ ] Introducir `QualifiedName` (soporta catálogo opcional, esquema opcional y nombre de objeto).
  - [ ] Introducir `SqlType` y `TypeFamily` para representar familias semánticas manteniendo el tipo nativo y sus opciones.
  - [ ] Extender `ColumnSnapshot` con expresiones por defecto, identidad, columnas generadas y collations.
  - [ ] Implementar `ProviderCapabilities` (soporte de esquemas, DDL transaccional, alter/drop column, necesidad de rebuild).
  - [ ] Implementar la política de comparación `native-strict` (modo predeterminado).
  - [ ] Crear la matriz de equivalencias de tipos como estructura de datos declarativa.
* **Criterio de salida:** Los contratos de dominio pueden representar metadatos de PostgreSQL, SQLite, MySQL, MariaDB y Oracle sin añadir campos ad-hoc por proveedor.

---

## Fase 5 — Provider PostgreSQL

### Change 07: `provider-postgresql`
* **Objetivo:** Incorporar soporte completo para PostgreSQL.
* **Archivos principales involucrados:**
  - `src/schema_comparator/infrastructure/providers/postgresql/` (nuevo)
  - `pyproject.toml`
* **Tareas:**
  - [ ] Implementar `PostgreSqlProvider` con el driver `psycopg`.
  - [ ] Introspección mediante `information_schema` y `pg_catalog` (domains, enums, arrays, composite types).
  - [ ] Quoting de identificadores con comillas dobles (`"name"`).
  - [ ] Normalización de `serial` / `bigserial` vs `IDENTITY`.
  - [ ] Renderer DDL para PostgreSQL (`CREATE TABLE`, `ADD COLUMN`, `ALTER COLUMN TYPE ... USING`).
  - [ ] Pruebas de integración con contenedor PostgreSQL real y pruebas de contrato.
* **Criterio de salida:** Comparación N-way homogénea funcional para PostgreSQL con generación de reportes y scripts específicos.

---

## Fase 6 — Provider SQLite

### Change 08: `provider-sqlite`
* **Objetivo:** Incorporar soporte para SQLite y gestionar limitaciones de DDL (`ALTER TABLE`).
* **Archivos principales involucrados:**
  - `src/schema_comparator/infrastructure/providers/sqlite/` (nuevo)
* **Tareas:**
  - [ ] Implementar `SqliteProvider` con el módulo estándar `sqlite3`.
  - [ ] Introspección usando `sqlite_schema` y `PRAGMA table_xinfo`.
  - [ ] Representación de bases de datos `main`, `temp` y adjuntas (`ATTACH`).
  - [ ] Modelar *type affinity* conservando la declaración nativa.
  - [ ] Detectar columnas generadas y tablas con sintaxis `STRICT`.
  - [ ] Implementar planificador de reconstrucción de tabla (`table rebuild`) cuando una operación DDL no sea soportada directamente por `ALTER TABLE`.
* **Criterio de salida:** SQLite funciona sin dependencias externas y las limitaciones DDL se resuelven mediante reconstrucción transparente o advertencias.

---

## Fase 7 — Providers MySQL y MariaDB

### Change 09: `provider-mysql-mariadb`
* **Objetivo:** Soporte para la familia MySQL respetando las diferencias entre ambos motores.
* **Archivos principales involucrados:**
  - `src/schema_comparator/infrastructure/providers/mysql_family/` (nuevo)
  - `src/schema_comparator/infrastructure/providers/mysql/` (nuevo)
  - `src/schema_comparator/infrastructure/providers/mariadb/` (nuevo)
* **Tareas:**
  - [ ] Crear utilidades compartidas bajo `providers/mysql_family`.
  - [ ] Implementar `MySqlProvider` y `MariaDbProvider` como adaptadores independientes.
  - [ ] Introspección de atributos específicos (`UNSIGNED`, `AUTO_INCREMENT`, `ENUM`, `SET`, charsets).
  - [ ] Quoting con backticks (`` `name` ``).
  - [ ] Renderer DDL con sintaxis `MODIFY COLUMN` / `CHANGE COLUMN`.
  - [ ] Pruebas de integración en contenedores independientes para MySQL y MariaDB.
* **Criterio de salida:** Ambos proveedores superan las pruebas de contrato y sus particularidades quedan encapsuladas en sus adaptadores.

---

## Fase 8 — Provider Oracle

### Change 10: `provider-oracle`
* **Objetivo:** Incorporar soporte para Oracle Database.
* **Archivos principales involucrados:**
  - `src/schema_comparator/infrastructure/providers/oracle/` (nuevo)
* **Tareas:**
  - [ ] Implementar `OracleProvider` usando `python-oracledb` (Thin mode por defecto).
  - [ ] Introspección mediante `ALL_TABLES` y `ALL_TAB_COLUMNS`.
  - [ ] Mapeo de `OWNER` a esquema y aplicación de reglas de mayúsculas e identificadores citados.
  - [ ] Modelar tipos nativos (`NUMBER`, `VARCHAR2`, semántica BYTE/CHAR, etc.).
  - [ ] Renderer DDL para Oracle (sin envoltorio transaccional T-SQL).
  - [ ] Pruebas de integración para Oracle.
* **Criterio de salida:** Oracle cumple las pruebas de contrato de introspección y generación de DDL sin contaminar el dominio.

---

## Fase 9 — Constraints, índices y metadatos avanzados

### Change 11: `advanced-schema-objects-comparison`
* **Objetivo:** Extender la comparación estructural más allá de tablas y columnas.
* **Archivos principales involucrados:**
  - `src/schema_comparator/domain/schema/`
  - `src/schema_comparator/domain/comparison/`
  - Adaptadores de proveedores (`infrastructure/providers/*/`)
* **Tareas:**
  - [ ] Modelar e inspeccionar Primary Keys y Unique Constraints.
  - [ ] Modelar e inspeccionar Foreign Keys y reglas de acción (`ON DELETE`, `ON UPDATE`).
  - [ ] Modelar e inspeccionar Índices (orden, parciales/filtrados, columnas incluidas).
  - [ ] Modelar e inspeccionar Check Constraints.
  - [ ] Actualizar el motor de comparación y los casos de uso para reportar discrepancias en estos objetos.
  - [ ] Actualizar los renderers DDL por proveedor para emitir las sentencias correspondientes.
* **Criterio de salida:** La comparación detecta y genera correcciones para índices y restricciones manteniendo el desacoplamiento por proveedor.

---

## Fase 10 — Comparación semántica entre motores y estabilización 1.0

### Change 12: `cross-provider-semantic-comparison`
* **Objetivo:** Ofrecer comparación heterogénea entre distintos motores de base de datos.
* **Archivos principales involucrados:**
  - `src/schema_comparator/domain/comparison/`
  - `src/schema_comparator/presentation/`
* **Tareas:**
  - [ ] Implementar el modo de comparación `semantic` (opt-in).
  - [ ] Definir la matriz de compatibilidad e incompatibilidad entre familias de tipos.
  - [ ] Generar advertencias de portabilidad en los reportes (pérdidas de precisión, diferencias de timezone o collation).
  - [ ] Publicar la API de proveedores estable y evaluar el soporte de plugins de terceros.
  - [ ] Consolidar la documentación final y el versionado semántico para el lanzamiento 1.0.
* **Criterio de salida:** Es posible comparar un esquema de SQL Server contra uno de PostgreSQL obteniendo un reporte semántico claro de portabilidad y discrepancias.
