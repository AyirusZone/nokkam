# nokkam

[![CI](https://github.com/AyirusZone/cad_tui/actions/workflows/ci.yml/badge.svg)](https://github.com/AyirusZone/cad_tui/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/nokkam.svg)](https://pypi.org/project/nokkam/)
[![Python versions](https://img.shields.io/pypi/pyversions/nokkam.svg)](https://pypi.org/project/nokkam/)
[![Downloads](https://img.shields.io/pypi/dm/nokkam.svg)](https://pypi.org/project/nokkam/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A calcurse-inspired terminal task manager and calendar. Calendar and tasks
live side by side on one home screen — no mode-switching to see what's due.
Local-first: everything lives in a single SQLite file, nothing leaves your
machine.

```
┌──────────────────────────────────────────────────────────────┐
│ nokkam / home                                     July 2026  │
├─────────────────┬────────────────────────────────────────────┤
│ mo tu we th fr  │ Saturday, 25 July 2026                     │
│ sa su           │    Design system spec        2026-07-25    │
│                 │    Standup              2026-07-25 09:00   │
│ 29 30  1  2  3  │ ────────────────────────────────────────── │
│  4  5▓ 6  7  8  │ All tasks                                  │
│  9 10 11 12 13  │    Design system spec        2026-07-25    │
│ ...             │    Standup              2026-07-25 09:00   │
│                 │    Weekly review             2026-07-28    │
│                 │    Read newsletter                         │
├─────────────────┴────────────────────────────────────────────┤
│ [ Prev ]  Next  t Today/Timer  a Add  e Edit  d Delete ...   │
└──────────────────────────────────────────────────────────────┘
```

## Contents

- [Features](#features)
- [Install](#install)
- [Usage](#usage)
- [Configuration](#configuration)
- [Development](#development)
- [Versioning](#versioning)
- [Release process](#release-process)
- [Contributing](#contributing)
- [License](#license)

## Features

**Tasks**
- Priority (high/medium/low), due date + time, projects, tags
- Subtasks with indented tree display
- Recurrence — type it in plain words in the task form's **Repeats** field;
  completing a recurring task automatically spawns the next occurrence.
  `every day`, `every 3 days`, `every 2 weeks`, `every weekday`,
  `every weekend`, `every mon,wed,fri`, `every 2 weeks on mon,thu`,
  `every month`, `every first tue`, `every last fri`, `every year`; add
  `until 2026-12-31` and/or `for 10 times` to end a series. Invalid text is
  rejected with a hint instead of being ignored.
- Dependencies — mark a task "blocked by" another; completing a blocked
  task is refused until its blocker is done
- Undo — every add/edit/delete/toggle can be undone with `u`

**Calendar (always visible, not a separate mode)**
- Month grid with a task-count dot on any day that has tasks due
- Keyboard (`h j k l` / arrows, `[` `]` for month) or mouse (click a day)
- The right-hand panes update live to whichever day is selected

**Quick add** — free-text capture with natural-language dates:
`Buy milk tmrw 3pm`, `Standup fri 9:30`, `Follow up in 3 days` — and
recurrence: `Standup every weekday 9:30`, `Book club every first tue`,
`Water plants every 2 days`. A recurring task with no date starts on the
first day the pattern fits. The same text works from the shell:
`nokkam add "Pay rent every month"`.

**Command palette** (`Ctrl+K`) — fuzzy-search tasks to jump to one, or run
any action: Add task, Quick add, Undo, Focus calendar, Open agenda, Show
stats, Pomodoro, Smart list: Today/Overdue/This week/All

**Smart lists** — Today, Overdue, This week, All (filters the task list
in place; shown in the header)

**Saved filters** — combine conditions in the command palette with
`Filter tasks…`, or name one with `Save filter…` and recall it later as
`Filter: <name>`. Syntax: `project:Work tag:urgent priority:high due:week`
plus free words that must appear in the title. Different keys AND together;
repeating a key ORs (`tag:a tag:b`). `due:` takes today, tomorrow, overdue,
week, none or a date; open tasks only unless you add `status:all` or
`status:done`. Quote values with spaces: `project:"Big Launch"`.

**Agenda** — rolling 14-day view of everything upcoming, chronological

**Stats** — completion rate, current streak, overdue count, and a
GitHub-style contribution heatmap of the last 12 weeks

**Projects overview** (`O`) — one row per project: done/total, open,
overdue, a progress bar, total time tracked, and time tracked in the last
7 days, plus a "No project" row for unassigned tasks

**Time tracking** — start/stop a timer on the selected task (starting a
new one stops whatever was running); **Pomodoro** — 25/5 focus timer with
pause/reset

**Reminders** — due-soon desktop notifications (macOS, Linux, Windows),
each task surfaced only once

**Import/export** — JSON and CSV round-trip tasks including tags; ICS
export for calendar apps

**CLI quick-capture** — `nokkam add "..."` writes a task from your shell
without opening the UI

**Design** — a considered visual system, not default Textual chrome: warm
near-black/linen-white neutrals, a single configurable signature accent
(vermillion by default), priority shown as a colored accent bar rather than
an icon, light/dark theme (`Ctrl+T`)

## Install

Requires Python 3.11+. Runs anywhere Textual does — macOS, Linux, and
Windows (Windows Terminal recommended for full color/glyph support).

**From PyPI** (once published):

```bash
pipx install nokkam   # or: pip install nokkam
```

**From source:**

```bash
git clone git@github.com:AyirusZone/cad_tui.git nokkam
cd nokkam
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install .
```

The only runtime dependency is [Textual](https://github.com/Textualize/textual)
— no C extensions, nothing else to compile.

## Usage

```bash
nokkam
```

launches the home screen: calendar on the left, the selected day's tasks
top-right, the full task list bottom-right. Data lives in
`~/.nokkam/data.db` (SQLite) — nothing else to set up.

### Panes and focus

`Tab` cycles focus between the three panes (calendar → today's tasks → all
tasks). Which pane is focused changes what a few keys do:

- `t` — jumps the calendar to today if the calendar pane is focused,
  otherwise starts/stops the timer on the selected task
- `a` — adding a task defaults its due date to the selected calendar day
  when the calendar or day pane is focused, otherwise leaves it blank

Everything else (`e` edit, `d` delete, `space` toggle complete, `s` add
subtask) acts on whichever task is currently selected, in whichever pane
has focus.

### Keybindings

| Key | Action |
|---|---|
| `Tab` | Cycle focus: calendar / today's tasks / all tasks |
| `h` `j` `k` `l` / arrows | Move — day+week in the calendar, line in a task list |
| `[` / `]` | Previous / next month |
| `t` | Jump to today (calendar focused) or start/stop timer (task focused) |
| `a` | Add task |
| `e` | Edit selected task |
| `d` | Delete selected task |
| `space` | Toggle complete |
| `s` | Add subtask under selected |
| `u` | Undo last action |
| `A` | Quick add (free text with a natural-language date) |
| `w` | Open agenda (next 14 days) |
| `S` | Open stats |
| `O` | Open projects overview (progress + time per project) |
| `P` | Open Pomodoro (25/5 focus timer) |
| `Ctrl+T` | Toggle light/dark theme |
| `Ctrl+K` | Command palette |
| `?` | Help |
| `q` | Quit |
| `esc` | Close current dialog / go back |

Clicking a calendar day with the mouse selects it, same as navigating to
it with the keyboard.

### Task fields

The add/edit form covers: title, notes, priority, due date + time,
project, tags (comma-separated), repeats (none/daily/weekly/monthly), and
"blocked by" (matched against an existing task's title). A subtask is
created the same way, just pinned under the task you had selected when you
pressed `s`.

Completing a task that's still blocked is refused with a warning instead
of silently succeeding. Completing a recurring task spawns its next
occurrence automatically, carrying over title, priority, project, and
tags.

### CLI quick-capture

Add a task without opening the UI — writes straight to the same database:

```bash
nokkam add "Buy milk tmrw 3pm"
nokkam add "Renew passport" --due 2026-09-01 --priority high --project Admin --tags docs,travel
```

Flags: `--due YYYY-MM-DD` (overrides any date parsed from the text),
`--priority high|medium|low`, `--project NAME`, `--tags a,b,c`.

### Import / export

```bash
nokkam export --format json --out tasks.json
nokkam export --format csv  --out tasks.csv
nokkam export --format ics  --out tasks.ics   # calendar apps

nokkam import --format json --in tasks.json
nokkam import --format csv  --in tasks.csv
```

JSON and CSV round-trip tags by name; ICS is export-only.

## Configuration

Optional — `~/.nokkam/config.toml`. Every option is optional; these are the
defaults:

```toml
theme = "nokkam-dark"       # or "nokkam-light"
accent = "#FF6B4A"          # any hex color; drives both themes' accent
db_path = "~/.nokkam/data.db"
default_priority = "medium" # priority new tasks start with: high | medium | low
first_weekday = "monday"    # calendar week starts on: monday | sunday
# start_filter = "today"    # apply on launch: today | overdue | week | a saved filter's name
# ics_sources = ["/path/to/calendar.ics", "https://example.com/cal.ics"]

# icons = { flight = "✈", standup = "🗣" }   # keyword -> icon overrides

# Rebind any home-screen or global key by its binding id. Separate several
# keys with a comma. Only the keys shown here change; the rest keep defaults.
[keys]
# add_task = "n"
# nav_left = "left,a"
```

A mistake in this file never stops nokkam from starting: bad TOML, a wrong
value, an unknown option or binding name, or two actions on the same key are
each reported as a warning notification (and the default is used).

**Binding ids** for `[keys]` (default key in brackets): `nav_left` [left,h],
`nav_right` [right,l], `nav_up` [up,k], `nav_down` [down,j], `prev_month` `[`,
`next_month` `]`, `context_today_or_timer` [t], `pause_resume_timer` [p],
`add_task` [a], `edit_task` [e], `delete_task` [d], `toggle_complete` [space],
`undo` [u], `add_subtask` [s], `quick_add` [A], `open_agenda` [w],
`open_stats` [S], `open_project_summary` [O], `open_pomodoro` [P],
`sync_calendars` [R], `show_help` [?], `toggle_theme` [ctrl+t],
`command_palette` [ctrl+k], `quit` [q]. Dialogs keep their fixed keys.

## Development

```bash
git clone https://github.com/AyirusZone/cad_tui.git nokkam
cd nokkam
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

The app is layered (`presentation` → `services` → `domain` → `data`/`infra`)
so business logic stays independent of the Textual UI. See commit history
for the phase-by-phase build log.

### Testing

```bash
pytest
pytest --cov=nokkam --cov-report=term-missing --cov-report=xml --cov-report=html
```

### Linting

```bash
ruff check src tests
```

### Formatting

```bash
black --check src tests   # verify
black src tests           # apply
```

### Type checking

```bash
mypy src
```

### Packaging

```bash
python -m build
twine check dist/*
```

## Versioning

nokkam follows [Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`).
Development releases use a PEP 440 dev suffix, e.g. `0.5.0.dev1`; stable
releases drop it, e.g. `0.5.0`. See [CHANGELOG.md](CHANGELOG.md) for the
version history.

## Release process

Releases are fully automated by CI once a tag is pushed — nothing is
published from a developer's machine.

| Branch        | Tag             | Publishes to | GitHub artifact  |
|---------------|-----------------|--------------|------------------|
| `development` | `dev-vX.Y.Z`    | TestPyPI     | Pre-release      |
| `master`      | `vX.Y.Z`        | PyPI         | Release          |

Each tag push runs: validate the tag matches the `pyproject.toml` version →
build → test → publish → create the GitHub release/pre-release with the
wheel and sdist attached. A version/tag mismatch fails the workflow before
anything is published. Maintainers: see the repository's release runbook
for the manual tagging steps.

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for the
branch strategy, dev setup, and pull request checklist. Please also review
the [Code of Conduct](CODE_OF_CONDUCT.md). To report a security issue, see
[SECURITY.md](SECURITY.md) instead of opening a public issue.

## License

[MIT](LICENSE)
