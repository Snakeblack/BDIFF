# Tasks — `config-v2-and-optional-dependencies`

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Low

## Phase 1 — Config v2 Models & Loader
- [x] 1.1 Extender `ConnectionProfile` en `config/models.py` con `provider: str = "sqlserver"` y `options: dict[str, Any]`.
- [x] 1.2 Actualizar `config/loader.py` para analizar versiones v1 (legacy auto-assign `provider="sqlserver"`) y v2.
- [x] 1.3 Mantener 100% retrocompatibilidad en la inicialización y representación redacted de `ConnectionProfile`.

## Phase 2 — Lazy Registry & Optional Dependencies
- [x] 2.1 Extender `ProviderRegistry` en `infrastructure/providers/registry.py` con `register_factory` para carga diferida (*lazy import*).
- [x] 2.2 Capturar `ImportError` al resolver proveedores no instalados y lanzar `DriverUnavailableError` descriptivo.
- [x] 2.3 Actualizar `pyproject.toml` declarando `[project.optional-dependencies]`.

## Phase 3 — Verification
- [x] 3.1 Añadir pruebas unitarias para `ConnectionProfile` v2, `config/loader.py` v2 y `ProviderRegistry` diferido.
- [x] 3.2 Ejecutar la suite completa de pruebas de pytest y asegurar 0 fallos.
