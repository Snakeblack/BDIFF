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
`connection_string` (the raw, unparsed ODBC connection string). The system
SHALL NOT decompose the connection string into host/user/password/auth-mode
fields; it MUST treat the string as an opaque value to be passed through
as-is to a future connector (`pyodbc.connect()`), so that both SQL
authentication (`UID=...;PWD=...;`) and Windows integrated authentication
(`Trusted_Connection=yes;`) are supported without the model or loader ever
branching on auth mode.

#### Scenario: Profile exposes name and raw connection string only

- **GIVEN** a `ConnectionProfile` is constructed with `name="poliza-service"`
  and `connection_string="Driver={ODBC Driver 18 for SQL Server};Server=...;Database=PolizaDB;UID=x;PWD=y;"`
- **WHEN** the profile's public attributes are inspected
- **THEN** only `name` and `connection_string` SHALL be present, with no
  derived host/user/password/auth-mode fields, and the connection string
  value SHALL be preserved verbatim aside from the leading/trailing
  whitespace trimming the loader applies on load (see the dedicated
  whitespace-trimming scenario below); no other re-encoding, internal
  trimming, or reformatting SHALL occur.

#### Scenario: Windows integrated auth string is accepted without special-casing

- **GIVEN** a raw connection string containing `Trusted_Connection=yes;`
  and no `UID=`/`PWD=` fragment
- **WHEN** a `ConnectionProfile` is constructed from it
- **THEN** the system SHALL accept and store it exactly like any other
  non-empty connection string, applying no auth-mode-specific parsing or
  validation branch.

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
