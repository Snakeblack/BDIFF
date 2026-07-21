# Apply Progress — `config-v2-and-optional-dependencies`

## Status

Completed.

## Tasks Completed

- [x] Extender `ConnectionProfile` en `config/models.py` agregando `provider` y `options`.
- [x] Actualizar `config/loader.py` para soportar versiones YAML v1 y v2 (`profiles:` / `databases:`).
- [x] Implementar registro diferido (*lazy import*) con `register_factory` en `ProviderRegistry`.
- [x] Capturar `ImportError` al resolver proveedores y emitir `DriverUnavailableError` con mensaje claro.
- [x] Actualizar `pyproject.toml` declarando dependencias opcionales `sqlserver = ["pyodbc>=5.0"]`.
- [x] Añadir unit tests para `ConnectionProfile` v2 y `ProviderRegistry` diferido.
- [x] Ejecutar la suite completa de pytest y verificar 0 fallos.
