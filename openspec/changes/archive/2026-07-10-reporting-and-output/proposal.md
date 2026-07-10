# Proposal: Reporting and Output

## Intent

Implement Change B, the final Milestone 1 slice: HTML report generation,
PDF export of that HTML (`xhtml2pdf`), and a console summary, all consuming
the now-complete `ComparisonResult` produced by `comparison-engine`
(REQ-001..007, plus the missing-column/mismatch extensions from
`diff-detection-completion`). This turns a `ComparisonResult` into the three
human-facing artifacts the roadmap commits to for Milestone 1, without
reshaping or re-deriving any comparison logic.

## Scope

### In Scope

- An HTML renderer (`src/schema_comparator/report/html.py`) that takes a
  `ComparisonResult` and produces a single self-contained HTML string via a
  Jinja2 template: inline Pico.css (technical-baseline.md decision #9), a
  small custom overlay for diff-type row coloring, findings grouped by
  table, and an N-way column-per-profile layout for multi-profile findings.
- A PDF exporter (`src/schema_comparator/report/pdf.py`) that feeds the
  rendered HTML string into `xhtml2pdf.pisa.CreatePDF` and returns/writes
  PDF bytes. No separate PDF template.
- A console summary renderer (`src/schema_comparator/report/console.py`)
  that formats a plain-text summary directly from `ComparisonResult`
  (counts per diff type, compared profiles, per-table breakdown), fully
  independent of the HTML path.
- A report file naming/location convention (decided below) applied by
  whichever module writes files to disk (HTML/PDF only; console output is
  stdout-only).
- CLI wiring in `cli.py` sufficient to invoke report generation from a
  `ComparisonResult` and write outputs to disk (or stdout for console),
  including the CLI flag strategy decided below. This is argument-parsing
  and dispatch only — it does not build the interactive Textual shell.
- New runtime dependencies `Jinja2` and `xhtml2pdf` added to
  `pyproject.toml` `[project].dependencies`.
- Unit tests for HTML rendering (string/structure assertions) and console
  formatting (near-100% coverage, no I/O). Integration-level tests for PDF
  generation (non-empty bytes / successful generation) and any
  file-writing paths, under `tests/integration/`.

### Out of Scope

- Any further diff-detection logic — `ComparisonResult`/`DiffEntry` shapes
  are frozen inputs, not something this change may reshape
  (`comparison-engine`, `diff-detection-completion`).
- The interactive Textual TUI shell (connections list, checkboxes, add/
  edit/delete screens — technical-baseline.md decision #7). `cli.py` gains
  only enough argument parsing to select/trigger report output; the
  connections/selection TUI is a separate, larger, future change.
  `src/schema_comparator/tui/` remains an untouched placeholder.
- Likely-rename heuristics (Milestone 2).
- Persistence/versioning of past reports beyond the naming convention
  below (no report history browser, no diffing between report runs).
- Configurable HTML/PDF theming beyond the Pico.css + overlay already
  committed to by technical-baseline.md decision #9.

## Capabilities

### New Capabilities

- `reporting-and-output`: Given a `ComparisonResult`, render an HTML
  report, export a PDF from that HTML, and print a console summary, using
  a documented file-naming convention and CLI flag strategy.

### Modified Capabilities

None. `comparison-engine` is unaffected and continues to be consumed
read-only.

## Approach

### Decision 1 — Report file naming/location convention

**Decision: timestamped filenames in the current working directory,**
using the pattern `schema-diff-report-YYYYMMDD-HHMMSS.html` and
`schema-diff-report-YYYYMMDD-HHMMSS.pdf`, both generated from a single
run timestamp shared by both files (not one timestamp per format) so an
HTML/PDF pair from the same run is identifiable by matching suffix.

- Rationale: reruns are expected to be common during iterative use
  (adjusting connection profiles, re-checking after a migration); a fixed
  name would silently overwrite prior findings, which is a worse default
  than accumulating files a user can clean up manually. A configurable
  output directory is deferred — out of scope for v1 — since no config
  surface for it exists yet and the roadmap does not call for one; this
  keeps the decision minimal and reversible (the output path is a single
  computed string, easy to change later without touching rendering logic).
- The output directory is the CWD from which the CLI is invoked, not a
  fixed absolute path, consistent with `config.example.yaml`/
  `config/loader.py` already resolving relative paths from the invocation
  context.

### Decision 2 — N-way table rendering approach in HTML

**Decision: one column per compared profile**, in a table whose header row
lists every `compared_profiles` name in the deterministic order already
provided by `ComparisonResult`. Each data row corresponds to one diff
entry (`MissingTable`, `MissingColumn`, or `ColumnMismatch`), grouped and
sub-headed by qualified table identity, in the existing engine ordering
(REQ-comparison-engine-004 tie-break: `MissingTable` < `MissingColumn` <
`ColumnMismatch`, then column name ascending).

- For `MissingTable`/`MissingColumn`: the row's profile column shows a
  "missing" marker (e.g. a styled dash `—`) for `missing_from_profile`,
  and is left blank/neutral for profiles where the object is present (not
  the subject of that row).
- For `ColumnMismatch`: each present profile's column shows its
  `ColumnAttributes` (type/size/precision/scale/nullability) rendered as
  a compact string (e.g. `varchar(50), NULL`); profiles not present for
  that table are blank.
- Rationale: a one-column-per-profile grid reads naturally as a
  side-by-side comparison regardless of N (2 to ~20 profiles per
  technical-baseline's assumed range), reuses one row-rendering
  code path for all three diff-entry types (a per-type `dict[profile_name,
  cell_value]` built in the template context), and avoids the harder-to-
  scan "profile: value" flattened-list alternative when N is large. At the
  high end of the assumed profile-count range the table becomes wide;
  this is accepted as a v1 tradeoff (horizontal scroll in HTML/PDF is
  acceptable, per Pico.css's default table overflow behavior) rather than
  building a second, more complex layout mode now.

### Decision 3 — CLI flag strategy for output-format selection

**Decision: always produce all three outputs in v1 (no format-selection
flag)**, per the exploration's minimal-risk recommendation. `cli.py` gains
just enough argument parsing to accept the inputs already required to run
a comparison (config path, profile selection) and, after producing a
`ComparisonResult`, unconditionally calls all three renderers: writes the
HTML and PDF files (Decision 1 naming) and prints the console summary to
stdout.

- Rationale: `cli.py` is currently a placeholder with zero argument
  parsing; introducing a `--format` flag now would require designing UX
  that the future interactive Textual shell (decision #7, not yet built
  and not owned by this change) may immediately obsolete or duplicate.
  Deferring format-selection avoids that rework. This is explicitly a v1
  scope decision, not a permanent constraint — a later change may add
  `--format html,pdf,console` if a real need to skip formats emerges.

### Decision 4 — New dependencies

**Decision: add `Jinja2` and `xhtml2pdf` to `pyproject.toml`
`[project].dependencies`.** `xhtml2pdf` was already a roadmap/
technical-baseline commitment (decision #4); `Jinja2` is a new addition
this change introduces, justified by the exploration's analysis (pure-
Python, no system deps, standard fit for grouped/conditional HTML
generation, testable independently of rendering call sites).
