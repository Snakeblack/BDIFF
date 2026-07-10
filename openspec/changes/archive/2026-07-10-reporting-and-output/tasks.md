# Tasks: Reporting and Output (Change B)

## Spec/Design Reconciliation

| Requirement / Scenario | Priority | Design Allocation | Status | Notes |
|------------------------|----------|-------------------|--------|-------|
| REQ-reporting-and-output-001 (self-contained HTML, grouped/ordered findings, header row lists every profile) | MUST | `report/html.py` `build_context`/`render_html`, `templates/report.html.jinja` (§3.1-§3.3) | covered-by-design | `entries` iterated via `itertools.groupby` over the already-sorted sequence — never re-sorted. |
| REQ-reporting-and-output-002 (timestamped HTML/PDF filenames, shared run timestamp, written to CWD) | MUST | `report/write.py` `write_reports` (§6.1) | covered-by-design | Single `timestamp` computed once before any of the three try/except blocks. |
| REQ-reporting-and-output-003 (PDF derived from the exact same HTML string, no second template) | MUST | `report/pdf.py` `export_pdf` (§4), `report/write.py` (§6.1) | covered-by-design | `export_pdf(html_str)` receives the same string written to the `.html` file. |
| REQ-reporting-and-output-004 (graceful degradation on unsupported CSS during PDF conversion) | MUST | `report/pdf.py` `export_pdf` normalizing both exception and `err>0` paths to `PdfExportError` (§4), `report/write.py` catch block (§6.1) | covered-by-design | Never a raw xhtml2pdf/reportlab exception escapes `export_pdf`. |
| REQ-reporting-and-output-005 (console summary independent of HTML/PDF outcome) | MUST | `report/console.py` `render_console` (§5) | covered-by-design | Pure function of `ComparisonResult` only; never receives HTML/PDF output. |
| REQ-reporting-and-output-006 (clean-comparison messaging across all three outputs) | MUST | `build_context`'s `has_findings` flag + template `{% if not has_findings %}` block (§3.1-§3.3), `render_console`'s empty-entries branch (§5) | covered-by-design | PDF inherits the message via REQ-003's shared-HTML-string derivation — no separate PDF-side check needed. |
| REQ-reporting-and-output-007 (per-format failure isolation, always attempt all three) | MUST | `report/write.py` `write_reports` — three independent `try/except Exception` blocks (§6.1), sequence diagram (§7) | covered-by-design | HTML/PDF/console failures are mutually non-blocking by construction; `write_reports` never raises. |
| Non-Goals narrowing (no diff-detection changes, no TUI shell, no `--format` flag, no theming/persistence beyond Decision 1) | MUST | N/A (scope boundary, not implemented behavior) | covered-by-design | No task touches `compare/` or `tui/`; enforced by scope, verified in Phase 8. |

### Reconciliation Verdict

- MUST coverage: complete (7/7 requirements, 20/20 scenarios traced to a design section).
- SHOULD/MAY gaps: none — the spec defines no SHOULD/MAY-level requirements.
- Ambiguities to track: none blocking `sdd-apply`. Two items are explicitly left to implementer discretion per the spec's Final Review note (compact `ColumnAttributes` string format, exact console per-table line format) — both already have a concrete illustrative implementation in design §3.1 and §5, used as the task-level source of truth below.

## Review Workload Forecast

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: High

