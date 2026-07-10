# Spec Delta: Connection Profile Config

Status: NEW capability spec (no baseline exists yet at
`openspec/specs/connection-profile-config/spec.md`). This delta is the
initial version of the capability.

Scope reminder (per proposal.md): read-only loading, parsing, and validation
of local connection-profile configuration only. Live `pyodbc` connectivity,
schema discovery, comparison, reporting, and any write/persist-back path
(TUI add/edit/delete) are explicitly out of scope for this capability and
covered by later changes.

## Clarifications

### Session 2026-07-10

- **Q: Should the loader support environment variables as a credential
  source in addition to `config.local.yaml`?**
  A: No. Env vars are rejected as a credential source for v1; the loader
  is YAML-only. The "No Hardcoded Credentials" requirement text has been
  updated to state that `config.local.yaml` is the sole supported source
  and that environment variables are explicitly not supported by loader
  v1.

- **Q: Is duplicate profile-name detection case-sensitive or
  case-insensitive?**
  A: Case-insensitive. `Poliza-Service` and `poliza-service` are treated as
  the same name and rejected as a duplicate. The duplicate-name
  requirement text and scenario have been updated accordingly.

- **Q: How does the loader resolve the path to `config.local.yaml` —
  implicit cwd-relative/repo-root-relative default, or an explicit
  parameter?**
  A: Explicit parameter. The caller passes the config file path to the
  loader function; there is no implicit cwd-relative or repo-root-relative
  default resolution. The loader requirement text and a dedicated scenario
  have been added/updated to make this explicit.

- **Q: Should leading/trailing whitespace on `name` and
  `connection_string` be trimmed on load, and if so, what is trimmed?**
  A: Yes — both `name` and `connection_string` are trimmed of leading and
  trailing whitespace on load (internal whitespace is left unchanged). A
  dedicated scenario has been added, and the data-model scenario has been
  updated to point to it instead of leaving this ambiguous.

## ADDED Requirements

### Requirement: Connection Profile Data Model

The system SHALL represent a connection profile as a `ConnectionProfile`
value object exposing exactly two attributes: a `name` (the human-readable
label used later in diff reports and any consumer output) and a
`connection_string` (the raw connection string). The system SHALL NOT
decompose the connection string into host/user/password/auth-mode fields
for the caller; it MUST treat the string as an opaque value to be passed
through as-is to a future connector (`pyodbc.connect()`), so that both SQL
authentication (`UID=...;PWD=...;`) and Windows integrated authentication
(`Trusted_Connection=yes;`) are supported without the model or loader ever
branching on auth mode. By the time a `ConnectionProfile` is constructed,
`connection_string` SHALL already be in ODBC form: any ADO.NET/`SqlClient`
-style keyword present in the original input SHALL have been translated to
its ODBC equivalent once, at config-load time, per the Connection String
Translation requirement below. The translation MUST operate only on
keyword spelling, never on auth semantics — it MUST NOT change which
authentication mode a string expresses, only how that mode is spelled in
ODBC terms.

#### Scenario: Profile exposes name and raw connection string only

- **GIVEN** a `ConnectionProfile` is constructed with `name="poliza-service"`
  and `connection_string="Driver={ODBC Driver 18 for SQL Server};Server=...;Database=PolizaDB;UID=x;PWD=y;"`
- **WHEN** the profile's public attributes are inspected
- **THEN** only `name` and `connection_string` SHALL be present, with no
  derived host/user/password/auth-mode fields, and the connection string
  value SHALL be preserved verbatim aside from the loader's
  whitespace-trimming and connection-string-translation steps (see the
  dedicated whitespace-trimming scenario below); no other re-encoding or
  reformatting SHALL occur.

#### Scenario: Windows integrated auth string is accepted without special-casing

- **GIVEN** a raw connection string containing `Trusted_Connection=yes;`
  and no `UID=`/`PWD=` fragment
- **WHEN** a `ConnectionProfile` is constructed from it (after translation,
  if any translation was applicable)
- **THEN** the system SHALL accept and store it exactly like any other
  non-empty connection string, applying no auth-mode-specific parsing or
  validation branch beyond the keyword translation defined below.

