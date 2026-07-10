# Exploration: Connection String Translation

## Current State

`src/schema_comparator/config/loader.py::load_profiles` reads
`config.local.yaml`, validates shape/name/blank-string rules, and constructs
`ConnectionProfile(name, connection_string)` with the raw YAML string
**unchanged** (only `.strip()` is applied). `ConnectionProfile` in
`src/schema_comparator/config/models.py` documents `connection_string` as an
opaque ODBC string "NEVER parsed into host/user/password/auth fields", and
`connectors/__init__.py::connect` passes `profile.connection_string` straight
into `pyodbc.connect(...)`. `docs/architecture/technical-baseline.md` decision
#2 documents the same "fully opaque, pass-through" contract as the recorded
architecture decision. `docs/roadmap.md` Milestone 2 already lists this
exact item as planned and pre-approved: "Accept ADO.NET-style connection
string fragments ... and translate them ... Revises technical-baseline.md
decision #2."

Critically, the workspace's own `config.local.yaml` contains a **live,
real-world motivating example** that is not a clean either/or case:

```
autos: "Driver={ODBC Driver 18 for SQL Server};Data Source=IBPFMPRU.aplicaciones.ibercaja.es;Initial Catalog=SegurosEcosistemaAutos;User Id=USR_SegurosEcosistemaAutos;Password=xxxxxxxxx;Integrated Security=False;Encrypt=True;TrustServerCertificate=True;"
```

