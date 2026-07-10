# Apply Progress: Reporting and Output

Status: complete (all 8 phases implemented and verified)

## Phase 1 — Dependencies

- 1.1: Added `Jinja2>=3.1` and `xhtml2pdf>=0.2.13` to `[project].dependencies`
  in `pyproject.toml`.
- 1.2: Ran `pip install -e .`; confirmed `python -c "import jinja2, xhtml2pdf"`
  succeeds with no import error.

## Phase 2 — HTML Rendering

- 2.1/2.2 (RED): Added `tests/unit/report/conftest.py` (plain factory
  functions `comparison_result_with_findings()` /
  `comparison_result_empty()`, matching the existing project convention of
  plain helper functions rather than `@pytest.fixture` — see Deviations)
  and `tests/unit/report/test_html.py` with the 6 `build_context` tests.
  Confirmed RED: `ModuleNotFoundError: No module named
  'schema_comparator.report.html'`.
- 2.3 (GREEN): Implemented `_format_attributes`, `_row_for_entry`,
  `build_context` in `src/schema_comparator/report/html.py`. 6/6 passed.
- 2.4/2.5 (RED then GREEN): Added the 4 `render_html` golden-substring
  tests plus `tests/unit/report/golden/{with_findings_expected_substrings,
  empty_expected_substrings}.txt`; created
  `src/schema_comparator/report/templates/report.html.jinja` and a vendored
  `pico.min.css` (see Deviations), and `render_html()`. 10/10 passed.

## Phase 3 — PDF Export

- 3.1 (RED): Added `tests/unit/report/test_pdf.py` (3 mocked-`pisa`
  tests). Confirmed RED:
  `ModuleNotFoundError: No module named 'schema_comparator.report.errors'`.
- 3.2 (GREEN): Implemented `PdfExportError` in
  `src/schema_comparator/report/errors.py` and `export_pdf` in
  `src/schema_comparator/report/pdf.py`. 3/3 passed.
- 3.3 (RED): Added `tests/integration/test_pdf_export.py` (real,
  un-mocked `export_pdf(render_html(result))`). First run failed with
  `CSSParseError` — see Deviations (CSS simplification).
- 3.4 (GREEN): Removed the quoted `"Segoe UI"` font-family entry (its
  HTML-entity-encoded quotes broke xhtml2pdf's CSS parser) and marked
  the inlined CSS as `| safe` in the Jinja template so it is not
  HTML-escaped. Spike-test now passes and is kept as a permanent
  regression guard.

## Phase 4 — Console Summary

- 4.1 (RED): Added `tests/unit/report/test_console.py` (4 tests).
  Confirmed RED: `ModuleNotFoundError: No module named
  'schema_comparator.report.console'`.
- 4.2 (GREEN): Implemented `render_console` in
  `src/schema_comparator/report/console.py`. 4/4 passed.

## Phase 5 — Orchestration (timestamped naming, failure isolation)

- 5.1-5.4 (RED then GREEN): Added `tests/unit/report/test_write.py` (6
  tests covering per-format failure isolation, never-raises, and shared
  timestamp/cwd). Confirmed RED:
  `ModuleNotFoundError: No module named 'schema_comparator.report.write'`.
  Implemented `write_reports` in `src/schema_comparator/report/write.py`
  exactly per design (single shared timestamp, three independent
  try/except blocks). 6/6 passed on first implementation — no gap found
  in 5.3/5.4.
- 5.5/5.6 (RED then GREEN): Added
  `tests/integration/test_write_reports.py` (real `write_reports`,
  `render_html`, `export_pdf`). First run failed: the file written to
  disk did not byte-match a fresh `render_html()` call — root cause and
  fix documented in Deviations (CRLF line-ending round-trip). After
  normalizing the vendored CSS and Jinja template to LF line endings,
  the test passed.

## Phase 6 — Public API Export

- 6.1: Updated `src/schema_comparator/report/__init__.py` to re-export
  `render_html`, `export_pdf`, `render_console`, `PdfExportError`,
  `write_reports` with a matching `__all__`.

## Phase 7 — CLI Wiring

- 7.1 (RED): Added `tests/unit/test_cli.py` (2 tests, mocking
  `load_profiles`/`extract_schema`/`compare_snapshots`/`write_reports`).
  Confirmed RED: `AttributeError: <module 'schema_comparator.cli'>
  does not have the attribute 'load_profiles'`.
- 7.2 (GREEN): Replaced the placeholder `main()` in
  `src/schema_comparator/cli.py` with `build_arg_parser()`
  (`--config` required, `--profiles` optional `nargs="+"`) and a
  `main(argv)` wiring `load_profiles` -> (optional filter) ->
  `extract_schema` (see Deviations — function name) ->
  `compare_snapshots` -> `write_reports(result)`. 2/2 passed.

## Phase 8 — Verification

- 8.1: `pytest tests/unit/report tests/integration/test_pdf_export.py
  tests/integration/test_write_reports.py tests/unit/test_cli.py
  --cov=schema_comparator.report --cov=schema_comparator.cli
  --cov-report=term-missing` → **27 passed**, coverage 98% overall
  (`report/__init__.py`, `console.py`, `errors.py`, `pdf.py`, `write.py`
  at 100%; `html.py` 95%; `cli.py` 95%, missing line is the
  `if __name__ == "__main__":` guard). Every REQ-001 through REQ-007
  scenario has a passing test; no live DB access in any unit test.
- 8.2: Extended `tests/unit/test_import_smoke.py` with
  `test_import_schema_comparator_report` → **2 passed**.
- 8.3: `git status`/`git diff --stat` confirms
  `src/schema_comparator/compare/**` and `src/schema_comparator/tui/**`
  show no changes introduced by this apply run (pre-existing unstaged
  changes to `compare/` from the prior `comparison-engine` session were
  already present before this run started and were left untouched).
- 8.4: Full suite: `pytest` → **136 passed, 1 skipped** (the skipped test
  is the pre-existing live-DB integration test, gated on
  `SCHEMA_COMPARATOR_TEST_DSN`, unrelated to this change).

## Final test run evidence

```
pytest -q
136 passed, 1 skipped in 1.13s
```

## Deviations from design

1. **`extract_schema` instead of `discover_schema`.** The design's §6.2
   `cli.py` snippet imports `discover_schema` from
   `discovery.service`, but that module's actual function (already
   implemented by the `schema-extraction` change) is named
   `extract_schema`. `cli.py` and `tests/unit/test_cli.py` use the real,
   existing function name; no new function was added to `discovery/`
   (which remains untouched, per the Non-Goals scope boundary).
