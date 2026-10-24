# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-10-24

### Added

- Saved filters: `project:`/`tag:`/`priority:`/`due:`/`status:` queries
  (plus title words) applied from the command palette, with named filters
  stored in the database.
- Projects overview screen (`O`, or "Project summary" in the command
  palette): per-project progress, overdue count, and time tracked overall
  and over the last 7 days.
- Habit streaks screen (`H`): current and best streak, on-time rate and recent
  history for every recurring task.
- Time report screen (`T`): time per project as bars and per day as a column
  chart, for the last 7 days, 30 days or all time.
- Richer recurrence: every N days/weeks/months/years, weekly on chosen days
  (`every mon,wed,fri`, `every weekday`), the nth or last weekday of a month
  (`every first tue`), and `until <date>` / `for N times` limits. Available in
  the task form's Repeats field, in quick add (`Standup every weekday 9:30`)
  and in `nokkam add`. One-word spellings (`everyday`) and plural day names
  (`mondays`) are understood.
- Configurable keybindings (`[keys]` in `config.toml`) plus new options
  `default_priority`, `first_weekday` (Monday or Sunday) and `start_filter`.

### Changed

- The task form's Repeats dropdown (daily/weekly/monthly only) is now a text
  field with a dropdown of ready-made intervals beside it (every day, weekday,
  weekend, week, 2 weeks, month, 3 months, year, or Custom…).
- Editing a recurring task's repeat rule updates its series in place instead of
  starting a new one, so its habit history and streak are kept.
- The Projects and Tags panes now list every project and tag, not only those
  already attached to a task.
- Existing databases upgrade automatically on first launch (schema versions 4
  and 5 add one table and two columns; nothing is removed or rewritten).

### Fixed

- Adding a project or tag from its pane appeared to do nothing, because the
  pane hid anything not yet used by a task.
- Adding or editing a recurring task with no explicit due date left it
  undated — invisible on the calendar and never actually scheduled. It now
  defaults to the first day the repeat rule fits.
- A malformed `config.toml` (bad TOML, wrong value type, unknown option or key
  binding, or a key bound to two actions) used to crash on launch. It now shows
  a warning notification and falls back to the default.

## [0.1.0] - 2026-07-26

### Added

- Initial Textual TUI application scaffold with SQLite storage and a
  Material-tonal/Apple-HIG-inspired theme system.
- Task management: create/edit/delete, priority, tags, projects, and undo.
- Calendar month view linked to tasks, with mouse support.
- Quick-add with natural-language dates, subtasks, and recurrence
  (daily/weekly/monthly).
- Command palette (`Ctrl+K`), smart lists (today/overdue/this week), agenda
  view, and stats screen.
- CLI quick-capture command plus JSON export/import.
- Time-tracking timer (with pause/resume) and Pomodoro mode.
- Desktop notifications for due-soon tasks and Pomodoro completion, with a
  configurable accent color.
- Contribution heatmap and task dependencies (blocked-by relationships).
- Home screen redesign: calendar and task list side by side
  (calcurse-style 3-pane layout), with a live clock/timer header and
  Projects/Tags/All Tasks filter tabs that narrow both panes.
- Read-only `.ics` calendar sync (local file or URL), keyword-based task
  icons, and a private-task flag that masks titles everywhere they appear.
- Responsive layout: the home screen degrades gracefully on narrow/short
  terminals instead of clipping panes to zero size.
- CI/CD pipeline: lint, format-check, type-check, test, build, and package
  validation on every PR and push to `development`/`master`.
- Automated dev releases to TestPyPI (`dev-v*` tags) and production releases
  to PyPI (`v*` tags) via GitHub Actions, using Trusted Publishing (OIDC).
- `pre-commit` configuration, `.editorconfig`, `CONTRIBUTING.md`,
  `CODE_OF_CONDUCT.md`, `SECURITY.md`, and Dependabot configuration.
- `ruff`, `black`, and `mypy` configuration in `pyproject.toml`; `pytest-cov`
  coverage reporting (XML + HTML) with an enforced 85% floor.
- PyPI-ready packaging (`py.typed` marker, cross-platform notification
  support including Windows).

### Changed

- Renamed the project from `cad-tui` to `nokkam`: package, CLI command,
  config directory (`~/.cad-tui` -> `~/.nokkam`), and theme names
  (`cad-dark`/`cad-light` -> `nokkam-dark`/`nokkam-light`).

### Fixed

- Timestamps were recorded in UTC while all business logic assumed local
  time; all timestamp columns now consistently use local time.

[Unreleased]: https://github.com/AyirusZone/nokkam/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/AyirusZone/nokkam/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/AyirusZone/nokkam/releases/tag/v0.1.0