| Field | Value |
|-------|-------|
| Estimated changed lines | ~950-1150 total: source ~350-400 (`html.py` ~110, `pdf.py` ~35, `console.py` ~55, `errors.py` ~5, `write.py` ~45, `report/__init__.py` ~15, `report.html.jinja` ~60, vendored `pico.min.css` excluded from line-risk as a third-party asset, `cli.py` ~40 net, `pyproject.toml` ~2); tests ~550-700 across 7 new test files (`tests/unit/report/`: `conftest.py`, `test_html.py`, `test_pdf.py`, `test_console.py`, `test_write.py`; `tests/integration/`: `test_pdf_export.py`, `test_write_reports.py`) plus golden HTML fixtures |
| Files touched | 9 new source/template files under `src/schema_comparator/report/` (`html.py`, `pdf.py`, `console.py`, `errors.py`, `write.py`, `__init__.py`, `templates/report.html.jinja`, `templates/pico.min.css`, package `__init__.py` already existed as placeholder), 2 modified (`cli.py`, `pyproject.toml`), 7+ new test files (unit + integration), 3+ golden fixture files — ~20 files total |
| Chained PRs recommended | No — the change is one cohesive, additive vertical slice (three renderers sharing one input contract, wired by one orchestration function); splitting HTML/PDF/console into separate PRs would leave each PR non-functional in isolation (no CLI entry point works without all three) and duplicate reviewer setup cost |
| 400-line budget risk | High — estimated total substantially exceeds the 400-line guideline, driven by the vendored Pico.css template asset, one Jinja2 template, three independent renderer modules, and their paired TDD test suites (unit + integration) all landing in the same additive, non-severable change |
| Suggested split | Single PR (size:exception) — `delivery_strategy: exception-ok` per this task's instructions; work units below are for reviewer navigation only, not separate PRs |
| Delivery strategy | exception-ok |
| Chain strategy | size-exception |

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Dependencies: `Jinja2` + `xhtml2pdf` added to `pyproject.toml`, installed (Phase 1) | PR 1 (single, size:exception) | No behavior yet; must land before any renderer code imports either package. |
| 2 | HTML rendering: `build_context` + `render_html` + Jinja2 template + vendored Pico.css (Phase 2) | PR 1 (single, size:exception) | Depends on Unit 1; REQ-001, REQ-006 (HTML side). |
| 3 | PDF export: `export_pdf` + `PdfExportError`, mocked unit tests + real integration spike-test (Phase 3) | PR 1 (single, size:exception) | Depends on Unit 1-2; REQ-003, REQ-004; the xhtml2pdf CSS-compatibility spike-test from the proposal lands here. |
| 4 | Console summary: `render_console` (Phase 4) | PR 1 (single, size:exception) | Independent of Units 2-3; REQ-005, REQ-006 (console side). |
| 5 | Orchestration: `write_reports` failure isolation + timestamped naming (Phase 5) | PR 1 (single, size:exception) | Depends on Units 2-4; REQ-002, REQ-007. |
| 6 | Public API export: `report/__init__.py` (Phase 6) | PR 1 (single, size:exception) | Depends on Units 2-5. |
| 7 | CLI wiring: `cli.py` argparse + dispatch (Phase 7) | PR 1 (single, size:exception) | Depends on Unit 6. |
| 8 | Verification: full suite run, scope-boundary check (Phase 8) | PR 1 (single, size:exception) | Depends on Units 1-7. |

### Checklist Status Legend

- `[ ]` Not implemented yet
- `[~]` Implemented but not yet verified locally
- `[x]` Implemented and verified locally

## Phase 1: Dependencies — `Jinja2` + `xhtml2pdf`

