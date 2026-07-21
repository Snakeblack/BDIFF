# Roadmap de arquitectura y soporte multibase de datos — BDIFF

> Estado propuesto para evolucionar BDIFF desde un comparador acoplado a SQL Server hacia una herramienta modular, extensible y mantenible, capaz de inspeccionar, comparar y generar planes de corrección para distintos motores de base de datos.

## 1. Objetivo

BDIFF debe permitir añadir un nuevo motor de base de datos sin modificar el motor de comparación, los reportes, la CLI o la TUI, salvo para registrar el nuevo provider y documentarlo.

La arquitectura objetivo debe cumplir estas propiedades:

- El dominio desconoce drivers, cadenas de conexión, SQL de catálogo, frameworks y detalles de presentación.
- Cada motor encapsula su conexión, introspección, normalización, reglas de identificadores, capacidades y generación de DDL.
- La comparación trabaja sobre un modelo canónico e inmutable.
- La generación de scripts parte de operaciones semánticas, no de fragmentos SQL construidos desde la TUI.
- Las operaciones no soportadas o potencialmente destructivas se representan explícitamente; nunca se improvisan.
- El comportamiento actual de SQL Server se conserva durante la migración mediante pruebas de caracterización.

## 2. Resumen ejecutivo

El proyecto ya tiene varias decisiones acertadas: estructura `src/`, modelos inmutables, orden determinista, motor N-way separado de los reportes, protección de secretos y una base de pruebas considerable.

El bloqueo para soportar otros motores no está en el algoritmo de comparación, sino en las fronteras:

- `ConnectionProfile` y su parser están diseñados para SQL Server y ODBC.
- La conexión global depende directamente de `pyodbc`.
- La extracción importa `pyodbc` y ejecuta una única consulta SQL Server.
- El modelo comparable depende del modelo de `discovery`, creando una dependencia entre capas que deberían compartir dominio.
- La consolidación mezcla decisiones, T-SQL, idempotencia, extracción del nombre de base de datos y escritura de archivos.
- La TUI construye resoluciones y llama directamente al generador SQL.
- `pyproject.toml` instala `pyodbc` obligatoriamente aunque el usuario pudiera querer únicamente SQLite o PostgreSQL.
- El roadmap existente está desactualizado respecto al código implementado.

La prioridad correcta es extraer primero un provider de SQL Server sin cambiar funcionalidad. PostgreSQL será el segundo provider para validar la abstracción con otro servidor SQL; SQLite debe llegar pronto porque fuerza a eliminar supuestos sobre schemas, tipos y `ALTER TABLE`. MySQL y MariaDB deben compartir utilidades internas, pero conservar providers distintos. Oracle debe implementarse después, cuando los contratos ya hayan sobrevivido a motores suficientemente diferentes.

## 3. Decisiones de alcance

### 3.1 Compatibilidad no significa equivalencia automática

Se separan dos escenarios:

1. **Comparación homogénea**, entre perfiles del mismo motor. Será el modo predeterminado y tendrá comparación exacta de metadatos normalizados.
2. **Comparación heterogénea**, entre motores distintos. Será posterior, explícita y basada en familias semánticas de tipos. No debe considerar automáticamente equivalentes dos tipos solo porque ambos almacenan texto o números.

### 3.2 SQLAlchemy no será la arquitectura

No se recomienda sustituir todo por SQLAlchemy como solución mágica. Puede utilizarse dentro de un adapter si aporta valor, pero no debe convertirse en el contrato del dominio. La introspección, los tipos nativos, las capacidades y el DDL siguen teniendo diferencias relevantes por motor.

### 3.3 Ningún provider debe contaminar el núcleo

Fuera de la composición y el registro, no deben aparecer condicionales como:

```python
if profile.provider == "oracle":
    ...
elif profile.provider == "postgresql":
    ...
```

La selección se realiza una vez mediante un registro de providers. A partir de ahí, el comportamiento es polimórfico.

### 3.4 Generar no significa ejecutar

BDIFF debe continuar generando artefactos y planes de corrección, no ejecutar migraciones automáticamente. Las operaciones destructivas deben quedar marcadas y requerir una decisión explícita del usuario.

## 4. Arquitectura objetivo

