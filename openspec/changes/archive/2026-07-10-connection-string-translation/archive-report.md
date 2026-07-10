# Archive Report: connection-string-translation

Date: 2026-07-11
Archiver: sdd-archive (executor phase, no delegation)

## Outcome

**Archived.** Verification (`verify-report.md`) concluded **PASS** — 0
CRITICAL, 0 WARNING findings, all 217 tests passed (1 pre-existing skip),
all tasks in `tasks.md` marked complete. No accepted-risk or follow-up
documentation was required to proceed.

## What shipped

Added token-level translation of ADO.NET/`SqlClient`-style connection
strings into ODBC form, applied once at config-load time in
`config/loader.py::load_profiles`, before each `ConnectionProfile` is
constructed:

- New module `src/schema_comparator/config/connection_string.py`: a
  brace-aware tokenizer (splits on `;`, respects `{...}` grouping, handles
  doubled `}}`), a case-insensitive keyword-mapping table (`Data
  Source`→`Server`, `Initial Catalog`→`Database`, `User Id`/`Uid`→`UID`,
  `Password`/`Pwd`→`PWD`, `Integrated Security` true/false handling →
  `Trusted_Connection=yes` or dropped), last-occurrence-wins duplicate
  precedence, and automatic `Driver={ODBC Driver 18 for SQL Server};`
  prepending when no driver token is present.
- New error case `ProfileValidationError.unrecognized_connection_string_format(name)`
  in `config/errors.py`, raised when zero tokens are recognized or brace
  grouping is malformed; message is name-only, never leaks connection
  string content, and is never chained via `raise ... from`.
- `config/models.py`: `ConnectionProfile.connection_string` docstring
  revised to state the load-time translation contract.
- `docs/architecture/technical-baseline.md` decision #2 revised in place
  to record that ADO.NET/`SqlClient` fragments are now accepted and
  translated to ODBC form at load time, narrowing the "does not
  parse/reconstruct auth mode" clause to keyword spelling only.
- Backward-compatibility guarantee: byte-identical output for all
  pre-existing pure-ODBC strings (`config.example.yaml`'s
  `example-sql-auth`/`example-windows-auth`, `config.local.yaml`'s
  `salud`-shaped string, archived `poliza-service`/`siniestro-service`/
  `only-service` samples), enforced by a dedicated regression test suite.
- Real-world motivating case verified end-to-end: the workspace's own
  `autos` profile (mixed `Driver=` + untranslated ADO.NET keywords)
  translates correctly with no duplicate `Driver=` token and no leftover
  ADO.NET keywords.

## Tests

`pytest` run: 217 passed, 1 skipped — matches `apply-progress.md` and the
verify-report's re-run exactly. New coverage: `tests/unit/config/test_connection_string.py`
(tokenizer, mapping table, precedence, driver auto-prepend, backward-compat
regression, secret-safety), plus additions to `tests/unit/config/test_errors.py`,
`test_loader.py`, and `test_models.py`.

## Specs synced

`openspec/specs/connection-profile-config/spec.md` updated:

- **MODIFIED**: "Connection Profile Data Model" — now documents that
  `connection_string` is already ODBC-form by construction time, via
  load-time translation, and that translation only rewrites keyword
  spelling, never auth semantics.
- **ADDED**: "Connection String Translation" — tokenizer, mapping table,
  precedence, driver auto-prepend, and all 9 associated scenarios.
- **ADDED**: "Unrecognized Connection String Format Is Rejected" — hard
  rejection of unrecognized/malformed strings and its 3 associated
  scenarios.

All other requirements in the baseline spec (`Load Profiles From Local YAML
Config`, `No Hardcoded Credentials`, `Committed Example Config Template`,
`Fail-Fast Validation Without Secret Leakage`, `No Live Connectivity or
Downstream Logic in Scope`) were left unchanged.

## Decisions promoted to memory

None. No `state.yaml` exists for this change (predates that workflow
feature), so `open_decisions` promotion was skipped per the archive
skill's contract (absence is not an error).

## Follow-ups / accepted risks

None required for archival. One non-blocking, cosmetic **SUGGESTION** was
noted in `verify-report.md` (a one-line comment opportunity in the
`Integrated Security` unrecognized-value branch of `translate()`) — not a
spec violation, not required to fix, no follow-up change opened.

## Archive location

`openspec/changes/archive/2026-07-10-connection-string-translation/`
