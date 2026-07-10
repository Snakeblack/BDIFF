# Proposal: Connection String Translation

## Change Class

normal

## Why

`docs/roadmap.md` Milestone 2 already lists this capability as planned and
pre-approved: accept ADO.NET/`SqlClient`-style connection string fragments
(as developers copy them straight out of a microservice's own
`appsettings.json`) and translate them into the ODBC form `pyodbc.connect()`
requires, revising `docs/architecture/technical-baseline.md` decision #2 in
the process.

The workspace's own `config.local.yaml` already contains a live,
non-hypothetical motivating example — the `autos` profile mixes a
manually-prepended `Driver={ODBC Driver 18 for SQL Server}` token with
untranslated ADO.NET-only keywords (`Data Source`, `Initial Catalog`,
`User Id`, `Password`, `Integrated Security`). Today this string is passed
to `pyodbc.connect()` unchanged, per `connectors/__init__.py::connect` and
the "fully opaque, pass-through" contract in decision #2, so it is missing
real `Server=`/`Database=`/`UID=`/`PWD=` keywords and will fail to connect
or behave unpredictably. Per `openspec/changes/connection-string-translation/exploration.md`,
the task brief's originally suggested heuristic ("if `Driver=` is present,
treat the whole string as ODBC and pass it through unchanged") is disproved
by this exact real profile: it has `Driver=` *and* untranslated ADO.NET
keywords side by side, so a binary gate would leave it silently broken.
This proposal instead adopts the exploration's recommended **token-level
translation**, which correctly handles pure-ODBC, pure-ADO.NET, and mixed
strings alike.

## What Changes

Add a token-level connection-string translator that runs at config-load
time, so every `ConnectionProfile.connection_string` is already
ODBC-formatted by the time any other code (connectors, discovery, a future
TUI) sees it.

### Where translation lives

A new module, `src/schema_comparator/config/connection_string.py`, owns the
tokenizer and keyword-mapping table, kept independently unit-testable and
separate from `config/loader.py`'s existing file/shape/duplicate-name
concerns. `load_profiles` in `config/loader.py` calls this module's
translate function once per profile, after the existing trim/blank-string
validation and before constructing `ConnectionProfile`. No other call site
(connectors, discovery, TUI) performs translation — they only ever see an
already-ODBC string.

### Tokenizer

The connection string is split on `;` into `key=value` tokens, respecting
`{...}` brace grouping (ODBC's only quoting mechanism, e.g.
`Driver={ODBC Driver 18 for SQL Server}`) so a braced value may itself
contain literal `;` or `=` without being split. Doubled `}}` inside a brace
group is treated as a literal `}`, matching existing ODBC/`SqlClient`
convention — this tool does not invent a new escaping scheme. Keys are
matched case-insensitively (case-folded before lookup); values are passed
through byte-for-byte unchanged, never re-cased, re-quoted, or otherwise
modified.

### Keyword-mapping table (normative)

| Input keyword (case-insensitive) | Output keyword | Behavior |
|---|---|---|
| `Data Source` | `Server` | renamed, value unchanged |
| `Server` | `Server` | already ODBC, pass through unchanged |
| `Initial Catalog` | `Database` | renamed, value unchanged |
| `Database` | `Database` | already ODBC, pass through unchanged |
| `User Id`, `Uid` | `UID` | renamed, value unchanged |
| `UID` | `UID` | already ODBC, pass through unchanged |
| `Password`, `Pwd` | `PWD` | renamed, value unchanged (including braced values containing `;`/`=`) |
| `PWD` | `PWD` | already ODBC, pass through unchanged |
| `Integrated Security` = `false`/`no` (case-insensitive value) | *(token dropped)* | ODBC infers non-integrated auth from presence of `UID`/`PWD`; an explicit "false" has no ODBC equivalent and is redundant |
| `Integrated Security` = `true`/`sspi`/`yes` (case-insensitive value) | `Trusted_Connection=yes` | replaces the token |
| `Trusted_Connection` | `Trusted_Connection` | already ODBC, pass through unchanged |
| `Encrypt` | `Encrypt` | identical in both dialects, pass through unchanged |
| `TrustServerCertificate` | `TrustServerCertificate` | identical in both dialects, pass through unchanged |
| `Driver` | `Driver` | already ODBC; its presence suppresses the auto-prepend step below |
| any other keyword | *(pass through unchanged)* | fail-open per-keyword — this tool does not maintain an exhaustive ODBC/`SqlClient` keyword list, so unknown keys are preserved verbatim rather than rejected |