```text
src/schema_comparator/
├── domain/
│   ├── schema/
│   │   ├── identifiers.py
│   │   ├── types.py
│   │   ├── models.py
│   │   └── capabilities.py
│   ├── comparison/
│   │   ├── findings.py
│   │   ├── policies.py
│   │   └── engine.py
│   └── migration/
│       ├── operations.py
│       ├── plan.py
│       └── safety.py
├── application/
│   ├── ports/
│   │   ├── database_provider.py
│   │   ├── profile_repository.py
│   │   ├── report_sink.py
│   │   └── script_sink.py
│   └── use_cases/
│       ├── compare_profiles.py
│       ├── build_migration_plan.py
│       ├── generate_scripts.py
│       └── generate_reports.py
├── infrastructure/
│   ├── config/
│   │   ├── loader.py
│   │   ├── migration.py
│   │   └── yaml_profile_repository.py
│   ├── providers/
│   │   ├── registry.py
│   │   ├── sqlserver/
│   │   │   ├── provider.py
│   │   │   ├── connection.py
│   │   │   ├── introspector.py
│   │   │   ├── type_mapper.py
│   │   │   ├── ddl_renderer.py
│   │   │   └── errors.py
│   │   ├── postgresql/
│   │   ├── sqlite/
│   │   ├── mysql/
│   │   ├── mariadb/
│   │   └── oracle/
│   └── output/
│       ├── filesystem_report_sink.py
│       └── filesystem_script_sink.py
└── presentation/
    ├── cli/
    ├── tui/
    └── report/
```

No es obligatorio mover todos los archivos en un único cambio. La estructura es el destino; la migración debe realizarse por slices verticales pequeños y verificables.

## 5. Regla de dependencias

```text
presentation ──────┐
                   ├──> application ───> domain
infrastructure ────┘
```

- `domain` no importa nada de `application`, `infrastructure` o `presentation`.
- `application` solo depende del dominio y de contratos propios.
- `infrastructure` implementa los puertos de aplicación.
- `presentation` invoca casos de uso; no abre conexiones ni renderiza DDL.
- `cli.py` actúa como composition root: carga configuración, construye el registro, conecta adapters y lanza el caso de uso.

## 6. Contrato de provider

El contrato debe ser pequeño. No se deben exponer conexiones, cursores ni excepciones del driver fuera del adapter.

```python
from typing import Protocol

class DatabaseProvider(Protocol):
    provider_id: str

    def validate_profile(self, profile: ConnectionProfile) -> None: ...

    def introspect(self, profile: ConnectionProfile) -> SchemaSnapshot: ...

    def capabilities(self, profile: ConnectionProfile) -> ProviderCapabilities: ...

    def render_migration(
        self,
        plan: MigrationPlan,
        target: ConnectionProfile,
    ) -> RenderedMigration: ...
```

El provider puede delegar internamente en `ConnectionFactory`, `SchemaIntrospector`, `TypeMapper` y `DdlRenderer`, pero esos componentes no necesitan formar parte del contrato público inicial.

### 6.1 Registro de providers

```python
registry.register(SqlServerProvider())
registry.register(PostgreSqlProvider())
provider = registry.require(profile.provider)
```

Inicialmente es preferible un registro interno explícito. Los entry points de Python pueden añadirse cuando exista una necesidad real de providers de terceros.

## 7. Modelo de dominio canónico

### 7.1 Identidad de objetos

El actual `(schema_name, table_name)` debe evolucionar a una identidad capaz de representar todos los motores:

```python
QualifiedName(
    catalog: str | None,
    schema: str | None,
    name: str,
)
```

El adapter debe producir tanto el valor mostrable como su clave de comparación. No se debe aplicar un `lower()` o `casefold()` global porque las reglas de identificadores citados y no citados varían por motor.

### 7.2 Tipos

No basta con conservar `data_type`, longitud, precisión y escala. Se necesita un descriptor extensible:

```python
SqlType(
    family: TypeFamily,
    native_name: str,
    length: int | None = None,
    precision: int | None = None,
    scale: int | None = None,
    timezone: bool | None = None,
    unsigned: bool | None = None,
    array_dimensions: int | None = None,
    charset: str | None = None,
    collation: str | None = None,
    native_options: tuple[tuple[str, str], ...] = (),
)
```

