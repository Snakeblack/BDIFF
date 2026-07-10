# Design: Connection Profile Config

Change: `connection-profile-config`
Status: design (phase artifact)
Scope: read-only loading, parsing, and validation of local connection-profile
configuration. No `pyodbc` connectivity, no discovery/compare/report, no
write/persist-back path (all deferred to later capabilities).

This design realizes the six ADDED requirements in
`openspec/changes/connection-profile-config/specs/connection-profile-config/spec.md`
and honors the four clarify decisions recorded in `state.yaml` (YAML-only
source, case-insensitive duplicate detection, explicit path parameter,
trim-on-load).

---

## 1. Module / file layout

All new code lives under the already-scaffolded (currently empty) package
`src/schema_comparator/config/`. Proposed files:

```text
src/schema_comparator/config/
  __init__.py     # public API surface: re-exports the loader, model, and error types
  models.py       # ConnectionProfile value object (frozen dataclass, redacting repr)
  errors.py       # ConfigError exception hierarchy (fail-fast, secret-safe messages)
  loader.py       # load_profiles(config_path) + YAML parsing + validation pipeline
config.example.yaml  # committed template (repo root), placeholder credentials only
```

Rationale for splitting `models` / `errors` / `loader`:

- `models.py` and `errors.py` have zero I/O and zero dependencies on PyYAML,
  so they stay trivially unit-testable and importable by future consumers
  (connectors, TUI) without pulling in loader concerns.
- `loader.py` is the only module that imports `yaml`, keeping the parsing
  dependency at the edge.
- Keeping the surface small (one public function, one value object, one error
  base) matches the "modular monolith, clear layers" architecture style in
  `docs/architecture/technical-baseline.md`.

`config.example.yaml` goes at the **repo root** (sibling of the git-ignored
`config.local.yaml`), matching the convention already established by the
existing `.gitignore` entry `config.local.yaml` (line 4) and the example
shown in `technical-baseline.md` "Connectivity & Secrets".

### Public API (`config/__init__.py`)

```python
from schema_comparator.config.models import ConnectionProfile
from schema_comparator.config.errors import (
    ConfigError,
    ConfigFileNotFoundError,
    ConfigParseError,
    ProfileValidationError,
)
from schema_comparator.config.loader import load_profiles

__all__ = [
    "ConnectionProfile",
    "load_profiles",
    "ConfigError",
    "ConfigFileNotFoundError",
    "ConfigParseError",
    "ProfileValidationError",
]
```

---

## 2. Data model: `ConnectionProfile`

### Decision: frozen `@dataclass`, not pydantic. Rationale.

Chosen: `@dataclass(frozen=True, slots=True)` from the standard library.

- **No new dependency.** `pyproject.toml` currently declares
  `dependencies = []`. This change should add exactly one runtime dependency
  (`PyYAML`, see §4). Introducing pydantic for a two-field value object is
  disproportionate and contradicts the "simple to `pip install` on any
  teammate's machine" constraint (baseline decision #6).
- **Secret-leakage safety.** This is the decisive factor. Pydantic's default
  behavior echoes field *values* into `ValidationError` messages and into the
  model `repr`. Given the hard guardrail "no connection-string fragment ever
  appears in raised errors or logs" (spec Requirement: Fail-Fast Validation),
  a library whose default failure mode is to print the offending value works
  against us. A hand-written dataclass lets us control exactly what is
  rendered.
- **Immutability = value semantics.** `frozen=True` makes the profile a true
  value object (the spec calls it a "value object"), preventing downstream
  mutation of a loaded connection string. `slots=True` blocks accidental
  attribute injection (e.g. someone stashing a parsed password on the object).

The model is deliberately *dumb*: it does not read files, does not trim, does
not validate business rules. Trimming and validation are the loader's job
(§5) so that the invariants are enforced at exactly one place and the model
stays a pure carrier.