### Requirement: Connection String Translation

The system SHALL translate ADO.NET/`SqlClient`-style connection-string
fragments into ODBC form at config-load time, before constructing each
`ConnectionProfile`, so that every consumer of `ConnectionProfile.connection_string`
(connectors, discovery, any future TUI) always observes an already-ODBC
string. Translation SHALL operate token-by-token: the input string is split
on `;` into `key=value` tokens, respecting `{...}` brace grouping (ODBC's
quoting mechanism) so that a braced value containing a literal `;` or `=`
is never split, and a doubled `}}` inside a brace group SHALL be treated as
a literal `}`. Keyword matching for translation purposes MUST be
case-insensitive (keys case-folded before lookup). Values MUST be passed
through byte-for-byte unchanged — never re-cased, re-quoted, or otherwise
modified — regardless of which keyword they are attached to.

The system MUST apply the following keyword-mapping table:

| Input keyword (case-insensitive) | Output | Behavior |
|---|---|---|
| `Data Source` | `Server` | renamed, value unchanged |
| `Server` | `Server` | already ODBC, pass through unchanged |
| `Initial Catalog` | `Database` | renamed, value unchanged |
| `Database` | `Database` | already ODBC, pass through unchanged |
| `User Id`, `Uid` | `UID` | renamed, value unchanged |
| `UID` | `UID` | already ODBC, pass through unchanged |
| `Password`, `Pwd` | `PWD` | renamed, value unchanged (including braced values containing `;`/`=`) |
| `PWD` | `PWD` | already ODBC, pass through unchanged |
| `Integrated Security` = `false`/`no` (case-insensitive value) | *(token dropped)* | ODBC infers non-integrated auth from presence of `UID`/`PWD` |
| `Integrated Security` = `true`/`sspi`/`yes` (case-insensitive value) | `Trusted_Connection=yes` | replaces the token |
| `Trusted_Connection` | `Trusted_Connection` | already ODBC, pass through unchanged |
| `Encrypt` | `Encrypt` | identical in both dialects, pass through unchanged |
| `TrustServerCertificate` | `TrustServerCertificate` | identical in both dialects, pass through unchanged |
| `Driver` | `Driver` | already ODBC; its presence suppresses auto-prepend |
| any other keyword | *(pass through unchanged)* | fail-open per-keyword; unknown keys are preserved verbatim |

If, after translation, no `Driver=` keyword is present in the resulting
string, the system SHALL prepend `Driver={ODBC Driver 18 for SQL Server};`
to it. If a `Driver=` keyword is already present (whether original or
surviving from the input), the system MUST NOT prepend or add a second one.

#### Scenario: Pure ADO.NET string is fully translated

- **GIVEN** a raw connection string
  `"Data Source=srv1;Initial Catalog=PolizaDB;User Id=u;Password=p;"`
- **WHEN** the loader translates it at config-load time
- **THEN** the resulting string SHALL contain `Server=srv1`,
  `Database=PolizaDB`, `UID=u`, and `PWD=p` in place of their ADO.NET
  equivalents, and SHALL have `Driver={ODBC Driver 18 for SQL Server};`
  prepended, since no `Driver=` token was present in the input.

#### Scenario: Mixed ODBC-and-ADO.NET string translates correctly

- **GIVEN** a raw connection string containing both an ODBC `Driver=`
  token and untranslated ADO.NET keywords in the same string, e.g.
  `"Driver={ODBC Driver 18 for SQL Server};Data Source=IBPFMPRU.example;Initial Catalog=SegurosEcosistemaAutos;User Id=USR_x;Password=xxxxxxxxx;Integrated Security=False;Encrypt=True;TrustServerCertificate=True;"`
  (the real-world `autos` profile shape discovered during exploration)
- **WHEN** the loader translates it at config-load time
- **THEN** the resulting string SHALL retain the original `Driver=` token
  unchanged (no duplicate `Driver=` token SHALL be added), SHALL rename
  `Data Source` to `Server`, `Initial Catalog` to `Database`, `User Id` to
  `UID`, and `Password` to `PWD` with each value preserved unchanged, SHALL
  drop the `Integrated Security=False` token entirely (relying on the
  presence of `UID`/`PWD` to imply non-integrated auth), and SHALL leave
  `Encrypt=True` and `TrustServerCertificate=True` unchanged, since they are
  identical in both dialects.