Familias iniciales:

- integer
- decimal
- floating
- boolean
- character
- text
- binary
- uuid
- date
- time
- datetime
- interval
- json
- xml
- enum
- array
- spatial
- custom
- unknown

`native_name` y `native_options` nunca se descartan. La normalización no debe destruir información que luego sea necesaria en reportes o DDL.

### 7.3 Columna

El modelo debe poder crecer sin romper el motor:

```python
ColumnSnapshot(
    name,
    type,
    nullable,
    ordinal_position,
    default_expression=None,
    generated_expression=None,
    identity=None,
    collation=None,
)
```

La posición puede seguir excluida de la comparación predeterminada, pero debe permanecer disponible.

### 7.4 Capacidades

```python
ProviderCapabilities(
    supports_schemas: bool,
    transactional_ddl: bool,
    supports_add_column: bool,
    supports_alter_column: bool,
    supports_drop_column: bool,
    supports_generated_columns: bool,
    supports_identity: bool,
    requires_table_rebuild_for_alter: bool,
)
```

Las capacidades deben poder depender de la versión del servidor. El renderer no debe emitir una operación que el target no soporte.

## 8. Plan de migración intermedio

La TUI no debe producir SQL. Debe construir decisiones que el caso de uso transforme en operaciones:

```text
CreateTable
DropTable
AddColumn
AlterColumn
DropColumn
```

Cada operación debe incluir:

- destino;
- metadatos canónicos;
- clasificación de seguridad;
- precondiciones;
- advertencias;
- referencia al hallazgo que la originó.

Clasificación mínima:

- `SAFE`
- `DESTRUCTIVE`
- `REQUIRES_DATA_MIGRATION`
- `REQUIRES_TABLE_REBUILD`
- `UNSUPPORTED`

El provider destino renderiza el plan. Esto elimina T-SQL de la capa de comparación y evita que la TUI conozca sintaxis, quoting o transacciones.

## 9. Configuración v2

Formato propuesto:

```yaml
profiles:
  billing-sqlserver:
    provider: sqlserver
    connection_string: "${BDIFF_BILLING_SQLSERVER_DSN}"
    options:
      connect_timeout_seconds: 30
      query_timeout_seconds: 30
      include_schemas: [dbo]

  billing-postgresql:
    provider: postgresql
    connection_string: "${BDIFF_BILLING_POSTGRESQL_DSN}"
    options:
      include_schemas: [public]

  local-sqlite:
    provider: sqlite
    connection_string: "./data/local.db"
```

Tareas obligatorias:

- [ ] Añadir `provider` como campo obligatorio en el formato v2.
- [ ] Mantener temporalmente `databases: {name: connection_string}` como formato legacy equivalente a `provider: sqlserver`.
- [ ] Mover la traducción ADO.NET→ODBC al adapter de SQL Server.
- [ ] Resolver variables de entorno sin incluir sus valores en logs o errores.
- [ ] Permitir opciones comunes y un bloque `provider_options` validado por cada adapter.
- [ ] Añadir comando de validación: `bdiff config validate`.
- [ ] Añadir comando de migración o diagnóstico del formato legacy.
- [ ] Versionar el documento de configuración para futuras migraciones.

## 10. Estrategia de dependencias

Los drivers deben ser extras opcionales:

```toml
[project.optional-dependencies]
sqlserver = ["pyodbc"]
postgresql = ["psycopg[binary]"]
oracle = ["oracledb"]
mysql = ["mysql-connector-python"]
mariadb = ["mariadb"]
all = [
  "pyodbc",
  "psycopg[binary]",
  "oracledb",
  "mysql-connector-python",
  "mariadb",
]
```

SQLite utiliza `sqlite3` de la biblioteca estándar.

- [ ] Eliminar `pyodbc` de las dependencias core.
- [ ] Importar drivers de forma diferida dentro de cada adapter.
- [ ] Traducir `ImportError` a un error accionable con el extra que debe instalarse.
- [ ] Actualizar `run.py` para elegir extras sin instalar todos los drivers obligatoriamente.
- [ ] Mantener un extra `all` para desarrollo y CI.
- [ ] Documentar requisitos externos, como el ODBC Driver de SQL Server.

