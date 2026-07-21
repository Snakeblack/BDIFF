# 0005. Generación de Scripts Desacoplada e Idempotente (Write-Only)

* Status: accepted
* Date: 2026-07-20

## Context

BDIFF permite a los usuarios consolidar decisiones en la TUI e interactuar con diferencias detectadas para generar planes de remediación en SQL/DDL.

Es crítico definir la responsabilidad de la herramienta respecto a la ejecución de dichos cambios en las bases de datos de producción o pruebas.

## Decision

1. **Generación Write-Only (Sin Auto-Ejecución)**:
   - BDIFF genera artefactos DDL/SQL y planes de remediación, pero **nunca** ejecuta scripts de alteración de esquema automáticamente contra las bases de datos origen ni destino.

2. **Representación de Operaciones Intermedias**:
   - La TUI y la aplicación generan un Plan de Migración neutro compuesto por operaciones semánticas (`CreateTable`, `AddColumn`, `AlterColumn`, `DropColumn`, `RebuildTable`).
   - El adaptador DDL del proveedor destino es el encargado de renderizar dicho plan en sentencias SQL específicas de su dialecto.

3. **Clasificación de Seguridad**:
   - Toda operación generada incluye un nivel de seguridad (`SAFE`, `DESTRUCTIVE`, `REQUIRES_DATA_MIGRATION`, `UNSUPPORTED`). Operaciones destructivas o no soportadas se anotan explícitamente en el script generado como comentarios y advertencias.

## Consequences

- **Positivas**:
  - Evita la corrupción accidental o pérdida de datos en bases de datos gestionadas.
  - La TUI permanece libre de lógica de renderizado SQL o sintaxis específica por motor.
