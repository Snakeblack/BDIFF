# Design: Connection String Translation

Status: DRAFT — inputs are `proposal.md` and
`specs/connection-profile-config/spec.md` (2 ADDED requirements, 1 MODIFIED
requirement, 13 scenarios, including the clarify-round addition forbidding
secret-leaking exception chaining). This design is the single source of
truth for `sdd-tasks`/`sdd-apply`; no decision here should require
re-reading the proposal to reconstruct.

## 1. Module: `src/schema_comparator/config/connection_string.py`

### 1.1 Public surface

```python
def translate(raw: str, *, name: str) -> str:
    """Translate an ADO.NET/ODBC-mixed connection string into pure ODBC form.

    `name` is the owning profile's name, used only to build a secret-safe
    error message if `raw` cannot be tokenized. Never logged, never
    included in any exception's message body beyond the name itself.
    """
```

`name` is a required keyword-only argument so call sites can never
accidentally pass the connection string as the error-context argument
(defense against the exact secret-leak risk the spec calls out).

Raises `ProfileValidationError.unrecognized_connection_string_format(name)`
for both failure modes (zero recognized tokens; unterminated `{`). No other
exception type escapes `translate`.

### 1.2 Tokenizer — brace-aware `;` split

Hand-written single-pass scanner (no `csv`/`shlex`/regex-split module reuse
— none of them natively model ODBC's `{...}` grouping with `}}`-escaping,
and reimplementing their edge cases on top would be less auditable than a
direct scanner). Algorithm, operating on the trimmed `raw` string:

```python
def _tokenize(raw: str, *, name: str) -> list[str]:
    """Split `raw` on ';' into raw 'key=value' segments, respecting {...}
    brace grouping. Returns segments with surrounding whitespace stripped;
    empty segments (from a trailing ';' or ';;') are dropped.
    """
    segments: list[str] = []
    buf: list[str] = []
    depth = 0  # 0 = outside braces, 1 = inside a single non-nested brace group
    i = 0
    length = len(raw)
    while i < length:
        ch = raw[i]
        if ch == "{" and depth == 0:
            depth = 1
            buf.append(ch)
        elif ch == "}" and depth == 1:
            # Doubled '}}' inside a brace group is a literal '}'; only a
            # single '}' followed by a non-'}' (or end of string) closes
            # the group.
            if i + 1 < length and raw[i + 1] == "}":
                buf.append("}")
                i += 1  # consume both characters of the doubled pair
            else:
                depth = 0
                buf.append(ch)
        elif ch == ";" and depth == 0:
            segments.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
        i += 1

    if depth != 0:
        # Unterminated '{': hard error, no partial/best-effort parse.
        raise ProfileValidationError.unrecognized_connection_string_format(name)

    segments.append("".join(buf))
    return [s.strip() for s in segments if s.strip()]
```

Key points a reviewer must be able to verify from this design alone:

- Brace depth only ever tracks 0 or 1 — ODBC/`SqlClient` braces are not
  nestable, so a second unescaped `{` while `depth == 1` is not itself an
  error condition per the spec (not mentioned as a rejected case); it is
  just a literal `{` character absorbed into the buffered value. Only an
  *unterminated* `{` (string ends with `depth == 1`) is rejected.
  Documented as a limitation in the module docstring: nested/nonstandard
  brace content is passed through literally, matching real ODBC driver
  manager behavior.
  and no new escaping scheme is invented (per the proposal's explicit
  non-goal).
- A `;` inside a brace group (`depth == 1`) never splits — this is the
  mechanism that keeps `Driver={ODBC Driver 18 for SQL Server}` intact
  even though the driver name itself contains no `;`, and is exactly the
  mechanism a hypothetical `Driver={SQL Server; some vendor suffix}` would
  need.
- `}}` doubling is checked by lookahead before deciding whether a `}`
  closes the group, consuming both characters of the pair without
  emitting a `depth`-toggle for the second one.

### 1.3 Key/value split per token

```python
def _split_token(token: str) -> tuple[str, str] | None:
    """Split one 'key=value' segment on the first '=' only. Returns None
    if the token has no '=' at all (unrecognized-format signal upstream).
    """
    if "=" not in token:
        return None
    key, _, value = token.partition("=")
    return key.strip(), value.strip()
```