## 11. Modos de comparación

### `native-strict`

Modo predeterminado. Solo compara perfiles del mismo provider y considera diferencias en tipos nativos y atributos relevantes.

### `semantic`

Modo opt-in para motores distintos. Compara familias canónicas y emite advertencias cuando la equivalencia sea parcial o dependiente de rango, precisión, timezone, collation o comportamiento del motor.

### `custom-policy`

Política configurable para ignorar diferencias aceptadas:

- aliases equivalentes;
- longitud no relevante;
- defaults distintos;
- orden de columnas;
- schemas excluidos;
- tablas o columnas conocidas;
- reglas por provider y proyecto.

No se debe implementar `semantic` hasta que existan al menos tres providers y una matriz de tipos probada.

# 12. Roadmap de implementación

## Fase 0 — Congelar el comportamiento actual y registrar decisiones

**Objetivo:** poder refactorizar sin cambiar silenciosamente SQL Server.

- [ ] Corregir `docs/roadmap.md` para que refleje Excel y la consolidación ya implementados.
- [ ] Crear ADR: arquitectura hexagonal ligera y regla de dependencias.
- [ ] Crear ADR: provider registry interno frente a sistema de plugins externo.
- [ ] Crear ADR: modelo de tipos canónico y modos de comparación.
- [ ] Crear ADR: configuración v2 y compatibilidad legacy.
- [ ] Crear ADR: generación de scripts sin ejecución automática.
- [ ] Añadir pruebas de caracterización para snapshots, findings, reportes y scripts T-SQL actuales.
- [ ] Guardar golden files representativos del DDL actual.
- [ ] Medir imports entre paquetes y definir reglas que puedan automatizarse.

**Criterio de salida:** la suite detecta cualquier cambio observable del provider SQL Server actual.

## Fase 1 — Separar dominio, aplicación y presentación

**Objetivo:** limpiar dependencias sin introducir todavía otro motor.

- [ ] Mover los modelos de esquema a `domain/schema`.
- [ ] Mover findings y comparación a `domain/comparison`.
- [ ] Eliminar la dependencia de `compare.models` hacia `discovery.models`.
- [ ] Crear puertos en `application/ports` usando `Protocol`.
- [ ] Crear `CompareProfilesUseCase` como único orquestador de extracción, filtros y comparación.
- [ ] Mover la lógica de exclusión a una política de aplicación o dominio, no a la TUI.
- [ ] Hacer que CLI y TUI llamen al mismo caso de uso.
- [ ] Mantener reportes como consumidores de `ComparisonResult` sin dependencia de providers.
- [ ] Convertir `cli.py` en composition root.

**Criterio de salida:** `domain` y `application` pueden importarse y probarse sin `pyodbc`, Textual, Jinja2, openpyxl o xhtml2pdf.

## Fase 2 — Extraer el provider SQL Server

**Objetivo:** demostrar que la arquitectura puede contener completamente el comportamiento existente.

- [ ] Crear `SqlServerProvider`.
- [ ] Mover `connectors.connect` a `providers/sqlserver/connection.py`.
- [ ] Mover la consulta de `INFORMATION_SCHEMA` a `providers/sqlserver/introspector.py`.
- [ ] Mover traducción ADO.NET→ODBC a `providers/sqlserver/profile_parser.py`.
- [ ] Mover traducción de errores `pyodbc` al provider.
- [ ] Mover quoting `[name]`, `USE`, `GO`, `sys.*` y T-SQL a `providers/sqlserver/ddl_renderer.py`.
- [ ] Separar `compare/consolidation.py` en operaciones de dominio, renderer SQL Server y writer de archivos.
- [ ] Eliminar imports locales de generación SQL desde `DecisionScreen`.
- [ ] Registrar SQL Server en `ProviderRegistry`.
- [ ] Verificar que los golden files actuales no cambian salvo correcciones deliberadas.

**Criterio de salida:** buscar `pyodbc`, `ODBC Driver`, `sys.columns`, `GO` o corchetes de quoting fuera de `providers/sqlserver` no devuelve código de producción.