### Shape

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class ConnectionProfile:
    """A named SQL Server connection profile.

    `connection_string` is an opaque ODBC string passed verbatim to a future
    pyodbc connector; it is NEVER parsed into host/user/password/auth fields.
    """
    name: str
    connection_string: str

    def __repr__(self) -> str:  # redact the secret even if the object is logged
        return f"ConnectionProfile(name={self.name!r}, connection_string=<redacted>)"
```

The custom `__repr__` is a defense-in-depth guardrail: even if a consumer
accidentally does `print(profile)` or a logger interpolates `%r`, the raw
connection string never surfaces. This satisfies the "even on error paths,
not only the happy path" clause of the leakage guardrail (spec scenario "No
connection-string fragment ever appears in raised errors or logs").

Only two public attributes exist (`name`, `connection_string`) — no derived
host/user/password/auth-mode fields — directly satisfying the "Profile
exposes name and raw connection string only" and "Windows integrated auth
string is accepted without special-casing" scenarios. Windows-auth strings
(`Trusted_Connection=yes;`) are stored identically to SQL-auth strings; the
model has no auth branch.

---

## 3. Loader function signature

```python
import os

def load_profiles(config_path: str | os.PathLike[str]) -> list[ConnectionProfile]:
    ...
```

Key contract points, tracing to clarify decision #3 (explicit path):

- `config_path` is a **required positional parameter with no default**.
  Omitting it raises the natural `TypeError` from Python's argument binding —
  which is exactly the spec's required behavior ("omitting the path argument
  SHALL be a caller error ... not a silently-resolved default location").
- The loader performs **no implicit path resolution**: no `os.getcwd()`
  join, no repo-root walk, no `SCHEMA_COMPARATOR_CONFIG` env var. The path is
  used exactly as given. (Reinforces the YAML-only, no-env-var clarify #1.)
- Return type is an **ordered `list[ConnectionProfile]`**, preserving YAML
  mapping insertion order (PyYAML `safe_load` preserves it on 3.7+ dicts).
  Ordering is stable so downstream diff reports can present profiles in the
  order the developer authored them.

---

## 4. YAML parsing approach

### Dependency

Add `PyYAML>=6.0` to `[project].dependencies` in `pyproject.toml` (currently
`[]`). This is the only runtime dependency this change introduces; `pyodbc`
and `textual` remain unowned by this capability (they belong to
connectors/TUI). PyYAML is already implied by `proposal.md` Impact.

### Parsing rules

1. Read the file at `config_path`. A missing file raises
   `ConfigFileNotFoundError` (§5), never a bare `FileNotFoundError` traceback.
2. Parse with **`yaml.safe_load`** (never `yaml.load` / full loader) so no
   arbitrary Python object construction is possible from config content.
3. Expect a top-level mapping with a `databases:` key whose value is a
   mapping of `name -> connection_string`. A document that is not a mapping,
   is missing `databases`, or whose `databases` is not a mapping, is a
   validation error (§5), not a crash.

### Duplicate-key handling (design detail worth calling out)

`yaml.safe_load` silently keeps the **last** value when a mapping has two
identical keys — which would defeat the "re-declared identical YAML key"
duplicate scenario in the spec. To honor it, the loader installs a small
`SafeLoader` subclass that overrides `construct_mapping` to **raise on an
exact duplicate key** before the dict collapses it:

```python
class _DuplicateKeyLoader(yaml.SafeLoader):
    pass

def _no_duplicate_keys(loader, node, deep=False):
    seen = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise ProfileValidationError.duplicate_name(str(key))
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)

_DuplicateKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicate_keys
)
```

Case-*insensitive* duplicates (e.g. `Poliza-Service` vs `poliza-service`,
which are distinct keys so PyYAML does not collapse them) are caught in the
validation pass (§5), after trimming, by comparing `name.strip().casefold()`.
Together these two mechanisms cover both halves of the spec's duplicate
scenario.

---

## 5. Validation rules (fail-fast, no secret leakage)

### Exception hierarchy (`errors.py`)

```text
ConfigError(Exception)                 # base — callers can catch this one type
├── ConfigFileNotFoundError            # path does not exist
├── ConfigParseError                   # malformed YAML / wrong top-level shape
└── ProfileValidationError             # empty/duplicate name, empty conn string
```

A single catchable base (`ConfigError`) lets the future TUI/CLI wrap all
config failures into one user-facing "your connection config is invalid"
surface without catching unrelated exceptions.

Each error carries a **pre-composed, actionable message**. Constructors are
the *only* place messages are built, which centralizes the secret-leakage
guarantee. Illustrative factory methods:

```python
class ProfileValidationError(ConfigError):
    @classmethod
    def empty_name(cls) -> "ProfileValidationError": ...
    @classmethod
    def duplicate_name(cls, name: str) -> "ProfileValidationError": ...
    @classmethod
    def empty_connection_string(cls, name: str) -> "ProfileValidationError": ...
```

### Validation pipeline (executed in order, fail-fast on first violation)

| # | Condition | Error raised | Message may contain |
|---|-----------|--------------|---------------------|
| 1 | Path does not exist | `ConfigFileNotFoundError` | the path + "copy `config.example.yaml`" hint; **no** conn-string (none read) |
| 2 | YAML syntax invalid | `ConfigParseError` | "file is malformed / not valid YAML" + example hint; **no** parser traceback, **no** conn-string fragment |
| 3 | Top-level not a mapping / no `databases` mapping | `ConfigParseError` | shape guidance + example hint |
| 4 | Exact duplicate YAML key | `ProfileValidationError` | the duplicated **name** only |
| 5 | Empty/blank name (after trim) | `ProfileValidationError` | "a profile name is empty/blank" — **no** name value (it's blank), **no** conn-string |
| 6 | Case-insensitive duplicate name (after trim/casefold) | `ProfileValidationError` | the duplicated **name** only |
| 7 | Empty/blank connection string (after trim) | `ProfileValidationError` | the offending **name** only — never the (empty) value |

### Trim-on-load (clarify decision #4)

Before validation, each entry's `name` and `connection_string` are stripped
of **leading/trailing** whitespace via `str.strip()`. Internal whitespace is
left untouched (a connection string like `Driver={ODBC Driver 18 for SQL
Server};...` keeps its internal spaces). "Empty/blank" checks therefore run
against the trimmed value, so a whitespace-only entry is treated as empty
(scenarios "Empty profile name is rejected", "Empty connection string is
rejected", and "Leading/trailing whitespace is trimmed ...").

### Secret-leakage guardrail (cross-cutting)

- **No error message ever interpolates a `connection_string` value or any
  substring of it** (no `PWD=`, `UID=`, `Password=`, `Trusted_Connection=`,
  host, or database name). Only the profile `name` may appear.
- Missing-file and malformed-YAML paths surface a clean domain error, **never
  the raw `FileNotFoundError`/`yaml.YAMLError` traceback** as the primary
  signal. The loader may chain the original as `raise ... from exc` for
  debuggers, but the *message* the user reads is the actionable domain
  string. (Note: `yaml.YAMLError` string forms can echo a snippet of the
  offending line; the loader therefore constructs its own message and does
  **not** embed `str(yaml_error)`.)
- The `ConnectionProfile.__repr__` redaction (§2) closes the accidental-log
  path.
- No fallback/default connection string exists anywhere in the module
  (satisfies "Loader has no built-in fallback credentials").

---

## 6. Load / validate flow

The flow is a linear fail-fast pipeline (no branching interactions between
components, no external calls), so per `openspec/config.yaml` `rules.design`
("sequence diagrams for complex flows") a full sequence diagram is not
warranted. A compact flowchart captures the fail-fast gates:

```mermaid
flowchart TD
    A[load_profiles(config_path)] --> B{path exists?}
    B -- no --> E1[raise ConfigFileNotFoundError\n+ point to config.example.yaml]
    B -- yes --> C[read bytes + safe_load\nwith duplicate-key loader]
    C -- YAMLError --> E2[raise ConfigParseError\n(no traceback, no fragment)]
    C -- duplicate key --> E3[raise ProfileValidationError.duplicate_name]
    C -- ok --> D{top-level has\n'databases' mapping?}
    D -- no --> E2
    D -- yes --> F[for each entry:\ntrim name + conn_string]
    F --> G{name blank?}
    G -- yes --> E4[raise ProfileValidationError.empty_name]
    G -- no --> H{name casefold\nalready seen?}
    H -- yes --> E5[raise ProfileValidationError.duplicate_name]
    H -- no --> I{conn_string blank?}
    I -- yes --> E6[raise ProfileValidationError.empty_connection_string(name)]
    I -- no --> J[append ConnectionProfile(name, conn_string)]
    J --> K[return list[ConnectionProfile]\nno network, no pyodbc]