Splitting on the *first* `=` only (via `partition`, not `split`) matters:
a value like `PWD={p@ss=word}` is already protected by braces (handled by
the tokenizer above, so no bare `=` reaches this function inside a braced
value), but this is still the correct generic rule for any unbraced value
that happens to contain `=` — ODBC/`SqlClient` both treat the first `=` as
the separator.

### 1.4 Keyword-mapping table (verbatim from spec, as code)

```python
# Case-folded ADO.NET/legacy keyword -> canonical ODBC keyword. Keys already
# in ODBC form (Server, Database, UID, PWD, Trusted_Connection, Driver,
# Encrypt, TrustServerCertificate, ...) are intentionally absent: absence
# means "pass through unchanged", which is the fail-open default for any
# keyword not in this dict (including genuinely unknown/driver-specific
# ones).
_RENAME_MAP: dict[str, str] = {
    "data source": "Server",
    "initial catalog": "Database",
    "user id": "UID",
    "uid": "UID",
    "password": "PWD",
    "pwd": "PWD",
}

# Keys recognized as already-valid ODBC keywords (pass through unchanged,
# but still count as "recognized" for the zero-recognized-tokens error
# check).
_ODBC_PASSTHROUGH_KEYS = {
    "server",
    "database",
    "trusted_connection",
    "encrypt",
    "trustservercertificate",
    "driver",
}

_INTEGRATED_SECURITY_KEY = "integrated security"
_INTEGRATED_SECURITY_TRUE_VALUES = {"true", "sspi", "yes"}
_INTEGRATED_SECURITY_FALSE_VALUES = {"false", "no"}

_DEFAULT_DRIVER_TOKEN = "Driver={ODBC Driver 18 for SQL Server}"
```

`_RENAME_MAP` only ever contains ADO.NET-only spellings, by construction —
this is *why* the byte-identical backward-compatibility guarantee holds:
a pure-ODBC string tokenizes into keys that are all either in
`_ODBC_PASSTHROUGH_KEYS`/`_INTEGRATED_SECURITY_KEY` (no-op branches) or in
neither map (fail-open pass-through branch), so no branch in `translate`
ever rewrites an already-ODBC token.

### 1.5 `translate()` algorithm

```python
def translate(raw: str, *, name: str) -> str:
    tokens = _tokenize(raw, name=name)

    recognized_any = False
    has_driver = False
    # dict preserves insertion order; re-inserting an existing key moves it
    # to the end, which is exactly last-occurrence-wins semantics.
    output: dict[str, str] = {}

    for token in tokens:
        split = _split_token(token)
        if split is None:
            # A token with no '=' at all is not itself a hard error unless
            # it is the *only* thing in the string (see recognized_any
            # check below) — but per spec, an unrecognized keyword still
            # "passes through unchanged" only when it plausibly is a
            # key=value pair. A bare no-'=' segment cannot be represented
            # in the output dict's key=value shape, so it is folded into
            # the zero-recognized-token check: it never sets
            # recognized_any, and if it is the *only* token, translate()
            # falls through to the unrecognized-format error below.
            continue

        key, value = split
        folded_key = key.casefold()

        if folded_key in _RENAME_MAP:
            output[_RENAME_MAP[folded_key]] = value
            recognized_any = True
        elif folded_key in _ODBC_PASSTHROUGH_KEYS:
            output[key] = value  # preserve original casing for passthrough
            recognized_any = True
            if folded_key == "driver":
                has_driver = True
        elif folded_key == _INTEGRATED_SECURITY_KEY:
            recognized_any = True
            folded_value = value.casefold()
            if folded_value in _INTEGRATED_SECURITY_TRUE_VALUES:
                output["Trusted_Connection"] = "yes"
            elif folded_value in _INTEGRATED_SECURITY_FALSE_VALUES:
                output.pop("Trusted_Connection", None)  # dropped, no-op if absent
            # any other value: spec defines only true/sspi/yes and
            # false/no; an unrecognized value is treated as an unknown
            # keyword+value pair and preserved verbatim under its
            # original key, matching the fail-open default elsewhere.
            else:
                output[key] = value
        else:
            # Fail-open: unknown keyword, preserved verbatim under its
            # original (non-case-folded) key. Does NOT count toward
            # recognized_any — an all-unknown-keyword string with zero
            # ODBC/ADO.NET keywords must still be rejected per spec.
            output[key] = value

    if not recognized_any:
        raise ProfileValidationError.unrecognized_connection_string_format(name)

    result = ";".join(f"{k}={v}" for k, v in output.items())
    if result and not result.endswith(";"):
        result += ";"

    if not has_driver:
        result = f"{_DEFAULT_DRIVER_TOKEN};{result}"

    return result
```