## Fase 3 — Configuración v2 y drivers opcionales

**Objetivo:** poder seleccionar provider sin cargar drivers innecesarios.

- [ ] Implementar `ConnectionProfile(provider, connection_string, options)`.
- [ ] Implementar loader v2 y adaptador de configuración legacy.
- [ ] Añadir validación específica por provider.
- [ ] Introducir extras opcionales en `pyproject.toml`.
- [ ] Añadir carga diferida de adapters.
- [ ] Mostrar errores de instalación accionables.
- [ ] Actualizar launcher, README y ejemplos.
- [ ] Añadir `bdiff providers list` y `bdiff providers doctor`.

**Criterio de salida:** una instalación `core + sqlite` arranca sin `pyodbc`; una configuración legacy continúa funcionando como SQL Server.

## Fase 4 — Modelo canónico, políticas y capacidades

**Objetivo:** preparar el núcleo para diferencias reales entre motores.

- [ ] Introducir `QualifiedName` con catálogo y schema opcionales.
- [ ] Introducir `SqlType`, `TypeFamily` y atributos extensibles.
- [ ] Conservar siempre tipo nativo y opciones no normalizadas.
- [ ] Añadir defaults, identidad, columnas generadas y collation al modelo.
- [ ] Implementar `ProviderCapabilities` versionado.
- [ ] Crear política `native-strict`.
- [ ] Convertir findings y reportes al nuevo modelo sin perder legibilidad.
- [ ] Crear matriz de equivalencias de tipos como datos, no como cadena de `if`.
- [ ] Definir comportamiento para tipos desconocidos: preservar y comparar como `custom/unknown`.

**Criterio de salida:** SQL Server sigue pasando; los contratos ya pueden representar PostgreSQL, SQLite, MySQL/MariaDB y Oracle sin añadir campos ad hoc por provider.

## Fase 5 — Provider PostgreSQL

**Objetivo:** validar la arquitectura con un segundo servidor SQL suficientemente diferente.

- [ ] Driver `psycopg`.
- [ ] Introspección base mediante `information_schema` y extensión con `pg_catalog` cuando sea necesario.
- [ ] Manejar schemas, identificadores, domains, enums, arrays y tipos definidos por usuario.
- [ ] Normalizar `serial` frente a identity/secuencia sin borrar el detalle nativo.
- [ ] Renderizar quoting con comillas dobles.
- [ ] Implementar `CREATE TABLE`, `ADD COLUMN`, `ALTER COLUMN` y `DROP` según capacidades.
- [ ] Emitir `USING` o advertencia cuando un cambio de tipo no sea seguro.
- [ ] Añadir integración con PostgreSQL real en contenedor.
- [ ] Añadir golden files y contract tests del provider.

**Criterio de salida:** comparación N-way homogénea PostgreSQL completa para tablas y columnas, con reportes y scripts target-specific.

## Fase 6 — Provider SQLite

**Objetivo:** eliminar supuestos de arquitectura propios de servidores tradicionales.

- [ ] Driver estándar `sqlite3`.
- [ ] Admitir rutas de archivo y `:memory:` en tests.
- [ ] Introspección mediante `sqlite_schema`, `PRAGMA table_list` y `PRAGMA table_xinfo`.
- [ ] Representar `main`, `temp` y bases adjuntas sin fingir schemas SQL tradicionales.
- [ ] Modelar type affinity y conservar la declaración nativa completa.
- [ ] Detectar tablas `STRICT` y columnas generadas/ocultas.
- [ ] Marcar operaciones que requieren reconstrucción de tabla.
- [ ] Generar un plan explícito de rebuild cuando corresponda; no emitir un `ALTER COLUMN` inexistente.
- [ ] Añadir integración rápida con archivos temporales.

**Criterio de salida:** SQLite funciona sin dependencias externas y las limitaciones DDL se muestran como capacidades, no como errores tardíos.

## Fase 7 — Providers MySQL y MariaDB

**Objetivo:** soportar la familia MySQL sin ocultar divergencias entre productos.

