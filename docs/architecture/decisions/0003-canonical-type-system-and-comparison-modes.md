# 0003. Sistema de Tipos Canónico y Modos de Comparación

* Status: accepted
* Date: 2026-07-20

## Context

Diferentes motores de bases de datos tienen tipos de datos nativos con nombres, representaciones y comportamientos variados (ej. `VARCHAR` en SQL Server vs `VARCHAR2` en Oracle, `DATETIME2` vs `TIMESTAMP WITH TIME ZONE`).

Para comparar esquemas sin perder precisión ni asumir falsas equivalencias entre motores distintos, es necesario separar la comparación nativa dentro del mismo motor de la comparación semántica entre motores diferentes.

## Decision

1. **Modelo Canónico de Tipos (`SqlType`)**:
   - Representar los tipos mediante un objeto `SqlType` en el dominio con una familia semántica (`TypeFamily`: `integer`, `character`, `datetime`, `decimal`, etc.), conservando **siempre** el tipo nativo original (`native_name`) y sus atributos extensibles (longitud, precisión, escala, timezone, collation).

2. **Dos Modos de Comparación**:
   - **`native-strict` (Predeterminado)**: Compara únicamente perfiles del mismo proveedor de base de datos. Exige coincidencia exacta de tipo nativo y atributos.
   - **`semantic` (Opt-in)**: Permite comparar esquemas entre diferentes proveedores. Compara según familias semánticas y emite advertencias de portabilidad cuando existan diferencias que puedan implicar pérdida de datos o comportamientos dispares.

## Consequences

- **Positivas**:
  - Evita falsos positivos y falsos negativos al comparar entre bases del mismo motor.
  - Permite evolucionar hacia comparaciones heterogéneas sin corromper la precisión nativa.
- **Consecuencias**:
  - Requiere mantener un mapeo declarativo por proveedor hacia la familia canónica.
