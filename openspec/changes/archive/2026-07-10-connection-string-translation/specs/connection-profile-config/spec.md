# Spec Delta: Connection Profile Config — Connection String Translation

Status: DELTA on top of the baseline capability at
`openspec/specs/connection-profile-config/spec.md`. This delta extends the
existing `connection-profile-config` domain with load-time ADO.NET-to-ODBC
connection-string translation; it does not fork a new capability.

Scope reminder (per `proposal.md`): translation is a pure keyword-spelling
rewrite performed once, at config-load time, before a `ConnectionProfile` is
constructed. It never decomposes the string into host/user/password/auth
fields, never validates connectivity or credentials, and never touches any
call site outside `config/loader.py`.

## MODIFIED Requirements

### Requirement: Connection Profile Data Model

The system SHALL represent a connection profile as a `ConnectionProfile`
value object exposing exactly two attributes: a `name` and a
`connection_string`. The system SHALL NOT decompose the connection string
into host/user/password/auth-mode fields for the caller. By the time a
`ConnectionProfile` is constructed, `connection_string` SHALL already be in
ODBC form: any ADO.NET/`SqlClient`-style keyword present in the original
input SHALL have been translated to its ODBC equivalent once, at
config-load time, per the Connection String Translation requirement below.
The translation MUST operate only on keyword spelling, never on auth
semantics — it MUST NOT change which authentication mode a string expresses,
only how that mode is spelled in ODBC terms.

#### Scenario: Profile exposes name and raw connection string only

- **GIVEN** a `ConnectionProfile` is constructed with `name="poliza-service"`
  and `connection_string="Driver={ODBC Driver 18 for SQL Server};Server=...;Database=PolizaDB;UID=x;PWD=y;"`
- **WHEN** the profile's public attributes are inspected
- **THEN** only `name` and `connection_string` SHALL be present, with no
  derived host/user/password/auth-mode fields, and the connection string
  value SHALL be preserved verbatim aside from the loader's
  whitespace-trimming and connection-string-translation steps; no other
  re-encoding or reformatting SHALL occur.

#### Scenario: Windows integrated auth string is accepted without special-casing

- **GIVEN** a raw connection string containing `Trusted_Connection=yes;`
  and no `UID=`/`PWD=` fragment
- **WHEN** a `ConnectionProfile` is constructed from it (after translation,
  if any translation was applicable)
- **THEN** the system SHALL accept and store it exactly like any other
  non-empty connection string, applying no auth-mode-specific parsing or
  validation branch beyond the keyword translation defined below.

## ADDED Requirements

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

## Clarifications

No material ambiguities found; reviewed on 2026-07-10.

Verification performed for this pass:
- **Secret-safety across all new error paths**: both new-error triggers
  (zero recognized tokens; unterminated `{`) route through the single
  name-only `ProfileValidationError.unrecognized_connection_string_format`
  constructor, consistent with the existing discipline in `config/errors.py`
  and `config/loader.py` (which already avoids embedding `str(exc)` from
  `yaml.YAMLError` for the same reason). One gap was found and closed with
  a normative addition above: the spec did not explicitly forbid exception
  chaining (`raise ... from exc`) that could leak connection-string content
  via a lower-level exception's own message when a full traceback is
  logged. This is now covered by an added assertion on the existing
  "Unrecognized-format error never leaks connection-string content"
  scenario.
- **Byte-identical backward-compatibility guarantee is testable**: the
  fixture set is finite and already named in the spec/proposal —
  `config.example.yaml`'s `example-sql-auth` and `example-windows-auth`
  entries, `config.local.yaml`'s pure-ODBC real entries (e.g. `salud`), and
  the archived `connection-profile-config` spec's `poliza-service` /
  `siniestro-service` samples — all confirmed present in the repository by
  direct inspection. A straightforward "run each through the translator,
  assert `result == original`" test is directly implementable from the
  spec as written; no further clarification is needed.