- [ ] Crear utilidades compartidas bajo `providers/mysql_family`.
- [ ] Mantener `provider: mysql` y `provider: mariadb` separados.
- [ ] Usar el conector oficial definido para cada provider.
- [ ] Introspección con `information_schema` y consultas específicas para atributos no estándar.
- [ ] Modelar `UNSIGNED`, `AUTO_INCREMENT`, `ENUM`, `SET`, charset, collation y columnas generadas.
- [ ] Diferenciar database/schema según semántica del motor.
- [ ] Renderizar backticks y `MODIFY COLUMN`/`CHANGE COLUMN` cuando corresponda.
- [ ] Hacer capacidades dependientes de producto y versión.
- [ ] Añadir contenedores independientes de MySQL y MariaDB.
- [ ] Evitar asumir compatibilidad total entre ambos en golden files.

**Criterio de salida:** ambos providers pasan el mismo contract suite y sus diferencias quedan limitadas a sus adapters/capabilities.

## Fase 8 — Provider Oracle

**Objetivo:** añadir Oracle sin deformar contratos ya validados.

- [ ] Driver `python-oracledb`, Thin mode como configuración predeterminada.
- [ ] Soportar DSN/Easy Connect y opciones de wallet o Thick mode como configuración avanzada.
- [ ] Introspección con `ALL_TABLES`, `ALL_TAB_COLUMNS`, constraints e índices accesibles al usuario.
- [ ] Tratar `OWNER` como schema y aplicar correctamente las reglas de mayúsculas e identificadores citados.
- [ ] Modelar `NUMBER`, `VARCHAR2`, semántica BYTE/CHAR, identity, virtual columns, JSON y tipos propios.
- [ ] Renderizar `ALTER TABLE ... MODIFY` y quoting Oracle.
- [ ] No envolver DDL Oracle con el modelo transaccional de SQL Server.
- [ ] Emitir advertencias explícitas por commit implícito y operaciones destructivas.
- [ ] Añadir integración Oracle en job separado o programado por su peso operativo.

**Criterio de salida:** Oracle cumple el contract suite de introspección y generación soportada sin lógica Oracle fuera de su provider.

## Fase 9 — Constraints, índices y metadatos avanzados

**Objetivo:** evolucionar de comparación de tablas/columnas a comparación estructural completa.

- [ ] Primary keys y unique constraints.
- [ ] Foreign keys, reglas `ON DELETE`/`ON UPDATE` y deferrability.
- [ ] Índices, orden, filtros/partial indexes, expresiones e includes.
- [ ] Check constraints.
- [ ] Defaults, identity/sequences y columnas generadas.
- [ ] Collations, charset y comentarios cuando sean relevantes.
- [ ] Findings separados por categoría y políticas de exclusión.
- [ ] Operaciones de migración nuevas con capabilities por provider.

**Criterio de salida:** el modelo no utiliza campos opcionales genéricos para esconder estructuras distintas; cada concepto tiene representación explícita.

## Fase 10 — Comparación semántica entre motores y estabilización 1.0

**Objetivo:** ofrecer compatibilidad cruzada sin prometer equivalencias falsas.

- [ ] Implementar modo `semantic` opt-in.
- [ ] Crear matriz versionada de equivalencias y pérdidas.
- [ ] Clasificar equivalencias como exactas, compatibles, potencialmente incompatibles o sin mapping.
- [ ] Añadir reportes de portabilidad separados del drift nativo.
- [ ] Requerir mapping explícito cuando el target no tenga equivalencia segura.
- [ ] Publicar API estable de providers.
- [ ] Considerar entry points para providers externos.
- [ ] Definir política de compatibilidad y versionado semántico.

**Criterio de salida:** añadir un provider interno requiere una carpeta de adapter, registro, contract tests y documentación; no cambios en el motor de comparación.

## 13. Tareas concretas por archivo actual

