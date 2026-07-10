# Tasks: Connection String Translation

## Review workload forecast

```text
Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Medium
```

Estimated changed lines: ~480-650 total across 9 new/changed files. Delivery
strategy for this change is `exception-ok` (given), so the size exception is
already pre-approved and no additional gate decision is needed before
`sdd-apply`. No single file is expected to exceed ~300 lines. Breakdown:

- `src/schema_comparator/config/connection_string.py` (new): ~120-160 lines
  (tokenizer, mapping tables, `translate()`)
- `src/schema_comparator/config/errors.py`: +15-25 lines (one new factory)
- `src/schema_comparator/config/loader.py`: +3-6 lines (one call site + import)
- `src/schema_comparator/config/models.py`: ~10-15 lines changed
  (docstring only, no field/shape change)
- `docs/architecture/technical-baseline.md`: ~10-20 lines changed
  (decision #2 row revision only, no new ADR file)
- `tests/unit/config/test_connection_string.py` (new): ~220-300 lines
  (largest new file; covers tokenizer + full mapping table + backward-compat
  regression suite)
- `tests/unit/config/test_errors.py`: +20-30 lines
- `tests/unit/config/test_loader.py`: +40-60 lines (new "Phase 7" section
  for the load-time integration point)
- `tests/unit/config/test_models.py`: +10-15 lines (docstring assertion)

Delivery strategy: single change, single PR (or direct-to-main per the
project's pre-approved `exception-ok` delivery strategy for this change).
No stacking/chaining needed. Risk is rated Medium (not Low) only because the
total diff approaches the 400-line guard threshold in aggregate, even though
every individual file stays well under it and the exception is already on
record — flagged for reviewer awareness, not as a blocker.

Suggested split (only relevant if a reviewer later asks for smaller diffs):
1. `errors.py` + `test_errors.py` (pure, no dependencies)
2. `connection_string.py` + `test_connection_string.py` (tokenizer, mapping,
   backward-compat suite — the bulk of the change)
3. `loader.py` + `test_loader.py` integration + `models.py` docstring +
   `test_models.py` docstring assertion
4. `docs/architecture/technical-baseline.md` decision #2 revision

Work units: 9 phases, ~24 discrete tasks, each completable within one
session.

---

## Notes on TDD ordering

Every functional phase below follows strict red-green-refactor: a task
tagged (RED) writes a failing test against not-yet-implemented behavior,
run with `pytest` to confirm the failure, then the paired (GREEN) task
implements the minimum code to pass it, followed by a task that runs the
relevant test file(s) to confirm green. This matches
`stack-python-testing` conventions and the design's own "write each test
against a not-yet-implemented `translate`, watch it fail, then implement"
guidance in `design.md` §4.

## Phase 1 — Error case (`config/errors.py`)

- [x] 1.1 (RED) Extend `tests/unit/config/test_errors.py`: assert
      `ProfileValidationError.unrecognized_connection_string_format(name)`
      returns a `ProfileValidationError` instance whose message contains
      the given `name` but does not contain any sentinel connection-string
      substring (e.g. assert a message built with `name="x"` never embeds
      a `raw`/token/value the test never even passes to the factory —
      confirm the factory's signature accepts only `name`).
- [x] 1.2 (GREEN) Add `unrecognized_connection_string_format(cls, name: str)`
      classmethod to `ProfileValidationError` in
      `src/schema_comparator/config/errors.py`, per `design.md` §2: no
      `raw`/token/value parameter, name-only message, actionable text
      referencing `config.example.yaml`.
- [x] 1.3 Run `pytest tests/unit/config/test_errors.py` and confirm all pass.

## Phase 2 — Tokenizer (`config/connection_string.py`, brace-aware split)

- [x] 2.1 (RED) Create `tests/unit/config/test_connection_string.py` and
      write tokenizer-level tests against the not-yet-created module:
      - a plain `;`-delimited string with no braces splits into the
        expected key=value segments, trailing/empty segments (from a
        trailing `;` or `;;`) dropped.
      - `Driver={ODBC Driver 18 for SQL Server};Server=srv;` keeps the
        brace-grouped value intact as one token (the `;`-free driver name
        case).
      - a braced value containing a literal `;` (e.g.
        `PWD={p;w=d};Server=srv;`) is not split on the internal `;`.
      - a doubled `}}` inside a brace group is treated as one literal `}`
        (e.g. `Driver={Foo}}Bar};` yields a value containing `Foo}Bar`).
      - an unterminated `{` (string ends with an open brace) raises
        `ProfileValidationError.unrecognized_connection_string_format`.
- [x] 2.2 (GREEN) Create `src/schema_comparator/config/connection_string.py`
      and implement `_tokenize(raw, *, name)` and `_split_token(token)` per
      `design.md` §1.2-1.3 (single-pass scanner, brace depth 0/1, `}}`
      lookahead, first-`=`-only `partition` split). No mapping table or
      `translate()` public function yet.
- [x] 2.3 Run `pytest tests/unit/config/test_connection_string.py` and
      confirm the Phase 2 tokenizer tests pass.

## Phase 3 — Keyword mapping, Integrated Security, and duplicate precedence

- [x] 3.1 (RED) Extend `test_connection_string.py` with tests against a new
      public `translate(raw, *, name)` (not yet implemented):
      - `test_pure_ado_net_string_is_fully_translated` — full `Data
        Source`/`Initial Catalog`/`User Id`/`Password` rename, per
        `design.md` §4.2.
      - ODBC passthrough keywords (`Server`, `Database`, `Trusted_Connection`,
        `Encrypt`, `TrustServerCertificate`) are recognized and left
        unchanged (value and original casing preserved).
      - `Integrated Security=True`/`sspi`/`yes` (any casing) maps to
        `Trusted_Connection=yes`.
      - `Integrated Security=False`/`No` (any casing) is dropped entirely,
        with no `Trusted_Connection` token added.
      - an unrecognized keyword (e.g. `AppName=foo;` alongside at least one
        recognized keyword) passes through verbatim and does not itself
        raise.
      - `test_duplicate_data_source_and_server_last_occurrence_wins` and
        `test_duplicate_password_and_pwd_last_occurrence_wins`, per
        `design.md` §4.2.
      - a string with zero recognized tokens (e.g. a single opaque value
        with no `=`, or only unknown keywords) raises
        `ProfileValidationError.unrecognized_connection_string_format`.
- [x] 3.2 (GREEN) Implement `_RENAME_MAP`, `_ODBC_PASSTHROUGH_KEYS`,
      `_INTEGRATED_SECURITY_KEY`/`_TRUE_VALUES`/`_FALSE_VALUES`, and the
      core `translate()` loop per `design.md` §1.4-1.5: case-folded lookup,
      `recognized_any` tracking (renamed/passthrough/Integrated-Security
      keys only, never fail-open unknown keys), and the `pop`-then-set
      write pattern on the `output` dict so last-occurrence-wins holds
      regardless of dict-reassignment ordering nuances. No driver
      auto-prepend logic yet (raw joined result only).
- [x] 3.3 Run `pytest tests/unit/config/test_connection_string.py` and
      confirm the Phase 3 tests pass.

## Phase 4 — Driver auto-prepend and idempotency

- [x] 4.1 (RED) Extend `test_connection_string.py`:
      - `test_driver_auto_prepended_when_absent` — a no-`Driver=` ADO.NET
        string yields exactly one `Driver={ODBC Driver 18 for SQL Server};`
        token, prepended first.
      - `test_driver_auto_prepend_suppressed_case_insensitively` —
        parametrized over `driver=`/`DRIVER=`/`Driver=` casings mixed with
        ADO.NET keywords, asserting exactly one `Driver=`-prefixed token
        (case-insensitive count) survives, with no duplicate added.
      - idempotency: translating an already-translated string a second
        time is a no-op (`translate(translate(raw, name="x"), name="x") ==
        translate(raw, name="x")`).
- [x] 4.2 (GREEN) Implement the unconditional string-concatenation
      driver-prepend step at the end of `translate()` per `design.md`
      §1.5 (`has_driver` flag set during the mapping loop; trailing `;`
      ensured before prepending `_DEFAULT_DRIVER_TOKEN`).
- [x] 4.3 Run `pytest tests/unit/config/test_connection_string.py` and
      confirm the Phase 4 tests pass.

## Phase 5 — Backward-compatibility byte-identical regression suite

- [x] 5.1 (RED) Add the parametrized
      `test_pure_odbc_string_is_byte_identical_after_translation` test to
      `test_connection_string.py`, covering the six named fixtures from
      `design.md` §4.1: `config.example.yaml`'s `example-sql-auth` and
      `example-windows-auth`, `config.local.yaml`'s `salud`, and the
      archived `connection-profile-config` spec's `poliza-service`,
      `siniestro-service`, and `only-service` (minimal/non-standard
      `Driver=X` token) strings. Also add
      `test_mixed_autos_shaped_string_translates_correctly` using the real
      `autos`-profile-shaped fixture from `config.local.yaml`, asserting
      the original `Driver=` token survives untouched, all four renamed
      keywords appear with unchanged values, `Integrated Security` does not
      appear anywhere in the output, and `Encrypt=True;TrustServerCertificate=True`
      survive unchanged.
- [x] 5.2 (GREEN) Fix any translate()/tokenizer edge case surfaced by the
      regression fixtures (expected to already pass given Phases 2-4; this
      task is the verification/adjustment step, not new feature work).
- [x] 5.3 Run `pytest tests/unit/config/test_connection_string.py` in full
      and confirm all tests (Phases 2-5) pass together.

## Phase 6 — Loader integration (`config/loader.py`)

- [x] 6.1 (RED) Add a new "Phase 7" section to
      `tests/unit/config/test_loader.py` (continuing that file's existing
      phase-numbered convention):
      - loading a profile whose YAML connection-string value is an ADO.NET
        string results in an already-ODBC `ConnectionProfile.connection_string`
        (integration-level check that `load_profiles` actually calls the
        translator).
      - loading a profile with an unrecognized/malformed connection string
        raises `ProfileValidationError` from `load_profiles` itself (not
        just from the translator in isolation).
      - the existing secret-leakage guardrail parametrization (per the
        archived `connection-profile-config` change's Phase 6 pattern) is
        extended to cover the new unrecognized-format failure mode: a
        config containing sentinel secrets alongside an unrecognized
        connection string never leaks the sentinel into `str(exc)`.
- [x] 6.2 (GREEN) In `src/schema_comparator/config/loader.py`, add
      `from schema_comparator.config.connection_string import translate`
      and the single new call `connection_string = translate(connection_string,
      name=name)` inside `load_profiles`'s per-entry loop, after the
      existing blank-connection-string check and before `ConnectionProfile(...)`
      construction, per `design.md` §3. No other change to `loader.py`.
- [x] 6.3 Run `pytest tests/unit/config/test_loader.py` and confirm all
      pass (existing Phases 0-6 plus new Phase 7).

## Phase 7 — Model docstring revision (`config/models.py`)

- [x] 7.1 (RED) Extend `tests/unit/config/test_models.py`: assert
      `ConnectionProfile.__doc__` (or the module docstring, whichever the
      revision targets) no longer contains the phrase "NEVER parsed into"
      and instead references load-time ADO.NET-to-ODBC translation.
- [x] 7.2 (GREEN) Update the `ConnectionProfile` docstring in
      `src/schema_comparator/config/models.py` per `proposal.md`'s
      "Contract and documentation revisions" section: state that ADO.NET
      input is translated once, at config-load time, into ODBC form, and
      that the tool still never decomposes the string into separate
      host/user/password/auth fields. No field, `__init__`, or `__repr__`
      change.
- [x] 7.3 Run `pytest tests/unit/config/test_models.py` and confirm all
      pass.

## Phase 8 — Documentation: technical baseline decision #2 revision

- [x] 8.1 Update `docs/architecture/technical-baseline.md` decision #2:
      mark the prior "fully opaque, pass-through" description as
      superseded with a brief note, recording that ADO.NET/`SqlClient`
      connection-string fragments are now accepted as valid profile input
      and translated to ODBC form at load time, and narrowing the
      "does not parse/reconstruct auth mode" clause to "does not change
      auth *mode*, only keyword *spelling*". No new ADR file is created —
      per the design's risk note, updating this baseline decision entry is
      sufficient documentation for this change.

## Phase 9 — Cross-cutting secret-safety guardrail

- [x] 9.1 (RED) Add a dedicated test in `test_connection_string.py`
      asserting that for both failure triggers (zero recognized tokens;
      unterminated `{`), the raised exception's message contains only the
      profile `name` and no substring of the offending connection string
      (including realistic `UID=`/`PWD=`-shaped fragments embedded in
      otherwise-unrecognized keywords), and that inspecting the full
      exception (including any `__cause__`/`__context__` chain) never
      surfaces connection-string content — i.e. `translate()`/`_tokenize()`
      never `raise ... from` a lower-level exception whose own args embed
      the raw string.
- [x] 9.2 (GREEN) Confirm (or adjust) that `_tokenize()` and `translate()`
      raise `ProfileValidationError.unrecognized_connection_string_format(name)`
      directly, with no intermediate `raise ... from exc` wrapping a
      lower-level parser exception, per `design.md` §2.
- [x] 9.3 Run `pytest tests/unit/config/test_connection_string.py` in full
      one final time and confirm all tests across every phase pass
      together.