#### Scenario: Pure-ODBC string is byte-identical after translation

- **GIVEN** a raw connection string that already uses only ODBC keywords,
  e.g. `"Driver={ODBC Driver 18 for SQL Server};Server=srv1;Database=PolizaDB;UID=u;PWD=p;"`
  or `"Driver={ODBC Driver 18 for SQL Server};Server=srv2;Database=SiniestroDB;Trusted_Connection=yes;"`
- **WHEN** the loader translates it at config-load time
- **THEN** the resulting string SHALL be byte-identical to the input,
  since none of its tokens match a renamed ADO.NET keyword, `Integrated
  Security` does not appear, and a `Driver=` token is already present so
  nothing is prepended. This guarantee MUST hold for every pre-existing
  pure-ODBC example, test, and archived-change connection string in the
  repository (including `config.example.yaml`'s `salud`,
  `example-sql-auth`, and `example-windows-auth` entries), verified by a
  regression test suite that runs each such string through the translator
  and diffs the result against the original, character for character.

#### Scenario: Duplicate keyword — last occurrence wins

- **GIVEN** a raw connection string containing both a mapped and an
  already-ODBC form of the same logical keyword, e.g.
  `"Data Source=old-srv;Server=new-srv;"` or
  `"Password=old-pwd;PWD=new-pwd;"`
- **WHEN** the loader translates it at config-load time
- **THEN** the resulting string SHALL retain only the value from whichever
  token appeared later in the original string (`Server=new-srv`, or
  `PWD=new-pwd`, respectively) and SHALL drop the earlier-occurring token
  entirely, so no duplicate keyword remains in the output.

#### Scenario: Driver auto-prepend only when entirely absent

- **GIVEN** a raw connection string with no `Driver=` token anywhere,
  whether before or after translation (e.g. a pure ADO.NET string with no
  driver hint)
- **WHEN** the loader translates it at config-load time
- **THEN** the system SHALL prepend `Driver={ODBC Driver 18 for SQL Server};`
  to the translated result

#### Scenario: Driver auto-prepend is suppressed when Driver is already present

- **GIVEN** a raw connection string that already contains a `Driver=`
  token, in any letter casing (e.g. `driver=...` or `DRIVER=...`), whether
  or not the string also contains ADO.NET keywords
- **WHEN** the loader translates it at config-load time
- **THEN** the system SHALL NOT prepend or add any additional `Driver=`
  token; exactly one `Driver=` token SHALL remain in the output.

#### Scenario: Integrated Security true/sspi maps to Trusted_Connection=yes

- **GIVEN** a raw connection string containing `Integrated Security=True;`,
  `Integrated Security=true;`, or `Integrated Security=sspi;` (any letter
  casing of the keyword or value)
- **WHEN** the loader translates it at config-load time
- **THEN** the token SHALL be replaced with `Trusted_Connection=yes` in the
  resulting string.

#### Scenario: Integrated Security false/no is dropped

- **GIVEN** a raw connection string containing `Integrated Security=False;`
  or `Integrated Security=No;` (any letter casing), typically alongside
  `UID=`/`PWD=` or their ADO.NET equivalents
- **WHEN** the loader translates it at config-load time
- **THEN** the `Integrated Security` token SHALL be dropped entirely from
  the resulting string, with no `Trusted_Connection` token added in its
  place, relying on the presence of `UID`/`PWD` (post-translation) to imply
  non-integrated auth.

#### Scenario: Unrecognized keywords pass through unchanged

- **GIVEN** a raw connection string containing a keyword that is neither
  an ODBC keyword nor a mapped ADO.NET keyword (e.g. a driver-specific
  option not covered by the mapping table)
- **WHEN** the loader translates it at config-load time
- **THEN** that token SHALL be preserved verbatim in the output, unmodified
  in key or value, and SHALL NOT by itself cause a translation error.

### Requirement: Unrecognized Connection String Format Is Rejected

