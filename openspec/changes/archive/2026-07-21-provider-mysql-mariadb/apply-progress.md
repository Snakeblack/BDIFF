# Apply Progress: `provider-mysql-mariadb`

## Status: COMPLETE

### Task Execution Log
- [x] 1.1 Core package `mysql_family` implementado (`profile_parser`, `introspector`, `ddl_renderer`, `errors`).
- [x] 1.2 Adaptadores `MySqlProvider` y `MariaDbProvider` implementados.
- [x] 1.3 Registro diferido de `mysql` y `mariadb` en `ProviderRegistry`.
- [x] 1.4 Extras opcionales `mysql` y `mariadb` añadidos en `pyproject.toml`.
- [x] 2.1 Pruebas unitarias de introspección, parsing, registro y renderizado DDL en `test_mysql_mariadb_provider.py`.

### TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR | Notes / Rationale |
| ---- | --------- | ----- | ---------- | --- | ----- | ----------- | -------- | ----------------- |
| Provider Registration | `tests/unit/infrastructure/test_mysql_mariadb_provider.py` | Unit | pytest | Pass | Pass | Pass | Clean | Verified registration of mysql & mariadb |
| DDL Rendering | `tests/unit/infrastructure/test_mysql_mariadb_provider.py` | Unit | pytest | Pass | Pass | Pass | Clean | Verified backticks quoting & DDL format |