| Archivo actual | Acción recomendada |
|---|---|
| `config/models.py` | Convertir el perfil en modelo neutral con `provider` y opciones; eliminar lenguaje SQL Server. |
| `config/connection_string.py` | Mover completo al provider SQL Server. |
| `connectors/__init__.py` | Sustituir por adapters de conexión privados por provider. |
| `discovery/service.py` | Reemplazar por caso de uso y puerto; no importar drivers. |
| `discovery/queries.py` | Mover consulta y mapper a `providers/sqlserver/introspector.py`. |
| `discovery/errors.py` | Conservar errores públicos neutrales; mover traducción SQLSTATE/pyodbc al provider. |
| `discovery/models.py` | Migrar a `domain/schema/models.py`. |
| `compare/models.py` | Eliminar import desde discovery y usar modelos de dominio compartidos. |
| `compare/engine.py` | Conservar como núcleo puro; adaptar a `QualifiedName`, `SqlType` y políticas. |
| `compare/consolidation.py` | Dividir en operaciones, planificador, renderer SQL Server y writer. |
| `tui/actions.py` | Invocar casos de uso; no llamar directamente a extracción concreta. |
| `tui/decision_screen.py` | Recoger decisiones y mostrar warnings; no importar ni escribir DDL. |
| `cli.py` | Convertir en composition root y comandos. |
| `report/*` | Mantener neutral; ampliar para mostrar provider, tipo nativo y equivalencia semántica. |
| `pyproject.toml` | Añadir extras por driver, quality gates y entry point CLI formal. |
| `docs/roadmap.md` | Sustituir por un roadmap vivo coherente con el estado real. |

## 14. Estrategia de pruebas

### 14.1 Pirámide

- **Dominio:** unit tests puros, rápidos y exhaustivos.
- **Aplicación:** use cases con providers fake.
- **Adapters:** contract tests compartidos.
- **Integración:** una instancia real por motor.
- **Presentación:** pruebas focalizadas de CLI/TUI, sin repetir reglas de dominio.
- **Golden tests:** snapshots y DDL por provider/version.

### 14.2 Contract suite obligatorio

Todo provider debe pasar los mismos contratos:

- [ ] valida perfiles sin filtrar secretos;
- [ ] informa driver ausente de forma accionable;
- [ ] abre y cierra recursos correctamente;
- [ ] produce snapshots inmutables y deterministas;
- [ ] preserva identidad cualificada;
- [ ] normaliza tipos sin perder el tipo nativo;
- [ ] declara capacidades coherentes;
- [ ] quotea identificadores correctamente;
- [ ] no renderiza operaciones no soportadas;
- [ ] genera warnings para operaciones destructivas o con pérdida;
- [ ] no introduce dependencias del provider en dominio o reportes.

### 14.3 Calidad y CI

- [ ] Añadir `ruff` para lint y formato.
- [ ] Añadir comprobación de tipos con mypy o pyright.
- [ ] Añadir `import-linter` o prueba equivalente para la regla de dependencias.
- [ ] Añadir workflow de tests unitarios por versiones de Python soportadas.
- [ ] Añadir jobs de integración por provider.
- [ ] Ejecutar Oracle en job separado/programado si el coste del contenedor es alto.
- [ ] Mantener cobertura alta en dominio y aplicación; no perseguir cobertura artificial en plantillas o CSS.
- [ ] Añadir tests de no filtración de secretos para todos los drivers.
- [ ] Añadir tests de propiedades para quoting, identificadores y mappings de tipos.

## 15. Orden recomendado de PRs

1. `docs(architecture): define provider architecture and migration boundaries`
2. `test(sqlserver): characterize current discovery and ddl behavior`
3. `refactor(domain): centralize schema and comparison models`
4. `refactor(application): introduce compare profiles use case and ports`
5. `refactor(sqlserver): extract discovery provider without behavior changes`
6. `refactor(migration): introduce migration operations and sqlserver renderer`
7. `feat(config): add provider-aware configuration with legacy compatibility`
8. `build(packaging): split database drivers into optional extras`
9. `feat(domain): add canonical types identifiers and capabilities`
10. `feat(postgresql): add PostgreSQL provider`
11. `feat(sqlite): add SQLite provider`
12. `feat(mysql): add MySQL provider`
13. `feat(mariadb): add MariaDB provider`
14. `feat(oracle): add Oracle provider`
15. `feat(schema): compare constraints indexes defaults and identities`
16. `feat(compare): add opt-in cross-provider semantic comparison`

Cada PR debe mantener la suite verde y evitar movimientos masivos mezclados con cambios funcionales.

## 16. Prioridades

### P0 — Bloqueantes