Design notes / rationale for reviewers:

- **Last-occurrence-wins via `dict` re-insertion.** Python's `dict`
  preserves original insertion order for a key's *first* insertion, but
  reassigning an existing key's value does not move it in iteration
  order in CPython — this is a real correctness risk. To make
  last-occurrence-wins unambiguous regardless of dict-reassignment
  ordering nuances, `output` MUST use the delete-then-reinsert pattern
  when a key is overwritten, so the key's position always reflects the
  order of its own last write. Concretely: `output.pop(key, None)`
  before `output[key] = value` on every write path above. (Shown as
  plain assignment above for readability; the actual implementation task
  must include this `pop`-then-set pair.) This is exactly the same
  technique already used above for the `Integrated Security=False` drop
  case, generalized to every write.
- **`recognized_any` counts renamed, passthrough, and
  `Integrated Security` keys — never fail-open unknown keys.** This is
  the precise mechanism implementing "reject only if *zero* tokens are
  recognized as either an ODBC keyword or a mapped ADO.NET keyword":
  an unknown-only string (e.g. a single `Foo=Bar;`) is NOT itself
  sufficient to pass; it must contain at least one keyword from the
  mapping/passthrough/integrated-security sets.
- **Driver auto-prepend is unconditional string concatenation, not a
  dict entry**, because prepending must produce
  `Driver={...};<rest of tokens>` with the driver token literally first
  and untouched, matching the exact fixture strings in the spec
  (`config.example.yaml`, proposal examples). Building it as a dict entry
  risks LLM-obvious but subtly wrong reordering if a future edit changes
  dict iteration assumptions.
- **Serialization ordering matches ODBC/`SqlClient` "last wins, but the
  surviving token stays roughly where the winning occurrence was
  written" convention** by relying on dict insertion-order semantics
  after the pop-then-set pattern above. This is a reasonable, testable,
  documented convention (spec does not mandate exact output token
  *order*, only exact output token *values* per scenario) — the
  byte-identical regression tests below therefore assert on full-string
  equality only for pure-ODBC (already-in-final-order) inputs, and on
  keyword/value substring presence + absence for translated/mixed inputs
  where order is not spec-normative.
- **A trailing `;` is always ensured** before Driver-prepend concatenation
  so `Driver={...};` + rest never collapses into `...}rest` without a
  separator, and the final output always parses back through the same
  tokenizer idempotently (translating an already-translated string is a
  no-op — worth one dedicated test, see §4).

## 2. Error type: `config/errors.py`

Add one factory to the existing `ProfileValidationError` class, following
the exact same secret-safety and docstring discipline as the other four
factories already in that file (name-only, no `raw`/token/value parameter
exists so there is nothing to accidentally interpolate):

```python
    @classmethod
    def unrecognized_connection_string_format(cls, name: str) -> "ProfileValidationError":
        return cls(
            f"Connection profile '{name}' has a connection string in an "
            "unrecognized or malformed format (no recognized ODBC/ADO.NET "
            "keyword found, or an unterminated '{' brace group). Check the "
            "profile's connection string against config.example.yaml for "
            "the expected format."
        )
```

No `raw`/`token`/`value` parameter is added to this factory's signature at
all — this is the enforcement mechanism for the clarify-round's exception-
chaining requirement: since `translate()`/`_tokenize()` never construct
this exception with anything but `name`, and never `raise ... from` a
lower-level exception (there is no lower-level parser exception in this
design — `_tokenize` raises `ProfileValidationError` directly, not a
generic `ValueError` that then gets re-wrapped), there is no traceback path
through which connection-string content can leak, matching the
`yaml.YAMLError`-avoidance precedent already in `loader.py`.

## 3. Integration point: `config/loader.py`

Exactly one new call, inside the existing per-entry loop in
`load_profiles`, after the existing blank-connection-string check and
before `ConnectionProfile(...)` is constructed:

```python
        if not connection_string:
            raise ProfileValidationError.empty_connection_string(name)

        connection_string = translate(connection_string, name=name)

        profiles.append(ConnectionProfile(name=name, connection_string=connection_string))
```

One new import: `from schema_comparator.config.connection_string import
translate`. No other change to `loader.py` — the trim/blank/duplicate-name
checks all continue to run on the *raw* (pre-translation) string exactly
as today, since those checks are about the YAML entry's shape, not its
ODBC-vs-ADO.NET content.

`config/models.py` changes only its module/class docstring (per proposal
§"Contract and documentation revisions") — no field, no `__init__`, no
`__repr__` change. The redaction in `__repr__` remains correct unchanged
since it never touches `connection_string`'s content either way.

## 4. Testing strategy (TDD, red-green-refactor per `stack-python-testing`)

New test module: `tests/unit/config/test_connection_string.py`, mirroring
the existing per-topic-file convention in `tests/unit/config/`. Additions
to the existing `tests/unit/config/test_loader.py` for the integration
point only (not a new file, since it extends the existing loader
integration suite, matching that file's own phase-based docstring
convention — this becomes its "Phase 7" section).

### 4.1 Byte-identical regression fixture set (pure ODBC, finite, named now)

Concrete list — drawn from the proposal's own enumeration, `config.example.yaml`,
`config.local.yaml`, and the archived `connection-profile-config` spec
examples already read during this design:

1. `"Driver={ODBC Driver 18 for SQL Server};Server=your-server;Database=YourDb;UID=your-user;PWD=your-password;TrustServerCertificate=yes;"` (`config.example.yaml` → `example-sql-auth`)
2. `"Driver={ODBC Driver 18 for SQL Server};Server=your-server;Database=YourOtherDb;Trusted_Connection=yes;"` (`config.example.yaml` → `example-windows-auth`)
3. `"Driver={ODBC Driver 18 for SQL Server};Server=your-server;Database=YourOtherDb;Trusted_Connection=yes;"` (`config.local.yaml` → `salud`, same shape as #2)
4. `"Driver={ODBC Driver 18 for SQL Server};Server=srv1;Database=PolizaDB;UID=u;PWD=p;"` (archived `connection-profile-config` spec / `test_loader.py` → `poliza-service`)
5. `"Driver={ODBC Driver 18 for SQL Server};Server=srv2;Database=SiniestroDB;Trusted_Connection=yes;"` (archived spec / `test_loader.py` → `siniestro-service`)
6. `"Driver=X;Server=srv;Database=Db;UID=u;PWD=p;"` (`test_loader.py` → `only-service`, minimal/non-standard driver token — exercises that `translate()` doesn't require a *specific* driver string, only *a* `Driver=` token's presence)

Implemented as one parametrized test:

```python
@pytest.mark.parametrize("raw", [<the 6 strings above>])
def test_pure_odbc_string_is_byte_identical_after_translation(raw: str) -> None:
    assert translate(raw, name="x") == raw
```

This directly implements the spec's "Pure-ODBC string is byte-identical
after translation" scenario and the proposal's backward-compatibility
guarantee as one required, always-run regression test — not a
`pytest.mark.skip`/manual check.

### 4.2 New translator unit tests (`test_connection_string.py`)

Each maps 1:1 to a spec scenario, named after it (red-green-refactor: write
each test against a not-yet-implemented `translate`, watch it fail, then
implement):

- `test_pure_ado_net_string_is_fully_translated` — the spec's `Data
  Source=srv1;Initial Catalog=PolizaDB;User Id=u;Password=p;` example;
  asserts `Server=srv1`, `Database=PolizaDB`, `UID=u`, `PWD=p`, and a
  prepended `Driver={ODBC Driver 18 for SQL Server};` are all present, and
  none of `Data Source=`, `Initial Catalog=`, `User Id=`, `Password=`
  remain as substrings.
- `test_mixed_autos_shaped_string_translates_correctly` — the real
  `autos`-profile-shaped fixture verbatim from `config.local.yaml` (already
  read during this design): asserts the original `Driver=` token is
  untouched and appears exactly once, `Server=IBPFMPRU.example` /
  `Database=SegurosEcosistemaAutos` / `UID=USR_x` / `PWD=xxxxxxxxx` are
  present, `Integrated Security` does not appear anywhere in the output,
  and `Encrypt=True;TrustServerCertificate=True` survive unchanged.
- `test_duplicate_data_source_and_server_last_occurrence_wins` —
  `"Data Source=old-srv;Server=new-srv;"` → output contains `Server=new-srv`
  and does not contain `old-srv` anywhere.
- `test_duplicate_password_and_pwd_last_occurrence_wins` —
  `"Password=old-pwd;PWD=new-pwd;"` → output contains `PWD=new-pwd` and does
  not contain `old-pwd`.
- `test_driver_auto_prepended_when_absent` — no-`Driver=` ADO.NET string →
  exactly one `Driver=` substring in output, equal to the default token.
- `test_driver_auto_prepend_suppressed_case_insensitively` —
  parametrized over `driver=`, `DRIVER=`, `Driver=` casings mixed with
  ADO.NET keywords → output contains exactly one `Driver=`-prefixed token
  (case-insensitive count via `re.findall`/`.casefold()` substring count).
- `test_integrated_security_true_variants_map_to_trusted_connection` —
  parametrized over `True`, `true`, `sspi` (and casing variants) → output
  contains `Trusted_Connection=yes` and no `Integrated Security` substring.
- `test_integrated_security_false_variants_are_dropped` — parametrized
  over `False`, `no` (and casing variants), alongside `UID=`/`PWD=` →
  output contains neither `Integrated Security` nor `Trusted_Connection`.
- `test_unrecognized_keyword_passes_through_unchanged` — a string with one
  genuine ODBC/ADO.NET keyword plus one made-up keyword (e.g.
  `App=MyApp`) → the made-up token's key and value both survive verbatim.
- `test_zero_recognized_tokens_raises_unrecognized_format_error` — a single
  opaque value with no `=` at all → raises
  `ProfileValidationError`; message contains the profile name and does not
  contain the raw string.
- `test_all_unknown_keywords_only_raises_unrecognized_format_error` — a
  string that tokenizes fine (has `=` signs) but every key is unknown
  (not in `_RENAME_MAP`/`_ODBC_PASSTHROUGH_KEYS`/`Integrated Security`) →
  same error, same secret-safety assertion.
- `test_unterminated_brace_raises_unrecognized_format_error` — e.g.
  `"Driver={ODBC Driver 18 for SQL Server;Server=srv;"` (missing closing
  `}`) → same error type, no partial parse artifact leaks into the message.
- `test_error_message_never_contains_connection_string_content` — the
  single required secret-safety test covering *every* trigger above in one
  parametrized sweep: for each raising fixture, assert `raw not in
  str(exc)` and that no individual token substring of `raw` (split crudely
  on `;`/`=` for the assertion, independent of the production tokenizer)
  appears in `str(exc)`. This directly implements the clarify-round's new
  scenario.
- `test_translate_is_idempotent_on_its_own_output` — feeding
  `translate()`'s own output back into `translate()` again yields the same
  string unchanged (proves the auto-prepend/rename logic never
  double-applies), one extra regression guard beyond what the spec strictly
  requires but cheap and directly derived from the design's serialization
  approach in §1.5.
- Braced-value edge cases (from the proposal's brace-grouping guidance,
  not yet spec-scenario-numbered but required by "the design must state
  how brace-grouping is detected"):
  - `test_braced_value_containing_semicolon_is_not_split` —
    `"Driver={ODBC Driver 18 for SQL Server};PWD={p;w}=d};Server=srv;"`
    style fixture (semicolon inside braces) → `PWD=` value retained whole,
    including the literal `;`, and no extraneous split occurs. *(Exact
    literal fixture string to be finalized at `sdd-apply` time against the
    tokenizer above; documented here as a required test case, not
    optional.)*
  - `test_doubled_closing_brace_is_literal_brace_in_value` — a value
    containing `}}` inside a brace group resolves to a single literal `}`
    in the output value.

### 4.3 Loader integration tests (append to `test_loader.py`, new "Phase 7" section)

- `test_load_profiles_translates_ado_net_profile_to_odbc` — a
  `config.local.yaml`-shaped fixture using the `autos` real shape →
  resulting `ConnectionProfile.connection_string` is ODBC-form (contains
  `Server=`/`Database=`/`UID=`/`PWD=`, not `Data Source=`/`Initial
  Catalog=`).
- `test_load_profiles_leaves_pure_odbc_profile_byte_identical` — a fixture
  using one of the §4.1 pure-ODBC strings → loaded
  `connection_string == raw` (integration-level restatement of the unit
  guarantee, catching any accidental double-processing at the loader
  layer).
- `test_load_profiles_raises_unrecognized_format_for_bad_profile` — a
  fixture with a zero-recognized-token connection string → `load_profiles`
  raises `ProfileValidationError`; assert profile name is in the message,
  raw string is not.

### 4.4 Coverage target

Per `stack-python-testing`/technical-baseline's testing bar: `config/` is
not the compare/diff critical path, but connection-string translation is
the direct entry point for every profile's credentials, so this design
targets ~100% line/branch coverage of `connection_string.py` (every
mapping-table branch, both brace-close paths, both integrated-security
value sets, both error triggers) via the enumerated tests above — no
branch in §1.5 is left untested by design.

## 5. Documentation task (required, not optional)

`sdd-tasks`/`sdd-apply` MUST include a task to revise
[docs/architecture/technical-baseline.md](docs/architecture/technical-baseline.md#L12)
decision #2's row: mark it superseded/revised (not silently contradicted),
recording that ADO.NET/`SqlClient` fragments are now accepted and
translated to ODBC at load time, and narrowing the "does not
parse/reconstruct auth mode" clause to "does not change auth *mode*, only
keyword *spelling*." Exact prose is left to the `sdd-apply` phase per the
task instructions; this design only specifies that the task must exist,
must touch decision #2 specifically (not add a new row), and must not
remove the original rationale text — append/annotate, since the table's
narrative-rationale style is a project convention worth preserving for
history.

## 6. File change list (exact)

**New:**
- `src/schema_comparator/config/connection_string.py`
- `tests/unit/config/test_connection_string.py`

**Modified:**
- `src/schema_comparator/config/loader.py` — one new import, one new call
  site (§3).
- `src/schema_comparator/config/errors.py` — one new
  `ProfileValidationError` factory (§2).
- `src/schema_comparator/config/models.py` — docstring only (§3, last
  paragraph).
- `tests/unit/config/test_loader.py` — new "Phase 7" integration test
  section (§4.3).
- `docs/architecture/technical-baseline.md` — decision #2 row revision
  (§5), executed as its own `sdd-apply` task.
- `openspec/specs/connection-profile-config/spec.md` — receives this
  change's spec delta on archive (standard OpenSpec lifecycle, not a
  manual edit during design/apply).

**Not modified:** `config.example.yaml`, `config.local.yaml` (both already
contain this change's primary regression fixtures as-is, per proposal),
`connectors/__init__.py`, `discovery/**`, `tui/**` (all unaffected
consumers, per proposal's impact section).

## 7. Sequence diagram — load-time translation flow

```mermaid
sequenceDiagram
    participant Caller as cli.py / TUI (future)
    participant Loader as config.loader.load_profiles
    participant Translate as config.connection_string.translate
    participant Errors as config.errors.ProfileValidationError
    participant Model as config.models.ConnectionProfile

    Caller->>Loader: load_profiles(config_path)
    Loader->>Loader: read YAML, validate shape
    loop each databases: entry
        Loader->>Loader: trim name/connection_string
        Loader->>Loader: empty-name / duplicate-name / empty-string checks
        Loader->>Translate: translate(connection_string, name=name)
        Translate->>Translate: _tokenize (brace-aware split on ';')
        alt unterminated '{' brace
            Translate->>Errors: unrecognized_connection_string_format(name)
            Errors-->>Loader: raise ProfileValidationError
            Loader-->>Caller: propagate (no partial profile list)
        else tokenizes cleanly
            Translate->>Translate: rename / passthrough / Integrated Security /\nfail-open per token, last-occurrence wins
            alt zero recognized tokens
                Translate->>Errors: unrecognized_connection_string_format(name)
                Errors-->>Loader: raise ProfileValidationError
                Loader-->>Caller: propagate
            else at least one recognized token
                Translate->>Translate: prepend Driver= if absent
                Translate-->>Loader: ODBC-form string
                Loader->>Model: ConnectionProfile(name, odbc_string)
                Model-->>Loader: profile instance
            end
        end
    end
```
