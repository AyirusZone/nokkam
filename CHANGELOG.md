# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- CI/CD pipeline: lint, format-check, type-check, test, build, and package
  validation on every PR and push to `development`/`master`.
- Automated dev releases to TestPyPI (`dev-v*` tags) and production releases
  to PyPI (`v*` tags) via GitHub Actions, using Trusted Publishing (OIDC).
- `pre-commit` configuration, `.editorconfig`, `CONTRIBUTING.md`,
  `CODE_OF_CONDUCT.md`, `SECURITY.md`, and Dependabot configuration.
- `ruff`, `black`, and `mypy` configuration in `pyproject.toml`; `pytest-cov`
  coverage reporting (XML + HTML).

## [0.1.0] - 2026-07-25

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
- Time-tracking timer and Pomodoro mode.
- Desktop notifications for due-soon tasks and Pomodoro completion, with a
  configurable accent color.
- Contribution heatmap and task dependencies (blocked-by relationships).
- Home screen redesign: calendar and task list side by side
  (calcurse-style 3-pane layout).
- PyPI-ready packaging with cross-platform (including Windows) notification
  support.

### Fixed

- Timestamps were recorded in UTC while all business logic assumed local
  time; all timestamp columns now consistently use local time.

[Unreleased]: https://github.com/AyirusZone/cad_tui/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/AyirusZone/cad_tui/releases/tag/v0.1.0