- [x] 1.1 In `pyproject.toml` `[project].dependencies`, add `"Jinja2>=3.1"` and `"xhtml2pdf>=0.2.13"` alongside the existing `PyYAML`/`pyodbc` entries, per design §9.
- [x] 1.2 Run `pip install -e .` (or the project's declared install command) to install both new dependencies into the active environment, and confirm `python -c "import jinja2, xhtml2pdf"` succeeds with no import error. (Environment setup — no paired failing-test step; a subsequent smoke test in Phase 8 covers importability under `tests/unit/test_import_smoke.py`.)

## Phase 2: HTML Rendering (REQ-reporting-and-output-001, REQ-reporting-and-output-006 HTML side)

- [x] 2.1 **(RED)** In `tests/unit/report/conftest.py`, add shared `ComparisonResult` fixtures (`comparison_result_with_findings` covering `MissingTable`, `MissingColumn`, and `ColumnMismatch` across 2 and 3 profiles; `comparison_result_empty` with an empty `entries` sequence and named `compared_profiles`), reusing `schema_comparator.compare.models` types directly, per design §8.1. (Fixture scaffolding — paired with the first failing tests in 2.2, which import and exercise it.)
- [x] 2.2 **(RED)** In `tests/unit/report/test_html.py`, write failing tests `test_build_context_missing_table_marks_profile_distinctly`, `test_build_context_missing_column_marks_profile_distinctly`, `test_build_context_column_mismatch_renders_present_profiles_and_blanks_absent`, `test_build_context_preserves_engine_entry_order_without_resorting`, `test_build_context_groups_by_qualified_table_identity`, and `test_build_context_empty_entries_sets_has_findings_false`, per design §3.1 and spec REQ-001 scenarios.
- [x] 2.3 **(GREEN)** In `src/schema_comparator/report/html.py`, implement `_format_attributes`, `_row_for_entry`, and `build_context(result)` exactly per design §3.1 (dict-shape only, no Jinja2 involved yet), to make 2.2 pass.
- [x] 2.4 **(RED)** In `tests/unit/report/test_html.py`, write failing tests `test_render_html_includes_every_diff_entry`, `test_render_html_header_row_lists_profiles_in_result_order`, `test_render_html_no_findings_shows_no_drift_message_and_no_empty_table`, and `test_render_html_is_self_contained_with_no_external_asset_links`, asserting on structural substrings against checked-in golden fixtures under `tests/unit/report/golden/*.html`, per design §3.3 and §8.1 and spec REQ-001/REQ-006 scenarios.
- [x] 2.5 **(GREEN)** Create `src/schema_comparator/report/templates/report.html.jinja` (inline Pico.css include point + diff-type overlay `<style>` block + grouped findings table + no-drift block, per design §3.3) and vendor `src/schema_comparator/report/templates/pico.min.css`; implement `render_html(result)` in `html.py` (module-level `_env`/`PackageLoader`, `pico_css_inline` constant read once at import time, `render_html` calling `build_context` and rendering the template), per design §3.1 and §3.3, to make 2.4 pass.

## Phase 3: PDF Export (REQ-reporting-and-output-003, REQ-reporting-and-output-004)

- [x] 3.1 **(RED)** In `tests/unit/report/test_pdf.py`, write failing tests `test_export_pdf_returns_bytes_unchanged_on_success` (mocked `pisa.CreatePDF`, `err=0`), `test_export_pdf_raises_pdf_export_error_when_err_greater_than_zero` (mocked, `err>0`), and `test_export_pdf_wraps_underlying_exception_as_pdf_export_error` (mocked `CreatePDF` raising), per design §4 and §8.2 and spec REQ-003/REQ-004 scenarios.
- [x] 3.2 **(GREEN)** Create `src/schema_comparator/report/errors.py` with `PdfExportError(Exception)`, and implement `export_pdf(html)` in `src/schema_comparator/report/pdf.py` exactly per design §4 (catches both raised-exception and `result.err > 0` paths, normalizing both to `PdfExportError`, never leaking a raw xhtml2pdf/reportlab exception), to make 3.1 pass.
- [x] 3.3 **(RED)** In `tests/integration/test_pdf_export.py`, write a failing integration test `test_export_pdf_produces_valid_pdf_bytes_from_rendered_html` calling the real, un-mocked `export_pdf(render_html(result))` against a small fixture `ComparisonResult` and asserting non-empty bytes starting with the `%PDF-` header, per design §8.2 and the proposal's required xhtml2pdf CSS-compatibility spike-test.
- [x] 3.4 **(GREEN)** Run the test from 3.3 against the actual overlay CSS in `templates/report.html.jinja`/`pico.min.css`; if `xhtml2pdf` fails to render any construct, simplify the offending CSS (background-color/border/basic-font only, per the proposal's Decision 4 risk mitigation) until 3.3 passes, keeping this test as a permanent regression guard afterward.

## Phase 4: Console Summary (REQ-reporting-and-output-005, REQ-reporting-and-output-006 console side)

- [x] 4.1 **(RED)** In `tests/unit/report/test_console.py`, write failing tests `test_render_console_reports_counts_by_diff_category`, `test_render_console_lists_compared_profiles_and_per_table_breakdown`, `test_render_console_no_drift_message_on_empty_entries_without_zero_counts`, and `test_render_console_is_independent_of_html_and_pdf_modules` (module-level import check: `console.py` imports neither `jinja2` nor `xhtml2pdf`), per design §5 and §8.3 and spec REQ-005/REQ-006 scenarios.
- [x] 4.2 **(GREEN)** Implement `render_console(result)` in `src/schema_comparator/report/console.py` exactly per design §5 (`_TYPE_LABELS` mapping, counts-by-category block, per-table breakdown via `itertools.groupby`, no-drift early return), to make 4.1 pass.

## Phase 5: Orchestration — Timestamped Naming and Failure Isolation (REQ-reporting-and-output-002, REQ-reporting-and-output-007)

- [x] 5.1 **(RED)** In `tests/unit/report/test_write.py`, write failing tests `test_write_reports_html_failure_still_attempts_pdf_and_console` (patch `render_html` to raise), `test_write_reports_pdf_failure_still_leaves_html_written_and_console_printed` (patch `export_pdf` to raise `PdfExportError`), `test_write_reports_console_failure_still_leaves_html_and_pdf_written` (patch `render_console` to raise), and `test_write_reports_never_raises_past_the_function_boundary`, using `tmp_path`/`monkeypatch.chdir` and `capsys`, per design §6.1 and §8.4 and spec REQ-007 scenarios.
- [x] 5.2 **(GREEN)** Implement `write_reports(result, *, out=sys.stdout)` in `src/schema_comparator/report/write.py` exactly per design §6.1 (single shared `timestamp` computed once, three independent `try/except Exception` blocks for HTML/PDF/console, `[ERROR]` prefix on failure lines, `html_str` gated PDF attempt), to make 5.1 pass.
- [x] 5.3 **(RED)** In `tests/unit/report/test_write.py`, write failing tests `test_write_reports_html_and_pdf_filenames_share_the_same_timestamp` and `test_write_reports_writes_to_the_current_working_directory` (via `tmp_path`/`monkeypatch.chdir`), per design §6.1 and spec REQ-002 scenarios.
- [x] 5.4 **(GREEN)** Confirm the existing `write_reports` implementation from 5.2 already satisfies 5.3 (shared `timestamp` variable, relative filenames written via plain `open(...)` against the process CWD); adjust only if the tests reveal a gap, to make 5.3 pass.
- [x] 5.5 **(RED)** In `tests/integration/test_write_reports.py`, write a failing integration test `test_write_reports_creates_paired_html_and_pdf_files_with_matching_timestamp_in_cwd` invoking the real `write_reports(result)` with `monkeypatch.chdir(tmp_path)`, asserting both `schema-diff-report-*.html` and `*.pdf` exist with matching timestamp suffixes and the HTML file's content matches `render_html(result)` exactly, per design §8.5.
- [x] 5.6 **(GREEN)** Run the test from 5.5 against the real (un-mocked) `write_reports`, `render_html`, and `export_pdf`; fix any discrepancy between the written HTML file content and `render_html(result)`'s return value until 5.5 passes.

## Phase 6: Public API Export

- [x] 6.1 Update `src/schema_comparator/report/__init__.py` (replacing the current docstring-only placeholder) to import and re-export `render_html`, `export_pdf`, `render_console`, `PdfExportError`, and `write_reports`, with a matching `__all__`, per design §1. (No new behavior — a re-export surface; covered by the existing Phase 2-5 unit tests plus the Phase 8 import-smoke check.)

## Phase 7: CLI Wiring

- [x] 7.1 **(RED)** In a new `tests/unit/test_cli.py` (or extending an existing CLI test module if one exists), write failing tests `test_cli_main_invokes_write_reports_after_compare_snapshots` (mocking `load_profiles`, `discover_schema`, `compare_snapshots`, `write_reports`) and `test_cli_main_filters_profiles_when_profiles_flag_given`, per design §6.2.
- [x] 7.2 **(GREEN)** Extend `src/schema_comparator/cli.py` — replace the placeholder `main()` with `build_arg_parser()` (`--config` required, `--profiles` optional `nargs="+"`) and a `main(argv)` that loads profiles, optionally filters by `--profiles`, discovers schemas, compares snapshots, and calls `write_reports(result)` exactly once (no `--format` flag, per Decision 3), per design §6.2, to make 7.1 pass.

## Phase 8: Verification

- [x] 8.1 Run `pytest tests/unit/report tests/integration/test_pdf_export.py tests/integration/test_write_reports.py tests/unit/test_cli.py --cov=schema_comparator.report --cov=schema_comparator.cli` and confirm every scenario in spec REQ-001 through REQ-007 has a passing test, with no live DB access attempted by any unit test.
- [x] 8.2 Run `pytest tests/unit/test_import_smoke.py` (extended if needed to import `schema_comparator.report`) to confirm `Jinja2`/`xhtml2pdf` import cleanly in the installed environment.
- [x] 8.3 Confirm `src/schema_comparator/compare/**` and `src/schema_comparator/tui/**` are untouched (`git status`/`git diff --stat` shows no changes under either path), per the proposal's Out of Scope and Rollback Plan.
- [x] 8.4 Run the full existing test suite (`pytest`) to confirm no regression in `compare/`, `config/`, `discovery/`, or `connectors/` tests from the `cli.py` and `pyproject.toml` changes.

## Review Workload Forecast

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: High

| Field | Value |
|-------|-------|
| Estimated changed lines | ~950-1150 total: source ~350-400, tests ~550-700, plus vendored `pico.min.css` (third-party asset, excluded from review-risk line count) |
| Files touched | ~20: `src/schema_comparator/report/{html,pdf,console,errors,write,__init__}.py`, `templates/{report.html.jinja,pico.min.css}`, `cli.py`, `pyproject.toml`, `tests/unit/report/{conftest,test_html,test_pdf,test_console,test_write}.py` + `golden/*.html`, `tests/integration/{test_pdf_export,test_write_reports}.py`, `tests/unit/test_cli.py` |
| Chained PRs recommended | No — one cohesive, additive vertical slice; no functional subset is independently mergeable/reviewable without the others |
| 400-line budget risk | High — estimated total substantially exceeds the 400-line guideline, driven by three renderer modules, one Jinja2 template + vendored CSS asset, and their paired TDD unit/integration suites landing together |
| Decision needed before apply | No — delivery strategy and scope are already fixed by the proposal/design; `delivery_strategy: exception-ok` was set for this change |