The system SHALL reject, at config-load time, any connection string for
which tokenizing yields zero tokens recognized as either an ODBC keyword or
a mapped ADO.NET keyword — i.e., the translator recognizes nothing in the
string at all. The system SHALL also reject any connection string with
malformed brace grouping (an unterminated `{`) as a hard error, rather than
attempting a partial or best-effort parse. In both cases the system SHALL
raise a new `ProfileValidationError` case (e.g.
`.unrecognized_connection_string_format(name)`) whose message includes only
the profile `name` — it MUST NOT include the connection string, any of its
tokens, or any extracted value, matching the existing secret-safety
discipline already enforced for every other validation error in this
module.

#### Scenario: String with zero recognized tokens is rejected

- **GIVEN** a `config.local.yaml` entry whose connection-string value
  contains no `=` at all (e.g. a single opaque garbage value) or contains
  only keywords absent from both the ODBC and ADO.NET recognized sets
- **WHEN** the loader attempts to translate and validate this profile
- **THEN** it SHALL raise a `ProfileValidationError` identifying the
  unrecognized connection-string format for that profile `name`, without
  including the connection string, any token, or any value in the error
  message.

#### Scenario: Malformed brace grouping is rejected

- **GIVEN** a `config.local.yaml` entry whose connection-string value
  contains an unterminated `{` (a brace opened but never closed)
- **WHEN** the loader attempts to tokenize this profile's connection string
- **THEN** it SHALL raise a `ProfileValidationError` identifying the
  malformed/unrecognized connection-string format for that profile `name`,
  without attempting a partial parse and without including the connection
  string, any token, or any value in the error message.

#### Scenario: Unrecognized-format error never leaks connection-string content

- **GIVEN** any profile whose connection string triggers the
  unrecognized-format or malformed-brace error path, including a
  real-looking string with `UID=`/`PWD=`-style fragments embedded in
  otherwise-unrecognized keywords
- **WHEN** the resulting exception message is inspected
- **THEN** it SHALL contain only the profile `name` and SHALL NOT contain
  the connection string value or any substring of it, confirming the
  existing secret-safety guardrail extends to this new error case.
- **AND** the exception SHALL NOT be raised via `raise ... from <exc>`
  chaining a lower-level exception whose own message or arguments embed
  connection-string content (e.g. a regex/parser error echoing the
  offending fragment) — matching the discipline `config/loader.py` already
  applies to `yaml.YAMLError` — so that no connection-string content can
  surface even in a full traceback, not only in the top-level message.

### Requirement: Load Profiles From Local YAML Config

The system SHALL load connection profiles from a git-ignored local YAML
file (conventionally named `config.local.yaml`) containing a top-level
`databases:` mapping of profile name (string key) to raw connection string
(string value), and SHALL return the parsed result as a list (or equivalent
ordered collection) of `ConnectionProfile` objects, supporting an arbitrary
number of named database entries (multi-database, not limited to a fixed
count). The loader function SHALL accept the config file path as an
explicit parameter supplied by the caller; the loader MUST NOT perform any
implicit path resolution (no cwd-relative default, no repo-root-relative
default, no environment-variable-derived path) — the caller is solely
responsible for determining and passing the correct path.

#### Scenario: Loader accepts an explicit file path parameter

- **GIVEN** a valid connection-profile YAML file saved at an arbitrary
  filesystem location (not necessarily named `config.local.yaml` or
  located at the repo root or the current working directory)
- **WHEN** the caller invokes the loader function, passing that file's path
  as an explicit argument
- **THEN** the loader SHALL read and parse the file at exactly that path,
  with no fallback to a cwd-relative or repo-root-relative default path if
  the argument is omitted — omitting the path argument SHALL be a caller
  error (e.g. a `TypeError`/missing-argument error), not a silently-resolved
  default location.

#### Scenario: Multiple named database profiles load successfully

- **GIVEN** a `config.local.yaml` file containing:
  ```yaml
  databases:
    poliza-service: "Driver={ODBC Driver 18 for SQL Server};Server=srv1;Database=PolizaDB;UID=u;PWD=p;"
    siniestro-service: "Driver={ODBC Driver 18 for SQL Server};Server=srv2;Database=SiniestroDB;Trusted_Connection=yes;"
  ```
