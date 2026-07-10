# Archive Report: Reporting and Output (Change B)

**Change**: `reporting-and-output`
**Archive date**: 2026-07-10
**Verification verdict**: PASS (no CRITICAL findings)

## Close Gate

`verify-report.md` reports **PASS**: an independent re-run of `pytest -q`
reproduced 136 passed / 1 skipped, matching `apply-progress.md` exactly —
not stale. All 7 requirements and 20/20 scenarios were traced
scenario-by-scenario to passing tests by reading `html.py`, `pdf.py`,
`console.py`, and `write.py` directly, not by trusting the narrative. All
6 documented deviations from design were independently re-verified as
accurate and justified. Zero CRITICAL findings. Two non-blocking findings,
both accepted as follow-up notes rather than fixed before archive:

1. **WARNING — `pico.min.css` filename is misleading (cosmetic)**: the
   vendored file is a small self-authored stylesheet, not the actual
   third-party Pico.css library, despite the name implying a minified
   third-party build. The file's own header comment discloses this. Does
   not affect any requirement or test outcome. Accepted as-is; recommended
   as a low-risk rename (e.g. to `report.css`) in a future cleanup change,
   not a blocker for this archive.
2. **SUGGESTION — scope-boundary check (task 8.3) relies on working-tree
   state, not a clean diff**: neither `comparison-engine` follow-up work
   nor this change has been committed yet, so `git status`/`git diff
   --stat` alone cannot fully distinguish "untouched by this apply run"
   from pre-existing dirty state in `compare/`. No `compare/` or `tui/`
   file content was touched by any commit or task in this change, and no
   test in `tests/unit/compare/` regressed. Process hygiene, not a
   functional issue. Recommend committing pending `compare/` work before
   starting the next change.

Non-goals compliance confirmed: no diff-detection logic changes, no
Textual TUI shell built, no `--format` CLI flag added, no theming/
persistence beyond Decision 1's timestamped-filename convention.
Archive is permitted.

## What Shipped

- Three read-only renderers over `ComparisonResult` under
  `src/schema_comparator/report/`: `html.py` (`build_context`/
  `render_html`, self-contained Jinja2 template + vendored inline CSS),
  `pdf.py` (`export_pdf`, deriving the PDF from the exact HTML string, no
  second template), and `console.py` (`render_console`, independent of
  `jinja2`/`xhtml2pdf`).
- `errors.py` with `PdfExportError`, normalizing both the raised-exception
  and `err > 0` xhtml2pdf failure paths so no raw third-party exception
  ever escapes `export_pdf`.
- `write.py` `write_reports(result, *, out=sys.stdout)`: a single shared
  run timestamp, three independent `try/except Exception` blocks giving
  per-format failure isolation (HTML/PDF/console), writing timestamped
  `schema-diff-report-YYYYMMDD-HHMMSS.{html,pdf}` files to the invocation
  CWD.
- Public API re-export surface in `report/__init__.py`
  (`render_html`, `export_pdf`, `render_console`, `PdfExportError`,
  `write_reports`).
- `cli.py` extended from a placeholder to `build_arg_parser()`
  (`--config` required, `--profiles` optional) and `main(argv)` wiring
  `load_profiles` → optional filter → `extract_schema` →
  `compare_snapshots` → `write_reports(result)` exactly once (no
  `--format` flag, per Decision 3).
- New dependencies `Jinja2>=3.1` and `xhtml2pdf>=0.2.13` added to
  `pyproject.toml`, plus `pytest-cov>=5.0` as a test-tooling-only dev
  dependency to run the Phase 8 coverage command.
- 7 new test files (`tests/unit/report/{conftest,test_html,test_pdf,
  test_console,test_write}.py`, `tests/integration/{test_pdf_export,
  test_write_reports}.py`, `tests/unit/test_cli.py`) plus golden HTML
  fixtures, covering all 20 scenarios including genuine forced-failure
  evidence for per-format isolation and a real (un-mocked) `xhtml2pdf`
  CSS-compatibility spike-test.
- Full suite: 136 passed, 1 skipped (pre-existing, unrelated live-DB
  integration test) — no regression to `compare/`, `config/`,
  `discovery/`, or `connectors/` tests.

## Specification Synchronization

| Domain | Action | Details |
|--------|--------|---------|
| `reporting-and-output` | Created | This change introduces a brand-new capability domain with no prior baseline. The change-local spec at [specs/reporting-and-output/spec.md](specs/reporting-and-output/spec.md) is copied verbatim as the new baseline at [openspec/specs/reporting-and-output/spec.md](../../../specs/reporting-and-output/spec.md) — no merge was needed since no prior version of this domain existed. |

The canonical specification baselines after this archive:

- `openspec/specs/comparison-engine/spec.md`
- `openspec/specs/connection-profile-config/spec.md`
- `openspec/specs/schema-extraction/spec.md`
- `openspec/specs/reporting-and-output/spec.md` (new)

No other capability baseline was touched; this change only reads
`ComparisonResult`/`DiffEntry` as an already-produced, immutable input.

## Decisions and ADRs

No `open_decisions` entries or change-local ADR files were present to
promote. The four clarification-session Q&A pairs recorded in the
change-local spec (report file naming/location convention, N-way column
layout, CLI format-selection scope, PDF failure isolation) are preserved
verbatim in the new baseline spec's Clarifications section; they were
resolved without a blocking user question during the spec-writing phase.

## Archive Copy

Artifacts were copied to
`openspec/changes/archive/2026-07-10-reporting-and-output/`. The active
source directory (`openspec/changes/reporting-and-output/`) could not be
deleted by this executor — no file-delete/move tool is available in this
environment (same limitation noted in the prior `comparison-engine` and
`diff-detection-completion` archives). See the Residual Cleanup section
of the final result for the exact path requiring manual removal.

## Cost

No per-phase cost data was recorded for this change
(`.ospec/session/reporting-and-output/phase-costs.jsonl` missing or
empty).

**Total user questions asked**: 0 (all clarifications resolved during the
spec-writing phase without a blocking user question).