```

The terminal node reasserts the out-of-scope guardrail: the loader returns an
in-memory list without importing `pyodbc`, opening a socket, or touching
`INFORMATION_SCHEMA` (spec Requirement: No Live Connectivity, scenario
"Loader returns without touching the network").

---

## 7. `config.example.yaml` template structure

Committed at repo root, placeholder values only, demonstrating **both** auth
modes (spec scenarios "Example file contains no real credentials" and
"Example file demonstrates both auth modes"):

```yaml
# config.example.yaml
#
# Copy this file to `config.local.yaml` (git-ignored) and replace the
# placeholder values with your real connection strings. NEVER commit
# `config.local.yaml`. Each key under `databases:` is a human-readable
# profile name used in diff reports; each value is a raw ODBC connection
# string passed as-is to the connector.
databases:
  # SQL Server authentication (username + password)
  example-sql-auth: "Driver={ODBC Driver 18 for SQL Server};Server=your-server;Database=YourDb;UID=your-user;PWD=your-password;TrustServerCertificate=yes;"

  # Windows integrated authentication (no username/password)
  example-windows-auth: "Driver={ODBC Driver 18 for SQL Server};Server=your-server;Database=YourOtherDb;Trusted_Connection=yes;"
```

Every value is obviously a placeholder (`your-server`, `your-user`,
`your-password`) — no real hostname/credential. Because the file is committed,
the "No Hardcoded Credentials" requirement is satisfied structurally: the only
committed connection strings are non-secret placeholders, and real secrets
live exclusively in the git-ignored `config.local.yaml`.

### `.gitignore`

`.gitignore` already contains `config.local.yaml` (line 4), satisfying the
"config.local.yaml is git-ignored" scenario. No change needed; the apply
phase should confirm it still matches and add it only if absent (idempotent).

---

## 8. Testing strategy

Runner: **pytest** (`openspec/config.yaml` `commands.test: ["pytest"]`;
`pyproject.toml` dev extra already pins `pytest>=8.0`). Layout matches the
existing `tests/unit` / `tests/integration` scaffold. All tests here are
**unit** tests — no DB, no network (consistent with baseline "Testing Bar").

Proposed new file: `tests/unit/config/test_loader.py` (+ optional
`test_models.py`). Fixtures write YAML into `tmp_path` and pass the resulting
path explicitly to `load_profiles`, exercising the explicit-path contract for
free (no monkeypatching of cwd).

### Coverage matrix (one test per spec scenario)

| Spec scenario | Test intent |
|---|---|
| Profile exposes name + raw string only | assert `dataclasses.fields` == (`name`, `connection_string`); no extra attrs (slots) |
| Windows integrated auth accepted | `Trusted_Connection=yes;` profile loads unchanged |
| Loader accepts explicit file path | load from an arbitrarily-named file under `tmp_path`; assert `load_profiles()` with no arg raises `TypeError` |
| Multiple named profiles load | 2-entry file → 2 profiles, strings intact |
| Arbitrary number of profiles | parametrized N in {1, 3, 20} → N profiles |
| Whitespace trimmed on load | `"  name  "` / `"  Driver=...  "` → trimmed; internal spaces preserved |
| Loader has no fallback credentials | source-inspection test: grep loader module for `UID=`/`PWD=`/`Driver=` literals → none |
| config.local.yaml git-ignored | read `.gitignore`, assert it matches `config.local.yaml` |
| Example file: no real creds | parse `config.example.yaml`, assert values contain `your-`/placeholder markers |
| Example file: both auth modes | assert at least one `UID=...;PWD=` and one `Trusted_Connection=yes;` entry |
| Missing file fails fast | non-existent path → `ConfigFileNotFoundError`, message references `config.example.yaml`, no traceback surfaced |
| Malformed YAML fails fast | invalid YAML → `ConfigParseError`, no raw parser message, no fragment |
| Empty name rejected | blank/whitespace key → `ProfileValidationError`, message has no conn-string |
| Duplicate name rejected (case-insensitive) | `Poliza-Service` + `poliza-service` → `ProfileValidationError`; also exact re-declared key case |
| Empty connection string rejected | name → blank value → `ProfileValidationError` naming the profile, not echoing value |
| No fragment ever in errors/logs | **guardrail test** (below) |
| Loader returns without touching network | with a valid file, assert `pyodbc` not imported and no socket opened |

### Secret-leakage guardrail test (critical)

A dedicated, reusable helper drives every error path against a config whose
connection strings contain sentinel secrets (e.g.
`UID=SECRET_USER;PWD=SECRET_PASS;Trusted_Connection=yes;`) and asserts that:

- `str(exc)` (and `repr(exc)`) contains none of the sentinel substrings, and
- captured log output (via `caplog`) contains none of them.

This is parametrized across all failure modes (missing file, malformed YAML,
empty/duplicate name, empty connection string) to prove the guardrail holds
on error paths, not just the happy path — directly encoding the spec's
"No connection-string fragment ever appears in raised errors or logs"
scenario. A companion assertion checks `repr(ConnectionProfile(...))` renders
`<redacted>`.

Coverage target follows the baseline bar (80%+); this module is pure logic
with no I/O beyond a file read, so near-100% is realistic and expected.

---

## 9. Architecture decisions (rationale summary)

No separate ADR file is created: all decisions below are **module-local**
(data-carrier representation, error taxonomy, parser hardening) rather than
cross-cutting architecture choices, and each is already recorded with
rationale inline above. `docs/architecture/technical-baseline.md` remains the
home for system-level decisions (#1–#10), which this design consumes rather
than amends.

| Decision | Choice | Rationale (§) |
|---|---|---|
| Model representation | frozen `@dataclass(slots=True)` over pydantic | no extra dep; pydantic default errors/repr leak field values, fighting the secret guardrail (§2) |
| Redacting `__repr__` | override to `<redacted>` | defense-in-depth against accidental logging (§2) |
| Error taxonomy | single `ConfigError` base + 3 subtypes | one catchable surface for the future TUI/CLI; messages built only in constructors to centralize leakage safety (§5) |
| YAML loader | `safe_load` + duplicate-key-detecting `SafeLoader` subclass | `safe_load` blocks arbitrary object construction; subclass catches exact-duplicate keys PyYAML would otherwise silently collapse (§4) |
| Path handling | required param, no default, no implicit resolution | clarify decision #3; omission → `TypeError` per spec (§3) |
| Example file location | repo root | matches existing `.gitignore` entry and baseline example (§7) |

---

## 10. Traceability

- proposal.md "Capabilities In Scope" 1–5 → §2 (1), §3–§4 (2), §5 (3), §7 (4),
  §2/§5/§7 (5).
- spec.md 6 ADDED requirements → §2, §3–§4, §5, §7, §5, §6 respectively; all
  scenarios mapped in the §8 coverage matrix.
- clarify approvals 001–004 → §4/§5 (YAML-only), §4/§5 (case-insensitive dup),
  §3 (explicit path), §5 (trim-on-load).
- technical-baseline.md decisions #2, #10 → §2 (opaque string passthrough),
  §7 (git-ignored local YAML + committed example).