- **WHEN** the loader reads this file
- **THEN** it SHALL return a collection of exactly two `ConnectionProfile`
  objects, one named `poliza-service` and one named `siniestro-service`,
  each carrying its corresponding connection string unchanged.

#### Scenario: Loader supports an arbitrary number of profiles

- **GIVEN** a `config.local.yaml` file with a `databases:` mapping
  containing N entries (N being any count greater than zero, e.g. 3, 10,
  or 20)
- **WHEN** the loader reads this file
- **THEN** it SHALL return exactly N `ConnectionProfile` objects, with no
  hardcoded upper or lower bound on the number of supported profiles other
  than "at least one" (see empty-config validation requirement below).

#### Scenario: Leading/trailing whitespace is trimmed from name and connection string on load

- **GIVEN** a `config.local.yaml` file whose `databases:` mapping contains
  an entry with leading and/or trailing whitespace around the profile name
  key (e.g. `"  poliza-service  "`) and/or around the connection-string
  value (e.g. `"  Driver=...;PWD=y;  "`)
- **WHEN** the loader reads and parses this file
- **THEN** the resulting `ConnectionProfile.name` and
  `ConnectionProfile.connection_string` SHALL have leading and trailing
  whitespace stripped (trimmed), while internal whitespace (within the
  name or within the connection string body) SHALL be left unchanged.

### Requirement: No Hardcoded Credentials

The system SHALL NOT contain any real or literal credential value (server
address, username, password, or full connection string pointing at a real
database) in committed source code, tests, or documentation. All
credential-bearing connection strings MUST originate from a
`config.local.yaml` file (git-ignored) — never from a value embedded in a
`.py` file, a docstring, a default parameter, or an environment variable.
Loader v1 supports YAML file input only; environment variables are NOT a
supported credential source.

#### Scenario: Loader has no built-in fallback credentials

- **GIVEN** the connection-profile loader module's source code
- **WHEN** it is inspected for any default/fallback connection string or
  credential literal
- **THEN** none SHALL be present; the loader's only source of profile data
  SHALL be the external `config.local.yaml` file passed to it, never an
  environment variable and never a hardcoded value baked into the module.

#### Scenario: config.local.yaml is git-ignored

- **GIVEN** the repository's `.gitignore` file
- **WHEN** it is inspected
- **THEN** it SHALL contain an entry that matches `config.local.yaml`,
  preventing the file (and therefore any real credentials within it) from
  ever being committed to source control.

### Requirement: Committed Example Config Template

The system SHALL ship a committed `config.example.yaml` file, at the repo
root (or the config directory, consistent with `sdd-design` placement),
documenting the expected `databases:` mapping shape using placeholder
values only (no real server names, usernames, or passwords), so a new
developer can copy it to `config.local.yaml` and edit in their own values.

#### Scenario: Example file contains no real credentials

- **GIVEN** the committed `config.example.yaml`
- **WHEN** its contents are inspected
- **THEN** every connection-string value SHALL use clearly-placeholder
  content (e.g. `Server=your-server;Database=YourDb;UID=your-user;PWD=your-password;`
  or an equivalent Windows-auth placeholder using `Trusted_Connection=yes;`),
  and SHALL NOT reference any real internal hostname, username, or
  password.

#### Scenario: Example file demonstrates both auth modes

- **GIVEN** the committed `config.example.yaml`
- **WHEN** its `databases:` mapping is inspected
- **THEN** it SHALL include at least one placeholder entry illustrating SQL
  authentication (`UID=...;PWD=...;`) and at least one placeholder entry
  illustrating Windows integrated authentication (`Trusted_Connection=yes;`),
  so both supported auth styles are discoverable from the template alone.

### Requirement: Fail-Fast Validation Without Secret Leakage

