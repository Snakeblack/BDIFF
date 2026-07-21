# 0002. Registro Interno de Proveedores de Bases de Datos

* Status: accepted
* Date: 2026-07-20

## Context

BDIFF necesita cargar adaptadores de base de datos según el proveedor especificado en cada perfil de conexión (`provider: sqlserver`, `provider: postgresql`, `provider: sqlite`, etc.).

Existen dos estrategias comunes para esto:
1. Un sistema dinámico basado en `entry_points` de Python o plugins externos cargados por reflexión.
2. Un registro explícito interno (*Internal Provider Registry*).

## Decision

Implementar un **Registro Interno de Proveedores (`ProviderRegistry`)** explícito en `infrastructure/providers/registry.py`.

- Cada proveedor se registra explícitamente mediante `registry.register(SqlServerProvider())`.
- La selección de proveedor se realiza en tiempo de ejecución buscando por identificador (`provider_id`).
- La carga de dependencias pesadas o drivers específicos se realiza de manera diferida (*lazy loading*) dentro de la implementación de cada proveedor para no forzar la instalación de drivers no utilizados.
- Se difiere la implementación de `entry_points` externos para futuras versiones cuando exista una demanda real de proveedores de terceros.

## Consequences

- **Positivas**:
  - Simplicidad, seguridad de tipos y mayor trazabilidad en tiempo de compilación/linting.
  - Facilidad para instrumentar carga perezosa y diagnósticos de drivers faltantes (`bdiff providers doctor`).
- **Limitaciones**:
  - Los proveedores deben ser parte del paquete base o estar contemplados en el registro interno.
