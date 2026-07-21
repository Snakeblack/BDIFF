# 0001. Arquitectura Hexagonal Ligera y Regla de Dependencias

* Status: accepted
* Date: 2026-07-20

## Context

BDIFF nació como un comparador de esquemas desacoplado entre microservicios de SQL Server. La implementación inicial combinaba modelos de descubrimiento (`discovery`), motores de comparación (`compare`), utilidades de formateo e integración directa con `pyodbc` y la TUI/CLI.

Para poder extender BDIFF hacia múltiples motores de bases de datos (PostgreSQL, SQLite, MySQL, MariaDB, Oracle), es necesario garantizar que las reglas de comparación, la representación de objetos de base de datos y la generación de reportes no dependan de drivers de base de datos ni de frameworks de presentación.

## Decision

Adoptar una **Arquitectura Hexagonal (Puertos y Adaptadores)** ligera orientada a casos de uso con una **Regla de Dependencias estricta**:

```text
presentation ──────┐
                   ├──> application ───> domain
infrastructure ────┘
```

1. **Capas de Dominio (`domain`)**:
   - Contiene únicamente entidades inmutables (`SchemaSnapshot`, `ColumnSnapshot`, `QualifiedName`, `SqlType`), reglas de hallazgos (`findings`) y el motor de comparación puro.
   - **Regla estricta**: `domain` no puede importar nada de `application`, `infrastructure` ni `presentation`. Tampoco puede importar drivers de bases de datos ni librerías de interfaz.

2. **Capa de Aplicación (`application`)**:
   - Contiene la definición de puertos (`DatabaseProvider`, `ProfileRepository`, `ReportSink`, `ScriptSink`) mediante protocolos (`typing.Protocol`) y la lógica de casos de uso (`CompareProfilesUseCase`).
   - `application` solo depende de `domain` y sus propios contratos.

3. **Capa de Infraestructura (`infrastructure`)**:
   - Implementa los puertos definidos en `application`.
   - Contiene los proveedores específicos por motor en `infrastructure/providers/<provider>/`, encapsulando drivers, cadenas de conexión, consultas de catálogo y renderers DDL.

4. **Capa de Presentación (`presentation`)**:
   - CLI y TUI. Invocan exclusivamente casos de uso de la capa de aplicación.

## Consequences

- **Positivas**:
  - Se puede probar todo el dominio y los casos de uso sin requerir drivers reales instalados (`pyodbc`, `psycopg`, etc.).
  - Añadir un nuevo motor de base de datos se limita a crear un nuevo adaptador bajo `infrastructure/providers/` sin tocar el motor de comparación ni la presentación.
- **Riesgos / Mitigaciones**:
  - Incremento en el número de paquetes e interfaces. Se mitigará usando tipos y protocolos nativos de Python sin sobreingeniería.