The system SHALL validate loaded profile data and fail fast — raising a
clear, actionable error before returning control to the caller — for each
of the following conditions: an empty or blank profile name, a duplicate
profile name (duplicate detection is case-insensitive — e.g. `Poliza-Service`
and `poliza-service` collide and count as a duplicate), an empty or blank
connection string, a missing `config.local.yaml` file, and a
malformed/unparsable YAML file. Every error
message and any log output produced along these paths MUST NOT include the
connection string value or any fragment of it (including but not limited to
substrings such as `PWD=`, `UID=`, `Password=`, `Trusted_Connection=`, host
or database names extracted from within a connection string). Only the
profile `name` (never file-path-adjacent secrets) MAY appear in
error/log output. The system MUST NOT surface a raw stack trace/traceback
to the end user as the primary error signal for these validation failures.

#### Scenario: Missing config file fails fast with actionable guidance

- **GIVEN** no file exists at the path explicitly passed to the loader
  function
- **WHEN** the loader attempts to load connection profiles
- **THEN** it SHALL raise a clear, actionable error (not a raw
  `FileNotFoundError` traceback surfaced as-is to the user) that references
  `config.example.yaml` as the template to copy, and the error message
  SHALL NOT contain any connection-string content (since none could have
  been read).

#### Scenario: Malformed YAML fails fast without a raw stack trace

- **GIVEN** a `config.local.yaml` file containing invalid YAML syntax
- **WHEN** the loader attempts to parse it
- **THEN** it SHALL raise a clear, actionable error describing that the
  file is malformed, without leaking the raw parser traceback as the
  user-facing message and without including any connection-string
  fragment from the (possibly partially parsed) content.

#### Scenario: Empty profile name is rejected

- **GIVEN** a `config.local.yaml` file whose `databases:` mapping contains
  an entry with an empty-string or blank (whitespace-only) key
- **WHEN** the loader validates the parsed entries
- **THEN** it SHALL raise a validation error identifying that a profile
  name is empty/blank, without including the associated connection string
  value in the error message.

#### Scenario: Duplicate profile name is rejected (case-insensitive)

- **GIVEN** a `config.local.yaml` file whose `databases:` mapping contains
  two entries whose names are equal under a case-insensitive comparison
  (e.g. a re-declared identical YAML key, or two distinct keys such as
  `Poliza-Service` and `poliza-service` that differ only in letter case)
- **WHEN** the loader validates the parsed entries
- **THEN** it SHALL raise a validation error identifying the duplicated
  profile name, without including either connection-string value in the
  error message; profile name comparison for duplicate detection SHALL be
  case-insensitive, so names differing only in case are treated as the
  same name and rejected.

#### Scenario: Empty connection string is rejected

- **GIVEN** a `config.local.yaml` file whose `databases:` mapping contains
  a profile name mapped to an empty-string or blank (whitespace-only)
  connection string
- **WHEN** the loader validates the parsed entries
- **THEN** it SHALL raise a validation error identifying which profile
  `name` has an invalid (empty) connection string, without needing to (and
  without) echoing the empty value itself as if it were meaningful secret
  content.

#### Scenario: No connection-string fragment ever appears in raised errors or logs

- **GIVEN** any validation failure path (missing file, malformed YAML,
  empty/duplicate name, empty connection string) exercised against a
  `config.local.yaml` containing at least one real-looking connection
  string with `UID=`/`PWD=`/`Trusted_Connection=` fragments
- **WHEN** the resulting exception message and any emitted log lines are
  inspected
- **THEN** none of them SHALL contain the connection string value or any
  substring of it, confirming the guardrail holds even on error paths (not
  only the happy path).

### Requirement: No Live Connectivity or Downstream Logic in Scope

The system's connection-profile-config capability SHALL only produce an
in-memory, validated collection of `ConnectionProfile` objects; it SHALL
NOT open a `pyodbc` connection, perform any network I/O against a SQL
Server instance, query `INFORMATION_SCHEMA`/`sys.*` catalog views, perform
schema comparison, or render any report. Any such behavior belongs to a
later capability that consumes this module's output.

#### Scenario: Loader returns without touching the network

- **GIVEN** a valid `config.local.yaml` with one or more profiles
- **WHEN** the loader loads and validates the profiles
- **THEN** it SHALL return the in-memory collection of `ConnectionProfile`
  objects without establishing any network connection, without importing
  or invoking `pyodbc.connect()`, and without performing any schema
  discovery, comparison, or reporting action.
