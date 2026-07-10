# Verify Report: connection-string-translation

Date: 2026-07-11
Verifier: sdd-verify (executor phase, no delegation)

## Overall outcome: **PASS**

## 1. Test suite re-run (not trusted from narrative)

Command: `.\.venv\Scripts\python.exe -m pytest -q`

Result:
```
217 passed, 1 skipped in 2.73s
```

Matches `apply-progress.md`'s reported "217 passed, 1 skipped" exactly — not
stale. No new failures, no new skips.

## 2. Requirement-by-requirement verification

### MODIFIED: Connection Profile Data Model

- `src/schema_comparator/config/models.py`: `ConnectionProfile` remains a
  frozen dataclass with exactly `name` and `connection_string`. Docstring
  now correctly states the translation contract (load-time, once, keyword
  spelling only — never auth semantics). `__repr__` still redacts
  `connection_string` unconditionally. **Verified.**
- Scenario "Windows integrated auth string accepted without special-casing":
  `loader.py` applies no auth-mode branching; `translate()` only rewrites
  keyword spelling (`Integrated Security=true/sspi/yes` → `Trusted_Connection=yes`),
  never deciding auth mode itself. **Verified** by reading
  `connection_string.py` and `test_loader.py`.

### ADDED: Connection String Translation

Read `src/schema_comparator/config/connection_string.py` in full (not just
apply-progress narrative):

- Brace-aware tokenizer (`_tokenize`) correctly implements depth 0/1 brace
  tracking, `}}` doubling via lookahead, and raises
  `unrecognized_connection_string_format` on unterminated `{`. Confirmed
  against `test_connection_string.py`'s Phase 2 tests (plain split,
  trailing/double `;`, braced value with literal `;`, doubled `}}`,
  unterminated brace) — all pass.
