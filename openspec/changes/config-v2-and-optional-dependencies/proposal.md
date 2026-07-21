# Proposal — `config-v2-and-optional-dependencies`

## Intent

Implementar el soporte de configuración v2 en `ConnectionProfile` (con campo `provider`, `connection_string` y `options`), soportar la carga diferida (lazy import) de proveedores en `ProviderRegistry`, y estructurar la configuración de dependencias opcionales en `pyproject.toml` para que el núcleo de BDIFF funcione de manera desacoplada sin requerir pyodbc u otros drivers de manera obligatoria.

## Scope

1. **`ConnectionProfile`**:
   - Extender el modelo `ConnectionProfile` con `provider: str = "sqlserver"` y `options: dict[str, Any] = field(default_factory=dict)`.
2. **`config/loader.py`**:
   - Soporte para sintaxis v2 `version: "2"` o detección implícita de perfiles v2 con campo `provider`.
   - Preservar retrocompatibilidad total con archivos v1 `databases:` o `profiles:` sin campo `provider` (asumiendo `provider="sqlserver"`).
3. **`ProviderRegistry` (Lazy Import)**:
   - Extender `ProviderRegistry` para registrar fábricas/callables diferidos de proveedores (`register_factory(provider_id, factory_fn)`).
   - Traducir `ImportError` al resolver proveedores en mensajes informativos sugiriendo la instalación del extra correspondiente (ej. `pip install bdiff[sqlserver]`).
4. **`pyproject.toml`**:
   - Configurar `[project.optional-dependencies]` con extras `sqlserver = ["pyodbc"]`, etc.

## Rollback Plan

Revertir los cambios en `src/schema_comparator/config/` y `pyproject.toml`.