This string already contains a `Driver=` token (from someone manually
prepending it) **and** ADO.NET-only keywords (`Data Source`, `Initial
Catalog`, `User Id`, `Password`, `Integrated Security`) that `pyodbc`/ODBC
Driver 18 do not recognize. Today this profile is passed to `pyodbc.connect`
unchanged, effectively missing a real `Server=`/`Database=`/`UID=`/`PWD=`,
which the ODBC driver manager will either reject or silently ignore. This
disproves the simple binary heuristic sketched in the task brief ("if
`Driver=` present, treat as pure ODBC and pass through unchanged") — that
rule would leave this exact real profile untranslated and still broken.

## Affected Areas

- `src/schema_comparator/config/loader.py` — best plug-in point for
  translation (see Recommendation).
- `src/schema_comparator/config/models.py` — `ConnectionProfile.connection_string`
  docstring/contract needs revision regardless of where translation happens,
  since the "NEVER parsed" claim becomes false at least at load time.
- `src/schema_comparator/config/errors.py` — needs a new error case for
  "connection string in an unrecognized/unparseable format" (distinct from
  today's `ProfileValidationError.empty_connection_string`).
- A new module is likely warranted, e.g.
  `src/schema_comparator/config/connection_string.py`, to keep the
  keyword-mapping/tokenizer logic isolated and independently unit-testable
  from YAML-loading concerns (`loader.py` stays about file/shape/duplicate
  handling; the new module owns dialect translation).
- `config.example.yaml` — should gain an ADO.NET-style example entry
  demonstrating the new supported input format, once this reaches design/apply.
- `tests/unit/config/` — new test module for the translator, plus additions
  to `test_loader.py` for the load-time integration point, following the
  existing phase-numbered-docstring convention.
- `docs/architecture/technical-baseline.md` decision #2 — must be explicitly
  revised/superseded (not silently contradicted), per the task's own
  instruction (deferred to design/apply, not touched by this explore phase).
- `docs/roadmap.md` — this item is already listed under Milestone 2; marking
  it in-progress/done is an apply-time bookkeeping step, not explore's job.

## Approaches

1. **Binary gate: "has `Driver=`?" → pass through unchanged; else translate.**
   - Pros: matches the task brief's suggested simplest heuristic; trivial to implement and reason about.
   - Cons: **disproven by real data.** The workspace's own `config.local.yaml` `autos` profile has `Driver=` *and* untranslated ADO.NET keywords side by side — this approach would leave it broken. Any string that mixes dialects (a very plausible real-world case: someone pastes an ODBC `Driver=` prefix in front of a connection string copied from an `appsettings.json`/ADO.NET `SqlClient` config) is silently mishandled.
   - Effort: Low, but wrong.

2. **Token-level translation (keyword-by-keyword), always applied.**
   Split the string into `;`-separated `key=value` tokens (respecting `{...}`
   brace grouping, since ODBC connection strings already use braces as their
   only quoting mechanism, e.g. `Driver={ODBC Driver 18 for SQL Server}`),
   case-fold each key for lookup against a keyword-mapping table, and:
   - Recognized ADO.NET-only keywords (`Data Source`, `Initial Catalog`,
     `User Id`/`Uid`, `Password`/`Pwd`) → rename to their ODBC canonical
     keyword (`Server`, `Database`, `UID`, `PWD`), values passed through
     unchanged.
   - Keywords identical in both dialects (`Encrypt`, `TrustServerCertificate`)
     → pass through unchanged (case-normalized to their canonical casing is
     optional/cosmetic, not required for `pyodbc` to accept them).
   - `Integrated Security=false` (case-insensitive) → dropped entirely (ODBC
     auth mode is implied by presence/absence of `UID`/`PWD`, so an explicit
     "false" carries no ODBC equivalent and is redundant once `UID`/`PWD`
     are present).
   - `Integrated Security=true`/`sspi` → replaced with `Trusted_Connection=yes`.
   - Already-ODBC keywords (`Server`, `Database`, `UID`, `PWD`, `Driver`,
     `Trusted_Connection`) → pass through unchanged, keys and values untouched.
   - Unrecognized keywords → pass through unchanged (fail-open, not
     fail-closed): the tool does not have a complete list of every valid
     ODBC/`SqlClient` keyword, so refusing on unknown keys would create false
     rejections; the fail-fast "unrecognized format" error is reserved for
     the case where **no** ODBC and **no** recognized ADO.NET keyword is
     found at all (see Detection below).
   - If no `Driver=` keyword survives after translation, prepend
     `Driver={ODBC Driver 18 for SQL Server};`.
   - Pros: correctly handles pure-ODBC strings (no-op, since there is nothing
     to translate and `Driver=` is already present), pure-ADO.NET strings
     (full translation), **and** the real mixed case in `config.local.yaml`
     (translates the ADO.NET tokens, keeps the pre-existing `Driver=` token,
     no duplicate `Driver=` added). Backward-compatible with every existing
     example/test/archived-change string by construction (they contain zero
     recognized ADO.NET-only keywords, so the translator is a no-op on them
     beyond the already-present `Driver=` check).
   - Cons: more implementation surface than a whole-string gate; needs a
     small, deliberately-scoped tokenizer instead of a one-line `in` check;
     must decide first-wins-vs-last-wins if both `Data Source` and `Server`
     (or both `Password` and `PWD`) appear in the same string (recommend:
     last occurrence wins, matching standard ODBC/ADO.NET driver-manager
     behavior of last-key-wins on duplicate keywords).
   - Effort: Medium.

3. **Translate at `connectors/connect` time instead of `config/loader.py` load time.**
   - Pros: keeps `ConnectionProfile.connection_string` as originally-authored
     text (arguably more "honest" persistence — what the user typed is what
     is stored/redacted/repr'd).
   - Cons: `connectors/connect` is documented as the "only call site" for
     `pyodbc.connect` and intentionally leaves driver errors untranslated,
     not string-format translated; pushing dialect-parsing there mixes a
     config-format concern into the connection boundary, and every other
     consumer of `ConnectionProfile.connection_string` (tests, future TUI
     display/edit screens per roadmap Milestone 2, `discovery` tests that
     assert the profile's connection string is never logged) would still see
     ADO.NET-style text, doubling the surface that must stay dialect-aware.
   - Effort: Medium, but pushes complexity to more call sites.

## Recommendation

Approach 2 (token-level translation), applied **at config-load time** in
`config/loader.py` (approach 3's alternative timing rejected), via a new,
independently-tested `config/connection_string.py` module:

- `load_profiles` calls the translator after trim/blank validation and
  before constructing `ConnectionProfile`, so `ConnectionProfile.connection_string`
  is always already-ODBC by the time any other code (connectors, discovery,
  a future TUI) sees it. This keeps "translate ADO.NET dialects" a single,
  well-tested seam instead of a concern every consumer must repeat.
- Detection/error rule: attempt translation unconditionally. If, after
  tokenizing, the string contains **zero** tokens recognized as either an
  ODBC keyword or a mapped ADO.NET keyword (i.e., nothing this module
  understands at all — e.g. a single opaque garbage string with no `=` in
  it), raise a new `ProfileValidationError`-style error (e.g.
  `.unrecognized_connection_string_format(name)`) rather than silently
  passing through something that will fail deep inside `pyodbc.connect`
  with a less actionable error. This is *not* a strict ADO.NET-vs-ODBC
  binary classification — it is "did we recognize anything at all" — so it
  naturally accepts pure-ODBC, pure-ADO.NET, and mixed strings, and only
  rejects genuinely unparseable input.
- `ConnectionProfile.connection_string`'s docstring must change from "NEVER
  parsed" to something like "already-ODBC by the time this object exists;
  ADO.NET-style input is translated once, at config-load time, in
  `config/loader.py`" — this is an explicit, informed revision of the
  contract, not a silent contradiction.
- `docs/architecture/technical-baseline.md` decision #2 needs a superseding
  note (design/apply phase, not this explore artifact) stating: connection
  strings are no longer required to be pre-formatted ODBC; ADO.NET/SqlClient
  fragments are now accepted and translated at load time; the "tool does not
  parse/reconstruct auth mode" clause needs narrowing to "does not change
  auth mode, only its keyword spelling" since `Integrated Security=` now is
  interpreted (dropped or mapped to `Trusted_Connection=yes`).

Keyword-mapping table (case-insensitive keys, values passed through as-is
except where noted):

| ADO.NET/SqlClient keyword | ODBC keyword | Notes |
|---|---|---|
| `Data Source` | `Server` | direct rename |
| `Server` | `Server` | already ODBC, pass through |
| `Initial Catalog` | `Database` | direct rename |
| `Database` | `Database` | already ODBC, pass through |
| `User Id`, `Uid` | `UID` | direct rename |
| `UID` | `UID` | already ODBC, pass through |
| `Password`, `Pwd` | `PWD` | direct rename; value untouched even if it contains `;`/`=` when braced |
| `PWD` | `PWD` | already ODBC, pass through |
| `Integrated Security=false` (any case) | *(dropped)* | ODBC infers non-integrated auth from presence of `UID`/`PWD` |
| `Integrated Security=true`/`sspi` (any case) | `Trusted_Connection=yes` | |
| `Trusted_Connection` | `Trusted_Connection` | already ODBC, pass through |
| `Encrypt` | `Encrypt` | identical in both dialects, pass through |
| `TrustServerCertificate` | `TrustServerCertificate` | identical in both dialects, pass through |
| `Driver` | `Driver` | already ODBC; presence suppresses the auto-prepend step |
| anything else unrecognized | *(pass through unchanged)* | fail-open per-keyword; only an all-unrecognized string is a hard error |

## Risks

- **Real motivating data disproves the brief's suggested simplest heuristic.**
  `config.local.yaml`'s `autos` profile mixes `Driver=` with untranslated
  ADO.NET keywords; a "has `Driver=` → skip" gate would leave it silently
  broken. This exploration recommends token-level translation specifically
  to cover this case; any subsequent design/apply work must keep this test
  case (or an equivalent fixture) as a required regression test.
- **Tokenizer correctness for quoting/edge cases is new attack surface for
  this codebase.** ODBC/ADO.NET connection strings allow `{...}`-braced
  values to contain literal `;` and `=`, and doubled `}}` for a literal `}`
  inside braces. A password containing `;` or `=` *unbraced* is genuinely
  ambiguous in both dialects (not just this tool's problem) — the tool
  should document that such secrets must be `{...}`-braced by the user, the
  same convention pyodbc/ODBC driver managers already require, not invent a
  new escaping scheme.
- **Case-insensitivity must be real, not just for the mapped keywords.**
  ADO.NET conventionally treats all keywords case-insensitively (`server`,
  `SERVER`, `Server` are equivalent); the lookup table must case-fold before
  matching, and this must be tested with mixed-case fixtures beyond the
  canonical casing shown in existing examples.
- **Secret-safety regression risk.** Every existing error message in
  `errors.py` is deliberately pre-composed with no interpolated
  connection-string content. The new "unrecognized format" error (and any
  translator-internal exception) must follow the same discipline — do not
  echo the offending fragment or value, only the profile `name`, mirroring
  the existing `ConfigParseError`/`ProfileValidationError` pattern.
- **`ConnectionProfile.__repr__` redaction already assumes a "settled" ODBC
  shape is not being pattern-matched** (it just prints `<redacted>`
  unconditionally), so no change needed there — but any *new* logging/debug
  path added during design (e.g. a translator that logs "detected ADO.NET
  style, translating keys: [...]") must not log values, only which keyword
  *names* (not values) were translated, if such diagnostics are added at all.
- **Duplicate/conflicting keyword precedence is undefined behavior today**
  (e.g. both `Data Source` and `Server` present, or both `Password` and
  `PWD`). Recommendation is last-occurrence-wins per standard ODBC driver
  manager convention, but this must be an explicit, tested design decision,
  not an accidental consequence of dict insertion order.
- **`docs/architecture/technical-baseline.md` decision #2 revision is a
  documentation deliverable, not optional.** The task brief is explicit that
  silently contradicting it is unacceptable; design/apply must produce an
  actual edit (e.g. an appended "Revision" note or updated decision row)
  before/alongside the code change, not after.

## Ready for Proposal

Yes. The scope is well-bounded (config-load-time keyword translation, one
new small module, one new error case, one docstring/contract revision, one
architecture-decision revision), the keyword-mapping table above is concrete
enough to drive a spec's scenarios, and the real `config.local.yaml` fixture
gives a concrete, non-hypothetical regression case that must be encoded as a
test. The proposal/spec should make normative: the exact keyword-mapping
table, the "translate unconditionally, error only when nothing recognized"
detection rule (rejecting the simpler "has `Driver=` → skip" heuristic), the
load-time integration point, case-insensitive matching, last-occurrence-wins
precedence for duplicate keywords, and the required
`technical-baseline.md` decision #2 revision.