2. **`conftest.py` uses plain factory functions, not `@pytest.fixture`.**
   The design's task list calls these "fixtures," but every existing
   `conftest.py` in this codebase (`tests/unit/compare/conftest.py`,
   `tests/unit/discovery/conftest.py`) uses plain importable functions,
   not pytest fixtures. `tests/unit/report/conftest.py` follows that
   established convention for consistency.
3. **Vendored `pico.min.css` is a small self-authored stylesheet, not the
   actual third-party Pico.css library.** Fetching and vendoring real
   third-party source was avoided; the file (same name/location per the
   design's module layout) provides an equivalent "readable, unstyled
   body" baseline with the same background-color/border/basic-font-only
   constraints the design already calls for, and does not change any
   test assertion or requirement.
4. **CSS overlay simplified per Phase 3 spike-test findings.** The
   `font-family` stack's quoted `"Segoe UI"` entry was removed (its
   HTML-entity-encoded quotes broke xhtml2pdf's CSS parser with
   `CSSParseError: Declaration group closing '}' not found`), and the
   inlined CSS block is rendered with Jinja2's `| safe` filter so it is
   not HTML-escaped. This matches the design's own risk mitigation
   ("background-color/border/basic-font only").
5. **Vendored CSS and Jinja template normalized to LF line endings.**
   Both files were initially created with CRLF line endings. Because
   `write_reports` writes `html_str` via `open(path, "w",
   encoding="utf-8")` (Windows text-mode newline translation) and the
   integration test then re-reads the file via `Path.read_text()`
   (also text-mode, universal-newline translation), a `\r\n` already
   present in the rendered string became `\r\r\n` on write and was
   read back as two line breaks — producing extra blank lines and
   failing the byte-for-byte content-match assertion in
   `tests/integration/test_write_reports.py`. Normalizing both source
   files to LF-only eliminates the round-trip artifact; `write_reports`
   itself was not changed.
6. **Added `pytest-cov>=5.0` to `[project.optional-dependencies].dev`.**
   Not listed in the design's dependency section, but required to run
   the `--cov` command specified for Phase 8.1 verification; it is a
   test-tooling-only addition with no production code impact.
