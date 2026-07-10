# Verify Report: Reporting and Output

Verdict: **PASS**

## Test Run Evidence (re-executed, not trusted from apply-progress.md)

```
python -m pytest -q
136 passed, 1 skipped in 1.16s
```

Matches the counts reported in `apply-progress.md` exactly. Not stale.

Targeted re-run also confirmed:
- `tests/unit/report/` + `tests/integration/test_pdf_export.py` +
  `tests/integration/test_write_reports.py` + `tests/unit/test_cli.py`: all
  green, including the two real (un-mocked) integration tests exercising
  `xhtml2pdf` and `write_reports`.

## Requirement-by-Requirement Check

| Req | Scenario coverage | Code verified | Verdict |
|-----|--------------------|----------------|---------|
| REQ-001 (self-contained HTML) | 6/6 build_context + 4/4 render_html tests | `html.py` groups via `itertools.groupby` over already-sorted `result.entries` (no re-sort); header row iterates `compared_profiles` in given order; `MissingTable`/`MissingColumn` mark `missing_from_profile` distinctly (`kind: "missing"`, `\u2014` + `cell-missing` CSS class); `ColumnMismatch` renders only present profiles' `ColumnAttributes`, blank elsewhere | Pass |
| REQ-002 (timestamped filenames, shared timestamp, CWD) | 2/2 unit + 1 integration | `write.py`: single `timestamp` computed once before both try/except blocks; files opened via bare relative `open(path, ...)` against process CWD | Pass |
| REQ-003 (PDF derived from same HTML string) | 1 integration | `write.py` passes the exact `html_str` returned by `render_html` into `export_pdf`; no second template exists | Pass |
| REQ-004 (graceful PDF degradation) | 3/3 mocked + 1 real integration spike-test | `pdf.py` normalizes both the raised-exception path and the `result.err > 0` path to `PdfExportError`; `write.py` catches it, prints a distinct `[ERROR] PDF report generation failed: ...` line separate from the console summary's own `print(render_console(...))` call, and still writes the HTML file / prints the console summary | Pass |
| REQ-005 (console independent of HTML/PDF) | 4/4 unit incl. import-isolation test | `console.py` imports neither `jinja2` nor `xhtml2pdf`; `render_console` is a pure function of `ComparisonResult` | Pass |
| REQ-006 (clean-comparison messaging, all 3 outputs) | golden HTML substrings + console test; PDF inherits via REQ-003 | `has_findings` flag drives the Jinja `{% if not has_findings %}` no-drift block; `render_console` early-returns the no-drift message without zero-count lines | Pass |
| REQ-007 (per-format failure isolation) | 4 dedicated tests with real forced failures + assertions on the other formats | `test_write_reports_html_failure_still_attempts_pdf_and_console`, `..._pdf_failure_still_leaves_html_written_and_console_printed`, `..._console_failure_still_leaves_html_and_pdf_written`, and `..._never_raises_past_the_function_boundary` each monkeypatch exactly one renderer/exporter to raise and assert the other two formats still completed (file exists on disk / console text present in captured `out`). This is genuine behavioral evidence, not just code inspection. | Pass |

20/20 scenarios traced and confirmed against actual code and passing tests.

## Deviation Verification

1. **`extract_schema` vs. design's `discover_schema`.** Confirmed:
   `src/schema_comparator/discovery/service.py` exports `extract_schema(profile, ...)`
   as the real, already-implemented function from the `schema-extraction`
   change; no `discover_schema` exists anywhere in `discovery/`. `cli.py`
   correctly imports and calls `extract_schema`. Deviation is accurate and
   necessary — the design snippet named a function that never existed.
2. **CSS simplification for xhtml2pdf compatibility.** Confirmed the quoted
   `"Segoe UI"` entry is absent from `templates/report.html.jinja`/
   `pico.min.css`; the real (un-mocked) `tests/integration/test_pdf_export.py`
   spike-test converts the actual template + overlay CSS and asserts valid
   `%PDF-` bytes are produced — this is genuine rendering evidence, not merely
   "doesn't crash." The design's own risk mitigation only required
   background-color/border/basic-font constructs, which the simplified CSS
   still provides (backgrounds for diff-type rows, borders on the no-drift
   box and table cells, a plain font stack). Graceful-degradation requirement
   (REQ-004) is separately covered by the mocked failure-path tests. Confirmed correct.
3. **`pytest-cov` declared in `pyproject.toml`.** Confirmed:
   `[project.optional-dependencies].dev` in [pyproject.toml](../../../pyproject.toml)
   lists `"pytest-cov>=5.0"` alongside `"pytest>=8.0"` — properly declared,
   not an ad-hoc/undeclared install.
4. **Failure isolation — actual test evidence.** Confirmed via direct reading
   of `tests/unit/report/test_write.py`: each of the three single-format
   failure tests patches exactly one of `render_html` / `export_pdf` /
   `render_console` to raise, then asserts the *other* formats' artifacts
   exist (file on disk) or text is present in the captured `out` stream.
   This is real forced-failure evidence, re-run and confirmed green in this
   verification pass, not just static code reading.

## Findings

### WARNING — `pico.min.css` filename is misleading (origin: `code-bug`, cosmetic/non-blocking)

The vendored file at
[src/schema_comparator/report/templates/pico.min.css](../../../src/schema_comparator/report/templates/pico.min.css)
is a small self-authored stylesheet, not the actual third-party Pico.css
library, despite the name and a `.min.css` extension implying a minified
third-party build. The file's own header comment discloses this, which
mitigates the risk, but a future maintainer skimming the file tree (or
attempting to "update" it by fetching the real Pico.css, which uses
different class names/conventions) could be misled. Does not affect any
requirement or test outcome. Suggest renaming to something like
`report.css` in a future low-risk cleanup change; not a blocker for this
change.

### SUGGESTION — Scope-boundary check (task 8.3) relies on working-tree state, not a clean diff

`git status`/`git diff --stat` for `src/schema_comparator/compare/` shows
pre-existing uncommitted modifications (from the `comparison-engine`
session, per prior commit history — only one `compare/` commit exists,
`ca3edb6`, and the working tree has further uncommitted changes on top of
it). Since neither the `comparison-engine` follow-up work nor this
`reporting-and-output` change has been committed yet, git alone cannot
fully distinguish "untouched by this apply run" from "pre-existing dirty
state." No `compare/` or `tui/` file content was touched by any commit or
task in this change's tasks.md, and no test in `tests/unit/compare/` or
elsewhere regressed, so this is process hygiene, not a functional issue.
Recommend committing pending `compare/` work before starting the next
change to keep future scope-boundary checks unambiguous.

## Summary

No CRITICAL issues found. 7/7 requirements and 20/20 scenarios verified
against actual code and passing, re-executed tests (136 passed, 1 skipped,
matching apply-progress.md exactly — not stale). All 6 documented
deviations were independently verified as accurate and justified. Two
non-blocking findings (1 WARNING, 1 SUGGESTION) are cosmetic/process
hygiene, not functional defects.

**Recommendation: proceed to `sdd-archive`.**
