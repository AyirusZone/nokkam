from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static

HELP_TEXT = """\
[bold accent]cad-tui — keybindings[/]

[bold]Task list[/]
  a          add task
  e          edit selected task
  d          delete selected task
  space      toggle complete
  j / down   move down
  k / up     move up
  u          undo last action
  c          open calendar
  s          add subtask under selected
  A          quick add (free text, e.g. "Buy milk tmrw 3pm")
  w          open agenda (next 14 days)
  S          open stats
  t          start/stop timer on selected task
  P          open Pomodoro (25/5 focus timer)

[bold]Calendar[/]
  h/j/k/l    move day / week
  [[ / ]]    prev / next month
  t          jump to today
  a d space  add / delete / toggle (selected day)
  esc        back to task list

[bold]Command palette[/]
  ctrl+k     open palette — fuzzy-search tasks to jump to them,
             or run: Add task, Quick add, Undo, Open calendar,
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
