# Apply Progress: Connection String Translation

Runner: `pytest` (via `.venv\Scripts\python.exe -m pytest`). All work done in
a single batch (no prior `apply-progress.md` existed).

## Phase 1 — Error case (`config/errors.py`)

- 1.1 (RED): added `test_unrecognized_connection_string_format_factory_contains_only_name`
  to `tests/unit/config/test_errors.py`. Confirmed failing with
  `AttributeError: ... has no attribute 'unrecognized_connection_string_format'`.
- 1.2 (GREEN): added `ProfileValidationError.unrecognized_connection_string_format(cls, name)`
  classmethod, name-only signature, actionable message referencing
  `config.example.yaml`.
- 1.3: `pytest tests/unit/config/test_errors.py` → 7 passed.

## Phase 2 — Tokenizer (`config/connection_string.py`)

- 2.1 (RED): created `tests/unit/config/test_connection_string.py` with
  tokenizer tests (plain split, trailing/double `;`, braced driver value,
  braced value with literal `;`, doubled `}}`, unterminated `{`,
  `_split_token` first-`=`-only / no-`=` cases). Confirmed failing with
  `ModuleNotFoundError` (module did not exist yet).
- 2.2 (GREEN): created `src/schema_comparator/config/connection_string.py`
  with `_tokenize` and `_split_token` per `design.md` §1.2-1.3 (single-pass
  brace-depth scanner, `}}` lookahead, `partition`-based split). No mapping
  table or `translate()` yet.
- 2.3: `pytest tests/unit/config/test_connection_string.py` → 8 passed.

## Phase 3 — Keyword mapping, Integrated Security, duplicate precedence

- 3.1 (RED): extended `test_connection_string.py` with tests against
  not-yet-implemented `translate()`: pure-ADO.NET rename, ODBC passthrough
  keywords, Integrated Security true/false variants, unrecognized-keyword
  passthrough, last-occurrence-wins duplicates (`Data Source`/`Server`,
  `Password`/`PWD`), and zero-recognized-token rejection. Confirmed failing
  with `ImportError: cannot import name 'translate'`.
- 3.2 (GREEN): implemented `_RENAME_MAP`, `_ODBC_PASSTHROUGH_KEYS`,
  `_INTEGRATED_SECURITY_KEY`/`_TRUE_VALUES`/`_FALSE_VALUES`, and `translate()`
  per `design.md` §1.4-1.5, using the `output.pop(key, None)` then
  `output[key] = value` pattern on every write path so last-occurrence-wins
  holds regardless of dict-reassignment ordering.  No driver auto-prepend
  yet (raw joined result only).
- 3.3: `pytest tests/unit/config/test_connection_string.py` → 28 passed.

## Phase 4 — Driver auto-prepend and idempotency

- 4.1 (RED): added `test_driver_auto_prepended_when_absent`,
  `test_driver_auto_prepend_suppressed_case_insensitively` (parametrized
  over `driver`/`DRIVER`/`Driver` casings), and `test_translate_is_idempotent`.
  Confirmed the prepend test failing (`assert False` — no `Driver=` prefix
  present yet).
- 4.2 (GREEN): added the unconditional string-concatenation prepend step
  using `_DEFAULT_DRIVER_TOKEN`, gated on the `has_driver` flag already
  tracked during the mapping loop, with a trailing-`;` guard before
  concatenation.
- 4.3: `pytest tests/unit/config/test_connection_string.py` → 33 passed.

## Phase 5 — Backward-compatibility byte-identical regression suite

- 5.1 (RED/verification): added the parametrized
  `test_pure_odbc_string_is_byte_identical_after_translation` covering the
  six named fixtures (`config.example.yaml`'s `example-sql-auth` and
  `example-windows-auth`; `config.local.yaml`'s `salud`; and the
  `poliza-service`/`siniestro-service`/`only-service` strings already
  present verbatim in `tests/unit/config/test_loader.py`, which is where
  the archived `connection-profile-config` change's fixtures live in this
  repository), plus `test_mixed_autos_shaped_string_translates_correctly`
  using the real `autos`-profile-shaped fixture from `config.local.yaml`.
