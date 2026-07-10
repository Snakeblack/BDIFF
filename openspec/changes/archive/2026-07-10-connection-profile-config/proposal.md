# Proposal: Connection Profile Config

## Change Class

normal

## Why

The schema-drift comparator cannot extract or compare anything until it can
reliably connect to each microservice's SQL Server database. Per
`docs/roadmap.md` Milestone 1, **connection profile config (multi-database,
no hardcoded credentials)** is the first capability to build — every later
capability (schema extraction, N-way comparison, reporting) depends on a
resolved set of named connection profiles being loadable at runtime.

Today the repository has only the scaffolded package skeleton (from
`scaffold-project`) with an empty `src/schema_comparator/config/` package —
no loading, validation, or persistence logic exists yet. Without this
capability, no other Milestone 1 work can start with real data: there is
nothing to connect to programmatically, and credentials would otherwise
risk being hardcoded ad hoc by whoever builds the next capability first.

## What Changes

Implement the **connection-profile configuration mechanism**: load, validate,
and expose a set of named SQL Server connection profiles from local,
git-ignored config — supporting both SQL authentication and Windows
integrated authentication, per the resolved architecture in
`docs/architecture/technical-baseline.md` (decisions #1, #2, #10).

Concretely, in `src/schema_comparator/config/`:

- A `ConnectionProfile` data model: `name` (human-readable label used later
  in diff reports) + a raw ODBC connection string, per decision #2 (the tool
  does not decompose the string into separate host/user/password fields; it
  passes it through to `pyodbc.connect()` as-is, so both SQL auth
  (`UID=...;PWD=...;`) and Windows integrated auth (`Trusted_Connection=yes;`)
  are supported transparently without the loader needing to branch on auth
  mode).
- A loader that reads `config.local.yaml` (git-ignored, per decision #10),
  parses a `databases:` mapping of profile name -> connection string, and
  returns a list/dict of `ConnectionProfile` objects.
- Validation: reject empty/duplicate profile names, reject empty connection
  strings, and fail fast with a clear, actionable error message (never a raw
  stack trace) when the config file is missing or malformed — pointing the
  developer at `config.example.yaml` as the template to copy.
- A committed `config.example.yaml` with placeholder connection strings
  (no real credentials) documenting the expected shape, so a new developer
  clone has a copy-paste starting point.
- `.gitignore` entry for `config.local.yaml` (may already exist from
  `scaffold-project`; confirm/add if missing).
- Guardrail: connection strings and any parsed fragments of them (e.g.
  `PWD=`, `UID=`) MUST NOT be logged, printed, or included in any error
  message — only the profile `name` may ever appear in output. This applies
  even to validation/error-path code, not just the happy path.

No connectivity, schema discovery, comparison, or reporting logic is part of
this change — this capability only produces a trustworthy, in-memory list
of named connection profiles ready to be handed to a future connector
module (`pyodbc.connect(profile.connection_string)`), which is out of scope
here.

## Impact

- Affected capability: new — `connection-profile-config` (first capability
  spec in `openspec/specs/`).
- Affected code: `src/schema_comparator/config/` (currently an empty
  placeholder package from `scaffold-project`); `tests/unit/` (new unit
  tests, mocked file I/O, no real DB or network); `config.example.yaml`
  (new, repo root or config dir per `sdd-design`); `.gitignore` (confirm
  entry).
- Affected specs: none exist yet to modify — this change authors the first
  spec delta under `openspec/specs/connection-profile-config/`.
- No changes to `pyproject.toml` dependencies beyond what's already declared
  (this capability is pure Python + YAML parsing, e.g. `PyYAML`; no
  `pyodbc`/`textual` dependency needed here — those belong to the
  connectors/TUI capabilities that consume this one later).
- No behavior change to existing shipped code — this is the first
  behavioral capability built on top of an otherwise-empty scaffold, so
  there is no prior behavior to regress.

## Capabilities In Scope

1. **Connection profile data model** — a `ConnectionProfile` (name + raw
   connection string) as the unit the rest of the system consumes.
2. **Profile loading from local YAML config** — read `config.local.yaml`,
   parse the `databases:` mapping into a list of profiles.
3. **Validation & fail-fast error handling** — empty/duplicate names, empty
   connection strings, missing/malformed config file, all with clear
   developer-facing messages (never a stack trace, never a leaked secret).
4. **Example config template** — `config.example.yaml` with placeholder
   values, committed to the repo as onboarding documentation.
5. **No-hardcoded-credentials guarantee** — enforced by construction
   (secrets only ever live in the git-ignored local file) and by a
   guardrail against logging/printing connection strings or their
   fragments.

## Explicitly Out of Scope (this change)

- Actual database connectivity (`pyodbc.connect()` calls, connection
  pooling/lifecycle) — next capability (`connectors`).
- Schema extraction, comparison, or reporting.
- The Textual TUI screens for add/edit/delete/list/select connections
  (decision #7, #10 in technical-baseline.md) — the TUI is a *consumer* of
  this loading/validation logic in a later capability, not built here. This
  change only guarantees the config module the TUI (and any interim CLI
  entry point) will call into.
- Any mechanism to *write*/persist profiles back to `config.local.yaml`
  (add/edit/delete) — v1 of this change is **read-only loading** of an
  already-existing local file; the TUI's own "add connection" flow
  (functional-scope.md capability #2) will extend this module later to add
  a save/write path when the TUI capability itself is built. Documented
  here as a known follow-up, not a gap in this change's acceptance.

## Risks and Rollback

- **Risk: secret leakage via logs/errors** (medium impact, low likelihood
  given guardrail is designed in from the start) — mitigated by the
  explicit guardrail above and by unit tests asserting no connection-string
  substring appears in any raised exception message or log line.
- **Risk: malformed/missing config causes a confusing crash** (low impact)
  — mitigated by fail-fast validation with actionable messages and the
  committed `config.example.yaml` reference.
- **Risk: scope creep into TUI/persistence** (low impact, would inflate
  this change) — mitigated by the explicit "read-only loading only, no
  write path" boundary stated above; write/persist is deferred to the TUI
  capability change.
- **Rollback:** purely additive — a new `config/` module, new tests, and a
  new example file, with no prior behavior depending on it yet. Revert via
  `git revert` of the change's commit(s); no data migration, no external
  state, no other module yet imports this one (scaffold's `config/` package
  is currently an empty placeholder with no callers).

---

**Branch advisory:** Before `sdd-apply` begins, a feature branch SHOULD be created following the `<tipo>/<descripción>` convention defined in the `branch-pr` skill (e.g. `git checkout -b feat/connection-profile-config main`). This note is SHOULD, not MUST.