If no `Driver=` keyword is present after translation, the string is
prefixed with `Driver={ODBC Driver 18 for SQL Server};`, matching the
driver version already used throughout `config.example.yaml` and
`docs/architecture/technical-baseline.md`.

### Duplicate-keyword precedence

**Confirmed: last-occurrence wins**, per the exploration's recommendation.
When a string contains both a mapped and an already-ODBC form of the same
logical keyword (e.g. both `Data Source=...` and `Server=...`, or both
`Password=...` and `PWD=...`), the translator keeps the value from whichever
token appears later in the original string and drops the earlier one. This
matches standard ODBC/`SqlClient` driver-manager behavior for duplicate
keywords, so it is a well-understood convention rather than an ad-hoc rule.
This precedence is a required, explicitly-tested behavior (not left as an
accidental consequence of dict/insertion order) — a mixed-duplicate fixture
is part of this change's mandatory test matrix.

### Detection and error behavior

Translation is attempted unconditionally — there is no upfront binary
classification of "this is ODBC" vs. "this is ADO.NET." The string is
rejected only if, after tokenizing, **zero** tokens are recognized as either
an ODBC keyword or a mapped ADO.NET keyword (i.e., the tool recognizes
nothing in the string at all, e.g. a single opaque value with no `=`
present). In that case, a new `ProfileValidationError` case is raised, e.g.
`.unrecognized_connection_string_format(name)`, following the existing
`errors.py` discipline: the message includes only the profile `name`,
**never** the connection string, its tokens, or any value — the same
secret-safety guarantee already enforced for every other validation error
in this module. Malformed brace grouping (an unterminated `{`) is treated
the same way: a hard, name-only error, not a partial/best-effort parse.

### Contract and documentation revisions (in scope, not deferred)

- `ConnectionProfile.connection_string`'s docstring in
  `config/models.py` changes from "NEVER parsed into host/user/password/auth
  fields" to state that ADO.NET-style input is translated once, at
  config-load time, into ODBC form, and that the object always holds an
  already-ODBC string by the time it exists. The tool still never
  decomposes the string into separate host/user/password/auth *fields* for
  the caller — the translation operates only on keyword spelling, not on
  auth semantics.
- `docs/architecture/technical-baseline.md` decision #2 is explicitly
  revised (not silently contradicted) as part of this change's scope: the
  row is updated to record that ADO.NET/`SqlClient` connection-string
  fragments are now accepted as valid profile input and translated to ODBC
  form at load time, and the "does not parse/reconstruct auth mode" clause
  is narrowed to "does not change auth *mode*, only keyword *spelling* —
  `Integrated Security=` is interpreted only to the extent of mapping it to
  its ODBC equivalent or dropping a redundant `false`." This edit ships in
  the same change as the code, not as a follow-up.
- `config.example.yaml` gains no new mixed-dialect example: it already
  contains one (the `autos` entry), which becomes this change's primary,
  non-synthetic regression fixture alongside `config.local.yaml`'s
  equivalent real profile.

### Backward compatibility guarantee

