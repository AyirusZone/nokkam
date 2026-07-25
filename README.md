# cad-tui

A calcurse-inspired terminal task manager and calendar, styled with a
Material-tonal / Apple-HIG color system. Local-first — everything lives in a
single SQLite file, nothing leaves your machine.

## Features

- **Tasks** — priority, due date/time, projects, tags, subtasks, recurrence
  (daily/weekly/monthly), dependencies ("blocked by"), undo for every
  destructive action
- **Calendar** — month grid linked to tasks, day/week/month navigation,
  mouse and keyboard, jump-to-today
- **Agenda** — rolling 14-day view of what's coming up
- **Command palette** (`Ctrl+K`) — fuzzy-search tasks to jump to them, or run
  any action (add, undo, open calendar/agenda/stats, smart-list filters)
- **Quick add** — free-text capture with natural-language dates, e.g.
  `Buy milk tmrw 3pm`, `Standup fri 9:30`
- **Smart lists** — Today, Overdue, This week, All
- **Time tracking** — start/stop a timer per task; **Pomodoro** — 25/5 focus
  timer
- **Stats** — completion rate, streak, GitHub-style contribution heatmap
- **Reminders** — due-soon desktop notifications (macOS, Linux, Windows), deduplicated
- **Import/export** — JSON, CSV, and ICS (calendar interop)
- **CLI quick-capture** — add a task from your shell without opening the UI
- Light/dark theme with a single configurable accent color

## Install

Requires Python 3.11+. Runs anywhere Textual does — macOS, Linux, and Windows
(Windows Terminal recommended for full color/glyph support).

**From PyPI** (once published):

```bash
pipx install cad-tui   # or: pip install cad-tui
```

**From source:**

```bash
git clone git@github.com:AyirusZone/cad_tui.git
cd cad_tui
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install .
```

The only runtime dependency is [Textual](https://github.com/Textualize/textual)
— no C extensions, nothing else to compile.

## Usage

```bash
cad-tui
```

launches the full-screen UI. Your data lives in `~/.cad-tui/data.db`
(SQLite) — nothing else to set up.

### Keybindings

**Task list**

| Key | Action |
|---|---|
| `a` | Add task |
| `e` | Edit selected task |
| `d` | Delete selected task |
| `space` | Toggle complete |
| `j` / `↓`, `k` / `↑` | Move down / up |
| `u` | Undo last action |
| `s` | Add subtask under selected |
| `A` | Quick add (free text with natural-language date) |
| `c` | Open calendar |
| `w` | Open agenda (next 14 days) |
| `S` | Open stats |
| `t` | Start/stop timer on selected task |
| `P` | Open Pomodoro (25/5 focus timer) |
| `?` | Help |

**Calendar**

| Key | Action |
|---|---|
| `h` `j` `k` `l` / arrows | Move day / week (or click a day) |
| `[` / `]` | Previous / next month |
| `t` | Jump to today |
| `a` `d` `space` | Add / delete / toggle complete (for the selected day) |
| `esc` | Back to task list |

**Command palette** (`Ctrl+K`)

Fuzzy-search your tasks to jump to one, or run: Add task, Quick add, Undo,
Open calendar, Open agenda, Show stats, Smart list: Today/Overdue/This
week/All tasks.

**Global**

| Key | Action |
|---|---|
| `Ctrl+T` | Toggle light/dark theme |
| `Ctrl+K` | Command palette |
| `q` | Quit |
| `esc` | Close current dialog |

### CLI quick-capture

Add a task without opening the UI — writes straight to the same database:

```bash
cad-tui add "Buy milk tmrw 3pm"
cad-tui add "Renew passport" --due 2026-09-01 --priority high --project Admin --tags docs,travel
```

Flags: `--due YYYY-MM-DD` (overrides any date parsed from the text),
`--priority high|medium|low`, `--project NAME`, `--tags a,b,c`.

### Import / export

```bash
cad-tui export --format json --out tasks.json
cad-tui export --format csv  --out tasks.csv
cad-tui export --format ics  --out tasks.ics   # calendar apps

cad-tui import --format json --in tasks.json
cad-tui import --format csv  --in tasks.csv
```

JSON and CSV round-trip tags by name; ICS is export-only.

## Configuration

Optional — `~/.cad-tui/config.toml`:

```toml
theme = "cad-dark"       # or "cad-light"
accent = "#FF6B4A"       # any hex color; drives both themes' accent
db_path = "~/.cad-tui/data.db"
```

Nothing needs to be set — these are the defaults if the file is absent.

## Development

```bash
pip install -e ".[dev]"
pytest
```

The app is layered (`presentation` → `services` → `domain` → `data`/`infra`)
so business logic stays independent of the Textual UI. See commit history
for the phase-by-phase build log.

## License

[MIT](LICENSE)
