# Pendientes de Refactorización y Mejoras Detectadas (Judgment Day Round 1)

Este documento registra los hallazgos de severidad WARNING y SUGGESTION identificados durante la revisión adversaria de Judgment Day para ser abordados en fases subsecuentes del roadmap.

---

## 📋 Lista de Issues Pendientes

### 1. Validación temprana de número de perfiles en CLI
- **Severidad:** `WARNING (real)`
- **Archivo:** `src/schema_comparator/cli.py` (líneas 73-78)
- **Descripción:** Si el parámetro `--profiles` filtra el listado dejando menos de 2 perfiles (o se especifican nombres inexistentes), `cli.main()` lanza `InsufficientSnapshotsError` con un traceback no formateado.
- **Acción a realizar en Fase 3:** Validar `len(profiles) >= 2` tras el filtrado en `cli.main()` y mostrar un mensaje descriptivo en `sys.stderr`.

### 2. Validación temprana en `CompareProfilesUseCase`
- **Severidad:** `WARNING (real)`
- **Archivo:** `src/schema_comparator/application/use_cases/compare_profiles.py` (líneas 30-44)
- **Descripción:** `CompareProfilesUseCase.execute()` ejecuta todas las extracciones de base de datos antes de validar la cantidad de snapshots. Si se pasan < 2 perfiles, se ejecutan consultas de red innecesarias antes de fallar en `compare_snapshots`.
- **Acción a realizar en Fase 3:** Añadir guarda `if len(profiles) < 2:` en `CompareProfilesUseCase.execute()` antes de invocar los extractores.

### 3. Tipo amplio para `path_or_source` en `ProfileRepository`
- **Severidad:** `WARNING (real)`
- **Archivo:** `src/schema_comparator/application/ports/profile_repository.py` (línea 11)
- **Descripción:** El método `load_profiles` en el puerto `ProfileRepository` está tipado estrictamente como `str`, mientras que los consumidores en `config.loader` aceptan `str | Path`.
- **Acción a realizar en Fase 3:** Actualizar la firma a `path_or_source: str | Path`.

### 4. Adaptador de interfaz para `ReportSink`
- **Severidad:** `WARNING (theoretical)`
- **Archivo:** `src/schema_comparator/application/ports/report_sink.py` (línea 11)
- **Descripción:** `ReportSink` define una interfaz orientada a objetos (`write_reports(self, result)`), mientras que `report.write.write_reports` es una función libre de módulo.
- **Acción a realizar en Fase 3:** Crear un adaptador de clase `FileSystemReportSink` en `infrastructure/output/`.

### 5. Cobertura de pruebas ampliada para `CompareProfilesUseCase`
- **Severidad:** `SUGGESTION`
- **Archivo:** `tests/unit/application/test_compare_profiles.py`
- **Descripción:** Ampliar los casos de prueba para verificar el paso de patrones de exclusión `exclude_patterns` y la propagación de excepciones.
- **Acción a realizar en Fase 3:** Añadir pruebas unitarias adicionales en `test_compare_profiles.py`.

---

## 📋 Issues Change 04 — `provider-sqlserver-extraction`

### 6. Escape de identificadores y literales T-SQL
- **Severidad:** `WARNING (real)`
- **Archivo:** `src/schema_comparator/infrastructure/providers/sqlserver/ddl_renderer.py` (líneas 75-158)
- **Descripción:** Nombres de esquemas, tablas y columnas interpolados sin escapar comillas simples `'` ni corchetes `]`.
- **Acción a realizar en Fase 3:** Escapar `]` como `]]` (o `QUOTENAME`) y `'` como `''`.

### 7. Traducción de cadenas de conexión ADO.NET en `SqlServerProvider.introspect`
- **Severidad:** `WARNING (real)`
- **Archivo:** `src/schema_comparator/infrastructure/providers/sqlserver/provider.py` (líneas 24-38)
- **Descripción:** `SqlServerProvider.introspect` pasa la cadena de conexión directamente sin invocar `profile_parser.translate(...)`.
- **Acción a realizar en Fase 3:** Invocar `profile_parser.translate(profile.connection_string)` antes de conectar.

### 8. Garantía de cierre de cursor en `SqlServerProvider.introspect`
- **Severidad:** `WARNING (real)`
- **Archivo:** `src/schema_comparator/infrastructure/providers/sqlserver/provider.py` (líneas 28-36)
- **Descripción:** El objeto `cursor` no se cierra en un bloque `finally`.
- **Acción a realizar en Fase 3:** Asegurar el cierre del cursor con bloque `finally: cursor.close()`.

### 9. Eliminación insensible a mayúsculas en `profile_parser.translate`
- **Severidad:** `WARNING (theoretical)`
- **Archivo:** `src/schema_comparator/infrastructure/providers/sqlserver/profile_parser.py` (líneas 100-118)
- **Descripción:** `output.pop(key, None)` usa la grafía original en lugar de `folded_key`.
- **Acción a realizar en Fase 3:** Usar `folded_key` para limpiar claves duplicadas.

---

## 📋 Issues Change 05 — `config-v2-and-optional-dependencies`

### 10. Intercepción de claves duplicadas anidadas en `loader.py`
- **Severidad:** `WARNING (real)`
- **Archivo:** `src/schema_comparator/config/loader.py` (líneas 27-39)
- **Descripción:** `_no_duplicate_keys` intercepta todas las claves YAML duplicadas, reportando claves duplicadas anidadas dentro de `options:` como nombres duplicados de perfiles de conexión.
- **Acción a realizar en Fase 4:** Restringir la verificación de nombres duplicados únicamente al mapeo raíz de perfiles.

### 11. Nombre de paquete PyPI en mensaje de `DriverUnavailableError`
- **Severidad:** `WARNING (theoretical)`
- **Archivo:** `src/schema_comparator/infrastructure/providers/registry.py` (líneas 44-46)
- **Descripción:** El mensaje de error recomienda `pip install bdiff[{pid}]` en lugar del nombre registrado en `pyproject.toml` (`schema-comparator`).
- **Acción a realizar en Fase 4:** Ajustar el texto de recomendación del paquete a `schema-comparator[{pid}]`.


