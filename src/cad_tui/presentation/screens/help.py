from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static

HELP_TEXT = """\
[bold $accent]cad — keybindings[/]

[bold]Home (calendar + tasks)[/]
  tab        cycle focus: calendar / today's tasks / all tasks
  h/j/k/l    move (day+week in calendar, line in a task list)
  [[ / ]]    prev / next month
  t          jump to today (calendar focused) or start/stop timer (task focused)
  a          add task (defaults to selected day if calendar/day-pane focused)
  e          edit selected task
  d          delete selected task
  space      toggle complete
  s          add subtask under selected
  u          undo last action
  A          quick add (free text, e.g. "Buy milk tmrw 3pm")
  w          open agenda (next 14 days)
  S          open stats
  P          open Pomodoro (25/5 focus timer)

[bold]Command palette[/]
  ctrl+k     open palette — fuzzy-search tasks to jump to them,
             or run: Add task, Quick add, Undo, Focus calendar,
             Open agenda, Show stats, Smart list: Today/Overdue/
             This week/All tasks

[bold]Global[/]
  ctrl+t     toggle theme
  ?          this help
  q          quit
  esc        close this dialog
"""


class HelpModal(ModalScreen[None]):
    BINDINGS = [("escape", "close_help", "Close"), ("question_mark", "close_help", "Close")]

    def compose(self) -> ComposeResult:
        with VerticalScroll(classes="panel", id="help-panel"):
            yield Static(HELP_TEXT)

    def action_close_help(self) -> None:
        self.dismiss(None)
