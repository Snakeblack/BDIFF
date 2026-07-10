# Exploration — `reporting-and-output` (Change B)

## Scope

Final Milestone 1 slice: HTML report generation, PDF export of that HTML
(`xhtml2pdf`), and console/TUI summary output, consuming `ComparisonResult`
produced by the now-complete comparison engine (`comparison-engine` spec,
REQ-001..007, archived `diff-detection-completion`). No further diff-detection
logic in scope — `ComparisonResult` / `DiffEntry` shapes are frozen inputs
here, not something this change may reshape.

## 1. HTML report generation approach

- `pyproject.toml` currently declares only `PyYAML` and `pyodbc` as runtime
  deps (plus `pytest` under `dev`). **Jinja2 is not yet a dependency.**
- `docs/architecture/technical-baseline.md` decision #9 already commits to
  **Pico.css**, vendored/embedded inline (not CDN), as the base stylesheet,
  with a small custom CSS overlay for diff-type row coloring. This is a
  styling decision, not a templating-engine decision, so it doesn't resolve
  question 1 on its own but constrains the output (single self-contained
  HTML file, no external asset loads).
- Two realistic options:
  - **Jinja2 templates** (new dependency): standard, testable (render to
    string, assert on output), keeps HTML structure out of Python string
    concatenation, and is the natural fit for a "grouped by table,
    color-coded by diff type" report with loops/conditionals. Widely used,
    small, pure-Python, no system deps — consistent with the project's
    "pip install only" constraint (technical-baseline.md decision #9
    rationale, and decision #4 on xhtml2pdf for the same reason).
  - **Plain string building / f-strings**: zero new dependency, but a
    multi-section, color-coded, grouped-by-table report expressed as
    nested f-strings becomes hard to read/maintain and awkward to test
    structurally (string-matching over shaped fragments).
  - **Recommendation**: adopt **Jinja2** as a new declared dependency. It is
    the standard choice for this exact shape of problem, keeps templates
    separate from rendering logic (testable independently), and its
    footprint/install friction is comparable to (dominated by) `xhtml2pdf`,
    which the roadmap has already committed to adding. Flag as a new
    dependency to add to `pyproject.toml` `dependencies`, alongside
    `xhtml2pdf`.

## 2. PDF export via `xhtml2pdf`

- **Not currently a dependency** — `xhtml2pdf` must be added to
  `pyproject.toml` `dependencies`. This is already an explicit roadmap
  commitment (`docs/roadmap.md` Milestone 1, technical-baseline.md
  decision #4), not a new proposal — this exploration just confirms it
  isn't installed yet.
- `xhtml2pdf` consumes an HTML string (or file-like object) and writes PDF
  bytes via `xhtml2pdf.pisa.CreatePDF(html_string, dest=output_stream)`. It
  supports a constrained CSS subset (no modern flexbox/grid) — Pico.css's
  table/heading styling is simple enough to be broadly compatible, but the
  custom diff-coloring overlay CSS should stay simple (background-color,
  borders, basic fonts) and avoid CSS features `xhtml2pdf` doesn't support.
  This is a concrete risk to validate during design/apply (spike-test the
  actual generated HTML against `xhtml2pdf`, not just visually in a
  browser).
- Because `xhtml2pdf` takes HTML as input, **PDF export naturally derives
  from the already-rendered HTML string** — no separate PDF-specific
  templating is needed as long as the HTML is self-contained (inline CSS,
  no external references), which decision #9 already requires anyway.

## 3. Console/TUI summary output — recommended scope for v1

- `docs/architecture/technical-baseline.md` decision #7 commits the overall
  **product** to a Textual TUI (connections list, checkboxes, add/edit/
  delete screens) as the primary interaction model — that is a separate,
  larger scope (arguably its own future change wiring `cli.py` to launch
  the Textual `App`) and is **not yet built**: `cli.py` today is only a
  placeholder printing a static string, and `src/schema_comparator/tui/`
  is an empty package with only a docstring.
- The roadmap's own wording for this item is **"console/TUI summary
  output"**, i.e. a quick overview *after each run*, distinct from the
  full interactive connections/selection TUI described in decision #7.
  Building a full Textual results screen now would front-run the
  as-yet-unbuilt connections/selection TUI this change doesn't own, and
  roadmap Milestone 1 does not list "interactive TUI shell" as its own
  checklist item — only "Console/TUI summary output".
- **Recommendation**: implement a **simple formatted text summary printed
  to stdout** for v1 — counts of `MissingTable` / `MissingColumn` /
  `ColumnMismatch` entries, compared profiles, and (optionally) a per-table
  breakdown — using plain `print()`/f-strings or, at most, lightweight
  ANSI/color formatting. This satisfies the roadmap item without taking on
  a `rich`/`textual` dependency or interactive event loop prematurely, and
  keeps `src/schema_comparator/tui/` as the placeholder home for the real
  interactive shell (decision #7) which is a distinctly larger, separately
  proposable change.
- Naming/placement question to resolve in design: does this "console
  summary" belong under `report/` (as a third render target alongside
  HTML/PDF) or under `tui/` (since the roadmap phrases it as "Console/TUI")?
  Given `tui/`'s docstring already says "Textual App and screens" (i.e. an
  interactive shell, not a one-shot print), and `report/`'s docstring
  already says "HTML renderer, PDF export, console summary, ..." — the
  `report/` package's own docstring already anticipates housing console
  summary. **Recommendation: put the console summary renderer in
  `report/`**, matching its existing docstring, and leave `tui/` untouched
  for the future interactive-shell change.

## 4. Shared intermediate representation across HTML / PDF / console

- **HTML and PDF should share one rendering path**: render HTML once (from
  `ComparisonResult` via Jinja2 template), then feed that HTML string
  directly into `xhtml2pdf.pisa.CreatePDF`. No separate PDF template or
  intermediate model is needed — this keeps the two outputs from drifting
  and avoids duplicating the grouping/color-coding logic in two places.
- **Console output should be independent**, not derived from HTML. Parsing
  or stripping HTML to produce a terminal summary would be fragile and
  unnecessary — a plain-text summary can be built directly from
  `ComparisonResult` with its own minimal formatting logic. This matches
  the exploration prompt's own framing and keeps the console path free of
  any HTML-templating or `xhtml2pdf` dependency, so it stays cheap/fast
  and testable in isolation.
- Suggested internal shape for design: a single `report/` module (e.g.
  `report/html.py` for the Jinja2 render function returning a `str`,
  `report/pdf.py` wrapping `xhtml2pdf` around that `str`, `report/
  console.py` for the independent text summary), all consuming
  `ComparisonResult` directly — no new intermediate diff model needed,
  since `ComparisonResult`/`DiffEntry` are already a stable, sufficiently
  structured input (out of scope to reshape here).

## 5. Risks and open questions for spec writing

- **Output file naming/location convention**: not yet decided. Options:
  fixed name in CWD (e.g. `schema-diff-report.html` / `.pdf`), timestamped
  filename (e.g. `schema-diff-report-20260710-153000.html`), or a
  configurable output directory/path via a CLI flag or config value.
  Needs a decision in `sdd-propose`/`sdd-design` — affects whether reruns
  overwrite previous reports or accumulate them.
- **N > 2 profile rendering in HTML tables**: `ColumnMismatch.values_by_profile`
  and `MissingTable`/`MissingColumn.missing_from_profile` can each involve
  more than 2 profiles (`compared_profiles` is unbounded, technical-baseline
  assumes 3-20 databases). The HTML table layout needs a concrete column
  strategy for N-way display (e.g. one column per compared profile showing
  each profile's `ColumnAttributes` or a "missing" marker, versus a flatter
  "profile: value" list per row) — this is a genuine design decision, not
  resolved by this exploration.
- **CLI flags for output-format selection**: `cli.py` is currently a
  placeholder with no argument parsing at all. This change likely needs to
  decide whether output format selection is CLI-flag-driven (e.g.
  `--format html,pdf,console`, default all three) or config-driven, and
  whether the interactive Textual shell (decision #7, not yet built) will
  eventually replace flag-driven invocation entirely — worth flagging so
  the spec doesn't over-commit to a flag design that the future TUI change
  would immediately obsolete. Minimal-risk default: always produce all
  three outputs in v1 (no format-selection flag yet), deferring
  format-selection UX to whichever change wires up the interactive shell.
- **`xhtml2pdf` CSS-compatibility risk** (see item 2): Pico.css plus a
  custom overlay must be validated as renderable by `xhtml2pdf`'s
  constrained CSS support before committing to specific styling detail in
  design.
- **New dependencies**: this change introduces two new runtime dependencies
  not yet in `pyproject.toml` — `Jinja2` (recommended, item 1) and
  `xhtml2pdf` (already committed by roadmap/technical-baseline, item 2).
  Both should be added under `[project].dependencies`.
- **Testing implications** (per `stack-python-testing` project standard):
  HTML rendering and console-summary formatting are pure functions over
  `ComparisonResult` and should be fully unit-testable (assert on rendered
  string fragments/structure) without any DB or filesystem I/O — a strong
  candidate for close-to-100% coverage similar to the compare engine. PDF
  generation via `xhtml2pdf` is closer to an integration concern (produces
  binary output) — tests there likely assert non-empty PDF bytes /
  successful generation rather than byte-for-byte content, and file-writing
  paths (if any) belong under `tests/integration/`.