- Regla de dependencias y ADRs.
- Pruebas de caracterización SQL Server.
- Dominio neutral.
- Provider registry.
- Extracción completa de SQL Server como adapter.
- Separación de migración IR y DDL renderer.

### P1 — Compatibilidad real

- Configuración v2.
- Drivers opcionales.
- Tipos e identificadores canónicos.
- Capabilities.
- PostgreSQL y SQLite.
- Contract tests e integración CI.

### P2 — Expansión

- MySQL y MariaDB.
- Oracle.
- Constraints, índices, defaults e identity.
- Políticas configurables.

### P3 — Madurez

- Comparación heterogénea semántica.
- Plugins externos.
- Caché e introspección paralela.
- Modo offline mediante snapshots o DDL exportado.

## 17. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Modelo canónico demasiado pobre | Preservar siempre metadatos nativos y ampliar mediante objetos explícitos. |
| Modelo canónico convertido en “cajón de strings” | Tipos y capacidades tipados; `native_options` solo como escape controlado. |
| Falsas equivalencias entre motores | Modo homogéneo predeterminado y modo semántico opt-in con niveles de compatibilidad. |
| Condicionales por provider repartidos | Registry, contracts e import-linter. |
| DDL inválido según versión | Capabilities versionadas y golden tests por versión relevante. |
| Pérdida de datos al alterar tipos | Clasificación de seguridad, warnings y operaciones `REQUIRES_DATA_MIGRATION`. |
| SQLite tratado como SQL Server pequeño | Adapter propio y estrategia explícita de rebuild. |
| MySQL y MariaDB tratados como idénticos | Providers separados con utilidades compartidas. |
| Oracle heredando transacciones T-SQL | Renderer Oracle sin wrapper transaccional genérico. |
| Instalación pesada | Extras opcionales y carga diferida. |
| Filtración de credenciales | Errores neutrales, redacción y tests específicos por driver. |
| Refactor interminable | Migración incremental, SQL Server primero y PRs pequeños. |

## 18. Métricas de éxito

La arquitectura puede considerarse conseguida cuando:

- Añadir un provider no modifica `domain/comparison/engine.py`.
- No existen imports de drivers fuera de `infrastructure/providers/<provider>`.
- No existe SQL específico de motor fuera de su provider.
- CLI, TUI y reportes trabajan con casos de uso y modelos neutrales.
- Todos los providers pasan el mismo contract suite.
- El formato legacy de SQL Server sigue funcionando durante la ventana de migración.
- Los scripts incluyen warnings y operaciones no soportadas en lugar de SQL inventado.
- La comparación homogénea es estable antes de activar comparación heterogénea.
- El roadmap, documentación y estado real del código no se contradicen.

## 19. Definición de “añadir un nuevo motor”

Un nuevo provider se considera completo cuando incorpora:

- registro y metadata del provider;
- validación de configuración;
- conexión y traducción segura de errores;
- introspector y mapper al modelo canónico;
- reglas de identificadores;
- mapper de tipos;
- capabilities por versión;
- renderer de las operaciones soportadas;
- warnings de operaciones parciales o no soportadas;
- contract tests;
- integración real;
- golden snapshots y DDL;
- documentación y ejemplo de configuración.

No debe requerir cambios en el motor N-way, los modelos de findings, la TUI, los renderers de reportes ni los providers existentes.

## 20. Resultado esperado por versiones

| Versión objetivo | Resultado |
|---|---|
| `0.3` | Arquitectura por capas, provider SQL Server extraído, config v2 y dependencias opcionales. |
| `0.4` | PostgreSQL soportado. |
| `0.5` | SQLite soportado y capabilities/rebuild validados. |
| `0.6` | MySQL y MariaDB soportados. |
| `0.7` | Oracle soportado. |
| `0.8` | Constraints, índices y metadatos avanzados. |
| `0.9` | Comparación semántica cross-provider experimental. |
| `1.0` | API de providers estable, CI completa y documentación consolidada. |

---

La decisión más importante de este roadmap es mantener el motor de comparación como núcleo puro y trasladar toda variación del proveedor a adapters explícitos. La compatibilidad multibase debe ser una propiedad de la arquitectura, no una acumulación de excepciones.