Every connection string that is already pure ODBC — including every
existing archived-change example (`connection-profile-config`'s samples),
`config.example.yaml`'s `salud`/`example-sql-auth`/`example-windows-auth`
entries, and any string containing only already-ODBC keywords — MUST
produce **byte-identical** output after translation, because none of their
tokens match a renamed ADO.NET keyword, `Integrated Security` never
appears, and a `Driver=` token is already present so nothing is prepended.
This is guaranteed by construction (the mapping table only acts on
ADO.NET-only keywords) and is asserted by a required regression test suite
that runs every pre-existing example string through the translator and
diffs the result against the original, character for character.

## Impact

- Affected code: new `src/schema_comparator/config/connection_string.py`
  (tokenizer + mapping table + translate function); `config/loader.py`
  (one new call site in `load_profiles`, between trim/blank validation and
  `ConnectionProfile` construction); `config/errors.py` (new
  `ProfileValidationError.unrecognized_connection_string_format` case);
  `config/models.py` (docstring revision only — no field/shape change to
  `ConnectionProfile`).
- Affected docs: `docs/architecture/technical-baseline.md` decision #2
  (revised, in scope of this change).
- Affected specs: `openspec/specs/connection-profile-config/spec.md` gains
  scenarios for the translation behavior (token mapping, precedence,
  detection/error, backward compatibility), since translation is a load-time
  extension of that existing capability rather than a new standalone
  capability.
- Affected tests: new unit-test module under `tests/unit/config/` for the
  translator (pure-ODBC no-op, pure-ADO.NET full translation, the real
  mixed `autos`-style case, duplicate-keyword precedence, unrecognized
  format error, secret-safety assertions on the new error's message), plus
  additions to `tests/unit/config/test_loader.py` for the load-time
  integration point.
- No `pyproject.toml` dependency changes — the tokenizer is pure
  standard-library string handling, no new package required.
- Existing consumers of `ConnectionProfile.connection_string`
  (`connectors/__init__.py::connect`, discovery, tests) are unaffected in
  behavior for already-ODBC input and gain correct behavior for ADO.NET/
  mixed input, with no call-site changes required outside `config/`.

## Capabilities In Scope

1. **Token-level connection-string translation** — tokenize on `;`
   respecting `{...}` brace grouping, case-insensitive keyword matching,
   the normative mapping table above, `Integrated Security` handling,
   last-occurrence-wins duplicate precedence, and auto-`Driver=` prepend
   when absent.
2. **Load-time integration** — `config/loader.py::load_profiles` invokes
   the translator for every profile before constructing
   `ConnectionProfile`; no other call site translates.
3. **Unrecognized-format error handling** — a new, secret-safe
   `ProfileValidationError` case for strings with zero recognized tokens,
   name-only in its message.
4. **Contract and documentation revision** — `ConnectionProfile.connection_string`
   docstring update and `docs/architecture/technical-baseline.md` decision #2
   revision, both shipped with this change.
5. **Backward-compatibility regression guarantee** — byte-identical output
   for all pre-existing pure-ODBC example/test/archived strings, enforced
   by a required test suite.

## Explicitly Out of Scope (this change)

- Decomposing `ConnectionProfile.connection_string` into separate
  host/user/password/auth fields for callers — the string remains a single
  opaque value once translated; only its keyword spelling changes.
- Any TUI screen for editing/previewing translated connection strings —
  translation is a config-load-time concern, independent of the TUI
  capability.
- Validating connectivity or credentials — this change only rewrites
  keyword spelling; it never attempts a real connection.
- Expanding the mapping table beyond the keywords identified in the
  exploration (e.g. other `SqlClient`-only keywords not seen in any real
  or example profile) — unrecognized keywords pass through unchanged by
  design, so the table can be extended later without a breaking change.

## Risks and Rollback

- **Risk: tokenizer/brace-grouping edge cases** (medium impact, low
  likelihood) — a password containing unbraced `;` or `=` is ambiguous in
  both ODBC and ADO.NET dialects, not a defect unique to this tool. Mitigated
  by documenting (in the new module's docstring) that such secrets must be
  `{...}`-braced, the same convention ODBC driver managers already require,
  and by covering braced-value fixtures in tests.
- **Risk: secret leakage via the new error path** (medium impact, low
  likelihood given the guardrail is designed in from the start) — mitigated
  by the name-only error message discipline above and a required unit test
  asserting no connection-string substring (token, key, or value) ever
  appears in the new error's rendered message.
- **Risk: duplicate-keyword precedence surprises a user** (low impact) —
  mitigated by making last-occurrence-wins an explicit, documented,
  tested rule rather than incidental behavior, and by covering it in the
  technical-baseline.md decision #2 revision.
- **Risk: backward-compatibility regression for existing profiles** (high
  impact if it occurred, low likelihood given the mapping table only
  touches ADO.NET-only keywords) — mitigated by the required
  byte-identical regression suite over every pre-existing example string
  before this change can be considered complete.
- **Rollback:** additive and load-time-scoped — revert
  `config/connection_string.py`, the one new call site in
  `config/loader.py::load_profiles`, the new error case, and the two
  docstring/decision-record edits via `git revert` of the change's
  commit(s). No data migration, no persisted state changes (translation
  happens in-memory at load time, `config.local.yaml`/`config.example.yaml`
  files themselves are never rewritten by this change), and no other
  capability depends on the new module beyond the single call site being
  reverted, so rollback restores the exact prior "opaque pass-through"
  behavior with no residual effect.

---

**Branch advisory:** Before `sdd-apply` begins, a feature branch SHOULD be
created following the `<tipo>/<descripción>` convention defined in the
`branch-pr` skill (e.g.
`git checkout -b feat/connection-string-translation main`). This note is
SHOULD, not MUST.