- 5.2 (GREEN): no code changes were needed — all fixtures passed on first
  run, confirming Phases 2-4 already satisfy the backward-compatibility
  guarantee.
- 5.3: `pytest tests/unit/config/test_connection_string.py` → 40 passed.

## Phase 6 — Loader integration (`config/loader.py`)

- 6.1 (RED): added a "Phase 7" section to `tests/unit/config/test_loader.py`
  (continuing that file's existing phase-numbered convention): an ADO.NET
  string is translated to ODBC form by `load_profiles`, an unrecognized
  connection string raises `ProfileValidationError` from `load_profiles`
  itself, and the existing secret-leakage guardrail parametrization is
  extended with a case covering the new unrecognized-format failure mode.
  Confirmed all three failing (assertion mismatch / "DID NOT RAISE").
- 6.2 (GREEN): added `from schema_comparator.config.connection_string import
  translate` and the single call `connection_string = translate(connection_string,
  name=name)` inside `load_profiles`'s per-entry loop, after the existing
  blank-connection-string check and before `ConnectionProfile(...)`
  construction. No other change to `loader.py`.
- 6.3: `pytest tests/unit/config/test_loader.py` → 30 passed (existing
  Phases 3-6 plus new Phase 7).

## Phase 7 — Model docstring revision (`config/models.py`)

- 7.1 (RED): added `test_docstring_reflects_load_time_translation_contract`
  to `tests/unit/config/test_models.py`, asserting the docstring no longer
  contains "NEVER parsed into" and mentions translation. Confirmed failing
  (old phrase still present).
- 7.2 (GREEN): revised the `ConnectionProfile` docstring to state that
  ADO.NET input is translated once, at config-load time, into ODBC form,
  while still never decomposing the string into host/user/password/auth
  fields. No field, `__init__`, or `__repr__` change.
- 7.3: `pytest tests/unit/config/test_models.py` → 6 passed.

## Phase 8 — Documentation: technical baseline decision #2 revision

- 8.1: updated `docs/architecture/technical-baseline.md` decision #2 row:
  narrowed "does not parse/reconstruct auth mode" to "does not change auth
  *mode*, only keyword *spelling*", and appended a
  "Superseded/revised (connection-string-translation, 2026-07-11)" note
  documenting that ADO.NET/`SqlClient` fragments are now accepted and
  translated to ODBC form at load time. No new ADR file created, per the
  design's explicit guidance that this is sufficient documentation.

## Phase 9 — Cross-cutting secret-safety guardrail

- 9.1 (RED)/9.2 (GREEN): added
  `test_error_never_leaks_connection_string_content` to
  `test_connection_string.py`, parametrized over the zero-recognized-token
  trigger (a realistic `UID=`/`PWD=`-shaped fragment embedded as the braced
  value of an unrecognized keyword) and the unterminated-`{` trigger.
  Asserts the raised exception's message contains only the profile name,
  never the sentinel secret values or the raw string, and that neither
  `__cause__` nor any `__context__` chain link embeds the sentinel values —
  confirming `_tokenize()`/`translate()` never `raise ... from` a
  lower-level exception. No code change was required: the existing
  implementation already raises `ProfileValidationError.unrecognized_connection_string_format(name)`
  directly in both paths, with no intermediate wrapping.
- 9.3: `pytest tests/unit/config/test_connection_string.py` → 42 passed
  (all phases together).

## Final verification

Command: `pytest` (full suite, repo root)
Result: **217 passed, 1 skipped** (the skip is a pre-existing
integration-test skip unrelated to this change; no test newly skipped or
newly failing).

## Deviations from design

None. Implementation follows `design.md` §1-4 verbatim, including the
`pop`-then-set write pattern for last-occurrence-wins, the unconditional
string-concatenation driver prepend, and the name-only error factory with
no exception chaining.