- Keyword-mapping table (`_RENAME_MAP`, `_ODBC_PASSTHROUGH_KEYS`,
  `_INTEGRATED_SECURITY_*`) matches the spec's table exactly: `Data Source`→
  `Server`, `Initial Catalog`→`Database`, `User Id`/`Uid`→`UID`,
  `Password`/`Pwd`→`PWD`, ODBC keywords pass through, `Integrated Security`
  true-family → `Trusted_Connection=yes`, false-family → dropped, unknown
  keywords fail-open (pass through, don't count toward `recognized_any`).
- Last-occurrence-wins implemented via `output.pop(key, None)` then
  `output[key] = value` on **every** write branch (rename, passthrough,
  Integrated Security true/false/unknown-value, fail-open unknown) —
  matches `design.md` §1.5's called-out correctness risk exactly; verified
  by direct code reading (not just the design doc's claim).
- Driver auto-prepend: unconditional string concatenation gated on
  `has_driver`, trailing-`;` guard present. **Verified.**
- `Unrecognized Connection String Format Is Rejected` requirement: both
  trigger paths (zero recognized tokens; unterminated brace) raise
  `ProfileValidationError.unrecognized_connection_string_format(name)`
  directly, no intermediate wrapping, no `raise ... from`. **Verified** by
  code reading of `connection_string.py` and `errors.py`.

## 3. Critical checks (performed directly, not delegated to narrative)

### 3.1 Byte-identical backward compatibility

Read `tests/unit/config/test_connection_string.py`'s
`_PURE_ODBC_FIXTURES` parametrized list directly (not summary): 6 fixtures
covering `config.example.yaml`'s `example-sql-auth`/`example-windows-auth`,
`config.local.yaml`'s `salud`-shaped string, and the archived
`poliza-service`/`siniestro-service`/`only-service` (non-standard
`Driver=X`) strings. Each asserts `translate(raw, name="x") == raw`
(full-string equality, not substring). Confirmed these strings match the
actual `config.example.yaml` content read directly during this
verification. **Verified — test exists and is not a stub/skip.**

### 3.2 Real mixed-format case (`autos` profile shape)

`test_mixed_autos_shaped_string_translates_correctly` in
`test_connection_string.py` uses a string shaped exactly like the
workspace's real `autos` profile (`Driver=` + `Data Source=`/`Initial
Catalog=`/`User Id=`/`Password=`/`Integrated Security=False` combined with
`Encrypt=True;TrustServerCertificate=True;`). Asserts: exactly one
`Driver=` token, `Server=`/`Database=`/`UID=`/`PWD=` present with correct
values, `Integrated Security` entirely absent from output, `Encrypt=True`
and `TrustServerCertificate=True` unchanged. **Verified** by reading the
test source, not the apply-progress summary.

Additionally ran an ad-hoc check (see final message) using the exact
string reported in the user's session, through the real `translate()`
function — output is well-formed ODBC with no leftover ADO.NET keywords
and no duplicate `Driver=`.

### 3.3 Secret-safety

`test_error_never_leaks_connection_string_content` in
`test_connection_string.py` is a real executed test (not just code
inspection): it triggers both error paths (zero-recognized-token via a
braced sentinel value; unterminated-brace) with sentinel secrets
(`SECRET_USER`, `SECRET_PASS`, `SentinelToken`) embedded in the raw input,
then asserts:
- `str(exc)` contains only the profile name, none of the sentinels, and
  not the raw string itself.
- `exc.__cause__ is None`.
- Walking the full `__context__` chain, no chained exception's `str()`
  contains any sentinel either.

This test passed in the full suite run above. **Verified — actual test,
not just code inspection.**

### 3.4 `docs/architecture/technical-baseline.md` decision #2

Read the current file content directly (row 2 of the Decisions table,
lines ~12). Confirmed it now reads: "The tool does not change auth *mode*
... only keyword *spelling* is normalized" plus an explicit
"**Superseded/revised (connection-string-translation, 2026-07-11):**" note
describing that ADO.NET/`SqlClient` fragments are now accepted and
translated to ODBC form at load time, and that the string is still never
decomposed into separate fields. **Verified — actually updated in the
file, not just claimed in apply-progress.md.**

### 3.5 Ad-hoc real bug-scenario translation

Ran directly against the actual `translate()` function (see final message
for full output/transcript). Input was the exact string from the user's
reported session (`autos`-shaped, `Password=x`). Output:

```
Driver={ODBC Driver 18 for SQL Server};Server=IBPFMPRU.aplicaciones.ibercaja.es;Database=SegurosEcosistemaAutos;UID=USR_SegurosEcosistemaAutos;PWD=x;Encrypt=True;TrustServerCertificate=True;
```

Confirmed: single `Driver=` token (no duplicate), `Server=`, `Database=`,
`UID=`, `PWD=` all present, no leftover `Data Source=`/`Initial
Catalog=`/`User Id=`/`Password=`/`Integrated Security=` tokens. Also
constructed a `ConnectionProfile` from this translated string end-to-end —
succeeded, and `repr()` correctly redacts the connection string
(`<redacted>`) while `.connection_string` still holds the real translated
value for the connector.

## 4. Tasks.md completion

All checkbox items in `tasks.md` (Phases 1-9, through the visible RED/GREEN
task pairs) are marked `[x]`. Cross-checked against `apply-progress.md`'s
phase-by-phase narrative and the actual test file contents — no
discrepancy found between what tasks claim was done and what the test file
and source actually contain.

## Findings

No CRITICAL issues found.
No WARNING issues found.

**SUGGESTION** (non-blocking, cosmetic): in `connection_string.py`'s
`translate()`, the `Integrated Security` branch with an unrecognized value
does an `output.pop(key, None)` / `output[key] = value` write under the
*original* `Integrated Security` key rather than a normalized key — this
matches the fail-open default described in the design and is not a spec
violation, just worth a one-line comment if a future reader wonders why
this branch exists inside the `Integrated Security` `elif` rather than
falling to the generic `else`. Not required to fix.

## Conclusion

All 2 ADDED + 1 MODIFIED requirements and their 13 scenarios are correctly
implemented and covered by passing tests. All 5 critical checks requested
for this verification pass were performed directly against actual code and
actual test execution (not narrative-trusting) and all passed. Test suite
re-run confirms 217 passed, 1 skipped, matching `apply-progress.md`
exactly. `docs/architecture/technical-baseline.md` decision #2 was
directly confirmed updated. Recommend proceeding to `sdd-archive`.
